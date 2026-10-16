# Pre-registered protocol: head-to-head on Baja California Sur's 2024 local PREP (IEEBCS)

Status: **frozen before the first model call of this run.** This file, the two schemas, the code, the tests, the
manifest, the published values and the prepare log were committed to git before any acta of the sample was sent to a
model. Whatever the numbers turn out to be, they are published (section 8), including a result below 62.84%.
This is a separate pre-registration. It does not amend `PROTOCOL.md`, `PROTOCOL_SENADO.md` or any amendment, and
nothing here changes any earlier prompt, schema or gate (the presidential and Senate prompts are pinned byte for byte
in `tests/test_ieebcs.py`).

## 1. Question
In 2024 the local PREP of Baja California Sur used commercial cloud OCR as its first capture: a custom Google Document
AI model read every count and vote box as a separate crop, and **14,501 of 23,077 fields (62.84%) matched the manual
capture** (IEEBCS, *Informe final del Programa de Resultados Electorales Preliminares, Proceso Electoral Local
Ordinario 2023-2024*, p. 19, table "Análisis de desempeño de lectura automatizada por recortes";
https://www.ieebcs.org.mx/documentos/acuerdos/INFORME_FINAL_PREP_PLE_2023-2024.pdf, local copy sha256
`8474b11b…6ead`; method p. 18; per acta 65 of 2,254, 2.88%). On a random, stratified sample of 300 of the same state's
published actas, what share of the same kind of fields does one open-weights read (Gemma 4 on AMD) match, against the
same PREP's published values? And, separately, what does our gate accept, and how accurate are the accepted fields?

## 2. Data and source (cited)
- PREP site: https://prep2024.ieebcs.org.mx/ (IEEBCS PREP 2024, final cut 03/06/2024 20:01 UTC-7), accessed
  **2026-10-16**. Database: https://prep2024.ieebcs.org.mx/bdatos/20240603_2001_PREP_BCS.zip (zip sha256
  `234e294d9f72f62e64331448a3fca5f977315ed28b43dd1176024a32411c318d`; pointer in `/js/json/publicacion_csv.json`),
  with `BCS_DIP_LOC_2024.csv` (sha256 `9a3ffd04…4334`) and `BCS_AYUN_2024.csv` (sha256 `a8c6f85f…79f8`) and their
  `LEEME.txt`. Image lists: `/js/json/diputaciones_votos_por_casilla.json` (sha256 `8b27c2bd…95e9`) and
  `/js/json/ayuntamiento_votos_por_casilla_nivel_municipio_seccion.json` (sha256 `fbe8e36a…d73974`), "Acta digitalizada"
  URLs on the PREP's public S3 bucket `prep-test-2023.s3.us-east-1.amazonaws.com/actas/<CODIGO_INTEGRIDAD>.jpeg`.
- **Terms.** The PREP site publishes the database and the acta images for public consultation (LEEME.txt describes the
  files; the site shows an "Aviso de privacidad"). On 2026-10-16 we found no terms-of-use page restricting reuse. We use
  the published data for a clerical accuracy comparison only, cite the source, store no unmasked image, and publish no
  name or signature (section 3.2).
- **Polite fetching.** Every request carries the User-Agent `TwoHands-research/1.0 (clerical capture QA; pre-registered
  300-acta sample of the published PREP BCS 2024 images; <=2 req/s)`, one shared limiter keeps it at **≤ 2 requests/s**,
  and every file is cached (`data/raw/ieebcs/`, gitignored): the zip and the two JSON files were fetched once, each
  acta image once. Code: `scripts/ieebcs_draw.py` (`polite_get`).
- Fact recorded: LEEME.txt says CODIGO_INTEGRIDAD is the SHA-256 of the digitised acta. The served file is named by
  it, but the served bytes hash differently (0 of the 295 images we fetched match; the bucket presumably serves a re-encoded copy).
  We use the name as the acta's image identity and record the sha256 of the bytes we received (`raw_sha256` in the
  prepare log).

## 3. Sample

### 3.1 Population (both election types, the full published list)
Every CSV row of `BCS_DIP_LOC_2024.csv` (diputaciones locales, 1,138 rows) and `BCS_AYUN_2024.csv` (ayuntamientos,
1,116 rows) **whose acta image is published** (its CODIGO_INTEGRIDAD is among the image URLs of the two JSON lists).
**The only exclusion is "no published image": 125 diputaciones and 109 ayuntamientos rows.** Result: **2,020 actas
(1,013 diputaciones locales, 1,007 ayuntamientos)**. This equals the 2,020 actas of the report's own per-acta table
(p. 20, "TOTAL* 2020", "se excluye ... los Formatos Sin Acta"), the set their 23,077 fields came from.
No condition on CONTABILIZADA, OBSERVACIONES, TIPO_DOCUMENTO or TIPO_CASILLA.

### 3.2 Strata, allocation, seed
- Strata: **election × municipality** (10 strata). A diputaciones acta's municipality comes from its sección (the
  ayuntamiento CSV maps every sección to its municipality).
- n = 300, allocated in proportion to stratum size, largest remainder (ties by stratum name): 150 diputaciones, 150
  ayuntamientos (1,013 : 1,007 of the population).
- Within a stratum: sorted by (CLAVE_ACTA, image name), shuffled with `random.Random("20261020:<stratum>")`, the first
  n taken. **Seed: 20261020.** No replacement of any kind. Code: `scripts/ieebcs_draw.py draw`.
- Manifest: `results/manifest_ieebcs300.json`, **sha256 `cd152fccd1632ae94b36afb02d45191f3664ace69076792d7fdd941714a12b30`**
  (208 CATD scans, 92 casilla phone captures; 297 "ACTA PREP", 3 "CC" copies).

### 3.3 Layouts: two schemas, row variants, and the special-station actas
- **One schema per election type**: `schemas/mx_bcs_dl_2024.yaml` (sha256 `b407b514c146b040f087bdefbd59a34c4b9623f878044509e06527b38dc3f7a5`)
  and `schemas/mx_bcs_ayto_2024.yaml` (sha256 `e58253a9f5bab9c2580818ab154008d6730cf025ec58ebc3dd4ff5471dd4553e`).
- Each type is printed in two row variants, declared inside its schema (`variants`): a district (diputaciones) with no
  PES candidacy, or a municipality (ayuntamientos) with no ML candidacy, prints one section-6 row fewer, taller rows,
  same frame; PREP shows `-` in that column. The variant is assigned from the CSV before the draw (the column is `-`
  on most of the district's / municipality's rows): `mx_bcs_dl_2024@sin_pes` (6 districts),
  `mx_bcs_ayto_2024@sin_ml` (Mulegé, Loreto).
- **Special-station actas** (TIPO_ACTA 05/06 diputaciones MR/RP, 07 ayuntamiento; 29 of the 2,020) print another
  form (three left-column sections, 4-digit boxes; the RP acta one row per party). No schema covers them. They stay in
  the population and the sample (**5 drawn**), are never downloaded or read, and **every numeric published field of
  theirs counts as unmatched** (with their election's base field list). We chose this over a third schema because it
  can only lower our number.

### 3.4 Field set (the count and vote boxes; no identification field)
Per acta, every field of its schema (variant) that has a PREP column; section 5 ("total de personas y representantes",
the 14th box) has no PREP column and is read but never scored. Fields per acta: **diputaciones 13 (12 without PES),
ayuntamientos 12 (11 without ML)** (their maximum of 14 crops per acta = the 14 boxes of the diputaciones acta,
p. 20). Our fields: SOBRANTES, VOTARON, REPRESENTANTES, SACADOS, each candidacy row (shown as "Option NN"),
NO_REGISTRADOS, NULOS, TOTAL.

### 3.5 Preparation, done before this file was committed (no model involved)
Each covered acta's image was downloaded once to `data/raw/ieebcs/img/`, located and masked with the schema's assets
(the Amendment 1 locator, fail-closed), saved as a 2400x1562 JPEG in `data/masked/ieebcs/` (local, gitignored), and
**the raw file was deleted at once**. Log: `results/ieebcs/prepare.jsonl` (sha256 `d29fc4a9…6699`).
**Located: 294 of the 295 covered actas** (not located: `030514C020003_8496bd41`, ayuntamiento, phone capture);
5 special-station actas not covered. Not-located and not-covered actas are never replaced. All raw images (including
three from the feasibility check and the layout pilots) are deleted. Rectification assets per layout were built from
6 pilot pages each (3 scans + 3 phone captures, outside the drawn sample, values never read; `results/ieebcs/pilot.json`
sha256 `16cf16fc…bdd5`; `scripts/build_ieebcs_reference.py`); every asset has the mask area zeroed.

## 4. Reader (frozen)
- **Privacy mask:** the whole right column (`[0.662, 0, 1, 1]`): incidents, the names and signatures of the mesa
  directiva and of the party representatives. Mask tests on all 294 masked pages (`tests/test_ieebcs.py`): the mask
  area is black, every field box and tile lies left of it, the boxes land on ink.
- **Input per call:** the masked page plus 4 tiles (left column; upper rows of section 6; lower rows of section 6 and
  section 7; the logo column, enlarged), JPEG q88, longest side ≤ 2400 px.
- **Prompt:** the same reader and prompt structure as every Two Hands run (`twohands/reader.py`); the schema names the
  issuer and the form ("This is a Mexican IEEBCS 2024 'Acta de Escrutinio y Computo de Casilla de la eleccion de
  Diputaciones Locales' (Baja California Sur local form, type 2)."), the head sections and the row count. Prompt sha256
  (`reader.prompt_sha256`):
  - `mx_bcs_dl_2024`: `58a92aec76c67218fbd5039f5de24aebcaefb3194e474fd20490962945dbd8bc`
  - `mx_bcs_dl_2024@sin_pes`: `74421b7ccc76172a909628236b5082370361bd02e542feb451270252b7820f40`
  - `mx_bcs_ayto_2024`: `b1de37ef0251c40483758350cd9ced844b895561c67ff7d476bbf676d2e3498e`
  - `mx_bcs_ayto_2024@sin_ml`: `9f430ae43c4c6a33999774e60fb7b0b7ef6ebd854e6b466c59af792ab18f9693`
  The presidential prompt (`3664253035b9…`) and the Senate prompt (`3c28a07a32a8…`) are unchanged byte for byte.
- **Reader: Gemma-4-31B-IT, temperature 0**, `max_tokens` 2000, no `response_format`, one read per acta. Served by
  **self-hosted vLLM on one AMD Instinct MI300X under the serving stack of PROTOCOL.md Amendment 4** (weights
  `google/gemma-4-31B-it` revision `842da3794eaa…`, bf16, one GPU; image `vllm/vllm-openai-rocm:v0.31.0@sha256:749f6f3f…`;
  exact command in `deploy/mi300x/README-session.md`), or by AMD Token Factory if Gemma-4-31B-IT is listed and answering
  there again on the run day. The choice, the served model id and the vLLM version are written to
  `results/ieebcs/RUN.md` before the first read; every call record carries the model id and the prompt hash.
- **Second reader: Qwen3.8-27B** (same prompt, `max_tokens` 6000, reasoning effort low), only after the Gemma pass, and
  reported second, never as the headline.
- Truncated replies, failed calls and unparseable replies are routed and their fields count as unmatched.
- Command (resumable; writes only `results/ieebcs/`; refuses unless this file is committed and unchanged):
  `python -m twohands.run --schema mx_bcs_dl_2024,mx_bcs_ayto_2024 --manifest results/manifest_ieebcs300.json --models gemma`
  (on the MI300X via `scripts/endpoint_switch.py -m twohands.run ...`, or the `ieebcs300` stage of
  `deploy/mi300x/orchestrate.py`, after `senado100`).

## 5. Metrics (pre-registered; all reported, whatever they show)

### 5.1 Reference
Ours: **the published PREP value** of each field in the final cut (their capture after verification and cotejo, as
published). Theirs: "la captura manual" (the human capture). These are close but not identical: the published value is
the value after their own checks. **A cleaner reference cannot depress our match the way a noisy reference can depress
theirs, so any difference from the reference favours us; we say so wherever the comparison appears.** The Document AI
values are not published (no column in the CSV or JSON; the report gives only aggregates), so their 62.84% cannot be
re-scored against our reference; ours can be re-scored by anyone (every read is in the repo).

### 5.2 (a) Raw per-field match: the number comparable in definition to their 62.84%
**Per-field match = fields whose digit reading equals the published value / all numeric fields on all 300 actas.**
- Denominator: every field of section 3.4 whose published value is a number, on **all 300 actas**: **3,622 fields**
  (1,876 diputaciones, 1,746 ayuntamientos; mean 12.07 per acta). Pages the locator rejects (1), actas not covered (5),
  failed or unparseable calls, and fields the model returns as null all count as **unmatched**.
- Fields whose published value is not a number are **excluded from the denominator, with their count reported**:
  46 on this sample (25 "sin dato", 12 blank, 9 "ilegible"). We do not know how their 62.84% treated such fields.
  A published `-` means the line is not on that acta's printed form: not a field.
- Match = exact integer equality of the model's digit reading ("n") with the published value.
- **Reported second, never first:** the same ratio over the fields of the pages the locator accepted.
- Wilson 95% interval; by election type; fields per acta per type and layout.

### 5.3 (b) After our gate (a separate line, never merged with (a))
- **Forms accepted** by the frozen gate (`twohands/gate.py`: shape, row labels with the neighbour-shift rule, every
  digit field read, words = digits, and the four identities: rows sum to TOTAL, votaron + representantes = section 5,
  section 5 = section 7, section 7 = TOTAL) out of 300.
- **Accepted-field errors against the published value**: on accepted forms, fields whose reading differs from the
  published value, each adjudicated from a crop of the **masked** page (`python scripts/ieebcs_score.py --crops`, into
  `results/ieebcs/adjudication/`) with one verdict: model_right, capture_right, neither, paper_ambiguous, unreadable or
  crop_wrong.
- **Fields where the published value does not match the paper** (verdict model_right), on all actas, labelled the way
  the Colima audit was: **the adjudicator is an AI reviewer (an AI model) working from the crops, labelled so everywhere**;
  a person spot-checks 20 adjudicated fields (all if fewer), drawn with `random.Random("20261020:spot")` over the list
  sorted by (clave, field), blind to the AI verdict; where the person disagrees, the person's verdict stands. The BCS
  PREP publishes no cómputos file in this database, so no cómputos join is made.
- Bias note, stated in advance: adjudication looks only where the reading and the published value disagree.

### 5.4 Scoring code
`scripts/ieebcs_score.py` computes everything from the committed raw files and writes the numbers block of
`results/ieebcs_head_to_head.md` and `results/ieebcs/score.json`; `make eval` re-checks them (0 mismatches required).
Until the run, the block reads "Empty until the run".

## 6. Limits of the comparison (stated wherever the comparison is shown)
1. **Same:** the actas (the same published images), the state, the election types, the definition of the metric
   (per field, exact match, matched / total), the kind of fields (count and vote boxes).
2. **Reference:** theirs the manual capture, ours the published final value (5.1); any difference favours us.
3. **Field list:** theirs is not published (≤ 14 crops per acta; 23,077 over 2,020 actas = 11.4 per acta); ours is
   stated in 3.4 (12.07 per acta on this sample).
4. **Conditions:** their run was live on election night; ours is offline, on the published images, with our
   registration, mask, tiling and prompt, at temperature 0. Their crops came from their own images, which may differ in
   resolution from the published ones.
5. **Sample:** 300 of 2,020 actas (Wilson interval reported); theirs is the full set.
6. **Not shown:** that the model would have performed the same live; that the published value is the truth (the paper
   decides, section 5.3).

## 7. Wording (same rules as the rest of Two Hands)
- Clerical wording only: a difference between a reading and a published value is a difference, nothing more. No
  inference about intent, parties or outcomes; vote rows are "Option NN" in every human-readable file.
- Comparison wording, used only after the run, on Results / the buyer section / a slide, never the hero:
  "In 2024 Baja California Sur's PREP used commercial cloud OCR for its first capture: 14,501 of 23,077 fields matched
  the manual capture, 62.84% (final report, p. 19). On a pre-registered sample of 300 of the same published actas,
  Gemma on AMD matched the published values on X% of all fields (Y% of pages the locator accepted). Same images;
  reference and pipeline differ, as stated on Results; their per-field output is not published, so it could not be
  re-scored." (X = 5.2 on all 300; Y = 5.2 second line.)
- Short form: "Commercial cloud OCR as the first capture in the 2024 BCS PREP: 62.84% of fields matched the manual
  capture (IEEBCS final report, p. 19). Open Gemma on AMD, on 300 of the same state's actas, against the same
  published values: X%."

## 8. Run order, stopping rule, deviations
- Run after this file is committed; Gemma first, Qwen second; results to `results/ieebcs/` only.
- **Stopping rule: the comparison is published whatever it shows, including below 62.84%.** No re-draw, no prompt or
  schema change after the first read; a fix found later is a new, separately labelled run.
- Deadline: if the Gemma pass and the scoring of (a) are not complete before the submission deadline
  (Sun 2026-10-18 10:00 UTC), nothing of this comparison is shown. (b) may be shown later only with its adjudication
  complete.
- Deviations are recorded in `results/ieebcs/RUN.md` with time and reason; none is made after looking at outcomes.

## 9. How the schemas were made (the builder)
Both schemas were made **with the schema builder** (`/builder`), driven through its HTTP API
(`scripts/ieebcs_build_schemas.py`: `POST /api/builder/validate` and `/api/builder/save`, then the builder re-opens
what it saved); `schemas/<slug>.yaml` is the builder's output byte for byte (`schemas/user/<slug>.yaml`, pinned in the
tests). **Two new form types in about 4 minutes of wall time** (00:14:01 to 00:18:02 UTC on 2026-10-16: geometry
measured on rectified pilot pages, the state drawn, both schemas saved, the per-layout rectification assets built, one
box adjustment re-saved). Builder gaps met, recorded here, not fixed in the builder (other work was editing the app):
1. no layout variants (the same form printed with fewer rows): written through the builder's `keep` pass-through as a
   `variants` block; the engine resolves `name@variant` (`twohands/schema.py`, a small addition);
2. no widgets for the PREP column per field, the public "Option NN" codes, the party aliases, the prompt wording or the
   data source: also through `keep`;
3. the builder does not build rectification assets (template, reference, landmarks, feature reference): a separate
   script (`scripts/build_ieebcs_reference.py`);
4. the builder's own test read uses its own prompt, not the engine reader; the engine reader was used for the hashes.
Engine support added for this run (no pre-registered prompt, schema or gate changed): schema variants
(`name@variant`), a schema-level `prompt_issuer` (default "INE", so earlier prompts are byte-identical), and a runner
manifest over several form types with per-item schema and a "not covered" status.

## 10. Placement rule (pre-registered before any read)

Where the comparison is shown depends only on the strict-denominator per-field match (metric 5a: all numeric fields on all
sampled actas, unlocated pages and null reads counted as unmatched), fixed now:

- **≥ 90%**: a card on the Home page ("the buyer's own benchmark"), plus the buyer section, Results and one slide.
- **80% to < 90%**: the buyer section, Results and one slide; not on Home.
- **< 80%**: a row on Results with the reading of why; not on Home or in the buyer section.

The comparison is published in every case (section 8).

```placement
home_threshold: 0.90
buyer_section_threshold: 0.80
metric: strict_per_field_match
```

## 11. Plumbing check (added before any read of the 300; pre-registered as such)

Before any metric is computed, a person compares our parsed read with the published CSV row on 5 actas (the first 5
located actas in manifest order), by eye, field by field, to catch a mis-mapped column or a wrong field order in the
join. Its only possible outcome is a fix to the **join/mapping code** (which CSV column feeds which schema field), recorded
here with the diff. **No prompt, schema box, tiling or gate change is allowed from it.** If a mapping fix is made, all
metrics are computed after it, on all actas, and the check and fix are reported on Results.

Also fixed now: the one acta the locator rejected, and the special-station actas with no schema, count as unmatched in
the strict denominator (section 5), and the strict figure is the one used in the comparison line and the placement rule
(section 10).
