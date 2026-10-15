# Business case

Two Hands audits a capture that already exists. You give us the keyed data and the scans. We give you the few
fields where the keyed value and the paper disagree, each with its photo, ordered by evidence.

Every number here is either **measured** (we cite the file in this repo) or **cited** (we fetched the source and
link it). Anything beyond elections is labelled **next market, not measured**.

## 1. The buyer and the trigger

### Now: Mexico's outside audit of every preliminary count

- **The rule.** Reglamento de Elecciones art. 347 says each electoral institute must submit the computer system of
  its preliminary-results programme (PREP) to an audit and designate an outside auditor (numeral 1). Preference
  goes to academic or research institutions, and the auditor is named at least four months before election day
  (numeral 2). Source: the art. 347 citations in IEEH Hidalgo agreement
  [IEEH/CG/022/2024](https://ieehidalgo.org.mx/images/sesiones/2024/Febrero/IEEH-CG-022-2024.pdf), points 9 to 14.
- **The buyers already exist.** INE's annex "Entes auditores para los Procesos Electorales Locales 2023-2024"
  (February 2024) lists all 32 state institutes. 26 had named an auditor, and every one of the 26 is a university,
  technological institute or research centre (UNAM centres for Aguascalientes, Mexico City, Hidalgo, Puebla,
  Querétaro and Veracruz; Tec de Monterrey campuses for nine states; CINVESTAV, CIMAT, state universities and
  technological institutes for the rest). The other 6 were still choosing.
  [INE annex 5, CCOE session 23-02-2024](https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/ccoe-1so-23-02-2024-p19-a5.pdf).
- **The gap we fill.** Art. 347 audits the computer system. It does not check the keyed numbers against the paper,
  field by field. Two Hands is that field-level check, sold to the auditor who is already contracted. Checking captured fields against the paper is our addition to the auditor's scope, not a legal requirement.
  No institute has asked for it yet.
- **The next window.** INE is organising the federal election and **32 concurrent local processes** for 2026-2027
  ([INE Central Electoral, 30 July 2026](https://centralelectoral.ine.mx/2026/07/30/perfila-ine-organizar-el-proceso-electoral-federal-y-32-concurrentes-2026-2027/)).
  Election day is **6 June 2027**, with local deputies elected in 31 states
  ([INE Central Electoral, 31 July 2026](https://centralelectoral.ine.mx/2026/07/31/planeara-y-organizara-ine-mas-de-500-actividades-del-proceso-electoral-federal-2026%E2%80%912027/)).
  Under numeral 2, auditors must be named by early February 2027 at the latest. That is the sales deadline.

### Next market, not measured: source-data verification in clinical trials

Site monitoring and source document verification account for **15% to 30% of clinical trial costs** (Lindblad,
Manukyan, Purohit-Sheth, Gensler, Okwesili, Meeker-O'Connell, Ball, Marler, *Clinical Trials* 2014; 11: 205-217,
[PDF](https://www.acepidemiology.org/assets/docs/Ball%20Clinical%20Trials%202014.pdf)). Source-data verification is
the same job as ours: compare the keyed case-report data with the source page. We have not run a case-report form.

### Next market, not measured: internal audit of keyed files

Loan files, insurance claims, registries, survey returns. Any file that was keyed from paper and still has the
scans. We have not measured any of these.

## 2. The product and the price

### What the auditor receives

The audit report (`/audit/{id}/report`, built by `app/audit_web.py` and `templates/audit_report.html`):

- the headline "N fields checked, D disputed, each with its photo";
- the method (model digits and words, the paper's own identities);
- every disputed field, with its crop, the keyed value, the model's digits and words, ordered by evidence (strong,
  medium, weak), a "confirmed / not an error" mark and a CSV export.

### What it yields (measured, pre-registered random sample of 300 forms)

| | Value | Source |
|---|---|---|
| Fields checked | 6,358 on 289 read forms | `app/data/headline.json`, `results/adjudication/SUMMARY.md` |
| Fields disputed | 267 (4.2%): **a person checks 1 field in 24 instead of every field** | the same |
| Disputed fields that are capture errors | 52 of 267, **1 in 5** | the same |
| Capture error rate at random | at least 52 of 6,358, **1 in 122** | the same |
| Strong-evidence tier | **12 of 18** are capture errors; medium 27 of 80; weak 13 of 169 | sample audit (`POST /api/audit/sample`, `order_check`); rule in `app/capture_audit.py` |
| The model alone | wrong on 173 of 6,358 fields, **1 in 37** | `results/adjudication/SUMMARY.md` |

Read the strong tier first: two of every three are real.

### Cost and proposed price

| | Per form | Per 1,000 forms | Source |
|---|---|---|---|
| AMD compute, Gemma-4-31B-IT (measured) | $0.000144 | **$0.14** | mean over 289 reads, `results/calls_gemma.jsonl` |
| AMD compute, second reader Qwen3.8-27B (measured, pilot) | $0.000507 | $0.51 | 43 pilot reads, `docs/NUMBERS.md` A2 |
| **Proposed price, two readers, report included** | **$0.10** | **$100** | proposal |

Compute with both readers is about $0.65 per 1,000 forms, under 1% of the proposed price. Hosting, support and
sales are not measured and are not in that figure. For scale only: auditing all 169,005 forms of the 2024 national presidential capture
(PREP 2024 CSV, `docs/NUMBERS.md` B) is $20 to $86 compute cost and would bill about $16,900.

For a sense of the market price of machine reading, cloud form extraction lists at $30 per 1,000 pages (Google
Document AI Form Parser, first tier, [pricing](https://cloud.google.com/document-ai/pricing)) and $70 per 1,000
pages (AWS Textract, tables + forms + queries, US West, [pricing](https://aws.amazon.com/textract/pricing/)). Those
products extract; they do not audit an existing capture.

We found no citable rate for a person keying or verifying a field, so we do not price the manual alternative. We
state it as work: **a person checks 1 field in 24 instead of every field**, and 12 of the first 18 they open (the strong tier) are
capture errors.

**Revenue, honestly.** Elections are lumpy: one season every few years, and each set is small at this price. They
are the proof market: public, audited, with a named buyer and a deadline. Sustainable revenue has to come from
keyed files that are audited every month (trials, claims, loans). That is next, and not measured.

## 3. Competitive analysis

"Unknown" means we did not find a vendor statement either way. Cost is list price where the vendor publishes one.

| | Handles handwriting? | Proves each accepted value? | Finds errors in an existing capture? | Photo evidence per finding? | Cost per form | Open model on AMD? |
|---|---|---|---|---|---|---|
| **Two Hands** | yes: digits and words, Spanish, phone photos (measured) | yes: the paper's identities must hold, or a person sees it | **yes, the product** | yes, crop per disputed field | $0.14 per 1,000 compute (measured); $100 per 1,000 proposed | yes |
| Tesseract | "it won't work very well, as Tesseract is designed for printed text" ([FAQ](https://tesseract-ocr.github.io/tessdoc/FAQ.html)) | no | no (you would build it) | no | free, self-hosted | open source, CPU |
| ABBYY FlexiCapture | yes, ICR for handwritten fields ([page](https://www.abbyy.com/flexicapture/)) | unknown | not a stated feature | unknown | not public | no |
| Rossum | yes, "handwriting in 30 languages" ([page](https://rossum.ai/ai-ocr-software/)) | unknown | not a stated feature | unknown | not public | no |
| Hypatos | unknown | unknown | not a stated feature | unknown | not public | no |
| UiPath Document Understanding | yes, lists handwriting ([docs](https://docs.uipath.com/document-understanding/automation-cloud/latest/user-guide/handwriting-recognition)) | unknown | not a stated feature | unknown | not public | no |
| AWS Textract | yes, but handwriting is English only; returns a confidence score per element ([FAQ](https://aws.amazon.com/textract/faqs/)) | confidence score, not a proof | not a stated feature | no | $1.50 per 1,000 pages text, $70 with forms ([pricing](https://aws.amazon.com/textract/pricing/)) | no |
| Google Document AI | yes, handwriting in Enterprise OCR ([docs](https://cloud.google.com/document-ai/docs/enterprise-document-ocr)) | unknown | not a stated feature | unknown | $1.50 per 1,000 pages OCR, $30 Form Parser ([pricing](https://cloud.google.com/document-ai/pricing)) | no |
| Sampling-based manual audit (status quo) | yes, a person | only for the sampled fields | yes, at the random rate: at least 1 error in 122 fields here | if the auditor files it | not cited | n/a |
| Double keying | yes, people | no: two keyers can agree on a paper that contradicts itself | no, it is a capture | no | not cited | n/a |

Why double keying is not enough: 19.2% of nationally captured tally forms (26,336 of 137,196) fail their own row
sum in the official capture (PREP 2024 CSV, `docs/NUMBERS.md` B). Keying twice copies the paper; it cannot say
which paper is wrong. Any IDP platform above could be configured to compare with a capture. None says it does it,
and none we found shows a crop per finding ordered by the paper's own arithmetic.

## 4. Risks and moats

### Risks

- **Procurement cycles.** Public institutes buy through calls and committees. Auditors are named by early 2027;
  if we miss that, the next window is years away.
- **Political sensitivity.** Election data draws attention. We use clerical language only ("capture error",
  "Option NN"), name no party, and say plainly that the first capture is preliminary and the certified count is
  the official result.
- **Recall is known only on a small subset.** On the forms the certified count settled by comparison, the model
  disputed 7 of 7 fields where the paper differs from the capture (Wilson 95% 65% to 100%;
  `results/adjudication/RECALL.md`). We do not know recall on the rest.
- **The model alone is wrong on 1 field in 37.** Most disputes are model misreads (156 of 267). That is why the
  model never decides and a person opens each dispute.
- **The new rule is our reading.** Art. 347 audits the system, not the field values. An institute may decide the
  field check is out of scope.
- **Next markets are untested.** We have no case-report form, claim or loan file measured.

### Why it holds

- **The paper's own arithmetic is the judge.** Words must equal digits, rows must sum to the total, sections must
  agree. The model only proposes; a value is accepted when the paper proves it. A competitor needs the same
  per-form-type identities, not a better model.
- **The photo trail.** Every finding has its crop and its mark. An auditor can hand the report to anyone and they can
  check it without trusting us.
- **An open model on AMD.** Gemma-4-31B-IT runs on AMD GPUs. Self-hosted, the scans never leave the country or the
  client. The names-and-signatures column is masked before anything is stored or sent.
- **A form type is a schema file.** The second form type (1850-1960 rainfall ledgers) was configuration, not code.

## 5. Next 90 days

1. **One pilot with a state count's auditor.** Offer the field-level check to one of the academic auditors in the
   INE annex, on that state's 2024 PREP data and scans, free, in exchange for a written evaluation. Target: a signed
   letter before the 2027 auditors are named.
2. **The second form type for elections.** Add a local-election tally sheet schema (local deputies are elected in 31
   states in 2027) and re-run the pre-registered protocol on a fresh random sample.
3. **A self-hosted AMD deployment.** Run Gemma-4-31B-IT on an AMD GPU server we control, measure cost per form
   and throughput without the shared-endpoint pacing, and package it so an auditor can run it inside their own
   network.
