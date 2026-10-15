"""Amendment 1 calibration set: a FRESH stratified draw (seed 20261016, n=150, same strata rule), excluding the
300 run actas and the 43 pilot actas. Raw images go to data/raw/calib/ (gitignored) and are deleted after tuning.
    python scripts/calib_draw.py"""
import collections, hashlib, json, random, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, sample
SEED, N = 20261016, 150
spike = {x["clave"] for x in json.loads(sample.SPIKE_SAMPLE.read_text())}
run = {i["clave"] for i in json.loads(sample.MANIFEST.read_text(encoding="utf-8"))["items"]}
el, why = sample.eligible(sample.load_rows(), spike | run)
strata = collections.defaultdict(list)
for r in el:
    strata[f"{int(r['ID_ENTIDAD']):02d}|{sample.capture(r['DIGITALIZACION'])}"].append(r)
alloc = sample.allocate({h: len(v) for h, v in strata.items()}, N)
items = []
for h in sorted(strata):
    order = sorted(strata[h], key=lambda r: r["CLAVE_CASILLA"]); random.Random(f"{SEED}:{h}").shuffle(order)
    took = 0
    for r in order:
        if took == alloc[h]: break
        urls = sample.district_urls(int(r["ID_ENTIDAD"]), int(r["ID_DISTRITO_FEDERAL"]))
        if r["CLAVE_CASILLA"] not in urls: continue
        items.append({"clave": r["CLAVE_CASILLA"], "stratum": h, "layout": sample.capture(r["DIGITALIZACION"]), "url": urls[r["CLAVE_CASILLA"]][0]})
        took += 1
out = REPO / "results" / "calibration_manifest.json"
out.write_text(json.dumps({"seed": SEED, "n": N, "excludes": "the 300 run actas and the 43 pilot actas", "items": items}, indent=1), encoding="utf-8")
print(len(items), collections.Counter(i["layout"] for i in items), hashlib.sha256(out.read_bytes()).hexdigest(), flush=True)
d = REPO / "data" / "raw" / "calib"; d.mkdir(parents=True, exist_ok=True)
for it in items:
    f = d / f"{it['clave']}.jpg"
    if f.exists(): continue
    for i in range(3):
        try:
            f.write_bytes(urllib.request.urlopen(urllib.request.Request(it["url"], headers=sample.UA), timeout=90).read()); break
        except Exception as e:
            print("dl fail", it["clave"], e, flush=True); time.sleep(5)
print("downloaded", len(list(d.glob("*.jpg"))), flush=True)
