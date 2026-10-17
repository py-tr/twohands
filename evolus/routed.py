"""Routed fields as Evolus "Audit finding" cases: every case is a field the paper's own arithmetic refused in a real
read, sent with its masked crop and the task for the clerk. Nothing is synthetic.

Sources (read only, last row per form):
  r300    results/calls_gemma.jsonl            the pre-registered random 300 (Gemma-4-31B-IT on the AMD Token Factory);
                                               "keyed" is the official first capture of that form
                                               (app/data/audit_sample_prep300.csv), as in the sample audit
  colima  results/colima/calls_gemma.jsonl     the Colima complete-state read (Amendment 8b); no capture is attached
                                               (nothing is compared with the official count here: that is scored
                                               elsewhere), so "keyed" is empty
One case per routed form: the first field the gate refused (digits vs words, an unread box, a row label), or, when only
an identity failed, the field on the right of the smallest failing identity. Forms are taken in the order of
sha256(case id), so a capped run is spread over the sample instead of the first districts.

The crop is the app's masked-crop pipeline (app/crops.py on data/masked/**, pad 0.02, no row label); the case carries
its link (/crop/<form>/<code>.jpg) and the sha256 of its bytes. A form without a masked page is never sent.

Ledger: results/evolus/executions.jsonl (append only). A case id with an execution id in it is never sent again; a
run started earlier and not yet returned is polled, not re-sent. Pacing: one start per --interval seconds (default
25), at most --in-flight runs open, a shared-limiter token before each start (each run = 1 AMD call, the AgentCall),
and the Evolus REST limit (60 requests/min per application, docs/evolus-openapi.json) is never approached.
Three HTTP errors in a row stop the run.

    python -m evolus routed --plan r300:100,colima:50 [--after-pid N] [--dry-run]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from app import capture_audit as ca
from app import store as storemod
from evolus.client import EvolusClient, EvolusError, NotConfigured
from evolus.config import load_ids, redact

WORKFLOW = "Audit finding"
LEDGER = storemod.RESULTS / "evolus" / "executions.jsonl"
SOURCES = {
    "r300": (storemod.RESULTS / "calls_gemma.jsonl", "the pre-registered random 300-form run"),
    "colima": (storemod.RESULTS / "colima" / "calls_gemma.jsonl", "the Colima complete-state read (Amendment 8b)"),
}
READER = "Gemma-4-31B-IT on the AMD Token Factory"
FINAL = {"completed", "failed", "succeeded", "cancelled", "canceled", "error"}
CROP_PAD = 0.02
BANNED = re.compile(r"fraud", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rows(path: Path) -> dict[str, dict]:
    out: dict = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for ln in text.splitlines():
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("clave"):
            out[r["clave"]] = r
    return out


def _capture300() -> dict[str, dict]:
    """{form: {key: (value, kind)}} from the official first capture of the 300 (the sample audit's keyed file)."""
    headers, rows = ca.parse_csv(ca.SAMPLE_CSV.read_text(encoding="utf-8"))
    m = ca.automap(headers)
    out: dict = {}
    for row in rows:
        fid = (row[m["id"]] if len(row) > m["id"] else "").strip().strip("'")
        vals = {}
        for code, col in m["fields"].items():
            if col is not None:
                vals[storemod.key_of(code)] = ca.keyed_value(row[col] if col < len(row) else "")
        out[fid] = vals
    return out


def refused(ev: dict) -> list[tuple[str, str]]:
    """[(schema key, why)] the gate refused on this read, arithmetic first: digits that disagree with the words, then
    the field on the right of the smallest identity that does not hold, then boxes not read, then row labels."""
    out = [(f["key"], f"its digits ({f['n']}) and its words ({f['w']}) disagree") for f in ev["fields"] if f["status"] == "words"]
    bad = sorted((i for i in ev["identities"] if i["ok"] is False), key=lambda i: len(i["keys"]))
    for i in bad[:1]:
        nm = ca.IDENT_NAMES.get(i["name"], i["name"])
        out.append((i["keys"][-1], f"the paper's identity {nm} does not hold on this read ({i['lhs']} vs {i['rhs']})"))
    out += [(f["key"], "its digit boxes were not read (blank or faint)") for f in ev["fields"] if f["status"] == "empty"]
    out += [(f["key"], "the printed row label read there is not the one expected for this row")
            for f in ev["fields"] if f["status"] == "label"]
    return out


def crop_sha(clave: str, key: str) -> Optional[str]:
    """sha256 of the masked crop the app serves at /crop/<form>/<code>.jpg?pad=0.02&label=0; None: no masked page."""
    from app import crops
    page = storemod.get_store().masked_image(clave)
    if page is None or storemod.MASKED not in Path(page).resolve().parents:
        return None
    try:
        return hashlib.sha256(crops.crop_bytes(str(page), page.stat().st_mtime, key, CROP_PAD, False)).hexdigest()
    except (KeyError, OSError):
        return None


def build(source: str, row: dict, keyed: Optional[dict]) -> Optional[dict]:
    """The 'Audit finding' input for the first refused field of one routed read (the keys of evolus.audit.case_input,
    plus why it was routed and the task for the clerk). None when the form is not routed or has no masked page."""
    if not row.get("routed") or row.get("no_call") or row.get("error") or not row.get("parsed_ok"):
        return None
    clave = row["clave"]
    r = storemod.read_from_core(clave, f"{source}_calls_gemma", row)
    ev = storemod.evaluate(r)
    if ev["accepted"]:
        return None
    got = refused(ev)
    if not got:
        return None
    k, why = got[0]
    code = storemod.code_of(k)
    sha = crop_sha(clave, k)
    if sha is None:
        return None
    view = ca.View(r.values, r.words, False, f"{source} read", None)
    kv, kind = (keyed or {}).get(k, (None, "not in the capture")) if keyed is not None else (None, "not keyed yet")
    idents, breaks, supports = [], [], []
    for name, lhs, rhs in ca._idents():
        if k not in lhs and k not in rhs:
            continue
        nm = ca.IDENT_NAMES.get(name, name)
        mod = ca._check(view.values, lhs, rhs)
        kd = ca._check({**view.values, k: kv}, lhs, rhs) if kv is not None else None
        idents.append({"name": nm, "model_lhs": mod[0] if mod else None, "model_rhs": mod[1] if mod else None,
                       "keyed_lhs": kd[0] if kd else None, "keyed_rhs": kd[1] if kd else None})
        if mod and mod[0] == mod[1]:
            supports.append(nm)
            if kd and kd[0] != kd[1]:
                breaks.append(nm)
    e = ca.evidence(k, kv, kind, view)
    name = storemod.name_of(k)
    crop = f"/crop/{clave}/{code}.jpg?pad={CROP_PAD}&label=0"
    task = (f"Look at {name} on the paper (crop {crop}) and key the value the paper shows. The form was routed because "
            f"{name} failed: {storemod.neutralize(why)}. Do not take the model's value without reading the paper.")
    out = {"case_id": f"{source}-{clave}-{code}", "form": clave, "field": name, "code": code,
           "source": SOURCES[source][1], "reader": READER, "why_routed": storemod.neutralize(ev["line"]),
           "field_check": storemod.neutralize(why), "task_for_clerk": task,
           "keyed": kv, "keyed_n": kv, "keyed_kind": kind if kv is None else "number",
           "model_digits": r.values.get(k), "model_words": r.words.get(k), "model_read_passes_gate": False,
           "identities": idents, "breaks": breaks, "supports": supports, "crop_url": crop, "crop_sha256": sha,
           "evidence_tier": e["tier"], "app_score": e["score"]}
    return storemod.public(out)


def safe(inp: dict) -> Optional[str]:
    """Why this input must not be sent (a party name, a schema row id, the banned word), or None."""
    txt = json.dumps(inp, ensure_ascii=False)
    if BANNED.search(txt):
        return "contains a banned word"
    s = storemod.schema()
    words = {a for names in s.get("party_aliases", {}).values() for a in names} | set(s.get("party_aliases", {}))
    words |= {k for k in s["keys"] if k not in storemod.PLAIN_NAMES}
    for w in sorted(words, key=len, reverse=True):
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(w)}(?![A-Za-z0-9])", txt, flags=re.I):
            return "contains a party name or row id"
    if "data/masked" in txt or ".jpg\"" in txt and "/crop/" not in txt:
        return "contains an image path"
    return None


def earlier_fields() -> set[tuple[str, str]]:
    """(form, code) of the fields already sent as audit cases (results/evolus_audit_runs.jsonl): not sent again."""
    from evolus import audit as auditmod
    return {(r.get("form"), r.get("code")) for r in auditmod.saved_runs()}


def candidates(source: str) -> list[dict]:
    path = SOURCES[source][0]
    keyed = _capture300() if source == "r300" else None
    skip = earlier_fields()
    out = []
    for clave, row in _rows(path).items():
        inp = build(source, row, (keyed or {}).get(clave, {}) if keyed is not None else None)
        if inp is not None and (inp["form"], inp["code"]) not in skip and safe(inp) is None:
            out.append(inp)
    out.sort(key=lambda x: hashlib.sha256(x["case_id"].encode()).hexdigest())
    return out


# ------------------------------------------------------------------------------------------- ledger
def ledger(path: Optional[Path] = None) -> list[dict]:
    try:
        lines = Path(path or LEDGER).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def append(row: dict, path: Optional[Path] = None) -> None:
    p = Path(path or LEDGER)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(redact(storemod.public(row)), ensure_ascii=False) + "\n")


def cases(path: Optional[Path] = None) -> dict[str, dict]:
    """The latest state per case id (rows merged in order)."""
    out: dict = {}
    for r in ledger(path):
        cid = r.get("case_id")
        if cid:
            out[cid] = {**out.get(cid, {}), **{k: v for k, v in r.items() if v is not None}}
    return out


def summary(path: Optional[Path] = None) -> dict:
    """What the ledger shows: executions sent, completed with a drafted finding, failed, still open."""
    cs = [c for c in cases(path).values() if c.get("execution_id")]
    st = lambda c: str(c.get("status") or "").lower()  # noqa: E731
    ok = [c for c in cs if st(c) in ("completed", "succeeded") and c.get("finding")]
    failed = [c for c in cs if st(c) in FINAL and c not in ok]
    models = sorted({str(c.get("model_reported")) for c in cs if c.get("model_reported")})
    ids = load_ids()
    by = {s: sum(1 for c in cs if c.get("source_id") == s) for s in SOURCES}
    agree = sum(1 for c in ok if (c.get("evidence") or {}).get("agrees_with_app") is True)
    times = sorted(c.get("started_at") for c in cs if c.get("started_at"))
    rate = round(100.0 * len(ok) / len(cs), 1) if cs else 0.0
    d = {"workspace": str(ids.get("workspace_name") or "py_tr"), "workflow": WORKFLOW, "sent": len(cs),
         "succeeded": len(ok), "failed": len(failed), "open": len(cs) - len(ok) - len(failed), "success_pct": rate,
         "by_source": by, "models_reported": models, "score_agrees": agree,
         "window": [times[0][:16] if times else None, times[-1][:16] if times else None],
         "http_errors": sum(1 for r in ledger(path) if r.get("event") == "error")}
    d["line"] = (f"Evolus workspace {d['workspace']}: {d['sent']} \"{WORKFLOW}\" executions of real routed fields "
                 f"({by['r300']} from the 300 run, {by['colima']} from Colima), {d['succeeded']} completed with a drafted "
                 f"finding ({rate:g}%), {d['failed']} failed, {d['open']} still open; model reported by Evolus: "
                 f"{', '.join(models) or 'none'}. Source: results/evolus/executions.jsonl.")
    return d


# ------------------------------------------------------------------------------------------- the runner
def pid_alive(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class Runner:
    def __init__(self, client: EvolusClient, interval: float = 25.0, in_flight: int = 4, poll_every: float = 20.0,
                 timeout_s: float = 2400.0, limiter=None, sleep: Callable[[float], None] = time.sleep,
                 log: Callable[[str], None] = print, path: Optional[Path] = None):
        self.c, self.s = client, client.s
        self.interval, self.in_flight, self.poll_every, self.timeout_s = interval, max(1, in_flight), poll_every, timeout_s
        self.limiter, self.sleep, self.log, self.path = limiter, sleep, log, path
        self.err_streak = 0
        self.stopped: Optional[str] = None
        self.model_reported: Optional[str] = None

    def _err(self, e: Exception) -> None:
        self.err_streak += 1
        if isinstance(e, EvolusError) and e.status == 429:
            self.sleep(60.0)
        if self.err_streak >= 3:
            self.stopped = f"3 HTTP errors in a row (last: {redact(str(e), self.s.secrets())[:160]})"

    def agent_model(self) -> Optional[str]:
        """The Intake clerk's model as Evolus reports it (GET /api/v1/agents/{agentId}: modelKey, modelState)."""
        aid = load_ids().get("agent_id")
        try:
            a = self.c.rest("GET", f"/api/v1/agents/{aid}", "GET /api/v1/agents/{agentId}")
            self.err_streak = 0
        except (EvolusError, NotConfigured) as e:
            self._err(e)
            return None
        mk = (a or {}).get("modelKey") or (a or {}).get("modelDisplayName")
        state = (a or {}).get("modelState")
        return f"{mk} ({state})" if mk and state else mk

    def start(self, inp: dict, source: str) -> dict:
        from evolus import audit as auditmod
        if self.limiter is None:
            from twohands.ratelimit import shared
            self.limiter = shared()
        waited = self.limiter.acquire()
        row = {"event": "sent", "case_id": inp["case_id"], "source_id": source, "form": inp["form"],
               "field": inp["field"], "code": inp["code"], "workflow": WORKFLOW, "workflow_id": self.s.audit_workflow_id,
               "started_at": _now(), "model_reported": self.model_reported,
               "model_configured": str(load_ids().get("model_key") or "").split("/", 1)[-1],
               "crop_url": inp["crop_url"], "crop_sha256": inp["crop_sha256"], "why_routed": inp["why_routed"],
               "task_for_clerk": inp["task_for_clerk"], "evidence_tier_sent": inp["evidence_tier"],
               "app_score": inp["app_score"], "paced_wait_s": round(waited, 1),
               "input_sha256": hashlib.sha256(json.dumps(inp, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
        try:
            r = self.c.execute_workflow(self.s.audit_workflow_id, json.dumps(inp, ensure_ascii=False),
                                        parameters=auditmod.parameters(inp))
            row["execution_id"] = (r or {}).get("executionId")
            row["status"] = "Pending"
            row["http"] = 200
            self.err_streak = 0
        except (EvolusError, NotConfigured) as e:
            row.update(event="error", status="not sent", http=getattr(e, "status", None),
                       error=redact(str(e), self.s.secrets())[:300])
            self._err(e)
        if row.get("event") == "sent" and not row.get("execution_id"):
            row.update(event="error", status="no execution id")
        append(row, self.path)
        self.log(f"{row['started_at']} {inp['case_id']}: {row.get('status')} {row.get('execution_id') or row.get('error', '')}")
        return row

    def poll(self, c: dict) -> dict:
        try:
            st = self.c.workflow_status(self.s.audit_workflow_id, c["execution_id"])
            self.err_streak = 0
        except (EvolusError, NotConfigured) as e:
            self._err(e)
            return c
        status = str((st or {}).get("status") or c.get("status"))
        if status.lower() not in FINAL:
            c["status"] = status
            return c
        raw = (st or {}).get("output")
        try:
            out = json.loads(raw) if isinstance(raw, str) and raw.strip()[:1] == "{" else raw
        except ValueError:
            out = raw
        row = {"event": "returned", "case_id": c["case_id"], "execution_id": c["execution_id"], "status": status,
               "returned_at": _now(), "model_reported": self.model_reported}
        if isinstance(out, dict):
            row["finding"] = storemod.neutralize(str(out.get("finding") or "").strip())
            ev = out.get("evidence") or {}
            row["evidence"] = {k: ev.get(k) for k in ("score", "tier", "agrees_with_app", "computed_by")} if isinstance(ev, dict) else None
            row["returned_status"] = out.get("status")
        for k in ("model", "modelKey", "modelName"):
            if (st or {}).get(k):
                row["model_in_execution"] = str(st[k])
        if (st or {}).get("error"):
            row["error"] = str(st["error"])[:300]
        states = (st or {}).get("stepStates") or {}
        if isinstance(states, dict):
            row["steps"] = [{"status": (v or {}).get("status"), "ms": (v or {}).get("durationMs")} for v in states.values()]
        append(row, self.path)
        self.log(f"{row['returned_at']} {c['case_id']}: {status}: {(row.get('finding') or row.get('error') or '')[:90]}")
        return {**c, **row}

    def run(self, plan: list[tuple[str, int]], cap: int) -> dict:
        if not self.s.audit_workflow_id:
            raise NotConfigured("no 'Audit finding' workflow id (run python -m evolus setup)")
        have = cases(self.path)
        sent_ids = {cid for cid, c in have.items() if c.get("execution_id")}
        queue: list[tuple[str, dict]] = []
        for src, n in plan:
            todo = [x for x in candidates(src) if x["case_id"] not in sent_ids]
            already = sum(1 for c in have.values() if c.get("source_id") == src and c.get("execution_id"))
            queue += [(src, x) for x in todo[: max(0, n - already)]]
        queue = queue[:cap]
        self.model_reported = self.agent_model()
        self.log(f"model reported by Evolus for the Intake clerk: {self.model_reported}; {len(queue)} cases to send")
        open_ = [c for c in have.values() if c.get("execution_id") and str(c.get("status", "")).lower() not in FINAL]
        sent = 0
        last_start = 0.0
        last_poll: dict = {}
        while (queue or open_) and not self.stopped:
            now = time.monotonic()
            if queue and len(open_) < self.in_flight and now - last_start >= self.interval:
                src, inp = queue.pop(0)
                last_start = time.monotonic()
                row = self.start(inp, src)
                sent += 1
                if row.get("execution_id"):
                    open_.append({**row, "_t0": time.monotonic()})
                continue
            for c in list(open_):
                if self.stopped:
                    break
                if time.monotonic() - last_poll.get(c["case_id"], 0.0) < self.poll_every:
                    continue
                last_poll[c["case_id"]] = time.monotonic()
                c2 = self.poll(c)
                done = str(c2.get("status", "")).lower() in FINAL
                if not done and time.monotonic() - c.get("_t0", time.monotonic()) > self.timeout_s:
                    append({"event": "timeout", "case_id": c["case_id"], "execution_id": c["execution_id"],
                            "status": "timeout", "note": f"still {c2.get('status')} after {int(self.timeout_s)} s; "
                            "a later call polls it again, never re-sends it", "at": _now()}, self.path)
                    done = True
                open_ = [x for x in open_ if x["case_id"] != c["case_id"]] + ([] if done else [{**c2, "_t0": c.get("_t0", time.monotonic())}])
            self.sleep(2.0)
        if self.stopped:
            append({"event": "stopped", "at": _now(), "reason": self.stopped}, self.path)
            self.log("STOPPED: " + self.stopped)
        return {"started": sent, "stopped": self.stopped, "left_open": len(open_), "calls": len(self.c.calls)}


def main(a) -> int:
    plan = []
    for part in a.plan.split(","):
        src, _, n = part.partition(":")
        if src not in SOURCES:
            print(f"unknown source {src}; one of {list(SOURCES)}")
            return 2
        plan.append((src, int(n or 0)))
    if a.dry_run:
        have = cases()
        for src, n in plan:
            cs = candidates(src)
            new = [x for x in cs if x["case_id"] not in have]
            print(f"{src}: {len(cs)} routed cases with a masked crop, {len(new)} not yet sent; plan {n}")
            for x in new[:2]:
                print(json.dumps(x, ensure_ascii=False)[:900])
        return 0
    if a.after_pid:
        waited = 0
        while pid_alive(a.after_pid):
            if waited >= a.wait_max:
                print(f"pid {a.after_pid} still running after {waited} s: nothing sent")
                return 3
            print(f"{_now()} pid {a.after_pid} alive; waiting 600 s (AMD calls only after it ends)", flush=True)
            time.sleep(600)
            waited += 600
    res = Runner(EvolusClient(), interval=a.interval, in_flight=a.in_flight).run(plan, a.cap)
    print(json.dumps(res))
    print(summary()["line"])
    return 1 if res["stopped"] else 0
