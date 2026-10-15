"""Concurrency sweep against the self-hosted endpoint (vLLM on one MI300X): what one GPU does for the buyer.

    TWOHANDS_BASE_URL=http://127.0.0.1:8000/v1 TWOHANDS_KEY=... TWOHANDS_MODEL_GEMMA=google/gemma-4-31B-it \\
      python bench/bench_mi300x.py --price-per-hour 1.99 [--levels 1,2,4,8,16] [--ssh root@IP | --local-smi]

Input: a FIXED set of masked pilot pages (data/masked/spike/*.jpg, sorted; never a confirmation or run page),
the PRODUCTION request (``twohands.reader.build_body``: the frozen prompt, the masked page + 6 tiles, temperature 0,
max_tokens 2000, prompt sha256 recorded). Bodies are built before the clock starts, so client-side JPEG/base64
work is not timed. Each level sends max(--min-requests, 2 x level) requests (pages cycled) with exactly `level`
in flight; one untimed warm-up request first. No retries: an HTTP error or timeout counts as an error.

Per level: mean and p95 seconds per form, forms per minute (successful replies / wall time), aggregate prefill and
decode tokens per second (sum of usage.prompt_tokens / completion_tokens over the level's wall time), errors,
finish_reason counts, parse rate, and (if sampled) GPU utilisation / VRAM from rocm-smi every 2 s, either on this
machine (--local-smi) or over SSH (--ssh user@host).

Writes results/bench_mi300x_<ts>.json and results/bench_mi300x_<ts>.md (the table in the buyer's units:
seconds per form single stream; forms/min at 8 and 16; cost per 1,000 forms at --price-per-hour; "a state count of
20,927 forms in H hours for $X"; tokens/s). The key is read from the env and never printed or written.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from twohands import reader, schema  # noqa: E402

PAGES = REPO / "data" / "masked" / "spike"
STATE_FORMS = 20927   # Estado de Mexico, presidential casilla actas in the PREP 2024 CSV (the largest state)
SMI_CMD = ["rocm-smi", "--showuse", "--showmemuse", "--showmeminfo", "vram", "--json"]


# ---------------------------------------------------------------- endpoint
def cfg(env=None) -> tuple[str, str, str]:
    env = os.environ if env is None else env
    base, key = env.get("TWOHANDS_BASE_URL"), env.get("TWOHANDS_KEY")
    if not base or not key:
        raise SystemExit("set TWOHANDS_BASE_URL and TWOHANDS_KEY (the self-hosted endpoint); this bench never "
                         "runs against the Token Factory")
    return base.rstrip("/"), key, env.get("TWOHANDS_MODEL_GEMMA") or "google/gemma-4-31B-it"


def post(base: str, key: str, body: bytes, timeout: float) -> dict:
    req = urllib.request.Request(base + "/chat/completions", data=body, method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def one(base: str, key: str, body: bytes, timeout: float) -> dict:
    t = time.perf_counter()
    try:
        r = post(base, key, body, timeout)
        ch = (r.get("choices") or [{}])[0]
        content = (ch.get("message") or {}).get("content") or ""
        u = r.get("usage") or {}
        return {"ok": True, "secs": time.perf_counter() - t, "finish": ch.get("finish_reason"),
                "prompt_tokens": u.get("prompt_tokens") or 0, "completion_tokens": u.get("completion_tokens") or 0,
                "parsed": reader.parse(content) is not None}
    except urllib.error.HTTPError as e:
        return {"ok": False, "secs": time.perf_counter() - t, "error": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001 - timeouts, resets
        return {"ok": False, "secs": time.perf_counter() - t, "error": type(e).__name__}


# ---------------------------------------------------------------- GPU sampling
def _num(x):
    m = re.search(r"-?\d+(\.\d+)?", str(x))
    return float(m.group()) if m else None


def parse_smi(text: str) -> dict:
    """rocm-smi --json -> {util_pct, vram_pct, vram_used_gb} (first card; keys differ across versions)."""
    try:
        d = json.loads(text)
    except ValueError:
        return {}
    cards = [v for k, v in d.items() if k.lower().startswith("card") and isinstance(v, dict)]
    if not cards:
        return {}
    c, out = cards[0], {}
    for k, v in c.items():
        kl = k.lower()
        if "gpu use" in kl:
            out["util_pct"] = _num(v)
        elif "vram%" in kl or "memory allocated" in kl or "gpu memory use" in kl:
            out["vram_pct"] = _num(v)
        elif "vram total used memory" in kl:
            n = _num(v)
            out["vram_used_gb"] = round(n / 1e9, 1) if n is not None else None
    return out


class SmiSampler:
    def __init__(self, ssh: str | None = None, local: bool = False, every: float = 2.0, runner=None):
        self.cmd = (["ssh", "-o", "BatchMode=yes", ssh] + SMI_CMD) if ssh else (SMI_CMD if local else None)
        self.every, self.samples, self._stop = every, [], threading.Event()
        self.runner = runner or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout)
        self._t = None

    @property
    def enabled(self) -> bool:
        return self.cmd is not None

    def _loop(self):
        while not self._stop.is_set():
            try:
                s = parse_smi(self.runner(self.cmd))
                if s:
                    self.samples.append(s)
            except Exception:  # noqa: BLE001 - sampling must never break the bench
                pass
            self._stop.wait(self.every)

    def start(self):
        self.samples = []
        if self.enabled:
            self._stop.clear()
            self._t = threading.Thread(target=self._loop, daemon=True)
            self._t.start()

    def stop(self) -> dict:
        if not self._t:
            return {}
        self._stop.set()
        self._t.join(timeout=25)
        self._t = None
        out = {"samples": len(self.samples)}
        for k in ("util_pct", "vram_pct", "vram_used_gb"):
            v = [s[k] for s in self.samples if s.get(k) is not None]
            if v:
                out[k + "_mean"] = round(statistics.mean(v), 1)
                out[k + "_max"] = max(v)
        return out


# ---------------------------------------------------------------- sweep
def p95(xs: list[float]) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(0.95 * len(xs)) - 1)]


def level_stats(level: int, rows: list[dict], wall: float, gpu: dict) -> dict:
    ok = [r for r in rows if r["ok"]]
    lat = [r["secs"] for r in ok]
    fin: dict = {}
    for r in ok:
        fin[r["finish"]] = fin.get(r["finish"], 0) + 1
    pt, ct = sum(r["prompt_tokens"] for r in ok), sum(r["completion_tokens"] for r in ok)
    errs: dict = {}
    for r in rows:
        if not r["ok"]:
            errs[r["error"]] = errs.get(r["error"], 0) + 1
    return {"concurrency": level, "requests": len(rows), "ok": len(ok), "errors": len(rows) - len(ok),
            "error_kinds": errs, "wall_s": round(wall, 2),
            "mean_s_per_form": round(statistics.mean(lat), 2) if lat else None,
            "p95_s_per_form": round(p95(lat), 2) if lat else None,
            "forms_per_min": round(len(ok) / wall * 60, 2) if wall > 0 else None,
            "prefill_tok_s": round(pt / wall, 1) if wall > 0 else None,
            "decode_tok_s": round(ct / wall, 1) if wall > 0 else None,
            "mean_prompt_tokens": round(pt / len(ok)) if ok else None,
            "mean_completion_tokens": round(ct / len(ok)) if ok else None,
            "finish_reason": fin, "parsed": sum(r["parsed"] for r in ok), "gpu": gpu}


def run_level(level: int, bodies: list[bytes], n: int, base: str, key: str, timeout: float, smi: SmiSampler,
              send=one) -> dict:
    work = [bodies[i % len(bodies)] for i in range(n)]
    smi.start()
    t = time.perf_counter()
    with ThreadPoolExecutor(level) as ex:
        rows = list(ex.map(lambda b: send(base, key, b, timeout), work))
    wall = time.perf_counter() - t
    return level_stats(level, rows, wall, smi.stop())


# ---------------------------------------------------------------- buyer's units
def fmt(x, nd=1):
    return "n/a" if x is None else f"{x:,.{nd}f}"


def buyer(levels: list[dict], price: float, state_forms: int = STATE_FORMS) -> dict:
    by = {L["concurrency"]: L for L in levels}
    good = [L for L in levels if L["forms_per_min"] and L["errors"] == 0] or [L for L in levels if L["forms_per_min"]]
    best = max(good, key=lambda L: L["forms_per_min"]) if good else None

    def per1000(L):
        return None if not L or not L["forms_per_min"] else price / (L["forms_per_min"] * 60) * 1000

    out = {"price_per_hour_usd": price, "single_stream_s_per_form": (by.get(1) or {}).get("mean_s_per_form"),
           "forms_per_min_at_8": (by.get(8) or {}).get("forms_per_min"),
           "forms_per_min_at_16": (by.get(16) or {}).get("forms_per_min"),
           "best_concurrency": best["concurrency"] if best else None,
           "best_forms_per_min": best["forms_per_min"] if best else None,
           "usd_per_1000_forms_best": None, "state_forms": state_forms, "state_hours": None, "state_usd": None}
    if best:
        out["usd_per_1000_forms_best"] = round(per1000(best), 3)
        h = state_forms / (best["forms_per_min"] * 60)
        out["state_hours"], out["state_usd"] = round(h, 2), round(h * price, 2)
    for c in (8, 16):
        v = per1000(by.get(c))
        out[f"usd_per_1000_forms_at_{c}"] = None if v is None else round(v, 3)
    return out


def markdown(res: dict) -> str:
    B, m = res["buyer"], res["meta"]
    L = [f"# MI300X throughput: {m['model']} (vLLM, 1x MI300X)", "",
         f"{m['ts']} · {m['pages']} masked pilot pages · production prompt `{m['prompt_sha256'][:12]}` · "
         f"temperature 0 · max_tokens {m['max_tokens']} · price ${B['price_per_hour_usd']}/h", "",
         "| In flight | Forms | Errors | Mean s/form | p95 s/form | Forms/min | $ per 1,000 forms | Prefill tok/s "
         "| Decode tok/s | GPU util % (mean/max) | VRAM (max) |",
         "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for r in res["levels"]:
        g = r.get("gpu") or {}
        per = (B["price_per_hour_usd"] / (r["forms_per_min"] * 60) * 1000) if r["forms_per_min"] else None
        util = f"{fmt(g.get('util_pct_mean'), 0)}/{fmt(g.get('util_pct_max'), 0)}" if g.get("samples") else "not sampled"
        vram = (f"{fmt(g.get('vram_used_gb_max'))} GB" if g.get("vram_used_gb_max") is not None
                else (f"{fmt(g.get('vram_pct_max'), 0)}%" if g.get("vram_pct_max") is not None else "not sampled"))
        L.append(f"| {r['concurrency']} | {r['ok']}/{r['requests']} | {r['errors']} | {fmt(r['mean_s_per_form'])} | "
                 f"{fmt(r['p95_s_per_form'])} | {fmt(r['forms_per_min'])} | {fmt(per, 2)} | {fmt(r['prefill_tok_s'], 0)} "
                 f"| {fmt(r['decode_tok_s'], 0)} | {util} | {vram} |")
    L += ["", "**In the buyer's units**", "",
          f"- Seconds per form, single stream: **{fmt(B['single_stream_s_per_form'])} s**",
          f"- Forms per minute at 8 in flight: **{fmt(B['forms_per_min_at_8'])}**; at 16: **{fmt(B['forms_per_min_at_16'])}**",
          f"- Cost per 1,000 forms at ${B['price_per_hour_usd']}/h: **${fmt(B['usd_per_1000_forms_best'], 2)}** "
          f"(at {B['best_concurrency']} in flight; at 8: ${fmt(B.get('usd_per_1000_forms_at_8'), 2)}, "
          f"at 16: ${fmt(B.get('usd_per_1000_forms_at_16'), 2)})",
          f"- A state count of {B['state_forms']:,} forms in **{fmt(B['state_hours'])} hours for ${fmt(B['state_usd'], 2)}** "
          f"(one MI300X at {B['best_concurrency']} in flight)", "",
          "Tokens/s are aggregate over each level's wall time (sum of usage tokens / wall seconds), so prefill and "
          "decode overlap. Wall time includes the client-to-server network path"
          f" ({m['client']}). Errors are not retried.", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--price-per-hour", type=float, required=True, help="USD per GPU-hour of the droplet")
    ap.add_argument("--levels", default="1,2,4,8,16")
    ap.add_argument("--pages", type=int, default=16, help="first N sorted masked pilot pages")
    ap.add_argument("--min-requests", type=int, default=16)
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--state-forms", type=int, default=STATE_FORMS)
    ap.add_argument("--ssh", help="user@host: sample rocm-smi over SSH (key auth, BatchMode)")
    ap.add_argument("--local-smi", action="store_true", help="sample rocm-smi on this machine")
    ap.add_argument("--out-dir", default=str(REPO / "results"))
    ap.add_argument("--client", default="", help="where the client ran (for the table note), e.g. 'on the droplet'")
    a = ap.parse_args(argv)

    base, key, model = cfg()
    reader.MODELS["gemma"] = model
    s = schema.load()
    pages = sorted(PAGES.glob("*.jpg"))[: a.pages]
    if not pages:
        raise SystemExit(f"no masked pilot pages in {PAGES}")
    from PIL import Image
    bodies = []
    for p in pages:
        with Image.open(p) as im:
            bodies.append(json.dumps(reader.build_body("gemma", im.copy(), s)).encode())
    smi = SmiSampler(ssh=a.ssh, local=a.local_smi or (not a.ssh and shutil.which("rocm-smi") is not None))
    print(f"{len(pages)} pages, model {model}, GPU sampling: {'on' if smi.enabled else 'off'}", flush=True)
    warm = one(base, key, bodies[0], a.timeout)
    print(f"warm-up: {'ok' if warm['ok'] else warm.get('error')} {warm['secs']:.1f}s", flush=True)

    levels = []
    for c in [int(x) for x in a.levels.split(",") if x.strip()]:
        n = max(a.min_requests, 2 * c)
        r = run_level(c, bodies, n, base, key, a.timeout, smi)
        levels.append(r)
        print(f"c={c:>2}  ok {r['ok']}/{r['requests']}  mean {fmt(r['mean_s_per_form'])}s  p95 {fmt(r['p95_s_per_form'])}s  "
              f"{fmt(r['forms_per_min'])} forms/min  prefill {fmt(r['prefill_tok_s'], 0)} tok/s  "
              f"decode {fmt(r['decode_tok_s'], 0)} tok/s  gpu {r['gpu']}", flush=True)

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    res = {"meta": {"ts": ts, "model": model, "pages": len(pages), "page_ids": [p.stem for p in pages],
                    "prompt_sha256": reader.prompt_sha256(s), "max_tokens": reader.MAX_TOKENS["gemma"],
                    "temperature": 0, "client": a.client or "client location not given",
                    "endpoint_host": re.sub(r"^https?://", "", base).split("/")[0], "warmup": warm},
           "levels": levels, "buyer": buyer(levels, a.price_per_hour, a.state_forms)}
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"bench_mi300x_{ts}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    md = markdown(res)
    (out / f"bench_mi300x_{ts}.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
