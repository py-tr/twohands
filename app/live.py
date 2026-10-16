"""Live read on AMD as a visible queued job: one form, one request, streamed to the browser as server-sent events.

Safety rails (the AMD Token Factory key is shared with the core's batch job: 20 req/min, 8 concurrent, $1/day):
  * ONE live read runs at a time, site-wide: jobs wait in a short FIFO queue (QUEUE_MAX, the running one
    included) and a single worker thread reads them in turn. A full queue answers "busy".
  * Every request goes through the core client (twohands.amd.chat), i.e. the core's shared rate limiter, with a
    short retry budget so a busy endpoint is reported in seconds, not minutes.
  * Budget guard when a job is queued AND again when it starts: the endpoint's own /usage
    (daily_cost_remaining_usd must stay above LIVE_MIN_REMAINING_USD, i.e. the key is not spent) and a local daily
    cap on reads and dollars: LIVE_MAX_USD_PER_DAY is the live share of the key's daily cap, $0.10 of $1.00
    (twohands/budgets.py; the worker keeps it as its reserve, bulk runs stop at their own $0.30). Live requests take
    the limiter's reserved live lane (4 of the 16 requests a minute).
  * Only a privacy-masked page is ever sent; a form without one cannot be read live.
  * AMD 503 / timeout: the job ends with code "endpoint_busy"; the browser shows the last measured read of the
    form (when it has one) under an honest banner, with a retry button.
  * The model comes from the endpoint's own model list (app/livemodel.py, cached 5 min): Gemma-4-31B-IT when it is
    listed; otherwise Qwen3.8-27B through the core reader's own frozen qwen path, with a banner saying so. A Gemma
    call answering 400 "not supported" switches the same job to Qwen at once.
"""
from __future__ import annotations

import collections
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from app import livemodel
from app import store as storemod

LIVE_MODEL = livemodel.CONFIGURED
MIN_REMAINING_USD = float(os.environ.get("LIVE_MIN_REMAINING_USD", "0.02"))
MAX_READS_PER_DAY = int(os.environ.get("LIVE_MAX_READS_PER_DAY", "40"))
from twohands import budgets as _budgets  # noqa: E402
MAX_USD_PER_DAY = _budgets.share("live")   # LIVE_MAX_USD_PER_DAY, default 0.10
QUEUE_MAX = int(os.environ.get("LIVE_QUEUE_MAX", "4"))
LIVE_RETRIES = int(os.environ.get("LIVE_RETRIES", "2"))
LIVE_DIR = storemod.STATE / "live"
BUDGET_FILE = storemod.STATE / "live_budget.json"

BUSY_MARKERS = ("503", "502", "504", "timeout", "timed out", "gave up", "gaveup", "urlerror", "remotedisconnected",
                "connectionreset", "connection reset", "temporarily unavailable")


_BUDGET_LOCK = threading.RLock()


def _read_budget() -> dict:
    try:
        return json.loads(BUDGET_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_atomic(path: Path, text: str) -> None:
    """Write a sibling temp file, then os.replace it over ``path``: readers see the old file or the new one, never a
    truncated one. On Windows the replace fails while another handle has the file open; retry briefly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    for i in range(50):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i == 49:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.01)


def _live_priority(active: bool) -> None:
    try:
        from twohands.ratelimit import live_priority
        live_priority(active)
    except Exception:  # noqa: BLE001 - priority is a courtesy; a live read never fails for it
        pass


class Refused(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _default_reader(model: str, page: Path) -> dict:
    from twohands import amd, reader

    def chat(body):  # the core client and its shared limiter, with a short retry budget for an interactive read
        return amd.chat(body, retries=LIVE_RETRIES, log=lambda *a, **k: None, kind="live")
    return reader.read(model, page, chat=chat)


def _default_usage() -> dict:
    from twohands import amd
    return amd.usage()


def endpoint_busy(err: Optional[str]) -> bool:
    e = (err or "").lower()
    return any(m in e for m in BUSY_MARKERS)


class Job:
    def __init__(self, clave: str, page: Path, kind: str = "form", out_dir: Optional[Path] = None,
                 fallback: Optional[str] = None):
        self.id = uuid.uuid4().hex[:12]
        self.clave = clave
        self.page = page
        self.kind = kind
        self.out_dir = out_dir
        self.fallback = fallback
        self.state = "queued"
        self.events: list[dict] = []
        self.done = False
        self.created = time.time()
        self.started: Optional[float] = None
        self.cond = threading.Condition()

    def emit(self, **ev) -> None:
        with self.cond:
            ev.setdefault("t", round(time.time() - self.created, 1))
            self.events.append(ev)
            self.cond.notify_all()

    def finish(self) -> None:
        with self.cond:
            self.done = True
            self.cond.notify_all()


class LiveManager:
    def __init__(self, reader_fn: Optional[Callable] = None, usage_fn: Optional[Callable] = None,
                 reveal_delay: float = 0.09, chooser: Optional[livemodel.Chooser] = None):
        self.reader_fn = reader_fn or _default_reader
        self.chooser = chooser or livemodel.chooser
        self.usage_fn = usage_fn or _default_usage
        self.reveal_delay = reveal_delay
        self._lock = threading.Lock()
        self._wake = threading.Condition(self._lock)
        self._queue: collections.deque = collections.deque()
        self._worker: Optional[threading.Thread] = None
        self.jobs: dict[str, Job] = {}
        self.current: Optional[Job] = None

    # ---- budget (one file per process group; read and written under _BUDGET_LOCK, replaced atomically so a reader
    # never sees a half-written file: a torn read used to count as "0 reads today")
    def _today(self) -> dict:
        d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with _BUDGET_LOCK:
            b = _read_budget()
        return b.get(d, {"reads": 0, "usd": 0.0}) | {"date": d}

    def _spend(self, usd: float) -> None:
        d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with _BUDGET_LOCK:
            b = _read_budget()
            t = b.get(d, {"reads": 0, "usd": 0.0})
            b[d] = {"reads": t["reads"] + 1, "usd": round(t["usd"] + (usd or 0.0), 6)}
            _write_atomic(BUDGET_FILE, json.dumps(b, indent=1))

    def _running(self) -> Optional[Job]:
        return self.current if self.current is not None and not self.current.done else None

    def status(self) -> dict:
        t = self._today()
        with self._lock:
            running = self._running()
            queued = len(self._queue)
        cur = None
        if running is not None:
            cur = running.clave if running.kind == "form" else "a photo upload"
        pick = self.chooser.choose(block=False)  # never waits on AMD; a stale list refreshes in the background
        return {"busy": running is not None or queued > 0, "running": running is not None, "queued": queued,
                "model": pick["model"], "fallback": pick["fallback"], "banner": pick["banner"],
                "banner_try": pick["banner_try"],
                "queue_max": QUEUE_MAX, "reads_today": t["reads"], "usd_today": t["usd"],
                "max_reads": MAX_READS_PER_DAY, "max_usd": MAX_USD_PER_DAY, "current": cur}

    def position(self, job: Job) -> int:
        """Reads ahead of this job (the running one included); 0 once it runs, or when it is next."""
        with self._lock:
            if job.state != "queued" or job not in self._queue:
                return 0
            return list(self._queue).index(job) + (1 if self._running() is not None else 0)

    def job_status(self, job_id: str) -> Optional[dict]:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        last = next((e for e in reversed(job.events) if e["type"] in ("verdict", "error")), None)
        return {"job": job.id, "form": job.clave, "kind": job.kind, "state": job.state, "position": self.position(job),
                "elapsed_s": round(time.time() - job.created, 1),
                "reading_s": round(time.time() - job.started, 1) if job.started else None,
                "stages": [e["stage"] for e in job.events if e["type"] == "stage"],
                "result": storemod.public(last) if last else None}

    def check_budget(self) -> dict:
        t = self._today()
        if t["reads"] >= MAX_READS_PER_DAY or t["usd"] >= MAX_USD_PER_DAY:
            raise Refused("budget", "Today's live-read allowance for this demo is used up. "
                                    "The last measured read is shown instead.")
        try:
            u = self.usage_fn() or {}
        except Exception as e:  # noqa: BLE001  endpoint down, key missing, timeout
            raise Refused("endpoint", f"AMD endpoint busy or not answering ({type(e).__name__}), showing the last "
                                      "measured read of this form; retry in a minute.")
        rem = u.get("daily_cost_remaining_usd")
        if rem is not None and float(rem) < MIN_REMAINING_USD:
            raise Refused("budget", "The shared AMD budget for today is spent. "
                                    "Please try again after the daily reset (16:00 UTC).")
        return u

    # ---- queue
    def start(self, clave: str, page: Optional[Path], kind: str = "form", out_dir: Optional[Path] = None,
              fallback: Optional[str] = None) -> Job:
        if page is None:
            raise Refused("no_image", "This form has no privacy-masked page yet, so it cannot be sent to the model.")
        with self._lock:
            if (1 if self._running() else 0) + len(self._queue) >= QUEUE_MAX:
                raise Refused("busy", "The live-read queue is full (one read at a time on the shared endpoint). "
                                      "Please try again in a minute.")
        self.check_budget()
        if fallback is None and kind == "form":
            fallback = clave
        job = Job(clave, page, kind=kind, out_dir=out_dir, fallback=fallback)
        with self._lock:
            self.jobs[job.id] = job
            self._queue.append(job)
            _live_priority(True)   # the live audit worker yields the shared limiter while a live read waits
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._loop, daemon=True)
                self._worker.start()
            self._wake.notify_all()
        job.emit(type="queued", position=self.position(job))
        return job

    def _loop(self) -> None:
        while True:
            with self._lock:
                while not self._queue:
                    self._wake.wait(timeout=30)
                    if not self._queue:
                        self._worker = None
                        return
                job = self._queue.popleft()
                job.state = "running"
                job.started = time.time()
                self.current = job
            try:
                self._run(job)
            finally:
                with self._lock:
                    if self.current is job:
                        self.current = None
                    if not self._queue:
                        _live_priority(False)

    def _fail(self, job: Job, code: str, msg: str) -> None:
        job.state = "failed"
        job.emit(type="error", code=code, msg=msg, fallback=job.fallback)

    def _run(self, job: Job) -> None:
        try:
            try:  # the allowance may have changed while the job waited in line
                self.check_budget()
            except Refused as e:
                self._fail(job, "endpoint_busy" if e.code == "endpoint" else e.code, e.message)
                return
            pick = self.chooser.choose(block=True)
            if pick["fallback"]:
                job.emit(type="notice", code="model_withdrawn", model=pick["model"],
                         msg=pick["banner"] if job.kind == "form" else pick["banner_try"])
            model_name = pick["model"]
            job.emit(type="stage", stage="prepare", msg="Masked page and zoomed tiles prepared")
            job.emit(type="stage", stage="send", msg=f"Sent to {model_name} on AMD, one request")
            row = self.reader_fn(pick["key"], job.page)
            cost = ((row.get("usage") or {}).get("cost") or 0.0) if isinstance(row.get("usage"), dict) else 0.0
            self._spend(cost)
            if livemodel.is_withdrawn_error(row.get("error")) and not pick["fallback"]:
                # the endpoint dropped the model between list refreshes: switch this job, and the next ones, now
                self.chooser.mark_withdrawn(model_name)
                pick = self.chooser.choose(block=False)
                if pick["fallback"]:
                    model_name = pick["model"]
                    job.emit(type="notice", code="model_withdrawn", model=model_name,
                             msg=pick["banner"] if job.kind == "form" else pick["banner_try"])
                    job.emit(type="stage", stage="send", msg=f"Sent to {model_name} on AMD, one request")
                    row = self.reader_fn(pick["key"], job.page)
                    cost = ((row.get("usage") or {}).get("cost") or 0.0) if isinstance(row.get("usage"), dict) else 0.0
                    self._spend(cost)
            if row.get("error") and endpoint_busy(row.get("error")):
                self._fail(job, "endpoint_busy", "AMD endpoint busy (503 or timeout)"
                           + (", showing the last measured read of this form; retry in a minute." if job.fallback
                              else "; your masked page is kept, retry in a minute."))
                return
            if row.get("error") or not row.get("parsed"):
                self._fail(job, "read", "The model did not return a readable answer"
                           + (f" ({storemod.neutralize(row.get('error'))[:120]})" if row.get("error") else "")
                           + (". Showing the last measured read." if job.fallback else "."))
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
            out_dir = job.out_dir or LIVE_DIR
            out_dir.mkdir(parents=True, exist_ok=True)
            out = {"clave": job.clave, "model": model_name, "model_fallback": pick["fallback"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "secs": row.get("secs"), "usage": u, "cost": cost, "finish_reason": row.get("finish_reason"),
                   "parsed": row["parsed"], "accepted": ev["accepted"], "reasons": ev["reasons"]}
            name = f"{job.clave}.json" if job.out_dir is None else f"{job.clave}.read.json"
            (out_dir / name).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            job.state = "done"
            job.emit(type="verdict", accepted=ev["accepted"], line=ev["line"], reasons=[storemod.neutralize(x) for x in ev["reasons"]],
                     secs=row.get("secs"), cost=cost, model=model_name, fallback=pick["fallback"])
        except Exception as e:  # noqa: BLE001
            self._fail(job, "internal", f"Live read failed ({type(e).__name__})."
                       + (" Showing the last measured read." if job.fallback else ""))
        finally:
            job.emit(type="done")
            job.finish()

    def stream(self, job_id: str, tick: float = 1.0):
        """Yield SSE frames: every event as it happens, plus a tick (elapsed time, queue position) every second."""
        job = self.jobs.get(job_id)
        if job is None:
            yield "data: " + json.dumps({"type": "error", "code": "unknown", "msg": "No such live read."}) + "\n\n"
            yield "data: " + json.dumps({"type": "done"}) + "\n\n"
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
                yield "data: " + json.dumps({"type": "tick", "t": round(time.time() - job.created, 1),
                                             "state": job.state, "position": self.position(job)}) + "\n\n"
