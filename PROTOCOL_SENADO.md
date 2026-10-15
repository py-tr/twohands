# Pre-registered protocol: 100 held-out INE 2024 Senate actas (the third measured form type)

Status: **frozen before the first model call of this run.** This file, the schema, the code, the tests and the
manifest were written and committed to git before any Senate acta of the sample was sent to a model. Whatever the
numbers turn out to be, they ship (unless the deadline rule of section 9 applies, in which case nothing is shown).
This is a separate pre-registration. It does not amend `PROTOCOL.md`, and nothing here changes the presidential run.

## 1. Question
Two Hands accepts a tally sheet only when the sheet's own redundancy agrees with the read. Does that carry over,
unchanged, to a second INE form? On a random, held-out, stratified sample of 100 photographed or scanned Senate
casilla actas, how many does the same gate accept after one Gemma read? How accurate are the accepted fields after
adjudication? How many capture errors in the official first capture does the process find?

## 2. Sample

### 2.1 Population and eligibility (applied to the PREP CSV before the draw)
Source: the same INE PREP 2024 final database as `PROTOCOL.md` (`20240603_2005_PREP.zip`, cut 03/06/2024 20:05 UTC-6,
zip sha256 `dcccf23088f81a4ab7c7942a79504b04c4a9347b0a4744f6c328c59fd4d6c31d`). Its inner Senate zip holds
`SEN_2024.csv` (sha256 `bde437ee60c0f545fe57c749289ce61f56f959329cd971a5436fefe2e5736588`, 172,438 rows).

An acta (row) is **eligible** iff all of:
1. `TIPO_ACTA == "3"` (the Senate casilla acta). This excludes the special-station duplicates: a special station
   (`TIPO_CASILLA == "S"`) carries two actas under one `CLAVE_CASILLA`, majority (`3EMR`) and proportional
   representation (`3ERP`). It also excludes the `3PVA` / `3PVE` rows and rows without a type;
2. **layout rule:** its state prints the 18-row section 6 (both coalitions registered for the Senate there). In 13
   states, a coalition was not registered for the Senate, and the acta prints fewer, taller rows in the same frame.
   PREP leaves those coalition columns empty on every acta of the state. Excluded states (`ID_ENTIDAD`):
   no Coalición 2 rows: 2, 7, 12, 13, 22, 24, 25, 26, 27, 28, 29; no Coalición 1 rows: 11; no coalition rows: 20.
   The rule is computed from the CSV (a vote column empty on more than half of the state's Acta PREP rows) and checked
   against `schemas/mx_senado_2024.yaml` `source.exclude_states` (`scripts/senado_draw.py`);
3. not a special station (`TIPO_CASILLA != "S"`): the 20 special-station rows left after rules 1 and 2 are excluded too;
4. `TIPO_DOCUMENTO == "Acta PREP"`;
5. `DIGITALIZACION` is `Móvil` or `Escáner`;
6. its `CLAVE_CASILLA` is unique among `TIPO_ACTA == "3"` rows;
7. **the polling station has not been used in any presidential sample**: the 300 run (`results/manifest.json`), the
   100 confirmation forms (`results/manifest_confirm100.json`), the 150 calibration forms
   (`results/calibration_manifest.json`), the 43 pilot forms (`../spikes/tally-witness/data/sample.json`) and the
   Colima whole-state staging (`results/prepare_state06.jsonl`, 1,018 stations). It is also not one of the 20 Senate
   pilot pages (section 3.1). Together these are 1,629 stations.

No condition on `CONTABILIZADA` or `OBSERVACIONES`. Counts of every exclusion reason are in the manifest
(`population.excluded_by_rule`). Result: **99,167 eligible actas in 18 states** (19 states print the 18-row layout; Colima has none left after rule 7).

### 2.2 Strata, allocation, seed
- Strata: state × capture type (Móvil / Escáner); 36 non-empty strata.
- n = 100, allocated in proportion to stratum size and rounded by largest remainder (ties by stratum name).
- Within a stratum: the eligible rows are sorted by `CLAVE_CASILLA`, shuffled with
  `random.Random("20261019:<stratum>")` and taken in that order. **Seed: 20261019.** Code: `scripts/senado_draw.py draw`.
- Replacement rule (the only one): an acta whose image URL is absent from the PREP Senate district file
  (`.../assets/senadurias/entidad/{ent}_{dist}.json`) is replaced by the next acta in the same stratum. 0 were replaced.

### 2.3 Manifest
`results/manifest_senado100.json` (66 Móvil, 34 Escáner; 18 states). It lists, per acta, the clave, stratum, state,
district, capture type and image URL. It also holds the population counts, the strata and the exclusion counts.
**Manifest sha256: `29ecb1ae0394a39ba41452e1652e4d01fd057b445ad3a27059b740069d74d0d3`.**

### 2.4 Recorded before the freeze: a first draw over all 32 states
A first draw, with the same seed and rules but without rule 2, was made and prepared (located and masked only).
This file is `results/senado/manifest_draw1_allstates.json`, sha256 `ce4ddc33…a34e47`. **28 of its 100 actas were not
located**, mostly in the states that rule 2 now excludes. The feasibility check had assumed one layout. The cause was
found on 3 calibration pages from outside the sample (Sinaloa, Guanajuato, Oaxaca): those states print fewer, taller
section-6 rows. No page of either draw was opened by a person or sent to a model. The first draw's masked pages were
deleted, and its prepare log is kept (`results/senado/prepare_draw1_allstates.jsonl`). The population was then
restricted by rule 2 and redrawn with the same seed. Consequence for the claim: **the result covers the 18-row Senate
acta of 19 states, not every Senate acta.** The 14-row and 10-row variants would each need their own schema.

## 3. Privacy and preparation (before any model sees an image)

### 3.1 Rectification assets
The Senate acta has the same printed geometry as the presidential acta: the same corner markers, columns, section-6
row positions, section 7 and right column. Its header band is grey, its title differs, and it shows the big "3".
The assets are rebuilt the way `scripts/build_template.py` and Amendment 1 built the presidential ones, from **20 Senate
pilot pages** (the first 10 Escáner and 10 Móvil eligible actas of district Aguascalientes 1 in clave order). These 20
pages are excluded from the draw and listed in `results/senado/pilot.json`, sha256 `fe083bf4…e7aa`. The script is
`scripts/build_senado_reference.py`. Each pilot page was located in memory and its raw file deleted at once. All 20
were located by the presidential locator, and all 20 again with the new assets.
- `schemas/mx_senado_2024.template.npy` sha256 `3196249c76f7a8c8eafe05befb3bdd01d88b4e2104b64401b7e40c8c3c54bd2d`
- `schemas/mx_senado_2024.reference.npy` sha256 `5e0406f6158e7fa044eab76b9e5ed430d5557749db6b4dbfc8cf42b596156534`
- `schemas/mx_senado_2024.landmarks.npy` sha256 `e07da2af72e0c02e2e6fc55df593e3208ae251dbdd6c805d5e3b224c6c447b43`
- `schemas/mx_senado_2024.feature_ref.jpg` (one masked pilot scan) sha256 `ba8a1ed5f78ad8c48c80d5750be975d1cf60f7fb4965525468a9f67848da78bb`

The mask area is zeroed in all of them, so none holds a name or a signature.

### 3.2 Locate, mask, store
The steps are the same as `PROTOCOL.md` section 3 and Amendment 1, with the Senate assets: `twohands.mask.prepare`,
the landmark-checked locator, fail-closed. The mask is the whole right column, sections 10 to 14 (`[0.657, 0, 1, 1]`).
Masked pages are stored as 2400x1552 JPEGs in `data/masked/senado/`, and the raw files are deleted. The log is
`results/senado/prepare.jsonl`. **Done before this file was committed: 96 of 100 located (Escáner 34/34, Móvil 62/66).**
Not located: 100874C0100, 156186C0100, 190220E0112, 311179B0100 (all Móvil). These count as routed to a person and
are never replaced. The mask tests run on all 96 pages (`tests/test_senado.py`). The mask area is fully black. Every
gate region lies outside the mask and still holds ink. No tile carries mask pixels.

## 4. Reader (frozen)
- Schema: `schemas/mx_senado_2024.yaml`, **sha256 `a25f8e482ddc1b51300575d16a8b63665bbc61c33a6505334e468d296292f2f7`**.
  Its 23 fields (keys, INE columns, row labels), its identities, mask, tiles and gate regions are identical to the
  presidential schema (pinned by `tests/test_senado.py`). Vote rows show as "Option 01" to "Option 15" and the other
  lines by plain names (`public`).
- Prompt: the same reader and prompt structure (`twohands/reader.py`; system prompt, 23 items with label, digits and
  words, the same instructions and example). **One change:** the first line names the form. It now reads "'Acta de
  Escrutinio y Computo de Casilla de la eleccion de Senadurias' (federal form, type 3)" instead of "...de
  Presidencia' (federal form, type 2)". The reason: the prompt must describe the page the model actually sees. The
  big "3" and the title are printed on it, and a prompt that names the wrong form invites the model to doubt the page.
  The wording comes from the schema (`prompt_form`); the presidential prompt is unchanged byte for byte
  (sha256 `3664253035b9…`, pinned in tests). **Senate prompt sha256:
  `3c28a07a32a8f88110273fe578b3b25def064bc3ef664e61963b89910b1bf80f`** (`reader.prompt_sha256(schema)`).
- Input per call: the masked page plus the same 6 tiles, JPEG q88, longest side ≤ 2400 px.
- **Model: Gemma-4-31B-IT, temperature 0**, `max_tokens` 2000, no `response_format`. One read per acta and a single
  reader (no Qwen pass). The parser is `reader.parse`, unchanged. Truncated replies (`finish_reason == "length"`),
  failed calls and unparseable replies are routed, never accepted.
- **Serving stack: whatever serves Gemma on the run day.** The AMD Token Factory is used if Gemma-4-31B-IT is listed
  and answering there. It was withdrawn on 2026-10-15 at about 15:41 UTC. Otherwise the run uses Gemma-4-31B-IT
  self-hosted with vLLM on one AMD Instinct MI300X (`scripts/endpoint_switch.py`, `TWOHANDS_BASE_URL`). The choice,
  the served model id and the vLLM version are recorded in `results/senado/RUN.md` before the first read. Every call
  record carries the served model id. A switch mid-run happens only after an outage, and is recorded as a deviation
  with its time.
- Budget and retries: as `PROTOCOL.md` section 4 on the Token Factory (shared limiter, 6 requests/min, 0.80 USD/day
  pause). On the MI300X: the self-hosted limiter defaults (`scripts/endpoint_switch.py`). Calls that error are retried
  in later passes.
- Command (resumable; writes only `results/senado/`):
  `python -m twohands.run --schema mx_senado_2024 --manifest results/manifest_senado100.json --models gemma`
  or, on the MI300X, `TWOHANDS_BASE_URL=… TWOHANDS_KEY=… TWOHANDS_MODEL_GEMMA=<served id> python scripts/endpoint_switch.py -m twohands.run --schema mx_senado_2024 --manifest results/manifest_senado100.json --models gemma`.
  The runner refuses unless this file is committed and unchanged. It also refuses any reader other than Gemma and a
  manifest made for another schema.

## 5. The gate (frozen, unchanged)
**Primary:** the frozen gate `twohands/gate.py`, exactly as in `PROTOCOL.md` section 5. Shape (23 values), row label
(with the neighbour-shift rule for logo rows), every digit field read, words = digits, and the four identities: the 17
vote rows sum to TOTAL, votaron + representantes = section 5, section 5 = section 7, section 7 = TOTAL.
**Secondary (labelled so):** gate v2 of Amendment 3 (`twohands/gate_v2.py`: SOBRANTES must have its words read and
equal).

## 6. Ground truth and adjudication
- **Ground truth = PREP's official capture of the Senate acta** (`SEN_2024.csv`, the same image's first capture) on
  the 22 fields with a PREP column. Section 5 has none. A non-numeric PREP value makes that field ungradable; such
  fields are counted and reported, not scored. The certified Senate count (Cómputos) is not used.
- **Adjudication:** the same method as Amendment 2(b). Every field of every acta with a parseable read where Gemma
  disagrees with PREP gets a crop of the **masked** page (`python -m twohands.adjudicate --schema mx_senado_2024`, into
  `results/senado/adjudication/`). Each crop gets one verdict: model_right, capture_right, neither, paper_ambiguous,
  unreadable or crop_wrong. Every ungradable field on an accepted acta is adjudicated the same way.
- **The adjudicator is an AI reviewer (an AI model),** working from the crops, and every report labels it so.
  **Hand-checks:** 20 adjudicated disagreements (all of them if fewer) are drawn with `random.Random("20261019:spot")`
  over the list sorted by (clave, field). A person re-judges them from the same crop, blind to the AI verdict.
  Agreement is reported. Where the person disagrees, the person's verdict stands.
- Truth = PREP unless adjudication shows that the paper says otherwise.
- Bias note, stated in advance: adjudication looks only where the read and PREP disagree. A field where both are
  wrong in the same way counts as right.

## 7. Metrics (all reported, whatever they show)
1. **Accept rate** = accepted / 100 (unlocated actas and failed calls in the denominator), by capture type, with the
   route-cause breakdown (label, empty, words, identity, no read). The same for gate v2 (secondary).
2. **Accepted-field accuracy after adjudication** = right fields / graded fields on accepted actas, against PREP raw and
   against adjudicated truth, with Wilson 95% CIs. With about 100 actas, the CI will be wide, and we say so.
3. **Capture errors found** = adjudicated fields with verdict `model_right` (the paper agrees with the model, not with
   PREP), on all actas and on accepted actas. Each is listed with its clave, field (Option NN), model value, PREP value
   and crop.
4. Also: locate rate (96/100, known before the run), finish_reason distribution, parse failures, mean latency, and
   cost or GPU time per form.
5. For context only, never as a combined headline: the same metrics side by side with the presidential 300 run.

## 8. Wording (same rules as the rest of Two Hands)
- Clerical wording only. A "capture error" means that the capture does not match the paper, nothing more. No
  inference about intent, parties or outcomes.
- Neutral: vote rows are "Option 01" to "Option 15" on every page and in every human-readable file. No party is
  named, compared or totalled. Machine files keep INE's column names.
- This is not an official INE product. The PREP first capture is preliminary by design. We never claim that the
  model beats the official capture; the paper decides, and a person sees the rest.
- Every number carries its n and, where it is a rate, its Wilson 95% CI. The adjudicator is named as an AI reviewer.
  The scope is stated in full: "the 18-row Senate acta of 19 states" (section 2.4).

## 9. Run order, deadline, deviations
- Run after this file is committed, on Gemma only, once the serving stack of section 4 is up. It must not share the
  Token Factory budget with a running presidential pass. The results are written to `results/senado/` only.
- **Deadline rule:** if the run, adjudication and hand-checks are not complete before the submission deadline
  (Sun 2026-10-18 10:00 UTC), the Senate result is not shown anywhere. It would not appear on any slide, in the
  README or in the demo.
- Deviations are recorded in `results/senado/RUN.md` with their time and reason. None is made after looking at
  outcomes.
