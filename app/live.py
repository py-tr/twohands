"""Live read on AMD: one form, one request, streamed to the browser as server-sent events.

Safety rails (the AMD Token Factory key is shared with the core's batch job: 20 req/min, 8 concurrent, $1/day):
  * ONE live read at a time, site-wide (a process lock; a second click gets "busy").
  * Every request goes through the core client (twohands.amd.chat), i.e. the core's shared rate limiter.
  * Budget guard before every read: the endpoint's own /usage (daily_cost_remaining_usd must stay above
    LIVE_MIN_REMAINING_USD so the batch job keeps its headroom) AND a local daily cap on reads and dollars.
  * Only a masked page (data/masked/**) is ever sent; a form without one cannot be read live.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from app import store as storemod

LIVE_MODEL = os.environ.get("TWOHANDS_LIVE_MODEL", "gemma")
MIN_REMAINING_USD = float(os.environ.get("LIVE_MIN_REMAINING_USD", "0.25"))
MAX_READS_PER_DAY = int(os.environ.get("LIVE_MAX_READS_PER_DAY", "40"))
MAX_USD_PER_DAY = float(os.environ.get("LIVE_MAX_USD_PER_DAY", "0.05"))
LIVE_DIR = storemod.STATE / "live"
BUDGET_FILE = storemod.STATE / "live_budget.json"


class Refused(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _default_reader(model: str, page: Path) -> dict:
    from twohands import reader
    return reader.read(model, page)


def _default_usage() -> dict:
    from twohands import amd
    return amd.usage()


class Job:
    def __init__(self, clave: str):
        self.id = uuid.uuid4().hex[:12]
        self.clave = clave
        self.events: list[dict] = []
        self.done = False
        self.started = time.time()
        self.cond = threading.Condition()

    def emit(self, **ev) -> None:
        with self.cond:
            ev.setdefault("t", round(time.time() - self.started, 1))
            self.events.append(ev)
            self.cond.notify_all()

    def finish(self) -> None:
        with self.cond:
            self.done = True
            self.cond.notify_all()


class LiveManager:
    def __init__(self, reader_fn: Optional[Callable] = None, usage_fn: Optional[Callable] = None,
                 reveal_delay: float = 0.09):
        self.reader_fn = reader_fn or _default_reader
        self.usage_fn = usage_fn or _default_usage
        self.reveal_delay = reveal_delay
        self._busy = threading.Lock()
        self.jobs: dict[str, Job] = {}
        self.current: Optional[Job] = None

    # ---- budget
    def _today(self) -> dict:
        d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            b = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            b = {}
        return b.get(d, {"reads": 0, "usd": 0.0}) | {"date": d}

    def _spend(self, usd: float) -> None:
        t = self._today()
        try:
            b = json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            b = {}
        b[t["date"]] = {"reads": t["reads"] + 1, "usd": round(t["usd"] + (usd or 0.0), 6)}
        BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)
        BUDGET_FILE.write_text(json.dumps(b, indent=1), encoding="utf-8")

    def status(self) -> dict:
        t = self._today()
        return {"busy": self._busy.locked(), "reads_today": t["reads"], "usd_today": t["usd"],
                "max_reads": MAX_READS_PER_DAY, "max_usd": MAX_USD_PER_DAY,
                "current": self.current.clave if self.current and not self.current.done else None}

    def check_budget(self) -> dict:
        t = self._today()
        if t["reads"] >= MAX_READS_PER_DAY or t["usd"] >= MAX_USD_PER_DAY:
            raise Refused("budget", "Today's live-read allowance for this demo is used up. "
                                    "The precomputed result for this form is shown instead.")
        try:
            u = self.usage_fn() or {}
        except Exception as e:  # noqa: BLE001  endpoint down, key missing, timeout
            raise Refused("endpoint", "The AMD endpoint is not answering right now "
                                      f"({type(e).__name__}). The precomputed result is shown instead.")
        rem = u.get("daily_cost_remaining_usd")
        if rem is not None and float(rem) < MIN_REMAINING_USD:
            raise Refused("budget", "The shared AMD budget for today is nearly spent, and it is reserved for the "
                                    "measured batch run. Please try again after the daily reset.")
        return u

    # ---- run
    def start(self, clave: str, page: Optional[Path]) -> Job:
        if page is None:
            raise Refused("no_image", "This form has no privacy-masked page yet, so it cannot be sent to the model.")
        if not self._busy.acquire(blocking=False):
            raise Refused("busy", "Another live read is running (one at a time on the shared endpoint). "
                                  "Please try again in a minute.")
        try:
            self.check_budget()
        except Refused:
            self._busy.release()
            raise
        job = Job(clave)
        self.jobs[job.id] = job
        self.current = job
        threading.Thread(target=self._run, args=(job, page), daemon=True).start()
        return job

    def _run(self, job: Job, page: Path) -> None:
        from twohands.reader import MODELS
        try:
            model_name = MODELS.get(LIVE_MODEL, LIVE_MODEL)
            job.emit(type="stage", stage="prepare", msg="Privacy-masked page and zoomed tiles prepared")
            job.emit(type="stage", stage="send", msg=f"Sent to {model_name} on AMD (Token Factory), one request")
            row = self.reader_fn(LIVE_MODEL, page)
            cost = ((row.get("usage") or {}).get("cost") or 0.0) if isinstance(row.get("usage"), dict) else 0.0
            self._spend(cost)
            if row.get("error") or not row.get("parsed"):
                job.emit(type="error", code="read",
                         msg="The model did not return a readable answer"
                             + (f" ({row.get('error')[:120]})" if row.get("error") else "") + ". Showing the precomputed result.")
                return
            u = row.get("usage") or {}
            job.emit(type="stage", stage="answer", msg=f"Answer received after {row.get('secs')} s; the gate checks every field",
                     secs=row.get("secs"), cost=cost, prompt_tokens=u.get("prompt_tokens"),
                     completion_tokens=u.get("completion_tokens"))
            r = storemod.read_from_core(job.clave, "live", {"clave": job.clave, "parsed": row["parsed"],
                                                            "usage": u, "secs": row.get("secs")})
            ev = storemod.evaluate(r)
            for f in ev["fields"]:
                job.emit(type="field", **{k: f[k] for k in ("code", "name", "n", "w", "status", "msg")})
                time.sleep(self.reveal_delay)
            for i in ev["identities"]:
                job.emit(type="identity", name=i["name"], ok=i["ok"], lhs=i["lhs"], rhs=i["rhs"])
            job.emit(type="verdict", accepted=ev["accepted"], line=ev["line"], reasons=[storemod.neutralize(x) for x in ev["reasons"]],
                     secs=row.get("secs"), cost=cost, model=model_name)
            LIVE_DIR.mkdir(parents=True, exist_ok=True)
            out = {"clave": job.clave, "model": model_name, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "secs": row.get("secs"), "usage": u, "cost": cost, "finish_reason": row.get("finish_reason"),
                   "parsed": row["parsed"], "accepted": ev["accepted"], "reasons": ev["reasons"]}
            (LIVE_DIR / f"{job.clave}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            job.emit(type="error", code="internal", msg=f"Live read failed ({type(e).__name__}). Showing the precomputed result.")
        finally:
            job.emit(type="done")
            job.finish()
            self._busy.release()

    def stream(self, job_id: str, tick: float = 1.0):
        """Yield SSE frames: every event as it happens, plus an elapsed-time tick every second."""
        job = self.jobs.get(job_id)
        if job is None:
            yield "event: error\ndata: " + json.dumps({"type": "error", "code": "unknown", "msg": "No such live read."}) + "\n\n"
            return
        i = 0
        while True:
            with job.cond:
                if i >= len(job.events) and not job.done:
                    job.cond.wait(timeout=tick)
                new = job.events[i:]
                i = len(job.events)
                done = job.done and i >= len(job.events)
            for ev in new:
                yield "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"
            if done:
                return
            if not new:
                yield "data: " + json.dumps({"type": "tick", "t": round(time.time() - job.started, 1)}) + "\n\n"
