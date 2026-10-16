"""Station index for /station: every presidential tally sheet (TIPO_ACTA 2) in the public PREP 2024 CSV, by state and
federal district. Writes app/data/stations.json.gz (no network, no vote values: only the station id, its state and
its district).

    python scripts/build_stations.py
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from twohands import REPO  # noqa: E402
from twohands.sample import PREP_CSV, load_rows  # noqa: E402

OUT = REPO / "app" / "data" / "stations.json.gz"


def build(prep_csv: Path = PREP_CSV) -> dict:
    states: dict[str, dict] = {}
    seen: set[str] = set()
    for r in load_rows(Path(prep_csv)):
        if r["TIPO_ACTA"].strip() != "2":
            continue
        k, d = r["CLAVE_CASILLA"].strip(), r["ID_DISTRITO_FEDERAL"].strip()
        if not d.isdigit() or k in seen:
            continue
        seen.add(k)
        e = str(int(r["ID_ENTIDAD"]))
        st = states.setdefault(e, {"name": r["ENTIDAD"].strip().title(), "d": {}})
        dd = st["d"].setdefault(str(int(d)), {"name": r["DISTRITO_FEDERAL"].strip().title(), "c": []})
        dd["c"].append(k)
    for st in states.values():
        for dd in st["d"].values():
            dd["c"].sort()
    return {"source": "PREP 2024 CSV (PRES_2024.csv), TIPO_ACTA 2, one entry per CLAVE_CASILLA",
            "n": len(seen), "states": dict(sorted(states.items(), key=lambda kv: int(kv[0])))}


def main() -> int:
    idx = build()
    OUT.write_bytes(gzip.compress(json.dumps(idx, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), mtime=0))
    print(f"{idx['n']:,} stations in {len(idx['states'])} states -> {OUT.relative_to(REPO)} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
