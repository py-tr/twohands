# Certified confirmation of the adjudicated capture errors

Secondary analysis (Amendment 2 b). For every field adjudicated `model_right` (paper shows the model's value: the
PREP capture mis-keyed) and, separately, `capture_right` (the model misread), the certified Computos Distritales value of
the same field (`data/raw/computos/PRES_2024.csv`, cut 08/06/2024) is compared with the paper value from adjudication.
Computos certify the 17 vote rows and the vote total (TOTAL_VOTOS_CALCULADOS, compared with the written TOTAL); they do
not cover SOBRANTES, VOTARON, REPRESENTANTES or SACADOS. A value marked Recuento is a recount of the ballots, so a
difference there need not mean the paper was misread. Code: `scripts/certified_check.py`.

> the first capture mis-keyed 52 of 6,358 fields; the certified count later covers 31 of them and agrees with the image on 22

Of the 31 covered, 6 are TOTAL (compared with the certified calculated total); the vote rows alone: 25 covered, 20 agree. Every covered field where the certified value differs from the paper was recounted: 9 of 9.

## model_right: 52 fields

- covered by the certified count: **31** (not covered: 21, fields Computos does not certify or no Computos row)
- of those, certified == paper value: **22**; differ: 9 (9 of the differing ones after a recount)

| clave | field | model | PREP | paper | Computos | Computos note | covered | certified = paper |
|---|---|---|---|---|---|---|---|---|
| 021600C0100 | SACADOS | 601 | 326 | 601 | - | Recuento (Para recuento-SRA) | no | - |
| 050397B0100 | SACADOS | None | 453 | blank | - | Recuento (Para recuento-SRA) | no | - |
| 050815B0100 | MORENA | 175 | 75 | 175 | 175 | Cotejo (Levantada en Casilla) | yes | yes |
| 070207C0100 | MC | 47 | Ilegible | 47 | 47 | Recuento (Para recuento-SRA) | yes | yes |
| 070207C0100 | PAN_PRD | 0 | Ilegible | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 070207C0100 | PAN_PRI_PRD | 1 | Ilegible | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 070207C0100 | PRI_PRD | 0 | Ilegible | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 070207C0100 | PVEM_PT | 0 | Ilegible | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 070207C0100 | PVEM_PT_MORENA | 8 | Ilegible | 8 | 7 | Recuento (Para recuento-SRA) | yes | NO |
| 070207C0100 | SACADOS | 416 | Ilegible | 416 | - | Recuento (Para recuento-SRA) | no | - |
| 070207C0100 | TOTAL | 416 | Ilegible | 416 | 416 | Recuento (Para recuento-SRA) | yes | yes |
| 070470E0100 | VOTARON | 420 | Ilegible | 420 | - | Recuento (Para recuento-SRA) | no | - |
| 080305B0100 | PRI | 15 | Ilegible | 15 | 15 | Recuento (Para recuento-SRA) | yes | yes |
| 080310B0100 | SOBRANTES | 180 | 480 | 180 | - | Cotejo (Levantada en Casilla) | no | - |
| 080336B0100 | SACADOS | None | 193 | blank | - | Recuento (Para recuento-SRA) | no | - |
| 093831B0100 | MC | 39 | Ilegible | 39 | 39 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | MORENA | 199 | Ilegible | 199 | 198 | Recuento (Para recuento-SRA) | yes | NO |
| 093831B0100 | NO_REGISTRADAS | 0 | Ilegible | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | NULOS | 9 | Ilegible | 9 | 10 | Recuento (Para recuento-SRA) | yes | NO |
| 093831B0100 | PAN_PRD | 0 | Ilegible | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | PAN_PRI | 1 | Ilegible | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | PAN_PRI_PRD | 7 | Ilegible | 7 | 7 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | PRD | 7 | Ilegible | 7 | 7 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | PT | 8 | Ilegible | 8 | 8 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | PT_MORENA | 5 | Ilegible | 5 | 5 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | PVEM | 11 | Ilegible | 11 | 11 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | PVEM_MORENA | 2 | Ilegible | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | PVEM_PT | 2 | Ilegible | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 093831B0100 | SACADOS | 388 | Ilegible | 388 | - | Recuento (Para recuento-SRA) | no | - |
| 093831B0100 | TOTAL | 383 | Ilegible | 383 | 383 | Recuento (Para recuento-SRA) | yes | yes |
| 094821C0200 | SACADOS | 388 | 386 | 388 | - | Recuento (Para recuento-SRA) | no | - |
| 094821C0200 | TOTAL | 388 | 386 | 388 | 394 | Recuento (Para recuento-SRA) | yes | NO |
| 131468C0100 | SACADOS | 354 | 352 | 354 | - | Recuento (Para recuento-SRA) | no | - |
| 131468C0100 | TOTAL | 354 | 352 | 354 | 357 | Recuento (Para recuento-SRA) | yes | NO |
| 154237C0200 | SACADOS | None | 422 | blank | - | Recuento (Para recuento-SRA) | no | - |
| 162776C0100 | SACADOS | 344 | 331 | 344 | - | Recuento (Para recuento-SRA) | no | - |
| 202005C0200 | MORENA | 75 | 15 | 75 | 75 | Recuento (Para recuento-SRA) | yes | yes |
| 220225C0200 | MORENA | 240 | 290 | 240 | 239 | Recuento (Para recuento-SRA) | yes | NO |
| 220313C0300 | SACADOS | 0 | 527 | 0 | - | Recuento (Para recuento-SRA) | no | - |
| 220497B0100 | NO_REGISTRADAS | 8 | Ilegible | 8 | 4 | Recuento (Para recuento-SRA) | yes | NO |
| 230252B0100 | SACADOS | None | 363 | blank | - | Recuento (Para recuento-SRA) | no | - |
| 230696B0100 | TOTAL | 307 | Ilegible | 307 | 315 | Recuento (Para recuento-SRA) | yes | NO |
| 230957B0100 | REPRESENTANTES | 3 | 2 | 3 | - | Recuento (Para recuento-SRA) | no | - |
| 241393C0100 | SACADOS | 376 | 370 | 376 | - | Recuento (Para recuento-SRA) | no | - |
| 250767B0100 | REPRESENTANTES | 3 | 393 | 3 | - | Recuento (Para recuento-SRA) | no | - |
| 250767B0100 | SOBRANTES | None | 390 | blank | - | Recuento (Para recuento-SRA) | no | - |
| 250767B0100 | VOTARON | 390 | 3 | 390 | - | Recuento (Para recuento-SRA) | no | - |
| 253737B0100 | SACADOS | None | 178 | blank | - | Recuento (Para recuento-SRA) | no | - |
| 270281B0100 | SACADOS | 344 | Sin dato | 344 | - | Recuento (Para recuento-SRA) | no | - |
| 270281B0100 | TOTAL | 344 | Sin dato | 344 | 342 | Recuento (Para recuento-SRA) | yes | NO |
| 301477B0100 | MORENA | 128 | 228 | 128 | 128 | Recuento (Para recuento-SRA) | yes | yes |
| 301480B0100 | SACADOS | 422 | 420 | 422 | - | Recuento (Para recuento-SRA) | no | - |

## capture_right: 153 fields

- covered by the certified count: **97** (not covered: 56, fields Computos does not certify or no Computos row)
- of those, certified == paper value: **69**; differ: 28 (28 of the differing ones after a recount)

| clave | field | model | PREP | paper | Computos | Computos note | covered | certified = paper |
|---|---|---|---|---|---|---|---|---|
| 010469C0400 | SOBRANTES | 239 | 234 | 234 | - | Cotejo (Levantada en Casilla) | no | - |
| 021309B0100 | SOBRANTES | 31 | 431 | 431 | - | Recuento (Para recuento-SRA) | no | - |
| 021600C0100 | PAN | 13 | 15 | 15 | 15 | Recuento (Para recuento-SRA) | yes | yes |
| 021626B0100 | PRD | 0 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 021626B0100 | PRI | 0 | 13 | 13 | 13 | Recuento (Para recuento-SRA) | yes | yes |
| 021626B0100 | PT | 0 | 18 | 18 | 18 | Recuento (Para recuento-SRA) | yes | yes |
| 021626B0100 | PVEM | 0 | 18 | 18 | 18 | Recuento (Para recuento-SRA) | yes | yes |
| 021937C0100 | MC | 1 | 11 | 11 | 11 | Recuento (Para recuento-SRA) | yes | yes |
| 021937C0100 | PVEM | 1 | 11 | 11 | 11 | Recuento (Para recuento-SRA) | yes | yes |
| 021937C0100 | PVEM_PT_MORENA | 0 | 10 | 10 | 10 | Recuento (Para recuento-SRA) | yes | yes |
| 030150B0100 | REPRESENTANTES | 104 | 4 | 4 | - | Cotejo (Levantada en Casilla) | no | - |
| 030150B0100 | SOBRANTES | 77 | 277 | 277 | - | Cotejo (Levantada en Casilla) | no | - |
| 070144C0200 | PRI_PRD | None | 2 | 2 | 0 | Recuento (Para recuento-SRA) | yes | NO |
| 070144C0200 | PVEM_PT_MORENA | 2 | Sin dato | blank | 17 | Recuento (Para recuento-SRA) | yes | NO |
| 070154C0100 | MORENA | 254 | 354 | 354 | 368 | Recuento (Para recuento-SRA) | yes | NO |
| 070154C0100 | NULOS | 61 | 30 | 30 | 32 | Recuento (Para recuento-SRA) | yes | NO |
| 070154C0100 | PAN | 75 | 15 | 15 | 15 | Recuento (Para recuento-SRA) | yes | yes |
| 070154C0100 | PRI_PRD | 5 | 3 | 3 | 1 | Recuento (Para recuento-SRA) | yes | NO |
| 070154C0100 | PT_MORENA | 0 | 1 | 1 | 7 | Recuento (Para recuento-SRA) | yes | NO |
| 070207C0100 | REPRESENTANTES | 2 | 3 | 3 | - | Recuento (Para recuento-SRA) | no | - |
| 070207C0100 | SOBRANTES | 27 | 277 | 277 | - | Recuento (Para recuento-SRA) | no | - |
| 070470E0100 | PT | 183 | 185 | 185 | 185 | Recuento (Para recuento-SRA) | yes | yes |
| 071709C0100 | VOTARON | 394 | 399 | 399 | - | Recuento (Para recuento-SRA) | no | - |
| 072354B0100 | SOBRANTES | 299 | 249 | 249 | - | Recuento (Para recuento-SRA) | no | - |
| 080338C0100 | MORENA | 143 | 93 | 93 | 93 | Recuento (Para recuento-SRA) | yes | yes |
| 080338C0100 | SOBRANTES | 321 | 381 | 381 | - | Recuento (Para recuento-SRA) | no | - |
| 083281B0100 | NO_REGISTRADAS | None | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 090955C0200 | REPRESENTANTES | 100 | 0 | 0 | - | Cotejo (Levantada en Casilla) | no | - |
| 090955C0200 | SOBRANTES | 200 | 206 | 206 | - | Cotejo (Levantada en Casilla) | no | - |
| 092366B0100 | SOBRANTES | 497 | 197 | 197 | - | Recuento (Para recuento-SRA) | no | - |
| 093975C0400 | PAN_PRD | 4 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 094821C0200 | REPRESENTANTES | 62 | 2 | 2 | - | Recuento (Para recuento-SRA) | no | - |
| 094821C0200 | SOBRANTES | 0 | 242 | 242 | - | Recuento (Para recuento-SRA) | no | - |
| 094821C0200 | VOTARON | 342 | 392 | 392 | - | Recuento (Para recuento-SRA) | no | - |
| 101300B0100 | MORENA | 10 | 210 | 210 | 210 | Recuento (Para recuento-SRA) | yes | yes |
| 101300B0100 | PAN_PRI | 0 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 101300B0100 | PVEM_MORENA | 0 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 101300B0100 | PVEM_PT_MORENA | 6 | 8 | 8 | 8 | Recuento (Para recuento-SRA) | yes | yes |
| 101300B0100 | REPRESENTANTES | None | 2 | 2 | - | Recuento (Para recuento-SRA) | no | - |
| 101300B0100 | SOBRANTES | None | 238 | 238 | - | Recuento (Para recuento-SRA) | no | - |
| 101300B0100 | VOTARON | None | 295 | 295 | - | Recuento (Para recuento-SRA) | no | - |
| 110451C0100 | NULOS | 0 | 6 | 6 | 6 | Recuento (Para recuento-SRA) | yes | yes |
| 110451C0100 | PAN_PRI | 202 | 2 | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 110451C0100 | PAN_PRI_PRD | 202 | 7 | 7 | 7 | Recuento (Para recuento-SRA) | yes | yes |
| 110451C0100 | PRD | 93 | 3 | 3 | 3 | Recuento (Para recuento-SRA) | yes | yes |
| 110451C0100 | PRI | 213 | 13 | 13 | 13 | Recuento (Para recuento-SRA) | yes | yes |
| 110451C0100 | PT | 95 | 5 | 5 | 5 | Recuento (Para recuento-SRA) | yes | yes |
| 110451C0100 | PVEM_PT_MORENA | 97 | 7 | 7 | 7 | Recuento (Para recuento-SRA) | yes | yes |
| 110922C0100 | PVEM | 54 | 51 | 51 | 51 | Cotejo (Levantada en Casilla) | yes | yes |
| 111666B0100 | PAN | 72 | 92 | 92 | 92 | Recuento (Para recuento-SRA) | yes | yes |
| 111666B0100 | PAN_PRD | None | 0 | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 111666B0100 | PAN_PRI | None | 0 | 0 | 1 | Recuento (Para recuento-SRA) | yes | NO |
| 111666B0100 | PRI_PRD | None | 0 | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 111666B0100 | PT | 4 | 6 | 6 | 5 | Recuento (Para recuento-SRA) | yes | NO |
| 111666B0100 | PT_MORENA | None | 0 | 0 | 3 | Recuento (Para recuento-SRA) | yes | NO |
| 111666B0100 | PVEM_PT | 10 | 1 | 1 | 0 | Recuento (Para recuento-SRA) | yes | NO |
| 111666B0100 | REPRESENTANTES | 103 | 3 | 3 | - | Recuento (Para recuento-SRA) | no | - |
| 111666B0100 | SOBRANTES | 123 | 183 | 183 | - | Recuento (Para recuento-SRA) | no | - |
| 111666B0100 | VOTARON | None | 238 | 238 | - | Recuento (Para recuento-SRA) | no | - |
| 111927C0400 | PRD | 7 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 111927C0400 | PRI | 78 | 18 | 18 | 18 | Recuento (Para recuento-SRA) | yes | yes |
| 121565B0100 | REPRESENTANTES | None | 0 | 0 | - | Recuento (Para recuento-SRA) | no | - |
| 122292C0100 | NO_REGISTRADAS | 9 | 0 | 0 | 0 | Cotejo (Levantada en Casilla) | yes | yes |
| 122292C0100 | NULOS | 252 | 9 | 9 | 9 | Cotejo (Levantada en Casilla) | yes | yes |
| 122292C0100 | TOTAL | None | 252 | 252 | 252 | Cotejo (Levantada en Casilla) | yes | yes |
| 122655C0100 | PRI | 23 | 123 | 123 | 123 | Cotejo (Levantada en Casilla) | yes | yes |
| 130704B0100 | SOBRANTES | 203 | 213 | 213 | - | Recuento (Para recuento-SRA) | no | - |
| 131052B0100 | SACADOS | None | 355 | 355 | - | Cotejo (Levantada en Casilla) | no | - |
| 131324C0200 | MC | 90 | 40 | 40 | 40 | Cotejo (Levantada en Casilla) | yes | yes |
| 131374C0200 | PAN_PRI | 80 | 0 | 0 | 1 | Recuento (Para recuento-SRA) | yes | NO |
| 131374C0200 | PRI | 27 | 21 | 21 | 21 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | MC | None | 69 | 69 | 68 | Recuento (Para recuento-SRA) | yes | NO |
| 140330C0200 | MORENA | None | 210 | 210 | 210 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | NO_REGISTRADAS | None | 0 | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | NULOS | None | 14 | 14 | 15 | Recuento (Para recuento-SRA) | yes | NO |
| 140330C0200 | PAN | None | 10 | 10 | 10 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | PAN_PRD | None | 0 | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | PAN_PRI | None | 0 | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | PAN_PRI_PRD | None | 2 | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | PRD | None | 5 | 5 | 5 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | PRI | None | 28 | 28 | 29 | Recuento (Para recuento-SRA) | yes | NO |
| 140330C0200 | PRI_PRD | None | 0 | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | PT | None | 18 | 18 | 18 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | PT_MORENA | None | 2 | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | PVEM | None | 16 | 16 | 14 | Recuento (Para recuento-SRA) | yes | NO |
| 140330C0200 | PVEM_MORENA | None | 2 | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | PVEM_PT | None | 1 | 1 | 3 | Recuento (Para recuento-SRA) | yes | NO |
| 140330C0200 | PVEM_PT_MORENA | None | 8 | 8 | 8 | Recuento (Para recuento-SRA) | yes | yes |
| 140330C0200 | REPRESENTANTES | None | 1 | 1 | - | Recuento (Para recuento-SRA) | no | - |
| 140330C0200 | SACADOS | 383 | 3 | 3 | - | Recuento (Para recuento-SRA) | no | - |
| 140330C0200 | TOTAL | None | 383 | 383 | 386 | Recuento (Para recuento-SRA) | yes | NO |
| 141113C0100 | SOBRANTES | 256 | 255 | 255 | - | Recuento (Para recuento-SRA) | no | - |
| 141113C0100 | VOTARON | 441 | 497 | 497 | - | Recuento (Para recuento-SRA) | no | - |
| 141155C0100 | VOTARON | 282 | 287 | 287 | - | Recuento (Para recuento-SRA) | no | - |
| 142210C0400 | PAN_PRI_PRD | 7 | 1 | 1 | 2 | Recuento (Para recuento-SRA) | yes | NO |
| 142210C0400 | PVEM_MORENA | 7 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 142210C0400 | SACADOS | 74 | 14 | 14 | - | Recuento (Para recuento-SRA) | no | - |
| 142479C0100 | SACADOS | None | 265 | 265 | - | Recuento (Para recuento-SRA) | no | - |
| 143587B0100 | SOBRANTES | 301 | 361 | 361 | - | Recuento (Para recuento-SRA) | no | - |
| 151055C0200 | MORENA | 273 | 275 | 275 | 275 | Cotejo (Levantada en Casilla) | yes | yes |
| 151055C0200 | PRI | 39 | 34 | 34 | 34 | Cotejo (Levantada en Casilla) | yes | yes |
| 151055C0200 | REPRESENTANTES | 96 | 6 | 6 | - | Cotejo (Levantada en Casilla) | no | - |
| 153572B0100 | SACADOS | 341 | 1 | 1 | - | Recuento (Para recuento-SRA) | no | - |
| 154383E0100 | SOBRANTES | 110 | 115 | 115 | - | Recuento (Para recuento-SRA) | no | - |
| 154476C0300 | SOBRANTES | 370 | 371 | 371 | - | Recuento (Para recuento-SRA) | no | - |
| 155026C0100 | REPRESENTANTES | 0 | 5 | 5 | - | Recuento (Para recuento-SRA) | no | - |
| 155026C0100 | VOTARON | 369 | 364 | 364 | - | Recuento (Para recuento-SRA) | no | - |
| 156371B0100 | PRD | 6 | 0 | 0 | 0 | Recuento (Para recuento-SRA) | yes | yes |
| 160026B0100 | SOBRANTES | 47 | 247 | 247 | - | Recuento (Para recuento-SRA) | no | - |
| 180307B0100 | SOBRANTES | 224 | 214 | 214 | - | Recuento (Para recuento-SRA) | no | - |
| 190150C0100 | PT_MORENA | 4 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 200475C0100 | PRD | 7 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 201201B0100 | SACADOS | 716 | 316 | 316 | - | Cotejo (Levantada en Casilla) | no | - |
| 212668C0300 | SOBRANTES | 300 | 379 | 379 | - | Cotejo (Levantada en Casilla) | no | - |
| 220225C0200 | NO_REGISTRADAS | None | 3 | 3 | 3 | Recuento (Para recuento-SRA) | yes | yes |
| 220497B0100 | MORENA | 197 | 199 | 199 | 198 | Recuento (Para recuento-SRA) | yes | NO |
| 220497B0100 | PAN_PRI | 6 | 5 | 5 | 4 | Recuento (Para recuento-SRA) | yes | NO |
| 220497B0100 | PT | 7 | 17 | 17 | 17 | Recuento (Para recuento-SRA) | yes | yes |
| 220497B0100 | PVEM | 26 | 20 | 20 | 20 | Recuento (Para recuento-SRA) | yes | yes |
| 220497B0100 | REPRESENTANTES | 104 | 4 | 4 | - | Recuento (Para recuento-SRA) | no | - |
| 220497B0100 | SOBRANTES | 318 | 348 | 348 | - | Recuento (Para recuento-SRA) | no | - |
| 230957B0100 | PT_MORENA | None | 2 | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 230957B0100 | PVEM_MORENA | 2 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 230957B0100 | PVEM_PT | 1 | Sin dato | blank | 0 | Recuento (Para recuento-SRA) | yes | NO |
| 240035C0100 | NULOS | 73 | 13 | 13 | 13 | Recuento (Para recuento-SC) | yes | yes |
| 240679B0100 | PT_MORENA | 4 | 2 | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 241393C0100 | TOTAL | 376 | 370 | 370 | 370 | Recuento (Para recuento-SRA) | yes | yes |
| 251701B0100 | SOBRANTES | 298 | 208 | 208 | - | Cotejo (Levantada en Casilla) | no | - |
| 253060B0100 | REPRESENTANTES | None | 2 | 2 | - | Recuento (Para recuento-SRA) | no | - |
| 260214C0300 | PAN_PRI | 0 | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 260214C0300 | SOBRANTES | 429 | 479 | 479 | - | Recuento (Para recuento-SRA) | no | - |
| 270180B0100 | SOBRANTES | 255 | 253 | 253 | - | Cotejo (Levantada en Casilla) | no | - |
| 270180B0100 | TOTAL | 113 | 413 | 413 | 413 | Cotejo (Levantada en Casilla) | yes | yes |
| 270844C0100 | REPRESENTANTES | 66 | 0 | 0 | - | Recuento (Para recuento-SRA) | no | - |
| 270971C0400 | PRD | 9 | 2 | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 270971C0400 | PVEM_MORENA | None | 1 | 1 | 1 | Recuento (Para recuento-SRA) | yes | yes |
| 270971C0400 | PVEM_PT | 1 | Sin dato | blank | 0 | Recuento (Para recuento-SRA) | yes | NO |
| 280078B0100 | REPRESENTANTES | 12 | 10 | 10 | - | Recuento (Para recuento-SRA) | no | - |
| 280078B0100 | VOTARON | 411 | 401 | 401 | - | Recuento (Para recuento-SRA) | no | - |
| 290625B0100 | PRI_PRD | 0 | 9 | 9 | 1 | Recuento (Para recuento-SRA) | yes | NO |
| 290625B0100 | PT_MORENA | 3 | 0 | 0 | 5 | Recuento (Para recuento-SRA) | yes | NO |
| 290625B0100 | PVEM_MORENA | 5 | 3 | 3 | 16 | Recuento (Para recuento-SRA) | yes | NO |
| 290625B0100 | PVEM_PT | 1 | 5 | 5 | 1 | Recuento (Para recuento-SRA) | yes | NO |
| 290625B0100 | PVEM_PT_MORENA | 9 | 1 | 1 | 14 | Recuento (Para recuento-SRA) | yes | NO |
| 300828B0100 | PRI | 26 | 20 | 20 | 20 | Recuento (Para recuento-SRA) | yes | yes |
| 302191C0100 | PAN | 66 | 6 | 6 | 6 | Recuento (Para recuento-SRA) | yes | yes |
| 302191C0100 | SACADOS | None | 249 | 249 | - | Recuento (Para recuento-SRA) | no | - |
| 303152C0100 | SOBRANTES | 242 | 244 | 244 | - | Cotejo (Levantada en Casilla) | no | - |
| 303152C0100 | VOTARON | 398 | 388 | 388 | - | Cotejo (Levantada en Casilla) | no | - |
| 304034C0100 | SACADOS | None | 0 | 0 | - | Cotejo (Levantada en Casilla) | no | - |
| 304395B0100 | PRD | 1 | 2 | 2 | 2 | Recuento (Para recuento-SRA) | yes | yes |
| 320267C0100 | MORENA | 94 | 91 | 91 | 89 | Recuento (Para recuento-SRA) | yes | NO |
| 321139B0100 | REPRESENTANTES | None | 0 | 0 | - | Recuento (Para recuento-SRA) | no | - |

