"""OpenAI-compatible client for AMD Token Factory. Reads AMD_KEY / AMD_BASE_URL from the env or ../.env.
Never prints, logs or stores the key. Every request goes through the shared rate limiter; 429 honours
Retry-After (pausing every worker) with exponential backoff; 5xx and timeouts back off and retry."""
from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from pathlib import Path

from twohands import REPO
from twohands.ratelimit import parse_retry_after, shared

TIMEOUT_S = 300


def _cfg() -> tuple[str, str]:
    key, base = os.environ.get("AMD_KEY"), os.environ.get("AMD_BASE_URL")
    for envf in (REPO / ".env", REPO.parent / ".env"):
        if (key and base) or not envf.is_file():
            continue
        for line in envf.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                v = v.strip().strip('"').strip("'")
                if k.strip() == "AMD_KEY" and not key:
                    key = v
                if k.strip() == "AMD_BASE_URL" and not base:
                    base = v
    if not key or not base:
        raise RuntimeError("AMD_KEY / AMD_BASE_URL not configured")
    return key, base.rstrip("/")


def _req(path: str, body=None, timeout=TIMEOUT_S):
    key, base = _cfg()
    h = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, headers=h, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def usage() -> dict:
    """GET {base}/usage: daily_cost_used_usd, daily_cost_remaining_usd, daily_reset_at, rpm_limit, ..."""
    return _req("/usage", timeout=60)


class GaveUp(Exception):
    pass


def chat(body: dict, retries: int = 6, log=print) -> tuple[dict, int]:
    """POST /chat/completions through the shared limiter. Returns (response, attempts)."""
    lim = shared()
    for attempt in range(1, retries + 1):
        with lim.slot():
            try:
                return _req("/chat/completions", body), attempt
            except urllib.error.HTTPError as e:
                msg = e.read()[:200].decode("utf-8", "replace")
                code = e.code
                ra = parse_retry_after(e.headers.get("Retry-After"))
            except Exception as e:  # timeouts, connection resets
                msg, code, ra = f"{type(e).__name__}: {str(e)[:120]}", None, None
        if code is not None and code != 429 and code < 500:
            raise GaveUp(f"HTTP {code}: {msg}")
        wait = min(300.0, max(ra or 0.0, 5.0 * 2 ** (attempt - 1))) * (0.75 + 0.5 * random.random())
        if code == 429:
            lim.pause(wait)
        log(f"retry {attempt}/{retries} after {wait:.0f}s ({code or ''} {msg[:100]})")
        time.sleep(wait)
    raise GaveUp(f"gave up after {retries} attempts")
