"""Amendment 5 (draft) national extension: a FRESH stratified draw (seed 20261018, n=3000, the same eligibility rules
and state x capture strata as PROTOCOL.md section 2, proportional allocation by largest remainder, within-stratum
shuffle random.Random("20261018:<stratum>"), the same replacement rule), EXCLUDING the 300 run actas, the 43 pilot
actas, the 150 calibration actas, the 100 confirmation actas and every Colima (ID_ENTIDAD 6) acta (Colima is covered
by the complete-state run). No model call.

    python scripts/ext_draw.py              # -> results/manifest_ext3000.json (+ sha256)
    python scripts/ext_draw.py --prepare    # download + rectify + mask (Amendment 1 locator) into data/masked/ext3000/,
                                            #   raw deleted; resumable; log results/prepare_ext3000.jsonl
"""
import collections, hashlib, json, random, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, sample

SEED, N, COLIMA = 20261018, 3000, 6
OUT = REPO / "results" / "manifest_ext3000.json"
PREP_LOG = REPO / "results" / "prepare_ext3000.jsonl"
MASKED = REPO / "data" / "masked" / "ext3000"
TERMINAL = ("ok", "not_located", "unreadable")


def _claves(p):
    return {i["clave"] for i in json.loads((REPO / "results" / p).read_text(encoding="utf-8"))["items"]}


def draw() -> None:
    spike = {x["clave"] for x in json.loads(sample.SPIKE_SAMPLE.read_text())}
    run, calib, conf = _claves("manifest.json"), _claves("calibration_manifest.json"), _claves("manifest_confirm100.json")
    rows = sample.load_rows()
    colima = {r["CLAVE_CASILLA"] for r in rows if int(r["ID_ENTIDAD"]) == COLIMA}
    excl = spike | run | calib | conf | colima
    el, why = sample.eligible(rows, excl)
    why = dict(why)
    n_ex = why.pop("spike (pilot) acta", 0)
    # break the exclusion-set count down (first matching set wins, in this order)
    el_pre, _ = sample.eligible(rows, set())
    br = collections.Counter()
    for r in el_pre:
        k = r["CLAVE_CASILLA"]
        for name, s in (("pilot 43", spike), ("run 300", run), ("calibration 150", calib),
                        ("confirmation 100", conf), ("Colima (complete-state run)", colima)):
            if k in s:
                br[name] += 1
                break
    assert sum(br.values()) == n_ex, (br, n_ex)
    for name, c in br.items():
        why[f"excluded set: {name}"] = c
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
        assert took == alloc[h], (h, took, alloc[h])
    # strata check against the 300: the 300's stratum sizes (Colima strata dropped), renormalised to n=3000
    m300 = json.loads(sample.MANIFEST.read_text(encoding="utf-8"))["strata"]
    ref_sizes = {h: v["size"] for h, v in m300.items() if not h.startswith(f"{COLIMA:02d}|")}
    ref = sample.allocate(ref_sizes, N)
    diff = {h: alloc.get(h, 0) - ref.get(h, 0) for h in sorted(set(ref) | set(alloc))}
    check = {"reference": "the 300's stratum sizes (PROTOCOL 2.2) without the 2 Colima strata, allocated to n=3000 "
                          "by the same largest-remainder rule",
             "max_abs_diff_forms": max(abs(d) for d in diff.values()),
             "strata_differing": {h: d for h, d in diff.items() if d},
             "x10_of_300_alloc_max_abs_diff": max(abs(alloc.get(h, 0) - 10 * v["n"]) for h, v in m300.items()
                                                  if not h.startswith(f"{COLIMA:02d}|"))}
    doc = {"protocol": "PROTOCOL_AMENDMENT5_DRAFT.md (national extension)", "seed": SEED, "n": N,
           "source": sample.PREP_ZIP_URL,
           "excludes": "the 300 run actas, the 43 pilot actas, the 150 calibration actas, the 100 confirmation actas "
                       "and every Colima (ID_ENTIDAD 6) acta",
           "population": {"csv_rows": len(rows), "eligible": len(el), "excluded_by_rule": why},
           "strata": {h: {"size": len(strata[h]), "n": alloc[h]} for h in sorted(strata)},
           "strata_check_vs_300": check,
           "items": items, "excluded_after_draw": excluded}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(items), "items;", collections.Counter(i["layout"] for i in items), len(excluded), "replaced;",
          "strata check max |diff|", check["max_abs_diff_forms"], "x10:", check["x10_of_300_alloc_max_abs_diff"],
          "; sha256", hashlib.sha256(OUT.read_bytes()).hexdigest(), flush=True)


_gate = threading.BoundedSemaphore(4)  # never more than 4 requests in flight against INE


def prepare(workers: int = 4) -> None:
    from twohands import run  # prepare_one: download (3 tries, backoff), rectify (Amendment 1), mask, delete raw
    assert run.mask.LOCATOR == "amendment1"
    run.MASKED = MASKED  # this extension's pages live in their own folder
    MASKED.mkdir(parents=True, exist_ok=True)
    items = json.loads(OUT.read_text(encoding="utf-8"))["items"]

    def one(it):
        with _gate:
            r = run.prepare_one(it)
        time.sleep(0.25)  # polite pacing between requests per worker
        return r

    def done_set():
        return {r["clave"] for r in run.jsonl(PREP_LOG) if r.get("status") in TERMINAL}

    for _pass in range(3):
        done = done_set()
        todo = [it for it in items if it["clave"] not in done]
        if not todo:
            break
        if _pass:
            time.sleep(120)  # back off before retrying download failures
        print(f"pass {_pass + 1}: {len(done)} done, {len(todo)} to fetch", flush=True)
        t0 = time.time()
        with ThreadPoolExecutor(min(workers, 4)) as ex:
            for i, r in enumerate(ex.map(one, todo), 1):
                r["ts"] = run.now()
                run.append(PREP_LOG, r)
                if i % 50 == 0 or r["status"] != "ok":
                    eta = (time.time() - t0) / i * (len(todo) - i) / 60
                    print(f"[{i}/{len(todo)} eta {eta:.0f} min] {r['clave']} {r['status']} {r.get('reason', '')[:80]}",
                          flush=True)
    last = {r["clave"]: r for r in run.jsonl(PREP_LOG)}
    c = collections.Counter((it["layout"], last.get(it["clave"], {}).get("status", "missing")) for it in items)
    raw_left = len(list(run.RAW.glob("*.jpg"))) if run.RAW.is_dir() else 0
    size = sum(f.stat().st_size for f in MASKED.glob("*.jpg"))
    print(json.dumps({"status": {f"{a}|{b}": n for (a, b), n in sorted(c.items())},
                      "masked_files": len(list(MASKED.glob("*.jpg"))), "masked_bytes": size, "raw_left": raw_left}),
          flush=True)


if __name__ == "__main__":
    prepare() if "--prepare" in sys.argv else draw()
