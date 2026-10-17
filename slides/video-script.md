# Video script: Two Hands (final, 4:29; limit 5:00, floor 3:00)

One voice, English, short sentences. Slides carry the story; four short demo segments show the working site.
Slides: the talk deck, 9 slides in the web app's own look (light, one accent), built by [build_talk.py](build_talk.py) into [talk.html](talk.html), the PNGs in
[`talk/`](talk/) and the PDF [two-hands-talk.pdf](two-hands-talk.pdf); one claim per slide, with one real product visual or a plain chart
(screenshots and masked crops captured from the app by [capture_talk.py](capture_talk.py)). The full evidence deck
([slides.md](slides.md)) is not shown in the video.
Screen capture of the hosted app, 1920x1080, browser zoom 125%. Captions: [two-hands.srt](two-hands.srt).
Reference screenshots of the site states: [`shots/`](shots/).

Words in **[brackets]** are read off the screen on the day (they change). Everything else is said exactly as written.
Speak slowly: about two words a second. If a line runs long, cut a sentence from the end of the segment, never speed up.
On the site, the viewer is never asked to read: point the mouse at the one number named in the voice line, nothing else.

| Time | On screen (slide, or page and exact action) | Voice (exact words) |
|---|---|---|
| **0:00-0:10** | **Talk slide 1** (title): "Two Hands", the tagline and the hook; the whole privacy-masked tally sheet 080310B0100 (masked column left out of the frame) with Unused ballots highlighted, its zoomed field (pointers: "In words: ciento ochenta (180)", "In digits: 180") and the ledger "Unused ballots: two records of one number" (official typed capture (PREP) 480 in red; Gemma read 180); four numbers (1,270 · 91.6% · 27 of 28 · 0 of 484). | "Two Hands. Verifiable quality control for handwritten numbers. OCR reads the number. Two Hands checks whether the whole form agrees." |
| **0:10-0:40** | **Talk slide 2**: "Two official records of the same paper disagree." The crop of 050815B0100 (pointers: "In words: ciento setenta y cinco (175)", "In digits: 175") beside the two typed records (official typed capture (PREP) 75 in red; certified count 175); point at **6.5%**, then on "nineteen point two" at **19.2%**. | "Mexico counts every tally sheet twice: a fast preliminary capture, then the certified count. On six point five percent of the polling stations not recounted, the two official records of the same paper disagree. And nineteen point two percent of national forms fail their own row sum, in the official capture. A sum says something is wrong; the photo says which field." |
| **0:40-1:00** | **Talk slide 3**: "The model reads. The paper's own arithmetic decides.", five numbered steps and the accepted form 211298B0100 (its five identity checks). | "Gemma, on AMD, reads every field twice: the digits and the amount in words. A second, independent reader must agree. The referee is the paper's own arithmetic. Every check holds: accepted. One fails: a person sees the field, with its photo." |
| **1:00-1:24** | **DEMO. Trace** (`/trace#routed`), form 122655C0100. Start at step 3: point at **366**, then **466** in the "rows sum to TOTAL" row (FAIL); scroll to step 4: "Routed to a person" and "With the paper's 123, rows sum to TOTAL gives 466 = 466". Real case, stored read; nothing typed. | "Here is a real sheet. Gemma read twenty-three, in digits and in words. But the rows sum to three hundred sixty-six, not four hundred sixty-six. On the site, the same sheet: routed to a person. The paper says one hundred twenty-three, and with it the sum holds." |
| **1:24-1:34** | Same page, step 6: the four "ok" lines and **VERIFIED** (point at it). Then 2 s on the terminal tab: `VERIFIED  root e56a8ef4...` for this receipt (pre-run, see the guide). | "Every field gets a receipt. Verified: it proves the record is unchanged. Not that the reading is right." |
| **1:34-1:50** | **DEMO. Form 211298B0100** (`/form/211298B0100`, `07_form_211298B0100.png`). Scroll to the live panel, click **Read live on AMD**. The timer starts. At about 0:05 on the timer, **hard cut** to the moment the answer lands; the timer stays visible, so the cut shows. Point at the verdict only. **Fallback** (endpoint down, or a Qwen banner you do not want): the recorded read from the guide, with the on-screen label "recorded [time] UTC". | "Now a live read. One request to Gemma, on the AMD Token Factory. We cut the wait; the timer stays on screen. It took **[ninety]** seconds. Every check holds: accepted." If one check fails, say instead of the last sentence: "One check fails, so it goes to a person." If the banner says Qwen, say "One request to Qwen, on the AMD Token Factory." Fallback: replace "Now a live read" with "This live read was recorded earlier today." |
| **1:50-2:18** | **DEMO. Audit** (`/audit/new`). Click **Run the sample audit**: point at "267 disputed fields in 6,358 checked" (`05_au1_audit.png`). Click **Printable report**: scroll to Option 07 of 050815B0100 (point at the crop, then 75, then 175). Then point at "Merkle root e56a8ef4f011b9e5" (`06_au2_report.png`). | "This is the product. An auditor brings the typed data and the scans. Here, the sample: six thousand fields, checked in seconds. Two hundred sixty-seven disputes, strongest first. This one: the capture keyed seventy-five; the paper says one hundred seventy-five. One fingerprint seals the whole report. Change one number, and the check fails." |
| **2:18-2:43** | **Talk slide 4**: "1,270 real tally sheets read on AMD. 49 capture errors confirmed by the certified count.": 28 dots (one outlined) and four numbers (1,270 · 49 · 27 of 28 · 0 of 484); the blind re-read line. | "The proof. Gemma on AMD read one thousand two hundred seventy real handwritten tally sheets. Forty-nine capture errors, confirmed by the certified count. Recall: twenty-seven of twenty-eight capture errors the certified count reveals, in one state, pre-registered. And a person re-read the AI-judged disputes blind: zero read differently." |
| **2:43-2:58** | **Talk slide 5**: "91.6% field match, where the reading the state bought scored 62.84%.": the comparison basis as a subtitle, two bars. | "On Baja California Sur's local actas: ninety-one point six percent field match. The Google Document AI reading the state bought scored sixty-two point eight four percent, on the same metric." |
| **2:58-3:20** | **Talk slide 6**: "Same 300 forms, same gate: Gemma accepts 1.8× the forms Qwen does, 4.6× cheaper, 2.8× faster.": three-row table; point at **$0.14** (Colima) on "fourteen cents". | "Same three hundred forms, same gate. It accepts one point eight times the forms Qwen does, at the same error rate, four point six times cheaper, two point eight times faster. A whole state: Colima. Gemma on AMD read all nine hundred eighty-two sheets for fourteen cents." |
| **3:20-3:35** | **DEMO. Evolus** tab: workspace **py_tr**, workflow **Audit finding**, open the newest run (drafted on Gemma, see the guide) to its three-sentence finding and the step "Recompute the evidence score (no AI)". Then 2 s on the agent **Intake clerk**: model `Gemma-4-31B-IT`. | "Each strong finding becomes a case in Evolus. The agent runs on Gemma, on AMD, and drafts it. A script, not the model, scores the evidence. The auditor decides." |
| **3:35-4:03** | **Talk slide 7**: "An independent check of the keyed values. $1 per sheet audited (proposed).": the audit report header and one strong finding (050815B0100 Option 07); Buyer, Why now, One state priced. | "Mexico's preliminary counts: INE, thirty-two state institutes, and their outside auditors. On June sixth, twenty twenty-seven, thirty-two local elections join the federal midterm. One dollar per sheet audited, proposed: for Morelos, half a percent of what it paid to run its count. The first step: a paid shadow-mode pilot on one state's count." |
| **4:03-4:19** | **Talk slide 8**: "Read 3114, paper 314. Gate v2 sends it to a person.": the masked crop of 070212B0100, unused ballots. | "Where it breaks. On fresh forms, the model read three thousand one hundred fourteen; the paper says three hundred fourteen. No sum covers that field. Gate version two sent it to a person." |
| **4:19-4:29** | **Talk slide 9** (close): "Every number re-derives from public data.": make eval, verify a receipt, the timestamp; the repo. Stay still. Then a 2 s credit card (small text, see notes). | "Every number re-derives from public data, with one command. Two Hands. Verifiable quality control for handwritten numbers. Running on AMD." |

Total: 4:29 (plus a 2 s credit card: 4:31). Product on screen: the real sheet on slide 1, the working site
from 1:00 to 2:18 and the Evolus case at 3:20. Slides used: talk slides 1 to 9, in order.

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
| Hook: "OCR reads the number. Two Hands checks whether the whole form agrees."; "verifiable quality control for handwritten numbers" | README title and subtitle; talk slides 1 and 9; evidence deck title and closing slides |
| 6.5% (3,382 of the 52,167 polling stations not recounted); 19.2% (26,336 of 137,196 national forms) | 6.5%: `results/national_counts.md`, checked by `scripts/national_counts.py --check`. 19.2%: README "Why double keying is not enough", `app/numbers.py`, `docs/NUMBERS.md` (PREP 2024 CSV, `docs/sources/tally-witness-pilot.md` §1). Evidence deck "The problem, from INE's own files"; talk slide 2 |
| Slide 1 (on screen only): 080310B0100, Unused ballots: the paper 180 (words "CIENTO OCHENTA" (180), boxes 1 8 0), the official typed capture (PREP) keyed 480, Gemma read 180 (digits and words; the gate accepted the form). The certified count does not cover this field, so none is shown | `results/adjudication/SUMMARY.md`, `docs/TRACE.md` (a), `app/data/headline.json`; page `/masked/080310B0100.jpg` (cut left of the masked column), crop `/crop/080310B0100/SOBRANTES.jpg?pad=0.02&label=0` |
| Slide 1 and 4 (on screen): 0 of 484 (gate v2, 100 held-out forms) | `results/confirm100.md`, checked by `scripts/confirm100_score.py --check`; README "Headline: the pre-registered 300" (pre-registered confirmation row) |
| 23 (digits and words), 366 / 466, 123 (122655C0100, Option 02); receipt VERIFIED, root e56a8ef4... | `docs/TRACE.md` (`/trace#routed`), generated by `scripts/build_trace.py` from `results/calls_gemma.jsonl`; shown live in the trace demo (no slide) |
| 3114 read, paper 314 (070212B0100, unused ballots); gate v2 blocked it, 0 wrong of 484 on the fresh 100 | `results/confirm100.md`, checked by `scripts/confirm100_score.py --check`; `docs/EVALUATION.md`; crop `/crop/070212B0100/SOBRANTES.jpg?pad=0.02&label=0` (`slides/talk/assets/`) |
| 6,358 fields, 267 disputes, root e56a8ef4...; 175 / 75 (050815B0100, Option 07) | `/audit/new` sample; `results/sample_audit_root.txt`; `results/adjudication/CERTIFIED.md` |
| 1,270 sheets, 49 capture errors confirmed by the certified count | README "Real data"; recomputed by `scripts/price_check.py --check` |
| 91.6% field match vs 62.84% for the Google Document AI reading Baja California Sur bought (same per-field metric; pre-registered random 300 actas) | README "Against the incumbent"; `results/ieebcs/score.json`, checked by `scripts/ieebcs_score.py --check` |
| Recall 27 of 28 (one state, pre-registered); 0 read differently | README "Checked"; `results/colima/recall.md` (PROTOCOL.md Amendment 9), checked by `scripts/colima_recall.py --check`; `app/honest.py` |
| 1.8x the forms, 4.6x cheaper, 2.8x faster; on screen 55 vs 31 of 300, $0.14 vs $0.64, 87 s vs 241 s | README "Why Gemma" (`app/data/bakeoff_300.json`), checked by `scripts/why_gemma.py --check` |
| 982 sheets of Colima, 14 cents ($0.14 billed) | `results/colima/colima_audit.json`, `results/colima/calls_gemma.jsonl` (sum of `cost_usd`), via `app/colima.py` (the caption line is checked in `two-hands.srt`) |
| INE, 32 state institutes, outside auditors; 6 June 2027, 32 local elections | README "Business at a glance"; sources: `docs/BUSINESS.md` "Sources for the Business at a glance table" |
| $1 per sheet audited (proposed), paid shadow-mode pilot | `app/pricing.py` (a proposal), checked by `scripts/price_check.py --check` |
| Morelos: half a percent (our check of every sheet about MXN 143k, 0.5% of the MXN 26.6M it paid to run its 2024 PREP) | README "Business at a glance" (Example); `scripts/price_check.py --check` |

## Notes for the edit

- Slides: export each page of `two-hands-talk.pdf` as an image (or screen-record the PDF full screen) and hold it for
  the row's time. Cut between slide and site on a hard cut; no transitions longer than 0.3 s.
- On the site, highlight only the number the voice names (mouse pointer, or a box added in the edit). Never let a
  paragraph fill the frame without a pointer on one number.
- Never show a party logo close-up: crops of vote rows only; rows are "Option NN" in the app.
- Burn in captions from `two-hands.srt`; after recording, replace the bracketed numbers with what you said
  (`scripts/make_srt.py`, then rerun it).
- Credit card at the end (2 s, small): "Tally sheets: INE PREP 2024, free-use terms. Not an official INE product."
