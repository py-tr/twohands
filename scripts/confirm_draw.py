"""Amendment 3 confirmation set: a FRESH stratified draw (seed 20261017, n=100, the same eligibility rules and
state x capture strata as PROTOCOL.md section 2), excluding the 300 run actas, the 43 pilot actas and the 150
calibration actas. Same replacement rule (no image URL in the district file -> next in the stratum order).

    python scripts/confirm_draw.py            # -> results/manifest_confirm100.json (+ sha256)
    python scripts/confirm_draw.py --prepare  # download + rectify + mask (Amendment 1 locator) into data/masked/,
                                              #   raw deleted; log in results/prepare_confirm100.jsonl. No model call.
"""
import collections, hashlib, json, random, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, sample

SEED, N = 20261017, 100
OUT = REPO / "results" / "manifest_confirm100.json"
PREP_LOG = REPO / "results" / "prepare_confirm100.jsonl"


def draw() -> None:
    spike = {x["clave"] for x in json.loads(sample.SPIKE_SAMPLE.read_text())}
    run = {i["clave"] for i in json.loads(sample.MANIFEST.read_text(encoding="utf-8"))["items"]}
    calib = {i["clave"] for i in json.loads((REPO / "results" / "calibration_manifest.json").read_text(encoding="utf-8"))["items"]}
    rows = sample.load_rows()
    el, why = sample.eligible(rows, spike | run | calib)
    strata = collections.defaultdict(list)
    for r in el:
        strata[f"{int(r['ID_ENTIDAD']):02d}|{sample.capture(r['DIGITALIZACION'])}"].append(r)
    alloc = sample.allocate({h: len(v) for h, v in strata.items()}, N)
    items, excluded = [], []
    for h in sorted(strata):
        order = sorted(strata[h], key=lambda r: r["CLAVE_CASILLA"])
        random.Random(f"{SEED}:{h}").shuffle(order)
        took = 0
        for r in order:
            if took == alloc[h]:
                break
            ent, dist = int(r["ID_ENTIDAD"]), int(r["ID_DISTRITO_FEDERAL"])
            urls = sample.district_urls(ent, dist)
            k = r["CLAVE_CASILLA"]
            if k not in urls:
                excluded.append({"clave": k, "stratum": h, "reason": "no image URL in the PREP district file (replaced)"})
                continue
            items.append({"clave": k, "stratum": h, "entidad": r["ENTIDAD"], "id_entidad": ent, "distrito": dist,
                          "layout": sample.capture(r["DIGITALIZACION"]), "url": urls[k][0], "url_tipo": urls[k][1]})
            took += 1
    why = dict(why)
    why["excluded set (pilot 43 + run 300 + calibration 150)"] = why.pop("spike (pilot) acta", 0)
    doc = {"protocol": "PROTOCOL.md Amendment 3", "seed": SEED, "n": N, "source": sample.PREP_ZIP_URL,
           "excludes": "the 300 run actas, the 43 pilot actas and the 150 calibration actas",
           "population": {"csv_rows": len(rows), "eligible": len(el), "excluded_by_rule": why},
           "strata": {h: {"size": len(strata[h]), "n": alloc[h]} for h in sorted(strata)},
           "items": items, "excluded_after_draw": excluded}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(items), "items;", collections.Counter(i["layout"] for i in items), len(excluded), "replaced; sha256",
          hashlib.sha256(OUT.read_bytes()).hexdigest(), flush=True)


def prepare() -> None:
    from twohands import run  # prepare_one: download, rectify (Amendment 1 locator), mask, delete raw
    assert run.mask.LOCATOR == "amendment1"
    items = json.loads(OUT.read_text(encoding="utf-8"))["items"]
    done = {r["clave"] for r in run.jsonl(PREP_LOG) if r.get("status") in ("ok", "not_located", "unreadable")}
    todo = [it for it in items if it["clave"] not in done]
    for _pass in range(2):
        with ThreadPoolExecutor(2) as ex:
            for r in ex.map(run.prepare_one, todo):
                r["ts"] = run.now()
                run.append(PREP_LOG, r)
                print(r["clave"], r["status"], r.get("reason", ""), flush=True)
        done = {r["clave"] for r in run.jsonl(PREP_LOG) if r.get("status") in ("ok", "not_located", "unreadable")}
        todo = [it for it in items if it["clave"] not in done]
        if not todo:
            break
    c = collections.Counter()
    last = {r["clave"]: r for r in run.jsonl(PREP_LOG)}
    for it in items:
        c[(it["layout"], last.get(it["clave"], {}).get("status", "missing"))] += 1
    print(dict(c), flush=True)


if __name__ == "__main__":
    prepare() if "--prepare" in sys.argv else draw()
