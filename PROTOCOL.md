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
