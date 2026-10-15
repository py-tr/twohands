"""`python -m evolus setup`: build (or find) every Evolus building block of the intake process, idempotently.

Find by name first, else create. Ids go to evolus/ids.json (not secrets). Endpoints: docs/evolus-openapi.json.

  agent     "Intake clerk"         POST /api/v1/agents (modelKey own/<alias>: the AMD Token Factory model
                                   connected under "Your models"); its knowledge library is the fallback register
  extractor "Tally sheet reader"   POST /api/v1/agents (isExtractor) + POST /api/v1/agents/{id}/json
                                   ("Tally sheet type 2", our 23 fields; needs a personal User API key)
  library   "Records register"     POST /api/v1/memories/simple (User API key) or the clerk's knowledge memory
                                   (POST /api/v1/agents/{id}/knowledge-memory, application key)
  workflow  "Review hand-off"      POST /api/v1/workflows + /steps (AgentCall, AiTool translate, Script,
                                   [Email], Output), switched on
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from evolus import case as casemod
from evolus.client import EvolusClient, EvolusError, NotConfigured
from evolus.config import load_ids, save_ids

AGENT = "Intake clerk"
EXTRACTOR_AGENT = "Tally sheet reader"
STRUCTURE = "Tally sheet type 2"
LIBRARY = "Records register"
WORKFLOW = "Review hand-off"
TAGS = ["two-hands", "paper-form-intake"]
# enum values from GET /api/v1/workflows/step-catalog (the API takes the numbers)
STEP = {"AgentCall": 1, "Email": 3, "CreateFile": 5, "Output": 14, "AiTool": 16, "Script": 19}
FILING = "Record filing"

CLERK_PROMPT = (
    "You work in a records office that captures paper tally forms. A deterministic checker (the form's own "
    "arithmetic) decides whether a form is accepted; you never decide and never guess a value. When a form is "
    "routed to a person, you write the review task for the clerk: which field(s) to look at on the page and why, "
    "in at most two plain sentences. Vote rows are called 'Option 01' to 'Option 15'; never name or compare "
    "parties. You can also answer questions about accepted records filed in your knowledge library.")

EXTRACTOR_PROMPT = (
    "You read one privacy-masked paper tally form (INE 2024, type 2; the right-hand column is blacked out on purpose). "
    "Return every field as an integer: the number written in its digit boxes; if the boxes are empty use the amount "
    "written in words; null if unreadable. Do not correct the numbers so that they add up: copy what is written. "
    "Fields:\n")

NOTE_PROMPT = (
    "A paper form was routed to a person. From the case below (JSON), write the review task for the clerk in at "
    "most two sentences of English: the field(s) to check on the page and why. Do not guess the correct value.\n\n")

ASSEMBLE_JS = (
    "const t = s => (s && s.text ? s.text : '').trim();\n"
    "return { case_id: params.case_id, form: params.form, fields_to_check: params.fields, crop_url: params.crop_url,\n"
    "  note_en: t(sources[0]), note_es: t(sources[1]), assigned_to: 'records office reviewer', status: 'awaiting review' };")


def filing_js() -> str:
    """The gate's identities, generated from our schema, as a deterministic Evolus Script step (zero AI calls).
    Input (JSON): {"form": ..., "values": {"OPT01": 12, ..., "TOTAL": 250}}."""
    from app import store as storemod
    s = storemod.schema()
    ids = []
    for idt in s.get("identities", []):
        lhs = s["vote_keys"] if idt["sum"] == "@vote" else idt["sum"]
        ids.append({"name": idt["name"], "lhs": [storemod.code_of(k) for k in lhs],
                    "rhs": [storemod.code_of(k) for k in idt["equals"]]})
    codes = [storemod.code_of(f["key"]) for f in s["fields"]]
    lines = [
        "const IDS = " + json.dumps(ids) + ";",
        "const CODES = " + json.dumps(codes) + ";",
        "const v = (data && data.values) || {};",
        "const num = c => (v[c] === null || v[c] === undefined || v[c] === '') ? null : Number(v[c]);",
        "const missing = CODES.filter(c => num(c) === null || !Number.isInteger(num(c)));",
        "const sum = cs => cs.reduce((a, c) => a + (num(c) || 0), 0);",
        "const checks = IDS.map(i => ({ name: i.name, lhs: sum(i.lhs), rhs: sum(i.rhs), "
        "ok: missing.length === 0 && sum(i.lhs) === sum(i.rhs) }));",
        "const ok = missing.length === 0 && checks.every(c => c.ok);",
        "return { form: data && data.form, status: ok ? 'filed' : 'refused: arithmetic does not hold', "
        "missing: missing, identities: checks, record: ok ? v : null };",
    ]
    return chr(10).join(lines)


def _items(x: Any) -> list:
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for k in ("items", "data", "results", "value"):
            if isinstance(x.get(k), list):
                return x[k]
    return []


def _id(x: dict, *keys: str) -> Optional[str]:
    for k in keys + ("id",):
        if isinstance(x, dict) and x.get(k):
            return str(x[k])
    return None


def model_key_candidates(model: str) -> list[str]:
    if model.startswith("own/") or "/" in model:
        return [model]
    slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
    return list(dict.fromkeys([f"own/{model}", f"own/{model.lower()}", f"own/{slug}"]))


class Setup:
    def __init__(self, client: EvolusClient, model: str = "Qwen3.8-27B", model_key: str = "",
                 reviewer_email: str = "", rebuild: bool = False, log: Callable[[str], None] = print):
        self.c, self.model, self.model_key = client, model, model_key
        self.reviewer_email, self.rebuild, self.log = reviewer_email, rebuild, log
        self.ids = load_ids()
        self.notes: list[str] = []

    # ------------------------------------------------------------------ agents
    def _agents(self) -> list[dict]:
        return _items(self.c.rest("GET", "/api/v1/agents", "GET /api/v1/agents"))

    def _with_model(self, fn: Callable[[str], Any]) -> tuple[Any, str]:
        """Try the model key candidates until the server accepts one (ai.model_not_found -> next)."""
        last: Optional[EvolusError] = None
        for key in ([self.model_key] if self.model_key else model_key_candidates(self.model)):
            try:
                return fn(key), key
            except EvolusError as e:
                if "model_not_found" in e.detail or "model_not_allowed" in e.detail:
                    last = e
                    continue
                raise
        raise last or EvolusError("?", "model", "no model key accepted")

    def ensure_agent(self, name: str, prompt: str, extractor: bool = False) -> str:
        found = next((a for a in self._agents() if (a.get("name") or "").strip().lower() == name.lower()), None)
        body = {"name": name, "prompt": prompt, "description": "Two Hands: paper form intake for a records office",
                "language": "en", "tags": TAGS, "isExtractor": extractor}
        if found:
            aid = _id(found, "agentId")
            cur = found.get("modelKey")
            want = self.model_key or None
            if not want or cur != want:
                _, key = self._with_model(lambda k: self.c.rest("PUT", f"/api/v1/agents/{aid}", "PUT /api/v1/agents/{agentId}",
                                                                {"modelKey": k} | ({"isExtractor": True} if extractor else {})))
                self.model_key = key
            self.log(f"agent '{name}': found ({aid}), model {self.model_key}")
            return aid
        a, key = self._with_model(lambda k: self.c.rest("POST", "/api/v1/agents", "POST /api/v1/agents", body | {"modelKey": k}))
        self.model_key = key
        aid = _id(a, "agentId")
        self.log(f"agent '{name}': created ({aid}), model {key}")
        return aid

    # ------------------------------------------------------------------ extractor schema
    def ensure_structure(self, agent_id: str) -> Optional[str]:
        fields = casemod.extractor_fields()
        example = {f["name"]: 0 for f in fields}
        prompt = EXTRACTOR_PROMPT + "\n".join(f"- {f['name']}: {f['description']}" for f in fields)
        body = {"title": STRUCTURE, "userPrompt": prompt, "structure": json.dumps(example), "canUseOCR": True,
                "maxCorrections": 0}
        try:
            existing = _items(self.c.rest("GET", f"/api/v1/agents/{agent_id}/json", "GET /api/v1/agents/{agentId}/json", user=True))
            hit = next((x for x in existing if (x.get("title") or "").lower() == STRUCTURE.lower()), None)
            if hit:
                sid = _id(hit)
                self.c.rest("PUT", f"/api/v1/agents/{agent_id}/json/{sid}", "PUT /api/v1/agents/{agentId}/json/{outputStructureId}",
                            body | {"id": sid}, user=True)
                self.log(f"extractor schema '{STRUCTURE}': found ({sid}), updated")
                return sid
            s = self.c.rest("POST", f"/api/v1/agents/{agent_id}/json", "POST /api/v1/agents/{agentId}/json", body, user=True)
            sid = _id(s)
            self.log(f"extractor schema '{STRUCTURE}': created ({sid})")
            return sid
        except NotConfigured:
            self.notes.append("extractor schema needs EVOLUS_USER_KEY (Evolus API reference page > API Keys tab > "
                              "create a personal key; put it in .env), then run setup again")
        except EvolusError as e:
            self.notes.append(f"extractor schema not created: HTTP {e.status} {e.detail[:160]}")
        self.log("extractor schema: NOT created (see notes)")
        return None

    # ------------------------------------------------------------------ library
    def ensure_library(self, clerk_id: str) -> Optional[str]:
        if self.c.s.user_key:
            try:
                mems = _items(self.c.rest("GET", "/api/v1/memories", "GET /api/v1/memories", user=True))
                hit = next((m for m in mems if (m.get("name") or "").lower() == LIBRARY.lower()), None)
                if hit:
                    self.log(f"library '{LIBRARY}': found ({_id(hit)})")
                    return _id(hit)
                m = self.c.rest("POST", "/api/v1/memories/simple", "POST /api/v1/memories/simple",
                                {"name": LIBRARY, "type": 0, "aiAccess": 0}, user=True)
                mid = _id(m)
                self.c.rest("POST", f"/api/v1/agents/{clerk_id}/memories", "POST /api/v1/agents/{agentId}/memories",
                            {"memoryId": mid})
                self.log(f"library '{LIBRARY}': created ({mid}) and assigned to '{AGENT}'")
                return mid
            except EvolusError as e:
                self.notes.append(f"named library not created (HTTP {e.status}); using the clerk's knowledge memory")
        try:
            am = self.c.rest("POST", f"/api/v1/agents/{clerk_id}/knowledge-memory",
                             "POST /api/v1/agents/{agentId}/knowledge-memory", params={"type": "Rag"})
        except EvolusError as e:
            self.notes.append(f"library not created (HTTP {e.status}): creating a library needs EVOLUS_USER_KEY "
                              "(a personal User API key); run setup again once it is in .env")
            self.log("library: NOT created (see notes)")
            return None
        mid = str(am.get("memoryId") or _id(am.get("memory") or {}) or "")
        self.log(f"library: the '{AGENT}' knowledge library ({mid})")
        return mid or None

    # ------------------------------------------------------------------ workflow
    def _workflows(self) -> list[dict]:
        return _items(self.c.rest("GET", "/api/v1/workflows", "GET /api/v1/workflows"))

    def ensure_workflow(self, clerk_id: str) -> str:
        found = next((w for w in self._workflows() if (w.get("name") or "").lower() == WORKFLOW.lower()), None)
        if found and not self.rebuild:
            full = self.c.rest("GET", f"/api/v1/workflows/{_id(found)}", "GET /api/v1/workflows/{workflowId}")
            if len(full.get("steps") or []) < 4:  # a half-built workflow from an interrupted setup
                self.rebuild = True
        if found and self.rebuild:
            self.c.rest("DELETE", f"/api/v1/workflows/{_id(found)}", "DELETE /api/v1/workflows/{workflowId}")
            found = None
        if found:
            wid = _id(found)
            w = self.c.rest("GET", f"/api/v1/workflows/{wid}", "GET /api/v1/workflows/{workflowId}")
            if not w.get("isActive"):
                self.c.rest("PUT", f"/api/v1/workflows/{wid}", "PUT /api/v1/workflows/{workflowId}", {"isActive": True})
            self.log(f"workflow '{WORKFLOW}': found ({wid}), {len(w.get('steps') or [])} steps, on")
            return wid
        params = [{"name": "form", "type": "string", "description": "form id", "required": True},
                  {"name": "case_id", "type": "string", "description": "Two Hands case id", "required": True},
                  {"name": "fields", "type": "string", "description": "fields to check (neutral names)", "required": False, "defaultValue": ""},
                  {"name": "crop_url", "type": "string", "description": "crop of the failing field", "required": False, "defaultValue": ""}]
        w = self.c.rest("POST", "/api/v1/workflows", "POST /api/v1/workflows",
                        {"name": WORKFLOW, "description": "Two Hands: a routed paper form goes to a person with a "
                         "review task drafted by the Intake clerk (AMD-hosted open model) in English and Spanish.",
                         "tags": TAGS, "parameters": params, "isActive": False})
        wid = _id(w)

        def add(body: dict) -> str:
            st = self.c.rest("POST", f"/api/v1/workflows/{wid}/steps", "POST /api/v1/workflows/{workflowId}/steps", body)
            return _id(st)

        s1 = add({"name": "Draft the review task (Intake clerk)", "stepType": STEP["AgentCall"], "agentId": clerk_id,
                  "inputMode": 1, "prompt": NOTE_PROMPT, "createDoc": False})
        s2 = add({"name": "Translate the task to Spanish", "stepType": STEP["AiTool"], "inputStepIds": [s1],
                  "inputMode": 0, "stepConfigJson": json.dumps({"toolSlug": "translate",
                                                                               "options": {"target": "Spanish"}})})
        s3 = add({"name": "Assemble the review task", "stepType": STEP["Script"], "inputStepIds": [s1, s2],
                  "inputMode": 0, "stepConfigJson": json.dumps({"script": ASSEMBLE_JS})})
        last = s3
        if self.reviewer_email:
            last = add({"name": "Hand to the reviewer (email)", "stepType": STEP["Email"], "inputStepIds": [s3],
                        "emailRecipients": self.reviewer_email,
                        "emailSubjectTemplate": "Review task: form {{param:form}}",
                        "emailBodyTemplate": "<p>{{step:" + s3 + ".note_en}}</p><p>{{step:" + s3 + ".note_es}}</p>"
                                             "<p>Crop: {{param:crop_url}}</p><p>Case {{param:case_id}}</p>"})
        add({"name": "Review task (output)", "stepType": STEP["Output"], "inputStepIds": [s3]})
        self.c.rest("PUT", f"/api/v1/workflows/{wid}", "PUT /api/v1/workflows/{workflowId}", {"isActive": True})
        self.log(f"workflow '{WORKFLOW}': created ({wid}) with {4 + bool(self.reviewer_email)} steps, switched on"
                 + ("" if last != s3 else "; hand-off goes to the Two Hands review desk (no reviewer email set)"))
        return wid

    # ------------------------------------------------------------------ workflow 2: record filing (no AI)
    def ensure_filing_workflow(self) -> str:
        found = next((w for w in self._workflows() if (w.get("name") or "").lower() == FILING.lower()), None)
        if found and not self.rebuild:
            full = self.c.rest("GET", f"/api/v1/workflows/{_id(found)}", "GET /api/v1/workflows/{workflowId}")
            if len(full.get("steps") or []) >= 3:
                if not full.get("isActive"):
                    self.c.rest("PUT", f"/api/v1/workflows/{_id(found)}", "PUT /api/v1/workflows/{workflowId}", {"isActive": True})
                self.log(f"workflow '{FILING}': found ({_id(found)}), on")
                return _id(found)
        if found:
            self.c.rest("DELETE", f"/api/v1/workflows/{_id(found)}", "DELETE /api/v1/workflows/{workflowId}")
        w = self.c.rest("POST", "/api/v1/workflows", "POST /api/v1/workflows",
                        {"name": FILING, "description": "Two Hands: an accepted paper form is re-checked against the "
                         "form's own arithmetic (deterministic script, no AI) and filed as a record file.",
                         "tags": TAGS, "isActive": False})
        wid = _id(w)

        def add(body: dict) -> str:
            return _id(self.c.rest("POST", f"/api/v1/workflows/{wid}/steps", "POST /api/v1/workflows/{workflowId}/steps", body))

        s1 = add({"name": "Re-check the paper's arithmetic", "stepType": STEP["Script"], "inputMode": 1,
                  "stepConfigJson": json.dumps({"script": filing_js()})})
        s2 = add({"name": "Create the record file", "stepType": STEP["CreateFile"], "inputStepIds": [s1], "inputMode": 0,
                  "stepConfigJson": json.dumps({"format": "json", "fileNamePattern": "record_{{timestamp}}.{{format}}"})})
        add({"name": "Filed record (output)", "stepType": STEP["Output"], "inputStepIds": [s2]})
        self.c.rest("PUT", f"/api/v1/workflows/{wid}", "PUT /api/v1/workflows/{workflowId}", {"isActive": True})
        self.log(f"workflow '{FILING}': created ({wid}) with 3 steps, switched on")
        return wid

    # ------------------------------------------------------------------ all
    def run(self) -> dict:
        clerk = self.ensure_agent(AGENT, CLERK_PROMPT)
        reader = self.ensure_agent(EXTRACTOR_AGENT, EXTRACTOR_PROMPT + "(see the output structure)", extractor=True)
        sid = self.ensure_structure(reader)
        lib = self.ensure_library(clerk)
        wid = self.ensure_workflow(clerk)
        fid = self.ensure_filing_workflow()
        self.ids.update({"agent_id": clerk, "agent": f"{self.c.s.app_id}:{clerk}", "model_key": self.model_key,
                         "extractor_agent_id": reader, "extractor_id": sid or "", "library_id": lib or "",
                         "workflow_id": wid, "filing_workflow_id": fid, "names": {"agent": AGENT, "extractor_agent": EXTRACTOR_AGENT,
                                                       "extractor": STRUCTURE, "library": LIBRARY, "workflow": WORKFLOW,
                                                       "filing_workflow": FILING},
                         "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        save_ids(self.ids)
        for n in self.notes:
            self.log("note: " + n)
        return self.ids
