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

- AI adjudicator's reading: capture right (model misread): 236
- AI adjudicator's reading: model right (capture error): 83
- AI adjudicator's reading: neither: 14
- confirmed by the certified count: capture right (model misread): 69
- confirmed by the certified count: model right (capture error): 27
- paper ambiguous or unreadable: 81

AI adjudication: 80 of the 414 disagreements the certified count does not settle (every disagreement on a field some gate accepts (census: these decide the error counts), then a seeded random draw from the rest up to 80 in all: random.Random(20261017).sample(sorted keys, 80 - census); census 21, draw 59); 80 adjudicated, 0 of the sample still pending, 0 not sampled and pending (`results/colima/pending.json`). Sheet: `results/colima/SHEET.md`; verdicts: `results/colima/verdicts.json`.

Paper ambiguous or unreadable (excluded from both error counts):

- 060024C0100 Voters on the list: no words; digit boxes 3, an open 'c' stroke, 2: the middle box reads as 6 or 0 (`results/colima/crops/060024C0100__VOTARON.jpg`)
- 060024C0200 Unused ballots: no words; digit boxes 3 8 and a flat-topped stroke with a curved base that reads as 3 or 2 (the first 3 is written round) (`results/colima/crops/060024C0200__SOBRANTES.jpg`)
- 060038C0100 Option 09: words 'Dos', digit boxes 0 0 and a final digit shaped like a 7 (the row above, 'Siete', has the same shape): words and digits disagree (`results/colima/crops/060038C0100__OPT09.jpg`)
- 060038C0100 Option 15: words 'Dos', digit boxes 0 0 and a final digit shaped like a 7 with a short foot: words and digits disagree (`results/colima/crops/060038C0100__OPT15.jpg`)
- 060038C0100 Option 13: words 'Cero', digit boxes 0 0 6: words and digits disagree (`results/colima/crops/060038C0100__OPT13.jpg`)
- 060046C0100 Ballots taken from the boxes: no words; digit boxes 2 8 and a last digit written over (3 and 7 on top of each other) (`results/colima/crops/060046C0100__SACADOS.jpg`)
- 060046C0100 Unused ballots: no words; digit boxes 6 and 5 clear, first digit written over in darker ink (1 or 2) (`results/colima/crops/060046C0100__SOBRANTES.jpg`)
- 060060C0400 Unused ballots: digit boxes empty; faint pencil figures '077' on the words line and another faint figure below it (`results/colima/crops/060060C0400__SOBRANTES.jpg`)
- 060067C0100 Unused ballots: no words; digit boxes 2 then two digits written over in heavy ink (0 or 8, then 0 or 9) (`results/colima/crops/060067C0100__SOBRANTES.jpg`)
- 060069C0500 Option 01: words 'Cuarenta y seis', digit boxes 0 1 6: words and digits disagree (`results/colima/crops/060069C0500__OPT01.jpg`)
- 060073C0200 Option 07: words 'Ciento treinta y cuatro', digit boxes 1 3 1 (faint): words and digits disagree (`results/colima/crops/060073C0200__OPT07.jpg`)
- 060073C0200 Option 01: words 'Treinta y cuatro', digit boxes 0 3 1 (faint): words and digits disagree (`results/colima/crops/060073C0200__OPT01.jpg`)
- 060073C0200 Option 02: words 'Veintidos', digit boxes 0 2 1: words and digits disagree (`results/colima/crops/060073C0200__OPT02.jpg`)
- 060086B0100 Option 07: words too faint to read on a folded page; digit boxes 1 3 and a faint last digit (2 or 0) (`results/colima/crops/060086B0100__OPT07.jpg`)
- 060087E0100 Voters on the list: words 'Ciento dies', digit boxes 1 2 0: words and digits disagree (`results/colima/crops/060087E0100__VOTARON.jpg`)
- 060093E0100 TOTAL: words 'Doscientos ochenta y tres', digit boxes 2, a middle digit between 2 and 8, 3 (`results/colima/crops/060093E0100__TOTAL.jpg`)
- 060105B0100 Option 03: words 'Ocho', digit boxes 0 0 6: words and digits disagree (`results/colima/crops/060105B0100__OPT03.jpg`)
- 060105E0100 Option 05: words 'Veintinueve', digit boxes 0 2 0: words and digits disagree (`results/colima/crops/060105E0100__OPT05.jpg`)
- 060125B0100 Ballots taken from the boxes: no words; digit boxes very faint: a first digit (1 or 4), 4, 6 (`results/colima/crops/060125B0100__SACADOS.jpg`)
- 060126C0100 Voters on the list: no words; digit boxes faint: a first digit (2 or 3), 2, 5 (`results/colima/crops/060126C0100__VOTARON.jpg`)
- 060128B0100 TOTAL: words 'Dosnoventa y tres', digit boxes 2 9 and a last digit shaped between 2 and 3 (Z-like, with a stroke below) (`results/colima/crops/060128B0100__TOTAL.jpg`)
- 060135B0100 Option 02: words 'Ochenta y seis', digit boxes 0, a middle digit between 8 and 9, 6 (`results/colima/crops/060135B0100__OPT02.jpg`)
- 060139E0201 Unused ballots: words 'Trescientos cuarenta y ocho', digit boxes 3, a closed-top middle digit (4 or 9), 8 (`results/colima/crops/060139E0201__SOBRANTES.jpg`)
- 060146B0100 Unused ballots: words 'Doscientos ochenta y uno', digit boxes 2 8 7: words and digits disagree (`results/colima/crops/060146B0100__SOBRANTES.jpg`)
- 060152E0300 Ballots taken from the boxes: words 'Trescientos setenta y ocho', digit boxes 3 7 6: words and digits disagree (`results/colima/crops/060152E0300__SACADOS.jpg`)
- 060156B0100 Voters on the list: words 'Doscientos treinta y siete', digit boxes 0 3 7: words and digits disagree (`results/colima/crops/060156B0100__VOTARON.jpg`)
- 060162B0100 Voters on the list: words 'Trecientos setenta y uno', digit boxes 3 7 and a last digit written over (1 and 6 on top of each other) (`results/colima/crops/060162B0100__VOTARON.jpg`)
- 060171B0100 Voters on the list: words 'Trescientos treinta y tres', digit boxes 3, a middle digit gone over in heavy ink (8 or 0), 3 (`results/colima/crops/060171B0100__VOTARON.jpg`)
- 060174C0100 TOTAL: no words; digit boxes with the first digit blotted out, then 9 0 (`results/colima/crops/060174C0100__TOTAL.jpg`)
- 060178C0100 Ballots taken from the boxes: very faint page; words partly legible ('... sesenta y seis'?), digit boxes not legible (`results/colima/crops/060178C0100__SACADOS.jpg`)
- 060182C0100 Voters on the list: words 'Docientos ochenta y tres', digit boxes 2 8 and a last digit written over (3 and 7 on top of each other) (`results/colima/crops/060182C0100__VOTARON.jpg`)
- 060206B0100 Option 02: words 'Veinte' written over another word, digit boxes 0, a middle digit written over (2 and 8 on top of each other), 0 gone over (`results/colima/crops/060206B0100__OPT02.jpg`)
- 060206C0100 Voters on the list: words 'Docientos noventa y uno', digit boxes 2 9 and a Z-shaped last digit (2-like): words and digits disagree (`results/colima/crops/060206C0100__VOTARON.jpg`)
- 060208B0100 Voters on the list: words 'Docientos dies y seis', digit boxes 2 1 and a last digit written over (5 and 6 on top of each other) (`results/colima/crops/060208B0100__VOTARON.jpg`)
- 060223C0100 Voters on the list: words 'Doscientos cincuenta', digit boxes 2 5 1: words and digits disagree (`results/colima/crops/060223C0100__VOTARON.jpg`)
- 060224B0100 Unregistered candidates: row left blank: no words, empty digit boxes; Gemma's 0 against an empty capture is the blank=0 convention (`results/colima/crops/060224B0100__NO_REGISTRADAS.jpg`)
- 060226E0200 Option 06: words 'diecinueve' written over another word, digit boxes 0 1 and a last digit written over (9 and 4 on top of each other) (`results/colima/crops/060226E0200__OPT06.jpg`)
- 060228B0100 Unused ballots: no words; digit boxes 2 6 and an open S-shaped last digit (5 or 8) (`results/colima/crops/060228B0100__SOBRANTES.jpg`)
- 060228E0300 Option 10: words 'Cero', digit boxes 0 0 6: words and digits disagree (`results/colima/crops/060228E0300__OPT10.jpg`)
- 060228E0300 Option 14: words 'Cero', digit boxes 0 0 6: words and digits disagree (`results/colima/crops/060228E0300__OPT14.jpg`)
- 060236E0303 Unused ballots: no words; digit boxes 4 8 and a last digit written over (0 and 1 on top of each other) (`results/colima/crops/060236E0303__SOBRANTES.jpg`)
- 060243C0100 Unused ballots: no words; a 1 written left of the three boxes, then 6 1 2 in the boxes: 1612 or 612 (`results/colima/crops/060243C0100__SOBRANTES.jpg`)
- 060246B0100 Null votes: faint; words 'Doscientos setenta y ocho' on the null-votes row, digit boxes 2, a faint middle digit, 0 (`results/colima/crops/060246B0100__NULOS.jpg`)
- 060246C0300 Ballots taken from the boxes: words 'Trescientos sesenta y cuatro', digit boxes 3 6 and a closed-top last digit (4 or 9) (`results/colima/crops/060246C0300__SACADOS.jpg`)
- 060248C0300 Option 12: words 'Trece' gone over, digit boxes 0 1 and a 5 gone over in heavy ink: words and digits disagree (`results/colima/crops/060248C0300__OPT12.jpg`)
- 060250C0200 TOTAL: words 'Cuatrocientos cuarenta y sie[te]' running into the boxes, digit boxes 4 4 and a last digit written over (7 and 8) (`results/colima/crops/060250C0200__TOTAL.jpg`)
- 060250E0100 Option 04: words corrected with brackets (reads like 'Cuarenta y cinco' written over), digit boxes 0, a closed-top digit (4 or 9), 5 (`results/colima/crops/060250E0100__OPT04.jpg`)
- 060251B0100 Unregistered candidates: words 'Uno' written over a struck word, digit boxes 0 0 and a last digit written over (1 and 2) (`results/colima/crops/060251B0100__NO_REGISTRADAS.jpg`)
- 060251C0200 Option 03: words 'Cero'; digit boxes 0, a pinched loop that reads as 8 or 0, 0 (`results/colima/crops/060251C0200__OPT03.jpg`)
- 060251C0500 Option 07: words 'Ciento noventa y seis', digit boxes 1 9 and a last digit written over (6 and 7) (`results/colima/crops/060251C0500__OPT07.jpg`)
- 060251C0500 Null votes: words 'Siete nulos', digit boxes 0 0 and a last digit written over (7 and 8) (`results/colima/crops/060251C0500__NULOS.jpg`)
- 060251C0500 TOTAL: no words; digit boxes 3 9 and a last digit written over (1 and 2), with 393 written below the field (`results/colima/crops/060251C0500__TOTAL.jpg`)
- 060252C0200 Option 02: words 'Treinta y seis', digit boxes 0 7 6: words and digits disagree (`results/colima/crops/060252C0200__OPT02.jpg`)
- 060254B0100 Option 02: words 'Cincuenta y cuatro', digit boxes a dash, 5 and a last digit written over (4 and 9) (`results/colima/crops/060254B0100__OPT02.jpg`)
- 060258C0300 Voters on the list: words 'Trescientos cincuenta y siete', digit boxes 3 5 4: words and digits disagree (`results/colima/crops/060258C0300__VOTARON.jpg`)
- 060259B0100 Voters on the list: words 'Dosientos ochenta y cuatro', digit boxes 2 8 and a closed-top last digit (4 or 9) (`results/colima/crops/060259B0100__VOTARON.jpg`)
- 060260C0200 Option 14: no words; digit boxes 0 0 and a faint flat-topped last digit (3 or 5) (`results/colima/crops/060260C0200__OPT14.jpg`)
- 060269C0100 Voters on the list: no words; digit boxes 3 5 and a last digit written over (7 and 9) (`results/colima/crops/060269C0100__VOTARON.jpg`)
- 060290C0400 Option 13: words unclear (possibly 'cuatro'); digit boxes 0 0 and a last box written over (4 and 6 superimposed) (`results/colima/crops/060290C0400__OPT13.jpg`)
- 060309B0100 Option 05: words 'Diecisiete', digit boxes a 6-shaped first digit, 1, 7: words and digits disagree (`results/colima/crops/060309B0100__OPT05.jpg`)
- 060309B0100 Option 15: words 'Uno', digit boxes 0 0 9: words and digits disagree (`results/colima/crops/060309B0100__OPT15.jpg`)
- 060309B0100 Unused ballots: no words; digit boxes 2, a B-shaped 8, and a hooked last digit (7 or 1) (`results/colima/crops/060309B0100__SOBRANTES.jpg`)
- 060316C0100 Option 02: words 'Veintisiete', digit boxes 0 2 and a last digit written over (7 and 8) (`results/colima/crops/060316C0100__OPT02.jpg`)
- 060316C0100 Representatives who voted: words 'Uno', digit boxes 2 0 1: words and digits disagree (`results/colima/crops/060316C0100__REPRESENTANTES.jpg`)
- 060316C0100 TOTAL: words 'Doscientos sesenta y cinco', digit boxes 2 6 and a last digit written over (5 and 2) (`results/colima/crops/060316C0100__TOTAL.jpg`)
- 060323C0100 Representatives who voted: no words; digit boxes 0 0 (gone over in heavy ink) and a last digit written over (1 and 4) (`results/colima/crops/060323C0100__REPRESENTANTES.jpg`)
- 060335B0100 Option 07: words 'Treinta y dos', digit boxes 1 3 2: words and digits disagree (`results/colima/crops/060335B0100__OPT07.jpg`)
- 060359B0100 Ballots taken from the boxes: words 'Cuatrocientos sesenta y cuatro', digit boxes 4 6 and a closed-top last digit (4 or 9) (`results/colima/crops/060359B0100__SACADOS.jpg`)
- 060362C0100 Unused ballots: words 'Trescientos cuatro', digit boxes 3 6 9: words and digits disagree (`results/colima/crops/060362C0100__SOBRANTES.jpg`)
- 060375B0100 Representatives who voted: very faint page; words not legible, digit boxes 0 0 and a faint last digit (5 or 6) (`results/colima/crops/060375B0100__REPRESENTANTES.jpg`)
- 060375C0100 Option 05: words 'Cinco', digit boxes 0 0 and a last digit written over (5 and 6) (`results/colima/crops/060375C0100__OPT05.jpg`)
- 060380C0100 TOTAL: words 'Trescientos noventa', digit boxes 3 7 0: words and digits disagree (`results/colima/crops/060380C0100__TOTAL.jpg`)
- 060382C0200 Unused ballots: words 'Doscientos sesenta y uno', digit boxes 2 6 and a last digit written over (1 and 2) (`results/colima/crops/060382C0200__SOBRANTES.jpg`)
- 060390C0100 Ballots taken from the boxes: words 'Trecientos s(i)cuenta y siete' (between sesenta and cincuenta), digit boxes 3, a middle digit between 5 and 6, 7 (`results/colima/crops/060390C0100__SACADOS.jpg`)
- 060391C0300 Option 09: words 'Cero', digit boxes 0 0 6: words and digits disagree (`results/colima/crops/060391C0300__OPT09.jpg`)
- 060396B0100 Representatives who voted: no words; digit boxes 0 0 and a last digit written over, with 378 written across the boxes from another field (`results/colima/crops/060396B0100__REPRESENTANTES.jpg`)
- 060396B0100 Unused ballots: no words; digit boxes 3 3 and a raised 3, with other figures written around the field (`results/colima/crops/060396B0100__SOBRANTES.jpg`)
- 060396B0100 Voters on the list: no words; digit boxes written over several times (3, 7, then 8 or 4), with other figures above the field (`results/colima/crops/060396B0100__VOTARON.jpg`)
- 060397C0200 Null votes: words 'Ocho', digit boxes 0 0 0: words and digits disagree (`results/colima/crops/060397C0200__NULOS.jpg`)
- 060398B0100 Option 14: words 'Uno', digit boxes 0 0 5: words and digits disagree (the digits look shifted by one row) (`results/colima/crops/060398B0100__OPT14.jpg`)
- 060398B0100 Option 13: words 'Cinco', digit boxes 0 0 6: words and digits disagree (the digits look shifted by one row) (`results/colima/crops/060398B0100__OPT13.jpg`)

PREP rows 1017; located 982; read and parsed 982; not located or no image 35 (routed, never replaced: listed in the JSON); also in other sets (flagged, not double-counted): 2 (060022C0100: calibration 150; 060079C0300: the 300).

Report from the /audit/new generator: `results/colima/audit_report.html` / `.csv` (audit aaf159eb1c448): 982 forms read, 21604 fields checked, 510 disputed on 238 forms; tiers {'strong': 64, 'medium': 193, 'weak': 253}; report fingerprint (SHA-256) `511a71e9ec1f31ce3f90d8a96a2f6899b5d2c22c3cd57813e316d9075623123a`, Merkle root of the disputes `f92ffa9246f0c75758bc6d5e855129fe837d667c6ba4d2bf4bce4db501ac5e43`.
