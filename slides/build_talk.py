"""The talk deck for the video: slides/talk.html (1920x1080 per slide) -> slides/talk/slide_N.png and
slides/two-hands-talk.pdf.

usage (repo root):  python slides/build_talk.py
Look: the web app's own tokens (static/style.css :root: paper background, ink, one accent, ok/bad used sparingly;
Inter + JetBrains Mono; the mark from static/mark.svg), so the slides and the demo read as one product.
Product visuals come from slides/talk/assets/ (captured from the running app by slides/capture_talk.py) and the
masked crops in slides/. Every number is copied from README.md, submission/lablab.md, docs/BUSINESS.md,
docs/EVALUATION.md and docs/EVOLUS.md, which `make eval` checks. Speaker notes (the detail cut from the slides) sit
in each slide's <aside class="notes">, hidden when rendered. No model call.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

S = Path(__file__).resolve().parent
OUT = S / "talk"
A = "talk/assets/"  # relative to talk.html
MARK = (S.parent / "static" / "mark.svg").read_text(encoding="utf8")

CSS = """
@page { size: 1920px 1080px; margin: 0; }
:root {
  --bg: #f5f5f2; --surface: #ffffff; --ink: #14161b; --ink-2: #2c3039; --muted: #5f6673; --faint: #969ca7;
  --line: #e2e2dc; --accent: #3047c0; --accent-soft: #eceffc; --ok: #157042; --bad: #b3261e;
  --sans: "Inter", "Segoe UI", system-ui, sans-serif; --mono: "JetBrains Mono", Consolas, monospace;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--sans); }
.slide { width: 1920px; height: 1080px; padding: 112px 120px 0; position: relative; overflow: hidden; page-break-after: always; background: var(--bg); }
.notes { display: none; }
.g { display: grid; grid-template-columns: repeat(12, 1fr); column-gap: 40px; align-items: start; }
.c3 { grid-column: span 3; } .c4 { grid-column: span 4; } .c5 { grid-column: span 5; } .c6 { grid-column: span 6; }
.c7 { grid-column: span 7; } .c8 { grid-column: span 8; } .c12 { grid-column: span 12; }
.kicker { font-size: 20px; font-weight: 600; letter-spacing: 2.4px; text-transform: uppercase; color: var(--muted); margin-bottom: 22px; }
h1 { font-size: 112px; font-weight: 650; letter-spacing: -3px; line-height: 1; margin: 0; }
h2 { font-size: 58px; font-weight: 600; letter-spacing: -1.2px; line-height: 1.12; margin: 0 0 56px; max-width: 1600px; }
h2 .mute { color: var(--muted); }
p, li { font-size: 26px; line-height: 1.45; color: var(--ink-2); margin: 0; }
.lead { font-size: 34px; line-height: 1.35; color: var(--ink-2); }
.acc { color: var(--accent); } .bad { color: var(--bad); } .ok { color: var(--ok); } .muted { color: var(--muted); }
b { font-weight: 600; color: var(--ink); }
.mono { font-family: var(--mono); font-size: .92em; }
.foot { position: absolute; left: 120px; right: 120px; bottom: 48px; display: flex; justify-content: space-between; align-items: center;
        font-size: 18px; color: var(--faint); border-top: 1px solid var(--line); padding-top: 18px; }
.foot .brand { display: flex; align-items: center; gap: 10px; color: var(--muted); font-weight: 600; }
.foot .brand svg { width: 22px; height: 22px; }
.foot .n { font-variant-numeric: tabular-nums; }
/* facts: hairline-separated lines */
.facts > div { border-top: 1px solid var(--line); padding: 22px 0 24px; }
.facts > div:last-child { border-bottom: 1px solid var(--line); }
.facts .k { font-size: 18px; font-weight: 600; letter-spacing: 1.8px; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }
.facts p { font-size: 27px; }
.facts.tight > div { padding: 15px 0 17px; } .facts.tight p { font-size: 23px; }
.stat .l { font-variant-numeric: tabular-nums; }
/* stat row */
.stats { display: grid; column-gap: 40px; border-top: 1px solid var(--ink); }
.stat { padding-top: 22px; }
.stat .v { font-size: 68px; font-weight: 600; letter-spacing: -1.5px; line-height: 1; font-variant-numeric: tabular-nums; }
.stat .v small { font-size: 32px; font-weight: 500; color: var(--muted); letter-spacing: 0; }
.stat .l { font-size: 22px; line-height: 1.35; color: var(--muted); margin-top: 14px; }
/* frames */
.frame { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; box-shadow: 0 1px 2px rgba(20,22,28,.04), 0 12px 32px rgba(20,22,28,.07); overflow: hidden; }
.frame img { display: block; width: 100%; }
.cap { font-size: 19px; color: var(--faint); margin-top: 14px; line-height: 1.4; }
/* annotated crop */
.ann { position: relative; }
.ann .img { border: 1px solid var(--line); border-radius: 6px; overflow: hidden; background: #fff; }
.ann .img img { display: block; width: 100%; }
.ann svg.lines { position: absolute; left: 0; top: 0; overflow: visible; pointer-events: none; }
.ann .lbl { position: absolute; font-size: 25px; line-height: 1.3; color: var(--ink); white-space: nowrap; }
.ann .lbl .sm { display: block; font-size: 19px; color: var(--muted); }
/* pipeline */
.steps { display: grid; grid-template-columns: repeat(5, 1fr); column-gap: 0; border-top: 1px solid var(--ink); }
.st { padding: 26px 40px 0 0; position: relative; }
.st .no { font-family: var(--mono); font-size: 20px; color: var(--accent); font-weight: 600; }
.st .t { font-size: 36px; font-weight: 600; margin: 14px 0 12px; letter-spacing: -.3px; }
.st p { font-size: 25px; color: var(--muted); line-height: 1.4; }
.st .arr { position: absolute; right: 12px; top: -13px; color: var(--faint); font-size: 22px; background: var(--bg); padding: 0 4px; }
/* bars */
.bars .row { display: grid; grid-template-columns: 500px 1fr; align-items: center; column-gap: 32px; margin-bottom: 48px; }
.bars .name { font-size: 26px; font-weight: 600; } .bars .name span { display: block; font-size: 20px; font-weight: 400; color: var(--muted); margin-top: 4px; }
.bars .trk { display: flex; align-items: center; gap: 22px; }
.bars .bar { height: 104px; }
.bars .val { font-size: 60px; font-weight: 600; letter-spacing: -1px; font-variant-numeric: tabular-nums; }
/* table */
table { border-collapse: collapse; width: 100%; font-size: 25px; }
td.r { font-variant-numeric: tabular-nums; }
th { font-size: 17px; font-weight: 600; letter-spacing: 1.6px; text-transform: uppercase; color: var(--muted); text-align: left; padding: 0 18px 14px 0; border-bottom: 1px solid var(--ink); }
td { padding: 18px 18px 18px 0; border-bottom: 1px solid var(--line); color: var(--ink-2); }
td.r, th.r { text-align: right; }
tr.hi td { color: var(--ink); font-weight: 600; }
/* dots */
.dots { display: grid; grid-template-columns: repeat(10, 60px); gap: 18px; }
.dot { width: 60px; height: 60px; border-radius: 50%; background: var(--accent); }
.dot.miss { background: transparent; border: 3px solid var(--bad); }
pre.cmd { font-family: var(--mono); font-size: 24px; color: var(--ink); background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px 20px; margin: 10px 0 0; white-space: pre-wrap; }
.wordmark { display: flex; align-items: center; gap: 18px; font-size: 26px; font-weight: 600; color: var(--ink); margin-bottom: 70px; }
.wordmark svg { width: 44px; height: 44px; }
"""

N = 9


def foot(i: int, last: bool = False) -> str:
    right = f'{i:02d}'  # the repo URL is set large on the last slide itself
    return f'<div class="foot"><span class="brand">{MARK}Two Hands</span><span class="n">{right}</span></div>'


def slide(i: int, body: str, notes: str = "", last: bool = False) -> str:
    return f'<section class="slide">{body}<aside class="notes">{notes}</aside>{foot(i, last)}</section>'


def annotated(src: str, alt: str, width: int, iw: int, ih: int, notes, band: int = 120) -> str:
    """A masked crop with thin leader lines to labels set below it; nothing is drawn over the handwriting.
    notes: (x, y, label_x, text, sub, colour, half_width, drop_x): a bracket centred at x, half_width wide, at height y
    (fractions; y sits just BELOW the digits or words it names, ticks pointing up at them), a leader dropping from
    drop_x (default x, chosen to run between handwritten marks) to the label whose left edge is label_x."""
    h = round(width * ih / iw)
    svg, lbls = [], []
    for note in notes:
        x, y, lx, text, sub, col = note[:6]
        hw = note[6] if len(note) > 6 else 0.04
        dx = note[7] if len(note) > 7 and note[7] is not None else x
        px0, px1, py, pd = (x - hw) * width, (x + hw) * width, y * h, dx * width
        ly = h + 28  # labels share one baseline
        tx = lx * width
        svg.append(f'<polyline points="{px0:.0f},{py - 6:.0f} {px0:.0f},{py:.0f} {px1:.0f},{py:.0f} {px1:.0f},{py - 6:.0f}" '
                   f'fill="none" stroke="{col}" stroke-width="2.5"/>'
                   f'<polyline points="{pd:.0f},{py:.0f} {pd:.0f},{h + 14:.0f} {tx:.0f},{h + 14:.0f} {tx:.0f},{ly:.0f}" '
                   f'fill="none" stroke="{col}" stroke-width="1.5"/>')
        lbls.append(f'<div class="lbl" style="left:{tx:.0f}px;top:{ly + 6:.0f}px;border-left:2px solid {col};padding-left:14px">'
                    f'{text}<span class="sm">{sub}</span></div>')
    return (f'<div class="ann" style="width:{width}px;height:{h + band}px"><div class="img"><img src="{src}" alt="{alt}"></div>'
            f'<svg class="lines" width="{width}" height="{h + band}">{"".join(svg)}</svg>{"".join(lbls)}</div>')


INK, ACC, BAD, OK = "#14161b", "#3047c0", "#b3261e", "#157042"
slides = []

# 1. Title: the whole masked page once (cut left of the masked names-and-signatures column), the unused-ballots field
# highlighted, a zoomed inset of it (pointers only to what the paper says) and, beside it, the two records as a ledger
PW, PH = 600, round(600 * 1552 / 1560)               # masked page 080310B0100, cropped to 1560 x 1552
PX, PY = 1200, 112
K = PW / 1560                                        # page px -> slide px
HB = (29 * K - 3, 875 * K - 3, 744 * K + 6, 96 * K + 6)  # the Unused ballots field (app/crops.py box 0.012-0.322 x 0.564-0.626)
IX, IY, IW = 500, 476, 640                           # the inset (the ledger sits left of it)
IH = round(IW * 158 / 744)
LEDGER = "font-size:18px;font-weight:600;letter-spacing:1.6px;text-transform:uppercase;color:var(--muted)"
slides.append(slide(1, f"""
  <div style="position:absolute;left:120px;top:92px;width:1000px">
    <div class="wordmark" style="margin-bottom:26px">{MARK}<span>AMD Developer Hackathon ACT III</span></div>
    <h1 style="font-size:96px">Two Hands</h1>
    <p class="lead" style="margin-top:18px;font-size:34px;color:var(--ink);font-weight:500">Verifiable quality control for handwritten numbers.</p>
    <p class="lead" style="margin-top:10px;font-size:28px;color:var(--muted)">OCR reads the number. Two Hands checks whether the whole form agrees.</p>
    <p style="margin-top:12px;font-size:21px;line-height:1.4;color:var(--ink-2);font-weight:500">For the institutes that run Mexico's vote counts and their auditors, and any handwritten form whose numbers must add up.</p>
  </div>
  <div style="position:absolute;left:{PX}px;top:{PY}px;width:{PW}px">
    <div class="frame" style="position:relative;border-radius:6px"><img src="{A}masked_080310B0100_left.jpg" alt="Tally sheet 080310B0100, privacy-masked; the masked names-and-signatures column is left out of the frame">
      <div style="position:absolute;left:{HB[0]:.0f}px;top:{HB[1]:.0f}px;width:{HB[2]:.0f}px;height:{HB[3]:.0f}px;border:2px solid var(--accent);border-radius:3px"></div></div>
    <p class="cap" style="margin-top:10px">Tally sheet 080310B0100 (INE 2024), privacy-masked.</p>
  </div>
  <svg style="position:absolute;left:0;top:0;pointer-events:none" width="1920" height="760">
    <line x1="{PX + HB[0]:.0f}" y1="{PY + HB[1] + HB[3] / 2:.0f}" x2="{IX + IW}" y2="{IY + IH / 2:.0f}" stroke="#3047c0" stroke-width="1.5"/>
  </svg>
  <div style="position:absolute;left:{IX}px;top:{IY}px">
    {annotated(A + "crop_080310B0100_SOBRANTES.jpg", "Unused ballots on form 080310B0100: words 'ciento ochenta' (180), boxes 1 8 0", IW, 744, 158, [
        (0.365, 0.66, 0.0, "In words: ciento ochenta (180)", "the paper", ACC, 0.185),
        (0.90, 0.64, 0.62, "In digits: 180", "the paper", ACC, 0.08)], band=96)}
  </div>
  <div style="position:absolute;left:120px;top:{IY - 6}px;width:340px">
    <div style="{LEDGER};margin-bottom:4px">Unused ballots: two records of one number</div>
    <table>
      <tr><td style="color:var(--muted);font-size:22px">Official typed capture (PREP)</td><td class="r" style="font-size:34px;font-weight:600;color:var(--bad)">480</td></tr>
      <tr><td style="color:var(--muted);font-size:22px">Gemma read</td><td class="r" style="font-size:34px;font-weight:600">180</td></tr>
    </table>
  </div>
  <div class="stats" style="grid-template-columns:repeat(4,1fr);position:absolute;left:120px;right:120px;top:772px">
    <div class="stat"><div class="v" style="font-size:60px">1,270</div><div class="l">real handwritten tally sheets read by Gemma on AMD</div></div>
    <div class="stat"><div class="v" style="font-size:60px">91.6%</div><div class="l">field match, vs 62.84% for the reading the state bought</div></div>
    <div class="stat"><div class="v" style="font-size:60px">27<small> of 28</small></div><div class="l">capture errors the certified count reveals, caught (one state, pre-registered)</div></div>
    <div class="stat"><div class="v" style="font-size:60px">0<small> of 484</small></div><div class="l">accepted fields wrong on 100 fresh forms, gate fixed in advance</div></div>
  </div>
""", "Form 080310B0100, Unused ballots (results/adjudication/SUMMARY.md; docs/TRACE.md (a)): words 'CIENTO OCHENTA' (180), boxes 1 8 0; the official typed capture (PREP) keyed 480; Gemma read 180 in digits and in words, and the gate accepted the form. The certified count does not cover this field. Page from the app's /masked endpoint, cut at x = 1560 so the masked column is not shown; crop from /crop/080310B0100/SOBRANTES.jpg?pad=0.02&label=0."))

# 2. The problem
slides.append(slide(2, f"""
  <div class="kicker">The problem, from INE's own files</div>
  <h2>Two official records of the same paper disagree. <span class="mute">Neither says which one is right.</span></h2>
  <div class="g">
    <div class="c8">
      {annotated("receipt_050815B0100.jpg", "Option 07 on form 050815B0100: words 'ciento setenta y cinco' (175), boxes 1 7 5", 1080, 619, 102, [
          (0.29, 0.80, 0.0, "In words: ciento setenta y cinco (175)", "the paper", ACC, 0.28, 0.50),
          (0.865, 0.70, 0.62, "In digits: 175", "the paper", ACC, 0.09, 0.833)], band=112)}
      <p class="cap" style="margin-top:0">Form 050815B0100, Option 07 (masked, cropped right of the logo column). One of the 52 on my random 300.</p>
    </div>
    <div class="c4">
      <div style="font-size:18px;font-weight:600;letter-spacing:1.8px;text-transform:uppercase;color:var(--muted);margin-bottom:6px">The two typed records of this field</div>
      <table>
        <tr><td style="color:var(--muted)">Official typed capture (PREP)</td><td class="r" style="font-size:40px;font-weight:600;color:var(--bad)">75</td></tr>
        <tr><td style="color:var(--muted)">Certified count</td><td class="r" style="font-size:40px;font-weight:600">175</td></tr>
      </table>
      <p style="margin-top:16px;font-size:22px;color:var(--muted)">The 75 is a typing error in the database, not on the paper.</p>
    </div>
  </div>
  <div class="stats" style="grid-template-columns:repeat(3,1fr);margin-top:34px">
    <div class="stat"><div class="v">6.5%</div><div class="l">of the 52,167 polling stations not recounted: the preliminary capture and the certified count disagree on at least one vote field</div></div>
    <div class="stat"><div class="v">19.2%</div><div class="l">of nationally captured tally forms fail their own row sum (26,336 of 137,196)</div></div>
    <div class="stat"><p style="font-size:28px;line-height:1.4;padding-top:4px">Double keying copies the paper faithfully but <b>cannot say which paper is wrong</b>. The photo can.</p></div>
  </div>
""", "6.5% = 3,382 of 52,167 (results/national_counts.md). 19.2% = 26,336 of 137,196 (README 'Why double keying is not enough'). The mandated audit checks the software, not the keyed values (docs/BUSINESS.md)."))

# 3. How it works
slides.append(slide(3, f"""
  <div class="kicker">How it works</div>
  <h2>The model reads. The paper's own arithmetic decides.</h2>
  <div class="steps" style="margin-top:10px">
    <div class="st"><div class="no">01</div><div class="t">Photo</div><p>Page located and privacy-masked before it is stored or sent</p><span class="arr">→</span></div>
    <div class="st"><div class="no">02</div><div class="t">Gemma reads</div><p>Gemma-4-31B-IT on AMD Token Factory reads every field twice: digits and words</p><span class="arr">→</span></div>
    <div class="st"><div class="no">03</div><div class="t">Arithmetic</div><p>words = digits · rows sum to TOTAL · section 5 = section 7 = TOTAL</p><span class="arr">→</span></div>
    <div class="st"><div class="no">04</div><div class="t">Accept or route</div><p>All hold: <b class="ok">accepted</b>. One fails: <b class="bad">a person</b> gets the field, with its photo</p><span class="arr">→</span></div>
    <div class="st"><div class="no">05</div><div class="t">Receipt</div><p>Each field a Merkle leaf; the root anchored with OpenTimestamps</p></div>
  </div>
  <div class="g" style="margin-top:48px">
    <div class="c6"><div class="frame"><img src="{A}form_accepted_head.png" alt="Form 211298B0100: Accepted: 0 fields to key"></div>
      <p class="cap">An accepted form on the site (211298B0100): every identity holds, so nobody keys it. A second reader, Qwen3.8-27B on AMD, never overrides Gemma: it can only withhold acceptance.</p></div>
    <div class="c6"><div class="frame"><img src="{A}form_accepted_idents.png" alt="The paper's identities on 211298B0100: 417 = 417 four times; words = digits 23 of 23"></div></div>
  </div>
""", "Masking: names-and-signatures column blacked out (OpenCV, CPU). The gate is plain Python. Every model read runs on AMD. Interfaces: web app, API, CLI, MCP server, Evolus workflows."))

# 4. Results (dots = the Colima recall check), merged
dots = "".join('<div class="dot"></div>' for _ in range(27)) + '<div class="dot miss"></div>'
slides.append(slide(4, f"""
  <div class="kicker">Results · pre-registered · INE's public data</div>
  <h2>1,270 real tally sheets read on AMD. <span class="mute">49 capture errors confirmed by the certified count.</span></h2>
  <div class="g">
    <div class="c6">
      <div class="dots">{dots}</div>
      <p class="cap" style="margin-top:22px">Recall, Colima: each dot is a capture error the certified count reveals. Filled: caught. Outlined: missed. One state; not total recall.</p>
    </div>
    <div class="c6">
      <div class="stats" style="grid-template-columns:1fr 1fr;row-gap:30px">
        <div class="stat"><div class="v">1,270</div><div class="l">handwritten tally sheets read by Gemma on AMD (289 of a random 300 and Colima's 982, one sheet in both)</div></div>
        <div class="stat"><div class="v">49</div><div class="l">capture errors confirmed by the certified count, each with its photo</div></div>
        <div class="stat" style="border-top:1px solid var(--line)"><div class="v">27<small> of 28</small></div><div class="l">caught, 96% (Wilson 95% 82-99%), pre-registered</div></div>
        <div class="stat" style="border-top:1px solid var(--line)"><div class="v">0<small> of 484</small></div><div class="l">accepted fields wrong on 100 fresh forms (gate v2, fixed before the draw; Wilson 95% upper bound 0.79%)</div></div>
      </div>
      <p style="margin-top:34px;border-top:1px solid var(--line);padding-top:20px">I re-read the AI-judged disputes myself, blind to its answers: <b>0 read differently</b>. Every crop is public.</p>
    </div>
  </div>
""", "1,270 = 289 of a random 300 (11 pages not located) + Colima's 982 located sheets - 1 sheet in both (060079C0300). 49 = 22 confirmed by the certified count on the random 300 + 27 in Colima (all 982 located presidential sheets for $0.14). On the 300: 52 fields where the official capture does not match the paper, in 6,358; 267 disputed; 55 forms accepted with no person, 2 of 1,210 fields wrong. Recall: results/colima/recall.md (PROTOCOL.md Amendment 9). Fresh 100: results/confirm100.md."))

# 5. Incumbent
slides.append(slide(5, """
  <div class="kicker">Against the incumbent · Baja California Sur, 2024 local actas</div>
  <h2 style="margin-bottom:22px">91.6% field match, where the reading the state bought scored 62.84%.</h2>
  <p class="lead" style="font-size:28px;color:var(--muted);max-width:1500px">Same per-field exact-match metric on Baja California Sur's 2024 local actas: mine on a pre-registered random 300, against the published values; theirs on all 2,020, against the manual capture.</p>
  <div class="bars" style="margin-top:60px">
    <div class="row"><div class="name">Two Hands<span>Gemma on AMD · random 300 actas, pre-registered</span></div>
      <div class="trk"><div class="bar" style="width:calc(91.6% * 0.85);background:var(--accent)"></div><div class="val acc">91.6%</div></div></div>
    <div class="row"><div class="name">Google Document AI<span>the state's purchased reading · all 2,020 actas</span></div>
      <div class="trk"><div class="bar" style="width:calc(62.84% * 0.85);background:#b9bdc6"></div><div class="val muted">62.84%</div></div></div>
  </div>
  <p style="margin:40px 0 0 532px;max-width:1100px;color:var(--muted);font-size:22px">Ours: 91.58% of 3,622 fields, Wilson 95% 90.63-92.44%. Theirs: 14,501 of 23,077 fields.</p>
""", "README 'Against the incumbent'; results/ieebcs/score.json, scripts/ieebcs_score.py --check. Two Hands accepts only what the paper's arithmetic proves and routes the rest with the photo. Second keying by a person, the rule today: at least 0.8% of fields in my random sample still do not match the paper."))

# 6. Why Gemma
slides.append(slide(6, """
  <div class="kicker">Gemma on AMD Token Factory</div>
  <h2>Same 300 forms, same checks: Gemma accepts 1.8× the forms Qwen does, 4.6× cheaper, 2.8× faster.</h2>
  <table style="max-width:1680px">
    <tr><th>Reader, on AMD</th><th class="r">Forms accepted</th><th class="r">Wrong of accepted fields</th><th class="r">$ per 1,000 forms</th><th class="r">Time per read</th></tr>
    <tr class="hi"><td>Gemma-4-31B-IT</td><td class="r acc">55 of 300</td><td class="r">2 of 1,210</td><td class="r acc">$0.14</td><td class="r acc">87 s</td></tr>
    <tr><td>Qwen3.8-27B</td><td class="r">31 of 300</td><td class="r">1 of 682</td><td class="r">$0.64</td><td class="r">241 s</td></tr>
    <tr><td>Both must agree, the paper's sums as referee</td><td class="r">89 of 300</td><td class="r ok"><b class="ok">0 of 1,958</b></td><td class="r">$0.78</td><td class="r">–</td></tr>
  </table>
  <p class="cap" style="font-size:21px">Rows 1-2: the first gate (v1) on the pre-registered 300. Row 3: two readers, a lighter gate, a secondary analysis. Gate v2 on 100 fresh forms: slide 7. Source: app/data/bakeoff_300.json.<br>Time per read: wall clock in the 300 run (2 in flight, my own pacing). Measured separately on the shared endpoint, 4 in flight (12 requests): 4.8 forms/min, 32 s p50 and 67 s p95 per read; 9.6 output tokens/s per request (300 run). For an audit after the count: Colima's 982 sheets in about 3.4 hours (results/throughput_sweep.json).</p>
  <div style="display:grid;grid-template-columns:auto 1fr;column-gap:48px;align-items:center;margin-top:64px;border-top:1px solid var(--line);padding-top:36px">
    <div class="v acc" style="font-size:112px;font-weight:600;letter-spacing:-2.5px;line-height:1;font-variant-numeric:tabular-nums">$0.14</div>
    <p style="font-size:34px;line-height:1.35;color:var(--ink-2)"><b>Colima, a whole state:</b> all 982 located presidential sheets, read by Gemma on AMD.</p>
  </div>
""", "README 'Why Gemma' and 'What ran on AMD'; docs/EVOLUS.md (150 executions of real routed fields; a Script recomputes the evidence score with no AI). Every zero-error two-reader pair includes Gemma. About $24 of AMD compute to read all 169,005 national presidential tally sheets."))

# 7. Where it breaks
slides.append(slide(7, f"""
  <div class="kicker">Where it holds, and where it breaks</div>
  <h2>Read 3114, paper 314. <span class="acc">Gate v2, fixed in advance, sends it to a person.</span></h2>
  <div class="g" style="align-items:center">
    <div class="c7">
      {annotated(A + "crop_070212B0100_SOBRANTES.jpg", "Unused ballots on form 070212B0100: boxes 3 1 4, words line blank", 960, 744, 158, [
          (0.45, 0.64, 0.0, "Words line: blank", "no second reading to compare", INK, 0.30),
          (0.895, 0.66, 0.62, "The paper: 314", "in digits", ACC, 0.08)], band=124)}
      <p class="cap" style="margin-top:0">Form 070212B0100, unused ballots (masked crop).</p>
    </div>
    <div class="c5 facts">
      <div><div class="k">The blind spot</div><p>The model read <b class="bad">3114</b>. Unused ballots sit in no identity: no sum can catch a digit inserted here. The first gate would have accepted it.</p></div>
      <div><div class="k">Held out</div><p>Gate v2 (digits and words both read and equal) was fixed before 100 fresh forms were drawn. On them: <b class="ok">0 wrong of 484</b> accepted fields (Wilson 95% upper bound 0.79%).</p></div>
      <div><div class="k">Scope</div><p>By design, an audit of the typed values: most forms go to a person, and the auditor sees only the disputed fields. Not an official INE product.</p></div>
    </div>
  </div>
""", "docs/EVALUATION.md; results/confirm100.md. One reader, frozen gate: 2 wrong of 1,210 accepted fields on 300 random forms (0.17%), 13 of 8,382 on a whole state (0.16%). Measured kinds so far: harmonised in one call (239/239 for 234), blank words (300 for 379), digit insertion (3114 for 314). No results, no parties (Option 01 to 15), no totals; the certified count is the official result."))

# 8. Business
slides.append(slide(8, f"""
  <div class="kicker">Business at a glance</div>
  <h2 style="margin-bottom:24px">An independent check of the keyed values. <span class="mute">$1 per sheet audited (proposed).</span></h2>
  <div class="g">
    <div class="c7"><div class="frame"><div style="overflow:hidden;height:196px"><img style="margin-top:-18px" src="{A}report_header.png" alt="Audit report: 6,358 fields checked, 267 disputed, each with its photo; Merkle root e56a8ef4f011b9e5"></div>
        <div style="border-top:1px solid var(--line)"><img src="{A}report_item_050815B0100.png" alt="Dispute 3: 050815B0100 Option 07, keyed 75, model digits 175, words 175, strong evidence"></div></div>
      <p style="margin-top:22px;font-size:27px;color:var(--ink)">The auditor looks at <b>267 of 6,358 fields (4%)</b>, each with its photo.</p>
      <p class="cap">The product: the audit report, strongest first, sealed by one Merkle root.</p>
      <p style="margin-top:14px;font-size:22px;line-height:1.4;color:var(--ink-2)"><b>Evolus:</b> each strong finding opens a case. Agent Intake clerk on Gemma-4-31B-IT, workflow Audit finding; a script, not the model, scores the evidence. 150 of 150 runs completed.</p></div>
    <div class="c5 facts tight">
      <div><div class="k">Buyer</div><p>INE and the 32 state institutes, each with an outside auditor.</p></div>
      <div><div class="k">Why now</div><p><b>6 June 2027</b>: the federal midterm and 32 concurrent local elections. First step: a <b>paid shadow-mode pilot</b> on one state's count.</p></div>
      <div><div class="k">One state, priced</div><p>Morelos paid MXN 26.6M to run its 2024 PREP. My check of every sheet: about <b>MXN 143k</b>, 0.5% of that. The federal count, 169,005 sheets: about $169,000.</p></div>
      <div><div class="k">Next</div><p style="font-size:22px;line-height:1.38">The check is the form's own arithmetic, so it isn't tied to elections. Proven on two form types: Mexico's tally sheets and UK rainfall ledgers (1850-1960), once typed by ~16,000 volunteers, no retraining. Next: tally sheets in at least 7 more countries that publish their images, and the monthly health-facility reports behind DHIS2, used in 70+ countries.</p></div>
    </div>
  </div>
""", "README 'Business at a glance'. All 26 auditors named in 2024 were universities. INE budgeted MXN 9.5M for automated capture in 2024 and bought none. AMD compute $0.00014 per sheet. Reviewer work: about one photo crop per sheet (0.92 measured) instead of re-keying about 22 fields. Next: The check is the form's own arithmetic, so it isn't tied to elections. Proven on two form types: Mexico's tally sheets and UK rainfall ledgers (1850-1960), no retraining. Next: tally sheets in at least 7 more countries that publish their images, and the monthly health-facility reports behind DHIS2, used in 70+ countries."))

# 9. Check it yourself
slides.append(slide(9, """
  <div class="kicker">Check it yourself</div>
  <h2>Every number re-derives from public data.</h2>
  <div class="g" style="margin-top:120px">
    <div class="c4"><div class="k" style="font-size:18px;font-weight:600;letter-spacing:1.8px;text-transform:uppercase;color:var(--muted)">Reproduce</div>
      <pre class="cmd">make eval</pre><p style="margin-top:18px">Recomputes every number offline and checks it against what the site shows.</p></div>
    <div class="c4"><div class="k" style="font-size:18px;font-weight:600;letter-spacing:1.8px;text-transform:uppercase;color:var(--muted)">Verify a receipt</div>
      <pre class="cmd">python -m twohands.verify_receipt
  receipt.json --crop crop.jpg</pre><p style="margin-top:18px">A changed value or crop fails.</p></div>
    <div class="c4"><div class="k" style="font-size:18px;font-weight:600;letter-spacing:1.8px;text-transform:uppercase;color:var(--muted)">Check the timestamp</div>
      <pre class="cmd">ots verify
results/sample_audit_root.txt.ots</pre><p style="margin-top:18px">The report's Merkle root, anchored in Bitcoin with OpenTimestamps.</p></div>
  </div>
  <div style="position:absolute;left:120px;right:120px;top:760px;border-top:1px solid var(--ink);padding-top:34px;display:flex;justify-content:space-between;align-items:baseline">
    <p style="font-size:40px;font-weight:600;color:var(--ink)">Two Hands. <span class="acc">Verifiable quality control for handwritten numbers.</span></p>
    <p style="font-size:28px;color:var(--muted)" class="mono">github.com/py-tr/twohands</p>
  </div>
""", "PROTOCOL.md: sample, prompt, gate and metrics committed before any model read. Data: INE PREP 2024 and Computos Distritales 2024, free-use terms (Libre-Uso-MX); masked pages only; an independent demonstration, not an official INE product.", last=True))

assert len(slides) == N

html = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Two Hands talk</title>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'><link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700&family=JetBrains+Mono:wght@400;500;600&display=swap' rel='stylesheet'>"
        f"<style>{CSS}</style></head><body>{''.join(slides)}</body></html>")
(S / "talk.html").write_text(html, encoding="utf8")

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("slide_*.png"):
        old.unlink()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto((S / "talk.html").as_uri()); pg.wait_for_load_state("networkidle")
        pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(600)
        print("Inter loaded:", pg.evaluate("document.fonts.check('600 40px Inter')"))
        over = pg.evaluate("""() => [...document.querySelectorAll('.slide')].map((s, i) => {
            const foot = s.querySelector('.foot').getBoundingClientRect().top;
            let maxb = 0;
            for (const el of s.querySelectorAll('*')) { if (el.closest('.foot') || el.closest('.notes')) continue;
              const r = el.getBoundingClientRect(); if (r.height) maxb = Math.max(maxb, r.bottom); }
            return [i + 1, Math.round(foot - maxb)]; })""")
        for i, gap in over:
            print(f"slide {i}: {gap}px above the footer" + ("  <-- OVERLAP" if gap < 16 else ""))
        pg.pdf(path=str(S / "two-hands-talk.pdf"), width="1920px", height="1080px", print_background=True)
        for i in range(N):
            pg.locator(".slide").nth(i).screenshot(path=str(OUT / f"slide_{i+1}.png"))
        b.close()
    print("talk deck built:", N, "slides")
