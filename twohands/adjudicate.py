"""Amendment 2 (b): every field where a reader disagrees with the official PREP capture, ready for a person.

    python -m twohands.adjudicate [--model gemma] [--only CLAVE[,CLAVE]]

For each disagreement it writes a crop of the MASKED page (never a raw image) to
results/adjudication/<clave>__<FIELD>.jpg, and records model digits/words/label, the PREP value and the certified
Computos value in results/adjudication/adjudication.jsonl with an empty ``verdict`` for a human:
model_right | capture_right | paper_ambiguous | unreadable. Verdicts already filled in are kept on re-runs.
It also writes results/adjudication/SHEET.md (one row per disagreement, crop inline) for review.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw

from twohands import REPO, schema
from twohands.run import jsonl
from twohands.sample import PREP_CSV, load_rows

OUT = REPO / "results" / "adjudication"
COMP_CSV = REPO / "data" / "raw" / "computos" / "PRES_2024.csv"
VERDICTS = ("model_right", "capture_right", "paper_ambiguous", "unreadable")
COMP_ALIAS = {"PAN-PRI-PRD": "PAN_PRI_PRD", "PAN-PRI": "PAN_PRI", "PAN-PRD": "PAN_PRD", "PRI-PRD": "PRI_PRD",
              "NO_REGISTRADAS": "CANDIDATO/A NO REGISTRADO/A", "NULOS": "VOTOS NULOS"}


def num(v):
    v = (v or "").strip().replace(",", "")
    return int(v) if v.isdigit() else None


def load_comp(claves: set) -> dict:
    if not COMP_CSV.is_file():
        return {}
    t = COMP_CSV.read_bytes().decode("utf-8-sig", "replace").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = next(k for k, l in enumerate(t) if l.startswith("CLAVE_CASILLA"))
    out = {}
    for r in csv.DictReader(io.StringIO("\n".join(t[i:])), delimiter="|"):
        k = r["CLAVE_CASILLA"].strip("'")
        if k in claves:
            out[k] = r
    return out


def boxes(s: dict) -> dict:
    from app.crops import field_boxes  # the app's measured per-field boxes (all left of the privacy mask)
    return field_boxes(s)


def crop(page_path: Path, box, out: Path, pad: float = 0.022) -> None:
    im = Image.open(page_path).convert("RGB")
    W, H = im.size
    x0, y0, x1, y1 = box
    c = im.crop((int(x0 * W), int(max(0, y0 - pad) * H), int(min(0.657, x1) * W), int(min(1, y1 + pad) * H)))
    d = ImageDraw.Draw(c)  # mark the field's own band
    d.rectangle([0, int(pad * H) - 2, c.size[0] - 1, int((y1 - y0 + pad) * H) + 2], outline=(255, 0, 160), width=2)
    out.parent.mkdir(parents=True, exist_ok=True)
    c.save(out, "JPEG", quality=90)


def main(argv=None) -> list:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma")
    ap.add_argument("--only", default=None)
    a = ap.parse_args(argv)
    s = schema.load()
    rows = {}
    for r in jsonl(REPO / "results" / f"calls_{a.model}.jsonl"):
        rows[r["clave"]] = r
    only = set(a.only.split(",")) if a.only else None
    claves = {k for k in rows if (only is None or k in only)}
    prep = {r["CLAVE_CASILLA"]: r for r in load_rows(PREP_CSV) if r["CLAVE_CASILLA"] in claves}
    comp = load_comp(claves)
    bx = boxes(s)
    ledger = OUT / "adjudication.jsonl"
    old = {(r["clave"], r["field"], r["model_key"]): r for r in jsonl(ledger)}
    out = dict(old)
    for k in sorted(claves):
        r = rows[k]
        if r.get("no_call") or not r.get("parsed_ok") or k not in prep:
            continue
        for f in s["fields"]:
            if not f.get("csv"):
                continue
            fld = (r.get("fields") or {}).get(f["key"]) or {}
            m, p = fld.get("n"), num(prep[k][f["csv"]])
            if m == p:
                continue
            cp = comp.get(k, {})
            ccol = COMP_ALIAS.get(f["csv"], f["csv"])
            cval = num(cp.get(ccol)) if cp else None
            img = REPO / r["image"]
            cpath = OUT / f"{k}__{f['key']}.jpg"
            crop(img, bx[f["key"]], cpath)
            key = (k, f["key"], a.model)
            prev = old.get(key, {})
            out[key] = {"clave": k, "field": f["key"], "model_key": a.model, "model_n": m, "model_w": fld.get("w"),
                        "model_label": fld.get("label"), "prep": p, "prep_raw": prep[k][f["csv"]], "computos": cval,
                        "computos_obs": (cp.get("OBSERVACIONES") or "").strip() if cp else None,
                        "form_accepted": r.get("accepted"), "crop": cpath.relative_to(REPO).as_posix(),
                        "page": r["image"], "verdict": prev.get("verdict"), "note": prev.get("note", "")}
    OUT.mkdir(parents=True, exist_ok=True)
    recs = sorted(out.values(), key=lambda x: (x["clave"], x["field"]))
    ledger.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in recs), encoding="utf-8")
    lines = ["# Adjudication sheet (Amendment 2 b)", "",
             "Every field where the reader disagrees with the PREP capture. Crops are cut from masked pages only.",
             f"Verdict: one of {', '.join(VERDICTS)}. Edit `adjudication.jsonl` (`verdict`, `note`).", "",
             "| clave | field | model digits / words | PREP | Computos | form | verdict | crop |", "|---|---|---|---|---|---|---|---|"]
    for x in recs:
        lines.append(f"| {x['clave']} | {x['field']} | {x['model_n']} / {x['model_w']} | {x['prep_raw'] or '-'} | "
                     f"{x['computos'] if x['computos'] is not None else '-'} | {'accepted' if x['form_accepted'] else 'routed'} | "
                     f"{x['verdict'] or ''} | ![]({Path(x['crop']).name}) |")
    (OUT / "SHEET.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(len(recs), "disagreements;", sum(1 for x in recs if x["verdict"]), "with a verdict")
    return recs


if __name__ == "__main__":
    main()
