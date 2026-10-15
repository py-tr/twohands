"""Privacy first: rectify, black out every name/signature region, downscale, store only the masked page.

    python -m twohands.mask RAW.jpg OUT.jpg [--layout movil|escaner]

INE actas carry the handwritten names and signatures of the polling officials (section 11) and the party
representatives (section 12) in the right column. The page is rectified onto the canonical frame
(``twohands.register``), the schema's mask rectangles are filled black, and only that image is written.
Tiles for the model are cut from the masked page and never reach into the mask (tests/test_mask.py).
A page that cannot be located raises ``NotLocated``: nothing is stored or sent; the form goes to a person.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from twohands import register, schema

JPEG_QUALITY = 85


def apply_mask(page: Image.Image, rects) -> Image.Image:
    page = page.copy()
    W, H = page.size
    d = ImageDraw.Draw(page)
    for x0, y0, x1, y1 in rects:
        d.rectangle([int(x0 * W), int(y0 * H), int(round(x1 * W)), int(round(y1 * H))], fill=(0, 0, 0))
    return page


def prepare(raw: Image.Image | str | Path, layout_kind: str = "movil", s: dict | None = None):
    """raw image -> (masked canonical page, info). Raises register.NotLocated."""
    s = s or schema.load()
    if isinstance(raw, Image.Image):
        img = raw
    else:
        with Image.open(raw) as im:  # load and close at once: the raw file must be deletable right after
            im.load()
            img = im.copy()
    loc = register.rectify(img, s["layout"], schema.template(s), ref=schema.reference(s))
    page = apply_mask(loc.image, schema.mask_rects(s, layout_kind))
    info = {"score": loc.score, "margin": loc.margin, "ecc": getattr(loc, "ecc", None), "markers_found": loc.markers_found,
            "size": list(page.size), "layout": layout_kind}
    return page, info


def save(page: Image.Image, out: str | Path) -> None:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    page.convert("RGB").save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)


def tiles(page: Image.Image, s: dict | None = None) -> list[Image.Image]:
    s = s or schema.load()
    W, H = page.size
    return [page.crop((int(a * W), int(b * H), int(c * W), int(d * H))) for a, b, c, d in
            (t["box"] for t in s["layout"]["tiles"])]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw"); ap.add_argument("out"); ap.add_argument("--layout", default="movil")
    a = ap.parse_args(argv)
    try:
        page, info = prepare(a.raw, a.layout)
    except register.NotLocated as e:
        print("NOT LOCATED:", e); return 2
    save(page, a.out); print(info); return 0


if __name__ == "__main__":
    sys.exit(main())
