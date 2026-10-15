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
    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "executionId": (body or {}).get("executionId"), "status": (body or {}).get("status"),
           "body": json.dumps(body, ensure_ascii=False)[:2000]}
    casemod.CALLBACKS.parent.mkdir(parents=True, exist_ok=True)
    with open(casemod.CALLBACKS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(redact(row), ensure_ascii=False) + "\n")
    return {"ok": True}


def panel(clave: str):
    """Template helper: the latest Evolus case for a form (or None)."""
    return casemod.load_cases().get(clave)
