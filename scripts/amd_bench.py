"""The AMD evidence block, computed from our own logs: what Gemma did on the AMD endpoint in the pre-registered 300 run.
No model call, no network.

    python scripts/amd_bench.py           # writes results/amd_benchmark.json and results/amd_benchmark.md
    python scripts/amd_bench.py --check   # the files and the docs that quote them match the logs (make eval)

Inputs: results/calls_gemma.jsonl (last row per form: wall time per form `latency_s`, `usage` tokens and cost,
`finish_reason`), results/endpoint_health.jsonl (one row per HTTP attempt, written by twohands/amd.py: status and
the HTTP round trip of that attempt, measured inside the limiter slot, so without our pacing). Only health rows of
Gemma `read` requests inside the 300 run's time window are used. The capacity line comes from the throughput sweep
(results/throughput_sweep.jsonl, scripts/throughput_sweep.py), whose json/md are checked here too.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

R = REPO / "results"
CALLS, HEALTH = R / "calls_gemma.jsonl", R / "endpoint_health.jsonl"
OUT_J, OUT_M = R / "amd_benchmark.json", R / "amd_benchmark.md"
MODEL = "Gemma-4-31B-IT"
NATIONAL = 169_005   # PREP 2024 CSV, presidential tally sheets (app/numbers.py CITED national_forms)
# docs that quote the block, and the keys whose sentence each must contain word for word
DOCS = {"docs/AMD.md": ("server", "sweep", "cost", "wall"), "README.md": ("server", "sweep", "cost", "latency"),
        "submission/lablab.md": ("server", "sweep", "cost", "wall", "latency")}


def rows(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def compute() -> dict:
    last = {}
    for r in rows(CALLS):
        last[r["clave"]] = r
    ok = [r for r in last.values() if r.get("parsed_ok")]
    t0, t1 = min(r["ts"] for r in ok), max(r["ts"] for r in ok)
    h = [x for x in rows(HEALTH) if x.get("model") == MODEL and x.get("kind") == "read" and t0 <= x["ts"] <= t1]
    http = [x["latency_s"] for x in h if x.get("status") == 200]
    failed = [x for x in h if x.get("status") != 200]
    wall = [r["latency_s"] for r in ok]
    tin = [r["usage"]["prompt_tokens"] for r in ok]
    tout = [r["usage"]["completion_tokens"] for r in ok]
    img = [r["usage"].get("prompt_tokens_details", {}).get("image_tokens") for r in ok]
    cost = [r["cost_usd"] for r in ok if r.get("cost_usd")]
    cpf = st.mean(cost)
    d = {"model": MODEL, "reads": len(ok), "forms": len(last), "window": [t0, t1],
         "http_200": len(http), "http_failed_attempts": len(failed),
         "server_mean_s": round(st.mean(http), 1), "server_median_s": round(st.median(http), 1),
         "wall_mean_s": round(st.mean(wall), 1), "wall_median_s": round(st.median(wall), 1),
         "tokens_in_mean": round(st.mean(tin)), "tokens_out_mean": round(st.mean(tout)),
         "image_tokens": sorted(set(img)),
         "out_tok_per_s": round(st.mean(tout) / st.mean(http), 1),
         "tok_per_s": round((st.mean(tin) + st.mean(tout)) / st.mean(http), 1),
         "finish_stop": sum(1 for r in ok if r.get("finish_reason") == "stop"),
         "cost_per_form": round(cpf, 6), "cost_per_1000": round(1000 * cpf, 2),
         "national_forms": NATIONAL, "national_usd": round(cpf * NATIONAL)}
    from scripts import throughput_sweep
    sw = throughput_sweep.summarize()
    d["sweep"] = {k: sw[k] for k in ("measured", "best_in_flight", "best_forms_per_min", "best_http_p50_s",
                                     "best_usd_per_form", "national_hours", "arithmetic", "reads", "usd_total", "line")}
    best = next(lv for lv in sw["levels"] if lv["in_flight"] == sw["best_in_flight"])
    d["sweep"].update(best_http_p95_s=best["http_p95_s"], best_requests=best["forms"] + best["retries"])
    from app import colima
    F = colima.facts() or {}
    d["colima_sheets"] = F.get("read")
    d["colima_hours"] = round(F["read"] / min(sw["best_forms_per_min"], sw["rpm_limit"]) / 60, 1) if F else None
    d["lines"] = lines(d)
    return d


def lines(d: dict) -> dict:
    return {
        "server": (f"Server time per form: {d['server_mean_s']:.0f} s mean, {d['server_median_s']:.0f} s median (HTTP "
                   f"round trip, shared endpoint, {d['http_200']} reads of {MODEL}, {d['tokens_in_mean']:,} "
                   f"tokens in, {d['tokens_out_mean']:,} out)."),
        "sweep": d["sweep"]["line"],
        "cost": (f"About ${d['national_usd']} of AMD compute to read all {d['national_forms']:,} national presidential "
                 f"tally sheets with {MODEL} (${d['cost_per_form']:.6f} per form, the mean billed cost of "
                 f"{d['reads']} reads)."),
        "latency": (f"Latency per read (shared AMD endpoint, queue included): {d['sweep']['best_http_p50_s']:.0f} s p50, "
                    f"{d['sweep']['best_http_p95_s']:.0f} s p95 at {d['sweep']['best_in_flight']} in flight "
                    f"({d['sweep']['best_requests']} of the sweep's {d['sweep']['reads']} requests); "
                    f"{d['server_median_s']:.0f} s median over the {d['http_200']} requests of the 300 run; "
                    f"{d['out_tok_per_s']} output tokens/s per request ({d['tokens_out_mean']:,} out, "
                    f"{d['server_mean_s']:.0f} s mean round trip). Fine for an audit after the count, where nobody waits "
                    f"on one sheet: a state the size of Colima ({d['colima_sheets']:,} sheets) in about "
                    f"{d['colima_hours']} hours."),
        "wall": (f"The 300 run's {d['wall_mean_s']:.0f} s per form was wall clock under my own pacing (2 in flight), not "
                 f"GPU time; {d['server_mean_s']:.0f} s of it was the endpoint's round trip, queue included."),
    }


def markdown(d: dict) -> str:
    L = d["lines"]
    return "\n".join([
        f"# AMD benchmark: {MODEL} on the AMD Token Factory, pre-registered 300 run", "",
        "Generated by `python scripts/amd_bench.py` from `results/calls_gemma.jsonl` and `results/endpoint_health.jsonl`; "
        "checked by `make eval`. No model call.", "",
        f"Run window: {d['window'][0]} to {d['window'][1]} UTC. Forms: {d['forms']}; reads answered and parsed: "
        f"{d['reads']} (11 pages were never sent).", "",
        "| measure | value | n |", "|---|---|---|",
        f"| Server time per form (HTTP round trip of the answered request) | {d['server_mean_s']} s mean, "
        f"{d['server_median_s']} s median | {d['http_200']} |",
        f"| Wall clock per form (incl. our limiter, 2 in flight) | {d['wall_mean_s']} s mean, {d['wall_median_s']} s median | {d['reads']} |",
        f"| Tokens per form | {d['tokens_in_mean']:,} in ({', '.join(str(x) for x in d['image_tokens'])} image tokens), "
        f"{d['tokens_out_mean']:,} out | {d['reads']} |",
        f"| Capacity (throughput sweep, {d['sweep']['measured'][0]} to {d['sweep']['measured'][1]} UTC) | "
        f"{d['sweep']['best_forms_per_min']} forms/min at {d['sweep']['best_in_flight']} in flight, "
        f"{d['sweep']['best_http_p50_s']} s median; {d['sweep']['arithmetic']} | {d['sweep']['reads']} |",
        f"| Replies finished with `stop` | {d['finish_stop']} of {d['reads']} | {d['reads']} |",
        f"| Failed HTTP attempts in the window (retried) | {d['http_failed_attempts']} | |",
        f"| Cost per form (billed, `usage.cost`) | ${d['cost_per_form']:.6f}; ${d['cost_per_1000']:.2f} per 1,000 | {d['reads']} |",
        f"| All {d['national_forms']:,} national presidential tally sheets | about ${d['national_usd']} | computed |", "",
        L["server"], "", L["sweep"], "", L["latency"], "", L["cost"], "", L["wall"], "",
        "The endpoint does not report the GPU model, so no card is named. The capacity sweep "
        "(`results/throughput_sweep.md`) is the shared endpoint under its rate limit, queueing included: not GPU time.", ""])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    d = compute()
    if not a.check:
        OUT_J.write_text(json.dumps(d, indent=1), encoding="utf-8")
        OUT_M.write_text(markdown(d), encoding="utf-8")
        print(f"amd_bench: wrote {OUT_J.name}, {OUT_M.name}")
        return 0
    bad = []
    try:
        if json.loads(OUT_J.read_text(encoding="utf-8")) != json.loads(json.dumps(d)):
            bad.append("results/amd_benchmark.json differs from the logs")
        if OUT_M.read_text(encoding="utf-8") != markdown(d):
            bad.append("results/amd_benchmark.md differs from the logs")
    except OSError as e:
        bad.append(str(e))
    from scripts import throughput_sweep
    if throughput_sweep.build(check=True):
        bad.append("results/throughput_sweep.json/.md differ from results/throughput_sweep.jsonl")
    for doc, keys in DOCS.items():
        s = " ".join((REPO / doc).read_text(encoding="utf-8").replace("**", "").split())
        for k in keys:
            if d["lines"][k] not in s:
                bad.append(f"{doc}: missing the current '{k}' line")
    print(f"amd_bench --check: {len(bad)} mismatches" + "".join(f"\n  - {b}" for b in bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
