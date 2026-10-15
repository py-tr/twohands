"""PROTOCOL_SENADO: the Senate acta sample (third measured form type). No model call.

    python scripts/senado_draw.py draw       # -> results/manifest_senado100.json (+ sha256)
    python scripts/senado_draw.py official   # -> app/data/official_senado.json (PREP's capture of the 100 Senate actas)
    python scripts/senado_draw.py prepare    # download + locate + mask into data/masked/senado/, raw deleted;
                                             #   log results/senado/prepare.jsonl (same code as twohands.run)

Draw: seed 20261019, n = 100, eligibility = PROTOCOL.md 2.1 with TIPO_ACTA "3" plus the special-station rule
(TIPO_CASILLA "S" carries an MR and an RP acta under one CLAVE_CASILLA) and the layout rule (only the 19 states whose
acta prints all 18 section-6 rows; the schema's source.exclude_states, re-derived here from the CSV), strata state x capture type, proportional
allocation by largest remainder, within-stratum shuffle random.Random("20261019:<stratum>"), the same replacement rule
(no image URL in the Senate district file -> next in the stratum order). Excluded: every polling station already
used in a presidential sample (the 300 run, the 43 pilot actas, the 150 calibration actas, the confirmation 100, the
Colima whole-state staging) and the 20 Senate pilot pages that built the rectification assets.
"""
import collections
import hashlib
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, run, sample, schema  # noqa: E402

SEED, N = 20261019, 100
FORM = "mx_senado_2024"
S = schema.load(FORM)
SRC = schema.source(S)
OUT = REPO / "results" / "manifest_senado100.json"
PILOT = REPO / SRC["results_dir"] / "pilot.json"
OFFICIAL = REPO / "app" / "data" / "official_senado.json"
PREP_LOG = REPO / SRC["results_dir"] / "prepare.jsonl"


def presidency_used() -> dict[str, set]:
    """Every CLAVE_CASILLA used in a presidential sample, by source."""
    R = REPO / "results"
    man = lambda p: {i["clave"] for i in json.loads((R / p).read_text(encoding="utf-8"))["items"]}  # noqa: E731
    return {
        "run300 (results/manifest.json)": man("manifest.json"),
        "confirm100 (results/manifest_confirm100.json)": man("manifest_confirm100.json"),
        "calibration150 (results/calibration_manifest.json)": man("calibration_manifest.json"),
        "pilot43 (spikes/tally-witness/data/sample.json)": {x["clave"] for x in json.loads(sample.SPIKE_SAMPLE.read_text())},
        "colima staging (results/prepare_state06.jsonl)": {r["clave"] for r in run.jsonl(R / "prepare_state06.jsonl")},
    }


VOTE_COLS = [f["csv"] for f in S["fields"] if f.get("vote")]


def variant_states(rows: list[dict]) -> set[int]:
    """States whose Senate acta prints fewer section-6 rows: some vote column is empty (not a number) on more than
    half of the state's Acta PREP rows (in the 2024 data: on all of them; the other states have it on < 5%)."""
    n, empty = collections.Counter(), collections.Counter()
    for r in rows:
        if r["TIPO_ACTA"].strip() != SRC["tipo_acta"] or r["TIPO_DOCUMENTO"].strip() != "Acta PREP":
            continue
        e = int(r["ID_ENTIDAD"])
        n[e] += 1
        for c in VOTE_COLS:
            empty[(e, c)] += not (r.get(c) or "").strip().isdigit()
    return {e for e in n if any(empty[(e, c)] > n[e] / 2 for c in VOTE_COLS)}


def draw() -> None:
    used = presidency_used()
    pilot = {p["clave"] for p in json.loads(PILOT.read_text(encoding="utf-8"))["pages"]}
    exclude = set().union(*used.values()) | pilot
    rows = sample.load_rows(REPO / SRC["prep_csv"])
    variants = variant_states(rows)
    assert variants == set(SRC["exclude_states"]), (sorted(variants), SRC["exclude_states"])
    el, why = sample.eligible(rows, exclude, tipo=SRC["tipo_acta"], special_rule=SRC.get("special_rule", False),
                              exclude_reason="polling station already used (presidential samples or Senate pilot)",
                              exclude_states=variants,
                              states_reason="state prints another section-6 layout (a coalition not registered there)")
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
            urls = sample.district_urls(ent, dist, SRC["district_url"], REPO / SRC["district_cache"])
            k = r["CLAVE_CASILLA"]
            if k not in urls:
                excluded.append({"clave": k, "stratum": h, "reason": "no image URL in the PREP district file (replaced)"})
                continue
            items.append({"clave": k, "stratum": h, "entidad": r["ENTIDAD"], "id_entidad": ent, "distrito": dist,
                          "layout": sample.capture(r["DIGITALIZACION"]), "url": urls[k][0], "url_tipo": urls[k][1]})
            took += 1
    csv_path = REPO / SRC["prep_csv"]
    doc = {"protocol": SRC["protocol"], "schema": FORM, "schema_sha256": schema.sha256(FORM), "seed": SEED, "n": N,
           "states_excluded_layout": sorted(variants),
           "source": sample.PREP_ZIP_URL + " (inner SEN zip, SEN_2024.csv)",
           "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
           "excludes": {**{k: len(v) for k, v in used.items()}, "senate pilot (results/senado/pilot.json)": len(pilot),
                        "union": len(exclude)},
           "population": {"csv_rows": len(rows), "eligible": len(el), "excluded_by_rule": dict(why)},
           "strata": {h: {"size": len(strata[h]), "n": alloc[h]} for h in sorted(strata)},
           "items": items, "excluded_after_draw": excluded}
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    lay = collections.Counter(i["layout"] for i in items)
    print(len(items), "items", dict(lay), ";", len(excluded), "replaced; sha256",
          hashlib.sha256(OUT.read_bytes()).hexdigest())


def num(v):
    v = (v or "").strip().replace(",", "").strip("'")
    return int(v) if v.isdigit() else None


def official() -> None:
    """PREP's capture of each drawn Senate acta, in the app's official.json format (prep values by schema key)."""
    man = json.loads(OUT.read_text(encoding="utf-8"))
    want = {i["clave"]: i for i in man["items"]}
    out = {}
    for r in sample.load_rows(REPO / SRC["prep_csv"]):
        k = r["CLAVE_CASILLA"]
        if k not in want or r["TIPO_ACTA"].strip() != SRC["tipo_acta"]:
            continue
        d = (r.get("DIGITALIZACION") or "").strip()
        out[k] = {"schema": FORM,
                  "prep": {f["key"]: num(r.get(f["csv"])) for f in S["fields"] if f.get("csv")},
                  "prep_raw": {f["key"]: (r.get(f["csv"]) or "").strip() for f in S["fields"] if f.get("csv")},
                  "cert": {}, "cert_mode": None, "dig": "M" if d.startswith("M") else ("E" if d.startswith("E") else None),
                  "entidad": r.get("ENTIDAD"), "stratum": want[k]["stratum"], "adjudicated": {},
                  "source": "PREP 2024 SEN_2024.csv (20240603_2005_PREP.zip)"}
    assert set(out) == set(want), set(want) - set(out)
    OFFICIAL.write_text(json.dumps(dict(sorted(out.items())), ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"official Senate values for {len(out)} forms -> {OFFICIAL.relative_to(REPO).as_posix()}")


def prepare() -> None:
    man = json.loads(OUT.read_text(encoding="utf-8"))
    masked = REPO / SRC["masked_dir"]
    done = {r["clave"] for r in run.jsonl(PREP_LOG) if r.get("status") in ("ok", "not_located", "unreadable")}
    todo = [it for it in man["items"] if it["clave"] not in done]
    PREP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(lambda it: run.prepare_one(it, S, masked), todo):
            r["ts"] = run.now()
            run.append(PREP_LOG, r)
            print(r["clave"], r["status"], r.get("reason", ""))
    rows = {r["clave"]: r for r in run.jsonl(PREP_LOG)}
    st = collections.Counter(rows[i["clave"]]["status"] for i in man["items"] if i["clave"] in rows)
    print(dict(st))


if __name__ == "__main__":
    {"draw": draw, "official": official, "prepare": prepare}[sys.argv[1]]()
