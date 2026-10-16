# Head-to-head on the buyer's own data: Baja California Sur PREP 2024 (PROTOCOL_IEEBCS.md)

**Their first capture.** In the 2024 local PREP of Baja California Sur (IEEBCS), the first capture of every acta was
a commercial cloud OCR (a custom Google Document AI model), field by field on crops of the acta: 14,501 of 23,077
fields matched the manual capture, **62.84%** (IEEBCS, *Informe final del PREP, PELO 2023-2024*, p. 19).

**Ours.** Gemma-4-31B-IT, open weights, self-hosted with vLLM on one AMD Instinct MI300X, one read per acta at
temperature 0, on a pre-registered stratified sample of 300 of the same state's published actas (seed 20261020),
scored against the same PREP's published values. Both election types (diputaciones locales, ayuntamientos), in their
published proportion. The numbers below are written by `scripts/ieebcs_score.py` from the committed raw files and are
checked by `make eval`.

<!-- BEGIN NUMBERS (scripts/ieebcs_score.py) -->
Empty until the run (PROTOCOL_IEEBCS.md). No acta of the sample has been read by a model.
<!-- END NUMBERS -->

## What is and is not comparable (PROTOCOL_IEEBCS.md section 6)
- **Same:** the state, the election, the actas (the same published PREP images, fetched from the PREP's own S3
  bucket), the definition of the metric (per field, exact match, matched / total fields), the kind of fields (the
  count and vote boxes, no identification field).
- **Different reference:** theirs is the manual capture; ours is the published final value (after their
  verification and cotejo). A cleaner reference cannot depress our match the way a noisy reference can depress
  theirs, so any difference from the reference favours us. Document AI's per-field output is not published, so
  their 62.84% cannot be re-scored against our reference; ours can be re-scored by anyone (every read is in the repo).
- **Different field list:** theirs is not published (at most 14 crops per acta; 23,077 fields over 2,020 actas);
  ours is stated per type and layout above.
- **Different conditions:** their run was live on election night; ours is offline. Their crops came from their own
  images (possibly at another resolution); ours come from the published images, registered, masked and tiled by
  our pipeline.
- Fields whose published value is not a number ('sin dato', 'ilegible', blank) are out of our denominator (count
  above); we do not know how their 62.84% treated them.

## Wording for the page (only after the run, Results / buyer section / slide, never the hero)
> In 2024 Baja California Sur's PREP used commercial cloud OCR for its first capture: 14,501 of 23,077 fields matched
> the manual capture, 62.84% (final report, p. 19). On a pre-registered sample of 300 of the same published actas,
> Gemma on AMD matched the published values on X% of all fields (Y% of pages the locator accepted). Same images;
> reference and pipeline differ, as stated on Results; their per-field output is not published, so it could not be
> re-scored.

Short form: "Commercial cloud OCR as the first capture in the 2024 BCS PREP: 62.84% of fields matched the manual
capture (IEEBCS final report, p. 19). Open Gemma on AMD, on 300 of the same state's actas, against the same published
values: X%."

X = (a) of the numbers block; Y = the read-page share where "pages the locator accepted" = located pages. Clerical
wording only: a mismatch is a difference between a reading and a published number, nothing more.
