# Video script: Two Hands (final, 4:14; limit 5:00, floor 3:00)

One voice, English, short sentences. Slides carry the story; four short demo segments show the working site.
Slides: the talk deck [talk.md](talk.md) (PDF [two-hands-talk.pdf](two-hands-talk.pdf)), one idea per slide, at most
about 20 words on screen. The full evidence deck ([slides.md](slides.md)) is not shown in the video.
Screen capture of the hosted app, 1920x1080, browser zoom 125%. Captions: [two-hands.srt](two-hands.srt).
Reference screenshots of the site states: [`shots/`](shots/).

Words in **[brackets]** are read off the screen on the day (they change). Everything else is said exactly as written.
Speak slowly: about two words a second. If a line runs long, cut a sentence from the end of the segment, never speed up.
On the site, the viewer is never asked to read: point the mouse at the one number named in the voice line, nothing else.

| Time | On screen (slide, or page and exact action) | Voice (exact words) |
|---|---|---|
| **0:00-0:10** | **Talk slide 1** (title): "Two Hands", "Verifiable quality control for handwritten numbers.", the hook. | "Two Hands. Verifiable quality control for handwritten numbers. OCR reads the number. Two Hands checks whether the whole form agrees." |
| **0:10-0:28** | **Talk slide 2**: "6.5%". | "Mexico counts every tally sheet twice: a fast preliminary capture, then the certified count. On six point five percent of the polling stations not recounted, the two official records of the same paper disagree." |
| **0:28-0:40** | **Talk slide 3**: "19.2%". | "And nineteen point two percent of national forms fail their own row sum, in the official capture. A sum says something is wrong; the photo says which field." |
| **0:40-1:00** | **Talk slide 4**: "Two hands and a referee", three boxes. | "Gemma, on AMD, reads every field twice: the digits and the amount in words. A second, independent reader must agree. The referee is the paper's own arithmetic. Every check holds: accepted. One fails: a person sees the field, with its photo." |
| **1:00-1:12** | **Talk slide 5**: the real crop of form 122655C0100, Option 02, and "366 ≠ 466". | "Here is a real sheet. Gemma read twenty-three, in digits and in words. But the rows sum to three hundred sixty-six, not four hundred sixty-six." |
| **1:12-1:24** | **DEMO. Trace** (`/trace#routed`), form 122655C0100. Start at step 3: point at **366**, then **466** in the "rows sum to TOTAL" row (FAIL); scroll to step 4: "Routed to a person" and "With the paper's 123, rows sum to TOTAL gives 466 = 466". Real case, stored read; nothing typed. | "On the site, the same sheet: routed to a person. The paper says one hundred twenty-three, and with it the sum holds." |
| **1:24-1:34** | Same page, step 6: the four "ok" lines and **VERIFIED** (point at it). Then 2 s on the terminal tab: `VERIFIED  root e56a8ef4...` for this receipt (pre-run, see the guide). | "Every field gets a receipt. Verified: it proves the record is unchanged. Not that the reading is right." |
| **1:34-1:50** | **DEMO. Form 211298B0100** (`/form/211298B0100`, `07_form_211298B0100.png`). Scroll to the live panel, click **Read live on AMD**. The timer starts. At about 0:05 on the timer, **hard cut** to the moment the answer lands; the timer stays visible, so the cut shows. Point at the verdict only. **Fallback** (endpoint down, or a Qwen banner you do not want): the recorded read from the guide, with the on-screen label "recorded [time] UTC". | "Now a live read. One request to Gemma, on the AMD Token Factory. We cut the wait; the timer stays on screen. It took **[ninety]** seconds. Every check holds: accepted." If one check fails, say instead of the last sentence: "One check fails, so it goes to a person." If the banner says Qwen, say "One request to Qwen, on the AMD Token Factory." Fallback: replace "Now a live read" with "This live read was recorded earlier today." |
| **1:50-2:18** | **DEMO. Audit** (`/audit/new`). Click **Run the sample audit**: point at "267 disputed fields in 6,358 checked" (`05_au1_audit.png`). Click **Printable report**: scroll to Option 07 of 050815B0100 (point at the crop, then 75, then 175). Then point at "Merkle root e56a8ef4f011b9e5" (`06_au2_report.png`). | "This is the product. An auditor brings the typed data and the scans. Here, the sample: six thousand fields, checked in seconds. Two hundred sixty-seven disputes, strongest first. This one: the capture keyed seventy-five; the paper says one hundred seventy-five. One fingerprint seals the whole report. Change one number, and the check fails." |
| **2:18-2:30** | **Talk slide 6**: "1,270". | "The proof. Gemma on AMD read one thousand two hundred seventy real handwritten tally sheets. Forty-nine capture errors, confirmed by the certified count." |
| **2:30-2:45** | **Talk slide 7**: "91.6%" and the two bars. | "On Baja California Sur's local actas: ninety-one point six percent field match. The Google Document AI reading the state bought scored sixty-two point eight four percent, on the same metric." |
| **2:45-2:58** | **Talk slide 8**: "27 of 28". | "Recall: twenty-seven of twenty-eight capture errors the certified count reveals, in one state, pre-registered. And a person re-read the AI-judged disputes blind: zero read differently." |
| **2:58-3:20** | **Talk slide 9**: "Why Gemma, on AMD", the three-row table. | "Same three hundred forms, same gate. It accepts one point eight times the forms Qwen does, at the same error rate, four point six times cheaper, two point eight times faster. A whole state: Colima. Gemma on AMD read all nine hundred eighty-two sheets for fourteen cents." |
| **3:20-3:35** | **DEMO. Evolus** tab: workspace **py_tr**, workflow **Audit finding**, open the newest run (drafted on Gemma, see the guide) to its three-sentence finding and the step "Recompute the evidence score (no AI)". Then 2 s on the agent **Intake clerk**: model `Gemma-4-31B-IT`. | "Each strong finding becomes a case in Evolus. The agent runs on Gemma, on AMD, and drafts it. A script, not the model, scores the evidence. The auditor decides." |
| **3:35-3:56** | **Talk slide 10**: "$1". | "Who pays? Mexico's preliminary counts: INE, thirty-two state institutes, and their outside auditors. On June sixth, twenty twenty-seven, thirty-two local elections join the federal midterm. One dollar per sheet audited, proposed. The first step: a paid shadow-mode pilot on one state's count." |
| **3:56-4:08** | **Talk slide 11**: "Elections are our proof set, not our only market." | "Next: seven more countries publish these sheets, and health reporting in seventy-plus countries runs on DHIS2. Elections are our proof set, not our only market." |
| **4:08-4:14** | **Talk slide 12** (close). Stay still. Then a 2 s credit card (small text, see notes). | "Two Hands. Verifiable quality control for handwritten numbers. Running on AMD." |

Total: 4:14 (plus a 2 s credit card: 4:16). Product on screen: the real sheet at 1:00, the working site from 1:12 to 2:18
and the Evolus case at 3:20. Slides used: talk slides 1 to 12, in order.

## Words never to say

- "fraud"; "election" as a product word (the product is "Two Hands", the thing is "a tally sheet", "a form");
  party names; vote totals.
- "errors" for the fields of the random 300: say "fields where the capture does not match the paper" (or "capture errors").
- The INE metric (83.5%) is not in the video. If it is ever said, always with "as we read it, computed after the fact";
  never "we passed INE's test", never "we beat INE's bar".
- "Confirmed by a person": not for the AI-judged fields (say "a person re-read them blind: zero read differently").
- The receipt "proves the record is unchanged", never "proves the reading is right".
- Recall is "twenty-seven of twenty-eight capture errors the certified count reveals, in one state", never "catches every error".
- The price is "proposed"; the practice sheet, if shown, is "a demonstration, not a measurement".

## Numbers used, and where they come from

| Spoken | Source |
|---|---|
| Hook: "OCR reads the number. Two Hands checks whether the whole form agrees."; "verifiable quality control for handwritten numbers" | README title and subtitle; talk slides 1 and 12; evidence deck title and closing slides |
| 6.5% (3,382 of the 52,167 polling stations not recounted); 19.2% (26,336 of 137,196 national forms) | 6.5%: `results/national_counts.md`, checked by `scripts/national_counts.py --check`. 19.2%: README "Why double keying is not enough", `app/numbers.py`, `docs/NUMBERS.md` (PREP 2024 CSV, `docs/sources/tally-witness-pilot.md` §1). Evidence deck "The problem, from INE's own files" |
| 23 (digits and words), 366 / 466, 123 (122655C0100, Option 02); receipt VERIFIED, root e56a8ef4... | `docs/TRACE.md` (`/trace#routed`), generated by `scripts/build_trace.py` from `results/calls_gemma.jsonl`; crop `slides/crop_122655C0100_OPT02.jpg` from `/crop/122655C0100/OPT02.jpg?pad=0.02&label=0` |
| 6,358 fields, 267 disputes, root e56a8ef4...; 175 / 75 (050815B0100, Option 07) | `/audit/new` sample; `results/sample_audit_root.txt`; `results/adjudication/CERTIFIED.md` |
| 1,270 sheets, 49 capture errors confirmed by the certified count | README "Real data"; recomputed by `scripts/price_check.py --check` |
| 91.6% field match vs 62.84% for the Google Document AI reading Baja California Sur bought (same per-field metric; pre-registered random 300 actas) | README "Against the incumbent"; `results/ieebcs/score.json`, checked by `scripts/ieebcs_score.py --check` |
| Recall 27 of 28 (one state, pre-registered); 0 read differently | README "Checked"; `results/colima/recall.md` (PROTOCOL.md Amendment 9), checked by `scripts/colima_recall.py --check`; `app/honest.py` |
| 1.8x the forms, 4.6x cheaper, 2.8x faster; on screen 55 vs 31 of 300, $0.14 vs $0.64, 87 s vs 241 s | README "Why Gemma" (`app/data/bakeoff_300.json`), checked by `scripts/why_gemma.py --check` |
| 982 sheets of Colima, 14 cents ($0.14 billed) | `results/colima/colima_audit.json`, `results/colima/calls_gemma.jsonl` (sum of `cost_usd`), via `app/colima.py` (the caption line is checked in `two-hands.srt`) |
| INE, 32 state institutes, outside auditors; 6 June 2027, 32 local elections | README "Business at a glance"; sources: `docs/BUSINESS.md` "Sources for the Business at a glance table" |
| $1 per sheet audited (proposed), paid shadow-mode pilot | `app/pricing.py` (a proposal), checked by `scripts/price_check.py --check` |
| 7 more countries; DHIS2 in 70+ countries (not yet measured) | README "Next: elections", "Next: health"; `docs/BUSINESS.md` |

## Notes for the edit

- Slides: export each page of `two-hands-talk.pdf` as an image (or screen-record the PDF full screen) and hold it for
  the row's time. Cut between slide and site on a hard cut; no transitions longer than 0.3 s.
- On the site, highlight only the number the voice names (mouse pointer, or a box added in the edit). Never let a
  paragraph fill the frame without a pointer on one number.
- Never show a party logo close-up: crops of vote rows only; rows are "Option NN" in the app.
- Burn in captions from `two-hands.srt`; after recording, replace the bracketed numbers with what you said
  (`scripts/make_srt.py`, then rerun it).
- Credit card at the end (2 s, small): "Tally sheets: INE PREP 2024, free-use terms. Not an official INE product."
