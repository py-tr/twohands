"""The pre-registered 100-form confirmation (PROTOCOL Amendment 3; gate v3 per Amendment 7), in words, every number
computed from results/confirm100.json (scripts/confirm100_score.py, recomputed by make eval) and
results/posthoc_v2_300.json, and the person check of its disagreements from the blind /check?set=confirm100 queue
(answers in app/state/spotcheck_confirm100.json, apart from the main spot-check; a committed copy in
results/adjudication_confirm100/person_check.json, written by scripts/confirm100_score.py --sync-person and checked by its
--check, gives a checkout without app/state/ the same wording).

Until a person has answered every disagreement crop and agreed with the AI verdict on each, the wording says
"adjudicated from crops by the AI adjudicator (person check pending)"; once all agree it says "checked by a person".
Used by the Results and Home pages and by scripts/build_report.py (docs/REPORT.md).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from twohands import REPO

R = REPO / "results"
ADJ = R / "adjudication_confirm100"
PERSON = ADJ / "person_check.json"
V2, V1, V3 = "v2 (primary, Amendment 3)", "v1 (frozen gate, section 5)", "v3 (Amendment 7: words + two reads + stock band)"
AI_PHRASE = "adjudicated from crops by the AI adjudicator (person check pending)"
# The v2 rule that blocked the digit insertion, checked against twohands.gate_v2 on the stored read of 070212B0100:
# v1 accepted the form; v2's only failure there is code "unchecked" on SOBRANTES (digits 3114, words None).
V2_RULE = ('"a field in no identity needs its digits and words both read and equal" (Amendment 3, condition 2(a); '
           'here the words line was blank)')


def _jload(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_verdicts() -> dict:
    return _jload(ADJ / "verdicts.json", {}) or {}


def load_answers() -> dict:
    """The live /check?set=confirm100 answers, else the committed copy (a checkout without app/state/)."""
    from app import spotcheck
    return spotcheck.load("confirm100") or (_jload(PERSON, {}) or {}).get("answers") or {}


def person_copy_mismatch() -> list[str]:
    """With live answers on this machine, the committed copy must hold exactly them (else the wording would differ
    between this machine and a fresh clone)."""
    from app import spotcheck
    live = spotcheck.load("confirm100")
    if live and (_jload(PERSON, {}) or {}).get("answers") != live:
        return ["results/adjudication_confirm100/person_check.json (run scripts/confirm100_score.py --sync-person)"]
    return []


def sync_person() -> int:
    """Write the committed copy from the live answers; returns how many answers it holds."""
    from app import spotcheck
    live = spotcheck.load("confirm100")
    PERSON.write_text(json.dumps({"set": "/check?set=confirm100", "answers": live}, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return len(live)


def person_check(answers: Optional[dict] = None, verdicts: Optional[dict] = None) -> dict:
    """State of the person check of the confirmation's disagreement crops: pending / in_progress / disagree / done."""
    from app.spotcheck import agrees
    verdicts = load_verdicts() if verdicts is None else verdicts
    answers = load_answers() if answers is None else answers
    keys = sorted(verdicts)
    got = [k for k in keys if answers.get(k)]
    agree = [k for k in got if agrees(answers[k], verdicts[k])]
    n = len(keys)
    if n and len(got) == n and len(agree) == n:
        state, phrase = "done", "checked by a person"
    elif not got:
        state, phrase = "pending", AI_PHRASE
    elif len(agree) < len(got):
        state = "disagree"
        phrase = (f"adjudicated from crops by the AI adjudicator (a person read {len(got) - len(agree)} of {n} "
                  f"differently)")
    else:
        state, phrase = "in_progress", f"adjudicated from crops by the AI adjudicator (person check {len(got)} of {n})"
    return {"n": n, "answered": len(got), "agree": len(agree), "state": state, "phrase": phrase,
            "checked": state == "done"}


def pct2(x: float) -> str:
    return f"{100 * x:.2f}%"


def texts(answers: Optional[dict] = None) -> Optional[dict]:
    """Every sentence the site and the report say about the confirmation. None until it is scored."""
    d = _jload(R / "confirm100.json")
    ph = _jload(R / "posthoc_v2_300.json")
    if not d or not d.get("tiers") or not ph:
        return None
    m, T = d["meta"], d["tiers"]
    v2, v1, v3 = T[V2], T[V1], T[V3]
    p2 = ph["v2"]
    pc = person_check(answers)
    n_dis = m["verdicts"]
    upper = pct2(v2["ci"][1])
    pooled_f, pooled_e = p2["fields"] + v2["fields"], p2["errors"] + len(v2["errors"])
    adj = "adjudicated from crops and checked by a person" if pc["checked"] else pc["phrase"]
    # v1's accepted error that v2 blocked: "070212B0100 SOBRANTES: read 3114, PREP 314, paper 314"
    ins = None
    for e in v1["errors"]:
        mm = re.match(r"(\S+) SOBRANTES: read (\d+), PREP \d+, paper (\d+)", e)
        if mm and mm.group(1) not in v2["forms"]:
            ins = {"clave": mm.group(1), "read": int(mm.group(2)), "paper": int(mm.group(3))}
    # the blind-spot cases measured so far, each "<what> (<read> for <paper>)": the post-hoc 300's v1 errors (the one v2
    # keeps is the harmonised read; the one v2 drops had no words) and the fresh 100's digit insertion
    modes = []
    v2_300 = {e.split()[0] for e in p2.get("error_list", [])}
    for e in ph.get("v1 (frozen gate)", {}).get("error_list", []):
        mm = re.match(r"(\S+) SOBRANTES: model (\d+), PREP \d+, paper (\d+)", e)
        if mm:
            kind = "harmonised in one call" if mm.group(1) in v2_300 else "blank words"
            what = (f"{kind} ({mm.group(2)}/{mm.group(2)} for {mm.group(3)})" if mm.group(1) in v2_300
                    else f"{kind} ({mm.group(2)} for {mm.group(3)})")
            modes.append({"clave": mm.group(1), "kind": kind, "text": what})
    if ins:
        modes.append({"clave": ins["clave"], "kind": "digit insertion",
                      "text": f"digit insertion ({ins['read']} for {ins['paper']})"})
    wilson = (f"The pre-registered criterion was an error rate under 0.5%; the point estimate meets it, and the sample is "
              f"too small to exclude 0.5% at 95% confidence (Wilson upper bound {upper}).")
    para = (f"Confirmation on fresh data (Amendment 3, pre-registered before any read): {m['n']} forms drawn after the "
            f"fix was designed, Gemma on the AMD Token Factory. The fixed gate (v2) accepted {v2['forms_accepted']} "
            f"forms; {len(v2['errors'])} of their {v2['fields']:,} fields were wrong against the official capture, with "
            f"{n_dis} disagreements {adj}. {wilson} Evidence for v2 across both sets: {pooled_e} wrong field in "
            f"{pooled_f:,} accepted, of which {p2['fields']:,} are a post-hoc re-score of the 300 and {v2['fields']:,} "
            f"are this pre-registered run.")
    held = None
    if ins:
        held = (f"On the same {m['n']} forms the original gate would have accepted one wrong field: the model read "
                f"{ins['read']} where the paper says {ins['paper']}, a digit inserted. The v2 rule {V2_RULE} "
                f"blocked it. That is the held-out test of a rule designed after the first run, and it passed.")
    v3_line = (f"v3 on the {m['n']}: {len(v3['errors'])} wrong of {v3['fields']:,} accepted; with no second reader in this "
               f"run every SOBRANTES went to a person, so the full v3 test waits for the 3,000 with Qwen.")
    return {"n": m["n"], "v2": v2, "v3": v3, "p2": p2, "upper": upper, "pooled_fields": pooled_f,
            "pooled_errors": pooled_e, "post_hoc_share": p2["fields"] / pooled_f, "person": pc, "adj": adj,
            "insertion": ins, "modes": modes, "rule": V2_RULE, "wilson": wilson, "para": para, "held": held, "v3_line": v3_line,
            "chip": f"fix confirmed on {m['n']} fresh forms: {len(v2['errors'])} wrong of {v2['fields']:,}"}
