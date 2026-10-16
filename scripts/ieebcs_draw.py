"""PROTOCOL_IEEBCS: the head-to-head sample on Baja California Sur's own 2024 local PREP (IEEBCS). No model call.

    python scripts/ieebcs_draw.py fetch      # the PREP database zip + the two per-casilla JSONs (cached, polite)
    python scripts/ieebcs_draw.py draw       # -> results/manifest_ieebcs300.json (+ sha256)
    python scripts/ieebcs_draw.py official   # -> results/ieebcs/official.json (the published value of every drawn acta)
    python scripts/ieebcs_draw.py prepare    # download + locate + mask into data/masked/ieebcs/, raw deleted at once;
                                             #   log results/ieebcs/prepare.jsonl (the runner reads it on resume)

Population: every row of BCS_DIP_LOC_2024.csv and BCS_AYUN_2024.csv (20240603_2001_PREP_BCS.zip, the final cut) whose
acta image is published: the image file name on the PREP site is the row's CODIGO_INTEGRIDAD, and the published image
list is the union of the "Acta digitalizada" URLs in diputaciones_votos_por_casilla.json and
ayuntamiento_votos_por_casilla_nivel_municipio_seccion.json. Only actas with no image are excluded (count reported).
Strata: election x municipality (a diputaciones acta's municipality comes from its seccion, via the ayuntamiento
CSV), proportional allocation by largest remainder, n = 300, within-stratum order: sorted by (CLAVE_ACTA, image hash),
shuffled with random.Random("20261020:<stratum>"). The image file name (CODIGO_INTEGRIDAD) is the acta's
identity: some CLAVE_ACTA values carry more than one row (pages of special-station actas).

Fetching: <= 2 requests/s overall, a named User-Agent, every file cached (data/raw/ieebcs/, gitignored); a raw acta
image is deleted as soon as its masked page is written (or the page is rejected).
"""
from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
import random
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, sample  # noqa: E402

SEED, N = 20261020, 300
BASE = "https://prep2024.ieebcs.org.mx"
ZIP_URL = f"{BASE}/bdatos/20240603_2001_PREP_BCS.zip"
JSONS = {"dip": f"{BASE}/js/json/diputaciones_votos_por_casilla.json",
         "ayun": f"{BASE}/js/json/ayuntamiento_votos_por_casilla_nivel_municipio_seccion.json"}
IMG_URL = "https://prep-test-2023.s3.us-east-1.amazonaws.com/actas/{h}.jpeg"
RAWDIR = REPO / "data" / "raw" / "ieebcs"
CSVS = {"dip": RAWDIR / "bdatos" / "20240603_2001_PREP_DIP_LOC_BCS" / "BCS_DIP_LOC_2024.csv",
        "ayun": RAWDIR / "bdatos" / "20240603_2001_PREP_AYUN_BCS" / "BCS_AYUN_2024.csv"}
JSON_CACHE = {"dip": RAWDIR / "site" / "dip_casilla.json", "ayun": RAWDIR / "site" / "ayu_casilla.json"}
# Special-station actas (TIPO_ACTA 05 = diputaciones MR, 06 = diputaciones RP, 07 = ayuntamiento) print another form
# (3 left-column sections, 4-digit boxes, RP: one row per party). No schema covers them: they stay in the population and
# the sample, are never read, and every published numeric field of theirs counts as unmatched (PROTOCOL_IEEBCS 3.3).
SPECIAL = ("05", "06", "07")
SCHEMA = {"dip": "mx_bcs_dl_2024", "ayun": "mx_bcs_ayto_2024"}
ELECTION = {"dip": "diputaciones locales", "ayun": "ayuntamientos"}
OUT = REPO / "results" / "manifest_ieebcs300.json"
RES = REPO / "results" / "ieebcs"
MASKED = REPO / "data" / "masked" / "ieebcs"
UA = {"User-Agent": "TwoHands-research/1.0 (clerical capture QA; pre-registered 300-acta sample of the published "
                    "PREP BCS 2024 images; <=2 req/s)"}

_rl_lock, _rl_last = threading.Lock(), [0.0]


def polite_get(url: str, timeout: int = 90) -> bytes:
    """GET with the shared limiter (<= 2 requests/s across threads) and 3 tries."""
    err = None
    for i in range(3):
        with _rl_lock:
            wait = _rl_last[0] + 0.5 - time.time()
            if wait > 0:
                time.sleep(wait)
            _rl_last[0] = time.time()
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"GET failed: {type(err).__name__}: {str(err)[:120]}")


def fetch() -> None:
    z = RAWDIR / "bdatos" / "PREP_BCS.zip"
    if not z.is_file():
        z.parent.mkdir(parents=True, exist_ok=True)
        z.write_bytes(polite_get(ZIP_URL))
    for k, p in CSVS.items():
        if not p.is_file():
            with zipfile.ZipFile(z) as zf:
                inner = [n for n in zf.namelist() if n.endswith(".zip") and ("DIP_LOC" if k == "dip" else "AYUN") in n]
                if inner:
                    with zipfile.ZipFile(io.BytesIO(zf.read(inner[0]))) as z2:
                        z2.extractall(p.parent)
                else:
                    zf.extractall(RAWDIR / "bdatos")
    for k, u in JSONS.items():
        if not JSON_CACHE[k].is_file():
            JSON_CACHE[k].parent.mkdir(parents=True, exist_ok=True)
            JSON_CACHE[k].write_bytes(polite_get(u))
    print("zip sha256", hashlib.sha256(z.read_bytes()).hexdigest())


def load_rows(path: Path) -> list[dict]:
    t = path.read_bytes().decode("latin-1").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = next(k for k, l in enumerate(t) if l.startswith("CLAVE_CASILLA"))
    return [r for r in csv.DictReader(io.StringIO("\n".join(t[i:]))) if (r.get("CLAVE_ACTA") or "").strip()]


def image_hashes() -> set[str]:
    out = set()
    for p in JSON_CACHE.values():
        d = json.loads(p.read_text(encoding="utf-8"))
        geo = next(k for k in d if k.startswith("datos_"))
        for g in d[geo]:
            for s in g["datos_secciones"]:
                for c in s["datos_casillas"]:
                    for v in c["datos_votos"]:
                        u = str(v.get("candidatura_votos_cantidad"))
                        if v.get("candidatura_id") == 999999999 and u.startswith("http"):
                            out.add(u.rsplit("/", 1)[1].split(".")[0])
    return out


def variant(elec: str, r: dict, geo_cols: dict) -> str:
    """The printed layout of this acta: the schema, with '@variant' when the acta prints fewer section-6 rows (a party
    with no candidacy in that district / municipality: its CSV column is '-') or is a special-station acta."""
    base = SCHEMA[elec]
    if r["TIPO_ACTA"].strip() in SPECIAL:
        return base  # not covered: see SPECIAL
    present = geo_cols[(elec, r["ID_DISTRITO_LOCAL" if elec == "dip" else "ID_MUNICIPIO"])]
    if elec == "dip" and "PES" not in present:
        return base + "@sin_pes"
    if elec == "ayun" and "ML" not in present:
        return base + "@sin_ml"
    return base


def population():
    hashes = image_hashes()
    rows = {e: load_rows(p) for e, p in CSVS.items()}
    sec_mun = {r["SECCION"]: (r["ID_MUNICIPIO"], r["MUNICIPIO"]) for r in rows["ayun"]}
    geo_cols = {}
    for e, rs in rows.items():
        by = collections.defaultdict(list)
        for r in rs:
            by[r["ID_DISTRITO_LOCAL" if e == "dip" else "ID_MUNICIPIO"]].append(r)
        for g, grs in by.items():
            geo_cols[(e, g)] = {c for c in ("PES", "ML") if sum((x.get(c) or "-").strip() != "-" for x in grs) > len(grs) / 2}
    pop, why = [], collections.Counter()
    for e, rs in rows.items():
        for r in rs:
            h = (r.get("CODIGO_INTEGRIDAD") or "").strip()
            if h not in hashes:
                why[f"{ELECTION[e]}: no published acta image"] += 1
                continue
            mun = sec_mun.get(r["SECCION"])
            if mun is None:
                why[f"{ELECTION[e]}: seccion not in the ayuntamiento CSV (municipality unknown)"] += 1
                continue
            pop.append({"elec": e, "row": r, "hash": h, "mun_id": mun[0], "mun": mun[1],
                        "schema": variant(e, r, geo_cols)})
    return rows, pop, why


def draw() -> None:
    rows, pop, why = population()
    dup = collections.Counter(p["hash"] for p in pop)
    assert max(dup.values()) == 1, "an image is shared by two CSV rows"
    strata = collections.defaultdict(list)
    for p in pop:
        strata[f"{p['elec']}|{p['mun_id']}"].append(p)
    alloc = sample.allocate({h: len(v) for h, v in strata.items()}, N)
    items = []
    for h in sorted(strata):
        order = sorted(strata[h], key=lambda p: (p["row"]["CLAVE_ACTA"], p["hash"]))
        random.Random(f"{SEED}:{h}").shuffle(order)
        for p in order[: alloc[h]]:
            r = p["row"]
            d = r["DIGITALIZACION"].strip().upper()
            items.append({"clave": f"{r['CLAVE_ACTA'].strip()}_{p['hash'][:8]}", "clave_acta": r["CLAVE_ACTA"].strip(),
                          "clave_casilla": r["CLAVE_CASILLA"].strip(), "election": ELECTION[p["elec"]],
                          "schema": p["schema"], "covered": r["TIPO_ACTA"].strip() not in SPECIAL, "stratum": h, "municipio": p["mun"], "tipo_acta": r["TIPO_ACTA"].strip(),
                          "tipo_documento": r["TIPO_DOCUMENTO"].strip(), "origen": r["ORIGEN"].strip(),
                          "layout": "movil" if d.startswith("M") else "escaner", "image_id": p["hash"],
                          "url": IMG_URL.format(h=p["hash"])})
    zp = RAWDIR / "bdatos" / "PREP_BCS.zip"
    doc = {"protocol": "PROTOCOL_IEEBCS.md", "schema": sorted(SCHEMA.values()), "seed": SEED, "n": N,
           "source": ZIP_URL, "zip_sha256": hashlib.sha256(zp.read_bytes()).hexdigest(),
           "csv_sha256": {ELECTION[e]: hashlib.sha256(p.read_bytes()).hexdigest() for e, p in CSVS.items()},
           "image_lists": JSONS,
           "population": {"csv_rows": {ELECTION[e]: len(v) for e, v in rows.items()}, "with_image": len(pop),
                          "by_election": dict(collections.Counter(ELECTION[p["elec"]] for p in pop)),
                          "by_schema": dict(sorted(collections.Counter(p["schema"] if p["row"]["TIPO_ACTA"].strip() not in SPECIAL
                                                         else "special-station acta (not covered)" for p in pop).items())),
                          "excluded_by_rule": dict(why)},
           "strata": {h: {"size": len(strata[h]), "n": alloc[h]} for h in sorted(strata)},
           "items": items}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    c = collections.Counter((i["election"], i["schema"], i["layout"]) for i in items)
    print(len(items), "items;", dict(c), "; sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())


def num(v):
    v = (v or "").strip().replace(",", "")
    return int(v) if v.isdigit() else None


def official() -> None:
    """The published value of every field of every drawn acta, by schema key (the reference of PROTOCOL_IEEBCS 4)."""
    from twohands import schema
    man = json.loads(OUT.read_text(encoding="utf-8"))
    rows = {}
    for e, p in CSVS.items():
        for r in load_rows(p):
            rows[(r["CLAVE_ACTA"].strip(), r["CODIGO_INTEGRIDAD"].strip())] = r
    out = {}
    for it in man["items"]:
        r = rows[(it["clave_acta"], it["image_id"])]
        s = schema.load(it["schema"])
        out[it["clave"]] = {"schema": it["schema"],
                            "prep": {f["key"]: num(r.get(f["csv"])) for f in s["fields"] if f.get("csv")},
                            "prep_raw": {f["key"]: (r.get(f["csv"]) or "").strip() for f in s["fields"] if f.get("csv")},
                            "covered": it["covered"], "observaciones": (r.get("OBSERVACIONES") or "").strip(),
                            "source": "IEEBCS PREP 2024 final cut (20240603_2001_PREP_BCS.zip)"}
    RES.mkdir(parents=True, exist_ok=True)
    (RES / "official.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"published values for {len(out)} actas -> results/ieebcs/official.json")


def prepare() -> None:
    from concurrent.futures import ThreadPoolExecutor
    from twohands import mask, register, run, schema
    man = json.loads(OUT.read_text(encoding="utf-8"))
    log = RES / "prepare.jsonl"
    RES.mkdir(parents=True, exist_ok=True)
    done = {r["clave"] for r in run.jsonl(log) if r.get("status") in ("ok", "not_located", "unreadable", "not_covered")}
    raw_dir = RAWDIR / "img"
    raw_dir.mkdir(parents=True, exist_ok=True)

    def one(it):
        k = it["clave"]
        dst = MASKED / f"{k}.jpg"
        raw = raw_dir / f"{k}.jpeg"
        if not it["covered"]:
            return {"clave": k, "status": "not_covered", "reason": "special-station acta: printed layout not covered by "
                    "the schemas (PROTOCOL_IEEBCS 3.3); not downloaded, not read, its fields count as unmatched"}
        try:
            try:
                raw.write_bytes(polite_get(it["url"]))
            except RuntimeError as e:
                return {"clave": k, "status": "download_failed", "reason": str(e)}
            raw_sha = hashlib.sha256(raw.read_bytes()).hexdigest()
            try:
                page, info = mask.prepare(raw, it["layout"], schema.load(it["schema"]))
            except register.NotLocated as e:
                return {"clave": k, "status": "not_located", "reason": str(e), "raw_sha256": raw_sha}
            except Exception as e:  # noqa: BLE001
                return {"clave": k, "status": "unreadable", "reason": f"{type(e).__name__}: {str(e)[:120]}"}
            mask.save(page, dst)
            return {"clave": k, "status": "ok", "image": dst.relative_to(REPO).as_posix(), "info": info,
                    "raw_sha256": raw_sha}
        finally:
            raw.unlink(missing_ok=True)  # the raw (unmasked) image is never kept

    todo = [it for it in man["items"] if it["clave"] not in done]
    with ThreadPoolExecutor(2) as ex:
        for r in ex.map(one, todo):
            r["ts"] = run.now()
            run.append(log, r)
            print(r["clave"], r["status"], r.get("reason", ""))
    st = {r["clave"]: r["status"] for r in run.jsonl(log)}
    print(dict(collections.Counter(st[i["clave"]] for i in man["items"] if i["clave"] in st)))


if __name__ == "__main__":
    {"fetch": fetch, "draw": draw, "official": official, "prepare": prepare}[sys.argv[1]]()
