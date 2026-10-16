"""Evolus in the live worker's critical path (evolus/live.py), Evolus mocked: only strong-evidence disputes start an
'Audit finding' run, capped per day, paced by the shared limiter; the case comes back by polling; the worker calls
the hook after each committed form; the review desk's "Send to Evolus"; the workspace name; no secrets stored."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from evolus import case as casemod
from evolus import config as configmod
from evolus import live
from evolus.config import Settings
from tests.test_worker import Ine, make_worker, three  # noqa: F401 - fixture
from twohands import worker as W

SECRET = "evk_TESTSECRET_live_0123456789"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(configmod, "IDS_FILE", tmp_path / "ids.json")
    monkeypatch.setattr(casemod, "CALLBACKS", tmp_path / "callbacks.jsonl")
    monkeypatch.setattr(casemod, "STATE_RUNS", tmp_path / "state_runs.jsonl")
    monkeypatch.setenv("EVOLUS_QUOTA_FILE", str(tmp_path / "quota.json"))
    monkeypatch.setattr(live, "_WS", {})
    for n in configmod.SECRET_NAMES:
        monkeypatch.delenv(n, raising=False)
    return tmp_path


class FakeEvolus:
    """Stands in for EvolusClient: records each workflow start; every run completes with a drafted finding."""

    def __init__(self, fail=False):
        self.s = Settings(key=SECRET, app_id="app-1", audit_workflow_id="wf-audit", workflow_id="wf-hand")
        self.started, self.fail, self.calls = [], fail, []

    def execute_workflow(self, wid, input_text, parameters=None, callback_url=None, callback_key=None):
        from evolus.client import EvolusError
        if self.fail:
            raise EvolusError(402, "POST /api/v1/workflows/{workflowId}/execute", "credits " + SECRET)
        self.started.append({"wid": wid, "input": json.loads(input_text), "params": parameters})
        return {"executionId": f"ex-{len(self.started)}"}

    def workflow_status(self, wid, eid):
        inp = self.started[int(eid.split("-")[1]) - 1]["input"]
        return {"status": "Completed", "output": json.dumps({
            "finding": f"The paper shows {inp['model_digits']}. The keyed value is {inp['keyed']}. Rows sum to TOTAL "
                       "supports the paper's value, for the auditor to confirm.",
            "evidence": {"score": inp["app_score"], "agrees_with_app": True}, "status": "open"}),
            "stepStates": {}}

    def rest(self, *a, **k):
        return {"steps": [], "application": {"name": "py_tr"}}


class Lim:
    def __init__(self):
        self.n = 0

    def acquire(self):
        self.n += 1
        return 0.0


def worker_rows(three):  # noqa: F811
    P, ep = three["P"], three["ep"]
    w = make_worker(P.root, ep, Ine())
    w.run()
    return {r["clave"]: r for r in W.read_jsonl(P.results)}, three["claves"]


def test_only_strong_disputes_go_to_evolus_and_come_back(three, tmp_path):  # noqa: F811
    rows, (a, b, c) = worker_rows(three)
    fake, lim = FakeEvolus(), Lim()
    h = live.LiveHook(tmp_path / "w", fake, quota=live.Quota(cap=60), limiter=lim, sync=True)
    sent = sum(h.on_result(r) for r in rows.values())
    # form a: a capture error the certified count confirms (strong); form b: model misreads (never sent)
    assert [x["input"]["form"] for x in fake.started] == [a] and sent == 1 and lim.n == 1
    inp = fake.started[0]["input"]
    assert inp["code"] == "OPT01" and inp["evidence_tier"] == "strong" and inp["app_score"] >= 6
    assert fake.started[0]["params"]["case_id"] == f"live-{a}-OPT01"
    case = h.cases()[f"live-{a}-OPT01"]
    assert case["run_status"] == "Completed" and "for the auditor to confirm" in case["finding"]
    assert case["case_status"] == "open" and case["source"] == "live worker"
    assert all(r for r in rows.values())
    # idempotent: the same form again starts nothing
    assert sum(h.on_result(r) for r in rows.values()) == 0 and len(fake.started) == 1
    assert SECRET not in (tmp_path / "w" / "evolus_cases.json").read_text(encoding="utf-8")


def test_weak_label_and_daily_cap(three, tmp_path):  # noqa: F811
    rows, (a, _b, _c) = worker_rows(three)
    r = json.loads(json.dumps(rows[a]))
    assert live.is_strong(r, r["disputes"][0])
    r["disputes"][0]["weak"] = True                      # row-label check failed: weaker evidence, not sent
    assert not live.is_strong(r, r["disputes"][0])
    fake = FakeEvolus()
    h = live.LiveHook(tmp_path / "w", fake, quota=live.Quota(tmp_path / "q.json", cap=0), limiter=Lim(), sync=True)
    h.on_result(rows[a])
    assert fake.started == [] and h.capped == 1         # cap 0: nothing sent, and the AMD token is not taken
    q = live.Quota(tmp_path / "q2.json", cap=2)
    assert [q.take(), q.take(), q.take()] == [True, True, False] and q.used() == 2


def test_an_evolus_error_is_recorded_without_the_key(three, tmp_path):  # noqa: F811
    rows, (a, _b, _c) = worker_rows(three)
    h = live.LiveHook(tmp_path / "w", FakeEvolus(fail=True), quota=live.Quota(cap=5), limiter=Lim(), sync=True)
    h.on_result(rows[a])
    case = h.cases()[f"live-{a}-OPT01"]
    assert case["run_status"] == "error" and "402" in case["error"] and SECRET not in case["error"]


def test_the_worker_calls_the_hook_after_each_committed_form(three):  # noqa: F811
    P, ep = three["P"], three["ep"]
    w = make_worker(P.root, ep, Ine())
    seen = []

    class Hook:
        def on_result(self, r):
            seen.append(r["clave"])
            raise RuntimeError("Evolus down")              # never stops the audit

    w.evolus = Hook()
    assert w.run() == 3
    rows = W.read_jsonl(P.results)
    assert seen == [r["clave"] for r in rows if r.get("disputes")] and seen


def test_hook_is_off_without_evolus_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(configmod, "_dotenv", lambda: {})
    assert live.hook_for(tmp_path) is None
    monkeypatch.setenv("EVOLUS_LIVE", "0")
    assert live.hook_for(tmp_path) is None


def test_workspace_name_from_the_api_and_fallback(isolated):
    ws = live.workspace(FakeEvolus(), refresh=True)
    assert ws["name"] == "py_tr" and "application.name" in ws["source"]
    assert ws["line"] == "Evolus event workspace: py_tr (event code AMDACT3)"
    assert configmod.load_ids()["workspace_name"] == "py_tr"

    class Down(FakeEvolus):
        def rest(self, *a, **k):
            raise RuntimeError("offline")
    live._WS.clear()
    configmod.save_ids({})
    ws = live.workspace(Down(), refresh=True)
    assert ws["name"] == "py_tr" and "UI" in ws["source"]


def test_results_page_shows_the_workspace_and_desk_send(monkeypatch, isolated):
    monkeypatch.setattr(configmod, "_dotenv", lambda: {})
    web = TestClient(app)
    html = web.get("/results").text
    assert "Evolus event workspace: py_tr (event code AMDACT3)" in html
    assert web.post("/api/evolus/send/010445C0100").status_code == 503     # not configured: refused, nothing sent
    from evolus import web as evolusweb
    ran = []

    class FakeCase:
        def __init__(self, clave, client, **kw):
            self.clave = clave

        def run(self):
            ran.append(self.clave)
            return {"clave": self.clave, "case_id": "c1", "at": "2026-10-16T00:00:00+00:00", "decision": "routed",
                    "decision_reason": "x", "steps": []}
    monkeypatch.setattr(casemod, "Case", FakeCase)
    monkeypatch.setattr(evolusweb.Settings, "load", classmethod(lambda cls: FakeEvolus().s))
    st = __import__("app.store", fromlist=["get_store"]).get_store()
    clave = next(k for k in st.ine_claves() if st.masked_image(k) is not None)
    r = web.post(f"/api/evolus/send/{clave}")
    assert r.status_code == 200 and r.json()["started"]
    import time
    for _ in range(50):
        if ran and casemod.STATE_RUNS.is_file():
            break
        time.sleep(0.05)
    assert ran == [clave] and "review desk" in casemod.STATE_RUNS.read_text(encoding="utf-8")
