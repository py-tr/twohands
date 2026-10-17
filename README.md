# Two Hands: verifiable quality control for handwritten numbers

OCR reads the number. Two Hands checks whether the whole form agrees.

Works on any handwritten form whose numbers must add up: cheques (amount in digits and words), invoices and receipts, election tally sheets in any country, clinic and health-facility reports, pharmacy and stock registers, timesheets, customs forms, historical ledgers. Tested on Mexico's 2024 tally sheets (and UK rainfall ledgers, 1850-1960).

A model reads; the form's own arithmetic decides what passes; people review the rest with the photo; accepted values get receipts.

- **Real data:** Gemma on AMD read 1,270 real handwritten tally sheets (289 of a random 300 and Colima's 982, one sheet in both); 49 capture errors confirmed by the certified count, each with its photo.
- **Against the incumbent:** on Baja California Sur's 2024 local actas, 91.6% of fields match the published values, on the same per-field metric where the state's purchased Google Document AI reading scored 62.84% (pre-registered random 300 actas).
- **Checked:** recall 27 of 28 on the capture errors the certified count reveals (one state, pre-registered); a person re-read the AI-judged disputes blind: 0 read differently.
- **Why Gemma:** same 300 forms, same gate, on AMD Token Factory: 1.8x the forms Qwen3.8-27B accepts at the same error rate, 4.6x cheaper, 2.8x faster ([the table](#why-gemma)).
- **Re-derive it:** images, keyed values and certified counts are public (INE); [`make eval`](#reproduce-every-number) recomputes every number offline.

**Business at a glance.**

| | |
|---|---|
| Buyer | Mexico's preliminary counts (PREP): INE and the 32 state institutes, each with an outside auditor (all 26 named in 2024 were universities). At least 13 of the 17 outsourced state PREPs of 2024 went to three firms. |
| Why now | 6 June 2027: the federal midterm and 32 concurrent local elections. Each state picks its PREP operator by about 6 December 2026. INE budgeted MXN 9.5M for automated capture in 2024 and bought none (no bidder met its 80% bar); its advisers asked for a pilot. |
| Product | An independent field-by-field check of a finished capture against the photo; no rule change needed. Also an API, CLI and MCP server, for software vendors that already key these forms. |
| Price | $1 per sheet audited (proposed); first step: a paid shadow-mode pilot on one state's 2027 count. AMD compute: $0.00014 per sheet. |
| Reviewer work | About one photo crop per sheet to look at (0.92 measured: fields where the read and the capture disagree), instead of re-keying about 22 fields. |
| Capacity | One shared AMD key audits Colima's 982 sheets in about 3.4 hours and Morelos's 7,802 in about a day. A check of a finished capture, not election-night capture. |
| Example | Morelos paid MXN 26.6M to run its 2024 PREP (7,802 sheets), including an MXN 1.5M audit of the software, not of the keyed values. Our check of every sheet: about MXN 143k ($7,800), 0.5% of that. |
| Competition | Second keying by a person (the rule today): at least 0.8% of fields in our random sample still do not match the paper. On Baja California Sur's 2024 local actas, Gemma on AMD matched the published PREP values on 91.58% of fields (n = 3,622 fields on a pre-registered random sample of 300 of the 2,020 actas; Wilson 95% 90.63-92.44%), on the per-field exact-match metric where the state's purchased Google Document AI reading scored 62.84% (14,501 of 23,077 fields on all 2,020 actas, against the manual capture rather than the published values). Ours accepts only what the paper's arithmetic proves and routes the rest with the photo. |
| Next | A paid shadow-mode pilot with one state for 2027. The same check: cheques, invoices and receipts, health-facility reports, stock registers, timesheets, customs forms, election tally sheets in other countries. Already measured on a second form type: UK rainfall ledgers (1850-1960). |
| Next: elections | The same public data exists in at least 7 more countries, e.g. Indonesia (823,236 polling stations), Colombia (125,259 tables), Peru (92,766 actas); Guatemala, Kenya and Argentina also vote in 2027. |
| Next: health | Monthly health-facility reports: DHIS2 runs national health reporting in 70+ countries; Ethiopia alone reports monthly from 30,000+ facilities, many on paper first. Funders already pay for manual re-checks (a malaria data audit in Zambia: about US$205 per facility). |

**Scope.** Clerical capture quality only: whether a typed number matches its paper. No results, no parties (vote rows are Option 01 to Option 15), no totals, no claim about any outcome; we did not assess vote impact. The certified count is the official result. An independent demonstration, not an official INE product.

<!-- links:start -->
**Live demo:** add at submission · **Video:** add at submission · **Repository:** add at submission ·
**Audit report sample:** add at submission (in the repo: [the 52, each with its crop](results/adjudication/SUMMARY.md)) ·
**How to reproduce:** [`make eval`](#reproduce-every-number) ·
**Report:** [technical report (PDF)](report/two-hands-report.pdf), source [`docs/REPORT.md`](docs/REPORT.md)
(links are kept in [`submission/links.json`](submission/links.json))
<!-- links:end -->

## Contents

1. [Headline: the pre-registered 300](#headline-the-pre-registered-300)
2. [Why Gemma](#why-gemma) · [What ran on AMD](#what-ran-on-amd)
3. [Business detail](#business-detail) (sources: [docs/BUSINESS.md](docs/BUSINESS.md#sources-for-the-business-at-a-glance-table))
4. [Run it](#run-it) · [Reproduce every number](#reproduce-every-number)
5. [Audit your capture](#audit-your-capture) · [Verify a receipt](#verify-a-receipt) · [CLI](#cli) · [MCP](#mcp)
6. [How it works](#how-it-works) · [Execution trace: two real forms, request to receipt](docs/TRACE.md) (site: `/trace`)
7. [Limits and failure cases](#limits-and-failure-cases)
8. [Data and privacy](#data-and-privacy) · [Data, credit and framing](#data-credit-and-framing)
9. [Evolus](#evolus) · [Docker](#run-with-docker) · [Deploy](#deploy) · [Repo map](#repo-map)

## Headline: the pre-registered 300

The PREP rules require a second capture and a comparison for every acta (numeral 33) and a cotejo. Two Hands checks a finished capture against the photo, field by field: it accepts what the paper's arithmetic confirms and sends the rest to a person, with the photo.

![Option 07 on form 050815B0100: the words say "ciento setenta y cinco", the boxes say 1 7 5](slides/receipt_050815B0100.jpg)

*Form 050815B0100, Option 07 (masked page, cropped right of the logo column). The paper says 175, the first
capture keyed 75, the certified count says 175. One of the 52.*

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
| Pre-registered confirmation, 100 fresh forms (Amendment 3) | gate v2 accepted 22 forms: **0 of 484 fields wrong**, judged against the official capture with every disagreement checked on the photo (point estimate meets the pre-registered 0.5% bar; Wilson 95% upper bound 0.79%) ([`results/confirm100.md`](results/confirm100.md)) |
| Yield of a disputed field | 1 in 5 disputed fields is a confirmed capture error (52 of 267). The capture's overall error rate is at least 1 in 122 (52 of 6,358 found so far). Of the 52: 22 confirmed by the certified count · 30 judged from the photo by the AI adjudicator (the builder's model, which could see both values; checked by a person: 30 of 30, 27 agree, 3 unreadable to the person). The multiple between the two rates is not a recall estimate. |
| Recall | Recall on the capture errors the certified count reveals, Colima (pre-registered, a person's blind check): 27 of 28 caught, 96% (Wilson 95% 82-99%). One state, certified-detectable errors only; not total recall. (`results/colima/recall.md`) |

The first capture is preliminary by design; the certified count is the official result.

One reader: 18% of forms accepted at second capture, 2 wrong fields in 1,210. Two readers that must agree, with the paper's sums as referee: 30%, 0 wrong in 1,958 (secondary, lighter gate; both readers on the full gate, 7% of these 300, 0 wrong in 484). The one-reader figure is the pre-registered primary. That 0 of 484 is two readers on the random 300. The deck's 0 of 484 is a separate result with the same count: one reader, gate v2, fixed before 100 fresh forms were drawn (Amendment 3), accepted 22 of them, 0 of their 484 fields wrong (Wilson 95% upper bound 0.79%).

Alone, one model mis-keys 1 field in 37. Two models that agree, refereed by the paper, mis-keyed 0 of 1,958 accepted fields against the official capture. That is the secondary two-reader tier, on the lighter gate.

Whole state: Gemma on AMD read all 982 located presidential sheets of Colima for $0.14; 27 fields where the capture does not match the paper, each confirmed by the certified count, with a field-level report. One reader, frozen gate: 2 wrong of 1,210 accepted fields on 300 random forms (0.17%), 13 of 8,382 on a whole state (0.16%). Every number: [`results/colima/colima_audit.md`](results/colima/colima_audit.md) (Amendment 8b).

Every number above is computed by `scripts/build_headline.py` into `app/data/headline.json`, which the web app
reads. Details: [docs/EVALUATION.md](docs/EVALUATION.md). Sources: [docs/NUMBERS.md](docs/NUMBERS.md). Every
verdict and crop: [`results/adjudication/`](results/adjudication/SUMMARY.md).

## Why Gemma

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

Measured on Gemma-4-31B-IT on the AMD Token Factory. Live reads use Gemma when it is listed, and fall back to Qwen3.8-27B otherwise; every receipt names its reader.

## What ran on AMD

**Standing workload.** The live audit reads INE's public presidential tally sheets on AMD, one form at a time, and shows
a public counter of reads on Home and at `/live` (computed from the worker's state).

**AMD evidence.**

| | |
|---|---|
| Hardware | AMD GPUs behind the **AMD Token Factory** ([notebooks.amd.com/tokenfactory](https://notebooks.amd.com/tokenfactory)), which AMD describes as "GPU Accelerated AMD ROCm"; the endpoint does not report the GPU model, so we name no card |
| Model | **Gemma-4-31B-IT**, temperature 0, one request per form (masked page + 6 zoomed tiles); every measured read of the 300 and of the 100-form confirmation |
| Serving | hosted by AMD, OpenAI-compatible API; our client is `twohands/amd.py` (standard library only) |
| Benchmark (our data, n = 289 reads) | Server time per form: 83 s mean, 71 s median (HTTP round trip, shared endpoint, 289 reads of Gemma-4-31B-IT, 2,609 tokens in, 804 out). Measured capacity (shared endpoint, 2026-10-17 00:48-01:03 UTC, queueing included, not GPU time): 4 in flight, 4.8 forms/minute, 32 s median, $0.000146/form; one shared key reads a state the size of Colima (982 sheets) in about 3.4 hours; national figures in results/throughput_sweep.json. Latency per read (shared AMD endpoint, queue included): 32 s p50, 67 s p95 at 4 in flight (12 of the sweep's 44 requests); 71 s median over the 289 requests of the 300 run; 9.6 output tokens/s per request (804 out, 83 s mean round trip). Fine for an audit after the count, where nobody waits on one sheet: a state the size of Colima (982 sheets) in about 3.4 hours. About $24 of AMD compute to read all 169,005 national presidential tally sheets with Gemma-4-31B-IT ($0.000144 per form, the mean billed cost of 289 reads). 289 of 289 replies finished with `stop`. Table: [`results/amd_benchmark.md`](results/amd_benchmark.md) |
| Logged | every HTTP attempt with timestamp, status and round trip (`results/endpoint_health.jsonl`); every read with its tokens and billed cost from the API's `usage` (`results/calls_*.jsonl`); the model catalogue snapshots ([docs/AMD.md](docs/AMD.md)) |
| Second reader | **Qwen3.8-27B** on the same endpoint, reasoning effort low; it never overrides Gemma, it only withholds acceptance |
| What ran on AMD | every model read: Gemma (primary), Qwen3.8-27B (second reader), the bake-off models; the Evolus agent's model |
| Not on AMD | page locating and masking (OpenCV, CPU), the gate (plain Python), the web app |

The 300 run's 87 s per form was wall clock under our own pacing (2 in flight), not GPU time; 83 s of it was the endpoint's round trip, queue included.

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
"Read live on AMD" button needs `AMD_KEY` and `AMD_BASE_URL` in the environment or in `.env` (never committed);
without them it says live reads are off and shows the form's last measured read. With a key, live reads are capped
at 5 per visitor and 40 per site a day, and at $0.10 a day (`LIVE_MAX_READS_PER_IP`, `LIVE_MAX_READS_PER_DAY`,
`LIVE_MAX_USD_PER_DAY`).
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

`make eval` then runs each script's `--check` (the lines under `eval:` in the [Makefile](Makefile); without `make`,
run them one by one). The INE source CSVs are not in the repo (`data/raw/` is gitignored, about 130 MB). Without them,
`ballot_stock`, `confirm100_score` and `national_counts` only confirm that their committed results are present.
To recompute those three as well, unzip
[the PREP file](https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip) to
`data/raw/prep/PRES_2024.csv` and [the Cómputos file](https://computos2024.ine.mx/20240608_2030_COMPUTOS.zip) to
`data/raw/computos/PRES_2024.csv`.

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
To have us run one on your forms: `/audit/request` ($1 per sheet audited, proposed; report within 24 hours).

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
HTTP server, then `--server-id <id> --apply` attaches it to the agent and reads the agent back).

## How it works

On the site: `/how`.

1. **Locate and mask.** The page is straightened onto a canonical layout. The right-hand column (names and
   signatures) is blacked out **before the image is stored or sent to any
   model**. A page that cannot be located is not stored, not sent, and goes to a person
   ([`twohands/mask.py`](twohands/mask.py)).
2. **Read on AMD.** One request to Gemma-4-31B-IT on AMD: masked page plus zoomed tiles. It returns every field
   twice, from the digit boxes and from the words, plus each row's printed label
   ([`twohands/reader.py`](twohands/reader.py)).
3. **Gate.** Code checks: 23 values parsed; every row label where it belongs; every digit field read;
   words = digits; 17 vote rows sum to TOTAL; voters + representatives = section 5; section 5 = section 7 =
   TOTAL ([`twohands/gate.py`](twohands/gate.py)). The gate decides, not the model.
4. **Second reader (optional).** In two-reader mode Qwen3.8-27B, also on AMD, must agree with Gemma field by
   field before the gate accepts. It can only withhold acceptance, never override Gemma.
5. **Accepted or routed.** All checks pass: accepted, 0 fields to key. Any fail: routed, with the failing field
   and its crop.
6. **Review desk.** A person types the value the paper could not settle, from the crop; the identities re-check
   at once. A self-contradicting paper is escalated with a note. Nothing is corrected silently.
7. **Receipt.** Each disputed field is a Merkle leaf (form, field, keyed value, model digits and words, tier,
   crop SHA-256); each report has one root, anchored in Bitcoin with OpenTimestamps. `python -m
   twohands.verify_receipt` checks one field alone ([Verify a receipt](#verify-a-receipt)).
8. **Audit at scale.** An auditor uploads the keyed data (CSV) and scans; disputes come back ranked strongest
   evidence first, each with its crop, plus a CSV and a printable report ([Audit your capture](#audit-your-capture)).
9. **Evolus.** Each strong finding opens a case: the agent Intake clerk, on Gemma-4-31B-IT on AMD, drafts it in
   the workflow Audit finding, and a script, not the model, scores the evidence. A routed form goes through Review
   hand-off, where the AI Tool `translate` turns the task into Spanish ([docs/EVOLUS.md](docs/EVOLUS.md)).
10. **Interfaces.** Web app, JSON API (`/api`), [CLI](#cli) and [MCP server](#mcp), one core.
11. **Form schema.** A form type is one YAML file
    ([`schemas/mx_presidencia_2024.yaml`](schemas/mx_presidencia_2024.yaml)): field positions, privacy mask, tiles
    and identities. A second, very different form type is measured too: UK rainfall ledgers, 1850-1960
    ([`ledger/`](ledger/)), where twelve months must add up to the annual total.

Architecture and diagram: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

**Why an LLM, not plain OCR.** Classic OCR fails on this handwriting; that is why Rainfall Rescue used 16,000
volunteers (we did not run an OCR baseline ourselves). One vision model reads digits, words and row labels from
phone photos with no per-form training.

## Limits and failure cases

- **Touchless share.** Most forms are routed to a person. Colima accepts 37.5% of forms, against 18% on the national random 300; phone photos pass about as often as scans (39.3% and 37.6%), and scans carry 11 of the 13 accepted errors.
- **One reader, one adjudicator.** The adjudicator is the AI adjudicator (the builder's model, which could see both
  values), working from the photo on published crops, which anyone can re-check; person-checked counts are reported
  separately (`/check`). Fields where the model and the capture agree were not individually checked (a seeded random
  200 is queued for a blind person check at `/check?set=agree200`). Recall is measured only on the errors the
  certified count reveals, in one state (27 of 28, Amendment 9); not total recall.
- **Blind spot.** SOBRANTES (unused ballots) is the one graded field in no printed identity, and one read can
  harmonise its words and digits: every accepted-field error on the 300 was SOBRANTES. Gate v3 (pre-registered)
  accepts it only when two independent reads agree.
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
- **Size of one job (at $1 per sheet audited).** Morelos, 7,802 forms: about $7,800 (MXN 143k), under the lowest federal direct-award ceiling; the largest state (Estado de México), 20,908 forms: about $20,900 (MXN 384k), over the lowest federal direct-award ceiling, under the highest; the federal count, 169,005 forms: about $169,000 (MXN 3.1M), over every federal direct-award ceiling: a tender; INE's own line was MXN 9.5M. Federal
  direct-award ceilings: MXN 309,000 to 1,145,000 ([PEF 2026 Anexo 9](https://dof.gob.mx/2025/SHCP/PEF_2026.html));
  states buy under their own rules.
- **Yield (measured).** A person looks at about 5 disputed fields per confirmed capture error, against about 122
  at random: 267 disputed fields found 52; 267 random fields would find about 2. The strong-evidence tier is right
  12 of 18 times.
- **Unit economics.** $1 per sheet audited (proposed); first step: a paid shadow-mode pilot. Costs: AMD compute $0.00014 per form (measured); review labour for routed fields about $0.09 to $0.13 per form (estimate: 20 s per disputed crop, 0.92 crops per form measured, $18 to $25 an hour); hosting and sales, not measured. Self-serve (CLI / MCP, you review your own disputes): $0.10 per form.
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
connected under "Your models" as an OpenAI-compatible server (requirement 2: [docs/EVOLUS.md](docs/EVOLUS.md)). Each strong finding opens a case in Evolus: the agent Intake clerk, on Gemma-4-31B-IT, drafts it in the workflow Audit finding; a script, not the model, scores the evidence. 150 of 150 runs on real routed fields completed (workspace py_tr, `results/evolus/executions.jsonl`).

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
  failed: weaker evidence" and counted separately.
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

Step by step for a fresh Ubuntu server (Docker, clone, key, Caddy with HTTPS or plain HTTP, health check, restart,
how the live read is capped per visitor and per day): [deploy/DEPLOY.md](deploy/DEPLOY.md).

`deploy/deploy.sh user@IP [domain]` does the same from your machine: it installs Docker, copies the repo (never `.env`, `data/raw`, `cache`) and your
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
