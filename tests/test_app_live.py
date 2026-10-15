"""Live read with a mocked reader and endpoint: SSE stream, one-at-a-time lock, budget and endpoint guards.
No request ever reaches the real AMD endpoint from these tests."""
import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import live as livemod
from app import store as storemod
from app.main import app

client = TestClient(app)
FORM = "201720E0100"


def _parsed_from_spike(clave):
    """A core-format read (values list with printed labels) built from the spike read of a form."""
    s = storemod.schema()
    r = storemod.get_store().runs["spike-gemma-v2"]["reads"][clave]
    lab = {"SOBRANTES": "BOLETAS SOBRANTES", "VOTARON": "PERSONAS DE LA LISTA NOMINAL QUE VOTARON",
           "REPRESENTANTES": "REPRESENTACIONES PARTIDISTAS QUE VOTARON",
           "PERSONAS_Y_REP": "TOTAL DE PERSONAS Y REPRESENTANTES QUE VOTARON", "SACADOS": "TOTAL DE VOTOS SACADOS",
           "NO_REGISTRADAS": "CANDIDATOS NO REGISTRADOS", "NULOS": "VOTOS NULOS", "TOTAL": "TOTAL"}
    items = []
    for f in s["fields"]:
        label = lab.get(f["key"]) or "+".join(f["label"]["parties"])
        items.append({"label": label, "n": r.values[f["key"]], "w": r.words[f["key"]]})
    return {"values": items}


@pytest.fixture
def mgr(tmp_path, monkeypatch):
    monkeypatch.setattr(livemod, "LIVE_DIR", tmp_path / "live")
    monkeypatch.setattr(livemod, "BUDGET_FILE", tmp_path / "budget.json")
    gate = threading.Event()
    calls = []

    def reader(model, page):
        calls.append((model, str(page)))
        gate.wait(5)
        return {"parsed": _parsed_from_spike(FORM), "secs": 1.2, "finish_reason": "stop",
                "usage": {"cost": 0.00012, "prompt_tokens": 2000, "completion_tokens": 700}}

    m = livemod.LiveManager(reader_fn=reader, usage_fn=lambda: {"daily_cost_remaining_usd": 0.9}, reveal_delay=0)
    m.gate, m.calls = gate, calls
    old = app.state.live
    app.state.live = m
    yield m
    gate.set()
    app.state.live = old


def _events(job):
    with client.stream("GET", f"/api/live/events/{job}") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        return [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]


def test_live_read_streams_fields_and_verdict(mgr):
    if storemod.get_store().masked_image(FORM) is None:
        pytest.skip("no masked page")
    r = client.post(f"/api/live/{FORM}")
    assert r.status_code == 200
    job = r.json()["job"]
    # a second live read anywhere on the site is refused while the first runs
    r2 = client.post("/api/live/211294C0100")
    assert r2.status_code == 409 and r2.json()["refused"] == "busy"
    mgr.gate.set()
    evs = _events(job)
    kinds = [e["type"] for e in evs]
    assert kinds.count("field") == len(storemod.schema()["fields"])
    assert kinds.count("identity") == len(storemod.schema()["identities"])
    v = next(e for e in evs if e["type"] == "verdict")
    assert v["accepted"] and v["line"] == "Accepted: 0 fields to key"
    assert kinds[-1] == "done"
    assert storemod.MASKED in Path(mgr.calls[0][1]).resolve().parents  # only the masked page is sent
    assert (livemod.LIVE_DIR / f"{FORM}.json").exists()
    assert json.loads(livemod.BUDGET_FILE.read_text())  # spend recorded
    for _ in range(50):
        if not mgr.status()["busy"]:
            break
        time.sleep(0.05)
    assert not mgr.status()["busy"]


def test_live_refuses_when_shared_budget_low(mgr):
    mgr.usage_fn = lambda: {"daily_cost_remaining_usd": 0.01}
    r = client.post(f"/api/live/{FORM}")
    if storemod.get_store().masked_image(FORM) is None:
        assert r.json()["refused"] == "no_image"
        return
    assert r.status_code == 503 and r.json()["refused"] == "budget"
    assert not mgr.status()["busy"] and mgr.calls == []


def test_live_refuses_when_endpoint_down(mgr):
    def down():
        raise TimeoutError("x")
    mgr.usage_fn = down
    r = client.post(f"/api/live/{FORM}")
    assert r.status_code in (409, 503) and r.json()["refused"] in ("endpoint", "no_image")
    assert mgr.calls == []


def test_live_refuses_over_local_daily_cap(mgr, monkeypatch):
    monkeypatch.setattr(livemod, "MAX_READS_PER_DAY", 0)
    r = client.post(f"/api/live/{FORM}")
    assert r.json()["refused"] in ("budget", "no_image")
    assert mgr.calls == []


def test_live_reader_failure_reports_and_releases(mgr):
    if storemod.get_store().masked_image(FORM) is None:
        pytest.skip("no masked page")
    mgr.reader_fn = lambda model, page: {"error": "GaveUp: HTTP 503", "parsed": None, "usage": {}}
    job = client.post(f"/api/live/{FORM}").json()["job"]
    evs = _events(job)
    assert any(e["type"] == "error" for e in evs) and evs[-1]["type"] == "done"
    time.sleep(0.1)
    assert not mgr.status()["busy"]


def test_live_refuses_form_without_masked_page(mgr):
    s = storemod.get_store()
    k = next((k for k in s.ine_claves() if s.masked_image(k) is None), None)
    if k is None:
        pytest.skip("every form is masked")
    r = client.post(f"/api/live/{k}")
    assert r.status_code == 409 and r.json()["refused"] == "no_image"
