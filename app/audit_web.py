"""Audit your capture: pages and API (/audit/new, /audit/{id}, its report and CSV). Logic in app/capture_audit.py."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app import capture_audit as ca
from app import numbers as numbersmod
from app import store as storemod

router = APIRouter()


def _t():
    from app.main import templates
    return templates


def _audit_or_404(aid: str) -> dict:
    a = ca.load(aid)
    if a is None:
        raise HTTPException(404, "unknown audit")
    return a


def _run(request: Request, a: dict, strict: bool = False) -> dict:
    mgr = request.app.state.live

    def js(job_id):
        j = mgr.job_status(job_id)
        return j["state"] if j else None
    return ca.run(a, job_state=js, strict=strict)


def _flist():
    return [{"code": storemod.code_of(f["key"]), "name": storemod.name_of(f["key"]),
             "section": storemod.SECTION.get(f["key"])} for f in ca.graded()]


def _methods(H: dict, L: dict) -> dict:
    """The methods paragraph: the measured yield and the recall caveat, word for word from the computed summary."""
    if not H:
        return {}
    return {"yield": (f"On a pre-registered random sample of {H['forms']} forms, the model disputed {H['disagree']} of "
                      f"{H['fields']:,} keyed fields; on the paper, {H['keying_errors']} of those {H['disagree']} were "
                      f"capture errors: 1 in {H['yield_one_in']}. A disputed field is a lead, not a finding, until a "
                      f"person confirms it on the photo."),
            "recall": ("Only fields where the model disagrees with the keyed value are listed, so a capture error the "
                       "model made too is not found. " + L.get("recall", ""))}


@router.get("/audit/new", response_class=HTMLResponse)
def audit_new(request: Request):
    H = numbersmod.headline()
    return _t().TemplateResponse(request, "audit_new.html", {"nav": "auditnew", "flist": _flist(), "H": H,
                                                             "M": _methods(H, numbersmod.lines(H))})


@router.post("/api/audit")
async def api_audit_create(request: Request, name: str = "keyed.csv"):
    """Body: the keyed CSV itself (text/csv). Returns the audit id, the columns (named neutrally) and the proposed
    mapping of each field to a column (auto-detected INE PREP names)."""
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > ca.MAX_CSV_BYTES:
            return JSONResponse({"error": "The file is larger than 20 MB."}, status_code=413)
    text = bytes(data).decode("utf-8-sig", "replace")
    if "�" in text:
        text = bytes(data).decode("latin-1")
    try:
        a = ca.create(text, name=name)
    except (ValueError, IndexError) as e:
        return JSONResponse({"error": str(e) or "Could not read that file as CSV."}, status_code=422)
    return _proposal(a)


def _proposal(a: dict) -> dict:
    rows = ca.keyed_rows(a)
    cols = []
    for i, h in enumerate(a["headers"]):
        ex = next((r[i].strip() for r in rows if len(r) > i and r[i].strip()), "")
        cols.append({"i": i, "label": ca.display_header(h), "example": storemod.neutralize(ex[:24])})
    return {"id": a["id"], "rows": a["rows"], "columns": cols, "id_col": a["id_col"],
            "mapping": a["mapping"], "how": a["how"], "fields": _flist()}


@router.post("/api/audit/sample")
def api_audit_sample():
    a = ca.sample()
    return {"id": a["id"], "url": f"/audit/{a['id']}"}


@router.post("/api/audit/{aid}/mapping")
async def api_audit_mapping(aid: str, request: Request):
    a = _audit_or_404(aid)
    body = await request.json()
    try:
        fields = {k: (int(v) if v not in (None, "") else None) for k, v in (body.get("fields") or {}).items()}
        idc = int(body.get("id_col")) if body.get("id_col") not in (None, "") else None
        a = ca.set_mapping(a, idc, fields, body.get("scans") or "stored")
    except (ValueError, TypeError) as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    return {"id": a["id"], "url": f"/audit/{a['id']}"}


@router.post("/api/audit/{aid}/scans")
async def api_audit_scans(aid: str, request: Request):
    """Body: a ZIP of page images (application/zip), read in memory, never extracted to disk. Each page is located
    and masked by the core; only masked pages are stored."""
    a = _audit_or_404(aid)
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > ca.MAX_ZIP_BYTES:
            return JSONResponse({"error": "The ZIP is larger than 200 MB; split it."}, status_code=413)
    try:
        out = ca.add_scans(a, bytes(data))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    finally:
        del data
    return {k: (len(v) if isinstance(v, list) else v) for k, v in out.items()} | {"not_located_forms": out["not_located"][:50]}


@router.post("/api/audit/{aid}/read")
def api_audit_read(aid: str, request: Request):
    a = _audit_or_404(aid)
    R = _run(request, a)
    return ca.queue_reads(a, request.app.state.live, R)


@router.post("/api/audit/{aid}/mark")
async def api_audit_mark(aid: str, request: Request):
    a = _audit_or_404(aid)
    body = await request.json()
    key = str(body.get("key") or "")
    try:
        ca.mark(a, key, body.get("mark") or None)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    case = _evolus_status(aid, key, body.get("mark") or None)
    return {"ok": True, "key": key, "mark": body.get("mark") or None, "case_status": case}


def _evolus_status(aid: str, key: str, mark):
    """The auditor's mark is the audit case's status: written to the case at once; to Evolus in the background."""
    from evolus import audit as auditmod
    case = auditmod.load_cases(aid).get(key)
    if case is None:
        return None
    case["case_status"] = auditmod.STATUS.get(mark, "open")
    auditmod.save_case(aid, key, case)

    def push():
        try:
            from evolus.client import EvolusClient
            auditmod.set_status(EvolusClient(), aid, key, mark)
        except Exception:  # noqa: BLE001 - the local status is already saved
            pass
    threading.Thread(target=push, daemon=True).start()
    return case["case_status"]


@router.post("/api/audit/{aid}/evolus")
def api_audit_evolus(aid: str, request: Request):
    """Open the strong-evidence fields as Evolus audit cases (workflow 'Audit finding'), paced in the background."""
    from evolus import audit as auditmod
    from evolus.client import EvolusClient
    from evolus.config import Settings
    from evolus.setup import ensure_user_blocks
    a = _audit_or_404(aid)
    s = Settings.load()
    if not (s.key and s.app_id and s.audit_workflow_id):
        return JSONResponse({"error": "Evolus is not configured on this server (keys or the 'Audit finding' workflow; "
                                      "run python -m evolus setup)."}, status_code=503)
    c = EvolusClient(s)
    ensure_user_blocks(c)
    R = _run(request, a)
    n = auditmod.start_background(c, a, R["disputes"])
    if n < 0:
        return JSONResponse({"error": "Already sending these fields to Evolus."}, status_code=409)
    return {"started": n, "strong": R["tiers"]["strong"], "max": auditmod.MAX_CASES}


@router.get("/api/audit/{aid}/evolus")
def api_audit_evolus_cases(aid: str):
    from evolus import audit as auditmod
    _audit_or_404(aid)
    cases = auditmod.load_cases(aid)
    keep = ("case_id", "form", "field", "execution_id", "run_status", "case_status", "finding", "evidence", "error",
            "note", "handoff", "started_at", "returned_at")
    return {"running": auditmod.running(aid), "runner_error": (cases.get("_runner") or {}).get("error"),
            "cases": {k: {x: c.get(x) for x in keep} for k, c in cases.items() if not k.startswith("_")}}


@router.get("/api/audit/{aid}")
def api_audit(aid: str, request: Request):
    a = _audit_or_404(aid)
    R = _run(request, a)
    return storemod.public({k: v for k, v in R.items()})


def _ctx(request: Request, a: dict, strict: bool = False) -> dict:
    R = _run(request, a, strict)
    H = numbersmod.headline()
    from evolus import audit as auditmod
    EV = {k: v for k, v in auditmod.load_cases(a["id"]).items() if not k.startswith("_")}
    return {"a": a, "R": R, "H": H, "M": _methods(H, numbersmod.lines(H)), "flist": _flist(), "EV": EV,
            "TIERS": ca.TIERS, "MARKS": ca.MARKS, "today": datetime.now(timezone.utc).strftime("%Y-%m-%d")}


@router.get("/audit/sample.csv")
def audit_sample_csv():
    """The sample's keyed file: the official first capture of the 300 pre-registered forms (INE column names, as
    published; a machine file like results/*.jsonl). Pages and exports of the audit show Option NN."""
    return Response(ca.SAMPLE_CSV.read_bytes(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=prep2024-300-keyed.csv"})


@router.get("/audit/{aid}", response_class=HTMLResponse)
def audit_view(aid: str, request: Request):
    a = _audit_or_404(aid)
    return _t().TemplateResponse(request, "audit_run.html", {"nav": "auditnew", **_ctx(request, a)})


@router.get("/audit/{aid}/report", response_class=HTMLResponse)
def audit_report(aid: str, request: Request, only: Optional[str] = None, strict: int = 0):
    """The printable report. ?strict=1: a field is strong only if Gemma and Qwen both read the same value that
    differs from the keyed one (stored Qwen reads; "second reader not available" where there is none)."""
    a = _audit_or_404(aid)
    ctx = _ctx(request, a, bool(strict))
    only = "unrefuted" if only == "unrefuted" else None
    if only:
        ctx["R"]["disputes"] = [d for d in ctx["R"]["disputes"] if d["mark"] != "not_error"]
    q = [k for k, v in (("strict=1", strict), (f"only={only}", only)) if v]
    ctx.update(FP=ca.fingerprint(a, ctx["R"], only), strict=bool(strict), only=only, RQ=("?" + "&".join(q)) if q else "")
    return _t().TemplateResponse(request, "audit_report.html", ctx)


@router.get("/audit/{aid}/receipt/{key}")
def audit_receipt(aid: str, key: str, request: Request, only: Optional[str] = None, strict: int = 0):
    """One disputed field's Merkle receipt (JSON): its leaf record and hash, the proof path and the report's root, for
    the same report view (?strict=1, ?only=unrefuted). Check it with python -m twohands.verify_receipt."""
    a = _audit_or_404(aid)
    R = _run(request, a, bool(strict))
    only = "unrefuted" if only == "unrefuted" else None
    if only:
        R["disputes"] = [d for d in R["disputes"] if d["mark"] != "not_error"]
    r = ca.receipt(a, R, key, only)
    if r is None:
        raise HTTPException(404, "no disputed field with that key in this report")
    return JSONResponse(r, headers={"Content-Disposition": f'inline; filename="receipt-{key}.json"'})


@router.get("/audit/{aid}/report.csv")
def audit_report_csv(aid: str, request: Request, strict: int = 0):
    """The report as CSV, with the report fingerprint and the input file hashes at the end (rows starting '#')."""
    a = _audit_or_404(aid)
    R = _run(request, a, bool(strict))
    sfx = "-strict" if strict else ""
    return Response(ca.report_csv(a, R, ca.fingerprint(a, R)), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=audit-report-{aid}{sfx}.csv"})


@router.get("/audit/{aid}/crop/{fid}/{code}.jpg")
def audit_crop(aid: str, fid: str, code: str):
    """Crop of a page this audit masked (only masked pages exist here)."""
    from app.main import _crop_bytes
    p = ca.page_of(aid, fid)
    key = storemod.key_of(code)
    if p is None or key is None:
        raise HTTPException(404, "no masked page")
    try:
        data = _crop_bytes(str(p), p.stat().st_mtime, key, 0.02, False)
    except KeyError:
        raise HTTPException(404, "unknown field")
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})
