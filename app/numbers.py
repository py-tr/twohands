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


def home(st: storemod.Store) -> dict:
    hid = st.headline_run()
    h = st.run_metrics(hid)
    q = st.run_metrics("spike-qwen") if "spike-qwen" in st.runs else None
    errs = st.keying_errors()
    on_acc = [e for e in errs if e["status"] == "confirmed" and e["accepted_by"] and e["kind"] == "keying"]
    cert_cov = [e for e in on_acc if e["certified"] is not None]
    cert_ok = [e for e in cert_cov if e["cert_agrees"]]
    cand = [e for e in errs if e["status"] == "candidate"]
    is_spike = h["kind"] == "spike"
    sample = "43 trouble-enriched forms (spike)" if is_spike else f"{h['forms']} forms ({h['source']})"
    headline = [
        {"value": pct(h["accepted"], h["forms"]),
         "label": "of forms accepted with no human touch",
         "small": f"{h['accepted']} of {h['forms']} forms passed every identity on the page; {h['model']}; {sample}.",
         "source": h["source"]},
        {"value": f"{h['acc_wrong_adj']} of {h['acc_fields']:,}",
         "label": "accepted fields wrong",
         "small": (f"Graded against the official capture after eye-checking its disagreements; "
                   f"{h['acc_wrong_raw']} raw disagreements with the official capture, "
                   f"{h['acc_wrong_raw'] - h['acc_wrong_adj']} of them the capture's own keying errors."
                   + (f" Second reader {q['model']}: {q['acc_wrong_adj']} of {q['acc_fields']}." if q and is_spike else "")),
         "source": h["source"] + " + spikes/tally-witness/adjudicate.json"},
        {"value": str(len(on_acc)),
         "label": "keying errors found in the official double-keyed capture",
         "small": (f"On forms the gate accepted, {len(on_acc)} fields on {len({e['clave'] for e in on_acc})} forms where "
                   f"the model and the official capture disagree; in every one the image shows the capture mis-keyed. "
                   f"The certified count covers {len(cert_cov)} of the {len(on_acc)} fields and matches the image on "
                   f"{'all ' + str(len(cert_ok)) if cert_ok and len(cert_ok) == len(cert_cov) else len(cert_ok)}."
                   + (f" {len(cand)} more candidates awaiting an eye check." if cand else "")),
         "source": "spikes/tally-witness/adjudicate.json + data/truth_rows.json"},
    ]
    g = st.run_metrics("spike-gemma-v2")
    cpf_g = g["cost_per_form"]
    cpf_q = q["cost_per_form"] if q else None
    N = CITED["national_forms"]["value"]
    business = {
        "per_1000_g": usd(cpf_g * 1000), "per_1000_q": usd(cpf_q * 1000) if cpf_q else None,
        "national_g": usd(cpf_g * N, 0), "national_q": usd(cpf_q * N, 0) if cpf_q else None,
        "cpf_g": cpf_g, "cpf_q": cpf_q, "N": N,
        "cost_source": f"{g['source']} ({g['forms']} reads, mean measured cost)" + (f"; {q['source']}" if q else ""),
    }
    lm = st.ledger_metrics()
    amd = {
        "models": [{"name": g["model"], "role": "primary reader", "secs": g["mean_secs"], "cpf": cpf_g,
                    "tokens": _mean_tokens(st, "spike-gemma-v2")},
                   ] + ([{"name": q["model"], "role": "second reader", "secs": q["mean_secs"], "cpf": cpf_q,
                          "tokens": _mean_tokens(st, "spike-qwen")}] if q else []),
        "live": _live_stats(st),
    }
    return {"headline": headline, "headline_run": h, "business": business, "cited": CITED, "amd": amd,
            "ledger": lm, "errors": errs, "on_acc": on_acc, "cert_ok": len(cert_ok), "cert_cov": len(cert_cov)}


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
