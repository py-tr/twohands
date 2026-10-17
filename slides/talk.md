---
marp: true
size: 16:9
paginate: true
theme: default
title: Two Hands (talk)
description: Verifiable quality control for handwritten numbers. Gemma on AMD. The short talk deck used in the video; the full evidence deck is slides.md.
style: |
  section { justify-content: center !important; font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 40px; line-height: 1.3; padding: 60px 90px; color: #1d232b; background: #fbfaf7; text-align: left; }
  section::after { font-size: 16px; color: #8a929b; }
  h1 { font-size: 96px; line-height: 1.05; color: #12324a; margin: 0 0 24px; }
  h2 { font-size: 62px; color: #12324a; margin: 0 0 30px; }
  strong { color: #12324a; }
  p { margin: 0 0 18px; }
  .huge { font-size: 190px; font-weight: 800; color: #12324a; line-height: 1.0; margin-bottom: 18px; letter-spacing: -0.02em; }
  .say { font-size: 50px; color: #1d232b; }
  .sub { font-size: 36px; color: #5a6470; }
  .ne { font-size: 120px; font-weight: 800; color: #c2410c; line-height: 1.0; margin: 24px 0 18px; }
  .row img { border: 2px solid #e3e0d8; border-radius: 8px; }
  .steps { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 26px; margin-top: 10px; }
  .step { background: #fff; border: 2px solid #e3e0d8; border-radius: 14px; padding: 26px 24px; font-size: 44px; line-height: 1.2; min-height: 260px; }
  .step.hi { border: 3px solid #12324a; }
  .step .k { font-size: 22px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #9a3412; margin-bottom: 12px; }
  .bars { margin-top: 28px; }
  .bar { height: 54px; border-radius: 6px; margin: 10px 0 4px; }
  .bar.us { background: #12324a; width: 91.6%; }
  .bar.them { background: #b9c2cc; width: 62.84%; }
  .bl { font-size: 30px; color: #3b4550; }
  table { font-size: 44px; border-collapse: collapse; margin-top: 10px; }
  th, td { padding: 12px 26px; border-bottom: 1px solid #e3e0d8; }
  th { color: #5a6470; font-weight: 600; font-size: 32px; }
  section.title { background: #12324a; color: #f3f1ea; }
  section.title h1 { color: #fff; font-size: 110px; }
  section.title .say { color: #ffd9a8; }
  section.title .sub { color: #d6dde4; }
  section.title::after { color: #9fb1c2; }
---

<!-- _class: title -->
<!-- _paginate: false -->

# Two Hands

<p class="say">Verifiable quality control for handwritten numbers.</p>

<p class="sub">OCR reads the number. Two Hands checks whether the whole form agrees.<br>Gemma on AMD</p>

<!--
Talk deck for the video (slides/video-script.md). Every number and its source is in the evidence deck, slides/slides.md, and in README.md.
-->

---

<div class="huge">6.5%</div>

<p class="say">of polling stations not recounted: the two official records of the same paper disagree.</p>

<!--
Source: results/national_counts.md (INE PREP 2024 CSV; Computos Distritales 2024 CSV). 3,382 of the 52,167 polling stations that were not recounted: the preliminary capture and the certified count disagree on at least one vote field. A difference says two captures disagree, not which one is right; the photo does. Clerical only: no party, no totals, no outcome.
-->

---

<div class="huge">19.2%</div>

<p class="say">of national forms fail their own row sum, in the official capture.</p>

<!--
Source: README "Why double keying is not enough"; app/numbers.py; docs/NUMBERS.md (PREP 2024 CSV, docs/sources/tally-witness-pilot.md section 1): 26,336 of 137,196 nationally captured forms.
-->

---

## Two hands and a referee

<div class="steps">
<div class="step"><div class="k">Hand 1</div>Gemma reads digits and words</div>
<div class="step"><div class="k">Hand 2</div>A second reader agrees</div>
<div class="step hi"><div class="k">Referee</div>The paper's own arithmetic</div>
</div>

<!--
Gemma-4-31B-IT on AMD Token Factory reads every field twice: the handwritten digits and the amount in words. A second, independent reader (Qwen3.8-27B on AMD) must agree field by field; it never overrides Gemma, it only withholds acceptance. The referee: words = digits, rows sum to TOTAL, sections agree. Every identity holds: accepted. Any fails: routed to a person, with the field named and its photo. docs/ARCHITECTURE.md.
-->

---

<div class="row">

![w:1100](crop_122655C0100_OPT02.jpg)

</div>

<div class="ne">366 ≠ 466</div>

<p class="say">Gemma read 23. The paper says 123. Routed to a person.</p>

<!--
Form 122655C0100, Option 02 (masked crop, right of the logo column). Gemma read 23 in digits and in words; the rows sum to 366, the form's TOTAL is 466; routed. With the paper's 123 the sum holds: 466 = 466. Source: docs/TRACE.md (b), /trace#routed.
-->

---

<div class="huge">1,270</div>

<p class="say">real handwritten tally sheets read by Gemma on AMD.</p>

<p class="sub">49 capture errors confirmed by the certified count.</p>

<!--
README "Real data": a pre-registered random 300 and a whole state (Colima); 49 capture errors confirmed by the certified count, each with its photo.
-->

---

<div class="huge">91.6%</div>

<p class="say">vs 62.84% for the AI reading the state bought.</p>

<div class="bars">
<div class="bar us"></div><div class="bl">Gemma on AMD</div>
<div class="bar them"></div><div class="bl">Google Document AI</div>
</div>

<p class="sub" style="margin-top:18px">Same metric. Baja California Sur, local actas.</p>

<!--
README "Against the incumbent": on Baja California Sur's 2024 local actas, 91.6% of fields match the published values, on the same per-field metric where the state's purchased Google Document AI reading scored 62.84% (pre-registered random 300 actas). Full line: 91.58% (n = 3,622 fields; Wilson 95% 90.63-92.44%); theirs 14,501 of 23,077 fields on all 2,020 actas, against the manual capture rather than the published values. results/ieebcs/score.json, scripts/ieebcs_score.py --check.
-->

---

<div class="huge">27 of 28</div>

<p class="say">certified-detectable capture errors caught (one state, pre-registered).</p>

<p class="sub">A person's blind re-read of the AI-judged disputes: 0 read differently.</p>

<!--
README "Checked": recall 27 of 28 on the capture errors the certified count reveals (Colima, PROTOCOL.md Amendment 9); not total recall. results/colima/recall.md.
-->

---

## Why Gemma, on AMD

| | **Gemma-4-31B-IT** | Qwen3.8-27B |
|---|---|---|
| Forms accepted, no person | **55 of 300** | 31 of 300 |
| $ per 1,000 forms | **$0.14** | $0.64 |
| Time per read | **87 s** | 241 s |

<!--
README "Why Gemma" (app/data/bakeoff_300.json): same 300 forms, same gate, on AMD: Gemma accepts 1.8x the forms Qwen3.8-27B does at the same error rate, 4.6x cheaper and 2.8x faster. Whole state: Colima, 982 sheets read on AMD for $0.14 (results/colima/).
-->

---

<div class="huge">$1</div>

<p class="say">per sheet audited (proposed). Buyer: INE, 32 state institutes and their outside auditors.</p>

<p class="sub">First step: a paid shadow-mode pilot, 2027.</p>

<!--
README "Business at a glance": price from app/pricing.py (a proposal): $1 per sheet audited (proposed); first step: a paid shadow-mode pilot on one state's 2027 count. Why now: 6 June 2027, the federal midterm and 32 concurrent local elections.
-->

---

## Elections are our proof set, not our only market.

<p class="say">Same public data: 7 more countries.<br>Health reporting on DHIS2: 70+ countries.</p>

<p class="sub">Not yet measured.</p>

<!--
README "Next: elections" and "Next: health"; sources: docs/BUSINESS.md "Sources for the Business at a glance table".
-->

---

<!-- _class: title -->
<!-- _paginate: false -->

# Two Hands

<p class="say">Verifiable quality control for handwritten numbers.</p>

<p class="sub">Gemma-4-31B-IT on AMD Token Factory</p>

<!--
Detail and sources: the evidence deck (slides/slides.md, two-hands-slides.pdf) and README.md. make eval recomputes every number offline.
-->
