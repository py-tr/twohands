"""HTTP surface for Evolus: our gate as an authenticated endpoint, the case record per form, and the
workflow callback. Mounted by app/main.py with one include_router line."""
from __future__ import annotations

import hmac
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app import store as storemod
from evolus import case as casemod
from evolus.config import Settings, redact

router = APIRouter()


def _check(supplied: str, expected: str) -> None:
    if not expected:
        raise HTTPException(503, "endpoint disabled: no token configured on the server")
    if not supplied or not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(401, "invalid or missing token")


def _bearer(request: Request) -> str:
    h = request.headers.get("authorization", "")
    if h.lower().startswith("bearer "):
        return h[7:].strip()
    return request.headers.get("x-api-key", "").strip()


@router.post("/api/gate")
async def api_gate(request: Request):
    """Body: {"values": {"OPT01": 12, ..., "TOTAL": 250}, "words": {...optional}} -> identities + verdict.
    Auth: Authorization: Bearer <TWOHANDS_GATE_TOKEN> (or X-Api-Key). Used by Evolus agents/workflows as a tool."""
    _check(_bearer(request), Settings.load().gate_token)
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "JSON body expected")
    if not isinstance(body, dict):
        raise HTTPException(400, "JSON object expected")
    vals = body.get("values") if isinstance(body.get("values"), dict) else {
        k: v for k, v in body.items() if storemod.key_of(str(k))}
    if not vals:
        raise HTTPException(400, "no field values; send {\"values\": {\"OPT01\": 12, ...}}")
    return casemod.gate_check(vals, body.get("words") if isinstance(body.get("words"), dict) else None)


@router.get("/api/evolus/case/{clave}")
def api_case(clave: str):
    c = casemod.load_cases().get(clave)
    if c is None:
        raise HTTPException(404, "no Evolus case for this form")
    return storemod.public(c)


@router.post("/api/evolus/callback")
async def api_callback(request: Request):
    """Evolus workflow callback (callbackApiKeyName = X-Callback-Key)."""
    _check(request.headers.get("x-callback-key", "").strip(), Settings.load().callback_key)
    try:
        body = await request.json()
    except ValueError:
        body = {}
    body = body if isinstance(body, dict) else {"body": body}
    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "executionId": body.get("executionId") or request.headers.get("x-workflow-execution-id"),
           "auditId": request.headers.get("x-workflow-audit-id"), "status": body.get("status"),
           "body": json.dumps(body, ensure_ascii=False)[:2000]}
    casemod.CALLBACKS.parent.mkdir(parents=True, exist_ok=True)
    with open(casemod.CALLBACKS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(redact(row), ensure_ascii=False) + "\n")
    return {"ok": True}


# ------------------------------------------------------------------------------------------- review desk -> Evolus
_sending: set = set()


@router.post("/api/evolus/send/{clave}")
def api_send(clave: str):
    """The review desk's "Send to Evolus": run the intake case of one routed form (workflow "Review hand-off") in
    the background. Counts against the daily cap of Evolus runs (EVOLUS_DAILY_RUNS) shared with the live worker."""
    import threading
    from evolus import live
    from evolus.client import EvolusClient
    s = Settings.load()
    st = storemod.get_store()
    if not (s.key and s.app_id and s.workflow_id):
        raise HTTPException(503, "Evolus is not configured on this server (run python -m evolus setup)")
    if st.masked_image(clave) is None:
        raise HTTPException(404, "no masked page for this form")
    if clave in _sending:
        raise HTTPException(409, "already sending this form to Evolus")
    q = live.Quota()
    if not q.take():
        raise HTTPException(429, f"today's cap of {q.cap} Evolus workflow runs is reached; it resets at 00:00 UTC")

    def go():
        try:
            rec = casemod.Case(clave, EvolusClient(s), poll_s=240.0).run()
            rec["sent_from"] = "review desk"
            casemod.save(rec, casemod.STATE_RUNS)
        except Exception as e:  # noqa: BLE001 - recorded, never raised in a background thread
            casemod.save({"clave": clave, "case_id": f"desk-{clave}", "at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"), "decision": "error", "decision_reason": f"not sent: {type(e).__name__}",
                "steps": []}, casemod.STATE_RUNS)
        finally:
            _sending.discard(clave)
    _sending.add(clave)
    threading.Thread(target=go, name=f"evolus-send-{clave}", daemon=True).start()
    return {"started": True, "form": clave, "runs_today": q.used(), "cap": q.cap}


@router.get("/api/evolus/live")
def api_live():
    """The live worker's Evolus audit cases (newest first) and today's run count."""
    from evolus import live
    keep = ("case_id", "form", "field", "execution_id", "run_status", "case_status", "finding", "evidence", "error",
            "started_at", "returned_at", "handoff")
    q = live.Quota()
    return {"workspace": live.workspace()["line"], "runs_today": q.used(), "cap": q.cap,
            "cases": [{k: c.get(k) for k in keep} for c in live.live_cases()[:50]]}


def info() -> dict:
    """Template helper for the Evolus section: workspace name, model, live cases (never a key)."""
    from evolus import live
    from evolus.config import load_ids
    ws = live.workspace()
    q = live.Quota()
    cases = live.live_cases()
    ids = load_ids()
    return ws | {"names": ids.get("names") or {}, "extractor_ready": bool(ids.get("extractor_id")), "runs_today": q.used(), "cap": q.cap,
                 "live_cases": cases[:5], "live_total": len(cases),
                 "live_returned": sum(1 for c in cases if c.get("finding"))}


def panel(clave: str):
    """Template helper: the latest Evolus case for a form (or None)."""
    return casemod.load_cases().get(clave)
