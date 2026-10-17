"""Colima, the whole state (PROTOCOL.md Amendment 8b): every number and sentence the site, the docs, the slides and the
video captions say about it, generated here from results/colima/colima_audit.json (scored by
`scripts/gemma_tf_reads2.py score-colima`), the read cost in results/colima/calls_gemma.jsonl, and the 300-form figures
in app/data/headline.json. Nothing is typed by hand: `score-colima` writes results/colima/report.json from here and
`score-colima --check` (make eval) checks report.json and every doc line below (doc_mismatches).

Wording rules: the 13 accepted wrong fields are the AI adjudicator's reading (never "confirmed", never "reviewer");
"the capture does not match the paper"; vote rows are Option NN; nothing about outcomes.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[1]
DIR = REPO / "results" / "colima"
AUDIT, CALLS, REPORT = DIR / "colima_audit.json", DIR / "calls_gemma.jsonl", DIR / "report.json"
CROPS = DIR / "crops"
HEADLINE = REPO / "app" / "data" / "headline.json"
TWO_READER = REPO / "app" / "data" / "two_reader_300.json"
V1, V2, V3 = "v1 (frozen gate, primary)", "v2 (Amendment 3)", "v3 (Amendment 7; no second reader, so SOBRANTES always to a person)"
CHECK_SET, CHECK_SEED = "colima13", 20261015
CERT, AI = "confirmed by the certified count: ", "AI adjudicator's reading: "
FIELD = {"SOBRANTES": "unused ballots", "SACADOS": "ballots taken from the boxes", "TOTAL": "TOTAL"}


def _j(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _calls() -> dict:
    out = {}
    try:
        for line in CALLS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["clave"]] = r
    except OSError:
        pass
    return out


def _err(e: str) -> dict:
    """'060058B0100__SOBRANTES read 268, capture 208, paper 208 [AI adjudicator's reading]' -> parts."""
    item, rest = e.split(" ", 1)
    form, code = item.split("__", 1)
    nums = dict(p.strip().split(" ", 1) for p in rest.split(" [")[0].split(","))
    return {"item": item, "form": form, "code": code, "read": int(nums["read"]), "capture": int(nums["capture"]),
            "paper": int(nums["paper"]), "by": rest.split(" [")[1].rstrip("]")}


def _pct(k: int, n: int, nd: int = 1) -> str:
    return f"{100 * k / n:.{nd}f}%"


def facts() -> Optional[dict]:
    d = _j(AUDIT)
    if not d or not d.get("complete"):
        return None
    calls = _calls()
    H, T = _j(HEADLINE, {}), (_j(TWO_READER, {}).get("tiers") or {}).get("two_reader") or {}
    L = d["labels"]
    g = {k: d["gates"][k] for k in (V1, V2, V3)}
    v1 = g[V1]
    from app.store import name_of
    errs = [dict(x, name=name_of(x["code"])) for x in (_err(e) for e in v1["errors"])]
    lay = {c: r.get("layout") for c, r in calls.items()}
    acc_forms = v1["movil"] + v1["escaner"]
    n_scan = sum(1 for x in lay.values() if x == "escaner")
    n_phone = sum(1 for x in lay.values() if x == "movil")
    gates = []
    for name, x in g.items():
        tag = name.split(" ", 1)[0]
        gates.append({"tag": tag, "name": name.split(" (", 1)[1].rstrip(")") if " (" in name else "",
                      "accepted": x["forms_accepted"], "pct": _pct(x["forms_accepted"], d["prep_rows"]),
                      "touchless": x["touchless"], "movil": x["movil"], "escaner": x["escaner"],
                      "fields": x["fields"], "wrong": len(x["errors"]), "ambiguous": len(x["undecided"]),
                      "lo": f"{100 * x['ci'][0]:.2f}%", "hi": f"{100 * x['ci'][1]:.2f}%",
                      "primary": tag == "v1", "to_person": x["sobrantes_to_person"]})
    kinds = {}
    for e in errs:
        kinds[e["code"]] = kinds.get(e["code"], 0) + 1
    return {
        "prep_rows": d["prep_rows"], "located": d["located"], "read": d["read"],
        "not_located": sorted(d["no_image_or_not_located"]), "cost": round(sum(r.get("cost_usd") or 0 for r in calls.values()), 4),
        "calls": len(calls), "gates": gates, "v1": gates[0], "v3": gates[2],
        "disagreements": d["disagreements"],
        "cert": sum(v for k, v in L.items() if k.startswith(CERT)),
        "cert_capture": L.get(CERT + "model right (capture error)", 0),
        "ai": sum(v for k, v in L.items() if k.startswith(AI)),
        "ambiguous": L.get("paper ambiguous or unreadable", 0),
        "pending": d["adjudication_sample"]["not_sampled_pending"] + d["adjudication_sample"]["pending_in_sample"],
        "pending_on_accepted": sum(len(x["pending"]) for x in g.values()),
        "errors": errs, "kinds": kinds,
        "errors_on_scans": sum(1 for e in errs if lay.get(e["form"]) == "escaner"),
        "scan_pass": _pct(v1["escaner"], n_scan), "phone_pass": _pct(v1["movil"], n_phone),
        "scans_pass_more": v1["escaner"] / n_scan > v1["movil"] / n_phone,
        "acc_forms": acc_forms,
        "h_forms": H.get("forms"), "h_wrong": H.get("acc_model_wrong"), "h_fields": H.get("acc_fields"),
        "h_pct": H.get("accepted_pct"), "t_wrong": T.get("errors"), "t_fields": T.get("fields"),
        "report": d.get("audit_report") or {},
    }


# ------------------------------------------------------------------ the person's blind check of the 13 (/check?set=colima13)
def check13_verdicts() -> dict:
    """The v1 accepted wrong fields, as /check items: the AI adjudicator's paper value, hidden on the blind page."""
    d = _j(AUDIT, {})
    out = {}
    for e in (d.get("gates", {}).get(V1, {}).get("errors") or []):
        x = _err(e)
        out[x["item"]] = {"form_id": x["form"], "field": x["code"], "verdict": "capture_right", "paper": x["paper"],
                          "evidence": f"AI adjudicator's reading: paper {x['paper']}, capture {x['capture']}, Gemma {x['read']}"}
    return out


def check13_queue() -> list[str]:
    q = sorted(check13_verdicts())
    random.Random(CHECK_SEED).shuffle(q)
    return q


def check13_result(answers: Optional[dict] = None) -> dict:
    from app import spotcheck
    v = check13_verdicts()
    answers = spotcheck.load(CHECK_SET) if answers is None else answers
    got = [k for k in sorted(v) if answers.get(k)]
    return {"queue": len(v), "answered": len(got), "agree": sum(1 for k in got if spotcheck.agrees(answers[k], v[k]))}


def who_line(F: dict, person: Optional[dict] = None) -> str:
    """Who decided the 13: the AI adjudicator; a person's blind check once all are answered."""
    n = F["v1"]["wrong"]
    p = person if person is not None else check13_result()
    tail = (f"checked by a person: {p['agree']} of {p['queue']} agree" if p["queue"] and p["answered"] == p["queue"]
            else f"person check pending (blind, /check?set={CHECK_SET})")
    return f"Each of the {n}: AI adjudicator's reading (it sided with the capture against Gemma); {tail}."


# ------------------------------------------------------------------ the recall check (Amendment 9, /check?set=colimarecall)
RECALL_SET, RECALL_SEED = "colimarecall", 20261017
RECALL_CAND, RECALL, RECALL_MD = DIR / "recall_candidates.json", DIR / "recall.json", DIR / "recall.md"
RECALL_CROPS = DIR / "recall_crops"
RECALL_RULE = ("graded field the certified count covers (vote rows, TOTAL), on a form settled by cotejo not recount; "
               "candidate: certified differs from the capture and Gemma equals the capture; caught: certified differs "
               "from the capture and Gemma equals the certified count; neither: certified differs from both")
MISS, CORR, AMB = "capture error Gemma also missed", "later correction by the council", "ambiguous"


def recall_candidates() -> Optional[dict]:
    return _j(RECALL_CAND)


def recall_verdicts() -> dict:
    """The candidates as blind /check items: no certified, capture or model value (nothing to compare on the page)."""
    C = recall_candidates() or {}
    return {c["item"]: {"form_id": c["form"], "field": c["field"], "verdict": "recall_candidate", "paper": None,
                        "evidence": ""} for c in C.get("candidates", [])}


def recall_queue() -> list[str]:
    q = sorted(recall_verdicts())
    random.Random(RECALL_SEED).shuffle(q)
    return q


def recall_label(a: dict, c: dict) -> str:
    from app import spotcheck
    pv = spotcheck.person_value(a)
    if spotcheck.person_ambiguous(a) or not isinstance(pv, int):
        return AMB
    return MISS if pv == c["certified"] else CORR if pv == c["capture"] else AMB


def recall_result(answers: Optional[dict] = None) -> Optional[dict]:
    """Amendment 9. Nothing but the size of the set until every candidate is answered; then the labels and recall.
    Answers: the live /check file, else the copy kept in results/colima/recall.json (a checkout without app/state/)."""
    C = recall_candidates()
    if not C:
        return None
    from app import spotcheck
    from twohands.score import wilson
    if answers is None:
        answers = spotcheck.load(RECALL_SET) or (_j(RECALL, {}) or {}).get("answers") or {}
    cand = C["candidates"]
    got = [c for c in cand if answers.get(c["item"])]
    base = {"amendment": C["amendment"], "set": f"/check?set={RECALL_SET}", "rule": C["rule"],
            "forms_read": C["forms_read"], "candidates": len(cand), "caught": len(C["caught"]),
            "neither": len(C["neither"]), "complete": bool(cand) and len(got) == len(cand), "answered": len(got)}
    if not base["complete"]:
        return base
    from app.store import name_of
    rows = []
    for c in sorted(cand, key=lambda c: c["item"]):
        a = answers[c["item"]]
        rows.append({"item": c["item"], "field": name_of(c["field"]), "capture": c["capture"],
                     "certified": c["certified"], "gemma": c["gemma"], "person_digits": a.get("digits"),
                     "person_words": a.get("words"), "label": recall_label(a, c)})
    n = {lab: sum(1 for r in rows if r["label"] == lab) for lab in (MISS, CORR, AMB)}
    k, miss = base["caught"], n[MISS]
    lo, hi = wilson(k, k + miss)
    wlo, whi = wilson(k, k + miss + n[AMB])
    return {**base, "missed": miss, "corrections": n[CORR], "ambiguous": n[AMB],
            "recall": k / (k + miss), "ci": [lo, hi],
            "recall_ambiguous_as_missed": k / (k + miss + n[AMB]), "ci_ambiguous_as_missed": [wlo, whi],
            "rows": rows, "answers": {c["item"]: answers[c["item"]] for c in sorted(cand, key=lambda c: c["item"])}}


def recall_line(R: Optional[dict]) -> str:
    if not R:
        return "Recall check (Amendment 9): not built."
    if not R["complete"]:
        return (f"Recall check (Amendment 9): {R['candidates']} fields where the certified count differs from the "
                f"capture and Gemma agreed with the capture; a person's blind check is in progress at "
                f"/check?set={RECALL_SET}.")
    k, m = R["caught"], R["missed"]
    return (f"Recall on capture errors the certified count sees (Amendment 9, a person's blind check): {k} caught, "
            f"{m} missed, {_pct(k, k + m)} (Wilson 95% {100 * R['ci'][0]:.1f}% to {100 * R['ci'][1]:.1f}%); of the "
            f"{R['candidates']} fields where Gemma agreed with a capture the certified count changes, {m} are capture "
            f"errors Gemma also missed, {R['corrections']} later corrections by the council, {R['ambiguous']} "
            f"ambiguous.")


def recall_pitch(R: Optional[dict] = None) -> str:
    """The measured recall as the pitch texts state it (README, lablab.md, slides, Results page, EVALUATION), with its
    scope: errors the certified count reveals, one state; never total recall. Until scored: the in-progress line."""
    R = recall_result() if R is None else R
    if not R or not R.get("complete"):
        return recall_line(R)
    k, m = R["caught"], R["missed"]
    return (f"Recall on the capture errors the certified count reveals, Colima (pre-registered, a person's blind "
            f"check): {k} of {k + m} caught, {round(100 * k / (k + m))}% (Wilson 95% {100 * R['ci'][0]:.0f}-"
            f"{100 * R['ci'][1]:.0f}%). One state, certified-detectable errors only; not total recall.")


def recall_clause(R: Optional[dict] = None) -> str:
    """The short clause of the README's "Real data" bullet and lablab.md's opening ("" until scored)."""
    R = recall_result() if R is None else R
    if not R or not R.get("complete"):
        return ""
    k, m = R["caught"], R["missed"]
    return f"recall on certified-detectable errors {k} of {k + m} (Colima, pre-registered; not total recall)"


def recall_page_mismatches() -> list[str]:
    """The Results page, rendered, must state the recall pitch line (and the site's recall line must be it)."""
    import html
    from fastapi.testclient import TestClient
    from app import numbers
    from app.main import app
    p = _norm(recall_pitch())
    bad = []
    if _norm((numbers.lines(numbers.headline()) or {}).get("recall", "")) != p:
        bad.append("app/numbers.py lines()['recall'] (not the recall pitch line)")
    if p not in _norm(html.unescape(TestClient(app).get("/results").text)):
        bad.append("/results (the recall pitch line)")
    return bad


def recall_file(R: Optional[dict] = None) -> dict:
    """results/colima/recall.json: without the running answered count while in progress (it would go stale)."""
    R = R or recall_result()
    return {k: v for k, v in R.items() if R["complete"] or k != "answered"}


def recall_md(R: dict) -> str:
    L = ["# Colima recall check (PROTOCOL.md Amendment 9)", "", recall_line(R), "",
         f"Rule: {R['rule']}.", "",
         f"Forms read: {R['forms_read']}. Candidates: {R['candidates']}. Caught (colima_audit.json): {R['caught']}. "
         f"Certified differs from both (not counted): {R['neither']}."]
    if R["complete"]:
        L += ["", "Secondary, every ambiguous candidate counted as missed: "
                  f"{100 * R['recall_ambiguous_as_missed']:.1f}% (Wilson 95% "
                  f"{100 * R['ci_ambiguous_as_missed'][0]:.1f}% to {100 * R['ci_ambiguous_as_missed'][1]:.1f}%).", "",
              "| Form | Field | Capture | Certified | Gemma | Person | Label |", "|---|---|---|---|---|---|---|"]
        L += [f"| {r['item'].split('__')[0]} | {r['field']} | {r['capture']} | {r['certified']} | {r['gemma']} | "
              f"{r['person_digits']} | {r['label']} |" for r in R["rows"]]
    else:
        L += ["", f"In progress: answers come from the blind page /check?set={RECALL_SET}; nothing is reported until "
                  "every candidate is answered."]
    L += ["", "Built by `scripts/colima_recall.py` (build, score); crops in `results/colima/recall_crops/`."]
    return "\n".join(L) + "\n"


def write_recall() -> None:
    R = recall_result()
    RECALL.write_text(json.dumps(recall_file(R), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    RECALL_MD.write_text(recall_md(R), encoding="utf-8")


def recall_mismatches() -> list[str]:
    R = recall_result()
    if R is None:
        return ["results/colima/recall_candidates.json (run scripts/colima_recall.py build)"]
    bad = []
    from twohands.adjudicate import crop_name
    miss = [c["item"] for c in recall_candidates()["candidates"]
            if not (RECALL_CROPS / crop_name(c["form"], c["field"])).is_file()]
    if miss:
        bad.append(f"results/colima/recall_crops/ ({len(miss)} crops missing)")
    if _j(RECALL) != json.loads(json.dumps(recall_file(R))):
        bad.append("results/colima/recall.json (run scripts/colima_recall.py score)")
    try:
        if RECALL_MD.read_text(encoding="utf-8") != recall_md(R):
            bad.append("results/colima/recall.md (run scripts/colima_recall.py score)")
    except OSError:
        bad.append("results/colima/recall.md (missing)")
    return bad


# ------------------------------------------------------------------ the sentences
def lines(F: Optional[dict] = None) -> Optional[dict]:
    F = F or facts()
    if not F:
        return None
    v1, v3 = F["v1"], F["v3"]
    k = F["kinds"]
    inside = {c: n for c, n in k.items() if c != "SOBRANTES"}
    from app.store import name_of
    inside_s = ", ".join(f"{n} {FIELD[c]}" if c in FIELD else f"{n} {name_of(c)}"
                         for c, n in sorted(inside.items(), key=lambda x: (x[0] not in FIELD, -x[1])))
    complete_ok = F["pending_on_accepted"] == 0
    return {
        "replication": (f"One reader, frozen gate: {F['h_wrong']} wrong of {F['h_fields']:,} accepted fields on "
                        f"{F['h_forms']} random forms ({_pct(F['h_wrong'], F['h_fields'], 2)}), {v1['wrong']} of "
                        f"{v1['fields']:,} on a whole state ({_pct(v1['wrong'], v1['fields'], 2)})."),
        "intake": (f"{F['prep_rows']:,} presidential sheets in the PREP; {F['read']} located and read by Gemma-4-31B-IT "
                   f"on AMD Token Factory, one request each, ${F['cost']:.2f} in all; {len(F['not_located'])} not "
                   f"located, listed."),
        "v1": (f"Frozen gate (v1, primary): {v1['accepted']} accepted with no person ({v1['pct']} of "
               f"{F['prep_rows']:,}), {v1['wrong']} wrong of {v1['fields']:,} accepted fields (Wilson 95% "
               f"{v1['lo']} to {v1['hi']})."),
        "v3": f"v3: {v3['accepted']} accepted, {v3['wrong']} wrong of {v3['fields']:,}.",
        "kinds": (f"{k.get('SOBRANTES', 0)} of the {v1['wrong']} are unused ballots, the one field outside every "
                  f"identity; the other {sum(inside.values())} ({inside_s}) sit inside an identity and passed because "
                  f"the read kept every identity true (a compensating or harmonised read, as in the 239/239 case): the "
                  f"gate's blind spot made visible."),
        "ledger": (f"{F['disagreements']} disputes with the first capture: {F['cert']} settled by the certified count "
                   f"(in {F['cert_capture']} of them the capture does not match the paper); {F['ai']} AI adjudicator's "
                   f"reading; {F['ambiguous']} paper ambiguous; {F['pending']} awaiting review."),
        "complete": ("The accepted-field error rate is complete, and every dispute carries a label." if complete_ok
                     and not F["pending"] else
                     f"The accepted-field error rate is complete: none of the {F['pending']} touches an accepted field."
                     if complete_ok else f"{F['pending_on_accepted']} accepted fields still await review."),
        "scans": (f"Colima accepts {v1['pct']} of forms, against {F['h_pct']}% on the national random {F['h_forms']}; "
                  + ("scans pass the gate more often and " if F["scans_pass_more"] else
                     f"phone photos pass about as often as scans ({F['phone_pass']} and {F['scan_pass']}), and ")
                  + f"scans carry {F['errors_on_scans']} of the {v1['wrong']} accepted errors."),
        "tiers": (f"v1 is the primary (the headline rule); v2 and v3 are pre-registered in Amendment 8b and shown "
                  f"beside it. The two-reader tier was not run on Colima (single reader); {F['t_wrong']} of "
                  f"{F['t_fields']:,} remains a {F['h_forms']}-form result."),
        "lablab": (f"Whole state: Gemma on AMD read all {F['read']} located presidential sheets of Colima for "
                   f"${F['cost']:.2f}; {F['cert_capture']} fields where the capture does not match the paper, each "
                   f"confirmed by the certified count, with a field-level report."),
        "slide": (f"Free sample deliverable: Colima, the whole state ({F['prep_rows']:,} in the PREP, {F['read']} read, "
                  f"{len(F['not_located'])} not located, listed), report attached."),
        "card": (f"Free sample: Colima, the whole state, {F['read']} of {F['prep_rows']:,} presidential sheets read on AMD "
                 f"for ${F['cost']:.2f}, field-level report."),
        "caption": f"Gemma on AMD read all {F['read']} sheets for {round(100 * F['cost'])} cents.",
        "recall": recall_line(recall_result()),
        "recall_pitch": recall_pitch(),
        "recall_clause": recall_clause(),
    }


def block() -> Optional[dict]:
    """Everything the Results page's Colima block shows."""
    F = facts()
    if not F:
        return None
    p = check13_result()
    return {"F": F, "L": lines(F), "who": who_line(F, p), "person": p}


def report_json(F: Optional[dict] = None) -> dict:
    """results/colima/report.json, the shape app/buyer._colima reads (finished, forms) plus the card's numbers."""
    F = F or facts()
    L = lines(F)
    return {"finished": True, "forms": F["read"], "prep_rows": F["prep_rows"], "not_located": len(F["not_located"]),
            "cost_usd": F["cost"], "accepted_v1": F["v1"]["accepted"], "wrong_v1": F["v1"]["wrong"],
            "fields_v1": F["v1"]["fields"], "capture_errors_certified": F["cert_capture"], "card": L["card"],
            "href": "/results#colima", "source": "app/colima.py from results/colima/colima_audit.json"}


def write_report() -> None:
    REPORT.write_text(json.dumps(report_json(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


# doc -> the line keys it must carry, word for word (whitespace and ** ignored)
DOCS = {"README.md": ("lablab", "scans", "recall_pitch", "recall_clause"),
        "submission/lablab.md": ("lablab", "recall_pitch", "recall_clause"), "slides/slides.md": ("slide", "recall_pitch"),
        "slides/two-hands.srt": ("caption",),
        "docs/EVALUATION.md": ("replication", "kinds", "tiers", "recall", "recall_pitch")}
RECALL_KEYS = ("recall_pitch", "recall_clause")


def recall_doc_mismatches() -> list[str]:
    """The Amendment 9 recall lines (recall_pitch, recall_clause) in every doc that must carry them, word for word."""
    L = {"recall_pitch": recall_pitch(), "recall_clause": recall_clause()}
    bad = []
    for doc, keys in DOCS.items():
        keys = [k for k in keys if k in RECALL_KEYS]
        if keys:
            s = _norm((REPO / doc).read_text(encoding="utf-8"))
            bad += [f"{doc} (the Colima '{k}' line)" for k in keys if _norm(L[k]) not in s]
    return bad


def _norm(s: str) -> str:
    return " ".join(s.replace("**", "").split())


def doc_mismatches() -> list[str]:
    F = facts()
    if not F:
        return ["results/colima/colima_audit.json (absent or incomplete)"]
    L = lines(F)
    bad = recall_mismatches()
    if _j(REPORT) != json.loads(json.dumps(report_json(F))):
        bad.append("results/colima/report.json (run score-colima)")
    for doc, keys in DOCS.items():
        try:
            s = _norm((REPO / doc).read_text(encoding="utf-8"))
        except OSError:
            bad.append(f"{doc} (missing)")
            continue
        bad += [f"{doc} (the Colima '{k}' line)" for k in keys if _norm(L[k]) not in s]
    return bad
