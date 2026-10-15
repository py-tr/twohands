"""Every number on the home and results pages, each with its n, method and source.

Measured numbers are computed from results files (app.store). Context numbers that we did not measure are
constants here, each carrying the file and URL it is cited from; docs/NUMBERS.md lists them all.
"""
from __future__ import annotations

from app import store as storemod

# ------------------------------------------------------------------ cited context (not measured by us)
CITED = {
    "national_forms": {
        "value": 169005, "text": "169,005",
        "what": "presidential tally forms (type 2) in the official 2024 capture",
        "source": "PREP 2024 CSV, https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip "
                  "(counted in spikes/tally-witness/README.md §1)"},
    "programme_cost_mxn": {
        "value": 273630875, "text": "MXN 273.6M",
        "what": "cost of the 2024 national preliminary-results capture programme (PREP), which keys every form twice",
        "source": "La Jornada, 2024-05-26 (\"36 millones 315 mil 225 pesos que se suman a los 237 millones 315 mil 650 "
                  "pesos\"), quoted in spikes/tally-witness/README.md §5"},
    "double_keying": {
        "text": "keyed twice by two capturistas, third review on mismatch",
        "source": "nmas.com.mx, quoted in spikes/tally-witness/README.md §5"},
    "base_rate": {
        "value": 0.192, "text": "19.2%", "num": "26,336", "den": "137,196",
        "what": "of fully captured national forms fail their own row sum in the official capture",
        "source": "PREP 2024 CSV, computed in spikes/tally-witness/README.md §1"},
    "state_counts_2027": {
        "text": "~32 state-level counts in 2027",
        "source": "spikes/tally-witness/README.md §5 (6 June 2027 midterm, ~32 state PREPs)"},
    "state_contract": {
        "text": "MXN 24.94M", "what": "one state's 2024 capture contract (Campeche)",
        "source": "spikes/tally-witness/README.md §5"},
    "ieeq_pilot": {
        "text": "IEEQ Querétaro 2024 piloted AI recognition on 264 polling stations' forms",
        "source": "spikes/tally-witness/README.md §5"},
    "endpoint": {
        "text": "AMD Token Factory (organisers' hosted AMD GPU endpoint, OpenAI-compatible)",
        "source": "notes/rules.md (Token Factory is the sanctioned AMD route; serves Gemma-4-31B-IT)"},
    "spike_throughput": {
        "text": "~2 forms/min", "what": "bounded by the 6 req/min, 2-concurrent pacing used in the spike",
        "source": "spikes/tally-witness/README.md §3"},
    "prep_audit": {
        "text": "Mexico requires an outside audit of every preliminary-results capture (PREP); Reglamento de Elecciones "
                "art. 347 gives priority to academic institutions",
        "source": "INE, Reglamento de Elecciones art. 347; INE COTAPREP/CCOE session 23-02-2024, "
                  "https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf"},
    "unam_2024": {
        "text": "in 2024 UNAM centres audited the PREPs of Querétaro, Aguascalientes, Puebla and Mexico City, among others",
        "source": "IEEQ press summary 2024, https://ieeq.mx/contenido/prensa/sintesis/2024/13469.pdf; "
                  "https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf"},
    "sdv_cost": {
        "text": "15-30% of clinical-trial costs",
        "what": "peer-reviewed estimate for monitoring, including source-data verification",
        "source": "Ball, Clinical Trials 2014, https://www.acepidemiology.org/assets/docs/Ball%20Clinical%20Trials%202014.pdf"},
    "volunteers": {
        "text": "~16,000 volunteers, 4 transcriptions per value",
        "source": "Hawkins et al., Geoscience Data Journal 2022, quoted in spikes/ledger-rescue/README.md §1"},
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


def lines(H: dict) -> dict:
    """The sentences built from the summary, word for word as the pages show them."""
    if not H:
        return {}
    r, v, rc, fa = H["recall"], H["verdicts"], H["receipt"], H["faint"]
    ci2 = r.get("ci2") or [0, 0]
    bt = {t["type"]: t["n"] for t in H["by_type"]}
    high = (r.get("recall2_pct") or 0) >= 50
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
                            f"{H['fields']:,} found so far).")
                           + (" More than ten times the yield of a random check." if high else ""),
                  "small": None},
        "honest": (f"Alone, the model mis-keys about 1 field in {H['model_one_in']}; the official two-person capture typed "
                   f"a wrong number in 1 field in {H['wrong_number_one_in']}. That is why the model never decides. The "
                   f"paper does, and a person sees the rest."),
        "preliminary": "The first capture is preliminary by design; the certified count is the official result.",
        "recall": (f"On the forms the certified count settled by comparison, it differs from the first capture on {r['E']} "
                   f"fields; judged on the paper, {r['corrections']} of them are council corrections or blank rows (the "
                   f"paper shows the capture's value), and the model disputed {r['C']} of the other {r['E2']} "
                   f"(measured recall {r['recall2_pct']}%, Wilson 95% {100 * ci2[0]:.0f}% to {100 * ci2[1]:.0f}%; small n)."),
        "receipt": (f"The paper says {rc['paper']}, the first capture keyed {rc['prep']}, the certified count says "
                    f"{rc['certified']}."),
        "product": (f"Give us your keyed data and the scans. You get the {H['flag_pct']:.0f}% of fields to look at, "
                    f"each with its photo."),
        "qwen": "Second-reader pass running; this line updates when it lands.",
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
        ("rate", "results/adjudication/SUMMARY.md (app/data/headline.json)"),
        ("yield", "results/adjudication/SUMMARY.md + RECALL.md (app/data/headline.json); docs/EVALUATION.md, \"Behind more than ten times the yield of a random check\""))] if H else []
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
    }
    return {"headline": headline_cards, "H": H, "L": L, "business": business, "cited": CITED, "amd": amd,
            "ledger": lm, "pilot": g, "pilot_q": q}


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
