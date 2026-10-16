"""The Two Hands practice sheet: a one-page printable form for the "print it, fill it in your language" demonstration.

    python scripts/make_sheet.py            # static/sheet/two-hands-sheet.pdf (A4, 300 dpi) + .png preview (150 dpi)
                                            # + schemas/practice_sheet.template.npy (orientation template)
    python scripts/make_sheet.py --schema   # also (re)build schemas/practice_sheet.yaml THROUGH THE SCHEMA BUILDER'S
                                            # API (POST /api/builder/save, in-process), timed

Layout (A4 portrait): four solid black corner markers like the INE acta (so the same marker registration finds the
page), a title, 10 numbered rows, each with a "words" line on the left and 3 digit boxes on the right (the tally
sheet's order: words left, digits right), and a TOTAL row (words + digits). There is no personal-data area, so the
schema's privacy mask is empty.

Geometry is defined once in millimetres; the PNG preview (150 dpi) IS the canonical page of the schema
(1240 x 1754 px), and every box in the schema is a fraction of it.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "static" / "sheet"
PDF = OUT_DIR / "two-hands-sheet.pdf"
PNG = OUT_DIR / "two-hands-sheet.png"
SCHEMA = REPO / "schemas" / "practice_sheet.yaml"
TEMPLATE = REPO / "schemas" / "practice_sheet.template.npy"

TITLE = "Two Hands practice sheet: write each amount twice, in words and in digits"
PAGE_MM = (210.0, 297.0)
CANON_DPI = 150                    # canonical page = 1240 x 1754
MARKER_MM = 10.0                   # solid black squares
MARKER_INSET_MM = 12.0             # marker edge from the paper edge (inside any printer's margin)
X_NUM, X_WORDS0, X_WORDS1 = 24.0, 36.0, 140.0
BOX_W, BOX_GAP, X_BOX0 = 13.0, 2.0, 145.0  # three digit boxes: 145..186 mm
ROW_Y0, ROW_H, TOTAL_GAP = 62.0, 16.0, 6.0  # rows 1..10 from 62 mm, 16 mm each; TOTAL after a 6 mm gap
KEYS = [f"ROW{i:02d}" for i in range(1, 11)] + ["TOTAL"]


def _font(size: int, bold: bool = False, hand: bool = False):
    names = (["segoepr.ttf", "segoesc.ttf", "comic.ttf", "DejaVuSans-Oblique.ttf"] if hand else
             (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]))
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def rows_mm() -> list[tuple[str, float, float]]:
    """(key, y0, y1) in mm for the 10 rows and the TOTAL row."""
    out = [(k, ROW_Y0 + i * ROW_H, ROW_Y0 + (i + 1) * ROW_H) for i, k in enumerate(KEYS[:10])]
    y = ROW_Y0 + 10 * ROW_H + TOTAL_GAP
    out.append(("TOTAL", y, y + ROW_H))
    return out


def markers_mm() -> list[tuple[float, float]]:
    """Top-left corners of the four markers, TL, TR, BR, BL, in mm."""
    W, H = PAGE_MM
    a, m = MARKER_INSET_MM, MARKER_MM
    return [(a, a), (W - a - m, a), (W - a - m, H - a - m), (a, H - a - m)]


def digit_boxes_mm(y0: float, y1: float) -> list[tuple[float, float, float, float]]:
    return [(X_BOX0 + j * (BOX_W + BOX_GAP), y0 + 2.0, X_BOX0 + j * (BOX_W + BOX_GAP) + BOX_W, y1 - 2.0) for j in range(3)]


def draw(dpi: int = CANON_DPI) -> Image.Image:
    """The blank sheet at ``dpi``."""
    k = dpi / 25.4
    px = lambda v: int(round(v * k))
    W, H = px(PAGE_MM[0]), px(PAGE_MM[1])
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    ink, grey, rule = "#111317", "#4a505c", "#8d939e"
    for x, y in markers_mm():
        d.rectangle([px(x), px(y), px(x + MARKER_MM) - 1, px(y + MARKER_MM) - 1], fill="black")
    # title (two lines; the full title string is TITLE)
    head, tail = TITLE.split(": ", 1)
    # a dark title band across the top: it also tells the registration which way is up (orientation template)
    bx1 = X_BOX0 + 3 * BOX_W + 2 * BOX_GAP
    d.rectangle([px(X_NUM - 3), px(23), px(bx1), px(34.5)], fill="#1c1f26")
    d.text((px(X_NUM), px(24.6)), head + ":", font=_font(px(6.2), bold=True), fill="white")
    d.text((px(X_NUM), px(36.5)), tail, font=_font(px(4.6), bold=True), fill=ink)
    d.text((px(X_NUM), px(45.5)), "Write the words in your own language. One digit per box, right-aligned. "
           "TOTAL is the sum of rows 1 to 10.", font=_font(px(3.0)), fill=grey)
    # column heads
    hy = ROW_Y0 - 7.5
    d.text((px(X_NUM), px(hy)), "#", font=_font(px(3.2), bold=True), fill=grey)
    d.text((px(X_WORDS0), px(hy)), "AMOUNT IN WORDS", font=_font(px(3.2), bold=True), fill=grey)
    d.text((px(X_BOX0), px(hy)), "IN DIGITS", font=_font(px(3.2), bold=True), fill=grey)
    d.line([px(X_NUM), px(ROW_Y0 - 1.5), px(X_BOX0 + 3 * BOX_W + 2 * BOX_GAP), px(ROW_Y0 - 1.5)], fill=ink,
           width=max(2, px(0.5)))
    for key, y0, y1 in rows_mm():
        tot = key == "TOTAL"
        if tot:
            d.line([px(X_NUM), px(y0 - TOTAL_GAP / 2), px(X_BOX0 + 3 * BOX_W + 2 * BOX_GAP), px(y0 - TOTAL_GAP / 2)],
                   fill=ink, width=max(2, px(0.6)))
        lab = "TOTAL" if tot else str(int(key[3:]))
        f = _font(px(4.4 if not tot else 4.0), bold=True)
        tb = d.textbbox((0, 0), lab, font=f)
        d.text((px(X_NUM), px((y0 + y1) / 2) - (tb[1] + tb[3]) // 2), lab, font=f, fill=ink)
        x_line0 = X_WORDS0 + (8.0 if tot else 0.0)
        d.line([px(x_line0), px(y1 - 3.5), px(X_WORDS1), px(y1 - 3.5)], fill=rule, width=max(1, px(0.3)))
        for b in digit_boxes_mm(y0, y1):
            d.rectangle([px(b[0]), px(b[1]), px(b[2]), px(b[3])], outline=ink, width=max(2, px(0.5 if tot else 0.35)))
    d.text((px(X_NUM), px(PAGE_MM[1] - 45)), "Keep all four black squares in the photo. Photograph the sheet flat, "
           "from above, in even light.", font=_font(px(3.0)), fill=grey)
    d.text((px(X_NUM), px(PAGE_MM[1] - 40)), "Two Hands demonstration sheet. Not an official form; it asks for no "
           "names or signatures.", font=_font(px(3.0)), fill=grey)
    return im


# ------------------------------------------------------------------------------------------- schema (builder state)
def builder_state() -> dict:
    """The schema as the builder's state (what /builder sends to /api/builder/save): fractions of the canonical page."""
    W, H = PAGE_MM
    fx = lambda v: round(v / W, 4)
    fy = lambda v: round(v / H, 4)
    markers = [[fx(x), fy(y), fx(x + MARKER_MM), fy(y + MARKER_MM)] for x, y in markers_mm()]
    fields = []
    for key, y0, y1 in rows_mm():
        if key == "TOTAL":
            label = {"keywords": ["TOTAL"]}
        else:
            n = int(key[3:])
            label = {"keywords": [str(n)], "none": ["TOTAL"] + (["10"] if n == 1 else [])}
        fields.append({"key": key, "type": "integer", "label": label,
                       "box": [fx(X_BOX0 - 1.0), fy(y0 + 1.0), fx(X_BOX0 + 3 * BOX_W + 2 * BOX_GAP + 1.0), fy(y1 - 1.0)],
                       "words_box": [fx(X_WORDS0), fy(y0 + 1.0), fx(X_WORDS1), fy(y1 - 1.0)]})
    r = rows_mm()
    tiles = [{"name": "rows_1_5", "box": [fx(X_NUM - 4), fy(r[0][1] - 9), fx(190), fy(r[4][2] + 1)],
              "says": "rows 1 to 5 (words on the left, digit boxes on the right)"},
             {"name": "rows_6_total", "box": [fx(X_NUM - 4), fy(r[5][1] - 1), fx(190), fy(r[10][2] + 1)],
              "says": "rows 6 to 10 and the TOTAL row"}]
    return {
        "form": "practice_sheet", "title": TITLE, "size": [round(W / 25.4 * CANON_DPI), round(H / 25.4 * CANON_DPI)],
        "whole_image": False, "markers": markers,
        "mask": [],  # no personal-data area on this sheet: nothing to black out
        "tiles": tiles, "fields": fields,
        "identities": ["rows sum to TOTAL: sum(ROW01..ROW10) == TOTAL", "words == digits"],
        "keep": {"top": {"words_required": True, "reader_note": READER_NOTE, "demonstration": True},
                 "layout": {"template": TEMPLATE.name}, "canonical": {}, "mask_layouts": ["movil", "escaner"]},
    }


READER_NOTE = (
    "The amounts in words may be written in ANY language or script (for example Czech 'dvanáct', English 'twelve', "
    "Spanish 'doce'). For \"w\", give the integer that the WORDS express, whatever the language. Read the words on "
    "their own: never look at the digit boxes to decide what the words say. If you cannot tell what number the words "
    "express (a language you cannot read, illegible handwriting, ambiguous wording), return null for \"w\". Never "
    "guess, and never copy the digits into \"w\". The printed label of each row is its number (1 to 10) or TOTAL.")

SCHEMA_HEADER = [
    "# PRIVACY: this sheet has no personal-data area (no names, no signatures), so the privacy mask region is EMPTY:",
    "#   nothing is blacked out, and the page is stored and read as photographed (straightened).",
    "# words_required: a row whose words were not read (null) routes, so no row is accepted on its digits alone.",
    "# reader_note: appended to the reader prompt; the words may be in any language, null when the model cannot tell.",
    "# identities: 'rows sum to TOTAL' (below) and 'words = digits' per field (every field has a words_box; the gate",
    "#   checks words against digits on each row, and with words_required a row with unread words routes).",
    "# Demonstration, not a measurement.",
]


def template_from(page: Image.Image) -> np.ndarray:
    """The orientation template (register.TEMPLATE_SIZE) of the blank page; no masked area to zero."""
    from twohands import register
    return register._tvec(page).astype(np.float32)


def build_schema() -> float:
    """POST the state to the builder's save API (in-process); move the YAML to schemas/; return seconds taken."""
    import tempfile
    from fastapi.testclient import TestClient
    from app import builder as B
    from app.main import app

    tmp = Path(tempfile.mkdtemp())
    old = B.USER_DIR
    B.USER_DIR = tmp
    try:
        c = TestClient(app)
        t0 = time.perf_counter()
        r = c.post("/api/builder/save", json=builder_state())
        secs = time.perf_counter() - t0
        j = r.json()
        if r.status_code != 200:
            raise SystemExit(f"builder refused the schema: {j}")
        text = (tmp / "practice_sheet.yaml").read_text(encoding="utf-8")
    finally:
        B.USER_DIR = old
        shutil.rmtree(tmp, ignore_errors=True)
    lines = text.splitlines()
    # insert our header after the builder's own 4-line header
    text = "\n".join(lines[:4] + SCHEMA_HEADER + lines[4:]) + "\n"
    SCHEMA.write_text(text, encoding="utf-8")
    print(f"schema: {SCHEMA.relative_to(REPO)} via POST /api/builder/save in {secs:.3f} s; warnings: {j.get('warnings')}")
    return secs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", action="store_true", help="also rebuild schemas/practice_sheet.yaml via the builder API")
    a = ap.parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    canon = draw(CANON_DPI)
    canon.save(PNG, optimize=True)
    draw(300).save(PDF, "PDF", resolution=300.0, title=TITLE, author="Two Hands")
    np.save(TEMPLATE, template_from(canon))
    print(f"sheet: {PDF.relative_to(REPO)}, {PNG.relative_to(REPO)} ({canon.width}x{canon.height}), "
          f"{TEMPLATE.relative_to(REPO)}")
    if a.schema:
        build_schema()
    return 0


if __name__ == "__main__":
    sys.exit(main())
