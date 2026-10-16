"""PROTOCOL_IEEBCS section 5: score the head-to-head from the committed raw files. No model call.

    python scripts/ieebcs_score.py                 # score -> results/ieebcs/score.json + the numbers block of
                                                   #   results/ieebcs_head_to_head.md
    python scripts/ieebcs_score.py --crops         # + a crop of the MASKED page for every field to adjudicate
                                                   #   (results/ieebcs/adjudication/, ledger adjudication.jsonl)
    python scripts/ieebcs_score.py --check         # make eval: recompute and compare with what is committed;
                                                   #   exit 1 on any mismatch (before the run: the empty template)
    [--model gemma|qwen]

Field set (the count and vote boxes; no identification field): per acta, every field of its schema (variant) with a
PREP column. Per field, the published value is one of: a number (in the denominator), '-' (no such line on that
acta's printed form: not a field), or anything else ('sin dato', 'ilegible', blank: excluded from the denominator and
counted). Special-station actas (no schema covers their layout) keep the fields of their election's base schema, and
every numeric one counts as unmatched.
(a) raw per-field match = fields whose digit reading equals the published value / all numeric fields on all 300
    actas. Pages not located, not covered, failed or unparseable calls and null readings are unmatched.
    Second (never first): the same over the fields of the pages the locator accepted.
(b) the gate: accepted forms / 300; on accepted forms, fields whose reading differs from the published value; the
    adjudicated verdicts (results/ieebcs/adjudication/verdicts.json; AI adjudicator, labelled) and the person's
    spot-check (spotcheck.json) when present.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, schema  # noqa: E402
from twohands.run import jsonl  # noqa: E402

MAN = REPO / "results" / "manifest_ieebcs300.json"
RES = REPO / "results" / "ieebcs"
MD = REPO / "results" / "ieebcs_head_to_head.md"
ADJ = RES / "adjudication"
BEGIN, END = "<!-- BEGIN NUMBERS (scripts/ieebcs_score.py) -->", "<!-- END NUMBERS -->"
THEIRS = {"fields": 23077, "matched": 14501, "pct": 62.84, "source": "IEEBCS, Informe final del PREP PELO 2023-2024, p. 19"}


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(100 * (c - h), 2), round(100 * (c + h), 2)]


def pct(k, n):
    return round(100 * k / n, 2) if n else None


def score(model: str = "gemma") -> dict | None:
    calls_path = RES / f"calls_{model}.jsonl"
    if not calls_path.is_file():
        return None
    man = json.loads(MAN.read_text(encoding="utf-8"))
    off = json.loads((RES / "official.json").read_text(encoding="utf-8"))
    prep = {r["clave"]: r for r in jsonl(RES / "prepare.jsonl")}
    calls = {r["clave"]: r for r in jsonl(calls_path) if not r.get("error")}
    calls.update({r["clave"]: r for r in jsonl(calls_path) if r.get("error") and r["clave"] not in calls})
    verdicts = json.loads((ADJ / "verdicts.json").read_text(encoding="utf-8")) if (ADJ / "verdicts.json").is_file() else {}
    tot = collections.Counter()
    by_type = collections.defaultdict(collections.Counter)
    per_acta_fields = collections.defaultdict(list)
    excluded_nonnum = collections.Counter()
    accepted_errors, disagreements = [], []
    for it in man["items"]:
        k = it["clave"]
        o = off[k]
        s = schema.load(it["schema"])
        rec = calls.get(k) or {}
        read_ok = bool(rec) and not rec.get("no_call") and not rec.get("error") and rec.get("parsed_ok")
        acc = bool(rec.get("accepted"))
        t = it["election"]
        by_type[t]["actas"] += 1
        tot["actas"] += 1
        tot["accepted"] += acc
        by_type[t]["accepted"] += acc
        tot["read_pages"] += read_ok
        located = (prep.get(k) or {}).get("status") == "ok"
        tot["located"] += located
        nf = 0
        for f in s["fields"]:
            if not f.get("csv"):
                continue
            raw = (o["prep_raw"].get(f["key"]) or "").strip()
            if raw == "-":
                continue
            ref = o["prep"].get(f["key"])
            if ref is None:
                excluded_nonnum[raw or "(blank)"] += 1
                continue
            nf += 1
            got = ((rec.get("fields") or {}).get(f["key"]) or {}).get("n") if read_ok else None
            m = got is not None and got == ref
            for c in (tot, by_type[t]):
                c["fields"] += 1
                c["matched"] += m
                if located:
                    c["fields_read"] += 1
                    c["matched_read"] += m
                if acc:
                    c["acc_fields"] += 1
                    c["acc_err"] += not m
            if read_ok and not m:
                d = {"clave": k, "field": f["key"], "public": f["public"]["name"], "model": got, "published": ref,
                     "accepted": acc, "schema": it["schema"]}
                v = verdicts.get(f"{k}__{f['key']}")
                if v:
                    d["verdict"] = v.get("verdict") if isinstance(v, dict) else v
                disagreements.append(d)
                if acc:
                    accepted_errors.append(d)
        per_acta_fields[(t, it["schema"])].append(nf)
    vc = collections.Counter(d.get("verdict") or "unadjudicated" for d in accepted_errors)
    vall = collections.Counter(d.get("verdict") or "unadjudicated" for d in disagreements)
    out = {
        "model": model, "n_actas": tot["actas"], "theirs": THEIRS,
        "a_raw": {"matched": tot["matched"], "fields": tot["fields"], "pct": pct(tot["matched"], tot["fields"]),
                  "wilson95": wilson(tot["matched"], tot["fields"]),
                  "second_fields_of_located_pages": {"matched": tot["matched_read"], "fields": tot["fields_read"],
                                                     "pct": pct(tot["matched_read"], tot["fields_read"])},
                  "pages_read": tot["read_pages"],
                  "pages_located": tot["located"]},
        "by_type": {t: {"actas": c["actas"], "matched": c["matched"], "fields": c["fields"],
                        "pct": pct(c["matched"], c["fields"]), "accepted": c["accepted"]} for t, c in sorted(by_type.items())},
        "fields_per_acta": {f"{t} | {sc}": {"actas": len(v), "fields_min": min(v), "fields_max": max(v),
                                             "fields_mean": round(sum(v) / len(v), 2)}
                            for (t, sc), v in sorted(per_acta_fields.items())},
        "excluded_non_numeric_published": dict(excluded_nonnum),
        "b_gate": {"accepted": tot["accepted"], "of": tot["actas"], "accept_pct": pct(tot["accepted"], tot["actas"]),
                   "accepted_fields": tot["acc_fields"], "accepted_fields_differing_from_published": tot["acc_err"],
                   "verdicts_on_accepted_differences": dict(vc),
                   "published_value_not_the_paper (verdict model_right, all actas)": vall.get("model_right", 0),
                   "verdicts_all_disagreements": dict(vall)},
        "adjudicator": "AI reviewer (an AI model) from crops of the masked page; a person spot-checks (spotcheck.json)",
    }
    return out


def render(sc: dict | None) -> str:
    if sc is None:
        return "Empty until the run (PROTOCOL_IEEBCS.md). No acta of the sample has been read by a model."
    a, b = sc["a_raw"], sc["b_gate"]
    lines = [
        f"**(a) Raw per-field match ({sc['model']}): {a['pct']}%** = {a['matched']:,} of {a['fields']:,} numeric fields "
        f"on all {sc['n_actas']} actas (Wilson 95% {a['wilson95'][0]}-{a['wilson95'][1]}%). Theirs: "
        f"{THEIRS['matched']:,} of {THEIRS['fields']:,}, {THEIRS['pct']}% ({THEIRS['source']}).",
        f"Second: {a['second_fields_of_located_pages']['pct']}% of the {a['second_fields_of_located_pages']['fields']:,} "
        f"fields on the {a['pages_located']} of {sc['n_actas']} pages the locator accepted ({a['pages_read']} read and parsed).",
        "",
        "| type | actas | fields | matched | % | accepted forms |", "|---|---|---|---|---|---|",
        *[f"| {t} | {v['actas']} | {v['fields']:,} | {v['matched']:,} | {v['pct']} | {v['accepted']} |"
          for t, v in sc["by_type"].items()],
        "",
        "| type and layout | actas | numeric fields per acta (min / mean / max) |", "|---|---|---|",
        *[f"| {k} | {v['actas']} | {v['fields_min']} / {v['fields_mean']} / {v['fields_max']} |"
          for k, v in sc["fields_per_acta"].items()],
        "",
        f"Excluded from the denominator (published value not a number): "
        f"{sum(sc['excluded_non_numeric_published'].values())} fields "
        f"({', '.join(f'{k}: {v}' for k, v in sorted(sc['excluded_non_numeric_published'].items())) or 'none'}).",
        "",
        f"**(b) After the gate:** {b['accepted']} of {b['of']} forms accepted ({b['accept_pct']}%); on them, "
        f"{b['accepted_fields_differing_from_published']} of {b['accepted_fields']:,} fields differ from the published "
        f"value (verdicts: {json.dumps(b['verdicts_on_accepted_differences'])}). Fields where the published value does not "
        f"match the paper (verdict model_right, all actas): {b['published_value_not_the_paper (verdict model_right, all actas)']}. "
        f"Adjudicator: {sc['adjudicator']}.",
    ]
    return "\n".join(lines)


def write_md(text: str) -> None:
    md = MD.read_text(encoding="utf-8")
    i, j = md.index(BEGIN) + len(BEGIN), md.index(END)
    MD.write_text(md[:i] + "\n" + text + "\n" + md[j:], encoding="utf-8")


def crops(model: str) -> int:
    from PIL import Image, ImageDraw
    man = {i["clave"]: i for i in json.loads(MAN.read_text(encoding="utf-8"))["items"]}
    sc = score(model)
    calls = {r["clave"]: r for r in jsonl(RES / f"calls_{model}.jsonl") if not r.get("error")}
    off = json.loads((RES / "official.json").read_text(encoding="utf-8"))
    ADJ.mkdir(parents=True, exist_ok=True)
    ledger = ADJ / "adjudication.jsonl"
    old = {(r["clave"], r["field"]) for r in jsonl(ledger)}
    n = 0
    for k, rec in sorted(calls.items()):
        if rec.get("no_call") or not rec.get("parsed_ok"):
            continue
        s = schema.load(man[k]["schema"])
        page = REPO / rec["image"]
        for f in s["fields"]:
            ref = off[k]["prep"].get(f["key"]) if f.get("csv") else None
            got = (rec["fields"].get(f["key"]) or {}).get("n")
            raw = (off[k]["prep_raw"].get(f["key"]) or "").strip() if f.get("csv") else "-"
            if raw == "-" or (ref is not None and got == ref) or (k, f["key"]) in old:
                continue
            im = Image.open(page).convert("RGB")
            W, H = im.size
            x0 = min(f["box"][0], f["words_box"][0]) - 0.04
            y0, y1 = f["box"][1] - 0.02, f["box"][3] + 0.02
            c = im.crop((int(max(0, x0) * W), int(max(0, y0) * H), int(0.66 * W), int(min(1, y1) * H)))
            ImageDraw.Draw(c).rectangle([0, int(0.02 * H), c.size[0] - 1, c.size[1] - int(0.02 * H)],
                                        outline=(255, 0, 160), width=2)
            name = f"{k}__{f['public']['code']}.jpg"
            c.save(ADJ / name, "JPEG", quality=90)
            with open(ledger, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"clave": k, "field": f["key"], "public": f["public"]["name"], "model": got,
                                     "model_words": (rec["fields"].get(f["key"]) or {}).get("w"), "published": ref,
                                     "published_raw": raw, "accepted": rec["accepted"], "crop": name, "verdict": "",
                                     "verdicts_allowed": "model_right | capture_right | neither | paper_ambiguous | "
                                                         "unreadable | crop_wrong"}, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} new crops -> {ADJ.relative_to(REPO).as_posix()}; score: {sc and sc['a_raw']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemma")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--crops", action="store_true")
    a = ap.parse_args(argv)
    sc = score(a.model)
    text = render(sc)
    if a.check:
        md = MD.read_text(encoding="utf-8")
        shown = md[md.index(BEGIN) + len(BEGIN): md.index(END)].strip()
        mism = int(shown != text.strip())
        if sc is not None:
            committed = json.loads((RES / "score.json").read_text(encoding="utf-8")) if (RES / "score.json").is_file() else None
            mism += int(committed != sc)
        print(f"IEEBCS head-to-head: {'no run yet (template)' if sc is None else sc['a_raw']['pct']}; mismatches: {mism}")
        return 1 if mism else 0
    if sc is not None:
        (RES / "score.json").write_text(json.dumps(sc, indent=1, ensure_ascii=False), encoding="utf-8")
    write_md(text)
    if a.crops:
        return crops(a.model)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
