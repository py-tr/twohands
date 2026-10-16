"""The IEEBCS head-to-head on the site, placed by the pre-registered rule (PROTOCOL_IEEBCS.md sections 10 and 11).

    load()          results/ieebcs/score.json (written by scripts/ieebcs_score.py), or None: everything stays hidden
                    until that file exists
    tier(d)         "home" (strict match >= home_threshold), "buyer" (>= buyer_section_threshold) or "results", from
                    the machine-readable ```placement block of the protocol
    card(slot)      the texts for one slot, or None when the rule does not place the comparison there:
                      slot "home"     the Home card ("the buyer's own benchmark"), tier home only
                      slot "buyer"    the buyer section (Who pays), tiers home and buyer
                      slot "results"  the row on Results, every tier (below 80% with the reading of why)

The headline figure is always the strict-denominator per-field match (metric 5a: every numeric field of every sampled
acta; unlocated pages, special-station actas and null reads count as unmatched). Every slot carries the same footnote
on what differs. Every number comes from the score file; nothing is typed in.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from twohands import REPO

RESULT = REPO / "results" / "ieebcs" / "score.json"
PROTOCOL = REPO / "PROTOCOL_IEEBCS.md"
DETAILS = "results/ieebcs_head_to_head.md"
FOOTNOTE = ("Same images; reference and pipeline differ (their raw manual capture vs. the published values; election "
            "night vs. offline); their per-field output isn't published, so it can't be re-scored. Details on Results.")
SLOTS = {"home": ("home",), "buyer": ("home", "buyer"), "results": ("home", "buyer", "results")}


def placement(path: Optional[Path] = None) -> Optional[dict]:
    """The ```placement block of PROTOCOL_IEEBCS.md as a dict (thresholds as floats), or None."""
    try:
        t = (path or PROTOCOL).read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"```placement\s*\n(.*?)```", t, flags=re.S)
    if not m:
        return None
    out: dict = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = (s.strip() for s in line.split(":", 1))
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out if "home_threshold" in out and "buyer_section_threshold" in out else None


def load(path: Optional[Path] = None) -> Optional[dict]:
    """The score file, or None when it does not exist (yet) or holds no strict figure."""
    p = path or RESULT
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    a = d.get("a_raw") or {}
    return d if isinstance(a.get("pct"), (int, float)) and a.get("fields") else None


def strict_share(d: dict) -> float:
    """The strict per-field match as a share (0..1): metric 5a, a_raw.pct of scripts/ieebcs_score.py."""
    return d["a_raw"]["pct"] / 100.0


def tier(d: dict, P: Optional[dict] = None) -> Optional[str]:
    P = P or placement()
    if not P:
        return None
    s = strict_share(d)
    return "home" if s >= P["home_threshold"] else ("buyer" if s >= P["buyer_section_threshold"] else "results")


def _model_name(key: Optional[str]) -> str:
    try:
        from twohands.reader import MODELS
        return MODELS.get(key or "", key or "the model")
    except Exception:  # noqa: BLE001
        return key or "the model"


def _why(d: dict) -> str:
    """Below the buyer-section threshold: where the unmatched fields are, from the score file alone."""
    a = d["a_raw"]
    sec = a.get("second_fields_of_located_pages") or {}
    n, located, read = d.get("n_actas"), a.get("pages_located"), a.get("pages_read")
    unmatched = a["fields"] - a["matched"]
    on_located = (sec.get("fields") or 0) - (sec.get("matched") or 0)
    off_located = unmatched - on_located
    s = (f"Of the {unmatched:,} unmatched fields, {off_located:,} are on the {n - located} of {n} pages the locator "
         f"did not accept (counted unmatched by the strict rule) and {on_located:,} on the {located} located pages")
    if read is not None and located > read:
        s += f", {located - read} of which were not read or not parsed"
    return s + f". On the located pages the match is {sec.get('pct')}%."


def stack(d: dict) -> str:
    """The serving stack of the run, named from the served model ids in score.json: the AMD Token Factory serves
    "Gemma-4-31B-IT"; a self-hosted vLLM server on an MI300X serves the Hugging Face id ("google/gemma-4-31B-it")."""
    served = d.get("served_models") or [_model_name(d.get("model"))]
    names = []
    for m in served:
        names.append(f"self-hosted vLLM on MI300X, {m}" if "/" in str(m) else f"Token Factory, {m}")
    return "; ".join(dict.fromkeys(names))


def facts(d: dict) -> dict:
    a, th = d["a_raw"], d.get("theirs") or {}
    sec = a.get("second_fields_of_located_pages") or {}
    ci = a.get("wilson95") or [None, None]
    return {"ours_pct": a["pct"], "matched": a["matched"], "fields": a["fields"], "ci": ci,
            "located_pct": sec.get("pct"), "pages_located": a.get("pages_located"), "n_actas": d.get("n_actas"),
            "theirs_pct": th.get("pct"), "theirs_matched": th.get("matched"), "theirs_fields": th.get("fields"),
            "theirs_source": th.get("source"), "model_key": d.get("model"), "model": _model_name(d.get("model")),
            "stack": stack(d)}


def card(slot: str, d: Optional[dict] = None, P: Optional[dict] = None) -> Optional[dict]:
    """The texts for one slot ("home", "buyer", "results"), or None when hidden there."""
    d = d if d is not None else load()
    if d is None:
        return None
    P = P or placement()
    t = tier(d, P)
    if t is None or t not in SLOTS[slot]:
        return None
    f = facts(d)
    theirs = (f"Commercial cloud OCR as the first capture in the 2024 Baja California Sur PREP: "
              f"{f['theirs_matched']:,} of {f['theirs_fields']:,} fields matched the manual capture, "
              f"{f['theirs_pct']}% (IEEBCS final report, p. 19).")
    ours = (f"Open {f['model']} on AMD ({f['stack']}), on a pre-registered sample of {f['n_actas']} of the same state's published "
            f"actas, against the same published values: {f['ours_pct']}% of all fields "
            f"({f['matched']:,} of {f['fields']:,})")
    out = {"slot": slot, "tier": t, **f, "footnote": FOOTNOTE, "details": DETAILS,
           "threshold_pct": round(100 * P["home_threshold"]),
           "buyer_threshold_pct": round(100 * P["buyer_section_threshold"])}
    if slot == "home":
        out.update(eyebrow="The buyer's own benchmark", text=f"{theirs} {ours}.")
    elif slot == "buyer":
        out.update(eyebrow="On the buyer's own actas",
                   text=f"{theirs} {ours}; {f['located_pct']}% on the {f['pages_located']} pages the locator accepted.")
    else:
        line = (f"Strict per-field match {f['ours_pct']}% ({f['matched']:,} of {f['fields']:,} numeric fields on all "
                f"{f['n_actas']} actas, {f['stack']}; Wilson 95% {f['ci'][0]}-{f['ci'][1]}%); {f['located_pct']}% on "
                f"the {f['pages_located']} pages the locator accepted. Theirs: {f['theirs_pct']}% "
                f"({f['theirs_matched']:,} of {f['theirs_fields']:,}, {f['theirs_source']}).")
        why = None
        if t == "results":
            why = (f"Below the pre-registered {out['buyer_threshold_pct']}% placement threshold, so it is shown here "
                   f"only (PROTOCOL_IEEBCS.md section 10). {_why(d)}")
        out.update(eyebrow="Head-to-head on the buyer's own actas", text=line, why=why)
    return out
