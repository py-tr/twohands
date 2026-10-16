# Commit history note

On 2026-10-17, before the repository was made public, its history was rewritten once to drop draft files not meant for publication and to replace an author email with the GitHub no-reply address. File contents and commit dates are unchanged; every commit hash changed. `PROTOCOL.md` is append-only, so it still cites the original hashes. They map as follows:

| Cited as | What | Commit now |
|---|---|---|
| `a93294c` | Protocol and the 300 manifest | `f85ca1f` |
| `b0e443c` | Amendment 1 (locator) | `ddfabe9` |
| `6bef8e0` | Amendment 2 (secondary analyses) | `56fe2e1` |
| `62f40cd` | Amendment 3 (confirmation draw) | `693451b` |
| `365eb56` | PROTOCOL_CORD.md | `5fccfb7` |
| `971bce2` | Amendment 6 (bake-off) | `1dd100a` |

The full old-to-new map is [commit-map.txt](commit-map.txt). `make eval` checks the pre-registration order from the commit dates, which the rewrite kept.
