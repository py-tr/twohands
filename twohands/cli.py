"""`twohands`: the audit, the reader, the gate and receipt checks from the command line (and the MCP server's tools).

    twohands audit --keyed capture.csv --scans scans/ --schema mx_presidencia_2024 --out report/
    twohands audit --keyed app/data/audit_sample_prep300.csv --from-stored --out report/   # the sample, no model call
    twohands read form.jpg [--masked] [--layout movil|escaner] [--model gemma|qwen]
    twohands gate values.json [--schema mx_presidencia_2024] [--variant v1|v2|v2b]
    twohands verify-receipt receipt.json [--crop crop.jpg] [--root <hex>]
    twohands mcp [--http] [--host 127.0.0.1] [--port 8765]      # the MCP server (stdio by default)

Nothing here re-implements the pipeline. Pages are located and masked by the core (twohands.mask.prepare, through
app.upload.locate_and_mask for an audit's scans), read by twohands.reader (one request per masked page, the frozen
prompt) through the configured OpenAI-compatible endpoint (twohands.amd: AMD_BASE_URL / AMD_KEY, or --base-url),
gated by twohands.gate (the frozen gate; gate_v2 for the post-hoc variants), and compared with the keyed CSV by
app.capture_audit, the module behind the web app's /audit pages: the same disputes, order, tiers, CSV, fingerprint
and Merkle root. The HTML report is the web app's own /audit/<id>/report page, rendered in-process.

--from-stored uses the stored pre-registered Gemma reads (results/calls_gemma.jsonl) and never calls a model: on the
sample (the official first capture of the 300 pre-registered forms) it reproduces the 267 disputed fields and the
published Merkle root (results/sample_audit_root.txt).

Privacy: only masked pages are read or written (the right-hand column with names and signatures is blacked out by
the core before anything else happens). Vote rows are shown as "Option NN".
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import io
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from twohands import REPO
from twohands import schema as schemamod

DEFAULT_SCHEMA = schemamod.DEFAULT
IMG_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")
ReaderFn = Callable[[str, Any], dict]   # (model key, masked page path or file object) -> twohands.reader.read row


# ------------------------------------------------------------------------------------------------ naming
def _public(s: dict, obj):
    """Neutral names (Option NN, no party names) for the presidential form, as the web app shows them."""
    if s.get("form") != DEFAULT_SCHEMA:
        return obj
    from app import store as storemod
    return storemod.public(obj)


def _code(s: dict, key: str) -> str:
    if s.get("form") != DEFAULT_SCHEMA:
        return key
    from app import store as storemod
    return storemod.code_of(key)


def _key(s: dict, name: str) -> Optional[str]:
    """A field named by schema key, by code (OPT07) or by neutral name (Option 07) -> schema key."""
    if name in s["keys"]:
        return name
    if s.get("form") == DEFAULT_SCHEMA:
        from app import store as storemod
        k = storemod.key_of(name) or storemod.key_of(str(name).upper().replace("OPTION ", "OPT").replace(" ", ""))
        if k:
            return k
        for k in s["keys"]:
            if storemod.name_of(k).lower() == str(name).strip().lower():
                return k
    return None


# ------------------------------------------------------------------------------------------------ the reader
def default_reader(base_url: Optional[str] = None) -> ReaderFn:
    """twohands.reader.read through the core client (twohands.amd: shared rate limiter, retries, health log)."""
    if base_url:
        os.environ["AMD_BASE_URL"] = base_url

    def fn(model: str, page) -> dict:
        from twohands import amd, reader
        return reader.read(model, page, chat=lambda body: amd.chat(body, log=lambda *a, **k: None, kind="cli"))
    return fn


def load_page(image, s: dict, masked: bool = False, layout: str = "movil"):
    """An image (path, bytes or base64 string) -> (masked canonical page, info). Unless ``masked``, the page is
    located, straightened and masked by the core (twohands.mask.prepare); raises register.NotLocated."""
    from PIL import Image

    from twohands import mask as maskmod
    if isinstance(image, (bytes, bytearray)):
        src = io.BytesIO(image)
    elif isinstance(image, str) and not Path(image).exists() and len(image) > 200:
        src = io.BytesIO(base64.b64decode(image.split(",", 1)[1] if image.startswith("data:") else image))
    else:
        src = Path(image)
    with Image.open(src) as im:
        im.load()
        img = im.convert("RGB")
    if masked:
        return img, {"masked": "given"}
    page, info = maskmod.prepare(img, layout, s)
    return page, info


def _jpeg(page) -> io.BytesIO:
    from twohands import mask as maskmod
    buf = io.BytesIO()
    page.convert("RGB").save(buf, "JPEG", quality=maskmod.JPEG_QUALITY, optimize=True)
    buf.seek(0)
    return buf


def read_form(image, schema: str = DEFAULT_SCHEMA, model: str = "gemma", masked: bool = False,
              layout: str = "movil", reader_fn: Optional[ReaderFn] = None, save_masked: Optional[str] = None) -> dict:
    """One form: (locate and mask unless ``masked``) -> one read -> the frozen gate. Returns values, words, labels
    (by field, neutral names), the gate's verdict and identities, latency and token use. No key, no image bytes."""
    from twohands import register
    from twohands.gate import gate
    s = schemamod.load(schema)
    try:
        page, info = load_page(image, s, masked, layout)
    except register.NotLocated as e:
        return {"ok": False, "not_located": True, "error": f"form not located on the image: {str(e)[:160]}",
                "accepted": False, "reasons": ["form not located: it goes to a person, no model call"]}
    if save_masked:
        from twohands import mask as maskmod
        maskmod.save(page, save_masked)
    row = (reader_fn or default_reader())(model, _jpeg(page))
    g = gate(row.get("parsed"), s)
    fields = {_code(s, k): {"n": g.values.get(k), "w": g.words.get(k), "label": g.labels.get(k)} for k in s["keys"]}
    out = {"ok": row.get("parsed") is not None, "model": row.get("model"), "secs": row.get("secs"),
           "usage": row.get("usage") or {}, "finish_reason": row.get("finish_reason"), "error": row.get("error"),
           "schema": s["form"], "locator": info, "fields": fields,
           "values": {_code(s, k): g.values.get(k) for k in s["keys"]},
           "accepted": g.accepted, "reasons": g.reasons, "codes": g.codes, "identities": g.identities,
           "failing_fields": [_code(s, k) for k in g.failing_fields], "parsed": row.get("parsed")}
    return _public(s, out)


# ------------------------------------------------------------------------------------------------ the gate
def items_from_values(values: Any, s: dict) -> tuple[Any, bool]:
    """Gate input -> (reader-shaped items, labels_given). Accepts the reader's own output ({"values": [...]} or a
    list of {label, n, w}), or a mapping field -> number (or -> {n, w}) by schema key, code or neutral name. With a
    mapping, no printed labels were read, so each item carries the label expected at its position (the row-label
    check is then not applicable; digits, words and identities are checked as usual)."""
    if isinstance(values, dict) and isinstance(values.get("values"), list):
        return values, True
    if isinstance(values, list):
        return {"values": values}, True
    if not isinstance(values, dict):
        raise ValueError("values must be the reader's JSON ({'values': [...]}) or a mapping field -> number")
    m = {}
    for name, v in values.items():
        k = _key(s, name)
        if k is None:
            raise ValueError(f"unknown field {name!r} for schema {s['form']}")
        m[k] = v
    aliases = s.get("party_aliases", {})
    items = []
    for f in s["fields"]:
        exp = f["label"]
        label = ("+".join((aliases.get(p) or [p])[0] for p in exp["parties"]) if "parties" in exp
                 else " ".join(exp.get("keywords", [])) or f["key"])
        v = m.get(f["key"])
        n, w = (v.get("n"), v.get("w")) if isinstance(v, dict) else (v, None)
        items.append({"label": label, "n": n, "w": w})
    return {"values": items}, False


def gate_values(values: Any, schema: str = DEFAULT_SCHEMA, variant: str = "v1") -> dict:
    """values + schema -> the gate's verdict, every identity (lhs, rhs, ok) and the failing fields. ``variant``:
    v1 = the frozen, pre-registered gate; v2 / v2b = the post-hoc gates (twohands.gate_v2)."""
    from twohands.gate import gate
    s = schemamod.load(schema)
    parsed, labels_given = items_from_values(values, s)
    if variant == "v1":
        g, extra = gate(parsed, s), {}
    else:
        from twohands.gate_v2 import gate_v2
        r = gate_v2(parsed, s, variant=variant)
        g = r.v1
        extra = {"accepted": r.accepted, "reasons": r.reasons, "codes": r.codes, "unchecked": r.unchecked}
    out = {"schema": s["form"], "variant": variant, "accepted": g.accepted, "reasons": g.reasons, "codes": g.codes,
           "identities": g.identities, "failing_fields": [_code(s, k) for k in g.failing_fields],
           "values": {_code(s, k): g.values.get(k) for k in s["keys"]},
           "row_label_check": "checked" if labels_given else "not applicable (no printed labels given)"}
    out.update(extra)
    if "unchecked" in out:
        out["unchecked"] = {_code(s, k): v for k, v in out["unchecked"].items()}
    out["verdict"] = "accepted: the paper's own checks agree with this read" if out["accepted"] \
        else "routed to a person: " + "; ".join(out["reasons"][:3])
    return _public(s, out)


# ------------------------------------------------------------------------------------------------ the audit
@contextlib.contextmanager
def _audit_env(state: Optional[Path], from_stored: bool):
    """Point app.capture_audit at ``state`` (its audits directory) and, with ``from_stored``, let it see only the
    stored pre-registered reads (as twohands.eval.sample_audit_root does): no live read, no model call."""
    from app import capture_audit as ca
    old_dir, old_find = ca.AUDITS, ca.find_read

    def stored_only(a, fid):
        v, page = old_find(a, fid)
        return (v, page) if v is None or v.source.startswith("stored read") else (None, page)
    try:
        if state is not None:
            ca.AUDITS = Path(state)
        if from_stored:
            ca.find_read = stored_only
        yield ca
    finally:
        ca.AUDITS, ca.find_read = old_dir, old_find


def _add_scans(ca, a: dict, scans: Path, layout: str) -> dict:
    """The scans folder -> app.capture_audit.add_scans (the web app's ZIP path: each image located and masked in
    memory by the core, only masked pages written), in ZIPs built in memory of at most MAX_ZIP_FILES images."""
    files = sorted(p for p in Path(scans).rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXT)
    total = {"masked": [], "not_located": [], "not_a_photo": [], "unmatched": [], "skipped": 0}
    for i in range(0, len(files), ca.MAX_ZIP_FILES):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
            for p in files[i:i + ca.MAX_ZIP_FILES]:
                z.write(p, p.name)
        out = ca.add_scans(a, buf.getvalue(), layout)
        for k, v in out.items():
            total[k] = total[k] + v
    a["zip"] = total
    ca.save(a)
    return total


def _read_unread(ca, a: dict, model: str, reader_fn: ReaderFn, log) -> dict:
    """Read every keyed form that has a masked page and no read yet (the web app's "read the rest"), one request per
    page, each answer stored as the live-read path stores it (<audit>/reads/<form>.read.json)."""
    R = ca.run(a)
    n, cost, failed = 0, 0.0, []
    todo = [u for u in R["unread"] if u["queueable"]]
    for j, u in enumerate(todo, 1):
        fid = u["form"]
        _, page = ca.find_read(a, fid)
        row = reader_fn(model, page)
        n += 1
        c = (row.get("usage") or {}).get("cost") or 0.0 if isinstance(row.get("usage"), dict) else 0.0
        cost += c
        if row.get("error") or not row.get("parsed"):
            failed.append(fid)
            log(f"  read {j}/{len(todo)} {fid}: no readable answer ({(row.get('error') or '')[:80]})")
            continue
        d = ca.adir(a["id"]) / "reads"
        d.mkdir(parents=True, exist_ok=True)
        rec = {"clave": fid, "model": row.get("model"), "model_fallback": False,
               "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "secs": row.get("secs"),
               "usage": row.get("usage") or {}, "cost": c, "finish_reason": row.get("finish_reason"),
               "parsed": row["parsed"], "source": "twohands cli"}
        (d / f"{fid}.read.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"  read {j}/{len(todo)} {fid}: {row.get('secs')} s")
    return {"calls": n, "failed": failed, "cost_usd": round(cost, 6)}


def _report_html(aid: str, strict: bool) -> Optional[str]:
    """The web app's printable report page for this audit, rendered in-process (no server, no network)."""
    try:
        from fastapi.testclient import TestClient

        from app import livemodel
        from app.main import app
    except Exception:  # noqa: BLE001 - the web app's extras are not installed: CSV and root still written
        return None
    c = livemodel.chooser
    old = c._refreshing
    c._refreshing = True     # the footer's endpoint status must not start a model-list request from here
    ots_env = os.environ.get("TWOHANDS_OTS")
    os.environ["TWOHANDS_OTS"] = "0"   # nor a timestamp submission (the CLI stamps only with --timestamp)
    try:
        r = TestClient(app).get(f"/audit/{aid}/report" + ("?strict=1" if strict else ""))
        return r.text if r.status_code == 200 else None
    finally:
        c._refreshing = old
        if ots_env is None:
            os.environ.pop("TWOHANDS_OTS", None)
        else:
            os.environ["TWOHANDS_OTS"] = ots_env


def audit(keyed: str | Path, scans: Optional[str | Path] = None, schema: str = DEFAULT_SCHEMA,
          out: Optional[str | Path] = None, from_stored: bool = False, strict: bool = False, model: str = "gemma",
          layout: str = "escaner", state: Optional[str | Path] = None, reader_fn: Optional[ReaderFn] = None,
          receipts: bool = False, html: bool = True, log=print, stamp: bool = False, stamp_post=None) -> dict:
    """The audit, as the web app runs it: keyed CSV (+ scans) -> masked pages -> reads -> gate -> compare.
    Writes to ``out``: report.csv (the web app's CSV, with fingerprint and input hashes), report.html (the web app's
    report page), merkle_root.txt, summary.json, disputes.json and, with ``receipts``, one Merkle receipt per field.
    With ``stamp``, merkle_root.txt is anchored in time on the OpenTimestamps calendars: merkle_root.txt.ots."""
    if schemamod.load(schema).get("form") != DEFAULT_SCHEMA:
        raise ValueError(f"the audit compares keyed files of {DEFAULT_SCHEMA} (the form whose capture columns the "
                         f"audit maps); use 'twohands read' and 'twohands gate' for {schema}")
    keyed = Path(keyed)
    with _audit_env(Path(state) if state else None, from_stored) as ca:
        text = keyed.read_bytes().decode("utf-8-sig", "replace")
        if "�" in text:
            text = keyed.read_bytes().decode("latin-1")
        a = ca.create(text, name=keyed.name, source="cli")
        a = ca.set_mapping(a, a["id_col"], a["mapping"], "zip" if scans else "stored")
        sc, reads = None, {"calls": 0, "failed": [], "cost_usd": 0.0}
        if scans:
            sc = _add_scans(ca, a, Path(scans), layout)
            log(f"scans: {len(sc['masked'])} masked, {len(sc['not_located'])} not located, "
                f"{len(sc['unmatched'])} not in the keyed file")
        if not from_stored:
            reads = _read_unread(ca, a, model, reader_fn or default_reader(), log)
        R = ca.run(a, strict=strict)
        fp = ca.fingerprint(a, R)
        summary = {"audit": a["id"], "keyed": str(keyed), "mode": "strict" if strict else "standard",
                   "reads": "stored (pre-registered Gemma run, no model call)" if from_stored else "stored or new",
                   "model_calls": reads["calls"], "model_cost_usd": reads["cost_usd"], "read_failed": reads["failed"],
                   "forms_keyed": R["forms_keyed"], "forms_read": R["forms_read"], "unread": len(R["unread"]),
                   "fields_mapped": R["fields_mapped"], "checked": R["checked"], "disputed": R["disputed"],
                   "disputed_forms": R["disputed_forms"], "tiers": R["tiers"], "merkle_root": fp["merkle_root"],
                   "fingerprint": fp["sha256"], "scans": ({k: (len(v) if isinstance(v, list) else v)
                                                           for k, v in sc.items()} if sc else None)}
        if out:
            o = Path(out)
            o.mkdir(parents=True, exist_ok=True)
            (o / "report.csv").write_text(ca.report_csv(a, R, fp), encoding="utf-8")
            (o / "merkle_root.txt").write_text(fp["merkle_root"] + "\n", encoding="utf-8", newline="\n")
            if stamp:
                from twohands import timestamp as ots
                try:
                    m = ots.stamp_file(o / "merkle_root.txt", **({"post": stamp_post} if stamp_post else {}))
                    summary["timestamp"] = {"proof": "merkle_root.txt.ots", "submitted": m["submitted"],
                                            "calendars": m["calendars"]}
                    log(f"timestamp: merkle_root.txt.ots ({len(m['calendars'])} calendars; "
                        f"'ots upgrade' after a few hours, then 'ots verify')")
                except OSError as e:
                    summary["timestamp"] = {"error": str(e)}
                    log(f"timestamp: not anchored ({e})")
            (o / "disputes.json").write_text(json.dumps(_disputes(R), ensure_ascii=False, indent=1), encoding="utf-8")
            if html:
                page = _report_html(a["id"], strict)
                if page:
                    (o / "report.html").write_text(page, encoding="utf-8")
            if receipts:
                rd = o / "receipts"
                rd.mkdir(exist_ok=True)
                T, mt = ca.merkle_tree(a, R), ca.merkle_tree
                ca.merkle_tree = lambda *_: T   # one tree for every receipt of this report (same root, same paths)
                try:
                    for d in R["disputes"]:
                        r = ca.receipt(a, R, d["key"])
                        (rd / f"{d['key']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
                finally:
                    ca.merkle_tree = mt
            summary["out"] = str(o)
            summary["files"] = sorted(p.name for p in o.iterdir())
            (o / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
        summary["_disputes"] = R["disputes"]
        return summary


def _disputes(R: dict) -> list[dict]:
    keep = ("pos", "key", "form", "code", "name", "keyed", "model", "words", "tier", "score", "mark")
    return [{k: d.get(k) for k in keep} | {"signals": [s["text"] for s in d["signals"]]} for d in R["disputes"]]


def summary_line(S: dict) -> str:
    t = S["tiers"]
    return (f"audit {S['audit']}: {S['forms_read']} of {S['forms_keyed']} keyed forms read, {S['checked']:,} fields "
            f"checked, {S['disputed']} disputed on {S['disputed_forms']} forms (strong {t['strong']}, medium "
            f"{t['medium']}, weak {t['weak']}); {S['model_calls']} model calls; Merkle root {S['merkle_root']}")


# ------------------------------------------------------------------------------------------------ commands
def cmd_audit(a) -> int:
    S = audit(a.keyed, a.scans, a.schema, a.out, from_stored=a.from_stored, strict=a.strict, model=a.model,
              layout=a.layout, state=a.state, reader_fn=default_reader(a.base_url) if not a.from_stored else None,
              receipts=a.receipts, stamp=a.timestamp, log=(lambda *x: None) if a.quiet else print)
    print(summary_line(S))
    if S.get("out"):
        print(f"report: {Path(S['out']) / 'report.html'}  csv: {Path(S['out']) / 'report.csv'}")
    return 0


def cmd_read(a) -> int:
    r = read_form(a.image, a.schema, a.model, a.masked, a.layout, reader_fn=default_reader(a.base_url),
                  save_masked=a.save_masked)
    if not a.raw:
        r.pop("parsed", None)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r.get("ok") else 1


def cmd_gate(a) -> int:
    values = json.loads(sys.stdin.read() if a.values == "-" else Path(a.values).read_text(encoding="utf-8"))
    r = gate_values(values, a.schema, a.variant)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r["accepted"] else 2


def cmd_verify(a) -> int:
    from twohands import verify_receipt
    return verify_receipt.main([a.receipt] + (["--crop", a.crop] if a.crop else []) + (["--root", a.root] if a.root else []))


def cmd_mcp(a) -> int:
    from twohands import mcp_server
    return mcp_server.main((["--http"] if a.http else []) + ["--host", a.host, "--port", str(a.port)]
                           + (["--allow-reads"] if a.allow_reads else [])
                           + [x for h in a.public_host for x in ("--public-host", h)])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="twohands", description="Two Hands: the model reads, the paper decides.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    au = sub.add_parser("audit", help="compare a keyed CSV with the paper: disputes, report, CSV, Merkle root")
    au.add_argument("--keyed", required=True, help="the keyed CSV (one row per form; INE PREP columns detected)")
    au.add_argument("--scans", help="folder of page images named <form id>.jpg (located and masked before anything)")
    au.add_argument("--schema", default=DEFAULT_SCHEMA)
    au.add_argument("--out", default="report", help="output folder (report.html, report.csv, merkle_root.txt, ...)")
    au.add_argument("--from-stored", action="store_true", help="stored pre-registered reads only: no model call")
    au.add_argument("--strict", action="store_true", help="strong only when Gemma and Qwen (stored) agree")
    au.add_argument("--model", default="gemma", choices=["gemma", "qwen"])
    au.add_argument("--layout", default="escaner", choices=["escaner", "movil"], help="mask layout of the scans")
    au.add_argument("--state", help="where audits are kept (default: the web app's app/state/audits)")
    au.add_argument("--receipts", action="store_true", help="also write one Merkle receipt per disputed field")
    au.add_argument("--timestamp", action="store_true",
                    help="anchor merkle_root.txt with OpenTimestamps (sends only a hash to the public calendars)")
    au.add_argument("--base-url", help="the OpenAI-compatible endpoint (default: AMD_BASE_URL)")
    au.add_argument("--quiet", action="store_true")
    au.set_defaults(fn=cmd_audit)
    rd = sub.add_parser("read", help="read one form: locate, mask, one request, the gate")
    rd.add_argument("image")
    rd.add_argument("--schema", default=DEFAULT_SCHEMA)
    rd.add_argument("--model", default="gemma", choices=["gemma", "qwen"])
    rd.add_argument("--masked", action="store_true", help="the image is already a masked canonical page")
    rd.add_argument("--layout", default="movil", choices=["movil", "escaner"])
    rd.add_argument("--save-masked", help="write the masked page here")
    rd.add_argument("--base-url", help="the OpenAI-compatible endpoint (default: AMD_BASE_URL)")
    rd.add_argument("--raw", action="store_true", help="include the model's parsed JSON")
    rd.set_defaults(fn=cmd_read)
    g = sub.add_parser("gate", help="the gate on a read: identities and verdict (exit 0 accepted, 2 routed)")
    g.add_argument("values", help="JSON file ('-' = stdin): the reader's output or a mapping field -> number")
    g.add_argument("--schema", default=DEFAULT_SCHEMA)
    g.add_argument("--variant", default="v1", choices=["v1", "v2", "v2b"])
    g.set_defaults(fn=cmd_gate)
    v = sub.add_parser("verify-receipt", help="check an audit receipt's Merkle path (and its crop)")
    v.add_argument("receipt")
    v.add_argument("--crop")
    v.add_argument("--root")
    v.set_defaults(fn=cmd_verify)
    m = sub.add_parser("mcp", help="run the MCP server (stdio; --http for streamable HTTP)")
    m.add_argument("--http", action="store_true")
    m.add_argument("--host", default="127.0.0.1")
    m.add_argument("--port", type=int, default=8765)
    m.add_argument("--allow-reads", action="store_true", help="over HTTP, allow read_form to call the model")
    m.add_argument("--public-host", action="append", default=[], help="public host name forwarded here (repeatable)")
    m.set_defaults(fn=cmd_mcp)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (OSError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
