# Pre-registered protocol: 300 held-out INE 2024 presidential actas

Status: **frozen before the first model call of this run.** Everything below was written, and committed to git,
before any of the 300 actas was sent to a model. The commit hash of this file is recorded in
`results/RUN.md` once the run starts. Whatever the numbers turn out to be, they ship.

## 1. Question
On a random, held-out, stratified sample of 300 photographed or scanned INE 2024 presidential casilla actas,
how many does the form's own redundancy auto-accept after a vision model reads them, and how many fields on
the accepted forms are wrong?

## 2. Sample

### 2.1 Population and eligibility (applied to the PREP CSV before the draw)
Source: INE PREP 2024 final database `20240603_2005_PREP.zip`
(https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip, file `PRES_2024.csv`,
cut 03/06/2024 20:05 UTC-6; downloaded 2026-10-14; zip sha256 `dcccf23088f81a4ab7c7942a79504b04c4a9347b0a4744f6c328c59fd4d6c31d`,
CSV sha256 `c9d7282e9ba0dabdc6d0378eb3383010ad3f301a26d79c3035a9f2a2fd6d5c45`).

An acta (row) is **eligible** iff all of:
1. `TIPO_ACTA == "2"` (presidential acta de casilla; excludes VMRE / special-type rows 2E, 2PVA, 2PVPP, 2PVE);
2. `TIPO_DOCUMENTO == "Acta PREP"` (the image is the PREP copy of the casilla acta; excludes "Acta Consejo",
   "Copia PE", "RPP" and rows without a document);
3. `DIGITALIZACION` is `Móvil` or `Escáner` (an image was captured);
4. its `CLAVE_CASILLA` is unique among `TIPO_ACTA == "2"` rows;
5. it is not one of the 43 pilot ("spike") actas in `../spikes/tally-witness/data/sample.json`.

No condition on `CONTABILIZADA` or `OBSERVACIONES`: actas the PREP marked illegible, empty or non-counted
stay in the population (they are part of the real workload). Counts of every exclusion reason are written
into the manifest (`population.excluded_by_rule`).

### 2.2 Strata, allocation, seed
- Strata: state (`ID_ENTIDAD`, 32) × capture type (Móvil / Escáner) = up to 64 strata.
- n = 300, allocated proportionally to stratum size, rounded by largest remainder (ties by stratum name).
- Within a stratum: eligible rows sorted by `CLAVE_CASILLA`, shuffled with `random.Random("20261015:<stratum>")`,
  taken in that order. **Seed: 20261015.** Code: `twohands/sample.py`.

### 2.3 Exclusions after the draw (listed with reasons in the manifest)
- An acta whose image URL is absent from the PREP district file (`.../presidencia/entidad/{ent}_{dist}.json`)
  is **excluded and replaced** by the next acta in the same stratum's shuffled order; it is listed in
  `excluded_after_draw` with its reason. This is the only replacement rule.
- Every other failure **stays in the 300 and counts as not accepted** ("routed to a person"), never replaced:
  image download fails 3 times in each of 2 passes; image not decodable; the page cannot be located
  (corner markers not found / page does not match the form template / fine alignment too weak; section 3);
  the model call fails after all retries; the reply cannot be parsed; `finish_reason == "length"`.

### 2.4 Manifest
`results/manifest.json` lists the 300 actas (clave, stratum, state, district, capture type, image URL), the
population counts, the strata sizes and allocation, and the after-draw exclusions.
**Manifest sha256: `605af97756662abb2a27c35cf04075b1963ab50438bc710f7eab2b9ab706e081`** (sha256 of the file bytes as committed).

## 3. Privacy (before any model sees an image)
Each image is downloaded to `data/raw/` (gitignored), rectified onto the canonical page by its four corner
markers (homography, orientation by template correlation, ECC fine alignment; `twohands/register.py`), the
right-hand column (sections 10-14: names and signatures of polling officials and party representatives) is
filled black (`schemas/mx_presidencia_2024.yaml` `layout.mask`), the page is stored as a 2400x1552 JPEG in
`data/masked/`, and the raw file is deleted. Only masked pages and tiles cut from them (which never reach into
the mask; `tests/test_mask.py`) are sent to a model or stored. A page that cannot be located is not stored
and not sent.

## 4. Readers (frozen)
- Schema: `schemas/mx_presidencia_2024.yaml` (sha256 `c9240632c3f0a8bb934144a2068f7d90471edc7f43ff2e83ed212d9d3f42e4aa`).
- Prompt: built by `twohands/reader.py::build_prompt` from the schema; system + user prompt
  **sha256 `3664253035b912184e24a205852e7b8e686f0abb36a4340e91834d60dc71193f`** (`reader.prompt_sha256()`).
- Input per call: the masked full page + 6 tiles cut from it (left column; party rows; coalition rows; bottom
  rows + section 7; enlarged single-party logo cells; enlarged coalition logo cells), each JPEG q88, longest
  side ≤ 2400 px. Rectification assets: `schemas/mx_presidencia_2024.template.npy` (sha256 `af94049809d973b3418f766f392fbc522d372de5f59554616e51ffc3253f502f`),
  `schemas/mx_presidencia_2024.reference.npy` (sha256 `77f1194d7a0aa55465cd817bcbb57d340713bb6298798f6c88bde2eac55f28f5`).
- Output: one JSON object `{"values": [23 items]}`, each `{"label", "n", "w"[, "fix"]}` in schema order.
- **Primary: `Gemma-4-31B-IT`**, temperature 0, `max_tokens` 2000, **no `response_format`** (images + JSON mode
  break Gemma on this endpoint).
- **Second reader: `Qwen3.8-27B`**, temperature 0, `reasoning_effort: "low"`, `max_tokens` 6000, on **all 300**.
- Order: Gemma over all 300 to completion first, then Qwen (so the headline lands even if Qwen stalls).
- Parser: the first complete JSON object in the reply holding a `values` list; code fences, `<think>` blocks,
  trailing degenerate text and leading zeros (`"n": 003`) tolerated (`reader.parse`). `finish_reason`, usage,
  cost and latency are logged per call.
- Endpoint: AMD Token Factory (OpenAI-compatible). Budget: ≤ 6 requests/min in total, 2 in flight, 429
  Retry-After honoured with exponential backoff; GET `/usage` checked every 4 calls; the run pauses at
  0.80 USD daily spend and resumes after the 16:00 UTC reset. Calls that error are retried (6 attempts with backoff per call, then up to 12 passes over the remaining forms, a worker backing off 5 min after a failed call).

## 5. The gate (frozen; `twohands/gate.py`, tests in `tests/test_gate.py`)
A form is **accepted** only if all hold, else **routed to a person** with the failing fields named:
1. shape: 23 values parsed;
2. **row label**: every value comes back with the printed label beside it; code compares it with the schema
   position — else "row label mismatch". Section titles and text rows (no registrados, nulos, TOTAL) must match
   their keywords. Logo rows fail when the label is empty or fits a neighbouring logo row (i-1, i+1) strictly
   better than its own (score = shared logos + 1 if the logo count matches): evidence of a skipped, doubled or
   shifted row;
3. every digit field read (not null);
4. words = digits for every field whose words were read;
5. identities: 17 vote rows sum to TOTAL; votaron + representantes = section 5; section 5 = section 7;
   section 7 = TOTAL.

## 6. Ground truth and adjudication
- **vs PREP**: the model's digits vs the PREP capture of the same image, on the 22 fields that have a PREP
  column (section 5 has none). A PREP value that is not a number (`Sin dato`, `Ilegible`, `-`, empty) makes that
  field ungradable vs PREP; ungradable fields are counted and reported, not scored.
- **Adjudicated**: every field on an accepted form (either tier) where a reader disagrees with PREP, and every
  ungradable field on an accepted form, is checked by eye on the masked page crop by an AI adjudicator (a
  model, not a person), recording what the digit boxes and the words say. Truth = PREP unless
  adjudication shows the paper says otherwise. Adjudications with crops go to `results/adjudication/`.
  Bias note, stated in advance: adjudication looks only where a reader disagrees with PREP on accepted forms.
- A **PREP keying error caught** = an adjudicated field where the paper agrees with the model, not PREP.

## 7. Report (all of these, whatever they show)
For Gemma alone, Qwen alone, and the two-reader tier (**accepted iff both readers' gates pass and their 23
digit values agree**):
1. accept rate = accepted / 300 (unlocated and failed calls count in the denominator), by capture type;
2. fields right on accepted forms vs PREP, and vs adjudicated truth (count, rate, Wilson 95% CI);
3. accepted forms with every field right (adjudicated);
4. PREP keying errors caught (count, with crops);
5. route reasons (label mismatch / empty / words / identity / no read), and the label-gate's share;
6. finish_reason distribution, parse failures, mean latency, total cost and cost per form.

**Headline rule (pre-registered):** the headline is **single-reader Gemma** unless its accepted-field error
rate after adjudication exceeds **0.5%**; then the headline is the **two-reader tier**. Both are published.

## 8. Pilot work before the freeze (pilot actas only; none of the 300 was read)
Changes from the spike's v2 reader, each tried on the 43 pilot ("spike") actas, never on the held-out 300:
- Rectify + mask (section 3). On the 43 pilot images 41 are located; 2 Móvil photos fail closed and would go
  to a person: 120293C0100 (the form fills part of a photo of several overlapping actas; template score 0.09)
  and 151794C0200 (template score 0.26, orientation margin 0.03). On 40 further random non-manifest actas
  (calibration only, no model call) 37 were located, 3 Móvil failed closed.
- Tiles: the v2 crops ended at x = 0.69 and reached into sections 11-12 (names, signatures); they now end at the
  mask edge 0.657. Two enlarged logo-cell tiles were added because the label gate needs legible logos.
- Prompt: each value carries its printed label; section 6 rows are no longer named in the prompt (the model
  must report what it sees), and v2's hint listing the coalition-2 logo order was removed.
- Pilot reads (Gemma, 5 actas, `results/verify_spike_gemma_try*.jsonl`; Qwen, 2 actas,
  `results/verify_spike_qwen.jsonl`): values 22/22 right on 3/4 Gemma reads that returned and 2/2 Qwen reads,
  but strict logo-identity labels misfired (PRD read as "MC", MC as "PVEM", coalition rows copied from the row
  above), which led to the neighbour-shift rule in section 5 and the logo tiles. The final 6-tile prompt was
  verified on Qwen only: Gemma-4-31B-IT returned HTTP 503 on every call from about 00:45 UTC on 2026-10-15
  (`results/verify_spike_gemma_try3_outage.jsonl`), so the party-logo tile is unverified on Gemma. This is
  recorded here before the run, not discovered after it.

## 9. Deviations
Any deviation from this protocol is recorded in `results/RUN.md` with its time and reason; none is made
after looking at outcomes.

## Amendment 1 (2026-10-15, before any model read of the 300): the page locator

**What happened.** Preparing the 300 actas with the pre-registered locator (commit `a93294c`) left **52 of 300
not located** (50 of 196 Móvil, 2 of 104 Escáner), about 17%, against about 8% predicted from 40 calibration
actas. Those 52 would have been routed to a person before any model saw them. No model read of any of the 300
had succeeded when this amendment was written: Gemma-4-31B-IT was returning HTTP 503 and the run was stopped.

**What changed (locator only).** `twohands/register.py::rectify_v2`, used by `mask.prepare` (`mask.LOCATOR =
"amendment1"`):
- the accept decision moves from the coarse template score (score ≥ 0.25, margin ≥ 0.08) and ECC ≥ 0.55 to a
  **landmark check**: 8 printed-structure windows next to the gate regions (section 6 header, digit-box column,
  TOTAL row, section 7, left-column sections 2-5, header block) are matched by normalised cross-correlation against
  a landmark reference (mean aligned pilot page, mask area zeroed; `schemas/mx_presidencia_2024.landmarks.npy`,
  sha256 `c148a6289c6c98a90a84bbd8434cdc0bfb8c81b101719b84bf9541330f86c5d8`). A warp is accepted only if **every** window lands within
  12 px at 1200 px width (1% of the page width) with correlation > 0.3;
- candidates: every plausible marker frame with its two best orientations, the image itself as a frame, and a
  SIFT + RANSAC homography against a masked reference scan (`schemas/mx_presidencia_2024.feature_ref.jpg`, sha256
  `3c1bb2b7d4a5b89e72179e355e6eb7fbff766554d6f437bb5b66d74d80eabda2`) for photos whose corner markers are cut off; ECC refines
  each; the first candidate that passes the landmark check is kept;
- still fail-closed: if no candidate passes, `NotLocated`, nothing stored or sent, routed to a person.
Nothing else changes: the sample, the manifest (sha256 `605af977…e081`), the mask rectangles, the tiles, the
prompt (sha256 `3664253035b9…`), the readers, the gate and the metrics are as pre-registered.

**How it was tuned.** Only on the 43 pilot actas and on a **fresh calibration set**: seed **20261016**, n = 150,
the same eligibility and state × capture strata (100 Móvil, 50 Escáner), excluding the 300 run actas and the 43
pilot actas (`results/calibration_manifest.json`, sha256 `d6786a7f9348dfc31c13faff87029423042562c07d5c2090bf73e8774183f2cf`;
`scripts/calib_draw.py`). None of the 52 failures was opened, viewed or used.

**Locator accuracy on the calibration set** (`results/calibration_locator.jsonl`, `results/calibration_audit.json`):
- original locator: located 128 / 150 (Móvil 79 / 100, Escáner 49 / 50);
- Amendment 1: located 144 / 150 (Móvil 94 / 100, Escáner 50 / 50); of these, **143 correctly aligned** by an
  eye audit of every located page (page overlaid on the reference over the section 6 digit column and section 7;
  doubled printed lines = misaligned). The one misaligned page is a bent sheet whose middle rows curve by more
  than 1%; its digit boxes are still left of the mask. **Located and correctly aligned: 143 / 150 (95.3%).**
- pilot: 43 / 43 located; 151794C0200 and 120293C0100 (a photo of several overlapping actas) are now located, and
  the latter was checked by eye to be the right acta (section 0293, casilla C1).

**Reporting.** Both are reported: the touchless (accept) rate with the original locator (the 52 count as routed and
their reads are not used; the other 248 use their Amendment 1 reads) and with Amendment 1 (all 300 re-prepared). Re-preparation log:
`results/prepare.jsonl`; the original locator's log: `results/prepare_original_locator.jsonl`.

## Amendment 2 (2026-10-15 10:36 UTC): secondary analyses (primary and headline rule unchanged)

**When and what was seen.** Written after observing the Gemma touchless (accept) rate on the first ~299 of the
300 forms (about 45 accepted), and **before any Qwen read of the 300 and before any adjudication**. The Qwen pass
is blocked in code (`twohands.run`) until this amendment is committed. The primary analysis, the metrics of
section 7 and the headline rule are unchanged; everything below is secondary and is labelled so in every report.

(a) **Primary, as committed**, reported with its route-cause breakdown: the touchless count, and how many routed
forms carry each cause (row label mismatch, empty field, words != digits, rows != TOTAL, section identities, no read
/ not located), both "any cause" and "only cause".

(b) **Second-keyer agreement.** Across ALL fields of ALL forms with a parseable Gemma read (accepted or not), count
agreement of the model's digits with the official PREP capture. Every disagreement is adjudicated on the masked
image crop together with the certified Cómputos value, with one verdict: **model right / capture right / paper
ambiguous / unreadable**. Report A = model right (a capture error found) and B = model wrong, each with the full
list (clave, field, model, PREP, Cómputos, verdict, crop path). Tool: `twohands/adjudicate.py`; crops of masked pages
only, in `results/adjudication/`.

(c) **Capture gate (Gemma alone)**: words = digits on every field AND the 17 rows sum to TOTAL; no section-5 =
section-7 identity, no row-label check. Reported as "fields captured with no person" (forms passing, and their
fields), with accuracy vs PREP and vs adjudicated truth.

(d) **Two-reader tier (strict mode)**: Gemma = Qwen on every one of the 23 digit values, plus the capture gate of
(c) on that agreed read.

(e) **Paper audit**: the number P of the 300 forms that are internally inconsistent on the paper itself (section 5 !=
section 7, rows != TOTAL, words != digits as written), counted from reads and confirmed where PREP or Cómputos allow
(rows != TOTAL from the PREP capture; section 5 by eye, since PREP does not capture section 5 by design). Clerical
wording only.

**Label-gate false alarms.** A form routed by the row-label check counts as a false alarm when its read matches PREP
(adjudicated) on every graded field; reported as a count over label-routed forms, overall and where the label was the
only cause.

## Amendment 3 (2026-10-15 ~13:40 UTC): a fresh confirmation draw of 100 forms for gate v2

**Why, and what was seen.** Gate v2 below was designed **after** seeing the Gemma reads of the 300 and the Amendment 2
adjudication (`results/adjudication/SUMMARY.md`): 2 of the 3 disagreements on the 55 accepted forms were model misreads
of SOBRANTES (section 2), the one graded field that sits in no arithmetic identity, and the row-label check routed 86
forms, at least 68 of them on reads that match the paper. Any number gate v2 produces on the 300 is therefore
**post-hoc** and is labelled so (`results/posthoc_v2_300.md`). The test of gate v2 is a fresh, untouched draw.

**Sample.** Seed **20261017**, n = **100**, the same eligibility rules (section 2.1), the same state x capture strata,
proportional allocation by largest remainder and within-stratum shuffle `random.Random("20261017:<stratum>")` (section
2.2), the same replacement rule (2.3), **excluding the 300 run actas, the 43 pilot actas and the 150 calibration actas**.
Code: `scripts/confirm_draw.py`. Manifest: `results/manifest_confirm100.json` (66 Movil, 34 Escaner, 0 replaced),
**sha256 `cc238efc2a1110944b6d29c9e3b0acdf32fa24062e1305706ef5145b30e570a8`**. Preparation (download, Amendment 1
locator, mask, raw deleted) is done before any read; log `results/prepare_confirm100.jsonl`. No page of the 100 is
viewed by a person or sent to a model before this amendment is committed. Unlocated pages count as routed, never replaced.

**Readers, prompt, schema, locator, mask, tiles:** unchanged (sections 3-4, Amendment 1). Gemma-4-31B-IT and
Qwen3.8-27B each read all 100, Gemma first.

**Gate v2** (`twohands/gate_v2.py`; the frozen `twohands/gate.py` is not changed). A form is accepted under v2 iff:
1. it passes every check of the frozen gate (section 5: shape, row label, every digit field read, words = digits where
   words were read, the four identities); and
2. **(a)** every field that appears in **no** arithmetic identity of the schema (computed from the schema; for this form
   only SOBRANTES) has **both** digits and words read **and** equal. Otherwise the form routes (code `unchecked`).
- **v2, two-reader variant (v2-2R):** as v2, except that an unchecked field whose words are missing or differ from its
  digits is accepted when Qwen's digits for that field equal Gemma's (Qwen's read otherwise not required to pass its gate).
- **(b)** the row-label check is **unchanged** in v2. **v2b (secondary):** as v2, but the label check on logo rows is
  relaxed: a logo row fails only if its label is empty, or it is part of a **run of two or more adjacent logo rows that
  each fit the same-direction neighbour (i-1, or i+1) strictly better than their own row** (the trace of a skipped or
  doubled row). An isolated misnamed logo passes. Text rows (sections 2-5, 7, NO REGISTRADAS, NULOS, TOTAL) keep the
  keyword rule unchanged.

**Truth and adjudication:** as section 6 and Amendment 2: every graded field on a form accepted under any of v1, v2,
v2-2R, v2b where Gemma disagrees with PREP, and every ungradable field on such a form, is adjudicated on the masked crop.

**Success criterion (pre-registered, primary = Gemma single-reader v2):** the **accepted-field error rate after
adjudication is <= 0.5%** (errors / graded fields on v2-accepted forms; point estimate, reported with its Wilson 95%
CI, which at this sample size will extend above 0.5%). Reported alongside, whatever they show: **touchless coverage**
(v2-accepted / 100, unlocated and failed reads in the denominator, by capture type), the same for v1, v2-2R and v2b
(v2b secondary), accepted-field errors for each, and the route-cause breakdown. If v2 fails the criterion, that is the
result.

## Amendment 6 (2026-10-15 ~23:55 UTC, before any bake-off read): open-model bake-off on AMD (secondary)

**Question.** Which open model on AMD Token Factory reads these forms best, and which pair of readers is the safest
second keyer? A **secondary** analysis: the primary analysis, the headline rule and every number already reported are
unchanged. Gemma-4-31B-IT (withdrawn from Token Factory on 2026-10-15) and Qwen3.8-27B enter with their reads of the 300
(`results/calls_gemma.jsonl`, `results/calls_qwen.jsonl`); they are not re-read.

**Readers.** Every model on Token Factory's `GET /models` list that is vision-capable (`vision: true` or `image` among its
input modalities) and accepts our request. Each is **probed with ONE call** on a pilot page (`data/masked/spike/010441C0100.jpg`,
one of the 43 pilot actas; none of the 300): the same 7 images and frozen prompt. A model is **compatible** iff the call
returns HTTP 200 and `reader.parse` finds a `{"values": [...]}` object. Probes are not results. A model that fails is
listed as **not compatible** with the reason (no image input, request refused, unparseable reply). Expected today:
DeepSeek-V4-Flash-Vision-Exp, MiniCPM-V-4.7-35B-A3B, MiniCPM-V-4.7-1B, plus whatever else the list marks as vision-capable.
Code: `scripts/bakeoff.py probe` -> `results/bakeoff_probe.jsonl`.

**Fixed for every reader:** the same 300 forms (manifest sha256 `605af977…e081`) and masked pages (Amendment 1), the same
page + 6 tiles (JPEG q88), the same frozen prompt (sha256 `3664253035b912184e24a205852e7b8e686f0abb36a4340e91834d60dc71193f`),
temperature 0, the same parser and the **frozen gate** (section 5) via `twohands.run.record`. **Per-model parameters:**
Qwen's frozen parameters (`max_tokens` 6000, `reasoning_effort: "low"`, no `response_format`); a parameter the API refuses
at the probe (HTTP 400 naming it) is dropped for that model, and the parameters used are recorded per model in
`results/bakeoff_plan.json` and on every row.

**Metrics** (per model; `scripts/bakeoff.py report` -> `results/bakeoff_300.md`, `app/data/bakeoff_300.json`; recomputed
independently by `make eval`):
1. **field agreement with the capture**: digits equal to the PREP capture / graded fields with a numeric PREP value, over
   every form with a parseable read (accepted or routed);
2. **accepted forms**: single-reader frozen gate; unlocated pages and failed reads count in the denominator;
3. **accepted-field errors after adjudication**: on accepted forms, fields judged against the paper. Truth = the existing
   verdict for that form and field where one exists (`results/adjudication/verdicts.json`, reused as is); otherwise, for a
   NEW disagreement with the capture on an accepted form: the **certified count** where it applies (a vote row or TOTAL
   whose Cómputos Distritales record is a cotejo, not a recount: the certified value is a reading of this paper and is
   taken as the paper), else the **AI adjudicator** (an AI model, an AI agent; labelled so) reads the masked crop of that field.
   New verdicts go to `results/adjudication/verdicts_bakeoff.json` with who decided. A field where the reader equals the
   capture and no verdict exists counts as right (section 6);
4. **cost per 1,000 forms** (every attempt, as billed by the API) and **mean latency** (server time of the answered request);
5. **every two-reader pair**, including with Gemma and Qwen: the Amendment 2 (d) strict two-reader tier (both readers'
   23 digit values agree, every digit read, words = digits wherever either reader read words, rows sum to TOTAL), accepted
   forms and accepted-field errors after adjudication, on the forms both have read.

**Order and the budget rule (subset).** The 300 are read in a **fixed, capture-stratified shuffled order**
(`results/bakeoff_order.json`; seed `20261019:bakeoff`; each capture type sorted by clave and shuffled with
`random.Random("20261019:bakeoff:<type>")`, merged so every prefix holds Móvil and Escáner in proportion; sha256 of the
newline-joined order `8de453814d3db5c455a5f4b72d753484f5ded1bb37710a50a288e65dd03437b4`). The models read interleaved, form
by form in that order. Budget: this run spends at most **$0.40 per Token Factory day** (reset 16:00 UTC), checked with
`/usage` before every batch of 8 calls (it also pauses if the key's whole day passes $0.90, leaving the live worker room); over the cap it
sleeps to the reset. Reads stop at **2026-10-17 12:00 UTC**. Each model gets a **spend cap** fixed from its probe cost
before any read: total $0.75, water-filled (a model needing 300 x probe cost x 1.15 or less gets that; the rest split the
remainder equally). A model that hits its cap or the stop time has read the **first n forms of the fixed order**, and is
reported with that n (and Gemma and Qwen on the same first n alongside); pairs are compared on the forms both have read.
The plan (parameters, probe costs, caps) is written to `results/bakeoff_plan.json` and committed after the probes and
before the first read; `scripts/bakeoff.py run` refuses to start unless this amendment and the plan are committed.
Calls: `results/calls_<model id in lower case>.jsonl` (resumable; the last row per form counts; failed calls are retried
in later passes, then count as routed).

**Headline (plain):** "Which open model on AMD reads handwriting best, and which pair is the safest second keyer": best
reader = highest field agreement with the capture; safest pair = fewest accepted-field errors after adjudication, ties
broken by more accepted forms.
