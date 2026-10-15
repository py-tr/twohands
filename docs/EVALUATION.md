# Evaluation

What we measured, how, and where it breaks. Every number has a source file; the full list is in
[`NUMBERS.md`](NUMBERS.md). Wilson 95% intervals are our own computation from the counts shown.

## Organiser checklist

| Item | Where |
|---|---|
| Headline | [Pre-registered random run](#pre-registered-random-run-300-forms-the-headline) |
| One business result | [Business result](#business-result) |
| One known limitation | [Known limitations](#known-limitations) |
| One failure case | [Failure case](#failure-case-a-silent-row-shift) |
| The safeguard or human review process | [Safeguard](#safeguard-and-human-review) |

## Ground truth

- **Tally sheets.** Mexico's 2024 presidential polling-station tally sheets (INE, type 2). Each image has an
  official double-keyed capture (PREP: two people key every form, a third reviews mismatches) and, for most vote
  rows, a later certified count (Cómputos). We grade the model's digits against the official capture on the 22
  fields that have one. On the pre-registered 300, every disagreement is settled on a crop of the masked image; in
  the pilot, only disagreements on accepted forms were.
  Truth = the official capture unless the image says otherwise.
- **Rainfall ledgers.** Rainfall Rescue sheets (UK, 1850-1960), graded against the volunteers' transcription
  (~16,000 volunteers, 4 transcriptions per value; Hawkins et al. 2022). Match = within 0.005 in.

## Pre-registered random run: 300 forms (the headline)

The protocol (`PROTOCOL.md`) was committed in `a93294c` before any of the 300 was sent to a model. It fixes the
sample (stratified by state x capture type, seed 20261015, manifest sha256 `605af977...e081`), the prompt (sha256
`3664253035b9...`), the gate, the metrics and the headline rule. **Amendment 1** (commit `b0e443c`) replaced only
the page locator, also before any model read of the 300: the original locator left 52 of 300 pages unlocated (50 of
them phone photos). The new locator was tuned on the 43 pilot forms and a **fresh calibration set of 150** (seed
20261016, disjoint from the 300): **143 of 150 located and correctly aligned** by an eye audit of every page (Wilson
95%: 90.7% to 97.7%). **Amendment 2** (before any Qwen read and before any adjudication) added the secondary
analyses below. **Amendment 3** defines a gate variant designed after seeing these reads; its numbers on the 300 are
post-hoc (`results/posthoc_v2_300.md`), and its test is a fresh 100-form draw.

Every number in this section is computed by `scripts/build_headline.py` into `app/data/headline.json` (the web app
reads the same file) from `results/calls_gemma.jsonl` (last read per form) and `results/adjudication/`.

| Metric | Gemma-4-31B-IT on AMD |
|---|---|
| Pages located and read | 289 of 300; 11 not located (all phone photos) go to a person before any model call |
| Fields compared with the official capture (22 per form) | 6,358 |
| Agreement with the official capture | 6,091 of 6,358 (95.80%) |
| Fields disputed (sent to a person) | 267 (4.2%) on 104 forms |
| Settled on the photo | capture mis-keyed 52 · model misread 156 · both off 17 · paper ambiguous 34 · unreadable 8 |
| **Keying errors in the official capture** | **52**; the certified count covers 31 and confirms the image on 22; all 9 differences were recounts |
| The model alone | wrong on 173 of 6,358 fields (156 + 17): about 1 in 37 |
| Accepted with no person (frozen gate, primary) | 55 of 300 (18%): 27 phone photos, 28 scans |
| Accepted fields wrong after adjudication | **2 of 1,210** (about 1 in 605; Wilson 95% 0.04% to 0.60%), so the headline rule (error rate <= 0.5%) keeps the single-reader tier |
| Yield of a disputed field | 52 of 267 = 1 in 5, against 52 of 6,358 = about 1 in 122 at random: up to 24x |
| Recall bound | on the 100 forms the certified count settled by comparison, the model had disputed 7 of the 23 fields where the certified count disagrees with the first capture (Wilson 95% 16% to 51%); a bound, not a measurement (`results/adjudication/RECALL.md`) |

**The model alone is a worse keyer than the official two-person capture: 156 misreads against 52 keying errors in
6,358 fields. That is why it never decides. The paper does, and a person sees the rest.** On accepted fields the
pair made 1 error and the model 2; we never claim the model beats the pair. The first capture is preliminary by
design; the certified count is the official result.

### The 52 keying errors by type

| Type | Fields |
|---|---|
| Wrong value keyed | 17 |
| Legible field marked illegible | 27 |
| Value keyed where the paper is blank | 6 |
| Other (legible field captured as "no data") | 2 |

One form shows how a single slip becomes three errors: on 250767B0100 the capture keyed each of sections 2 to 4 with
the value written one section further down (unused ballots keyed 390, the voters' figure; voters keyed 3, the
representatives' figure; representatives keyed 393, the section 5 total). Every case, with its crop:
`results/adjudication/SUMMARY.md` and the app's audit page.

## Pilot (43 hand-picked forms)

Before the pre-registered run. Kept for the record; it is not a headline.

**Sample.** 43 forms from 10 districts in 10 states, 23 phone photos and 20 scans. **Deliberately enriched with
trouble**: 16 clean, 5 with a paper row-sum mismatch, 12 where the official capture differs from the certified
count, 10 recounted (`spikes/tally-witness/README.md` section 2). Not random, and its accept rate does not
generalise: we once called it a lower bound, and the random 300 accepted 18% against the pilot's 49%.

| Reader | Accepted | Accepted fields wrong (raw vs capture, then after eye check) | Routed but read perfectly | USD / form |
|---|---|---|---|---|
| Gemma-4-31B-IT, page + 3 tiles (v1) | 17 / 43 (40%) | 6, then **0 of 374** | 6 | $0.000102 |
| **Gemma-4-31B-IT, page + 4 tiles (v2)** | **21 / 43 (49%)** | 5, then **0 of 462** (Wilson 95% upper 0.82%) | 7 | $0.000118 |
| Qwen3.8-27B, page + 3 tiles | 22 / 43 (51%) | 4, then **0 of 484** (upper 0.79%) | 10 | $0.000507 |
| Both agree on every field + gate | 20 / 43 | 0 | | $0.00063 |

Sources: the app's results page, computed from the spike result files (snapshot `app/data/spike_runs.json`) and
`spikes/tally-witness/adjudicate.json`; the two-reader row from `spikes/tally-witness/README.md` section 3.

"Routed but read perfectly" means every field was right but the paper itself is inconsistent (rows that do not
add up, words that disagree with digits). Those are correct routings, not reader errors.

Base rate for context: in the official national capture, 19.2% of fully captured forms (26,336 of 137,196) fail
their own row sum (PREP 2024 CSV, `spikes/tally-witness/README.md` section 1).

### Keying errors found in the pilot

On forms the gate accepted, the model and the official capture disagreed on **6 fields on 5 forms**. In every
one the image shows the official capture mis-keyed and the model read it right. **The certified count covers 5
of them and matches the image on all 5** (the sixth, section 7, is not part of the certified data).

| Form | Field | Image shows | Capture keyed | Certified |
|---|---|---|---|---|
| 093954C0200 | Option 01 | 69 | 64 | 69 (by comparison) |
| 156723B0100 | Option 08 | 5 | 3 | 5 (by recount) |
| 202451B0100 | TOTAL | 271 | 272 | 271 (by comparison) |
| 202451B0100 | Section 7 (ballots taken from the boxes) | 271 | 272 | not in certified data |
| 211298B0100 | Option 06 | 39 | 34 | 39 (by comparison) |
| 211420C0400 | Option 14 | 2 | 0 | 2 (by comparison) |

These are typing mistakes in a capture, nothing more. Vote rows are named by printed position only. Crops are
in the app's audit gallery.

**Not a keying error, shown apart:** on 211294C0100 the TOTAL digits say 262 and the words say 162. The capture
applied its words-prevail rule and keyed 162; the rows, section 7 and the certified count (262) support 262. The
paper contradicts itself, so the gate routed the form to a person. That is the gate doing its job.

## Second form type: rainfall ledgers (spike, 40 sheets)

| | |
|---|---|
| Sheets / cells | 40 sheets from 5 stations, 4,915 cells |
| Identity | 12 monthly values = the clerk's handwritten annual total (within 0.01 in) |
| Reader | Gemma-4-31B-IT, whole sheet + 3 zoomed strips, no re-reads |
| Year-columns accepted | 306 of 380 (80.5%) |
| Accepted cells right | **3,976 of 3,976** (spike, 40 sheets; Wilson 95% upper 0.10% error) |
| Cost | $0.00011 per sheet |

Source: `ledger/ledger.json` (built from `spikes/ledger-rescue` with the spike's own scorer).

## Business result

On 289 random forms already keyed twice, the model sent **267 of 6,358 fields (4.2%)** to a person, and **52** of
those were confirmed keying errors in the official capture, each with its photo. The AMD compute cost was
**$0.000144 per form** (mean over the 289 reads), about $0.14 per 1,000 forms, or about $24 to re-read all 169,005
national tally forms. The buyer is the auditor: Mexico requires an outside audit of every PREP (Reglamento de
Elecciones art. 347), and in 2024 UNAM centres audited several state PREPs (sources in the README).

## Known limitations

- **One reader, one adjudicator.** Every disagreement was settled by one reviewer (the builder, an AI agent, not a
  native Spanish speaker) on published crops; anyone can re-check them, and the app's blind spot-check page lets a
  person do so without seeing any AI or capture value.
- **Recall is only bounded.** We checked only where the model disagreed with the capture, so errors both made are
  not counted. On forms the certified count settled without a recount, the model had disputed 7 of the 23 fields
  where the certified count disagrees with the first capture; council corrections can move certified values, so
  this is a bound.
- **The label gate's cost.** The row-label check routed 86 forms; on 68 of them the read matched the paper on every
  graded field, including all 15 forms routed for a label alone. Each false alarm costs a person one look.
- **One read is not two independent reads.** In one call the model can harmonise words and digits: on 010469C0400
  it read unused ballots as 239 in digits and 239 in words, while the paper says 234 in both. That field sits in no
  identity, so the gate accepted the form; it is one of the 2 wrong fields on accepted forms. The fix is separate
  reads or a second reader.
- **Throughput on a shared key.** About 2 forms a minute under our pacing; mean latency 87 s per form on the 300
  (wall clock, including queueing). A real deployment needs a dedicated AMD endpoint, which we have not measured.
- **Page locator.** 11 of 300 phone photos could not be located and go to a person before any model call.
- **The gate cannot see an error that keeps the arithmetic true.** See the failure case.

## Failure case: a silent row shift

On the rainfall ledgers, read as **one image**, Gemma put Balcombe Gables' 1887 values under 1886, and so on
along the row. Every shifted column still summed to its total, so the checksum accepted wrong cells: **26 of
870 accepted cells were wrong** on that reader (79.2% of all 4,915 cells right). Source:
`spikes/ledger-rescue/scores.json` (`models.gemma`), README section 4.

What we did about it:
1. **Zoomed tiles** removed it on the ledgers (0 of 3,976 accepted cells wrong; spike, 40 sheets). Tiling is a mitigation, not a proof.
2. **Row-label check** on the tally sheet: the model must report the printed label beside every value, and the
   gate rejects a row whose label fits a neighbouring row better than its own. A shifted or doubled row cannot pass.
3. That check has a cost: in the newer re-reads, some forms were routed for row labels although every value was
   right (listed on the app's results page). A false alarm costs a person one look; a false accept would cost a
   wrong number.

## Safeguard and human review

- **Accept only on proof.** A form is accepted only when every identity printed into it holds. Everything else
  goes to the review desk.
- **The failing field is named.** The desk shows the field, the model's digits and words, and the crop. A person
  types one value; the identities re-check at once. A form is resolved only when its own arithmetic holds. If the
  paper itself is inconsistent, the person escalates it with a note. Nothing is corrected silently.
- **Fail closed.** Page not located, call failed, reply not parseable, reply cut off: routed to a person, never
  accepted.
- **Privacy first.** The names-and-signatures column is masked before the image is stored or sent to any model.
  A page that cannot be located is neither stored nor sent.
- **Pre-registration.** The 300-form protocol and Amendment 1 were committed before any model read, Amendment 2
  before any second-reader read or adjudication, and the results ship whatever they show.

## Appendix: endpoint outages and re-reads

- During the pre-registered run, 51 of the 300 forms had a first call fail during endpoint outages (HTTP 503) and
  were re-read later with the same frozen prompt; the last read of each form counts (355 rows in
  `results/calls_gemma.jsonl`).
- Re-reads of 5 masked pilot forms with the frozen prompt (`results/verify_spike_*.jsonl`), one of them made during
  an outage that returned no usable read, are on the app's Results page, appendix. They are not part of any
  headline.
