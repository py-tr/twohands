"""Which model the live read uses, from the AMD endpoint's own model list (GET /models via the core client,
cached 5 minutes).

  Gemma-4-31B-IT listed      -> Gemma, as in the measured run (no banner)
  Gemma-4-31B-IT not listed  -> Qwen3.8-27B with its own frozen prompt and parameters (the core reader's qwen path,
                                 as in the 300 run), plus an honest banner on the live panel
  list unavailable           -> the configured model (TWOHANDS_LIVE_MODEL, default gemma), no banner

When Gemma reappears in the list, the next refresh switches back by itself. A chat call that answers HTTP 400
"... not supported" marks the model withdrawn at once (no waiting for the 5-minute refresh).

Every fetch of the list writes one endpoint-health row for Gemma (kind "models"): status 200 when listed,
"withdrawn" when not. app/health.py reads those rows and the probe's 400s as "withdrawn", not as "down".
"""
from __future__ import annotations

import os
import re
import threading
import time
from typing import Callable, Optional

PRIMARY = "gemma"
FALLBACK = "qwen"
CONFIGURED = os.environ.get("TWOHANDS_LIVE_MODEL", PRIMARY)
TTL_S = 300.0
WITHDRAWN_SINCE = "2026-10-15 15:41 UTC"
BANNER = ("Gemma-4-31B-IT is currently not offered by the AMD endpoint (since " + WITHDRAWN_SINCE + "). "
          "This live read uses Qwen3.8-27B on AMD; the stored results above were read by Gemma on AMD.")
BANNER_TRY = ("Gemma-4-31B-IT is currently not offered by the AMD endpoint (since " + WITHDRAWN_SINCE + "). "
              "This live read uses Qwen3.8-27B on AMD; the stored results on this site were read by Gemma on AMD.")

_NOT_SUPPORTED = re.compile(r"\b400\b.*not supported", re.I | re.S)


def _names() -> dict:
    from twohands.reader import MODELS
    return MODELS


def _default_fetch() -> list[str]:
    from twohands import amd
    r = amd._req("/models", timeout=20)  # the core client: key from env / ../.env, never logged
    return [m.get("id") for m in (r.get("data") or []) if isinstance(m, dict) and m.get("id")]


def _default_record(model: str, status, secs: float, note: str = "") -> None:
    from twohands import amd
    amd.health(model, status, secs, kind="models", note=note)


def is_withdrawn_error(err: Optional[str]) -> bool:
    """An HTTP 400 whose body says the requested model is not supported (the endpoint dropped the model)."""
    return bool(err) and bool(_NOT_SUPPORTED.search(err))


class Chooser:
    def __init__(self, fetch: Optional[Callable[[], list]] = None, record: Optional[Callable] = None,
                 ttl: float = TTL_S, clock: Callable[[], float] = time.time):
        self.fetch = fetch or _default_fetch
        self.record = record or _default_record
        self.ttl = ttl
        self.clock = clock
        self._lock = threading.Lock()
        self._listed: Optional[list] = None  # None = never fetched / last fetch failed
        self._at = -1e18
        self._refreshing = False

    def _gemma(self) -> str:
        return _names()[PRIMARY]

    def refresh(self, fetch: Optional[Callable] = None, record: Optional[Callable] = None) -> Optional[list]:
        fetch, record = fetch or self.fetch, record or self.record
        t0 = self.clock()
        try:
            ids = list(fetch())
        except Exception:  # noqa: BLE001  endpoint down / key missing: keep the last known list
            with self._lock:
                self._at = self.clock()
                self._refreshing = False
                return self._listed
        with self._lock:
            self._listed, self._at, self._refreshing = ids, self.clock(), False
        g = self._gemma()
        try:
            record(g, 200 if g in ids else "withdrawn", self.clock() - t0,
                        "" if g in ids else "not in GET /models")
        except Exception:  # noqa: BLE001
            pass
        return ids

    def listed(self, block: bool = True) -> Optional[list]:
        """The cached model list; refreshed when older than the TTL (in the background when block=False)."""
        with self._lock:
            stale = self.clock() - self._at >= self.ttl
            if stale and not block:
                if not self._refreshing:
                    self._refreshing = True
                    # bind fetch / record now, so a late thread uses the ones in force when it was started
                    threading.Thread(target=self.refresh, args=(self.fetch, self.record), daemon=True).start()
                return self._listed
        return self.refresh() if stale else self._listed

    def peek(self) -> Optional[list]:
        with self._lock:
            return self._listed

    def mark_withdrawn(self, model_name: str) -> None:
        """A chat call said 400 '... not supported': drop it from the cached list now."""
        with self._lock:
            if self._listed is not None:
                self._listed = [m for m in self._listed if m != model_name]
            else:
                self._listed = [_names()[FALLBACK]]
            self._at = self.clock()
        try:
            self.record(model_name, "withdrawn", 0.0, "HTTP 400 not supported on a live read")
        except Exception:  # noqa: BLE001
            pass

    def gemma_listed(self, ids: Optional[list]) -> Optional[bool]:
        return None if ids is None else self._gemma() in ids

    def choose(self, block: bool = True) -> dict:
        """{key, model, fallback, banner}: the model the live read uses now."""
        ids = self.listed(block=block)
        names = _names()
        if CONFIGURED == PRIMARY and self.gemma_listed(ids) is False:
            return {"key": FALLBACK, "model": names[FALLBACK], "fallback": True, "banner": BANNER,
                    "banner_try": BANNER_TRY}
        return {"key": CONFIGURED, "model": names.get(CONFIGURED, CONFIGURED), "fallback": False, "banner": None,
                "banner_try": None}


chooser = Chooser()
