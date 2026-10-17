# Every number in the web app, and where it comes from

Vote rows are shown as "Option 01" to "Option 15" (printed order). The app never shows party names, in HTML or in JSON.
The app computes measured numbers at request time (`app/store.py`, `app/numbers.py`) from results files. It does not
type them in. Cited context numbers are constants in `app/numbers.py` (`CITED`), and each one carries its source.
This file lists both kinds. Values below are as of 2026-10-15; if a results file changes, the page changes with it.

## A. Headline: the pre-registered 300 (one computed summary)

`scripts/build_headline.py` computes every number below into `app/data/headline.json` from `results/calls_gemma.jsonl`
(last read per form), the PREP and Computos CSVs, and `results/adjudication/` (verdicts.json, certified.json). The
Overview, Inbox, Audit and Results pages all read that one file, so they cannot disagree.

| Shown as | Value now | Method |
|---|---|---|
| Fields where the official capture does not match the paper (capture errors) | 52 in 6,358 fields: 17 wrong numbers, 27 readable fields recorded as illegible (23 on two faint forms), 6 typed where blank, 2 other | verdict `model_right`: the paper shows the model's value |
| Certified confirmation | covers 31, confirms 22; all 9 differences recounts | `scripts/certified_check.py` -> CERTIFIED.md |
| The model alone | 173 of 6,358 wrong, about 1 in 37 | verdicts `capture_right` (156) + `neither` (17) |
| The capture typed a wrong number | 17 of 6,358, 1 in 374 | type "wrong numbers typed" of the 52 |
| On the forms the gate accepts | 55 of 300 (18%); 2 of 1,210 fields wrong, about 1 in 605 | frozen gate, stored `accepted` |
| Yield | 52 of 267 disputed = 1 in 5; overall capture error rate at least 52 of 6,358 = 1 in 122; the multiple depends on recall on the random 300, not measured there; up to 24x if the model finds nearly every error (EVALUATION) | |
| Audit line (business case, slide 9b) | in the preliminary capture (PREP, before the cómputos and any later cotejo correction), at least 0.8% of fields in the random sample do not match the paper (52 of 6,358, 0.82%); 1 in 5 disputes (52 of 267, 19.5%) is a capture error | `keying_errors` / `fields` and `keying_errors` / `disagree` in `app/data/headline.json`; the capture is the published PREP 2024 CSV |
| Fields to look at | 267 of 6,358 = 4.2% | model digits != PREP |
| Agreement with the capture | 6,091 of 6,358 = 95.80% | |
| Recall (Colima, Amendment 9) | 27 of 28 certified-detectable capture errors caught, 96% (Wilson 82-99%), a person's blind check of all 139 candidates; one state, not total recall | results/colima/recall.json / .md |
| Recall (random 300, history) | loose bound 7 of 23 (Wilson 16-51%); judged on the paper, 16 are corrections, the model disputed 7 of 7, of which 1 is a confirmed capture error and 6 are ambiguous on the paper: too few to measure recall there | forms certified by comparison (Cotejo); vote rows + TOTAL; RECALL.md |
| 52 by type | wrong numbers 17; readable recorded as illegible 27; typed where blank 6; other 2 | from PREP's keyed text and the paper value |
| Cost per form (Gemma) | $0.000144; $0.14 per 1,000; ~$24 compute cost for 169,005 forms | mean `cost_usd` over the 289 reads |

## A2. Pilot (43 hand-picked forms) and spikes (computed from results files)

| Shown as | Value now | Computed from | Method |
|---|---|---|---|
| Pilot accept rate (results, pilot table) | 49% = 21 of 43 forms | `app/data/spike_runs.json`, a snapshot of `results/pilot/tally-witness/results_v2/gemma__*.json` | Gate = completeness + words = digits + the 4 schema identities (`schemas/mx_presidencia_2024.yaml`). Same checks as the spike's `score.py` FULL gate. The spike reads predate the row-label check. |
| Accepted fields wrong | 0 of 462 (Gemma), 0 of 484 (Qwen) | the same, plus `app/data/official.json` (from `data/pilot/tally-witness/truth_rows.json` and `adjudicate.json`) | 22 graded fields per form against the PREP capture. "After eye check" swaps in the fields in `adjudicate.json`. Raw disagreements: 5 (Gemma), 4 (Qwen). |
| Pilot capture errors | 6 fields on 5 forms | `adjudicate.json` entries on forms that a spike reader accepted | 093954C0200, 156723B0100, 202451B0100 (TOTAL and section 7), 211298B0100, 211420C0400. The app labels vote rows "Option NN" and never by party. |
| Certified count | covers 5 of the 6 fields and matches the image on all 5 | `official.json` `cert` (Cómputos) | Section 7 (SACADOS) is not in the certified data. One of the five (156723B) was certified by recount, four by comparison (Cotejo). This replaces the earlier hand count in the spike README; the app shows the computed figure. |
| Paper inconsistency (not a capture error) | 211294C TOTAL: words 162, digits 262 | `adjudicate.json` + spike reads | The capture applied its words-prevail rule. Shown separately from capture errors and never counted with them. The same form's SACADOS (262 in words and digits, keyed 162) is a capture error on a routed form. |
| Routed, read perfectly | 7 (Gemma v2), 10 (Qwen) | the same | Rejected forms where every graded field equals the adjudicated truth. |
| Cost per form | $0.000118 (Gemma v2), $0.000507 (Qwen) | `usage.cost` in each result file | Mean over the 43 reads. |
| Per 1,000 forms | $0.12 / $0.51 | cost per form × 1,000 | |
| Compute cost to audit the national set, at pilot costs | about $20 (Gemma) / $86 (Qwen) for 169,005 forms | pilot cost per form × 169,005 (cited, below) | The headline uses the costs measured on the 300: about $24 (Gemma, A1 above) and about $101 (Qwen, $0.000597, `results/gemma_vs_qwen.md`). |
| Mean latency | 49 s (Gemma v2), 85 s (Qwen) | `secs` in each result file | Wall-clock per request on the shared endpoint, including queueing. |
| Tokens per form | about 2,153 in / 641 out (Gemma), 8,739 / 1,667 (Qwen) | `usage.prompt_tokens / completion_tokens` | Means. |
| Ledger: sheets, cells | 40 sheets, 4,915 cells | `ledger/ledger.json` (built by `ledger/build.py` from the pilot copies in `data/pilot/ledger-rescue` and `results/pilot/ledger-rescue`, which used the spike's own `evaluate.py`) | Cells where the volunteers have a value. |
| Ledger: year-columns accepted | 306 of 380 (80.5%) | the same | Tiled Gemma (`gemmatile`), no re-reads. The spike README's "81.6%" includes re-reads; the app shows 80.5%. |
| Ledger: accepted cells right | 3,976 of 3,976 (spike, 40 sheets) | the same | Within 0.005 in of the volunteers. |
| Ledger: cost per sheet | $0.00011 | token counts × prices in `docs/sources/ledger-rescue-pilot.md, appendix` | |
| Ledger failure case | 26 of 870 accepted cells wrong (single-image read) | `data/pilot/ledger-rescue/scores.json` `models.gemma` (copied into `ledger.json` meta) | Silent column shift, README §4. |
| Every-run table (results page) | all runs | every `results/*.jsonl` (core runs), the spike runs, live reads | Picked up automatically; see C. |
| Live reads (home, after the first one) | n, mean secs, mean cost | `app/state/live/*.json` | Written by the live button. |

## B. Cited (not measured by us)

| Shown as | Value | Source |
|---|---|---|
| National presidential tally forms | 169,005 | PREP 2024 CSV, https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip. Counted in [sources/tally-witness-pilot.md](sources/tally-witness-pilot.md) §1. |
| Every form keyed twice, third review on mismatch | (text) | nmas.com.mx, quoted in [sources/tally-witness-pilot.md](sources/tally-witness-pilot.md) §5 |
| Forms failing their own row sum | 19.2% (26,336 of 137,196) | PREP 2024 CSV, computed in [sources/tally-witness-pilot.md](sources/tally-witness-pilot.md) §1 |
| State-level counts in 2027 | ~32 | [sources/tally-witness-pilot.md](sources/tally-witness-pilot.md) §5 |
| AI-recognition pilot by a state institute | IEEQ Querétaro 2024, 264 polling stations | [sources/tally-witness-pilot.md](sources/tally-witness-pilot.md) §5 |
| Endpoint | AMD Token Factory, the organisers' AMD route | [docs/sources/event-rules.md](sources/event-rules.md) |
| Throughput | ~2 forms/min under 6 req/min, 2-concurrent pacing | [sources/tally-witness-pilot.md](sources/tally-witness-pilot.md) §3 |
| PREP second capture by a person, system comparison (PTO numeral 33); third capture on mismatch (34); Centro de Verificación (35); automatic first capture allowed (30); cotejo (4 f, 3 j, 45) | INE federal PTO 2023-2024, quoted verbatim in docs/BUSINESS.md section 0 | https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/155635/CGex202311-03-ap-8-a.pdf |
| State PREPs: minimum phases captura and verificación (Anexo 13 num. 15 III-IV), roles capturista and verificador (num. 21 III-IV); each OPL approves its own PTO (RE art. 339.1 d), system may be built by third parties (art. 346.1) | Reglamento de Elecciones, consolidated Sept 2026; Anexo 13 as modified by INE/CG825/2022 (latest per INE Dirección Jurídica, Feb 2025) | https://sidj.ine.mx/restWSsidj-nc/app/doc/662/20/1; https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/146752/CGor202211-29-ap-25-a.pdf; https://ine.mx/wp-content/uploads/2025/02/DJ-Anexos-ReglamentoElecciones-05-02-25.pdf |
| 2024 state PREPs: IEEBCS took a Google Document AI reading as first capture, matching the manual capture on 14,501 of 23,077 fields (62.84%), 65 of 2,254 actas (2.88%); 2,254 of 2,256 actas captured. IMPEPAC: operator Informática Electoral S.C. (IMPEPAC/LP/001/2024); actas captured 2,476 / 2,525 / 2,507 (gubernatura / diputaciones / ayuntamientos) | OPLE final PREP reports, quoted in docs/BUSINESS.md section 0b | https://www.ieebcs.org.mx/documentos/acuerdos/INFORME_FINAL_PREP_PLE_2023-2024.pdf pp. 6, 18-19; https://impepac.mx/wp-content/uploads/2024/07/Informe%20Final%20PREP_23-24_V_2.0.pdf pp. 3-4; https://impepac.mx/wp-content/uploads/2024/04/Informe_Marzo-2024_PREP.pdf p. 19 |
| Outside audit of every PREP; 26 of 32 state institutes had named one in Feb 2024, all academic or research | Reglamento de Elecciones art. 347 numerals 1-2 (preference to academic or research institutions) | IEEH/CG/022/2024, https://ieehidalgo.org.mx/images/sesiones/2024/Febrero/IEEH-CG-022-2024.pdf; INE annex 5, https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf |
| UNAM centres audited 2024 state PREPs | Aguascalientes, Mexico City, Hidalgo, Puebla, Querétaro, Veracruz | INE annex 5, https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf |
| 2027 window | federal election + 32 concurrent local processes; election day 6 June 2027 | INE Central Electoral 2026-07-30 and 2026-07-31 (URLs in `app/numbers.py` `window_2027`) |
| Site monitoring and source document verification | 15-30% of clinical-trial costs | Lindblad et al. (incl. Ball), Clinical Trials 2014; 11: 205-217, https://www.acepidemiology.org/assets/docs/Ball%20Clinical%20Trials%202014.pdf |
| Proposed price (a proposal, not measured) | $1 per sheet audited (proposed); first step: a paid shadow-mode pilot | app/pricing.py; docs/BUSINESS.md section 2 |
| FX for every MXN / USD conversion | MXN 18.3835 per USD (ECB, 2026-10-16) | https://api.frankfurter.app/latest?from=USD&to=MXN (ECB reference rate, fetched 2026-10-16) |
| INE's 2024 acceptance metric as we read it (primary, per field) | see results/ine_metric.md | scripts/ine_metric.py; definition results/ine_metric_DEFINITION.md |
| PREP vs certified count, not-recounted stations differing | see results/national_counts.md | scripts/national_counts.py |
| Volunteers | ~16,000, 4 transcriptions per value | Hawkins et al., Geoscience Data Journal 2022, quoted in [sources/ledger-rescue-pilot.md](sources/ledger-rescue-pilot.md) §1 |

**Not shown:** a cost for a human keyer. We found no citable figure, so the business panel shows only our compute cost.

## C. How a new run flows in

- Any `results/<name>.jsonl` is loaded on the next request (the store watches file mtimes). Rows are read by
  `store.read_from_core`, which accepts these forms:
  - `values/words/labels/accepted/reasons` (the `scripts/verify_spike.py` format),
  - `parsed` only (the raw `reader.read` row), gated with `twohands.gate.gate`,
  - `not_located`.
- Grading needs official values for each clave. The 43 spike forms are in `app/data/official.json`. For new forms, run
  `python -m app.build`. It reads the PREP and Cómputos CSVs (paths in `app/build.py`) and adds official values for
  every clave that appears in `results/*.jsonl`. Forms without official values show as "not graded".
- **Headline:** the Overview, Inbox, Audit and Results pages show the pre-registered 300 from `app/data/headline.json`
  (rebuild it with `python scripts/build_headline.py` after any change to the reads or verdicts).
- Masked pages are found by filename (`<clave>.jpg`) anywhere under `data/masked/`.

## D. Images and licences

- **INE tally sheets.** The app serves only files under `data/masked/**`, produced by `twohands.mask`. Crops are cut
  from those masked pages only, and every crop box lies left of the privacy mask (`tests/test_app_routes.py`). Forms
  without a masked page show a placeholder. Reuse is under INE's free-use terms (Libre-Uso-MX, SICEE), with the source
  URL and consultation date in the footer, plus a statement that the app is not an official INE product.
- **Rainfall ledgers.** The source repository (github.com/ed-hawkins/rainfall-rescue) has no licence file, so no sheet
  image is copied. The app shows our extracted values only and links each sheet to its public PDF page with attribution.
  Zenodo lists the data as CC-BY-4.0; see [sources/ledger-rescue-pilot.md](sources/ledger-rescue-pilot.md) §1.
