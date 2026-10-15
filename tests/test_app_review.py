"""Review desk: a typed value re-checks the identities and resolves the form; stored in a local JSON file."""
import json

import pytest
from fastapi.testclient import TestClient

from app import review as reviewmod
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def tmp_review(tmp_path, monkeypatch):
    monkeypatch.setattr(reviewmod, "FILE", tmp_path / "review.json")
    yield tmp_path / "review.json"


def test_queue_lists_routed_forms_with_named_field():
    html = client.get("/review").text
    assert "211294C0100" in html and "TOTAL digits 262, words 162" in html
    assert "201720E0100" not in html  # accepted form is not in the queue


def test_wrong_value_keeps_form_open(tmp_review):
    r = client.post("/api/review/211294C0100", json={"values": {"TOTAL": "162"}})
    assert r.status_code == 200 and r.json()["status"] == "open"
    assert not tmp_review.exists() or "211294C0100" not in json.loads(tmp_review.read_text())


def test_right_value_resolves_and_persists(tmp_review):
    r = client.post("/api/review/211294C0100", json={"values": {"TOTAL": "262"}, "note": "digits and rows agree"})
    j = r.json()
    assert j["status"] == "resolved" and j["recheck"]["accepted"]
    saved = json.loads(tmp_review.read_text())
    assert saved["211294C0100"]["values"] == {"TOTAL": 262}
    assert ">resolved<" in client.get("/review").text
    assert client.delete("/api/review/211294C0100").status_code == 200
    assert "211294C0100" not in json.loads(tmp_review.read_text())


def test_escalate_and_bad_input(tmp_review):
    assert client.post("/api/review/211294C0100", json={"values": {"TOTAL": "abc"}}).status_code == 400
    j = client.post("/api/review/211294C0100", json={"action": "escalate", "note": "words and digits disagree"}).json()
    assert j["status"] == "escalated"
    assert client.post("/api/review/NOPE", json={}).status_code == 404
