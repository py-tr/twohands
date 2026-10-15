# Video script: Two Hands (target 3:55, hard limit 4:00)

Screen capture of the web app at {{DEMO_URL}}, 1920x1080, browser zoom 125%. One voice. Short sentences.
Slides appear only for the business and limits beats. Burn in captions.

Before recording: open the pages in tabs in this order: form 010441C0100 (accepted), form 211294C0100 (routed),
Overview, Audit, Review desk (form 141097C0100 open), form 211298B0100 (for the live read), a ledger sheet, Results.

| Time | On screen | Voice |
|---|---|---|
| 0:00-0:08 | Form viewer, **010441C0100**, accepted. The masked page on the left, the field table on the right, all green. Banner: "Accepted: 0 fields to key". | "This is a real paper tally sheet. A vision model on AMD read every field. Zero fields to type." |
| 0:08-0:20 | Slow scroll down the field table: digits column, words column, official capture column, all matching. Hover one green check. | "The model reads each number twice, from the digit boxes and from the words. Then code checks the form's own arithmetic. The model reads. The paper decides." |
| 0:20-0:40 | Switch to **211294C0100**. Red banner: "Routed: TOTAL digits 262, words 162, rows sum 262". Click the TOTAL crop; it opens beside the row. | "Here the paper disagrees with itself. The total says two six two in digits, and one hundred sixty-two in words. The rows add to two six two. The gate does not guess. It sends this one field to a person, with the crop." |
| 0:40-1:00 | **Overview** page, headline row. Zoom on the three numbers. | "We pre-registered a random sample of three hundred forms, before any model read them. {{RUN300_ACCEPT_RATE}} were accepted with no human touch. On those, {{RUN300_ACC_WRONG}} of {{RUN300_ACC_FIELDS}} fields were wrong." (If the run is not in: "On a hard pilot of forty-three forms, twenty-one were accepted with no human touch. Zero of their four hundred sixty-two fields were wrong.") |
| 1:00-1:25 | **Audit** page. Scroll the gallery of keying errors; pause on 211298B0100: image shows 39, capture keyed 34, certified 39. | "These forms were already typed twice by the official capture. On forms our gate accepted, we found six fields on five forms where the capture mis-typed. The image proves it. The certified count covers five of them, and matches the image on all five." |
| 1:25-1:50 | **Review desk**, form 141097C0100 ("Option 02 digits 38, words 138"). Show the crop: the word for one hundred is bracketed out by hand. Type 38. The identities re-check and stay green. Click "Re-check and resolve". | "Everything the paper cannot settle lands here. Here someone crossed out a word and rewrote it. A person sees only that field and its crop. They type one value. The arithmetic re-checks at once. If the paper itself is wrong, they escalate it with a note. Nothing is fixed silently." |
| 1:50-2:25 | Form **211298B0100**, click "Read live on AMD". The timer starts. Hard cut at about 0:05 on the timer to the moment the answer lands; **keep the timer visible in the corner** so the cut shows (for example 0:05 then {{LIVE_SECS}} s). Fields fill; the gate lights each identity. | "Now a live read on AMD. One request: the masked page and zoomed tiles, to Gemma 4 on the organisers' AMD Token Factory. We cut the wait. The timer shows it took {{LIVE_SECS}} seconds on a shared endpoint." Then say what the screen shows, for example: "Every identity holds. Accepted." or "One field fails, so it goes to the desk." Do not re-take until it accepts. |
| 2:25-2:45 | A **ledger sheet** (Ardnamurchan Lighthouse 1850-1859). Columns green and amber; the "Sum of months" row against "Written total". | "Same model, a different form from a different century. UK rainfall ledgers. Twelve months must add up to the clerk's total. On forty sheets, every one of the three thousand nine hundred seventy-six accepted cells matched the transcription by sixteen thousand volunteers." |
| 2:45-3:15 | Slide 10 (Who pays). | "Who pays? Mexico runs about thirty-two state-level counts in 2027. Each one types every tally sheet twice, under its own contract. The national programme cost two hundred seventy-three million pesos. On AMD, our reader costs about twelve cents per thousand forms. Auditing every national tally sheet costs twenty to eighty-six dollars. Then any form that checks itself: clinical trial forms, census sheets, archives." |
| 3:15-3:45 | **Results** page: "One failure, shown honestly", then the limitation box. | "Where does it break? On one ledger read as a single image, the model shifted a whole row by one year. Every sum still held, so twenty-six wrong cells got through. Zoomed tiles fixed it, and the tally sheet now checks every row label. The limit: our pilot is small, and the shared endpoint does about two forms a minute. A national run needs a dedicated AMD endpoint." |
| 3:45-3:55 | Overview page, top. Title only. | "Two Hands. The model reads, the paper decides." |

## Notes for the edit

- Something working is on screen from 0:00; a routed form with its failing field by 0:20-0:40; the headline
  number by 1:00.
- Never show a party name or logo close-up: crops of vote rows only; rows are "Option NN" in the app.
- Never say "fraud" or "election" in the voice-over; say "tally sheet", "keying error", "official capture".
- If the 300-form numbers are not in at recording time, use the pilot line given at 0:40 and drop the word
  "pre-registered" from that beat.
- Credit card at the end (2 s, small): "Tally sheets: INE PREP 2024, free-use terms. Not an official INE product.
  Rainfall ledgers: Rainfall Rescue, Hawkins et al. 2022, images linked not redistributed."
