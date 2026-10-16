# Two Hands: receipts for every number keyed from paper

Every number typed from a paper form, checked against the photo of that paper, with the photo as proof. Others
check the model against the source. We check the record against the paper. A vision model on AMD reads the form;
the form's own arithmetic decides what to trust; every dispute arrives with its crop.

Two hands: two independent readers, and the paper's own arithmetic as the referee.

The PREP rules require a second capture and a comparison for every acta (numeral 33) and a cotejo. Two Hands checks a finished capture against the photo, field by field: it accepts what the paper's arithmetic confirms and sends the rest to a person, with the photo.

Measured on a pre-registered random sample of 300 handwritten tally sheets from Mexico's 2024 count, graded against
the official double-keyed capture: the model found 52 fields where the capture does not match the paper (22
confirmed by the certified count; the other 30 judged from the photo by the AI adjudicator, the builder's model, which could see both values; a blind person check is in progress at `/check`). Errors we did not plant, in a record we did not write, in a sample drawn
before any model read. Public ground truth is also why every number here can be re-derived by anyone: the images, the keyed values and the certified count are INE's, the scripts are ours (`make eval`).

**Who pays in 2027: the PREP's outside auditor or its contracted operator, for an independent check of a finished capture, field by field against the photo. It needs no rule change: it is an outside check, which is what we measured. A model as the regulated second capture (PTO numeral 33) needs the institute's governing body to approve it after INE's opinion (RE art. 339); that is the longer-term path, not the 2027 product.**
The appetite is on record: INE put MXN 9.5M in its 2024 draft budget for an automated first capture service (PTO numeral 30), a different step from our check, and bought none: no entrant met its 80% bar on words and digits, and its advisers asked for a pilot ([INE report](https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/176400/ccoe-10se-26-08-2024-p17-1.pdf), pp. 4, 5, 10).
Which form: state institutes (OPLEs) process local actas (governor, local deputies, municipalities). The presidential forms we measured (and the Senate forms we read) are federal, processed by INE. Our local evidence is the Baja California Sur head-to-head on local actas (PROTOCOL_IEEBCS.md): read on AMD, not yet scored: no result is shown until it is. Status: no buyer contacted yet.
Price (proposal): **$1 per form audited (second capture + cotejo + receipts)**, or $5 per confirmed capture error, $0 if none is found. INE's own line was MXN 9.5M for ~170,000 actas, about MXN 56 (~$3) per acta for a first capture alone.

<!-- links:start -->
**Live demo:** add at submission · **Video:** add at submission · **Repository:** add at submission ·
**Audit report sample:** add at submission (in the repo: [the 52, each with its crop](results/adjudication/SUMMARY.md)) ·
**How to reproduce:** [`make eval`](#reproduce-every-number) ·
**Report:** [technical report (PDF)](report/two-hands-report.pdf), source [`docs/REPORT.md`](docs/REPORT.md)
(links are kept in [`submission/links.json`](submission/links.json))
<!-- links:end -->

**Scope.** Clerical capture quality only: whether a typed number matches its paper. No results, no parties (vote rows are Option 01 to Option 15), no totals, no claim about any outcome; we did not assess vote impact. The certified count is the official result; the preliminary capture is preliminary by design. An independent demonstration, not an official INE product.

| 52 | 1 in 5 |
|---|---|
| fields where the official capture does not match the paper, each with its photo: 22 confirmed by the certified count · 0 checked by a person · 30 judged from the photo by the AI adjudicator only (the builder's model, which could see both values; a blind person check is in progress at `/check`) | disputed fields is a confirmed capture error (52 of 267). The capture's overall error rate is at least 1 in 122 (52 of 6,358 found so far). |

**Alone, one model mis-keys 1 field in 37. Two models that agree, refereed by the paper, mis-keyed 0 of 1,958 accepted fields against the official capture.**

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

Measured on Gemma-4-31B-IT on the AMD Token Factory. Gemma-4-31B-IT was unavailable on the AMD Token Factory from 2026-10-15 15:41 to 2026-10-16 02:06 UTC (our probe log); since then it serves again, with intermittent provider 500s on vision requests that succeed on retry. Live reads use Gemma when it is listed, and fall back to Qwen3.8-27B otherwise; every receipt names its reader.

![Option 07 on form 050815B0100: the words say "ciento setenta y cinco", the boxes say 1 7 5](slides/receipt_050815B0100.jpg)

*Form 050815B0100, Option 07 (masked page, cropped right of the logo column). The paper says 175, the first
capture keyed 75, the certified count says 175. One of the 52.*

## Contents

1. [Who pays](#who-pays)
2. [Headline: the pre-registered 300](#headline-the-pre-registered-300)
3. [What ran on AMD](#what-ran-on-amd)
4. [Run it](#run-it) · [Reproduce every number](#reproduce-every-number)
5. [Audit your capture](#audit-your-capture) · [Verify a receipt](#verify-a-receipt) · [CLI](#cli) · [MCP](#mcp)
6. [How it works](#how-it-works)
7. [Limits and failure cases](#limits-and-failure-cases)
8. [Business detail](#business-detail)
9. [Data and privacy](#data-and-privacy) · [Data, credit and framing](#data-credit-and-framing)
10. [Evolus](#evolus) · [Docker](#run-with-docker) · [Deploy](#deploy) · [Repo map](#repo-map)

## Who pays

| | |
|---|---|
| **Buyer** | The state institutes (OPLEs) that run the regulated second capture; PREP vendors (three firms ran at least 13 of 17 outsourced 2024 state PREPs) and the outside auditors are the channel. Next markets, not measured: health facility reports (DHIS2), mortgage post-closing QC, clinical-trial source data verification |
| **Price** | Proposal: $1 per form audited (second capture + cotejo + receipts); or $5 per confirmed capture error, $0 if none is found. INE's own line was MXN 9.5M for ~170,000 actas, about MXN 56 (~$3) per acta for a first capture alone |
| **Measured cost on AMD** | $0.14 per 1,000 forms (Gemma, 289 reads); $0.65 with the second reader (Qwen, 43 pilot reads) |
| **Proof** | Pre-registered random 300; every dispute with its photo; `make eval` recomputes every number offline |

Product, in one line: give us your keyed data and the scans; you get the 4% of fields to look at, each with its
photo. Full case, with every source: [docs/BUSINESS.md](docs/BUSINESS.md).

## Headline: the pre-registered 300

Mexico's 2024 polling-station tally sheets (INE). Sample, prompt, gate and metrics were committed before any model
read (`PROTOCOL.md`, Amendments 1-3). Gemma-4-31B-IT on AMD read every page. Every field was compared with the
official two-person capture (PREP); every disagreement was settled on a crop of the masked photo.

| | Pre-registered random sample, n = 300 |
|---|---|
| Pages located and read | 289 (11 went to a person before any model call) |
| Fields compared with the official capture | 6,358; the model agrees on 95.80% and disputes **267 (4.2%)** |
| **Fields where the official capture does not match the paper** | **52**: 17 wrong numbers typed; 27 readable fields recorded as illegible, 23 of them on two faint pencil forms; 6 numbers typed where the paper is blank; 2 other. Each with its photo. The certified count covers 31 and confirms the paper on 22; all 9 differences were recounts |
| The model alone | wrong on 173 of 6,358 fields: about **1 in 37** |
| Forms the gate accepts with no person | 55 of 300 (18%): **2 of 1,210 fields wrong, about 1 in 605** (one reader, the primary) |
| Two readers that must agree, the paper's sums as referee | 89 of 300 (30%): **0 of 1,958 fields wrong**: a secondary analysis, defined (Amendment 2) after the one-reader result was seen and before the second reader ran; it uses the lighter gate (no section checks). With the full gate (section 7): 22 of 300 (7%), **0 of 484 fields wrong** |
| How "wrong" was checked | Judged against the official capture; every disagreement checked on the photo; fields where the model and the capture agree were not individually checked. |
| Pre-registered confirmation, 100 fresh forms (Amendment 3) | gate v2 accepted 22 forms: **0 of 484 fields wrong**, judged against the official capture with every disagreement checked on the photo (Wilson 95% upper 0.79%, above the 0.5% bar: the point estimate meets it, the bound does not) ([`results/confirm100.md`](results/confirm100.md)) |
| Yield of a disputed field | 1 in 5 disputed fields is a confirmed capture error (52 of 267). The capture's overall error rate is at least 1 in 122 (52 of 6,358 found so far). Of the 52: 22 confirmed by the certified count, 30 judged from the photo by the AI adjudicator (the builder's model, which could see both values). Recall is unmeasured, so the multiple between the two rates is too. |
| Recall | On the forms the certified count settled by comparison, it differs from the first capture on 23 fields; judged on the paper, 16 of them are council corrections or blank rows (the paper shows the capture's value), and the model disputed 7 of the other 7: 1 a confirmed capture error, 6 where the paper is ambiguous. Recall on confirmed capture errors rests on 1 field: it is unmeasured. |

The first capture is preliminary by design; the certified count is the official result.

One reader: 18% of forms accepted at second capture, 2 wrong fields in 1,210. Two readers that must agree, with the paper's sums as referee: 30%, 0 wrong in 1,958 (secondary, lighter gate; with the full gate, 7%, 0 wrong in 484). The one-reader figure is the pre-registered primary.

Every number above is computed by `scripts/build_headline.py` into `app/data/headline.json`, which the web app
reads. Details: [docs/EVALUATION.md](docs/EVALUATION.md). Sources: [docs/NUMBERS.md](docs/NUMBERS.md). Every
verdict and crop: [`results/adjudication/`](results/adjudication/SUMMARY.md).

## What ran on AMD

**Standing workload.** The live audit reads INE's public presidential tally sheets on AMD, one form at a time, and shows
a public counter of reads on Home and at `/live` (computed from the worker's state). On a fresh deployment it starts at
zero; this repo's local worker state holds 10 forms read on 2026-10-15, by Qwen3.8-27B during Gemma's gap.

**AMD evidence.**

| | |
|---|---|
| Hardware | AMD GPUs behind the **AMD Token Factory** ([notebooks.amd.com/tokenfactory](https://notebooks.amd.com/tokenfactory)), which AMD describes as "GPU Accelerated AMD ROCm"; the endpoint does not report the GPU model, so we name no card |
| Model | **Gemma-4-31B-IT**, temperature 0, one request per form (masked page + 6 zoomed tiles); every measured read of the 300 and of the 100-form confirmation |
| Serving | hosted by AMD, OpenAI-compatible API; our client is `twohands/amd.py` (standard library only) |
| Benchmark (our data, n = 289 reads) | Server time per form: 83 s mean, 71 s median: the HTTP round trip of the answered request on the shared endpoint, 289 answered reads of Gemma-4-31B-IT, 2,609 tokens in and 804 out per form (about 10 output tokens a second per request). About $24 of AMD compute to read all 169,005 national presidential tally sheets with Gemma-4-31B-IT ($0.000144 per form, the mean billed cost of 289 reads). 289 of 289 replies finished with `stop`. Table: [`results/amd_benchmark.md`](results/amd_benchmark.md) |
| Logged | every HTTP attempt with timestamp, status and round trip (`results/endpoint_health.jsonl`); every read with its tokens and billed cost from the API's `usage` (`results/calls_*.jsonl`); the model catalogue snapshot during the outage ([docs/AMD.md](docs/AMD.md)) |
| Outage | Gemma was unavailable on the shared endpoint from 2026-10-15 15:41 to 2026-10-16 02:06 UTC (`results/endpoint_health.jsonl`); every stored Gemma number is Gemma on AMD |
| Second reader | **Qwen3.8-27B** on the same endpoint, reasoning effort low; it never overrides Gemma, it only withholds acceptance |
| What ran on AMD | every model read: Gemma (primary), Qwen3.8-27B (second reader), the bake-off models; the Evolus agent's model |
| Not on AMD | page locating and masking (OpenCV, CPU), the gate (plain Python), the web app |

The 87 s per form reported for the 300 run is wall clock on a shared key under our own pacing (2 requests in flight), not GPU time; the endpoint's own round trip, which includes its queue, was 83 s of it.

Two Gemma misreads the arithmetic caught, each with its masked crop: [docs/GEMMA.md](docs/GEMMA.md#misreads-the-arithmetic-caught).

Full detail and the raw result files: [docs/AMD.md](docs/AMD.md). How Gemma is made to work here, and Gemma vs
Qwen on the same forms: [docs/GEMMA.md](docs/GEMMA.md).

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env                    # optional: fill in AMD_KEY and AMD_BASE_URL for live reads
python run_app.py                       # http://127.0.0.1:8000
python -m pytest -q                     # tests
```

The app serves the measured reads from the result files in this repo. No API key is needed to browse. The
"Read live on AMD" button needs `AMD_KEY` and `AMD_BASE_URL` in the environment or in `.env` (never committed).
[`.env.example`](.env.example) lists every environment variable the app, the worker, the CLI, the Evolus
integration and the deploy scripts read, one comment each, no values.

### Reproduce every number

No key, no model call, no network:

```bash
make eval        # or: python -m twohands.eval
```

`make eval` → "every number on the site recomputed from raw results in 2 seconds". It recomputes:

- the headline numbers, the 52 by type, 1 in 37 / 1 in 374 / 1 in 605, 1 in 5 vs at least 1 in 122;
- the certified 22 of 31, recall 7 of 7, the post-hoc v2/v2b lines, the touchless count;
- the cost per form from `results/calls_*.jsonl`, the adjudication verdicts and the official values in `app/data/`.

It checks each against what the app displays, checks the manifest sha256s and that PROTOCOL.md and each amendment
were committed before the first model read they govern, writes `results/eval_report.md` and exits non-zero on any
mismatch.

Reproduce the pre-registered run (needs the AMD key; resumable):

```bash
python -m twohands.run --models gemma,qwen --max-daily-usd 0.80
```

## Audit your capture

`/audit/new` (nav: "Audit your capture"). Upload the keyed data as a CSV (one row per form; INE PREP column names
are mapped automatically, any column can be re-mapped) plus a ZIP of scans, or use the forms this site has already
read.

Every keyed field is compared with the model's digits and words and with the paper's identities. Disputes are
ranked by evidence (strong: digits = words, and the keyed value breaks an identity the model's value satisfies).
Each comes with its crop, a "confirmed / not an error" mark, a CSV export and a printable report. Scans are masked
in memory by the core before anything is stored; forms without a read go through the live-read path and its
budget guard.

**Run the sample audit** loads the official first capture of the 300 pre-registered forms
(`app/data/audit_sample_prep300.csv`, built by `scripts/build_audit_sample.py`) against the stored Gemma reads. No
model call; 6,358 fields checked; the same 267 disputes as `results/adjudication/`. 12 of the 18 ranked strong are
confirmed capture errors, 13 of the 169 ranked weak (the rule was written before that check, on the same forms).
To have us run one on your forms: `/audit/request` ($1 per form audited, report within 24 hours).

## Verify a receipt

Each report prints a Merkle root over its disputed fields; each field's "receipt" link (`/audit/<id>/receipt/<key>`) gives its leaf (form, field, keyed value, model digits and words, tier, crop SHA-256) and the path to that root.
Check one field alone: `python -m twohands.verify_receipt receipt.json --crop crop.jpg` (a changed value or crop fails).
The sample audit's root is published in `results/sample_audit_root.txt`, and `make eval` rebuilds it so it cannot drift.

## Verify the timestamp

Each report's root is anchored in Bitcoin with OpenTimestamps (only a hash goes to the public calendars); the report links the `.ots` proof, and the sample's is `results/sample_audit_root.txt.ots`. `pip install opentimestamps-client`, then `ots verify results/sample_audit_root.txt.ots`.
The Bitcoin confirmation takes a few hours after stamping, so run `ots upgrade results/sample_audit_root.txt.ots` first (once) to fetch it; `twohands audit --timestamp` stamps a CLI report's `merkle_root.txt`.

## CLI

`pip install -e ".[mcp]"` (from this folder) gives the `twohands` command (also `python -m twohands`). It reuses the
core and the web app's audit module, so it gives the same disputes, order, CSV, fingerprint and Merkle root as `/audit`.

```
twohands audit --keyed capture.csv --scans scans/ --schema mx_presidencia_2024 --out report/
twohands audit --keyed app/data/audit_sample_prep300.csv --from-stored --out report/   # no model call
twohands read form.jpg [--masked] [--layout movil|escaner]      # locate, mask, one read, the gate
twohands gate values.json [--variant v1|v2|v2b]                 # exit 0 accepted, 2 routed to a person
twohands verify-receipt receipt.json [--crop crop.jpg] [--root <hex>]
```

`audit` locates and masks each scan (named `<form id>.jpg`) in memory, reads only the forms without a read through the
configured OpenAI-compatible endpoint (`AMD_BASE_URL` / `AMD_KEY`, or `--base-url`), and writes `report.html`,
`report.csv`, `merkle_root.txt`, `summary.json`, `disputes.json` (and with `--receipts`, one receipt per field).
`--from-stored` uses the stored pre-registered reads only. On the sample it prints:

```
audit a…: 289 of 300 keyed forms read, 6,358 fields checked, 267 disputed on 104 forms (strong 18, medium 80, weak 169); 0 model calls; Merkle root e56a8ef4f011b9e5a3b7bd91dd708580fe1a8912e3bd65f51d780a6dd5898721
```

the published root (`results/sample_audit_root.txt`); `tests/test_cli.py` checks it.

## MCP

`twohands mcp` (stdio) or `twohands mcp --http --port 8765` (streamable HTTP at `/mcp`) runs an MCP server on the
official Python SDK (`twohands/mcp_server.py`) with four tools: `read_form` (a masked page path or base64 → values,
words, labels, the gate's verdict), `gate` (values + schema → every identity and the verdict), `audit_capture` (keyed
CSV + stored or new reads → disputes summary, first disputes, report and CSV paths) and `verify_receipt`. File paths
must lie under the repo, the working directory or `TWOHANDS_MCP_ROOTS`; over HTTP, tools that would call the model are
refused unless started with `--allow-reads`. Desktop MCP clients: command `twohands`, args `["mcp"]`.

**Evolus.** The Evolus API attaches an MCP server that already exists in the application's MCP collection to an agent
(`POST /api/v1/agents/{agentId}/mcpserver/{mcpServerId}`); it cannot create the server entry, and Evolus calls the
server from its cloud, so it must be on a public HTTPS URL first. `python -m evolus mcp-register --url https://<host>/mcp`
prints the steps (run `twohands mcp --http --public-host <host>` behind HTTPS, add it in the workspace as a Streamable
HTTP server, then `--server-id <id> --apply` attaches it to the agent and reads the agent back). Not run against the
live workspace yet: no public URL.

## How it works

1. **Locate and mask.** The page is straightened onto a canonical layout. The right-hand column (names and
   signatures of officials and representatives) is blacked out **before the image is stored or sent to any
   model**. A page that cannot be located is not stored, not sent, and goes to a person.
2. **Read on AMD.** One request: masked page plus zoomed tiles. The model returns every field twice, from the
   digit boxes and from the words, plus the printed label of each row.
3. **Gate.** Code checks: 23 values parsed; every row label where it belongs; every digit field read;
   words = digits; 17 vote rows sum to TOTAL; voters + representatives = section 5; section 5 = section 7 =
   TOTAL. All pass: accepted, 0 fields to key. Any fail: routed, with the failing field and its crop.
4. **Review desk.** A person types the one value the paper could not settle. The identities re-check at once.
   If the paper contradicts itself, the person escalates it with a note. Nothing is corrected silently.

A form type is one schema file ([`schemas/mx_presidencia_2024.yaml`](schemas/mx_presidencia_2024.yaml)): field
positions, privacy mask, tiles and identities. A second, very different form type is measured too: UK rainfall
ledgers from 1850-1960, where twelve months must add up to the clerk's annual total. Architecture and diagram:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

**Why not plain OCR, why an LLM.** Classic OCR fails on this handwriting; that is why Rainfall Rescue used 16,000
volunteers (we did not run an OCR baseline ourselves). One vision model reads digits, words and row labels from
phone photos with no per-form training. It never decides: the paper's arithmetic does.

## Limits and failure cases

- **Touchless share.** The gate accepts 18% of forms with no person; the rest are routed.
- **One reader, one adjudicator.** The adjudicator is the AI adjudicator (the builder's model, which could see both
  values), working from the photo on published crops, which anyone can re-check; person-checked counts are reported
  separately (`/check`). Fields where the model and the capture agree were not individually checked (a seeded random
  200 is queued for a blind person check at `/check?set=agree200`). Recall is unmeasured: 1 of the 7 recall fields is a
  confirmed capture error.
- **Row-label check.** It is costly: it routed 86 forms, and on 68 of them the read matched the paper on every
  field (all 15 routed for a label alone).
- **Not independent.** In one call the model can harmonise words and digits, so one read is not two independent
  reads. The fix is separate reads or a second reader.
- **Pages not located.** 11 of the 300 went to a person before any model call.
- **Speed.** At our polite pace on a shared key (2 requests in flight) we read about 2 forms a minute; a dedicated endpoint was not measured.
- **Failure case.** On a rainfall ledger read as one image, Gemma shifted a whole row of values one year to the
  left. Every shifted column still summed to its total, so the checksum accepted 26 wrong cells (of 870
  accepted). Zoomed tiles removed it (0 of 3,976 accepted cells wrong; spike, 40 sheets). On the tally sheet we
  added the row-label check so a shifted row cannot pass.
- **Safeguard.** Accept only when every identity holds; everything else goes to a person with the field named.
  Privacy mask before storage or model call. Fail closed when the page cannot be located.

Full write-up, including the 43-form pilot: [docs/EVALUATION.md](docs/EVALUATION.md).

## Business detail

- **Buyer, 2027: an independent check of a finished capture.** The outside auditor or the contracted PREP operator,
  paid by the state institute (OPLE); no rule change needed. A model as the regulated second capture (PTO numeral 33)
  needs the institute's approval after INE's opinion (RE art. 339.1 d, 339.2): the longer-term path. Full case in
  [docs/BUSINESS.md](docs/BUSINESS.md#institutes-already-tried-to-buy-machine-reading).
- **Then the auditors.** Reglamento de Elecciones art. 347: every state institute has its PREP audited by an outside body,
  preferably academic. In February 2024, 26 of 32 institutes had named one, all universities or research centres
  ([INE annex](https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf)).
  The audit covers the computer system; we add the field-by-field check against the paper.
- **Next window.** The federal election and 32 concurrent local processes, election day 6 June 2027
  ([INE](https://centralelectoral.ine.mx/2026/07/30/perfila-ine-organizar-el-proceso-electoral-federal-y-32-concurrentes-2026-2027/)).
- **Size of one job (at $1 per form audited).** Morelos, 7,802 forms: about $7,800 (MXN 143k), under the lowest federal direct-award ceiling; the largest state (Estado de México), 20,908 forms: about $20,900 (MXN 384k), over the lowest federal direct-award ceiling, under the highest; the federal count, 169,005 forms: about $169,000 (MXN 3.1M), over every federal direct-award ceiling: a tender; INE's own line was MXN 9.5M. Federal
  direct-award ceilings: MXN 309,000 to 1,145,000 ([PEF 2026 Anexo 9](https://dof.gob.mx/2025/SHCP/PEF_2026.html));
  states buy under their own rules.
- **Yield (measured).** A person looks at about 5 disputed fields per confirmed capture error, against about 122
  at random: 267 disputed fields found 52; 267 random fields would find about 2. The strong-evidence tier is right
  12 of 18 times.
- **Unit economics.** $1 per form audited (second capture + cotejo + receipts) (proposal). Costs: AMD compute $0.00014 per form (measured); review labour for routed fields about $0.09 to $0.13 per form (GUESS: 20 s per disputed crop, 0.92 crops per form measured, $18 to $25 an hour); hosting and sales,
  not measured. Line 2: $5 per confirmed capture error, $0 if none is found (measured: 52 confirmed capture errors in 267 disputed fields (19.5%, 1 in 5.1) on 289 read forms, 180 per 1,000 forms; $1 / 0.180 = $5.56, rounded down to $5). Self-serve (CLI / MCP, you review your own disputes): $0.10 per form.
- **A second line, not the hero.** When an agent keys a form, the paper still has to agree. Receipts work the same
  for a model as for a person; in our measurement, Gemma is the agent (alone it mis-keys 1 field in 37; the paper's
  arithmetic catches it the same way).
- **Next markets, not measured** (sources in [docs/BUSINESS.md](docs/BUSINESS.md#next-markets-not-measured)):
  1. Health facility monthly reports (HMIS / DHIS2): WHO's Data Quality Review recounts the paper source documents against what was keyed into the national database, and DHIS2 is the national health data system in 80+ low- and middle-income countries; the monthly forms carry their own totals (Kenya MOH 711A: new + re-visits = total).
  2. US mortgage post-closing QC: Fannie Mae's Selling Guide makes lenders re-check at least 10% of the loans they close (or a statistical sample) every month, plus targeted selections, against the source documents; 4.4 million closed-end originations in 2023.
  3. Clinical-trial source data verification: a 7,000-trial analysis found it corrects 1.1% of site-entered data, while monitoring and verification take 15-30% of trial costs; pointing the monitor at the fields the paper disputes is the mechanism we measured on election forms.
- **Competition.** OCR and IDP platforms (Tesseract, ABBYY, Rossum, Hypatos, UiPath, Textract, Document AI)
  extract; none says it audits an existing capture with a crop per finding.
- **Same job elsewhere (volume, not measured).** Peru: ONPE's 2026 rule keys every acta twice, one of them by a virtual assistant ("una de ellas, por un asistente virtual"); same process, second country, by regulation; not measured by us. One result sheet per polling station: Nigeria
  176,846, Kenya 46,229, India 1,052,664, Indonesia 820,161, Peru 92,766; sources in
  [docs/BUSINESS.md](docs/BUSINESS.md#the-same-job-in-other-countries-volume-only-not-measured).
- **Why double keying is not enough.** It copies the paper faithfully but cannot say which paper is wrong: 19.2% of
  nationally captured tally forms (26,336 of 137,196) fail their own row sum. Table in
  [docs/BUSINESS.md](docs/BUSINESS.md#3-competitive-analysis).

## Data and privacy

- **Masking.** Every page is privacy-masked before it is stored or sent to a model: the column with the officials'
  names and signatures is blacked out (`schemas/*.yaml`, `twohands/mask.py`); `tests/test_mask.py` checks every stored page
  is masked.
- **No personal data stored.** The repo holds masked pages, numeric fields and crops of vote rows. Audit requests
  and uploads live in `app/state/`, which is not committed; email is sent only when SMTP is configured.
- **Not in the repo.** Unmasked originals (`data/raw/`) and the builder's outreach drafts to institutions are kept
  outside the repository and are never committed.
- **Terms.** INE data is reused under INE's free-use terms (Libre-Uso-MX: extraction, commercial use and derived
  datasets permitted; cite the source and date; do not imply an official position or endorsement). Source, quote
  and date: [docs/sources/tally-witness-pilot.md](docs/sources/tally-witness-pilot.md) section 1.

## Data, credit and framing

- **Tally sheets:** INE PREP 2024 (prep2024.ine.mx) and certified Cómputos Distritales 2024
  (computos2024.ine.mx), consulted 2026-10-14, reused under INE's free-use terms (Libre-Uso-MX).
- **Not official.** This is an independent demonstration of clerical capture quality. **It is not an official INE
  product** and does not represent INE or any government.
- **Neutral.** Vote rows are shown as "Option 01" to "Option 15"; no party is named, compared or totalled.
  "Capture error" means the capture does not match the paper, nothing more.
- **Machine files use INE's column names** (the schema YAML, `results/*.jsonl`, `verdicts.json` keys); every
  human-readable file and page uses "Option NN".
- **Personal data:** the names-and-signatures column is masked before any image is stored or sent to a model.
  Only masked pages are in this repo.
- **Rainfall ledgers:** Rainfall Rescue (Hawkins et al., Geoscience Data Journal 2022;
  github.com/ed-hawkins/rainfall-rescue; Met Office scans). Sheet images are **linked, not redistributed**; only
  our extracted values are stored.

## Evolus

**Evolus event workspace: py_tr (event code AMDACT3).** The name is read from the Evolus API
(`application.name`) and shown on the site's Evolus section. The workspace stays online until Nov 15, 2026 for the
Evolus team's review.

The same process runs as a case on **Evolus** (Evolus Business Agents track). The masked page is the input, and an
open model on AMD reasons over it: the agent "Intake clerk" runs **Gemma-4-31B-IT on the AMD Token Factory**,
connected under "Your models" as an OpenAI-compatible server (requirement 2: [docs/EVOLUS.md](docs/EVOLUS.md)).

- **Live audit (critical path):** every strong-evidence dispute the live worker finds starts one run of the workflow
  **"Audit finding"** (the clerk drafts the finding, a Script recomputes the evidence score with no AI); the case
  comes back to the site. Capped at `EVOLUS_DAILY_RUNS` (60) runs a day to protect the shared AMD key.

- **Accepted form:** starts the workflow **"Record filing"**. A deterministic Script re-checks the paper's
  identities inside Evolus and files the record.
- **Routed form:** starts the workflow **"Review hand-off"**. The agent **"Intake clerk"** (an open model on the
  AMD Token Factory, connected under "Your models") writes the review task, the AI Tool `translate` turns it into
  Spanish, and the task reaches a person on our review desk ("Send to Evolus" on any routed form).
- **Third reader:** an Evolus extractor ("Tally sheet reader"), gated and compared, never trusted blindly.

The form page and the review desk show each form's Evolus run: id, steps and status. Details, endpoints and the
real run: [docs/EVOLUS.md](docs/EVOLUS.md).

```bash
python -m evolus setup            # find or create every Evolus block (idempotent) -> evolus/ids.json
python -m evolus run --pick 2,3   # run the case on 2 accepted + 3 routed forms -> results/evolus_runs.jsonl
python -m twohands.worker run     # the live audit; strong disputes -> "Audit finding" (EVOLUS_LIVE=0 turns it off)
```

Environment: `EVOLUS_KEY`, `EVOLUS_APP_ID`; optional `EVOLUS_USER_KEY` (needed to create the extractor schema and
the library), `EVOLUS_REVIEWER_EMAIL`, `TWOHANDS_GATE_TOKEN`, `TWOHANDS_PUBLIC_URL`, `EVOLUS_CALLBACK_KEY`, `EVOLUS_DAILY_RUNS`,
`EVOLUS_LIVE`.

## Live audit

A standing service keeps auditing presidential tally sheets on AMD during judging: `python -m twohands.worker run`
(`twohands/worker.py`; the `worker` service in `deploy/docker-compose.prod.yml`). Status at **/live**, sources at
**/about-data**, three numbers on the Overview.

- **Order:** smallest state first (Colima); inside a state, forms whose certified count was settled by comparison
  first, then recounts. Forms in any measured sample are skipped (they are on Results). Queue:
  `live_audit/queue.json.gz`, built offline by `python -m twohands.worker build-queue` from the PREP and Computos CSVs.
- **Per form:** fetch the image from INE's public PREP URL (at most one request per second, User-Agent
  `two-hands-audit (contact: see README)`, backoff; 429/403 pauses the source), mask it in memory, store only the
  masked page downscaled to 150 KB, read it with the model the endpoint offers (Gemma-4-31B-IT when listed, else
  Qwen3.8-27B; the id is on every row), gate it, and compare it with the PREP capture and the certified count.
- **Labels:** on vote rows and TOTAL of comparison-settled forms, certified = model != capture is "confirmed by the
  certified count", certified = capture != model is "model misread"; everything else is "dispute (unconfirmed)".
  Each dispute is a Merkle leaf (`twohands/merkle.py`), one root per completed state, a running root for the open one.
- **Row-label check failed:** such a form is still compared field by field; its disputes are tagged "label check
  failed: weaker evidence" and counted separately (the check was a false alarm in 68 of 86 cases on the 300).
- **Budget and pace:** 3 reads in flight (`WORKER_CONCURRENCY`), at most $0.60 a day, keeping $0.20 for the
  live-read button; then it sleeps until 16:00 UTC. It shares the rate-limiter file with the live reads and yields
  to them while one is queued. Resumable, crash-safe writes, a watchdog, rotating logs, a disk cap.
- **Separate:** it never writes `results/`; `make eval` never reads `live_audit/`.
- **Contact** (for INE or any operator of the source, as the User-Agent says): the maintainers of this repository,
  through the submission page's team contact.

## Run with Docker

```bash
docker compose up --build         # http://localhost:8000
```

The image is `python:3.13-slim` with OpenCV headless and runs as a non-root user. Keys are read at run time from an
untracked `.env` next to `docker-compose.yml`: `cp .env.example .env` and fill in `AMD_KEY`, `AMD_BASE_URL` and, for
Evolus, the Evolus variables above. `.env` is excluded from the image by `.dockerignore`.

`data/masked` and `results` are mounted read-only; `app/state` (review desk, live reads, Evolus callbacks) is a
writable volume. Without a `.env` the app still serves every measured result. Inside the container the live-read
rate limiter uses its own file (`app/state/ratelimit.json`), so it does not see a batch run on the host.

## Deploy

`deploy/deploy.sh user@IP [domain]` installs Docker, copies the repo (never `.env`, `data/raw`, `cache`) and your
`.env` (scp, mode 600), and starts the app behind Caddy: HTTPS for a domain, plain HTTP on the IP otherwise;
variables in `deploy/.env.prod.example` (a subset of [`.env.example`](.env.example)).

`python -m app.export_static out/ --main-url URL` writes a static mirror (relative links, masked images only, live
parts off); `.github/workflows/pages.yml` publishes it to GitHub Pages on push to main.

## Repo map

| Path | What |
|---|---|
| `twohands/` | core: sample, locate + mask, reader, AMD client + rate limiter, gate, runner, eval |
| `schemas/` | the form type: layout, privacy mask, fields, identities |
| `app/`, `templates/`, `static/` | FastAPI web app: viewer, review desk, audit gallery, results, live read |
| `ledger/` | the rainfall-ledger snapshot (second form type) |
| `results/` | manifest, prepare log, run log, every raw model call |
| `PROTOCOL.md` | the pre-registered protocol for the 300-form run, with Amendments 1-3 and 6-8 (drafts 4 and 5 in their own files) |
| `scripts/build_headline.py` | computes every headline number into `app/data/headline.json` (+ adjudication SUMMARY, RECALL) |
| `submission/lablab.md` | the submission page text |
| `submission/links.json` | the one place the submission links (repo, demo, video, sample report, slides) are kept |
| `docs/sources/` | the event rules we cite (public URLs, dated Discord quotes) and the pilot write-ups, copied with their origin |
| `.env.example` | every environment variable, one comment each, no values |
| `tests/` | gate, mask, rate limiter, app routes, privacy and neutrality tests |
| `evolus/` | Evolus integration: REST client, the intake case, gate endpoint, CLI (`python -m evolus`) |
| `twohands/cli.py`, `twohands/mcp_server.py` | the `twohands` command and the MCP server (`pyproject.toml`) |

MIT licence. API keys live only in the environment or an untracked `.env`.
