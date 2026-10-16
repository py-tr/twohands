# Pre-registered confirmation: gate v2 on 100 fresh forms (Amendment 3), gate v3 (Amendment 7)

Built by `scripts/confirm100_score.py`; `make eval` recomputes it (`--check`). No model call: the stored Gemma reads
(`results/calls_confirm100_gemma.jsonl`, last row per form) are gated by the frozen gate, gate v2 / v2b
(`twohands/gate_v2.py`) and gate v3 (`twohands/gate_v3.py`), all committed before any read of the 100.
Manifest `results/manifest_confirm100.json` (seed 20261017; 66 Movil, 34 Escaner).
Gemma-4-31B-IT read 100 of 100: 97 parsed, 3 pages unlocated (090602C0200, 110266B0100, 240998C0200; routed, never replaced). Unlocated pages and failed reads stay in every denominator.
Recomputed v1 vs the stored `accepted` flag: 0 mismatches.
Qwen3.8-27B reads: **none** (the Qwen pass of Amendment 3 was not run). So v2-2R equals v2 here, and under gate v3 the two-read rule (b) fails on every form ("No usable second read = (b) fails"): **every SOBRANTES goes to a person under v3**; v3 accepts only the other 22 fields.

**Truth (Amendment 2 / section 6).** Every graded field on an accepted form (any gate above) where Gemma
disagrees with the PREP capture was adjudicated on its masked crop (`results/adjudication_confirm100/`: SHEET.md,
the crops, `verdicts.json`; the certified Computos count is shown where it exists). **Adjudicator: an AI (an AI model)
looking at the published crops, labelled as such**; every crop is committed for anyone to re-judge. With no
verdict, read = PREP counts as correct. Verdicts: 3 (capture_right 2, model_right 1).

**Success criterion (pre-registered, primary = Gemma single-reader v2): accepted-field error rate after adjudication <= 0.5%** (Amendment 3; the same bar for v3, Amendment 7).

| gate | forms accepted (/100) | touchless (all 23) | Movil / Escaner | accepted graded fields | errors | error rate (Wilson 95%) | undecided | flagged | SOBRANTES to a person (wrong / correct) |
|---|---|---|---|---|---|---|---|---|---|
| v1 (frozen gate, section 5) | 23 | 23 | 15 / 8 | 506 | 1 | 0.20% (0.03-1.11%) | 0 | 0 | 0 (0 / 0) |
| v2 (primary, Amendment 3) | 22 | 22 | 14 / 8 | 484 | 0 | 0.00% (0.00-0.79%) | 0 | 0 | 0 (0 / 0) |
| v2-2R (Qwen digits may confirm SOBRANTES) | 22 | 22 | 14 / 8 | 484 | 0 | 0.00% (0.00-0.79%) | 0 | 0 | 0 (0 / 0) |
| v2b (relaxed logo-row labels, secondary) | 29 | 29 | 21 / 8 | 638 | 0 | 0.00% (0.00-0.60%) | 0 | 0 | 0 (0 / 0) |
| v3 (Amendment 7: words + two reads + stock band) | 24 | 0 | 15 / 9 | 504 | 0 | 0.00% (0.00-0.76%) | 0 | 0 | 24 (2 / 22) |
| v3-emax (secondary: E in [0, E_max]) | 24 | 0 | 15 / 9 | 504 | 0 | 0.00% (0.00-0.76%) | 0 | 0 | 24 (2 / 22) |
| v3 part: words + stock band (no two-read rule) | 24 | 21 | 15 / 9 | 525 | 0 | 0.00% (0.00-0.73%) | 0 | 0 | 3 (2 / 1) |

## v1 (frozen gate, section 5)
- errors: 070212B0100 SOBRANTES: read 3114, PREP 314, paper 314
- undecided (ambiguous / unreadable / crop): none
- flagged (read != PREP, no verdict): none

## v2 (primary, Amendment 3)
- errors: none
- undecided (ambiguous / unreadable / crop): none
- flagged (read != PREP, no verdict): none

## v2-2R (Qwen digits may confirm SOBRANTES)
- errors: none
- undecided (ambiguous / unreadable / crop): none
- flagged (read != PREP, no verdict): none

## v2b (relaxed logo-row labels, secondary)
- errors: none
- undecided (ambiguous / unreadable / crop): none
- flagged (read != PREP, no verdict): none

## v3 (Amendment 7: words + two reads + stock band)
- errors: none
- undecided (ambiguous / unreadable / crop): none
- flagged (read != PREP, no verdict): none
- wrong SOBRANTES caught (sent to a person): 070212B0100 (read 3114, PREP 314); 152285C0100 (read 207, PREP 217)

## v3-emax (secondary: E in [0, E_max])
- errors: none
- undecided (ambiguous / unreadable / crop): none
- flagged (read != PREP, no verdict): none
- wrong SOBRANTES caught (sent to a person): 070212B0100 (read 3114, PREP 314); 152285C0100 (read 207, PREP 217)

## v3 part: words + stock band (no two-read rule)
- errors: none
- undecided (ambiguous / unreadable / crop): none
- flagged (read != PREP, no verdict): none
- wrong SOBRANTES caught (sent to a person): 070212B0100 (read 3114, PREP 314); 152285C0100 (read 207, PREP 217)

## Lines

> Confirmation: the pre-registered confirmation on 100 fresh forms: gate v2 accepted 22 forms, 0 of 484 accepted fields wrong; criterion met.
> Also: gate v3 (Amendment 7, pre-registered before these reads) accepted the other 22 fields on 24 forms (0 touchless), 0 of 504 accepted fields wrong; criterion met; 24 SOBRANTES sent to a person (no second reader was run, so the two-read rule routes every SOBRANTES).
