# lablab.ai submission text

Paste each block into the matching field. Every number here is the one in `app/data/headline.json`; `make eval`
recomputes them.

## Title (42 characters)

Two Hands: receipts for every keyed number

## Short description (253 characters)

Gemma on AMD read 1,270 real handwritten tally sheets (289 of a random 300 and Colima's 982, one sheet in both): 49 capture errors confirmed by the certified count, each with its photo. The paper's own arithmetic decides what is accepted with no person.

## Long description

Every number typed from a paper form, checked against the photo of that paper, with the photo as proof. Others
check the model against the source. Two Hands checks the record against the paper. A vision model on AMD reads the form;
the form's own arithmetic decides what to trust; every dispute arrives with its crop.

**Where it works.** The check is the form's own arithmetic, so it isn't tied to elections. Proven on two form types: Mexico's tally sheets and UK rainfall ledgers (1850-1960), no retraining. Next: tally sheets in at least 7 more countries that publish their images, and the monthly health-facility reports behind DHIS2, used in 70+ countries.

**Proof in three lines.** 1,270 real tally sheets read on AMD; 49 capture errors confirmed by the certified count. Against the incumbent: 91.6% field match on Baja California Sur's local actas vs 62.84% for the Google Document AI reading the state bought (same metric). Recall 27 of 28 on certified-detectable errors (pre-registered); a person's blind re-read of the AI-judged disputes: 0 read differently.

Verifiable quality control for handwritten numbers: the model reads, the form's own arithmetic decides what passes, people review the rest, every accepted value gets a receipt.

**Scope.** Clerical capture quality only: whether a typed number matches its paper. No results, no
parties (vote rows are Option 01 to Option 15), no totals, no claim about any outcome; I did not assess vote impact.
The certified count is the official result. An independent demonstration, not an official INE product.

Measured on a pre-registered random sample of 300 handwritten tally sheets from Mexico's 2024 count, graded against
the official double-keyed capture: the model found 52 fields where the capture does not match the paper, 22 of them
confirmed by the certified count and 30 judged from the photo by the AI adjudicator (the builder's model, which could
see both values; checked by a person: 30 of 30, 27 agree, 3 unreadable to the person). Errors I did not plant, in a record I did not write, in a sample drawn before any model read.
Public ground truth is also why every number here can be re-derived by anyone: the images, the keyed values and the certified count are INE's, the scripts are mine (make eval).

Mexico's rule already asks for this job. In INE's PREP process every tally sheet gets a second capture by a
person, and the system compares it with the first; a mismatch goes to a third capture, then a verification centre,
and published data are later checked against the sheet in the cotejo (Proceso Técnico Operativo 2023-2024,
numerals 30 to 35; the same phases bind all 32 state PREPs through Anexo 13 of INE's Reglamento de Elecciones).
Two Hands is an automated capture with a referee. In the preliminary capture (PREP, before the cómputos and before
any later cotejo correction), at least 0.8% of fields in my random sample do not match the paper (52 of 6,358); 1 in 5
of the fields my check disputes is a capture error, against at least 1 in 122 at random.

**Business at a glance.**

| | |
|---|---|
| Buyer | Mexico's preliminary counts (PREP): INE and the 32 state institutes, each with an outside auditor (all 26 named in 2024 were universities). At least 13 of the 17 outsourced state PREPs of 2024 went to three firms. |
| Why now | 6 June 2027: the federal midterm and 32 concurrent local elections. Each state picks its PREP operator by about 6 December 2026. INE budgeted MXN 9.5M for automated capture in 2024 and bought none (no bidder met its 80% bar); its advisers asked for a pilot. |
| Product | An independent field-by-field check of a finished capture against the photo; no rule change needed. Also an API, CLI and MCP server, for software vendors that already key these forms. |
| Price | $1 per sheet audited (proposed); first step: a paid shadow-mode pilot on one state's 2027 count. AMD compute: $0.00014 per sheet. |
| Reviewer work | About one photo crop per sheet to look at (0.92 measured: fields where the read and the capture disagree), instead of re-keying about 22 fields. |
| Capacity | One shared AMD key audits Colima's 982 sheets in about 3.4 hours and Morelos's 7,802 in about a day. A check of a finished capture, not election-night capture. |
| Example | Morelos paid MXN 26.6M to run its 2024 PREP (7,802 sheets), including an MXN 1.5M audit of the software, not of the keyed values. My check of every sheet: about MXN 143k ($7,800), 0.5% of that. |
| Competition | Second keying by a person (the rule today): at least 0.8% of fields in my random sample still do not match the paper. On Baja California Sur's 2024 local actas, Gemma on AMD matched the published PREP values on 91.58% of fields (n = 3,622 fields on a pre-registered random sample of 300 of the 2,020 actas; Wilson 95% 90.63-92.44%), on the per-field exact-match metric where the state's purchased Google Document AI reading scored 62.84% (14,501 of 23,077 fields on all 2,020 actas, against the manual capture rather than the published values). Two Hands accepts only what the paper's arithmetic proves and routes the rest with the photo. |
| Next | A paid shadow-mode pilot with one state for 2027. The check is the form's own arithmetic, so it isn't tied to elections. Proven on two form types: Mexico's tally sheets and UK rainfall ledgers (1850-1960), no retraining. Next: tally sheets in [at least 7 more countries](docs/BUSINESS.md#sources-for-the-business-at-a-glance-table) that publish their images, and the monthly health-facility reports behind DHIS2, used in [70+ countries](docs/BUSINESS.md#sources-for-the-business-at-a-glance-table). |
| Next: elections | The same public data exists in at least 7 more countries, e.g. Indonesia (823,236 polling stations), Colombia (125,259 tables), Peru (92,766 actas); Guatemala, Kenya and Argentina also vote in 2027. |
| Next: health | Monthly health-facility reports: DHIS2 runs national health reporting in 70+ countries; Ethiopia alone reports monthly from 30,000+ facilities, many on paper first. Funders already pay for manual re-checks (a malaria data audit in Zambia: about US$205 per facility). |

Each strong finding opens a case in Evolus: the agent Intake clerk, on Gemma-4-31B-IT, drafts it in the workflow Audit finding; a script, not the model, scores the evidence. 150 of 150 runs on real routed fields completed (workspace py_tr, `results/evolus/executions.jsonl`).

Whole state: Gemma on AMD read all 982 located presidential sheets of Colima for $0.14; 27 fields where the capture does not match the paper, each confirmed by the certified count, with a field-level report.

<!-- why-gemma:start -->
Same 300 forms, same gate, on AMD: Gemma accepts 1.8x the forms Qwen3.8-27B does at the same error rate, 4.6x cheaper and 2.8x faster, with no truncated answers. Every zero-error two-reader pair includes Gemma; the only pair without it made errors (2 of 814).

| Reader | Forms accepted | Wrong of accepted fields | $ per 1,000 forms | Mean time per read |
|---|---|---|---|---|
| **Gemma-4-31B-IT** | **55 of 300 (18%)** | 2 of 1,210 | $0.14 | 87 s |
| Qwen3.8-27B | 31 of 300 (10%) | 1 of 682 (+2 undecided) | $0.64 | 241 s |
| Qwen3.8-Flash-Next | 17 of 128 (13%) | 0 of 374 (+1 undecided) | $2.11 | 120 s |
| Gemma-4-31B-IT + Qwen3.8-27B | 89 of 300 (30%) | **0 of 1,958** | $0.78 | – |
| Gemma-4-31B-IT + Qwen3.8-Flash-Next | 42 of 128 (33%) | **0 of 924** | $2.25 | – |
| Qwen3.8-27B + Qwen3.8-Flash-Next | 37 of 128 (29%) | 2 of 814 (+1 undecided) | $2.75 | – |

*Pairs: all 23 digits agree, lighter gate (secondary). Qwen3.8-Flash-Next: first 128 forms (budget rule). Source: app/data/bakeoff_300.json.*
<!-- why-gemma:end -->

One reader: 18% of forms with no person, 2 wrong fields in 1,210. Two readers that must agree, with the paper's sums as referee: 30%, 0 wrong in 1,958 (secondary, lighter gate; both readers on the full gate, 7% of these 300, 0 wrong in 484). The one-reader figure is the pre-registered primary. That 0 of 484 is two readers on the random 300. The deck's 0 of 484 is a separate result with the same count: one reader, gate v2, fixed before 100 fresh forms were drawn (Amendment 3), accepted 22 of them, 0 of their 484 fields wrong (Wilson 95% upper bound 0.79%).

Alone, one model mis-keys 1 field in 37. Two models that agree, refereed by the paper, mis-keyed 0 of 1,958 accepted fields against the official capture. That is the secondary two-reader tier, on the lighter gate.

What runs on AMD: every measured read of the 300 is Gemma-4-31B-IT on AMD GPUs through AMD Token Factory, one
request per form. Server time per form: 83 s mean, 71 s median (HTTP round trip, shared endpoint, 289 reads of Gemma-4-31B-IT, 2,609 tokens in, 804 out). Measured capacity (shared endpoint, 2026-10-17 00:48-01:03 UTC, queueing included, not GPU time): 4 in flight, 4.8 forms/minute, 32 s median, $0.000146/form; one shared key reads a state the size of Colima (982 sheets) in about 3.4 hours; national figures in results/throughput_sweep.json. Latency per read (shared AMD endpoint, queue included): 32 s p50, 67 s p95 at 4 in flight (12 of the sweep's 44 requests); 71 s median over the 289 requests of the 300 run; 9.6 output tokens/s per request (804 out, 83 s mean round trip). Fine for an audit after the count, where nobody waits on one sheet: a state the size of Colima (982 sheets) in about 3.4 hours. About $24 of AMD compute to read all 169,005 national presidential tally sheets with Gemma-4-31B-IT ($0.000144 per form, the mean billed cost of 289 reads). The 300 run's 87 s per form was wall clock under my own pacing (2 in flight), not GPU time; 83 s of it was the endpoint's round trip, queue included. Gemma was briefly unavailable on the shared endpoint (2026-10-15
15:41 to 2026-10-16 02:06 UTC); every stored number is Gemma on AMD (log: `results/endpoint_health.jsonl`). Page
locating, the privacy mask and the gate run on CPU.

Limits: most forms are routed to a person (see the table). "Wrong" is judged against the official capture: every disagreement was checked on the photo, the
agreeing fields were not (a seeded random 200 of them is queued for a blind person check). Recall: 27 of 28 certified-detectable errors, one state; not total recall. The
pre-registered second-reader pass on the 100-form confirmation was not run (a protocol deviation). 11 of the 300 pages could
not be located and went to a person before any model call.

## Links

<!-- links:start -->
Live demo: add at submission · Video: add at submission · Repository: add at submission · Audit report sample: add at submission · Slides (PDF): add at submission · How to reproduce: `make eval` in the repo
<!-- links:end -->

(Filled from `submission/links.json` by `python scripts/fill_links.py`.)

## Technology tags

AMD Token Factory, AMD GPUs, Gemma, Gemma-4-31B-IT, Evolus, Python, FastAPI, OpenCV,
vision language model, document verification, data quality, audit

## Tracks

- AMD (main track)
- Google DeepMind Gemma (best use of Gemma models on AMD GPUs)
- Evolus (Business Agents)
