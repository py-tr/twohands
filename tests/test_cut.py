"""The mentor's cut: six nav items, the first screen in order, the phone fold, /station (instant vs queued), no party
names, no "touchless" in titles or nav."""
import html as htmlmod
import json
import re
import socket
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app import live_status as LS
from app import numbers as numbersmod
from app import stations as ST
from app.main import app
from twohands import worker as W
from twohands.priority import prioritized

client = TestClient(app)
PARTY = re.compile(r"(?<![A-Za-z0-9])(PAN|PRI|PRD|PVEM|PT|MC|MORENA)(?![A-Za-z0-9])")
PARTY_CI = re.compile(r"(?<![A-Za-z0-9])(morena|pvem|verde)(?![A-Za-z0-9])", re.I)
SIX = ["Home", "Findings", "Audit your capture", "Try it", "Results", "API"]
MORE = ["Inbox", "Keyer", "Builder", "AMD status", "Evolus", "Data and credits"]
H1 = "Receipts for every number keyed from paper."
SUB = "A vision model on AMD reads the form; the form's own arithmetic decides; every dispute comes with its photo."
DIFF = "Others check the model against the source. We check the record against the paper."
PAGES = ["/", "/audit", "/audit/new", "/review", "/try", "/results", "/api", "/station", "/station?c=202451B0100",
         "/inbox", "/keyer?s=1", "/builder", "/live", "/about-data"]


def _text(h):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


def _nav(h):
    return re.search(r'<nav class="nav" id="nav"[^>]*>(.*?)</nav>', h, flags=re.S).group(1)


@pytest.fixture
def empty_worker(tmp_path, monkeypatch):
    """A worker directory with no rows: the strip falls back to the measured sample."""
    monkeypatch.setattr(W, "WORKER_DIR", tmp_path / "w")
    return tmp_path / "w"


@pytest.fixture
def queue_worker(tmp_path, monkeypatch):
    """A worker directory whose queue holds two stations that no sample has read."""
    root = tmp_path / "w"
    root.mkdir()
    keys = [k for k in ST.search("0103", 400) if not ST.storemod.get_store().masked_image(k)][:2]
    assert len(keys) == 2
    q = {"states": {"1": {"name": "Aguascalientes", "size": 2, "queue": 2, "measured_skipped": 0}},
         "items": [{"clave": k, "ent": 1, "dist": 1, "layout": "movil", "mode": "comparison", "cap": [], "cert": None}
                   for k in keys]}
    W.save_queue(q, root / "queue.json.gz")
    monkeypatch.setattr(W, "WORKER_DIR", root)
    return root, keys


# ------------------------------------------------------------------------------------------------ nav
def test_nav_has_six_items_and_a_more_menu():
    h = client.get("/").text
    nav = _nav(h)
    top = re.sub(r'<details class="more".*?</details>', "", nav, flags=re.S)
    assert [_text(a) for a in re.findall(r"<a [^>]*>(.*?)</a>", top, flags=re.S)] == SIX
    more = re.search(r'<details class="more".*?</details>', nav, flags=re.S).group(0)
    labels = [_text(a) for a in re.findall(r"<a [^>]*>(.*?)</a>", more, flags=re.S)]
    assert [x.split(":")[0] for x in labels] == MORE
    assert 'href="/check"' not in nav and "/receipt" not in nav
    assert re.search(r'class="livedot[^"]*" href="/live"', h)
    for u in ("/check", "/live", "/about-data"):
        assert client.get(u).status_code == 200


def test_review_desk_is_a_tab_of_audit_your_capture():
    for u in ("/audit/new", "/review"):
        h = client.get(u).text
        tabs = re.search(r'<nav class="tabs".*?</nav>', h, flags=re.S).group(0)
        assert "Audit your capture" in tabs and "Review desk" in tabs and 'href="/audit/request"' in tabs
        assert re.search(r'<a href="/audit/new" class="on">Audit your capture</a>', _nav(h))
    assert "Request an audit" in _text(client.get("/").text)


def test_no_touchless_in_titles_or_nav():
    for u in PAGES:
        h = client.get(u).text
        title = re.search(r"<title>(.*?)</title>", h, flags=re.S).group(1)
        heads = " ".join(re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", h, flags=re.S))
        assert "touchless" not in (title + _nav(h) + heads).lower(), u


# ------------------------------------------------------------------------------------------------ first screen
def test_first_screen_content_in_order(empty_worker):
    h = client.get("/").text
    first = re.search(r'<section class="first".*?</section>', h, flags=re.S).group(0)
    t = _text(first)
    H = numbersmod.headline()
    marks = [H1, SUB, f"{H['read']} forms audited on AMD so far", f"{H['disagree']} disputes",
             f"{H['cert_agree']} confirmed by the certified count", "measured sample",
             "reader: Gemma-4-31B-IT on AMD Token Factory",
             "The paper: 271 · The first capture keyed: 272 · The certified count: 271",
             "dispute confirmed by the certified count", "202451B0100", "Pick any polling station",
             "Audit your capture", DIFF]
    pos = [t.find(m) for m in marks]
    assert all(p >= 0 for p in pos), [m for m, p in zip(marks, pos) if p < 0]
    assert pos == sorted(pos), list(zip(marks, pos))
    assert h.count("<h1") == 1 and f">{H1}</h1>" in h
    # removed: the replay animation, any pilot number, the word touchless
    assert 'id="reader"' not in h and "loopData" not in h and "hero.js" not in h
    assert "pilot" not in t.lower() and "touchless" not in t.lower() and "spike" not in t.lower()
    # the receipt card goes to Findings
    assert re.search(r'<a class="rcard card" href="/audit"', first)


def test_strip_uses_live_numbers_once_the_worker_has_audited(monkeypatch):
    fake = {"audited": 41, "disputes": 9, "confirmed": 3, "updated": "2026-10-16T00:00:00Z", "reader_now": "Qwen3.8-27B",
            "states": [{"name": "Colima", "complete": True, "pct": 100.0}, {"name": "Baja California Sur", "complete": False, "pct": 12.5}],
            "queue_states": 32, "status": {"kind": "live", "text": "Running"},
            "recent": [{"clave": "060101C0100", "code": "OPT03", "name": "Option 03", "paper": 12, "capture": 21,
                        "certified": 12, "state": "Colima", "label": "confirmed", "crop": "/live/crop/060101C0100/OPT03.jpg",
                        "reader": "Qwen3.8-27B"},
                       {"clave": "060102C0100", "code": "TOTAL", "name": "TOTAL", "paper": 300, "capture": 310,
                        "certified": 300, "state": "Colima", "label": "confirmed", "crop": "/live/crop/060102C0100/TOTAL.jpg",
                        "reader": "Qwen3.8-27B"}]}
    monkeypatch.setattr(LS, "_summary", lambda: fake)
    s = LS.status()
    assert (s["kind"], s["forms_audited"], s["disputes"], s["certified_confirmed"]) == ("live", 41, 9, 3)
    assert s["states_complete"].startswith("1 of 32 states complete") and s["reader_model"] == "Qwen3.8-27B"
    t = _text(client.get("/").text)
    assert "41 forms audited on AMD so far" in t and "measured sample" not in t.split("Measured, not promised")[0]
    assert "updated" in t and "reader: Qwen3.8-27B on AMD Token Factory" in t
    rs = s["latest_receipts"]
    assert (rs[0]["clave"], rs[0]["code"]) == ("202451B0100", "TOTAL")
    assert rs[1]["clave"] == "060102C0100"            # a live TOTAL before the measured TOTALs
    assert rs[-1]["code"].startswith("OPT")


def test_default_receipt_and_rotation_order(empty_worker):
    s = LS.status()
    rs = s["latest_receipts"]
    r0 = rs[0]
    assert (r0["clave"], r0["code"], r0["paper"], r0["capture"], r0["certified"]) == ("202451B0100", "TOTAL", 271, "272", 271)
    orders = [LS._field_order(r["code"]) for r in rs]
    assert orders == sorted(orders)
    assert all(r["paper"] == r["certified"] and str(r["paper"]) != r["capture"] for r in rs)
    j = client.get("/api/live-strip").json()
    assert j["kind"] == "measured" and j["label"] == "measured sample"


def test_second_screen_measured_not_promised():
    t = _text(client.get("/").text)
    m = t[t.index("Measured, not promised"):t.index("How it works")]
    H = numbersmod.headline()
    T = numbersmod.tiers()["tiers"]["two_reader"]
    for s in (f"{H['keying_errors']}", f"{H['cert_agree']} of {H['cert_covered']}", f"{H['accepted_pct']}%",
              f"{H['acc_model_wrong']} of {H['acc_fields']:,}", f"{T['errors']} of {T['fields']:,}",
              f"1 in {H['model_one_in']} vs 1 in {H['acc_one_in']}", f"1 in {H['yield_one_in']} vs 1 in {H['random_one_in']}"):
        assert s in m, s
    h = client.get("/").text
    assert "/static/builder.webm" in h and "/audit/request" in h


def test_builder_clip_is_small():
    from twohands import REPO
    p = REPO / "static" / "builder.webm"
    assert p.is_file() and p.stat().st_size <= 2 * 1024 * 1024


# ------------------------------------------------------------------------------------------------ /station
def test_station_instant_answer_for_a_measured_form(empty_worker):
    a = client.get("/api/station/202451B0100").json()
    assert a["kind"] == "measured" and a["loc"]["state"] == "Oaxaca"
    assert any(r["code"] == "TOTAL" and r["paper"] == 271 for r in a["receipts"])
    t = _text(client.get("/station?c=202451B0100").text)
    assert "instant answer" in t and "the first capture keyed: 272" in t and "Open the full viewer" in t
    assert client.get(a["img"]).status_code == 200


def test_station_search_and_picker():
    r = client.get("/api/station/search?q=2024").json()["results"]
    assert r and all(x["clave"].startswith("2024") for x in r) and r[0]["state"] == "Oaxaca"
    d = client.get("/api/station/states/20").json()["districts"]
    assert d and client.get(f"/api/station/states/20/{d[0]['dist']}").json()["stations"]
    assert client.get("/api/station/99A").status_code == 404
    assert "is not a station id" in _text(client.get("/station?c=12").text)


def test_station_not_audited_then_queued_with_position(queue_worker):
    root, (k1, k2) = queue_worker
    a = client.get(f"/api/station/{k1}").json()
    assert a["kind"] == "not_audited"
    assert "Queue a live read on AMD" in _text(client.get(f"/station?c={k1}").text)
    j = client.post(f"/api/station/{k2}/queue").json()
    assert j["queued"] and j["position"] == 1
    j = client.post(f"/api/station/{k1}/queue").json()
    assert j["queued"] and j["position"] == 2 and j["waiting"] == 2
    assert client.post(f"/api/station/{k1}/queue").json()["position"] == 2      # idempotent
    a = client.get(f"/api/station/{k1}").json()
    assert a["kind"] == "queued" and a["position"] == 2
    assert "position, of 2 waiting" in _text(client.get(f"/station?c={k1}").text)
    # the worker takes requested stations first, in request order
    todo = W.load_queue(root / "queue.json.gz")["items"]
    assert [it["clave"] for it in prioritized(todo, root)] == [k2, k1]
    assert json.loads((root / "priority.json").read_text())["items"][0]["clave"] == k2


def test_station_queue_refuses_measured_and_unknown(queue_worker):
    assert client.post("/api/station/202451B0100/queue").json()["queued"] is False
    assert client.post("/api/station/999999Z9999/queue").status_code == 404


def test_station_queue_is_capped(queue_worker, monkeypatch):
    root, (k1, k2) = queue_worker
    monkeypatch.setattr(ST, "MAX_PENDING", 1)
    assert client.post(f"/api/station/{k1}/queue").status_code == 200
    r = client.post(f"/api/station/{k2}/queue")
    assert r.status_code == 429 and r.json()["refused"] == "full"


def test_no_party_names_on_new_pages(empty_worker):
    urls = ["/", "/station", "/station?c=202451B0100", "/station?c=070207C0100", "/api/live-strip",
            "/api/station/202451B0100", "/api/station/search?q=0702", "/api/station/states/7", "/results", "/api"]
    for u in urls:
        r = client.get(u)
        assert r.status_code == 200, u
        m = PARTY.search(r.text) or PARTY_CI.search(r.text)
        assert m is None, (u, r.text[max(0, m.start() - 60):m.end() + 60] if m else "")


# ------------------------------------------------------------------------------------------------ phone
def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture(scope="module")
def server():
    uvicorn = pytest.importorskip("uvicorn")
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    th.join(timeout=5)


def test_phone_first_screen(server):
    sync = pytest.importorskip("playwright.sync_api")
    try:
        p = sync.sync_playwright().start()
        br = p.chromium.launch()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"no browser: {e}")
    try:
        pg = br.new_page(viewport={"width": 390, "height": 844})
        pg.goto(server + "/", wait_until="domcontentloaded")
        fold = 844

        def box(sel):
            el = pg.locator(sel).first
            return el.bounding_box() if el.is_visible() else None

        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        assert box("#menubtn") and box(".brand")
        for sel in (".f-h1", ".n-aud", ".n-conf", "#rcard", ".f-actions .btn.primary"):
            b = box(sel)
            assert b and b["y"] + b["height"] <= fold, (sel, b)
        assert box(".n-disp") is None and box(".f-second") is None and box(".nav a") is None
        assert pg.locator(".f-actions .btn:visible").count() == 1
        assert pg.inner_text(".f-actions .btn.primary").strip() == "Pick any polling station"
        for sel in (".below-fold .f-sub", ".below-fold .f-diff", "#measured"):
            b = box(sel)
            assert b and b["y"] >= fold, (sel, b)
        rc = pg.locator("#rcard .rslide.on .rvals")
        assert float(pg.evaluate("e => parseFloat(getComputedStyle(e).fontSize)", rc.element_handle())) >= 13
    finally:
        br.close()
        p.stop()


def test_prep_procedure_note_under_the_counter():
    h = client.get("/").text
    first = re.search(r'<section class="first".*?</section>', h, flags=re.S).group(0)
    t = _text(first)
    b = numbersmod.home(ST.storemod.get_store())["business"]["per_1000_g"]
    note = f"This is that step, for {b} per 1,000 forms."
    assert note in t and t.index("confirmed by the certified count") < t.index("Required by the PREP procedure") < t.index(note)
    assert "CGex202311-03-ap-8-a.pdf" in first and 'href="/business.md"' in first
    assert client.get("/business.md").status_code == 200


def test_results_has_every_gate_tier_in_one_table():
    from app import gates
    G = gates.table()
    rows = {r["key"]: (r["accepted"], r["errors"], r["fields"]) for r in G["rows"]}
    T = numbersmod.tiers()["tiers"]
    for k in ("gemma", "gemma_capture", "qwen", "two_reader", "v2_2r", "v2_2r_strict"):
        assert rows[k] == (T[k]["accepted"], T[k]["errors"], T[k]["fields"])
    assert {"v2", "v2b (relaxed label, secondary)"} <= set(rows)
    assert all(r["post_hoc"] == r["key"].startswith("v2") for r in G["rows"])
    t = _text(client.get("/results").text)
    assert t.count("Every gate tier, one table") == 1 and G["takeaway"] in t
