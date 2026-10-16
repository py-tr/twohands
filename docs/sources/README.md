# Sources copied into the repo

Every citation in this repo can be followed from the repo alone. Material that lived outside it is either linked at
its public URL or copied here with its origin.

| File | What | Origin |
|---|---|---|
| [event-rules.md](event-rules.md) | the hackathon rules, Evolus track requirements and organiser statements we cite | public lablab.ai / Evolus pages (URLs inside) and the lablab Discord (date and author role per quote) |
| [tally-witness-pilot.md](tally-witness-pilot.md) | the 43-form tally-sheet pilot of 2026-10-14: data sources and INE licence terms (§1), sample (§2), results (§3), paper discrepancies (§4), context and buyers (§5) | the builder's pilot write-up, copied 2026-10-16 |
| [ledger-rescue-pilot.md](ledger-rescue-pilot.md) | the 40-sheet rainfall-ledger pilot of 2026-10-14, with the cost formula | the builder's pilot write-up, copied 2026-10-16 |

The pilots' data files (JSON and CSV, with SHA-256) are in [`data/pilot/`](../../data/pilot/SOURCES.md).

The pre-registered protocol files (`PROTOCOL*.md`) are append-only and are not edited after commit. Where they name
`../spikes/tally-witness/data/sample.json` (the 43 pilot forms excluded from the draws), the same file is committed as
[`data/pilot/tally-witness/sample.json`](../../data/pilot/tally-witness/sample.json) (same SHA-256, listed in
`data/pilot/SOURCES.md`). Frozen result files that carry the old path as a label (`results/manifest_senado100.json`)
are left as written.
