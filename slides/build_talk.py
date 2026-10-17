"""The talk deck for the video: slides/talk.html (1920x1080 per slide) -> slides/talk/slide_N.png and
slides/two-hands-talk.pdf.

usage (repo root):  python slides/build_talk.py
Product visuals come from slides/talk/assets/ (captured from the running app by slides/capture_talk.py) and the
masked crops in slides/. Every number is copied from README.md, submission/lablab.md and docs/BUSINESS.md, which
`make eval` checks. No model call.
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

S = Path(__file__).resolve().parent
OUT = S / "talk"
A = "talk/assets/"  # relative to talk.html

CSS = """
@page { size: 1920px 1080px; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: #e5e7eb; background: #0b1020; }
.slide { width: 1920px; height: 1080px; padding: 72px 110px 0; position: relative; page-break-after: always; overflow: hidden;
         background: radial-gradient(1200px 700px at 85% 10%, #13224a 0%, #0b1020 60%); }
h1 { font-size: 150px; margin: 0; letter-spacing: -3px; line-height: 1; color: #fff; }
h2 { font-size: 60px; margin: 0 0 34px; line-height: 1.12; color: #fff; letter-spacing: -0.5px; }
.kicker { color: #5eead4; font-size: 26px; letter-spacing: 3px; text-transform: uppercase; font-weight: 600; margin-bottom: 16px; }
.lead { font-size: 40px; line-height: 1.3; color: #cbd5e1; }
ul { font-size: 30px; line-height: 1.38; padding-left: 34px; margin: 0; color: #cbd5e1; }
li { margin-bottom: 14px; }
b, strong { color: #fff; }
.accent { color: #5eead4; } .warn { color: #f87171; } .gold { color: #fbbf24; } .dim { color: #94a3b8; }
code { font-family: Consolas, 'Cascadia Mono', monospace; color: #5eead4; background: #132033; padding: 1px 8px; border-radius: 6px; font-size: 0.9em; }
.foot { position: absolute; left: 110px; right: 110px; bottom: 40px; font-size: 22px; color: #94a3b8; display: flex; justify-content: space-between; }
.foot .pg { color: #64748b; margin: 0 18px; }
.card { background: #0f172a; border: 1px solid #1f2a44; border-radius: 20px; padding: 24px 28px; }
.row { display: flex; gap: 30px; }
.row > * { flex: 1; min-width: 0; }
.stat .n { font-size: 76px; font-weight: 800; line-height: 1; color: #5eead4; letter-spacing: -1px; }
.stat .n small { font-size: 34px; font-weight: 700; color: #cbd5e1; letter-spacing: 0; }
.stat .t { font-size: 25px; color: #cbd5e1; margin-top: 12px; line-height: 1.3; }
.stat.red .n { color: #f87171; } .stat.gold .n { color: #fbbf24; } .stat.white .n { color: #fff; }
.shot { background: #fff; border-radius: 14px; overflow: hidden; border: 1px solid #334155; box-shadow: 0 18px 50px rgba(0,0,0,.45); }
.shot img { display: block; width: 100%; }
.cap { font-size: 22px; color: #94a3b8; margin-top: 10px; line-height: 1.3; }
.paper { background: #fff; border-radius: 14px; overflow: hidden; border: 3px solid #334155; }
.paper img { display: block; width: 100%; }
.tag { display: inline-block; font-size: 24px; font-weight: 700; padding: 6px 16px; border-radius: 999px; margin: 0 10px 10px 0; }
.tag.t { color: #0b1020; background: #5eead4; } .tag.r { color: #fff; background: #b91c1c; } .tag.a { color: #0b1020; background: #fbbf24; } .tag.g { color: #e5e7eb; background: #1e293b; border: 1px solid #334155; }
table { border-collapse: collapse; width: 100%; font-size: 26px; }
th, td { border-bottom: 1px solid #1f2a44; padding: 12px 16px; text-align: left; vertical-align: top; }
th { color: #94a3b8; font-weight: 600; font-size: 22px; text-transform: uppercase; letter-spacing: 1.5px; }
td.num { font-variant-numeric: tabular-nums; white-space: nowrap; }
tr.hi td { background: #10243a; color: #fff; }
td.yes { color: #5eead4; font-weight: 700; }
/* pipeline */
.flow { display: flex; align-items: stretch; }
.step { flex: 1; background: #0f172a; border: 2px solid #1f2a44; border-radius: 20px; padding: 22px 22px 20px; }
.step .no { font-size: 20px; color: #94a3b8; font-weight: 700; letter-spacing: 2px; }
.step .ti { font-size: 32px; font-weight: 800; color: #fff; margin: 6px 0 10px; line-height: 1.15; }
.step .d { font-size: 23px; color: #cbd5e1; line-height: 1.32; }
.step.amd { border-color: #ed1c24; } .step.amd .ti { color: #ff6b6b; }
.step.ref { border-color: #5eead4; } .step.ref .ti { color: #5eead4; }
.step.hum { border-color: #fbbf24; } .step.hum .ti { color: #fbbf24; }
.arrow { width: 40px; display: flex; align-items: center; justify-content: center; font-size: 38px; color: #5eead4; }
.loop { margin: 20px auto 0; text-align: center; }
.loop div { display: inline-block; font-size: 24px; color: #fde68a; background: #1f1a0e; border: 1px dashed #fbbf24; border-radius: 12px; padding: 9px 20px; }
/* bars */
.bar-row { display: flex; align-items: center; gap: 26px; margin: 18px 0; }
.bar-lbl { width: 470px; font-size: 28px; color: #e5e7eb; line-height: 1.25; }
.bar-lbl .dim { font-size: 22px; }
.bar-track { flex: 1; height: 110px; background: #0f172a; border: 1px solid #1f2a44; border-radius: 12px; position: relative; }
.bar-fill { height: 100%; border-radius: 12px 0 0 12px; display: flex; align-items: center; justify-content: flex-end; padding-right: 22px; font-size: 64px; font-weight: 800; color: #0b1020; }
.gh { font-size: 28px; font-weight: 800; color: #5eead4; margin-bottom: 12px; }
.card p { font-size: 24px; line-height: 1.36; color: #cbd5e1; margin: 0 0 12px; }
.card p:last-child { margin-bottom: 0; }
.kv { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.kv .card { padding: 18px 24px; }
.kv .k { font-size: 20px; color: #5eead4; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 6px; }
.kv .v { font-size: 24px; color: #cbd5e1; line-height: 1.33; }
.kv .v b { color: #fff; }
.callouts { display: flex; gap: 0; align-items: stretch; margin-top: 18px; }
.callouts > div { flex: 1; padding: 14px 18px; font-size: 25px; line-height: 1.25; color: #cbd5e1; border-left: 4px solid #334155; }
.callouts .big { display: block; font-size: 44px; font-weight: 800; margin-bottom: 4px; }
.runs { margin-top: 24px; font-size: 24px; color: #cbd5e1; background: #0f172a; border: 1px solid #1f2a44; border-radius: 16px; padding: 16px 26px; }
pre.cmd { font-family: Consolas, 'Cascadia Mono', monospace; font-size: 22px; color: #e5e7eb; background: #0b1324; border: 1px solid #1f2a44; border-radius: 10px; padding: 12px 16px; margin: 6px 0 14px; white-space: pre-wrap; word-break: break-all; }
"""

N = 10


def foot(i: int) -> str:
    return (f'<div class="foot"><span>Two Hands · AMD Developer Hackathon ACT III</span>'
            f'<span><span class="pg">{i:02d} / {N:02d}</span>github.com/py-tr/twohands</span></div>')


def slide(i: int, body: str, style: str = "") -> str:
    return f'<section class="slide" style="{style}">{body}{foot(i)}</section>'


slides = []

# 1. Title
slides.append(slide(1, f"""
  <div class="kicker">AMD Developer Hackathon ACT III · Gemma on AMD Token Factory</div>
  <h1>Two Hands</h1>
  <p class="lead" style="margin:18px 0 6px"><span class="accent" style="font-size:52px;font-weight:600">Verifiable quality control for handwritten numbers.</span></p>
  <p class="lead" style="font-size:36px;margin:0 0 30px">OCR reads the number. Two Hands checks whether the whole form agrees.</p>
  <div class="row" style="gap:40px;align-items:center">
    <div style="flex:1.25">
      <div class="paper"><img src="crop_122655C0100_OPT02.jpg" alt="Option 02 on form 122655C0100: words 'ciento veintitres', boxes 1 2 3"></div>
      <div class="callouts">
        <div style="border-color:#94a3b8"><span class="big" style="color:#fff">23</span>Gemma's read, digits and words</div>
        <div style="border-color:#f87171"><span class="big warn">366 ≠ 466</span>rows sum vs the form's TOTAL</div>
        <div style="border-color:#fbbf24"><span class="big gold">routed</span>to a person, with this crop</div>
        <div style="border-color:#5eead4"><span class="big accent">123</span>the paper; the sum holds</div>
      </div>
    </div>
    <div style="flex:0.75;display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div class="card stat"><div class="n">1,270</div><div class="t">real handwritten tally sheets read on AMD</div></div>
      <div class="card stat"><div class="n">91.6%</div><div class="t">field match vs <b>62.84%</b> for the reading the state bought</div></div>
      <div class="card stat"><div class="n">27<small> of 28</small></div><div class="t">certified-detectable capture errors caught</div></div>
      <div class="card stat gold"><div class="n">$1</div><div class="t">per sheet audited (proposed)</div></div>
    </div>
  </div>
  <p class="cap" style="margin-top:16px">Form 122655C0100, Option 02: a real INE 2024 tally sheet, privacy-masked, cropped right of the logo column.</p>
"""))

# 2. The problem
slides.append(slide(2, f"""
  <div class="kicker">The problem, from INE's own files</div>
  <h2>Two official records of the same paper disagree.<br><span class="dim">Neither says which one is right.</span></h2>
  <div class="row" style="gap:44px">
    <div style="flex:1.1">
      <div class="paper"><img src="receipt_050815B0100.jpg" alt="Option 07 on form 050815B0100: words 'ciento setenta y cinco', boxes 1 7 5"></div>
      <div style="margin-top:16px"><span class="tag r">first capture keyed 75</span><span class="tag t">the paper says 175</span><span class="tag g">certified count: 175</span></div>
      <p class="cap" style="margin-top:4px">Form 050815B0100, Option 07 (masked, cropped right of the logo column). One of the 52 on our random 300.</p>
      <ul style="margin-top:30px;font-size:32px">
        <li>Every sheet is already keyed twice by people. Double keying copies the paper faithfully but <b>cannot say which paper is wrong</b>.</li>
        <li>The mandated audit checks <b>the software</b>, not the keyed values.</li>
        <li>A difference says two captures disagree. <b class="accent">The photo says which.</b></li>
      </ul>
    </div>
    <div style="flex:0.9;display:flex;flex-direction:column;gap:26px">
      <div class="card stat red"><div class="n" style="font-size:110px">6.5%</div><div class="t">of the <b>52,167</b> polling stations not recounted: the preliminary capture and the certified count disagree on at least one vote field (<b>3,382</b>)</div></div>
      <div class="card stat gold"><div class="n" style="font-size:110px">19.2%</div><div class="t">of nationally captured tally forms fail their own row sum, in the official capture (<b>26,336</b> of <b>137,196</b>)</div></div>
    </div>
  </div>
"""))

# 3. How it works
slides.append(slide(3, f"""
  <div class="kicker">How it works</div>
  <h2>The model reads. The paper's own arithmetic decides.</h2>
  <div class="flow">
    <div class="step"><div class="no">1 · PHOTO</div><div class="ti">Scan or phone photo</div>
      <div class="d">Page located and <b>privacy-masked</b> (names and signatures blacked out) before it is stored or sent</div></div>
    <div class="arrow">→</div>
    <div class="step amd"><div class="no">2 · READ</div><div class="ti">Gemma on AMD</div>
      <div class="d">Gemma-4-31B-IT on AMD Token Factory reads every field <b>twice</b>: the digits and the amount in words</div></div>
    <div class="arrow">→</div>
    <div class="step ref"><div class="no">3 · CHECK</div><div class="ti">The paper's identities</div>
      <div class="d">words = digits · rows sum to TOTAL · section 5 = section 7 = TOTAL</div></div>
    <div class="arrow">→</div>
    <div class="step hum"><div class="no">4 · DECIDE</div><div class="ti">Accept or route</div>
      <div class="d">All hold: <b>accepted</b>, nobody keys it. One fails: <b>a person</b> gets the field named, with its photo</div></div>
    <div class="arrow">→</div>
    <div class="step"><div class="no">5 · RECEIPT</div><div class="ti">Sealed</div>
      <div class="d">Each field is a Merkle leaf; the report's root is anchored with <b>OpenTimestamps</b></div></div>
  </div>
  <div class="loop"><div>A second reader (Qwen3.8-27B, also on AMD) never overrides Gemma: it can only <b style="color:#fde68a">withhold</b> acceptance</div></div>
  <div class="row" style="margin-top:26px;gap:28px;align-items:flex-start">
    <div style="flex:0 0 640px">
      <div class="shot"><img src="{A}form_accepted_head.png" alt="Form 211298B0100: Accepted: 0 fields to key"></div>
      <p class="cap">Form 211298B0100 on the site: every identity holds, so nobody keys this form.</p>
    </div>
    <div style="flex:0 0 560px">
      <div class="shot"><img src="{A}form_accepted_idents.png" alt="Every identity holds: 417 = 417; words = digits 23 of 23"></div>
    </div>
    <div class="card"><div class="gh">Runs where</div>
      <p><b>On AMD:</b> every model read, incl. the second reader and the Evolus agent</p>
      <p><b>On CPU:</b> locating, masking, the gate</p>
      <p><b>As:</b> web app, API, CLI, MCP server</p></div>
  </div>
"""))

# 4. One real case
slides.append(slide(4, f"""
  <div class="kicker">One real sheet, request to receipt · /trace</div>
  <h2>Gemma read 23. The paper says 123. <span class="accent">The sum caught it.</span></h2>
  <div class="row" style="gap:40px;align-items:flex-start">
    <div style="flex:0 0 760px">
      <div class="shot"><img src="{A}trace_gate.png" alt="The gate on form 122655C0100: rows sum to TOTAL 366 vs 466 FAIL; the other identities pass; routed to a person"></div>
      <p class="cap">The gate, re-run on Gemma's stored raw output: one identity fails, so a person decides.</p>
    </div>
    <div>
      <div class="paper"><img src="crop_122655C0100_OPT02.jpg" alt="Option 02: the paper says 123"></div>
      <div style="margin:14px 0 22px"><span class="tag g">Gemma: 23</span><span class="tag r">366 ≠ 466</span><span class="tag a">routed</span><span class="tag t">paper: 123</span></div>
      <div class="shot"><img src="{A}trace_verified.png" alt="Receipt checks: four ok lines and VERIFIED"></div>
      <p class="cap">Leaf 146 of 267, Merkle root e56a8ef4f011b9e5. <b style="color:#e5e7eb">VERIFIED</b> proves the record is unchanged since the report was sealed, not that the reading is right.</p>
    </div>
  </div>
"""))

# 5. Results
slides.append(slide(5, f"""
  <div class="kicker">Results · pre-registered · INE's public data</div>
  <h2>1,270 real tally sheets. 49 capture errors confirmed by the certified count.</h2>
  <div class="row" style="gap:26px">
    <div class="card stat"><div class="n">1,270</div><div class="t">handwritten tally sheets read by Gemma on AMD</div></div>
    <div class="card stat white"><div class="n">49</div><div class="t">capture errors confirmed by the certified count, each with its photo</div></div>
    <div class="card stat"><div class="n">27<small> of 28</small></div><div class="t">recall on the errors the certified count reveals (one state)</div></div>
    <div class="card stat gold"><div class="n">0<small> of 484</small></div><div class="t">accepted fields wrong on 100 fresh forms (gate v2)</div></div>
  </div>
  <table style="margin-top:30px">
    <tr><th style="width:30%">Run</th><th>Measured</th></tr>
    <tr><td><b>Pre-registered random 300</b></td><td>6,358 fields checked · 267 disputed · <b>52</b> where the official capture does not match the paper · 55 forms accepted with no person: 2 of 1,210 fields wrong</td></tr>
    <tr><td><b>100 fresh forms</b> (Amendment 3)</td><td>gate v2 accepted 22 forms: <b class="accent">0 of 484</b> fields wrong</td></tr>
    <tr><td><b>Colima, a whole state</b></td><td>all 982 located presidential sheets for <b>$0.14</b> · 27 fields where the capture does not match the paper, each confirmed by the certified count</td></tr>
    <tr><td><b>Recall</b> (Colima, pre-registered)</td><td><b class="accent">27 of 28</b> certified-detectable capture errors caught, 96% (Wilson 95% 82-99%); not total recall</td></tr>
    <tr><td><b>A person's blind re-read</b></td><td>of the AI-judged disputes: <b class="accent">0 read differently</b></td></tr>
  </table>
"""))

# 6. Incumbent
slides.append(slide(6, f"""
  <div class="kicker">Against the incumbent · Baja California Sur, 2024 local actas</div>
  <h2>91.6% field match, where the reading the state bought scored 62.84%</h2>
  <div style="margin-top:56px">
    <div class="bar-row"><div class="bar-lbl"><b>Two Hands</b>: Gemma on AMD<br><span class="dim">pre-registered random 300 actas · 3,622 fields</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:91.6%;background:#5eead4">91.6%</div></div></div>
    <div class="bar-row"><div class="bar-lbl"><b>Google Document AI</b><br><span class="dim">the state's purchased reading · all 2,020 actas</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:62.84%;background:#64748b;color:#fff">62.84%</div></div></div>
  </div>
  <p class="lead" style="font-size:28px;margin:10px 0 56px 496px">Same per-field exact-match metric. Ours: 91.58%, Wilson 95% 90.63-92.44%, against the published PREP values. Theirs: 14,501 of 23,077 fields, against the manual capture.</p>
  <div class="row" style="gap:30px">
    <div class="card"><div class="gh">Reading is not the product</div><p>Ours accepts only what the paper's arithmetic proves and routes the rest to a person, with the photo.</p></div>
    <div class="card"><div class="gh">Second keying by a person</div><p>The rule today. At least <b>0.8%</b> of fields in our random sample still do not match the paper (52 of 6,358).</p></div>
    <div class="card"><div class="gh">Where a person looks</div><p><b>1 in 5</b> disputed fields is a confirmed capture error, against at least 1 in 122 at random.</p></div>
  </div>
"""))

# 7. Gemma on AMD
slides.append(slide(7, f"""
  <div class="kicker">Gemma on AMD Token Factory</div>
  <h2>Why Gemma: more forms accepted, cheaper, faster</h2>
  <div class="row" style="gap:26px">
    <div class="card stat"><div class="n">1.8×</div><div class="t">the forms Qwen3.8-27B accepts, at the same error rate</div></div>
    <div class="card stat"><div class="n">4.6×</div><div class="t">cheaper</div></div>
    <div class="card stat"><div class="n">2.8×</div><div class="t">faster</div></div>
    <div class="card stat white"><div class="n">4.8<small> /min</small></div><div class="t">forms, 4 in flight, $0.000146 per form (shared endpoint)</div></div>
  </div>
  <table style="margin-top:28px">
    <tr><th>Same 300 forms, same gate, on AMD</th><th>Forms accepted</th><th>Wrong of accepted fields</th><th>$ per 1,000 forms</th><th>Time per read</th></tr>
    <tr class="hi"><td><b>Gemma-4-31B-IT</b></td><td class="num"><b>55 of 300</b> (18%)</td><td class="num">2 of 1,210</td><td class="num"><b>$0.14</b></td><td class="num"><b>87 s</b></td></tr>
    <tr><td>Qwen3.8-27B</td><td class="num">31 of 300 (10%)</td><td class="num">1 of 682 (+2 undecided)</td><td class="num">$0.64</td><td class="num">241 s</td></tr>
    <tr><td>Gemma + Qwen3.8-27B, two readers must agree</td><td class="num">89 of 300 (30%)</td><td class="num yes">0 of 1,958</td><td class="num">$0.78</td><td class="num">–</td></tr>
  </table>
  <p class="cap">Pairs: all 23 digits agree, lighter gate (secondary). Source: app/data/bakeoff_300.json. Every zero-error two-reader pair includes Gemma.</p>
  <div class="row" style="gap:30px;margin-top:20px">
    <div class="card"><div class="gh">Evolus · workflow "Audit finding"</div><p><b>150 of 150</b> executions completed on real routed fields. The agent "Intake clerk" runs Gemma-4-31B-IT on AMD and drafts the finding; a Script recomputes the evidence score with no AI.</p></div>
    <div class="card"><div class="gh">A whole state, then the country</div><p>Colima: all <b>982</b> located presidential sheets read for <b>$0.14</b>. About <b>$24</b> of AMD compute to read all 169,005 national presidential tally sheets.</p></div>
  </div>
"""))

# 8. Business
slides.append(slide(8, f"""
  <div class="kicker">Business at a glance</div>
  <h2>An independent check of the keyed values, <span class="gold">$1 per sheet</span> (proposed)</h2>
  <div class="row" style="gap:40px;align-items:flex-start">
    <div style="flex:0 0 700px">
      <div class="shot" style="height:372px"><img src="{A}report_head.png" alt="Audit report: 6,358 fields checked, 267 disputed, each with its photo; Merkle root"></div>
      <div class="shot" style="margin-top:14px"><img src="{A}report_item_050815B0100.png" alt="Dispute 3: 050815B0100 Option 07, keyed 75, model digits 175, words 175, strong"></div>
      <p class="cap">The product: the audit report. Every dispute with its photo, strongest first, sealed by one Merkle root.</p>
    </div>
    <div class="kv">
      <div class="card"><div class="k">Buyer</div><div class="v"><b>INE</b> and the <b>32 state institutes</b>, each with an outside auditor (all 26 named in 2024 were universities)</div></div>
      <div class="card"><div class="k">Why now</div><div class="v"><b>6 June 2027</b>: the federal midterm and 32 concurrent local elections. INE budgeted MXN 9.5M for automated capture in 2024 and bought none</div></div>
      <div class="card"><div class="k">Price</div><div class="v"><b>$1 per sheet audited</b> (proposed); first step: a <b>paid shadow-mode pilot</b> on one state's 2027 count. AMD compute: $0.00014 per sheet</div></div>
      <div class="card"><div class="k">Reviewer work</div><div class="v">About <b>one photo crop</b> per sheet to look at (0.92 measured), instead of re-keying about 22 fields</div></div>
      <div class="card"><div class="k">Example</div><div class="v">Morelos paid MXN 26.6M to run its 2024 PREP. Our check of every sheet: about <b>MXN 143k</b>, <b>0.5%</b> of that</div></div>
      <div class="card"><div class="k">Next</div><div class="v">The same public data in <b>7 more countries</b>. Health reporting on <b>DHIS2</b> in 70+ countries. Not yet measured</div></div>
    </div>
  </div>
"""))

# 9. Where it breaks
slides.append(slide(9, f"""
  <div class="kicker">Where it holds, and where it breaks</div>
  <h2>Read 3114, paper 314: <span class="accent">gate v2 sends it to a person</span></h2>
  <div class="row" style="gap:44px;align-items:flex-start">
    <div style="flex:1">
      <div class="paper"><img src="{A}crop_070212B0100_SOBRANTES.jpg" alt="Unused ballots on form 070212B0100: boxes 3 1 4, words line blank"></div>
      <div style="margin-top:16px"><span class="tag r">model read 3114</span><span class="tag t">paper: 314</span><span class="tag g">words line blank</span></div>
      <ul style="margin-top:22px;font-size:32px">
        <li>Form 070212B0100, unused ballots: a field in <b>no identity</b>, with no words written. No sum can catch a digit inserted here.</li>
        <li>On 100 fresh forms (pre-registered), the frozen gate let it through. The v2 rule, <b>digits and words both read and equal</b>, blocked it and accepted <b class="accent">0 wrong of 484</b>.</li>
      </ul>
    </div>
    <div style="flex:0.85;display:flex;flex-direction:column;gap:18px">
      <div class="card"><div class="gh">Where it holds</div>
        <p>One reader, frozen gate: <b>2 wrong of 1,210</b> accepted fields on 300 random forms (0.17%), <b>13 of 8,382</b> on a whole state (0.16%).</p></div>
      <div class="card"><div class="gh">Where it breaks: the measured kinds so far</div>
        <p><b>Harmonised in one call:</b> 239/239 for 234</p>
        <p><b>Blank words:</b> 300 for 379</p>
        <p><b>Digit insertion:</b> 3114 for 314</p></div>
      <div class="card"><div class="gh">Scope</div>
        <p>Clerical capture quality only: whether a typed number matches its paper. No results, no parties (Option 01 to 15), no totals.</p>
        <p>Most forms go to a person: one reader accepts 18%, two readers 30%.</p>
        <p>The certified count is the official result. Not an official INE product.</p></div>
    </div>
  </div>
"""))

# 10. Check it yourself
slides.append(slide(10, f"""
  <div class="kicker">Check it yourself</div>
  <h2>Two Hands at a glance: every number re-derives from public data</h2>
  <div class="row" style="gap:30px;align-items:stretch">
    <div class="card"><div class="gh">Reproduce</div>
      <pre class="cmd">make eval</pre>
      <p>recomputes every number offline from the committed raw results and checks it against what the site shows</p>
      <p><b>PROTOCOL.md</b>: sample, prompt, gate and metrics committed before any model read; every later change is a numbered amendment</p></div>
    <div class="card" style="flex:1.15"><div class="gh">Verify a receipt</div>
      <pre class="cmd">python -m twohands.verify_receipt
  receipt.json --crop crop.jpg</pre>
      <p>A changed value or crop fails.</p>
      <p>Each report's Merkle root is anchored in Bitcoin with <b>OpenTimestamps</b>:</p>
      <pre class="cmd">ots verify
  results/sample_audit_root.txt.ots</pre></div>
    <div class="card"><div class="gh">Proven on real paper</div>
      <p><b class="accent">1,270</b> tally sheets read by Gemma on AMD</p>
      <p><b class="accent">49</b> capture errors confirmed by the certified count</p>
      <p><b class="accent">91.6%</b> vs 62.84% for the incumbent reading</p>
      <p><b class="accent">27 of 28</b> recall, one state, pre-registered</p>
      <p><b class="gold">$1</b> per sheet audited (proposed)</p></div>
  </div>
  <div class="runs"><b>Data:</b> INE PREP 2024 and Cómputos Distritales 2024, free-use terms (Libre-Uso-MX) · masked pages only · an independent demonstration, not an official INE product</div>
  <p class="lead" style="font-size:44px;margin-top:34px;color:#fff;font-weight:600">Two Hands. <span class="accent">Verifiable quality control for handwritten numbers.</span></p>
"""))

assert len(slides) == N

html = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Two Hands talk</title>"
        f"<style>{CSS}</style></head><body>{''.join(slides)}</body></html>")
(S / "talk.html").write_text(html, encoding="utf8")

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto((S / "talk.html").as_uri()); pg.wait_for_timeout(800)
        over = pg.evaluate("""() => [...document.querySelectorAll('.slide')].map((s, i) => {
            const foot = s.querySelector('.foot').getBoundingClientRect().top;
            let maxb = 0;
            for (const el of s.querySelectorAll(':scope > *:not(.foot)')) maxb = Math.max(maxb, el.getBoundingClientRect().bottom);
            return [i + 1, Math.round(foot - maxb)]; })""")
        for i, gap in over:
            print(f"slide {i}: {gap}px above the footer" + ("  <-- OVERLAP" if gap < 10 else ""))
        pg.pdf(path=str(S / "two-hands-talk.pdf"), width="1920px", height="1080px", print_background=True)
        for i in range(N):
            pg.locator(".slide").nth(i).screenshot(path=str(OUT / f"slide_{i+1}.png"))
        b.close()
    print("talk deck built:", N, "slides")
