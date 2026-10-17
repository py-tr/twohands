"""An end-to-end execution trace of two real forms of the pre-registered 300, from stored data only (no model call,
no network, no key): one form the gate ACCEPTED and one it ROUTED because the arithmetic refused a misread.

    python scripts/build_trace.py           # writes app/data/trace.json (the /trace page reads it) and docs/TRACE.md
    python scripts/build_trace.py --check   # recomputes both from the stored data and compares (make eval)

For each form, everything is recomputed here, not copied:
  request   model id and prompt sha256 from the run record (results/calls_gemma.jsonl), checked against the prompt
            rebuilt from twohands/reader.py; temperature, max_tokens and the images sent from reader.build_body
  read      the raw model output (the stored `content`; its sha256), the items of the relevant field as returned
            (the printed row label of a vote row is shown as Option NN, never the party)
  gate      reader.parse + twohands/gate.py run again on that raw output: every identity with its terms and sums,
            words = digits, and the decision; it must equal the stored record's decision
  record    the official first capture (app/data/audit_sample_prep300.csv, via the sample audit), the paper value
            and the certified count (results/adjudication/certified.json, verdicts.json)
  receipt   the sample audit's Merkle tree rebuilt over the stored Gemma reads and the committed masked pages, as
            twohands/eval.py does for results/sample_audit_root.txt: the field's leaf, its proof path, the root, and
            twohands.verify_receipt run on it (with the crop bytes and the published root)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT_J = REPO / "app" / "data" / "trace.json"
OUT_M = REPO / "docs" / "TRACE.md"
CALLS = REPO / "results" / "calls_gemma.jsonl"
CERT = REPO / "results" / "adjudication" / "certified.json"
VERDICTS = REPO / "results" / "adjudication" / "verdicts.json"
ROOT_FILE = REPO / "results" / "sample_audit_root.txt"
# (form, field code, what the trace shows). Fixed once: the only accepted form of the 300 whose read disagrees with
# the official capture where the paper sides with the read, and the first caught misread of docs/GEMMA.md.
FORMS = (("080310B0100", "SOBRANTES", "accepted"), ("122655C0100", "OPT02", "routed"))
ENDPOINT = "AMD Token Factory"


def _last_reads() -> dict:
    out = {}
    for line in CALLS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["clave"]] = r
    return out


def _sample_audit():
    """The sample audit (official capture of the 300 vs the stored Gemma reads), rebuilt in a temporary directory over
    stored reads only, exactly as twohands/eval.py's sample_audit_root does."""
    from app import capture_audit as ca
    old_dir, old_find = ca.AUDITS, ca.find_read
    tmp = Path(tempfile.mkdtemp(prefix="twohands-trace-"))

    def stored_only(a, fid):
        v, page = old_find(a, fid)
        return (v, page) if v is None or v.source.startswith("stored read") else (None, page)
    try:
        ca.AUDITS, ca.find_read = tmp / "audits", stored_only
        a = ca.sample()
        R = ca.run(a)
        out = {"a": a, "R": R, "T": ca.merkle_tree(a, R), "receipts": {}, "crops": {}}
        for clave, code, _ in FORMS:
            key = f"{clave}__{code}"
            out["receipts"][key] = ca.receipt(a, R, key)
            d = next(d for d in R["disputes"] if d["key"] == key)
            out["crops"][key] = ca.crop_of(a, d)
        return out
    finally:
        ca.AUDITS, ca.find_read = old_dir, old_find
        shutil.rmtree(tmp, ignore_errors=True)


def _raw_items(content: str) -> list:
    from twohands import gate as gatemod
    from twohands import reader
    return gatemod.items_of(reader.parse(content)) or []


def request_block(rows: list[dict]) -> dict:
    from twohands import reader
    from twohands import schema as schemamod
    s = schemamod.load()
    rec = {r["prompt_sha256"] for r in rows}
    models = {r["model"] for r in rows}
    assert len(rec) == 1 and len(models) == 1, "the two forms were read with one prompt and one model"
    tiles = s["layout"]["tiles"]
    body = reader.build_body("gemma", __import__("PIL.Image", fromlist=["Image"]).new("RGB", (400, 600), "white"), s)
    imgs = sum(1 for c in body["messages"][1]["content"] if c["type"] == "image_url")
    assert imgs == 1 + len(tiles)
    return {"model": models.pop(), "endpoint": ENDPOINT, "api": "OpenAI-compatible POST /chat/completions",
            "prompt_sha256": rec.pop(), "prompt_sha256_rebuilt": reader.prompt_sha256(s),
            "temperature": body["temperature"], "max_tokens": body["max_tokens"],
            "response_format": "none" if "response_format" not in body else body["response_format"],
            "images": imgs, "tiles": [t["name"] for t in tiles],   # the tile ids (their prompt text names parties)
            "jpeg": f"longest side at most {reader.B64_MAXSIDE} px, quality {reader.B64_QUALITY}",
            "image_tokens": sorted({r["usage"]["prompt_tokens_details"]["image_tokens"] for r in rows})}


def _ident_rows(gr, s: dict) -> list[dict]:
    from app import store as storemod
    out = []
    for idt, got in zip(s["identities"], gr.identities):
        lhs = s["vote_keys"] if idt["sum"] == "@vote" else idt["sum"]
        L = [{"name": storemod.name_of(k), "v": gr.values.get(k)} for k in lhs]
        Rr = [{"name": storemod.name_of(k), "v": gr.values.get(k)} for k in idt["equals"]]
        out.append({"name": idt["name"], "lhs_terms": L, "rhs_terms": Rr, "lhs": got.get("lhs"), "rhs": got.get("rhs"),
                    "ok": got.get("ok")})
    return out


def form_block(clave: str, code: str, kind: str, row: dict, A: dict, cert: dict, verdicts: dict) -> dict:
    from app import store as storemod
    from twohands import gate as gatemod
    from twohands import merkle
    from twohands import schema as schemamod
    from twohands import verify_receipt as vr
    s = schemamod.load()
    key = storemod.key_of(code)
    name = storemod.name_of(key)
    items = _raw_items(row["content"])
    pos = [f["key"] for f in s["fields"]].index(key)
    it = dict(items[pos])
    is_vote = key in s["vote_keys"]
    raw = {"label": f"(printed row logos; shown here as {name})" if is_vote else it.get("label"), "n": it.get("n"),
           "w": it.get("w")}
    if it.get("fix"):
        raw["fix"] = it["fix"]
    gr = gatemod.gate(reader_parse(row["content"]), s)
    # the gate run again on the raw output must give the stored decision
    assert gr.accepted == row["accepted"] and gr.reasons == row["route_reasons"], clave
    assert [(i["name"], i.get("lhs"), i.get("rhs"), i["ok"]) for i in gr.identities] == \
           [(i["name"], i.get("lhs"), i.get("rhs"), i["ok"]) for i in row["identities"]], clave
    with_words = [f["key"] for f in s["fields"] if gr.words.get(f["key"]) is not None]
    agree_words = [k for k in with_words if gr.values.get(k) == gr.words.get(k)]
    idents = _ident_rows(gr, s)
    fid = f"{clave}__{code}"
    dispute = next(d for d in A["R"]["disputes"] if d["key"] == fid)
    form_disputes = [d for d in A["R"]["disputes"] if d["form"] == clave]
    c = cert.get((clave, key)) or {}
    v = verdicts.get(f"{clave}__{key}") or {}
    paper = c.get("paper", v.get("paper"))
    if c.get("covered"):
        certified = {"value": c["computos"], "how": "settled by comparison with the paper, Cotejo"
                     if str(c.get("obs", "")).startswith("Cotejo") else "settled by recount"}
    else:
        certified = {"value": None, "how": "the certified count covers the vote rows and TOTAL, not this field"}
    paper_by = ("confirmed by the certified count" if c.get("covered") and c.get("agrees")
                else "the AI adjudicator's reading of the crop: "
                + re.sub(r"\s*\(PREP keyed [^)]*\)", "", storemod.neutralize(v.get("evidence", ""))))
    whatif = None
    if kind == "routed":
        bad = [i for i in idents if i["ok"] is False]
        assert len(bad) == 1, clave
        b = bad[0]
        fixed = b["lhs"] - gr.values[key] + paper
        assert fixed == b["rhs"], clave
        whatif = {"identity": b["name"], "with": paper, "lhs": fixed, "rhs": b["rhs"]}
    rc = A["receipts"][fid]
    root_published = ROOT_FILE.read_text(encoding="utf-8").split()[0]
    crop = A["crops"][fid]
    checks = vr.check(rc, crop, root_published)
    assert merkle.walk(rc["leaf_hash"], rc["proof"]) == rc["root"]
    return {
        "form": clave, "code": code, "name": name, "kind": kind,
        "crop_site": f"/crop/{clave}/{code}.jpg?pad=0.02&label=0", "page_site": f"/masked/{clave}.jpg",
        "form_site": f"/form/{clave}",
        "crop_repo": (f"caught/{clave}_{code}.jpg" if (REPO / "docs" / "caught" / f"{clave}_{code}.jpg").is_file()
                      else f"../results/adjudication/{clave}__{key}.jpg"),
        "record": {"ts": row["ts"], "image": row["image"], "latency_s": row["latency_s"], "attempts": row["attempts"],
                   "finish_reason": row["finish_reason"], "prompt_tokens": row["usage"]["prompt_tokens"],
                   "completion_tokens": row["usage"]["completion_tokens"], "cost_usd": row["cost_usd"],
                   "content_sha256": hashlib.sha256(row["content"].encode("utf-8")).hexdigest(),
                   "content_chars": len(row["content"]), "n_items": len(items)},
        "raw_item": raw, "position": pos + 1,
        "gate": {"shape": f"{len(items)} values, the form has {len(s['fields'])}",
                 "labels_ok": "label" not in gr.codes,
                 "digits_read": f"{sum(1 for f in s['fields'] if gr.values.get(f['key']) is not None)} of {len(s['fields'])}",
                 "words": f"{len(agree_words)} of {len(with_words)} fields with words read: digits = words",
                 "field_words": "digits = words" if gr.words.get(key) == gr.values.get(key) else "digits != words",
                 "in_identities": [i["name"] for i in idents if name in [t["name"] for t in i["lhs_terms"] + i["rhs_terms"]]],
                 "identities": idents, "accepted": gr.accepted,
                 "reasons": [storemod.neutralize(x) for x in gr.reasons], "codes": gr.codes},
        "whatif": whatif,
        "official": {"keyed": dispute["keyed"], "read": gr.values.get(key), "words": gr.words.get(key), "paper": paper,
                     "paper_by": paper_by, "certified": certified, "form_disputes": len(form_disputes)},
        "receipt": {"index": rc["index"], "n_leaves": rc["n_leaves"], "leaf": rc["leaf"], "leaf_hash": rc["leaf_hash"],
                    "proof": rc["proof"], "root": rc["root"], "root_published": root_published,
                    "verify_route": f"/verify/{clave}/{code}",
                    "checks": [{"label": lab, "ok": ok, "hash": h[:16]} for lab, ok, h in checks],
                    "verified": all(ok for _, ok, _ in checks)},
    }


def reader_parse(content: str):
    from twohands import reader
    return reader.parse(content)


def compute() -> dict:
    last = _last_reads()
    rows = [last[c] for c, _, _ in FORMS]
    cert = {(x["clave"], x["field"]): x for grp in json.loads(CERT.read_text(encoding="utf-8")).values() for x in grp}
    verdicts = json.loads(VERDICTS.read_text(encoding="utf-8"))
    A = _sample_audit()
    forms = [form_block(c, code, kind, last[c], A, cert, verdicts) for c, code, kind in FORMS]
    return {"request": request_block(rows), "forms": forms, "root": A["T"]["root"], "n_leaves": A["T"]["n"],
            "source": "scripts/build_trace.py from results/calls_gemma.jsonl, app/data/audit_sample_prep300.csv, "
                      "results/adjudication/, data/masked/ (no model call)"}


# ------------------------------------------------------------------------------------------- markdown
def _terms(ts: list[dict]) -> str:
    return " + ".join(f"{t['name']} {t['v']}" for t in ts)


def markdown(d: dict) -> str:
    Q = d["request"]
    a, b = d["forms"]
    L = ["# Execution trace: two real forms, end to end", "",
         "Generated by `python scripts/build_trace.py` from stored data (no model call); `--check` runs in `make eval`. "
         "The same trace is on the site at `/trace`.", "",
         f"Two forms of the pre-registered random 300, followed from the request to the receipt: **{a['form']}**, "
         f"which the gate accepted, and **{b['form']}**, which the gate routed to a person because the arithmetic "
         "refused a misread (the first caught misread in [GEMMA.md](GEMMA.md#misreads-the-arithmetic-caught)). "
         "Vote rows are Option NN. Every value below is recomputed from the files named in each step.", "",
         "## The request (the same for both forms)", "",
         "| setting | value | source |", "|---|---|---|",
         f"| model | `{Q['model']}` | run record (`results/calls_gemma.jsonl`, field `model`) |",
         f"| endpoint | {Q['endpoint']}, {Q['api']} | `twohands/amd.py`; the key comes from the environment and is never stored |",
         f"| prompt sha256 | `{Q['prompt_sha256']}` | run record; rebuilt from `twohands/reader.py`: "
         f"{'the same' if Q['prompt_sha256'] == Q['prompt_sha256_rebuilt'] else 'DIFFERENT'} |",
         f"| temperature | {Q['temperature']} | `twohands/reader.py` `build_body` |",
         f"| max_tokens | {Q['max_tokens']} | `twohands/reader.py` `MAX_TOKENS` |",
         f"| response_format | {Q['response_format']} | `build_body` (it breaks Gemma with images) |",
         f"| images sent | {Q['images']}: the masked page, then {len(Q['tiles'])} masked tiles ({', '.join(f'`{t}`' for t in Q['tiles'])}); "
         f"JPEG, {Q['jpeg']} | `build_body`, `twohands/mask.py` `tiles` |",
         f"| image tokens billed | {', '.join(f'{x:,}' for x in Q['image_tokens'])} per form | run record `usage` |", ""]
    for i, f in enumerate(d["forms"]):
        g, o, r, rec = f["gate"], f["official"], f["receipt"], f["record"]
        head = "Accepted" if f["kind"] == "accepted" else "Routed"
        L += [f"## ({'ab'[i]}) {head}: form {f['form']}, {f['name']}", "",
              "**1. The photo.** "
              f"Masked crop: [{f['crop_repo'].split('/')[-1]}]({f['crop_repo']}); on the site `{f['crop_site']}` "
              f"(the exact bytes the receipt hashes), the masked page `{f['page_site']}`, the form `{f['form_site']}`.", "",
              f"**2. The read.** One request, {rec['ts']}: {rec['latency_s']} s, {rec['attempts']} attempt, finish "
              f"`{rec['finish_reason']}`, {rec['prompt_tokens']:,} tokens in, {rec['completion_tokens']:,} out, "
              f"${rec['cost_usd']:.9f}. Raw output: {rec['content_chars']:,} characters, sha256 "
              f"`{rec['content_sha256']}`, {rec['n_items']} items. Item {f['position']} ({f['name']}), as returned:", "",
              "```json", json.dumps(f["raw_item"], ensure_ascii=False), "```", "",
              f"**3. The gate** (`twohands/gate.py`, run again here on the raw output). Shape: {g['shape']}. Row labels: "
              f"{'consistent' if g['labels_ok'] else 'mismatch'}. Digits read: {g['digits_read']}. Words: {g['words']} "
              f"({f['name']}: {g['field_words']}). Identities:", "",
              "| identity | left side | right side | result |", "|---|---|---|---|"]
        for t in g["identities"]:
            L.append(f"| {t['name']} | {_terms(t['lhs_terms'])} = **{t['lhs']}** | {_terms(t['rhs_terms'])} = "
                     f"**{t['rhs']}** | {'pass' if t['ok'] else 'FAIL'} |")
        L.append("")
        if g["accepted"]:
            L.append(f"**4. Decision: accepted**, no person: every check holds. The same as the stored record. "
                     + (f"{f['name']} is in no identity; on this field the check that holds is digits = words."
                        if not g["in_identities"] else ""))
        else:
            w = f["whatif"]
            L.append(f"**4. Decision: routed to a person.** Cause: {'; '.join(g['reasons'])} (the only reason; the same "
                     f"as the stored record). {f['name']}: digits = words, so only the arithmetic could catch it. With "
                     f"the paper's {w['with']}, {w['identity']} gives {w['lhs']} = {w['rhs']}.")
        cv = o["certified"]
        L += ["", f"**5. Against the official record.** The official first capture keyed **{o['keyed']}**; Gemma read "
              f"{o['read']} (digits) and {o['words']} (words); the paper says **{o['paper']}** ({o['paper_by']}); "
              + (f"the certified count says **{cv['value']}** ({cv['how']})." if cv["value"] is not None
                 else f"certified count: none ({cv['how']}).")
              + f" Disputed fields on this form in the sample audit: {o['form_disputes']}.", "",
              f"**6. The receipt.** Leaf {r['index'] + 1} of {r['n_leaves']} in the sample audit's Merkle tree "
              "(`twohands/merkle.py`: leaf = SHA-256(0x00 || canonical JSON), node = SHA-256(0x01 || left || right)).", "",
              "```json", json.dumps(r["leaf"], ensure_ascii=False, sort_keys=True), "```", "",
              f"Leaf hash `{r['leaf_hash']}`. Proof path ({len(r['proof'])} steps):", "",
              "| step | sibling on the | sibling hash |", "|---|---|---|"]
        L += [f"| {k + 1} | {p['side']} | `{p['hash']}` |" for k, p in enumerate(r["proof"])]
        L += ["", f"Root `{r['root']}` (published: `results/sample_audit_root.txt`, "
              f"{'the same' if r['root'] == r['root_published'] else 'DIFFERENT'}; anchored with OpenTimestamps).", "",
              "Verify:", "", "```",
              f"curl -sL https://<host>{r['verify_route']} -o receipt.json",
              f"curl -s \"https://<host>{f['crop_site']}\" -o crop.jpg",
              f"python -m twohands.verify_receipt receipt.json --crop crop.jpg --root {r['root_published']}", "```", "",
              "Result (the same checks, run here):", ""]
        L += [f"- {'ok' if c['ok'] else 'FAIL'}: {c['label']} (`{c['hash']}`)" for c in r["checks"]]
        L += ["", f"**{'VERIFIED' if r['verified'] else 'NOT VERIFIED'}.** The receipt proves this record (form, field, "
              "keyed value, Gemma's digits and words, tier, crop hash) is unchanged since the report was sealed. It does "
              "not prove the reading is right"
              + (": here Gemma's reading is wrong, and the receipt seals it all the same; the arithmetic is what caught "
                 "it." if f["kind"] == "routed" else "; the paper settles that."), ""]
    return "\n".join(L)


def _party_words() -> list[str]:
    from twohands import schema as schemamod
    s = schemamod.load()
    return sorted({a for names in s.get("party_aliases", {}).values() for a in names} | set(s.get("party_aliases", {})))


def leaks(text: str) -> list[str]:
    """Party names or the word we never use, in a generated text."""
    out = [w for w in _party_words() if re.search(rf"(?<![A-Za-z0-9]){re.escape(w)}(?![A-Za-z0-9])", text, re.I)]
    return out + (["fraud"] if "fraud" in text.lower() else [])


def page_text() -> str:
    import html
    from fastapi.testclient import TestClient
    from app.main import app
    h = TestClient(app).get("/trace").text
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", h)).split())


def must_show(d: dict) -> list[str]:
    """What the /trace page must carry: per form the leaf hash, the root, the raw output hash, each identity's sums."""
    out = [d["request"]["prompt_sha256"], d["request"]["model"], d["request"]["endpoint"]]
    for f in d["forms"]:
        out += [f["receipt"]["leaf_hash"], f["receipt"]["root"], f["record"]["content_sha256"], f["official"]["keyed"]]
        out += [f"{t['lhs']}" for t in f["gate"]["identities"]] + [p["hash"] for p in f["receipt"]["proof"]]
    return out


def _write(p: Path, text: str) -> None:
    p.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    d = compute()
    md = markdown(d)
    js = json.dumps(d, indent=1, ensure_ascii=False) + "\n"
    if not a.check:
        bad = leaks(md + js)
        if bad:
            print(f"build_trace: refused, the trace names {bad}")
            return 1
        _write(OUT_J, js)
        _write(OUT_M, md)
        print(f"build_trace: wrote {OUT_J.relative_to(REPO)} and {OUT_M.relative_to(REPO)}: "
              + "; ".join(f"{f['form']} {f['kind']}, receipt {'VERIFIED' if f['receipt']['verified'] else 'NOT VERIFIED'}"
                          for f in d["forms"]))
        return 0
    bad = []
    try:
        if json.loads(OUT_J.read_text(encoding="utf-8")) != json.loads(js):
            bad.append("app/data/trace.json differs from the stored data (run python scripts/build_trace.py)")
        if OUT_M.read_text(encoding="utf-8").replace("\r\n", "\n") != md:
            bad.append("docs/TRACE.md differs from the stored data (run python scripts/build_trace.py)")
    except OSError as e:
        bad.append(str(e))
    if not all(f["receipt"]["verified"] for f in d["forms"]):
        bad.append("a receipt does not verify")
    if d["root"] != ROOT_FILE.read_text(encoding="utf-8").split()[0]:
        bad.append("the rebuilt sample audit root differs from results/sample_audit_root.txt")
    bad += [f"the trace names '{w}'" for w in leaks(md + js)]
    t = page_text()
    bad += [f"/trace does not show {m[:24]}" for m in must_show(d) if m not in t]
    for doc, link in (("README.md", "docs/TRACE.md"), ("templates/results.html", 'href="/trace"')):
        if link not in (REPO / doc).read_text(encoding="utf-8"):
            bad.append(f"{doc}: no link to the trace")
    print(f"build_trace --check: {len(bad)} mismatches" + "".join(f"\n  - {b}" for b in bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
