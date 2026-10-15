"""Gemma-4-31B-IT vs Qwen3.8-27B on the same pre-registered 300 forms, recomputed from the raw calls files.

    python scripts/gemma_vs_qwen.py      # writes app/data/gemma_vs_qwen.json (the app reads it) and results/gemma_vs_qwen.md

Read-only inputs, no model call, no network: results/manifest.json, results/calls_gemma.jsonl,
results/calls_qwen.jsonl (the Qwen pass may still be running; the comparison is then on the forms both models have
been sent, and says how many), results/adjudication/verdicts.json, results/adjudication/recall_judged.json,
app/data/audit_sample_prep300.csv (the official two-person capture, PREP 2024).

Both models get the same masked page + 6 tiles, the same frozen prompt (sha256 checked on every row) and the same
frozen gate. Last row per form counts (resumed runs append).

Accepted-field accuracy: on the forms the gate accepted, each graded field is judged against the paper when we have
a reading of the paper for it (adjudication verdict, else the recall judging), otherwise against the official
capture. A field where the model differs from the capture and nobody has looked at the paper yet is counted as
"not adjudicated", never as right.
"""
from __future__ import annotations

import collections
import csv
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from twohands import reader, schema as schemamod  # noqa: E402

R = REPO / "results"
ADJ = R / "adjudication"
UNDECIDED = {"paper_ambiguous", "unreadable", "crop_wrong"}
N_IMAGES = 7  # page + 6 tiles (PROTOCOL.md section 4)


def num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    return int(v) if v.isdigit() else None


def last_rows(path: Path) -> tuple[dict, list]:
    last, every = {}, []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue  # half-written last line of a running pass
            last[r["clave"]] = r
            every.append(r)
    return last, every


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def paper_value(k: str, f: str, V: dict, J: dict):
    """(known, value, undecided) for the paper at form k field f, if anyone has read the paper for it."""
    v = V.get(f"{k}__{f}")
    if v:
        if v.get("verdict") in UNDECIDED:
            return True, None, True
        p = v.get("paper")
        return True, (None if p == "blank" else p), False
    j = J.get(f"{k}__{f}")
    if j and j.get("paper") is not None:
        p = j["paper"]
        return True, (None if p == "blank" else p), False
    return False, None, False


def model_block(name: str, last: dict, every: list, C: list, s: dict, prep: dict, V: dict, J: dict, prompt: str):
    # published files name no party (tests/test_headline.py): a vote row is reported by its position
    graded = [dict(f, row=i + 1) for i, f in enumerate(f for f in s["fields"] if f.get("vote")) if f.get("csv")]
    graded = [f for f in s["fields"] if f.get("csv") and not f.get("vote")] + graded
    rows = {k: last[k] for k in C}
    sent = [k for k, r in rows.items() if not r.get("no_call")]
    parsed = [k for k in sent if rows[k].get("parsed_ok")]
    touchless = [k for k in parsed if rows[k].get("accepted")]
    fr = collections.Counter(str(rows[k].get("finish_reason")) for k in sent)

    n = right = wrong = undecided = unadj = 0
    wrong_list = []
    for k in touchless:
        F = rows[k].get("fields") or {}
        for f in graded:
            m = (F.get(f["key"]) or {}).get("n")
            n += 1
            known, paper, und = paper_value(k, f["key"], V, J)
            if known and und:
                undecided += 1
            elif known:
                if m == paper:
                    right += 1
                else:
                    wrong += 1
                    wrong_list.append(f"{k}__{f['key']}" if not f.get("vote") else f"{k}__vote_row_{f['row']}")
            elif m == num(prep[k][f["csv"]]):
                right += 1
            else:
                unadj += 1

    # digits and words both read, and equal: the two independent readings on every parsed form
    both = agree = 0
    for k in parsed:
        for fv in (rows[k].get("fields") or {}).values():
            if fv.get("n") is not None and fv.get("w") is not None:
                both += 1
                agree += fv["n"] == fv["w"]

    U = [rows[k].get("usage") or {} for k in parsed]
    img = [(u.get("prompt_tokens_details") or {}).get("image_tokens") for u in U]
    img = [x for x in img if x]
    comp = [u.get("completion_tokens") for u in U if u.get("completion_tokens")]
    cset = set(C)
    spend_all = sum((r.get("cost_usd") or 0) for r in every if r["clave"] in cset)
    return {
        "model": next((r.get("model") for r in rows.values() if r.get("model")), name),
        "forms": len(C), "sent": len(sent), "parsed": len(parsed),
        "finish_reason": dict(sorted(fr.items())),
        "prompt_sha256_all_frozen": all(rows[k].get("prompt_sha256") == prompt for k in sent),
        "touchless": len(touchless), "touchless_pct": round(100 * len(touchless) / len(C), 1) if C else None,
        "accepted_fields": n, "accepted_right": right, "accepted_wrong": wrong, "accepted_undecided": undecided,
        "accepted_not_adjudicated": unadj, "accepted_wrong_fields": wrong_list,
        "accepted_right_pct_of_judged": round(100 * right / (right + wrong), 2) if right + wrong else None,
        "words_and_digits_both_read": both, "words_equal_digits": agree,
        "mean_latency_s": round(mean([rows[k].get("latency_s") for k in parsed]), 1) if parsed else None,
        "mean_tokens_in": round(mean([u.get("prompt_tokens") for u in U])) if U else None,
        "mean_tokens_out": round(mean(comp)) if comp else None,
        "max_tokens_out": max(comp) if comp else None,
        "max_tokens_cap": reader.MAX_TOKENS.get(name),
        "image_tokens_per_request": {"min": min(img), "max": max(img), "mean": round(mean(img))} if img else None,
        "image_tokens_per_image_mean": round(mean(img) / N_IMAGES) if img else None,
        "cost_per_read_usd": mean([rows[k].get("cost_usd") for k in parsed]),
        "cost_per_form_all_attempts_usd": spend_all / len(C) if C else None,
        "spend_usd": round(spend_all, 6),
    }


def compute() -> dict:
    s = schemamod.load()
    man = json.loads((R / "manifest.json").read_text(encoding="utf-8"))
    claves = [it["clave"] for it in man["items"]]
    G, Gall = last_rows(R / "calls_gemma.jsonl")
    Q, Qall = last_rows(R / "calls_qwen.jsonl")
    with (REPO / "app" / "data" / "audit_sample_prep300.csv").open(encoding="utf-8", newline="") as fh:
        prep = {r["CLAVE_CASILLA"]: r for r in csv.DictReader(fh)}
    V = json.loads((ADJ / "verdicts.json").read_text(encoding="utf-8"))
    J = json.loads((ADJ / "recall_judged.json").read_text(encoding="utf-8")) if (ADJ / "recall_judged.json").is_file() else {}
    prompt = reader.prompt_sha256(s)
    # same forms for both: in the pre-registered sample, a row in both calls files, and in the official capture
    C = [k for k in claves if k in G and k in Q and k in prep]
    if not C:
        return {"sample": len(claves), "common_forms": 0, "qwen_complete": False, "prompt_sha256": prompt}
    g = model_block("gemma", G, Gall, C, s, prep, V, J, prompt)
    q = model_block("qwen", Q, Qall, C, s, prep, V, J, prompt)
    ratio = (g["cost_per_read_usd"] / q["cost_per_read_usd"]) if g["cost_per_read_usd"] and q["cost_per_read_usd"] else None
    return {"sample": len(claves), "common_forms": len(C), "qwen_complete": len(C) == len(claves),
            "prompt_sha256": prompt, "gemma": g, "qwen": q,
            "gemma_cost_share_of_qwen": round(ratio, 3) if ratio else None,
            "gemma_full_300": model_block("gemma", G, Gall, [k for k in claves if k in G and k in prep],
                                          s, prep, V, J, prompt)}


def usd(x, d=6):
    return "n/a" if x is None else f"${x:.{d}f}"


def line(d: dict) -> str:
    g, q = d["gemma"], d["qwen"]
    return (f"On the same {d['common_forms']} forms: Gemma accepted {g['touchless']} touchless "
            f"({g['accepted_wrong']} of {g['accepted_fields']} accepted fields wrong), Qwen {q['touchless']} "
            f"({q['accepted_wrong']} of {q['accepted_fields']} wrong, {q['accepted_not_adjudicated']} not yet adjudicated); "
            f"Gemma {usd(g['cost_per_read_usd'])} per form vs Qwen {usd(q['cost_per_read_usd'])} "
            f"(about 1/{round(1 / d['gemma_cost_share_of_qwen'])}), {g['mean_latency_s']:.0f} s vs {q['mean_latency_s']:.0f} s.")


def markdown(d: dict) -> str:
    g, q = d["gemma"], d["qwen"]
    status = ("complete: all 300 read by both" if d["qwen_complete"] else
              f"the Qwen pass is still running; compared on the {d['common_forms']} of {d['sample']} forms both models have been sent")
    rows = [
        ("Forms compared (same forms for both)", d["common_forms"], d["common_forms"]),
        ("Sent / parsed", f"{g['sent']} / {g['parsed']}", f"{q['sent']} / {q['parsed']}"),
        ("finish_reason (last read per form)", ", ".join(f"{k} {v}" for k, v in g["finish_reason"].items()),
         ", ".join(f"{k} {v}" for k, v in q["finish_reason"].items())),
        ("Touchless (frozen gate accepted)", f"{g['touchless']} ({g['touchless_pct']}%)", f"{q['touchless']} ({q['touchless_pct']}%)"),
        ("Accepted fields", g["accepted_fields"], q["accepted_fields"]),
        ("Accepted fields wrong (vs the paper)", g["accepted_wrong"], q["accepted_wrong"]),
        ("Accepted fields undecided on the paper", g["accepted_undecided"], q["accepted_undecided"]),
        ("Accepted fields not yet adjudicated", g["accepted_not_adjudicated"], q["accepted_not_adjudicated"]),
        ("Mean latency per form", f"{g['mean_latency_s']} s", f"{q['mean_latency_s']} s"),
        ("Tokens in / out (mean)", f"{g['mean_tokens_in']:,} / {g['mean_tokens_out']:,}", f"{q['mean_tokens_in']:,} / {q['mean_tokens_out']:,}"),
        ("Image tokens per request (7 images)", f"{g['image_tokens_per_request']['min']:,}-{g['image_tokens_per_request']['max']:,}",
         f"{q['image_tokens_per_request']['min']:,}-{q['image_tokens_per_request']['max']:,}"),
        ("Max completion tokens / cap", f"{g['max_tokens_out']} / {g['max_tokens_cap']}", f"{q['max_tokens_out']} / {q['max_tokens_cap']}"),
        ("Cost per form read", usd(g["cost_per_read_usd"]), usd(q["cost_per_read_usd"])),
        ("Spend per form compared, all attempts incl. failed", usd(g["cost_per_form_all_attempts_usd"]), usd(q["cost_per_form_all_attempts_usd"])),
    ]
    out = ["# Gemma vs Qwen on the same pre-registered forms", "",
           "Generated by `python scripts/gemma_vs_qwen.py` (also run by `make eval`). No model call. Inputs: "
           "`results/calls_gemma.jsonl`, `results/calls_qwen.jsonl` (last row per form), `results/adjudication/`, "
           "`app/data/audit_sample_prep300.csv`.", "",
           f"Status: {status}. Same masked page + 6 tiles, same frozen prompt (sha256 `{d['prompt_sha256'][:12]}...`, "
           f"on every row: Gemma {g['prompt_sha256_all_frozen']}, Qwen {q['prompt_sha256_all_frozen']}), same frozen gate. "
           "Both on AMD Token Factory.", "",
           f"**{line(d)}**", "",
           "| | Gemma-4-31B-IT | Qwen3.8-27B |", "|---|---|---|"]
    out += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    out += ["", "Accepted fields are judged against the paper where an adjudication verdict or the recall judging read it, "
            "otherwise against the official two-person capture. The adjudication was done on Gemma's disagreements, so a "
            "Qwen-only disagreement on an accepted form is listed as not yet adjudicated, not counted as right.", ""]
    if q["accepted_wrong_fields"] or g["accepted_wrong_fields"]:
        out += [f"Wrong accepted fields: Gemma {', '.join(g['accepted_wrong_fields']) or 'none'}; "
                f"Qwen {', '.join(q['accepted_wrong_fields']) or 'none'}.", ""]
    return "\n".join(out)


def main() -> int:
    d = compute()
    if not d["common_forms"]:
        print("no form read by both models yet; nothing written")
        return 0
    (REPO / "app" / "data" / "gemma_vs_qwen.json").write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    (R / "gemma_vs_qwen.md").write_text(markdown(d), encoding="utf-8")
    print(line(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
