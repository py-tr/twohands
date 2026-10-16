"""What a hostile judge would check on the first screen and on Findings, computed, never typed in.

  confirmation(H)   the 52 split by what confirms each: the certified count, a person (app/state/spotcheck.json,
                    the blind /check), or the AI adjudicator alone; "person check pending" until a person has checked
  gate_label(L)     the gate tiers in the regulation's words ("accepted at second capture"), from numbers.lines()
  strip_figures(ls)       the live strip: states complete, the current state's %, +N a day for the worker's daily budget
                    on AMD, total audited. Never a national fraction, never the queue size
  model_line()      which model measured, which reads live, and (only once results/bench_mi300x_*.json holds a
                    real run of Gemma) the self-hosted MI300X bench
  buyer_card()      the IEEBCS head-to-head card, only when its result file exists and clears the pre-registered
                    Home threshold (PROTOCOL_IEEBCS.md, the ```placement block); else None

A new small module so app/numbers.py stays as the bake-off left it; every figure comes from a results or state file.
"""
from __future__ import annotations

import glob
import json
import math
import re
from pathlib import Path
from typing import Optional

from twohands import REPO

TIER = "accepted at second capture"
REG_LINE = ("The PREP rules require a second capture and a comparison for every acta (numeral 33) and a cotejo. "
            "Two Hands does that second capture: it accepts what the paper's arithmetic confirms and sends the rest "
            "to a person, with the photo.")
NUMERAL_33 = ("https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/155635/"
              "CGex202311-03-ap-8-a.pdf")
IEEBCS_RESULT = REPO / "results" / "ieebcs_head_to_head.json"
IEEBCS_PROTOCOL = REPO / "PROTOCOL_IEEBCS.md"
RESULTS = REPO / "results"


# ------------------------------------------------------------------------------------------- (b) the 52, confirmed by what
def confirmation(H: dict, answers: Optional[dict] = None) -> Optional[dict]:
    """The capture errors of the pre-registered run, split by their strongest confirmation. A person's blind reading
    (app/state/spotcheck.json) counts only for the ones the certified count does not confirm; a person who read the
    paper differently is counted apart, never as a confirmation."""
    items = (H or {}).get("keying_list") or []
    if not items:
        return None
    from app import spotcheck
    answers = spotcheck.load() if answers is None else answers
    verdicts = spotcheck.load_verdicts()
    cert = [x for x in items if x.get("cert_agrees")]
    rest = [x for x in items if not x.get("cert_agrees")]
    person = disagree = 0
    for x in rest:
        k = f"{x['clave']}__{x['field']}"
        a = answers.get(k)
        if not a or k not in verdicts:
            continue
        if spotcheck.agrees(a, verdicts[k]):
            person += 1
        else:
            disagree += 1
    ai = len(rest) - person - disagree
    checked = person + disagree
    state = "pending" if checked == 0 else ("done" if checked == len(rest) else "in_progress")
    parts = [f"{len(cert)} confirmed by the certified count", f"{person} checked by a person"]
    if disagree:
        parts.append(f"{disagree} read differently by a person")
    parts.append(f"{ai} AI-adjudicated only")
    note = {"pending": "person check pending",
            "in_progress": f"person check in progress, {checked} of {len(rest)}", "done": None}[state]
    return {"total": len(items), "certified": len(cert), "person": person, "person_disagree": disagree, "ai_only": ai,
            "state": state, "note": note, "text": " · ".join(parts) + (f" ({note})" if note else "")}


# ------------------------------------------------------------------------------------------- (a) tiers in the rule's words
def gate_label(L: dict) -> str:
    """numbers.lines()'s gate sentence with the tier named as the regulation names the step."""
    s = ((L or {}).get("gate") or {}).get("label") or ""
    return s.replace("of forms with no person", f"of forms {TIER}").replace("no person", TIER)


# ------------------------------------------------------------------------------------------- (d) the live counter
def _worker_rows() -> list[dict]:
    try:
        from app import live_audit
        from twohands import worker as W
        return [r for r in live_audit._rows(W.Paths(live_audit.worker_dir())) if r.get("status") == "audited"]
    except Exception:  # noqa: BLE001 - the strip must never break Home
        return []


def per_day(rows: Optional[list[dict]] = None) -> Optional[dict]:
    """Forms a day the live worker can audit inside its daily AMD budget: the budget over the measured mean cost per
    form, capped by its concurrency over the measured mean latency. None until the worker has audited a form."""
    from twohands import worker as W
    rows = _worker_rows() if rows is None else rows
    cost = [r["cost_usd"] for r in rows if r.get("cost_usd")]
    secs = [r["latency_s"] for r in rows if r.get("latency_s")]
    if not cost:
        return None
    mc = sum(cost) / len(cost)
    by_budget = math.floor(W.DAILY_USD / mc)
    by_time = math.floor(W.CONCURRENCY * 86400 / (sum(secs) / len(secs))) if secs else None
    n = min(by_budget, by_time) if by_time else by_budget
    return {"n": n, "budget_usd": W.DAILY_USD, "budget_text": f"${W.DAILY_USD:.2f}", "mean_cost": mc,
            "mean_secs": (sum(secs) / len(secs)) if secs else None, "reads": len(cost),
            "bound": "budget" if n == by_budget else "time",
            "why": (f"{W.DAILY_USD:.2f} USD a day over the measured mean of {mc:.6f} USD per form ({len(cost)} live "
                    f"reads) = {by_budget:,}" + (f"; {W.CONCURRENCY} in flight at the measured {sum(secs) / len(secs):.0f} s "
                                                 f"per form = {by_time:,}; the smaller is shown" if by_time else ""))}


def strip_figures(ls: dict, summary: Optional[dict] = None) -> dict:
    """The strip's four figures. states_complete and the current state come from the worker's own summary; the
    total is every form read on AMD (live_status). Nothing here is a share of the country or of the queue."""
    if summary is None:
        from app import live_status
        summary = live_status._summary()   # never raises; None when the worker has written nothing
    live = bool(ls.get("live")) and bool(summary and summary.get("audited"))
    states = ((summary or {}).get("states") or []) if live else []
    cur = next((s for s in states if not s.get("complete")), None)
    return {"live": live, "states_complete": sum(1 for s in states if s.get("complete")) if live else None,
            "current": {"name": cur["name"], "pct": cur["pct"]} if cur else None,
            "per_day": per_day() if live else None, "total": ls.get("forms_audited")}


# ------------------------------------------------------------------------------------------- (c) the model line
def bench_ran() -> Optional[dict]:
    """The newest results/bench_mi300x_*.json that is a real run of Gemma (at least one request answered)."""
    for p in sorted(glob.glob(str(RESULTS / "bench_mi300x_*.json")), reverse=True):
        try:
            d = json.loads(Path(p).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        model = str((d.get("meta") or {}).get("model") or "")
        if "gemma" in model.lower() and any((lv or {}).get("ok") for lv in d.get("levels") or []):
            return {"file": Path(p).name, "model": model}
    return None


def model_line() -> str:
    from app import livemodel
    from twohands.reader import MODELS
    m = re.match(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}:\d{2}) UTC", livemodel.WITHDRAWN_SINCE)
    month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(m.group(2)) - 1]
    when = f"{month} {int(m.group(3))}, {m.group(4)} UTC"
    g, q = MODELS[livemodel.PRIMARY], MODELS[livemodel.FALLBACK]
    s = (f"Measured on {g} on the AMD Token Factory; live reads use {q} there since the organisers withdrew Gemma "
         f"({when})")
    if bench_ran():
        s += "; benchmarked on self-hosted Gemma on an AMD Instinct MI300X"
    return s + "."


# ------------------------------------------------------------------------------------------- (d) the buyer card slot
def placement() -> Optional[dict]:
    """The machine-readable ```placement block of PROTOCOL_IEEBCS.md, or None when there is none."""
    try:
        t = IEEBCS_PROTOCOL.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"```placement\s*\n(.*?)```", t, flags=re.S)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip()
            try:
                out[k.strip()] = float(v)
            except ValueError:
                out[k.strip()] = v
    return out if "home_threshold" in out else None


def buyer_card() -> Optional[dict]:
    """The IEEBCS head-to-head on Home: only when results/ieebcs_head_to_head.json exists and its strict per-field
    match (metric 5a, the a_raw block of scripts/ieebcs_score.py) reaches the pre-registered home_threshold."""
    P = placement()
    if not P or not IEEBCS_RESULT.is_file():
        return None
    try:
        d = json.loads(IEEBCS_RESULT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    a = d.get("a_raw") or {}
    pct = d.get(str(P.get("metric", ""))) if isinstance(d.get(str(P.get("metric", ""))), (int, float)) else a.get("pct")
    if pct is None:
        return None
    share = pct / 100 if pct > 1 else pct
    if share < P["home_threshold"]:
        return None
    th = d.get("theirs") or {}
    return {"ours_pct": round(100 * share, 1), "theirs_pct": th.get("pct"), "n_actas": d.get("n_actas"),
            "matched": a.get("matched"), "fields": a.get("fields"), "model": d.get("model"),
            "threshold_pct": round(100 * P["home_threshold"])}
