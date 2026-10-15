"""Blind spot-check (/check): queue, blindness, saving answers, and the agreement math."""
import json

import pytest
from fastapi.testclient import TestClient

from app import spotcheck as sc
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def tmp_answers(tmp_path, monkeypatch):
    monkeypatch.setattr(sc, "FILE", tmp_path / "spotcheck.json")
    yield tmp_path / "spotcheck.json"


def test_queue_composition_is_fixed_and_deduplicated():
    V, L = sc.load_verdicts(), sc.load_ledger()
    q = sc.build_queue(V, L)
    assert q == sc.build_queue(V, L) and len(q) == len(set(q))
    mr = {k for k, v in V.items() if v["verdict"] == "model_right"}
    acc = {k for k in V if (L.get(k) or {}).get("form_accepted")}
    assert mr <= set(q) and acc <= set(q)
    other = set(q) - mr - acc
    assert len(set(q) - mr) >= len(other) and len(set(q) - mr - acc) <= sc.OTHER_N
    assert not any(V[k]["verdict"] == "crop_wrong" for k in q)
    assert len(q) == len(mr | acc | (set(q) - mr - acc))


def test_check_page_is_blind():
    V = sc.load_verdicts()
    q = sc.queue()
    html = client.get("/check?i=0").text
    v = V[q[0]]
    for word in ("model_right", "capture_right", "paper_ambiguous", "PREP", "Computos", "evidence"):
        assert word not in html
    assert v.get("evidence", "")[:20] not in html or not v.get("evidence")
    assert "/check/img/0.jpg" in html
    r = client.get("/check/img/0.jpg")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert client.get(f"/check/img/{len(q)}.jpg").status_code == 404


def test_answer_saves_and_points_to_next(tmp_answers):
    r = client.post("/api/check/0", json={"digits": "175", "words": "175"})
    j = r.json()
    assert r.status_code == 200 and j["next"] == 1 and j["answered"] == 1
    saved = json.loads(tmp_answers.read_text())
    assert saved[sc.queue()[0]]["digits"] == 175
    assert client.post("/api/check/1", json={}).status_code == 400  # nothing typed, nothing ticked
    assert "Item 2 /" in client.get("/check").text  # resumes at the first unanswered item


def test_clean_answer_shortcuts():
    assert sc.clean_answer({"digits": "b"})["blank"] is True
    assert sc.clean_answer({"digits": "?"})["cant_tell"] is True
    a = sc.clean_answer({"digits": "75", "words": "175"})
    assert a["differ"] is True and a["digits"] == 75


def test_agreement_math():
    v_int = {"verdict": "model_right", "paper": 180}
    v_blank = {"verdict": "model_right", "paper": "blank"}
    v_amb = {"verdict": "paper_ambiguous", "paper": "24/21"}
    v_unr = {"verdict": "unreadable", "paper": None}
    assert sc.agrees({"digits": 180}, v_int)
    assert not sc.agrees({"digits": 480}, v_int)
    assert not sc.agrees({"cant_tell": True}, v_int)            # person ambiguous, AI decided
    assert sc.agrees({"blank": True}, v_blank)
    assert sc.agrees({"differ": True, "digits": 24, "words": 21}, v_amb)
    assert sc.agrees({"cant_tell": True}, v_unr)
    assert not sc.agrees({"digits": 24, "words": 24}, v_amb)    # person sure, AI ambiguous
    q = ["a", "b", "c"]
    V = {"a": v_int, "b": v_amb, "c": v_unr}
    res = sc.score({"a": {"digits": 180}, "b": {"digits": 5}}, q, V)
    assert res["answered"] == 2 and res["agree"] == 1 and res["rate"] == 0.5
    assert res["model_right"] == {"agree": 1, "n": 1}
    assert [d["item"] for d in res["disagreements"]] == ["b"]


def test_results_page_renders(tmp_answers):
    client.post("/api/check/0", json={"cant_tell": True})
    html = client.get("/check/results").text
    assert "/ 1" in html and "AI verdict" in html
    assert client.get("/api/check/results").json()["answered"] == 1
