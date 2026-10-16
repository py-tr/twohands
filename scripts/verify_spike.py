"""Re-verify reading after the privacy changes (rectify + mask + tiles pulled in to the mask edge) on spike forms.
    python scripts/verify_spike.py gemma 211294C0100,141097C0100,...
Writes data/masked/spike/<clave>.jpg (masked only) and results/verify_spike_<model>.jsonl.
Inputs are in-repo (data/pilot/tally-witness: sample, PREP rows, adjudicated fields). The unmasked page is fetched from
its public PREP URL (sample.json) into cache/spike_img/ (gitignored) and only its masked version is kept in data/."""
import json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import PILOT_DATA, REPO, mask, reader, register
from twohands.gate import gate
from twohands.sample import UA
model, claves = sys.argv[1], sys.argv[2].split(",")
sample = {x["clave"]: x for x in json.loads((PILOT_DATA / "sample.json").read_text())}
P = {k: v["prep"] for k, v in json.loads((PILOT_DATA / "truth_rows.json").read_text(encoding="utf-8")).items()}
ADJ = json.loads((PILOT_DATA / "adjudicate.json").read_text())
IMG = REPO / "cache" / "spike_img"
def num(v):
    v = (v or "").strip().replace(",", "")
    return int(v) if v.isdigit() else None
def original(k):
    p = IMG / f"{k}.jpg"
    if not p.is_file():
        p.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(urllib.request.Request(sample[k]["url"], headers=UA), timeout=60) as r:
            p.write_bytes(r.read())
    return p
CSV = {f["key"]: f["csv"] for f in reader.schemamod.load()["fields"]}
out = REPO / "results" / f"verify_spike_{model}.jsonl"; out.parent.mkdir(exist_ok=True)
def one(k):
    x = sample[k]; kind = "movil" if x["dig"] == "M" else "escaner"
    dst = REPO / "data" / "masked" / "spike" / f"{k}.jpg"
    try:
        page, info = mask.prepare(original(k), kind); mask.save(page, dst)
    except register.NotLocated as e:
        return {"clave": k, "not_located": str(e)}
    row = reader.read(model, dst)
    g = gate(row["parsed"])
    truth = {f: ADJ.get(k, {}).get(f, num(P[k][c])) for f, c in CSV.items() if c}
    wrong = {f: (g.values.get(f), t) for f, t in truth.items() if g.values.get(f) != t}
    res = {"clave": k, "dig": x["dig"], "image": dst.relative_to(REPO).as_posix(), "info": info, "accepted": g.accepted,
           "reasons": g.reasons, "labels": g.labels, "values": g.values, "words": g.words, "wrong_vs_adjudicated": wrong,
           "finish_reason": row.get("finish_reason"), "usage": row.get("usage"), "secs": row["secs"], "error": row.get("error"),
           "content": row["content"]}
    print(k, x["dig"], "ACCEPT" if g.accepted else "route", len(truth) - len(wrong), "/", len(truth), wrong, g.reasons[:4],
          row.get("finish_reason"), (row.get("usage") or {}).get("completion_tokens"), row["secs"], flush=True)
    return res
with ThreadPoolExecutor(2) as ex, open(out, "a", encoding="utf-8") as fh:
    for r in ex.map(one, claves):
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
