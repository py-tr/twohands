# Two Hands: receipts for every number keyed from paper

Every number typed from a paper form, checked against the photo of that paper, with the photo as proof. A vision
model on AMD reads the form; the form's own arithmetic decides what to trust; every dispute arrives with its crop.

Measured on a pre-registered random sample of 300 handwritten tally sheets from Mexico's 2024 count, graded against
the official double-keyed capture: the model found 52 fields where the capture does not match the paper, 22 of
them confirmed by the certified count. Errors we did not plant, in a record we did not write, in a sample drawn
before any model read.

Who pays: auditors who already check the count's system, trial monitors who verify source data against charts,
internal audit of keyed files. By hand, checking numbers against paper does not pay. Here it costs $0.14 to $0.65
of AMD compute per 1,000 forms, offered at $100 per 1,000 audited. A state's count is about 1,000 to 21,000 forms
(one per polling station), so one state audit is about $100 to $2,100.

Others check the model against the source. We check the record against the paper.

**Live demo:** add at submission · **Video:** add at submission ·
**Audit report sample:** add at submission (in the repo: [the 52, each with its crop](results/adjudication/SUMMARY.md)) ·
**How to reproduce:** [`make eval`](#reproduce-every-number)

| 52 | 1 in 605 | 1 in 5 |
|---|---|---|
| fields where the official capture does not match the paper, each with its photo | fields wrong on the 18% of forms the paper's gate accepts with no person | disputed fields is a confirmed capture error (52 of 267) |

**Alone, the model mis-keys about 1 field in 37; the official two-person capture typed a wrong number in 1 field in 374. That is why the model never decides. The paper does, and a person sees the rest.**

![Option 07 on form 050815B0100: the words say "ciento setenta y cinco", the boxes say 1 7 5](slides/receipt_050815B0100.jpg)

*Form 050815B0100, Option 07 (masked page, cropped right of the logo column). The paper says 175, the first
capture keyed 75, the certified count says 175. One of the 52.*

## Contents

1. [Who pays](#who-pays)
2. [Headline: the pre-registered 300](#headline-the-pre-registered-300)
3. [What ran on AMD](#what-ran-on-amd)
4. [Run it](#run-it) · [Reproduce every number](#reproduce-every-number)
5. [Audit your capture](#audit-your-capture)
6. [How it works](#how-it-works)
7. [Limits and failure cases](#limits-and-failure-cases)
8. [Business detail](#business-detail)
9. [Data, credit and framing](#data-credit-and-framing)
10. [Evolus](#evolus) · [Docker](#run-with-docker) · [Deploy](#deploy) · [Repo map](#repo-map)

## Who pays

| | |
|---|---|
| **Buyer** | Now: the outside auditors of Mexico's preliminary count (PREP), mostly universities. Next, not measured: clinical-trial monitors, internal audit of keyed loan and claim files |
| **Price** | Proposal: $100 per 1,000 forms audited, two readers and the report included |
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
| Forms the gate accepts with no person | 55 of 300 (18%): **2 of 1,210 fields wrong, about 1 in 605** |
| Yield of a disputed field | 1 in 5 disputed fields is a confirmed capture error (52 of 267). The capture's overall error rate is at least 1 in 122 (52 of 6,358 found so far). More than ten times the yield of a random check. |
| Recall | On the forms the certified count settled by comparison, it differs from the first capture on 23 fields; judged on the paper, 16 of them are council corrections or blank rows (the paper shows the capture's value), and the model disputed 7 of the other 7 (measured recall 100%, Wilson 95% 65% to 100%; small n). |

The first capture is preliminary by design; the certified count is the official result.

Every number above is computed by `scripts/build_headline.py` into `app/data/headline.json`, which the web app
reads. Details: [docs/EVALUATION.md](docs/EVALUATION.md). Sources: [docs/NUMBERS.md](docs/NUMBERS.md). Every
verdict and crop: [`results/adjudication/`](results/adjudication/SUMMARY.md).

## What ran on AMD

| | |
|---|---|
| Hardware | AMD GPUs behind **AMD Token Factory**, the organisers' hosted AMD inference endpoint (OpenAI-compatible) |
| Primary reader | **Gemma-4-31B-IT**, temperature 0, one request per form; every measured read of the 300 |
| Second reader | **Qwen3.8-27B**, reasoning effort low, on every form |
| Measured on the 300 | Gemma: **87 s** mean latency on the shared endpoint, **$0.000144** per form, ~2,609 tokens in / 804 out, 289 of 289 replies `stop` |
| Pilot (43 forms) | Gemma 49 s, $0.000118 per form; Qwen 85 s, $0.000507 per form |
| Throughput | ~2 forms/min under our 6 req/min, 2-in-flight pacing on the shared endpoint |
| Cost | **$0.14 per 1,000 forms** (Gemma); $20 to $86 compute cost to audit all 169,005 forms (Gemma, Qwen) |
| Live reads | Gemma-4-31B-IT was withdrawn from AMD Token Factory on 2026-10-15; live reads in the app now fall back to Qwen on AMD, with a banner |
| Not on AMD | page locating and masking (OpenCV, CPU), the gate (plain Python), the web app |

Full detail and the raw result files: [docs/AMD.md](docs/AMD.md). How Gemma is made to work here, and Gemma vs
Qwen on the same forms: [docs/GEMMA.md](docs/GEMMA.md).

## Run it

```bash
pip install -r requirements.txt
python run_app.py                       # http://127.0.0.1:8000
python -m pytest -q                     # tests
```

The app serves the measured reads from the result files in this repo. No API key is needed to browse. The
"Read live on AMD" button needs `AMD_KEY` and `AMD_BASE_URL` in the environment (never committed).

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
- **One reader, one adjudicator.** The adjudicator is an AI agent working on published crops, which anyone can
  re-check. Recall is only bounded (7 of 7, small n).
- **Row-label check.** It is costly: it routed 86 forms, and on 68 of them the read matched the paper on every
  field (all 15 routed for a label alone).
- **Not independent.** In one call the model can harmonise words and digits, so one read is not two independent
  reads. The fix is separate reads or a second reader.
- **Pages not located.** 11 of the 300 went to a person before any model call.
- **Speed.** The shared endpoint paces us to about 2 forms a minute.
- **Failure case.** On a rainfall ledger read as one image, Gemma shifted a whole row of values one year to the
  left. Every shifted column still summed to its total, so the checksum accepted 26 wrong cells (of 870
  accepted). Zoomed tiles removed it (0 of 3,976 accepted cells wrong; spike, 40 sheets). On the tally sheet we
  added the row-label check so a shifted row cannot pass.
- **Safeguard.** Accept only when every identity holds; everything else goes to a person with the field named.
  Privacy mask before storage or model call. Fail closed when the page cannot be located.

Full write-up, including the 43-form pilot: [docs/EVALUATION.md](docs/EVALUATION.md).

## Business detail

- **Buyer, now.** Reglamento de Elecciones art. 347: every state institute has its PREP audited by an outside body,
  preferably academic. In February 2024, 26 of 32 institutes had named one, all universities or research centres
  ([INE annex](https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf)).
  The audit covers the computer system; we add the field-by-field check against the paper.
- **Next window.** The federal election and 32 concurrent local processes, election day 6 June 2027
  ([INE](https://centralelectoral.ine.mx/2026/07/30/perfila-ine-organizar-el-proceso-electoral-federal-y-32-concurrentes-2026-2027/)).
- **Size of one job.** The 2024 PREP file has about 1,000 (Colima) to 21,000 (Estado de México) presidential
  tally sheets per state, median about 4,200.
- **Yield (measured).** 1 in 5 disputed fields is a capture error, against at least 1 in 122 at random; a person
  checks 1 field in 24; the strong-evidence tier is right 12 of 18 times.
- **Price (proposal).** $100 per 1,000 forms audited, two readers and the report included. Measured AMD compute:
  $0.14 per 1,000 (Gemma) plus $0.51 (Qwen, pilot).
- **Next markets, not measured.** Clinical-trial source-data verification (site monitoring and source document
  verification: 15-30% of trial costs, [Lindblad et al., Clinical Trials 2014](https://www.acepidemiology.org/assets/docs/Ball%20Clinical%20Trials%202014.pdf));
  internal audit of keyed loan and claim files.
- **Competition.** OCR and IDP platforms (Tesseract, ABBYY, Rossum, Hypatos, UiPath, Textract, Document AI)
  extract; none says it audits an existing capture with a crop per finding.
- **Why double keying is not enough.** It copies the paper faithfully but cannot say which paper is wrong: 19.2% of
  nationally captured tally forms (26,336 of 137,196) fail their own row sum. Table in
  [docs/BUSINESS.md](docs/BUSINESS.md#3-competitive-analysis).

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

The same process runs as a case on **Evolus** (Evolus Business Agents track). The masked page is the input, and an
open model on AMD reasons over it.

- **Accepted form:** starts the workflow **"Record filing"**. A deterministic Script re-checks the paper's
  identities inside Evolus and files the record.
- **Routed form:** starts the workflow **"Review hand-off"**. The agent **"Intake clerk"** (an open model on the
  AMD Token Factory, connected under "Your models") writes the review task, the AI Tool `translate` turns it into
  Spanish, and the task reaches a person on our review desk.
- **Third reader:** an Evolus extractor ("Tally sheet reader"), gated and compared, never trusted blindly.

The form page and the review desk show each form's Evolus run: id, steps and status. Details, endpoints and the
real run: [docs/EVOLUS.md](docs/EVOLUS.md).

```bash
python -m evolus setup            # find or create every Evolus block (idempotent) -> evolus/ids.json
python -m evolus run --pick 2,3   # run the case on 2 accepted + 3 routed forms -> results/evolus_runs.jsonl
```

Environment: `EVOLUS_KEY`, `EVOLUS_APP_ID`; optional `EVOLUS_USER_KEY` (needed to create the extractor schema and
the library), `EVOLUS_REVIEWER_EMAIL`, `TWOHANDS_GATE_TOKEN`, `TWOHANDS_PUBLIC_URL`, `EVOLUS_CALLBACK_KEY`.

## Run with Docker

```bash
docker compose up --build         # http://localhost:8000
```

The image is `python:3.13-slim` with OpenCV headless and runs as a non-root user. Keys are read at run time from an
untracked `.env` next to `docker-compose.yml` (`AMD_KEY`, `AMD_BASE_URL`, the Evolus variables above); `.env` is
excluded from the image by `.dockerignore`.

`data/masked` and `results` are mounted read-only; `app/state` (review desk, live reads, Evolus callbacks) is a
writable volume. Without a `.env` the app still serves every measured result. Inside the container the live-read
rate limiter uses its own file (`app/state/ratelimit.json`), so it does not see a batch run on the host.

## Deploy

`deploy/deploy.sh user@IP [domain]` installs Docker, copies the repo (never `.env`, `data/raw`, `cache`) and your
`.env` (scp, mode 600), and starts the app behind Caddy: HTTPS for a domain, plain HTTP on the IP otherwise;
variables in `deploy/.env.prod.example`.

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
| `PROTOCOL.md` | the pre-registered protocol for the 300-form run, with Amendments 1-3 |
| `scripts/build_headline.py` | computes every headline number into `app/data/headline.json` (+ adjudication SUMMARY, RECALL) |
| `submission/lablab.md` | the submission page text |
| `tests/` | gate, mask, rate limiter, app routes, privacy and neutrality tests |
| `evolus/` | Evolus integration: REST client, the intake case, gate endpoint, CLI (`python -m evolus`) |

MIT licence. API keys live only in the environment or an untracked `.env`.
