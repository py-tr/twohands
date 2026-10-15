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

Touchless capture of self-checking paper forms. An open vision model on AMD GPUs reads every field. The form's own arithmetic decides what is accepted.

<p class="small">Demo: {{DEMO_URL}} · Video: {{VIDEO_URL}} · Repo: {{REPO_URL}}</p>

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

## Results

<div class="cols">
<div><div class="big">{{RUN300_ACCEPT_RATE}}</div>accepted with no human touch<br><span class="small">pre-registered random 300; pilot: 21 of 43 (49%)</span></div>
<div><div class="big">{{RUN300_ACC_WRONG}}</div>accepted fields wrong<br><span class="small">of {{RUN300_ACC_FIELDS}}; pilot: 0 of 462</span></div>
<div><div class="big">{{RUN300_KEYING_ERRORS}}</div>keying errors in the official capture<br><span class="small">pilot: 6 fields on 5 accepted forms</span></div>
</div>

<p class="small">Gemma-4-31B-IT on AMD. Graded against the official double-keyed capture; every disagreement on an accepted form checked by eye. Protocol committed (a93294c, Amendment 1 b0e443c) before any model read.</p>

---

<!-- Slide 6: audit mode -->

## Audit mode: errors in data already keyed twice

On 5 accepted forms, **6 fields** where the image shows the official capture mis-keyed. The model read them right.

The certified count covers 5 of them and **matches the image on all 5**.

<p class="small">Typing mistakes in a capture, nothing more. Rows are shown as Option 01 to 15; no party is named or compared.</p>

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
| Mean latency per form | 49 s | 85 s |
| Tokens in / out | ~2,153 / 641 | ~8,739 / 1,667 |
| Cost per form | $0.000118 | $0.000507 |

AMD Token Factory, the organisers' hosted AMD GPUs. One request per form. ~2 forms/min under our shared-key pacing.

<p class="small">Measured over 43 forms each. Locating, masking and the gate run on CPU.</p>

---

<!-- Slide 9: second form type -->

## A second form, a different century

UK rainfall ledgers, 1850 to 1960. Twelve months must add up to the clerk's annual total.

**40 sheets, 4,915 cells.** 306 of 380 year-columns accepted. **3,976 of 3,976** accepted cells match the 16,000 volunteers.

<p class="small">Rainfall Rescue, Hawkins et al. 2022. Images linked, not redistributed.</p>

---

<!-- Slide 10: business -->

## Who pays

- **First buyer:** Mexico's ~32 state-level counts in 2027, each with its own double-keyed capture contract (one 2024 contract: MXN 24.94M).
- **Then:** any self-checking form. Clinical-trial case report forms, census and survey sheets, archives.
- **Cost:** $0.12 per 1,000 forms on AMD. Auditing all 169,005 national tally forms: $20 to $86.

---

<!-- Slide 11: why not OCR -->

## Why an LLM, and who else is here

- **Classic OCR fails on this handwriting.** That is why Rainfall Rescue needed volunteers.
- **One vision model** reads digits, words and row labels from phone photos, with no per-form training. It never decides.
- **Status quo is double keying.** One state institute piloted AI recognition in 2024. Handwriting tools transcribe; none we found proves when to trust the read.

---

<!-- Slide 12: limits, failure, close -->

## Where it breaks

- **Limitation:** the 43-form pilot was small and chosen to be hard. The shared endpoint paces us to ~2 forms/min; a national run needs a dedicated AMD endpoint.
- **Failure case:** read as one image, a ledger row shifted one year. Sums still held: 26 of 870 accepted cells wrong. Fixed with tiles and a row-label check.
- **Next:** run beside one state capture in 2027; add a case-report-form schema.

**The model reads, the paper decides.**
