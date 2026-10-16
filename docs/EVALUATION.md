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
| Settled on the photo | capture does not match the paper 52 · model misread 156 · both off 17 · paper ambiguous 34 · unreadable 8 |
| **Fields where the official capture does not match the paper** | **52**: 17 wrong numbers typed; 27 readable fields recorded as illegible, 23 of them on two faint pencil forms; 6 numbers typed where the paper is blank; 2 other. Each with its photo. The certified count covers 31 and confirms the paper on 22; all 9 differences were recounts |
| The model alone | wrong on 173 of 6,358 fields (156 + 17): about 1 in 37 |
| Accepted with no person (frozen gate, primary) | 55 of 300 (18%): 27 phone photos, 28 scans |
| Accepted fields wrong after adjudication | **2 of 1,210** (about 1 in 605; Wilson 95% 0.04% to 0.60%), so the headline rule (error rate <= 0.5%) keeps the single-reader tier |
| Yield of a disputed field | 1 in 5 disputed fields is a confirmed capture error (52 of 267). The capture's overall error rate is at least 1 in 122 (52 of 6,358 found so far). More than ten times the yield of a random check. |
| Recall | On the forms the certified count settled by comparison, it differs from the first capture on 23 fields; judged on the paper, 16 of them are council corrections or blank rows (the paper shows the capture's value), and the model disputed 7 of the other 7 (measured recall 100%, Wilson 95% 65% to 100%; small n). (`results/adjudication/RECALL.md`) |

**Alone, one model mis-keys 1 field in 37. Two models that agree, refereed by the paper, mis-keyed 0 of 1,958.** On accepted fields the
pair made 1 error and the model 2; we never claim the model beats the pair. The first capture is preliminary by
design; the certified count is the official result.

### Two readers: the stricter mode (Amendment 2, secondary)

Qwen3.8-27B read the same 289 located pages with the same frozen prompt and gate (239 usable reads; 50 replies were cut
at `max_tokens` and are never accepted). Amendment 2 was committed before any Qwen read of the 300 and before any
adjudication; these tiers are secondary and the headline rule is unchanged (Gemma alone, 2 of 1,210 wrong, is under
0.5%). **Strict mode** (Amendment 2 d) accepts a form when Gemma and Qwen read the same digits on all 23 fields, every
digit field is read, the words either reader wrote down agree with those digits, and the vote rows sum to the total.
It drops the row-label check and the section identities and relies on the two readers' agreement instead, which is
why it accepts more forms than either reader alone.

| Mode (accepted / 300) | Accepted | Accepted fields | Differ from the capture (capture errors) | Wrong on the paper (Wilson 95%) |
|---|---|---|---|---|
| Gemma alone, frozen gate (primary) | 55 | 1,210 | 3 (1) | 2 (0.04% to 0.60%) |
| Qwen alone, frozen gate | 31 | 682 | 2 (1) | 1 (0.03% to 0.83%); 2 undecided on the paper |
| **Two readers, strict mode (Amendment 2 d)** | **89** | **1,958** | **3 (3)** | **0 (0.00% to 0.20%)** |
| Two readers, both frozen gates (section 7) | 22 | 484 | 1 (1) | 0 (0.00% to 0.79%) |
| POST-HOC v2-2R (Amendment 3) | 54 | 1,188 | 2 (1) | 1 (0.01% to 0.47%) |
| POST-HOC v2-2R strict (in no amendment) | 45 | 990 | 1 (1) | 0 (0.00% to 0.39%) |

**With two readers (strict mode): 89 forms, 0 wrong fields in 1,958.** The 3 accepted fields where the agreed read
differs from the official capture (080310B0100 unused ballots, 202005C0200 Option 07, 220313C0300 ballots taken from
the boxes) are all capture errors on the photo. Qwen alone's one wrong field is unused ballots on 090955C0200 (read 200,
paper 206); its 2 undecided fields are ones where it equals the capture and the paper was judged ambiguous. Every
accepted field in every tier that differs from the capture already had a verdict on the photo, so no new adjudication
was needed. The bias note of the protocol applies: an error both readers share with the capture is not counted.

The two v2-2R rows are **post-hoc** (gate v2 was designed after seeing these reads, Amendment 3) and test nothing; the
pre-registered test of v2 is the fresh 100-form draw. v2-2R accepts unused ballots, the one field in no identity, when
Gemma's words equal its digits or Qwen's digits agree; its one error is 010469C0400, where one Gemma call read 239 in
both digits and words (paper 234) and Qwen read 234. The strict variant, which needs Qwen's agreement whatever the
words say, removes it. Sources: `results/two_reader_300.md`, `app/data/two_reader_300.json`
(`scripts/two_reader_300.py`), `results/posthoc_v2_300.md`; `make eval` recomputes every number independently.

**The pre-registered confirmation on 100 fresh forms: gate v2 accepted 22 forms, 0 of 484 accepted fields wrong;
criterion met** (Amendment 3: accepted-field error <= 0.5% after adjudication; Wilson 95% 0.00% to 0.79%, so the interval
still reaches above 0.5%, as the amendment said it would at this size). Gemma read all 100 (97 located; the 3 unlocated
pages stay in the denominator); 14 phone photos and 8 scans accepted. The frozen gate (v1) accepted 23 with 1 wrong
field in 506 (070212B0100 unused ballots, read 3114, paper 314: the field in no identity, with no words written), which
is exactly the error v2 exists to stop; v2b (secondary) accepted 29 with 0 wrong in 638. Gate v3 (Amendment 7, committed
before these reads) accepted the other 22 fields on 24 forms, 0 of 504 wrong, but no Qwen pass was run on the 100, so its
two-read rule sends every unused-ballots field to a person (0 touchless); with words + ballot stock alone, 21 of the 24
would be touchless and both wrong unused-ballot reads (3114 vs 314, 207 vs 217) are caught. Every accepted-field
disagreement with PREP (3 fields) was adjudicated on its crop by an AI adjudicator (an AI model), labelled as such:
`results/confirm100.md`, `results/adjudication_confirm100/`.

### Behind "more than ten times the yield of a random check"

On the forms settled by comparison, 23 fields differ between the certified count and the first capture. 16 are council corrections or blank rows, where the paper shows the capture's value, so a faithful read cannot dispute them. The model disputed all 7 of the rest (1 confirmed capture error, 6 where the paper is ambiguous). That is a small subset; Wilson 65-100%.

The multiple: a random check finds a capture error in at least 1 field in 122 (52 of 6,358 found so far; a lower bound on the capture's error rate); in a disputed field, 1 in 5 (52 of 267). The multiple is about 12 to 24 times the yield per field checked: 24 if the model finds nearly every error, 12 if it finds half; "more than ten times" is the conservative end. Counting the 16 corrections in the denominator gives the loose bound, 7 of 23 disputed (Wilson 16-51%). (`results/adjudication/RECALL.md`)

### The 52 capture errors by type

| Type | Fields |
|---|---|
| Wrong numbers typed | 17 |
| Readable fields recorded as illegible (23 of them on two faint pencil forms) | 27 |
| Numbers typed where the paper is blank | 6 |
| Other (readable field captured as "no data") | 2 |

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
`data/pilot/tally-witness/adjudicate.json`; the two-reader row from `spikes/tally-witness/README.md` section 3.

"Routed but read perfectly" means every field was right but the paper itself is inconsistent (rows that do not
add up, words that disagree with digits). Those are correct routings, not reader errors.

Base rate for context: in the official national capture, 19.2% of fully captured forms (26,336 of 137,196) fail
their own row sum (PREP 2024 CSV, `spikes/tally-witness/README.md` section 1).

### Capture errors found in the pilot

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

**Not a capture error, shown apart:** on 211294C0100 the TOTAL digits say 262 and the words say 162. The capture
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

Source: `ledger/ledger.json` (built from the pilot copies in `data/pilot/ledger-rescue`, `results/pilot/ledger-rescue` with the spike's own scorer).

## Business result

On 289 random forms already keyed twice, the model sent **267 of 6,358 fields (4.2%)** to a person, and **52** of
those were fields where the official capture does not match the paper, each with its photo. The AMD compute cost was
**$0.000144 per form** (mean over the 289 reads), about $0.14 per 1,000 forms: $20 to $86 compute cost to audit all 169,005
forms (Gemma, Qwen). The buyer is the auditor: Mexico requires an outside audit of every PREP (Reglamento de
Elecciones art. 347), and in 2024 UNAM centres audited several state PREPs (sources in the README).

## Known limitations

- A receipt-audit run on the public CORD benchmark was pre-registered (commit 365eb56) and not run for lack of time.

- **One reader, one adjudicator.** Every disagreement was settled by one reviewer (the builder, an AI agent, not a
  native Spanish speaker) on published crops; anyone can re-check them, and the app's blind spot-check page lets a
  person do so without seeing any AI or capture value.
- **Recall rests on few fields.** We checked only where the model disagreed with the capture, so errors both made
  are not counted directly. On the forms the certified count settled by comparison, it differs from the first capture on 23 fields; judged on the paper, 16 of them are council corrections or blank rows (the paper shows the capture's value), and the model disputed 7 of the other 7 (measured recall 100%, Wilson 95% 65% to 100%; small n).
- **The label gate's cost.** The row-label check routed 86 forms; on 68 of them the read matched the paper on every
  graded field, including all 15 forms routed for a label alone. Each false alarm costs a person one look.
- **One read is not two independent reads.** In one call the model can harmonise words and digits: on 010469C0400
  it read unused ballots as 239 in digits and 239 in words, while the paper says 234 in both. That field sits in no
  identity, so the gate accepted the form; it is one of the 2 wrong fields on accepted forms. The fix is separate
  reads or a second reader.
- **Throughput on a shared key.** About 2 forms a minute under our pacing; mean latency 87 s per form on the 300
  (wall clock, including queueing). A real deployment needs a dedicated AMD endpoint, which we have not measured.
- **Page locator.** 11 of 300 phone photos could not be located and go to a person before any model call.
- **The gate cannot see an error that keeps the arithmetic true.** See the next section and the failure case.

## What the paper's arithmetic can and cannot catch

**The guarantee.** The tally sheet is redundant twice over: each value is written in digits and in words, and the
values are tied by the schema's 4 identities (the 17 vote rows sum to TOTAL; voters + representatives = section 5 =
section 7 = TOTAL). On a paper whose own arithmetic holds, **any single misread is caught**: a value misread in its
digits fails words = digits when both are written, and a misread value inside an identity breaks that sum. The form
then routes to a person.

**Only an error that preserves every identity passes.** Three ways:

1. **Compensating errors:** +k and -k on two terms of one sum (two vote rows, or voters and representatives), or one
   misread carried through every side of a chain of identities. A shifted row is a case of this.
2. **A field outside every identity.** Computed from the schema (`twohands.gate_v2.unchecked_fields` over
   `schemas/mx_presidencia_2024.yaml`; the Senate schema gives the same): **SOBRANTES (unused ballots)**, and no other
   field. Its only check is words = digits, and there is none when the words are not read.
3. **A harmonised read:** words and digits come from one model call, so a call that misreads the digits can write
   words that match. One call is one read, not two.

(The guarantee assumes the paper's own sums hold; on a sheet whose arithmetic is off, a misread that repairs it passes.)

**Measured blind spots.** Every wrong field on a form the frozen gate accepted, both readers (Gemma 2 of 1,210
accepted fields, Qwen 1 of 682), is SOBRANTES:

| Reader | Form | Digits | Words | Paper | Way through |
|---|---|---|---|---|---|
| Gemma | 010469C0400 | 239 | 239 | 234 | harmonised in one call (the 239/239 case) |
| Gemma | 212668C0300 | 300 | not read | 379 | no words: no check at all |
| Qwen | 090955C0200 | 200 | not read | 206 | no words: no check at all |

No compensating error was found among the accepted forms; that describes this sample, not a bound.

**What closes each one** (post-hoc on the 300, Amendment 3; the fresh 100-form draw is the test):

- **The v2 rule** (a field outside every identity needs digits and words both read and equal) removes the no-words
  cases: 1 wrong of 1,034 accepted fields. It cannot remove a harmonised read.
- **A second reader:** v2-2R strict accepts SOBRANTES only when Qwen's digits agree: 0 wrong of 990. v2-2R, which
  also accepts Gemma's own words, keeps 010469C0400: 1 wrong.
- **Separate reads** of digits and words would make words = digits two reads; not built, not measured.
- **Compensating errors:** the row-label check and the tiles make a shift visible; only a second reader that does not
  make the same pair catches a compensating pair. Two readers sharing one misread remain possible and are not counted.

So: a single misread cannot pass the gate; an error passes only through the three named ways, and on this sample every
one that did went through the one field outside every identity. The report (`docs/REPORT.md`, section 5) computes
these numbers from the committed results.

## Failure case: a silent row shift

On the rainfall ledgers, read as **one image**, Gemma put Balcombe Gables' 1887 values under 1886, and so on
along the row. Every shifted column still summed to its total, so the checksum accepted wrong cells: **26 of
870 accepted cells were wrong** on that reader (79.2% of all 4,915 cells right). Source:
`data/pilot/ledger-rescue/scores.json` (`models.gemma`), README section 4.

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
