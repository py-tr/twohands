"""The cover image from slides/cover.html (headless Chromium via Playwright; no model call, no AI image generation).

    python scripts/render_cover.py    # static/cover.png (1920x1080) and static/cover-og.png (1200x630)
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "slides" / "cover.html"


def main() -> None:
    with sync_playwright() as p:
        b = p.chromium.launch()
        for out, (w, h), size in ((REPO / "static" / "cover.png", (1920, 1080), None),
                                  # same width, og aspect (1.905), then scaled to 1200x630
                                  (REPO / "static" / "cover-og.png", (1920, 1008), (1200, 630))):
            pg = b.new_page(viewport={"width": w, "height": h})
            pg.goto(SRC.as_uri())
            pg.wait_for_load_state("networkidle")
            png = pg.screenshot(full_page=False)
            im = Image.open(io.BytesIO(png)).convert("RGB")
            if size:
                im = im.resize(size, Image.LANCZOS)
            im.save(out, optimize=True)
            print(out.relative_to(REPO), im.size)
            pg.close()
        b.close()


if __name__ == "__main__":
    main()
