# What ran on AMD

Short answer: **every model read in this repo.** Each form is one request to Gemma-4-31B-IT (and, as second
reader, Qwen3.8-27B) on AMD Token Factory, the organisers' hosted AMD GPU endpoint. The live button in the web
app sends a new request to the same endpoint.

## Standing workload

The live audit reads INE's public presidential tally sheets on AMD, one form at a time, and keeps a public counter of
reads on Home and at `/live`, computed from the worker's state (`app/live_status.py`).

## AMD evidence block

| | |
|---|---|
| Hardware | AMD GPUs behind the AMD Token Factory ([notebooks.amd.com/tokenfactory](https://notebooks.amd.com/tokenfactory)), which AMD describes as "GPU Accelerated AMD ROCm". The endpoint does not report the GPU model, so we name no card. |
| Model | Gemma-4-31B-IT, temperature 0, `max_tokens` 2000, one request per form: masked page + 6 zoomed tiles |
| Serving | hosted by AMD, OpenAI-compatible `/chat/completions` and `/usage`; client `twohands/amd.py` |
| Benchmark (our data) | `results/amd_benchmark.md`, from `scripts/amd_bench.py` (checked by `make eval`): n = 289 reads of the pre-registered 300, 2026-10-15T05:56:11Z to 2026-10-15T11:49:05Z UTC |
| Server time per form | 83.4 s mean, 70.7 s median (HTTP round trip of the answered request) |
| Tokens per form | 2,609 in (1843 of them image tokens), 804 out |
| Cost per form | $0.000144 billed (`usage.cost`), $0.14 per 1,000; about $24 for all 169,005 national forms |
| Reliability | 289 of 289 replies finished with `stop`; 126 failed HTTP attempts in the run window, each retried |
| Logged | every HTTP attempt with timestamp, status and round trip (`results/endpoint_health.jsonl`); every read with tokens and billed cost (`results/calls_*.jsonl`); the model catalogue snapshots (below) |
| What ran on AMD | every model read: Gemma (primary, the 300 and the 100-form confirmation), Qwen3.8-27B (second reader), the bake-off models (Amendment 6); the Evolus agent's model |

Server time per form: 83 s mean, 71 s median (HTTP round trip, shared endpoint, 289 reads of Gemma-4-31B-IT, 2,609 tokens in, 804 out).

Measured capacity (shared endpoint, 2026-10-17 00:48-01:03 UTC, queueing included, not GPU time): 4 in flight, 4.8 forms/minute, 32 s median, $0.000146/form; one shared key reads a state the size of Colima (982 sheets) in about 3.4 hours; national figures in results/throughput_sweep.json.

About $24 of AMD compute to read all 169,005 national presidential tally sheets with Gemma-4-31B-IT ($0.000144 per form, the mean billed cost of 289 reads).

The 300 run's 87 s per form was wall clock with fixed pacing (2 in flight), not GPU time; 83 s of it was the endpoint's round trip, queue included.

How Gemma is made to work here (the fixed image budget and tiling, the frozen prompt, the row-label check, the
`finish_reason` handling) and Gemma vs Qwen on the same forms: [GEMMA.md](GEMMA.md).

## Hardware and serving stack

| | |
|---|---|
| Infrastructure | **AMD Token Factory** (notebooks.amd.com/tokenfactory), the AMD-hosted inference service given to registered teams for this hackathon. Models run on AMD GPUs operated by the organisers. |
| GPU model | Not reported by the endpoint, so we do not claim a specific card. |
| API | OpenAI-compatible `/chat/completions` plus `/usage`. Client: `twohands/amd.py` (standard library only). |
| Primary model | **Gemma-4-31B-IT** (settings of the pre-registered run): temperature 0, `max_tokens` 2000, no `response_format` (images plus JSON mode broke Gemma on this endpoint, see `PROTOCOL.md` section 4). |
| Second model | **Qwen3.8-27B** (same): temperature 0, `reasoning_effort: "low"`, `max_tokens` 6000. |
| Input per request | One masked page plus zoomed tiles, each a JPEG (q88, longest side at most 2400 px). Pilot v2: page + 4 tiles. Pre-registered run: page + 6 tiles. |
| Output | One JSON object, 23 values, each with digits, words and the printed row label. |
| Pacing | Our own limit: 6 request starts per minute across processes, 2 in flight, 429 Retry-After honoured, `/usage` checked every 4 calls, pause at 0.80 USD daily spend. (The key's own limits: 20 req/min, 8 concurrent, $1/day; `app/live.py`.) |

## What runs on CPU

Page locating and masking (OpenCV on CPU), the gate (plain Python arithmetic), the sampler and
the web app run on an ordinary CPU host. They are cheap and deterministic. The AMD part is the part that needs a
large vision model: reading handwritten digits, handwritten words and printed row labels from phone photos.

## Pilot benchmark: 43 hand-picked tally forms on AMD Token Factory (measured)

Source: per-call `usage`, `cost` and wall-clock `secs` in the pilot result files
(`results/pilot/tally-witness/results_v2/gemma__*.json`, `results/pilot/tally-witness/results/qwen__*.json`; snapshot in
`app/data/spike_runs.json`). Means over 43 reads per model.

| Model | Mean latency per form | Tokens in / out | Cost per form | Per 1,000 forms | Forms accepted | Accepted fields wrong |
|---|---|---|---|---|---|---|
| Gemma-4-31B-IT (page + 4 tiles) | **49 s** | ~2,153 / 641 | **$0.000118** | **$0.12** | 21 / 43 | 0 / 462 |
| Qwen3.8-27B (page + 3 tiles) | 85 s | ~8,739 / 1,667 | $0.000507 | $0.51 | 22 / 43 | 0 / 484 |

- **Latency is wall-clock on a shared endpoint**, including queueing, not raw GPU time.
- **Throughput:** about 2 forms per minute, bounded by our 6 req/min, 2-in-flight pacing, not by the GPU
  ([sources/tally-witness-pilot.md](sources/tally-witness-pilot.md) section 3).
- **Reliability in the pilot:** all 86 Gemma calls finished with `stop` at 605-660 completion tokens, no parse
  failures; Qwen 43 of 43 `stop` ([sources/tally-witness-pilot.md](sources/tally-witness-pilot.md) section 3).
- **Total pilot spend:** about $0.031 for both models over 43 forms (same source).
- **Image budget:** Gemma receives a fixed ~265 tokens per image, Qwen ~1,800, which is why zoomed tiles
  matter for Gemma (same source).

Second form type, same model on the same endpoint: rainfall ledgers, whole sheet + 3 zoomed strips,
**$0.00011 per sheet** (spike, 40 sheets) (`ledger/ledger.json`, prices from `docs/sources/ledger-rescue-pilot.md, appendix`).

## Endpoint behaviour we saw (and logged)

- During the pre-registered run, 51 of the 300 forms had a first call fail during outages and were re-read later
  with the same frozen prompt; the last read counts (appendix of EVALUATION.md).
- From about 00:45 UTC on 2026-10-15, Gemma-4-31B-IT returned HTTP 503 on every call for a period
  (`results/verify_spike_gemma_try3_outage.jsonl`, `results/endpoint_health.jsonl`). The runner backs off and
  retries; a call that never succeeds routes its form to a person and counts against the accept rate.
- While the endpoint was degraded, re-reads of 5 pilot forms with the frozen prompt took 160 s and 477 s mean
  (two Gemma attempts) and 451 s (Qwen, 2 forms) (`results/verify_spike_*.jsonl`, shown on the app's results
  page).

### 2026-10-15 15:41 to 2026-10-16 02:06 UTC: Gemma-4-31B-IT unavailable on the endpoint

**Current state.** Gemma-4-31B-IT was unavailable on the AMD Token Factory from 2026-10-15 15:41 to 2026-10-16 02:06
UTC (our probe log, `results/endpoint_health.jsonl`); since then it serves again, with intermittent provider 500s on
vision requests that succeed on retry. Live reads use Gemma when it is listed, and fall back to Qwen3.8-27B otherwise;
every receipt names its reader.

- **What the log shows.** The first Gemma probe answering HTTP 400 is 2026-10-15 15:41:09 UTC; the first 200 after
  the gap is 2026-10-16 02:06:46 UTC. In between, `GET /models` listed `DeepSeek-V4.1-Flash, DeepSeek-V4-Flash,
  DeepSeek-V4-Flash-Vision-Exp, GLM-5.3-Flash, MiMo-V2.6-Flash, MinerU2.5-Pro, MiniCPM5-2B, MiniCPM-V-4.7-1B,
  MiniCPM-V-4.7-35B-A3B, Qwen3.8-27B, Qwen3.8-Flash-Next`, without Gemma, and a Gemma call answered HTTP 400:
  `{"error":{"message":"Requested model Gemma-4-31B-IT not supported","type":"invalid_request_error","param":null,"code":null}}`.
  The app reads those rows, and its own `kind: "models"` rows, as **withdrawn**, not as an outage. AMD acknowledged
  the Gemma issue on the lablab Discord on 2026-10-15 ([docs/sources/event-rules.md](sources/event-rules.md)).
- **Since it returned.** From 02:06 to 19:30 UTC on 2026-10-16 the log holds 1,009 Gemma read requests: 778 answered
  200, 190 answered a provider 500, the rest 400/502/504/429/timeouts. The runner backs off and retries; a form whose
  read never succeeds goes to a person and stays in the denominator.
- **Live demo.** The live read checks `GET /models` (cached 5 min, `app/livemodel.py`). While Gemma is not listed it
  reads with Qwen3.8-27B using Qwen's own frozen prompt and parameters from the 300 run (the core reader's `qwen`
  path: temperature 0, `reasoning_effort: "low"`, `max_tokens` 6000), and the live panel says so in a banner; the
  header chip shows "AMD live · Gemma unavailable". When Gemma is listed again the live read switches back by itself.
  Check of the fallback during the gap: one live read of masked form 201720E0100 with Qwen on AMD, 89.1 s, $0.000518
  (6,612 tokens in, 2,369 out), accepted by the gate.
- **Stored results are unchanged.** Every Gemma number of the pilot and the pre-registered 300 was read by Gemma on
  AMD before the gap.
- **The 100-form confirmation (PROTOCOL.md, Amendment 3) was read by Gemma after it returned** (2026-10-16 08:51 to
  11:06 UTC, `results/calls_confirm100_gemma.jsonl`): gate v2 accepted 22 forms, **0 of 484 accepted fields wrong**
  (Wilson 95% upper 0.79%), criterion met (`results/confirm100.md`).

## Pre-registered run on AMD: 300 forms (measured)

| | Gemma-4-31B-IT |
|---|---|
| Forms sent | 289 (11 pages not located, never sent) |
| Server time per form | **83.4 s** mean (HTTP round trip of the answered request; `results/amd_benchmark.md`) |
| Wall clock per form | 87.0 s (includes our limiter, 2 in flight) |
| Tokens in / out | ~2,609 / 804 (page + 6 tiles) |
| Cost per form | **$0.000144**, so $0.14 per 1,000 forms |
| `finish_reason` = stop | 289 of 289 |

Source: `results/calls_gemma.jsonl` (fields `latency_s`, `cost_usd`, `usage`, `finish_reason`; last read per form),
summarised in `app/data/headline.json` by `scripts/build_headline.py`. What it measured: the headline in
[EVALUATION.md](EVALUATION.md) (52 fields where the official capture does not match the paper, in 6,358).

## Cost at scale

- **About $24 of compute to audit all 169,005 forms** (national presidential tally sheets) with Gemma at the cost measured on the 300
  ($0.000144 x 169,005; form count from the PREP 2024 CSV); about $101 with Qwen at its cost on the 300 ($0.000597 per form; $86 at its
  pilot cost).
- **Time:** at the measured capacity of one shared key (4.8 forms a minute, 4 in flight), a state the size of Colima takes about 3.4 hours; national figures in `results/throughput_sweep.json`.
