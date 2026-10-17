"""Routed fields as Evolus "Audit finding" cases (evolus/routed.py), Evolus mocked: every case is a field the gate
refused in a real read, with its masked crop; nothing party-named or banned is sent; the ledger makes the runner
idempotent (a case with an execution id is never sent again); three HTTP errors in a row stop it."""
import json

import httpx
import pytest

from evolus import config as configmod
from evolus import routed
from evolus.client import EvolusClient
from evolus.config import Settings

SECRET = "evk_FAKE_FOR_TESTS_routed_0123456789"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(configmod, "IDS_FILE", tmp_path / "ids.json")
    for n in configmod.SECRET_NAMES:
        monkeypatch.delenv(n, raising=False)
    return tmp_path


@pytest.fixture(scope="module")
def r300():
    cs = routed.candidates("r300")
    if not cs:
        pytest.skip("no masked pages of the 300 here (clean clone)")
    return cs


class Lim:
    def acquire(self):
        return 0.0


def test_cases_are_real_refused_fields_with_masked_crops(r300):
    from app import store as storemod
    rows = routed._rows(routed.SOURCES["r300"][0])
    assert len({c["case_id"] for c in r300}) == len(r300)
    for c in r300[:60]:
        row = rows[c["form"]]
        assert row["routed"] and not row["accepted"]
        ev = storemod.evaluate(storemod.read_from_core(c["form"], "t", row))
        assert storemod.key_of(c["code"]) in {k for k, _ in routed.refused(ev)}
        assert c["crop_url"].startswith(f"/crop/{c['form']}/{c['code']}.jpg") and len(c["crop_sha256"]) == 64
        assert routed.safe(c) is None and c["task_for_clerk"].startswith("Look at ")


def test_guard_refuses_party_names_and_the_banned_word(r300):
    c = dict(r300[0])
    assert routed.safe(c | {"task_for_clerk": "check MORENA"}) is not None
    assert routed.safe(c | {"why_routed": "possible Fraud"}) is not None


def fake(fail=False):
    n = {"exec": 0}

    def h(req: httpx.Request):
        if fail:
            return httpx.Response(500, text="boom")
        if req.url.path.startswith("/api/v1/agents/"):
            return httpx.Response(200, json={"modelKey": "own/gemma-4-31b-it", "modelState": "ok"})
        if req.url.path.endswith("/execute"):
            n["exec"] += 1
            return httpx.Response(200, headers={"X-Workflow-Execution-Id": f"ex-{n['exec']}"}, json={})
        out = {"finding": "The paper shows 5. Nothing was keyed. No identity supports it, for the auditor to confirm.",
               "evidence": {"score": 3, "tier": "medium", "agrees_with_app": True}, "status": "open"}
        return httpx.Response(200, json={"status": "Completed", "output": json.dumps(out)})
    return h, n


def runner(tmp_path, h):
    c = EvolusClient(Settings(key=SECRET, app_id="app-1", audit_workflow_id="wf-audit"),
                     transport=httpx.MockTransport(h), pace_s=0)
    return routed.Runner(c, interval=0, in_flight=2, poll_every=0, limiter=Lim(), sleep=lambda s: None,
                         log=lambda s: None, path=tmp_path / "ex.jsonl")


def test_runner_is_idempotent_and_records_each_execution(tmp_path, r300):
    h, n = fake()
    res = runner(tmp_path, h).run([("r300", 3)], cap=150)
    assert res["started"] == 3 and n["exec"] == 3
    s = routed.summary(tmp_path / "ex.jsonl")
    assert (s["sent"], s["succeeded"], s["success_pct"]) == (3, 3, 100.0)
    assert s["models_reported"] == ["own/gemma-4-31b-it (ok)"]
    for c in routed.cases(tmp_path / "ex.jsonl").values():
        assert c["workflow"] == "Audit finding" and c["execution_id"] and c["status"] == "Completed" and c["started_at"]
    res = runner(tmp_path, h).run([("r300", 3)], cap=150)
    assert res["started"] == 0 and n["exec"] == 3          # the plan is met: nothing is sent twice
    text = (tmp_path / "ex.jsonl").read_text(encoding="utf-8")
    assert SECRET not in text and "fraud" not in text.lower()


def test_three_errors_in_a_row_stop(tmp_path, r300):
    h, _ = fake(fail=True)
    res = runner(tmp_path, h).run([("r300", 10)], cap=150)
    assert res["stopped"] and res["started"] <= 3
