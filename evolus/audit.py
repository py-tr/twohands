"""Audit cases in Evolus: one disputed field of a capture audit becomes one run of the workflow "Audit finding".

The workflow (built by `python -m evolus setup`, steps from GET /api/v1/workflows/step-catalog):
  1. AgentCall "Intake clerk"  drafts the finding in the auditor's format: three sentences (what the paper shows,
                               what was keyed, which identity supports the paper), ending "for the auditor to confirm".
                               It never decides.
  2. Script (no AI)            recomputes the evidence score from the inputs, the same rule as
                               app.capture_audit.evidence, so the model cannot change it.
  3. Script (no AI)            assembles the audit case: finding + score + crop link, status "open".
  [4. Webhook]                 hands the case back to our app (/api/evolus/callback) when the app has a public URL.
  5. Output                    the case; without a public URL our app polls the execution for it.

The auditor's Confirm / Not an error writes the status back: to the case record here, to the Evolus workflow audit
of that run (clientData) when Evolus has one, and, once a library exists, a confirmed finding is filed in it.

Pacing: every run starts with a token from the shared limiter (cache/ratelimit.json, the batch uses it too), at most
IN_FLIGHT runs at once and at most MAX_CASES per call. One run = one AMD model call (the AgentCall step).
Only neutral names leave this module (Option NN); every record passes through redact().
"""
from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from app import capture_audit as ca
from app import store as storemod
from evolus.client import EvolusClient, EvolusError, NotConfigured
from evolus.config import redact

WORKFLOW = "Audit finding"
RESULTS = storemod.RESULTS / "evolus_audit_runs.jsonl"
MAX_CASES = 18
IN_FLIGHT = 2
TIMEOUT_S = 360.0          # per case: a run still going after this is recorded as "timeout" and the next one starts
OPEN_RUN = {"pending", "running", "queued", "timeout"}   # never re-sent (the AMD call is spent); a later call polls it
FINAL = {"completed", "failed", "succeeded", "cancelled", "canceled", "error"}
STATUS = {"confirmed": "confirmed", "not_error": "not an error", None: "open", "": "open"}
CONFIRM = "for the auditor to confirm"

FINDING_PROMPT = (
    "You draft one finding for a capture auditor. The case below (JSON) is one field of a paper form where the "
    "keyed (typed) value disagrees with a model's read of the paper. Write exactly three sentences of plain English: "
    "(1) what the paper shows: the model's digits and the amount in words; (2) what was keyed; (3) which of the "
    "paper's identities supports the paper's value ('supports'; 'breaks' lists those the keyed value breaks), or "
    "that none does, ending with the words "
    "'for the auditor to confirm'. You never decide whether it is an error, never propose another value, and name "
    "the field only as given (vote rows are 'Option NN'; never name a party). Answer with the three sentences only."
    "\n\n")

ASSEMBLE_JS = (
    "const t = s => (s && s.text ? s.text : '').trim();\n"
    "const ev = (sources[1] && sources[1].data) || {};\n"
    "let f = t(sources[0]).replace(/\\s+/g, ' ');\n"
    "if (!/for the auditor to confirm/i.test(f)) f = (f ? f.replace(/\\.?$/, '. ') : '') + 'For the auditor to confirm.';\n"
    "return { kind: 'audit case', case_id: params.case_id, form: params.form, field: params.field,\n"
    "  finding: f, evidence: ev, evidence_tier_sent: params.tier, crop_url: params.crop_url,\n"
    "  status: 'open', statuses: ['open', 'confirmed', 'not an error'], decided_by: 'the auditor' };")


def evidence_js() -> str:
    """app.capture_audit.evidence as a deterministic Evolus Script (zero AI calls). Input: the case JSON."""
    return chr(10).join([
        "const d = data || {};",
        "const isN = x => typeof x === 'number' && isFinite(x);",
        "const m = isN(d.model_digits) ? d.model_digits : null, w = isN(d.model_words) ? d.model_words : null;",
        "const kv = isN(d.keyed_n) ? d.keyed_n : null, kind = d.keyed_kind || '';",
        "const sig = [];",
        "if (m !== null && w !== null && m === w) sig.push([3, 'model digits and words agree (' + m + ')']);",
        "else if (m !== null && w !== null) sig.push([-2, 'model digits ' + m + ' and words ' + w + ' disagree']);",
        "else if (m !== null) sig.push([1, 'model read digits ' + m + '; no words read']);",
        "if (m === null && kv === 0) sig.push([-3, 'keyed 0 where the model saw an empty row (the blank = 0 convention)']);",
        "else if (m === null) sig.push([-1, 'model saw the boxes blank or faint']);",
        "if ((kind === 'illegible' || kind === 'no_data') && m !== null) sig.push([1, 'keyed as ' + "
        "(kind === 'illegible' ? 'illegible' : 'no data') + '; the model read a value']);",
        "for (const i of (d.identities || [])) {",
        "  if (!isN(i.model_lhs) || !isN(i.model_rhs)) continue;",
        "  const kd = isN(i.keyed_lhs) && isN(i.keyed_rhs);",
        "  if (i.model_lhs === i.model_rhs && kd && i.keyed_lhs !== i.keyed_rhs) sig.push([3, 'the keyed value breaks ' "
        "+ i.name + ' (' + i.keyed_lhs + ' vs ' + i.keyed_rhs + '); the model\\'s value satisfies it']);",
        "  else if (i.model_lhs === i.model_rhs && kv === null) sig.push([2, 'the model\\'s value satisfies ' + i.name]);",
        "  else if (i.model_lhs !== i.model_rhs && kd && i.keyed_lhs === i.keyed_rhs) sig.push([-3, 'the keyed value "
        "satisfies ' + i.name + '; the model\\'s breaks it (' + i.model_lhs + ' vs ' + i.model_rhs + ')']);",
        "}",
        "if (d.model_read_passes_gate === true) sig.push([1, 'the model\\'s read of this form passes every check of the gate']);",
        "const score = sig.reduce((a, s) => a + s[0], 0);",
        "const tier = score >= 6 ? 'strong' : (score >= 3 ? 'medium' : 'weak');",
        "return { score: score, tier: tier, signals: sig.map(s => ({ pts: s[0], text: s[1] })),",
        "  computed_by: 'Evolus Script step (no AI)', app_score: isN(d.app_score) ? d.app_score : null,",
        "  agrees_with_app: isN(d.app_score) ? d.app_score === score : null };",
    ])


# ------------------------------------------------------------------------------------------- the input of one case
def case_id(aid: str, key: str) -> str:
    return f"{aid}-{key}"


def case_input(a: dict, d: dict, base_url: str = "") -> dict:
    """The workflow input for one disputed field: neutral names, the raw numbers the score is computed from."""
    view, _ = ca.find_read(a, d["form"])
    k = storemod.key_of(d["code"])
    kv = d.get("keyed_n")
    vals = view.values if view else {}
    idents, breaks, supports = [], [], []
    for name, lhs, rhs in ca._idents():
        if k not in lhs and k not in rhs:
            continue
        nm = ca.IDENT_NAMES.get(name, name)
        mod = ca._check(vals, lhs, rhs)
        kd = ca._check({**vals, k: kv}, lhs, rhs) if kv is not None else None
        idents.append({"name": nm, "model_lhs": mod[0] if mod else None, "model_rhs": mod[1] if mod else None,
                       "keyed_lhs": kd[0] if kd else None, "keyed_rhs": kd[1] if kd else None})
        if mod and mod[0] == mod[1]:
            supports.append(nm)
            if kd and kd[0] != kd[1]:
                breaks.append(nm)
    img = d.get("img") or ""
    crop = (base_url.rstrip("/") + img) if img and base_url else img
    out = {"case_id": case_id(a["id"], d["key"]), "form": d["form"], "field": d["name"], "code": d["code"],
           "keyed": d["keyed"], "keyed_n": kv, "keyed_kind": d.get("keyed_kind") or ("number" if kv is not None else "blank"),
           "model_digits": d.get("model"), "model_words": d.get("words"),
           "model_read_passes_gate": bool(view.accepted) if view else False,
           "identities": idents, "breaks": breaks, "supports": supports, "crop_url": crop, "evidence_tier": d["tier"],
           "app_score": d["score"]}
    return storemod.public(out)


def parameters(inp: dict) -> dict:
    return {"form": inp["form"], "case_id": inp["case_id"], "field": inp["field"],
            "crop_url": inp.get("crop_url") or "", "tier": inp["evidence_tier"]}


def agent_model() -> str:
    """The model the agent "Intake clerk" runs on (evolus/ids.json model_key, set by setup), recorded per case."""
    from evolus.config import load_ids
    return str(load_ids().get("model_key") or "").split("/", 1)[-1]


def saved_runs(path: Optional[Path] = None) -> list[dict]:
    """The recorded "Audit finding" cases (results/evolus_audit_runs.jsonl), newest first; the last row per case."""
    try:
        lines = Path(path or RESULTS).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: dict = {}
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("case_id"):
            rows[r["case_id"]] = r
    return sorted(rows.values(), key=lambda r: (r.get("returned_at") or r.get("at") or "", r.get("started_at") or ""),
                  reverse=True)


# ------------------------------------------------------------------------------------------- case records (per audit)
_lock = threading.RLock()


def cases_file(aid: str) -> Path:
    return ca.adir(aid) / "evolus_cases.json"


def load_cases(aid: str) -> dict:
    with _lock:
        try:
            cases = json.loads(cases_file(aid).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cases = {}
    _merge_callbacks(cases)
    return cases


def save_case(aid: str, key: str, case: dict) -> dict:
    with _lock:
        try:
            cases = json.loads(cases_file(aid).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cases = {}
        cases[key] = redact(case)
        p = cases_file(aid)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(cases, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(p)
    return cases[key]


def _merge_callbacks(cases: dict) -> None:
    """Hand-off by callback: a Webhook delivery of the case (app/state/evolus_callbacks.jsonl) fills it in."""
    from evolus import case as casemod
    try:
        lines = casemod.CALLBACKS.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    by_eid = {c.get("execution_id"): c for c in cases.values() if c.get("execution_id")}
    for ln in lines:
        try:
            cb = json.loads(ln)
            body = json.loads(cb.get("body") or "{}")
        except ValueError:
            continue
        c = by_eid.get(cb.get("executionId"))
        if c is None or not isinstance(body, dict) or body.get("kind") != "audit case":
            continue
        c.setdefault("finding", storemod.neutralize(str(body.get("finding") or "")))
        c.setdefault("evidence", body.get("evidence"))
        c["handoff"] = "callback"
        if cb.get("auditId"):
            c["workflow_audit_id"] = cb["auditId"]


# ------------------------------------------------------------------------------------------- the runner
class AuditRunner:
    """Send disputed fields to the 'Audit finding' workflow, paced, and collect the cases as they return."""

    def __init__(self, client: EvolusClient, a: dict, limiter=None, max_cases: int = MAX_CASES,
                 in_flight: int = IN_FLIGHT, poll_every: float = 8.0, poll_s: float = TIMEOUT_S,
                 sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = lambda s: None,
                 results: Optional[Path] = None):
        self.c, self.a, self.s = client, a, client.s
        self.limiter = limiter
        self.max_cases, self.in_flight = max_cases, max(1, in_flight)
        self.poll_every, self.poll_s, self.sleep, self.log = poll_every, poll_s, sleep, log
        self.results = results
        self.amd_calls = 0
        self._names: Optional[dict] = None

    def _limiter(self):
        if self.limiter is None:
            from twohands.ratelimit import shared
            self.limiter = shared()
        return self.limiter

    def todo(self, disputes: list[dict]) -> list[dict]:
        """Strong-evidence fields without a case that is running or returned; at most max_cases."""
        have = load_cases(self.a["id"])
        out = [d for d in disputes if d["tier"] == "strong"
               and (have.get(d["key"]) or {}).get("run_status", "").lower() not in FINAL | OPEN_RUN]
        return out[: self.max_cases]

    def start(self, d: dict) -> dict:
        inp = case_input(self.a, d, self.s.public_url)
        case = {"key": d["key"], "case_id": inp["case_id"], "form": d["form"], "field": d["name"], "code": d["code"],
                "workflow": WORKFLOW, "workflow_id": self.s.audit_workflow_id, "case_status": STATUS.get(d.get("mark")),
                "sent": {k: inp[k] for k in ("keyed", "model_digits", "model_words", "breaks", "supports", "evidence_tier", "app_score")},
                "started_at": _now(), "run_status": "Pending", "model": agent_model()}
        waited = self._limiter().acquire()   # one AMD call follows (the AgentCall step): take a shared token
        cb = f"{self.s.public_url}/api/evolus/callback" if self.s.public_url and self.s.callback_key else None
        try:
            r = self.c.execute_workflow(self.s.audit_workflow_id, json.dumps(inp, ensure_ascii=False),
                                        parameters=parameters(inp), callback_url=cb,
                                        callback_key=self.s.callback_key or None)
            case["execution_id"] = (r or {}).get("executionId")
            self.amd_calls += 1
            case["amd_calls"] = 1
            case["paced_wait_s"] = round(waited, 1)
            case["handoff"] = "callback + poll" if cb else "poll"
        except (EvolusError, NotConfigured) as e:
            case.update(run_status="error", error=redact(str(e), self.s.secrets())[:300])
        if not case.get("execution_id") and case["run_status"] != "error":
            case.update(run_status="error", error="no execution id returned")
        self.log(f"{d['form']} {d['name']}: {case['run_status']} {case.get('execution_id') or case.get('error', '')}")
        return save_case(self.a["id"], d["key"], case)

    def step_names(self) -> dict:
        if self._names is None:
            try:
                w = self.c.rest("GET", f"/api/v1/workflows/{self.s.audit_workflow_id}", "GET /api/v1/workflows/{workflowId}")
                steps = w.get("steps") or []
                self._names = {str(s.get("id")): s.get("name") or "" for s in steps}
                self._names |= {str(s.get("order")): s.get("name") or "" for s in steps if s.get("order") is not None}
            except (EvolusError, NotConfigured):
                self._names = {}
        return self._names

    def poll(self, case: dict) -> dict:
        try:
            st = self.c.workflow_status(self.s.audit_workflow_id, case["execution_id"])
        except (EvolusError, NotConfigured) as e:
            case["poll_error"] = redact(str(e), self.s.secrets())[:200]
            return case
        case["run_status"] = str((st or {}).get("status") or case["run_status"])
        if case["run_status"].lower() in FINAL:
            case["returned_at"] = _now()
            raw = st.get("output")
            try:
                out = json.loads(raw) if isinstance(raw, str) and raw.strip()[:1] == "{" else raw
            except ValueError:
                out = raw
            if isinstance(out, dict):
                case["finding"] = storemod.neutralize(str(out.get("finding") or "").strip())
                case["evidence"] = out.get("evidence")
                case["returned_status"] = out.get("status")
            if st.get("error"):
                case["error"] = str(st["error"])[:300]
            names = self.step_names()
            states = st.get("stepStates") or {}
            if isinstance(states, dict):
                case["steps"] = [{"step": names.get(str(k), str(k)[:8]), "status": (v or {}).get("status"),
                                  "ms": (v or {}).get("durationMs")} for k, v in states.items()]
        return case

    def run(self, disputes: list[dict]) -> list[dict]:
        if not self.s.audit_workflow_id:
            raise NotConfigured("no 'Audit finding' workflow id (run python -m evolus setup)")
        pending = self.todo(disputes)
        keys = {d["key"] for d in disputes}
        # resume: runs started earlier and not yet collected are polled again, never re-sent (no new AMD call)
        running: list[dict] = [c for k, c in load_cases(self.a["id"]).items() if k in keys and c.get("execution_id")
                               and str(c.get("run_status", "")).lower() in OPEN_RUN]
        done: list[dict] = []
        while pending or running:
            while pending and len(running) < self.in_flight:
                c = self.start(pending.pop(0))
                (running if c.get("execution_id") else done).append(c)
            if not running:
                continue
            self.sleep(self.poll_every)
            for c in list(running):
                c = self.poll(c)
                c["waited_s"] = c.get("waited_s", 0.0) + self.poll_every * 1  # approximate, for the timeout only
                final = c["run_status"].lower() in FINAL
                if not final and c["waited_s"] >= self.poll_s:
                    c["note"] = (f"Evolus run still {c['run_status']} after {int(self.poll_s)} s; recorded as timeout, "
                                 "the next call polls it again (no new AMD call)")
                    c["run_status"] = "timeout"
                    final = True
                save_case(self.a["id"], c["key"], {k: v for k, v in c.items() if k != "waited_s"})
                if final:
                    running = [x for x in running if x["key"] != c["key"]]
                    done.append(c)
                    if self.results:
                        append_result(self.results, self.a, c)
                    self.log(f"{c['form']} {c['field']}: {c['run_status']}: {(c.get('finding') or c.get('error') or '')[:100]}")
                else:
                    running = [c if x["key"] == c["key"] else x for x in running]
        return done


def append_result(path: Path, a: dict, c: dict) -> None:
    row = {"at": _now(), "audit": a["id"], "audit_source": a.get("source"), "workflow": WORKFLOW,
           **{k: v for k, v in c.items() if k != "waited_s"}}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(redact(storemod.public(row)), ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------------------------- the auditor's status
def set_status(client: Optional[EvolusClient], aid: str, key: str, mark: Optional[str]) -> Optional[dict]:
    """Confirm / Not an error / cleared -> the case status, written to the case record and, where it exists, to
    Evolus: the run's workflow audit (clientData) and, for a confirmed finding, the library."""
    case = load_cases(aid).get(key)
    if case is None:
        return None
    case["case_status"] = STATUS.get(mark, "open")
    case["status_at"] = _now()
    wb: dict = {}
    if client is not None and case.get("execution_id"):
        wb["workflow_audit"] = _write_workflow_audit(client, case)
        if mark == "confirmed" and client.s.library_id:
            wb["library"] = _file_finding(client, case)
    case["writeback"] = wb
    return save_case(aid, key, case)


def _write_workflow_audit(client: EvolusClient, case: dict) -> str:
    try:
        aud = case.get("workflow_audit_id")
        if not aud:
            got = client.rest("GET", "/api/v1/workflow-audits", "GET /api/v1/workflow-audits",
                              params={"workflowId": case.get("workflow_id") or client.s.audit_workflow_id, "pageSize": 100})
            items = got if isinstance(got, list) else (got or {}).get("items") or (got or {}).get("data") or []
            hit = next((x for x in items if str(x.get("workflowExecutionId")) == str(case["execution_id"])), None)
            aud = (hit or {}).get("id")
        if not aud:
            return "no workflow audit found for this run yet"
        client.rest("PUT", f"/api/v1/workflow-audits/{aud}", "PUT /api/v1/workflow-audits/{auditId}",
                    {"clientData": {"status": case["case_status"], "decided_by": "the auditor", "at": case["status_at"],
                                    "case_id": case["case_id"]}})
        case["workflow_audit_id"] = aud
        return "written"
    except (EvolusError, NotConfigured) as e:
        return redact(f"not written: {e}", client.s.secrets())[:200]


def _file_finding(client: EvolusClient, case: dict) -> str:
    doc = (f"Audit finding {case['case_id']}\nForm {case['form']}, field {case['field']}\n"
           f"Status: confirmed capture error (by the auditor)\n\n{case.get('finding') or ''}\n")
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", f"finding_{case['form']}_{case['code']}.txt")
    try:
        client.upload_document(client.s.library_id, name, doc.encode("utf-8"))
        return f"filed {name}"
    except (EvolusError, NotConfigured) as e:
        return redact(f"not filed: {e}", client.s.secrets())[:200]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------------------------------- background runs (web)
_threads: dict[str, threading.Thread] = {}


def running(aid: str) -> bool:
    t = _threads.get(aid)
    return bool(t and t.is_alive())


def start_background(client: EvolusClient, a: dict, disputes: list[dict], **kw: Any) -> int:
    """Start (or refuse to double-start) a paced run for one audit. Returns how many fields will be sent."""
    if running(a["id"]):
        return -1
    r = AuditRunner(client, a, **kw)
    n = len(r.todo(disputes))
    if n:
        t = threading.Thread(target=_safe_run, args=(r, disputes), name=f"evolus-audit-{a['id']}", daemon=True)
        _threads[a["id"]] = t
        t.start()
    return n


def _safe_run(r: AuditRunner, disputes: list[dict]) -> None:
    try:
        r.run(disputes)
    except Exception as e:  # noqa: BLE001 - a background thread must record, not raise
        save_case(r.a["id"], "_runner", {"error": redact(f"{type(e).__name__}: {e}", r.s.secrets())[:300], "at": _now()})
