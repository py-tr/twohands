# Recall bound: how many capture errors does the model dispute?

**A bound, not a measurement.** Secondary analysis (Amendment 2), computed by `scripts/build_headline.py`.

Forms: the 100 of the 289 read forms whose certified count (Computos Distritales 2024) was settled by comparison with the tally sheet (OBSERVACIONES "Cotejo"), not by a recount of the ballots.
Fields: 17 vote rows + TOTAL (TOTAL compared with the certified calculated total). E = fields where the certified value differs from the first capture (PREP, including fields PREP marked Ilegible or left without data). C = how many of those E the model disputed (its digits differ from PREP).

> On the forms the certified count settled without a recount, the model had disputed 7 of the 23 fields where the certified count disagrees with the first capture (30%, Wilson 95% 16% to 51%).

Why only a bound: a certified value can differ from the first capture for reasons other than a keying error (the district council can correct a sheet during the comparison, and TOTAL is compared with the certified CALCULATED total, which differs from the written total whenever the paper's rows do not add up). E is therefore an upper bound on the keying errors among these fields, and C/E a lower bound on the share the model would surface.

| clave | field | PREP | certified | model | disputed | verdict |
|---|---|---|---|---|---|---|
| 050815B0100 | Option 07 | 75 | 175 | 175 | yes | model_right |
| 112879B0100 | Option 09 | Sin dato | 0 | None | no | - |
| 112879B0100 | Option 10 | Sin dato | 0 | None | no | - |
| 112879B0100 | Option 11 | Sin dato | 0 | None | no | - |
| 112879B0100 | Option 15 | Sin dato | 0 | None | no | - |
| 112879B0100 | Unregistered candidates | Sin dato | 0 | None | no | - |
| 112747C0100 | Option 15 | 3 | 0 | 3 | no | - |
| 112747C0100 | TOTAL | 379 | 376 | 379 | no | - |
| 120867B0100 | Option 04 | 153 | 151 | 151 | yes | paper_ambiguous |
| 131324C0200 | Null votes | 0 | 15 | 15 | yes | paper_ambiguous |
| 153906C0300 | TOTAL | 458 | 451 | 458 | no | - |
| 153717B0100 | Unregistered candidates | Sin dato | 0 | None | no | - |
| 150512C0100 | TOTAL | 340 | 345 | 340 | no | - |
| 251701B0100 | Option 01 | Ilegible | 31 | 31 | yes | paper_ambiguous |
| 251701B0100 | Option 06 | Ilegible | 8 | 68 | yes | paper_ambiguous |
| 251701B0100 | Option 07 | Ilegible | 149 | 189 | yes | paper_ambiguous |
| 251701B0100 | Null votes | Ilegible | 6 | 67 | yes | paper_ambiguous |
| 251701B0100 | TOTAL | 301 | 299 | 301 | no | - |
| 253749C0100 | Option 09 | Sin dato | 0 | None | no | - |
| 253749C0100 | Option 10 | Sin dato | 0 | None | no | - |
| 253749C0100 | Option 11 | Sin dato | 0 | None | no | - |
| 253749C0100 | Option 13 | Sin dato | 0 | None | no | - |
| 253749C0100 | Unregistered candidates | Sin dato | 0 | None | no | - |
