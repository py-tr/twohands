# IEEBCS plumbing check (PROTOCOL_IEEBCS.md section 11)

The first 5 located actas in manifest order; reader `gemma` (results/ieebcs/calls_gemma.jsonl); CSV value from the PREP CSV on disk.

A person confirms, acta by acta and field by field, that each CSV column feeds the schema field next to it (the CSV value and our read should name the same box on the page). The only allowed outcome is a fix to the join/mapping code, recorded in PROTOCOL_IEEBCS.md with its diff.

## 030042B010003_3be25802 (mx_bcs_ayto_2024, escaner)

Masked page: `data/masked/ieebcs/030042B010003_3be25802.jpg` · CSV row: CLAVE_ACTA 030042B010003, CODIGO_INTEGRIDAD 3be2580270d5... · read: parsed

| field | CSV column | CSV value | scorer uses | our read (digits / words) | same? |
|---|---|---|---|---|---|
| SOBRANTES (Unused ballots) | TOTAL_BOLETAS_SOBRANTES (#13) | 452 | 452 | 452 / 452 | yes |
| VOTARON (Voters on the list) | TOTAL_PERSONAS_VOTARON (#14) | 226 | 226 | 226 / 226 | yes |
| REPRESENTANTES (Representatives who voted) | TOTAL_REP_PARTIDO_CI_VOTARON (#15) | 3 | 3 | 3 / 3 | yes |
| SACADOS (Ballots taken from the boxes) | TOTAL_VOTOS_SACADOS (#16) | 229 | 229 | 229 / 229 | yes |
| OPT01 | #17 | 28 | 28 | 28 / 28 | yes |
| OPT02 | #18 | 154 | 154 | 144 / 144 | NO |
| OPT03 | #19 | 30 | 30 | 30 / 30 | yes |
| OPT04 | #20 | 3 | 3 | 3 / 3 | yes |
| OPT05 | #21 | 3 | 3 | 3 / 3 | yes |
| NO_REGISTRADOS | #22 | 0 | 0 | 0 / 0 | yes |
| NULOS | #23 | 19 | 19 | 19 / 19 | yes |
| TOTAL | TOTAL_VOTOS_ASENTADO (#24) | 222 | 222 | 227 / 222 | NO |

Confirmed by: the builder, 2026-10-17 (mapping correct: yes; the mismatches are reading differences on the same field, no column shifted)

## 030041C010003_61ea4009 (mx_bcs_ayto_2024, escaner)

Masked page: `data/masked/ieebcs/030041C010003_61ea4009.jpg` · CSV row: CLAVE_ACTA 030041C010003, CODIGO_INTEGRIDAD 61ea4009d9fe... · read: parsed

| field | CSV column | CSV value | scorer uses | our read (digits / words) | same? |
|---|---|---|---|---|---|
| SOBRANTES (Unused ballots) | TOTAL_BOLETAS_SOBRANTES (#13) | 322 | 322 | 322 / 322 | yes |
| VOTARON (Voters on the list) | TOTAL_PERSONAS_VOTARON (#14) | 243 | 243 | 243 / 243 | yes |
| REPRESENTANTES (Representatives who voted) | TOTAL_REP_PARTIDO_CI_VOTARON (#15) | 5 | 5 | 5 / 5 | yes |
| SACADOS (Ballots taken from the boxes) | TOTAL_VOTOS_SACADOS (#16) | 231 | 231 | 231 / 231 | yes |
| OPT01 | #17 | 35 | 35 | 35 / 35 | yes |
| OPT02 | #18 | 150 | 150 | 150 / 150 | yes |
| OPT03 | #19 | 28 | 28 | 28 / 28 | yes |
| OPT04 | #20 | (blank) | - | 0 / 0 | NO |
| OPT05 | #21 | 7 | 7 | 7 / 7 | yes |
| NO_REGISTRADOS | #22 | 0 | 0 | 0 / 0 | yes |
| NULOS | #23 | 11 | 11 | 11 / 11 | yes |
| TOTAL | TOTAL_VOTOS_ASENTADO (#24) | 231 | 231 | 231 / 231 | yes |

Confirmed by: the builder, 2026-10-17 (mapping correct: yes; the mismatches are reading differences on the same field, no column shifted)

## 030003C020003_06373cc7 (mx_bcs_ayto_2024, escaner)

Masked page: `data/masked/ieebcs/030003C020003_06373cc7.jpg` · CSV row: CLAVE_ACTA 030003C020003, CODIGO_INTEGRIDAD 06373cc76076... · read: parsed

| field | CSV column | CSV value | scorer uses | our read (digits / words) | same? |
|---|---|---|---|---|---|
| SOBRANTES (Unused ballots) | TOTAL_BOLETAS_SOBRANTES (#13) | 291 | 291 | 291 / 291 | yes |
| VOTARON (Voters on the list) | TOTAL_PERSONAS_VOTARON (#14) | 333 | 333 | 333 / 333 | yes |
| REPRESENTANTES (Representatives who voted) | TOTAL_REP_PARTIDO_CI_VOTARON (#15) | 5 | 5 | 5 / 5 | yes |
| SACADOS (Ballots taken from the boxes) | TOTAL_VOTOS_SACADOS (#16) | 337 | 337 | 337 / 337 | yes |
| OPT01 | #17 | 57 | 57 | 57 / 57 | yes |
| OPT02 | #18 | 159 | 159 | 159 / 159 | yes |
| OPT03 | #19 | 107 | 107 | 107 / 107 | yes |
| OPT04 | #20 | 1 | 1 | 1 / 1 | yes |
| OPT05 | #21 | 8 | 8 | 8 / 8 | yes |
| NO_REGISTRADOS | #22 | 0 | 0 | 0 / 0 | yes |
| NULOS | #23 | 5 | 5 | 5 / 5 | yes |
| TOTAL | TOTAL_VOTOS_ASENTADO (#24) | 337 | 337 | 337 / 337 | yes |

Confirmed by: the builder, 2026-10-17 (mapping correct: yes; the mismatches are reading differences on the same field, no column shifted)

## 030073B010003_2d44aa12 (mx_bcs_ayto_2024, escaner)

Masked page: `data/masked/ieebcs/030073B010003_2d44aa12.jpg` · CSV row: CLAVE_ACTA 030073B010003, CODIGO_INTEGRIDAD 2d44aa128677... · read: parsed

| field | CSV column | CSV value | scorer uses | our read (digits / words) | same? |
|---|---|---|---|---|---|
| SOBRANTES (Unused ballots) | TOTAL_BOLETAS_SOBRANTES (#13) | 309 | 309 | 309 / 309 | yes |
| VOTARON (Voters on the list) | TOTAL_PERSONAS_VOTARON (#14) | 418 | 418 | 418 / 418 | yes |
| REPRESENTANTES (Representatives who voted) | TOTAL_REP_PARTIDO_CI_VOTARON (#15) | 0 | 0 | 0 / 0 | yes |
| SACADOS (Ballots taken from the boxes) | TOTAL_VOTOS_SACADOS (#16) | 418 | 418 | 418 / 418 | yes |
| OPT01 | #17 | 86 | 86 | 86 / 86 | yes |
| OPT02 | #18 | 219 | 219 | 219 / 219 | yes |
| OPT03 | #19 | 79 | 79 | 79 / 79 | yes |
| OPT04 | #20 | 12 | 12 | 12 / 12 | yes |
| OPT05 | #21 | 8 | 8 | 8 / 8 | yes |
| NO_REGISTRADOS | #22 | 0 | 0 | 0 / 0 | yes |
| NULOS | #23 | 14 | 14 | 14 / 14 | yes |
| TOTAL | TOTAL_VOTOS_ASENTADO (#24) | 418 | 418 | 418 / 418 | yes |

Confirmed by: the builder, 2026-10-17 (mapping correct: yes; the mismatches are reading differences on the same field, no column shifted)

## 030004B010003_f3c87cce (mx_bcs_ayto_2024, movil)

Masked page: `data/masked/ieebcs/030004B010003_f3c87cce.jpg` · CSV row: CLAVE_ACTA 030004B010003, CODIGO_INTEGRIDAD f3c87cce58c0... · read: parsed

| field | CSV column | CSV value | scorer uses | our read (digits / words) | same? |
|---|---|---|---|---|---|
| SOBRANTES (Unused ballots) | TOTAL_BOLETAS_SOBRANTES (#13) | 283 | 283 | 233 / 233 | NO |
| VOTARON (Voters on the list) | TOTAL_PERSONAS_VOTARON (#14) | 424 | 424 | 424 / 424 | yes |
| REPRESENTANTES (Representatives who voted) | TOTAL_REP_PARTIDO_CI_VOTARON (#15) | 3 | 3 | 3 / 3 | yes |
| SACADOS (Ballots taken from the boxes) | TOTAL_VOTOS_SACADOS (#16) | 427 | 427 | 427 / 427 | yes |
| OPT01 | #17 | 86 | 86 | 96 / 86 | NO |
| OPT02 | #18 | 206 | 206 | 206 / 206 | yes |
| OPT03 | #19 | 110 | 110 | 110 / 112 | yes |
| OPT04 | #20 | 4 | 4 | 4 / 4 | yes |
| OPT05 | #21 | 6 | 6 | 6 / 6 | yes |
| NO_REGISTRADOS | #22 | 2 | 2 | 2 / 2 | yes |
| NULOS | #23 | 13 | 13 | 13 / 13 | yes |
| TOTAL | TOTAL_VOTOS_ASENTADO (#24) | 427 | 427 | 427 / 427 | yes |

Confirmed by: the builder, 2026-10-17 (mapping correct: yes; the mismatches are reading differences on the same field, no column shifted)

