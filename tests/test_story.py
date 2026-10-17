"""The 4-step story: Home -> Try it (pick a real sheet) -> the sheet page (stored read, one verdict, how it's checked)
-> the finished sample audit."""
import html as htmlmod
import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _text(h):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    t = htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()
    return re.sub(r"\s+([,.;:)])", r"\1", t)


def test_try_picks_real_sheets_then_upload():
    h = client.get("/try").text
    for k in ("211298B0100", "122655C0100", "080310B0100", "050815B0100"):
        assert f'href="/form/{k}"' in h, k
    t = _text(h)
    assert t.index("Pick a real sheet") < t.index("Or upload your own photo") < t.index("Drop a photo")
    assert '<details class="card tips-d">' in h and '<details class="more-d own-practice">' in h


def test_sheet_page_routed_verdict_and_receipt():
    h = client.get("/form/122655C0100").text
    t = _text(h)
    assert "Measured on AMD: Gemma-4-31B-IT, 2026-10-15, 60.7 s, $0.000146" in t
    assert "Rows sum to 366, TOTAL says 466: this field goes to a person, with its photo" in t
    assert "Read again live on AMD (about 60 s)" in t and 'data-stored="2026-10-15"' in h
    assert t.index("Rows sum to 366") < t.index("How it's checked") < t.index("All fields") < t.index("Now on 300 sheets")
    assert "/crop/122655C0100/OPT02.jpg" in h and "With the paper's 123, rows sum to TOTAL gives 466 = 466." in t
    assert 'href="/trace"' in h and "github.com/py-tr/twohands" in h and 'href="/audit/new"' in h
    assert re.search(r'<details class="sh-all" id="all-fields">.*id="ftable"', h, flags=re.S)
    j = client.get("/api/receipt/122655C0100/OPT02").json()
    assert j["verified"] and len(j["checks"]) == 4 and all(c["ok"] for c in j["checks"])


def test_sheet_page_capture_line_is_separate_from_accepted():
    t = _text(client.get("/form/211298B0100").text)
    assert "Every check holds: accepted, nothing to key" in t
    assert "Option 06: the official capture keyed 34; the paper says 39" in t
    assert t.index("Every check holds") < t.index("The official typed record") < t.index("the official capture keyed 34")
    t = _text(client.get("/form/050815B0100").text)
    assert "Option 07: the official capture keyed 75; the paper says 175" in t
    t = _text(client.get("/form/080310B0100").text)
    assert "Unused ballots: the official capture keyed 480; the paper says 180" in t


def test_busy_endpoint_banner_is_loud():
    js = client.get("/static/live.js").text
    assert "AMD endpoint busy" in js and "showing the stored read from" in js and "loud" in js
