# The cost of the problem, from INE's own 2024 files

Built by `scripts/national_counts.py`; `make eval` recomputes it (`--check`). No model call. Presidential file; "Ilegible" counted on every captured row, the comparison with the certified count on TIPO_ACTA 2. Sources: data/raw/prep/PRES_2024.csv (PREP 2024 final cut, https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip); data/raw/computos/PRES_2024.csv (Cómputos Distritales 2024, presidential).

| Measure | Value |
|---|---|
| Captured actas in the PREP | 162,517 |
| Fields recorded "Ilegible" (vote, count and total fields) | 28,607 on 6,009 actas |
| Not recounted (certified count by cotejo), captured | 52,167 |
| of which the PREP capture and the certified count differ on at least one vote field | **3,382 (6.5%)** |
| fields: numbers that differ | 12,326 |
| fields: "Ilegible" in the PREP, non-zero in the count | 2,356 |
| fields: "Sin dato" in the PREP, non-zero in the count | 1,459 |

A difference says two captures disagree, not which one is right; the photo does. The preliminary count is preliminary by design; the certified count is the official result. No party, no totals, no outcome.

## Line

> On the 52,167 polling stations that were not recounted, INE's two official records of the same paper, the preliminary capture and the certified count, disagree on at least one vote field in 3,382 (6.5%).
