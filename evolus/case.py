"""The business process: paper-form intake for a records office, run as an Evolus case.

For one masked form:
  1. primary read   - our measured Gemma-4-31B-IT read on AMD (results/calls_gemma.jsonl), checked by our gate
  2. extractor      - an Evolus document extractor reads the same masked page: an independent third opinion,
                      checked by the same gate and compared field by field (never trusted blindly)
  3. decision       - the paper decides: accepted only if the primary read passes every identity and the
                      extractor does not produce a *different* reading that also passes them
  4a. accepted      - the record is filed in an Evolus knowledge library (the office's register)
  4b. routed        - the Evolus agent (Gemma on AMD) drafts a short note for the reviewer, the "translate"
                      AI Tool turns it into Spanish, and the "review hand-off" workflow is started with the
                      failing field, its crop link and both notes; we poll the run until it settles.
Every step is recorded (block, endpoint, status, time, one-line summary) in results/evolus_runs.jsonl.
Only masked pages (data/masked/**) are ever sent. Vote rows are "Option NN"; nothing is aggregated by option.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from app import store as storemod
from evolus.client import EvolusClient, EvolusError, NotConfigured
from evolus.config import Settings, redact

RUNS_FILE = storemod.RESULTS / "evolus_runs.jsonl"
STATE_RUNS = storemod.STATE / "evolus_runs.jsonl"
CALLBACKS = storemod.STATE / "evolus_callbacks.jsonl"
PRIMARY_MODEL = "Gemma-4-31B-IT"
FINAL = {"completed", "failed", "succeeded", "cancelled", "canceled", "error"}


# ------------------------------------------------------------------------------------------- schema for Evolus
def codes() -> list[str]:
    return [storemod.code_of(f["key"]) for f in storemod.schema()["fields"]]


def extractor_fields() -> list[dict]:
    """The extractor's field list, to paste into the Evolus extractor editor (neutral names only)."""
    out = []
    vote_row = 0
    for f in storemod.schema()["fields"]:
        k = f["key"]
        code, name = storemod.code_of(k), storemod.name_of(k)
        if f.get("vote"):
            vote_row += 1
            where = f"row {vote_row} of the vote table (17 rows, top to bottom)"
        else:
            where = storemod.SECTION.get(k, "")
        out.append({"name": code, "type": "integer",
                    "description": f"{name}: {where}. The number written in the digit boxes; "
                                   "if the boxes are empty use the amount written in words; null if unreadable."})
    return out


# ------------------------------------------------------------------------------------------- gate
def gate_check(values: dict, words: Optional[dict] = None) -> dict:
    """Run our deterministic gate on field values given by public code. Returns a neutral verdict."""
    s = storemod.schema()
    vals, wds = {}, {}
    for f in s["fields"]:
        k = f["key"]
        c = storemod.code_of(k)
        vals[k] = storemod.iv((values or {}).get(c))
        wds[k] = storemod.iv((words or {}).get(c)) if words else None
    r = storemod.Read("api", "api", vals, wds, {}, [], False)
    ev = storemod.evaluate(r)
    return storemod.public({
        "accepted": ev["accepted"], "line": ev["line"], "reasons": ev["reasons"],
        "failing": sorted(set(ev["failing"])),
        "identities": [{"name": i["name"], "ok": i["ok"], "lhs": i["lhs"], "rhs": i["rhs"]} for i in ev["identities"]],
    })


def find_values(obj: Any) -> Optional[dict]:
    """Locate the {CODE: value} map in an extractor response, whatever envelope it comes in."""
    want = {c.lower(): c for c in codes()}

    def norm(k: str) -> str:
        return re.sub(r"[^a-z0-9_]", "", str(k).lower().replace(" ", "_"))

    def walk(o, depth=0):
        if depth > 6:
            return None
        if isinstance(o, str):
            t = o.strip()
            if t.startswith("```"):
                t = t.strip("`").split("\n", 1)[-1]
            if t[:1] in "{[":
                try:
                    return walk(json.loads(t), depth + 1)
                except ValueError:
                    return None
            return None
        if isinstance(o, dict):
            hits = {want[norm(k)]: v for k, v in o.items() if norm(k) in want}
            if len(hits) >= 5:
                return {c: (v.get("value") if isinstance(v, dict) else v) for c, v in hits.items()}
            for v in o.values():
                got = walk(v, depth + 1)
                if got:
                    return got
        if isinstance(o, list):
            if o and all(isinstance(x, dict) and ("name" in x or "field" in x) for x in o):
                m = {str(x.get("name") or x.get("field")): x.get("value") for x in o}
                got = walk(m, depth + 1)
                if got:
                    return got
            for v in o:
                got = walk(v, depth + 1)
                if got:
                    return got
        return None

    return walk(obj)


def text_of(obj: Any) -> str:
    """The main text of an AI Tool / workflow response (first long string found)."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        for k in ("text", "result", "output", "translation", "translatedText", "content", "data"):
            if k in obj:
                t = text_of(obj[k])
                if t:
                    return t
        for v in obj.values():
            t = text_of(v)
            if t and len(t) > 20:
                return t
    if isinstance(obj, list):
        for v in obj:
            t = text_of(v)
            if t:
                return t
    return ""


def translate_options(catalog: Any, lang: str = "es") -> dict:
    """Pick the target-language option of the 'translate' tool from GET /api/v1/ai-tools."""
    tools = catalog if isinstance(catalog, list) else (catalog or {}).get("tools") or (catalog or {}).get("data") or []
    for t in tools if isinstance(tools, list) else []:
        if not isinstance(t, dict) or str(t.get("id") or t.get("name") or t.get("slug")).lower() != "translate":
            continue
        opts = t.get("options") or []
        items = opts.items() if isinstance(opts, dict) else [((o or {}).get("name") or (o or {}).get("key"), o) for o in opts]
        for name, spec in items:
            if name and ("lang" in str(name).lower() or "target" in str(name).lower()):
                allowed = (spec or {}).get("values") or (spec or {}).get("enum") or [] if isinstance(spec, dict) else []
                for a in allowed:
                    av = a.get("value") if isinstance(a, dict) else a
                    if str(av).lower() in (lang, "spanish", "es-es", "es-mx"):
                        return {name: av}
                return {name: lang}
    return {"targetLanguage": lang}


# ------------------------------------------------------------------------------------------- the case
class Case:
    def __init__(self, clave: str, client: EvolusClient, store: Optional[storemod.Store] = None,
                 poll_s: float = 90.0, poll_every: float = 6.0, sleep: Callable[[float], None] = time.sleep):
        self.clave, self.c = clave, client
        self.s: Settings = client.s
        self.st = store or storemod.get_store()
        self.poll_s, self.poll_every, self.sleep = poll_s, poll_every, sleep
        self.steps: list[dict] = []
        self.amd_calls_via_evolus = 0

    def step(self, block: str, endpoint: str, fn: Callable[[], Any], summarize: Callable[[Any], str]) -> Any:
        t0 = time.monotonic()
        try:
            out = fn()
        except NotConfigured as e:
            self.steps.append({"block": block, "endpoint": endpoint, "status": "skipped", "summary": str(e)})
            return None
        except EvolusError as e:
            self.steps.append({"block": block, "endpoint": endpoint, "status": "error", "http": e.status,
                               "ms": int((time.monotonic() - t0) * 1000), "summary": e.detail[:200]})
            return None
        self.steps.append({"block": block, "endpoint": endpoint, "status": "ok",
                           "ms": int((time.monotonic() - t0) * 1000), "summary": summarize(out)[:240]})
        return out

    def skip(self, block: str, why: str) -> None:
        self.steps.append({"block": block, "status": "skipped", "summary": why})

    def crop_urls(self, fail_codes: list[str]) -> list[str]:
        base = self.s.public_url or ""
        return [f"{base}/crop/{self.clave}/{c}.jpg?pad=0.01" for c in fail_codes[:4]] + [f"{base}/form/{self.clave}"]

    # ----------------------------------------------------------------------------- run
    def run(self) -> dict:
        n0 = len(self.c.calls)
        page = self.st.masked_image(self.clave)
        if page is None or storemod.MASKED not in Path(page).resolve().parents:
            raise ValueError(f"{self.clave}: no masked page; nothing is sent")
        r = self.st.default_read(self.clave)
        primary = None
        if r is not None:
            ev = storemod.evaluate(r)
            pvals = {storemod.code_of(k): v for k, v in r.values.items()}
            primary = {"source": f"results/{r.run_id}.jsonl" if r.run_id.startswith(("calls_", "verify_")) else r.run_id,
                       "model": PRIMARY_MODEL, "on": "AMD Token Factory", "accepted": ev["accepted"], "line": ev["line"],
                       "reasons": [storemod.neutralize(x) for x in ev["reasons"]][:6],
                       "failing": [storemod.code_of(k) for k in dict.fromkeys(ev["failing"])]}
            self.steps.append({"block": "primary read (our app)", "endpoint": "local gate on the measured read",
                               "status": "ok", "summary": ev["line"]})
        else:
            pvals = {}
            self.steps.append({"block": "primary read (our app)", "status": "missing", "summary": "no measured read"})

        # 2. Evolus document extractor: independent reader
        extractor: dict = {"status": "skipped"}
        if self.s.extractor_agent_id and self.s.extractor_id:
            out = self.step("document extractor", "POST /api/v1/agents/{agentId}/json/{extractorId}/ask-file",
                            lambda: self.c.extract_file(self.s.extractor_agent_id, self.s.extractor_id, page),
                            lambda o: f"{len(find_values(o) or {})} fields returned")
            vals = find_values(out) if out is not None else None
            if vals:
                g = gate_check(vals)
                ex = {c: storemod.iv(vals.get(c)) for c in codes()}
                dis = [{"code": c, "name": storemod.name_of(storemod.key_of(c)), "primary": pvals.get(c), "extractor": ex[c]}
                       for c in codes() if pvals and ex[c] != pvals.get(c)]
                extractor = {"status": "ok", "read": ex, "accepted": g["accepted"], "line": g["line"],
                             "agree": len(codes()) - len(dis) if pvals else None, "disagree": dis}
                self.steps.append({"block": "gate on the extractor's read (our app)", "endpoint": "POST /api/gate",
                                   "status": "ok", "summary": g["line"] + (f"; differs from the primary read on {len(dis)} field(s)" if pvals else "")})
            elif out is not None:
                extractor = {"status": "unparsed", "raw": json.dumps(out, ensure_ascii=False)[:600]}
            else:
                extractor = {"status": "error"}
        else:
            self.skip("document extractor", "EVOLUS_EXTRACTOR_AGENT_ID / EVOLUS_EXTRACTOR_ID not set")

        # 3. decision: the paper decides
        if primary is None:
            decision, why = "routed", "no primary read"
        elif not primary["accepted"]:
            decision, why = "routed", primary["line"]
        elif extractor.get("status") == "ok" and extractor["accepted"] and extractor["disagree"]:
            decision = "routed"
            why = ("two readings both pass every identity but differ on "
                   + ", ".join(d["name"] for d in extractor["disagree"][:4]) + ": a person decides")
        else:
            decision, why = "accepted", "every identity on the paper holds" + (
                "; the extractor's differing read fails the paper's arithmetic, so it is overruled"
                if extractor.get("status") == "ok" and extractor["disagree"] else "")

        rec: dict = {"case_id": uuid.uuid4().hex[:12], "clave": self.clave,
                     "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "process": "paper form intake (records office)", "schema": storemod.schema().get("name", "mx_presidencia_2024"),
                     "image": str(Path(page).resolve().relative_to(storemod.REPO.resolve())).replace("\\", "/"),
                     "primary": primary, "extractor": extractor, "decision": decision, "decision_reason": why}

        if decision == "accepted":
            rec["library"] = self.file_record(pvals, primary)
        else:
            fail = (primary or {}).get("failing") or [d["code"] for d in extractor.get("disagree", [])]
            rec["handoff"] = self.handoff(fail, why, pvals, extractor)
            rec["workflow"] = self.start_workflow(rec)
        rec["steps"] = self.steps
        rec["evolus_calls"] = self.c.calls[n0:]
        rec["amd_calls_via_evolus"] = self.amd_calls_via_evolus
        rec["workspace_url"] = self.s.workspace_url
        return redact(storemod.public(rec), self.s.secrets())

    # ----------------------------------------------------------------------------- accepted: file the record
    def file_record(self, pvals: dict, primary: dict) -> dict:
        if not self.s.library_id:
            self.skip("knowledge library", "EVOLUS_LIBRARY_ID not set")
            return {"status": "skipped"}
        lines = [f"Record {self.clave}", "Form type: tally sheet, type 2 (paper form intake)",
                 "Status: accepted with no human touch - every identity on the paper holds.",
                 f"Read by {PRIMARY_MODEL} on AMD; checked by the Two Hands gate.", ""]
        for c in codes():
            lines.append(f"{storemod.name_of(storemod.key_of(c))} ({c}): {pvals.get(c)}")
        doc = "\n".join(lines) + "\n"
        name = f"record_{self.clave}.txt"
        out = self.step("knowledge library", "POST /api/v1/memories/{libraryId}/documents",
                        lambda: self.c.upload_document(self.s.library_id, name, doc.encode("utf-8")),
                        lambda o: f"filed {name}")
        return {"status": "ok" if out is not None else "error", "document": name,
                "id": (out or {}).get("id") if isinstance(out, dict) else None}

    # ----------------------------------------------------------------------------- routed: hand to a person
    def handoff(self, fail: list[str], why: str, pvals: dict, extractor: dict) -> dict:
        names = [storemod.name_of(storemod.key_of(c)) for c in fail if storemod.key_of(c)]
        facts = {"form": self.clave, "why_routed": why, "fields_to_check": names[:6],
                 "model_read": {n: pvals.get(c) for n, c in zip(names, fail)},
                 "extractor_read": {n: (extractor.get("read") or {}).get(c) for n, c in zip(names, fail)}
                 if extractor.get("status") == "ok" else None}
        note_en = ""
        model = self.s.agent
        if not model:
            ms = self.step("agent chat", "GET /v1/models", self.c.models, lambda o: f"{len(o)} agent(s)")
            model = (ms or [{}])[0].get("id", "") if ms else ""
        if model:
            msgs = [{"role": "user", "content":
                     "You prepare review tasks in a records office that captures paper forms. A form could not be "
                     "accepted automatically. Write a note of at most two sentences for the clerk: which field(s) to "
                     "look at on the page and why. Do not guess the correct value. Facts (JSON): "
                     + json.dumps(facts, ensure_ascii=False)}]
            out = self.step("agent chat (Gemma-4-31B-IT on AMD)", "POST /v1/chat/completions",
                            lambda: self.c.chat(model, msgs), lambda o: (o or {}).get("text", "")[:120])
            self.amd_calls_via_evolus += 1
            note_en = storemod.neutralize(((out or {}).get("text") or "").strip())
        else:
            self.skip("agent chat (Gemma-4-31B-IT on AMD)", "no agent in the workspace (GET /v1/models is empty)")
        if not note_en:
            note_en = f"Check {', '.join(names[:3]) or 'the rows'} on the page: {why}."
        note_es = ""
        if self.s.app_id:
            cat = self.step("AI Tools catalog", "GET /api/v1/ai-tools", self.c.ai_tools, lambda o: "catalog read")
            opts = translate_options(cat)
            out = self.step("AI Tool: translate", "POST /api/v1/ai-tools/{tool}/run",
                            lambda: self.c.run_tool("translate", note_en, options=opts),
                            lambda o: text_of(o)[:120])
            note_es = storemod.neutralize(text_of(out).strip()) if out is not None else ""
        else:
            self.skip("AI Tool: translate", "EVOLUS_APP_ID not set")
        return {"fields": names, "note_en": note_en, "note_es": note_es, "crop_urls": self.crop_urls(fail)}

    def start_workflow(self, rec: dict) -> dict:
        if not self.s.workflow_id:
            self.skip("workflow: review hand-off", "EVOLUS_WORKFLOW_ID not set")
            return {"status": "skipped"}
        h = rec["handoff"]
        task = {"case_id": rec["case_id"], "form": self.clave, "why_routed": rec["decision_reason"],
                "fields_to_check": h["fields"], "note_en": h["note_en"], "note_es": h["note_es"],
                "crop_urls": h["crop_urls"], "assign_to": "records office reviewer"}
        cb = f"{self.s.public_url}/api/evolus/callback" if self.s.public_url and self.s.callback_key else None
        out = self.step("workflow: review hand-off", "POST /api/v1/workflows/{workflowId}/execute",
                        lambda: self.c.execute_workflow(self.s.workflow_id, json.dumps(task, ensure_ascii=False),
                                                        parameters={"form": self.clave, "case_id": rec["case_id"]},
                                                        callback_url=cb, callback_key=self.s.callback_key or None),
                        lambda o: f"execution {(o or {}).get('executionId')}")
        eid = (out or {}).get("executionId") if isinstance(out, dict) else None
        if not eid:
            return {"status": "error" if out is None else "no execution id"}
        status, result, waited = "Pending", None, 0.0
        while waited < self.poll_s:
            self.sleep(self.poll_every)
            waited += self.poll_every
            st = self.step("workflow: status", "GET /api/v1/workflows/{workflowId}/executions/{executionId}",
                           lambda: self.c.workflow_status(self.s.workflow_id, eid),
                           lambda o: str((o or {}).get("status")))
            if st is None:
                break
            status = str(st.get("status") or status)
            if status.lower() in FINAL:
                result = text_of({k: v for k, v in st.items() if k not in ("status", "executionId")})[:800]
                break
        # collapse the repeated status polls into the last one
        polls = [s for s in self.steps if s["block"] == "workflow: status"]
        if len(polls) > 1:
            last = polls[-1] | {"summary": f"{polls[-1]['summary']} after {len(polls)} polls"}
            self.steps = [s for s in self.steps if s["block"] != "workflow: status"] + [last]
        return {"status": status, "execution_id": eid, "result": result}


# ------------------------------------------------------------------------------------------- records
def save(rec: dict, path: Path = RUNS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(redact(rec), ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_cases() -> dict:
    """Latest case per form from results/evolus_runs.jsonl and app/state/evolus_runs.jsonl, plus callbacks."""
    out: dict = {}
    for p in (RUNS_FILE, STATE_RUNS):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("clave") and row.get("case_id"):
                if row["clave"] not in out or row.get("at", "") >= out[row["clave"]].get("at", ""):
                    out[row["clave"]] = row
    try:
        for line in CALLBACKS.read_text(encoding="utf-8").splitlines():
            cb = json.loads(line)
            for row in out.values():
                wf = row.get("workflow") or {}
                if wf.get("execution_id") and wf["execution_id"] == cb.get("executionId"):
                    wf["status"] = cb.get("status") or wf.get("status")
                    wf["callback_at"] = cb.get("at")
    except (OSError, ValueError):
        pass
    return out
