"""AMD endpoint chip for the header, from the core's own log of HTTP attempts (results/endpoint_health.jsonl).
Reading it makes no request to AMD.

Only the health PROBES and LIVE reads count (kind = probe | live, last 15 min). The measured batch's own 503s and
retries (kind = read) are deliberately ignored: they say the batch is being paced, not that a visitor's read fails.
  AMD live  (green)   the last probe / live read answered 200 within 60 s
  AMD slow  (amber)   the last one answered but took more than 60 s, or failed once
  AMD down, showing stored reads (grey)   the last 2 probes both failed
  AMD (grey)          nothing in the last 15 min
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from twohands import REPO

HEALTH = REPO / "results" / "endpoint_health.jsonl"
WINDOW_S = 15 * 60
SLOW_S = 60.0
KINDS = ("probe", "live")
_cache: dict = {"at": 0.0, "v": None, "key": None}


def _tail(nbytes: int = 64000) -> list[dict]:
    try:
        with open(HEALTH, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - nbytes))
            lines = fh.read().decode("utf-8", "replace").splitlines()[1:]
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            pass
    return out


def _age(row: dict, now: float) -> float:
    try:
        return now - datetime.strptime(row["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (KeyError, ValueError, TypeError):
        return 1e12


def classify(rows: list[dict], now: float) -> dict:
    recent = [r for r in rows if r.get("kind") in KINDS and _age(r, now) <= WINDOW_S]
    if not recent:
        return {"state": "quiet", "label": "AMD", "detail": "No probe of the AMD endpoint in the last 15 minutes."}
    last = recent[-1]
    mins = int(_age(last, now) // 60)
    ago = "just now" if mins < 1 else f"{mins} min ago"
    probes = [r for r in recent if r.get("kind") == "probe"]
    if len(probes) >= 2 and all(p.get("status") != 200 for p in probes[-2:]):
        return {"state": "down", "label": "AMD down, showing stored reads",
                "detail": f"The last two probes of the AMD endpoint failed (last {ago}). Every form still opens from its measured read."}
    lat = last.get("latency_s") or 0
    if last.get("status") != 200 or lat > SLOW_S:
        return {"state": "busy", "label": "AMD slow",
                "detail": f"Last probe {ago}: " + (f"answered in {lat:.0f} s." if last.get("status") == 200 else "no answer.")
                          + " Live reads may queue longer; measured reads open instantly."}
    return {"state": "up", "label": "AMD live", "detail": f"Last probe of the AMD endpoint {ago}: answered in {lat:.1f} s."}


def status(now: float | None = None) -> dict:
    now = now or time.time()
    try:
        key = HEALTH.stat().st_mtime_ns
    except OSError:
        key = None
    if _cache["v"] is not None and _cache["key"] == key and now - _cache["at"] < 30:
        return _cache["v"]
    v = classify(_tail(), now)
    _cache.update(at=now, v=v, key=key)
    return v
