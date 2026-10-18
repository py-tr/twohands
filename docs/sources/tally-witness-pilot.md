> **Source copy.** Pilot write-up "Tally Witness" of 2026-10-14 (43 forms), copied on 2026-10-16 from the builder's
> working folder (spikes/tally-witness/README.md, outside this repo and not published), verbatim except that section 6
> is shortened to its political-sensitivity notes (one phrase in them reworded), and planning notes and the spike's
> file list are removed. Its data files are committed under [`data/pilot/`](../../data/pilot/SOURCES.md). Section numbers are the ones the
> docs cite (for example "§1", "section 3").
>
> **Superseded:** the final computation is `results/national_counts.md` (3,382 of 52,167 not-recounted stations, 6.5%).

# Tally Witness: spike (2026-10-14, 19:11 to ~20:25 UTC)

**Question:** can a vision model read photographed polling-station result forms, and can the form's OWN arithmetic accept the read or flag the exact inconsistency, graded against the official numbers?

**Answer: yes, on Mexico's INE 2024 presidential actas.**
- Two readers were tested on 43 stratified actas: Gemma-4-31B (tiled) and Qwen3.8-27B.
- The gate is the acta's own checks: digits = words on every field, the 17 rows sum to TOTAL, votaron + representantes = section 5, and section 5 = section 7 = TOTAL. It auto-accepts **49-51%** of forms.
- **Every accepted form had every field right (Gemma 462/462 fields, Qwen 484/484), but only against an adjudicated truth.** Against the raw PREP capture both readers show 4-5 "errors" on accepted forms. Six of those turned out, by eye, to be **PREP keying errors**: the official capture disagrees with the digits on the image, and the model was right each time.
- **Forms rejected with a perfect read are real paper inconsistencies, 7-10 per reader.** Pooled across both readers that is **12 distinct actas**:
  - 8 are row-sum failures that INE's own captured numbers confirm.
  - 3 are words-vs-digits disagreements or crossed-out rewrites, checked by eye.
  - 2 are section 5 vs section 7 disagreements that I could not verify.
  - One acta has both a confirmed row-sum failure and an eye-checked words/digits disagreement, so 8 + 3 + 2 = 13 flags fall on 12 actas.

## 1. Data: which source has images + numbers + licence
| Source | Reachable today | Image | Per-form official numbers | Licence |
|---|---|---|---|---|
| **Mexico INE PREP 2024** (chosen) | yes (HTTP 200) | JPEG per acta. The phone app ("Móvil") gives ~2932x1900 to 4082x2640; the CATD scanner ("Escáner") gives 4082x2640. URL per casilla in `https://prep2024.ine.mx/publicacion/nacional/assets/presidencia/entidad/{ent}_{dist}.json` → `https://prep2024-actas.ine.mx/...jpg` | `https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip` (47 MB). It holds 169,005 presidential actas, with every field as captured: sobrantes, votaron, representantes, sacados, 15 party/coalition rows, no registrados, nulos, total asentado, plus DIGITALIZACION (Móvil / Escáner) and hash | see below |
| **Mexico INE Cómputos Distritales 2024** (certified) | yes | (none) | `https://computos2024.ine.mx/20240608_2030_COMPUTOS.zip`. Certified per-casilla votes, and OBSERVACIONES says whether the casilla was "Cotejo" (acta compared) or "Recuento" (recounted) | same |
| Kenya IEBC Form 34A (forms.iebc.or.ke) | yes, no login | 1-page PDF scans | **None.** IEBC publishes no per-form numeric table. kenyaelection.live (ML + volunteers) calls its own CSV "fairly inaccurate" | "Copyright © 2026 IEBC. All rights reserved." No terms |
| Nigeria INEC IReV EC8A | site loads; API did not answer | JPEG/PDF, many at 192x256 px | No official per-PU table. CCIJ/VEZA: "Since January 2025, none of the public records are available online for inspection." | none found |

**Licence: the INE free-use terms I verified sit on SICEE.** I read them myself in the sicee.ine.mx bundle; SICEE is INE's results site and also hosts actas. The terms are the Libre-Uso-MX text:
- *"Los presentes 'Términos de libre uso' promueven el uso y redistribución de los conjuntos de datos abiertos…"*
- Permitted uses: *"Extraer total o parcialmente el contenido del conjunto de datos. / Explotar comercialmente el conjunto de datos y su contenido. / Crear conjuntos de datos derivados del conjunto de datos o su contenido."*
- Conditions: *"Citar la fuente de origen… Liga de internet de los datos descargados, y la fecha de la consulta"* and *"No aparentar que el uso que usted haga de los datos representa una postura oficial del Gobierno o que el mismo está avalado por la fuente de origen."*

The PREP and Cómputos sites themselves carry **no licence text**. The research agent grepped both bundles; ine.mx shows only "© Derechos Reservados". Publishing the images and CSV is mandated by the Lineamientos PREP (Anexo 13, art. 30: "VI. Imágenes de las Actas PREP… IX. Las bases de datos… CSV"). Legal footing is reasonable but not explicit; cite SICEE's terms and the source URL with the date.

**What makes INE ideal: every number on the acta is written twice, in words and in digit boxes, and there are four arithmetic identities.** This is far richer than a rainfall ledger's single total. National base rates from the PREP CSV:
- In **26,336 / 137,196 (19.2%)** fully captured actas, the rows do not sum to the written total.
- Cómputos recounted **116,402 / 170,766 (68%)** of packages; the rest went through "Cotejo".
- Among Cotejo (not recounted) actas, PREP ≠ certified in **2,444 / 47,540 (5.1%)**.

## 2. Sample and method
- **Sample: 43 presidential actas (type 2) from 10 districts in 10 states** (AGS, CDMX, OAX, CHIS, NL, MEX, VER, JAL, PUE, GRO), 23 Móvil and 20 Escáner. Strata:
  - A clean: Cotejo, PREP = certified, all checks pass (16)
  - B paper-sum mismatch with PREP = certified (5, all that exist in these districts)
  - C PREP ≠ certified under Cotejo (12)
  - D recounted, with a PREP row-sum mismatch (10)
- **The sample is deliberately enriched with trouble.** It is not a random draw, so the accept rate below is a lower bound for clean days.
- **Reader input:** each request carries the full image plus zoomed tiles. In v1 there were 3 tiles: left column, table top, table bottom. In v2 there were 4: left column, party rows, coalition rows, and bottom + section 7. The prompt asks for digits AND words per field, independently.
- **Ground truth:** the PREP capture of the same image. "Adjudicated" = PREP plus **6 fields in 5 actas** where I checked the crop by eye and PREP mis-keyed: 202451B (TOTAL/SACADOS 271, not 272), 211420C (PVEM_MORENA "Dos 002", not 0), 156723B (PAN_PRI_PRD "Cinco 005", not 3), 093954C (PAN "Sesenta y nueve 069", not 64), 211298B (MC 039, not 34). For 211294C, SACADOS is written 262 in both words and digits, but PREP keyed 162. In 3 of these cases the certified Cómputos value also matches the model.
- **Bias warning:** I adjudicated only where a model disagreed with PREP on an accepted form. I did not search for PREP errors anywhere else.

## 3. Results (43 forms, 22 graded fields each = 946 fields)
| Reader | Field exact vs PREP | vs adjudicated | Forms auto-accepted (full gate) | Field acc on accepted (raw → adjudicated) | Accepted forms fully right | Field acc on rejected | USD / form | Latency |
|---|---|---|---|---|---|---|---|---|
| Gemma-4-31B, 1+3 tiles | 92.4% | 93.2% | 17/43 (40%) | 98.4% → **100%** (374/374) | 17/17 | 88.5% | $0.00010 | 55 s |
| Gemma-4-31B, 1+4 tiles + targeted prompt | 96.5% | 97.4% | 21/43 (49%) | 98.9% → **100%** (462/462) | 21/21 | 94.2% | $0.00012 | 49 s |
| Qwen3.8-27B (reasoning low), 1+3 tiles | **97.4%** | **98.2%** | 22/43 (51%) | 99.2% → **100%** (484/484) | 22/22 | 95.5% | $0.00051 | 85 s |
| Both agree on every field + gate | (n/a) | (n/a) | 20/43 | 100% | 20/20 | (n/a) | $0.00063 | (n/a) |

- **By stratum (Qwen):** clean 99.1% fields with 13/16 accepted; recounted-with-sum-mismatch 96.8% with 1/10 accepted. Móvil vs Escáner made no consistent difference.
- **Gemma's main v1 errors were row shifts and blank zeros.** Coalition-2 rows shifted by one (PVEM_PT_MORENA ↔ PVEM_PT ↔ PVEM_MORENA), and faint pink "0 0 0" boxes came back as null. The v2 tiles and prompt fixed most of both.
- **Qwen sees the image at higher resolution.** It receives ~1,800 tokens per image against Gemma's fixed ~265, about 7.4k prompt tokens per form against 2.1k.
- **Gemma reliability (Discord warning):** all 86 Gemma calls finished with `stop` at 605-660 completion tokens, with no degenerate tails and no parse failures. The parser now takes the first complete JSON object, and `max_tokens` is 1500. One v2 output had `"n": 003`, which the lenient parser now handles. Qwen: 43/43 `stop`, 1.3-3.1k tokens.
- **Throughput was ~2 forms/min,** bounded by the ≤6 req/min, 2-concurrent cap.
- **Total spend ≈ $0.031:** $0.0044 + $0.0051 Gemma, $0.0218 Qwen.
- **A full national run is cheap but slow on this endpoint.** 170k actas would cost about $20 (Gemma) or $86 (Qwen), but at 2 forms/min that is 59 days. A real deployment needs a dedicated MI300X endpoint.

## 4. Paper discrepancies found (forms rejected although every field was read correctly)
Pooled across both readers, 12 distinct actas:
- **8 row-sum failures confirmed by INE's own capture:** 201791B, 156044B, 010474B, 122837B, 201717C, 151806B, 191790C, 200742B.
- **3 words-vs-digits disagreements or rewrites, checked by eye:** 211294C, 200742B, 141097C. 200742B is also on the row-sum list, which is why the list adds to 13 on 12 actas.
- **2 section 5 ≠ section 7 that I could not verify:** 156034C, 095566C. Section 5 is not in the CSV.

Two examples:
1. **211294C (Guerrero), "Móvil":**
   - The TOTAL boxes say **2 6 2**, but the words say ***"ciento sesenta y dos"* (162)**. Section 7 reads "doscientos sesenta y dos / 262", and the rows sum to 262.
   - PREP captured TOTAL = 162, applying the "letter prevails" rule, and **also keyed SACADOS = 162** although that field says 262 in both words and digits.
   - Cómputos certified 262. Both models flagged the TOTAL words/digits split (Gemma v2 and Qwen) or read SACADOS correctly.
2. **200742B (Puebla), scanner:**
   - Boletas sobrantes are written ***"CIENTO CINCO"* (105) next to digit boxes 1 0 6.** The rows sum to 100 against a written TOTAL of 99.
   - PREP keyed 106 and 99, so its own row check fails too. Cómputos certified 99 by Cotejo, without a recount.

Also flagged: **141097C, a crossed-out rewrite.** PRI reads "(CIENTO) TREINTA Y OCHO", with "ciento" bracketed out, against digits 038. Gemma returned `"fix": true`.

## 5. Context
- **Who keys the forms today:** INE PREP 2024 cost MXN **273,630,875** (La Jornada, 2024-05-26: "36 millones 315 mil 225 pesos que se suman a los 237 millones 315 mil 650 pesos").
  - Images come from the "PREP Casilla" phone app or a CATD scanner. Every acta is keyed **twice by two capturistas**, with a third review on mismatch (nmas.com.mx).
  - The audit was done by UAM-Iztapalapa. The number of capture staff was not found.
  - A state-level PREP is a contract of its own; Campeche 2024 paid Informática Electoral MXN 24.94M.
  - Observer groups run Parallel Vote Tabulations: Yiaga 2023 "3,014 PVT observers… 1,507 polling units"; ELOG 2022 "1000 PVT observers". Cost was not found for either.
- **Incumbents:**
  - IEEQ Querétaro 2024 ran a *"prueba piloto de reconocimiento de datos, mediante inteligencia artificial, en actas de escrutinio y cómputo de 264 casillas"*.
  - An IEEM column calls AI capture "viable… para el próximo proceso electoral de 2027" for "aproximadamente 45,369 AEC". INE reportedly told IEEQ that automated recognition would not replace verification; that comes from a search summary and was not read.
  - INEC Nigeria (Oct 2026) is "integrating artificial intelligence tools into its election-results verification process".
  - Small private tools: irevwatch.com ("read and cross-checked by AI… confirmed by a human"), kenyaelection.live (ML + volunteers) and TransTally (Kenya, campaign tallies).
  - Academic: "Election Tally Sheets Processing System" (ResearchGate 303950937).
  - **Not found:** Smartmatic, Indra or ABBYY products doing this.
- **Upcoming elections:**
  - Mexico: 6 June 2027 midterm (500 deputies, 17 governorships), with ~32 state PREPs. Federal PREP continuity is uncertain: Sheinbaum proposed abolishing it, and the reform was reported rejected in March 2026 (single source).
  - Kenya: 10 Aug 2027.
  - Nigeria: early 2027 (dates in flux).
- **Buyers:** Mexican OPLEs (state electoral institutes) are the most concrete, since they already contract out their PREPs and are piloting AI. Then observer missions (often donor-funded, and USAID cuts hurt them), parties and campaigns, and media.

## 6. Political sensitivity

(Planning notes of this section are omitted.)

- **Political sensitivity: high.** Showing "discrepancies" in Mexico's 2024 presidential actas can read as an accusation. Mitigations:
  - Frame it strictly as clerical arithmetic: 19% of actas fail their own sums nationally, and recounts fixed them.
  - Show certified Cómputos agreeing.
  - Never rank parties or candidates.
  - Honour the licence clause against implying official endorsement.
  - Use 2024 data (settled), not live data.

## 7. Model to ask AMD to host
- **A reader with a native-resolution image budget.** Gemma's fixed ~265 tokens per image is the bottleneck, and tiling only partly fixes it.
- **Ask for Qwen3-VL-32B/30B-A3B-Instruct, served with vLLM's dynamic resolution.** Alternatives are a document-OCR VLM (dots.ocr or PaddleOCR-VL) or Gemma with a larger `max_pixels`.
- **Not tested.** This is a request, not a measurement.

## 8. Verdict
- **The tech claim holds.** Readers that cost cents per thousand forms, gated by the acta's own redundancy, auto-accept about half of a trouble-enriched sample with **zero accepted errors once PREP's own keying errors are adjudicated**. The reject queue names the exact field, and about a third to half of rejections are genuine paper inconsistencies.
- **The demo story is strong:** "we found INE's double-keyed capture wrong on 6 fields that the model read right."
- **Caveats:**
  - n = 43, one run, crop fractions tuned by hand.
  - Adjudication covered only accepted-form disagreements.
  - The accept rate on a random (clean-heavy) draw was not measured.
- **The market is real but thin and slow.** OPLE procurement runs on election cycles, AI capture pilots already exist (IEEQ), and the subject is politically radioactive.
