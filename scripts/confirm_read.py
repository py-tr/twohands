"""Read the Amendment 3 confirmation set (results/manifest_confirm100.json, pages prepared in
results/prepare_confirm100.jsonl) with one reader, writing the stable ``run.record`` rows to
results/calls_confirm100_<model>.jsonl (resumable: rows with an error are re-read on the next start).

    # Gemma 4 on the self-hosted MI300X (Amendment 4): the endpoint env of scripts/endpoint_switch.py
    TWOHANDS_BASE_URL=http://127.0.0.1:8000/v1 TWOHANDS_KEY=... TWOHANDS_MODEL_GEMMA=google/gemma-4-31B-it \\
      python scripts/confirm_read.py --model gemma --workers 8
    # Qwen on the Token Factory (no TWOHANDS_BASE_URL; the shared 6 req/min limiter, 2 in flight)
    python scripts/confirm_read.py --model qwen

Refuses unless PROTOCOL.md at HEAD contains Amendment 3 and the working copy of PROTOCOL.md is unchanged; on a
switched endpoint it also requires Amendment 4 at HEAD. Unlocated pages are recorded as routed (no call).

Stretch goal (throughput on a whole state, NOT pre-registered, no amendment guard):
    python scripts/confirm_read.py --model gemma --set state06 --workers 16
reads the pages staged by scripts/stage_state.py (results/prepare_state06.jsonl) into
results/stretch_state06_<model>.jsonl (deliberately not a calls_*.jsonl file: the app and make eval do not pick it up).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import endpoint_switch  # noqa: E402
from twohands import reader, run, schema  # noqa: E402

RESULTS = REPO / "results"


def protocol_has(*needles: str) -> bool:
    try:
        head = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:PROTOCOL.md"], capture_output=True, check=True).stdout
        dirty = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "HEAD", "--", "PROTOCOL.md"]).returncode != 0
    except Exception:  # noqa: BLE001
        return False
    return all(n.encode() in head for n in needles) and not dirty


def state_items(name: str) -> tuple[list[dict], dict]:
    """Items + prepare rows from results/prepare_<name>.jsonl (scripts/stage_state.py); last row per clave."""
    prepared = {r["clave"]: r for r in run.jsonl(RESULTS / f"prepare_{name}.jsonl")}
    if not prepared:
        raise SystemExit(f"no results/prepare_{name}.jsonl: run scripts/stage_state.py first")
    items = []
    for k, r in sorted(prepared.items()):
        lay = (r.get("info") or {}).get("layout") or "unknown"
        items.append({"clave": k, "layout": lay, "stratum": f"{name}|{lay}"})
    return items, prepared


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=("gemma", "qwen"), required=True)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--set", default="confirm100", help="confirm100 (Amendment 3) or stateNN (stage_state.py)")
    a = ap.parse_args(argv)
    info = endpoint_switch.apply()
    s = schema.load()
    # the Gemma 3 fallback (Amendment 4 variant B) never writes into the Gemma 4 file
    tag = "gemma3" if a.model == "gemma" and "gemma-3" in reader.MODELS["gemma"].lower() else a.model
    if a.set == "confirm100":
        need = ["## Amendment 3"] + (["## Amendment 4"] if info["switched"] else [])
        if not protocol_has(*need):
            print(f"refusing: PROTOCOL.md at HEAD must contain {need} with no uncommitted edits")
            return 3
        items = json.loads((RESULTS / "manifest_confirm100.json").read_text(encoding="utf-8"))["items"]
        prepared = {r["clave"]: r for r in run.jsonl(RESULTS / "prepare_confirm100.jsonl")}
        path = RESULTS / f"calls_confirm100_{tag}.jsonl"
    else:
        if not info["switched"]:
            print("refusing: the whole-state stretch run is for the self-hosted endpoint only (TWOHANDS_BASE_URL)")
            return 3
        items, prepared = state_items(a.set)
        path = RESULTS / f"stretch_{a.set}_{tag}.jsonl"
    print("endpoint:", info, flush=True)
    have = {r["clave"] for r in run.jsonl(path) if not r.get("error")}
    todo = [it for it in items if it["clave"] not in have]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{a.model} ({reader.MODELS[a.model]}): {len(have)} done, {len(todo)} to read; prompt {reader.prompt_sha256(s)[:12]}",
          flush=True)
    lock, n = threading.Lock(), {"i": 0}

    def work(it):
        prep = prepared.get(it["clave"], {"status": "missing", "reason": "not in prepare_confirm100.jsonl"})
        if prep.get("status") != "ok":
            rec = run.record(it, prep, a.model, s, None)
        else:
            rec = run.record(it, prep, a.model, s, reader.read(a.model, REPO / prep["image"], s))
        run.append(path, rec)
        with lock:
            n["i"] += 1
            print(f"[{n['i']}/{len(todo)}] {it['clave']} {'ACCEPT' if rec['accepted'] else 'route'} "
                  f"{rec.get('latency_s')}s {rec.get('finish_reason')} {(rec.get('error') or '')[:80]}", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(work, todo))
    rows = {r["clave"]: r for r in run.jsonl(path)}
    print(f"done: {len(rows)} rows, accepted (v1 gate) {sum(r['accepted'] for r in rows.values())}, "
          f"errors {sum(bool(r.get('error')) for r in rows.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
