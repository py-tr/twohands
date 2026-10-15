"""Consistency check of the new serving stack on the 43 pilot ("spike") forms.

    # read on the self-hosted endpoint (scripts/endpoint_switch.py env), then compare:
    python scripts/consistency_43.py read [--workers 8]
    # recompute the comparison from a saved read, no model call:
    python scripts/consistency_43.py compare results/consistency_43_<ts>.jsonl

The 43 masked pilot pages (data/masked/spike/<clave>.jpg) are read with the PRODUCTION reader (frozen prompt, page +
6 tiles, temperature 0) and gated with the frozen gate (v1) and gate v2 (Amendment 3). Reference: the stored
Token Factory Gemma-4-31B-IT run on the same 43 forms, spike v2 (../spikes/tally-witness/scores_gemma_v2.json and
app/data/spike_runs.json "spike-gemma-v2"): its accept decisions and its accepted-field accuracy against the
adjudicated truth (PREP capture + ../spikes/tally-witness/adjudicate.json). Note: the reference used the spike's v2
prompt and gate, so this compares serving stacks AND reader versions; per-field digit agreement on all 43 forms is
the stack-level number least affected by that.

Prints one consistency row and writes results/consistency_43_<ts>.json. Never writes results/calls_*.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from twohands import reader, schema  # noqa: E402
from twohands.gate import gate  # noqa: E402
from twohands.gate_v2 import gate_v2  # noqa: E402

SPIKE = REPO.parent / "spikes" / "tally-witness"
PAGES = REPO / "data" / "masked" / "spike"
RESULTS = REPO / "results"


def num(v):
    v = str(v if v is not None else "").strip().strip("'").replace(",", "")
    return int(v) if v.isdigit() else None


def load_reference(spike: Path = SPIKE, runs_json: Path = REPO / "app" / "data" / "spike_runs.json") -> dict:
    """{claves, truth{clave:{KEY:int|None}}, ref{clave:{accepted, values{KEY:int}}}} from the stored spike v2 run."""
    s = schema.load()
    graded = [f for f in s["fields"] if f.get("csv")]
    sample = json.loads((spike / "data" / "sample.json").read_text(encoding="utf-8"))
    claves = [x["clave"] for x in sample]
    tr = json.loads((spike / "data" / "truth_rows.json").read_text(encoding="utf-8"))
    adj = json.loads((spike / "adjudicate.json").read_text(encoding="utf-8"))
    truth = {}
    for k in claves:
        prep = tr[k]["prep"]
        truth[k] = {f["key"]: adj.get(k, {}).get(f["key"], num(prep.get(f["csv"]))) for f in graded}
    sc = {r["clave"]: r for r in json.loads((spike / "scores_gemma_v2.json").read_text(encoding="utf-8"))["gemma"]}
    vals = {}
    if runs_json.is_file():
        for run in json.loads(runs_json.read_text(encoding="utf-8")):
            if run.get("id") == "spike-gemma-v2":
                for r in run["rows"]:
                    vals[r["clave"]] = {kk: (v or {}).get("n") for kk, v in (r.get("parsed") or {}).items()}
    ref = {k: {"accepted": bool(sc.get(k, {}).get("accepted")), "values": vals.get(k, {})} for k in claves}
    return {"claves": claves, "truth": truth, "ref": ref, "graded": [f["key"] for f in graded]}


def judge(parsed, s) -> dict:
    g1 = gate(parsed, s)
    g2 = gate_v2(parsed, s, "v2")
    return {"accepted_v1": g1.accepted, "accepted_v2": g2.accepted, "values": dict(g1.values),
            "route_codes": sorted(set(g1.codes))}


def field_acc(claves, accepted: dict, values: dict, truth: dict, graded: list) -> tuple[int, int]:
    ok = n = 0
    for k in claves:
        if not accepted.get(k):
            continue
        for f in graded:
            t = truth[k][f]
            if t is None:
                continue
            n += 1
            ok += values.get(k, {}).get(f) == t
    return ok, n


def compare(rows: list[dict], R: dict) -> dict:
    claves, truth, ref, graded = R["claves"], R["truth"], R["ref"], R["graded"]
    new = {r["clave"]: r for r in rows}
    read_ok = [k for k in claves if k in new and new[k].get("parsed_ok")]
    acc_new = {k: bool(new.get(k, {}).get("accepted_v1")) for k in claves}
    acc_new2 = {k: bool(new.get(k, {}).get("accepted_v2")) for k in claves}
    acc_ref = {k: ref[k]["accepted"] for k in claves}
    vnew = {k: new.get(k, {}).get("values") or {} for k in claves}
    vref = {k: ref[k]["values"] for k in claves}
    same = sum(acc_new[k] == acc_ref[k] for k in claves)
    agree = tot = 0
    for k in claves:
        if k in read_ok and vref.get(k):
            for f in graded:
                tot += 1
                agree += vnew[k].get(f) == vref[k].get(f)
    a_new, n_new = field_acc(claves, acc_new, vnew, truth, graded)
    a_new2, n_new2 = field_acc(claves, acc_new2, vnew, truth, graded)
    a_ref, n_ref = field_acc(claves, acc_ref, vref, truth, graded)
    lat = [new[k]["secs"] for k in read_ok if new[k].get("secs")]
    return {"forms": len(claves), "read_ok": len(read_ok),
            "accepted_new_v1": sum(acc_new.values()), "accepted_new_v2": sum(acc_new2.values()),
            "accepted_ref": sum(acc_ref.values()), "same_decision_v1_vs_ref": same,
            "flips_new_accepts": sorted(k for k in claves if acc_new[k] and not acc_ref[k]),
            "flips_new_routes": sorted(k for k in claves if acc_ref[k] and not acc_new[k]),
            "field_acc_new_v1": [a_new, n_new], "field_acc_new_v2": [a_new2, n_new2], "field_acc_ref": [a_ref, n_ref],
            "digit_agreement_all_fields": [agree, tot],
            "mean_latency_s": round(sum(lat) / len(lat), 1) if lat else None}


def row_text(c: dict, model: str) -> str:
    def frac(p):
        return f"{p[0]}/{p[1]}" + (f" ({100 * p[0] / p[1]:.1f}%)" if p[1] else "")
    return (f"CONSISTENCY 43 pilot | {model} self-hosted vs Token Factory (spike v2) | read {c['read_ok']}/{c['forms']} | "
            f"accepted v1 {c['accepted_new_v1']} (v2 {c['accepted_new_v2']}) vs TF {c['accepted_ref']} | "
            f"same decision {c['same_decision_v1_vs_ref']}/{c['forms']} | accepted-field acc (adjudicated) "
            f"v1 {frac(c['field_acc_new_v1'])}, v2 {frac(c['field_acc_new_v2'])} vs TF {frac(c['field_acc_ref'])} | "
            f"digit agreement with TF {frac(c['digit_agreement_all_fields'])} | mean {c['mean_latency_s']} s/form")


def do_read(workers: int) -> Path:
    import endpoint_switch
    info = endpoint_switch.apply()
    if not info["switched"]:
        raise SystemExit("refusing: TWOHANDS_BASE_URL is not set (this check is for the self-hosted endpoint only)")
    s = schema.load()
    R = load_reference()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = RESULTS / f"consistency_43_{ts}.jsonl"
    missing = [k for k in R["claves"] if not (PAGES / f"{k}.jpg").is_file()]

    def work(k):
        if k in missing:
            return {"clave": k, "parsed_ok": False, "error": "no masked page", "accepted_v1": False, "accepted_v2": False}
        r = reader.read("gemma", PAGES / f"{k}.jpg", s)
        j = judge(r.get("parsed"), s)
        return {"clave": k, "model": r["model"], "prompt_sha256": reader.prompt_sha256(s), "secs": r["secs"],
                "finish_reason": r.get("finish_reason"), "usage": r.get("usage"), "error": r.get("error"),
                "parsed_ok": r.get("parsed") is not None, **j, "content": r.get("content")}

    with ThreadPoolExecutor(workers) as ex, open(out, "w", encoding="utf-8") as fh:
        for i, row in enumerate(ex.map(work, R["claves"]), 1):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{i}/43] {row['clave']} {'ACCEPT' if row['accepted_v1'] else 'route'} {row.get('secs')}s "
                  f"{row.get('error') or ''}", flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read"); r.add_argument("--workers", type=int, default=8)
    c = sub.add_parser("compare"); c.add_argument("path")
    a = ap.parse_args(argv)
    path = do_read(a.workers) if a.cmd == "read" else Path(a.path)
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    res = compare(rows, load_reference())
    model = next((r.get("model") for r in rows if r.get("model")), "gemma")
    res["model"], res["source"] = model, path.name
    path.with_suffix(".json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(row_text(res, model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
