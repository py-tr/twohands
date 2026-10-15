"""Try it with your own photo: a photo of an INE type-2 tally sheet -> located, straightened, masked IN MEMORY
by the core (twohands.mask.prepare, imported, not changed) -> ONLY the masked page is written -> a live read is
queued through the same live-read path (budget guard, one at a time).

Privacy rules (tests/test_app_upload.py):
  * The raw upload is never written to disk: the request body is read into memory (no multipart spooling, no
    temp file), decoded with PIL, and dropped.
  * A page the core cannot locate is not stored at all (NotLocated -> a friendly message, nothing on disk).
  * What is stored is the masked canonical page (names-and-signatures column blacked out) plus a small JSON
    note (locator scores, time). Upload ids are random; uploads live under app/state/uploads/ (git-ignored).
"""
from __future__ import annotations

import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps, UnidentifiedImageError

from app import store as storemod

UPLOADS = storemod.STATE / "uploads"
MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 60_000_000
SAMPLES = {  # "Use a sample photo": existing masked pages, sent through the same pipeline
    "clean": {"clave": "120293C0100", "label": "A clean form", "note": "phone photo; every identity holds"},
    "problem": {"clave": "211294C0100", "label": "A form with a problem", "note": "phone photo; TOTAL digits and words disagree"},
}
_ID = re.compile(r"^u[0-9a-f]{12}$")

GOOD_PHOTO = [
    "The whole sheet is in the frame, all four corners visible.",
    "Flat on a table, shot from straight above, not at an angle.",
    "Even light: no strong shadow or glare across the number boxes.",
    "Sharp: hold still, tap to focus; no fingers over the boxes.",
    "It is the type-2 tally sheet (the one with 15 option rows and a TOTAL).",
]


class NotAPhoto(Exception):
    pass


def valid_id(uid: str) -> bool:
    return bool(_ID.match(uid or ""))


def page_path(uid: str) -> Optional[Path]:
    if not valid_id(uid):
        return None
    p = (UPLOADS / f"{uid}.jpg").resolve()
    if UPLOADS.resolve() not in p.parents or not p.is_file():
        return None
    return p


def meta(uid: str) -> Optional[dict]:
    if not valid_id(uid):
        return None
    try:
        m = json.loads((UPLOADS / f"{uid}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        m["read"] = json.loads((UPLOADS / f"{uid}.read.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        m["read"] = None
    return m


def decode(data: bytes) -> Image.Image:
    """Bytes in memory -> upright RGB image in memory. Nothing touches the disk."""
    if not data:
        raise NotAPhoto("The file is empty.")
    if len(data) > MAX_BYTES:
        raise NotAPhoto("The photo is larger than 20 MB. Please send a smaller one.")
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width * im.height > MAX_PIXELS:
                raise NotAPhoto("The photo has too many pixels. Please send a smaller one.")
            im = ImageOps.exif_transpose(im)
            im.load()
            return im.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise NotAPhoto("That file is not a photo we can open (JPEG or PNG please).") from e


def process(data: bytes, source: str = "upload", sample_of: Optional[str] = None, layout: str = "movil") -> dict:
    """Locate, straighten and mask in memory; store only the masked page. Returns a result dict:
    {"ok": True, "id": ..., "info": ...} or {"ok": False, "code": "not_located"|"not_a_photo", "message": ...}."""
    from twohands import mask, register  # the core, imported and used as is

    try:
        img = decode(data)
    except NotAPhoto as e:
        return {"ok": False, "code": "not_a_photo", "message": str(e)}
    finally:
        data = None  # noqa: F841  drop our reference to the raw bytes
    try:
        page, info = mask.prepare(img, layout)
    except register.NotLocated as e:
        return {"ok": False, "code": "not_located", "detail": str(e)[:160],
                "message": "We could not find the form's frame on this photo, so nothing was stored or sent. "
                           "A page that cannot be located always goes to a person; for a demo read, try another photo."}
    finally:
        del img
    uid = "u" + uuid.uuid4().hex[:12]
    UPLOADS.mkdir(parents=True, exist_ok=True)
    mask.save(page, UPLOADS / f"{uid}.jpg")
    note = {"id": uid, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": source,
            "sample_of": sample_of, "layout": layout,
            "locator": {k: info.get(k) for k in ("locator", "score", "margin", "ecc", "landmark_worst_px")}}
    (UPLOADS / f"{uid}.json").write_text(json.dumps(note, indent=1), encoding="utf-8")
    return {"ok": True, "id": uid, "info": note}


def process_sample(name: str) -> dict:
    s = SAMPLES.get(name)
    if s is None:
        return {"ok": False, "code": "unknown_sample", "message": "No such sample."}
    p = storemod.get_store().masked_image(s["clave"])
    if p is None:
        return {"ok": False, "code": "unknown_sample", "message": "The sample page is not available."}
    return process(p.read_bytes(), source="sample", sample_of=s["clave"])
