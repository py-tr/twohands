# Recording guide: Two Hands video

Goal: one MP4, 1920x1080, about 4:05, under 300 MB. Script: [video-script.md](video-script.md). Captions:
[two-hands.srt](two-hands.srt) (regenerate with `python scripts/make_srt.py` after you edit the bracketed numbers).
Rules: max 5 min, MP4; under 3 min scores lower; the product must be working by 0:20; judges watch the first minute.

## 1. Recorder settings

**OBS Studio (preferred)**

- Settings > Video: Base and Output resolution **1920x1080**, FPS **30**.
- Settings > Output > Recording: format **MP4** (or MKV, then File > Remux to MP4), encoder hardware (AMF/NVENC) or
  x264, rate control CBR **8,000 kbps** (4 min = about 240 MB), audio 160 kbps.
- Sources: one **Display Capture** (the monitor with the browser) and **Audio Input Capture** (your mic). Turn off
  Desktop Audio (no notification sounds).
- Mic level: speak a normal sentence; the meter should peak in the **yellow, around -12 dB**, never red. Add filters
  on the mic: Noise Suppression (RNNoise), then Compressor (default), then Limiter at -3 dB.
- Hotkeys: set Start/Stop Recording and **Pause** (for example F9 / F10). Pause is how you cut long waits in one take.

**Windows Game Bar (fallback)**: Win+G > Capture settings: 30 fps, video quality Standard, record audio "Game only"
off, mic on. It records one window only: make the browser full screen (F11). Win+Alt+R starts and stops. No pause:
cut waits in an editor afterwards (Clipchamp, built into Windows 11: Split, delete, export 1080p).

## 2. Browser setup

- Chrome or Edge, a clean profile (no bookmarks bar, no extensions icons), **zoom 125%** (Ctrl and +), full screen
  F11 so the address bar is hidden; or windowed if you want the URL visible (judges like the real URL once).
- Close chat apps; turn on Windows Focus (no notifications).
- Open these tabs, in this order (left to right):
  1. **Home** `/` (scrolled to the top)
  2. **Station** `/station` (empty)
  3. **Audit** `/audit/new`
  4. **Form** `/form/211298B0100` (for the live read)
  5. **Try it** `/try?form=practice`
  6. **Evolus** workspace **py_tr**: workflow "Audit finding", executions list (logged in)
  7. **Results** `/results#limits` (scroll so the "3114 where the paper says 314" paragraph is in view)
  8. A **terminal** (Windows Terminal, font size 20) with the receipt check already run (below)

## 3. The day before (or one hour before)

- **Counter.** Note the "audited in total" number on Home; that is the [310] you say at 0:10.
- **Not-yet-read station.** On `/station`, check that `130011B0100` still says "Not audited yet". If the live audit
  has read it, pick another id from the same state that says "Not audited yet" and write it on a sticky note.
- **Receipt check in the terminal** (no model call):
  ```
  curl -sL https://<host>/verify/050815B0100/OPT07 -o receipt.json
  curl -s "https://<host>/crop/050815B0100/OPT07.jpg?pad=0.02&label=0" -o crop.jpg
  python -m twohands.verify_receipt receipt.json --crop crop.jpg
  ```
  It must end with `VERIFIED  root e56a8ef4f011b9e5...`. Leave that output on screen in the terminal tab.
- **Evolus case on Gemma.** The agent "Intake clerk" moved to Gemma-4-31B-IT on 2026-10-16; the recorded audit
  cases of 2026-10-15 were drafted on Qwen. Make one new case on Gemma: open the sample audit report and click
  **Open as Evolus cases** (or wait for the live worker's "Audit finding" runs). In the Evolus workspace, open that
  execution and check the agent step shows model `Gemma-4-31B-IT`. If you cannot get one on Gemma, change the
  2:30 line to "The agent runs on an open model on AMD" and do not say Gemma.
- **Practice sheet.** Print `static/sheet/two-hands-sheet.pdf`. Fill it by hand: each amount in words and in the
  digit boxes, rows 1-5 in Czech, rows 6-10 in English, TOTAL = the sum of rows 1 to 10 (check it with a
  calculator). Photograph it flat, from above, in even light, all four corner marks visible. Do one practice upload
  to see that the page registers.
- **Fallback live read.** Do one live read of 211298B0100 the day before while recording (OBS), keep the clip with
  the timer and the result. Note its UTC time for the label "recorded [time] UTC".

## 4. Checklist before each take

- [ ] Water, phone silent, window closed, Focus on.
- [ ] OBS: 1920x1080, 30 fps, mic peaks around -12 dB on a test sentence; Desktop Audio off.
- [ ] Browser zoom 125%, all tabs open in order, each scrolled to its starting point; Home at the top.
- [ ] AMD status: `/results#amd` shows "AMD live"; note if the reader is Gemma or Qwen (banner on the form).
- [ ] Not-yet-read station id on the sticky note.
- [ ] Terminal shows `VERIFIED`.
- [ ] Script printed in big font, bracketed numbers filled in by hand.
- [ ] Mouse moves slowly; no hovering over party logos; never zoom into a vote row's logo.

Record **one segment per take** if you like: it is easier to read short lines well. Leave 1 s of silence at the
start and end of each take, so cuts are clean.

## 5. Cutting the live-read wait (1:50 and 2:10)

The live read takes 40 s to several minutes on the shared endpoint. Show it honestly:

1. Click **Read live on AMD**. Say "Now a live read. One request to Gemma, on the AMD Token Factory. We cut the wait."
2. Let the **timer** run to about **0:05** on screen. Then **Pause** in OBS (or, in Game Bar, just keep recording).
3. When the result lands, **Resume** (or, in the editor, delete the waiting part). The timer jumps from 0:05 to the
   final time: that jump *is* the honest sign of the cut. Add a 0.3 s cross-fade and a small caption "wait cut".
4. Read the final time from the timer: "It took [ninety] seconds." Then say what the screen shows.
5. If it fails (HTTP 500, no answer after 5 minutes) do not re-take endlessly: use the fallback clip from the day
   before, with the caption "recorded [time] UTC", and say "This live read was recorded earlier today."

The same for the practice sheet at 2:10: drop the photo, pause, resume when the rows appear.

## 6. Captions

- `slides/two-hands.srt` has 61 captions timed to the script (4:05).
- After recording: if you said a different counter or time, edit those numbers in `scripts/make_srt.py`
  (the lines "310 forms" and "90 seconds"), run `python scripts/make_srt.py`, then shift the whole file if your
  video starts later (most editors: import SRT, then drag).
- Burn them in (judges often watch muted): Clipchamp > Captions > import is not supported, so use
  `ffmpeg -i two-hands.mp4 -vf "subtitles=slides/two-hands.srt:force_style='FontSize=22,MarginV=30'" -c:a copy two-hands-captioned.mp4`.
- Also upload the `.srt` with the video where the platform allows it.

## 7. Export

- MP4, H.264, 1920x1080, 30 fps, AAC audio. Check the length (3:30-4:30; never over 4:59) and size (< 300 MB).
- Watch the first 60 seconds once with sound off: the receipt, the one sentence, the station pick must be clear
  from the captions alone.

## 8. Minimum viable video (if time is short): 60 seconds of recording, 3:10+ total

If you have under one hour, record only these four takes, then pad to over three minutes with slides from
`slides/slides.md` (PDF) and the voice lines of the other segments over them:

| Take | Length | What |
|---|---|---|
| A | 0:00-0:20 | Home receipt + counter (script lines 1-2). |
| B | 0:20-0:40 | Station pick: one measured id, one "Not audited yet" (script line 3). |
| C | 0:20 | Sample audit: Run the sample audit, the report, one receipt (script line 6). No live read. |
| D | 0:10 | Close (script line 12). |

Then over static screenshots from `slides/shots/` (pan slowly, no new recording): How it works (`01_home.png`
scrolled), Measured (`04_home_measured.png`), Who pays (`10_home_ine.png`), Limits (`11_res_digit.png`), with their
voice lines recorded as audio only. That is about 3:30 with no live read and no Evolus clip; say in the
description that the live read is on the site. Never publish under 3:00.
