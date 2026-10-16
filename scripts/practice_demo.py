"""Synthetic stand-in for a hand-filled practice sheet, and its ONE live read. LABELLED SYNTHETIC.

    python scripts/practice_demo.py            # fill + phone-photo simulation + registration only (no model call)
    python scripts/practice_demo.py --live     # ... then ONE live read on AMD (Gemma) + the gate -> results/practice_sheet_demo.md

The blank sheet is the PNG preview at screen resolution (static/sheet/two-hands-sheet.png, 150 dpi); the amounts
are drawn in code with a script font (Czech number words + digits) in blue "ink", then the page is put on a table,
turned, warped in perspective, unevenly lit and JPEG-compressed, as a stand-in for a phone photo of a printed sheet.
It is not handwriting and not a photo: a person will fill a real one by hand (Czech, English) and photograph it.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

PNG = REPO / "static" / "sheet" / "two-hands-sheet.png"
OUT_MD = REPO / "results" / "practice_sheet_demo.md"
OUT_JSON = REPO / "results" / "practice_sheet_demo.json"

# Czech number words; the digits agree on every row and the rows sum to TOTAL (225)
CZECH = [(12, "dvanáct"), (7, "sedm"), (23, "dvacet tři"), (5, "pět"), (18, "osmnáct"), (40, "čtyřicet"),
         (9, "devět"), (31, "třicet jedna"), (14, "čtrnáct"), (66, "šedesát šest")]
TOTAL = (225, "dvě stě dvacet pět")
assert sum(v for v, _ in CZECH) == TOTAL[0]


def _hand(size: int):
    for n in ("segoepr.ttf", "segoesc.ttf", "comic.ttf", "DejaVuSans-Oblique.ttf"):
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def fill(rows=CZECH, total=TOTAL, seed: int = 7) -> Image.Image:
    """Draw the amounts onto the blank sheet, at the schema's boxes, in a handwriting-like script font."""
    from app import practice
    s = practice.schema()
    rng = np.random.default_rng(seed)
    im = Image.open(PNG).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    ink = (26, 50, 130)
    for f, (v, words) in zip(s["fields"], list(rows) + [total]):
        x0, y0, x1, y1 = f["words_box"]
        hy = int((y1 - y0) * H)
        d.text((int(x0 * W) + 18 + int(rng.integers(0, 14)), int(y0 * H) + int(hy * 0.12) + int(rng.integers(-3, 4))),
               words, font=_hand(int(hy * 0.58)), fill=ink)
        bx0, by0, bx1, by1 = f["box"]
        bw = (bx1 - bx0) * W / 3
        for j, ch in enumerate(str(v).rjust(3)):
            if ch != " ":
                d.text((int(bx0 * W + j * bw + bw * 0.28) + int(rng.integers(-3, 4)), int(by0 * H) + int(hy * 0.06)),
                       ch, font=_hand(int(hy * 0.72)), fill=ink)
    return im


def as_phone_photo(page: Image.Image, angle: float = 4.0, seed: int = 3, size=(3000, 4000)) -> Image.Image:
    """Page on a wooden-ish table, turned by ``angle``, perspective-warped, unevenly lit, noisy, JPEG."""
    import cv2
    rng = np.random.default_rng(seed)
    W, H = size
    bg = np.zeros((H, W, 3), np.float32)
    bg[:] = (122, 98, 80)
    bg += rng.normal(0, 6, bg.shape).astype(np.float32)
    pw, ph = page.size
    sc = 0.78 * H / ph
    cx, cy = W / 2 + rng.uniform(-80, 80), H / 2 + rng.uniform(-80, 80)
    a = np.deg2rad(angle)
    R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    corners = np.array([[-pw / 2, -ph / 2], [pw / 2, -ph / 2], [pw / 2, ph / 2], [-pw / 2, ph / 2]]) * sc
    dst = (corners @ R.T) + [cx, cy]
    dst[0] += [rng.uniform(-40, 40), rng.uniform(-40, 40)]   # perspective: corners pulled unevenly
    dst[1] += [rng.uniform(-70, 0), rng.uniform(-20, 40)]
    dst[2] += [rng.uniform(0, 60), rng.uniform(-30, 30)]
    src = np.float32([[0, 0], [pw, 0], [pw, ph], [0, ph]])
    Hm = cv2.getPerspectiveTransform(src, dst.astype(np.float32))
    pg = np.asarray(page.convert("RGB"), np.float32)
    warped = cv2.warpPerspective(pg, Hm, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
    m = cv2.warpPerspective(np.ones((ph, pw), np.float32), Hm, (W, H))[..., None]
    out = warped * m + bg * (1 - m)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    light = 0.80 + 0.22 * (xx / W) - 0.10 * (yy / H)          # uneven light, a soft shadow to one side
    out = out * light[..., None] * np.array([1.0, 0.97, 0.90], np.float32)  # warm indoor light
    out += rng.normal(0, 4, out.shape).astype(np.float32)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def registration_checks() -> list[dict]:
    """Phone-photo tolerance: the automatic registration on simulated photos at several angles and orientations."""
    from app import builder as B, practice
    page = fill()
    out = []
    for name, angle, rot in [("straight", 0.0, 0), ("turned 4°", 4.0, 0), ("turned -9°", -9.0, 0),
                             ("turned 15°", 15.0, 0), ("turned -25°", -25.0, 0), ("landscape (90°)", 3.0, 90),
                             ("upside down", -2.0, 180)]:
        ph = as_phone_photo(page, angle=angle, seed=int(abs(angle) * 10) + rot)
        if rot:
            ph = ph.rotate(rot, expand=True)
        t = time.time()
        try:
            pg, info = practice.register_photo(ph)
            a = np.asarray(pg.convert("L").resize((310, 438)), float)
            b = np.asarray(page.convert("L").resize((310, 438)), float)
            corr = float(np.corrcoef(a.ravel(), b.ravel())[0, 1])
            out.append({"case": name, "ok": corr > 0.6, "locator": info.get("locator"),
                        "deskew_deg": info.get("deskew_deg"), "corr_with_page": round(corr, 3),
                        "secs": round(time.time() - t, 2)})
        except B.NotRegistered as e:
            out.append({"case": name, "ok": False, "error": str(e)[:120], "secs": round(time.time() - t, 2)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="ONE live read on AMD (Gemma) and the gate")
    ap.add_argument("--save", help="write the synthetic photo here (jpg)")
    a = ap.parse_args(argv)
    from app import builder as B, practice
    checks = registration_checks()
    for c in checks:
        print(c)
    photo = as_phone_photo(fill(), angle=4.0, seed=11)
    if a.save:
        photo.save(a.save, quality=88)
    if not a.live:
        return 0
    page, info = practice.register_photo(photo)
    s = practice.schema()
    tmp = REPO / "results" / "practice_sheet_demo_page.jpg"
    page.save(tmp, quality=90)
    from app import livemodel
    pick = livemodel.chooser.choose(block=True)  # Gemma when GET /models lists it, else the documented fallback
    print("model:", pick["model"], "(fallback)" if pick["fallback"] else "")
    row = B.default_read(pick["key"], tmp, s)
    g = B.gate_schema(row.get("parsed"), s)
    view = B.gate_view(g, s)
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "synthetic": True, "model": row.get("model"),
           "secs": row.get("secs"), "usage": row.get("usage"), "error": row.get("error"), "register": info,
           "gemma_listed": not pick["fallback"], "registration_checks": checks, "truth": {"rows": [v for v, _ in CZECH], "total": TOTAL[0]},
           "content": row.get("content"), "parsed": row.get("parsed"), **view}
    OUT_JSON.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: rec[k] for k in ("model", "secs", "accepted", "reasons")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
