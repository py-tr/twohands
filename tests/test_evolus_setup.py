"""`python -m evolus setup`: idempotent find-or-create against a fake Evolus workspace (no network)."""
import json

import httpx
import pytest

from evolus import config as configmod
from evolus import setup as setupmod
from evolus.client import EvolusClient
from evolus.config import Settings

SECRET = "evk_TESTSECRET_setup_0123456789"
USER = "usr_TESTSECRET_user_0123456789"


class Workspace:
    """Minimal in-memory Evolus: agents, json structures, memories, workflows + steps."""

    def __init__(self, own_models=("Qwen3.8-27B",), agents=None):
        self.own = {f"own/{m}" for m in own_models}
        self.agents = list(agents or [])
        self.structures, self.memories, self.workflows = {}, [], []
        self.log = []
        self.n = 0

    def nid(self, p):
        self.n += 1
        return f"{p}-{self.n}"

    def __call__(self, req: httpx.Request):
        m, p = req.method, req.url.path
        body = json.loads(req.content) if req.content and req.headers.get("content-type", "").startswith("application/json") else {}
        self.log.append((m, p, "user" if "x-user-apikey" in req.headers else "app"))
        assert req.headers.get("x-apikey") == SECRET or req.headers.get("x-user-apikey") == USER
        if p == "/api/v1/agents" and m == "GET":
            return httpx.Response(200, json=self.agents)
        if p == "/api/v1/agents" and m == "POST":
            if body.get("modelKey") not in self.own:
                return httpx.Response(422, json={"errorCode": "ai.model_not_found"})
            a = body | {"agentId": self.nid("agent")}
            self.agents.append(a)
            return httpx.Response(200, json=a)
        if p.startswith("/api/v1/agents/") and m == "PUT" and p.count("/") == 4:
            a = next(x for x in self.agents if x["agentId"] == p.rsplit("/", 1)[-1])
            if "modelKey" in body and body["modelKey"] not in self.own:
                return httpx.Response(422, json={"errorCode": "ai.model_not_found"})
            a.update(body)
            return httpx.Response(200, json=a)
        if p.endswith("/json") and p.startswith("/api/v1/agents/"):
            if "x-user-apikey" not in req.headers:
                return httpx.Response(401, json={"errorCode": "auth.unauthorized"})
            aid = p.split("/")[4]
            if m == "GET":
                return httpx.Response(200, json=self.structures.get(aid, []))
            s = body | {"id": self.nid("struct")}
            self.structures.setdefault(aid, []).append(s)
            return httpx.Response(200, json=s)
        if "/json/" in p and m == "PUT":
            return httpx.Response(200, json=body)
        if p == "/api/v1/memories" and m == "GET":
            return httpx.Response(200, json=self.memories)
        if p == "/api/v1/memories/simple":
            mm = {"id": self.nid("mem"), "name": body["name"]}
            self.memories.append(mm)
            return httpx.Response(201, json=mm)
        if p.endswith("/memories") and m == "POST":
            return httpx.Response(200, json={})
        if p.endswith("/knowledge-memory"):
            return httpx.Response(401, json={"errorCode": "auth.unauthorized"})
        if p == "/api/v1/workflows" and m == "GET":
            return httpx.Response(200, json=[{"id": w["id"], "name": w["name"]} for w in self.workflows])
        if p == "/api/v1/workflows" and m == "POST":
            w = body | {"id": self.nid("wf"), "steps": [], "isActive": False}
            self.workflows.append(w)
            return httpx.Response(201, json=w)
        if p.startswith("/api/v1/workflows/"):
            wid = p.split("/")[4]
            w = next(x for x in self.workflows if x["id"] == wid)
            if p.endswith("/steps"):
                assert isinstance(body["stepType"], int)  # the API takes the enum numbers
                st = body | {"id": self.nid("step")}
                w["steps"].append(st)
                return httpx.Response(200, json=st)
            if m == "GET":
                return httpx.Response(200, json=w)
            if m == "PUT":
                w.update(body)
                return httpx.Response(200, json=w)
            if m == "DELETE":
                self.workflows.remove(w)
                return httpx.Response(204)
        return httpx.Response(404, json={"error": f"unexpected {m} {p}"})


def client(ws, user=False):
    s = Settings(key=SECRET, app_id="app-1", user_key=USER if user else "")
    return EvolusClient(s, transport=httpx.MockTransport(ws), pace_s=0)


@pytest.fixture(autouse=True)
def ids_file(tmp_path, monkeypatch):
    f = tmp_path / "ids.json"
    monkeypatch.setattr(configmod, "IDS_FILE", f)
    return f


def test_setup_creates_everything_with_user_key(ids_file):
    ws = Workspace()
    ids = setupmod.Setup(client(ws, user=True), model="Qwen3.8-27B", log=lambda s: None).run()
    assert {a["name"] for a in ws.agents} == {"Intake clerk", "Tally sheet reader"}
    assert all(a["modelKey"] == "own/Qwen3.8-27B" for a in ws.agents)
    assert next(a for a in ws.agents if a["name"] == "Tally sheet reader")["isExtractor"] is True
    assert ids["extractor_id"] and ids["library_id"] and ids["workflow_id"] and ids["filing_workflow_id"]
    names = {w["name"]: w for w in ws.workflows}
    hand = names["Review hand-off"]
    assert hand["isActive"] and [s["stepType"] for s in hand["steps"]] == [1, 16, 19, 14]
    assert json.loads(hand["steps"][1]["stepConfigJson"])["options"]["target"] == "Spanish"
    filing = names["Record filing"]
    assert filing["isActive"] and [s["stepType"] for s in filing["steps"]] == [19, 5, 14]
    struct = ws.structures[ids["extractor_agent_id"]][0]
    assert set(json.loads(struct["structure"])) >= {"OPT01", "TOTAL"} and struct["maxCorrections"] == 0
    saved = json.loads(ids_file.read_text(encoding="utf-8"))
    assert saved["agent"] == f"app-1:{ids['agent_id']}" and SECRET not in ids_file.read_text() and USER not in ids_file.read_text()
    # the extractor schema and the library are created with the personal key; the rest with the application key
    assert ("POST", f"/api/v1/agents/{ids['extractor_agent_id']}/json", "user") in ws.log
    assert ("POST", "/api/v1/workflows", "app") in ws.log


def test_setup_is_idempotent_and_reuses_a_hand_made_agent(ids_file):
    ws = Workspace(agents=[{"agentId": "hand-1", "name": "Intake clerk", "modelKey": None}])
    setupmod.Setup(client(ws, user=True), log=lambda s: None).run()
    n_agents, n_wf, n_steps = len(ws.agents), len(ws.workflows), sum(len(w["steps"]) for w in ws.workflows)
    assert next(a for a in ws.agents if a["agentId"] == "hand-1")["modelKey"] == "own/Qwen3.8-27B"
    setupmod.Setup(client(ws, user=True), log=lambda s: None).run()
    assert (len(ws.agents), len(ws.workflows), sum(len(w["steps"]) for w in ws.workflows)) == (n_agents, n_wf, n_steps)
    assert len(ws.memories) == 1 and sum(len(v) for v in ws.structures.values()) == 1


def test_switching_the_model_is_one_command(ids_file):
    ws = Workspace(own_models=("Qwen3.8-27B", "Gemma-4-31B-IT"))
    setupmod.Setup(client(ws), model="Qwen3.8-27B", log=lambda s: None).run()
    ids = setupmod.Setup(client(ws), model="Gemma-4-31B-IT", log=lambda s: None).run()
    assert ids["model_key"] == "own/Gemma-4-31B-IT"
    assert all(a["modelKey"] == "own/Gemma-4-31B-IT" for a in ws.agents)


def test_without_user_key_the_gaps_are_reported_not_faked(ids_file):
    ws = Workspace()
    notes = []
    s = setupmod.Setup(client(ws), log=notes.append)
    ids = s.run()
    assert ids["extractor_id"] == "" and ids["library_id"] == ""
    assert ids["workflow_id"] and ids["filing_workflow_id"]
    assert any("EVOLUS_USER_KEY" in n for n in s.notes)


def test_half_built_workflow_is_rebuilt(ids_file):
    ws = Workspace()
    ws.workflows.append({"id": "wf-broken", "name": "Review hand-off", "steps": [], "isActive": False})
    setupmod.Setup(client(ws), log=lambda s: None).run()
    hand = [w for w in ws.workflows if w["name"] == "Review hand-off"]
    assert len(hand) == 1 and hand[0]["id"] != "wf-broken" and len(hand[0]["steps"]) == 4


def test_settings_read_ids_json_first(ids_file, monkeypatch):
    ids_file.write_text(json.dumps({"workflow_id": "from-ids", "agent": "a:b"}), encoding="utf-8")
    monkeypatch.setenv("EVOLUS_WORKFLOW_ID", "from-env")
    s = Settings.load()
    assert s.workflow_id == "from-ids" and s.agent == "a:b"


def test_filing_script_matches_the_gate():
    js = setupmod.filing_js()
    assert "rows sum to TOTAL" in js and "OPT15" in js and "TOTAL" in js
    assert "return {" in js
