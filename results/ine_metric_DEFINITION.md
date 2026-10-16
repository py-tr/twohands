# INE's 2024 acceptance metric, as we read it: the definition, committed before any computation

Status: written and committed **before** `scripts/ine_metric.py` exists and before any number below is computed.
No model call: the computation uses reads that already exist. **Stopping rule: the result is published whatever it
shows** (above, at or below 80%), on the site and in `results/ine_metric.md`, with the label in section 6. No change
to this definition after the first computation; any later variant is labelled post-hoc.

## 1. The source, quoted

INE, UTSI, *PREP PEF 2023-2024. Informe de las actividades realizadas relativas al servicio de "Captura
Automática"*, presented to the CCOE, 10th session, 26 Aug 2024:
<https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/176400/ccoe-10se-26-08-2024-p17-1.pdf>
(page numbers are the document's own "N de 10"; text read from the PDF on 2026-10-16).

Page 5:

> "el 29 de enero de 2024 se llevó a cabo una prueba de concepto a partir de una muestra de 2500 imágenes de
> segmentos de actas. [...] Los resultados obtenidos por parte de la ESIME alcanzaron un nivel de coincidencia en el
> reconocimiento de las cifras en letra en un 83%, en tanto que en número alcanzó un 90% de coincidencia. Ahora
> bien, considerando aquellos casos en los que el resultado fue coincidente tanto en letra como número, alcanzo
> solamente el 75%. Se debe precisar que, para evaluar los resultados de los participantes, se utilizó un set de
> datos en el cual el Instituto conocía el valor correcto que debía obtenerse en la prueba realizada."

> "el porcentaje mínimo de confiabilidad establecido siempre ha sido del 80%, por lo que el resultado de 75%
> obtenido por la ESIME, no se encontraba dentro de los parámetros requeridos por el Instituto."

Page 7 (COTAPREP minute): the providers were evaluated on "reconocimiento tanto en letra como en número;
reconocimiento sólo en letra y reconocimiento sólo en número".

## 2. Our reading of the unit and the rule

- **Unit: one field (one quantity).** INE's test items were "imágenes de segmentos de actas" (p. 5); a segment
  ("trozo") is the crop of one quantity, written in words (letra) and digits (número). Our equivalent is one
  captured field of one acta. **Primary = per field.** The report does not define a per-acta rate; we add one as a
  **secondary** (an acta counts only if all its graded fields agree), because a buyer keys whole actas.
- **Rule: words AND digits.** A field agrees only if **the words read and the digits read both equal the
  reference value** ("coincidente tanto en letra como número", p. 5). We also report words-only and digits-only
  agreement, INE's other two criteria (p. 7), as secondary rows.
- **Reference value.** INE used a set where it "conocía el valor correcto". We have no such set for words; our
  reference is **the official PREP capture** of the same acta (`app/data/audit_sample_prep300.csv`). Primary =
  vs the PREP capture. Secondary = vs the paper where a committed adjudication verdict read the paper
  (`results/adjudication/verdicts.json`; verdict model_right / capture_right / neither), else the capture
  (PROTOCOL.md section 6 rule). Undecided verdicts count as not agreeing in the secondary.

## 3. The data

- Forms: the pre-registered 300 (`results/manifest.json`, PROTOCOL.md), the full draw, nothing excluded.
- Reads: the existing Gemma-4-31B-IT reads, `results/calls_gemma.jsonl`, last row per form (the same rows every
  other 300 number uses). Fields `n` (digits) and `w` (words). No new read, no re-run.
- Graded fields: the 22 schema fields that have a PREP column (`schema` fields with `csv`; the derived
  PERSONAS_Y_REP has no capture and is excluded). So 300 x 22 = **6,600 fields** in the strict denominator.

## 4. Denominators and what counts as not agreeing (strict first)

**Primary (strict, all fields):** denominator = all 6,600 fields. A field agrees iff the PREP capture is a number
AND Gemma's digits = it AND Gemma's words = it. Everything else counts as **not agreeing**:
- a form whose read failed or whose page was not located (no usable read): all 22 fields;
- a field Gemma left unread in digits or in words (null);
- a field the PREP captured as "Ilegible" or "Sin dato" (no number to agree with), whatever Gemma read.

**Secondary rows**, each labelled:
1. words-only and digits-only agreement, same strict denominator;
2. conditional per field: denominator = fields on usable reads whose capture is a number;
3. per acta, strict: actas (of 300) whose 22 graded fields all agree;
4. vs the paper (section 2), strict denominator.

## 5. What this is not

Not INE's test set (2,500 segments, Jan 2024), not its images, not its conditions (we read whole pages, then
compare per field), not run by INE, and the reads were made before this definition (the definition was fixed
before the computation, not before the reads). It is never described as passing or failing INE's test, and it is
always shown beside, never instead of, the accepted-set result (0 wrong of 1,958), and never in the same sentence
as the 2024 entrant's 75%.

## 6. The label (verbatim, wherever the number appears)

"INE's 2024 acceptance metric as we read it from the report, computed on our existing reads after they were made;
the definition was committed before computation; not the same test set or conditions as INE's trial."

Output: `scripts/ine_metric.py` -> `results/ine_metric.md` and `app/data/ine_metric.json`, checked by `make eval`.
