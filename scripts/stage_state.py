"""Stage one whole state for the MI300X throughput stretch goal: every presidential casilla acta of the state is
downloaded from INE's public PREP image URL, located + masked with the Amendment 1 locator (``twohands.mask``, via
``twohands.run.prepare_one``), and the raw file deleted. NO model call.

    python scripts/stage_state.py --smallest            # the state with the fewest TIPO_ACTA == 2 rows (Colima)
    python scripts/stage_state.py --ent 6 --workers 4

Population: PREP CSV rows with TIPO_ACTA == "2" in the state. A row whose clave has no image URL in the PREP
district file, or whose DIGITALIZACION is not Movil/Escaner, is logged ("no_image") and not fetched.
Outputs: data/masked/state<NN>/<clave>.jpg (gitignored: large), results/prepare_state<NN>.jsonl (one row per acta,
resumable), results/stage_state<NN>.json (counts + disk size). Raw images only ever sit in data/raw/img/ (gitignored)
and are deleted right after masking, as in the core's prepare step.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from twohands import REPO, run  # noqa: E402
from twohands.sample import capture, district_urls, load_rows  # noqa: E402

TERMINAL = ("ok", "not_located", "unreadable", "no_image")


def state_rows(rows: list[dict]) -> dict[int, list[dict]]:
    by = collections.defaultdict(list)
    for r in rows:
        if r["TIPO_ACTA"].strip() == "2":
            by[int(r["ID_ENTIDAD"])].append(r)
    return by


def smallest(by: dict[int, list[dict]]) -> int:
    return min(by, key=lambda e: (len(by[e]), e))


def items_for(ent: int, rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """(items to fetch, rows logged as no_image)."""
    items, skipped, seen = [], [], set()
    urls: dict = {}
    for d in sorted({int(r["ID_DISTRITO_FEDERAL"]) for r in rows}):
        urls.update(district_urls(ent, d))
    for r in sorted(rows, key=lambda r: r["CLAVE_CASILLA"]):
        k = r["CLAVE_CASILLA"]
        if k in seen:
            continue
        seen.add(k)
        lay = capture(r["DIGITALIZACION"])
        if k not in urls or lay is None:
            skipped.append({"clave": k, "status": "no_image",
                            "reason": "no image URL in the PREP district file" if k not in urls
                            else f"DIGITALIZACION={r['DIGITALIZACION'].strip() or '-'}"})
            continue
        items.append({"clave": k, "layout": lay, "url": urls[k][0], "stratum": f"{ent:02d}|{lay}"})
    return items, skipped


def dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.glob("*.jpg")) if p.is_dir() else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ent", type=int)
    g.add_argument("--smallest", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="fetch at most N (testing)")
    a = ap.parse_args(argv)

    by = state_rows(load_rows())
    ent = smallest(by) if a.smallest else a.ent
    name = by[ent][0]["ENTIDAD"]
    out_dir = REPO / "data" / "masked" / f"state{ent:02d}"
    log_path = REPO / "results" / f"prepare_state{ent:02d}.jsonl"
    run.MASKED = out_dir  # prepare_one writes MASKED/<clave>.jpg; keep the state's pages in their own folder
    out_dir.mkdir(parents=True, exist_ok=True)

    items, skipped = items_for(ent, by[ent])
    done = {r["clave"]: r for r in run.jsonl(log_path) if r.get("status") in TERMINAL}
    for r in skipped:
        if r["clave"] not in done:
            r["ts"] = run.now()
            run.append(log_path, r)
            done[r["clave"]] = r
    todo = [it for it in items if it["clave"] not in done]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{name} (ent {ent}): {len(by[ent])} TIPO_ACTA=2 rows, {len(items)} with an image, "
          f"{len(skipped)} without; {len(todo)} to fetch", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(run.prepare_one, todo), 1):
            r["ts"] = run.now()
            run.append(log_path, r)
            done[r["clave"]] = r
            if i % 50 == 0 or r["status"] != "ok":
                print(f"[{i}/{len(todo)}] {r['clave']} {r['status']} {r.get('reason', '')[:80]}", flush=True)

    rows = {r["clave"]: r for r in run.jsonl(log_path)}  # last row per clave
    c = collections.Counter(r["status"] for r in rows.values())
    raw_left = sorted(p.name for p in run.RAW.glob("*.jpg")) if run.RAW.is_dir() else []
    summary = {"ent": ent, "entidad": name, "tipo_acta_2_rows": len(by[ent]),
               "with_image": len(items), "status": dict(c), "located": c.get("ok", 0),
               "not_located": c.get("not_located", 0), "masked_dir": run.rel(out_dir),
               "masked_files": len(list(out_dir.glob("*.jpg"))), "masked_bytes": dir_size(out_dir),
               "raw_left": len(raw_left), "ts": run.now()}
    (REPO / "results" / f"stage_state{ent:02d}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
