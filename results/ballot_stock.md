# Ballot stock: checking SOBRANTES against the official lista nominal (gate v3)

No model was called. Source: the INE PREP CSV `data/raw/prep/PRES_2024.csv` (cut 2024-06-03 20:05 UTC-6) and its
`LEEME.txt`. Built by `scripts/ballot_stock.py`; `--check` recomputes everything here.

**E** = SOBRANTES + VOTARON + REPRESENTANTES - LISTA_NOMINAL (CSV: TOTAL_BOLETAS_SOBRANTES +
TOTAL_PERSONAS_VOTARON + TOTAL_REP_PARTIDO_CI_VOTARON - LISTA_NOMINAL): ballots the casilla had beyond its list.
**D** = E - REPRESENTANTES_PP_CI: beyond the list and the representatives' allowance. Expected: D = 0.
Population: every presidential acta (TIPO_ACTA 2 / 2E) with CONTABILIZADA = 1 and the four ballot fields
numeric. *Consistent* = the capture's own identities hold (VOTARON + REPRESENTANTES = SACADOS = TOTAL), the
only forms a gate can accept.

## 1. The distribution

| casilla | population | n | E 1% | 5% | 25% | 50% | 75% | 95% | 99% | E in [0,0] | [0,5] | [0,10] | [0,20] | [0,30] | [0,50] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| básica (B) | all | 60269 | -164 | 25 | 29 | 32 | 36 | 44 | 286 | 0.06% | 0.15% | 0.32% | 0.98% | 43.12% | 94.68% |
| básica (B) | consistent | 31063 | 17 | 28 | 30 | 32 | 36 | 44 | 54 | 0.06% | 0.10% | 0.13% | 0.35% | 43.44% | 98.18% |
| contigua (C) | all | 78353 | -170 | 24 | 29 | 31 | 36 | 44 | 290 | 0.05% | 0.20% | 0.40% | 1.18% | 47.39% | 94.84% |
| contigua (C) | consistent | 33782 | 20 | 27 | 30 | 31 | 36 | 41 | 53 | 0.04% | 0.10% | 0.17% | 0.41% | 48.95% | 98.29% |
| extraordinaria (E) | all | 7022 | -118 | 27 | 30 | 34 | 38 | 44 | 292 | 0.04% | 0.20% | 0.33% | 0.87% | 34.49% | 95.03% |
| extraordinaria (E) | consistent | 4374 | 23 | 28 | 30 | 34 | 37 | 42 | 50 | 0.05% | 0.11% | 0.16% | 0.23% | 34.80% | 98.42% |

E sits at the representatives' allowance (28-44 per casilla in 2024), not at 0, so E in [0, 20] holds
for only about 1% of actas. Subtracting the allowance:

| casilla | population | n | D 1% | 5% | 10% | 50% | 90% | 95% | 99% | D = 0 | abs(D) <= 5 | <= 10 | <= 20 | <= 30 | <= 50 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| básica (B) | all | 60266 | -200 | -5 | -2 | 0 | 2 | 6 | 253 | 60.42% | 89.69% | 93.16% | 94.58% | 95.21% | 95.80% |
| básica (B) | consistent | 31060 | -15 | -2 | -1 | 0 | 0 | 0 | 20 | 82.11% | 96.84% | 97.65% | 98.11% | 98.36% | 98.69% |
| contigua (C) | all | 78352 | -200 | -6 | -3 | 0 | 2 | 6 | 258 | 54.66% | 89.03% | 92.87% | 94.65% | 95.46% | 96.10% |
| contigua (C) | consistent | 33781 | -11 | -2 | -1 | 0 | 0 | 1 | 20 | 77.82% | 96.39% | 97.53% | 98.24% | 98.56% | 98.87% |
| extraordinaria (E) | all | 7022 | -156 | -4 | -1 | 0 | 1 | 6 | 257 | 69.60% | 90.83% | 93.59% | 94.83% | 95.33% | 95.80% |
| extraordinaria (E) | consistent | 4374 | -8 | -1 | 0 | 0 | 0 | 0 | 16 | 88.02% | 97.26% | 97.94% | 98.33% | 98.49% | 98.83% |

Especial (S): 960 contabilizada actas (types {'2E': 960}); LISTA_NOMINAL is 0 on 960 of them (no list: the LEEME says so) and TOTAL_REP_PARTIDO_CI_VOTARON is not numeric on 960, so E is undefined. Especial casillas are **excluded**: under v3 their SOBRANTES always goes to a person. None of the 300, the 100 or the 3,000 is an especial casilla.

## 2. The frozen bands (gate v3)

Nearest-rank 1st and 99th percentile of D over the consistent actas of each type, **excluding** the 300, the
100 and the 3,000 (so no form that v3 will be scored on calibrates it). Frozen in `twohands/gate_v3.py`.

| casilla | n | D band [1%, 99%] | secondary: E_max (99% of E) | recomputed = frozen |
|---|---|---|---|---|
| básica (B) | 30407 | [-15, 20] | 53 | yes |
| contigua (C) | 33040 | [-11, 20] | 53 | yes |
| extraordinaria (E) | 4288 | [-9, 16] | 50 | yes |

By construction about 2% of correct, consistent SOBRANTES fall outside the band and go to a person.
A misread SOBRANTES passes the band when it moves D by less than the band's margin: by up to 16-20 upward or 9-15 downward from a paper whose D is 0.

## The two sources (fetched 2026-10-16 and read)

**TEPJF, Sala Superior, SUP-JIN-57/2012** (juicio de inconformidad, 24 August 2012; PDF
`https://www.te.gob.mx/media/SentenciasN/pdf/Superior/SUP-JIN-0057-2012.pdf`, 151 pages). The identity is used by the
court and by the parties, but always as boletas recibidas *minus* sobrantes against the people who voted / ballots taken
out of the urn:

> "...resulta necesario relacionar los rubros de TOTAL DE CIUDADANOS QUE VOTARON CONFORME A LA LISTA NOMINAL, TOTAL DE
> BOLETAS EXTRAÍDAS DE LA URNA, VOTACIÓN EMITIDA Y DEPOSITADA EN LA URNA, según corresponda, con el de NÚMERO DE BOLETAS
> SOBRANTES, para confrontar su resultado final con el número de boletas entregadas..." (p. 97, quoting the Sala
> Superior's own criterion)

> "...al restar las cantidades asentadas en los rubros boletas recibidas y boletas sobrantes resulta que la diferencia
> obtenida consiste en una cantidad igual o equivalente a la que existe en los rubros suma de los rubros 3 y 4 del acta
> (total de personas que votaron) y resultados de la votación de presidente (total)..." (pp. 140-141, casilla 900 E1)

The same ruling is also the caveat: the court calls the ballot rubros *accesorios* and holds that a mismatch there
alone does not show a miscount of votes, because poll workers make ballot-count mistakes:

> "...cuando las diferencias numéricas se localizan únicamente en las cifras relativas a boletas recibidas o boletas
> sobrantes, esto resulta insuficiente para considerar que se ha producido la causa de nulidad en comento." (p. 111)

So the identity is real and official, and it is also violated on real paper; the tails below are that.

**Reglamento de Elecciones del INE, art. 178, numeral 1.** Primary text (DOF, the CG reform that set inciso b),
`https://dof.gob.mx/nota_detalle_popup.php?codigo=5597009`):

> "Artículo 178. 1. Al término del conteo y sellado del total de boletas, éstas se agruparán de manera consecutiva por
> tipo de elección y siguiendo el procedimiento descrito en el anexo referido, conforme a los criterios siguientes:
> ( ... ) b) Para el caso de casillas especiales en elecciones concurrentes o no concurrentes, se asignarán hasta 1,500
> boletas por casilla para cada una de las elecciones federales, y otro tanto igual por cada tipo de elecciones
> locales. El número exacto de boletas deberá ser definido por el Consejo General a más tardar en el mes de febrero
> del año de la Jornada Electoral."

The DOF reform note prints only the amended inciso. Incisos a), c), d) as transcribed in a 2024 electoral-authority
agreement (Instituto Electoral del Estado de Querétaro, IEEQ/CD03/A/008/24, considerando 13,
`https://ieeq.mx/contenido/convocatorias/archivos/AnxCD030505241000E-2.pdf`; the consolidated INE text itself could
not be downloaded from here, diputados.gob.mx did not answer):

> "a) Total de personas electoras de cada casilla inscritas en el listado nominal. [...] c) Las boletas adicionales por
> cada partido político y, en su caso, candidaturas independientes, para que sus representantes acreditados ante la
> mesa directiva de casilla puedan ejercer su derecho de voto. d) En su caso, las boletas necesarias para que vote la
> ciudadanía que obtuvo resolución favorable del Tribunal Electoral que le faculte emitir su sufragio."

The same agreement (considerando 14) records that INE/CG293/24 gave each especial casilla 1,000 ballots in 2024.

**Column definitions (the INE CSV's own `LEEME.txt`).** TOTAL_PERSONAS_VOTARON = "Total de personas que votaron";
TOTAL_REP_PARTIDO_CI_VOTARON = representatives "que votaron"; LISTA_NOMINAL = the casilla's lista ("Para el caso de
casillas especiales no se tienen listas nominales, por lo que el valor es 0"); REPRESENTANTES_PP_CI = "Número de las y
los representantes acreditados de los Partidos Políticos y Candidaturas Independientes ante cada mesa directiva de
casilla". On the acta, PERSONAS_Y_REP = VOTARON + REPRESENTANTES (an identity the gate already checks), so **VOTARON
excludes the representatives** and the right sum is SOBRANTES + VOTARON + REPRESENTANTES. By art. 178 the casilla
receives LISTA_NOMINAL + the representatives' ballots (+ any TEPJF ballots), so E should equal REPRESENTANTES_PP_CI,
and D = E - REPRESENTANTES_PP_CI should be 0. The CSV confirms it: D = 0 exactly on most consistent actas.

## 3. POST-HOC on the 300 (not a test of v3)

**Post-hoc.** v3 was designed after seeing these 300 reads and their adjudication; numbers here are NOT a test of
v3. The pre-registered tests are the 100-form confirmation and the 3,000 extension (Amendment 7). Stored reads
re-gated, no model call. Truth as in `results/posthoc_v2_300.md` (verdict decides; with no verdict model = PREP
is correct). Lista nominal and allowance from the PREP CSV. Field-level: under v3 a routed SOBRANTES is shown to a
person and is not an accepted field; the form's other fields stay accepted.

Every accepted-field error on the 300 (v1-accepted forms, either reader), all SOBRANTES:

| form | reader | read | paper | lista | allowance | D on paper | D read | band | caught by band | caught by [0, E_max] |
|---|---|---|---|---|---|---|---|---|---|---|
| 010469C0400 | Gemma-4-31B-IT | 239 | 234 | 614 | 28 | 0 | 5 | [-11, 20] | no | no |
| 212668C0300 | Gemma-4-31B-IT | 300 | 379 | 680 | 34 | 0 | -79 | [-11, 20] | yes | yes |
| 090955C0200 | Qwen3.8-27B | 200 | 206 | 516 | 28 | 0 | -6 | [-11, 20] | no | no |

### Gemma primary, Qwen second

| gate | forms, other fields accepted | touchless (all 23) | accepted graded fields | errors | SOBRANTES to a person: correct read (false alarm) | wrong read (caught) | flagged |
|---|---|---|---|---|---|---|---|
| v1 (frozen gate) | 55 | 55 | 1210 | 2 | 0 | 0 | 0 |
| v2 | 47 | 47 | 1034 | 1 | 0 | 0 | 0 |
| v2-2R strict | 45 | 45 | 990 | 0 | 0 | 0 | 0 |
| v3 part: stock band only | 56 | 55 | 1231 | 2 | 0 | 1 | 0 |
| v3 part: words + stock band | 56 | 47 | 1223 | 1 | 7 | 2 | 0 |
| v3 part: words + two reads | 56 | 38 | 1214 | 0 | 15 | 3 | 0 |
| v3 (pre-registered: words + two reads + stock band) | 56 | 38 | 1214 | 0 | 15 | 3 | 0 |
| v3-emax (secondary: E in [0, E_max]) | 56 | 38 | 1214 | 0 | 15 | 3 | 0 |

- **v1 (frozen gate)**: errors: 010469C0400 SOBRANTES: read 239, PREP 234; 212668C0300 SOBRANTES: read 300, PREP 379. SOBRANTES to a person (wrong read, caught): none.
- **v2**: errors: 010469C0400 SOBRANTES: read 239, PREP 234. SOBRANTES to a person (wrong read, caught): none.
- **v2-2R strict**: errors: none. SOBRANTES to a person (wrong read, caught): none.
- **v3 part: stock band only**: errors: 010469C0400 SOBRANTES: read 239, PREP 234; 154383E0100 SOBRANTES: read 110, PREP 115. SOBRANTES to a person (wrong read, caught): 212668C0300 (read 300, PREP 379).
- **v3 part: words + stock band**: errors: 010469C0400 SOBRANTES: read 239, PREP 234. SOBRANTES to a person (wrong read, caught): 154383E0100 (read 110, PREP 115); 212668C0300 (read 300, PREP 379).
- **v3 part: words + two reads**: errors: none. SOBRANTES to a person (wrong read, caught): 010469C0400 (read 239, PREP 234); 154383E0100 (read 110, PREP 115); 212668C0300 (read 300, PREP 379).
- **v3 (pre-registered: words + two reads + stock band)**: errors: none. SOBRANTES to a person (wrong read, caught): 010469C0400 (read 239, PREP 234); 154383E0100 (read 110, PREP 115); 212668C0300 (read 300, PREP 379).
- **v3-emax (secondary: E in [0, E_max])**: errors: none. SOBRANTES to a person (wrong read, caught): 010469C0400 (read 239, PREP 234); 154383E0100 (read 110, PREP 115); 212668C0300 (read 300, PREP 379).

### Qwen primary, Gemma second

| gate | forms, other fields accepted | touchless (all 23) | accepted graded fields | errors | SOBRANTES to a person: correct read (false alarm) | wrong read (caught) | flagged |
|---|---|---|---|---|---|---|---|
| v1 (frozen gate) | 31 | 31 | 682 | 1 | 0 | 0 | 0 |
| v2 | 24 | 24 | 528 | 0 | 0 | 0 | 0 |
| v2-2R strict | 27 | 27 | 594 | 1 | 0 | 0 | 0 |
| v3 part: stock band only | 31 | 30 | 681 | 1 | 1 | 0 | 0 |
| v3 part: words + stock band | 31 | 23 | 674 | 0 | 7 | 1 | 0 |
| v3 part: words + two reads | 31 | 21 | 672 | 0 | 9 | 1 | 0 |
| v3 (pre-registered: words + two reads + stock band) | 31 | 20 | 671 | 0 | 10 | 1 | 0 |
| v3-emax (secondary: E in [0, E_max]) | 31 | 20 | 671 | 0 | 10 | 1 | 0 |

- **v1 (frozen gate)**: errors: 090955C0200 SOBRANTES: read 200, PREP 206. SOBRANTES to a person (wrong read, caught): none. Undecided: 143587B0100 vote row 6; 155940C0100 vote row 3.
- **v2**: errors: none. SOBRANTES to a person (wrong read, caught): none. Undecided: 143587B0100 vote row 6; 155940C0100 vote row 3.
- **v2-2R strict**: errors: 090955C0200 SOBRANTES: read 200, PREP 206. SOBRANTES to a person (wrong read, caught): none. Undecided: 155940C0100 vote row 3.
- **v3 part: stock band only**: errors: 090955C0200 SOBRANTES: read 200, PREP 206. SOBRANTES to a person (wrong read, caught): none. Undecided: 143587B0100 vote row 6; 155940C0100 vote row 3.
- **v3 part: words + stock band**: errors: none. SOBRANTES to a person (wrong read, caught): 090955C0200 (read 200, PREP 206). Undecided: 143587B0100 vote row 6; 155940C0100 vote row 3.
- **v3 part: words + two reads**: errors: none. SOBRANTES to a person (wrong read, caught): 090955C0200 (read 200, PREP 206). Undecided: 143587B0100 vote row 6; 155940C0100 vote row 3.
- **v3 (pre-registered: words + two reads + stock band)**: errors: none. SOBRANTES to a person (wrong read, caught): 090955C0200 (read 200, PREP 206). Undecided: 143587B0100 vote row 6; 155940C0100 vote row 3.
- **v3-emax (secondary: E in [0, E_max])**: errors: none. SOBRANTES to a person (wrong read, caught): 090955C0200 (read 200, PREP 206). Undecided: 143587B0100 vote row 6; 155940C0100 vote row 3.

## Lines

> POST-HOC, Gemma primary: the ballot-stock band alone catches 1 of the 2 wrong SOBRANTES Gemma read on v1-accepted forms (010469C0400 read 239 vs paper 234 not caught; 212668C0300 read 300 vs paper 379 caught) and sends 0 correct SOBRANTES to a person (of 56 forms whose other fields are accepted).

> POST-HOC, Gemma primary, full v3 (words + two reads + band): 56 forms with the other 22 fields accepted, 38 touchless (v2: 47, v1: 55), 1214 accepted graded fields (v2: 1034), 0 errors, 3 wrong SOBRANTES caught and 15 correct SOBRANTES sent to a person (the false-alarm cost, mostly from the two-read and words rules).

> Site sentence: "Every accepted field is checked by the paper's own arithmetic, and the one field the paper cannot check is checked against the official voter list and ballot allowance; a misread smaller than that check's tolerance (at most 20 ballots) can still pass on that field alone."
