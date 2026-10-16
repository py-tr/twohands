# lablab.ai submission text

Paste each block into the matching field. Every number here is the one in `app/data/headline.json`; `make eval`
recomputes them.

## Title (42 characters)

Two Hands: receipts for every keyed number

## Short description (253 characters)

Gemma on AMD read 300 random handwritten tally sheets: 52 fields where the official capture differs from the paper, each with its photo. With the paper's own arithmetic as referee, one reader accepts 18% of forms with no person, 2 wrong fields in 1,210.

## Long description

Every number typed from a paper form, checked against the photo of that paper, with the photo as proof. Others
check the model against the source. We check the record against the paper. A vision model on AMD reads the form;
the form's own arithmetic decides what to trust; every dispute arrives with its crop.

Two hands: two independent readers, and the paper's own arithmetic as the referee.

**Sponsor-safe framing.** Clerical capture quality only: whether a typed number matches its paper. No results, no
parties (vote rows are Option 01 to Option 15), no totals, no claim about any outcome; we did not assess vote impact.
The certified count is the official result. An independent demonstration, not an official INE product.

Measured on a pre-registered random sample of 300 handwritten tally sheets from Mexico's 2024 count, graded against
the official double-keyed capture: the model found 52 fields where the capture does not match the paper, 22 of them
confirmed by the certified count and 30 judged from the photo by the AI adjudicator (the builder's model, which could
see both values). Errors we did not plant, in a record we did not write, in a sample drawn before any model read.
Public ground truth is also why every number here can be re-derived by anyone: the images, the keyed values and the certified count are INE's, the scripts are ours (make eval).

Mexico's rule already asks for this job. In INE's PREP process every tally sheet gets a second capture by a
person, and the system compares it with the first; a mismatch goes to a third capture, then a verification centre,
and published data are later checked against the sheet in the cotejo (Proceso Técnico Operativo 2023-2024,
numerals 30 to 35; the same phases bind all 32 state PREPs through Anexo 13 of INE's Reglamento de Elecciones).
Our engine is an automated capture with a referee. In the preliminary capture (PREP, before the cómputos and before
any later cotejo correction), at least 0.8% of fields in our random sample do not match the paper (52 of 6,358); 1 in 5
of the fields our check disputes is a capture error, against at least 1 in 122 at random. Recall is unmeasured.

Who pays in 2027: the PREP's outside auditor or its contracted operator, for an independent check of a finished capture, field by field against the photo. It needs no rule change: it is an outside check, which is what we measured. A model as the regulated second capture (PTO numeral 33) needs the institute's governing body to approve it after INE's opinion (RE art. 339); that is the longer-term path, not the 2027 product. INE put MXN 9.5M in its 2024 draft budget for an automated first capture service, a different step
from our check, and bought none: no entrant met its 80% bar on words and digits, and its advisers asked for a pilot
(INE CCOE report, 26-08-2024, pp. 4, 5, 10). Which form: state institutes (OPLEs) process local actas (governor, local deputies, municipalities). The presidential forms we measured (and the Senate forms we read) are federal, processed by INE. Our local evidence is the Baja California Sur head-to-head on local actas (PROTOCOL_IEEBCS.md): read on AMD, not yet scored: no result is shown until it is. Status: no buyer contacted yet.
Price (proposal): $1 per form audited (second capture + cotejo + receipts), or $5 per confirmed capture error, $0 if none is found. INE's own line was MXN 9.5M for ~170,000 actas, about MXN 56 (~$3) per acta for a first capture alone. Costs: AMD compute $0.00014 per form (measured); review labour for routed fields about $0.09 to $0.13 per form (GUESS: 20 s per disputed crop, 0.92 crops per form measured, $18 to $25 an hour); hosting and sales. Example:
Morelos, 7,802 forms: about $7,800 (MXN 143k), under the lowest federal direct-award ceiling. Health facility reports (DHIS2), mortgage post-closing QC and clinical-trial source data
verification are the next markets, not measured.

When an agent keys a form, the paper still has to agree. Receipts work the same for a model as for a person.

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

One reader: 18% of forms with no person, 2 wrong fields in 1,210. Two readers that must agree, with the paper's sums as referee: 30%, 0 wrong in 1,958 (secondary, lighter gate; with the full gate, 7%, 0 wrong in 484). The one-reader figure is the pre-registered primary.

Alone, one model mis-keys 1 field in 37. Two models that agree, refereed by the paper, mis-keyed 0 of 1,958 accepted fields against the official capture.

What runs on AMD: every measured read of the 300 is Gemma-4-31B-IT on AMD GPUs through AMD Token Factory, one
request per form. Server time per form: 83 s mean, 71 s median: the HTTP round trip of the answered request on the shared endpoint, 289 answered reads of Gemma-4-31B-IT, 2,609 tokens in and 804 out per form (about 10 output tokens a second per request). About $24 of AMD compute to read all 169,005 national presidential tally sheets with Gemma-4-31B-IT ($0.000144 per form, the mean billed cost of 289 reads). The 87 s per form reported for the 300 run is wall clock on a shared key under our own pacing (2 requests in flight), not GPU time; the endpoint's own round trip, which includes its queue, was 83 s of it. Gemma was briefly unavailable on the shared endpoint (2026-10-15
15:41 to 2026-10-16 02:06 UTC); every stored number is Gemma on AMD (log: `results/endpoint_health.jsonl`). Page
locating, the privacy mask and the gate run on CPU.

Limits: most forms are routed to a person (see the table). "Wrong" is judged against the official capture: every disagreement was checked on the photo, the
agreeing fields were not (a seeded random 200 of them is queued for a blind person check). The adjudicator is the AI
adjudicator, not a person. Recall is unmeasured: of the 7 recall fields, 1 is a confirmed capture error. The
pre-registered second-reader pass on the 100-form confirmation was not run (a protocol deviation). The row-label check
is costly: it routed 86 forms, and on 68 of them the read matched the paper on every field. 11 of the 300 pages could
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
