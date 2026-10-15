"""Point the core reader at another OpenAI-compatible endpoint (self-hosted vLLM on one MI300X) for ONE process,
without editing the core.

    TWOHANDS_BASE_URL=http://127.0.0.1:8000/v1   # required to switch; unset = the AMD Token Factory as before
    TWOHANDS_KEY=...                              # the vLLM --api-key (read from env, never printed or written)
    TWOHANDS_MODEL_GEMMA=google/gemma-4-31B-it    # the served model name for the "gemma" reader (optional)
    TWOHANDS_MODEL_QWEN=...                       # same for "qwen" (optional; normally Qwen stays on the Token Factory)

How it works (no core file changes):
- ``twohands.amd._cfg`` reads AMD_KEY / AMD_BASE_URL from the process env FIRST and only falls back to ../.env when
  either is missing. ``apply()`` sets both from TWOHANDS_KEY / TWOHANDS_BASE_URL, so the .env file is never read.
- ``twohands.reader.MODELS`` is a module-level dict read at request time; ``apply()`` overrides the "gemma" entry
  in this process only. Records then carry the served model id, so self-hosted rows are distinguishable.
- The rate limiter and the health log are per endpoint: TWOHANDS_RATE_FILE defaults to
  cache/ratelimit_selfhosted.json (the Token Factory's 6 req/min budget in cache/ratelimit.json is not consumed
  or shared), TWOHANDS_RPM to 6000, TWOHANDS_CONCURRENCY to 16, TWOHANDS_HEALTH_FILE to
  results/endpoint_health_selfhosted.jsonl. Any of these already set in the env wins.

Call ``apply()`` before the first request. Usage as a wrapper:  python scripts/endpoint_switch.py -m twohands.mask ...
"""
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DEFAULTS = {"TWOHANDS_RATE_FILE": str(REPO / "cache" / "ratelimit_selfhosted.json"),
            "TWOHANDS_RPM": "6000", "TWOHANDS_CONCURRENCY": "16",
            "TWOHANDS_HEALTH_FILE": str(REPO / "results" / "endpoint_health_selfhosted.jsonl")}


def active(env=None) -> bool:
    env = os.environ if env is None else env
    return bool(env.get("TWOHANDS_BASE_URL"))


def apply(env=None) -> dict:
    """Switch this process to TWOHANDS_BASE_URL. Returns a key-free description. No-op if unset."""
    env = os.environ if env is None else env
    if not active(env):
        return {"endpoint": "token-factory", "switched": False}
    base, key = env["TWOHANDS_BASE_URL"].rstrip("/"), env.get("TWOHANDS_KEY")
    if not key:
        raise RuntimeError("TWOHANDS_BASE_URL is set but TWOHANDS_KEY is not (the vLLM --api-key)")
    env["AMD_BASE_URL"], env["AMD_KEY"] = base, key
    for k, v in DEFAULTS.items():
        env.setdefault(k, v)
    from twohands import amd, ratelimit, reader
    # these modules read their env at import time: re-read so the order of imports does not matter
    ratelimit.RPM = float(env["TWOHANDS_RPM"])
    ratelimit.CONCURRENCY = int(env["TWOHANDS_CONCURRENCY"])
    ratelimit.reset_shared(None)
    amd.HEALTH = Path(env["TWOHANDS_HEALTH_FILE"])
    for mk, var in (("gemma", "TWOHANDS_MODEL_GEMMA"), ("qwen", "TWOHANDS_MODEL_QWEN")):
        if env.get(var):
            reader.MODELS[mk] = env[var]
    u = urlparse(base)
    return {"endpoint": "self-hosted", "switched": True, "host": u.hostname, "port": u.port,
            "models": dict(reader.MODELS), "rpm": ratelimit.RPM, "concurrency": ratelimit.CONCURRENCY}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] != "-m":
        print(__doc__)
        return 2
    mod = argv[1]
    if mod == "twohands.run" and active():
        print("refusing: twohands.run writes the 300-run files (results/calls_<model>.jsonl); "
              "use scripts/confirm_read.py, scripts/consistency_43.py or bench/bench_mi300x.py")
        return 3
    print("endpoint:", apply(), flush=True)
    sys.argv = [mod] + argv[2:]
    runpy.run_module(mod, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
