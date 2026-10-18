"""Cover image for the submission (1920x1080, 16:9): python slides/build_cover.py -> slides/cover.png"""
from pathlib import Path

from playwright.sync_api import sync_playwright

S = Path(__file__).resolve().parent
MARK = (S.parent / "static" / "mark.svg").read_text(encoding="utf8")
CROP = (S / "talk" / "assets" / "crop_080310B0100_SOBRANTES.jpg").as_uri()
PAGE = (S / "talk" / "assets" / "masked_080310B0100_left.jpg").as_uri()

HTML = f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{ --bg:#f5f5f2; --ink:#14161b; --ink2:#2c3039; --muted:#5f6673; --line:#e2e2dc; --accent:#3047c0; --bad:#b3261e; }}
html,body {{ margin:0; }}
body {{ width:1920px; height:1080px; background:var(--bg); font-family:Inter,"Segoe UI",sans-serif; color:var(--ink);
       position:relative; overflow:hidden; }}
.left {{ position:absolute; left:120px; top:150px; width:880px; }}
.brand {{ display:flex; align-items:center; gap:18px; font-size:30px; font-weight:600; color:var(--ink2); }}
.brand svg {{ width:52px; height:52px; }}
h1 {{ font-size:150px; line-height:1; margin:56px 0 28px; letter-spacing:-4px; font-weight:700; }}
.tag {{ font-size:46px; line-height:1.2; font-weight:500; color:var(--accent); margin:0 0 36px; }}
.hook {{ font-size:32px; line-height:1.4; color:var(--ink2); margin:0; max-width:820px; }}
.stats {{ position:absolute; left:120px; bottom:110px; display:flex; gap:64px; border-top:2px solid var(--ink); padding-top:26px; }}
.stat b {{ display:block; font-size:58px; font-weight:700; letter-spacing:-1px; }}
.stat span {{ font-size:22px; color:var(--muted); }}
.page {{ position:absolute; right:110px; top:90px; width:640px; height:560px; overflow:hidden; border:1px solid var(--line);
        box-shadow:0 18px 50px rgba(20,22,27,.14); background:#fff; }}
.page img {{ width:100%; display:block; }}
.zoom {{ position:absolute; right:110px; top:560px; width:700px; background:#fff; border:1px solid var(--line);
        box-shadow:0 24px 60px rgba(20,22,27,.22); padding:18px 18px 22px; }}
.zoom img {{ width:100%; display:block; }}
.rec {{ display:flex; gap:40px; margin-top:16px; font-size:26px; }}
.rec .bad {{ color:var(--bad); font-weight:700; }} .rec .ok {{ color:var(--accent); font-weight:700; }}
.foot {{ position:absolute; right:110px; bottom:44px; font-size:22px; color:var(--muted); }}
</style></head><body>
<div class="left">
  <div class="brand">{MARK}<span>Gemma on AMD</span></div>
  <h1>Two Hands</h1>
  <p class="tag">Verifiable quality control for handwritten numbers.</p>
  <p class="hook">OCR reads the number. Two Hands checks whether the whole form agrees, and sends only what fails to a person.</p>
</div>
<div class="stats">
  <div class="stat"><b>1,270</b><span>real tally sheets read on AMD</span></div>
  <div class="stat"><b>49</b><span>typing errors confirmed</span></div>
  <div class="stat"><b>91.6%</b><span>vs 62.84% for the AI a state bought</span></div>
</div>
<div class="page"><img src="{PAGE}"></div>
<div class="zoom"><img src="{CROP}">
  <div class="rec"><span>Official record: <span class="bad">480</span></span><span>The paper: <span class="ok">180</span></span><span>Gemma read: <span class="ok">180</span></span></div>
</div>
<div class="foot">AMD Developer Hackathon ACT III</div>
</body></html>"""

if __name__ == "__main__":
    out = S / "cover.png"
    html_path = S / "cover.html"
    html_path.write_text(HTML, encoding="utf8")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(html_path.as_uri())
        pg.wait_for_timeout(1500)
        pg.screenshot(path=str(out))
        b.close()
    print(out)
