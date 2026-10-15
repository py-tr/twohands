# Recall: how many capture errors does the model dispute?

Secondary analysis (Amendment 2), computed by `scripts/build_headline.py`. No model call.

Forms: the 100 of the 289 read forms whose certified count (Computos Distritales 2024) was settled by comparison with the tally sheet (OBSERVACIONES "Cotejo"), not by a recount of the ballots.
Fields: 17 vote rows + TOTAL (TOTAL compared with the certified calculated total). E = fields where the certified value differs from the first capture (PREP, including fields PREP marked Ilegible or left without data). C = how many of those E the model disputed (its digits differ from PREP).

## 1. The loose bound

> On the forms the certified count settled without a recount, the model had disputed 7 of the 23 fields where the certified count disagrees with the first capture (30%, Wilson 95% 16% to 51%).

That denominator includes council corrections and the blank = 0 convention, which a faithful read of the paper cannot dispute, so it is a loose lower bound on recall.

## 2. Tightened: every undisputed field judged on the paper

Each of the 16 undisputed fields was cropped from the masked page and judged from what is written. Paper shows the capture's value (a council correction or blank = 0, not a capture error): **16**. Paper shows the certified value (a capture error the model missed): **0**.

> Dropping the 16 corrections, the model disputed 7 of the 7 remaining fields: measured recall 100% (Wilson 95% 65% to 100%).

Small n. The 7 disputed fields were themselves adjudicated: model_right 1, paper_ambiguous 6. Only the model_right ones are confirmed capture errors; the paper_ambiguous ones are fields where the paper itself does not settle the value, so the measured recall says the model missed no capture error here, not that each of these was one.

| clave | field | PREP | certified | model | disputed | verdict / paper shows | evidence |
|---|---|---|---|---|---|---|---|
| 050815B0100 | Option 07 | 75 | 175 | 175 | yes | model_right |  |
| 112879B0100 | Option 09 | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
| 112879B0100 | Option 10 | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
| 112879B0100 | Option 11 | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
| 112879B0100 | Option 15 | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
| 112879B0100 | Unregistered candidates | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
| 112747C0100 | Option 15 | 3 | 0 | 3 | no | paper shows the capture's value | words "tres", boxes 0 0 3 = the capture; certified 0 |
| 112747C0100 | TOTAL | 379 | 376 | 379 | no | paper shows the capture's value | words "trescientos setenta y nueve", boxes 3 7 9 = the capture; certified calculated total 376 |
| 120867B0100 | Option 04 | 153 | 151 | 151 | yes | paper_ambiguous |  |
| 131324C0200 | Null votes | 0 | 15 | 15 | yes | paper_ambiguous |  |
| 153906C0300 | TOTAL | 458 | 451 | 458 | no | paper shows the capture's value | words "Cuatrocientos cincuenta y ocho", boxes 4 5 8 = the capture; certified calculated total 451 |
| 153717B0100 | Unregistered candidates | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper; captured as no data, certified 0 |
| 150512C0100 | TOTAL | 340 | 345 | 340 | no | paper shows the capture's value | words "trecientos cuarenta", boxes 3 4 0 = the capture; certified calculated total 345 |
| 251701B0100 | Option 01 | Ilegible | 31 | 31 | yes | paper_ambiguous |  |
| 251701B0100 | Option 06 | Ilegible | 8 | 68 | yes | paper_ambiguous |  |
| 251701B0100 | Option 07 | Ilegible | 149 | 189 | yes | paper_ambiguous |  |
| 251701B0100 | Null votes | Ilegible | 6 | 67 | yes | paper_ambiguous |  |
| 251701B0100 | TOTAL | 301 | 299 | 301 | no | paper shows the capture's value | words "trecientos uno", boxes 3 0 1 = the capture; certified calculated total 299 |
| 253749C0100 | Option 09 | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
| 253749C0100 | Option 10 | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
| 253749C0100 | Option 11 | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
| 253749C0100 | Option 13 | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
| 253749C0100 | Unregistered candidates | Sin dato | 0 | None | no | paper shows the capture's value | row left blank on the paper (no words, empty boxes); captured as no data, certified 0 |
