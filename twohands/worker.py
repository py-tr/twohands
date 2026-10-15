"""Live audit worker: a standing service that keeps auditing presidential tally sheets (actas) on AMD.

    python -m twohands.worker build-queue          # data/raw PREP + Computos CSVs -> <dir>/queue.json.gz (no network)
    python -m twohands.worker run [--limit N]      # audit forms in queue order until stopped (or N forms read)
    python -m twohands.worker status               # one line: counts, pause state, reader model
    python -m twohands.worker check                # healthcheck: exit 0 when the heartbeat is fresh

What it does, per form, in queue order (smallest state first; inside a state the forms whose certified count was
settled by comparison ("Cotejo") first, then recounts, then the rest; forms already in a measured sample skipped):
  1. fetch the acta image from INE's public PREP URL, politely (>= 1 s between requests to the source, a named
     User-Agent, retries with backoff; HTTP 429/403 pauses the source);
  2. register + mask it IN MEMORY (twohands.mask): the unmasked image is never written anywhere; only the masked page,
     downscaled to <= TWOHANDS_WORKER_PAGE_KB, is stored (and only while under the disk cap);
  3. read the masked page on the AMD Token Factory (twohands.reader, the frozen prompt) with the model available:
     Gemma-4-31B-IT when GET /models lists it, else Qwen3.8-27B; the model id goes on every row and receipt;
  4. gate it (twohands.gate), join the official PREP capture and the certified count (Computos Distritales);
  5. write one result row, its disputes (model != capture) with an automatic label, and a Merkle leaf per dispute.

Labels (vote rows and TOTAL, on forms whose certified count was settled by comparison, not recount):
  certified == model != capture  -> "confirmed by the certified count"
  certified == capture != model  -> "model misread"
  anything else (other fields, recounted forms, no certified value) -> "dispute (unconfirmed)"

Receipts: the Merkle scheme of twohands/merkle.py, one tree per state over its dispute leaves in audit order; the root
of a completed state is final, the open state has a running root.

Budget: GET /usage before every read. The worker sleeps until the daily reset (16:00 UTC) when the key's spend today
reaches TWOHANDS_WORKER_DAILY_USD (0.60), when its remaining budget would drop below TWOHANDS_LIVE_RESERVE_USD (0.20,
kept for the site's live-read button), or when the worker's own spend today reaches the cap. Every model request goes
through the shared cross-process rate limiter (cache/ratelimit.json or TWOHANDS_RATE_FILE), so the worker and the live
reads never exceed the key's pace together.

Robustness: state is derived from the append-only results.jsonl (a half-written last line is ignored) plus atomic
JSON files; a restart resumes at the first form without a row. A watchdog thread exits the process (the container
restarts it) when no progress or heartbeat happens for TWOHANDS_WORKER_STALL_S. Logs rotate (logs/worker.log).

The worker's numbers are NOT part of the pre-registered results: it never writes results/ and twohands.eval never
reads its directory. Nothing here names a party: vote rows are stored by their public code (OPT01 ... OPT15).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import logging
import logging.handlers
import os
import random
import re
import shutil
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from twohands import REPO

# ------------------------------------------------------------------------------------------------ configuration
WORKER_DIR = Path(os.environ.get("TWOHANDS_WORKER_DIR") or REPO / "live_audit")
SEED_DIR = os.environ.get("TWOHANDS_WORKER_SEED") or ""
DAILY_USD = float(os.environ.get("TWOHANDS_WORKER_DAILY_USD", "0.60"))
RESERVE_USD = float(os.environ.get("TWOHANDS_LIVE_RESERVE_USD", "0.20"))
PAGE_KB = int(os.environ.get("TWOHANDS_WORKER_PAGE_KB", "150"))
DISK_CAP_MB = float(os.environ.get("TWOHANDS_WORKER_DISK_MB", "2000"))
FETCH_INTERVAL_S = max(1.0, float(os.environ.get("TWOHANDS_WORKER_FETCH_INTERVAL_S", "1.0")))  # never faster than 1/s
STALL_S = float(os.environ.get("TWOHANDS_WORKER_STALL_S", "1800"))
RESET_HOUR_UTC = 16
USER_AGENT = "two-hands-audit (contact: see README)"
PRIMARY, FALLBACK = "gemma", "qwen"

LABELS = {"confirmed": "confirmed by the certified count", "model_misread": "model misread",
          "unconfirmed": "dispute (unconfirmed)"}
PAUSES = {"source": "Paused: source unavailable",
          "budget": "Paused: daily AMD budget reached; resumes 16:00 UTC",
          "endpoint": "Paused: AMD endpoint unavailable; retrying"}
TERMINAL = ("audited", "no_image", "not_located", "image_unavailable", "unreadable")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(t: Optional[datetime] = None) -> str:
    return (t or utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_reset(now: Optional[datetime] = None) -> datetime:
    """The next 16:00 UTC (the AMD Token Factory's daily budget reset)."""
    now = now or utcnow()
    r = now.replace(hour=RESET_HOUR_UTC, minute=0, second=0, microsecond=0)
    return r if r > now else r + timedelta(days=1)


def budget_day(now: Optional[datetime] = None) -> str:
    """The budget window a moment belongs to (windows run 16:00 UTC to 16:00 UTC), named by its start date."""
    now = now or utcnow()
    return (now - timedelta(hours=RESET_HOUR_UTC)).strftime("%Y-%m-%d")


# ------------------------------------------------------------------------------------------------ files
def write_atomic(path: Path, data: bytes | str) -> None:
    """Temp file + fsync + os.replace: a reader (or a crash) sees the old file or the new one, never half of one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    with open(tmp, "wb") as fh:
        fh.write(data.encode("utf-8") if isinstance(data, str) else data)
        fh.flush()
        os.fsync(fh.fileno())
    for i in range(50):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: a reader holds the file open
            if i == 49:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.02)


def append_jsonl(path: Path, row: dict) -> None:
    """One line per row, flushed and fsynced. A crash mid-write leaves at most one partial last line, which
    ``read_jsonl`` skips; the form then simply has no row and is audited again on resume."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    with open(path, "ab") as fh:
        # a previous crash may have left a partial line without newline: start on a fresh line
        if fh.tell() > 0:
            with open(path, "rb") as rh:
                rh.seek(-1, os.SEEK_END)
                if rh.read(1) != b"\n":
                    fh.write(b"\n")
        fh.write(line.encode("utf-8"))
        fh.flush()
        os.fsync(fh.fileno())


def read_jsonl(path: Path) -> list[dict]:
    out = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                out.append(r)
    return out


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


class Paths:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.queue = self.root / "queue.json.gz"
        self.results = self.root / "results.jsonl"
        self.disputes = self.root / "disputes.jsonl"
        self.roots = self.root / "roots.json"
        self.state = self.root / "state.json"
        self.heartbeat = self.root / "heartbeat.json"
        self.sources = self.root / "sources.json"
        self.pages = self.root / "pages"
        self.crops = self.root / "crops"
        self.urls = self.root / "urls"
        self.logs = self.root / "logs"
        self.lock = self.root / "worker.lock"


# ------------------------------------------------------------------------------------------------ queue
def _int(v) -> Optional[int]:
    v = str(v if v is not None else "").strip().strip("'").replace(",", "")
    return int(v) if v.isdigit() else None


def measured_claves(repo: Path = REPO) -> set[str]:
    """Every form already in one of our measured samples (shown separately on the site): the manifests, the forms with
    official records in the app, and any clave that appears in a committed model-call file."""
    out: set[str] = set()
    res = repo / "results"
    for p in sorted(res.glob("manifest*.json")) + [res / "calibration_manifest.json"]:
        d = read_json(p, {}) or {}
        for it in d.get("items", []) if isinstance(d, dict) else []:
            if isinstance(it, dict) and it.get("clave"):
                out.add(str(it["clave"]))
    for p in (repo / "app" / "data").glob("official*.json"):
        out |= set((read_json(p, {}) or {}).keys())
    for p in list(res.glob("calls_*.jsonl")) + list(res.glob("*/calls_*.jsonl")):
        for r in read_jsonl(p):
            k = r.get("clave") or r.get("form_id")
            if isinstance(k, str):
                out.add(k)
    return out


def cert_mode(obs: Optional[str]) -> Optional[str]:
    """How the certified count settled this form: 'comparison' (Cotejo: the acta's values were compared and kept),
    'recount' (the ballots were counted again), None (no certified row / package not received)."""
    o = (obs or "").strip().lower()
    if o.startswith("cotejo"):
        return "comparison"
    if o.startswith("recuento"):
        return "recount"
    return None


MODE_ORDER = {"comparison": 0, "recount": 1, None: 2}


def order_items(items: list[dict], sizes: dict) -> list[dict]:
    """Smallest state first (by its number of presidential casilla actas); inside a state the forms settled by
    comparison first, then recounts, then forms without a certified row; then by clave."""
    return sorted(items, key=lambda it: (sizes.get(it["ent"], 0), it["ent"], MODE_ORDER.get(it.get("mode"), 3),
                                         it["clave"]))


def build_queue(prep_csv: Optional[Path] = None, comp_csv: Optional[Path] = None,
                measured: Optional[set] = None) -> dict:
    """The whole audit queue from the public PREP and Computos CSVs (no network)."""
    from twohands import schema
    from twohands.adjudicate import COMP_CSV, load_comp
    from twohands.sample import PREP_CSV, capture, load_rows
    from app.store import code_of
    s = schema.load()
    prep_csv, comp_csv = Path(prep_csv or PREP_CSV), Path(comp_csv or COMP_CSV)
    rows = [r for r in load_rows(prep_csv) if r["TIPO_ACTA"].strip() == "2"]
    sizes: dict[int, int] = {}
    names: dict[int, str] = {}
    n_key: dict[str, int] = {}
    for r in rows:
        e = int(r["ID_ENTIDAD"])
        sizes[e] = sizes.get(e, 0) + 1
        names[e] = r["ENTIDAD"].strip()
        n_key[r["CLAVE_CASILLA"]] = n_key.get(r["CLAVE_CASILLA"], 0) + 1
    comp = load_comp({r["CLAVE_CASILLA"] for r in rows}, comp_csv)
    measured = measured_claves() if measured is None else measured
    cert_cols = {"NO_REGISTRADAS": "CANDIDATO/A NO REGISTRADO/A", "NULOS": "VOTOS NULOS",
                 "TOTAL": "TOTAL_VOTOS_CALCULADOS"}
    cap_fields = [f for f in s["fields"] if f.get("csv")]
    cert_keys = s["vote_keys"] + ["TOTAL"]
    items, skipped = [], {}
    for r in rows:
        k, e = r["CLAVE_CASILLA"], int(r["ID_ENTIDAD"])
        lay = capture(r["DIGITALIZACION"])
        if lay is None or n_key[k] > 1 or r["TIPO_DOCUMENTO"].strip() != "Acta PREP":
            continue
        if k in measured:
            skipped[e] = skipped.get(e, 0) + 1
            continue
        c = comp.get(k)
        mode = cert_mode(c.get("OBSERVACIONES") if c else None)
        items.append({"clave": k, "ent": e, "dist": int(r["ID_DISTRITO_FEDERAL"]), "layout": lay, "mode": mode,
                      "cap": [_int(r.get(f["csv"])) for f in cap_fields],
                      "cert": [_int(c.get(cert_cols.get(k2, k2))) for k2 in cert_keys] if c else None})
    items = order_items(items, sizes)
    states = {}
    for it in items:
        st = states.setdefault(str(it["ent"]), {"name": names[it["ent"]].title(), "size": sizes[it["ent"]],
                                                "queue": 0, "measured_skipped": skipped.get(it["ent"], 0)})
        st["queue"] += 1
    return {"built": iso(), "schema": s["form"], "order": "state size asc; comparison, recount, none; clave",
            "cap_fields": [code_of(f["key"]) for f in cap_fields], "cert_fields": [code_of(k) for k in cert_keys],
            "states": states, "items": items}


def save_queue(q: dict, path: Path) -> None:
    write_atomic(path, gzip.compress(json.dumps(q, separators=(",", ":")).encode("utf-8"), mtime=0))


def load_queue(path: Path) -> Optional[dict]:
    try:
        return json.loads(gzip.decompress(Path(path).read_bytes()).decode("utf-8"))
    except (OSError, ValueError, EOFError):
        return None


# ------------------------------------------------------------------------------------------------ polite source
class SourcePaused(Exception):
    def __init__(self, until: float, why: str):
        super().__init__(why)
        self.until, self.why = until, why


class NotFound(Exception):
    pass


def _http_get(url: str, timeout: float = 90) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, b"", dict(e.headers or {})


class Source:
    """INE's public PREP host, fetched politely: one request at a time, >= interval_s between request starts,
    a named User-Agent, retries with exponential backoff on timeouts / 5xx; 429 or 403 pauses the whole source
    (Retry-After when given, else pause_s) and raises SourcePaused. The pause survives restarts (sources.json)."""

    def __init__(self, state_file: Path, get: Callable = _http_get, interval_s: float = FETCH_INTERVAL_S,
                 retries: int = 4, pause_s: float = 1800.0, clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep):
        self.state_file, self.get = Path(state_file), get
        self.interval_s, self.retries, self.pause_s = max(1.0, interval_s), retries, pause_s
        self.clock, self.sleep = clock, sleep
        self._last = 0.0
        self.requests = 0
        st = read_json(self.state_file, {}) or {}
        self.paused_until = float(st.get("paused_until", 0.0))

    def _save(self, why: str = "") -> None:
        write_atomic(self.state_file, json.dumps({"paused_until": self.paused_until, "why": why,
                                                  "requests": self.requests, "ts": iso()}))

    def check(self) -> None:
        if self.clock() < self.paused_until:
            raise SourcePaused(self.paused_until, "source paused")

    def fetch(self, url: str) -> bytes:
        from twohands.ratelimit import parse_retry_after
        self.check()
        last_err = ""
        for attempt in range(1, self.retries + 1):
            wait = self._last + self.interval_s - self.clock()
            if wait > 0:
                self.sleep(wait)
            self._last = self.clock()
            self.requests += 1
            try:
                code, body, headers = self.get(url)
            except Exception as e:  # noqa: BLE001 - timeouts, resets
                code, body, headers, last_err = None, b"", {}, f"{type(e).__name__}"
            if code == 200 and body:
                return body
            if code in (429, 403):
                ra = parse_retry_after((headers or {}).get("Retry-After"))
                self.paused_until = self.clock() + max(ra or 0.0, self.pause_s)
                self._save(f"HTTP {code}")
                raise SourcePaused(self.paused_until, f"HTTP {code}")
            if code in (404, 410):
                raise NotFound(f"HTTP {code}")
            last_err = last_err or f"HTTP {code}"
            self.sleep(min(120.0, 5.0 * 2 ** (attempt - 1)) * (0.75 + 0.5 * random.random()))
        # the source keeps failing (timeouts / 5xx): pause it for a while rather than skipping forms
        self.paused_until = self.clock() + min(self.pause_s, 600.0)
        self._save(last_err)
        raise SourcePaused(self.paused_until, last_err)


def district_map(ent: int, dist: int, src: Source, cache: Path, local: Optional[Path] = None) -> dict:
    """{clave: image url} for one federal district: a local copy of the PREP district file when there is one, else
    one polite fetch of INE's public district file; only the compact clave -> url map is kept."""
    from twohands.sample import DIST_URL, clave_of
    fn = Path(cache) / f"{ent}_{dist}.json"
    m = read_json(fn)
    if isinstance(m, dict):
        return m
    lf = Path(local or REPO / "data" / "raw" / "districts") / f"{ent}_{dist}.json"
    raw = lf.read_bytes() if lf.is_file() else src.fetch(DIST_URL.format(ent=ent, dist=dist))
    J = json.loads(raw.decode("utf-8"))
    out = {}
    for sec, v in J["secciones"]["listaSecciones"].items():
        for key, b in v["listaCasillas"]["body"].items():
            k = clave_of(ent, sec, key)
            if k and b.get("tabla") and str(b["tabla"][0].get("url", "")).startswith("http"):
                out[k] = b["tabla"][0]["url"]
    write_atomic(fn, json.dumps(out, separators=(",", ":")))
    return out


# ------------------------------------------------------------------------------------------------ budget
class BudgetPaused(Exception):
    def __init__(self, until: float, why: str):
        super().__init__(why)
        self.until, self.why = until, why


class Budget:
    """Daily spend guard, checked before every model call."""

    def __init__(self, usage: Callable[[], dict], cap: float = DAILY_USD, reserve: float = RESERVE_USD,
                 own_today: Callable[[], float] = lambda: 0.0, now: Callable[[], datetime] = utcnow):
        self.usage, self.cap, self.reserve, self.own_today, self.now = usage, cap, reserve, own_today, now
        self.last: dict = {}

    def check(self, est: float = 0.01) -> dict:
        now = self.now()
        own = float(self.own_today() or 0.0)
        why = None
        try:
            u = self.usage() or {}
        except Exception:  # noqa: BLE001 - /usage unavailable: fall back to the worker's own spend
            u = {}
        used, rem = u.get("daily_cost_used_usd"), u.get("daily_cost_remaining_usd")
        self.last = {"used_usd": used, "remaining_usd": rem, "own_usd": round(own, 6), "ts": iso(now)}
        if own >= self.cap:
            why = f"worker spend today {own:.3f} >= {self.cap:.2f} USD"
        elif used is not None and float(used) >= self.cap:
            why = f"key spend today {float(used):.3f} >= {self.cap:.2f} USD"
        elif rem is not None and float(rem) - est < self.reserve:
            why = f"remaining {float(rem):.3f} USD would go below the {self.reserve:.2f} USD live-read reserve"
        if why:
            reset = next_reset(now)
            try:
                r = datetime.fromisoformat(str(u.get("daily_reset_at")).replace("Z", "+00:00"))
                if r.tzinfo and r > now:
                    reset = r
            except ValueError:
                pass
            raise BudgetPaused((reset + timedelta(minutes=3)).timestamp(), why)
        return self.last


# ------------------------------------------------------------------------------------------------ model choice
class ModelChoice:
    """Gemma-4-31B-IT whenever the endpoint lists it again, else Qwen3.8-27B. The list is re-read every ttl seconds;
    when it cannot be read the last choice stands (Qwen at start: Gemma has been withdrawn since 15 Oct)."""

    def __init__(self, list_models: Optional[Callable[[], list]] = None, ttl: float = 600.0,
                 clock: Callable[[], float] = time.time):
        self.list_models = list_models or self._fetch
        self.ttl, self.clock = ttl, clock
        self._at, self.key = -1e18, FALLBACK

    @staticmethod
    def _fetch() -> list:
        from twohands import amd
        r = amd._req("/models", timeout=20)
        return [m.get("id") for m in (r.get("data") or []) if isinstance(m, dict)]

    def choose(self) -> str:
        from twohands.reader import MODELS
        if self.clock() - self._at >= self.ttl:
            self._at = self.clock()
            try:
                ids = list(self.list_models())
                self.key = PRIMARY if MODELS[PRIMARY] in ids else FALLBACK
            except Exception:  # noqa: BLE001
                pass
        return self.key

    def withdrawn(self, key: str) -> None:
        if key == PRIMARY:
            self.key, self._at = FALLBACK, self.clock()


_NOT_SUPPORTED = re.compile(r"\b400\b.*not supported", re.I | re.S)


# ------------------------------------------------------------------------------------------------ images
def downscale(page, max_kb: int = PAGE_KB) -> bytes:
    """The masked page as a JPEG of at most max_kb (shrinking the size, then the quality)."""
    from PIL import Image
    im = page.convert("RGB")
    limit = max_kb * 1024
    side = 1800
    while True:
        for q in (80, 70, 60, 50):
            x = im.copy()
            x.thumbnail((side, side), Image.LANCZOS)
            buf = io.BytesIO()
            x.save(buf, "JPEG", quality=q, optimize=True)
            if buf.tell() <= limit:
                return buf.getvalue()
        side = int(side * 0.85)
        if side < 300:
            return buf.getvalue()


def crop_jpeg(page_jpeg: bytes, key: str) -> bytes:
    """The field's crop from the (masked, downscaled) page: words and digit boxes, never the printed row label
    (logos) and never right of the privacy mask (app/crops.py geometry)."""
    from PIL import Image
    from app.crops import LABEL_X1, field_boxes, mask_left_edge
    from twohands import schema
    s = schema.load()
    x0, y0, x1, y1 = field_boxes(s)[key]
    if x0 < LABEL_X1 < x1:
        x0 = LABEL_X1
    x1 = min(x1, mask_left_edge(s) - 0.002)
    im = Image.open(io.BytesIO(page_jpeg))
    W, H = im.size
    pad = 0.012
    c = im.crop((int(x0 * W), int(max(0, y0 - pad) * H), int(x1 * W), int(min(1, y1 + pad) * H))).convert("RGB")
    buf = io.BytesIO()
    c.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def dir_bytes(p: Path) -> int:
    return sum(f.stat().st_size for f in Path(p).glob("*.jpg")) if Path(p).is_dir() else 0


# ------------------------------------------------------------------------------------------------ labels + disputes
def label_for(key: str, model: int, capture: int, certified: Optional[int], mode: Optional[str],
              cert_keys: set) -> str:
    if key in cert_keys and mode == "comparison" and certified is not None:
        if certified == model != capture:
            return "confirmed"
        if certified == capture != model:
            return "model_misread"
    return "unconfirmed"


def disputes_of(g, cap: dict, cert: dict, mode: Optional[str], s: dict) -> list[dict]:
    """Fields where the model's read differs from the official capture. A field counts only when the model's words
    agree with its digits (the paper's own redundancy backs the read) and the rows are aligned (no shape / row-label
    failure); otherwise the read is not evidence and the field is not disputed."""
    if "shape" in g.codes or "label" in g.codes:
        return []
    cert_keys = set(s["vote_keys"]) | {"TOTAL"}
    out = []
    for f in s["fields"]:
        k = f["key"]
        n, w, c = g.values.get(k), g.words.get(k), cap.get(k)
        if n is None or w is None or n != w or c is None or n == c:
            continue
        cv = cert.get(k)
        out.append({"key": k, "model": n, "words": w, "capture": c, "certified": cv,
                    "label": label_for(k, n, c, cv, mode, cert_keys)})
    return out


# ------------------------------------------------------------------------------------------------ the worker
class Stop(Exception):
    pass


class Worker:
    def __init__(self, root: Path = WORKER_DIR, chat: Optional[Callable] = None, usage: Optional[Callable] = None,
                 list_models: Optional[Callable] = None, http_get: Callable = _http_get,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.time,
                 page_kb: int = PAGE_KB, disk_cap_mb: float = DISK_CAP_MB, daily_usd: float = DAILY_USD,
                 reserve_usd: float = RESERVE_USD, local_districts: Optional[Path] = None, log: Optional[logging.Logger] = None):
        from twohands import amd, schema
        from app.store import code_of
        self.P = Paths(root)
        self.P.root.mkdir(parents=True, exist_ok=True)
        self.s = schema.load()
        self.code_of = code_of
        self.chat = chat or (lambda body: amd.chat(body, retries=4, log=lambda *a, **k: None, kind="worker"))
        self.sleep_fn, self.clock = sleep, clock
        self.page_kb, self.disk_cap = page_kb, disk_cap_mb * 1024 * 1024
        self.source = Source(self.P.sources, get=http_get, clock=clock, sleep=sleep)
        self.models = ModelChoice(list_models, clock=clock)
        self.budget = Budget(usage or amd.usage, daily_usd, reserve_usd, own_today=self.own_today)
        self.local_districts = local_districts
        self.log = log or logging.getLogger("twohands.worker")
        self.stop_flag = threading.Event()
        self.last_progress = clock()
        self._urls: dict = {}
        self._load()

    # ---- state
    def _load(self) -> None:
        self.queue = load_queue(self.P.queue)
        if self.queue is None:
            raise RuntimeError(f"no audit queue at {self.P.queue}: run `python -m twohands.worker build-queue`")
        self.cap_keys = [f["key"] for f in self.s["fields"] if f.get("csv")]
        self.cert_keys = self.s["vote_keys"] + ["TOTAL"]
        self.rows = {r["clave"]: r for r in read_jsonl(self.P.results) if r.get("status") in TERMINAL}
        self.leaves: dict[str, list[str]] = {}
        self.records: dict[str, list[dict]] = {}
        seen: set = set()
        for r in read_jsonl(self.P.results):  # in file order: the order the leaves were added
            if r.get("status") in TERMINAL and r["clave"] not in seen:
                seen.add(r["clave"])
                for d in r.get("disputes", []):
                    self._add_leaf(str(r["ent"]), d["leaf"])
        self.pages_bytes = dir_bytes(self.P.pages)
        self.spent = {}
        for r in self.rows.values():
            day = budget_day(datetime.fromisoformat(r["ts"].replace("Z", "+00:00")))
            self.spent[day] = self.spent.get(day, 0.0) + float(r.get("cost_usd") or 0.0)

    def _add_leaf(self, ent: str, rec: dict) -> int:
        from twohands import merkle
        self.leaves.setdefault(ent, []).append(merkle.leaf_hash(rec))
        self.records.setdefault(ent, []).append(rec)
        return len(self.leaves[ent]) - 1

    def own_today(self) -> float:
        return self.spent.get(budget_day(datetime.fromtimestamp(self.clock(), timezone.utc)), 0.0)

    def items(self) -> list[dict]:
        return self.queue["items"]

    def todo(self) -> list[dict]:
        from twohands.priority import prioritized  # station requests from the site (/station) go first
        return prioritized([it for it in self.items() if it["clave"] not in self.rows], self.P.root)

    def state_done(self, ent: str) -> int:
        return sum(1 for r in self.rows.values() if str(r["ent"]) == ent)

    def roots(self) -> dict:
        from twohands import merkle
        out = {}
        for ent, st in self.queue["states"].items():
            done = self.state_done(ent)
            if not done:
                continue
            lv = self.leaves.get(ent, [])
            out[ent] = {"state": st["name"], "done": done, "queue": st["queue"], "complete": done >= st["queue"],
                        "leaves": len(lv), "root": merkle.root(lv)}
        return out

    def write_status(self, status: str, pause: Optional[str] = None, until: Optional[float] = None,
                     why: str = "", current: Optional[str] = None) -> None:
        from twohands.reader import MODELS
        write_atomic(self.P.state, json.dumps({
            "status": status, "pause": pause, "pause_text": PAUSES.get(pause) if pause else None,
            "resume_at": iso(datetime.fromtimestamp(until, timezone.utc)) if until else None, "why": why,
            "reader": MODELS[self.models.key], "current": current, "done": len(self.rows),
            "queue": len(self.items()), "budget": self.budget.last, "own_spend_today_usd": round(self.own_today(), 6),
            "pages_mb": round(self.pages_bytes / 1048576, 2), "disk_cap_mb": round(self.disk_cap / 1048576, 1),
            "page_kb": self.page_kb, "pid": os.getpid(), "ts": iso()}, indent=1))
        self.beat()

    def beat(self) -> None:
        self.last_progress = self.clock()
        self.beat_file()

    def beat_file(self) -> None:
        """The heartbeat file only (the watchdog writes it while a long model call is in flight)."""
        write_atomic(self.P.heartbeat, json.dumps({"ts": iso(), "t": time.time(), "pid": os.getpid()}))

    # ---- one form
    def url_of(self, it: dict) -> Optional[str]:
        k = (it["ent"], it["dist"])
        if k not in self._urls:
            self._urls[k] = district_map(it["ent"], it["dist"], self.source, self.P.urls, self.local_districts)
        return self._urls[k].get(it["clave"])

    def process(self, it: dict) -> dict:
        """Audit one form. Returns its (terminal) result row; raises SourcePaused / BudgetPaused / EndpointDown."""
        from PIL import Image
        from twohands import mask, merkle, reader, register
        from twohands.gate import gate
        k, ent = it["clave"], str(it["ent"])
        base = {"clave": k, "ent": it["ent"], "state": self.queue["states"][ent]["name"], "dist": it["dist"],
                "layout": it["layout"], "cert_mode": it.get("mode"), "ts": iso()}
        url = self.url_of(it)
        if not url:
            return base | {"status": "no_image", "why": "no image URL in the PREP district file"}
        try:
            raw = self.source.fetch(url)
        except NotFound as e:
            return base | {"status": "image_unavailable", "why": str(e)}
        try:
            img = Image.open(io.BytesIO(raw))
            img.load()
            img = img.copy()
        except Exception as e:  # noqa: BLE001
            return base | {"status": "unreadable", "why": type(e).__name__}
        finally:
            del raw  # the unmasked bytes never leave this function
        try:
            page, info = mask.prepare(img, it["layout"], self.s)
        except register.NotLocated as e:
            return base | {"status": "not_located", "why": str(e)[:120]}
        except Exception as e:  # noqa: BLE001
            return base | {"status": "unreadable", "why": f"{type(e).__name__}: {str(e)[:100]}"}
        finally:
            del img
        full = io.BytesIO()
        page.convert("RGB").save(full, "JPEG", quality=mask.JPEG_QUALITY)
        small = downscale(page, self.page_kb)
        del page
        # budget, then the read (the stored page is written only after a successful read, so a paused form leaves
        # nothing behind and is simply fetched again)
        self.budget.check()
        key = self.models.choose()
        row = reader.read(key, io.BytesIO(full.getvalue()), self.s, chat=self.chat)
        if row.get("error") and key == PRIMARY and _NOT_SUPPORTED.search(row["error"]):
            self.models.withdrawn(key)
            key = self.models.choose()
            self.budget.check()
            row = reader.read(key, io.BytesIO(full.getvalue()), self.s, chat=self.chat)
        if row.get("error"):
            raise EndpointDown(row["error"][:160])
        cost = float((row.get("usage") or {}).get("cost") or 0.0)
        day = budget_day(datetime.fromtimestamp(self.clock(), timezone.utc))
        self.spent[day] = self.spent.get(day, 0.0) + cost
        page_rel = None
        if self.pages_bytes + len(small) <= self.disk_cap:
            write_atomic(self.P.pages / f"{k}.jpg", small)
            self.pages_bytes += len(small)
            page_rel = f"pages/{k}.jpg"
        g = gate(row.get("parsed"), self.s)
        if row.get("finish_reason") == "length":
            g.accepted = False
            g.codes.append("shape")
        cap = dict(zip(self.cap_keys, it["cap"]))
        cert = dict(zip(self.cert_keys, it["cert"])) if it.get("cert") else {}
        ds = disputes_of(g, cap, cert, it.get("mode"), self.s)
        model_id = reader.MODELS[key]
        out_d = []
        for d in ds:
            code = self.code_of(d["key"])
            crop = crop_jpeg(small, d["key"])
            write_atomic(self.P.crops / f"{k}__{code}.jpg", crop)
            rec = merkle.leaf_record_live(k, code, d["capture"], d["model"], d["words"], d["label"],
                                          hashlib.sha256(crop).hexdigest(), model_id, d["certified"])
            out_d.append({"code": code, "paper": d["model"], "words": d["words"], "capture": d["capture"],
                          "certified": d["certified"], "label": d["label"], "crop": f"crops/{k}__{code}.jpg",
                          "leaf": rec})
        fields = {self.code_of(f["key"]): {"n": g.values.get(f["key"]), "w": g.words.get(f["key"]),
                                           "capture": cap.get(f["key"]), "certified": cert.get(f["key"])}
                  for f in self.s["fields"]}
        return base | {"status": "audited", "reader": model_id, "model_key": key,
                       "prompt_sha256": reader.prompt_sha256(self.s), "accepted": g.accepted,
                       "route_codes": sorted(set(g.codes)), "finish_reason": row.get("finish_reason"),
                       "cost_usd": round(cost, 6), "latency_s": row.get("secs"), "page": page_rel,
                       "page_bytes": len(small), "locator": {"score": info.get("score")}, "fields": fields,
                       "disputes": out_d}

    def commit(self, it: dict, r: dict) -> None:
        """Make one result durable: the row, its dispute lines, then the roots (all derived again on restart)."""
        ent = str(it["ent"])
        for d in r.get("disputes", []):
            d["leaf_index"] = len(self.leaves.get(ent, []))
            self._add_leaf(ent, d["leaf"])
        append_jsonl(self.P.results, r)
        for d in r.get("disputes", []):
            append_jsonl(self.P.disputes, {"clave": r["clave"], "ent": r["ent"], "state": r["state"],
                                           "reader": r["reader"], "ts": r["ts"], **{x: d[x] for x in d if x != "leaf"}})
        self.rows[r["clave"]] = r
        write_atomic(self.P.roots, json.dumps(self.roots(), indent=1))

    # ---- loop
    def wait_until(self, until: float, pause: str, why: str) -> None:
        self.log.info("pause %s until %s: %s", pause, iso(datetime.fromtimestamp(until, timezone.utc)), why)
        while not self.stop_flag.is_set() and self.clock() < until:
            self.write_status("paused", pause, until, why)
            self.sleep_fn(min(60.0, max(0.0, until - self.clock())))

    def run(self, limit: Optional[int] = None, max_steps: Optional[int] = None) -> int:
        """Audit until the queue is done, stop() is called, or ``limit`` forms have been read on AMD."""
        read = steps = 0
        endpoint_backoff = 120.0
        while not self.stop_flag.is_set():
            if max_steps is not None and steps >= max_steps:
                break
            steps += 1
            todo = self.todo()
            if not todo:
                self.write_status("complete")
                self.log.info("queue complete")
                break
            it = todo[0]
            self.write_status("running", current=it["clave"])
            try:
                r = self.process(it)
            except SourcePaused as e:
                self.wait_until(e.until, "source", e.why)
                continue
            except BudgetPaused as e:
                self.wait_until(e.until, "budget", e.why)
                continue
            except EndpointDown as e:
                self.wait_until(self.clock() + endpoint_backoff, "endpoint", str(e))
                endpoint_backoff = min(1800.0, endpoint_backoff * 2)
                continue
            endpoint_backoff = 120.0
            self.commit(it, r)
            nd = len(r.get("disputes", []))
            self.log.info("%s %s %s %s disputes=%d cost=%.5f", r["clave"], r["state"], r["status"],
                          r.get("reader", ""), nd, r.get("cost_usd") or 0.0)
            if r["status"] == "audited":
                read += 1
                if limit is not None and read >= limit:
                    break
        self.write_status("stopped" if self.todo() else "complete")
        return read

    def stop(self, *_a) -> None:
        self.stop_flag.set()


class EndpointDown(Exception):
    pass


# ------------------------------------------------------------------------------------------------ service plumbing
def setup_logging(P: Paths) -> logging.Logger:
    P.logs.mkdir(parents=True, exist_ok=True)
    lg = logging.getLogger("twohands.worker")
    lg.setLevel(logging.INFO)
    if not lg.handlers:
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%SZ")
        fmt.converter = time.gmtime
        fh = logging.handlers.RotatingFileHandler(P.logs / "worker.log", maxBytes=5 * 1024 * 1024, backupCount=3,
                                                  encoding="utf-8")
        sh = logging.StreamHandler(sys.stdout)
        for h in (fh, sh):
            h.setFormatter(fmt)
            lg.addHandler(h)
    return lg


def acquire_lock(P: Paths, stale_s: float = 600.0) -> bool:
    """One worker per directory. A lock whose heartbeat is older than stale_s belongs to a dead process."""
    P.root.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(P.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            hb = read_json(P.heartbeat, {}) or {}
            if time.time() - float(hb.get("t", 0)) > stale_s and time.time() - P.lock.stat().st_mtime > stale_s:
                P.lock.unlink(missing_ok=True)
                continue
            return False
    return False


def release_lock(P: Paths) -> None:
    P.lock.unlink(missing_ok=True)


def watchdog(w: Worker, stall_s: float = STALL_S, period: float = 60.0) -> threading.Thread:
    """Exit the whole process when the loop has made no progress (no row, no heartbeat) for stall_s: a hung HTTP call
    or a deadlock. The container's restart policy starts a fresh worker, which resumes from results.jsonl."""
    def loop():
        while not w.stop_flag.is_set():
            time.sleep(period)
            if time.time() - w.last_progress > stall_s:
                w.log.error("watchdog: no progress for %.0f s, exiting for a restart", stall_s)
                logging.shutdown()
                os._exit(70)
            try:
                w.beat_file()  # alive and within the stall limit (a slow model call is not a stall)
            except OSError:
                pass
    t = threading.Thread(target=loop, daemon=True, name="watchdog")
    t.start()
    return t


def seed(P: Paths, seed_dir: str = SEED_DIR) -> bool:
    """First start on a fresh volume: copy the committed state (queue, rows, pages, crops, receipts) so the service
    continues where the last run stopped."""
    src = Path(seed_dir) if seed_dir else None
    if not src or not (src / "queue.json.gz").is_file() or P.queue.is_file():
        return False
    for item in src.iterdir():
        if item.name in ("logs", "worker.lock", "heartbeat.json"):
            continue
        dst = P.root / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)
    return True


def status_line(P: Paths) -> str:
    st = read_json(P.state, {}) or {}
    rows = [r for r in read_jsonl(P.results) if r.get("status") == "audited"]
    ds = [d for r in rows for d in r.get("disputes", [])]
    conf = sum(d["label"] == "confirmed" for d in ds)
    return (f"{st.get('status', 'never run')}{' (' + st['pause_text'] + ')' if st.get('pause_text') else ''}: "
            f"{len(rows)} forms audited on AMD, {len(ds)} disputes, {conf} confirmed by the certified count; "
            f"reader {st.get('reader', '-')}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m twohands.worker")
    ap.add_argument("cmd", choices=["build-queue", "run", "status", "check"])
    ap.add_argument("--dir", default=str(WORKER_DIR))
    ap.add_argument("--limit", type=int, default=None, help="stop after N forms read on AMD")
    ap.add_argument("--stale", type=float, default=900.0, help="check: heartbeat age that counts as unhealthy (s)")
    a = ap.parse_args(argv)
    P = Paths(Path(a.dir))
    if a.cmd == "build-queue":
        q = build_queue()
        save_queue(q, P.queue)
        print(f"{P.queue}: {len(q['items'])} forms in {len(q['states'])} states; "
              f"first state {q['states'][str(q['items'][0]['ent'])]['name']}")
        return 0
    if a.cmd == "status":
        print(status_line(P))
        return 0
    if a.cmd == "check":
        hb = read_json(P.heartbeat, {}) or {}
        return 0 if time.time() - float(hb.get("t", 0)) < a.stale else 1
    seed(P)
    lg = setup_logging(P)
    if not acquire_lock(P):
        lg.error("another worker holds %s", P.lock)
        return 2
    try:
        w = Worker(P.root, log=lg)
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, w.stop)
            except (ValueError, OSError):
                pass
        watchdog(w)
        lg.info("worker start: %d of %d forms done, reader %s, cap %.2f USD/day, reserve %.2f USD",
                len(w.rows), len(w.items()), w.models.choose(), w.budget.cap, w.budget.reserve)
        n = w.run(limit=a.limit)
        lg.info("worker stop: %d forms read this session; %s", n, status_line(P))
    finally:
        release_lock(P)
    return 0


if __name__ == "__main__":
    sys.exit(main())
