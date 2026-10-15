"""Evolus integration: case orchestration (Evolus mocked), gate endpoint auth, no secret in logs or records."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import store as storemod
from app.main import app
from evolus import case as casemod
from evolus import web as evolusweb
from evolus.client import EvolusClient
from evolus.config import Settings, redact

SECRET = "evk_TESTSECRET_0123456789abcdef"
GATE = "gate_TOKEN_abcdef123456"
CB = "cb_KEY_987654321zyx"


def settings(**kw):
    base = dict(key=SECRET, app_id="app-1", extractor_agent_id="ag-1", extractor_id="ex-1", library_id="lib-1",
                workflow_id="wf-1", filing_workflow_id="wf-file", agent="app-1:agent-7",
                public_url="https://twohands.example", gate_token=GATE, callback_key=CB)
    return Settings(**(base | kw))


def forms():
    st = storemod.get_store()
    acc = rout = None
    for k in st.ine_claves():
        r = st.default_read(k)
        if r is None or st.masked_image(k) is None or r.not_located:
            continue
        ev = storemod.evaluate(r)
        if ev["accepted"] and acc is None:
            acc = (k, r)
        if not ev["accepted"] and ev["failing"] and rout is None:
            rout = (k, r)
    if not acc or not rout:
        pytest.skip("needs one accepted and one routed form with a masked page")
    return acc, rout


def codes_of(r):
    return {storemod.code_of(k): v for k, v in r.values.items()}


class Fake:
    """Evolus mock: records every request; the extractor returns `extract`."""

    def __init__(self, extract, echo_secret=False, wf_status="Completed"):
        self.extract, self.echo, self.wf_status = extract, echo_secret, wf_status
        self.reqs = []
        self.filing_input = None

    def __call__(self, req: httpx.Request):
        self.reqs.append(req)
        p = req.url.path
        if p.endswith("/ask-file"):
            assert req.headers["x-apikey"] == SECRET and req.headers["x-application-id"] == "app-1"
            assert req.url.params.get("useWebhook") == "false"
            return httpx.Response(200, json={"result": json.dumps(self.extract)},
                                  headers={"X-AskFile-Audit-Id": "aud-1"})
        if p == "/v1/chat/completions":
            assert req.headers["authorization"] == "Bearer " + SECRET
            body = json.loads(req.content)
            assert body["model"] == "app-1:agent-7"
            return httpx.Response(200, json={"choices": [{"message": {"content": "Check the TOTAL box against the rows."}}]})
        if p == "/api/v1/ai-tools/translate/run":
            body = json.loads(req.content)
            assert body["options"] == {"target": "Spanish"}
            return httpx.Response(200, json={"tool": "translate", "output": "Revise la casilla TOTAL contra las filas."})
        if p.endswith("/execute"):
            assert req.headers["content-type"].startswith("multipart/form-data")
            assert b'name="input"' in req.content
            if self.echo:
                return httpx.Response(500, text=f"bad key {SECRET}")
            eid = "exe-file" if "/wf-file/" in p else "exe-42"
            if eid == "exe-file":
                self.filing_input = req.content
            return httpx.Response(202, headers={"X-Workflow-Execution-Id": eid})
        if p.endswith("/executions/exe-42"):
            out = {"note_en": "Check the TOTAL box against the rows.", "note_es": "Revise la casilla TOTAL contra las filas.",
                   "status": "awaiting review"}
            return httpx.Response(200, json={"status": self.wf_status, "output": json.dumps(out),
                                              "stepStates": {"1": {"status": "done", "durationMs": 900},
                                                             "2": {"status": "done", "durationMs": 80}}})
        if p.endswith("/executions/exe-file"):
            out = {"status": "filed", "identities": [{"name": "rows sum to TOTAL", "ok": True}]}
            return httpx.Response(200, json={"status": "Completed", "output": json.dumps(out), "stepStates": {}})
        if p in ("/api/v1/workflows/wf-1", "/api/v1/workflows/wf-file"):
            return httpx.Response(200, json={"id": p.rsplit("/", 1)[-1], "steps": [
                {"id": "s1", "order": 1, "name": "Draft the review task (Intake clerk)"},
                {"id": "s2", "order": 2, "name": "Translate the task to Spanish"}]})
        if "/memories/" in p and req.method == "POST":
            assert b"record_" in req.content
            return httpx.Response(201, json={"id": "doc-9"})
        return httpx.Response(404, json={"error": "unexpected " + p})


def run_case(clave, fake, **kw):
    c = EvolusClient(settings(**kw), transport=httpx.MockTransport(fake), pace_s=0)
    return casemod.Case(clave, c, poll_s=12, poll_every=6, sleep=lambda s: None).run(), c


def test_routed_form_hands_off_through_workflow():
    _, (k, r) = forms()
    fake = Fake(codes_of(r))
    rec, c = run_case(k, fake)
    assert rec["decision"] == "routed"
    blocks = [s["block"] for s in rec["steps"]]
    assert "document extractor" in blocks and "workflow: review hand-off" in blocks
    assert "workflow step: Draft the review task (Intake clerk)" in blocks
    # the workflow drafts and translates: the app makes no chat or translate call of its own
    assert not any(q.url.path in ("/v1/chat/completions", "/api/v1/ai-tools/translate/run") for q in fake.reqs)
    assert rec["workflow"]["execution_id"] == "exe-42" and rec["workflow"]["status"] == "Completed"
    assert rec["handoff"]["note_es"].startswith("Revise") and rec["handoff"]["note_en"].startswith("Check")
    assert "workflow 'Review hand-off'" in rec["handoff"]["drafted_by"]
    assert rec["handoff"]["crop_urls"][0].startswith("https://twohands.example/crop/" + k + "/")
    assert rec["extractor"]["status"] == "ok" and rec["extractor"]["disagree"] == []
    assert rec["amd_calls_via_evolus"] == 1
    assert all(s["status"] in ("ok", "skipped") for s in rec["steps"])
    ex = next(q for q in fake.reqs if q.url.path.endswith("/execute"))
    assert b'name="parameters"' in ex.content and k.encode() in ex.content


def test_routed_form_without_workflow_uses_agent_chat_and_ai_tool():
    _, (k, r) = forms()
    rec, c = run_case(k, Fake(codes_of(r)), workflow_id="")
    blocks = {s["block"]: s["status"] for s in rec["steps"]}
    assert blocks["agent chat (Intake clerk)"] == "ok" and blocks["AI Tool: translate"] == "ok"
    assert blocks["workflow: review hand-off"] == "skipped"
    assert rec["handoff"]["note_es"].startswith("Revise")


def test_accepted_form_is_rechecked_and_filed():
    (k, r), _ = forms()
    fake = Fake(codes_of(r))
    rec, c = run_case(k, fake)
    assert rec["decision"] == "accepted"
    assert rec["filing"]["execution_id"] == "exe-file" and rec["filing"]["filed"] and rec["filing"]["identities_ok"]
    sent = fake.filing_input.decode("utf-8")
    assert '"TOTAL"' in sent and k in sent  # the record goes to Evolus by neutral codes
    assert rec["library"]["status"] == "ok" and rec["library"]["document"] == f"record_{k}.txt"
    assert "handoff" not in rec and rec["amd_calls_via_evolus"] == 0


def test_extractor_never_trusted_blindly():
    (k, r), _ = forms()
    vals = codes_of(r)
    # a different reading that breaks the paper's arithmetic is overruled
    wrong = dict(vals, TOTAL=(vals["TOTAL"] or 0) + 7)
    rec, _ = run_case(k, Fake(wrong))
    assert rec["decision"] == "accepted" and "overruled" in rec["decision_reason"]
    assert [d["code"] for d in rec["extractor"]["disagree"]] == ["TOTAL"]
    # a different reading that ALSO passes every identity goes to a person
    opt = next(c for c in vals if c.startswith("OPT") and (vals[c] or 0) > 0)
    other = next(c for c in vals if c.startswith("OPT") and c != opt)
    alt = dict(vals, **{opt: vals[opt] - 1, other: (vals[other] or 0) + 1})
    rec, _ = run_case(k, Fake(alt))
    assert rec["decision"] == "routed" and "a person decides" in rec["decision_reason"]


def test_unconfigured_blocks_are_skipped_not_faked():
    _, (k, r) = forms()
    rec, c = run_case(k, Fake(codes_of(r)), extractor_id="", workflow_id="", app_id="")
    st = {s["block"]: s["status"] for s in rec["steps"]}
    assert st["document extractor"] == "skipped" and st["workflow: review hand-off"] == "skipped"
    assert st["AI Tool: translate"] == "skipped"
    assert rec["workflow"] == {"status": "skipped"}
    (k2, r2), _ = forms()
    rec, _ = run_case(k2, Fake(codes_of(r2)), library_id="", filing_workflow_id="")
    st = {s["block"]: s["status"] for s in rec["steps"]}
    assert st["knowledge library"] == "skipped" and st["workflow: record filing"] == "skipped"


def test_no_secret_in_records_or_logs(tmp_path, capsys):
    _, (k, r) = forms()
    rec, c = run_case(k, Fake(codes_of(r), echo_secret=True))
    out = tmp_path / "evolus_runs.jsonl"
    casemod.save(rec, out)
    text = out.read_text(encoding="utf-8") + json.dumps(c.calls) + capsys.readouterr().out
    assert SECRET not in text and GATE not in text and CB not in text
    assert "***" in text  # the echoed key was redacted, not dropped silently
    assert any(s["status"] == "error" for s in rec["steps"])
    # a record is never mistaken for a read by the store (no read keys at the top level)
    assert not any(x in rec for x in storemod.READ_KEYS)
    # the real .env values are redacted too
    for s in Settings.load().secrets():
        assert s not in text
    assert redact(f"x {SECRET} y", [SECRET]) == "x *** y"


def test_saved_evidence_has_no_secret():
    p = casemod.RUNS_FILE
    if not p.is_file():
        pytest.skip("no evidence file yet")
    text = p.read_text(encoding="utf-8")
    for s in Settings.load().secrets():
        assert s not in text
    for line in text.splitlines():
        row = json.loads(line)
        assert not any(x in row for x in storemod.READ_KEYS)


def test_execute_is_multipart_and_carries_callback():
    _, (k, r) = forms()
    fake = Fake(codes_of(r))
    run_case(k, fake)
    ex = next(q for q in fake.reqs if q.url.path.endswith("/execute"))
    assert b'name="callbackUrl"' in ex.content and b"https://twohands.example/api/evolus/callback" in ex.content
    assert b'name="callbackApiKeyName"' in ex.content


# ------------------------------------------------------------------------------------------- gate endpoint
client = TestClient(app)


def test_gate_endpoint_auth(monkeypatch):
    (k, r), _ = forms()
    body = {"values": codes_of(r)}
    monkeypatch.setattr(evolusweb.Settings, "load", classmethod(lambda cls: settings(gate_token="")))
    assert client.post("/api/gate", json=body).status_code == 503
    monkeypatch.setattr(evolusweb.Settings, "load", classmethod(lambda cls: settings()))
    assert client.post("/api/gate", json=body).status_code == 401
    assert client.post("/api/gate", json=body, headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.post("/api/gate", json=body, headers={"Authorization": "Bearer " + GATE})
    assert ok.status_code == 200
    v = ok.json()
    assert v["accepted"] is True and all(i["ok"] for i in v["identities"])
    bad = dict(codes_of(r), TOTAL=(codes_of(r)["TOTAL"] or 0) + 1)
    v = client.post("/api/gate", json={"values": bad}, headers={"X-Api-Key": GATE}).json()
    assert v["accepted"] is False and any(i["ok"] is False for i in v["identities"])
    assert GATE not in json.dumps(v)


def test_callback_requires_key(monkeypatch, tmp_path):
    monkeypatch.setattr(evolusweb.Settings, "load", classmethod(lambda cls: settings()))
    monkeypatch.setattr(casemod, "CALLBACKS", tmp_path / "cb.jsonl")
    assert client.post("/api/evolus/callback", json={"executionId": "e", "status": "Completed"}).status_code == 401
    r = client.post("/api/evolus/callback", json={"executionId": "e", "status": "Completed"}, headers={"X-Callback-Key": CB})
    assert r.status_code == 200 and "Completed" in (tmp_path / "cb.jsonl").read_text(encoding="utf-8")


def test_panel_renders_on_form_and_review(monkeypatch):
    _, (k, r) = forms()
    rec, _ = run_case(k, Fake(codes_of(r)))
    monkeypatch.setattr(casemod, "load_cases", lambda: {k: rec})
    html = client.get(f"/form/{k}").text
    assert "Evolus case" in html and "exe-42" in html and "Revise" in html
    assert "Evolus case" in client.get("/review").text
    j = client.get(f"/api/evolus/case/{k}").json()
    assert j["workflow"]["execution_id"] == "exe-42"


def test_extractor_fields_are_neutral():
    f = casemod.extractor_fields()
    assert len(f) == len(storemod.schema()["fields"])
    s = storemod.schema()
    names = {a.lower() for al in s.get("party_aliases", {}).values() for a in al} | {a.lower() for a in s.get("party_aliases", {})}
    blob = json.dumps(f).lower()
    assert not any(f'"{n}"' in blob or f" {n} " in blob for n in names if len(n) > 2)
    assert f[5]["name"] == "OPT01"
