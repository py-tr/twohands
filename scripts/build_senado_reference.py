"""Build the Senate acta's rectification assets from 20 pilot pages, the way scripts/build_template.py and Amendment 1
built the presidential ones. No model call.

    python scripts/build_senado_reference.py

Pilot pages: the first 10 Escaner and the first 10 Movil eligible Senate actas (PROTOCOL_SENADO 2.1 rules) of federal
district Aguascalientes 1, in CLAVE_CASILLA order. They are excluded from the draw (results/senado/pilot.json).
Each is downloaded to data/raw/img/ (gitignored), located with the presidential Amendment 1 locator (same printed
geometry), kept only in memory, and the raw file is deleted at once. From the located pages:
  schemas/mx_senado_2024.template.npy    96x62 orientation template (mean, normalised), mask area zeroed
  schemas/mx_senado_2024.reference.npy   600x388 fine-alignment reference (mean page, blurred), mask area zeroed
  schemas/mx_senado_2024.landmarks.npy   1200x776 landmark reference (mean aligned page), mask area zeroed
  schemas/mx_senado_2024.feature_ref.jpg one MASKED pilot scan at 1200x776 (SIFT registration)
None of them holds a name or a signature. Then every pilot page is re-located with the Senate assets (check).
"""
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, landmarks as LM, mask, register, sample, schema  # noqa: E402

PRES = schema.load()
S = schema.load("mx_senado_2024")
SRC = schema.source(S)
L = S["layout"]
SDIR = Path(S["_dir"])
RAW = REPO / "data" / "raw" / "img"
OUT = REPO / SRC["results_dir"] / "pilot.json"
N_EACH = 10


def zero_mask(a):
    a = a.copy()
    h, w = a.shape
    for x0, y0, x1, y1 in schema.mask_rects(S, "escaner"):
        a[int(y0 * h):int(np.ceil(y1 * h)), int(np.floor(x0 * w)):int(np.ceil(x1 * w))] = 0.0
    return a


def fetch(url: str, dst: Path) -> None:
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=sample.UA)
            dst.write_bytes(urllib.request.urlopen(req, timeout=90).read())
            return
        except Exception:  # noqa: BLE001
            time.sleep(5 * (i + 1))
    raise RuntimeError("download failed")


def load_raw(p: Path) -> Image.Image:
    with Image.open(p) as im:
        im.load()
        return im.copy()


def pilot_rows() -> list[dict]:
    rows = sample.load_rows(REPO / SRC["prep_csv"])
    el, _ = sample.eligible(rows, set(), tipo=SRC["tipo_acta"], special_rule=True)
    el = sorted((r for r in el if int(r["ID_ENTIDAD"]) == 1 and int(r["ID_DISTRITO_FEDERAL"]) == 1),
                key=lambda r: r["CLAVE_CASILLA"])
    urls = sample.district_urls(1, 1, SRC["district_url"], REPO / SRC["district_cache"])
    out = []
    for kind in ("escaner", "movil"):
        out += [r for r in el if sample.capture(r["DIGITALIZACION"]) == kind and r["CLAVE_CASILLA"] in urls][:N_EACH]
    return [dict(r, _url=urls[r["CLAVE_CASILLA"]][0]) for r in out]


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    pilot = pilot_rows()
    pages, log, imgs = [], [], {}
    for r in pilot:
        k, kind = r["CLAVE_CASILLA"], sample.capture(r["DIGITALIZACION"])
        raw = RAW / f"senpilot_{k}.jpg"
        rec = {"clave": k, "layout": kind, "url": r["_url"]}
        try:
            fetch(r["_url"], raw)
            img = load_raw(raw)
        finally:
            raw.unlink(missing_ok=True)  # the raw (unmasked) image is never kept on disk
        imgs[k] = img
        try:
            loc = register.rectify_v2(img, PRES["layout"], schema.template(PRES), schema.reference(PRES),
                                      schema.landmark_ref(PRES))
            pages.append((k, kind, loc.image))
            rec["presidential_assets"] = {"located": True, "ecc": loc.ecc, "worst_px": loc.worst_px}
        except register.NotLocated as e:
            rec["presidential_assets"] = {"located": False, "reason": str(e)}
        log.append(rec)
        print(k, kind, rec["presidential_assets"])
    gray = [pg.convert("L") for _, _, pg in pages]
    T = np.mean([register._tvec(g) for g in gray], 0)
    T = (T - T.mean()) / T.std()
    np.save(SDIR / L["template"], zero_mask(T).astype(np.float32))
    R = np.mean([np.asarray(g.resize(register.REF_SIZE, Image.BILINEAR), dtype=np.float32) for g in gray], 0)
    R = cv2.GaussianBlur(R, (3, 3), 0)
    np.save(SDIR / L["reference"], zero_mask(R).astype(np.float32))
    LMR = LM.build_reference(gray)
    np.save(SDIR / L["landmarks"], zero_mask(LMR).astype(np.float16))
    k0, kind0, pg0 = next(p for p in pages if p[1] == "escaner")
    fr = mask.apply_mask(pg0, schema.mask_rects(S, "escaner")).resize(LM.WORK, Image.BILINEAR)
    fr.convert("RGB").save(SDIR / L["feature_ref"], "JPEG", quality=90)
    schema.load.cache_clear()
    s2 = schema.load("mx_senado_2024")
    ok = 0
    for rec in log:
        try:
            pg, info = mask.prepare(imgs[rec["clave"]], rec["layout"], s2)
            rec["senate_assets"] = {"located": True, "ecc": info["ecc"], "worst_px": info["landmark_worst_px"]}
            ok += 1
        except register.NotLocated as e:
            rec["senate_assets"] = {"located": False, "reason": str(e)}
    imgs.clear()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"purpose": "Senate rectification assets (scripts/build_senado_reference.py); excluded "
                                          "from the PROTOCOL_SENADO draw", "district": "01-01",
                               "feature_ref_page": k0, "n_pages_used": len(pages), "pages": log},
                              indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"assets from {len(pages)} of {len(log)} pilot pages; re-located with the Senate assets: {ok}/{len(log)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
