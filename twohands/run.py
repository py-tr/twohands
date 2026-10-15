"""Resumable runner for the pre-registered run (PROTOCOL.md).

    python -m twohands.run [--models gemma,qwen] [--max-daily-usd 0.80]

1. prepare: download each manifest acta to data/raw/img/ (gitignored), rectify + mask it into
   data/masked/<clave>.jpg, delete the raw file. Outcome per acta in results/prepare.jsonl.
2. read: Gemma over every prepared acta to completion, then Qwen. One row per form in
   results/calls_<model>.jsonl (stable record; see ``record``). Rows with an error are retried on resume.

Budget: the shared ``twohands.ratelimit`` limiter (TWOHANDS_RPM=6 req/min total, 2 in flight); 429 honours
Retry-After. GET /usage is read before the run and every 4 calls: if daily_cost_used_usd >= --max-daily-usd
the runner sleeps until daily_reset_at (16:00 UTC) + 3 min and continues. Status: results/run_status.json.
The API key is never printed or written.
"""
from __future__ import annotations

import argparse
import json
import os
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from twohands import REPO, amd, mask, reader, register, schema
from twohands.gate import gate

RESULTS = REPO / "results"
MASKED = REPO / "data" / "masked"
RAW = REPO / "data" / "raw" / "img"
LOG = RESULTS / "run.log"
_loglock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{now()} {msg}"
    with _loglock:
        print(line, flush=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def jsonl(path: Path) -> list[dict]:
    out = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # half-written last line of a killed run
    return out


def append(path: Path, row: dict, lock=threading.Lock()) -> None:
    with lock:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def rel(p: Path) -> str:
    return Path(os.path.relpath(p, REPO)).as_posix()


# ---------------------------------------------------------------- prepare
def prepare_one(it: dict) -> dict:
    k = it["clave"]
    dst = MASKED / f"{k}.jpg"
    if dst.exists():
        return {"clave": k, "status": "ok", "image": rel(dst), "cached": True}
    RAW.mkdir(parents=True, exist_ok=True)
    raw = RAW / f"{k}.jpg"
    err = None
    for i in range(3):
        try:
            req = urllib.request.Request(it["url"], headers={"User-Agent": "Mozilla/5.0 (two-hands research)"})
            raw.write_bytes(urllib.request.urlopen(req, timeout=90).read())
            err = None
            break
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(5 * (i + 1))
    if err:
        return {"clave": k, "status": "download_failed", "reason": err}
    try:
        page, info = mask.prepare(raw, it["layout"])
        mask.save(page, dst)
        return {"clave": k, "status": "ok", "image": rel(dst), "info": info}
    except register.NotLocated as e:
        return {"clave": k, "status": "not_located", "reason": str(e)}
    except Exception as e:  # noqa: BLE001 - unreadable file etc.
        return {"clave": k, "status": "unreadable", "reason": f"{type(e).__name__}: {str(e)[:120]}"}
    finally:
        for _ in range(5):  # raw (unmasked) images are never kept
            try:
                raw.unlink(missing_ok=True)
                break
            except OSError:
                time.sleep(1)
        if raw.exists():
            log(f"WARNING raw image could not be deleted: {rel(raw)}")


def prepare_all(items: list[dict]) -> dict:
    path = RESULTS / "prepare.jsonl"
    done = {r["clave"]: r for r in jsonl(path) if r.get("status") in ("ok", "not_located", "unreadable")}
    todo = [it for it in items if it["clave"] not in done]
    log(f"prepare: {len(done)} done, {len(todo)} to fetch")
    with ThreadPoolExecutor(2) as ex:
        for r in ex.map(prepare_one, todo):
            r["ts"] = now()
            append(path, r)
            if r["status"] != "ok":
                log(f"prepare {r['clave']}: {r['status']} {r.get('reason', '')}")
            if r["status"] in ("ok", "not_located", "unreadable"):
                done[r["clave"]] = r
    return done


# ---------------------------------------------------------------- read
def record(it: dict, prep: dict, model_key: str, s: dict, row: dict | None) -> dict:
    """The stable per-form record (one per acta per model)."""
    base = {"form_id": it["clave"], "clave": it["clave"], "layout": it["layout"], "stratum": it["stratum"],
            "schema": s["form"], "model": reader.MODELS[model_key], "model_key": model_key,
            "prompt_sha256": reader.prompt_sha256(s), "image": prep.get("image"), "ts": now()}
    if row is None:  # never sent: the page was not located / not readable / not downloadable
        reason = {"not_located": "form not located", "unreadable": "image unreadable",
                  "download_failed": "image not downloadable"}.get(prep.get("status"), prep.get("status"))
        return base | {"no_call": True, "accepted": False, "routed": True,
                       "route_reasons": [f"{reason}: {prep.get('reason', '')}"], "route_codes": ["no_read"],
                       "fields": {}, "identities": [], "failing_fields": [], "latency_s": None, "cost_usd": 0.0}
    g = gate(row.get("parsed"), s)
    fields = {f["key"]: {"label": g.labels.get(f["key"]), "n": g.values.get(f["key"]), "w": g.words.get(f["key"]),
                         "fix": f["key"] in g.fixes} for f in s["fields"]}
    u = row.get("usage") or {}
    reasons, codes, acc = list(g.reasons), set(g.codes), g.accepted
    if row.get("finish_reason") == "length":  # PROTOCOL 2.3: a truncated reply is never accepted
        reasons.insert(0, "reply truncated (finish_reason=length)"); codes.add("no_read"); acc = False
    if row.get("error"):
        reasons.insert(0, f"model call failed: {row['error'][:120]}"); codes.add("no_read"); acc = False
    return base | {"no_call": False, "accepted": acc, "routed": not acc, "route_reasons": reasons,
                   "route_codes": sorted(codes), "fields": fields, "identities": g.identities,
                   "failing_fields": g.failing_fields, "latency_s": row.get("secs"),
                   "cost_usd": u.get("cost"), "usage": u, "finish_reason": row.get("finish_reason"),
                   "attempts": row.get("attempts"), "error": row.get("error"), "parsed_ok": row.get("parsed") is not None,
                   "content": row.get("content")}


class Budget:
    def __init__(self, cap: float):
        self.cap, self.lock, self.n, self.used = cap, threading.Lock(), 0, None

    def check(self, force: bool = False) -> None:
        with self.lock:
            self.n += 1
            if not force and self.n % 4:
                return
            while True:
                try:
                    u = amd.usage()
                except Exception as e:  # noqa: BLE001
                    log(f"usage read failed: {type(e).__name__}")
                    return
                self.used = float(u.get("daily_cost_used_usd") or 0)
                if self.used < self.cap:
                    return
                reset = datetime.fromisoformat(str(u.get("daily_reset_at")).replace("Z", "+00:00"))
                wait = max(60.0, (reset - datetime.now(timezone.utc)).total_seconds() + 180)
                log(f"daily spend {self.used:.3f} >= {self.cap} USD: sleeping {wait / 3600:.1f} h until after reset {u.get('daily_reset_at')}")
                time.sleep(wait)


def read_model(model_key: str, items: list[dict], prepared: dict, s: dict, budget: Budget) -> None:
    path = RESULTS / f"calls_{model_key}.jsonl"
    for attempt_pass in range(12):  # API errors are retried in later passes (outages on the shared endpoint)
        have = {r["clave"] for r in jsonl(path) if not r.get("error")}
        todo = [it for it in items if it["clave"] not in have and it["clave"] in prepared]
        if not todo:
            break
        log(f"{model_key}: pass {attempt_pass + 1}, {len(have)} done, {len(todo)} to read")
        t0 = time.time()
        counter = {"n": 0}

        def work(it):
            prep = prepared[it["clave"]]
            if prep.get("status") != "ok":
                rec = record(it, prep, model_key, s, None)
            else:
                budget.check()
                row = reader.read(model_key, REPO / prep["image"], s)
                rec = record(it, prep, model_key, s, row)
            append(path, rec)
            counter["n"] += 1
            el = time.time() - t0
            eta = el / counter["n"] * (len(todo) - counter["n"]) / 3600
            log(f"{model_key} {it['clave']} {'ACCEPT' if rec['accepted'] else 'route'} "
                f"{rec.get('finish_reason')} {rec.get('latency_s')}s err={bool(rec.get('error'))} "
                f"[{counter['n']}/{len(todo)}, eta {eta:.1f} h] {'; '.join(rec['route_reasons'][:2])[:140]}")
            status(model_key, path, len(items), budget)
            if rec.get("error"):
                time.sleep(300)  # endpoint outage / 5xx storm: back off this worker for 5 min

        with ThreadPoolExecutor(2) as ex:
            list(ex.map(work, todo))


def status(model_key: str, path: Path, n: int, budget: Budget) -> None:
    rows = [r for r in jsonl(path) if not r.get("error")]
    st = {"ts": now(), "model": model_key, "done": len(rows), "n": n,
          "accepted": sum(r["accepted"] for r in rows), "daily_cost_used_usd": budget.used,
          "cost_usd_this_model": round(sum((r.get("cost_usd") or 0) for r in rows), 6)}
    (RESULTS / "run_status.json").write_text(json.dumps(st, indent=1), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="gemma,qwen")
    ap.add_argument("--max-daily-usd", type=float, default=0.80)
    ap.add_argument("--prepare-only", action="store_true")
    a = ap.parse_args(argv)
    RESULTS.mkdir(exist_ok=True)
    man = json.loads((RESULTS / "manifest.json").read_text(encoding="utf-8"))
    items = man["items"]
    s = schema.load()
    log(f"run start: {len(items)} actas, models {a.models}, prompt {reader.prompt_sha256(s)[:12]}, pid {os.getpid()}")
    prepared = prepare_all(items)
    # download failures are retried once more, then recorded as routed (never replaced)
    if any(it["clave"] not in prepared for it in items):
        prepared = prepare_all(items)
        for r in jsonl(RESULTS / "prepare.jsonl"):
            prepared.setdefault(r["clave"], r)
    if a.prepare_only:
        return 0
    budget = Budget(a.max_daily_usd)
    budget.check(force=True)
    for m in a.models.split(","):
        read_model(m.strip(), items, prepared, s, budget)
    log("run complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
