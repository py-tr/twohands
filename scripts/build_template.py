"""Build the orientation template (96x62) and the fine-alignment reference page (600x388) from upright
spike actas; the privacy-mask area is zeroed in both, so neither holds any name or signature. Run once.
    python scripts/build_template.py <dir with upright actas>"""
import sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import register, schema
s = schema.load(); L = s["layout"]
def zero_mask(a):
    h, w = a.shape
    for x0, y0, x1, y1 in schema.mask_rects(s, "escaner"):
        a[int(y0 * h):int(np.ceil(y1 * h)), int(np.floor(x0 * w)):int(np.ceil(x1 * w))] = 0.0
    return a
pages = []
T0 = schema.template(s)
for p in sorted(Path(sys.argv[1]).glob("*.jpg")):
    try:
        loc = register.rectify(Image.open(p), L, T0)  # first pass: T0 None -> assume upright
    except register.NotLocated as e:
        print("skip", p.name, e); continue
    pages.append(loc.image.convert("L"))
T = np.mean([register._tvec(pg) for pg in pages], 0); T = (T - T.mean()) / T.std()
np.save(Path(s["_dir"]) / L["template"], zero_mask(T).astype(np.float32))
R = np.mean([np.asarray(pg.resize(register.REF_SIZE, Image.BILINEAR), dtype=np.float32) for pg in pages], 0)
R = cv2.GaussianBlur(R, (3, 3), 0)
R = zero_mask(R) ; R[R == 0] = 0.0
np.save(Path(s["_dir"]) / L["reference"], R.astype(np.float32))
print("template + reference from", len(pages), "pages")
