# Evaluation

What we measured, how, and where it breaks. Every number has a source file; the full list is in
[`NUMBERS.md`](NUMBERS.md). Wilson 95% intervals are our own computation from the counts shown.

## Organiser checklist

| Item | Where |
|---|---|
| One business result | [Business result](#business-result) |
| One known limitation | [Known limitations](#known-limitations) |
| One failure case | [Failure case](#failure-case-a-silent-row-shift) |
| The safeguard or human review process | [Safeguard](#safeguard-and-human-review) |

## Ground truth

- **Tally sheets.** Mexico's 2024 presidential polling-station tally sheets (INE, type 2). Each image has an
  official double-keyed capture (PREP: two people key every form, a third reviews mismatches) and, for most vote
  rows, a later certified count (Cómputos). We grade the model's digits against the official capture on the 22
  fields that have one. Every disagreement on an accepted form is then checked by eye on the masked image.
  Truth = the official capture unless the image says otherwise.
- **Rainfall ledgers.** Rainfall Rescue sheets (UK, 1850-1960), graded against the volunteers' transcription
  (~16,000 volunteers, 4 transcriptions per value; Hawkins et al. 2022). Match = within 0.005 in.

## Pre-registered random run: 300 forms

**Status: in progress.** The protocol (`PROTOCOL.md`) was committed in `a93294c` before any of the 300 was sent
to a model. It fixes the sample (stratified by state x capture type, seed 20261015, manifest sha256
`605af977...e081`), the prompt (sha256 `3664253035b9...`), the gate, the metrics and the headline rule.
**Amendment 1** (commit `b0e443c`) replaced only the page locator, and was also committed before any model read
of the 300: the original locator left 52 of 300 pages unlocated (50 of them phone photos). The new locator was
tuned on the 43 pilot forms and a **fresh calibration set of 150** (seed 20261016, disjoint from the 300):
144 of 150 located, **143 of 150 located and correctly aligned** by an eye audit of every page (Wilson 95%:
90.7% to 97.7%); the original locator managed 128 of 150. None of the 52 failures was opened or used.

On the 300: **289 located, 11 not located** (all phone photos). The 11 are routed to a person before any model
call and count as not accepted (`results/prepare.jsonl`).

**Headline rule (pre-registered):** single-reader Gemma, unless its accepted-field error rate after
adjudication exceeds 0.5%; then the two-reader tier. Both are published either way.

| Metric (denominator = all 300) | Gemma-4-31B-IT | Qwen3.8-27B | Two readers agree + gate |
|---|---|---|---|
| Accepted with no human touch | {{RUN300_ACCEPT_RATE}} ({{RUN300_ACCEPTED}}) | {{RUN300_QWEN_ACCEPT_RATE}} | {{RUN300_BOTH_ACCEPT_RATE}} |
| Accepted, phone photo / scanner | {{RUN300_ACCEPT_MOVIL}} / {{RUN300_ACCEPT_ESCANER}} | | |
| Accepted fields wrong vs official capture (raw) | {{RUN300_ACC_WRONG_RAW}} of {{RUN300_ACC_FIELDS}} | {{RUN300_QWEN_ACC_WRONG_RAW}} | {{RUN300_BOTH_ACC_WRONG_RAW}} |
| Accepted fields wrong after eye check | {{RUN300_ACC_WRONG}} of {{RUN300_ACC_FIELDS}} (Wilson 95% upper {{RUN300_ACC_WRONG_CI}}) | {{RUN300_QWEN_ACC_WRONG}} | {{RUN300_BOTH_ACC_WRONG}} |
| Keying errors in the official capture (eye-checked) | {{RUN300_KEYING_ERRORS}} | | |
| Route reasons (label / empty / words / identity / no read) | {{RUN300_ROUTE_REASONS}} | | |
| Accept rate with the original locator (52 routed) | {{RUN300_ACCEPT_ORIG_LOCATOR}} | | |
| Headline tier under the rule | {{RUN300_HEADLINE_TIER}} | | |

Source when filled: `results/calls_gemma.jsonl`, `results/calls_qwen.jsonl`, adjudications in
`results/adjudication/`. The web app switches its headline to this run automatically once it has 100 or more
graded forms.

## Pilot: 43 tally forms (measured)

**Sample.** 43 forms from 10 districts in 10 states, 23 phone photos and 20 scans. **Deliberately enriched with
trouble**: 16 clean, 5 with a paper row-sum mismatch, 12 where the official capture differs from the certified
count, 10 recounted. Not random, so accept rates are a lower bound for an ordinary day
(`spikes/tally-witness/README.md` section 2).

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

### Keying errors found in the official capture

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

## Second form type: 40 rainfall ledger sheets (measured)

| | |
|---|---|
| Sheets / cells | 40 sheets from 5 stations, 4,915 cells |
| Identity | 12 monthly values = the clerk's handwritten annual total (within 0.01 in) |
| Reader | Gemma-4-31B-IT, whole sheet + 3 zoomed strips, no re-reads |
| Year-columns accepted | 306 of 380 (80.5%) |
| Accepted cells right | **3,976 of 3,976** (Wilson 95% upper 0.10% error) |
| Cost | $0.00011 per sheet |

Source: `ledger/ledger.json` (built from `spikes/ledger-rescue` with the spike's own scorer).

## Business result

On the 43-form pilot, **21 forms (49%) needed no keying at all and 0 of their 462 fields were wrong**, while the
official double-keyed capture had **6 keying errors** on those same forms. The AMD compute cost was **$0.000118
per form**, about $0.12 per 1,000 forms, or about $20 to audit all 169,005 national tally forms.

## Known limitations

- **Small, difficult pilot.** 43 forms, chosen to be hard, one run, crop positions tuned by hand. The 300-form
  random run exists to fix this.
- **Adjudication bias.** We eye-checked only where a reader disagreed with the official capture on an accepted
  form. Capture errors elsewhere are not counted. The adjudicator is the builder (an AI agent, not a native
  Spanish speaker).
- **Throughput on a shared key.** About 2 forms a minute under our pacing; the national set would take about
  59 days. A real deployment needs a dedicated AMD endpoint, which we have not measured.
- **Page locator.** 11 of 300 phone photos could not be located and go to a person before any model call.
- **The gate cannot see an error that keeps the arithmetic true.** See the failure case.

## Failure case: a silent row shift

On the rainfall ledgers, read as **one image**, Gemma put Balcombe Gables' 1887 values under 1886, and so on
along the row. Every shifted column still summed to its total, so the checksum accepted wrong cells: **26 of
870 accepted cells were wrong** on that reader (79.2% of all 4,915 cells right). Source:
`spikes/ledger-rescue/scores.json` (`models.gemma`), README section 4.

What we did about it:
1. **Zoomed tiles** removed it on the ledgers (0 of 3,976 accepted cells wrong). Tiling is a mitigation, not a proof.
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
- **Pre-registration.** The 300-form protocol and its one amendment were committed before any model read, and
  the results ship whatever they show.
