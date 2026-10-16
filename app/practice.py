"""Practice sheet on /try: "print it, fill it in your language, photograph it". Demonstration, not a measurement.

The sheet (static/sheet/two-hands-sheet.pdf, made by scripts/make_sheet.py) has four black corner markers like the
INE acta, 10 numbered rows (words on the left, 3 digit boxes on the right) and a TOTAL row. Its schema
(schemas/practice_sheet.yaml, made through the schema builder's API) runs through the builder's own path:

  photo (in memory) -> registered by the corner markers (the core blob finder and frame search, with the portrait
  normalisation in ``locate``; orientation template; a few in-plane rotations are tried
  for a phone photo held at an angle; or the four corners a person clicked) -> stored straightened (the sheet has no
  personal-data area, so the mask is empty) -> ONE live read on AMD through the builder's live path (same budget
  guard, one read at a time) with the schema's reader note (the words may be in any language; null when the model
  cannot tell, never a guess) -> the core gate (twohands.gate.gate).

The gate's verdict: accepted only if every row's words were read and equal its digits, and the rows sum to TOTAL.
A row whose words came back null (a language or a hand the model could not read) routes, with the field named;
the gate never accepts a row on its digits alone (``words_required: true`` in the schema, checked by
``app.builder.gate_schema`` on top of the frozen core gate, which is used as is).
"""
from __future__ import annotations

import functools
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image

from app import builder as B
from app import live as livemod
from app import upload as uploadmod
from twohands import REPO
from twohands import mask as maskmod
from twohands import register

router = APIRouter()

SCHEMA_PATH = REPO / "schemas" / "practice_sheet.yaml"
PDF_URL = "/static/sheet/two-hands-sheet.pdf"
PNG_URL = "/static/sheet/two-hands-sheet.png"
FORM = "practice_sheet"
LABEL = "Practice sheet (any language)"
CALL = "Print this sheet (PDF), fill it in your language, photograph it."
DEMO = "Demonstration, not a measurement."
# in-plane angles tried when the markers are not found as drawn: the locator wants near-axis-aligned squares
ANGLES = (0.0, 8.0, -8.0, 16.0, -16.0, 24.0, -24.0, 32.0, -32.0, 40.0, -40.0)


@functools.lru_cache(maxsize=1)
def schema() -> dict:
    return B.load_yaml(SCHEMA_PATH)


def locate(img: Image.Image, s: dict, min_score: float = 0.25, min_margin: float = 0.08,
           work: int = 1600) -> tuple[Image.Image, dict]:
    """The corner-marker registration of ``twohands.register.rectify`` (its blob finder, frame search and template
    correlation, imported and used as is), for a PORTRAIT page. The core rectify measures the frame aspect as
    width / height and the marker size against the width, which only fits landscape forms (the actas); the core is
    frozen, so the portrait normalisation lives here: aspect = long / short side, marker size / long side.
    The sheet's orientation template (its dark title band) picks the upright of the four rotations.
    Raises register.NotLocated."""
    import cv2
    import numpy as np
    from PIL import ImageOps
    from twohands import schema as schemamod

    img = ImageOps.exif_transpose(img).convert("RGB")
    W, H = img.size
    sc = work / max(W, H)
    gray = np.asarray(img.convert("L").resize((max(1, round(W * sc)), max(1, round(H * sc)))))
    cands = register._candidates(gray)
    can = s["layout"]["canonical"]
    cw, ch = can["size"]
    M = (np.array(can["markers"], dtype=float) * [cw, ch]).astype(np.float32)
    fw, fh = float(np.linalg.norm(M[1] - M[0])), float(np.linalg.norm(M[3] - M[0]))
    aspect, size_ratio = max(fw, fh) / min(fw, fh), float(can["marker_size"]) * fw / max(fw, fh)
    frames = sorted(register._frames(cands, aspect, size_ratio), key=lambda f: -f[0])[:8]
    if not frames:
        raise register.NotLocated(f"corner markers not found ({len(cands)} candidates)")
    tpl = schemamod.template(s)
    gray_full = np.asarray(img.convert("L"))
    small = np.diag([register.TEMPLATE_SIZE[0] / cw, register.TEMPLATE_SIZE[1] / ch, 1.0])
    best = None
    for _area, q, nfound in frames:
        scored = []
        for rot in range(4):
            src = np.roll(q / sc, -rot, axis=0).astype(np.float32)
            Hm = cv2.getPerspectiveTransform(src, M)
            v = cv2.warpPerspective(gray_full, small @ Hm, register.TEMPLATE_SIZE, flags=cv2.INTER_AREA,
                                    borderValue=255).astype(float)
            scored.append((register._corr(v, tpl), Hm))
        scored.sort(key=lambda x: -x[0])
        cand = (scored[0][0], scored[0][0] - scored[1][0], scored[0][1], nfound)
        if best is None or cand[0] > best[0]:
            best = cand
    score, margin, Hm, nfound = best
    if score < min_score or margin < min_margin:
        raise register.NotLocated(f"page does not match the sheet (score {score:.2f}, margin {margin:.2f})")
    out = cv2.warpPerspective(np.asarray(img), Hm, (cw, ch), flags=cv2.INTER_AREA, borderValue=(255, 255, 255))
    page = maskmod.apply_mask(Image.fromarray(out), schemamod.mask_rects(s, "movil") or [])  # empty: no personal data
    return page, {"locator": "corner markers + orientation template", "score": round(float(score), 3),
                  "margin": round(float(margin), 3), "markers_found": int(nfound), "size": [cw, ch]}


def register_photo(img: Image.Image, corners: Optional[list] = None) -> tuple[Image.Image, dict]:
    """Photo in memory -> straightened practice page (mask empty), info. Raises B.NotRegistered (nothing stored)."""
    s = schema()
    if corners is not None:
        from twohands import corners as cornersmod
        try:
            return cornersmod.prepare(img, corners, "movil", s)
        except register.NotLocated as e:
            raise B.NotRegistered(f"Those four points did not give us the sheet ({e}). Click the centre of each "
                                  "black corner square once, then try again.")
    last = None
    for a in ANGLES:
        im = img if a == 0 else img.rotate(a, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
        try:
            page, info = locate(im, s)
        except register.NotLocated as e:
            last = B.NotRegistered(f"The four corner markers were not found ({e}). Retake the photo with all four "
                                   "black corner squares in the frame, flat, from above.")
            continue
        info["deskew_deg"] = a
        return page, info
    raise last or B.NotRegistered("The four corner markers were not found.")


def tid_meta(tid: str) -> Optional[dict]:
    p = B.masked_test_page(tid)
    if p is None:
        return None
    try:
        m = json.loads((B.TESTS_DIR / f"{tid}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if m.get("schema") != FORM:
        return None
    try:
        m["read"] = json.loads((B.TESTS_DIR / f"{tid}.read.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        m["read"] = None
    return m


def verdict(read: Optional[dict]) -> Optional[dict]:
    """A stored builder read -> the rows and the verdict line for the page."""
    if not read:
        return None
    rows = []
    for f in read.get("fields") or []:
        k = f["key"]
        name = "TOTAL" if k == "TOTAL" else f"Row {int(k[3:])}"
        rows.append({"key": k, "name": name, "w": f.get("w"), "n": f.get("n"), "ok": f.get("ok")})
    bad = [r["key"] for r in rows if not r["ok"]]
    if read.get("accepted"):
        line = "Accepted: every row's words equal its digits, and rows 1 to 10 sum to TOTAL."
    else:
        line = "Routed to a person: " + ", ".join(bad or ["the read"]) + "."
    return {"accepted": bool(read.get("accepted")), "line": line, "rows": rows, "reasons": read.get("reasons") or [],
            "identities": read.get("identities") or [], "model": read.get("model"), "secs": read.get("secs"),
            "cost": read.get("cost")}


def store_page(page: Image.Image, info: dict, source: str = "upload") -> str:
    tid = B._new_tid()
    B.TESTS_DIR.mkdir(parents=True, exist_ok=True)
    maskmod.save(page, B.TESTS_DIR / f"{tid}.jpg")
    (B.TESTS_DIR / f"{tid}.json").write_text(json.dumps({
        "id": tid, "schema": FORM, "info": info, "source": source,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}), encoding="utf-8")
    return tid


def queue(request: Request, img: Image.Image, corners: Optional[list] = None) -> JSONResponse | dict:
    try:
        page, info = register_photo(img, corners)
    except B.NotRegistered as e:
        return JSONResponse({"ok": False, "code": "not_located", "manual": corners is not None,
                             "message": "We could not find the sheet's four corner squares on this photo, so nothing "
                                        "was stored or sent. " + ("" if corners is None else str(e))},
                            status_code=422)
    tid = store_page(page, info)
    out = {"ok": True, "id": tid, "page_url": f"/try/practice/{tid}", "masked_url": f"/builder/test/{tid}.jpg",
           "info": info}
    m = B.builder_live(request)
    try:
        job = m.start_test(tid, B.TESTS_DIR / f"{tid}.jpg", schema())
        out.update(job=job.id, position=m.position(job), status_url=f"/api/builder/job/{job.id}")
    except livemod.Refused as e:
        out.update(refused=e.code, message=e.message)
    return out


@router.post("/api/try/practice")
async def api_try_practice(request: Request, corners: Optional[str] = None):
    """Body: the photo itself (bytes, never written). ?corners=x1,y1,...: four clicked corner markers (photo pixels)."""
    try:
        pts = uploadmod.parse_corners(corners)
    except ValueError:
        return JSONResponse({"ok": False, "code": "bad_corners", "message": "Click the four corner markers."},
                            status_code=422)
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > uploadmod.MAX_BYTES:
            return JSONResponse({"ok": False, "code": "not_a_photo", "message": "The photo is larger than 20 MB."},
                                status_code=413)
    try:
        img = uploadmod.decode(bytes(data))
    except uploadmod.NotAPhoto as e:
        return JSONResponse({"ok": False, "code": "not_a_photo", "message": str(e)}, status_code=422)
    del data
    return queue(request, img, pts)


@router.get("/try/practice/{tid}", response_class=HTMLResponse)
def try_practice(request: Request, tid: str, job: Optional[str] = None):
    from app.main import templates
    m = tid_meta(tid)
    if m is None:
        raise HTTPException(404, "unknown practice sheet")
    return templates.TemplateResponse(request, "try_practice.html", {
        "nav": "try", "up": m, "v": verdict(m.get("read")), "job": job, "pdf": PDF_URL, "png": PNG_URL,
        "call": CALL, "demo": DEMO, "rows": [("TOTAL" if f["key"] == "TOTAL" else f"Row {int(f['key'][3:])}")
                                             for f in schema()["fields"]]})
