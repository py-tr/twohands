"""Every number on the home and results pages, each with its n, method and source.

Measured numbers are computed from results files (app.store). Context numbers that we did not measure are
constants here, each carrying the file and URL it is cited from; docs/NUMBERS.md lists them all.
"""
from __future__ import annotations

from app import pricing as _pricing
from app import store as storemod

# ------------------------------------------------------------------ cited context (not measured by us)
CITED = {
    "national_forms": {
        "value": 169005, "text": "169,005",
        "what": "presidential tally forms (type 2) in the official 2024 capture",
        "source": "PREP 2024 CSV, https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip "
                  "(counted in docs/sources/tally-witness-pilot.md §1)"},
    "double_keying": {
        "text": "keyed twice by two capturistas, third review on mismatch",
        "source": "nmas.com.mx, quoted in docs/sources/tally-witness-pilot.md §5"},
    "base_rate": {
        "value": 0.192, "text": "19.2%", "num": "26,336", "den": "137,196",
        "what": "of fully captured national forms fail their own row sum in the official capture",
        "source": "PREP 2024 CSV, computed in docs/sources/tally-witness-pilot.md §1"},
    "state_counts_2027": {
        "text": "~32 state-level counts in 2027",
        "source": "docs/sources/tally-witness-pilot.md §5 (6 June 2027 midterm, ~32 state PREPs)"},
    "ieeq_pilot": {
        "text": "IEEQ Querétaro 2024 piloted AI recognition on 264 polling stations' forms",
        "source": "docs/sources/tally-witness-pilot.md §5"},
    "endpoint": {
        "text": "AMD Token Factory (organisers' hosted AMD GPU endpoint, OpenAI-compatible)",
        "source": "docs/sources/event-rules.md (Token Factory is the sanctioned AMD route; serves Gemma-4-31B-IT)"},
    "spike_throughput": {
        "text": "~2 forms/min", "what": "bounded by the 6 req/min, 2-concurrent pacing used in the spike",
        "source": "docs/sources/tally-witness-pilot.md §3"},
    "prep_audit": {
        "text": "Mexico requires an outside audit of every preliminary-results programme (PREP); Reglamento de "
                "Elecciones art. 347 gives preference to academic or research institutions. In February 2024, 26 of 32 "
                "state institutes had named one, all universities or research centres",
        "source": "Reglamento de Elecciones art. 347 numerals 1-2, as cited in IEEH/CG/022/2024, "
                  "https://ieehidalgo.org.mx/images/sesiones/2024/Febrero/IEEH-CG-022-2024.pdf; INE annex 5 'Entes "
                  "auditores para los Procesos Electorales Locales 2023-2024', "
                  "https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf"},
    "unam_2024": {
        "text": "UNAM centres audited the 2024 PREPs of Aguascalientes, Mexico City, Hidalgo, Puebla, Querétaro and Veracruz",
        "source": "INE annex 5, CCOE session 23-02-2024, "
                  "https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf"},
    "window_2027": {
        "text": "the federal election and 32 concurrent local processes, election day 6 June 2027",
        "source": "INE Central Electoral 2026-07-30, https://centralelectoral.ine.mx/2026/07/30/perfila-ine-organizar-el-"
                  "proceso-electoral-federal-y-32-concurrentes-2026-2027/; 2026-07-31 (election day), "
                  "https://centralelectoral.ine.mx/2026/07/31/planeara-y-organizara-ine-mas-de-500-actividades-del-"
                  "proceso-electoral-federal-2026%E2%80%912027/"},
    "sdv_cost": {
        "text": "15-30% of clinical-trial costs",
        "what": "site monitoring and source document verification, peer-reviewed estimate",
        "source": "Lindblad et al. (incl. Ball), Clinical Trials 2014; 11: 205-217, "
                  "https://www.acepidemiology.org/assets/docs/Ball%20Clinical%20Trials%202014.pdf"},
    "price_proposal": {
        "value": _pricing.PRICE_PER_FORM_USD, "text": _pricing.texts()["price"],
        "what": "proposed price, second capture + cotejo + receipts (a proposal, not a measured number)",
        "source": "app/pricing.py (the one config value); docs/BUSINESS.md section 2"},
    "volunteers": {
        "text": "~16,000 volunteers, 4 transcriptions per value",
        "source": "Hawkins et al., Geoscience Data Journal 2022, quoted in docs/sources/ledger-rescue-pilot.md §1"},
}


def pct(a, b, d=0):
    return f"{100 * a / b:.{d}f}%" if b else "n/a"


def usd(x, d=2):
    if x is None:
        return "n/a"
    return f"${x:,.{d}f}"


HEADLINE_FILE = storemod.DATA / "headline.json"
_H: dict = {}


def headline() -> dict:
    """The ONE computed summary of the pre-registered 300-form run (built by scripts/build_headline.py).
    Overview, Inbox, Audit and Results all read it, so they cannot drift apart."""
    try:
        mt = HEADLINE_FILE.stat().st_mtime_ns
    except OSError:
        return {}
    if _H.get("mt") != mt:
        import json
        _H.clear()
        _H.update(mt=mt, data=json.loads(HEADLINE_FILE.read_text(encoding="utf-8")))
    return _H["data"]


TIERS_FILE = storemod.DATA / "two_reader_300.json"


def tiers() -> dict | None:
    """Qwen alone, the two-reader tier (Amendment 2 d) and the post-hoc v2-2R pair on the 300
    (app/data/two_reader_300.json, written by scripts/two_reader_300.py, recomputed by `make eval`)."""
    return storemod._jload(TIERS_FILE, None)


def tier_lines(T: dict | None) -> dict:
    """The second-reader sentences. "two_readers" (the overview line) only when the tier is clean: no accepted field
    wrong on the paper, none undecided, none left unadjudicated."""
    if not T or "tiers" not in T:
        return {"qwen": "Second reader: no reads loaded.", "two_readers": None}
    q, t2 = T["tiers"]["qwen"], T["tiers"]["two_reader"]
    n = T["forms"]
    clean = t2["errors"] == 0 and t2["undecided"] == 0 and t2["unadjudicated"] == 0
    capt = (f"; the {t2['disagree']} accepted fields where they differ from the official capture are all capture errors"
            if t2["disagree"] and t2["capture_errors"] == t2["disagree"] else
            f"; {t2['capture_errors']} of the {t2['disagree']} accepted fields where they differ from the capture are capture errors")
    und = f", {q['undecided']} undecided on the paper" if q["undecided"] else ""
    return {
        "qwen": (f"Qwen3.8-27B read the same pages ({T['qwen_reads']} usable reads of {n} forms). Alone, the frozen gate accepted {q['accepted']} of its reads "
                 f"({pct(q['accepted'], n)}): {q['errors']} of {q['fields']:,} accepted fields wrong{und}. With two readers "
                 f"(strict mode, Amendment 2: Gemma and Qwen agree on all 23 digits, the words agree with them and the "
                 f"vote rows sum to the total): {t2['accepted']} forms ({pct(t2['accepted'], n)}), {t2['errors']} of "
                 f"{t2['fields']:,} accepted fields wrong{capt}."),
        "two_readers": (f"With two readers (strict mode): {t2['accepted']} forms, {t2['errors']} wrong fields in "
                        f"{t2['fields']:,}." if clean else None),
    }


ADJUDICATOR = "the AI adjudicator (the builder's model, which could see both values)"
_FRACTION = {2: "half", 3: "a third", 4: "a quarter", 5: "a fifth"}


def gemma_pairs() -> dict | None:
    """From the bake-off pairs (app/data/bakeoff_300.json, recomputed by make eval): the model that is in every
    compared two-reader pair with 0 accepted fields wrong, those pairs, and the compared pairs without it."""
    d = storemod._jload(storemod.DATA / "bakeoff_300.json", None)
    if not d or not d.get("pairs"):
        return None
    P = [p for p in d["pairs"] if p["n"] and not p.get("halted")]
    clean = [p for p in P if p["accepted_wrong"] == 0 and p["accepted_unadjudicated"] == 0]
    if not clean:
        return None
    common = set.intersection(*({p["a"], p["b"]} for p in clean))
    m = next((x for x in sorted(common) if x.lower().startswith("gemma")), None)
    if not m:
        return None
    other = lambda p: p["b"] if p["a"] == m else p["a"]  # noqa: E731
    without = [p for p in P if m not in (p["a"], p["b"])]
    return {"model": m, "clean": [{"with": other(p), "wrong": p["accepted_wrong"], "fields": p["accepted_fields"]}
                                  for p in clean],
            "without": [{"pair": f"{p['a']} + {p['b']}", "wrong": p["accepted_wrong"], "fields": p["accepted_fields"]}
                        for p in without]}


def gemma_pairs_line(GP: dict | None) -> str | None:
    """'Gemma-4-31B-IT is in both zero-error two-reader pairs (...); the only pair without Gemma made errors (2 of 814).'"""
    if not GP or not GP["clean"]:
        return None
    n = {1: "the", 2: "both", 3: "all three"}.get(len(GP["clean"]), f"all {len(GP['clean'])}")
    c = "; ".join(f"{x['wrong']} wrong of {x['fields']:,} accepted fields with {x['with']}" for x in GP["clean"])
    s = f"{GP['model']} is in {n} zero-error two-reader pair{'s' if len(GP['clean']) > 1 else ''} ({c})"
    bad = [x for x in GP["without"] if x["wrong"]]
    if bad and len(GP["without"]) == 1:
        s += f"; the only pair without Gemma made errors ({bad[0]['wrong']} of {bad[0]['fields']:,})"
    elif bad:
        s += "; the pairs without Gemma made errors (" + ", ".join(f"{x['wrong']} of {x['fields']:,}" for x in bad) + ")"
    return s + "."


def checked_line() -> str:
    """How far 'wrong' was checked: against the official capture, every disagreement on the photo; the agreeing
    fields only through the blind /check?set=agree200 (a seeded random 200), and only once all 200 are answered."""
    base = "against the official capture; every disagreement checked on the photo"
    try:
        from app import spotcheck
        r = spotcheck.agree200_result()
    except Exception:  # noqa: BLE001 - a missing state file must never break a page
        r = None
    if r and r["queue"] and r["answered"] == r["queue"]:
        return f"{base}; and a random {r['queue']} agreeing fields were checked by a person: {r['agree']} agreed"
    return f"{base}; fields where the model and the capture agree were not individually checked"


def gate_lines(H: dict, T: dict | None) -> dict:
    """The hero's gate line (the one-reader primary first, then the two-reader tiers with their status), the honest
    sentence, and Gemma's role. Two-reader wording only when the tier file is loaded; else the one-reader sentences."""
    g_one = (f"One reader: {H['accepted_pct']}% of forms with no person, {H['acc_model_wrong']} wrong fields in "
             f"{H['acc_fields']:,}.")
    note = "the two-reader tier checks words = digits and row sums, without the section checks"
    chk = checked_line()
    if not T or "tiers" not in T:
        return {"gate": {"value": None, "label": g_one + " The one-reader figure is the primary.", "small": None},
                "honest": (f"Alone, the model mis-keys about 1 field in {H['model_one_in']}; the official two-person capture "
                           f"typed a wrong number in 1 field in {H['wrong_number_one_in']}. That is why the model never "
                           f"decides. The paper does, and a person sees the rest."),
                "gemma_role": None, "checked": chk}
    t2, tg, tq = T["tiers"]["two_reader"], T["tiers"]["gemma"], T["tiers"]["qwen"]
    s7 = T["tiers"].get("two_reader_s7")
    full = (f"; with the full gate, {pct(s7['accepted'], T['forms'])}, {s7['errors']} wrong in {s7['fields']:,}"
            if s7 else "")
    gq = storemod._jload(storemod.DATA / "gemma_vs_qwen.json", None) or {}
    share = gq.get("gemma_cost_share_of_qwen")
    k = round(1 / share) if share else None
    cost = (f", and costs {_FRACTION.get(k, f'1/{k}')} of the second reader" if k else "")
    gp = gemma_pairs_line(gemma_pairs())
    return {
        "gate": {"value": None,
                 "label": (f"{g_one} Two readers that must agree, with the paper's sums as referee: "
                           f"{pct(t2['accepted'], T['forms'])}, {t2['errors']} wrong in {t2['fields']:,} (secondary, lighter "
                           f"gate{full}). The one-reader figure is the pre-registered primary."),
                 "small": (f"The 30% tier is a secondary analysis, defined (Amendment 2) after the one-reader result was "
                           f"seen and before the second reader ran; it uses the lighter gate (no section checks). Wrong is "
                           f"judged {chk}.").replace("The 30% tier", f"The {pct(t2['accepted'], T['forms'])} tier")},
        "gate_note": note,
        "checked": chk,
        "honest": (f"Alone, one model mis-keys 1 field in {H['model_one_in']}. Two models that agree, refereed by the paper, "
                   f"mis-keyed {t2['errors']} of {t2['fields']:,} accepted fields against the official capture."),
        "gemma_role": ((gp + " " if gp else "")
                       + f"Gemma-4-31B-IT is the primary reader in every mode: it reads every form, accepts the most forms "
                         f"alone ({tg['accepted']} against Qwen's {tq['accepted']}){cost}. In two-reader mode a second "
                         f"model must agree with Gemma field by field before the paper's arithmetic accepts; the second "
                         f"reader never overrides Gemma, it only withholds acceptance."),
    }


def lines(H: dict, T: dict | None = None) -> dict:
    """The sentences built from the summary, word for word as the pages show them."""
    if not H:
        return {}
    T = T if T is not None else tiers()
    from app import colima
    TL = tier_lines(T)
    GL = gate_lines(H, T)
    r, v, rc, fa = H["recall"], H["verdicts"], H["receipt"], H["faint"]
    ci2 = r.get("ci2") or [0, 0]
    bt = {t["type"]: t["n"] for t in H["by_type"]}
    n_cert = sum(1 for x in H.get("keying_list") or [] if x.get("cert_agrees"))
    dv = r.get("disputed_verdicts") or {}
    r_conf, r_amb = dv.get("model_right", 0), dv.get("paper_ambiguous", 0)
    breakdown = (f"{bt['wrong_value']} wrong numbers typed; {bt['marked_illegible']} readable fields recorded as illegible, "
                 f"{H['illegible_on_faint']} of them on two faint pencil forms; {bt['keyed_blank']} numbers typed where the "
                 f"paper is blank; {bt['other']} other. Each with its photo.")
    return {
        "unit": "fields where the official capture does not match the paper",
        "breakdown": breakdown,
        "keying": {"value": f"{H['keying_errors']}",
                   "label": "fields where the official capture does not match the paper",
                   "small": breakdown,
                   "small2": (f"The certified count covers {H['cert_covered']} and confirms the paper on {H['cert_agree']}; "
                              f"all {H['cert_differ']} differences were recounts.")},
        "rate": {"value": f"1 in {H['acc_one_in']}",
                 "label": (f"Alone, the model mis-keys about 1 field in {H['model_one_in']}; on the {H['accepted_pct']}% of "
                           f"forms the paper's gate accepts, about 1 in {H['acc_one_in']}"),
                 "small": (f"{H['model_wrong']} of {H['fields']:,} fields alone ({v['capture_right']} where the capture was "
                           f"right, {v['neither']} where both were off); {H['acc_model_wrong']} of {H['acc_fields']:,} on the "
                           f"{H['accepted']} accepted forms.")},
        "yield": {"value": f"1 in {H['yield_one_in']}",
                  "label": (f"disputed fields is a confirmed capture error ({H['keying_errors']} of {H['disagree']}). The "
                            f"capture's overall error rate is at least 1 in {H['random_one_in']} ({H['keying_errors']} of "
                            f"{H['fields']:,} found so far)."),
                  "small": (f"Of the {H['keying_errors']}: {n_cert} confirmed by the certified count, "
                            f"{H['keying_errors'] - n_cert} judged from the photo by {ADJUDICATOR}. The multiple between "
                            f"the two rates is not a recall estimate.")},
        "honest": GL["honest"],
        "gate": GL["gate"],
        "gemma_role": GL["gemma_role"],
        "why_gemma": _why_gemma_lead(),
        "gate_note": GL.get("gate_note"),
        "checked": GL.get("checked"),
        "preliminary": "The first capture is preliminary by design; the certified count is the official result.",
        # the measured recall (PROTOCOL.md Amendment 9, Colima), word for word as the pitch texts state it
        "recall": colima.recall_pitch(),
        # the random 300's earlier bound, kept as history (Results table, EVALUATION, REPORT)
        "recall_300": (f"On the forms the certified count settled by comparison, it differs from the first capture on "
                       f"{r['E']} fields; judged on the paper, {r['corrections']} of them are council corrections or "
                       f"blank rows (the paper shows the capture's value), and the model disputed {r['C']} of the other "
                       f"{r['E2']}: {r_conf} a confirmed capture error, {r_amb} where the paper is ambiguous. On these "
                       f"forms recall on confirmed capture errors rests on {r_conf} field{'s' if r_conf != 1 else ''}, "
                       f"too few to measure; the measured recall is the Colima check."),
        "receipt": (f"The paper says {rc['paper']}, the first capture keyed {rc['prep']}, the certified count says "
                    f"{rc['certified']}."),
        "product": (f"Give us your keyed data and the scans. You get the {H['flag_pct']:.0f}% of fields to look at, "
                    f"each with its photo."),
        "qwen": TL["qwen"],
        "two_readers": TL["two_readers"],
        "label_cost": (f"The row-label check routed {H['label_gate']['routed']} forms; on {H['label_gate']['read_right']} "
                       f"of them the read matched the paper on every field, including all "
                       f"{H['label_gate']['label_only']} routed for a label alone."),
        "harmonised": (f"In one call the model can harmonise words and digits, so one read is not two independent reads: "
                       f"on {H['harmonised']['clave']} it read {H['harmonised']['name']} as {H['harmonised']['digits']} "
                       f"in digits and {H['harmonised']['words']} in words; the paper says {H['harmonised']['paper']}. "
                       f"The fix is separate reads or a second reader."),
        "faint": (f"On the two faint pencil forms, the official capture recorded {fa['illegible']} fields as illegible. On "
                  f"{fa['model_read']} of them the paper shows the model's value; the model misread "
                  f"{fa['verdicts'].get('neither', 0)} and the paper does not settle "
                  f"{fa['illegible'] - fa['model_read'] - fa['verdicts'].get('neither', 0)}. The certified count covers "
                  f"{fa['covered']} of the {fa['model_read']} and agrees with the model on {fa['agree']} (the "
                  f"{fa['covered'] - fa['agree']} that differ are recounts)."),
    }


def home(st: storemod.Store) -> dict:
    H = headline()
    L = lines(H)
    headline_cards = [dict(L[k], source=src) for k, src in (
        ("keying", "results/adjudication/SUMMARY.md + CERTIFIED.md (app/data/headline.json)"),
        ("gate", "app/data/headline.json (one reader, primary) + app/data/two_reader_300.json (two readers, Amendment 2 d)"),
        ("yield", "results/adjudication/SUMMARY.md + RECALL.md (app/data/headline.json); docs/EVALUATION.md, \"Behind 1 in 5 vs at least 1 in 122\""))] if H else []
    q = st.run_metrics("spike-qwen") if "spike-qwen" in st.runs else None
    g = st.run_metrics("spike-gemma-v2")
    cpf_g = (H.get("gemma") or {}).get("cost_per_form") or g["cost_per_form"]
    cpf_q = q["cost_per_form"] if q else None
    N = CITED["national_forms"]["value"]
    business = {
        "per_1000_g": usd(cpf_g * 1000), "per_1000_q": usd(cpf_q * 1000) if cpf_q else None,
        "national_g": usd(cpf_g * N, 0), "national_q": usd(cpf_q * N, 0) if cpf_q else None,
        "cpf_g": cpf_g, "cpf_q": cpf_q, "N": N,
        "cost_source": (f"results/calls_gemma.jsonl ({H['gemma']['reads']} reads of the pre-registered run, mean measured "
                        f"cost)" if H else g["source"]) + (f"; second reader: {q['source']} (pilot, 43 reads)" if q else ""),
    }
    lm = st.ledger_metrics()
    amd = {
        "models": [{"name": g["model"], "role": "primary reader", "secs": (H.get("gemma") or {}).get("mean_secs") or g["mean_secs"],
                    "cpf": cpf_g, "tokens": ({"prompt": H["gemma"]["tokens_in"], "completion": H["gemma"]["tokens_out"]}
                                             if H and H["gemma"].get("tokens_in") else _mean_tokens(st, "spike-gemma-v2")),
                    "basis": f"{H['gemma']['reads']} reads, pre-registered run" if H else "pilot, 43 reads"},
                   ] + ([{"name": q["model"], "role": "second reader", "secs": q["mean_secs"], "cpf": cpf_q,
                          "tokens": _mean_tokens(st, "spike-qwen"), "basis": "pilot, 43 reads"}] if q else []),
        "live": _live_stats(st),
        "gemma": _gemma_vs_qwen(),
        "bakeoff": _bakeoff(),
        "why": _why_gemma(),
    }
    return {"confirm100": _confirm100(), "headline": headline_cards, "H": H, "L": L, "T": tiers(), "business": business, "cited": CITED, "amd": amd,
            "ledger": lm, "pilot": g, "pilot_q": q}


def _confirm100():
    """The pre-registered confirmation (PROTOCOL Amendment 3; gate v3 per Amendment 7): results/confirm100.json, from
    scripts/confirm100_score.py, recomputed by make eval. None until scored."""
    from twohands import REPO
    d = storemod._jload(REPO / "results" / "confirm100.json", None)
    if not d or not d.get("lines"):
        return None
    from app import confirm100 as c100
    return {"v2": d["lines"]["v2"], "v3": d["lines"]["v3"], **(c100.texts() or {})}


def _why_gemma_lead():
    """'Same 300 forms, same gate, on AMD: Gemma accepts 1.8x the forms ...' (app/why_gemma.py, from bakeoff_300.json)."""
    from app import why_gemma
    return why_gemma.lead()


def _why_gemma():
    """The Gemma table and the misreads the arithmetic caught, for the results page (app/why_gemma.py)."""
    from app import why_gemma
    d = why_gemma.load()
    if not d:
        return None
    return {"lead": why_gemma.lead(d), "head": why_gemma.HEAD, "rows": why_gemma.rows(d), "note": why_gemma.note(d),
            "caught": [dict(c, line=why_gemma.caught_line(c)) for c in why_gemma.caught()],
            "same_model": why_gemma.same_model_line()}


def _bakeoff():
    """Amendment 6: every vision model on AMD Token Factory on the same forms (app/data/bakeoff_300.json, from
    scripts/bakeoff.py report, recomputed by make eval). Models listed by field agreement; pairs by fewest errors."""
    d = storemod._jload(storemod.DATA / "bakeoff_300.json", None)
    if not d or not d.get("models"):
        return None
    models = sorted(({"model": m, **b} for m, b in d["models"].items() if b["n"] and not b.get("halted")), key=lambda b: -(b["field_agreement_pct"] or 0))
    return {"models": models, "pairs": [p for p in d.get("pairs", []) if p["n"] and not p.get("halted")][:5],
            "halted": {m: b for m, b in d["models"].items() if b.get("halted")}, "not_compatible": d.get("not_compatible", {}),
            "spend": d.get("total_bakeoff_spend_usd"), "prompt": d["prompt_sha256"][:12],
            "verdict": d.get("model_verdict")}


def _gemma_vs_qwen():
    """Gemma vs Qwen on the same forms of the 300 run (app/data/gemma_vs_qwen.json, from scripts/gemma_vs_qwen.py)."""
    d = storemod._jload(storemod.DATA / "gemma_vs_qwen.json", None)
    if not d or not d.get("common_forms"):
        return None
    g, q = d["gemma"], d["qwen"]
    share = d.get("gemma_cost_share_of_qwen")
    return {"n": d["common_forms"], "sample": d["sample"], "complete": d["qwen_complete"], "g": g, "q": q,
            "img_g": g.get("image_tokens_per_image_mean"), "img_q": q.get("image_tokens_per_image_mean"),
            "cost_ratio": round(1 / share) if share else None, "prompt": d["prompt_sha256"][:12],
            "full": d.get("gemma_full_300")}


def _mean_tokens(st, rid):
    import json
    runs = storemod._jload(storemod.DATA / "spike_runs.json", [])
    run = next((r for r in runs if r["id"] == rid), None)
    if not run:
        return None
    pt = [r["prompt_tokens"] for r in run["rows"] if r.get("prompt_tokens")]
    ct = [r["completion_tokens"] for r in run["rows"] if r.get("completion_tokens")]
    return {"prompt": sum(pt) / len(pt) if pt else None, "completion": sum(ct) / len(ct) if ct else None}


def _live_stats(st):
    rows = list(st.live.values())
    if not rows:
        return None
    secs = [r["secs"] for r in rows if r.get("secs")]
    cost = [r["cost"] for r in rows if r.get("cost")]
    return {"n": len(rows), "secs": sum(secs) / len(secs) if secs else None, "cost": sum(cost) / len(cost) if cost else None}
