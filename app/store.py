"""Data layer: every number the app shows is computed here from a results file.

Sources (all read-only):
  app/data/spike_runs.json   spike reads (snapshot of spikes/tally-witness/results*/, by app/build.py)
  app/data/official.json     official PREP capture, certified Computos values, adjudicated fields
  results/*.jsonl            core runs (verify runs, the pre-registered 300-form run, ...): picked up automatically
  ledger/ledger.json         rainfall ledgers (snapshot of spikes/ledger-rescue, by ledger/build.py)
  app/state/live/*.json      live reads made from the web app
Images: only masked pages under data/masked/** (made by twohands.mask). Nothing else is ever served.
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from twohands import REPO
from twohands import gate as gatemod
from twohands import schema as schemamod

APP = REPO / "app"
DATA = APP / "data"
STATE = APP / "state"
RESULTS = REPO / "results"
MASKED = (REPO / "data" / "masked").resolve()
LEDGER = REPO / "ledger" / "ledger.json"

HEADLINE_MIN_FORMS = 100   # a core run takes over the headline once it has this many graded forms
READ_KEYS = ("values", "fields", "parsed", "not_located", "no_call")

# Public names. Vote rows are shown as neutral "Option NN" (never by party); the other lines of the form by a plain
# English name. Codes are what URLs, HTML attributes and JSON use; schema keys stay internal.
PLAIN_NAMES = {
    "SOBRANTES": "Unused ballots",
    "VOTARON": "Voters on the list",
    "REPRESENTANTES": "Representatives who voted",
    "PERSONAS_Y_REP": "Voters + representatives",
    "SACADOS": "Ballots taken from the boxes",
    "NO_REGISTRADAS": "Unregistered candidates",
    "NULOS": "Null votes",
    "TOTAL": "TOTAL",
}
SECTION = {"SOBRANTES": "section 2", "VOTARON": "section 3", "REPRESENTANTES": "section 4",
           "PERSONAS_Y_REP": "section 5", "SACADOS": "section 7", "TOTAL": "section 6"}


def _naming():
    s = schemamod.load()
    if "_app_names" not in s:
        code, name = {}, {}
        i = 0
        for f in s["fields"]:
            k = f["key"]
            if k in PLAIN_NAMES:
                code[k], name[k] = k, PLAIN_NAMES[k]
            else:
                i += 1
                code[k], name[k] = f"OPT{i:02d}", f"Option {i:02d}"
        s["_app_names"] = (code, name, {v: k for k, v in code.items()})
    return s["_app_names"]


def code_of(k: str) -> str:
    return _naming()[0].get(k, k)


def name_of(k: str) -> str:
    return _naming()[1].get(k, k)


def key_of(code: str) -> Optional[str]:
    return _naming()[2].get(code)


def neutralize(text: Any) -> Any:
    """Replace schema row ids and printed party names in a text by neutral names."""
    if not isinstance(text, str):
        return text
    s = schemamod.load()
    for k in sorted(s["keys"], key=len, reverse=True):
        if k not in PLAIN_NAMES:
            text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(k)}(?![A-Za-z0-9])", name_of(k), text)
    words = sorted({a for names in s.get("party_aliases", {}).values() for a in names} | set(s.get("party_aliases", {})),
                   key=len, reverse=True)
    for a in words:
        text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(a)}(?![A-Za-z0-9])", "[logo]", text, flags=re.I)
    return text


def public(obj: Any) -> Any:
    """JSON-safe, party-neutral copy: schema keys -> codes, every string neutralized."""
    if isinstance(obj, dict):
        return {(code_of(k) if isinstance(k, str) else k): public(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [public(x) if not (isinstance(x, str) and x in schemamod.load()["keys"]) else code_of(x) for x in obj]
    if isinstance(obj, str):
        return code_of(obj) if obj in schemamod.load()["keys"] else neutralize(obj)
    return obj


def schema() -> dict:
    return schemamod.load()


def iv(x) -> Optional[int]:
    return gatemod.iv(x)


# ----------------------------------------------------------------------------------------------- reads
@dataclass
class Read:
    clave: str
    run_id: str
    values: dict
    words: dict
    labels: dict                 # {} when the read predates the row-label check (spike)
    fixes: list
    has_labels: bool
    stored_accepted: Optional[bool] = None
    stored_reasons: list = field(default_factory=list)
    secs: Optional[float] = None
    cost: Optional[float] = None
    error: Optional[str] = None
    not_located: Optional[str] = None
    raw: dict = field(default_factory=dict)


def read_from_spike(clave: str, run_id: str, row: dict) -> Read:
    p = row.get("parsed") or {}
    s = schema()
    vals, words, fixes = {}, {}, []
    for k in s["keys"]:
        d = p.get(k) if isinstance(p, dict) else None
        if isinstance(d, dict):
            vals[k], words[k] = iv(d.get("n")), iv(d.get("w"))
            if d.get("fix"):
                fixes.append(k)
        else:
            vals[k], words[k] = iv(d), None
    return Read(clave, run_id, vals, words, {}, fixes, False, secs=row.get("secs"), cost=row.get("cost"),
                error=None if p else "no parseable read")


def read_from_core(clave: str, run_id: str, row: dict) -> Read:
    """Adapter for the core's jsonl rows (scripts/verify_spike.py format, and any run that writes
    values/words/labels/accepted/reasons, or only the raw reader row with 'parsed')."""
    s = schema()
    if row.get("not_located") or row.get("no_call"):
        why = row.get("not_located") or "; ".join(row.get("route_reasons") or []) or "not read"
        return Read(clave, run_id, {k: None for k in s["keys"]}, {k: None for k in s["keys"]}, {}, [], True,
                    stored_accepted=False, stored_reasons=[f"form not located: {why}" if row.get("not_located") else why],
                    not_located=str(why), raw={"stratum": row.get("stratum"), "image": row.get("image")})
    if isinstance(row.get("fields"), dict) and row["fields"]:
        # run.record format (results/calls_<model>.jsonl): fields{KEY:{label,n,w,fix}}
        fd = row["fields"]
        vals = {k: iv((fd.get(k) or {}).get("n")) for k in s["keys"]}
        words = {k: iv((fd.get(k) or {}).get("w")) for k in s["keys"]}
        labels = {k: (fd.get(k) or {}).get("label") for k in s["keys"]}
        fixes = [k for k in s["keys"] if (fd.get(k) or {}).get("fix")]
        return Read(clave, run_id, vals, words, labels, fixes, True, stored_accepted=row.get("accepted"),
                    stored_reasons=list(row.get("route_reasons") or []), secs=row.get("latency_s"),
                    cost=row.get("cost_usd"), error=row.get("error"),
                    raw={k: row.get(k) for k in ("image", "layout", "stratum", "model", "prompt_sha256", "ts")})
    if "values" in row and isinstance(row["values"], dict):
        vals = {k: iv(row["values"].get(k)) for k in s["keys"]}
        words = {k: iv((row.get("words") or {}).get(k)) for k in s["keys"]}
        labels = dict(row.get("labels") or {})
        fixes = list(row.get("fixes") or [])
        acc, reasons = row.get("accepted"), list(row.get("reasons") or [])
    else:
        g = gatemod.gate(row.get("parsed"), s)
        vals, words, labels, fixes = g.values, g.words, g.labels, g.fixes
        acc, reasons = g.accepted, g.reasons
    u = row.get("usage") or {}
    return Read(clave, run_id, vals, words, labels, fixes, True, stored_accepted=acc, stored_reasons=reasons,
                secs=row.get("secs"), cost=u.get("cost") if isinstance(u, dict) else None, error=row.get("error"),
                raw={k: row.get(k) for k in ("wrong_vs_adjudicated", "image", "dig", "model", "info")})


# ----------------------------------------------------------------------------------------------- verdict
def evaluate(r: Read, overrides: Optional[dict] = None, labels_confirmed: bool = False) -> dict:
    """Per-field status, identities, verdict. Same checks as twohands.gate: completeness, words = digits,
    row labels (only for reads that carry labels), the schema's identities. ``overrides`` = values typed by a
    reviewer (they settle both digits and words for that field)."""
    s = schema()
    aliases = s.get("party_aliases", {})
    overrides = {k: iv(v) for k, v in (overrides or {}).items() if iv(v) is not None}
    vals = dict(r.values)
    words = dict(r.words)
    for k, v in overrides.items():
        vals[k] = v
        words[k] = v
    fields, reasons, failing = [], [], []
    if r.not_located:
        reasons.append("form not located on the image (sent to a person, nothing read)")
    for i, f in enumerate(s["fields"]):
        k = f["key"]
        n, w = vals.get(k), words.get(k)
        st = "ok"
        msg = ""
        if r.has_labels and not labels_confirmed and k not in overrides and not r.not_located:
            if not gatemod.label_ok(r.labels.get(k), f["label"], aliases):
                st, msg = "label", f"row {i + 1}: the printed label read is not the one expected here"
        if n is None:
            # wording only (the gate is unchanged): a null read is either a blank box or faint writing; the model
            # cannot tell which, so neither do we (eye check of the 300-run crops: both occur)
            st, msg = "empty", (f"digit boxes not read (blank or faint); words say {w}" if w is not None
                                else "not read: blank or too faint on the page")
        elif w is not None and n != w:
            st, msg = "words", f"digits {n}, words {w}"
        if st != "ok" and not r.not_located:
            failing.append(k)
            reasons.append(f"{name_of(k)}: {msg}")
        fields.append({"key": k, "code": code_of(k), "name": name_of(k), "section": SECTION.get(k), "n": n, "w": w, "label": r.labels.get(k),
                       "status": st, "msg": msg, "fix": k in r.fixes, "vote": bool(f.get("vote")),
                       "override": k in overrides})
    idents = []
    for idt in s.get("identities", []):
        lhs = s["vote_keys"] if idt["sum"] == "@vote" else idt["sum"]
        a = [vals.get(k) for k in lhs]
        b = [vals.get(k) for k in idt["equals"]]
        if None in a or None in b:
            idents.append({"name": idt["name"], "ok": None, "lhs": None, "rhs": None, "keys": lhs + idt["equals"]})
            continue
        ok = sum(a) == sum(b)
        idents.append({"name": idt["name"], "ok": ok, "lhs": sum(a), "rhs": sum(b), "keys": list(lhs) + list(idt["equals"])})
        if not ok:
            reasons.append(f"{idt['name']}: {sum(a)} != {sum(b)}")
    accepted = not reasons
    # the core's stored verdict is the authority for its own runs (it also routes e.g. truncated replies)
    if r.stored_accepted is not None and not overrides and not labels_confirmed and not r.not_located:
        if r.stored_accepted and not accepted and all(f["status"] in ("ok", "label") for f in fields)                 and all(i["ok"] is not False for i in idents):
            for f in fields:
                f["status"], f["msg"] = "ok", ""
            reasons, failing, accepted = [], [], True
        elif not r.stored_accepted and accepted:
            reasons = [neutralize(x) for x in r.stored_reasons] or ["routed by the core gate"]
            accepted = False
    # the verdict line: name the failing field(s) and the evidence the paper gives
    rows_sum = next((x["lhs"] for x in idents if x["name"].startswith("rows sum")), None)
    if accepted:
        line = "Accepted: 0 fields to key"
    elif r.not_located:
        line = "Routed: form not located on the image"
    else:
        parts = []
        for f in fields:
            if f["status"] == "words":
                p = f"{f['name']} digits {f['n']}, words {f['w']}"
                if f["key"] == "TOTAL" and rows_sum is not None:
                    p += f", rows sum {rows_sum}"
                parts.append(p)
            elif f["status"] == "empty":
                parts.append(f"{f['name']} not read (blank or faint)")
        nlab = sum(f["status"] == "label" for f in fields)
        if nlab:
            parts.append(f"{nlab} row label{'s' if nlab > 1 else ''} not where expected")
        for x in idents:
            if x["ok"] is False:
                parts.append(f"{x['name']} ({x['lhs']} vs {x['rhs']})")
        if not parts:
            parts = [str(x) for x in reasons[:2]]
        line = "Routed: " + "; ".join(parts[:4]) + (" …" if len(parts) > 4 else "")
    to_key = len(set(failing)) if not accepted else 0
    if not accepted and not failing:  # identity-only failure: the person checks the fields in that identity
        to_key = len({k for x in idents if x["ok"] is False for k in x["keys"]})
    return {"accepted": accepted, "fields": fields, "identities": idents, "reasons": reasons, "line": line,
            "failing": failing, "to_key": to_key, "rows_sum": rows_sum}


def grade(r: Read, off: Optional[dict]) -> dict:
    """Compare a read with the official capture (PREP) and with the adjudicated truth (PREP + eye-checked fixes)."""
    if not off or not off.get("prep"):
        return {"graded": False}
    adj = off.get("adjudicated") or {}
    keys = [k for k, v in off["prep"].items() if v is not None]
    wrong_raw = {k: (r.values.get(k), off["prep"][k]) for k in keys if r.values.get(k) != off["prep"][k]}
    wrong_adj = {k: (r.values.get(k), adj.get(k, off["prep"][k])) for k in keys if r.values.get(k) != adj.get(k, off["prep"][k])}
    return {"graded": True, "n": len(keys), "wrong_raw": wrong_raw, "wrong_adj": wrong_adj}


# ----------------------------------------------------------------------------------------------- store
class Store:
    """Loads everything; reloads when a source file changes (so a new results/*.jsonl flows in)."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sig = None
        self._img_index: dict[str, Path] = {}
        self._img_at = 0.0
        self.reload(force=True)

    # ---- sources
    def _sources(self) -> list[Path]:
        ps = [DATA / "spike_runs.json", DATA / "official.json", LEDGER]
        ps += sorted(RESULTS.glob("*.jsonl")) if RESULTS.is_dir() else []
        ps += sorted((STATE / "live").glob("*.json")) if (STATE / "live").is_dir() else []
        return ps

    def _signature(self):
        out = []
        for p in self._sources():
            try:
                st = p.stat()
                out.append((str(p), st.st_mtime_ns, st.st_size))
            except OSError:
                pass
        return tuple(out)

    def reload(self, force: bool = False) -> None:
        with self._lock:
            sig = self._signature()
            if not force and sig == self._sig:
                return
            self._sig = sig
            self.official = _jload(DATA / "official.json", {})
            self.runs: dict[str, dict] = {}
            for run in _jload(DATA / "spike_runs.json", []):
                reads = {row["clave"]: read_from_spike(row["clave"], run["id"], row) for row in run["rows"]}
                self.runs[run["id"]] = {**{k: v for k, v in run.items() if k != "rows"}, "reads": reads}
            for p in sorted(RESULTS.glob("*.jsonl")) if RESULTS.is_dir() else []:
                reads = {}
                model = None
                for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    k = row.get("clave") or row.get("form_id") or row.get("id")
                    if not k or not any(x in row for x in READ_KEYS):
                        continue  # not a read (e.g. results/prepare.jsonl)
                    model = model or row.get("model")
                    reads[str(k)] = read_from_core(str(k), p.stem, row)
                if not reads:
                    continue
                low = p.stem.lower()
                mname = model or ("Qwen3.8-27B" if "qwen" in low else "Gemma-4-31B-IT")
                if low.startswith("calls_") and (RESULTS / "manifest.json").is_file():
                    kind = "pre-registered random run"
                elif low.startswith("verify_"):
                    kind = "re-read of masked forms with the frozen prompt" + (", attempt " + low.rsplit("try", 1)[-1]
                                                                               if "try" in low else "")
                else:
                    kind = "core reader"
                self.runs[p.stem] = {"id": p.stem, "model": mname, "label": f"{mname}, {kind}",
                                     "method": "twohands/reader.py (frozen prompt) + twohands/gate.py, masked page + tiles",
                                     "kind": "core", "source": f"results/{p.name}", "reads": reads}
            self.live = {}
            for p in sorted((STATE / "live").glob("*.json")) if (STATE / "live").is_dir() else []:
                row = _jload(p, None)
                if row and row.get("clave"):
                    self.live[row["clave"]] = row
            if self.live:
                self.runs["live"] = {"id": "live", "model": "Gemma-4-31B-IT", "kind": "live",
                                     "label": "Live reads made from this site (latest per form)",
                                     "method": "twohands/reader.py + twohands/gate.py, run on request",
                                     "source": "app/state/live/*.json",
                                     "reads": {k: read_from_core(k, "live", {"clave": k, "parsed": v.get("parsed"),
                                                                             "usage": v.get("usage"), "secs": v.get("secs"),
                                                                             "model": v.get("model")})
                                               for k, v in self.live.items()}}
            self.ledger = _jload(LEDGER, {"meta": {}, "sheets": []})
            self._metrics_cache: dict = {}

    def maybe_reload(self) -> None:
        self.reload(force=False)

    # ---- images (masked only)
    def masked_image(self, clave: str) -> Optional[Path]:
        now = time.time()
        if now - self._img_at > 20 or clave not in self._img_index:
            if now - self._img_at > 2:
                idx = {}
                if MASKED.is_dir():
                    for p in MASKED.rglob("*.jpg"):
                        idx.setdefault(p.stem, p)
                self._img_index, self._img_at = idx, now
        p = self._img_index.get(clave)
        if p is None:
            return None
        rp = p.resolve()
        if MASKED not in rp.parents or not rp.is_file():
            return None
        return rp

    # ---- forms
    def short_name(self, rid: str) -> str:
        run = self.runs.get(rid, {})
        m = (run.get("model") or "").split("-")[0]
        if rid == "spike-gemma-v2":
            return f"{m} · measured run"
        if rid == "spike-qwen":
            return f"{m} · second reader"
        if rid == "spike-gemma-v1":
            return f"{m} · earlier prompt"
        if rid == "live":
            return "Live read"
        if rid.startswith("calls_"):
            return f"{m} · pre-registered run"
        if rid.startswith("verify_"):
            n = rid.rsplit("try", 1)[-1] if "try" in rid else None
            return f"{m} · re-read after masking" + (f" (attempt {n})" if n and n.isdigit() else "")
        return f"{m} · {rid}"

    def run_order(self) -> list[str]:
        """Default-reader preference: the headline run, the frozen spike reader, other core runs (largest first),
        then the second reader and the older spike reader."""
        core = [r["id"] for r in sorted((r for r in self.runs.values() if r["kind"] == "core"), key=lambda r: -len(r["reads"]))]
        order = [self.headline_run(), "spike-gemma-v2"] + core + ["spike-qwen", "spike-gemma-v1"]
        return [k for k in dict.fromkeys(order) if k in self.runs]

    def default_read(self, clave: str) -> Optional[Read]:
        for rid in self.run_order():
            r = self.runs[rid]["reads"].get(clave)
            if r and r.error is None:
                return r
        for rid in self.run_order():
            r = self.runs[rid]["reads"].get(clave)
            if r:
                return r
        return None

    def ine_claves(self) -> list[str]:
        ks = set(self.official)
        for run in self.runs.values():
            ks |= set(run["reads"])
        return sorted(ks)

    def form_summary(self, clave: str) -> dict:
        r = self.default_read(clave)
        off = self.official.get(clave, {})
        ev = evaluate(r) if r else None
        return {"clave": clave, "accepted": ev["accepted"] if ev else None, "line": ev["line"] if ev else "not read yet",
                "run": r.run_id if r else None, "has_image": self.masked_image(clave) is not None,
                "dig": off.get("dig"), "stratum": off.get("stratum"), "entidad": off.get("entidad"),
                "to_key": ev["to_key"] if ev else None}

    # ---- metrics per run
    def run_metrics(self, rid: str) -> dict:
        if rid in self._metrics_cache:
            return self._metrics_cache[rid]
        run = self.runs[rid]
        m = dict(forms=0, accepted=0, not_located=0, errors=0, graded_forms=0, acc_fields=0, acc_wrong_raw=0,
                 acc_wrong_adj=0, all_fields=0, all_wrong_raw=0, all_wrong_adj=0, cost=0.0, cost_n=0, secs=0.0, secs_n=0,
                 acc_forms_graded=0, paper_rejects=0, stored_mismatch=0)
        for k, r in run["reads"].items():
            m["forms"] += 1
            ev = evaluate(r)
            acc = ev["accepted"] if r.stored_accepted is None else bool(r.stored_accepted)
            if r.stored_accepted is not None and r.stored_accepted != ev["accepted"]:
                m["stored_mismatch"] += 1
            m["accepted"] += acc
            m["not_located"] += bool(r.not_located)
            m["errors"] += bool(r.error)
            if r.cost:
                m["cost"] += r.cost
                m["cost_n"] += 1
            if r.secs:
                m["secs"] += r.secs
                m["secs_n"] += 1
            g = grade(r, self.official.get(k))
            if not g["graded"] or r.not_located:
                continue
            m["graded_forms"] += 1
            m["all_fields"] += g["n"]
            m["all_wrong_raw"] += len(g["wrong_raw"])
            m["all_wrong_adj"] += len(g["wrong_adj"])
            if acc:
                m["acc_forms_graded"] += 1
                m["acc_fields"] += g["n"]
                m["acc_wrong_raw"] += len(g["wrong_raw"])
                m["acc_wrong_adj"] += len(g["wrong_adj"])
            elif not g["wrong_adj"]:
                m["paper_rejects"] += 1
        m["cost_per_form"] = m["cost"] / m["cost_n"] if m["cost_n"] else None
        m["mean_secs"] = m["secs"] / m["secs_n"] if m["secs_n"] else None
        m["accept_rate"] = m["accepted"] / m["forms"] if m["forms"] else None
        m.update(id=rid, model=run["model"], label=run["label"], source=run["source"], kind=run["kind"], method=run["method"])
        self._metrics_cache[rid] = m
        return m

    def headline_run(self) -> str:
        """The largest graded core run with >= 100 forms (the pre-registered random run when it lands),
        else the frozen spike reader (Gemma v2)."""
        best = None
        for rid, run in self.runs.items():
            if run["kind"] != "core":
                continue
            m = self.run_metrics(rid)
            if m["graded_forms"] >= HEADLINE_MIN_FORMS and (best is None or m["graded_forms"] > self.run_metrics(best)["graded_forms"]):
                best = rid
        return best or "spike-gemma-v2"

    # ---- keying errors (audit)
    def keying_errors(self) -> list[dict]:
        """Confirmed: adjudicated fields (eye-checked: the official capture disagrees with the image).
        Candidates: on accepted forms in any core run, fields where the model disagrees with PREP and
        that are not yet adjudicated."""
        out = []
        acc_by = {}
        for rid in ("spike-gemma-v2", "spike-qwen"):
            for k, r in self.runs.get(rid, {}).get("reads", {}).items():
                if evaluate(r)["accepted"]:
                    acc_by.setdefault(k, []).append(self.runs[rid]["model"])
        for k, off in sorted(self.official.items()):
            for f, v in (off.get("adjudicated") or {}).items():
                models = {}
                for rid in ("spike-gemma-v2", "spike-qwen"):
                    r = self.runs.get(rid, {}).get("reads", {}).get(k)
                    if r:
                        models[self.runs[rid]["model"]] = r.values.get(f)
                cert = (off.get("cert") or {}).get(f)
                words = self._words(k, f)
                paper = f == "TOTAL" and words is not None and words == (off.get("prep") or {}).get(f) and words != v
                out.append({"clave": k, "field": f, "code": code_of(f), "name": name_of(f),
                            "kind": "paper" if paper else "keying", "image_value": v, "official": (off.get("prep") or {}).get(f),
                            "certified": cert, "cert_agrees": cert == v if cert is not None else None,
                            "cert_mode": off.get("cert_mode"), "models": models, "status": "confirmed",
                            "accepted_by": acc_by.get(k, []), "words": words,
                            "has_image": self.masked_image(k) is not None})
        seen = {(e["clave"], e["field"]) for e in out}
        for rid, run in self.runs.items():
            if run["kind"] != "core":
                continue
            for k, r in run["reads"].items():
                off = self.official.get(k)
                if not off or not evaluate(r)["accepted"]:
                    continue
                for f, (mv, pv) in grade(r, off).get("wrong_raw", {}).items():
                    if (k, f) in seen:
                        continue
                    seen.add((k, f))
                    cert = (off.get("cert") or {}).get(f)
                    out.append({"clave": k, "field": f, "code": code_of(f), "name": name_of(f), "kind": "candidate",
                                "image_value": None, "official": pv, "certified": cert,
                                "cert_agrees": (cert == mv) if cert is not None else None, "cert_mode": off.get("cert_mode"),
                                "models": {run["model"]: mv}, "status": "candidate", "run": rid,
                                "accepted_by": [run["model"]], "words": r.words.get(f),
                                "has_image": self.masked_image(k) is not None})
        return out

    def _words(self, clave: str, f: str):
        for rid in ("spike-gemma-v2", "spike-qwen"):
            r = self.runs.get(rid, {}).get("reads", {}).get(clave)
            if r and r.words.get(f) is not None:
                return r.words.get(f)
        return None

    # ---- ledger
    def ledger_sheet(self, sid: str) -> Optional[dict]:
        return next((s for s in self.ledger.get("sheets", []) if s["id"] == sid), None)

    def ledger_metrics(self) -> dict:
        sheets = self.ledger.get("sheets", [])
        cols = [c for s in sheets for c in s["cols"]]
        acc = [c for c in cols if c["accepted"]]
        cells = acc_cells = acc_ok = all_ok = 0
        for c in cols:
            pairs = list(zip(c["read"] + [c["read_total"]], c["truth"] + [c["truth_total"]]))
            for rv, tv in pairs:
                if tv is None:
                    continue
                ok = rv is not None and abs(rv - tv) < 0.005
                cells += 1
                all_ok += ok
                if c["accepted"]:
                    acc_cells += 1
                    acc_ok += ok
        pin, pout = (self.ledger.get("meta", {}).get("price_per_token") or {}).get("in"), \
            (self.ledger.get("meta", {}).get("price_per_token") or {}).get("out")
        tin = sum(s.get("prompt_tokens") or 0 for s in sheets)
        tout = sum(s.get("completion_tokens") or 0 for s in sheets)
        usd = tin * pin + tout * pout if pin else None
        return {"sheets": len(sheets), "cols": len(cols), "acc_cols": len(acc), "cells": cells, "all_ok": all_ok,
                "acc_cells": acc_cells, "acc_ok": acc_ok,
                "sheets_accepted": sum(all(c["accepted"] for c in s["cols"]) for s in sheets),
                "usd": usd, "usd_per_sheet": usd / len(sheets) if usd and sheets else None}


def _jload(p: Path, default: Any):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


_STORE: Optional[Store] = None


def get_store() -> Store:
    global _STORE
    if _STORE is None:
        _STORE = Store()
    else:
        _STORE.maybe_reload()
    return _STORE
