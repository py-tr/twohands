"""Draw the pre-registered held-out sample (PROTOCOL.md section 2) and write the manifest.

    python -m twohands.sample            # -> results/manifest.json (+ prints its sha256)

Deterministic: the seed, the eligibility rules, the strata and the replacement rule are all here and in
PROTOCOL.md. No model is called. District JSONs (image URLs) are cached under data/raw/districts/.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
import random
import re
import time
import urllib.request
from pathlib import Path

from twohands import REPO

SEED = 20261015
N = 300
PREP_ZIP_URL = "https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip"
PREP_CSV = REPO / "data" / "raw" / "prep" / "PRES_2024.csv"
DIST_URL = "https://prep2024.ine.mx/publicacion/nacional/assets/presidencia/entidad/{ent}_{dist}.json"
DIST_DIR = REPO / "data" / "raw" / "districts"
SPIKE_SAMPLE = REPO.parent / "spikes" / "tally-witness" / "data" / "sample.json"
MANIFEST = REPO / "results" / "manifest.json"
UA = {"User-Agent": "Mozilla/5.0 (two-hands research; clerical capture QA)"}


def capture(dig: str) -> str | None:
    d = (dig or "").strip()
    return "movil" if d.startswith("M") and d.endswith("vil") else ("escaner" if d.startswith("Esc") else None)


def load_rows(path: Path = PREP_CSV) -> list[dict]:
    t = path.read_bytes().decode("utf-8-sig", "replace").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = next(k for k, l in enumerate(t) if l.startswith("CLAVE_CASILLA"))
    rows = list(csv.DictReader(io.StringIO("\n".join(t[i:]))))
    for r in rows:
        r["CLAVE_CASILLA"] = r["CLAVE_CASILLA"].strip("'")
    return rows


def eligible(rows: list[dict], exclude: set[str]) -> tuple[list[dict], collections.Counter]:
    """PROTOCOL 2.1. Returns (eligible rows, counts of each exclusion reason)."""
    why = collections.Counter()
    n_key = collections.Counter(r["CLAVE_CASILLA"] for r in rows if r["TIPO_ACTA"].strip() == "2")
    out = []
    for r in rows:
        if r["TIPO_ACTA"].strip() != "2":
            why["not a presidential casilla acta (TIPO_ACTA != 2)"] += 1
        elif r["TIPO_DOCUMENTO"].strip() != "Acta PREP":
            why[f"document is not the Acta PREP ({r['TIPO_DOCUMENTO'].strip() or '-'})"] += 1
        elif capture(r["DIGITALIZACION"]) is None:
            why["no image captured (DIGITALIZACION not Movil/Escaner)"] += 1
        elif n_key[r["CLAVE_CASILLA"]] > 1:
            why["CLAVE_CASILLA not unique in the CSV"] += 1
        elif r["CLAVE_CASILLA"] in exclude:
            why["spike (pilot) acta"] += 1
        else:
            out.append(r)
    return out, why


def allocate(sizes: dict, n: int) -> dict:
    """Proportional allocation, largest remainder (ties: stratum name)."""
    tot = sum(sizes.values())
    q = {h: n * s / tot for h, s in sizes.items()}
    a = {h: int(v) for h, v in q.items()}
    for h in sorted(q, key=lambda h: (-(q[h] - a[h]), h))[: n - sum(a.values())]:
        a[h] += 1
    return a


def clave_of(ent: int, sec: str, key: str) -> str | None:
    if key == "basica":
        t, n, e = "B", 1, 0
    elif m := re.fullmatch(r"contigua(\d+)", key):
        t, n, e = "C", int(m[1]), 0
    elif m := re.fullmatch(r"extraordinaria(\d+)", key):
        t, n, e = "E", int(m[1]), 0
    elif m := re.fullmatch(r"extraordinaria(\d+)-contigua(\d+)", key):
        t, n, e = "E", int(m[1]), int(m[2])
    else:
        return None
    return f"{ent:02d}{int(sec):04d}{t}{n:02d}{e:02d}"


def district_urls(ent: int, dist: int) -> dict:
    fn = DIST_DIR / f"{ent}_{dist}.json"
    if not fn.exists():
        DIST_DIR.mkdir(parents=True, exist_ok=True)
        for i in range(4):
            try:
                req = urllib.request.Request(DIST_URL.format(ent=ent, dist=dist), headers=UA)
                fn.write_bytes(urllib.request.urlopen(req, timeout=120).read())
                break
            except Exception:  # noqa: BLE001
                time.sleep(5 * (i + 1))
    if not fn.exists():
        return {}
    J = json.loads(fn.read_text(encoding="utf-8"))
    out = {}
    for sec, v in J["secciones"]["listaSecciones"].items():
        for key, b in v["listaCasillas"]["body"].items():
            k = clave_of(ent, sec, key)
            if k and b.get("tabla") and str(b["tabla"][0].get("url", "")).startswith("http"):
                out[k] = (b["tabla"][0]["url"], b["tabla"][0].get("tipoDigitalizacion"))
    return out


def main() -> None:
    spike = {x["clave"] for x in json.loads(SPIKE_SAMPLE.read_text())}
    rows = load_rows()
    el, why = eligible(rows, spike)
    strata = collections.defaultdict(list)
    for r in el:
        strata[f"{int(r['ID_ENTIDAD']):02d}|{capture(r['DIGITALIZACION'])}"].append(r)
    alloc = allocate({h: len(v) for h, v in strata.items()}, N)
    items, excluded = [], []
    for h in sorted(strata):
        order = sorted(strata[h], key=lambda r: r["CLAVE_CASILLA"])
        random.Random(f"{SEED}:{h}").shuffle(order)
        took = 0
        for r in order:
            if took == alloc[h]:
                break
            ent, dist = int(r["ID_ENTIDAD"]), int(r["ID_DISTRITO_FEDERAL"])
            urls = district_urls(ent, dist)
            k = r["CLAVE_CASILLA"]
            if k not in urls:
                excluded.append({"clave": k, "stratum": h, "reason": "no image URL in the PREP district file (replaced)"})
                continue
            items.append({"clave": k, "stratum": h, "entidad": r["ENTIDAD"], "id_entidad": ent, "distrito": dist,
                          "layout": capture(r["DIGITALIZACION"]), "url": urls[k][0], "url_tipo": urls[k][1]})
            took += 1
    doc = {"protocol": "PROTOCOL.md", "seed": SEED, "n": N, "source": PREP_ZIP_URL,
           "population": {"csv_rows": len(rows), "eligible": len(el), "excluded_by_rule": dict(why)},
           "strata": {h: {"size": len(strata[h]), "n": alloc[h]} for h in sorted(strata)},
           "items": items, "excluded_after_draw": excluded}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(items), "items;", len(excluded), "replaced; sha256", hashlib.sha256(MANIFEST.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
