"""Register a page from four corner markers a person clicked, for photos the automatic locator misses.

``register.rectify_v2`` finds the four black corner markers itself. When it cannot (``NotLocated``), a person can
click them on the photo instead. This module warps the photo onto the SAME canonical page as the locator
(``layout['canonical']['size']``, markers at ``layout['canonical']['markers']``) with ``cv2.getPerspectiveTransform``,
and ``prepare`` then applies the SAME privacy mask as ``twohands.mask.prepare``. Everything happens in memory.

The clicks may come in any order: they are ordered clockwise, and of the four cyclic assignments the one whose warp
best correlates with the reference page template is kept (a photo taken sideways or upside down still lands
upright). A fine alignment (ECC, as in the locator) is tried on top of the clicked warp and kept when it holds.
Fail-closed: points that are not a plausible frame, or a warp that does not look like the form, raise
``register.NotLocated`` (nothing stored, nothing sent).
"""
from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np
from PIL import Image, ImageOps

from twohands import register, schema

MIN_SCORE = 0.20        # correlation with the page template of the best orientation
MIN_AREA_FRAC = 0.02    # the clicked frame covers at least 2% of the photo


def _points(pts: Sequence[Sequence[float]], W: int, H: int) -> np.ndarray:
    try:
        p = np.array(pts, dtype=float).reshape(4, 2)
    except (ValueError, TypeError):
        raise register.NotLocated("need exactly four corner points (x, y)")
    if not np.isfinite(p).all():
        raise register.NotLocated("corner points must be numbers")
    tol = 0.02 * max(W, H)
    if (p[:, 0] < -tol).any() or (p[:, 1] < -tol).any() or (p[:, 0] > W + tol).any() or (p[:, 1] > H + tol).any():
        raise register.NotLocated("a corner point lies outside the photo")
    q = register._order(p)
    if not cv2.isContourConvex(q.astype(np.float32).reshape(-1, 1, 2)):
        raise register.NotLocated("the four points do not form a frame (click each corner marker once)")
    if cv2.contourArea(q.astype(np.float32)) < MIN_AREA_FRAC * W * H:
        raise register.NotLocated("the four points are too close together")
    return q


def rectify_corners(img: Image.Image, pts, layout: dict, template=None, ref=None,
                    min_score: float = MIN_SCORE) -> register.Located:
    """Photo + four clicked marker centres (photo pixels, any order) -> upright canonical page (unmasked, in memory)."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    W, H = img.size
    q = _points(pts, W, H)
    can = layout["canonical"]
    cw, ch = can["size"]
    M = (np.array(can["markers"], dtype=float) * [cw, ch]).astype(np.float32)  # TL, TR, BR, BL, canonical pixels
    gray = np.asarray(img.convert("L"))
    small = np.diag([register.TEMPLATE_SIZE[0] / cw, register.TEMPLATE_SIZE[1] / ch, 1.0])
    scored = []
    for rot in range(4):
        src = np.roll(q, -rot, axis=0).astype(np.float32)
        Hm = cv2.getPerspectiveTransform(src, M)
        if template is not None:
            v = cv2.warpPerspective(gray, small @ Hm, register.TEMPLATE_SIZE, flags=cv2.INTER_AREA,
                                    borderValue=255).astype(float)
            sc = register._corr(v, template)
        else:
            sc = 1.0 if rot == 0 else 0.0
        scored.append((sc, src, Hm))
    scored.sort(key=lambda t: -t[0])
    score, src, Hm = scored[0]
    if template is not None and score < min_score:
        raise register.NotLocated(f"the clicked frame does not look like the form (score {score:.2f})")
    ecc = None
    if ref is not None:
        Hf, e = register._ecc_refine(gray, Hm, ref, cw, ch, 0.35)
        if Hf is not None:
            Hm, ecc = Hf, e
    out = cv2.warpPerspective(np.asarray(img), Hm, (cw, ch), flags=cv2.INTER_AREA, borderValue=(255, 255, 255))
    loc = register.Located(Image.fromarray(out), src.tolist(), round(float(score), 3),
                           round(float(score - scored[1][0]), 3), 4)
    loc.ecc = None if ecc is None else round(float(ecc), 3)
    return loc


def prepare(img: Image.Image, pts, layout_kind: str = "movil", s: dict | None = None):
    """Photo + four clicked corners -> (masked canonical page, info), the same mask as ``mask.prepare``.
    Raises ``register.NotLocated``."""
    from twohands import mask
    s = s or schema.load()
    loc = rectify_corners(img, pts, s["layout"], schema.template(s), schema.reference(s))
    page = mask.apply_mask(loc.image, schema.mask_rects(s, layout_kind))
    del loc.image
    info = {"locator": "manual_corners", "score": loc.score, "margin": loc.margin, "ecc": loc.ecc,
            "landmark_worst_px": None, "markers_found": 4, "size": list(page.size), "layout": layout_kind}
    return page, info
