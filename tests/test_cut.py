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
H1 = "OCR reads the number. Two Hands checks whether the whole form agrees."
EYEBROW = "Two Hands · verifiable quality control for handwritten numbers"
PRIMARY = "Read a real tally sheet live on AMD"
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
    """Home is the product page: the hook, a real receipt, three proof tiles that link to their evidence on /results,
    the actions. The background that used to follow moved to /results (tests below check it there)."""
    h = client.get("/").text
    first = re.search(r'<section class="first".*?</section>', h, flags=re.S).group(0)
    t = _text(first)
    from app import honest
    tiles = honest.proof_tiles(numbersmod.headline())
    marks = [EYEBROW, H1, "The paper: 175 · The first capture keyed: 75 · The certified count: 175",
             'In English: words: "ciento setenta y cinco" = 175 · boxes: 1 7 5',
             "certified count, by comparison", "050815B0100", "verify this receipt"]
    marks += [x["big"] for x in tiles] + [PRIMARY, "Audit your capture", "or try your own sheet"]
    pos = [t.find(m) for m in marks]
    assert all(p >= 0 for p in pos), [m for m, p in zip(marks, pos) if p < 0]
    assert pos == sorted(pos), list(zip(marks, pos))
    assert h.count("<h1") == 1 and f">{H1}</h1>" in h
    # the three tiles: the head-to-head, the recall, sheets read and certified-confirmed errors, each to its evidence
    assert [x["href"] for x in tiles] == ["/results#ieebcs", "/results#colima", "/results#random300"]
    assert "91.6% vs 62.84%" in t and "27 of 28" in t
    assert "1,270 real tally sheets read on AMD; 49 capture errors confirmed by the certified count" in t
    res = client.get("/results").text
    for x in tiles:
        assert f'id="{x["href"].split("#")[1]}"' in res, x["href"]
    # the actions: a live read of the receipt's own sheet, audit your capture, try your own sheet
    assert 'class="btn primary lg" href="/form/050815B0100#live"' in first
    assert 'href="/audit/new"' in first and 'href="/try"' in first
    # removed: the replay animation, any pilot number, the word touchless
    assert 'id="reader"' not in h and "loopData" not in h and "hero.js" not in h
    assert "pilot" not in t.lower() and "touchless" not in t.lower() and "spike" not in t.lower()
    # the receipt card links to Findings and to the field's Merkle receipt
    assert 'id="rcard"' in first and 'href="/audit"' in first and 'href="/verify/050815B0100/OPT07"' in first
    # the faint-pencil TOTAL is the second card, enhanced for display and labelled so
    assert '/crop/enhanced/070207C0100/TOTAL.jpg' in first and "enhanced for display" in first


def test_home_is_short_and_the_background_moved_to_results():
    """Home stays under 350 words of copy (the first receipt slide only: the others are hidden until they rotate);
    every section that left Home is on /results under its old id, and Home links to it."""
    h = client.get("/").text
    main = re.search(r"<main>(.*)</main>", h, flags=re.S).group(1)
    first, rest = main.split('<div class="rslide" data-i="1"', 1)
    rest = rest[rest.index('<div class="proof"'):]
    words = len(_text(first + rest).split())
    assert words <= 350, words
    res = client.get("/results").text
    for i in ("measured", "cost-of-problem", "who-pays", "ine-buyer", "offer-2027", "market-lines", "price-lines",
              "market-size", "next-markets", "amd-models", "any-form", "reg"):
        assert f'id="{i}"' in res and f'id="{i}"' not in h, i
    for i in ("cost-of-problem", "who-pays", "amd-models", "any-form"):
        assert f'href="/results#{i}"' in h, i
    heads = [_text(x) for x in re.findall(r"<h[23][^>]*>(.*?)</h[23]>", res, flags=re.S)]
    for s in ("Measured, not promised", "The cost of the problem", "Who pays, and what runs on AMD",
              "Open models on the AMD endpoint", "Any form that checks itself"):
        assert heads.count(s) == 1, s
    assert "(proposed)" in _text(res)   # the price keeps its qualifier where it moved
    js = client.get("/static/home.js").text   # old Home anchors are forwarded to /results
    assert "'who-pays'" in js and "'ine-buyer'" in js and "'any-form'" in js and "location.replace" in js


def test_strip_uses_live_numbers_once_the_worker_has_audited(monkeypatch):
    fake = {"audited": 41, "disputes": 9, "confirmed": 3, "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 300)), "reader_now": "Qwen3.8-27B",
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
    H = numbersmod.headline()
    # the strip sums the measured sample and the live worker, the same way for all three numbers
    assert (s["kind"], s["forms_audited"], s["disputes"], s["certified_confirmed"]) ==         ("live", H["forms"] + 41, H["disagree"] + 9, H["cert_agree"] + 3)
    assert s["states_complete"].startswith("1 of 32 states complete")
    assert s["reader_model"] == "Gemma-4-31B-IT (sample), Qwen3.8-27B (live)"
    t = _text(client.get("/").text)
    first = t.split("Background:")[0]
    assert f"{H['forms'] + 41} audited in total" in first and "1 states complete" in first
    assert "12.5 % of Baja California Sur so far" in first and "of 32" not in first
    assert f"{H['forms']} in the pre-registered sample · 41 live since" in first and "updated" in first
    # receipts come from the pre-registered random 300 only, never the live worker or the pilot
    rs = s["latest_receipts"]
    assert (rs[0]["clave"], rs[0]["code"]) == ("050815B0100", "OPT07")
    assert all(r["sample"] == "pre-registered random 300" for r in rs)
    assert "060102C0100" not in t and "060101C0100" not in t


def test_strip_hidden_when_the_live_worker_is_idle(monkeypatch):
    """Home shows the live strip only while the worker has written within honest.LIVE_FRESH_MIN minutes; idle (or
    never started), Home shows no live figures and keeps the background links. /live keeps the full status."""
    from app import honest
    base = {"audited": 41, "disputes": 9, "confirmed": 3, "reader_now": "Qwen3.8-27B", "queue_states": 32,
            "states": [{"name": "Colima", "complete": False, "pct": 1.0}], "status": {"kind": "live", "text": "Running"},
            "recent": []}
    for ago, shown in ((5, True), (honest.LIVE_FRESH_MIN, True), (honest.LIVE_FRESH_MIN + 2, False), (3000, False)):
        fake = dict(base, updated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 60 * ago - 1)))
        monkeypatch.setattr(LS, "_summary", lambda f=fake: f)
        h = client.get("/").text
        assert ('id="strip"' in h) == shown and ("of Colima so far" in h) == shown, ago
        assert 'href="/results#who-pays"' in h and "Background:" in _text(h)
    monkeypatch.setattr(LS, "_summary", lambda: None)
    h = client.get("/").text
    assert 'id="strip"' not in h and "Background:" in _text(h)
    assert client.get("/live").status_code == 200


def test_default_receipt_and_rotation_order(empty_worker):
    s = LS.status()
    rs = s["latest_receipts"]
    got = [(r["clave"], r["code"], r["paper"], r["capture"], r["certified"], r["conf_label"]) for r in rs[:4]]
    from app import spotcheck
    person = bool(spotcheck.load())
    assert got[:2] == [("050815B0100", "OPT07", 175, "75", 175, "certified count, by comparison"),
                       ("070207C0100", "TOTAL", 416, "Ilegible", 416, "certified count, by recount")]
    assert [g[:5] for g in got[2:]] == [("250767B0100", "VOTARON", 390, "3", None), ("080310B0100", "SOBRANTES", 180, "480", None)]
    if not person:   # nobody has spot-checked yet: never "confirmed by a person"
        assert all(g[5] == LS.AI_LABEL for g in got[2:])
    # every receipt is in the random 300 (results/manifest.json), none from the pilot
    import json
    from twohands import REPO
    man = {i["clave"] for i in json.loads((REPO / "results" / "manifest.json").read_text(encoding="utf-8"))["items"]}
    assert all(r["clave"] in man for r in rs) and len(rs) <= 8
    assert all(str(r["paper"]) != r["capture"] for r in rs)
    assert all(r["certified"] is None or r["certified"] == r["paper"] for r in rs)
    j = client.get("/api/live-strip").json()
    assert j["kind"] == "measured" and j["label"] == "measured sample"


def test_second_screen_measured_not_promised():
    t = _text(client.get("/results").text)   # moved from Home to /results
    m = t[t.index("Measured, not promised"):]
    m = m[:m.index("The cost of the problem")]
    H = numbersmod.headline()
    T = numbersmod.tiers()["tiers"]["two_reader"]
    for s in (f"{H['keying_errors']}", f"{H['cert_agree']} of {H['cert_covered']}", f"{H['accepted_pct']}%",
              f"{H['acc_model_wrong']} of {H['acc_fields']:,}", f"{T['errors']} of {T['fields']:,}",
              f"1 in {H['model_one_in']} vs 1 in {H['acc_one_in']}", f"1 in {H['yield_one_in']} vs 1 in {H['random_one_in']}"):
        assert s in m, s
    h = client.get("/results").text
    assert "/static/builder.webm" in h and "/audit/request" in h and "/audit/request" in client.get("/").text


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
        pg.goto(server + "/", wait_until="load")
        pg.evaluate("document.fonts.ready.then(() => true)")   # measure with the web font, as a phone shows it
        fold = 844

        def box(sel):
            el = pg.locator(sel).first
            return el.bounding_box() if el.is_visible() else None

        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        assert box("#menubtn") and box(".brand")
        for sel in (".f-h1", "#rcard", ".f-actions .btn.primary"):
            b = box(sel)
            assert b and b["y"] + b["height"] <= fold, (sel, b)
        assert box(".n-disp") is None and box(".nav a") is None
        assert pg.locator(".f-actions .btn:visible").count() == 2
        assert pg.inner_text(".f-actions .btn.primary").strip() == PRIMARY
        assert box("#rcard")["y"] < box(".f-actions .btn.primary")["y"] < box("#proof")["y"]
        for sel in ("#how", "#strip") if pg.locator("#strip").count() else ("#how",):
            b = box(sel)
            assert b and b["y"] >= fold, (sel, b)
        rc = pg.locator("#rcard .rslide.on .rvals")
        assert float(pg.evaluate("e => parseFloat(getComputedStyle(e).fontSize)", rc.element_handle())) >= 13
    finally:
        br.close()
        p.stop()



@pytest.mark.parametrize("w,h", [(1366, 768), (1366, 900), (1280, 800), (1440, 900)])
def test_desktop_first_screen(server, w, h):
    """Desktop fold: the hook, the receipt, the three proof tiles and both first-screen buttons."""
    sync = pytest.importorskip("playwright.sync_api")
    try:
        p = sync.sync_playwright().start()
        br = p.chromium.launch()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"no browser: {e}")
    try:
        pg = br.new_page(viewport={"width": w, "height": h})
        pg.goto(server + "/", wait_until="load")
        pg.evaluate("document.fonts.ready.then(() => true)")
        assert pg.evaluate("document.documentElement.scrollWidth") <= w
        boxes = {}
        for sel in (".f-h1", "#rcard", "#proof", ".f-actions .btn.primary", ".f-actions .f-second"):
            el = pg.locator(sel).first
            b = el.bounding_box() if el.is_visible() else None
            assert b and b["y"] + b["height"] <= h, (sel, b)
            boxes[sel] = b
        assert pg.inner_text(".f-actions .btn.primary").strip() == PRIMARY
        assert pg.locator(".ptile").count() == 3   # the proof tiles sit beside the receipt, above the actions
        assert pg.locator(".ptile").last.bounding_box()["y"] < boxes[".f-actions .btn.primary"]["y"]
    finally:
        br.close()
        p.stop()

def test_prep_procedure_note_on_results():
    """The regulated step (numeral 33), its sources and the compute cost moved with the buyer section to /results."""
    h = client.get("/results").text
    sec = re.search(r'<section id="who-pays".*?</section>', h, flags=re.S).group(0)
    t = _text(sec)
    b = numbersmod.home(ST.storemod.get_store())["business"]["per_1000_g"]
    from app.honest import REG_LINE
    note = f"The second capture costs {b} of AMD compute per 1,000 forms."
    assert note in t and t.index(REG_LINE) < t.index(note)
    assert "CGex202311-03-ap-8-a.pdf" in sec and 'href="/business.md"' in sec
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


def test_ieebcs_card_names_the_stack_per_run():
    from app import ieebcs_card
    assert ieebcs_card.stack({"model": "gemma", "served_models": ["Gemma-4-31B-IT"]}) == "Token Factory, Gemma-4-31B-IT"
    assert ieebcs_card.stack({"model": "gemma", "served_models": ["google/gemma-4-31B-it"]}) == \
        "self-hosted vLLM on MI300X, google/gemma-4-31B-it"


def test_verify_this_receipt_resolves_to_the_published_root(empty_worker):
    from twohands import REPO
    root = (REPO / "results" / "sample_audit_root.txt").read_text(encoding="utf-8").split()[0]
    j = client.get("/verify/070207C0100/TOTAL", follow_redirects=True).json()
    assert j["root"] == root and j["leaf"]["form"] == "070207C0100" and j["leaf"]["field"] == "TOTAL"


def test_spanish_number_words_are_captioned_in_english():
    from app import caption as C
    assert C.es_to_int("ciento setenta y cinco") == 175 and C.es_to_int("Cuatrocientos dieciseis") == 416
    assert C.es_to_int("Trecientos Noventa") == 390 and C.es_to_int("veinti siete") == 27
    assert C.es_to_int("Dos cuarenta y siete") is None and C.es_to_int("Veinti...") is None
    # every parsed caption of the adjudication agrees with the adjudicated paper value
    for k, v in C._verdicts().items():
        w = C.parse_evidence(v.get("evidence", ""))["words"]
        n = C.es_to_int(w) if w else None
        if n is not None and isinstance(v.get("paper"), int):
            assert n == v["paper"], k
    assert C.caption("080310B0100", "SOBRANTES") == 'words: "CIENTO OCHENTA" = 180 · boxes: 1 8 0'


def test_judge_page_asks_digits_and_helps_with_spanish(empty_worker):
    t = _text(client.get("/judge/050815B0100/OPT07").text)
    assert "The digits in the boxes" in t and "(optional)" in t and "novecientos" in t
    assert "ciento setenta y cinco" not in t.lower().replace("ciento setenta y cinco = 100", "")  # no reveal before answering
    a = _text(client.get("/audit").text)
    assert 'In English: words: "ciento setenta y cinco" = 175 · boxes: 1 7 5' in a
