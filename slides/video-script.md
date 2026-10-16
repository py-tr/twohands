# Video script: Two Hands (final, 4:05; limit 5:00, floor 3:00)

One voice, English, short sentences. Screen capture of the hosted app, 1920x1080, browser zoom 125%.
How to record, tabs, cuts and captions: [recording-guide.md](recording-guide.md). Captions: [two-hands.srt](two-hands.srt).
Reference screenshots of each state (taken from the app on 2026-10-16): [`shots/`](shots/).

Words in **[brackets]** are read off the screen on the day (they change). Everything else is said exactly as written.
Speak slowly: about two words a second. If a line runs long, cut a sentence from the end of the segment, never speed up.

| Time | On screen (page, exact action) | Voice (exact words) |
|---|---|---|
| **0:00-0:10** | **Home** (`/`), first screen, nothing moving. The receipt card: form 050815B0100, Option 07, crop with "ciento setenta y cinco" and boxes 1 7 5; "The paper: 175 · The first capture keyed: ~~75~~ · The certified count: 175". Move the mouse slowly under "175", then "75", then "175". Shot: `shots/01_home.png`. | "The paper says one hundred seventy-five. The official capture typed seventy-five. The certified count says one hundred seventy-five." |
| **0:10-0:20** | Same screen. Move the mouse to the counter card on the right: "**[310]** audited in total" and the line "reader: Gemma-4-31B-IT ... on AMD Token Factory". | "Two Hands checks every number typed from paper, against the paper. On AMD, **[three hundred ten]** forms audited so far." |
| **0:20-0:40** | Click **Pick any polling station**. Type `050815B0100`, press Enter: the masked page and "in a measured sample · instant answer" appear at once; scroll a little to the Option 07 receipt. Then select the id, type `130011B0100` (or the not-yet-read id you picked, see the guide), Enter: "Not audited yet". Click **Queue a live read on AMD**; the queue position appears. Shots: `02_st2_have.png`, `03_st3_not.png`. | "Pick any polling station. One hundred sixty-nine thousand of them. This one we have read: the page and its receipts, at once. This one, not yet. One click, and the reader on AMD takes it next." |
| **0:40-1:00** | **Home**, scroll to **How it works**: the three steps (01 image, 02 model on AMD, 03 deterministic gate) and the two outcomes "Accepted, 0 fields to key" / "Dispute, with its photo". Point at each step as you name it. | "How does it work? Two hands. The model on AMD reads every number twice: the digits, and the words. Then the gate: the form's own arithmetic. If it all adds up, nobody types anything. If not, a person sees the rest, with the photo." |
| **1:00-1:25** | **Home**, scroll up to **Measured, not promised** (`04_home_measured.png`): point at "52", then at the line "fix confirmed on 100 fresh forms: 0 wrong of 484" in the second card. | "Measured, not promised. Three hundred random forms, chosen before any model read. Fifty-two fields where the capture does not match the paper. Then we tested the fix on one hundred new forms. Zero wrong, in four hundred eighty-four accepted fields. That is not proof of zero. It means: fewer than one in a hundred." |
| **1:25-1:50** | Click **Audit your capture** (`/audit/new`). Click **Run the sample audit**: "267 disputed fields in 6,358 checked" (`05_au1_audit.png`). Click **Printable report**: point at "Merkle root e56a8ef4f011b9e5" (`06_au2_report.png`). Scroll to Option 07 of 050815B0100, click its **receipt** link: the JSON, point at `"root": "e56a8ef4..."`. Cut to the terminal tab: the line `VERIFIED root e56a8ef4...` (pre-run, see the guide). | "This is the product. An auditor brings the typed data and the scans. Here, the sample: six thousand fields, checked in seconds. Two hundred sixty-seven disputes, strongest first. Each has its photo and a receipt. One fingerprint seals the whole report. Change one number, and the check fails." |
| **1:50-2:10** | Form **211298B0100** (`/form/211298B0100`, `07_form_211298B0100.png`). Scroll to the live panel, click **Read live on AMD**. The timer starts. At about 0:05 on the timer, **hard cut** to the moment the answer lands; the timer stays visible in the corner, so the cut shows. Fields fill; the gate lights each check. **Fallback** (endpoint down, or a Qwen banner you do not want): the recorded read from the guide, with the on-screen label "recorded [time] UTC". | "Now a live read. One request to Gemma, on the AMD Token Factory. We cut the wait. The timer stays on screen. It took **[ninety]** seconds. Every check holds: accepted." If one check fails, say instead: "One check fails, so it goes to a person." If the banner says Qwen, say "One request to Qwen, on the AMD Token Factory." Fallback: replace "Now a live read" with "This live read was recorded earlier today." |
| **2:10-2:30** | **Try it** (`/try`), select **Practice sheet (any language)** (`08_try_practice.png`); the "Demonstration, not a measurement" badge shows. Hold your own filled sheet to the camera for 2 s (or show its photo), then drop the photo; cut the wait as above; the result page shows each row's words and digits and the verdict. Caption burned in: "Demonstration, not a measurement." | "Arithmetic has no language. I filled this practice sheet by hand, in Czech and in English. The model reads my words and my digits. The sums decide. This is a demonstration, not a measurement." |
| **2:30-2:50** | **Evolus** tab: workspace **py_tr**, workflow **Audit finding**, executions list; open the newest run (drafted on Gemma, see the guide) to its three-sentence finding and the score step "Recompute the evidence score (no AI)". Then 2 s on the agent **Intake clerk**: model `Gemma-4-31B-IT`. Shot of the site side: `09_res_evolus.png`. | "Each strong finding becomes a case in Evolus. This is our workspace, P Y T R. The agent runs on Gemma, on AMD, and drafts the finding. A script, not the model, scores the evidence. The auditor decides." |
| **2:50-3:30** | **Home**, scroll to **The cost of the problem**: hold on the three-line paragraph ("The problem: ... The gap: ... The buyer: ..."). Then scroll to the **Who pays** card (`10_home_ine.png`): point at "MXN 9.5M", "80%", then the grey box "83.5% ... as we read it" and its italic caveat, then "$1 per form audited" in the counter card or Who pays line. | "Who pays? The problem, in three lines from INE's own files. One: on six and a half percent of stations, two official records of one paper disagree. Two: almost one form in five fails its own row sum. Three: the audit checks the software, not the typed numbers. INE budgeted nine and a half million pesos for this, with an eighty percent bar. On that metric, as we read it, computed after the fact, we reach eighty-three and a half. State institutes buy it, at one dollar per form." Leave the caveat "not the same test set" and "$0.14 per 1,000 forms" on screen; do not read them. |
| **3:30-3:55** | **Results** (`/results`), click **Limitations** in "On this page", scroll to the paragraph "On the same 100 forms the original gate would have accepted one wrong field: the model read 3114 where the paper says 314" (`11_res_digit.png`). Point at 3114 and 314. | "Where does it fail? Unused ballots sit in no sum, so arithmetic cannot check them. Once, the model read three thousand one hundred fourteen. The paper says three hundred fourteen. One digit added. The first gate would accept it. Gate version two sent it to a person." |
| **3:55-4:05** | **Home**, top of page: the receipt card and the counter. Stay still. Last 2 s: credit card (small text, see notes). | "Two Hands. Receipts for every number keyed from paper. Running on AMD." |

Total: 4:05 (plus a 2 s credit card: 4:07). Product on screen from 0:00; a working action (station pick) by 0:20.

## Words never to say

- "fraud"; "election" as a product word (the product is "Two Hands", the thing is "a tally sheet", "a form");
  party names; vote totals.
- "errors" for the 52: say "fields where the capture does not match the paper" (or "capture errors").
- The INE metric is always said with "as we read it, computed after the fact". Never "we passed INE's test",
  never "we beat INE's bar".
- "Confirmed by a person": not for the AI-adjudicated fields.

## Numbers used, and where they come from

| Spoken | Source |
|---|---|
| 175 / 75 / 175 (050815B0100, Option 07) | `results/adjudication/CERTIFIED.md`; Home receipt card |
| [310] audited | Home counter (read on the day) |
| 169,005 stations | `/station` header |
| 300 random, 52 fields | `app/data/headline.json`; README headline |
| 0 of 484 on 100 new forms; "fewer than one in a hundred" = Wilson 95% upper bound 0.79% | `results/confirm100.md` (gate v2) |
| 6,358 fields, 267 disputes, root e56a8ef4... | `/audit/new` sample; `results/sample_audit_root.txt` |
| 6.5% of stations, 19.2% fail their row sum, audit checks the software | `docs/BUSINESS.md` "In three sentences", "The cost of the problem" |
| MXN 9.5M, 80% bar | INE CCOE report pp. 4-5, via `docs/BUSINESS.md` |
| 83.5% (as we read it, computed after the fact) | `results/ine_metric.md` |
| $1 per form; $0.14 per 1,000 forms | README "Who pays"; `docs/GEMMA.md` 2.5 |
| 3114 for 314 (070212B0100, unused ballots), caught by v2 | `results/confirm100.md`; Results "Limitations" |

## Notes for the edit

- Never show a party logo close-up: crops of vote rows only; rows are "Option NN" in the app.
- Burn in captions from `two-hands.srt`; after recording, replace the bracketed numbers with what you said.
- Credit card at the end (2 s, small): "Tally sheets: INE PREP 2024, free-use terms. Not an official INE product.
  Practice sheet: a demonstration, not a measurement."
