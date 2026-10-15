"""Inbox: the screen a records office runs its day from. Every form, its status, why, and what it cost;
plus the export of captured records (CSV / JSON). Field names are neutral ("Option 01", never a party).

Status of a form (first match):
  resolved / escalated   a person settled it on the review desk (app/state/review.json)
  accepted               every identity on the page holds: 0 fields to key
  paper inconsistency    routed, and every field was read right (graded against the official capture): the paper
                         itself disagrees with itself, which is a correct routing
  routed                 waiting on the review desk with the failing field named (or the page could not be located,
                         or the model call failed)
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Optional

from app import review as reviewmod
from app import store as storemod

STATES = ["Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Coahuila", "Colima", "Chiapas",
          "Chihuahua", "Ciudad de México", "Durango", "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "México",
          "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo",
          "San Luis Potosí", "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán",
          "Zacatecas"]
STATUSES = [("accepted", "Accepted", "ok"), ("routed", "Routed", "warn"), ("resolved", "Resolved", "accent"),
            ("escalated", "Escalated", "bad"), ("paper", "Paper inconsistency", "violet")]


def state_name(clave: str) -> str:
    try:
        return STATES[int(clave[:2]) - 1]
    except (ValueError, IndexError):
        return ""


def _capture(r: Optional[storemod.Read], off: dict) -> str:
    lay = (r.raw.get("layout") if r else None) or {"M": "movil", "E": "escaner"}.get(off.get("dig") or "")
    return {"movil": "phone photo", "escaner": "scanner"}.get(lay or "", "")


def _ts(x) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def rows(st: storemod.Store) -> list[dict]:
    reviews = reviewmod.load()
    out = []
    for k in st.ine_claves():
        r = st.default_read(k)
        off = st.official.get(k, {})
        if r is None:
            continue
        ev = storemod.evaluate(r)
        g = storemod.grade(r, off) if off else {"graded": False}
        rv = reviews.get(k)
        if rv and rv.get("status") in ("resolved", "escalated"):
            status = rv["status"]
        elif ev["accepted"]:
            status = "accepted"
        elif g.get("graded") and not g.get("wrong_adj") and not r.not_located and not r.error:
            status = "paper"
        else:
            status = "routed"
        if r.not_located:
            reason = "page not located; sent to a person before any model call"
        elif r.error:
            reason = "model call failed; the form waits for a re-read"
        elif ev["accepted"]:
            reason = "every identity holds"
        else:
            reason = storemod.neutralize("; ".join(ev["reasons"][:2]))
        out.append({"clave": k, "status": status, "accepted": ev["accepted"], "to_key": ev["to_key"],
                    "line": ev["line"], "reason": reason, "capture": _capture(r, off), "state": state_name(k),
                    "model": st.runs[r.run_id].get("model"), "run": r.run_id, "run_name": st.short_name(r.run_id),
                    "secs": r.secs, "cost": r.cost, "ts": r.raw.get("ts"), "has_image": st.masked_image(k) is not None,
                    "review_at": (rv or {}).get("at"), "_read": r, "_ev": ev, "_review": rv})
    out.sort(key=lambda x: (x["ts"] or "", x["clave"]), reverse=True)
    return out


ADJ = storemod.RESULTS / "adjudication" / "adjudication.jsonl"


def _adjudication() -> tuple[dict, bool, float]:
    """Per (clave, model_key): fields where the reader disagrees with PREP (PREP value present); whether any
    verdict has been entered yet; the file's time (reads made after it are not covered)."""
    out: dict = {}
    judged = False
    try:
        lines = ADJ.read_text(encoding="utf-8").splitlines()
        mtime = ADJ.stat().st_mtime
    except OSError:
        return {}, False, 0.0
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        judged = judged or bool(r.get("verdict"))
        d = out.setdefault((r.get("clave"), r.get("model_key")), {"wrong": 0, "no_prep": 0})
        d["no_prep" if r.get("prep") is None else "wrong"] += 1
    return out, judged, mtime


def agreement(st: storemod.Store, rs: list[dict]) -> dict:
    """Fields where the reader's digits equal the official double-keyed capture (PREP), before any eye check.
    Forms with PREP values in app/data/official.json are graded directly; forms of the pre-registered run are
    counted from results/adjudication (which lists every field that disagrees with PREP)."""
    adj, judged, mtime = _adjudication()
    n_csv = sum(1 for f in storemod.schema()["fields"] if f.get("csv"))
    compared = agree = 0
    for r in rs:
        rd: storemod.Read = r["_read"]
        if rd.not_located or rd.error:
            continue
        off = st.official.get(r["clave"])
        g = storemod.grade(rd, off) if off else {"graded": False}
        if g.get("graded"):
            compared += g["n"]
            agree += g["n"] - len(g["wrong_raw"])
            continue
        if not rd.run_id.startswith("calls_"):
            continue
        t = _ts(r["ts"])
        if t is None or t.timestamp() > mtime:
            continue  # read after the adjudication sheet was built: not yet compared
        d = adj.get((r["clave"], rd.run_id.split("_", 1)[1]), {"wrong": 0, "no_prep": 0})
        compared += n_csv - d["no_prep"]
        agree += n_csv - d["no_prep"] - d["wrong"]
    return {"compared": compared, "agree": agree, "rate": agree / compared if compared else None,
            "adjudicated": judged}


def kpis(rs: list[dict]) -> dict:
    n = len(rs)
    c = {s: sum(1 for r in rs if r["status"] == s) for s, _, _ in STATUSES}
    cost = sum(r["cost"] or 0 for r in rs)
    secs = [r["secs"] for r in rs if r["secs"]]
    # throughput: forms per minute while the reader was actually running (gaps over 10 min are pauses, not work)
    ts = sorted(t for t in (_ts(r["ts"]) for r in rs) if t)
    active = sum(min((b - a).total_seconds(), 600) for a, b in zip(ts, ts[1:]) if (b - a).total_seconds() <= 600)
    per_min = (len(ts) - 1) / (active / 60) if len(ts) > 2 and active > 0 else None
    last = ts[-1] if ts else None
    read_ok = [r for r in rs if not r["_read"].not_located and not r["_read"].error]
    fields_read = sum(sum(1 for v in r["_read"].values.values() if v is not None) for r in read_ok)
    routed = [r for r in rs if r["status"] in ("routed", "paper")]
    return {"n": n, **c, "touchless": c["accepted"] / n if n else None, "fields_read": fields_read,
            "forms_read": len(read_ok), "routed_forms": len(routed),
            "routed_fields": sum(r["to_key"] or 0 for r in routed if not r["_read"].error),
            "awaiting_reread": sum(1 for r in routed if r["_read"].error),
            "settled": c["accepted"] + c["resolved"], "open": c["routed"] + c["paper"],
            "cost": cost, "cost_n": sum(1 for r in rs if r["cost"]), "mean_secs": sum(secs) / len(secs) if secs else None,
            "per_min": per_min, "last": last.strftime("%Y-%m-%d %H:%M UTC") if last else None}


def record(r: dict) -> dict:
    """One captured record: the values the office would file (reviewer's typed values applied), neutral codes."""
    rd: storemod.Read = r["_read"]
    rv = r["_review"] or {}
    typed = {storemod.key_of(c): v for c, v in (rv.get("values") or {}).items() if storemod.key_of(c)}
    s = storemod.schema()
    values = {}
    for f in s["fields"]:
        k = f["key"]
        values[storemod.code_of(k)] = typed.get(k, rd.values.get(k)) if r["status"] in ("accepted", "resolved") else rd.values.get(k)
    return {"form_id": r["clave"], "status": r["status"], "fields_to_key": r["to_key"], "reason": r["reason"],
            "capture": r["capture"], "state": r["state"], "reader": r["model"], "read_at": r["ts"],
            "latency_s": r["secs"], "cost_usd": r["cost"], "reviewed_at": r["review_at"],
            "final": r["status"] in ("accepted", "resolved"), "values": values}


def export_json(rs: list[dict]) -> dict:
    s = storemod.schema()
    return storemod.public({
        "about": "Captured records from Two Hands. Vote rows are Option 01 to Option 15 in printed order (no party "
                 "names). 'final' records are accepted by the gate or resolved by a person; others are still open, "
                 "and their values are the model's unconfirmed read.",
        "fields": {storemod.code_of(f["key"]): storemod.name_of(f["key"]) for f in s["fields"]},
        "records": [record(r) for r in rs]})


def export_csv(rs: list[dict]) -> str:
    s = storemod.schema()
    codes = [storemod.code_of(f["key"]) for f in s["fields"]]
    names = [storemod.name_of(f["key"]) for f in s["fields"]]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    head = ["form_id", "status", "final", "fields_to_key", "capture", "state", "reader", "read_at", "latency_s",
            "cost_usd", "reason"]
    w.writerow(head + names)
    for r in rs:
        rec = record(r)
        w.writerow([rec[h] if rec[h] is not None else "" for h in head]
                   + ["" if rec["values"][c] is None else rec["values"][c] for c in codes])
    return storemod.neutralize(buf.getvalue())
