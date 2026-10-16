# Practice sheet: one live read of a SYNTHETIC fill (demonstration, not a measurement)

**SYNTHETIC.** No person filled this sheet and no camera took this photo. The blank sheet is the PNG preview at
screen resolution (`static/sheet/two-hands-sheet.png`, 150 dpi); the amounts were drawn in code
(`scripts/practice_demo.py`) with a script font (Segoe Print) in blue, as Czech number words plus digits, then the
page was put on a simulated table, turned 4 degrees, warped in perspective, unevenly lit, blurred and JPEG-compressed
as a stand-in for a phone photo. A real hand-filled sheet (Czech and English) will be photographed later.

Filled values (truth): rows [12, 7, 23, 5, 18, 40, 9, 31, 14, 66], TOTAL 225; words: dvanáct, sedm, dvacet tři, pět,
osmnáct, čtyřicet, devět, třicet jedna, čtrnáct, šedesát šest; TOTAL dvě stě dvacet pět. Every row's words equal its
digits and the rows sum to TOTAL, so the correct verdict is **accepted**.

## Registration (no model call)

The same synthetic sheet as simulated phone photos, through `app.practice.register_photo` (the core blob finder and
frame search with a portrait normalisation, the sheet's orientation template, in-plane rotations tried up to 40
degrees). "corr" is the correlation of the straightened page with the filled sheet.

| photo | result | turned back (deg) | corr | secs |
|---|---|---|---|---|
| straight | registered | 0.0 | 0.947 | 0.24 |
| turned 4° | registered | 0.0 | 0.945 | 0.38 |
| turned -9° | registered | 0.0 | 0.948 | 0.23 |
| turned 15° | registered | 8.0 | 0.934 | 1.12 |
| turned -25° | registered | -16.0 | 0.754 | 3.23 |
| landscape (90°) | registered | 0.0 | 0.928 | 0.2 |
| upside down | registered | 0.0 | 0.907 | 0.21 |

Registration of the live-read photo: corner markers + orientation template, score 0.636, margin 0.505.

## The one live read

- When: 2026-10-16T11:33:42+00:00 (UTC). Model: **Gemma-4-31B-IT** (listed in GET /models: True). One read, as allowed;
  not retried.
- Result: **no answer.** The AMD endpoint returned HTTP 500 on both attempts of the read's short retry budget
  (10.2 s, then 146.2 s; `results/endpoint_health.jsonl`, kind "live", 11:31:01Z and 11:33:33Z) while the Senate
  run chain was reading on the same endpoint. Error: `GaveUp: gave up after 2 attempts`; 170.7 s; no usage billed.
- Gate: `no parseable read` -> **routed to a person**, not accepted. Fail-closed as designed, but this is not a
  read of the words: **the synthetic live read did not happen.**
- To repeat it when the endpoint is quiet: `python scripts/practice_demo.py --live` (one read; writes
  `results/practice_sheet_demo.json`, then update this file).

## What the gate guarantees here (verified in code and tests)

- Accepted only if every row's words were read and equal its digits, and rows 1 to 10 sum to TOTAL
  (`app.builder.gate_schema`: the frozen core gate `twohands/gate.py`, unchanged, plus `words_required` from
  `schemas/practice_sheet.yaml`). `tests/test_practice_sheet.py`.
- A row whose words come back null (a language or a hand the model cannot read) routes, with the row named; no row is
  accepted on its digits alone.
- Not guaranteed: if the model ignores the instruction and copies the digits into the words, a row can pass on one
  reading. The prompt forbids it; the gate cannot detect it. So we do not claim the gate never shows a wrong
  accepted number.
