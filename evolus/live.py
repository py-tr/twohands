"""Evolus in the critical path of the live audit worker, and the review desk's "Send to Evolus".

For every form the live worker (twohands/worker.py) audits, ``LiveHook.on_result`` scores each dispute (model read
!= official capture) with the audit's evidence rule (app.capture_audit.evidence). Each STRONG-evidence dispute
(score >= 6; not on a form whose row-label check failed; not on a form where the certified count shows the model
misread a field) starts one run of the Evolus workflow "Audit finding": the Intake clerk (Gemma-4-31B-IT on the AMD Token
Factory) drafts the finding, a Script recomputes the score with no AI, the case comes back with status "open".

Not every routed form goes to Evolus: each run is one call on the shared AMD key, so runs are capped per UTC day
(EVOLUS_DAILY_RUNS, default 60; the desk's sends count too) and each start takes a token from the shared limiter.
Cases live in <worker dir>/evolus_cases.json; a background thread polls each run until it returns (or a Webhook
callback delivers it, merged by execution id, as for the audit cases). Keys never leave Settings; every stored
record passes through redact().
"""
from __future__ import annotations

import json
import os
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from twohands import REPO

DAILY_RUNS = int(os.environ.get("EVOLUS_DAILY_RUNS") or "60")
EVENT_CODE = "AMDACT3"
WORKSPACE_FALLBACK = "py_tr"          # the name on the space's home page in the Evolus UI
LIVE_TIMEOUT_S = 3600.0               # a run still open after this is recorded as "timeout" (never re-sent)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _read(path: Path) -> dict:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


# ------------------------------------------------------------------------------------------- the daily cap
class Quota:
    """At most ``cap`` Evolus workflow runs per UTC day, counted in a small JSON file ({day: n})."""

    def __init__(self, path: Optional[Path] = None, cap: Optional[int] = None):
        default = Path(os.environ.get("TWOHANDS_RATE_FILE") or REPO / "cache" / "ratelimit.json").parent
        self.path = Path(path or os.environ.get("EVOLUS_QUOTA_FILE") or default / "evolus_daily.json")
        self.cap = DAILY_RUNS if cap is None else int(cap)
        self._lock = threading.Lock()

    def used(self) -> int:
        return int(_read(self.path).get(_day()) or 0)

    def take(self) -> bool:
        with self._lock:
            d = _read(self.path)
            n = int(d.get(_day()) or 0)
            if n >= self.cap:
                return False
            _write(self.path, {_day(): n + 1})   # only today's count is kept
            return True


# ------------------------------------------------------------------------------------------- one live case
def _view(r: dict):
    from app import capture_audit as ca
    from app import store as storemod
    vals, words = {}, {}
    for code, f in (r.get("fields") or {}).items():
        k = storemod.key_of(code) or code
        vals[k], words[k] = (f or {}).get("n"), (f or {}).get("w")
    return ca.View(vals, words, bool(r.get("accepted")), "live worker read", None)


def score(r: dict, d: dict) -> dict:
    """The audit's evidence score of one live dispute (keyed value = the official capture)."""
    from app import capture_audit as ca
    from app import store as storemod
    k = storemod.key_of(d["code"]) or d["code"]
    return ca.evidence(k, d.get("capture"), "number", _view(r))


def is_strong(r: dict, d: dict) -> bool:
    return (not d.get("weak") and d.get("label") != "model_misread"
            and score(r, d)["tier"] == "strong")


def case_input(r: dict, d: dict, base_url: str = "") -> dict:
    """The 'Audit finding' input for one live dispute: the same keys as evolus.audit.case_input."""
    from app import capture_audit as ca
    from app import store as storemod
    view = _view(r)
    k = storemod.key_of(d["code"]) or d["code"]
    kv = d.get("capture")
    idents, breaks, supports = [], [], []
    for name, lhs, rhs in ca._idents():
        if k not in lhs and k not in rhs:
            continue
        nm = ca.IDENT_NAMES.get(name, name)
        mod = ca._check(view.values, lhs, rhs)
        kd = ca._check({**view.values, k: kv}, lhs, rhs) if kv is not None else None
        idents.append({"name": nm, "model_lhs": mod[0] if mod else None, "model_rhs": mod[1] if mod else None,
                       "keyed_lhs": kd[0] if kd else None, "keyed_rhs": kd[1] if kd else None})
        if mod and mod[0] == mod[1]:
            supports.append(nm)
            if kd and kd[0] != kd[1]:
                breaks.append(nm)
    ev = ca.evidence(k, kv, "number", view)
    crop = f"/live/crop/{r['clave']}/{d['code']}.jpg"
    out = {"case_id": f"live-{r['clave']}-{d['code']}", "form": r["clave"], "field": storemod.name_of(k),
           "code": d["code"], "keyed": kv, "keyed_n": kv, "keyed_kind": "number" if kv is not None else "blank",
           "model_digits": d.get("paper"), "model_words": d.get("words"),
           "model_read_passes_gate": bool(r.get("accepted")), "identities": idents, "breaks": breaks,
           "supports": supports, "crop_url": (base_url.rstrip("/") + crop) if base_url else crop,
           "evidence_tier": ev["tier"], "app_score": ev["score"], "source": "live audit worker (official capture)"}
    return storemod.public(out)


# ------------------------------------------------------------------------------------------- the worker hook
class LiveHook:
    """Called by the live worker after each committed result. Sending and polling run on one daemon thread, so the
    worker never waits on Evolus; ``sync=True`` (tests) does both inline."""

    def __init__(self, root: Path, client=None, quota: Optional[Quota] = None, limiter=None, sync: bool = False,
                 poll_every: float = 20.0, timeout_s: float = LIVE_TIMEOUT_S, log: Callable[[str], None] = lambda s: None,
                 sleep: Callable[[float], None] = time.sleep):
        from evolus.client import EvolusClient
        self.c = client or EvolusClient()
        self.s = self.c.s
        self.path = Path(root) / "evolus_cases.json"
        self.quota = quota or Quota()
        self.limiter, self.sync = limiter, sync
        self.poll_every, self.timeout_s, self.log, self.sleep = poll_every, timeout_s, log, sleep
        self.q: "queue.Queue[dict]" = queue.Queue()
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self.capped = 0

    # ---- records
    def cases(self) -> dict:
        from evolus import audit as auditmod
        with self._lock:
            c = _read(self.path)
        auditmod._merge_callbacks(c)
        return c

    def save(self, case: dict) -> dict:
        from evolus.config import redact
        with self._lock:
            c = _read(self.path)
            c[case["case_id"]] = redact(case, self.s.secrets())
            _write(self.path, c)
            return c[case["case_id"]]

    # ---- the hook
    def on_result(self, r: dict) -> int:
        """Queue the strong-evidence disputes of one audited form. Returns how many were queued."""
        if r.get("status") != "audited":
            return 0
        if any(d.get("label") == "model_misread" for d in r.get("disputes") or []):
            return 0   # the certified count shows the model misread this form: its other disputes are not strong
        have = self.cases()
        n = 0
        for d in r.get("disputes") or []:
            if f"live-{r['clave']}-{d['code']}" in have or not is_strong(r, d):
                continue
            self.q.put({"r": r, "d": d})
            n += 1
        if n:
            self.kick()
        return n

    def kick(self) -> None:
        if self.sync:
            self.drain()
            return
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, name="evolus-live", daemon=True)
            self._thread.start()

    def _lim(self):
        if self.limiter is None:
            from twohands.ratelimit import shared
            self.limiter = shared()
        return self.limiter

    def start(self, r: dict, d: dict) -> Optional[dict]:
        from evolus.client import EvolusError, NotConfigured
        from evolus.config import redact
        from evolus import audit as auditmod
        inp = case_input(r, d, self.s.public_url)
        if inp["case_id"] in self.cases():
            return None
        if not self.quota.take():
            self.capped += 1
            self.log(f"evolus: daily cap of {self.quota.cap} workflow runs reached; {inp['case_id']} not sent")
            return None
        case = {"case_id": inp["case_id"], "form": inp["form"], "field": inp["field"], "code": inp["code"],
                "workflow": auditmod.WORKFLOW, "workflow_id": self.s.audit_workflow_id, "case_status": "open",
                "sent": {x: inp[x] for x in ("keyed", "model_digits", "model_words", "breaks", "supports",
                                             "evidence_tier", "app_score")},
                "label": d.get("label"), "reader": r.get("reader"), "started_at": _now(), "run_status": "Pending",
                "source": "live worker"}
        waited = self._lim().acquire()      # the AgentCall step is one AMD call: take a shared token first
        cb = f"{self.s.public_url}/api/evolus/callback" if self.s.public_url and self.s.callback_key else None
        try:
            res = self.c.execute_workflow(self.s.audit_workflow_id, json.dumps(inp, ensure_ascii=False),
                                          parameters=auditmod.parameters(inp), callback_url=cb,
                                          callback_key=self.s.callback_key or None)
            case["execution_id"] = (res or {}).get("executionId")
            case.update(amd_calls=1, paced_wait_s=round(waited, 1), handoff="callback + poll" if cb else "poll")
        except (EvolusError, NotConfigured) as e:
            case.update(run_status="error", error=redact(str(e), self.s.secrets())[:300])
        if not case.get("execution_id") and case["run_status"] != "error":
            case.update(run_status="error", error="no execution id returned")
        self.log(f"evolus: {inp['case_id']} {case['run_status']} {case.get('execution_id') or case.get('error', '')}")
        return self.save(case)

    def open_cases(self) -> list[dict]:
        from evolus import audit as auditmod
        return [c for c in self.cases().values() if c.get("execution_id")
                and str(c.get("run_status", "")).lower() not in auditmod.FINAL | {"timeout"}]

    def poll_open(self) -> int:
        """Poll every open run once; returns how many are still open."""
        from evolus import audit as auditmod
        runner = auditmod.AuditRunner(self.c, {"id": "live"})
        still = 0
        for c in self.open_cases():
            c = runner.poll(c)
            if str(c.get("run_status", "")).lower() in auditmod.FINAL:
                c.setdefault("returned_at", _now())
            else:
                try:
                    age = time.time() - datetime.fromisoformat(c["started_at"]).timestamp()
                except (KeyError, ValueError):
                    age = 0.0
                if age >= self.timeout_s:
                    c.update(run_status="timeout", note=f"still open after {int(self.timeout_s)} s; not re-sent")
                else:
                    still += 1
            self.save(c)
        return still

    def drain(self) -> None:
        while True:
            try:
                job = self.q.get_nowait()
            except queue.Empty:
                break
            self.start(job["r"], job["d"])
        self.poll_open()

    def _loop(self) -> None:
        while True:
            try:
                job = self.q.get(timeout=self.poll_every)
                self.start(job["r"], job["d"])
            except queue.Empty:
                pass
            except Exception as e:  # noqa: BLE001 - a background thread records, never kills the worker
                self.log(f"evolus: {type(e).__name__}")
            try:
                if self.poll_open() == 0 and self.q.empty():
                    return
            except Exception as e:  # noqa: BLE001
                self.log(f"evolus poll: {type(e).__name__}")


def hook_for(root: Path, log: Callable[[str], None] = lambda s: None) -> Optional[LiveHook]:
    """The worker's hook, or None when Evolus is not configured here or EVOLUS_LIVE=0."""
    from evolus.config import Settings
    if (os.environ.get("EVOLUS_LIVE") or "1").strip() == "0":
        return None
    s = Settings.load()
    if not (s.key and s.app_id and s.audit_workflow_id):
        return None
    from evolus.client import EvolusClient
    h = LiveHook(root, EvolusClient(s), log=log)
    if h.open_cases():
        h.kick()   # resume: runs started before a restart are polled again, never re-sent
    return h


def worker_dir() -> Path:
    return Path(os.environ.get("TWOHANDS_WORKER_DIR") or REPO / "live_audit")


def live_cases(root: Optional[Path] = None) -> list[dict]:
    """Newest first, for the Evolus section of the site."""
    from evolus import audit as auditmod
    c = _read(Path(root or worker_dir()) / "evolus_cases.json")
    auditmod._merge_callbacks(c)
    return sorted(c.values(), key=lambda x: x.get("started_at") or "", reverse=True)


# ------------------------------------------------------------------------------------------- workspace identity
_WS: dict = {}


def workspace(client=None, refresh: bool = False) -> dict:
    """The event workspace's name, read from the API (GET /api/v1/agents/{agentId} -> application.name); the
    name shown on the space's home page in the UI when the API cannot be reached. Cached in evolus/ids.json;
    only refresh=True (python -m evolus setup) calls the API."""
    from evolus.config import load_ids, save_ids
    if _WS and not refresh:
        return _WS
    ids = load_ids()
    name, src = str(ids.get("workspace_name") or ""), str(ids.get("workspace_name_source") or "")
    if refresh:   # pages never call the API: the name is read once (setup / this call) and cached in ids.json
        try:
            from evolus.client import EvolusClient
            c = client or EvolusClient()
            a = c.rest("GET", f"/api/v1/agents/{ids.get('agent_id')}", "GET /api/v1/agents/{agentId}")
            got = ((a or {}).get("application") or {}).get("name")
            if got:
                name, src = str(got), "Evolus API: GET /api/v1/agents/{agentId} -> application.name"
                ids.update(workspace_name=name, workspace_name_source=src)
                save_ids(ids)
        except Exception:  # noqa: BLE001 - fall back to the name the UI shows
            pass
    if not name:
        name, src = WORKSPACE_FALLBACK, "the Evolus UI (the space's home page)"
    _WS.update(name=name, source=src, event_code=EVENT_CODE, line=f"Evolus event workspace: {name} (event code {EVENT_CODE})",
               model=str(ids.get("model_key") or "").split("/", 1)[-1])
    return _WS
