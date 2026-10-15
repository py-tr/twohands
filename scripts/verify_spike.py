"""Re-verify reading after the privacy changes (rectify + mask + tiles pulled in to the mask edge) on spike forms.
    python scripts/verify_spike.py gemma 211294C0100,141097C0100,...
Writes data/masked/spike/<clave>.jpg (masked only) and results/verify_spike_<model>.jsonl."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, mask, reader, register
from twohands.gate import gate
SPIKE = REPO.parent / "spikes" / "tally-witness"
model, claves = sys.argv[1], sys.argv[2].split(",")
sample = {x["clave"]: x for x in json.loads((SPIKE / "data" / "sample.json").read_text())}
sys.path.insert(0, str(SPIKE)); import common  # noqa: E402
P = common.load_prep(); ADJ = json.loads((SPIKE / "adjudicate.json").read_text())
CSV = {f["key"]: f["csv"] for f in reader.schemamod.load()["fields"]}
out = REPO / "results" / f"verify_spike_{model}.jsonl"; out.parent.mkdir(exist_ok=True)
def one(k):
    x = sample[k]; kind = "movil" if x["dig"] == "M" else "escaner"
    dst = REPO / "data" / "masked" / "spike" / f"{k}.jpg"
    try:
        page, info = mask.prepare(SPIKE / "data" / "img" / f"{k}.jpg", kind); mask.save(page, dst)
    except register.NotLocated as e:
        return {"clave": k, "not_located": str(e)}
    row = reader.read(model, dst)
    g = gate(row["parsed"])
    truth = {f: ADJ.get(k, {}).get(f, common.num(P[k][c])) for f, c in CSV.items() if c}
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
