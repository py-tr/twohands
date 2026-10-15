# POST-HOC: gate v2 / v2b re-scored on the stored Gemma reads of the 300

**Post-hoc.** Gate v2 was designed after seeing these 300 reads and their adjudication (PROTOCOL.md Amendment 3).
These numbers are NOT a test of v2; the pre-registered test is the fresh 100-form draw (`results/manifest_confirm100.json`).
No model was called: the stored Gemma reads (`results/calls_gemma.jsonl`, last row per form) are re-gated.
Truth: a verdict in `results/adjudication/verdicts.json` decides; with no verdict, model = PREP counts as correct and
model != PREP is flagged for adjudication. Graded fields: the 22 with a PREP column.

Recomputed v1 vs the stored `accepted` flag: 0 mismatches.
Qwen reads available for v2-2R: 40 of 300 (the Qwen pass is still running; a form without a Qwen read
cannot be confirmed by Qwen, so v2-2R is a lower bound until the pass ends).

| gate | touchless forms (/300) | Movil / Escaner | accepted fields | errors | error rate (Wilson 95%) | undecided | flagged |
|---|---|---|---|---|---|---|---|
| v1 (frozen gate) | 55 | 27 / 28 | 1210 | 2 | 0.17% (0.04-0.60%) | 0 | 0 |
| v2 | 47 | 24 / 23 | 1034 | 1 | 0.10% (0.02-0.55%) | 0 | 0 |
| v2-2R (Qwen confirms SOBRANTES) | 47 | 24 / 23 | 1034 | 1 | 0.10% (0.02-0.55%) | 0 | 0 |
| v2b (relaxed label, secondary) | 62 | 39 / 23 | 1364 | 1 | 0.07% (0.01-0.41%) | 0 | 0 |

## v1 (frozen gate)
- errors: 010469C0400 SOBRANTES: model 239, PREP 234, paper 234 (capture_right); 212668C0300 SOBRANTES: model 300, PREP 379, paper 379 (capture_right)
- undecided (ambiguous/unreadable/crop): none
- flagged for adjudication (model != PREP, no verdict): none

## v2
- errors: 010469C0400 SOBRANTES: model 239, PREP 234, paper 234 (capture_right)
- undecided (ambiguous/unreadable/crop): none
- flagged for adjudication (model != PREP, no verdict): none

## v2-2R (Qwen confirms SOBRANTES)
- errors: 010469C0400 SOBRANTES: model 239, PREP 234, paper 234 (capture_right)
- undecided (ambiguous/unreadable/crop): none
- flagged for adjudication (model != PREP, no verdict): none

## v2b (relaxed label, secondary)
- errors: 010469C0400 SOBRANTES: model 239, PREP 234, paper 234 (capture_right)
- undecided (ambiguous/unreadable/crop): none
- flagged for adjudication (model != PREP, no verdict): none

## Lines
> POST-HOC v2 on the 300: 47 touchless forms (v1: 55), 1034 accepted fields, 1 errors (0.10%), 0 flagged for adjudication.
> POST-HOC v2b on the 300: 62 touchless forms (v1: 55), 1364 accepted fields, 1 errors (0.07%), 0 flagged for adjudication.
