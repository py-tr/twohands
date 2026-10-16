> **DRY RUN of the self-hosting kit, 2026-10-15, served by the AMD Token Factory: NOT a measurement on an MI300X.** No self-hosted run exists; every "MI300X" / "self-hosted" label in this file is the template the kit would fill on a real box.

## Amendment 4.1 ([date] [hh:mm] UTC, before any read of the 100-form confirmation set): arm B

As Amendment 4 provides, the 43-form image-budget ablation (post-hoc, pilot forms only;
`results/resolution_43_<date>.json`) ran first and chose arm B by the rule stated there.
**Arm B = `tiles_560`: page + 6 tiles at 560 soft tokens/image.** Request: the page + 6 tiles with the frozen prompt (sha256 unchanged), temperature 0, `max_tokens` 2000, and per request
`mm_processor_kwargs` = `{"max_soft_tokens": 560}`. Tiling: 6 tiles.
Arm B reads the same 100 forms (the same 97 located pages) as arm A, on the same server; output
`results/armb_confirm100_gemma.jsonl`. Arm A (the original settings) remains the confirmation of gate v2
and the primary; arm B is reported beside it, whatever it shows, with the same list, never pooled with A.
The AMD Token Factory runs Gemma at a fixed image budget, so the 300's numbers and the public live read use that budget; the higher budget was measured on our self-hosted MI300X.
