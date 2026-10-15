# Two Hands: the model reads, the paper decides

**Touchless capture of self-checking paper forms.** An open vision model on AMD GPUs reads every field. A
deterministic gate then applies the form's own arithmetic: amounts in words must equal amounts in digits, rows
must sum to the printed total, sections must agree. A form that passes every check is accepted with no human
touch. Anything else goes to a person, with the failing field named.

- **Demo:** {{DEMO_URL}}
- **Video (3-4 min):** {{VIDEO_URL}}
- **Repo:** {{REPO_URL}}
- **Slides:** [`slides/slides.md`](slides/slides.md) (Marp source of the PDF)

## Headline numbers

Measured on real public forms: Mexico's 2024 polling-station tally sheets (INE), graded against the official
double-keyed capture of the same image. Every disagreement on an accepted form was checked by eye on the image.

| | Pre-registered random sample, n = 300 | Pilot, n = 43 (trouble-enriched) |
|---|---|---|
| Forms accepted with no human touch | {{RUN300_ACCEPT_RATE}} ({{RUN300_ACCEPTED}} of 300) | **49%** (21 of 43) |
| Fields wrong on accepted forms | {{RUN300_ACC_WRONG}} of {{RUN300_ACC_FIELDS}} | **0 of 462** |
| Keying errors found in the official capture | {{RUN300_KEYING_ERRORS}} | **6 fields on 5 accepted forms** |

- Reader: Gemma-4-31B-IT on AMD, one request per form (masked page + zoomed tiles), temperature 0.
- Pilot keying errors: on 5 accepted forms, 6 fields where the image shows the official capture mis-keyed. The
  certified count covers 5 of them and matches the image on all 5.
- The pilot was chosen to be difficult, so 49% is a lower bound for an ordinary day. The second reader
  (Qwen3.8-27B) accepted 22 of 43 with 0 of 484 accepted fields wrong.
- The 300-form run is pre-registered: sample, prompt, gate and metrics were committed (`PROTOCOL.md`, commit
  `a93294c`) before any model read; Amendment 1 (a better page locator, commit `b0e443c`) was also committed
  before any model read. The new locator was tuned on a fresh calibration set (143 of 150 pages located and
  correctly aligned). On the 300: 289 located, 11 routed to a person before any model call.
  Details: [docs/EVALUATION.md](docs/EVALUATION.md).
- Every number has a source file: [docs/NUMBERS.md](docs/NUMBERS.md).

## What ran on AMD

| | |
|---|---|
| Hardware | AMD GPUs behind **AMD Token Factory**, the organisers' hosted AMD inference endpoint (OpenAI-compatible) |
| Primary reader | **Gemma-4-31B-IT**, temperature 0, one request per form |
| Second reader | **Qwen3.8-27B**, reasoning effort low, on every form |
| Benchmark (43 forms, measured) | Gemma: **49 s** mean latency, **$0.000118** per form, ~2,153 tokens in / 641 out. Qwen: 85 s, $0.000507, ~8,739 / 1,667 |
| Throughput | ~2 forms/min under our 6 req/min, 2-in-flight pacing on the shared endpoint |
| Cost | **$0.12 per 1,000 forms** (Gemma); $20 to $86 to audit all 169,005 national tally forms |
| Not on AMD | page locating and masking (OpenCV, CPU), the gate (plain Python), the web app |

Full detail and the raw result files: [docs/AMD.md](docs/AMD.md).

## Run it

```bash
pip install -r requirements.txt
python run_app.py                       # http://127.0.0.1:8000
```

The app serves the measured reads from the result files in this repo. No API key is needed to browse. The
"Read live on AMD" button needs `AMD_KEY` and `AMD_BASE_URL` in the environment (never committed).

Tests (436 pass, 2 skipped on our machine):

```bash
python -m pytest -q
```

Reproduce the pre-registered run (needs the AMD key; resumable):

```bash
python -m twohands.run --models gemma,qwen --max-daily-usd 0.80
```

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

## Evaluation at a glance

- **Business result.** 21 of 43 pilot forms needed no keying, 0 of their 462 fields were wrong, and on those
  same forms the official double-keyed capture had 6 keying errors.
- **Known limitation.** The pilot is small (43 forms) and chosen to be difficult. Crop positions were tuned by
  hand. Only disagreements on accepted forms were eye-checked. The shared endpoint paces us to about 2 forms a
  minute; a national run needs a dedicated AMD endpoint.
- **Failure case.** On a rainfall ledger read as one image, Gemma shifted a whole row of values one year to the
  left. Every shifted column still summed to its total, so the checksum accepted 26 wrong cells (of 870
  accepted). Zoomed tiles removed it; on the tally sheet we added the row-label check so a shifted row cannot
  pass.
- **Safeguard.** Accept only when every identity holds; everything else goes to a person with the field named.
  Privacy mask before storage or model call. Fail closed when the page cannot be located.

Full write-up: [docs/EVALUATION.md](docs/EVALUATION.md).

## Who pays for this

Today the status quo is **double keying**: two people type every form, a third resolves mismatches. Mexico's
2024 national capture programme that does this cost **MXN 273.6M**. About **32 state-level counts in 2027** each
run the same double-keyed capture under their own contract (one 2024 state contract: MXN 24.94M). Two Hands
replaces the second keyer on forms the paper accepts, for about $0.12 per 1,000 forms of AMD compute, and in
audit mode lists the first keyer's errors with the image as proof.

The same gate fits any form that checks itself: clinical-trial case report forms, census and survey sheets,
archive rescue.

**Why not plain OCR, why an LLM.** Classic OCR fails on this handwriting; that is why Rainfall Rescue used
16,000 volunteers (we did not run an OCR baseline ourselves). One vision model reads digits, words and row
labels from phone photos with no per-form training. It never decides: the paper's arithmetic does.

**Competition.** Double keying copies the paper faithfully but cannot say which paper is wrong; 19.2% of
nationally captured tally forms (26,336 of 137,196) fail their own row sum in the official capture. One state
institute piloted AI recognition on 264 polling stations' forms in 2024. Handwriting tools such as Transkribus
transcribe tables; none we found gives a per-form proof of when to trust the read.

## Data, credit and framing

- **Tally sheets:** INE PREP 2024 (prep2024.ine.mx) and certified Cómputos Distritales 2024
  (computos2024.ine.mx), consulted 2026-10-14, reused under INE's free-use terms (Libre-Uso-MX). This is an
  independent demonstration of clerical capture quality. **It is not an official INE product** and does not
  represent INE or any government. Vote rows are shown as "Option 01" to "Option 15"; no party is named,
  compared or totalled. "Keying error" means a typing mistake in the capture, nothing more.
- **Personal data:** the names-and-signatures column is masked before any image is stored or sent to a model.
  Only masked pages are in this repo.
- **Rainfall ledgers:** Rainfall Rescue (Hawkins et al., Geoscience Data Journal 2022;
  github.com/ed-hawkins/rainfall-rescue; Met Office scans). Sheet images are **linked, not redistributed**; only
  our extracted values are stored.

## Evolus

The same process runs as a case on **Evolus** (Evolus Business Agents track): an Evolus **document extractor** reads
the masked page as an independent third reader (its read is gated and compared, never trusted blindly); accepted
forms are filed in an Evolus **knowledge library** (the office's register); routed forms get a clerk's note drafted
by an Evolus **agent running on Gemma-4-31B-IT on AMD**, translated to Spanish by the **AI Tool** `translate`, and
are handed to a person by the Evolus **workflow** "Review hand-off". Our gate is exposed as `POST /api/gate` so an
Evolus agent can check the paper's arithmetic. The form page and the review desk show each form's Evolus case: run
id, steps and status. Endpoints, setup clicks and limits: [docs/EVOLUS.md](docs/EVOLUS.md).

```bash
python -m evolus check            # which blocks are configured (keys shown only as set / not set)
python -m evolus run --pick 2,3   # run the case on 2 accepted + 3 routed forms -> results/evolus_runs.jsonl
```

Environment: `EVOLUS_KEY`, `EVOLUS_APP_ID`, `EVOLUS_AGENT`, `EVOLUS_EXTRACTOR_AGENT_ID`, `EVOLUS_EXTRACTOR_ID`,
`EVOLUS_LIBRARY_ID`, `EVOLUS_WORKFLOW_ID`; optional `TWOHANDS_GATE_TOKEN`, `TWOHANDS_PUBLIC_URL`,
`EVOLUS_CALLBACK_KEY`.

## Run with Docker

```bash
docker compose up --build         # http://localhost:8000
```

The image is `python:3.13-slim` with OpenCV headless and runs as a non-root user. Keys are read at run time from an
untracked `.env` next to `docker-compose.yml` (`AMD_KEY`, `AMD_BASE_URL`, the Evolus variables above); `.env` is
excluded from the image by `.dockerignore`. `data/masked` and `results` are mounted read-only; `app/state` (review
desk, live reads, Evolus callbacks) is a writable volume. Without a `.env` the app still serves every measured
result. Note: inside the container the live-read rate limiter uses its own file (`app/state/ratelimit.json`), so it
does not see a batch run on the host.

## Repo map

| Path | What |
|---|---|
| `twohands/` | core: sample, locate + mask, reader, AMD client + rate limiter, gate, runner |
| `schemas/` | the form type: layout, privacy mask, fields, identities |
| `app/`, `templates/`, `static/` | FastAPI web app: viewer, review desk, audit gallery, results, live read |
| `ledger/` | the rainfall-ledger snapshot (second form type) |
| `results/` | manifest, prepare log, run log, every raw model call |
| `PROTOCOL.md` | the pre-registered protocol for the 300-form run, with Amendment 1 |
| `tests/` | gate, mask, rate limiter, app routes, privacy and neutrality tests |
| `evolus/` | Evolus integration: REST client, the intake case, gate endpoint, CLI (`python -m evolus`) |

MIT licence. API keys live only in the environment or an untracked `.env`.
