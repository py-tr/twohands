"""Live model choice from the AMD model list (mocked): Gemma listed -> Gemma; Gemma gone -> Qwen + banner; a 400
"not supported" is "withdrawn", not "down". No request reaches the real endpoint."""
import time

import pytest

from app import health
from app import live as livemod
from app import livemodel
from app import store as storemod
from tests.test_app_live import FORM, _events, _parsed_from_spike, client, drain  # noqa: F401
from app.main import app

GEMMA, QWEN = "Gemma-4-31B-IT", "Qwen3.8-27B"
ERR_400 = ('GaveUp: HTTP 400: {"error":{"message":"Requested model Gemma-4-31B-IT not supported",'
           '"type":"invalid_request_error","param":null,"code":null}}')


def chooser(listed, rec=None):
    box = {"ids": listed, "n": 0}

    def fetch():
        box["n"] += 1
        if isinstance(box["ids"], Exception):
            raise box["ids"]
        return box["ids"]
    c = livemodel.Chooser(fetch=fetch, record=lambda *a, **k: rec.append(a) if rec is not None else None)
    c.box = box
    return c


def test_gemma_listed_uses_gemma_no_banner():
    p = chooser([GEMMA, QWEN]).choose()
    assert p["key"] == "gemma" and p["model"] == GEMMA and not p["fallback"] and p["banner"] is None


def test_gemma_missing_uses_qwen_with_banner_and_records_withdrawn():
    rec = []
    p = chooser(["DeepSeek-V4-Flash", QWEN], rec).choose()
    assert p["key"] == "qwen" and p["model"] == QWEN and p["fallback"]
    assert p["banner"] == ("Gemma-4-31B-IT is currently not offered by the AMD endpoint (since 2026-10-15 16:20 UTC). "
                           "This live read uses Qwen3.8-27B on AMD; the stored results above were read by Gemma on AMD.")
    assert rec and rec[-1][0] == GEMMA and rec[-1][1] == "withdrawn"


def test_list_cached_5_min_and_switches_back_when_gemma_returns():
    t = [1000.0]
    c = chooser([QWEN])
    c.clock = lambda: t[0]
    assert c.choose()["key"] == "qwen"
    c.box["ids"] = [GEMMA, QWEN]
    t[0] += 299
    assert c.choose()["key"] == "qwen" and c.box["n"] == 1  # cached
    t[0] += 2
    assert c.choose()["key"] == "gemma" and c.box["n"] == 2  # refreshed: Gemma is back


def test_list_unavailable_keeps_configured_model():
    c = chooser(RuntimeError("down"))
    assert c.choose()["key"] == livemodel.CONFIGURED and c.choose()["banner"] is None


def test_400_not_supported_parsing():
    assert livemodel.is_withdrawn_error(ERR_400)
    assert not livemodel.is_withdrawn_error("GaveUp: HTTP 503: provider 503")
    assert not livemodel.is_withdrawn_error("GaveUp: HTTP 400: max_tokens too large")
    assert not livemodel.is_withdrawn_error(None)


def _row(model, kind, status, mins_ago, now, lat=1.0):
    return {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 60 * mins_ago)), "model": model,
            "kind": kind, "status": status, "latency_s": lat}


def test_health_reads_400_as_withdrawn_not_down():
    now = time.time()
    # the probe alternates: Gemma 400, Qwen 200 -> endpoint up, Gemma withdrawn (amber), never "down" / "slow"
    rows = [_row(GEMMA, "probe", 400, 9, now), _row(QWEN, "probe", 200, 9, now),
            _row(GEMMA, "probe", 400, 4, now), _row(QWEN, "probe", 200, 4, now), _row(GEMMA, "probe", 400, 1, now)]
    v = health.classify(rows, now)
    assert v["state"] == "degraded" and v["label"] == "AMD live · Gemma unavailable"
    # the model list alone decides when known
    v = health.classify([_row(QWEN, "probe", 200, 2, now)], now, gemma_listed=False)
    assert v["state"] == "degraded" and v["label"] == "AMD live · Gemma unavailable"
    # Gemma back (listed, latest probe 200): green again
    v = health.classify(rows + [_row(GEMMA, "probe", 200, 0, now)], now, gemma_listed=True)
    assert v["state"] == "up" and v["label"] == "AMD live"
    # a "withdrawn" row written by app/livemodel.py counts the same way
    v = health.classify([_row(QWEN, "probe", 200, 2, now), _row(GEMMA, "models", "withdrawn", 1, now)], now)
    assert v["state"] == "degraded"
    # a real outage is still "down"
    v = health.classify([_row(QWEN, "probe", 503, 8, now), _row(QWEN, "probe", "TimeoutError", 2, now)], now,
                        gemma_listed=False)
    assert v["state"] == "down"


@pytest.fixture
def mgr_with(tmp_path, monkeypatch):
    monkeypatch.setattr(livemod, "LIVE_DIR", tmp_path / "live")
    monkeypatch.setattr(livemod, "BUDGET_FILE", tmp_path / "budget.json")
    made = []

    def make(listed, reader):
        calls = []

        def rd(model, page):
            calls.append(model)
            return reader(model, page)
        m = livemod.LiveManager(reader_fn=rd, usage_fn=lambda: {"daily_cost_remaining_usd": 0.9}, reveal_delay=0,
                                chooser=chooser(listed))
        m.calls = calls
        made.append((m, app.state.live))
        app.state.live = m
        return m
    yield make
    for m, old in reversed(made):
        drain(m)
        app.state.live = old


def _ok(model, page):
    return {"parsed": _parsed_from_spike(FORM), "secs": 1.0, "finish_reason": "stop",
            "usage": {"cost": 0.0008, "prompt_tokens": 6600, "completion_tokens": 4000}}


def _need_page():
    if storemod.get_store().masked_image(FORM) is None:
        pytest.skip("no masked page")


def test_live_read_gemma_listed_reads_with_gemma(mgr_with):
    _need_page()
    m = mgr_with([GEMMA, QWEN], _ok)
    evs = _events(client.post(f"/api/live/{FORM}").json()["job"])
    assert m.calls == ["gemma"]
    assert not any(e["type"] == "notice" for e in evs)
    v = next(e for e in evs if e["type"] == "verdict")
    assert v["model"] == GEMMA and v["fallback"] is False


def test_live_read_gemma_missing_reads_with_qwen_and_banner(mgr_with):
    _need_page()
    m = mgr_with([QWEN], _ok)
    m.chooser.refresh()  # pages never wait on AMD: the list is fetched in the background on a cold cache
    page = client.get(f"/form/{FORM}").text
    assert "Gemma-4-31B-IT is currently not offered by the AMD endpoint" in page
    evs = _events(client.post(f"/api/live/{FORM}").json()["job"])
    assert m.calls == ["qwen"]
    n = next(e for e in evs if e["type"] == "notice")
    assert n["code"] == "model_withdrawn" and "This live read uses Qwen3.8-27B on AMD" in n["msg"]
    v = next(e for e in evs if e["type"] == "verdict")
    assert v["model"] == QWEN and v["fallback"] is True


def test_live_read_gemma_400_mid_job_switches_to_qwen(mgr_with):
    _need_page()

    def rd(model, page):
        if model == "gemma":
            return {"error": ERR_400, "parsed": None, "usage": {}, "secs": 0.9}
        return _ok(model, page)
    m = mgr_with([GEMMA, QWEN], rd)
    evs = _events(client.post(f"/api/live/{FORM}").json()["job"])
    assert m.calls == ["gemma", "qwen"]
    assert any(e["type"] == "notice" for e in evs)
    assert next(e for e in evs if e["type"] == "verdict")["model"] == QWEN
    assert m.chooser.choose()["key"] == "qwen"  # the next job goes straight to Qwen


def test_header_chip_amber_when_gemma_missing(monkeypatch):
    c = livemodel.chooser
    monkeypatch.setattr(c, "_listed", [QWEN])
    monkeypatch.setattr(c, "_at", time.time())
    now = time.time()
    monkeypatch.setattr(health, "_tail", lambda: [_row(QWEN, "probe", 200, 2, now), _row(GEMMA, "probe", 400, 1, now),
                                                  _row(QWEN, "live", 200, 0, now, lat=95.0)])
    health._cache.update(at=0.0, v=None, key=None)
    html = client.get("/").text
    assert "AMD live · Gemma unavailable" in html and 'amdpill degraded' in html
