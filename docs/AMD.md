# What ran on AMD

Short answer: **every model read in this repo.** Each form is one request to Gemma-4-31B-IT (and, as second
reader, Qwen3.8-27B) on AMD Token Factory, the organisers' hosted AMD GPU endpoint. The live button in the web
app sends a new request to the same endpoint.

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

## What did not run on AMD

Honest boundary: page locating and masking (OpenCV on CPU), the gate (plain Python arithmetic), the sampler and
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
  (`spikes/tally-witness/README.md` section 3).
- **Reliability in the pilot:** all 86 Gemma calls finished with `stop` at 605-660 completion tokens, no parse
  failures; Qwen 43 of 43 `stop` (`spikes/tally-witness/README.md` section 3).
- **Total pilot spend:** about $0.031 for both models over 43 forms (same source).
- **Image budget:** Gemma receives a fixed ~265 tokens per image, Qwen ~1,800, which is why zoomed tiles
  matter for Gemma (same source).

Second form type, same model on the same endpoint: rainfall ledgers, whole sheet + 3 zoomed strips,
**$0.00011 per sheet** (spike, 40 sheets) (`ledger/ledger.json`, prices from `spikes/ledger-rescue/evaluate.py`).

## Endpoint behaviour we saw (and logged)

- During the pre-registered run, 51 of the 300 forms had a first call fail during outages and were re-read later
  with the same frozen prompt; the last read counts (appendix of EVALUATION.md).
- From about 00:45 UTC on 2026-10-15, Gemma-4-31B-IT returned HTTP 503 on every call for a period
  (`results/verify_spike_gemma_try3_outage.jsonl`, `results/endpoint_health.jsonl`). The runner backs off and
  retries; a call that never succeeds routes its form to a person and counts against the accept rate.
- While the endpoint was degraded, re-reads of 5 pilot forms with the frozen prompt took 160 s and 477 s mean
  (two Gemma attempts) and 451 s (Qwen, 2 forms) (`results/verify_spike_*.jsonl`, shown on the app's results
  page). We report these as they are.

### 2026-10-15 ~15:41 UTC: Gemma-4-31B-IT withdrawn from the endpoint

- **What happened.** Since about 15:41 UTC on 2026-10-15, AMD Token Factory no longer offers Gemma-4-31B-IT.
  `GET /models` (17:35 UTC) lists `DeepSeek-V4.1-Flash, DeepSeek-V4-Flash, DeepSeek-V4-Flash-Vision-Exp,
  GLM-5.3-Flash, MiMo-V2.6-Flash, MinerU2.5-Pro, MiniCPM5-2B, MiniCPM-V-4.7-1B, MiniCPM-V-4.7-35B-A3B, Qwen3.8-27B,
  Qwen3.8-Flash-Next`, without Gemma. A Gemma call answers HTTP 400:
  `{"error":{"message":"Requested model Gemma-4-31B-IT not supported","type":"invalid_request_error","param":null,"code":null}}`.
  The health probe logs it as status 400 on every Gemma probe since then (`results/endpoint_health.jsonl`); the app
  reads those rows, and its own `kind: "models"` rows, as **withdrawn**, not as an outage. Qwen3.8-27B still answers.
- **Live demo.** The live read checks `GET /models` (cached 5 min, `app/livemodel.py`). While Gemma is not listed it
  reads with Qwen3.8-27B using Qwen's own frozen prompt and parameters from the 300 run (the core reader's `qwen`
  path: temperature 0, `reasoning_effort: "low"`, `max_tokens` 6000), and the live panel says so in a banner; the
  header chip shows "AMD live · Gemma unavailable". When Gemma is listed again the live read switches back by itself.
  Check after the switch: one live read of masked form 201720E0100 with Qwen on AMD, 89.1 s, $0.000518
  (6,612 tokens in, 2,369 out), accepted by the gate.
- **Stored results are unchanged.** Every Gemma number in this repo (pilot and the pre-registered 300) was read by
  Gemma on AMD before the withdrawal.
- **The 100-form confirmation (PROTOCOL.md, Amendment 3) specifies Gemma first.** We do not substitute Qwen for
  Gemma in it. It waits for Gemma to return to the endpoint; if Gemma does not return before the deadline, it is
  reported as **not run**.

## Pre-registered run on AMD: 300 forms (measured)

| | Gemma-4-31B-IT |
|---|---|
| Forms sent | 289 (11 pages not located, never sent) |
| Mean latency per form | **87 s** (wall clock on the shared endpoint, including queueing) |
| Tokens in / out | ~2,609 / 804 (page + 6 tiles) |
| Cost per form | **$0.000144**, so $0.14 per 1,000 forms |
| `finish_reason` = stop | 289 of 289 |

Source: `results/calls_gemma.jsonl` (fields `latency_s`, `cost_usd`, `usage`, `finish_reason`; last read per form),
summarised in `app/data/headline.json` by `scripts/build_headline.py`. What it measured: the headline in
[EVALUATION.md](EVALUATION.md) (52 fields where the official capture does not match the paper, in 6,358).

## Cost at scale

- **$20 to $86 compute cost to audit all 169,005 forms** (national presidential tally sheets): about $24 compute cost with Gemma at the cost measured on the 300
  ($0.000144 x 169,005; form count from the PREP 2024 CSV); about $86 compute cost with Qwen at its pilot cost.
- **Time on the shared endpoint:** at about 2 forms a minute, about 59 days (`spikes/tally-witness/README.md`
  section 3). That pacing is a property of a shared hackathon key. A production run would use a dedicated AMD
  Instinct endpoint; we have not measured one, so we give no number for it.
