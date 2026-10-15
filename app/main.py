"""Two Hands web app.

    cd twohands && python run_app.py            (or: uvicorn app.main:app --port 8000)
"""
from __future__ import annotations

import io
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image

from app import health as healthmod
from app import hero as heromod
from app import inbox as inboxmod
from app import numbers as numbersmod
from app import review as reviewmod
from app import store as storemod
from app import upload as uploadmod
from app.crops import field_boxes, mask_left_edge
from app.live import LiveManager, Refused
from twohands import REPO

app = FastAPI(title="Two Hands", version="1.0",
              description="A second keyer for self-checking paper forms: the model reads, the paper decides.",
              docs_url="/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=str(REPO / "static")), name="static")
templates = Jinja2Templates(directory=str(REPO / "templates"))
app.state.live = LiveManager()


def st() -> storemod.Store:
    return storemod.get_store()


def fmt_usd(x, d=5):
    return "n/a" if x is None else f"${x:.{d}f}"


def fmt_int(x):
    return "" if x is None else f"{x:,}"


templates.env.filters["usd"] = fmt_usd
templates.env.filters["int"] = fmt_int
templates.env.filters["field_list"] = lambda fields: [{"code": f["code"], "name": f["name"]} for f in fields]
templates.env.filters["plain"] = lambda t: re.sub(r"\s*\((spike|v\d)[^)]*\)", "", t or "").replace(" (spike)", "").replace("3_outage", "3, during an endpoint outage")
templates.env.globals["cited"] = numbersmod.CITED
templates.env.globals["amd_status"] = healthmod.status
templates.env.globals["STATUSES"] = inboxmod.STATUSES

# Evolus integration (additive): gate endpoint, case API, workflow callback; the panel reads the case records
from evolus import web as evolusweb  # noqa: E402
app.include_router(evolusweb.router)
templates.env.globals["evolus_case"] = evolusweb.panel

# Blind spot-check of the AI adjudication by a person (additive): /check, /check/results
from app import spotcheck as spotcheckmod  # noqa: E402
app.include_router(spotcheckmod.router)


def page(request: Request, name: str, nav: str, **ctx):
    return templates.TemplateResponse(request, name, {"nav": nav, **ctx})


# ------------------------------------------------------------------------------------------- pages
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    s = st()
    n = numbersmod.home(s)
    return page(request, "home.html", "home", n=n, schema=storemod.schema(),
                heroloop=heromod.loop_data(s), receipt=heromod.receipt(s, n["H"]))


@app.get("/forms", response_class=HTMLResponse)
def forms(request: Request):
    s = st()
    ine = [s.form_summary(k) for k in s.ine_claves()]
    ine.sort(key=lambda f: (not f["has_image"], f["accepted"] is not True, f["clave"]))
    sheets = []
    for sh in s.ledger.get("sheets", []):
        acc = sum(c["accepted"] for c in sh["cols"])
        sheets.append({"id": sh["id"], "station": sh["station"].replace("-", " ").title(), "years": sh["years"],
                       "acc": acc, "n": len(sh["cols"])})
    return page(request, "forms.html", "forms", ine=ine, sheets=sheets, run=s.runs.get(s.run_order()[0]) if s.run_order() else None)


@app.get("/form/{clave}", response_class=HTMLResponse)
def form(request: Request, clave: str, run: Optional[str] = None):
    s = st()
    if clave not in s.ine_claves():
        raise HTTPException(404, "unknown form")
    reads = [(rid, s.runs[rid]) for rid in s.run_order() + (["live"] if "live" in s.runs else [])
             if clave in s.runs[rid]["reads"]]
    r = s.runs[run]["reads"].get(clave) if run in s.runs else s.default_read(clave)
    if r is None:
        raise HTTPException(404, "no read for this form")
    ev = storemod.evaluate(r)
    off = s.official.get(clave, {})
    g = storemod.grade(r, off)
    rv = reviewmod.load().get(clave)
    return page(request, "form.html", "forms", clave=clave, r=r, ev=ev, off=off, g=g, reads=reads,
                run=s.runs[r.run_id], short={rid: s.short_name(rid) for rid, _ in reads},
                main_runs=[rid for rid, _ in reads if rid in (s.headline_run(), "spike-qwen", "live")],
                has_image=s.masked_image(clave) is not None, review=rv,
                live=request.app.state.live.status(), errors=[e for e in s.keying_errors() if e["clave"] == clave])


@app.get("/ledger/{sid}", response_class=HTMLResponse)
def ledger(request: Request, sid: str):
    s = st()
    sh = s.ledger_sheet(sid)
    if sh is None:
        raise HTTPException(404, "unknown sheet")
    return page(request, "ledger.html", "forms", sh=sh, meta=s.ledger.get("meta", {}),
                station=sh["station"].replace("-", " ").title())


@app.get("/review", response_class=HTMLResponse)
def review(request: Request):
    s = st()
    q = reviewmod.queue(s)
    return page(request, "review.html", "review", q=q, open_n=sum(1 for x in q if not x["review"]))


def _audit_items(s, H: dict) -> list[dict]:
    """The capture errors of the pre-registered run (from app/data/headline.json), ready for a card each."""
    out = []
    for x in H.get("keying_list", []):
        code = storemod.code_of(x["field"])
        out.append({**{k: v for k, v in x.items() if k != "field"}, "code": code, "name": storemod.name_of(x["field"]),
                    "evidence": storemod.neutralize(x.get("evidence", "")),
                    "img": f"/crop/{x['clave']}/{code}.jpg?pad=0.014&label=0" if s.masked_image(x["clave"]) else None})
    return out


@app.get("/audit", response_class=HTMLResponse)
def audit(request: Request):
    s = st()
    H = numbersmod.headline()
    items = _audit_items(s, H)
    feat = [i for i in items if i["clave"] == (H.get("featured") or {}).get("clave")]
    order = {"SOBRANTES": 0, "VOTARON": 1, "REPRESENTANTES": 2}
    feat.sort(key=lambda i: order.get(i["code"], 9))
    return page(request, "audit.html", "audit", H=H, L=numbersmod.lines(H), items=items, featured=feat)


@app.get("/results", response_class=HTMLResponse)
def results(request: Request):
    s = st()
    n = numbersmod.home(s)
    pilot = [s.run_metrics(rid) for rid in ("spike-gemma-v2", "spike-qwen", "spike-gemma-v1") if rid in s.runs]
    appendix = [s.run_metrics(rid) for rid in s.run_order() if rid.startswith("verify_")]
    live = s.run_metrics("live") if "live" in s.runs else None
    q = reviewmod.queue(s)
    return page(request, "results.html", "results", n=n, H=n["H"], L=n["L"], pilot=pilot, appendix=appendix, live=live,
                lm=s.ledger_metrics(), meta=s.ledger.get("meta", {}), queue_n=len(q),
                resolved=sum(1 for x in q if x["review"]))


# ------------------------------------------------------------------------------------------- images (masked only)
def _masked_or_404(clave: str) -> Path:
    p = st().masked_image(clave)
    if p is None:
        raise HTTPException(404, "no masked image")
    if storemod.MASKED not in p.resolve().parents:  # belt and braces
        raise HTTPException(403, "refused")
    return p


@app.get("/masked/{clave}.jpg")
def masked(clave: str):
    p = _masked_or_404(clave)
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"})


LABEL_X1 = 0.39   # right edge of the printed row-label (logo) column on vote rows


@lru_cache(maxsize=256)
def _crop_bytes(path: str, mtime: float, key: str, pad: float, label: bool = True) -> bytes:
    s = storemod.schema()
    box = field_boxes(s).get(key)
    if box is None:
        raise KeyError(key)
    x0, y0, x1, y1 = box
    if not label and x0 < LABEL_X1 < x1:
        x0 = LABEL_X1  # start right of the printed row label: words and digit boxes only, no logo
    edge = mask_left_edge(s)
    x1 = min(x1, edge - 0.002)
    im = Image.open(path)
    W, H = im.size
    c = im.crop((int(x0 * W), int(max(0, y0 - pad) * H), int(x1 * W), int(min(1, y1 + pad) * H))).convert("RGB")
    buf = io.BytesIO()
    c.save(buf, "JPEG", quality=85)
    return buf.getvalue()


@app.get("/crop/{clave}/{code}.jpg")
def crop(clave: str, code: str, pad: float = 0.0, label: int = 1):
    p = _masked_or_404(clave)
    key = storemod.key_of(code)
    if key is None:
        raise HTTPException(404, "unknown field")
    pad = max(0.0, min(pad, 0.05))
    try:
        data = _crop_bytes(str(p), p.stat().st_mtime, key, pad, bool(label))
    except KeyError:
        raise HTTPException(404, "unknown field")
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"})


# ------------------------------------------------------------------------------------------- APIs
@app.get("/api/form/{clave}")
def api_form(clave: str, run: Optional[str] = None):
    s = st()
    r = s.runs[run]["reads"].get(clave) if run in s.runs else s.default_read(clave)
    if r is None:
        raise HTTPException(404, "unknown form")
    ev = storemod.evaluate(r)
    for f in ev["fields"]:
        f.pop("label", None)  # the printed row label (party logos) is never served
    return storemod.public({"clave": clave, "run": r.run_id, "verdict": ev, "official": s.official.get(clave),
                            "grade": storemod.grade(r, s.official.get(clave)), "has_image": s.masked_image(clave) is not None})


@app.post("/api/review/{clave}")
async def api_review(clave: str, request: Request):
    body = await request.json()
    try:
        rec = reviewmod.resolve(st(), clave, body.get("values") or {}, action=body.get("action", "resolve"),
                                note=body.get("note", ""), labels_confirmed=bool(body.get("labels_confirmed")))
    except KeyError:
        raise HTTPException(404, "unknown form")
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return storemod.public(rec)


@app.delete("/api/review/{clave}")
def api_review_reset(clave: str):
    reviewmod.reset(clave)
    return {"ok": True}


@app.get("/api/live/status")
def live_status(request: Request):
    return request.app.state.live.status()


def _refused(e: Refused) -> JSONResponse:
    return JSONResponse({"refused": e.code, "message": e.message},
                        status_code=409 if e.code in ("busy", "no_image") else 503)


@app.post("/api/live/{clave}")
def live_start(clave: str, request: Request):
    """Queue a live read of one form's masked page on AMD. Returns the job id and its place in the queue."""
    s = st()
    if clave not in s.ine_claves():
        raise HTTPException(404, "unknown form")
    m = request.app.state.live
    try:
        job = m.start(clave, s.masked_image(clave))
    except Refused as e:
        return _refused(e)
    return {"job": job.id, "position": m.position(job), "status_url": f"/api/jobs/{job.id}"}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, request: Request):
    """State of a live read: queued (with position), running, done or failed; elapsed time; stages; verdict."""
    j = request.app.state.live.job_status(job_id)
    if j is None:
        raise HTTPException(404, "unknown job")
    return j


@app.get("/api/live/events/{job_id}")
def live_events(job_id: str, request: Request):
    return StreamingResponse(request.app.state.live.stream(job_id), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/healthz")
def healthz():
    s = st()
    return {"ok": True, "runs": {k: len(v["reads"]) for k, v in s.runs.items()}, "ledger_sheets": len(s.ledger.get("sheets", []))}


# ------------------------------------------------------------------------------------------- try it: your own photo
def _flist():
    return [{"code": storemod.code_of(f["key"]), "name": storemod.name_of(f["key"])} for f in storemod.schema()["fields"]]


@app.get("/try", response_class=HTMLResponse)
def try_page(request: Request):
    return page(request, "try.html", "try", samples=uploadmod.SAMPLES, good=uploadmod.GOOD_PHOTO, up=None, ev=None,
                flist=_flist())


@app.get("/try/{uid}", response_class=HTMLResponse)
def try_result(request: Request, uid: str):
    m = uploadmod.meta(uid)
    if m is None or uploadmod.page_path(uid) is None:
        raise HTTPException(404, "unknown upload")
    ev = None
    if m.get("read"):
        rd = m["read"]
        ev = storemod.evaluate(storemod.read_from_core(uid, "live", {"clave": uid, "parsed": rd.get("parsed"),
                                                                     "usage": rd.get("usage"), "secs": rd.get("secs")}))
    return page(request, "try.html", "try", samples=uploadmod.SAMPLES, good=uploadmod.GOOD_PHOTO, up=m, ev=ev,
                flist=_flist())


def _queue_upload(request: Request, res: dict) -> dict:
    if not res.get("ok"):
        return res
    uid = res["id"]
    out = {"ok": True, "id": uid, "page_url": f"/try/{uid}", "masked_url": f"/upload/{uid}.jpg",
           "fallback": res["info"].get("sample_of"), "locator": res["info"].get("locator")}
    m = request.app.state.live
    try:
        job = m.start(uid, uploadmod.page_path(uid), kind="upload", out_dir=uploadmod.UPLOADS,
                      fallback=res["info"].get("sample_of"))
        out.update(job=job.id, position=m.position(job))
    except Refused as e:
        out.update(refused=e.code, message=e.message)
    return out


@app.post("/api/upload")
async def api_upload(request: Request):
    """Body: the photo itself (image/jpeg or image/png), not multipart, so it is never spooled to disk.
    Located and masked in memory; only the masked page is stored; a live read is queued."""
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > uploadmod.MAX_BYTES:
            return JSONResponse({"ok": False, "code": "not_a_photo", "message": "The photo is larger than 20 MB."},
                                status_code=413)
    res = uploadmod.process(bytes(data))
    del data
    if not res["ok"]:
        return JSONResponse(res, status_code=422)
    return _queue_upload(request, res)


@app.post("/api/upload/sample/{name}")
def api_upload_sample(name: str, request: Request):
    res = uploadmod.process_sample(name)
    if not res["ok"]:
        return JSONResponse(res, status_code=404 if res["code"] == "unknown_sample" else 422)
    return _queue_upload(request, res)


@app.post("/api/upload/{uid}/read")
def api_upload_read(uid: str, request: Request):
    p = uploadmod.page_path(uid)
    m = uploadmod.meta(uid)
    if p is None or m is None:
        raise HTTPException(404, "unknown upload")
    try:
        job = request.app.state.live.start(uid, p, kind="upload", out_dir=uploadmod.UPLOADS, fallback=m.get("sample_of"))
    except Refused as e:
        return _refused(e)
    return {"job": job.id, "position": request.app.state.live.position(job)}


@app.get("/upload/{uid}.jpg")
def upload_image(uid: str):
    p = uploadmod.page_path(uid)
    if p is None:
        raise HTTPException(404, "no masked page")
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


# ------------------------------------------------------------------------------------------- inbox + export
@app.get("/inbox", response_class=HTMLResponse)
def inbox(request: Request):
    s = st()
    rs = inboxmod.rows(s)
    return page(request, "inbox.html", "inbox", rows=rs, k=inboxmod.kpis(rs), H=numbersmod.headline(),
                live=request.app.state.live.status())


def _export_rows(status: Optional[str]):
    rs = inboxmod.rows(st())
    if status:
        rs = [r for r in rs if r["status"] in status.split(",")]
    return rs


@app.get("/api/export.json")
def export_json(status: Optional[str] = None):
    """Captured records as JSON (Option NN field codes, no party names). ?status=accepted,resolved filters."""
    return JSONResponse(inboxmod.export_json(_export_rows(status)),
                        headers={"Content-Disposition": "inline; filename=twohands-records.json"})


@app.get("/api/export.csv")
def export_csv(status: Optional[str] = None):
    """Captured records as CSV, one row per form, one column per field (Option 01 ... TOTAL)."""
    return Response(inboxmod.export_csv(_export_rows(status)), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=twohands-records.csv"})


@app.get("/api", response_class=HTMLResponse)
def api_page(request: Request):
    base = str(request.base_url).rstrip("/")
    return page(request, "api.html", "api", base=base)


@app.get("/favicon.ico")
def favicon():
    return FileResponse(REPO / "static" / "favicon.png", media_type="image/png")
