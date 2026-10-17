# Colima, complete-state audit on the AMD Token Factory (PROTOCOL.md Amendment 8b)

**Colima, whole state: 381 of 1017 presidential actas accepted under the frozen gate (982 located), 13 wrong of 8,382 accepted fields (13 AI adjudicator's reading).**

Gemma-4-31B-IT, frozen prompt, page + 6 tiles, temperature 0, one read per form. Truth: the certified count (Computos, cotejo forms only, and only where it equals Gemma's reading or the capture's), else the AI adjudicator's reading of the masked crop; a field where Gemma equals the capture counts as right. Gates as pre-registered: v1 primary, v2, v3. There is no second reader for Colima, so v3's two-read rule fails on every form and every unused-ballots field goes to a person under v3.

| gate | forms accepted (% of PREP rows / of located) | touchless | Movil / Escaner | accepted fields | wrong (Wilson 95%) | wrong by label | awaiting adjudication | paper ambiguous |
|---|---|---|---|---|---|---|---|---|
| v1 (frozen gate, primary) | 381 (37.5% / 38.8%) | 381 | 267 / 114 | 8,382 | 13 (0.09% to 0.27%) | 13 AI adjudicator's reading | 0 | 3 |
| v2 (Amendment 3) | 344 (33.8% / 35.0%) | 344 | 247 / 97 | 7,568 | 7 (0.04% to 0.19%) | 7 AI adjudicator's reading | 0 | 2 |
| v3 (Amendment 7; no second reader, so SOBRANTES always to a person) | 388 (38.2% / 39.5%) | 0 | 272 / 116 | 8,148 | 4 (0.02% to 0.13%) | 4 AI adjudicator's reading | 0 | 2 |

Wrong accepted fields, each with who decided:

- v1: 060058B0100 Unused ballots read 268, capture 208, paper 208 [AI adjudicator's reading]; 060111B0100 Unused ballots read 29, capture 291, paper 291 [AI adjudicator's reading]; 060151B0100 Unused ballots read 227, capture 229, paper 229 [AI adjudicator's reading]; 060239C0100 Unused ballots read 47, capture 247, paper 247 [AI adjudicator's reading]; 060242B0100 Unused ballots read 30, capture 307, paper 307 [AI adjudicator's reading]; 060248E0208 Unused ballots read 44, capture 344, paper 344 [AI adjudicator's reading]; 060248E0208 Ballots taken from the boxes read 381, capture 384, paper 384 [AI adjudicator's reading]; 060248E0208 TOTAL read 381, capture 384, paper 384 [AI adjudicator's reading]; 060290C0400 Unused ballots read 369, capture 364, paper 364 [AI adjudicator's reading]; 060290C0400 Option 05 read 10, capture 16, paper 16 [AI adjudicator's reading]; 060291C0400 Unused ballots read 301, capture 387, paper 387 [AI adjudicator's reading]; 060369C0100 Ballots taken from the boxes read 294, capture 291, paper 291 [AI adjudicator's reading]; 060374B0100 Unused ballots read 79, capture 179, paper 179 [AI adjudicator's reading]
- v2: 060058B0100 Unused ballots read 268, capture 208, paper 208 [AI adjudicator's reading]; 060111B0100 Unused ballots read 29, capture 291, paper 291 [AI adjudicator's reading]; 060151B0100 Unused ballots read 227, capture 229, paper 229 [AI adjudicator's reading]; 060239C0100 Unused ballots read 47, capture 247, paper 247 [AI adjudicator's reading]; 060290C0400 Unused ballots read 369, capture 364, paper 364 [AI adjudicator's reading]; 060290C0400 Option 05 read 10, capture 16, paper 16 [AI adjudicator's reading]; 060374B0100 Unused ballots read 79, capture 179, paper 179 [AI adjudicator's reading]
- v3: 060248E0208 Ballots taken from the boxes read 381, capture 384, paper 384 [AI adjudicator's reading]; 060248E0208 TOTAL read 381, capture 384, paper 384 [AI adjudicator's reading]; 060290C0400 Option 05 read 10, capture 16, paper 16 [AI adjudicator's reading]; 060369C0100 Ballots taken from the boxes read 294, capture 291, paper 291 [AI adjudicator's reading]

Route causes (forms routed, by cause; a form can have several):

- v1: 601 forms routed (identity 418, label 164, words 151, empty 131, shape 5)
- v2: 638 forms routed (identity 418, unchecked 179, label 164, words 151, empty 131, shape 5)
- v3: 594 forms routed (identity 418, label 164, words 136, empty 127, shape 5); 388 accepted forms send unused ballots to a person

Disagreements with the first capture on graded fields: 510, by label (never pooled):

- AI adjudicator's reading: capture right (model misread): 58
- AI adjudicator's reading: model right (capture error): 12
- AI adjudicator's reading: neither: 3
- awaiting the AI adjudicator (not sampled): 334
- confirmed by the certified count: capture right (model misread): 69
- confirmed by the certified count: model right (capture error): 27
- paper ambiguous or unreadable: 7

AI adjudication: 80 of the 414 disagreements the certified count does not settle (every disagreement on a field some gate accepts (census: these decide the error counts), then a seeded random draw from the rest up to 80 in all: random.Random(20261017).sample(sorted keys, 80 - census); census 21, draw 59); 80 adjudicated, 0 of the sample still pending, 334 not sampled and pending (`results/colima/pending.json`). Sheet: `results/colima/SHEET.md`; verdicts: `results/colima/verdicts.json`.

Paper ambiguous or unreadable (excluded from both error counts):

- 060024C0100 Voters on the list: no words; digit boxes 3, an open 'c' stroke, 2: the middle box reads as 6 or 0 (`results/colima/crops/060024C0100__VOTARON.jpg`)
- 060024C0200 Unused ballots: no words; digit boxes 3 8 and a flat-topped stroke with a curved base that reads as 3 or 2 (the first 3 is written round) (`results/colima/crops/060024C0200__SOBRANTES.jpg`)
- 060178C0100 Ballots taken from the boxes: very faint page; words partly legible ('... sesenta y seis'?), digit boxes not legible (`results/colima/crops/060178C0100__SACADOS.jpg`)
- 060243C0100 Unused ballots: no words; a 1 written left of the three boxes, then 6 1 2 in the boxes: 1612 or 612 (`results/colima/crops/060243C0100__SOBRANTES.jpg`)
- 060251C0200 Option 03: words 'Cero'; digit boxes 0, a pinched loop that reads as 8 or 0, 0 (`results/colima/crops/060251C0200__OPT03.jpg`)
- 060290C0400 Option 13: words unclear (possibly 'cuatro'); digit boxes 0 0 and a last box written over (4 and 6 superimposed) (`results/colima/crops/060290C0400__OPT13.jpg`)
- 060396B0100 Voters on the list: no words; digit boxes written over several times (3, 7, then 8 or 4), with other figures above the field (`results/colima/crops/060396B0100__VOTARON.jpg`)

PREP rows 1017; located 982; read and parsed 982; not located or no image 35 (routed, never replaced: listed in the JSON); also in other sets (flagged, not double-counted): 2 (060022C0100: calibration 150; 060079C0300: the 300).

Report from the /audit/new generator: `results/colima/audit_report.html` / `.csv` (audit a4aff8e574023): 982 forms read, 21604 fields checked, 510 disputed on 238 forms; tiers {'strong': 64, 'medium': 193, 'weak': 253}; report fingerprint (SHA-256) `5b3b610ed4a98d0d6484527b5746cb59da687394d66a689f3e32e93bcfcfe62b`, Merkle root of the disputes `f92ffa9246f0c75758bc6d5e855129fe837d667c6ba4d2bf4bce4db501ac5e43`.
