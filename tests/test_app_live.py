"""Live read with a mocked reader and endpoint: SSE stream, one-at-a-time queue, budget and endpoint guards,
AMD 503 fallback.
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


def drain(m, timeout=5.0):
    """Let queued jobs finish while the test's paths are still patched."""
    t = time.time() + timeout
    while m.status()["busy"] and time.time() < t:
        time.sleep(0.02)


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
    drain(m)
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
    # a second live read waits in the queue behind the first (one at a time on the shared endpoint)
    for _ in range(100):
        if mgr.calls:  # the first read is with the model
            break
        time.sleep(0.02)
    r2 = client.post("/api/live/211294C0100")
    assert r2.status_code == 200 and r2.json()["position"] == 1
    st = client.get(f"/api/jobs/{r2.json()['job']}").json()
    assert st["state"] == "queued" and st["position"] == 1
    assert len(mgr.calls) == 1  # the second read has not reached the model
    mgr.gate.set()
    evs = _events(job)
    kinds = [e["type"] for e in evs]
    assert kinds.count("field") == len(storemod.schema()["fields"])
    assert kinds.count("identity") == len(storemod.schema()["identities"])
    v = next(e for e in evs if e["type"] == "verdict")
    assert v["accepted"] and v["line"] == "Accepted: 0 fields to key"
    # the receipt next to the verdict: model, endpoint, tokens in/out, latency and cost of this call
    assert v["model"] == "Gemma-4-31B-IT" and v["endpoint"] == "AMD Token Factory"   # conftest: Gemma is listed
    assert (v["prompt_tokens"], v["completion_tokens"], v["secs"], v["cost"]) == (2000, 700, 1.2, 0.00012)
    js = (Path(livemod.__file__).resolve().parents[1] / "static" / "live.js").read_text(encoding="utf-8")
    assert "data-receipt" in js and "tokens in / " in js and "ev.endpoint" in js and "ev.prompt_tokens" in js
    assert kinds[-1] == "done"
    # the queued second read now runs and writes the same budget file: wait for it before reading any file
    drain(mgr)
    assert not mgr.status()["busy"]
    assert len(mgr.calls) == 2  # the second read reached the model only after the first finished
    assert storemod.MASKED in Path(mgr.calls[0][1]).resolve().parents  # only the masked page is sent
    assert (livemod.LIVE_DIR / f"{FORM}.json").exists()
    assert next(iter(json.loads(livemod.BUDGET_FILE.read_text()).values()))["reads"] == 2  # both spends recorded


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


def test_live_queue_is_bounded(mgr, monkeypatch):
    if storemod.get_store().masked_image(FORM) is None:
        pytest.skip("no masked page")
    monkeypatch.setattr(livemod, "QUEUE_MAX", 2)
    assert client.post(f"/api/live/{FORM}").status_code == 200
    assert client.post(f"/api/live/{FORM}").status_code == 200
    r = client.post(f"/api/live/{FORM}")
    assert r.status_code == 409 and r.json()["refused"] == "busy"
    mgr.gate.set()


def test_live_amd_503_falls_back_to_measured_read(mgr):
    """A mocked AMD 503: the job ends with endpoint_busy and names the form whose measured read to show."""
    if storemod.get_store().masked_image(FORM) is None:
        pytest.skip("no masked page")
    mgr.reader_fn = lambda model, page: {"error": "GaveUp: HTTP 503: upstream unavailable", "parsed": None, "usage": {}}
    job = client.post(f"/api/live/{FORM}").json()["job"]
    evs = _events(job)
    err = next(e for e in evs if e["type"] == "error")
    assert err["code"] == "endpoint_busy" and err["fallback"] == FORM
    assert "AMD endpoint busy" in err["msg"] and "last measured read" in err["msg"]
    assert client.get(f"/api/jobs/{job}").json()["state"] == "failed"
    # the fallback the page then shows is the stored read of the same form
    j = client.get(f"/api/form/{FORM}").json()
    assert j["verdict"]["fields"] and j["verdict"]["line"]


def test_live_timeout_is_reported_as_busy_endpoint(mgr):
    if storemod.get_store().masked_image(FORM) is None:
        pytest.skip("no masked page")
    mgr.reader_fn = lambda model, page: {"error": "TimeoutError: The read operation timed out", "parsed": None}
    evs = _events(client.post(f"/api/live/{FORM}").json()["job"])
    assert next(e for e in evs if e["type"] == "error")["code"] == "endpoint_busy"


def test_live_queued_job_rechecks_budget_when_it_starts(mgr):
    if storemod.get_store().masked_image(FORM) is None:
        pytest.skip("no masked page")
    job = client.post(f"/api/live/{FORM}").json()["job"]
    mgr.usage_fn = lambda: {"daily_cost_remaining_usd": 0.0}  # spent while the job waited
    mgr.gate.set()
    evs = _events(job)
    assert any(e["type"] in ("verdict", "error") for e in evs) and evs[-1]["type"] == "done"


def test_job_status_unknown_404():
    assert client.get("/api/jobs/nope").status_code == 404


def test_live_per_visitor_daily_cap(mgr, monkeypatch):
    """One visitor (client address) gets LIVE_MAX_READS_PER_IP live reads a UTC day, queued ones included; then the
    read is refused as "budget" (the page falls back to the measured read) while other visitors still get theirs."""
    s = storemod.get_store()
    if s.masked_image(FORM) is None:
        pytest.skip("no masked page")
    monkeypatch.setattr(livemod, "MAX_READS_PER_IP", 2)
    assert client.post(f"/api/live/{FORM}").status_code == 200
    assert client.post(f"/api/live/{FORM}").status_code == 200   # queued behind the first: counts already
    r = client.post(f"/api/live/{FORM}")
    assert r.status_code == 503 and r.json()["refused"] == "budget" and "per visitor" in r.json()["message"]
    mgr.gate.set()
    drain(mgr)
    day = next(iter(json.loads(livemod.BUDGET_FILE.read_text()).values()))
    assert day["reads"] == 2 and list(day["ips"].values()) == [2]
    assert "testclient" not in livemod.BUDGET_FILE.read_text()   # the address is stored hashed
    assert client.post(f"/api/live/{FORM}").json()["refused"] == "budget"   # spent reads still count
    tok = livemod.CLIENT_IP.set("203.0.113.9")   # another visitor is not affected
    try:
        job = mgr.start(FORM, s.masked_image(FORM))
    finally:
        livemod.CLIENT_IP.reset(tok)
    assert job.ip and job.ip != next(iter(day["ips"]))
    drain(mgr)


def test_live_without_key_is_off_and_falls_back(monkeypatch, tmp_path):
    """A fresh clone has no AMD key: the live read is refused as "off" (never "endpoint busy"), with the fallback."""
    monkeypatch.setattr(livemod, "BUDGET_FILE", tmp_path / "budget.json")

    def no_key():
        raise RuntimeError("AMD_KEY / AMD_BASE_URL not configured")
    m = livemod.LiveManager(reader_fn=lambda *a: {}, usage_fn=no_key, reveal_delay=0)
    old, app.state.live = app.state.live, m
    try:
        if storemod.get_store().masked_image(FORM) is None:
            pytest.skip("no masked page")
        r = client.post(f"/api/live/{FORM}")
    finally:
        app.state.live = old
    assert r.status_code == 503 and r.json()["refused"] == "off" and "no AMD key" in r.json()["message"]
