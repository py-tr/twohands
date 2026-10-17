"""Product visuals for the talk deck, captured from the running app (python slides/capture_talk.py [base_url]).

Saves PNG/JPG crops to slides/talk/assets/. Only pages and crops the app already serves are captured: every
tally-sheet image there is the privacy-masked page (names-and-signatures column blacked out), and crops are taken
right of the logo column (label=0). No model call. The deck itself is built by slides/build_talk.py from these files.
"""
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
OUT = Path(__file__).resolve().parent / "talk" / "assets"
OUT.mkdir(parents=True, exist_ok=True)

# Box from the top of element A to the bottom of element B (page coordinates), padded.
BOX_JS = """([a, b, pad]) => {
  const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
  const x0 = Math.min(ra.left, rb.left), x1 = Math.max(ra.right, rb.right);
  return {x: x0 - pad + scrollX, y: ra.top - pad + scrollY, width: x1 - x0 + 2 * pad, height: rb.bottom - ra.top + 2 * pad};
}"""


def clip(pg, a, b, path, pad=14):
    ea, eb = pg.locator(a).first.element_handle(), pg.locator(b).first.element_handle()
    r = pg.evaluate(BOX_JS, [ea, eb, pad])
    pg.screenshot(path=str(OUT / path), clip=r, full_page=True)
    print("saved", path, {k: round(v) for k, v in r.items()})


def main():
    # masked crops served by the app
    for name, url in {"crop_070212B0100_SOBRANTES.jpg": "/crop/070212B0100/SOBRANTES.jpg?pad=0.02&label=0",
                      "crop_110922C0100_OPT04.jpg": "/crop/110922C0100/OPT04.jpg?pad=0.02&label=0",
                      "masked_110922C0100.jpg": "/masked/110922C0100.jpg"}.items():
        (OUT / name).write_bytes(urllib.request.urlopen(BASE + url).read())
        print("saved", name)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": 1180, "height": 900}, device_scale_factor=2)

        # Trace, routed form 122655C0100: the gate table and decision; the receipt check
        pg.set_viewport_size({"width": 840, "height": 900})  # narrower page: larger text once placed on a slide
        pg.goto(BASE + "/trace#routed"); pg.wait_for_timeout(800)
        R = "#routed + section.card"
        clip(pg, f"{R} h3:nth-of-type(3)", f"{R} h3:nth-of-type(4) + p", "trace_gate.png")
        clip(pg, f"{R} ul", f"{R} ul + p", "trace_verified.png")

        # Accepted form 211298B0100: verdict banner and the paper's identities
        pg.set_viewport_size({"width": 720, "height": 900})
        pg.goto(BASE + "/form/211298B0100"); pg.wait_for_timeout(800)
        clip(pg, "h1", ".verdict.ok", "form_accepted_head.png", pad=8)
        clip(pg, ".idents:not([data-live-ids]) .ident >> nth=0", ".idents:not([data-live-ids]) .ident >> nth=-1", "form_accepted_idents.png", pad=6)

        # Sample audit: run it, then the printable report
        pg.set_viewport_size({"width": 1180, "height": 900})
        pg.goto(BASE + "/audit/new"); pg.wait_for_timeout(500)
        with pg.expect_navigation():
            pg.get_by_role("button", name="Run the sample audit").first.click()
        pg.wait_for_selector(".card.au-check"); pg.wait_for_timeout(800)
        audit_url = pg.url
        pg.goto(audit_url + "/report"); pg.wait_for_timeout(1200)
        item = pg.locator(".item", has_text="050815B0100").first.element_handle()
        r = pg.evaluate(BOX_JS, [item, item, 10])
        pg.screenshot(path=str(OUT / "report_item_050815B0100.png"), clip=r, full_page=True)
        print("saved report_item_050815B0100.png from", audit_url + "/report")
        pg.set_viewport_size({"width": 700, "height": 900})  # narrower: the report text reads at slide size
        pg.goto(audit_url + "/report"); pg.wait_for_timeout(1200)
        clip(pg, "h1", "table.sum", "report_head.png", pad=20)
        b.close()


if __name__ == "__main__":
    main()
