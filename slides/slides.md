---
marp: true
size: 16:9
paginate: true
theme: default
title: Two Hands
style: |
  section { font-family: "Inter", "Helvetica Neue", Arial, sans-serif; font-size: 28px; padding: 56px 72px; color: #1d232b; background: #fbfaf7; }
  h1 { font-size: 52px; color: #12324a; margin-bottom: 0.3em; }
  h2 { font-size: 38px; color: #12324a; }
  strong { color: #12324a; }
  table { font-size: 22px; }
  .big { font-size: 64px; font-weight: 700; color: #12324a; line-height: 1.1; }
  .small { font-size: 18px; color: #5a6470; }
  .cols { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 32px; margin-top: 24px; }
  .two { display: grid; grid-template-columns: 1.1fr 1fr; gap: 40px; align-items: center; }
  footer { font-size: 14px; color: #8a929b; }
footer: "Two Hands · AMD Developer Hackathon ACT III"
---

<!-- Slide 1: the one sentence -->

# Two Hands

## The model reads, the paper decides.

A second keyer that shows its proof. An open vision model on AMD GPUs re-reads every field of forms already keyed. The form's own arithmetic decides what is accepted; every disputed field goes to a person with its photo.

<p class="small">Demo, video and repo links: on the submission page.</p>

---

<!-- Slide 2: the problem -->

## Today every form is typed twice

Organisations key paper forms twice, because one keyer's mistakes cannot be found any other way. Mexico's 2024 national capture programme did this for every tally sheet. It cost **MXN 273.6M**.

Double keying copies the paper faithfully. It cannot say which paper is wrong: **19.2%** of nationally captured tally forms (26,336 of 137,196) fail their own row sum.

<p class="small">Sources: La Jornada 2024-05-26; PREP 2024 CSV. See docs/NUMBERS.md.</p>

---

<!-- Slide 3: how it works -->

## Many forms check themselves

<div class="cols">
<div>

**1. Mask**
Locate the page. Black out the names-and-signatures column before anything is stored or sent.

</div>
<div>

**2. Read on AMD**
Gemma-4-31B-IT reads every field twice: digits and words. Plus the printed label of each row.

</div>
<div>

**3. Gate**
Words = digits. Rows sum to TOTAL. Sections agree. All pass: accepted. Any fail: a person sees the field.

</div>
</div>

A form type is one schema file. A new form is configuration, not code.

---

<!-- Slide 4: a routed form -->

## A routed form names its failing field

<div class="two">
<div>

Form 211294C0100. The TOTAL digits say **262**. The words say **162**. The rows sum to 262.

The gate does not guess. It sends this one field to a person.

</div>
<div>

![w:520](../data/masked/spike/211294C0100.jpg)

<p class="small">Masked page. INE PREP 2024, free-use terms. Not an official INE product.</p>

</div>
</div>

---

<!-- Slide 5: headline numbers -->

## Results: a pre-registered random 300

<div class="cols">
<div><div class="big">52</div>fields where the official capture does not match the paper<br><span class="small">17 wrong numbers typed; 27 readable fields recorded as illegible, 23 of them on two faint pencil forms; 6 numbers typed where the paper is blank; 2 other. Each with its photo.</span></div>
<div><div class="big">1 in 605</div>fields wrong on the 18% of forms the paper's gate accepts<br><span class="small">alone, the model mis-keys about 1 field in 37</span></div>
<div><div class="big">1 in 5</div>disputed fields is a confirmed capture error (52 of 267)<br><span class="small">the capture's overall error rate is at least 1 in 122 (52 of 6,358 found so far); more than ten times the yield of a random check</span></div>
</div>

**Alone, the model mis-keys about 1 field in 37; the official two-person capture typed a wrong number in 1 field in 374. That is why the model never decides. The paper does, and a person sees the rest.**

<p class="small">Gemma-4-31B-IT on AMD. Protocol committed (a93294c, Amendment 1 b0e443c) before any model read. The first capture is preliminary by design; the certified count is the official result. Recall: on forms the certified count settled by comparison, 16 of its 23 differences from the first capture are council corrections or blank rows; the model disputed all 7 others (small n).</p>

---

<!-- Slide 6: audit mode -->

## Audit mode: one capture error

<div class="two">
<div>

Form 050815B0100, Option 07. **The paper says 175, the first capture keyed 75, the certified count says 175.**

The 52: 17 wrong numbers typed; 27 readable fields recorded as illegible, 23 of them on two faint pencil forms; 6 numbers typed where the paper is blank; 2 other. Each with its photo. On 250767B0100 the capture shifted a whole column by one row.

</div>
<div>

![w:520](receipt_050815B0100.jpg)

<p class="small">Masked crop. INE PREP 2024, free-use terms. Not an official INE product. Rows are Option 01 to 15; no party is named or compared.</p>

</div>
</div>

---

<!-- Slide 7: safeguard -->

## A person sees everything the paper cannot settle

The review desk shows only the failing field, the model's digits and words, and the crop. A person types one value. The identities re-check at once.

If the paper contradicts itself, the person escalates it. Nothing is corrected silently. A page that cannot be located is never sent.

---

<!-- Slide 8: AMD -->

## What ran on AMD

| | Gemma-4-31B-IT | Qwen3.8-27B |
|---|---|---|
| Role | primary reader | second reader |
| Mean latency per form | 87 s (300 run) | 85 s (pilot) |
| Tokens in / out | ~2,609 / 804 | ~8,739 / 1,667 |
| Cost per form | $0.000144 | $0.000507 |

AMD Token Factory, the organisers' hosted AMD GPUs. One request per form. ~2 forms/min under our shared-key pacing.

<p class="small">Gemma: means over the 289 reads of the pre-registered run. Qwen: pilot, 43 forms. Locating, masking and the gate run on CPU.</p>

---

<!-- Slide 9: second form type -->

## A second form, a different century

UK rainfall ledgers, 1850 to 1960. Twelve months must add up to the clerk's annual total.

**Spike, 40 sheets, 4,915 cells.** 306 of 380 year-columns accepted. **3,976 of 3,976** accepted cells (spike, 40 sheets) match the 16,000 volunteers.

<p class="small">Rainfall Rescue, Hawkins et al. 2022. Images linked, not redistributed.</p>

---

<!-- Slide 10: market and model -->

## Market and model: the auditor pays

**Now.** Every state PREP has an outside auditor (Reglamento de Elecciones art. 347); in 2024, 26 of 32 had named one, all universities or research centres. Next window: 32 concurrent local processes, election day **6 June 2027**. We add the field-by-field check against the paper.

**Next, not measured.** Clinical-trial source-data verification (site monitoring and source document verification: 15-30% of trial costs); keyed loan and claim files.

| Yield (measured) | Cost (measured) | Price (proposal) |
|---|---|---|
| 1 in 5 disputed fields is a capture error; at random, at least 1 in 122. A person checks 1 field in 24. Strong tier: 12 of 18 | $0.14 per 1,000 forms (Gemma) + $0.51 (Qwen, pilot) on AMD | **$100 per 1,000 forms audited**, report included |

<p class="small">Sources: INE annex 5, CCOE 23-02-2024; IEEH/CG/022/2024; INE Central Electoral 30-31 July 2026; Lindblad et al., Clinical Trials 2014. Full case: docs/BUSINESS.md.</p>

---

<!-- Slide 11: competition -->

## Competition: others extract, we audit

| | Handwriting | Proves each accepted value | Audits an existing capture | Photo per finding | Open model on AMD |
|---|---|---|---|---|---|
| **Two Hands** | yes (measured) | the paper's identities | **yes** | yes | yes |
| Tesseract | "won't work very well" | no | no | no | open, CPU |
| ABBYY, Rossum, UiPath, Document AI | yes (vendor pages) | unknown | not a stated feature | unknown | no |
| AWS Textract | English only | confidence score | not a stated feature | no | no |
| Sampling audit (status quo) | a person | sampled fields only | at the random rate | if filed | n/a |
| Double keying | people | no | no | no | n/a |

Double keying copies the paper; it cannot say which paper is wrong: 19.2% of national tally captures fail their own row sum. Cloud extraction lists at $30 to $70 per 1,000 pages with forms; it extracts, it does not audit.

<p class="small">Vendor sources, and Hypatos (mostly unknown): docs/BUSINESS.md section 3.</p>

---

<!-- Slide 12: limits, failure, close -->

## Where it breaks

- **Limitations:** the row-label check routed 86 forms, and 68 of them were read right (all 15 label-only routes). In one call the model can harmonise words and digits, so one read is not two independent reads; the fix is separate reads or a second reader. ~2 forms/min on a shared endpoint.
- **Failure case:** read as one image, a ledger row shifted one year. Sums still held: 26 of 870 accepted cells wrong. Fixed with tiles and a row-label check.
- **Next:** audit one state PREP beside its auditor; add a case-report-form schema.

**The model reads, the paper decides.**
