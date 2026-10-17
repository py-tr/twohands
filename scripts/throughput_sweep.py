"""Capacity sweep of the production Gemma read on the shared AMD Token Factory endpoint: forms per minute at 1, 2, 4
and 6 requests in flight. A benchmark only: it never writes calls_*.jsonl and never touches a score.

    python scripts/throughput_sweep.py run       # ~44 reads (about $0.007): results/throughput_sweep.jsonl, then build
    python scripts/throughput_sweep.py build     # results/throughput_sweep.json + .md from the jsonl (no model call)
    python scripts/throughput_sweep.py --check   # the json/md match the jsonl (scripts/amd_bench.py --check runs it too)

The read is the production one, as in the pre-registered 300 run: twohands.reader.read (frozen prompt, page + tiles of
the masked page, Gemma-4-31B-IT, temperature 0, max_tokens 2000) through twohands.amd.chat (key from the repo loader,
the cross-process limiter in cache/ratelimit.json shared with every other job on this machine, budget role bulk,
retries with backoff). Pages: masked pages of the 300 run (data/masked/<clave>.jpg, rows of results/calls_gemma.jsonl
with a parsed read), drawn once with a fixed seed, no page read twice. Never an unmasked image.

Every number is labelled: shared endpoint, measured at the UTC times recorded, includes queueing (the endpoint's own
queue and our limiter's), not GPU time, not a self-hosted benchmark.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

R = REPO / "results"
OUT_L, OUT_J, OUT_M = R / "throughput_sweep.jsonl", R / "throughput_sweep.json", R / "throughput_sweep.md"
LEVELS = [(1, 6), (2, 8), (4, 12), (6, 18)]   # (requests in flight, forms)
SEED = 20261017
NATIONAL = 169_005   # PREP 2024 CSV, presidential tally sheets (app/numbers.py CITED national_forms)
RPM_LIMIT = 20       # the endpoint's limit per key, requests a minute
LABEL = "shared endpoint, includes queueing; not GPU time; not a self-hosted benchmark"


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jsonl(p: Path) -> list[dict]:
    out = []
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def pages() -> list[str]:
    """Masked pages of the 300 run with a parsed read, in a fixed seeded order."""
    last = {}
    for r in jsonl(R / "calls_gemma.jsonl"):
        last[r["clave"]] = r
    imgs = sorted(r["image"] for r in last.values() if r.get("parsed_ok") and r.get("image"))
    masked = (REPO / "data" / "masked").resolve()
    imgs = [i for i in imgs if (REPO / i).resolve().parent == masked and (REPO / i).is_file()]
    random.Random(SEED).shuffle(imgs)
    return imgs


def run() -> int:
    from twohands import amd, reader, schema
    import twohands.ratelimit as rl
    s = schema.load()
    state = rl.live_flag().with_suffix(".json")   # the production cross-process state file (cache/ratelimit.json)
    imgs = pages()
    assert len(imgs) >= sum(n for _, n in LEVELS), "not enough masked pages"
    done = {r["image"] for r in jsonl(OUT_L)}
    try:
        u0 = amd.usage()
        print(f"usage before: used {u0.get('daily_cost_used_usd')} USD, rpm_limit {u0.get('rpm_limit')}", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"usage read failed: {type(e).__name__}", flush=True)
    lock = threading.Lock()
    i0 = 0
    for c, n in LEVELS:
        batch, i0 = imgs[i0:i0 + n], i0 + n
        todo = [b for b in batch if b not in done]
        if not todo:
            continue
        rl.reset_shared(rl.FileRateLimiter(state, rl.RPM, c, live_rpm=rl.LIVE_RPM))
        print(f"level {c} in flight: {len(todo)} forms, start {iso(time.time())}", flush=True)

        def one(img, c=c):
            retries: list = []
            timing: dict = {}
            seen: dict = {}

            def chat(body):
                assert body["model"] == "Gemma-4-31B-IT" and body["temperature"] == 0 and body["max_tokens"] == 2000
                seen["images"] = sum(1 for x in body["messages"][1]["content"] if x["type"] == "image_url")
                return amd.chat(body, log=retries.append, kind="sweep", timing=timing)
            t_sub = time.time()
            row = reader.read("gemma", REPO / img, s, chat=chat)
            t_end = time.time()
            u = row.get("usage") or {}
            codes = [m.group(1) for m in (re.search(r"\((\d{3})", x) for x in retries) if m]
            rec = {"level": c, "image": img, "prompt_sha256": reader.prompt_sha256(s), "images_sent": seen.get("images"),
                   "submitted": iso(t_sub), "end": iso(t_end), "t_submit": round(t_sub, 2), "t_end": round(t_end, 2),
                   "http_start": iso(t_end - timing["http_s"]) if "http_s" in timing else None,
                   "status": 200 if not row.get("error") else "error", "error": row.get("error"),
                   "http_s": timing.get("http_s"), "wall_s": round(t_end - t_sub, 1),
                   "attempts": row.get("attempts"), "retries": len(retries), "n_429": codes.count("429"),
                   "retry_codes": codes, "tokens_in": u.get("prompt_tokens"), "tokens_out": u.get("completion_tokens"),
                   "cost_usd": u.get("cost"), "finish_reason": row.get("finish_reason"),
                   "parsed_ok": row.get("parsed") is not None}
            with lock, open(OUT_L, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
            print(f"  c={c} {Path(img).stem} {rec['status']} http {rec['http_s']}s wall {rec['wall_s']}s "
                  f"out {rec['tokens_out']} ${rec['cost_usd']} retries {rec['retries']}", flush=True)
        with ThreadPoolExecutor(c) as ex:
            list(ex.map(one, todo))
    try:
        print(f"usage after: used {amd.usage().get('daily_cost_used_usd')} USD", flush=True)
    except Exception:  # noqa: BLE001
        pass
    return build()


def pct(xs: list[float], p: float) -> float:
    """Nearest-rank percentile (with 6 to 18 values, p95 is the slowest or second slowest)."""
    xs = sorted(xs)
    return xs[max(0, math.ceil(p / 100 * len(xs)) - 1)]


def summarize(rows: list[dict] | None = None) -> dict:
    rows = jsonl(OUT_L) if rows is None else rows
    levels = []
    for c, _ in LEVELS:
        rs = [r for r in rows if r["level"] == c]
        if not rs:
            continue
        ok = [r for r in rs if r["status"] == 200]
        t0, t1 = min(r["t_submit"] for r in rs), max(r["t_end"] for r in rs)
        span = t1 - t0
        cost = [r["cost_usd"] for r in ok if r.get("cost_usd")]
        reqs = len(rs) + sum(r["retries"] for r in rs)
        levels.append({
            "in_flight": c, "forms": len(rs), "answered": len(ok), "window": [iso(t0), iso(t1)],
            "span_s": round(span, 1), "forms_per_min": round(len(ok) / span * 60, 2),
            "requests_per_min": round(reqs / span * 60, 2),
            "http_p50_s": round(pct([r["http_s"] for r in ok], 50), 1),
            "http_p95_s": round(pct([r["http_s"] for r in ok], 95), 1),
            "wall_p50_s": round(pct([r["wall_s"] for r in ok], 50), 1),
            "wall_p95_s": round(pct([r["wall_s"] for r in ok], 95), 1),
            "error_rate": round(1 - len(ok) / len(rs), 3), "retries": sum(r["retries"] for r in rs),
            "n_429": sum(r["n_429"] for r in rs),
            "tokens_in_mean": round(sum(r["tokens_in"] for r in ok) / len(ok)),
            "tokens_out_mean": round(sum(r["tokens_out"] for r in ok) / len(ok)),
            "usd_per_form": round(sum(cost) / len(cost), 6), "usd_total": round(sum(cost), 6),
            "parsed_ok": sum(r["parsed_ok"] for r in ok)})
    if not levels:
        return {}
    clean = [x for x in levels if x["error_rate"] == 0] or levels
    best = max(clean, key=lambda x: x["forms_per_min"])
    fpm = min(best["forms_per_min"], RPM_LIMIT)   # one request per form: forms/min is requests/min, capped at 20
    hours = NATIONAL / fpm / 60
    starts = sorted(r["t_end"] - r["http_s"] for r in rows if r.get("http_s") is not None)
    peak = max((sum(1 for x in starts if a <= x < a + 60) for a in starts), default=0)
    d = {"label": LABEL, "measured": [levels[0]["window"][0], levels[-1]["window"][1]], "levels": levels,
         "reads": sum(x["forms"] for x in levels), "peak_starts_60s": peak, "usd_total": round(sum(x["usd_total"] for x in levels), 6),
         "images_sent": sorted({r["images_sent"] for r in rows if r.get("images_sent")}),
         "best_in_flight": best["in_flight"], "best_forms_per_min": best["forms_per_min"],
         "best_http_p50_s": best["http_p50_s"], "best_usd_per_form": best["usd_per_form"],
         "national_forms": NATIONAL, "rpm_limit": RPM_LIMIT, "national_hours": round(hours, 1),
         "national_days": round(hours / 24, 1), "national_usd": round(NATIONAL * best["usd_per_form"]),
         "arithmetic": (f"{NATIONAL:,} forms / {fpm} forms a minute = {NATIONAL / fpm:,.0f} min = {hours:,.1f} h "
                        f"(one request per form, so {fpm} requests a minute, under the {RPM_LIMIT} a minute limit)")}
    d["line"] = line(d)
    return d


COLIMA = 982   # Colima's located presidential sheets (PROTOCOL.md Amendment 8b)


def line(d: dict) -> str:
    m0, m1 = d["measured"]
    return (f"Measured capacity (shared endpoint, {m0[:10]} {m0[11:16]}-{m1[11:16]} UTC, queueing included, not GPU "
            f"time, not self-hosted): {d['best_in_flight']} in flight, {d['best_forms_per_min']:.1f} forms/minute, "
            f"{d['best_http_p50_s']:.0f} s median, ${d['best_usd_per_form']:.6f}/form; one shared key reads a state the size "
            f"of Colima ({COLIMA:,} sheets) in about {COLIMA / min(d['best_forms_per_min'], d['rpm_limit']) / 60:.1f} hours; "
            f"national figures in results/throughput_sweep.json.")


def markdown(d: dict) -> str:
    rows = ["| in flight | forms | window (UTC) | forms/min | req/min | HTTP p50 / p95 s | wall p50 / p95 s | errors | "
            "retries (429) | $/form |", "|---|---|---|---|---|---|---|---|---|---|"]
    for x in d["levels"]:
        rows.append(f"| {x['in_flight']} | {x['forms']} | {x['window'][0][11:19]} to {x['window'][1][11:19]} | "
                    f"{x['forms_per_min']:.2f} | {x['requests_per_min']:.2f} | {x['http_p50_s']} / {x['http_p95_s']} | "
                    f"{x['wall_p50_s']} / {x['wall_p95_s']} | {x['error_rate']:.0%} | {x['retries']} ({x['n_429']}) | "
                    f"${x['usd_per_form']:.6f} |")
    return "\n".join([
        "# Throughput sweep: Gemma-4-31B-IT on the shared AMD Token Factory endpoint", "",
        f"**{d['label'][0].upper() + d['label'][1:]}.** Measured {d['measured'][0]} to {d['measured'][1]} UTC.", "",
        "Generated by `python scripts/throughput_sweep.py build` from `results/throughput_sweep.jsonl`; checked by "
        "`make eval` (`scripts/amd_bench.py --check`). A benchmark only: these reads are never scored and never "
        "written to `calls_*.jsonl`.", "",
        f"The production read of the 300 run: frozen prompt, masked page + tiles ({', '.join(map(str, d['images_sent']))} "
        "images per request), Gemma-4-31B-IT, temperature 0, max_tokens 2000, through `twohands.amd.chat` and the "
        "cross-process limiter shared with the other job on this key. Masked pages of the 300 run only, a fixed seeded "
        "draw, no page twice. HTTP = round trip of the answered attempt (the endpoint's queue included); wall = from "
        "submit to answer (our limiter's wait included). Forms/min = answered forms / (last answer - first submit), "
        "so the start and the tail of each level count. p95 is nearest rank over 6 to 18 values.", "",
        *rows, "",
        f"Best level: {d['best_in_flight']} in flight. Hours for the {d['national_forms']:,} national presidential tally "
        f"sheets at that level: {d['arithmetic']}; about {d['national_days']} days. Cost at the measured "
        f"${d['best_usd_per_form']:.6f} a form: about ${d['national_usd']}.", "",
        f"Sweep total: {d['reads']} reads, ${d['usd_total']:.4f} billed. Most answered requests of ours started in any 60 s: "
        f"{d['peak_starts_60s']} (client limit 12 a minute for every non-live job on the key, the endpoint's {RPM_LIMIT}).", "",
        d["line"], ""])


def build(check: bool = False) -> int:
    d = summarize()
    if not check:
        OUT_J.write_text(json.dumps(d, indent=1), encoding="utf-8")
        OUT_M.write_text(markdown(d), encoding="utf-8")
        print(f"throughput_sweep: wrote {OUT_J.name}, {OUT_M.name}")
        return 0
    bad = []
    try:
        if json.loads(OUT_J.read_text(encoding="utf-8")) != json.loads(json.dumps(d)):
            bad.append("results/throughput_sweep.json differs from the jsonl")
        if OUT_M.read_text(encoding="utf-8") != markdown(d):
            bad.append("results/throughput_sweep.md differs from the jsonl")
    except OSError as e:
        bad.append(str(e))
    print(f"throughput_sweep --check: {len(bad)} mismatches" + "".join(f"\n  - {b}" for b in bad))
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", choices=["run", "build"], default="build")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        return build(check=True)
    return run() if a.cmd == "run" else build()


if __name__ == "__main__":
    sys.exit(main())
