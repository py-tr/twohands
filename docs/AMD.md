# What ran on AMD

Short answer: **every model read in this repo.** Each form is one request to Gemma-4-31B-IT (and, as second
reader, Qwen3.8-27B) on AMD Token Factory, the organisers' hosted AMD GPU endpoint. The live button in the web
app sends a new request to the same endpoint.

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

## Benchmark: 43 tally forms on AMD Token Factory (measured)

Source: per-call `usage`, `cost` and wall-clock `secs` in the pilot result files
(`spikes/tally-witness/results_v2/gemma__*.json`, `spikes/tally-witness/results/qwen__*.json`; snapshot in
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
**$0.00011 per sheet** over 40 sheets (`ledger/ledger.json`, prices from `spikes/ledger-rescue/evaluate.py`).

## Endpoint behaviour we saw (and logged)

- From about 00:45 UTC on 2026-10-15, Gemma-4-31B-IT returned HTTP 503 on every call for a period
  (`results/verify_spike_gemma_try3_outage.jsonl`, `results/endpoint_health.jsonl`). The runner backs off and
  retries; a call that never succeeds routes its form to a person and counts against the accept rate.
- While the endpoint was degraded, re-reads of 5 pilot forms with the frozen prompt took 160 s and 477 s mean
  (two Gemma attempts) and 451 s (Qwen, 2 forms) (`results/verify_spike_*.jsonl`, shown on the app's results
  page). We report these as they are.

## Pre-registered run on AMD (in progress)

| | Gemma-4-31B-IT | Qwen3.8-27B |
|---|---|---|
| Forms sent | {{RUN300_GEMMA_CALLS}} | {{RUN300_QWEN_CALLS}} |
| Mean latency | {{RUN300_GEMMA_LATENCY}} | {{RUN300_QWEN_LATENCY}} |
| Cost per form | {{RUN300_GEMMA_COST_PER_FORM}} | {{RUN300_QWEN_COST_PER_FORM}} |
| `finish_reason` = stop | {{RUN300_GEMMA_STOP}} | {{RUN300_QWEN_STOP}} |

Source when filled: `results/calls_gemma.jsonl`, `results/calls_qwen.jsonl` (fields `latency_s`, `cost_usd`,
`usage`, `finish_reason`).

## Cost at scale

- **Audit all 169,005 national presidential tally forms:** $20 (Gemma) to $86 (Qwen) of AMD compute
  (cost per form x 169,005; form count from the PREP 2024 CSV).
- **Time on the shared endpoint:** at about 2 forms a minute, about 59 days (`spikes/tally-witness/README.md`
  section 3). That pacing is a property of a shared hackathon key. A production run would use a dedicated AMD
  Instinct endpoint; we have not measured one, so we give no number for it.
