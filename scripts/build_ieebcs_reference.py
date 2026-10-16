"""PROTOCOL_IEEBCS 3.1: the rectification assets of the two BCS schemas and their row variants, from pilot pages, the
way scripts/build_senado_reference.py built the Senate ones. No model call; no value is read from any page.

    python scripts/build_ieebcs_reference.py

Pilot pages: per printed layout (mx_bcs_dl_2024, @sin_pes, mx_bcs_ayto_2024, @sin_ml) the first 3 Escaner and the
first 3 Movil actas in CLAVE_ACTA order of the population that are NOT in the drawn sample (the draw was made first and
is unaffected). Each is downloaded to data/raw/ieebcs/img/ (politely), located with the corner markers only (no
template yet), kept in memory, and the raw file is deleted at once. Per layout:
  <slug>[.<variant>].template.npy    96x62 orientation template (mean, normalised), mask area zeroed
  <slug>[.<variant>].reference.npy   600x388 fine-alignment reference (mean page, blurred), mask area zeroed
  <slug>[.<variant>].landmarks.npy   1200x776 landmark reference (mean aligned page), mask area zeroed
  <slug>[.<variant>].feature_ref.jpg one MASKED pilot scan at 1200x776 (SIFT registration)
None holds a name or a signature. Every pilot page is then re-located with the new assets (the protocol locator).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from twohands import REPO, landmarks as LM, mask, register, schema  # noqa: E402
import ieebcs_draw as D  # noqa: E402

N_EACH = 3
OUT = REPO / "results" / "ieebcs" / "pilot.json"


def zero_mask(a, s):
    a = a.copy()
    h, w = a.shape
    for x0, y0, x1, y1 in schema.mask_rects(s, "escaner"):
        a[int(y0 * h):int(np.ceil(y1 * h)), int(np.floor(x0 * w)):int(np.ceil(x1 * w))] = 0.0
    return a


def main() -> int:
    man = json.loads(D.OUT.read_text(encoding="utf-8"))
    drawn = {i["image_id"] for i in man["items"]}
    _, pop, _ = D.population()
    raw_dir = D.RAWDIR / "img"
    raw_dir.mkdir(parents=True, exist_ok=True)
    report = {"purpose": "rectification assets of the BCS schemas (scripts/build_ieebcs_reference.py); pilot pages are "
                         "outside the drawn sample; no value was read", "layouts": {}}
    for name in ("mx_bcs_dl_2024", "mx_bcs_dl_2024@sin_pes", "mx_bcs_ayto_2024", "mx_bcs_ayto_2024@sin_ml"):
        cand = sorted((p for p in pop if p["schema"] == name and p["hash"] not in drawn
                       and p["row"]["TIPO_ACTA"].strip() not in D.SPECIAL),
                      key=lambda p: (p["row"]["CLAVE_ACTA"], p["hash"]))
        pilot = []
        for kind in ("ESCANER", "MOVIL"):
            pilot += [p for p in cand if p["row"]["DIGITALIZACION"].strip().upper() == kind][:N_EACH]
        s = schema.load(name)
        L = s["layout"]
        sdir = Path(s["_dir"])
        pages, log, imgs = [], [], {}
        for p in pilot:
            k = f"{p['row']['CLAVE_ACTA'].strip()}_{p['hash'][:8]}"
            kind = "movil" if p["row"]["DIGITALIZACION"].strip().upper().startswith("M") else "escaner"
            raw = raw_dir / f"pilot_{k}.jpeg"
            try:
                raw.write_bytes(D.polite_get(D.IMG_URL.format(h=p["hash"])))
                with Image.open(raw) as im:
                    im.load()
                    img = im.copy()
            finally:
                raw.unlink(missing_ok=True)  # the raw (unmasked) image is never kept
            imgs[k] = (img, kind)
            rec = {"clave": k, "layout": kind}
            try:
                loc = register.rectify(img, L)
                pages.append((k, kind, loc.image))
                rec["markers_only"] = {"located": True, "markers_found": loc.markers_found}
            except register.NotLocated as e:
                rec["markers_only"] = {"located": False, "reason": str(e)}
            log.append(rec)
        gray = [pg.convert("L") for _, _, pg in pages]
        T = np.mean([register._tvec(g) for g in gray], 0)
        T = (T - T.mean()) / T.std()
        np.save(sdir / L["template"], zero_mask(T, s).astype(np.float32))
        R = np.mean([np.asarray(g.resize(register.REF_SIZE, Image.BILINEAR), dtype=np.float32) for g in gray], 0)
        np.save(sdir / L["reference"], zero_mask(cv2.GaussianBlur(R, (3, 3), 0), s).astype(np.float32))
        np.save(sdir / L["landmarks"], zero_mask(LM.build_reference(gray), s).astype(np.float16))
        k0, _, pg0 = next(p for p in pages if p[1] == "escaner")
        fr = mask.apply_mask(pg0, schema.mask_rects(s, "escaner")).resize(LM.WORK, Image.BILINEAR)
        fr.convert("RGB").save(sdir / L["feature_ref"], "JPEG", quality=90)
        schema.load.cache_clear()
        s2 = schema.load(name)
        ok = 0
        for rec in log:
            img, kind = imgs[rec["clave"]]
            try:
                _, info = mask.prepare(img, kind, s2)
                rec["protocol_locator"] = {"located": True, "ecc": info["ecc"], "worst_px": info["landmark_worst_px"]}
                ok += 1
            except register.NotLocated as e:
                rec["protocol_locator"] = {"located": False, "reason": str(e)}
        imgs.clear()
        report["layouts"][name] = {"n_pages_used": len(pages), "feature_ref_page": k0, "pages": log}
        print(f"{name}: assets from {len(pages)}/{len(log)} pilot pages; re-located with them: {ok}/{len(log)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
