# INE's 2024 acceptance metric, as we read it, on the pre-registered 300

*INE's 2024 acceptance metric as we read it from the report, computed on our existing reads after they were made; the definition was committed before computation; not the same test set or conditions as INE's trial.*

Built by `scripts/ine_metric.py`; `make eval` recomputes it (`--check`). No model call. Definition, committed before this computation: `results/ine_metric_DEFINITION.md`. Source of the metric: INE CCOE report, p. 5, https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/176400/ccoe-10se-26-08-2024-p17-1.pdf

Forms: 300 (Gemma reads usable on 289); 22 graded fields per form. Captures with no number: "Ilegible" 68, "Sin dato" 207 (count as not agreeing in the strict rows).

| Row | Result |
|---|---|
| **Primary: per field, words AND digits = the PREP capture, strict (all fields)** | **83.5% (5,508 of 6,600; Wilson 95% 82.5-84.3%)** |
| Words only = capture, strict | 84.6% (5,581 of 6,600; Wilson 95% 83.7-85.4%) |
| Digits only = capture, strict | 89.1% (5,879 of 6,600; Wilson 95% 88.3-89.8%) |
| Per field, conditional (usable read, capture is a number) | 90.5% (5,508 of 6,087; Wilson 95% 89.7-91.2%) |
| Per acta, strict (all 22 fields agree) | 32.7% (98 of 300; Wilson 95% 27.6-38.2%) |
| Per field vs the paper where adjudicated, strict | 84.0% (5,547 of 6,600; Wilson 95% 83.1-84.9%) |

The reference here is the official capture, which itself has errors (52 confirmed on the 300), so a model that reads the paper right can still count as not agreeing. This is a different measure from the accepted-set result, shown beside it: 0 wrong of 1,958 accepted fields (two readers, `results/two_reader_300.md`).

## Line

> 83.5% of fields agree in words and digits (5,508 of 6,600). INE's 2024 acceptance metric as we read it from the report, computed on our existing reads after they were made; the definition was committed before computation; not the same test set or conditions as INE's trial.
