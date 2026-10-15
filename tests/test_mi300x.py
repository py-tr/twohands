"""MI300X session kit: endpoint switch (no core edits), bench against a mocked OpenAI-compatible server, consistency
comparison. No test reaches a real endpoint."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from twohands import REPO, amd, ratelimit, reader

KEY = "test-key-not-real-123"


@pytest.fixture
def isolate(monkeypatch, tmp_path):
    """Every module-level value the switch touches is restored after the test."""
    for k in ("AMD_KEY", "AMD_BASE_URL", "TWOHANDS_BASE_URL", "TWOHANDS_KEY", "TWOHANDS_MODEL_GEMMA",
              "TWOHANDS_MODEL_QWEN", "TWOHANDS_RPM", "TWOHANDS_CONCURRENCY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("TWOHANDS_RATE_FILE", str(tmp_path / "rate.json"))
    monkeypatch.setenv("TWOHANDS_HEALTH_FILE", str(tmp_path / "health.jsonl"))
    monkeypatch.setattr(ratelimit, "RPM", ratelimit.RPM)
    monkeypatch.setattr(ratelimit, "CONCURRENCY", ratelimit.CONCURRENCY)
    monkeypatch.setattr(amd, "HEALTH", amd.HEALTH)
    monkeypatch.setattr(reader, "MODELS", dict(reader.MODELS))
    yield tmp_path
    ratelimit.reset_shared(None)


class Mock:
    """A tiny OpenAI-compatible /chat/completions server. fail_every=n -> every n-th request returns HTTP 500."""

    def __init__(self, fail_every=0):
        self.seen, self.fail_every, self.n, self.lock = [], fail_every, 0, threading.Lock()
        mock = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                with mock.lock:
                    mock.n += 1
                    n = mock.n
                    mock.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
                if mock.fail_every and n % mock.fail_every == 0:
                    self.send_response(500); self.end_headers(); self.wfile.write(b"boom"); return
                out = {"choices": [{"message": {"content": '{"values": []}'}, "finish_reason": "stop"}],
                       "usage": {"prompt_tokens": 2600, "completion_tokens": 640, "total_tokens": 3240}}
                data = json.dumps(out).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}/v1"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


@pytest.fixture
def server():
    m = Mock()
    yield m
    m.close()


# ---------------------------------------------------------------- endpoint switch
def test_switch_noop_without_base_url(isolate):
    from scripts import endpoint_switch
    env = {}
    assert endpoint_switch.apply(env) == {"endpoint": "token-factory", "switched": False}
    assert env == {}
    assert reader.MODELS["gemma"] == "Gemma-4-31B-IT"


def test_switch_requires_key(isolate):
    from scripts import endpoint_switch
    with pytest.raises(RuntimeError):
        endpoint_switch.apply({"TWOHANDS_BASE_URL": "http://127.0.0.1:8000/v1"})


def test_switch_sets_core_config_and_model(isolate, monkeypatch):
    from scripts import endpoint_switch
    monkeypatch.setenv("TWOHANDS_BASE_URL", "http://127.0.0.1:8000/v1/")
    monkeypatch.setenv("TWOHANDS_KEY", KEY)
    monkeypatch.setenv("TWOHANDS_MODEL_GEMMA", "google/gemma-4-31B-it")
    info = endpoint_switch.apply()
    assert KEY not in json.dumps(info)
    assert info["switched"] and info["models"]["gemma"] == "google/gemma-4-31B-it"
    assert reader.MODELS["qwen"] == "Qwen3.8-27B"
    assert amd._cfg() == (KEY, "http://127.0.0.1:8000/v1")  # env wins: ../.env is never consulted
    assert ratelimit.RPM >= 600 and ratelimit.CONCURRENCY >= 8
    assert ratelimit.shared().path.name == "rate.json"  # the test's own file, not cache/ratelimit.json


def test_core_reader_reaches_switched_endpoint(isolate, server, monkeypatch):
    """reader.read -> amd.chat -> the mock: the production body, the key as bearer, the served model id."""
    from scripts import endpoint_switch
    monkeypatch.setenv("TWOHANDS_BASE_URL", server.base)
    monkeypatch.setenv("TWOHANDS_KEY", KEY)
    monkeypatch.setenv("TWOHANDS_MODEL_GEMMA", "google/gemma-4-31B-it")
    endpoint_switch.apply()
    page = sorted((REPO / "data" / "masked" / "spike").glob("*.jpg"))
    if not page:
        pytest.skip("no masked pilot page")
    row = reader.read("gemma", page[0])
    assert row["parsed"] == {"values": []} and row["usage"]["completion_tokens"] == 640
    req = server.seen[0]
    assert req["path"] == "/v1/chat/completions" and req["auth"] == "Bearer " + KEY
    b = req["body"]
    assert b["model"] == "google/gemma-4-31B-it" and b["temperature"] == 0 and b["max_tokens"] == 2000
    imgs = [c for c in b["messages"][1]["content"] if c["type"] == "image_url"]
    assert len(imgs) == 7  # page + 6 tiles -> --limit-mm-per-prompt image >= 7
    assert (isolate / "health.jsonl").is_file()


def test_switch_refuses_the_300_runner(isolate, monkeypatch):
    from scripts import endpoint_switch
    monkeypatch.setenv("TWOHANDS_BASE_URL", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("TWOHANDS_KEY", KEY)
    assert endpoint_switch.main(["-m", "twohands.run"]) == 3


# ---------------------------------------------------------------- bench
def test_bench_sweep_against_mock(isolate, server, monkeypatch, tmp_path):
    from bench import bench_mi300x as B
    if not sorted(B.PAGES.glob("*.jpg")):
        pytest.skip("no masked pilot pages")
    monkeypatch.setenv("TWOHANDS_BASE_URL", server.base)
    monkeypatch.setenv("TWOHANDS_KEY", KEY)
    out = tmp_path / "out"
    assert B.main(["--price-per-hour", "2.0", "--levels", "1,2", "--pages", "2", "--min-requests", "3",
                   "--out-dir", str(out), "--client", "test"]) == 0
    js = list(out.glob("bench_mi300x_*.json"))
    md = list(out.glob("bench_mi300x_*.md"))
    assert len(js) == 1 and len(md) == 1
    res = json.loads(js[0].read_text())
    assert [L["concurrency"] for L in res["levels"]] == [1, 2]
    assert [L["requests"] for L in res["levels"]] == [3, 4]
    assert all(L["errors"] == 0 and L["parsed"] == L["ok"] for L in res["levels"])
    assert res["levels"][0]["mean_prompt_tokens"] == 2600 and res["levels"][0]["decode_tok_s"] > 0
    assert res["meta"]["prompt_sha256"] == reader.prompt_sha256()
    text = md[0].read_text()
    assert "A state count of 20,908 forms in" in text and "Seconds per form, single stream" in text
    assert KEY not in js[0].read_text() + text
    assert len(server.seen) == 1 + 3 + 4  # warm-up + levels


def test_bench_counts_errors_without_retry():
    from bench import bench_mi300x as B
    m = Mock(fail_every=2)
    try:
        smi = B.SmiSampler()
        r = B.run_level(2, [b'{"model": "x"}'], 6, m.base, KEY, 10, smi)
    finally:
        m.close()
    assert r["requests"] == 6 and r["errors"] == 3 and r["error_kinds"] == {"HTTP 500": 3}
    assert r["gpu"] == {}


def test_buyer_units():
    from bench import bench_mi300x as B
    lv = [{"concurrency": 1, "mean_s_per_form": 20.0, "forms_per_min": 3.0, "errors": 0},
          {"concurrency": 8, "mean_s_per_form": 30.0, "forms_per_min": 16.0, "errors": 0},
          {"concurrency": 16, "mean_s_per_form": 40.0, "forms_per_min": 24.0, "errors": 0}]
    b = B.buyer(lv, 2.4, 20908)
    assert b["single_stream_s_per_form"] == 20.0 and b["forms_per_min_at_16"] == 24.0
    assert b["best_concurrency"] == 16
    assert b["usd_per_1000_forms_best"] == pytest.approx(2.4 / (24 * 60) * 1000, abs=1e-3)
    assert b["state_hours"] == pytest.approx(20908 / (24 * 60), abs=0.01)
    assert b["state_usd"] == pytest.approx(b["state_hours"] * 2.4, abs=0.02)


def test_p95_and_smi_parse():
    from bench import bench_mi300x as B
    assert B.p95([1.0] * 19 + [10.0]) == 1.0 and B.p95([1.0] * 18 + [9.0, 10.0]) == 9.0
    smi = json.dumps({"card0": {"GPU use (%)": "97", "GPU Memory Allocated (VRAM%)": "91",
                                "VRAM Total Memory (B)": "205822885888", "VRAM Total Used Memory (B)": "187000000000"}})
    assert B.parse_smi(smi) == {"util_pct": 97.0, "vram_pct": 91.0, "vram_used_gb": 187.0}
    s = B.SmiSampler(local=True, every=0.01, runner=lambda cmd: smi)
    s.start()
    import time
    time.sleep(0.1)
    g = s.stop()
    assert g["samples"] >= 1 and g["util_pct_max"] == 97.0


# ---------------------------------------------------------------- consistency
def test_consistency_reference_reproduces_spike_v2():
    from scripts import consistency_43 as C
    if not (C.SPIKE / "scores_gemma_v2.json").is_file():
        pytest.skip("spike results not present")
    R = C.load_reference()
    assert len(R["claves"]) == 43
    same = [{"clave": k, "parsed_ok": True, "accepted_v1": R["ref"][k]["accepted"], "accepted_v2": False,
             "values": R["ref"][k]["values"], "secs": 5.0} for k in R["claves"]]
    c = C.compare(same, R)
    assert c["accepted_ref"] == 21 and c["field_acc_ref"] == [462, 462]  # the spike README's 21/43, 462/462
    assert c["same_decision_v1_vs_ref"] == 43 and c["digit_agreement_all_fields"] == [946, 946]
    # one form flips to route, one value changes on an accepted form
    k0 = next(k for k in R["claves"] if R["ref"][k]["accepted"])
    same[R["claves"].index(k0)]["values"] = dict(R["ref"][k0]["values"], PAN=-1)
    k1 = next(k for k in R["claves"] if R["ref"][k]["accepted"] and k != k0)
    same[R["claves"].index(k1)]["accepted_v1"] = False
    c = C.compare(same, R)
    assert c["same_decision_v1_vs_ref"] == 42 and c["flips_new_routes"] == [k1]
    assert c["field_acc_new_v1"] == [439, 440] and c["digit_agreement_all_fields"] == [945, 946]
    assert "same decision 42/43" in C.row_text(c, "m")


# ---------------------------------------------------------------- confirmation runner guards
def test_confirm_read_guards(isolate, monkeypatch):
    from scripts import confirm_read
    calls = []
    monkeypatch.setattr(confirm_read.reader, "read", lambda *a, **k: calls.append(a) or {})
    # the whole-state stretch run never goes to the Token Factory
    assert confirm_read.main(["--model", "gemma", "--set", "state06"]) == 3
    # a switched endpoint needs Amendment 4 committed (and Amendment 3) before any confirmation call
    monkeypatch.setattr(confirm_read, "protocol_has", lambda *n: "## Amendment 4" not in n)
    monkeypatch.setenv("TWOHANDS_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("TWOHANDS_KEY", KEY)
    assert confirm_read.main(["--model", "gemma"]) == 3
    assert calls == []
