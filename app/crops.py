"""Per-field crop boxes on the canonical (rectified, masked) INE page, as fractions [x0, y0, x1, y1].

Crops are cut ONLY from masked pages (twohands/data/masked/**), and every box lies left of the privacy mask
(x < 0.657), so a crop can never show a name or signature. Measured on the canonical page geometry
of schemas/mx_presidencia_2024.yaml (section 6: 18 rows, PAN at y=0.143, TOTAL at y=0.696).
"""
from __future__ import annotations

import io
from functools import lru_cache

from PIL import Image

ROW_X = (0.330, 0.648)
ROW_Y0, ROW_STEP, ROW_HALF = 0.143, 0.03253, 0.0185
LEFT = {"SOBRANTES": 0.596, "VOTARON": 0.705, "REPRESENTANTES": 0.812, "PERSONAS_Y_REP": 0.914}
SACADOS_Y = 0.797


def field_boxes(s: dict) -> dict[str, tuple[float, float, float, float]]:
    out = {}
    for k, y in LEFT.items():
        out[k] = (0.012, y - 0.032, 0.322, y + 0.03)
    out["SACADOS"] = (ROW_X[0], SACADOS_Y - 0.03, ROW_X[1], SACADOS_Y + 0.03)
    rows = [f["key"] for f in s["fields"] if f.get("vote")] + ["TOTAL"]
    for i, k in enumerate(rows):
        y = ROW_Y0 + i * ROW_STEP
        out[k] = (ROW_X[0], y - ROW_HALF, ROW_X[1], y + ROW_HALF + 0.005)
    return out


def mask_left_edge(s: dict) -> float:
    rects = [r for v in s["layout"]["mask"].values() for r in v]
    return min(r[0] for r in rects)


LABEL_X1 = 0.39   # right edge of the printed row-label (logo) column on vote rows


@lru_cache(maxsize=256)
def crop_bytes(path: str, mtime: float, key: str, pad: float, label: bool = True) -> bytes:
    from app import store as storemod
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
