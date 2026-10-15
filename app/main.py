"""Two Hands web app.

    cd twohands && python run_app.py            (or: uvicorn app.main:app --port 8000)
"""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image

from app import numbers as numbersmod
from app import review as reviewmod
from app import store as storemod
from app.crops import field_boxes, mask_left_edge
from app.live import LiveManager, Refused
from twohands import REPO

app = FastAPI(title="Two Hands", docs_url=None, redoc_url=None)
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
templates.env.globals["cited"] = numbersmod.CITED

# Evolus integration (additive): gate endpoint, case API, workflow callback; the panel reads the case records
from evolus import web as evolusweb  # noqa: E402
app.include_router(evolusweb.router)
templates.env.globals["evolus_case"] = evolusweb.panel


def page(request: Request, name: str, nav: str, **ctx):
    return templates.TemplateResponse(request, name, {"nav": nav, **ctx})


# ------------------------------------------------------------------------------------------- pages
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    s = st()
    return page(request, "home.html", "home", n=numbersmod.home(s), schema=storemod.schema())


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


@app.get("/audit", response_class=HTMLResponse)
def audit(request: Request):
    s = st()
    return page(request, "audit.html", "audit", errs=s.keying_errors())


@app.get("/results", response_class=HTMLResponse)
def results(request: Request):
    s = st()
    runs = [s.run_metrics(rid) for rid in s.run_order() + (["live"] if "live" in s.runs else [])]
    n = numbersmod.home(s)
    # failure case 1: forms routed by the row-label check although every value was right (core runs)
    label_fp = []
    for rid in s.run_order():
        if s.runs[rid]["kind"] != "core":
            continue
        for k, r in s.runs[rid]["reads"].items():
            ev = storemod.evaluate(r)
            g = storemod.grade(r, s.official.get(k))
            if k in {x["clave"] for x in label_fp}:
                continue
            if not ev["accepted"] and g.get("graded") and not g["wrong_adj"] and any(f["status"] == "label" for f in ev["fields"]):
                label_fp.append({"clave": k, "run": rid, "n_label": sum(f["status"] == "label" for f in ev["fields"]),
                                 "other": [x for x in ev["reasons"] if "label" not in x]})
    q = reviewmod.queue(s)
    return page(request, "results.html", "results", runs=runs, n=n, lm=s.ledger_metrics(), meta=s.ledger.get("meta", {}),
                label_fp=label_fp, queue_n=len(q), resolved=sum(1 for x in q if x["review"]),
                headline_id=s.headline_run())


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


@lru_cache(maxsize=256)
def _crop_bytes(path: str, mtime: float, key: str, pad: float) -> bytes:
    s = storemod.schema()
    box = field_boxes(s).get(key)
    if box is None:
        raise KeyError(key)
    x0, y0, x1, y1 = box
    edge = mask_left_edge(s)
    x1 = min(x1, edge - 0.002)
    im = Image.open(path)
    W, H = im.size
    c = im.crop((int(x0 * W), int(max(0, y0 - pad) * H), int(x1 * W), int(min(1, y1 + pad) * H))).convert("RGB")
    buf = io.BytesIO()
    c.save(buf, "JPEG", quality=85)
    return buf.getvalue()


@app.get("/crop/{clave}/{code}.jpg")
def crop(clave: str, code: str, pad: float = 0.0):
    p = _masked_or_404(clave)
    key = storemod.key_of(code)
    if key is None:
        raise HTTPException(404, "unknown field")
    pad = max(0.0, min(pad, 0.05))
    try:
        data = _crop_bytes(str(p), p.stat().st_mtime, key, pad)
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


@app.post("/api/live/{clave}")
def live_start(clave: str, request: Request):
    s = st()
    if clave not in s.ine_claves():
        raise HTTPException(404, "unknown form")
    try:
        job = request.app.state.live.start(clave, s.masked_image(clave))
    except Refused as e:
        return JSONResponse({"refused": e.code, "message": e.message},
                            status_code=409 if e.code in ("busy", "no_image") else 503)
    return {"job": job.id}


@app.get("/api/live/events/{job_id}")
def live_events(job_id: str, request: Request):
    return StreamingResponse(request.app.state.live.stream(job_id), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/healthz")
def healthz():
    s = st()
    return {"ok": True, "runs": {k: len(v["reads"]) for k, v in s.runs.items()}, "ledger_sheets": len(s.ledger.get("sheets", []))}
