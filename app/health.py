"""AMD endpoint chip for the header, from the core's own log of HTTP attempts (results/endpoint_health.jsonl).
Reading it makes no request to AMD.

Only the health PROBES and LIVE reads count (kind = probe | live, last 15 min). The measured batch's own 503s and
retries (kind = read) are deliberately ignored: they say the batch is being paced, not that a visitor's read fails.
  AMD live  (green)   the last probe / live read answered 200 within 60 s
  AMD slow  (amber)   the last one answered but took more than 60 s, or failed once
  AMD down, showing stored reads (grey)   the last 2 probes both failed
  AMD (grey)          nothing in the last 15 min
  AMD live · Gemma unavailable (amber)   the endpoint answers, but Gemma-4-31B-IT is withdrawn: missing from
                      GET /models (app/livemodel.py) or its latest probe / live / models row is "withdrawn"

"Withdrawn" is not "down": an HTTP 400 on a probe or live row (the probe's 5-token text call cannot be a malformed
request; the endpoint answers 400 "Requested model ... not supported" for a dropped model) and the "withdrawn" rows
app/livemodel.py writes (kind "models") mark that model as withdrawn and are left out of the up / slow / down rules.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from twohands import REPO

from twohands.amd import HEALTH  # noqa: E402  (same file the core writes; TWOHANDS_HEALTH_FILE overrides)
WINDOW_S = 15 * 60
SLOW_S = 60.0
SLOW_QWEN_LIVE_S = 180.0  # a whole Qwen read (it reasons first) takes 75-150 s on a healthy endpoint
KINDS = ("probe", "live")
GEMMA = "Gemma-4-31B-IT"


def withdrawn(row: dict) -> bool:
    st = row.get("status")
    return st == "withdrawn" or (st == 400 and row.get("kind") in KINDS)


def gemma_withdrawn(rows: list[dict], now: float) -> bool:
    """Gemma's latest probe / live / models row in the window says withdrawn."""
    g = [r for r in rows if r.get("model") == GEMMA and r.get("kind") in KINDS + ("models",) and _age(r, now) <= WINDOW_S]
    return bool(g) and withdrawn(g[-1])
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


def classify(rows: list[dict], now: float, gemma_listed=None) -> dict:
    """gemma_listed: True / False from the cached model list, None when unknown (then the log alone decides)."""
    v = _classify([r for r in rows if not withdrawn(r)], now)
    out = gemma_listed is False or (gemma_listed is None and gemma_withdrawn(rows, now))
    if not out or v["state"] == "down":
        return v
    if v["state"] == "busy":
        return {"state": "busy", "label": "AMD slow · Gemma unavailable",
                "detail": v["detail"] + " Gemma-4-31B-IT is not offered by the endpoint now; live reads use Qwen3.8-27B."}
    return {"state": "degraded", "label": "AMD live · Gemma unavailable",
            "detail": "The AMD endpoint answers, but Gemma-4-31B-IT is not in its model list now; live reads use "
                      "Qwen3.8-27B on AMD. Stored results were read by Gemma on AMD."}


def _classify(rows: list[dict], now: float) -> dict:
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
    slow = SLOW_QWEN_LIVE_S if last.get("kind") == "live" and str(last.get("model", "")).startswith("Qwen") else SLOW_S
    if last.get("status") != 200 or lat > slow:
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
    from app import livemodel
    listed = livemodel.chooser.gemma_listed(livemodel.chooser.listed(block=False))  # cached, never waits on AMD
    if _cache["v"] is not None and _cache["key"] == (key, listed) and now - _cache["at"] < 30:
        return _cache["v"]
    v = classify(_tail(), now, gemma_listed=listed)
    _cache.update(at=now, v=v, key=(key, listed))
    return v
