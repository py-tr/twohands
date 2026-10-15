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
            "/api/export.csv", "/api/export.json", "/api/export.csv?status=accepted", "/openapi.json"]
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
