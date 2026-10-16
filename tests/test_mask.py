"""Privacy mask + tiles: no tile reaches a name/signature region, and every gate input stays visible."""
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from twohands import REPO, mask, schema

S = schema.load()
L = S["layout"]
FIX = Path(__file__).parent / "fixtures"


def inter(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def contains(outer, inner):
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


@pytest.mark.parametrize("layout", ["movil", "escaner"])
def test_no_tile_touches_the_mask(layout):
    for t in L["tiles"]:
        for m in schema.mask_rects(S, layout):
            assert inter(t["box"], m) == 0, (t["name"], m)


@pytest.mark.parametrize("layout", ["movil", "escaner"])
def test_gate_regions_outside_mask_and_inside_a_tile(layout):
    for name, reg in L["field_regions"].items():
        for m in schema.mask_rects(S, layout):
            assert inter(reg, m) == 0, name          # section 5 / section 7 / rows are never blacked out
        assert any(contains(t["box"], reg) for t in L["tiles"]) or name == "section6_rows", name
    # section 6 rows are split over the party / coalition / bottom tiles: their union must cover the region
    reg = L["field_regions"]["section6_rows"]
    ys = sorted((t["box"][1], t["box"][3]) for t in L["tiles"] if t["box"][0] <= reg[0] and t["box"][2] >= reg[2])
    covered = reg[1]
    for y0, y1 in ys:
        if y0 <= covered:
            covered = max(covered, y1)
    assert covered >= reg[3]


def test_apply_mask_blacks_out_exactly_the_rectangles():
    page = Image.new("RGB", tuple(L["canonical"]["size"]), (200, 200, 200))
    out = np.asarray(mask.apply_mask(page, schema.mask_rects(S, "movil")))
    W, H = page.size
    x0 = int(schema.mask_rects(S, "movil")[0][0] * W)
    assert (out[:, x0 + 1:] == 0).all()
    assert (out[:, : x0 - 1] == 200).all()
    assert all(mask.tiles(Image.fromarray(out))[i].getextrema()[0][1] > 0 for i in range(len(L["tiles"])))


@pytest.mark.parametrize("name", ["movil", "escaner"])
def test_masked_fixture_pages(name):
    """Real masked pages (one Movil photo, one CATD scan): the mask area is pure black, the tiles carry no
    black mask pixels, and every gate region still holds ink (it was not cut)."""
    p = FIX / f"masked_{name}.jpg"
    page = Image.open(p).convert("L")
    a = np.asarray(page, dtype=float)
    H, W = a.shape
    for x0, y0, x1, y1 in schema.mask_rects(S, name):
        blk = a[int(y0 * H) + 2:int(y1 * H) - 2, int(x0 * W) + 2:int(x1 * W) - 2]
        assert blk.mean() < 8
    for name_r, (x0, y0, x1, y1) in L["field_regions"].items():
        reg = a[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
        assert (reg < 120).mean() > 0.02, name_r       # printed boxes + handwriting present
        assert (reg < 8).mean() < 0.02, name_r         # not blacked out


def test_gate_fields_read_after_masking():
    """Recorded reads of the masked fixture pages (scripts/verify_spike.py, Gemma): every one of the 23 gate
    fields came back as a number on one Movil and one Escaner page, so the identities can still fire."""
    rec = json.loads((FIX / "verify_reads.json").read_text(encoding="utf-8"))
    for layout in ("movil", "escaner"):
        r = rec[layout]
        assert len(r["values"]) == len(S["fields"])
        assert all(v is not None for v in r["values"].values()), r["values"]
        assert r["values"]["SACADOS"] is not None and r["values"]["PERSONAS_Y_REP"] is not None
        assert r["wrong_vs_adjudicated"] == {}


STORED = sorted((REPO / "data" / "masked").rglob("*.jpg"))


@pytest.mark.parametrize("path", STORED, ids=[p.name for p in STORED])
def test_every_stored_page_is_masked(path):
    """Every page under data/masked/: canonical size, the whole mask area black, gate regions not blacked out."""
    a = np.asarray(Image.open(path).convert("L"), dtype=float)
    H, W = a.shape
    s = S
    if "ieebcs" in path.parts:  # PROTOCOL_IEEBCS: the page's own schema (BCS actas, 2400x1562, mask from x 0.662)
        man = json.loads((REPO / "results" / "manifest_ieebcs300.json").read_text(encoding="utf-8"))
        s = schema.load(next(i["schema"] for i in man["items"] if i["clave"] == path.stem))
    lay = s["layout"]
    assert [W, H] == lay["canonical"]["size"]
    for x0, y0, x1, y1 in schema.mask_rects(s, "movil"):
        blk = a[int(y0 * H) + 2:int(y1 * H) - 2, int(x0 * W) + 2:int(x1 * W) - 2]
        assert blk.max() < 40 and blk.mean() < 8
    for name_r, (x0, y0, x1, y1) in lay["field_regions"].items():
        reg = a[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
        assert (reg < 8).mean() < 0.05, name_r
