"""Endpoint health probe: every 5 min one tiny text call per model (5 tokens, no image), logged by amd.chat into
results/endpoint_health.jsonl (kind=probe). Real reads are logged there too (kind=read).
    python scripts/health_probe.py [interval_s]"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import amd
every = float(sys.argv[1]) if len(sys.argv) > 1 else 300
while True:
    for m in ("Gemma-4-31B-IT", "Qwen3.8-27B"):
        try:
            amd.chat({"model": m, "messages": [{"role": "user", "content": "Say OK."}], "max_tokens": 5, "temperature": 0},
                     retries=1, log=lambda s: None, kind="probe")
        except Exception:
            pass
    time.sleep(every)
