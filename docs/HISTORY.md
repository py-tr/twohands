# Commit history note

On 2026-10-17, before the repository was made public, its history was rewritten once to drop outreach drafts that held personal contact details and to replace an author email with the GitHub no-reply address. File contents and the author and committer dates of every commit are unchanged (check any pair below with `git log -1 --format='%aI %cI' <hash>`); every commit hash changed. The original history is kept as a git bundle and is available to the organisers on request. `PROTOCOL.md` is append-only, so it still cites the original hashes. Every commit that touched a protocol file maps as follows (commit times in CEST, as committed):

| Original | Now | Committed | What |
|---|---|---|---|
| `a93294c` | `f85ca1f` | 2026-10-15 03:09 | Pre-register the 300-acta held-out run: protocol, manifest, frozen reader and gate |
| `b0e443c` | `ddfabe9` | 2026-10-15 03:29 | Protocol Amendment 1: landmark-checked page locator, before any model read |
| `6bef8e0` | `56fe2e1` | 2026-10-15 12:36 | Protocol Amendment 2: secondary analyses, before any Qwen read or adjudication |
| `62f40cd` | `693451b` | 2026-10-15 15:36 | Protocol Amendment 3: fresh 100-form confirmation draw (seed 20261017) for gate v2, before |
| `365eb56` | `5fccfb7` | 2026-10-15 16:11 | CORD receipt-label audit: pre-registration only (record; not run, no model call) |
| `7a55b7a` | `c4e429b` | 2026-10-15 21:24 | Senate acta as a third measured form type: schema, sampler, 100-form manifest, PROTOCOL_SE |
| `971bce2` | `1dd100a` | 2026-10-16 01:53 | Amendment 6: open-model bake-off on AMD pre-registered (readers by probe, fixed stratified |
| `6466d49` | `31e393a` | 2026-10-16 02:13 | Amendment 6 probe record and plan: 2 new compatible readers, caps fixed before any bake-of |
| `e1b41c1` | `b23109b` | 2026-10-16 02:34 | Amendment 6 deviation 1: budget on billed cost (timed-out calls are billed), 900 s call ti |
| `a5d75b7` | `f234ea1` | 2026-10-16 02:40 | PROTOCOL_IEEBCS: head-to-head on Baja California Sur's own 2024 PREP, pre-registered befor |
| `1710737` | `f846122` | 2026-10-16 02:51 | PROTOCOL_IEEBCS: pre-register the placement threshold before any read |
| `86f8b76` | `1be8ce1` | 2026-10-16 02:55 | Amendment 6 deviation 2: DeepSeek-V4.1-Flash halted (billed, unanswered calls); its cap to |
| `062ad61` | `96c0e98` | 2026-10-16 03:13 | PROTOCOL Amendment 7: gate v3 (ballot-stock check), before any v3 read |
| `6517f8c` | `e520725` | 2026-10-16 10:57 | PROTOCOL_IEEBCS: plumbing check and strict-denominator rule, before any read |
| `e123586` | `77f6025` | 2026-10-16 16:57 | PROTOCOL Amendment 8 (two Gemma reads as the two hands on the 300; tiling ablation) and 8b |

The full old-to-new map is [commit-map.txt](commit-map.txt). `make eval` checks the pre-registration order from the commit dates, which the rewrite kept, and checks that every commit a document cites exists, directly or through this map.
