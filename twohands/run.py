"""Resumable runner for the pre-registered run (PROTOCOL.md).

    python -m twohands.run [--models gemma,qwen] [--max-daily-usd 0.80]
    python -m twohands.run --schema mx_senado_2024 --manifest results/manifest_senado100.json --models gemma
        (another form type: PROTOCOL_SENADO.md; writes only the schema's source.results_dir, masks into its
        source.masked_dir; refuses unless that protocol is committed; add --mock --limit 3 for an offline dry run)
    python -m twohands.run --schema mx_bcs_dl_2024,mx_bcs_ayto_2024 --manifest results/manifest_ieebcs300.json --models gemma
        (a manifest over several form types: each item names its schema, ``name@variant`` for a printed row variant;
        an item with "covered": false is never downloaded or read; PROTOCOL_IEEBCS.md)

1. prepare: download each manifest acta to data/raw/img/ (gitignored), rectify + mask it into
   data/masked/<clave>.jpg, delete the raw file. Outcome per acta in results/prepare.jsonl.
2. read: Gemma over every prepared acta to completion, then Qwen. One row per form in
   results/calls_<model>.jsonl (stable record; see ``record``). Rows with an error are retried on resume.

Budget: the shared ``twohands.ratelimit`` limiter (TWOHANDS_RPM=16 req/min total, 4 of them reserved for live reads, so 12 for runs; 2 in flight; bulk share $0.30 a day, twohands/budgets.py); 429 honours
Retry-After. GET /usage is read before the run and every 4 calls: if daily_cost_used_usd >= --max-daily-usd
the runner sleeps until daily_reset_at (16:00 UTC) + 3 min and continues. Status: results/run_status.json.
The API key is never printed or written.
"""
from __future__ import annotations

import argparse
import json
import os
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from twohands import REPO, amd, mask, reader, register, schema
from twohands.gate import gate

RESULTS = REPO / "results"
MASKED = REPO / "data" / "masked"
RAW = REPO / "data" / "raw" / "img"
LOG = RESULTS / "run.log"
_loglock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{now()} {msg}"
    with _loglock:
        print(line, flush=True)
        Path(LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def jsonl(path: Path) -> list[dict]:
    out = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # half-written last line of a killed run
    return out


def append(path: Path, row: dict, lock=threading.Lock()) -> None:
    with lock:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def rel(p: Path) -> str:
    return Path(os.path.relpath(p, REPO)).as_posix()


# ---------------------------------------------------------------- prepare
def prepare_one(it: dict, s: dict | None = None, masked_dir: Path | None = None) -> dict:
    """Download, locate + mask (schema ``s``; default the presidential acta) into ``masked_dir``, delete the raw."""
    k = it["clave"]
    if it.get("covered") is False:  # a printed layout no schema covers (PROTOCOL_IEEBCS 3.3): routed, never read
        return {"clave": k, "status": "not_covered", "reason": "printed layout not covered by the schemas"}
    dst = (masked_dir or MASKED) / f"{k}.jpg"
    if dst.exists():
        return {"clave": k, "status": "ok", "image": rel(dst), "cached": True}
    RAW.mkdir(parents=True, exist_ok=True)
    raw = RAW / f"{k}.jpg"
    err = None
    for i in range(3):
        try:
            req = urllib.request.Request(it["url"], headers={"User-Agent": "Mozilla/5.0 (two-hands research)"})
            raw.write_bytes(urllib.request.urlopen(req, timeout=90).read())
            err = None
            break
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(5 * (i + 1))
    if err:
        return {"clave": k, "status": "download_failed", "reason": err}
    try:
        page, info = mask.prepare(raw, it["layout"], s)
        mask.save(page, dst)
        return {"clave": k, "status": "ok", "image": rel(dst), "info": info}
    except register.NotLocated as e:
        return {"clave": k, "status": "not_located", "reason": str(e)}
    except Exception as e:  # noqa: BLE001 - unreadable file etc.
        return {"clave": k, "status": "unreadable", "reason": f"{type(e).__name__}: {str(e)[:120]}"}
    finally:
        for _ in range(5):  # raw (unmasked) images are never kept
            try:
                raw.unlink(missing_ok=True)
                break
            except OSError:
                time.sleep(1)
        if raw.exists():
            log(f"WARNING raw image could not be deleted: {rel(raw)}")


def prepare_all(items: list[dict], s: dict | None = None, out_dir: Path | None = None,
                masked_dir: Path | None = None) -> dict:
    path = (out_dir or RESULTS) / "prepare.jsonl"
    done = {r["clave"]: r for r in jsonl(path) if r.get("status") in ("ok", "not_located", "unreadable", "not_covered")}
    todo = [it for it in items if it["clave"] not in done]
    log(f"prepare: {len(done)} done, {len(todo)} to fetch")
    with ThreadPoolExecutor(int(os.environ.get("TWOHANDS_WORKERS", "2"))) as ex:
        for r in ex.map(lambda it: prepare_one(it, item_schema(it, s), masked_dir), todo):
            r["ts"] = now()
            append(path, r)
            if r["status"] != "ok":
                log(f"prepare {r['clave']}: {r['status']} {r.get('reason', '')}")
            if r["status"] in ("ok", "not_located", "unreadable", "not_covered"):
                done[r["clave"]] = r
    return done


# ---------------------------------------------------------------- read
def record(it: dict, prep: dict, model_key: str, s: dict, row: dict | None) -> dict:
    """The stable per-form record (one per acta per model)."""
    base = {"form_id": it["clave"], "clave": it["clave"], "layout": it["layout"], "stratum": it["stratum"],
            "schema": s["form"], "model": reader.MODELS[model_key], "model_key": model_key,
            "prompt_sha256": reader.prompt_sha256(s), "image": prep.get("image"), "ts": now()}
    if row is None:  # never sent: the page was not located / not readable / not downloadable
        reason = {"not_located": "form not located", "unreadable": "image unreadable",
                  "download_failed": "image not downloadable", "not_covered": "layout not covered"}.get(prep.get("status"), prep.get("status"))
        return base | {"no_call": True, "accepted": False, "routed": True,
                       "route_reasons": [f"{reason}: {prep.get('reason', '')}"], "route_codes": ["no_read"],
                       "fields": {}, "identities": [], "failing_fields": [], "latency_s": None, "cost_usd": 0.0}
    g = gate(row.get("parsed"), s)
    fields = {f["key"]: {"label": g.labels.get(f["key"]), "n": g.values.get(f["key"]), "w": g.words.get(f["key"]),
                         "fix": f["key"] in g.fixes} for f in s["fields"]}
    u = row.get("usage") or {}
    reasons, codes, acc = list(g.reasons), set(g.codes), g.accepted
    if row.get("finish_reason") == "length":  # PROTOCOL 2.3: a truncated reply is never accepted
        reasons.insert(0, "reply truncated (finish_reason=length)"); codes.add("no_read"); acc = False
    if row.get("error"):
        reasons.insert(0, f"model call failed: {row['error'][:120]}"); codes.add("no_read"); acc = False
    return base | {"no_call": False, "accepted": acc, "routed": not acc, "route_reasons": reasons,
                   "route_codes": sorted(codes), "fields": fields, "identities": g.identities,
                   "failing_fields": g.failing_fields, "latency_s": row.get("secs"),
                   "cost_usd": u.get("cost"), "usage": u, "finish_reason": row.get("finish_reason"),
                   "attempts": row.get("attempts"), "error": row.get("error"), "parsed_ok": row.get("parsed") is not None,
                   "content": row.get("content")}


class Budget:
    def __init__(self, cap: float):
        self.cap, self.lock, self.n, self.used = cap, threading.Lock(), 0, None

    def check(self, force: bool = False) -> None:
        with self.lock:
            self.n += 1
            if not force and self.n % 4:
                return
            while True:
                try:
                    u = amd.usage()
                except Exception as e:  # noqa: BLE001
                    log(f"usage read failed: {type(e).__name__}")
                    return
                self.used = float(u.get("daily_cost_used_usd") or 0)
                if self.used < self.cap:
                    return
                reset = datetime.fromisoformat(str(u.get("daily_reset_at")).replace("Z", "+00:00"))
                wait = max(60.0, (reset - datetime.now(timezone.utc)).total_seconds() + 180)
                log(f"daily spend {self.used:.3f} >= {self.cap} USD: sleeping {wait / 3600:.1f} h until after reset {u.get('daily_reset_at')}")
                time.sleep(wait)


def read_model(model_key: str, items: list[dict], prepared: dict, s: dict, budget: Budget,
               out_dir: Path | None = None, chat=None) -> None:
    out_dir = out_dir or RESULTS
    path = out_dir / f"calls_{model_key}.jsonl"
    for attempt_pass in range(12):  # API errors are retried in later passes (outages on the shared endpoint)
        have = {r["clave"] for r in jsonl(path) if not r.get("error")}
        todo = [it for it in items if it["clave"] not in have and it["clave"] in prepared]
        if not todo:
            break
        log(f"{model_key}: pass {attempt_pass + 1}, {len(have)} done, {len(todo)} to read")
        t0 = time.time()
        counter = {"n": 0}

        def work(it):
            s_it = item_schema(it, s)
            prep = prepared[it["clave"]]
            if prep.get("status") != "ok":
                rec = record(it, prep, model_key, s_it, None)
            else:
                budget.check()
                _CUR.clave = it["clave"]
                row = reader.read(model_key, REPO / prep["image"], s_it, chat=chat)
                rec = record(it, prep, model_key, s_it, row)
            append(path, rec)
            counter["n"] += 1
            el = time.time() - t0
            eta = el / counter["n"] * (len(todo) - counter["n"]) / 3600
            log(f"{model_key} {it['clave']} {'ACCEPT' if rec['accepted'] else 'route'} "
                f"{rec.get('finish_reason')} {rec.get('latency_s')}s err={bool(rec.get('error'))} "
                f"[{counter['n']}/{len(todo)}, eta {eta:.1f} h] {'; '.join(rec['route_reasons'][:2])[:140]}")
            status(model_key, path, len(items), budget, out_dir)
            if rec.get("error") and chat is None:
                time.sleep(300)  # endpoint outage / 5xx storm: back off this worker for 5 min

        with ThreadPoolExecutor(int(os.environ.get("TWOHANDS_WORKERS", "2"))) as ex:
            list(ex.map(work, todo))


def status(model_key: str, path: Path, n: int, budget: Budget, out_dir: Path | None = None) -> None:
    rows = [r for r in jsonl(path) if not r.get("error")]
    st = {"ts": now(), "model": model_key, "done": len(rows), "n": n,
          "accepted": sum(r["accepted"] for r in rows), "daily_cost_used_usd": budget.used,
          "cost_usd_this_model": round(sum((r.get("cost_usd") or 0) for r in rows), 6)}
    ((out_dir or RESULTS) / "run_status.json").write_text(json.dumps(st, indent=1), encoding="utf-8")


def amendment2_committed() -> bool:
    """True only if the committed PROTOCOL.md (HEAD) contains 'Amendment 2' and the working copy is unchanged."""
    import subprocess
    try:
        head = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:PROTOCOL.md"], capture_output=True, check=True).stdout
        dirty = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "HEAD", "--", "PROTOCOL.md"]).returncode != 0
    except Exception:  # noqa: BLE001
        return False
    return b"Amendment 2" in head and not dirty


def committed_clean(relpath: str) -> bool:
    """True only if ``relpath`` is committed at HEAD and the working copy of it is unchanged."""
    import subprocess
    try:
        subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{relpath}"], capture_output=True, check=True)
        dirty = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "HEAD", "--", relpath]).returncode != 0
    except Exception:  # noqa: BLE001
        return False
    return not dirty


def item_schema(it: dict, s: dict) -> dict:
    """The schema of one manifest item: its own ``schema`` (``name@variant``) when it names one, else the run's."""
    return schema.load(it["schema"]) if it.get("schema") else s


_CUR = threading.local()  # the form being read (the dry-run mock answers per form)


def mock_chat(s0, official: dict | None = None):
    """Offline stand-in for ``amd.chat`` (dry runs only): replies with the official PREP values of the form being read,
    words = digits, the labels the schema expects, section 5 = votaron + representantes. No network, key or cost."""
    def chat(body):
        off = official.get(getattr(_CUR, "clave", None)) or {}
        vals = off.get("prep") or {}
        s = schema.load(off["schema"]) if off.get("schema") else (s0 or schema.load())
        items = []
        for f in s["fields"]:
            n = vals.get(f["key"])
            if f["key"] == "PERSONAS_Y_REP" and None not in (vals.get("VOTARON"), vals.get("REPRESENTANTES")):
                n = vals["VOTARON"] + vals["REPRESENTANTES"]
            lab = f["label"]
            label = "+".join(lab["parties"]) if "parties" in lab else (f.get("where") or " ".join(lab["keywords"]))
            items.append({"label": label.split(" ", 2)[-1] if label.startswith("section ") else label, "n": n, "w": n})
        return {"choices": [{"message": {"content": json.dumps({"values": items})}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0}}, 1
    return chat


def main(argv=None) -> int:
    global LOG
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="gemma,qwen")
    ap.add_argument("--max-daily-usd", type=float, default=0.80)
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--schema", default=schema.DEFAULT, help="form type (schemas/<name>.yaml)")
    ap.add_argument("--manifest", default=None, help="default: results/manifest.json (the pre-registered 300)")
    ap.add_argument("--out", default=None, help="results dir; default: the schema's source.results_dir "
                                                 "(out/dryrun_<form>/ with --mock)")
    ap.add_argument("--limit", type=int, default=None, help="first N manifest items only (dry runs)")
    ap.add_argument("--mock", action="store_true",
                    help="dry run: an offline fake client that echoes the official values (no network, no model)")
    a = ap.parse_args(argv)
    forms = [x.strip() for x in a.schema.split(",") if x.strip()]
    s = schema.load(forms[0])
    src = schema.source(s)
    default_form = s["form"] == schema.DEFAULT
    if a.out:
        out_dir = Path(a.out)
    else:
        out_dir = REPO / "out" / f"dryrun_{s['form']}" if a.mock else REPO / src["results_dir"]
    out_dir = out_dir if out_dir.is_absolute() else REPO / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    masked_dir = REPO / src["masked_dir"]
    if out_dir.resolve() != RESULTS.resolve():
        LOG = out_dir / "run.log"
    man_path = Path(a.manifest) if a.manifest else RESULTS / "manifest.json"
    man_path = man_path if man_path.is_absolute() else REPO / man_path
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man_forms = man.get("schema", schema.DEFAULT)
    man_forms = sorted(man_forms) if isinstance(man_forms, list) else [man_forms]
    if man_forms != sorted(forms) or any(it.get("schema", forms[0]).split("@")[0] not in forms for it in man["items"]):
        log(f"REFUSING: the manifest is for {', '.join(man_forms)}, not {', '.join(forms)}")
        return 3
    items = man["items"][: a.limit] if a.limit else man["items"]
    log(f"run start: {len(items)} actas, schema {s['form']}, models {a.models}, prompt {reader.prompt_sha256(s)[:12]}, "
        f"out {rel(out_dir)}, pid {os.getpid()}{' (MOCK client, no model)' if a.mock else ''}")
    prepared = prepare_all(items, s, out_dir, masked_dir)
    # download failures are retried once more, then recorded as routed (never replaced)
    if any(it["clave"] not in prepared for it in items):
        prepared = prepare_all(items, s, out_dir, masked_dir)
        for r in jsonl(out_dir / "prepare.jsonl"):
            prepared.setdefault(r["clave"], r)
    if a.prepare_only:
        return 0
    chat = None
    budget = Budget(a.max_daily_usd)
    if a.mock:
        off = {}
        offs = sorted((REPO / "app" / "data").glob("official*.json"))
        offs += [REPO / src["official"]] if src.get("official") else []
        for p in offs:
            try:
                off.update(json.loads(p.read_text(encoding="utf-8")))
            except ValueError:
                pass
        chat = mock_chat(s, off)
        budget.check = lambda force=False: None  # no /usage call in a dry run
    else:
        budget.check(force=True)
    for m in a.models.split(","):
        m = m.strip()
        if not default_form:
            if m not in src.get("readers", ["gemma"]):
                log(f"REFUSING the {m} pass: {src['protocol']} pre-registers {', '.join(src.get('readers', ['gemma']))} only")
                return 3
            if not a.mock and not committed_clean(src["protocol"]):
                log(f"REFUSING: {src['protocol']} is not committed (or has uncommitted changes)")
                return 3
        elif m == "qwen" and not amendment2_committed():
            log("REFUSING the qwen pass: PROTOCOL.md 'Amendment 2' is not committed")
            return 3
        read_model(m, items, prepared, s, budget, out_dir, chat=chat)
    log("run complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
