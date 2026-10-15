# Every number in the web app, and where it comes from

Vote rows are shown as "Option 01" to "Option 15" (printed order). The app never shows party names, in HTML or in JSON.
The app computes measured numbers at request time (`app/store.py`, `app/numbers.py`) from results files. It does not
type them in. Cited context numbers are constants in `app/numbers.py` (`CITED`), and each one carries its source.
This file lists both kinds. Values below are as of 2026-10-15; if a results file changes, the page changes with it.

## A. Measured (computed from results files)

| Shown as | Value now | Computed from | Method |
|---|---|---|---|
| Touchless rate (home, results) | 49% = 21 of 43 forms | `app/data/spike_runs.json`, a snapshot of `spikes/tally-witness/results_v2/gemma__*.json` | Gate = completeness + words = digits + the 4 schema identities (`schemas/mx_presidencia_2024.yaml`). Same checks as the spike's `score.py` FULL gate. The spike reads predate the row-label check. |
| Accepted fields wrong | 0 of 462 (Gemma), 0 of 484 (Qwen) | the same, plus `app/data/official.json` (from `spikes/tally-witness/data/truth_rows.json` and `adjudicate.json`) | 22 graded fields per form against the PREP capture. "After eye check" swaps in the fields in `adjudicate.json`. Raw disagreements: 5 (Gemma), 4 (Qwen). |
| Keying errors in the official capture | 6 fields on 5 forms | `adjudicate.json` entries on forms that a spike reader accepted | 093954C0200, 156723B0100, 202451B0100 (TOTAL and section 7), 211298B0100, 211420C0400. The app labels vote rows "Option NN" and never by party. |
| Certified count | covers 5 of the 6 fields and matches the image on all 5 | `official.json` `cert` (Cómputos) | Section 7 (SACADOS) is not in the certified data. One of the five (156723B) was certified by recount, four by comparison (Cotejo). This replaces the earlier hand count in the spike README; the app shows the computed figure. |
| Paper inconsistency (not a keying error) | 211294C TOTAL: words 162, digits 262 | `adjudicate.json` + spike reads | The capture applied its words-prevail rule. Shown separately from keying errors and never counted with them. The same form's SACADOS (262 in words and digits, keyed 162) is a keying error on a routed form. |
| Routed, read perfectly | 7 (Gemma v2), 10 (Qwen) | the same | Rejected forms where every graded field equals the adjudicated truth. |
| Cost per form | $0.000118 (Gemma v2), $0.000507 (Qwen) | `usage.cost` in each result file | Mean over the 43 reads. |
| Per 1,000 forms | $0.12 / $0.51 | cost per form × 1,000 | |
| Audit of the national set | $20 to $86 | cost per form × 169,005 (cited, below) | |
| Mean latency | 49 s (Gemma v2), 85 s (Qwen) | `secs` in each result file | Wall-clock per request on the shared endpoint, including queueing. |
| Tokens per form | about 2,153 in / 641 out (Gemma), 8,739 / 1,667 (Qwen) | `usage.prompt_tokens / completion_tokens` | Means. |
| Ledger: sheets, cells | 40 sheets, 4,915 cells | `ledger/ledger.json` (built by `ledger/build.py` from `spikes/ledger-rescue`, which used the spike's own `evaluate.py`) | Cells where the volunteers have a value. |
| Ledger: year-columns accepted | 306 of 380 (80.5%) | the same | Tiled Gemma (`gemmatile`), no re-reads. The spike README's "81.6%" includes re-reads; the app shows 80.5%. |
| Ledger: accepted cells right | 3,976 of 3,976 | the same | Within 0.005 in of the volunteers. |
| Ledger: cost per sheet | $0.00011 | token counts × prices in `spikes/ledger-rescue/evaluate.py` | |
| Ledger failure case | 26 of 870 accepted cells wrong (single-image read) | `spikes/ledger-rescue/scores.json` `models.gemma` (copied into `ledger.json` meta) | Silent column shift, README §4. |
| Every-run table (results page) | all runs | every `results/*.jsonl` (core runs), the spike runs, live reads | Picked up automatically; see C. |
| Live reads (home, after the first one) | n, mean secs, mean cost | `app/state/live/*.json` | Written by the live button. |

## B. Cited (not measured by us)

| Shown as | Value | Source |
|---|---|---|
| National presidential tally forms | 169,005 | PREP 2024 CSV, https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip. Counted in `spikes/tally-witness/README.md` §1. |
| National capture programme cost | MXN 273,630,875 (MXN 273.6M) | La Jornada, 2024-05-26 ("36 millones 315 mil 225 pesos que se suman a los 237 millones 315 mil 650 pesos"), quoted in `spikes/tally-witness/README.md` §5. No USD conversion is shown because we have no cited exchange rate. |
| Every form keyed twice, third review on mismatch | (text) | nmas.com.mx, quoted in `spikes/tally-witness/README.md` §5 |
| Forms failing their own row sum | 19.2% (26,336 of 137,196) | PREP 2024 CSV, computed in `spikes/tally-witness/README.md` §1 |
| State-level counts in 2027 | ~32 | `spikes/tally-witness/README.md` §5 |
| One state capture contract | MXN 24.94M (Campeche 2024) | `spikes/tally-witness/README.md` §5 |
| AI-recognition pilot by a state institute | IEEQ Querétaro 2024, 264 polling stations | `spikes/tally-witness/README.md` §5 |
| Endpoint | AMD Token Factory, the organisers' AMD route | `notes/rules.md` |
| Throughput | ~2 forms/min under 6 req/min, 2-concurrent pacing | `spikes/tally-witness/README.md` §3 |
| Volunteers | ~16,000, 4 transcriptions per value | Hawkins et al., Geoscience Data Journal 2022, quoted in `spikes/ledger-rescue/README.md` §1 |

**Not shown:** a cost for a human keyer. We found no citable figure, so the business panel shows only our compute cost
and the cited programme cost.

## C. How a new run flows in

- Any `results/<name>.jsonl` is loaded on the next request (the store watches file mtimes). Rows are read by
  `store.read_from_core`, which accepts these forms:
  - `values/words/labels/accepted/reasons` (the `scripts/verify_spike.py` format),
  - `parsed` only (the raw `reader.read` row), gated with `twohands.gate.gate`,
  - `not_located`.
- Grading needs official values for each clave. The 43 spike forms are in `app/data/official.json`. For new forms, run
  `python -m app.build`. It reads the PREP and Cómputos CSVs (paths in `app/build.py`) and adds official values for
  every clave that appears in `results/*.jsonl`. Forms without official values show as "not graded".
- **Headline switch:** the home and results pages use the largest core run with at least 100 graded forms. Until one
  exists they use the spike's Gemma v2 run. The pre-registered 300-form run therefore takes over the headline as soon
  as its file and its official values exist. No code changes.
- Masked pages are found by filename (`<clave>.jpg`) anywhere under `data/masked/`.

## D. Images and licences

- **INE tally sheets.** The app serves only files under `data/masked/**`, produced by `twohands.mask`. Crops are cut
  from those masked pages only, and every crop box lies left of the privacy mask (`tests/test_app_routes.py`). Forms
  without a masked page show a placeholder. Reuse is under INE's free-use terms (Libre-Uso-MX, SICEE), with the source
  URL and consultation date in the footer, plus a statement that the app is not an official INE product.
- **Rainfall ledgers.** The source repository (github.com/ed-hawkins/rainfall-rescue) has no licence file, so no sheet
  image is copied. The app shows our extracted values only and links each sheet to its public PDF page with attribution.
  Zenodo lists the data as CC-BY-4.0; see `spikes/ledger-rescue/README.md` §1.
