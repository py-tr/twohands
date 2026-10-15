"""Amendment 4 pre-registered secondary: two Gemma reads with different tilings as the two hands, on the 43 pilot forms.

    # on the self-hosted MI300X endpoint (scripts/endpoint_switch.py env), Gemma served:
    python scripts/gemma_gemma_43.py read [--workers 8] [--qwen results/<qwen reads of the 43>.jsonl]
    # recompute from a saved read, no model call:
    python scripts/gemma_gemma_43.py compare results/gemma_gemma_43_<ts>.jsonl [--qwen ...]

Read A = the masked page + 4 tiles (the four content tiles of the schema: left column, party rows, coalition rows,
bottom rows + section 7; no enlarged logo strips). Read B = the masked page + 6 tiles (the production read). Both
Gemma-4-31B-IT, temperature 0, max_tokens 2000, the same parser. A reply cut at max_tokens is not a usable read.

Tiers, each on the same 43 forms, judged against the pilot truth (PREP capture + the pilot adjudication,
scripts/consistency_43.py::load_reference):
- gemma_gemma: Amendment 2 (d) two-reader rule (twohands/tiers.py) with read A and read B as the two readers;
- gemma_qwen: the same rule with read B and a Qwen read of the same 43 (--qwen: a jsonl of reader rows of the 43 with
  "clave" and "parsed"/"fields"; default: the stored pilot Qwen run "spike-qwen" in app/data/spike_runs.json, which used
  the pilot prompt and tiling, and is labelled so);
- gemma_a_alone / gemma_b_alone: the frozen gate on each read (context).
Shared mistakes: fields (truth known, both reads usable) where both reads are wrong with the same value, against
fields where only one is wrong. If same-model reads share mistakes, the line says so.

Writes results/gemma_gemma_43_<ts>.jsonl (raw rows, read A and B) and .json (the comparison). Never writes
results/calls_*.jsonl.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from twohands import reader, schema as schemamod  # noqa: E402
from twohands.gate import gate  # noqa: E402
from twohands.tiers import digits, two_reader, usable  # noqa: E402

PAGES = REPO / "data" / "masked" / "spike"
RESULTS = REPO / "results"
TILES_A = 4          # page + the first 4 schema tiles (content tiles, no logo strips)


def schema_for(read_id: str, s: dict) -> dict:
    if read_id == "B":
        return s
    sa = copy.deepcopy(s)
    sa["layout"]["tiles"] = sa["layout"]["tiles"][:TILES_A]
    return sa


def to_fields(parsed, s: dict) -> dict:
    g = gate(parsed, s)
    return {f["key"]: {"label": g.labels.get(f["key"]), "n": g.values.get(f["key"]), "w": g.words.get(f["key"])}
            for f in s["fields"]}


def rec(clave: str, read_id: str, r: dict, s: dict, sr: dict) -> dict:
    ok = r.get("parsed") is not None and r.get("finish_reason") != "length" and not r.get("error")
    return {"clave": clave, "read": read_id, "tiles": len(sr["layout"]["tiles"]), "model": r.get("model"),
            "prompt_sha256": reader.prompt_sha256(sr), "secs": r.get("secs"), "finish_reason": r.get("finish_reason"),
            "usage": r.get("usage"), "error": r.get("error"), "parsed_ok": ok,
            "accepted_v1": bool(ok and gate(r.get("parsed"), s).accepted),
            "fields": to_fields(r.get("parsed"), s) if ok else {}, "content": r.get("content")}


def qwen_rows(path: Path | None, runs_json: Path = REPO / "app" / "data" / "spike_runs.json") -> tuple[dict, str]:
    """{clave: row with fields} for the Qwen reads of the 43, and a label saying where they came from."""
    s = schemamod.load()
    out = {}
    if path:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("fields") is None and "parsed" in r:
                ok = r.get("parsed") is not None and r.get("finish_reason") != "length" and not r.get("error")
                r = {**r, "parsed_ok": ok, "fields": to_fields(r["parsed"], s) if ok else {}}
            out[r["clave"]] = r
        return out, f"Qwen reads in {Path(path).name}"
    for run in json.loads(runs_json.read_text(encoding="utf-8")):
        if run.get("id") == "spike-qwen":
            for r in run["rows"]:
                p = r.get("parsed") or {}
                out[r["clave"]] = {"clave": r["clave"], "parsed_ok": bool(p),
                                   "fields": {k: {"n": (v or {}).get("n"), "w": (v or {}).get("w")} for k, v in p.items()}}
    return out, "stored pilot Qwen run spike-qwen (pilot prompt and tiling, Token Factory)"


def compare(rows: list[dict], Q: dict, R: dict, s: dict | None = None, qwen_label: str = "") -> dict:
    s = s or schemamod.load()
    keys = s["keys"]
    claves, truth, graded = R["claves"], R["truth"], R["graded"]
    A = {r["clave"]: r for r in rows if r.get("read") == "A"}
    B = {r["clave"]: r for r in rows if r.get("read") == "B"}

    def frozen(r):
        return bool(usable(r) and r.get("accepted_v1"))

    rules = {"gemma_gemma": lambda k: two_reader(A.get(k), B.get(k), s)[0],
             "gemma_qwen": lambda k: two_reader(B.get(k), Q.get(k), s)[0],
             "gemma_a_alone": lambda k: frozen(A.get(k)),
             "gemma_b_alone": lambda k: frozen(B.get(k))}
    src = {"gemma_gemma": A, "gemma_qwen": B, "gemma_a_alone": A, "gemma_b_alone": B}
    tiers = {}
    for name, rule in rules.items():
        acc = [k for k in claves if rule(k)]
        n, errs = 0, []
        for k in acc:
            d = digits(src[name][k], keys)
            for f in graded:
                t = truth[k][f]
                if t is None:
                    continue
                n += 1
                if d.get(f) != t:
                    errs.append({"clave": k, "field": f, "read": d.get(f), "truth": t})
        tiers[name] = {"accepted": len(acc), "fields": n, "errors": len(errs), "error_list": errs, "forms_accepted": acc}

    def shared(X, Y):
        both_same = both_diff = only_x = only_y = n = 0
        same_list = []
        for k in claves:
            if not (usable(X.get(k)) and usable(Y.get(k))):
                continue
            dx, dy = digits(X[k], keys), digits(Y[k], keys)
            for f in graded:
                t = truth[k][f]
                if t is None:
                    continue
                n += 1
                wx, wy = dx.get(f) != t, dy.get(f) != t
                if wx and wy and dx.get(f) == dy.get(f):
                    both_same += 1
                    same_list.append({"clave": k, "field": f, "read": dx.get(f), "truth": t})
                elif wx and wy:
                    both_diff += 1
                elif wx:
                    only_x += 1
                elif wy:
                    only_y += 1
        return {"fields": n, "both_wrong_same_value": both_same, "both_wrong_different": both_diff,
                "only_first_wrong": only_x, "only_second_wrong": only_y, "shared_list": same_list}

    return {"forms": len(claves), "reads_a": sum(usable(A.get(k)) for k in claves),
            "reads_b": sum(usable(B.get(k)) for k in claves), "reads_q": sum(usable(Q.get(k)) for k in claves),
            "qwen_source": qwen_label, "tiles_a": TILES_A, "tiles_b": len(s["layout"]["tiles"]),
            "tiers": tiers, "shared_gemma_gemma": shared(A, B), "shared_gemma_qwen": shared(B, Q)}


def row_text(c: dict) -> str:
    t, sg, sq = c["tiers"], c["shared_gemma_gemma"], c["shared_gemma_qwen"]

    def tier(n):
        return f"{t[n]['accepted']}/{c['forms']} accepted, {t[n]['errors']} of {t[n]['fields']} accepted fields wrong"
    verdict = ("same-model reads SHARE mistakes" if sg["both_wrong_same_value"] > sq["both_wrong_same_value"]
               else "same-model reads do not share more mistakes than Gemma+Qwen")
    return (f"GEMMA+GEMMA 43 pilot | A page+{c['tiles_a']} tiles, B page+{c['tiles_b']} tiles | reads A {c['reads_a']}, "
            f"B {c['reads_b']}, Qwen {c['reads_q']} | Gemma+Gemma: {tier('gemma_gemma')} | Gemma+Qwen: {tier('gemma_qwen')} "
            f"({c['qwen_source']}) | both wrong with the same value: Gemma+Gemma {sg['both_wrong_same_value']} of "
            f"{sg['fields']}, Gemma+Qwen {sq['both_wrong_same_value']} of {sq['fields']} | {verdict}")


def do_read(workers: int, chat=None, claves=None, pages: Path = PAGES, out: Path | None = None) -> Path:
    if chat is None:
        import endpoint_switch
        info = endpoint_switch.apply()
        if not info["switched"]:
            raise SystemExit("refusing: TWOHANDS_BASE_URL is not set (this ablation runs on the self-hosted endpoint only)")
    s = schemamod.load()
    if claves is None:
        from consistency_43 import load_reference
        claves = load_reference()["claves"]
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = out or RESULTS / f"gemma_gemma_43_{ts}.jsonl"
    jobs = [(k, rid) for k in claves for rid in ("A", "B")]

    def work(job):
        k, rid = job
        sr = schema_for(rid, s)
        page = pages / f"{k}.jpg"
        if not page.is_file():
            return {"clave": k, "read": rid, "parsed_ok": False, "error": "no masked page", "fields": {}}
        r = reader.read("gemma", page, sr, chat=chat)
        return rec(k, rid, r, s, sr)

    with ThreadPoolExecutor(workers) as ex, open(out, "w", encoding="utf-8") as fh:
        for i, row in enumerate(ex.map(work, jobs), 1):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{i}/{len(jobs)}] {row['clave']} {row['read']} {'ok' if row.get('parsed_ok') else 'no read'} "
                  f"{row.get('secs')}s {row.get('error') or ''}", flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read"); r.add_argument("--workers", type=int, default=8); r.add_argument("--qwen")
    c = sub.add_parser("compare"); c.add_argument("path"); c.add_argument("--qwen")
    a = ap.parse_args(argv)
    path = do_read(a.workers) if a.cmd == "read" else Path(a.path)
    from consistency_43 import load_reference
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    Q, ql = qwen_rows(Path(a.qwen) if a.qwen else None)
    res = compare(rows, Q, load_reference(), qwen_label=ql)
    res["source"] = path.name
    path.with_suffix(".json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(row_text(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
