"""PROTOCOL.md Amendment 9: the Colima recall check (capture errors Gemma missed, on errors the certified count sees).

    python scripts/colima_recall.py build    # candidates -> results/colima/recall_candidates.json + masked crops in
                                             # results/colima/recall_crops/ (needs data/raw/; no model call)
    python scripts/colima_recall.py score    # -> results/colima/recall.json + .md (in progress until all answered)
    python scripts/colima_recall.py --check  # recompute; exit 1 if the committed files differ, or if the README,
                                             # lablab.md, slides, EVALUATION or the rendered Results page do not
                                             # carry the recall line (app/colima.recall_pitch); make eval

Candidate: a graded field the certified count covers (vote rows and TOTAL, the column mapping of
scripts/gemma_tf_reads2.py settle) on a form settled by cotejo, not recount (Computos row present, OBSERVACIONES without
"Recuento", the certified value an integer), where the certified count differs from the first capture (PREP) AND Gemma's
reading equals the capture. Caught: same rule, certified differs from the capture, Gemma equals the certified count.
Neither: the certified count differs from both (counted apart). The person's blind answers come from
/check?set=colimarecall (app/state/spotcheck_colimarecall.json); app/colima.recall_result labels and scores them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app import colima  # noqa: E402

AMENDMENT = "PROTOCOL.md Amendment 9"
PAD = 0.02   # as the capture-audit crops (app/capture_audit.py)


def compute() -> dict:
    """The candidates, the caught and the neither lists, from the PREP CSV, Computos and the Colima reads."""
    from scripts.gemma_tf_reads2 import CERT_COLS, Truth, colima_prepared, last
    from twohands import schema as schemamod
    from twohands.adjudicate import COMP_ALIAS, load_comp
    from twohands.gate import iv
    from twohands.sample import PREP_CSV, load_rows
    from twohands.tiers import digits, usable
    s = schemamod.load()
    keys = s["keys"]
    fs = {f["key"]: f for f in s["fields"]}
    graded = [f["key"] for f in s["fields"] if f.get("csv")]
    covered = [f for f in graded if fs[f].get("vote") or f == "TOTAL"]
    prepared = colima_prepared()
    G = last(colima.CALLS)
    rows = [r for r in load_rows(PREP_CSV) if r["CLAVE_CASILLA"].strip("'")[:2] == "06"
            and str(r.get("TIPO_ACTA", "")).strip() == "2"]
    prep = {r["CLAVE_CASILLA"].strip("'"): r for r in rows}
    ok = sorted(k for k, r in prepared.items() if r.get("status") == "ok")
    read = [k for k in ok if usable(G.get(k))]
    T = Truth([], prep, s)
    comp = load_comp(set(read))
    cand, caught, neither = [], [], []
    for k in read:
        cp = comp.get(k) or {}
        obs = (cp.get("OBSERVACIONES") or "").strip()
        if not cp or "Recuento" in obs:
            continue
        g = digits(G[k], keys)
        for f in covered:
            col = CERT_COLS.get(f, COMP_ALIAS.get(fs[f]["csv"], fs[f]["csv"]))
            cval = iv(str(cp.get(col, "")).strip())
            cap = T.capture(k, f)
            if cval is None or cval == cap:
                continue
            row = {"item": f"{k}__{f}", "form": k, "field": f, "capture": cap, "certified": cval, "gemma": g.get(f),
                   "obs": obs or "cotejo"}
            (cand if g.get(f) == cap else caught if g.get(f) == cval else neither).append(row)
    return {"amendment": AMENDMENT, "rule": colima.RECALL_RULE, "forms_read": len(read), "candidates": cand,
            "caught": caught, "neither": neither}


def cut_crops(C: dict, check: bool = False) -> list[str]:
    """Masked crops for the candidates, by the app's crop code (right of the row-label column: no logo, no name)."""
    from app import crops
    from scripts.gemma_tf_reads2 import colima_prepared
    from twohands.adjudicate import crop_name
    prepared = colima_prepared()
    missing = []
    for c in C["candidates"]:
        dst = colima.RECALL_CROPS / crop_name(c["form"], c["field"])
        if dst.is_file():
            continue
        if check:
            missing.append(dst.relative_to(REPO).as_posix())
            continue
        page = REPO / (prepared[c["form"]].get("image") or "")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(marked(crops.crop_bytes(str(page), page.stat().st_mtime, c["field"], PAD, False), c["field"]))
    return missing


def marked(jpg: bytes, field: str) -> bytes:
    """Outline the field's own band (as twohands.adjudicate.crop does): the crop shows its neighbours above and below,
    and without the logo column the person needs to see which row is asked."""
    import io
    from PIL import Image, ImageDraw
    from app import crops, store as storemod
    _, y0, _, y1 = crops.field_boxes(storemod.schema())[field]
    im = Image.open(io.BytesIO(jpg)).convert("RGB")
    top = max(0.0, y0 - PAD)
    H = im.size[1] / (min(1.0, y1 + PAD) - top)   # page height in pixels
    ImageDraw.Draw(im).rectangle([0, int((y0 - top) * H) - 2, im.size[0] - 1, int((y1 - top) * H) + 2],
                                 outline=(255, 0, 160), width=2)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def dump(d) -> str:
    return json.dumps(d, indent=1, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", choices=("build", "score"), default=None)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    from twohands.sample import PREP_CSV
    if a.check:
        bad = colima.recall_mismatches() + colima.recall_doc_mismatches() + colima.recall_page_mismatches()
        if PREP_CSV.is_file() and colima.RECALL_CAND.is_file():
            if json.loads(dump(compute())) != json.loads(colima.RECALL_CAND.read_text(encoding="utf-8")):
                bad.append("results/colima/recall_candidates.json (recomputed candidates differ)")
        print(f"colima_recall --check: {len(bad)} mismatches" + (f" ({', '.join(bad)})" if bad else ""))
        return 1 if bad else 0
    if a.cmd == "build":
        C = compute()
        colima.RECALL_CAND.write_text(dump(C), encoding="utf-8")
        cut_crops(C)
        print(f"colima_recall build: {len(C['candidates'])} candidates, {len(C['caught'])} caught, "
              f"{len(C['neither'])} neither, on {C['forms_read']} read forms; crops in "
              f"{colima.RECALL_CROPS.relative_to(REPO).as_posix()}/")
        return 0
    if a.cmd == "score":
        colima.write_recall()
        R = colima.recall_result()
        print(colima.recall_line(R))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
