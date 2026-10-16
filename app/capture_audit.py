"""Audit your capture: keyed data + scans in, an ordered list of fields where the paper disagrees with the keyed data out.

The buyer is an auditor (an outside PREP auditor, or internal audit). They bring
  (a) the keyed data: a CSV, one row per form, one column per field (INE PREP column names are detected), and
  (b) the scans: a ZIP of page images, or "use already-read forms" (the stored reads of this site).
For every keyed field the audit compares the keyed value with the model's digits and words and with the paper's own
identities, and orders every disagreement by the strength of its evidence. Nothing is decided here: a disputed field
goes to a person with its crop, who marks it "confirmed" or "not an error".

Reads: a form with a stored read (results/calls_gemma.jsonl, the pre-registered Gemma pass; then live reads from
app/state/live) costs no model call. A form without one is read live through the existing live-read path
(app.live.LiveManager: one at a time, budget guard), on its privacy-masked page only.

Privacy: uploaded scans are located and masked IN MEMORY by the core (app.upload.locate_and_mask ->
twohands.mask.prepare); only masked pages are written, under app/state/audits/<id>/pages/ (git-ignored). The ZIP is
read from memory and never extracted to disk. Every page and export uses "Option NN" for vote rows; the auditor's
own column names are shown neutralised (an INE column is shown as the field it holds).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import threading
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app import store as storemod
from app import upload as uploadmod

AUDITS = storemod.STATE / "audits"
SAMPLE_CSV = storemod.DATA / "audit_sample_prep300.csv"
STORED_RUN = storemod.RESULTS / "calls_gemma.jsonl"
SECOND_RUN = storemod.RESULTS / "calls_qwen.jsonl"   # the second reader (Qwen3.8-27B) for strict mode; read only
VERDICTS = storemod.RESULTS / "adjudication" / "verdicts.json"
ADJ_LEDGER = storemod.RESULTS / "adjudication" / "adjudication.jsonl"

MAX_CSV_BYTES = 20 * 1024 * 1024
MAX_ROWS = 50_000
MAX_ZIP_BYTES = 200 * 1024 * 1024
MAX_ZIP_FILES = 400
IMG_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")
_AID = re.compile(r"^a[0-9a-f]{12}$")
_FID = re.compile(r"^[A-Za-z0-9_\-]{1,40}$")
ID_ALIASES = ("CLAVE_CASILLA", "CLAVE", "FORM_ID", "FORM", "ID", "ACTA", "CASILLA", "FOLIO", "RECORD_ID")
MARKS = {"confirmed": "Confirmed capture error", "not_error": "Not an error"}
TIERS = (("strong", "Strong"), ("medium", "Medium"), ("weak", "Weak"))
VERDICT_LABEL = {"model_right": "capture error (paper = model)", "capture_right": "capture right (model misread)",
                 "neither": "neither matches the paper", "paper_ambiguous": "paper does not settle it",
                 "unreadable": "unreadable on the photo", "crop_wrong": "crop missed the field"}
_lock = threading.RLock()


# ------------------------------------------------------------------------------------------- schema helpers
def graded() -> list[dict]:
    """The fields a keyed file can hold: every schema field with a capture column (section 5 is not keyed)."""
    return [f for f in storemod.schema()["fields"] if f.get("csv")]


def norm(h: str) -> str:
    h = unicodedata.normalize("NFKD", str(h or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", h.upper().strip().strip("'\""))


def _names_for(f: dict) -> list[tuple[str, str]]:
    """(normalised header, how) candidates for one field, strongest first."""
    k = f["key"]
    code, name = storemod.code_of(k), storemod.name_of(k)
    out = [(norm(f["csv"]), "INE PREP column"), (norm(code), "field code"), (norm(name), "field name")]
    if code.startswith("OPT"):
        i = int(code[3:])
        out += [(f"OPTION{i}", "field name"), (f"OPT{i}", "field code")]
    else:
        out.append((norm(k), "field code"))
    seen, res = set(), []
    for a, how in out:
        if a and a not in seen:
            seen.add(a)
            res.append((a, how))
    return res


def automap(headers: list[str]) -> dict:
    """Detect the id column and the column of each field. INE PREP names (TOTAL_BOLETAS_SOBRANTES, PAN-PRI-PRD,
    TOTAL_VOTOS_ASENTADO, ...) are detected, as are this site's codes and names (OPT01, Option 01, Unused ballots).
    Returns {"id": index|None, "fields": {code: index|None}, "how": {code: "INE PREP column"|...}}."""
    nh = [norm(h) for h in headers]
    taken: set[int] = set()
    idc = None
    for a in ID_ALIASES:
        if norm(a) in nh:
            idc = nh.index(norm(a))
            break
    if idc is not None:
        taken.add(idc)
    fields, how = {}, {}
    for f in graded():
        code = storemod.code_of(f["key"])
        fields[code] = None
        for a, h in _names_for(f):
            hits = [i for i, x in enumerate(nh) if x == a and i not in taken]
            if len(hits) == 1:
                fields[code], how[code] = hits[0], h
                taken.add(hits[0])
                break
    return {"id": idc, "fields": fields, "how": how}


def display_header(h: str) -> str:
    """How the UI names one of the auditor's columns: an INE column is shown as the field it holds (never by party)."""
    n = norm(h)
    for f in graded():
        if n in (norm(f["csv"]), norm(f["key"])) and n != norm(storemod.name_of(f["key"])):
            return f"{storemod.name_of(f['key'])} (INE)"
    return storemod.neutralize(str(h).strip()) or "(no name)"


# ------------------------------------------------------------------------------------------- the keyed file
def parse_csv(text: str) -> tuple[list[str], list[list[str]]]:
    """CSV text -> (headers, rows). Tolerates INE's preamble lines above the header, a BOM, and , ; | or tab."""
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    start = 0
    ids = {norm(a) for a in ID_ALIASES}
    for i, ln in enumerate(lines[:60]):
        cells = [norm(c) for c in re.split(r"[,;|\t]", ln)]
        if ids & set(cells):
            start = i
            break
    head = lines[start] if start < len(lines) else ""
    delim = max([",", ";", "|", "\t"], key=lambda d: head.count(d))
    rd = csv.reader(io.StringIO("\n".join(lines[start:])), delimiter=delim)
    rows = [r for r in rd if any(c.strip() for c in r)]
    if not rows:
        raise ValueError("The file has no rows.")
    headers = [c.strip() for c in rows[0]]
    if len(headers) < 2:
        raise ValueError("Need at least two columns: a form id and one field.")
    if len(rows) - 1 > MAX_ROWS:
        raise ValueError(f"More than {MAX_ROWS:,} rows; split the file.")
    return headers, rows[1:]


def keyed_value(raw) -> tuple[Optional[int], str]:
    """A keyed cell -> (number or None, kind): kind is number | blank | illegible | no_data | text."""
    s = str(raw if raw is not None else "").strip().strip("'\"")
    t = s.replace(",", "").replace(" ", "")
    if t.isdigit():
        return int(t), "number"
    low = s.lower()
    if not s:
        return None, "blank"
    if low.startswith("ilegible") or low.startswith("illegible"):
        return None, "illegible"
    if low in ("sin dato", "sin datos", "no data", "-", "n/a", "na", "null", "none"):
        return None, "no_data"
    return None, "text"


def show_keyed(raw) -> str:
    v, kind = keyed_value(raw)
    return str(v) if v is not None else {"blank": "blank", "illegible": "illegible", "no_data": "no data"}.get(kind, "text")


# ------------------------------------------------------------------------------------------- reads
class View:
    """One read of one form, as the audit uses it."""

    def __init__(self, values, words, accepted, source, page, ok=True, why=""):
        self.values, self.words, self.accepted, self.source, self.page = values, words, accepted, source, page
        self.ok, self.why = ok, why


_STORED: dict = {}


def _last_rows(path: Path) -> dict[str, dict]:
    """A results/calls_<model>.jsonl file, last row per form (cached on its mtime and size; read only)."""
    try:
        st = path.stat()
    except OSError:
        return {}
    c = _STORED.get(str(path))
    if c is None or c[0] != (st.st_mtime_ns, st.st_size):
        rows = {}
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(ln)
            except ValueError:
                continue  # a line still being written by a running batch
            if isinstance(r, dict) and r.get("clave"):
                rows[r["clave"]] = r
        c = ((st.st_mtime_ns, st.st_size), rows)
        _STORED[str(path)] = c
    return c[1]


def stored_reads() -> dict[str, dict]:
    """The pre-registered Gemma pass, last row per form (as scripts/build_headline.py counts it)."""
    return _last_rows(STORED_RUN)


def second_reads() -> dict[str, dict]:
    """The stored Qwen reads (second reader for strict mode), last row per form."""
    return _last_rows(SECOND_RUN)


def second_value(fid: str, key: str):
    """(available, value) of the second reader (Qwen) for one field: available only when its read of the form parsed."""
    row = second_reads().get(fid)
    if not row or row.get("no_call") or row.get("not_located") or row.get("error") or not row.get("parsed_ok"):
        return False, None
    return True, storemod.iv(((row.get("fields") or {}).get(key) or {}).get("n"))


def _view_from_row(row: dict, source: str, page) -> View:
    keys = storemod.schema()["keys"]
    if row.get("no_call") or row.get("not_located"):
        return View({}, {}, False, source, None, ok=False, why="page not located: it goes to a person, no model call")
    if not row.get("parsed_ok"):
        return View({}, {}, False, source, page, ok=False, why="no readable answer from the model")
    F = row.get("fields") or {}
    return View({k: storemod.iv((F.get(k) or {}).get("n")) for k in keys},
                {k: storemod.iv((F.get(k) or {}).get("w")) for k in keys}, bool(row.get("accepted")), source, page)


def _view_from_live(fid: str, row: dict, source: str, page) -> Optional[View]:
    if not row or not row.get("parsed"):
        return None
    r = storemod.read_from_core(fid, "live", {"clave": fid, "parsed": row.get("parsed")})
    return View(r.values, r.words, storemod.evaluate(r)["accepted"], source, page)


def find_read(a: dict, fid: str) -> tuple[Optional[View], Optional[Path]]:
    """The read the audit uses for a form, and the masked page it would be read from (for a live read)."""
    s = storemod.get_store()
    own = page_of(a["id"], fid)
    stored_page = s.masked_image(fid)
    row = stored_reads().get(fid)
    if row is not None:
        v = _view_from_row(row, "stored read (Gemma-4-31B-IT, pre-registered run)", stored_page)
        if v.ok or own is None:
            return v, own or stored_page
    p = adir(a["id"]) / "reads" / f"{fid}.read.json"
    if p.is_file():
        v = _view_from_live(fid, storemod._jload(p, None), "live read for this audit", own or stored_page)
        if v:
            return v, own or stored_page
    lv = s.live.get(fid)
    if lv and stored_page:
        v = _view_from_live(fid, lv, "live read (this site)", stored_page)
        if v:
            return v, stored_page
    return None, own or stored_page


# ------------------------------------------------------------------------------------------- evidence and order
def _idents():
    s = storemod.schema()
    return [(i["name"], s["vote_keys"] if i["sum"] == "@vote" else list(i["sum"]), list(i["equals"]))
            for i in s.get("identities", [])]


def _check(vals: dict, lhs, rhs):
    a, b = [vals.get(k) for k in lhs], [vals.get(k) for k in rhs]
    if None in a or None in b:
        return None
    return sum(a), sum(b)


IDENT_NAMES = {"rows sum to TOTAL": "rows sum to TOTAL", "votaron + representantes = section 5":
               "voters + representatives = section 5", "section 5 = section 7": "section 5 = section 7",
               "section 7 = TOTAL": "section 7 = TOTAL"}


def evidence(key: str, kv: Optional[int], kind: str, view: View) -> dict:
    """Score one disputed field. Positive points say the paper is with the model (a capture error is likely);
    negative points say the model probably misread. Each signal carries the sentence the auditor sees."""
    m, w = view.values.get(key), view.words.get(key)
    sig: list[tuple[int, str]] = []
    if m is not None and w is not None and m == w:
        sig.append((3, f"model digits and words agree ({m})"))
    elif m is not None and w is not None:
        sig.append((-2, f"model digits {m} and words {w} disagree"))
    elif m is not None:
        sig.append((1, f"model read digits {m}; no words read"))
    if m is None and kv == 0:
        sig.append((-3, "keyed 0 where the model saw an empty row (the blank = 0 convention)"))
    elif m is None:
        sig.append((-1, "model saw the boxes blank or faint"))
    if kind in ("illegible", "no_data") and m is not None:
        sig.append((1, f"keyed as {'illegible' if kind == 'illegible' else 'no data'}; the model read a value"))
    pts = 0
    for name, lhs, rhs in _idents():
        if key not in lhs and key not in rhs:
            continue
        nm = IDENT_NAMES.get(name, name)
        mod = _check(view.values, lhs, rhs)
        if kv is not None:
            kd = _check({**view.values, key: kv}, lhs, rhs)
        else:
            kd = None
        if mod is None:
            continue
        if mod[0] == mod[1] and kd is not None and kd[0] != kd[1]:
            pts += 3
            sig.append((3, f"the keyed value breaks {nm} ({kd[0]} vs {kd[1]}); the model's value satisfies it"))
        elif mod[0] == mod[1] and kv is None:
            pts += 2
            sig.append((2, f"the model's value satisfies {nm}"))
        elif mod[0] != mod[1] and kd is not None and kd[0] == kd[1]:
            pts -= 3
            sig.append((-3, f"the keyed value satisfies {nm}; the model's breaks it ({mod[0]} vs {mod[1]})"))
    if view.accepted:
        sig.append((1, "the model's read of this form passes every check of the gate"))
    score = sum(p for p, _ in sig)
    tier = "strong" if score >= 6 else ("medium" if score >= 3 else "weak")
    return {"score": score, "tier": tier, "signals": [{"pts": p, "text": t} for p, t in sig]}


# ------------------------------------------------------------------------------------------- audits on disk
def valid_id(aid: str) -> bool:
    return bool(_AID.match(aid or ""))


def adir(aid: str) -> Path:
    return AUDITS / aid


def page_of(aid: str, fid: str) -> Optional[Path]:
    if not valid_id(aid) or not _FID.match(fid or ""):
        return None
    p = (adir(aid) / "pages" / f"{fid}.jpg").resolve()
    if AUDITS.resolve() not in p.parents or not p.is_file():
        return None
    return p


def load(aid: str) -> Optional[dict]:
    if not valid_id(aid):
        return None
    a = storemod._jload(adir(aid) / "audit.json", None)
    if not a:
        return None
    return a


def save(a: dict) -> None:
    d = adir(a["id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "audit.json.tmp"
    tmp.write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(d / "audit.json")


def create(csv_text: str, name: str = "keyed.csv", source: str = "upload") -> dict:
    """Store the keyed file of a new audit and propose a column mapping. Returns the audit record."""
    if len(csv_text.encode("utf-8", "ignore")) > MAX_CSV_BYTES:
        raise ValueError("The file is larger than 20 MB.")
    headers, rows = parse_csv(csv_text)
    aid = "a" + uuid.uuid4().hex[:12]
    d = adir(aid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "keyed.csv").write_text(csv_text, encoding="utf-8")
    m = automap(headers)
    a = {"id": aid, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": source,
         "name": storemod.neutralize(re.sub(r"[^\w.,\- ]", "_", name)[:80]),"headers": headers, "rows": len(rows), "id_col": m["id"],
         "mapping": m["fields"], "how": m["how"], "auto": m, "scans": "stored", "confirmed_mapping": False,
         "marks": {}, "jobs": {}, "zip": None}
    save(a)
    return a


def set_mapping(a: dict, id_col, fields: dict, scans: str = "stored") -> dict:
    n = len(a["headers"])

    def ok(i):
        return isinstance(i, int) and 0 <= i < n
    if not ok(id_col):
        raise ValueError("Choose the column that holds the form id.")
    codes = {storemod.code_of(f["key"]) for f in graded()}
    mp = {c: (fields.get(c) if ok(fields.get(c)) and fields.get(c) != id_col else None) for c in codes}
    if not any(v is not None for v in mp.values()):
        raise ValueError("Map at least one field to a column.")
    a.update(id_col=id_col, mapping=mp, scans="zip" if scans == "zip" else "stored", confirmed_mapping=True)
    save(a)
    return a


def keyed_rows(a: dict) -> list[list[str]]:
    _, rows = parse_csv((adir(a["id"]) / "keyed.csv").read_text(encoding="utf-8"))
    return rows


def sample(aid: Optional[str] = None) -> dict:
    """The sample audit: the official first capture of the 300 pre-registered forms as the keyed CSV, auto-mapped,
    against the stored Gemma reads. No model call."""
    a = create(SAMPLE_CSV.read_text(encoding="utf-8"), name="PREP 2024, 300 pre-registered forms", source="sample")
    return set_mapping(a, a["id_col"], a["mapping"], "stored")


# ------------------------------------------------------------------------------------------- scans (ZIP)
def add_scans(a: dict, data: bytes, layout: str = "escaner") -> dict:
    """A ZIP of page images, read in memory. Each image whose file name is a form id of the keyed file is located
    and masked by the core in memory; only the masked page is written. Nothing else from the ZIP touches the disk."""
    ids = {r[a["id_col"]].strip().strip("'") for r in keyed_rows(a) if len(r) > a["id_col"]}
    out = {"masked": [], "not_located": [], "not_a_photo": [], "unmatched": [], "skipped": 0}
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("That file is not a ZIP archive.")
    with zf:
        members = [i for i in zf.infolist() if not i.is_dir() and i.filename.lower().endswith(IMG_EXT)]
        if len(members) > MAX_ZIP_FILES:
            raise ValueError(f"More than {MAX_ZIP_FILES} images in one ZIP; split it.")
        for info in members:
            fid = Path(info.filename.replace("\\", "/")).stem.strip()
            if not _FID.match(fid) or fid not in ids:
                out["unmatched"].append(fid[:40])
                continue
            if info.file_size > uploadmod.MAX_BYTES:
                out["not_a_photo"].append(fid)
                continue
            raw = zf.read(info)
            page, res = uploadmod.locate_and_mask(raw, layout)
            del raw
            if page is None:
                out[res["code"] if res.get("code") in ("not_located", "not_a_photo") else "not_a_photo"].append(fid)
                continue
            uploadmod.save_masked(page, adir(a["id"]) / "pages" / f"{fid}.jpg")
            out["masked"].append(fid)
    a["zip"] = {k: (v if k != "skipped" else v) for k, v in out.items()}
    a["scans"] = "zip"
    save(a)
    return out


# ------------------------------------------------------------------------------------------- compare
def _verdicts() -> tuple[dict, dict]:
    try:
        V = json.loads(VERDICTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        V = {}
    prep = {}
    try:
        for ln in ADJ_LEDGER.read_text(encoding="utf-8").splitlines():
            r = json.loads(ln)
            prep[f"{r['clave']}__{r['field']}"] = r.get("prep")
    except (OSError, ValueError):
        pass
    return V, prep


SECOND_NAME = "Qwen3.8-27B"


def _strict(d: dict, kv, m, fid: str, key: str) -> None:
    """Strict mode: a field is a strong dispute only if two readers (Gemma and Qwen) both read the same value and it
    differs from the keyed one. A strong field without that agreement is shown as medium, with the reason."""
    ok, q = second_value(fid, key)
    d["second"] = {"available": ok, "value": q, "agrees": ok and q == m and m is not None and m != kv}
    if not ok:
        d["second"]["text"] = "second reader not available"
    elif d["second"]["agrees"]:
        d["second"]["text"] = f"both readers read {m} (Gemma and Qwen)"
    else:
        d["second"]["text"] = f"second reader (Qwen) read {'blank' if q is None else q}"
    if d["tier"] == "strong" and not d["second"]["agrees"]:
        d["tier"] = "medium"
        d["demoted"] = True


def run(a: dict, job_state=None, strict: bool = False) -> dict:
    """Compare every mapped field of every keyed form with its read. Returns the summary and the order disputes.
    strict=True: strong only when Gemma and Qwen (stored reads) agree on a value that differs from the keyed one."""
    by_code = {storemod.code_of(f["key"]): f for f in graded()}
    mapped = [(c, i) for c, i in a["mapping"].items() if i is not None and c in by_code]
    mapped.sort(key=lambda x: list(by_code).index(x[0]))
    V, vprep = _verdicts()
    disputes, unread, forms, seen = [], [], 0, set()
    checked = 0
    rows = keyed_rows(a)
    invalid = 0
    for row in rows:
        fid = (row[a["id_col"]] if len(row) > a["id_col"] else "").strip().strip("'")
        if not _FID.match(fid) or fid in seen:
            invalid += 1
            continue
        seen.add(fid)
        view, page = find_read(a, fid)
        if view is None or not view.ok:
            job = (a.get("jobs") or {}).get(fid)
            js = (job_state(job) if job_state else None) if job else None
            can = page is not None and (view is None or view.page is not None)
            unread.append({"form": fid, "why": view.why if view else ("no read yet" if page else "no masked page to read"),
                            "queueable": can, "job": job, "job_state": js,
                            "can_queue": can and js not in ("queued", "running", "done")})
            continue
        forms += 1
        own = page_of(a["id"], fid)
        for code, col in mapped:
            f = by_code[code]
            k = f["key"]
            raw = row[col] if col < len(row) else ""
            kv, kind = keyed_value(raw)
            checked += 1
            m = view.values.get(k)
            if m == kv:
                continue
            ev = evidence(k, kv, kind, view)
            vk = f"{fid}__{k}"
            adj = V.get(vk) if vk in V and vprep.get(vk) == kv else None
            key = f"{fid}__{code}"
            disputes.append({
                "key": key, "form": fid, "code": code, "name": storemod.name_of(k), "keyed": show_keyed(raw),
                "keyed_n": kv, "keyed_kind": kind, "model": m, "words": view.words.get(k), "score": ev["score"], "tier": ev["tier"],
                "signals": ev["signals"], "accepted": view.accepted, "source": view.source,
                "img": (f"/audit/{a['id']}/crop/{fid}/{code}.jpg" if own is not None
                        else (f"/crop/{fid}/{code}.jpg?pad=0.02&label=0" if storemod.get_store().masked_image(fid) else None)),
                "mark": (a.get("marks") or {}).get(key),
                "adjudicated": ({"verdict": adj["verdict"], "label": VERDICT_LABEL.get(adj["verdict"], adj["verdict"]),
                                 "paper": adj.get("paper")} if adj else None)})
            if strict:
                _strict(disputes[-1], kv, m, fid, k)
    order = list(by_code)
    tier_order = {t: i for i, (t, _) in enumerate(TIERS)}
    disputes.sort(key=lambda d: ((tier_order[d["tier"]] if strict else 0), -d["score"], d["form"], order.index(d["code"])))
    for i, d in enumerate(disputes, 1):
        d["pos"] = i
    tiers = {t: sum(d["tier"] == t for d in disputes) for t, _ in TIERS}
    marks = {m: sum(d["mark"] == m for d in disputes) for m in MARKS}
    adj = [d for d in disputes if d["adjudicated"]]
    check = None
    if adj:
        check = [{"tier": t, "label": lab, "n": sum(d["tier"] == t for d in adj),
                  "errors": sum(d["tier"] == t and d["adjudicated"]["verdict"] == "model_right" for d in adj)}
                 for t, lab in TIERS]
    return {"forms_keyed": len(seen), "invalid_rows": invalid, "forms_read": forms, "fields_mapped": len(mapped),
            "checked": checked, "disputed": len(disputes), "disputed_forms": len({d["form"] for d in disputes}),
            "tiers": tiers, "marks": marks, "unread": unread, "disputes": disputes,
            "queueable": sum(p["can_queue"] for p in unread), "order_check": check,
            "adjudicated": len(adj), "strict": strict,
            "second": ({"name": SECOND_NAME, "available": sum(d["second"]["available"] for d in disputes),
                        "missing": sum(not d["second"]["available"] for d in disputes),
                        "agree": sum(d["second"]["agrees"] for d in disputes),
                        "demoted": sum(bool(d.get("demoted")) for d in disputes)} if strict else None)}


def mark(a: dict, key: str, value: Optional[str]) -> dict:
    if value not in (None, "", *MARKS):
        raise ValueError("mark must be confirmed, not_error or empty")
    with _lock:
        a = load(a["id"]) or a
        marks = a.setdefault("marks", {})
        if value:
            marks[key] = value
        else:
            marks.pop(key, None)
        save(a)
    return a


# ------------------------------------------------------------------------------------------- report fingerprint
_HASHES: dict = {}


def file_sha256(path: Path) -> Optional[str]:
    """SHA-256 of a file (cached on mtime and size); None when it does not exist."""
    try:
        st = path.stat()
    except OSError:
        return None
    k = (str(path), st.st_mtime_ns, st.st_size)
    if k not in _HASHES:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _HASHES[k] = h.hexdigest()
    return _HASHES[k]


def report_inputs(a: dict, strict: bool) -> list[dict]:
    """The input files a report is computed from, each with its SHA-256."""
    out = [("keyed file", adir(a["id"]) / "keyed.csv"), ("stored Gemma reads", STORED_RUN)]
    if strict:
        out.append(("stored Qwen reads (second reader)", SECOND_RUN))
    out.append(("photo adjudication", VERDICTS))
    res = [{"name": n, "file": p.name, "sha256": file_sha256(p)} for n, p in out]
    pages = adir(a["id"]) / "pages"
    if pages.is_dir():
        ph = hashlib.sha256()
        for p in sorted(pages.glob("*.jpg")):
            ph.update(f"{p.name}:{file_sha256(p)}\n".encode())
        res.append({"name": "masked pages of this audit", "file": "pages/*.jpg", "sha256": ph.hexdigest()})
    return [r for r in res if r["sha256"]]


def fingerprint(a: dict, R: dict, only: Optional[str] = None) -> dict:
    """Report fingerprint: SHA-256 over the report's content (summary and every listed field, in order, with its
    values, evidence tier, second reader and auditor mark) plus the SHA-256 of each input file. The same audit, mode
    and inputs always give the same fingerprint; the HTML report and its CSV print the same one."""
    content = {"audit": a["id"], "strict": bool(R.get("strict")), "only": only or "",
               "summary": {k: R.get(k) for k in ("forms_keyed", "forms_read", "fields_mapped", "checked", "disputed")},
               "tiers": R.get("tiers"),
               "fields": [[d["pos"], d["form"], d["code"], d["keyed"], d["model"], d["words"], d["tier"], d["score"],
                           (d.get("second") or {}).get("text"), d.get("mark")] for d in R["disputes"]]}
    csha = hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()
    inputs = report_inputs(a, bool(R.get("strict")))
    top = hashlib.sha256(json.dumps({"content": csha, "inputs": [[i["file"], i["sha256"]] for i in inputs]},
                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"sha256": top, "content_sha256": csha, "inputs": inputs, "merkle_root": merkle_tree(a, R)["root"],
            "merkle_n": len(R["disputes"])}


# ------------------------------------------------------------------------------------------- Merkle receipts
_CROP_SHA: dict = {}


def crop_of(a: dict, d: dict) -> Optional[bytes]:
    """The crop image bytes the report shows for a disputed field (the audit's own masked page, else this site's
    masked page; pad 0.02, no row label): the same bytes /audit/<id>/crop/... and /crop/... serve. None: no crop."""
    from app import crops
    if not d.get("img"):
        return None
    p = page_of(a["id"], d["form"]) or storemod.get_store().masked_image(d["form"])
    key = storemod.key_of(d["code"])
    if p is None or key is None:
        return None
    return crops.crop_bytes(str(p), p.stat().st_mtime, key, 0.02, False)


def crop_sha256(a: dict, d: dict) -> Optional[str]:
    if not d.get("img"):
        return None
    p = page_of(a["id"], d["form"]) or storemod.get_store().masked_image(d["form"])
    if p is None:
        return None
    st = p.stat()
    k = (str(p), st.st_mtime_ns, st.st_size, d["code"])
    if k not in _CROP_SHA:
        b = crop_of(a, d)
        _CROP_SHA[k] = hashlib.sha256(b).hexdigest() if b is not None else None
    return _CROP_SHA[k]


def leaf_of(a: dict, d: dict) -> dict:
    from twohands import merkle
    return merkle.leaf_record(d["form"], d["code"], d["keyed"], d["model"], d["words"], d["tier"], crop_sha256(a, d))


def merkle_tree(a: dict, R: dict) -> dict:
    """The report's Merkle root over its listed disputes, in report order (twohands/merkle.py)."""
    from twohands import merkle
    records = [leaf_of(a, d) for d in R["disputes"]]
    leaves = [merkle.leaf_hash(r) for r in records]
    return {"root": merkle.root(leaves), "n": len(leaves), "leaves": leaves, "records": records,
            "keys": [d["key"] for d in R["disputes"]]}


def receipt(a: dict, R: dict, key: str, only: Optional[str] = None) -> Optional[dict]:
    """One disputed field's receipt: its leaf record and hash, the proof path and the report's root."""
    from twohands import merkle
    T = merkle_tree(a, R)
    if key not in T["keys"]:
        return None
    i = T["keys"].index(key)
    d = R["disputes"][i]
    return {"receipt": "Two Hands audit receipt v1", "audit": a["id"],
            "mode": "strict" if R.get("strict") else "standard", "only": only or "all",
            "key": key, "position": d["pos"], "index": i, "n_leaves": T["n"],
            "leaf": T["records"][i], "leaf_hash": T["leaves"][i], "proof": merkle.proof(T["leaves"], i),
            "root": T["root"], "crop": d["img"],
            "check": "python -m twohands.verify_receipt receipt.json --crop crop.jpg"}


def report_csv(a: dict, R: dict, fp: Optional[dict] = None) -> str:
    """The report as CSV: one row per disputed field, then the report fingerprint and the input hashes (rows whose
    first cell starts with '#')."""
    buf = io.StringIO()
    w = csv.writer(buf)
    strict = bool(R.get("strict"))
    w.writerow(["position", "form", "field", "keyed value", "model digits", "model words", "evidence", "score",
                "evidence signals", "auditor mark", "crop"] + (["second reader (Qwen)"] if strict else []))
    for d in R["disputes"]:
        w.writerow([d["pos"], d["form"], d["name"], d["keyed"], "" if d["model"] is None else d["model"],
                    "" if d["words"] is None else d["words"], d["tier"], d["score"],
                    "; ".join(s["text"] for s in d["signals"]), MARKS.get(d["mark"], ""), d["img"] or ""]
                   + ([d["second"]["text"]] if strict else []))
    fp = fp or fingerprint(a, R)
    w.writerow([])
    w.writerow(["# report fingerprint (SHA-256)", fp["sha256"]])
    w.writerow(["# mode", "strict: strong only when Gemma and Qwen agree" if strict else "standard"])
    w.writerow(["# report content (SHA-256)", fp["content_sha256"]])
    if fp.get("merkle_root"):
        w.writerow(["# Merkle root of the disputes (SHA-256)", fp["merkle_root"]])
    for i in fp["inputs"]:
        w.writerow([f"# input: {i['name']} ({i['file']})", i["sha256"]])
    return buf.getvalue()


def queue_reads(a: dict, mgr, R: dict) -> dict:
    """Queue live reads (existing live-read path, its queue and budget guard) for keyed forms without a read."""
    from app.live import Refused
    queued, refused = [], None
    for p in R["unread"]:
        if not p["can_queue"]:
            continue
        _, page = find_read(a, p["form"])
        try:
            job = mgr.start(p["form"], page, kind="upload", out_dir=adir(a["id"]) / "reads", fallback=None)
        except Refused as e:
            refused = {"code": e.code, "message": e.message}
            break
        a.setdefault("jobs", {})[p["form"]] = job.id
        queued.append(p["form"])
    save(a)
    return {"queued": queued, "refused": refused}


# ------------------------------------------------------------------------------------------- OpenTimestamps
# Each report's Merkle root is anchored in time with OpenTimestamps (twohands/timestamp.py): the file "<root>\n" is
# stamped on the public calendars (only a hash leaves the server) and its .ots proof is kept next to it. The sample
# audit's root has a committed proof (results/sample_audit_root.txt.ots). TWOHANDS_OTS=0 turns stamping off.
TIMESTAMPS = storemod.STATE / "timestamps"
SAMPLE_ROOT_FILE = storemod.RESULTS / "sample_audit_root.txt"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_STAMPING: dict = {}          # root -> time of the last attempt (in flight or failed), so a render never re-sends at once
STAMP_RETRY_S = 600


def _sample_root() -> Optional[str]:
    try:
        return SAMPLE_ROOT_FILE.read_text(encoding="utf-8").split()[0]
    except (OSError, IndexError):
        return None


def stamped_file(root: str) -> Optional[Path]:
    """The file whose SHA-256 the proof of ``root`` commits to: results/sample_audit_root.txt for the sample's root,
    else <state>/timestamps/<root>.txt. None for an invalid root."""
    if not _HEX64.match(root or ""):
        return None
    return SAMPLE_ROOT_FILE if root == _sample_root() else TIMESTAMPS / f"{root}.txt"


def timestamp_of(root: str) -> Optional[dict]:
    """The report's "anchored in time" line: date submitted, calendars, Bitcoin heights once upgraded, proof link."""
    from twohands import timestamp as ots
    p = stamped_file(root)
    st = ots.status(p) if p else None
    if not st or not st["matches"]:
        return None
    return st | {"proof": f"/timestamp/{root}.ots", "file": f"/timestamp/{root}.txt", "name": p.name,
                 "n_calendars": len(st["pending"])}


def stamping_enabled() -> bool:
    import os
    return os.environ.get("TWOHANDS_OTS", "1") != "0"


def ensure_stamped(root: str, post=None, background: bool = True) -> str:
    """Stamp a report root once (in a background thread unless ``background`` is False). Returns "stamped",
    "started", "pending" (an attempt is in flight or failed less than STAMP_RETRY_S ago), "off" or "invalid"."""
    import time
    from twohands import timestamp as ots
    p = stamped_file(root)
    if p is None:
        return "invalid"
    if timestamp_of(root):
        return "stamped"
    if not stamping_enabled():
        return "off"
    with _lock:
        if time.time() - _STAMPING.get(root, -1e18) < STAMP_RETRY_S:
            return "pending"
        _STAMPING[root] = time.time()

    def go():
        try:
            if p != SAMPLE_ROOT_FILE:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(root + "\n", encoding="utf-8", newline="\n")
            ots.stamp_file(p, **({"post": post} if post else {}))
            _STAMPING.pop(root, None)
        except Exception as e:  # noqa: BLE001 (no calendar reachable: the report shows "not yet anchored")
            print(f"[timestamp] {root[:16]}: {e}")
    if background:
        threading.Thread(target=go, daemon=True, name=f"ots-{root[:8]}").start()
        return "started"
    go()
    return "stamped" if timestamp_of(root) else "pending"
