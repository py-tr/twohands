# Video script: Two Hands (final, 4:05; limit 5:00, floor 3:00)

One voice, English, short sentences. Screen capture of the hosted app, 1920x1080, browser zoom 125%.
Captions: [two-hands.srt](two-hands.srt).
Reference screenshots of each state (taken from the app on 2026-10-16): [`shots/`](shots/).

Words in **[brackets]** are read off the screen on the day (they change). Everything else is said exactly as written.
Speak slowly: about two words a second. If a line runs long, cut a sentence from the end of the segment, never speed up.

| Time | On screen (page, exact action) | Voice (exact words) |
|---|---|---|
| **0:00-0:08** | **Title card** burned in over the first 8 s, top of frame: "Two Hands" and, below it, "OCR reads the number. Two Hands checks whether the whole form agrees." Under it, a real acta: **Form** `/form/122655C0100`, the masked page at full height, still. In the edit, a highlight box on the Option 02 row (the same crop as `/trace#routed`, step 1). Shot: `shots/00_trace_page.png` (to take on the day). | "OCR reads the number. Two Hands checks whether the whole form agrees." |
| **0:08-0:22** | **Trace** (`/trace#routed`), form 122655C0100. Scroll slowly: step 2, the raw item `{"n": 23, "w": 23}` (point at 23 and 23); step 3, the identity row "rows sum to TOTAL ... **366** / **466** FAIL" (point at 366, then 466); step 4, "Routed to a person" and "With the paper's 123, rows sum to TOTAL gives 466 = 466". Real case, stored read; nothing typed on screen. | "Gemma, on AMD, reads twenty-three, in digits and in words. The rows sum to three hundred sixty-six, not four hundred sixty-six. Routed to a person. The paper says one hundred twenty-three." |
| **0:22-0:33** | Same page, step 6: the leaf, the proof path, then the four "ok" lines and **VERIFIED** (point at it). Then 2 s on the terminal tab: `VERIFIED  root e56a8ef4...` for this receipt (pre-run, see the guide). | "Every field gets a receipt. Verified: it proves the record is unchanged. Not that the reading is right." |
| **0:33-0:53** | **Home** (`/`), the receipt card: form 050815B0100, Option 07, "The paper: 175 · The first capture keyed: ~~75~~ · The certified count: 175" (one of the 49). Then cut to the repository page, README first screen: point at "1,270 real handwritten tally sheets" and "49 capture errors confirmed by the certified count", then at "91.6%" and "62.84%" in the "Against the incumbent" bullet. | "One thousand two hundred seventy real tally sheets, read by Gemma on AMD. Forty-nine capture errors, confirmed by the certified count. On the state's own local actas, ninety-one point six percent field match, where the AI tool the state bought scored sixty-three." |
| **0:53-1:06** | **Home**, the **Who pays** card (`10_home_ine.png`): point at "$1 per sheet audited (proposed); first step: a paid shadow-mode pilot". | "One dollar per sheet audited. The first step: a paid shadow-mode pilot, on one state's count in twenty twenty-seven." |
| **1:06-1:31** | **Home**, scroll up to **Measured, not promised** (`04_home_measured.png`): point at "52", then at the line "fix confirmed on 100 fresh forms: 0 wrong of 484" in the second card. | "Measured, not promised. Three hundred random forms, chosen before any model read. Fifty-two fields where the capture does not match the paper. Then we tested the fix on one hundred new forms. Zero wrong, in four hundred eighty-four accepted fields. With ninety-five percent confidence, fewer than one in a hundred." |
| **1:31-1:56** | Click **Audit your capture** (`/audit/new`). Click **Run the sample audit**: "267 disputed fields in 6,358 checked" (`05_au1_audit.png`). Click **Printable report**: point at "Merkle root e56a8ef4f011b9e5" (`06_au2_report.png`). Scroll to Option 07 of 050815B0100, click its **receipt** link: the JSON, point at `"root": "e56a8ef4..."`. Cut to the terminal tab: the line `VERIFIED root e56a8ef4...` (pre-run, see the guide). | "This is the product. An auditor brings the typed data and the scans. Here, the sample: six thousand fields, checked in seconds. Two hundred sixty-seven disputes, strongest first. Each has its photo and a receipt. One fingerprint seals the whole report. Change one number, and the check fails." |
| **1:56-2:04** | **Results** (`/results#colima`): the block "Colima, the whole state"; point at "1,017 presidential sheets in the PREP", "982 located and read" and the cost, then the line "One reader, frozen gate: ... 13 of 8,382 on a whole state". Do not read the rest. | "A whole state: Colima. Gemma on AMD read all nine hundred eighty-two sheets for fourteen cents." |
| **2:04-2:20** | Form **211298B0100** (`/form/211298B0100`, `07_form_211298B0100.png`). Scroll to the live panel, click **Read live on AMD**. The timer starts. At about 0:05 on the timer, **hard cut** to the moment the answer lands; the timer stays visible in the corner, so the cut shows. Fields fill; the gate lights each check. **Fallback** (endpoint down, or a Qwen banner you do not want): the recorded read from the guide, with the on-screen label "recorded [time] UTC". | "Now a live read. One request to Gemma, on the AMD Token Factory. We cut the wait. The timer stays on screen. It took **[ninety]** seconds. Every check holds: accepted." If one check fails, say instead: "One check fails, so it goes to a person." If the banner says Qwen, say "One request to Qwen, on the AMD Token Factory." Fallback: replace "Now a live read" with "This live read was recorded earlier today." |
| **2:20-2:35** | **Try it** (`/try`), select **Practice sheet (any language)** (`08_try_practice.png`); the "Demonstration, not a measurement" badge shows. Hold your own filled sheet to the camera for 2 s (or show its photo), then drop the photo; cut the wait as above; the result page shows each row's words and digits and the verdict. Caption burned in: "Demonstration, not a measurement." | "Arithmetic has no language. I filled this practice sheet by hand, in Czech and in English. This is a demonstration, not a measurement." |
| **2:35-2:52** | **Evolus** tab: workspace **py_tr**, workflow **Audit finding**, executions list; open the newest run (drafted on Gemma, see the guide) to its three-sentence finding and the score step "Recompute the evidence score (no AI)". Then 2 s on the agent **Intake clerk**: model `Gemma-4-31B-IT`. Shot of the site side: `09_res_evolus.png`. | "Each strong finding becomes a case in Evolus. The agent runs on Gemma, on AMD, and drafts the finding. A script, not the model, scores the evidence. The auditor decides." |
| **2:52-3:20** | **Home**, scroll to the **Who pays** card (`10_home_ine.png`): point at "MXN 9.5M" and "80%", then at "first step: a paid shadow-mode pilot" in the price line. On "Next", cut to the deck slide **Business at a glance** (`two-hands-slides.pdf`) and point at its "Next" row. | "Who pays? Mexico's preliminary counts: INE, thirty-two state institutes, and their outside auditors. On June sixth, twenty twenty-seven, thirty-two local elections join the federal midterm. The pilot runs beside the state's own capture; nothing in its process changes. Next: seven more countries publish these sheets, and health reporting in seventy-plus countries runs on DHIS2." Leave "83.5% ... as we read it", its caveat "not the same test set" and "$0.14 per 1,000 forms" on screen; do not read them. |
| **3:20-3:43** | **Home**, back to the receipt card: point at the crop (the photo), then "The first capture keyed", then "The certified count" as each is named. On "Elections are our proof set", cut to the deck slide **The next markets, not measured** (`two-hands-slides.pdf`), its "Why elections" line. | "Most paper records are private, by law or by contract: patient charts, loan files, drug registers, so nobody can publish an error rate on them. Mexico's tally sheets are the clearest exception: the photo, the keyed value and the certified count are all public. Elections are our proof set, not our only market." |
| **3:43-3:59** | **Results** (`/results`), click **Limitations** in "On this page", scroll to the paragraph "On the same 100 forms the original gate would have accepted one wrong field: the model read 3114 where the paper says 314" (`11_res_digit.png`). Point at 3114 and 314. | "Where does it fail? Once, the model read three thousand one hundred fourteen. The paper says three hundred fourteen. One digit added. The first gate would accept it. Gate version two sent it to a person." |
| **3:59-4:05** | **Home**, top of page: the receipt card and the counter. Stay still. Last 2 s: credit card (small text, see notes). | "Two Hands. Receipts for every number keyed from paper. Running on AMD." |

Total: 4:05 (plus a 2 s credit card: 4:07). Product on screen from 0:00: a real form read, checked by its arithmetic and routed by 0:22, its receipt verified by 0:33.

## Words never to say

- "fraud"; "election" as a product word (the product is "Two Hands", the thing is "a tally sheet", "a form");
  party names; vote totals.
- "errors" for the 52: say "fields where the capture does not match the paper" (or "capture errors").
- The INE metric is always said with "as we read it, computed after the fact". Never "we passed INE's test",
  never "we beat INE's bar".
- "Confirmed by a person": not for the AI-adjudicated fields.
- The receipt "proves the record is unchanged", never "proves the reading is right".

## Numbers used, and where they come from

| Spoken | Source |
|---|---|
| Hook: "OCR reads the number. Two Hands checks whether the whole form agrees." | README subtitle; title slide |
| 23 (digits and words), 366 / 466, 123 (122655C0100, Option 02); receipt VERIFIED, root e56a8ef4... | `docs/TRACE.md` (`/trace#routed`), generated by `scripts/build_trace.py` from `results/calls_gemma.jsonl` |
| 175 / 75 / 175 (050815B0100, Option 07) | `results/adjudication/CERTIFIED.md`; Home receipt card |
| 1,270 sheets, 49 capture errors confirmed by the certified count | README first screen; recomputed by `scripts/price_check.py --check` |
| 91.6% field match vs 63 (62.84%) for the Google Document AI reading Baja California Sur bought (same per-field metric; pre-registered random 300 actas) | README "Against the incumbent"; `results/ieebcs/score.json`, checked by `scripts/ieebcs_score.py --check` |
| 300 random, 52 fields | `app/data/headline.json`; README headline |
| 0 of 484 on 100 new forms; "fewer than one in a hundred" = Wilson 95% upper bound 0.79% | `results/confirm100.md` (gate v2) |
| 6,358 fields, 267 disputes, root e56a8ef4... | `/audit/new` sample; `results/sample_audit_root.txt` |
| MXN 9.5M, 80% bar (on screen only) | INE CCOE report pp. 4-5, via `docs/BUSINESS.md` |
| 83.5% (on screen only, not spoken: as we read it, computed after the fact) | `results/ine_metric.md` |
| INE, 32 state institutes, outside auditors; 6 June 2027, 32 local elections (operator chosen by December: on screen only) | README "Business at a glance"; sources: `docs/BUSINESS.md` "Sources for the Business at a glance table" |
| $1 per sheet audited (proposed), paid shadow-mode pilot (spoken at 0:53) | `app/pricing.py` (a proposal) |
| 7 more countries; DHIS2 in 70+ countries | `docs/BUSINESS.md` "Sources for the Business at a glance table" |
| $0.14 per 1,000 forms (on screen only) | `docs/GEMMA.md` 2.5 |
| 982 sheets of Colima, 14 cents ($0.14 billed); 13 of 8,382 on screen only | `results/colima/colima_audit.json`, `results/colima/calls_gemma.jsonl` (sum of `cost_usd`), via `app/colima.py` |
| 3114 for 314 (070212B0100, unused ballots), caught by v2 | `results/confirm100.md`; Results "Limitations" |

## Notes for the edit

- Never show a party logo close-up: crops of vote rows only; rows are "Option NN" in the app.
- Burn in captions from `two-hands.srt`; after recording, replace the bracketed numbers with what you said.
- Credit card at the end (2 s, small): "Tally sheets: INE PREP 2024, free-use terms. Not an official INE product.
  Practice sheet: a demonstration, not a measurement."
