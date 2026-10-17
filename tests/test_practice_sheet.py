"""Practice sheet ("print it, fill it in your language, photograph it"): the sheet and its schema, the gate on synthetic
values, phone-photo registration, /try routing for the practice sheet, and the wording rules.
No request reaches the real AMD endpoint from these tests (the reader is mocked)."""
import io
import re
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import builder as B
from app import live as livemod
from app import practice as P
from app.main import app
from scripts import make_sheet as MS
from scripts import practice_demo as PD
from twohands import REPO
from twohands import gate as gatemod

client = TestClient(app)
KEYS = [f"ROW{i:02d}" for i in range(1, 11)] + ["TOTAL"]
ROWS = [12, 7, 23, 5, 18, 40, 9, 31, 14, 66]


def _parsed(rows=ROWS, total=None, words=None, labels=None):
    total = sum(rows) if total is None else total
    vals = list(rows) + [total]
    words = vals if words is None else words
    labels = labels or [str(i) for i in range(1, 11)] + ["TOTAL"]
    return {"values": [{"label": lb, "n": n, "w": w} for lb, n, w in zip(labels, vals, words)]}


# ------------------------------------------------------------------------------------------------ sheet + schema
def test_sheet_files_exist_and_match_the_canonical_page():
    pdf = REPO / "static" / "sheet" / "two-hands-sheet.pdf"
    png = REPO / "static" / "sheet" / "two-hands-sheet.png"
    assert pdf.read_bytes()[:5] == b"%PDF-" and pdf.read_bytes().count(b"/Type /Page\n") <= 1
    s = P.schema()
    with Image.open(png) as im:
        assert list(im.size) == s["layout"]["canonical"]["size"] == [1240, 1754]
        g = np.asarray(im.convert("L"))
    W, H = im.size
    # four solid black markers where the schema says; the title is the one asked for
    side = s["layout"]["canonical"]["marker_size"] * (s["layout"]["canonical"]["markers"][1][0] -
                                                      s["layout"]["canonical"]["markers"][0][0]) * W
    for cx, cy in s["layout"]["canonical"]["markers"]:
        x, y, r = int(cx * W), int(cy * H), int(side * 0.4)
        assert g[y - r:y + r, x - r:x + r].mean() < 10
    assert s["title"] == MS.TITLE == "Two Hands practice sheet: write each amount twice, in words and in digits"


def test_schema_fields_identities_mask_and_reader_note():
    s = P.schema()
    assert s["keys"] == KEYS
    assert [i["name"] for i in s["identities"]] == ["rows sum to TOTAL"]
    assert s["identities"][0]["sum"] == KEYS[:10] and s["identities"][0]["equals"] == ["TOTAL"]
    for f in s["fields"]:  # words left, digits right, like the tally sheet
        assert f["words_box"][2] <= f["box"][0], f["key"]
    assert s["words_required"] is True
    assert s["layout"]["mask"] == {"movil": [], "escaner": []}
    text = P.SCHEMA_PATH.read_text(encoding="utf-8")
    assert "Made with the Two Hands schema builder" in text and "privacy mask region is EMPTY" in text
    assert "words = digits" in text
    st = B.schema_to_state(s)  # the builder reads it back: words == digits is one of its identity lines
    assert "words == digits" in st["identities"] and "rows sum to TOTAL: sum(ROW01..ROW10) == TOTAL" in st["identities"]
    note = s["reader_note"]
    assert "whatever the language" in note and "return null" in note and "Never guess" in note
    prompt = B.build_prompt(s)
    assert prompt.rstrip().endswith(note) and "exactly 11 items" in prompt


def test_schema_is_what_the_builder_saves(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "USER_DIR", tmp_path)
    r = client.post("/api/builder/save", json=MS.builder_state())
    assert r.status_code == 200, r.text
    saved = B.load_yaml(tmp_path / "practice_sheet.yaml")
    committed = P.schema()
    for k in ("form", "title", "layout", "fields", "identities", "words_required", "reader_note"):
        assert saved[k] == committed[k], k


# ------------------------------------------------------------------------------------------------ the gate
def test_gate_accepts_only_when_every_row_agrees_and_sums():
    s = P.schema()
    g = B.gate_schema(_parsed(), s)
    assert g.accepted and not g.failing_fields


@pytest.mark.parametrize("mutate,code,field", [
    (lambda w: w.__setitem__(2, 32), "words", "ROW03"),        # words say 32, digits 23
    (lambda w: w.__setitem__(4, None), "words", "ROW05"),      # words not read (a language the model cannot read)
    (lambda w: w.__setitem__(10, None), "words", "TOTAL"),
])
def test_gate_routes_with_the_field_named(mutate, code, field):
    s = P.schema()
    words = ROWS + [sum(ROWS)]
    mutate(words)
    g = B.gate_schema(_parsed(words=words), s)
    assert not g.accepted and code in g.codes and g.failing_fields == [field]
    assert any(field in r for r in g.reasons)


def test_gate_routes_when_rows_do_not_sum_to_total():
    s = P.schema()
    g = B.gate_schema(_parsed(total=224, words=ROWS + [224]), s)
    assert not g.accepted and g.codes == ["identity"]
    assert g.identities == [{"name": "rows sum to TOTAL", "ok": False, "lhs": 225, "rhs": 224}]


def test_gate_never_accepts_a_row_on_digits_alone():
    s = P.schema()
    g = B.gate_schema(_parsed(words=[None] * 11), s)
    assert not g.accepted and g.failing_fields == KEYS


def test_words_required_is_opt_in():
    """Schemas without words_required keep the old rule (words checked only when read)."""
    s = dict(P.schema())
    s.pop("words_required")
    assert B.gate_schema(_parsed(words=[None] * 11), s).accepted
    assert gatemod.gate(_parsed(words=[None] * 11), P.schema()).accepted  # the frozen core gate is unchanged


def test_gate_routes_a_shifted_row_label():
    s = P.schema()
    labels = [str(i) for i in range(1, 11)] + ["TOTAL"]
    labels[0] = "10"
    g = B.gate_schema(_parsed(labels=labels), s)
    assert not g.accepted and "label" in g.codes and "ROW01" in g.failing_fields


# ------------------------------------------------------------------------------------------------ registration
@pytest.mark.parametrize("angle,rot", [(0.0, 0), (5.0, 0), (-9.0, 0), (15.0, 0), (2.0, 90), (-2.0, 180)])
def test_phone_photo_registers(angle, rot):
    page = PD.fill()
    ph = PD.as_phone_photo(page, angle=angle, seed=3)
    if rot:
        ph = ph.rotate(rot, expand=True)
    pg, info = P.register_photo(ph)
    a = np.asarray(pg.convert("L").resize((310, 438)), float)
    b = np.asarray(page.convert("L").resize((310, 438)), float)
    assert np.corrcoef(a.ravel(), b.ravel())[0, 1] > 0.8, info


def test_clicked_corners_register():
    page = PD.fill()
    ph = PD.as_phone_photo(page, angle=3.0, seed=4)
    import cv2
    g = np.asarray(ph.convert("L"))
    n, _l, st, cen = cv2.connectedComponentsWithStats((g < 60).astype(np.uint8), 8)
    sq = [i for i in range(1, n) if 0.7 < st[i][2] / st[i][3] < 1.4 and st[i][4] > 0.7 * st[i][2] * st[i][3]]
    big = sorted(sq, key=lambda i: -st[i][4])[:4]
    assert len(big) == 4
    pts = [[float(cen[i][0]), float(cen[i][1])] for i in big][::-1]
    pg, info = P.register_photo(ph, pts)
    assert info["locator"] == "manual_corners"


def test_not_a_sheet_is_not_registered():
    with pytest.raises(B.NotRegistered):
        P.register_photo(Image.new("RGB", (1200, 1600), (200, 190, 180)))


# ------------------------------------------------------------------------------------------------ /try routing
@pytest.fixture
def tdir(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "TESTS_DIR", tmp_path / "tests")
    monkeypatch.setattr(livemod, "BUDGET_FILE", tmp_path / "budget.json")
    return tmp_path


def _jpeg(im):
    b = io.BytesIO()
    im.save(b, "JPEG", quality=85)
    return b.getvalue()


def test_try_page_offers_the_practice_sheet_and_keeps_ine():
    html = client.get("/try").text
    assert "Practice sheet (any language)" in html and "INE tally sheet, type 2" in html
    assert "Print this sheet (PDF), fill it in your language, photograph it." in re.sub(r"<[^>]+>", "", html)
    assert "Demonstration, not a measurement." in html and "/static/sheet/two-hands-sheet.pdf" in html
    assert "/api/try/practice" in html and "'/api/upload'" in html
    assert "Use a sample photo" in html and "Click the four corner markers" in html  # INE behaviour kept
    assert 'name="ftype" value="practice" checked' in client.get("/try?form=practice").text
    assert client.get("/static/sheet/two-hands-sheet.pdf").status_code == 200


def test_try_practice_reads_gates_and_shows_rows(tdir):
    calls = []

    def fake_read(model, page, s):
        calls.append(s["form"])
        words = ROWS + [sum(ROWS)]
        words[6] = None  # row 7: the model could not tell what the words say
        return {"parsed": _parsed(words=words), "secs": 0.4, "usage": {"cost": 0.0001}}

    main = livemod.LiveManager(usage_fn=lambda: {"daily_cost_remaining_usd": 0.9})
    app.state.builder_live = B.BuilderLive(main, read_fn=fake_read)
    try:
        photo = _jpeg(PD.as_phone_photo(PD.fill(), angle=4.0, seed=2))
        d = client.post("/api/try/practice", content=photo, headers={"Content-Type": "image/jpeg"}).json()
        assert d["ok"] and d["job"] and d["page_url"] == f"/try/practice/{d['id']}", d
        m = app.state.builder_live
        t = time.time() + 5
        while not m.jobs[d["job"]].done and time.time() < t:
            time.sleep(0.02)
        assert calls == ["practice_sheet"]
        html = client.get(d["page_url"]).text
        assert "Routed to a person: ROW07." in html and "Row 7" in html and "Demonstration, not a measurement." in html
        assert "rows sum to TOTAL" in html and "225 = 225" in html
        files = sorted(p.name for p in (tdir / "tests").iterdir())
        assert files == [f"{d['id']}.jpg", f"{d['id']}.json", f"{d['id']}.read.json"]  # never the raw photo
    finally:
        app.state.builder_live = None


def test_try_practice_accepts_a_clean_read(tdir):
    main = livemod.LiveManager(usage_fn=lambda: {"daily_cost_remaining_usd": 0.9})
    app.state.builder_live = B.BuilderLive(main, read_fn=lambda m, p, s: {"parsed": _parsed(), "secs": 0.3,
                                                                           "usage": {"cost": 0.0}})
    try:
        d = client.post("/api/try/practice", content=_jpeg(PD.as_phone_photo(PD.fill(), angle=-3.0)),
                        headers={"Content-Type": "image/jpeg"}).json()
        t = time.time() + 5
        while not app.state.builder_live.jobs[d["job"]].done and time.time() < t:
            time.sleep(0.02)
        html = client.get(d["page_url"]).text
        assert "Accepted: every row" in html
    finally:
        app.state.builder_live = None


def test_try_practice_unlocated_stores_nothing(tdir):
    r = client.post("/api/try/practice", content=_jpeg(Image.new("RGB", (900, 1200), "white")),
                    headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 422 and r.json()["code"] == "not_located"
    assert not (tdir / "tests").exists() or not any((tdir / "tests").iterdir())


def test_try_practice_ids_are_validated(tdir):
    for bad in ["b123", "..%2Fx", "u0123456789ab"]:
        assert client.get(f"/try/practice/{bad}").status_code == 404


# ------------------------------------------------------------------------------------------------ wording
BANNED = [r"works in any language", r"multilingual tool", r"language[- ]agnostic"]
COUNT = re.compile(r"\b(in|across|supports?|reads?)\s+\d+\s+languages\b", re.I)
LINE = ("No second-language corpus with an official keyed record and usable terms was reachable; "
        "the language claim stays at what was measured.")


def _ours():
    files = list((REPO / "app").glob("*.py")) + list((REPO / "templates").glob("*.html")) + \
        list((REPO / "static").glob("*.js")) + [REPO / "README.md", REPO / "slides" / "slides.md"] + \
        list((REPO / "docs").glob("*.md")) + [REPO / "schemas" / "practice_sheet.yaml",
                                             REPO / "scripts" / "make_sheet.py", REPO / "scripts" / "practice_demo.py"]
    res = REPO / "results" / "practice_sheet_demo.md"
    return files + ([res] if res.is_file() else [])


def test_no_language_capability_claims():
    for p in _ours():
        if not p.is_file():
            continue
        for ln in p.read_text(encoding="utf-8").splitlines():
            if "BANNED" in ln or "COUNT = " in ln:
                continue
            for pat in BANNED:
                assert not re.search(pat, ln, flags=re.I), (p.name, ln[:160])
            for m in COUNT.finditer(ln):  # a language count is allowed only inside a quoted third-party claim
                assert '"' in ln[:m.start()] and '"' in ln[m.end():], (p.name, ln[:160])


def test_language_claim_scoped_on_the_volume_slide_and_business():
    slides = (REPO / "slides" / "slides.md").read_text(encoding="utf-8")
    vol = slides.split("<!-- Slide 10b: volume -->", 1)[1].split("<!--", 1)[0]
    assert "Measured on Spanish handwriting and English ledgers" in vol   # the slide states only what was measured
    assert LINE in (REPO / "docs" / "BUSINESS.md").read_text(encoding="utf-8")   # the full limit, with the business case
