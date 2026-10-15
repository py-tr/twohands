# Pre-registered protocol: auditing the CORD v2 receipt benchmark's own labels (100 test receipts)

Status: **record only; NOT to be run** (the receipt panel was dropped on 2026-10-15 before any model call). **Frozen before the first model call of this audit.** Everything below (this file, the schema, the code, the
tests and the manifest) was written and committed to git before any CORD receipt was sent to a model. Whatever the
numbers turn out to be, they ship, unless the kill rule (section 9) applies, in which case nothing is shown.

## 1. Question
Two Hands accepts a value only when the document's own redundancy agrees with the read. A printed receipt's only
redundancy is its arithmetic. On the 100 receipts of the CORD v2 test split: how many fields does the receipt's
arithmetic accept after one vision-model read, how accurate are those accepted fields after adjudication against
the image, and how many of the benchmark's own labels does that process show to be wrong?

## 2. Data and sample
- Dataset: **CORD v2**, `naver-clova-ix/cord-v2` (Park et al., 2019), licence **CC BY 4.0**, confirmed from the dataset
  card metadata (`license: cc-by-4.0`) at https://huggingface.co/datasets/naver-clova-ix/cord-v2 (revision
  `7f0115a4b758a71d6473b8d085751692da2fef98`, read 2026-10-15). Attribution: CORD, NAVER Clova, CC BY 4.0.
- File: `data/test-00000-of-00001-9c204eb3f4e11791.parquet` at that revision, sha256
  `51c65f1788faff392abe2a0b55b023eb23e9be551c509138eaa3a832514224e7`, stored in `data/raw/cord/` (gitignored), read only
  with `python -I` from `scripts/cord_audit.py`.
- **Test split only.** It holds exactly 100 receipts, so the sample is the whole split: **n = 100, no exclusions.**
  Receipts whose labels print no total, or violate an identity, stay in. Seed **20261016** fixes the read order only:
  rows sorted by `meta.image_id`, shuffled with `random.Random("20261016:cord-test")`.
- Manifest: `results/manifest_cord100.json` (per receipt: test index, image_id, sha256 of the image bytes and of the
  ground-truth JSON, label violations), **Manifest sha256: `0763c48c9380adf0e9ead185729e08eb6b62672964bf271719b470143b9f710c`**.
- Privacy: CORD images are released with personal information already blurred by the dataset authors. No other
  masking; images go to the model as published.

## 3. Schema and identities (`schemas/cord_receipt.yaml`, sha256 `ce7d3d9a9a241ae7793e5caf5c6a4609abaa680acc4e5a6acc1129592ceb21b6`)
Fields (whatever the CORD labels support): line items (name, count, unit price, price, line discount, add-on sub-lines
with their price); subtotal, tax, service, discount, total, cash, card, e-money, change. Amounts are integers in the
printed unit, thousands separators removed; discounts as positive numbers. **Receipts are printed by a till, so
there is no words-vs-digits field**: the arithmetic is the only redundancy.

Identities (checked only when every needed term is printed; optional terms `?` count 0 when absent):
1. **line prices sum to subtotal**: sum over lines of (price + add-on prices - line discount) = subtotal;
2. **subtotal + tax + service - discount = total** (also accepted: subtotal + service - discount = total, tax printed
   as already included, common on Indonesian receipts);
3. **paid - total = change**: cash + card? + e-money? - total = change;
4. **count x unit price = price**, per line where all three are printed.

**Rounding tolerance:** sides agree when |lhs - rhs| <= max(1, 0.005 x max(|lhs|, |rhs|)), i.e. 1 unit or 0.5%
(rupiah rounding of tax/service to the nearest 100). Counts at zero tolerance are reported alongside.

## 4. Reader (frozen)
- Prompt: `twohands/receipts.py::SYS` + `build_prompt()`, **Prompt sha256: `ff17bd8bb31bd5acee84da2f8182201440daa775407d8661b1368b35ef415e1c`**
  (`receipts.prompt_sha256()`; pinned in `tests/test_receipts.py`).
- Input per call: the receipt image + (receipts taller than 1.6x their width) 2-4 overlapping horizontal bands
  (`receipts.tiles`), JPEG q88, longest side <= 2400 px (core `reader.b64`).
- Output: one JSON object `{items: [{name, count, unit_price, price, discount, subs}], subtotal, tax, service,
  discount, total, cash, card, emoney, change}`; parsed by the core `reader.parse`.
- **Model: `Gemma-4-31B-IT`**, temperature 0, max_tokens 2000, no `response_format` (the core reader's settings).
  One read per receipt; no second reader. If Gemma is down, a switch to Qwen3.8-27B is a recorded deviation.
- Client and budget: the core `amd.chat` through the shared cross-process limiter (`twohands.ratelimit.shared()`,
  6 requests/min in total across every Two Hands process, 2 in flight, 429 Retry-After honoured). Core modules are
  imported, not edited.

## 5. The gate (`twohands/receipts.py::gate`, tests `tests/test_receipts.py`)
- A checked identity that fails routes the whole receipt (no field on it is accepted).
- A field is **accepted** when it is a term of at least one checked identity that holds, on a receipt where none fails.
- A field read but covered by no identity that held is **unverified** (reported, never counted as accepted).
- A receipt is **touchless** when it parsed, a total was read, no identity failed and every amount read is accepted.

## 6. Metrics (all reported, whatever they show)
1. **Accepted-field accuracy after adjudication** (primary): accepted fields whose read equals the truth / accepted
   fields, with Wilson 95% CI. Truth = the CORD label unless adjudication of the image says otherwise.
2. **Label errors found**: disagreements (read != CORD label, any field, accepted or not) where adjudication of the
   image shows the model right (`model_right`). Listed with crops.
3. **Touchless rate** (receipts touchless / 100): reported, **not a target**.
4. Also: fields accepted / unverified / routed, route reasons by identity, parse failures, finish_reason, latency, cost.
Item lines are paired with label lines by index when the counts agree, else by an in-order name match
(`receipts.align_items`). Item names are not graded.

## 7. Adjudication
- Every disagreement between the read and the CORD label is adjudicated by an **AI reviewer (an AI model) from crops** of
  the image (the CORD `valid_line` box of the field, `receipts.crop_box`; the model's line located by eye when the label
  has none), one verdict each: `model_right` / `label_right` / `both_wrong` / `ambiguous` / `unreadable`. The reviewer
  sees the crop, the read and the label. Verdicts and crops go to `results/cord_adjudication/`.
- **20 human spot-checks**: 20 adjudicated disagreements (all of them if fewer), drawn with
  `random.Random("20261016:spot")` over the adjudicated list sorted by (index, field), are re-judged by a person from the
  same crop, blind to the AI verdict. Agreement is reported; where they differ, the human verdict stands.
- Bias note, stated in advance: adjudication looks only where the read and the label disagree; a field where both are
  wrong the same way is counted right.

## 8. A first finding, before any model call: CORD's labels against the identities
`python -I scripts/cord_audit.py labels` -> `results/cord_label_audit.json`. On the 100 test receipts, 95 have at least
one checkable identity; **4 receipts' labels violate an identity at the stated tolerance** (8 at zero tolerance; the
other 4 are rupiah rounding of tax, 1-161 units):
| test index | identity | lhs | label |
|---|---|---|---|
| 0 | subtotal + tax + service - discount = total | 5,455 | 60,000 |
| 14 | paid - total = change | -81,435 | 18,565 |
| 48 | line prices sum to subtotal | 25,000 | 22,728 |
| 71 | paid - total = change | 2,200 | 22,000 |
Per identity (checkable / violated): line sum 63 / 1, total 64 / 1, change 51 / 2, count x unit 63 / 0.
These are **candidates, not label errors**: from the labels alone, 14 looks like an unlabelled payment line
(`total_etc` 100,000 makes it add up), 48 like tax-inclusive line prices, 0 like a full-value voucher; only 71 looks
like a keying slip. The image decides; each is adjudicated with the run.

## 9. Run order and kill rule
- **Run only after** the Qwen pass of the 300 and the 100-form INE confirmation (Amendment 3) have finished: all share
  one rate limit. The runner refuses without `--after-qwen-and-confirm100`, refuses if the prompt or manifest hash
  differs from this file, and refuses after the deadline.
- Command: `python -I scripts/cord_audit.py run --after-qwen-and-confirm100` (resumable; `results/calls_cord_gemma.jsonl`).
- **Kill rule:** if the audit is not run, adjudicated and spot-checked by **Fri 2026-10-16 22:00 UTC**, it is not
  shown anywhere (no slide, no README line, no demo).

## 10. Deviations
Any deviation is recorded in `results/RUN_CORD.md` with its time and reason; none is made after looking at outcomes.
