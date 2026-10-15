"""Alignment check: do the printed boxes land where the schema says?

For each landmark window (printed structure next to a gate region: section 6 header, the digit-box column, the
TOTAL row, section 7, sections 2-5 of the left column), the rectified page is matched (normalised
cross-correlation) against the landmark reference (mean of aligned pilot pages, mask area zeroed) over shifts of
+-SEARCH px at WORK resolution. A landmark is aligned when the best shift is within TOL px. The page is
correctly aligned when at least MIN_OK landmarks are aligned and none is off by more than OFF px.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

WORK = (1200, 776)
SEARCH = 18          # px at WORK (1.5% of width)
TOL = 4              # px at WORK (0.33% of width = 8 px canonical)
OFF = 10
MIN_OK = 7
WINDOWS = {
    "sec6_header":      [0.335, 0.065, 0.650, 0.125],
    "sec6_digits_mid":  [0.570, 0.250, 0.652, 0.550],
    "sec6_total_row":   [0.335, 0.655, 0.650, 0.720],
    "sec7":             [0.335, 0.720, 0.650, 0.800],
    "left_sec2":        [0.010, 0.500, 0.335, 0.585],
    "left_sec3_4":      [0.010, 0.600, 0.335, 0.760],
    "left_sec5":        [0.010, 0.780, 0.335, 0.920],
    "header_block":     [0.030, 0.100, 0.330, 0.200],
}


@dataclass
class Check:
    aligned: bool
    n_ok: int
    worst_px: float
    shifts: dict


def _gray(page) -> np.ndarray:
    im = page if isinstance(page, Image.Image) else Image.open(page)
    return np.asarray(im.convert("L").resize(WORK, Image.BILINEAR), dtype=np.float32)


def build_reference(pages) -> np.ndarray:
    return np.mean([_gray(p) for p in pages], 0).astype(np.float32)


def check(page, ref: np.ndarray) -> Check:
    a = _gray(page)
    W, H = WORK
    shifts, n_ok, worst = {}, 0, 0.0
    for name, (x0, y0, x1, y1) in WINDOWS.items():
        X0, Y0, X1, Y1 = int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)
        tpl = ref[Y0:Y1, X0:X1]
        sx0, sy0 = max(0, X0 - SEARCH), max(0, Y0 - SEARCH)
        sx1, sy1 = min(W, X1 + SEARCH), min(H, Y1 + SEARCH)
        res = cv2.matchTemplate(a[sy0:sy1, sx0:sx1], tpl, cv2.TM_CCOEFF_NORMED)
        _, peak, _, loc = cv2.minMaxLoc(res)
        dx, dy = loc[0] + sx0 - X0, loc[1] + sy0 - Y0
        d = float(max(abs(dx), abs(dy)))
        shifts[name] = [int(dx), int(dy), round(float(peak), 3)]
        n_ok += d <= TOL and peak > 0.3
        worst = max(worst, d)
    return Check(n_ok >= MIN_OK and worst <= OFF, n_ok, worst, shifts)
