"""Audit cases in Evolus (evolus/audit.py), Evolus mocked: the workflow input of one disputed field, the no-AI
evidence script against our own scoring, idempotent setup of 'Audit finding', the paced runner (at most 18, only
the strong tier, shared limiter), the auditor's status written back, no party names and no secrets anywhere."""
import json
import re
import shutil
import subprocess

import httpx
import pytest
from fastapi.testclient import TestClient

from app import capture_audit as ca
from app.main import app
from evolus import audit as auditmod
from evolus import case as casemod
from evolus import config as configmod
from evolus import setup as setupmod
from evolus.client import EvolusClient
from evolus.config import Settings
from tests.test_app_neutral import _clean
from tests.test_evolus_setup import SECRET as WS_SECRET, Workspace

SECRET = "evk_TESTSECRET_audit_0123456789"
CB = "cb_TESTSECRET_audit_987654321"
USER = "usr_TESTSECRET_audit_555555555"
web = TestClient(app)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(ca, "AUDITS", tmp_path / "audits")
    monkeypatch.setattr(configmod, "IDS_FILE", tmp_path / "ids.json")
    monkeypatch.setattr(casemod, "CALLBACKS", tmp_path / "callbacks.jsonl")
    for n in configmod.SECRET_NAMES:
        monkeypatch.delenv(n, raising=False)
    return tmp_path


@pytest.fixture(scope="module")
def sample():
    import tempfile
    from pathlib import Path
    d = Path(tempfile.mkdtemp())
    old = ca.AUDITS
    ca.AUDITS = d / "audits"
    try:
        a = ca.sample()
        R = ca.run(a)
        shutil.copytree(ca.AUDITS, d / "keep")
    finally:
        ca.AUDITS = old
    return a, R, d / "keep"


@pytest.fixture
def audit(sample, isolated):
    a, R, keep = sample
    shutil.copytree(keep, ca.AUDITS)
    return a, R


def settings(**kw):
    return Settings(**(dict(key=SECRET, app_id="app-1", audit_workflow_id="wf-audit", agent="app-1:clerk") | kw))


class FakeLimiter:
    def __init__(self):
        self.n = 0

    def acquire(self):
        self.n += 1
        return 0.0


def multipart(req: httpx.Request) -> dict:
    ct = req.headers["content-type"]
    b = re.search(r"boundary=([^;]+)", ct).group(1).strip('"').encode()
    out = {}
    for part in req.content.split(b"--" + b)[1:-1]:
        head, _, body = part.partition(b"\r\n\r\n")
        name = re.search(rb'name="([^"]+)"', head).group(1).decode()
        out[name] = body[:-2].decode("utf-8")
    return out


class Evolus:
    """Mock of the execute / status / workflow-audit endpoints. Each run completes on the second poll with the
    output the real Script step would give (the evidence object comes from our input)."""

    def __init__(self, finding="The paper shows 120 in digits and words. The keyed value is 102. The rows sum to "
                              "TOTAL supports the paper's value, for the auditor to confirm.", audits=True):
        self.finding, self.audits = finding, audits
        self.inputs, self.params, self.runs, self.puts, self.uploads = [], [], {}, [], []
        self.in_flight = self.max_in_flight = 0
        self.reqs = []

    def __call__(self, req: httpx.Request):
        self.reqs.append(req)
        p, m = req.url.path, req.method
        assert req.headers.get("x-apikey") == SECRET
        if p.endswith("/execute"):
            f = multipart(req)
            inp, prm = json.loads(f["input"]), json.loads(f["parameters"])
            self.inputs.append(inp)
            self.params.append(prm)
            eid = f"exec-{len(self.runs) + 1}"
            self.runs[eid] = {"polls": 0, "inp": inp}
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            return httpx.Response(202, json={"executionId": eid})
        if "/executions/" in p:
            r = self.runs[p.rsplit("/", 1)[-1]]
            r["polls"] += 1
            if r["polls"] < 2:
                return httpx.Response(200, json={"status": "Running"})
            self.in_flight -= 1
            inp = r["inp"]
            out = {"kind": "audit case", "case_id": inp["case_id"], "finding": self.finding, "status": "open",
                   "evidence": {"score": inp["app_score"], "tier": inp["evidence_tier"], "agrees_with_app": True}}
            return httpx.Response(200, json={"status": "Completed", "output": json.dumps(out),
                                             "stepStates": {"s1": {"status": "Completed", "durationMs": 21000}}})
        if p == "/api/v1/workflows/wf-audit" and m == "GET":
            return httpx.Response(200, json={"steps": [{"id": "s1", "name": "Draft the finding (Intake clerk)"}]})
        if p == "/api/v1/workflow-audits" and m == "GET":
            return httpx.Response(200, json=[{"id": "aud-1", "workflowExecutionId": "exec-1"}] if self.audits else [])
        if p.startswith("/api/v1/workflow-audits/") and m == "PUT":
            self.puts.append((p, json.loads(req.content)))
            return httpx.Response(200, json={})
        if p.endswith("/documents"):
            self.uploads.append(p)
            return httpx.Response(200, json={"id": "doc-1"})
        return httpx.Response(404, json={"error": f"unexpected {m} {p}"})


def client(fake, **kw):
    return EvolusClient(settings(**kw), transport=httpx.MockTransport(fake), pace_s=0)


# ------------------------------------------------------------------ the input of one case
def test_case_input_carries_the_dispute_in_neutral_names(audit):
    a, R = audit
    strong = [d for d in R["disputes"] if d["tier"] == "strong"]
    assert len(strong) == 18
    for d in strong:
        inp = auditmod.case_input(a, d)
        assert inp["form"] == d["form"] and inp["field"] == d["name"] and inp["evidence_tier"] == "strong"
        assert re.fullmatch(r"Option \d\d", inp["field"]) or not inp["field"].startswith("OPT")
        assert inp["model_digits"] == d["model"] and inp["model_words"] == d["words"] and inp["keyed"] == d["keyed"]
        assert inp["crop_url"] == d["img"] and inp["supports"], "a strong field has an identity on the paper's side"
        assert set(inp["breaks"]) <= set(inp["supports"])
        _clean(json.dumps(inp, ensure_ascii=False), d["key"])
        assert set(auditmod.parameters(inp)) == {"form", "case_id", "field", "crop_url", "tier"}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_evolus_script_recomputes_our_score_for_every_dispute(audit, tmp_path):
    """The Script step is the evidence rule: run it (as Evolus would, data = the input) on every dispute."""
    a, R = audit
    inputs = [auditmod.case_input(a, d) for d in R["disputes"]]
    (tmp_path / "in.json").write_text(json.dumps(inputs), encoding="utf-8")
    js = ("const all = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));\n"
          "const f = new Function('data', 'params', 'sources', 'input', " + json.dumps(auditmod.evidence_js()) + ");\n"
          "console.log(JSON.stringify(all.map(d => f(d, {}, [], JSON.stringify(d)))));")
    (tmp_path / "run.js").write_text(js, encoding="utf-8")
    out = json.loads(subprocess.run(["node", str(tmp_path / "run.js"), str(tmp_path / "in.json")], capture_output=True,
                                    text=True, check=True).stdout)
    assert len(out) == len(R["disputes"]) > 200
    for d, o in zip(R["disputes"], out):
        assert (o["score"], o["tier"], o["agrees_with_app"]) == (d["score"], d["tier"], True), d["key"]


# ------------------------------------------------------------------ setup: idempotent
def ws_client(ws, **kw):
    return EvolusClient(Settings(key=WS_SECRET, app_id="app-1", **kw), transport=httpx.MockTransport(ws), pace_s=0)


def test_setup_builds_the_audit_workflow_once():
    ws = Workspace()
    ids = setupmod.Setup(ws_client(ws), log=lambda s: None).run()
    w = next(x for x in ws.workflows if x["name"] == "Audit finding")
    assert ids["audit_workflow_id"] == w["id"] and w["isActive"]
    assert [s["stepType"] for s in w["steps"]] == [1, 19, 19, 14]   # AgentCall, Script, Script, Output
    assert w["steps"][0]["agentId"] == ids["agent_id"] and "for the auditor to confirm" in w["steps"][0]["prompt"]
    assert "agrees_with_app" in json.loads(w["steps"][1]["stepConfigJson"])["script"]
    declared = {p["name"] for p in w["parameters"]}
    used = set(re.findall(r"params\.(\w+)", auditmod.ASSEMBLE_JS))
    assert used <= declared
    n = (len(ws.workflows), sum(len(x["steps"]) for x in ws.workflows))
    setupmod.Setup(ws_client(ws), log=lambda s: None).run()
    assert (len(ws.workflows), sum(len(x["steps"]) for x in ws.workflows)) == n


def test_with_a_public_url_the_hand_off_is_a_webhook_step():
    ws = Workspace()
    setupmod.Setup(ws_client(ws), log=lambda s: None).run()
    ws2 = ws_client(ws, public_url="https://twohands.example", callback_key=CB)
    setupmod.Setup(ws2, log=lambda s: None).run()            # shape changed: rebuilt, not duplicated
    w = [x for x in ws.workflows if x["name"] == "Audit finding"]
    assert len(w) == 1 and [s["stepType"] for s in w[0]["steps"]] == [1, 19, 19, 2, 14]
    hook = json.loads(w[0]["steps"][3]["stepConfigJson"])
    assert hook["url"] == "https://twohands.example/api/evolus/callback" and CB not in json.dumps(w[0])


def test_user_key_blocks_activate_by_themselves(isolated):
    ws = Workspace()
    from tests.test_evolus_setup import USER
    c = EvolusClient(Settings(key=WS_SECRET, app_id="app-1"), transport=httpx.MockTransport(ws), pace_s=0)
    assert setupmod.ensure_user_blocks(c) is False and not ws.log          # no key: nothing happens
    c.s.user_key = USER
    assert setupmod.ensure_user_blocks(c) is True
    assert c.s.extractor_id and c.s.library_id and c.s.audit_workflow_id


# ------------------------------------------------------------------ the runner
def test_runner_sends_only_the_strong_tier_paced_and_records_without_secrets(audit, tmp_path):
    a, R = audit
    fake, lim = Evolus(), FakeLimiter()
    out = tmp_path / "evolus_audit_runs.jsonl"
    r = auditmod.AuditRunner(client(fake, callback_key=CB), a, limiter=lim, sleep=lambda s: None, results=out)
    done = r.run(R["disputes"])
    assert len(done) == len(fake.inputs) == 18 == r.amd_calls == lim.n
    assert fake.max_in_flight <= auditmod.IN_FLIGHT
    assert {i["evidence_tier"] for i in fake.inputs} == {"strong"}
    for i in fake.inputs:
        _clean(json.dumps(i, ensure_ascii=False), i["case_id"])
    assert all(c["finding"].endswith("for the auditor to confirm.") and c["case_status"] == "open" for c in done)
    text = out.read_text(encoding="utf-8") + auditmod.cases_file(a["id"]).read_text(encoding="utf-8")
    assert SECRET not in text and CB not in text
    _clean(text, "records")
    assert len(out.read_text(encoding="utf-8").splitlines()) == 18
    # a second call sends nothing again
    assert auditmod.AuditRunner(client(Evolus()), a, limiter=lim, sleep=lambda s: None).run(R["disputes"]) == []
    assert lim.n == 18


def test_runner_caps_the_number_of_amd_calls(audit):
    a, R = audit
    fake, lim = Evolus(), FakeLimiter()
    auditmod.AuditRunner(client(fake), a, limiter=lim, max_cases=5, sleep=lambda s: None).run(R["disputes"])
    assert len(fake.inputs) == lim.n == 5


def test_an_evolus_error_is_recorded_redacted(audit):
    a, R = audit

    def boom(req):
        return httpx.Response(402, text=f"credits gone for {SECRET}")
    done = auditmod.AuditRunner(client(boom), a, limiter=FakeLimiter(), max_cases=2, sleep=lambda s: None).run(R["disputes"])
    assert all(c["run_status"] == "error" and SECRET not in c["error"] and "402" in c["error"] for c in done)


# ------------------------------------------------------------------ the auditor's status
def test_confirm_writes_the_status_back(audit):
    a, R = audit
    fake = Evolus()
    done = auditmod.AuditRunner(client(fake), a, limiter=FakeLimiter(), max_cases=1, sleep=lambda s: None).run(R["disputes"])
    key = done[0]["key"]
    c = auditmod.set_status(client(fake, library_id="lib-1"), a["id"], key, "confirmed")
    assert c["case_status"] == "confirmed" and c["writeback"]["workflow_audit"] == "written"
    assert fake.puts[0][1]["clientData"]["status"] == "confirmed" and fake.uploads
    c = auditmod.set_status(client(Evolus(audits=False)), a["id"], key, "not_error")   # the audit id is kept
    assert c["case_status"] == "not an error" and c["writeback"]["workflow_audit"] == "written"
    other = auditmod.AuditRunner(client(Evolus(audits=False)), a, limiter=FakeLimiter(), max_cases=1,
                                 sleep=lambda s: None).run(R["disputes"])[0]["key"]
    c = auditmod.set_status(client(Evolus(audits=False)), a["id"], other, "confirmed")
    assert c["case_status"] == "confirmed" and c["writeback"]["workflow_audit"].startswith("no workflow audit")


def test_callback_hand_off_fills_the_case(audit):
    a, R = audit
    d = next(x for x in R["disputes"] if x["tier"] == "strong")
    auditmod.save_case(a["id"], d["key"], {"key": d["key"], "execution_id": "exec-9", "run_status": "Running"})
    body = {"kind": "audit case", "finding": "Paper 5, keyed 3, for the auditor to confirm.", "evidence": {"score": 9}}
    casemod.CALLBACKS.write_text(json.dumps({"executionId": "exec-9", "auditId": "aud-9", "body": json.dumps(body)}) + "\n",
                                 encoding="utf-8")
    c = auditmod.load_cases(a["id"])[d["key"]]
    assert c["finding"].startswith("Paper 5") and c["workflow_audit_id"] == "aud-9" and c["handoff"] == "callback"


# ------------------------------------------------------------------ the report page
def test_report_button_and_cases_on_the_page(audit, monkeypatch):
    a, R = audit
    html = web.get(f"/audit/{a['id']}/report").text
    assert "Open as Evolus cases" in html
    monkeypatch.setattr(configmod.Settings, "load", classmethod(lambda cls: settings()))
    sent = []
    monkeypatch.setattr(auditmod, "start_background", lambda c, au, disputes: sent.append(disputes) or 18)
    j = web.post(f"/api/audit/{a['id']}/evolus").json()
    assert j == {"started": 18, "strong": 18, "max": 18} and len(sent) == 1
    monkeypatch.setattr(configmod.Settings, "load", classmethod(lambda cls: settings(audit_workflow_id="")))
    assert web.post(f"/api/audit/{a['id']}/evolus").status_code == 503


def test_report_shows_the_finding_and_mark_sets_the_case_status(audit, monkeypatch):
    a, R = audit
    auditmod.AuditRunner(client(Evolus()), a, limiter=FakeLimiter(), max_cases=2, sleep=lambda s: None).run(R["disputes"])
    pushed = []
    monkeypatch.setattr(auditmod, "set_status", lambda *x: pushed.append(x))
    html = web.get(f"/audit/{a['id']}/report").text
    assert html.count("for the auditor to confirm") >= 2 and "exec-1"[:8] in html
    key = next(iter(auditmod.load_cases(a["id"])))
    j = web.post(f"/api/audit/{a['id']}/mark", json={"key": key, "mark": "not_error"}).json()
    assert j["case_status"] == "not an error"
    cases = web.get(f"/api/audit/{a['id']}/evolus").json()["cases"]
    assert cases[key]["case_status"] == "not an error"
    _clean(json.dumps(cases, ensure_ascii=False), "cases api")


def test_a_hanging_run_times_out_and_a_later_call_collects_it_without_resending(audit):
    a, R = audit

    class Slow(Evolus):
        def __call__(self, req):
            if "/executions/" in req.url.path:
                return httpx.Response(200, json={"status": "Running"})
            return super().__call__(req)
    slow, lim = Slow(), FakeLimiter()
    done = auditmod.AuditRunner(client(slow), a, limiter=lim, max_cases=3, poll_every=60, poll_s=360,
                                sleep=lambda s: None).run(R["disputes"])
    assert [c["run_status"] for c in done] == ["timeout"] * 3 and lim.n == 3
    fast = Evolus()
    fast.runs = {c["execution_id"]: {"polls": 5, "inp": slow.runs[c["execution_id"]]["inp"]} for c in done}
    again = auditmod.AuditRunner(client(fast), a, limiter=lim, max_cases=0, sleep=lambda s: None).run(R["disputes"])
    assert {c["run_status"] for c in again} == {"Completed"} and len(again) == 3
    assert fast.inputs == [] and lim.n == 3          # collected, not re-sent: no new AMD call


def test_saved_runs_newest_first_with_model(tmp_path):
    from evolus import audit as auditmod
    p = tmp_path / "runs.jsonl"
    rows = [{"case_id": "a-1", "returned_at": "2026-10-15T16:00:00+00:00", "finding": "old"},
            {"case_id": "b-1", "returned_at": "2026-10-16T19:32:00+00:00", "finding": "new", "model": "Gemma-4-31B-IT"},
            {"case_id": "a-1", "returned_at": "2026-10-15T16:01:00+00:00", "finding": "old, last row"}]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n", encoding="utf-8")
    got = auditmod.saved_runs(p)
    assert [r["case_id"] for r in got] == ["b-1", "a-1"]
    assert got[0]["model"] == "Gemma-4-31B-IT" and got[1]["finding"] == "old, last row"
