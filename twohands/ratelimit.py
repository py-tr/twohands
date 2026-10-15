"""One shared rate limiter for every request to the model endpoint.

Copied from Ice Clock (tested there). The AMD Token Factory key is shared by several agents, so Two Hands
keeps itself to RPM requests/min and CONCURRENCY in flight; all callers in a process share ONE budget.
``RateLimiter`` is a token bucket (``rpm`` tokens per minute, at most ``burst`` saved
up) plus a semaphore (``concurrency`` requests in flight).  A 429 with Retry-After calls
``pause(seconds)``: every thread then waits until that moment, not only the one that was refused.

    with shared().slot():
        session.post(...)

``shared()`` is the process-wide instance (env TWOHANDS_RPM, default 6; TWOHANDS_CONCURRENCY, default 2).  The clock and sleep functions are
injectable so tests never sleep.
"""
from __future__ import annotations

import contextlib
import os
import random
import threading
import time
from typing import Callable, Iterator, Optional




class RateLimiter:
    def __init__(self, rpm: float = 18.0, concurrency: int = 4, burst: float = 2.0,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        if rpm <= 0:
            raise ValueError("rpm must be > 0")
        self.rpm = float(rpm)
        self.concurrency = max(1, int(concurrency))
        self.burst = max(1.0, float(burst))
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._sem = threading.BoundedSemaphore(self.concurrency)
        self._tokens = self.burst
        self._last = clock()
        self._paused_until = 0.0
        self.acquired = 0
        self.waited_s = 0.0

    @property
    def interval_s(self) -> float:
        return 60.0 / self.rpm

    def _refill(self, now: float) -> None:
        self._tokens = min(self.burst, self._tokens + (now - self._last) / self.interval_s)
        self._last = now

    def acquire(self) -> float:
        """Block until one request may start (token + not paused). Returns seconds waited.
        Does NOT take a concurrency slot: use ``slot()`` for that."""
        waited = 0.0
        while True:
            with self._lock:
                now = self._clock()
                self._refill(now)
                wait = 0.0
                if now < self._paused_until:
                    wait = self._paused_until - now
                elif self._tokens >= 1.0:
                    self._tokens -= 1.0
                    self.acquired += 1
                    self.waited_s += waited
                    return waited
                else:
                    wait = (1.0 - self._tokens) * self.interval_s
            wait = max(wait, 0.01)
            self._sleep(wait)
            waited += wait

    def pause(self, seconds: float, jitter: float = 0.2) -> float:
        """Nobody starts a request for ``seconds`` (+ up to ``jitter`` x seconds). Returns the pause applied.
        Also drains the bucket so the restart is paced, not a burst."""
        s = max(0.0, float(seconds)) * (1.0 + random.random() * max(0.0, jitter))
        with self._lock:
            self._paused_until = max(self._paused_until, self._clock() + s)
            self._tokens = 0.0
        return s

    @contextlib.contextmanager
    def slot(self) -> Iterator[float]:
        """Concurrency slot + rate token for one request."""
        self._sem.acquire()
        try:
            yield self.acquire()
        finally:
            self._sem.release()


class FileRateLimiter(RateLimiter):
    """Cross-process pacing: one request start per 60/rpm s for EVERY process on this machine that uses the
    same state file (the batch run and the web app's live button). State = {"next": t, "paused_until": t}
    in a JSON file guarded by an O_EXCL lock file; in-flight concurrency stays per process."""

    def __init__(self, path, rpm: float = 6.0, concurrency: int = 2, stale_lock_s: float = 30.0) -> None:
        super().__init__(rpm=rpm, concurrency=concurrency, burst=1.0)
        from pathlib import Path
        self.path = Path(path)
        self.lock = self.path.with_suffix(".lock")
        self.stale = stale_lock_s
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _locked(self, fn):
        import json as _json
        while True:
            try:
                fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.lock) > self.stale:
                        os.remove(self.lock)  # a crashed holder
                        continue
                except OSError:
                    pass
                time.sleep(0.05)
        try:
            try:
                st = _json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                st = {"next": 0.0, "paused_until": 0.0}
            out = fn(st)
            self.path.write_text(_json.dumps(st), encoding="utf-8")
            return out
        finally:
            os.close(fd)
            try:
                os.remove(self.lock)
            except OSError:
                pass

    def acquire(self) -> float:
        waited = 0.0
        while True:
            def take(st):
                now = time.time()
                start = max(st.get("next", 0.0), st.get("paused_until", 0.0))
                if now >= start:
                    st["next"] = now + self.interval_s
                    return 0.0
                return start - now
            w = self._locked(take)
            if w <= 0:
                self.acquired += 1
                self.waited_s += waited
                return waited
            w = min(w, 5.0)
            self._sleep(w)
            waited += w

    def pause(self, seconds: float, jitter: float = 0.2) -> float:
        s = max(0.0, float(seconds)) * (1.0 + random.random() * max(0.0, jitter))
        def setp(st):
            st["paused_until"] = max(st.get("paused_until", 0.0), time.time() + s)
        self._locked(setp)
        return s


RPM = float(os.environ.get("TWOHANDS_RPM", "6"))
CONCURRENCY = int(os.environ.get("TWOHANDS_CONCURRENCY", "2"))
_shared: Optional[RateLimiter] = None
_shared_lock = threading.Lock()


def shared() -> RateLimiter:
    """The process-wide limiter (one per process: batch, bench and the sweep all go through it)."""
    global _shared
    with _shared_lock:
        if _shared is None:
            from pathlib import Path
            state = os.environ.get("TWOHANDS_RATE_FILE") or str(Path(__file__).resolve().parent.parent / "cache" / "ratelimit.json")
            _shared = FileRateLimiter(state, RPM, CONCURRENCY)
        return _shared


def reset_shared(limiter: Optional[RateLimiter] = None) -> None:
    """Replace (tests) or drop the process-wide limiter."""
    global _shared
    with _shared_lock:
        _shared = limiter


def parse_retry_after(value, default: Optional[float] = None) -> Optional[float]:
    """Retry-After header -> seconds (delta-seconds form; an HTTP-date is parsed too). None/default if absent."""
    if value is None or str(value).strip() == "":
        return default
    v = str(value).strip()
    try:
        return max(0.0, float(v))
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime
        from datetime import datetime, timezone
        dt = parsedate_to_datetime(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (dt - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError, IndexError):
        return default
