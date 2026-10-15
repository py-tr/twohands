# Run log (pre-registered run, PROTOCOL.md)

- Protocol commit: `a93294cc1a4ea61043d979ca353a2a353de95fdb` (2026-10-15 ~01:08 UTC), committed before any of the 300 actas was read.
- Manifest sha256: `605af97756662abb2a27c35cf04075b1963ab50438bc710f7eab2b9ab706e081` (300 actas: 196 Movil, 104 Escaner; 0 replaced).
- Prompt sha256: `3664253035b912184e24a205852e7b8e686f0abb36a4340e91834d60dc71193f`.
- Started: 2026-10-15T01:09:13Z, `python -u -m twohands.run --models gemma,qwen --max-daily-usd 0.80` (detached; PID 55456).
  Resume after any stop with the same command; finished rows are skipped.
- Endpoint state at start: Gemma-4-31B-IT answering HTTP 503 since ~00:45 UTC; the runner backs off and retries.

## Deviations
- 2026-10-15 ~01:15 UTC: run stopped (PID 55456 killed) before any successful model read, because the original
  locator left 52 of 300 not located. PROTOCOL.md Amendment 1 replaces the locator; all 300 are re-prepared.
  The original locator's prepare log is kept as `results/prepare_original_locator.jsonl`.
