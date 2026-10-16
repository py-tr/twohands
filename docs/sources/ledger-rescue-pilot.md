> **Source copy.** Pilot write-up "Ledger Rescue" of 2026-10-14 (40 rainfall-ledger sheets), copied from the
> builder's working folder (spikes/ledger-rescue/README.md, outside this repo and not published) on 2026-10-16, verbatim
> except that the internal hackathon self-scoring line and the spike's file list are removed. Its data files are
> committed under [`data/pilot/`](../../data/pilot/SOURCES.md) and [`ledger/`](../../ledger/).

# Ledger Rescue: kill-claim spike (2026-10-14, 17:24 to 19:00 UTC)

**Kill-claim:** on sheets the checksum accepts, Gemma agrees with the volunteers on at least 98% of cells, and the gate accepts at least 60% of sheets.

**Result:** the claim **passes at the year-column level** and **fails at the sheet level**, and it passes only once the image is tiled. Read as one image, Gemma gets 79% of cells right and the claim is dead. Read as the whole sheet plus three zoomed strips, it gets 96.8% right. Its own checksum then accepts 81.6% of year-columns, and on those it matches the volunteers on **3,976 of 3,976 cells (100%; the 95% upper bound on error is about 0.08%)**. Only 25% of whole sheets pass, because a single bad column rejects the sheet.

## 1. Licence and data
- **GitHub repo** (ed-hawkins/rainfall-rescue): it has no LICENSE file, and the GitHub API reports `license: null`. The README says: *"Data made openly available from the RainfallRescue.org project which involved more than 16,000 citizen scientist volunteers transcribing >65,000 pages…"*
- **Zenodo** (10.5281/zenodo.5770390, v2.1.0, 2025-09-09): the licence field reads **`cc-by-4.0`**. Zenodo's GitHub integration can set this field on its own, but it is the record's formal licence.
- **Paper** (Hawkins et al., Geoscience Data Journal 2022): *"This is an open access article under the terms of the Creative Commons Attribution License, which permits use, distribution and reproduction in any medium, provided the original work is properly cited."* Its data statement says: *"The data is available at https://doi.org/10.5281/zenodo.5770389."*
- **Met Office Digital Archive** (the original scans): the page footer links **"Open Government Licence"** and says *"Provided by the National Meteorological Library and Archive – open to everyone"*. I found no licence statement specific to the scans, so OGL v3 is likely but unconfirmed.
- **Zooniverse** (edh/rainfall-rescue): state `finished`, with 17,467 classifiers and 3,717,745 classifications.
- **Programmatic images: yes.** `DATA/<STATION>/<STATION>.pdf` downloads from raw.githubusercontent. Each page is an embedded JPEG of about 670x1080 px, in chronological order, and lines up 1:1 with that station's source CSVs (year headers checked on all 40 sheets). Zooniverse subject JPGs (about 1250x1930 px) are also public through the Panoptes API. My mapping from their filenames to ALLSHEETS CSVs was wrong (it matched a different station), so that experiment is **discarded**.
- **Checksum: yes.** Every sheet has a printed TOTALS row with the clerk's handwritten annual total, and the volunteers transcribed it. With the volunteers' values, 374 of 380 year-columns (98.4%) and 34 of 40 sheets balance to 0.01". Volunteers needed **16 days, about 16,000 people, about 100M keystrokes, 4 transcriptions per value** (from the paper).

## 2. Sample
40 sheets from 5 stations: Ardnamurchan Lighthouse, Balcombe Gables, Balcombe Highley Manor, Barkby Hall and Barrowford Res. The stations were drawn at random from the first 1,000 DATA folders, and the sheets span 1850 to 1960. Each sheet has at least 36 filled cells, 4,915 graded cells in all. Ground truth is the volunteers' source CSV. Cells marked -999 (accumulated values) are excluded. Exact match means within 0.005 inches.

## 3. Accuracy table
| Reader | Sheets | Cell exact | Columns accepted by checksum | Accuracy on accepted columns | Sheets accepted (accuracy) | USD/sheet |
|---|---|---|---|---|---|---|
| Gemma-4-31B, single image | 40 | 79.2% | 17.6% | 97.0% (a column-shift error got through) | 0% | $0.00008 |
| **Gemma-4-31B, tiled (1 + 3 strips)** | 40 | **96.8%** | **80.5%** | **100.0%** (3,976/3,976) | 25% (100%) | **$0.00011** |
| Gemma tiled + one re-read of failing columns | 40 | 96.9% | **81.6%** | 100.0% | 25% | +$0.00002 |
| Qwen3.8-27B (low reasoning), single image | 21 | 87.5% | 32.2% | 99.3% | 4.8% | $0.00024 |
| MiniCPM-V-4.7-35B-A3B, single image | 22 | 39.3% | 1.4% | 87% | 0% | $0.00008 |
| Ceiling (volunteer values) | 40 | - | 98.4% | - | 85% | - |

**Two-model agreement:** where Gemma (single image) and Qwen agree, precision is 98.7% at 75% coverage. Tiled Gemma with Qwen gives 99.2% at 87% coverage. All three models agreeing gives 99.4%, but at only 32% coverage. On the 21 shared sheets, "agree AND balance" is 100% precise at 28% coverage. Agreement is **worse** than the arithmetic gate: two models make the same column-shift error together, and the sum check covers more cells.

**Re-reads:** at single-image resolution, re-reading 50 failing columns fixed 1 and made cell accuracy worse (78.9% to 72.2%). With tiles, 4 of 40 failing columns came back balanced and fully correct. The remaining failures are true misreads (2 of the columns could never balance, because the clerk's own sum is off).

**Why tiling matters:** the endpoint gives every image a fixed budget of about 280 tokens. A 2x upscale got the same 565 prompt tokens and no gain (75.2% vs 74.6% on 8 sheets). Four images in one request gives about 1,400 prompt tokens.

## 4. Three example failures
1. **Silent column shift (single image).** On Balcombe Gables 1880s, Gemma put the 1887 values under 1886, and so on along the row. Each moved column still balances, so the checksum **accepted 26 wrong cells**. Tiling fixed it. This is the one failure the arithmetic gate cannot catch, so a year-header and neighbour-station check is needed.
2. **Leading-dot decimals.** On Ardnamurchan in 1873, "·38" was read as 3.82 and "·61" as 6.13, even with tiles. The sum check catches these.
3. **Dropped 11th column.** The 1920-1930 sheets have 11 years. Tiled Gemma returned 10 and dropped 1930. The check passes because the column is missing rather than wrong, so missing columns need a coverage check.

Baseline: Tesseract and other classic OCR are **not installed**, and I did not install them (writes were restricted to this folder). The paper's own reason for using volunteers is that classic OCR fails on this handwriting.

## 5. Cost and throughput
Tiled Gemma costs about $0.00011 per sheet, so the whole corpus of about 66k sheets would cost about $7. The whole spike spent **$0.0195** (207k tokens in, 175k out). Effective throughput was only about 3 sheets/min (2 concurrent calls at 30-60 s each). At that rate the corpus takes about 15 days on Token Factory, which is no faster than the volunteers. "Overnight" needs a self-hosted MI300X batch.

## 6. Verdict
**The kill-claim survives at the column level.** Tiled Gemma with a per-year checksum auto-accepts about 81% of year-columns with zero errors against the volunteers in 3,976 cells. The other ~19% goes to a human queue, about 2 columns per sheet instead of 10 columns keyed 4 times each. Measured as written per sheet, it fails (25% < 60%). Caveats: n = 40 sheets from 5 A-B stations, a single run, and crop fractions tuned by hand. Qwen and MiniCPM were not tiled.

**Buyer, bluntly:** this corpus is already transcribed. The value is in the next archives: other national met services' ledgers, C3S/WMO data-rescue programmes and I-DARE. Those are grant-funded with small budgets and are not a daily process. Reinsurers and flood modellers buy finished long series from met services; they do not buy a transcription tool.

## Appendix: the cost formula (excerpt of the spike's `evaluate.py`)

The dollar figures above (and `ledger/build.py`, "price_per_token") use the Token Factory prices in effect during the
spike, USD per token:

```python
usd = round(S["tok_in"] * 3.5e-8 + S["tok_out"] * 7e-8, 5)
```

`S["tok_in"]` / `S["tok_out"]` are the summed `usage.prompt_tokens` / `usage.completion_tokens` of the reads.
