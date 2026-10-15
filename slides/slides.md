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
<div><div class="big">52</div>keying errors in 6,358 fields, each with its photo<br><span class="small">the certified count covers 31 and confirms the image on 22; all 9 differences were recounts</span></div>
<div><div class="big">1 in 605</div>fields wrong on the 18% of forms the paper's gate accepts<br><span class="small">alone, the model mis-keys about 1 field in 37</span></div>
<div><div class="big">1 in 5</div>disputed fields is a confirmed keying error (52 of 267)<br><span class="small">about 1 in 122 at random: up to 24x the yield</span></div>
</div>

**The model alone is a worse keyer than the official two-person capture: 156 misreads against 52 keying errors in 6,358 fields. That is why it never decides. The paper does, and a person sees the rest.**

<p class="small">Gemma-4-31B-IT on AMD. Protocol committed (a93294c, Amendment 1 b0e443c) before any model read. The first capture is preliminary by design; the certified count is the official result. Recall is bounded: on forms the certified count settled without a recount, the model had disputed 7 of the 23 fields where it disagrees with the first capture.</p>

---

<!-- Slide 6: audit mode -->

## Audit mode: the receipt

<div class="two">
<div>

Form 050815B0100, Option 07. **The paper says 175, the first capture keyed 75, the certified count says 175.**

Of the 52: 17 wrong values keyed, 27 legible fields marked illegible, 6 values keyed where the paper is blank, 2 other. On 250767B0100 the capture shifted a whole column by one row.

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

<!-- Slide 10: business -->

## Who pays: auditors

**Give us your keyed data and the scans. You get the 4% of fields to look at, each with its photo.**

- **Now:** Mexico requires an outside audit of every PREP; Reglamento de Elecciones art. 347 gives priority to academic institutions. In 2024 UNAM centres audited the PREPs of Querétaro, Aguascalientes, Puebla and Mexico City, among others.
- **Next (not measured):** clinical-trial source-data verification; monitoring takes 15-30% of trial costs in peer-reviewed estimates.
- **Also:** internal audit of any keyed file with its scans. **Cost:** $0.14 per 1,000 forms on AMD; about $24 to re-read all 169,005 national tally forms.

<p class="small">Sources: repositoriodocumental.ine.mx (ccoe-1so-23-02-2024-p19-a5); ieeq.mx síntesis 2024/13469; Ball, Clinical Trials 2014.</p>

---

<!-- Slide 11: why not OCR -->

## Why an LLM, and who else is here

- **Classic OCR fails on this handwriting.** That is why Rainfall Rescue needed volunteers.
- **One vision model** reads digits, words and row labels from phone photos, with no per-form training. It never decides.
- **Status quo is double keying.** One state institute piloted AI recognition in 2024. Handwriting tools transcribe; none we found proves when to trust the read.

---

<!-- Slide 12: limits, failure, close -->

## Where it breaks

- **Limitations:** the row-label check routed 86 forms, and 68 of them were read right (all 15 label-only routes). In one call the model can harmonise words and digits, so one read is not two independent reads; the fix is separate reads or a second reader. ~2 forms/min on a shared endpoint.
- **Failure case:** read as one image, a ledger row shifted one year. Sums still held: 26 of 870 accepted cells wrong. Fixed with tiles and a row-label check.
- **Next:** audit one state PREP beside its auditor; add a case-report-form schema.

**The model reads, the paper decides.**
