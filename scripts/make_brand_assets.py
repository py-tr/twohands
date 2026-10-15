"""Make static/favicon.png, static/apple-touch-icon.png and static/og.jpg (social preview).

    python scripts/make_brand_assets.py

The social preview is cut from a privacy-masked page only (data/masked/**), left of the mask edge, with the
gate's verdict drawn over the fields: green = consistent, red = the field the paper could not settle.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import hero  # noqa: E402
from app import store as storemod  # noqa: E402
from app.crops import field_boxes  # noqa: E402

STATIC = storemod.REPO / "static"
ACCENT, BAR = (48, 71, 192), (18, 20, 26)


def font(size, bold=False):
    for name in (["seguisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"] if bold else
                 ["segoeui.ttf", "DejaVuSans.ttf", "arial.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def mark(size):
    s = 4 * size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = s / 32
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=8 * u, fill=ACCENT)
    for x in (9, 17):
        d.rectangle([x * u, 9 * u, (x + 6) * u, 23 * u], outline="white", width=max(1, round(2 * u)))
        d.ellipse([(x + 3 - 1.6) * u, (16 - 1.6) * u, (x + 3 + 1.6) * u, (16 + 1.6) * u], fill="white")
    return im.resize((size, size), Image.LANCZOS)


def og():
    st = storemod.get_store()
    src = st.masked_image(hero.HERO_FORM)
    page = Image.open(src).convert("RGB")
    W, H = page.size
    boxes = field_boxes(storemod.schema())
    ev = storemod.evaluate(st.default_read(hero.HERO_FORM))
    crop_box = (int(0.392 * W), int(0.122 * H), int(0.655 * W), int(0.724 * H))  # words + digits only: no logos, no header
    c = page.crop(crop_box)
    ov = Image.new("RGBA", c.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for f in ev["fields"]:
        b = boxes.get(f["key"])
        if not b or b[0] < 0.30:  # vote rows and TOTAL only
            continue
        x0, y0, x1, y1 = (max(b[0] * W, crop_box[0] + 3) - crop_box[0], b[1] * H - crop_box[1], min(b[2], 0.655) * W - crop_box[0], b[3] * H - crop_box[1])
        ok = f["status"] == "ok"
        d.rectangle([x0, y0, x1, y1], fill=(21, 112, 66, 40) if ok else (179, 38, 30, 70),
                    outline=(21, 112, 66, 200) if ok else (179, 38, 30, 255), width=3 if ok else 5)
    c = Image.alpha_composite(c.convert("RGBA"), ov).convert("RGB")
    out = Image.new("RGB", (1200, 630), BAR)
    h = 630 - 2 * 40
    w = int(c.width * h / c.height)
    c = c.resize((w, h), Image.LANCZOS)
    out.paste(c, (1200 - w - 40, 40))
    d = ImageDraw.Draw(out)
    m = mark(64)
    out.paste(m, (60, 64), m)
    d.text((140, 76), "Two Hands", font=font(40, True), fill="white")
    d.text((60, 190), "The model reads.", font=font(58, True), fill="white")
    d.text((60, 262), "The paper decides.", font=font(58, True), fill=(140, 160, 255))
    y = 370
    for line in ("Touchless capture of self-checking", "paper forms. Open vision model on AMD;",
                 "the form's own arithmetic decides."):
        d.text((60, y), line, font=font(26), fill=(200, 204, 214))
        y += 38
    d.text((60, 540), "TOTAL: words say 162, digits say 262. Routed to a person.", font=font(20), fill=(140, 145, 155))
    out.save(STATIC / "og.jpg", "JPEG", quality=86, optimize=True)


if __name__ == "__main__":
    mark(64).save(STATIC / "favicon.png")
    mark(180).save(STATIC / "apple-touch-icon.png")
    og()
    print("wrote favicon.png, apple-touch-icon.png, og.jpg")
