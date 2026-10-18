# Commit history note

On 2026-10-17, before the repository was made public, its history was cleaned: drafts and working notes that held personal or internal details were removed, and author emails were replaced with the GitHub no-reply address. File contents and the author and committer dates of every commit are unchanged (check any pair below with `git log -1 --format='%aI %cI' <hash>`); every commit hash changed. The original history is kept as a git bundle and is available to the organisers on request. `PROTOCOL.md` is append-only, so it still cites the original hashes. Every commit that touched a protocol file maps as follows (commit times in CEST, as committed):

| Original | Now | Committed | What |
|---|---|---|---|
| `a93294c` | `ae103dd` | 2026-10-15 03:09 | Pre-register the 300-acta held-out run: protocol, manifest, frozen reader and gate |
| `b0e443c` | `6081edf` | 2026-10-15 03:29 | Protocol Amendment 1: landmark-checked page locator, before any model read |
| `6bef8e0` | `54dd69a` | 2026-10-15 12:36 | Protocol Amendment 2: secondary analyses, before any Qwen read or adjudication |
| `62f40cd` | `f790f6f` | 2026-10-15 15:36 | Protocol Amendment 3: fresh 100-form confirmation draw (seed 20261017) for gate v2, before |
| `365eb56` | `28940df` | 2026-10-15 16:11 | CORD receipt-label audit: pre-registration only (record; not run, no model call) |
| `7a55b7a` | `2ae73e3` | 2026-10-15 21:24 | Senate acta as a third measured form type: schema, sampler, 100-form manifest, PROTOCOL_SE |
| `971bce2` | `1f5ad2f` | 2026-10-16 01:53 | Amendment 6: open-model bake-off on AMD pre-registered (readers by probe, fixed stratified |
| `6466d49` | `1a121b6` | 2026-10-16 02:13 | Amendment 6 probe record and plan: 2 new compatible readers, caps fixed before any bake-of |
| `e1b41c1` | `9284182` | 2026-10-16 02:34 | Amendment 6 deviation 1: budget on billed cost (timed-out calls are billed), 900 s call ti |
| `a5d75b7` | `369222b` | 2026-10-16 02:40 | PROTOCOL_IEEBCS: head-to-head on Baja California Sur's own 2024 PREP, pre-registered befor |
| `1710737` | `dcbc933` | 2026-10-16 02:51 | PROTOCOL_IEEBCS: pre-register the placement threshold before any read |
| `86f8b76` | `077cf28` | 2026-10-16 02:55 | Amendment 6 deviation 2: DeepSeek-V4.1-Flash halted (billed, unanswered calls); its cap to |
| `062ad61` | `1d56495` | 2026-10-16 03:13 | PROTOCOL Amendment 7: gate v3 (ballot-stock check), before any v3 read |
| `6517f8c` | `b0b652c` | 2026-10-16 10:57 | PROTOCOL_IEEBCS: plumbing check and strict-denominator rule, before any read |
| `e123586` | `37e2d51` | 2026-10-16 16:57 | PROTOCOL Amendment 8 (two Gemma reads as the two hands on the 300; tiling ablation) and 8b |

The full old-to-new map is [commit-map.txt](commit-map.txt). `make eval` checks the pre-registration order from the commit dates, which the rewrite kept, and checks that every commit a document cites exists, directly or through this map.
