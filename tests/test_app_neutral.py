"""Party neutrality: no party acronym appears in any rendered page or any JSON the app serves.
Vote rows are shown as "Option NN"; the other lines of the form by plain-English names."""
import json
import re
import threading

import pytest
from fastapi.testclient import TestClient

from app import live as livemod
from app import review as reviewmod
from app import store as storemod
from app.main import app

client = TestClient(app)
PARTY = re.compile(r"(?<![A-Za-z0-9])(PAN|PRI|PRD|PVEM|PT|MC|MORENA)(?![A-Za-z0-9])")
PARTY_CI = re.compile(r"(?<![A-Za-z0-9])(morena|pvem|verde)(?![A-Za-z0-9])", re.I)


def _clean(text, where):
    m = PARTY.search(text) or PARTY_CI.search(text)
    assert m is None, (where, text[max(0, m.start() - 80):m.end() + 80] if m else "")


def _all_urls():
    s = storemod.get_store()
    urls = ["/", "/forms", "/review", "/audit", "/results", "/healthz", "/api/live/status", "/try", "/inbox", "/api",
            "/api/export.csv", "/api/export.json", "/api/export.csv?status=accepted", "/openapi.json", "/audit/new", "/audit/request", "/keyer?s=1"]
    for k in s.ine_claves():
        urls += [f"/form/{k}", f"/api/form/{k}"]
        for rid in s.runs:
            if k in s.runs[rid]["reads"]:
                urls += [f"/form/{k}?run={rid}", f"/api/form/{k}?run={rid}"]
    urls += [f"/ledger/{sh['id']}" for sh in s.ledger["sheets"]]
    return urls


def test_no_party_names_in_any_page_or_json():
    for u in _all_urls():
        r = client.get(u)
        assert r.status_code == 200, u
        _clean(r.text, u)


def test_vote_rows_are_options_in_viewer():
    html = client.get("/form/211294C0100").text
    assert "Option 01" in html and "Option 15" in html and "Option 16" not in html
    assert "Unused ballots" in html and "Null votes" in html and "Unregistered candidates" in html


def test_review_response_and_crop_codes_are_neutral(tmp_path, monkeypatch):
    monkeypatch.setattr(reviewmod, "FILE", tmp_path / "review.json")
    j = client.post("/api/review/141097C0100", json={"values": {"OPT02": "38"}})
    assert j.status_code == 200
    _clean(j.text, "review POST")
    _clean((tmp_path / "review.json").read_text() if (tmp_path / "review.json").exists() else "", "review.json")
    s = storemod.get_store()
    if s.masked_image("211294C0100"):
        assert client.get("/crop/211294C0100/OPT01.jpg").status_code == 200
        assert client.get("/crop/211294C0100/PAN.jpg").status_code == 404


def test_live_events_are_neutral(tmp_path, monkeypatch):
    s = storemod.get_store()
    if s.masked_image("211294C0100") is None:
        pytest.skip("no masked page")
    monkeypatch.setattr(livemod, "LIVE_DIR", tmp_path / "live")
    monkeypatch.setattr(livemod, "BUDGET_FILE", tmp_path / "budget.json")
    sch = storemod.schema()
    r = s.runs["spike-gemma-v2"]["reads"]["211294C0100"]
    items = [{"label": "PAN+PRI+PRD", "n": r.values[f["key"]], "w": r.words[f["key"]]} for f in sch["fields"]]
    m = livemod.LiveManager(reader_fn=lambda model, page: {"parsed": {"values": items}, "usage": {"cost": 0.0001},
                                                           "secs": 1.0}, usage_fn=lambda: {}, reveal_delay=0)
    old = app.state.live
    app.state.live = m
    try:
        job = client.post("/api/live/211294C0100").json()["job"]
        with client.stream("GET", f"/api/live/events/{job}") as resp:
            text = "".join(resp.iter_lines())
        _clean(text, "SSE")
        assert "Option 01" in text
    finally:
        app.state.live = old


def test_spot_check_pages_are_neutral(tmp_path, monkeypatch):
    """Every spot-check item shows its field as 'Option NN' (or a plain name), never a party; the results page and
    its JSON name the items the same way, and every crop it serves exists."""
    from app import spotcheck as sc
    monkeypatch.setattr(sc, "FILE", tmp_path / "spotcheck.json")
    q = sc.queue()
    assert q
    for i in range(len(q)):
        r = client.get(f"/check?i={i}")
        assert r.status_code == 200
        _clean(r.text, f"/check?i={i}")
        assert client.get(f"/check/img/{i}.jpg").status_code == 200, q[i]
    # answer every item with a value that disagrees, so every item and its evidence appear on the results page
    for i in range(len(q)):
        assert client.post(f"/api/check/{i}", json={"digits": "99999"}).status_code == 200
    for u in ("/check/results", "/api/check/results", "/check"):
        r = client.get(u)
        assert r.status_code == 200
        _clean(r.text, u)
    assert "Option " in client.get("/check/results").text


def test_keyer_pages_are_neutral():
    """Be the second keyer: the blind page, every crop, and the reveal (with its evidence lines) show Option NN or a
    plain name, never a party, for many rounds; no title says 'election'."""
    from app import keyer
    covered = set()
    for s in range(1, 41):
        for u in (f"/keyer?s={s}", f"/keyer/reveal?s={s}&a=1&a=b&a=%3F&a=&a=12"):
            r = client.get(u)
            assert r.status_code == 200, u
            _clean(r.text, u)
            assert "election" not in r.text.split("</title>")[0].lower()
        covered.update(keyer.draw(s))
        assert client.get(f"/keyer/img/{s}/0.jpg").status_code == 200
    assert "Option " in "".join(client.get(f"/keyer/reveal?s={s}").text for s in range(1, 41))
    assert len(covered) > 100


def test_audit_page_is_neutral_and_complete():
    from app.numbers import headline
    H = headline()
    html = client.get("/audit").text
    _clean(html, "/audit")
    assert html.count('class="card err"') == H["keying_errors"]
    for t in H["by_type"]:
        assert t["label"].replace('"', "&#34;") in html or t["label"] in html
    assert "label=0" in html  # crops start right of the printed row label: no logo


def test_capture_audit_pages_and_exports_are_neutral(tmp_path, monkeypatch):
    """Audit your capture: the keyed CSV uses INE column names (PAN, MORENA, ...), but every page, JSON and export of
    the audit shows Option NN, including the mapping proposal that echoes the auditor's columns, and an auditor mark."""
    from app import capture_audit as ca
    monkeypatch.setattr(ca, "AUDITS", tmp_path / "audits")
    assert PARTY.search(ca.SAMPLE_CSV.read_text(encoding="utf-8"))  # the machine file keeps INE's names
    prop = client.post("/api/audit?name=PAN-MORENA.csv", content=ca.SAMPLE_CSV.read_bytes(),
                       headers={"Content-Type": "text/csv"})
    _clean(prop.text, "proposal")
    aid = client.post("/api/audit/sample").json()["id"]
    client.post(f"/api/audit/{aid}/mark", json={"key": "050815B0100__OPT07", "mark": "not_error"})
    for u in ("/audit/new", f"/audit/{aid}", f"/audit/{aid}/report", f"/audit/{aid}/report.csv", f"/api/audit/{aid}",
              f"/audit/{prop.json()['id']}"):
        r = client.get(u)
        assert r.status_code == 200, u
        _clean(r.text, u)
        assert "election" not in re.sub(r"<[^>]+>", "", r.text.split("</title>")[0]).lower()
    assert "Option 07" in client.get(f"/audit/{aid}/report.csv").text
