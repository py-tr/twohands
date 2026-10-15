"""Locate the form in a photo or scan and warp it onto the canonical page.

INE actas carry four solid black corner markers. PREP "Móvil" images are phone photos: the form can be
small, skewed, rotated or surrounded by other papers, so fixed relative crops would land on the wrong
pixels (and a privacy mask would miss the names). Every image is therefore rectified first:

1. find dark, filled, square blobs (several thresholds),
2. choose the 4 (or 3 + an inferred 4th) that form the form's frame: similar size, frame aspect and
   marker-to-frame size ratio within the layout's tolerance,
3. homography onto the canonical marker positions from the schema,
4. orientation: of the 4 cyclic corner assignments keep the one whose warp best correlates with the
   reference page template (handles 90/180/270 degree captures).

If no frame is found, or the best warp does not look like the form, ``rectify`` raises ``NotLocated``:
the image is not stored, not sent to any model, and the form goes to a person ("form not located").
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import cv2
import numpy as np
from PIL import Image, ImageOps

TEMPLATE_SIZE = (96, 62)  # (w, h) of the orientation template
REF_SIZE = (600, 388)     # (w, h) of the fine-alignment reference page


class NotLocated(Exception):
    """The form's frame could not be found reliably: route to a person, store and send nothing."""


@dataclass
class Located:
    image: Image.Image          # canonical, upright, RGB, unmasked (never stored)
    corners: list               # source pixel coords TL, TR, BR, BL of the markers
    score: float                # correlation with the reference template
    margin: float               # best minus second-best orientation score
    markers_found: int          # 4, or 3 when the 4th was inferred


def _candidates(gray: np.ndarray) -> list[tuple[float, float, float]]:
    """Dark filled square blobs -> (cx, cy, size) in the given array's pixels."""
    work = max(gray.shape)
    out: list[tuple[float, float, float]] = []
    seen: list[tuple[float, float]] = []
    for thr in (90, 120, 60):
        mask = (gray < thr).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        n, _lab, st, cen = cv2.connectedComponentsWithStats(mask, 8)
        for i in range(1, n):
            x, y, w, h, area = st[i]
            if w < 8 or h < 8 or w > work * 0.06 or h > work * 0.06:
                continue
            if not (0.6 < w / h < 1.6) or area / float(w * h) < 0.72:
                continue
            cx, cy = float(cen[i][0]), float(cen[i][1])
            if any(abs(cx - a) < 6 and abs(cy - b) < 6 for a, b in seen):
                continue
            seen.append((cx, cy))
            out.append((cx, cy, (w + h) / 2.0))
    out.sort(key=lambda c: -c[2])
    return out[:16]


def _order(pts: np.ndarray) -> np.ndarray:
    """Order 4 points clockwise starting from the one nearest the top-left of the image."""
    c = pts.mean(0)
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    p = pts[np.argsort(ang)]  # clockwise in image coords (y down)
    start = int(np.argmin(p[:, 0] + p[:, 1]))
    return np.roll(p, -start, axis=0)


def _plausible(quad: np.ndarray, sizes: Sequence[float], aspect: float, size_ratio: float) -> Optional[float]:
    """Frame plausibility; returns area if plausible else None. Accepts portrait (rotated) frames."""
    if not cv2.isContourConvex(quad.astype(np.float32).reshape(-1, 1, 2)):
        return None
    s = [np.linalg.norm(quad[(i + 1) % 4] - quad[i]) for i in range(4)]
    if min(s) <= 0 or s[0] / s[2] > 1.4 or s[2] / s[0] > 1.4 or s[1] / s[3] > 1.4 or s[3] / s[1] > 1.4:
        return None
    a, b = (s[0] + s[2]) / 2, (s[1] + s[3]) / 2
    long_, short = max(a, b), min(a, b)
    if not (aspect * 0.8 < long_ / short < aspect * 1.25):
        return None
    if sizes and max(sizes) / min(sizes) > 1.7:
        return None
    msize = float(np.mean(sizes)) / long_
    if not (size_ratio * 0.55 < msize < size_ratio * 1.6):
        return None
    return float(cv2.contourArea(quad.astype(np.float32)))


def _frames(cands, aspect, size_ratio):
    """Yield (area, quad[4,2], n_found) for plausible frames: 4 markers, else 3 + inferred 4th."""
    res = []
    for comb in itertools.combinations(range(len(cands)), 4):
        pts = np.array([cands[i][:2] for i in comb], dtype=float)
        q = _order(pts)
        area = _plausible(q, [cands[i][2] for i in comb], aspect, size_ratio)
        if area:
            res.append((area, q, 4))
    if res:
        return res
    for comb in itertools.combinations(range(len(cands)), 3):
        P = np.array([cands[i][:2] for i in comb], dtype=float)
        for k in range(3):  # P[k] is the right-angle corner; complete the parallelogram
            a, b = [P[j] for j in range(3) if j != k]
            d = a + b - P[k]
            q = _order(np.vstack([P, d]))
            area = _plausible(q, [cands[i][2] for i in comb], aspect, size_ratio)
            if area:
                res.append((area, q, 3))
    return res


def _tvec(im: Image.Image) -> np.ndarray:
    a = np.asarray(im.convert("L").resize(TEMPLATE_SIZE, Image.BILINEAR), dtype=float)
    return (a - a.mean()) / (a.std() + 1e-6)


def _corr(v: np.ndarray, template: np.ndarray) -> float:
    """Pearson correlation over the template's unmasked cells (masked cells are exactly 0)."""
    w = template != 0
    a, b = v[w], template[w]
    a = (a - a.mean()) / (a.std() + 1e-6)
    b = (b - b.mean()) / (b.std() + 1e-6)
    return float((a * b).mean())


def load_template(path: str | Path) -> np.ndarray:
    return np.load(path)


def rectify(img: Image.Image, layout: dict, template: Optional[np.ndarray] = None,
            min_score: float = 0.25, min_margin: float = 0.08, work: int = 1600,
            ref: Optional[np.ndarray] = None, min_ecc: float = 0.55) -> Located:
    """Return the upright canonical page (layout['canonical']['size']) or raise NotLocated."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    W, H = img.size
    s = work / max(W, H)
    gray = np.asarray(img.convert("L").resize((max(1, round(W * s)), max(1, round(H * s)))))
    cands = _candidates(gray)
    can = layout["canonical"]
    cw, ch = can["size"]
    M = np.array(can["markers"], dtype=float) * [cw, ch]  # TL, TR, BR, BL in canonical pixels
    aspect = (np.linalg.norm(M[1] - M[0])) / (np.linalg.norm(M[3] - M[0]))
    size_ratio = float(can["marker_size"])  # marker side / frame long side
    frames = sorted(_frames(cands, aspect, size_ratio), key=lambda f: -f[0])[:8]
    if not frames:
        raise NotLocated(f"corner markers not found ({len(cands)} candidates)")
    gray_full = np.asarray(img.convert("L"))
    small_scale = np.diag([TEMPLATE_SIZE[0] / cw, TEMPLATE_SIZE[1] / ch, 1.0])
    best = None  # (score, margin, src, H, nfound)
    for _area, q, nfound in frames:
        src = q / s
        scored = []
        for rot in range(4):
            srcr = np.roll(src, -rot, axis=0).astype(np.float32)
            Hm = cv2.getPerspectiveTransform(srcr, M.astype(np.float32))
            if template is not None:
                v = cv2.warpPerspective(gray_full, small_scale @ Hm, TEMPLATE_SIZE, flags=cv2.INTER_AREA,
                                        borderValue=255).astype(float)
                score = _corr(v, template)
            else:
                score = 1.0 if rot == 0 else 0.0
            scored.append((score, srcr, Hm))
        scored.sort(key=lambda t: -t[0])
        cand = (scored[0][0], scored[0][0] - scored[1][0], scored[0][1], scored[0][2], nfound)
        if best is None or cand[0] > best[0]:
            best = cand
    score, margin, srcr, Hm, nfound = best
    if template is not None and (score < min_score or margin < min_margin):
        raise NotLocated(f"page does not match the form template (score {score:.2f}, margin {margin:.2f})")
    ecc = None
    if ref is not None:
        # fine alignment: ECC homography of the coarse warp onto the reference page (masked area ignored)
        S = np.diag([REF_SIZE[0] / cw, REF_SIZE[1] / ch, 1.0])
        small = cv2.warpPerspective(gray_full, S @ Hm, REF_SIZE, flags=cv2.INTER_AREA, borderValue=255).astype(np.float32)
        refmask = (ref != 0).astype(np.uint8)
        Wm = np.eye(3, dtype=np.float32)
        try:
            ecc, Wm = cv2.findTransformECC(ref.astype(np.float32), small, Wm, cv2.MOTION_HOMOGRAPHY,
                                           (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5), refmask, 5)
        except cv2.error as e:
            raise NotLocated(f"fine alignment failed ({str(e)[:60]})")
        if ecc < min_ecc:
            raise NotLocated(f"fine alignment too weak (ecc {ecc:.2f})")
        Hm = np.linalg.inv(S) @ np.linalg.inv(Wm.astype(np.float64)) @ S @ Hm
    out = cv2.warpPerspective(np.asarray(img), Hm, (cw, ch), flags=cv2.INTER_AREA, borderValue=(255, 255, 255))
    loc = Located(Image.fromarray(out), srcr.tolist(), round(score, 3), round(margin, 3), nfound)
    loc.ecc = None if ecc is None else round(float(ecc), 3)
    return loc


# ---------------------------------------------------------------------------------------------------------
# Amendment 1 locator (PROTOCOL.md, Amendment 1). Same markers and fine alignment, but the accept decision is
# made by the landmark check (printed boxes land where the schema says, within LANDMARK_MAX_PX), not by the
# coarse template score: every plausible frame and its two best orientations are tried, and the first warp
# whose landmarks all land is kept. Still fail-closed: no candidate passes -> NotLocated.
# ---------------------------------------------------------------------------------------------------------
LANDMARK_MAX_PX = 12   # at 1200 px width = 1% of the page width (24 px canonical)


def _ecc_refine(gray_full, Hm, ref, cw, ch, min_ecc):
    S = np.diag([REF_SIZE[0] / cw, REF_SIZE[1] / ch, 1.0])
    small = cv2.warpPerspective(gray_full, S @ Hm, REF_SIZE, flags=cv2.INTER_AREA, borderValue=255).astype(np.float32)
    Wm = np.eye(3, dtype=np.float32)
    try:
        ecc, Wm = cv2.findTransformECC(ref.astype(np.float32), small, Wm, cv2.MOTION_HOMOGRAPHY,
                                       (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5),
                                       (ref != 0).astype(np.uint8), 5)
    except cv2.error:
        return None, None
    if ecc < min_ecc:
        return None, ecc
    return np.linalg.inv(S) @ np.linalg.inv(Wm.astype(np.float64)) @ S @ Hm, ecc


_FEAT = {}


def _feature_reference(path=None):
    """SIFT keypoints of the masked reference scan (tests/fixtures/masked_escaner.jpg is the same page) at 1200 px,
    left of the privacy mask only. ``path``: another form type's reference (schema ``layout.feature_ref``)."""
    from twohands import REPO
    p = Path(path) if path else REPO / "schemas" / "mx_presidencia_2024.feature_ref.jpg"
    key = str(p.resolve())
    if key not in _FEAT:
        g = np.asarray(Image.open(p).convert("L"))
        m = np.zeros_like(g, dtype=np.uint8)
        m[:, : int(0.65 * g.shape[1])] = 255
        sift = cv2.SIFT_create(nfeatures=4000)
        kp, des = sift.detectAndCompute(g, m)
        _FEAT[key] = (g.shape, kp, des, sift)
    return _FEAT[key]


def _feature_homography(gray_full, cw, ch, work=1600, feature_ref=None):
    try:
        (rh, rw), kp_r, des_r, sift = _feature_reference(feature_ref)
    except Exception:  # noqa: BLE001
        return None
    H0, W0 = gray_full.shape
    sc = work / max(H0, W0)
    g = cv2.resize(gray_full, (round(W0 * sc), round(H0 * sc)), interpolation=cv2.INTER_AREA)
    kp, des = sift.detectAndCompute(g, None)
    if des is None or len(kp) < 50:
        return None
    pairs = cv2.BFMatcher().knnMatch(des_r, des, k=2)
    good = [m for m, n in (p for p in pairs if len(p) == 2) if m.distance < 0.75 * n.distance]
    if len(good) < 40:
        return None
    src = np.float32([kp[m.trainIdx].pt for m in good]) / sc            # photo pixels
    dst = np.float32([kp_r[m.queryIdx].pt for m in good]) * [cw / rw, ch / rh]  # canonical pixels
    Hm, inl = cv2.findHomography(src, dst, cv2.RANSAC, 6.0)
    if Hm is None or inl is None or int(inl.sum()) < 30:
        return None
    return Hm


def rectify_v2(img: Image.Image, layout: dict, template: np.ndarray, ref: np.ndarray, landmark_ref: np.ndarray,
               work: int = 1600, min_ecc: float = 0.35, max_candidates: int = 12, feature_ref=None) -> Located:
    from twohands import landmarks as LM
    img = ImageOps.exif_transpose(img).convert("RGB")
    W, H = img.size
    s = work / max(W, H)
    gray = np.asarray(img.convert("L").resize((max(1, round(W * s)), max(1, round(H * s)))))
    can = layout["canonical"]
    cw, ch = can["size"]
    M = np.array(can["markers"], dtype=float) * [cw, ch]
    aspect = (np.linalg.norm(M[1] - M[0])) / (np.linalg.norm(M[3] - M[0]))
    frames = sorted(_frames(_candidates(gray), aspect, float(can["marker_size"])), key=lambda f: -f[0])[:8]
    # fallback frame: the image itself is the page (scans whose markers were not found)
    mk = np.array(can["markers"], dtype=float)
    if W < H:
        fb = np.array([[W * (1 - mk[3][1]), H * mk[3][0]], [W * (1 - mk[0][1]), H * mk[0][0]],
                       [W * (1 - mk[1][1]), H * mk[1][0]], [W * (1 - mk[2][1]), H * mk[2][0]]]) * s
    else:
        fb = mk * [W, H] * s
    frames.append((0.0, _order(fb), 0))
    gray_full = np.asarray(img.convert("L"))
    small_scale = np.diag([TEMPLATE_SIZE[0] / cw, TEMPLATE_SIZE[1] / ch, 1.0])
    tried, cand = 0, []
    for _area, q, nfound in frames:
        src = q / s
        scored = []
        for rot in range(4):
            srcr = np.roll(src, -rot, axis=0).astype(np.float32)
            Hm = cv2.getPerspectiveTransform(srcr, M.astype(np.float32))
            v = cv2.warpPerspective(gray_full, small_scale @ Hm, TEMPLATE_SIZE, flags=cv2.INTER_AREA,
                                    borderValue=255).astype(float)
            scored.append((_corr(v, template), srcr, Hm))
        scored.sort(key=lambda t: -t[0])
        for score, srcr, Hm in scored[:2]:
            cand.append((score, scored[0][0] - scored[1][0], srcr, Hm, nfound))
    cand.sort(key=lambda c: -c[0])  # most form-like warps first
    fH = _feature_homography(gray_full, cw, ch, feature_ref=feature_ref)  # markers cut off / bent page: SIFT + RANSAC on printed structure
    if fH is not None:
        cand.insert(min(len(cand), 2), (0.06, 0.0, np.zeros((4, 2), np.float32), fH, -1))
    last = "no candidate frame"
    for score, margin, srcr, Hm, nfound in cand[:max_candidates]:
        if score < 0.05:
            break
        tried += 1
        Hf, ecc = _ecc_refine(gray_full, Hm, ref, cw, ch, min_ecc)
        if Hf is None:  # no fine alignment: the landmark check below still decides on the coarse warp
            last = f"fine alignment too weak (ecc {ecc if ecc is None else round(float(ecc), 2)})"
            Hf, ecc = Hm, (ecc or 0.0)
        out = Image.fromarray(cv2.warpPerspective(np.asarray(img), Hf, (cw, ch), flags=cv2.INTER_AREA,
                                                  borderValue=(255, 255, 255)))
        chk = LM.check(out, landmark_ref)
        bad = [k for k, (dx, dy, pk) in chk.shifts.items() if max(abs(dx), abs(dy)) > LANDMARK_MAX_PX or pk <= 0.3]
        if bad:
            last = f"printed boxes not where expected ({', '.join(bad[:3])})"
            continue
        loc = Located(out, srcr.tolist(), round(score, 3), round(margin, 3), nfound)
        loc.ecc = round(float(ecc), 3)
        loc.landmarks = chk.shifts
        loc.worst_px = chk.worst_px
        return loc
    raise NotLocated(f"no candidate passed the landmark check after {tried} tries: {last}")
