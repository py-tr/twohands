"""PROTOCOL_IEEBCS section 11: the plumbing check, for a person to confirm by eye. No model call.

    python scripts/ieebcs_plumbing.py [--model gemma] [--n 5]

For the first N (5) located actas in manifest order (results/manifest_ieebcs300.json; "located" = status ok in
results/ieebcs/prepare.jsonl), prints our parsed read next to the published CSV row, field by field, and writes the
same tables to results/ieebcs/plumbing_check.md:

    field (public code) | CSV column (position; name for the count rows) | CSV value | value the scorer uses | our read
    (digits / words) | same?

"CSV value" is read from the PREP CSV itself (data/raw/ieebcs/bdatos/..., local, gitignored) when it is on disk, so a
mis-mapped column or a wrong field order in the join shows as a CSV value that differs from the scorer's value or from
the paper; without the CSV the column falls back to results/ieebcs/official.json's prep_raw (said so in the file).
Its only allowed outcome is a fix to the join/mapping code (which CSV column feeds which schema field), recorded in
PROTOCOL_IEEBCS.md with the diff; never a prompt, schema box, tiling or gate change.

Vote rows are shown by their public code (Option NN) and CSV column position only, never by a party name.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from twohands import REPO, schema  # noqa: E402
from twohands.run import jsonl  # noqa: E402

MAN = REPO / "results" / "manifest_ieebcs300.json"
RES = REPO / "results" / "ieebcs"
OUT = RES / "plumbing_check.md"


def csv_rows() -> tuple[dict, dict]:
    """{(CLAVE_ACTA, CODIGO_INTEGRIDAD): row} and {election key: header list} from the local PREP CSVs ({} when absent)."""
    try:
        import ieebcs_draw as D
    except Exception:  # noqa: BLE001
        return {}, {}
    rows, headers = {}, {}
    for e, p in D.CSVS.items():
        if not p.is_file():
            continue
        rs = D.load_rows(p)
        if rs:
            headers[D.SCHEMA[e]] = list(rs[0].keys())
        for r in rs:
            rows[(r["CLAVE_ACTA"].strip(), r["CODIGO_INTEGRIDAD"].strip())] = r
    return rows, headers


def first_located(n: int) -> list[dict]:
    man = json.loads(MAN.read_text(encoding="utf-8"))
    prep = {r["clave"]: r for r in jsonl(RES / "prepare.jsonl")}
    return [it for it in man["items"] if (prep.get(it["clave"]) or {}).get("status") == "ok"][:n]


def build(model: str = "gemma", n: int = 5) -> tuple[str, list[dict]]:
    off = json.loads((RES / "official.json").read_text(encoding="utf-8"))
    calls_path = RES / f"calls_{model}.jsonl"
    calls = {r["clave"]: r for r in jsonl(calls_path) if not r.get("error")} if calls_path.is_file() else {}
    rows, headers = csv_rows()
    items = first_located(n)
    src = "the PREP CSV on disk" if rows else "results/ieebcs/official.json prep_raw (the PREP CSV is not on disk here)"
    md = ["# IEEBCS plumbing check (PROTOCOL_IEEBCS.md section 11)", "",
          f"The first {len(items)} located actas in manifest order; reader `{model}` "
          f"({'results/ieebcs/' + calls_path.name if calls else 'no read yet: run the IEEBCS pass first'}); "
          f"CSV value from {src}.", "",
          "A person confirms, acta by acta and field by field, that each CSV column feeds the schema field next to it "
          "(the CSV value and our read should name the same box on the page). The only allowed outcome is a fix to the "
          "join/mapping code, recorded in PROTOCOL_IEEBCS.md with its diff.", ""]
    out = []
    for it in items:
        k, o = it["clave"], off[it["clave"]]
        s = schema.load(it["schema"])
        votes = set(s.get("vote_keys") or [])
        hdr = headers.get(it["schema"].split("@")[0]) or []
        row = rows.get((it["clave_acta"], it["image_id"]))
        rec = calls.get(k) or {}
        ok_read = bool(rec) and rec.get("parsed_ok") and not rec.get("no_call")
        md += [f"## {k} ({it['schema']}, {it.get('layout')})", "",
               f"Masked page: `data/masked/ieebcs/{k}.jpg` · CSV row: CLAVE_ACTA {it['clave_acta']}, "
               f"CODIGO_INTEGRIDAD {it['image_id'][:12]}... · read: "
               f"{'parsed' if ok_read else ('no call' if rec.get('no_call') else ('not parsed' if rec else 'none yet'))}", "",
               "| field | CSV column | CSV value | scorer uses | our read (digits / words) | same? |",
               "|---|---|---|---|---|---|"]
        for f in s["fields"]:
            if not f.get("csv"):
                continue
            col = f["csv"]
            pos = (hdr.index(col) + 1) if col in hdr else None
            col_txt = (f"#{pos}" if pos else "?") if f["key"] in votes else (f"{col} (#{pos})" if pos else col)
            csv_val = (row.get(col) or "").strip() if row is not None else o["prep_raw"].get(f["key"], "")
            used = o["prep"].get(f["key"])
            got = (rec.get("fields") or {}).get(f["key"]) or {} if ok_read else {}
            dn, dw = got.get("n"), got.get("w")
            same = "" if not ok_read else ("yes" if dn is not None and dn == used else "NO")
            pub = f["public"]
            name = pub["code"] + ("" if f["key"] in votes or pub["name"] == pub["code"] else f" ({pub['name']})")
            md.append(f"| {name} | {col_txt} | {csv_val or '(blank)'} | {'-' if used is None else used} | "
                      f"{'' if not ok_read else (('-' if dn is None else dn) if dw is None else f'{dn} / {dw}')} | {same} |")
            out.append({"clave": k, "field": f["public"]["code"], "csv": csv_val, "used": used, "read": dn, "same": same})
        md += ["", "Confirmed by: ________  (mapping correct: yes / no; if no, which column)", ""]
    return "\n".join(md) + "\n", out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma")
    ap.add_argument("--n", type=int, default=5)
    a = ap.parse_args(argv)
    text, _ = build(a.model, a.n)
    OUT.write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)
    print(f"-> {OUT.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
