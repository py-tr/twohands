"""Start the Two Hands web app.

    python run_app.py [--port 8000] [--host 127.0.0.1] [--build]

--build refreshes the snapshots first (app/data from spikes/tally-witness, ledger/ledger.json from
spikes/ledger-rescue, and official values for any new form in results/*.jsonl). New results/*.jsonl files are
picked up by the running app without a restart.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--build", action="store_true")
    a = ap.parse_args()
    if a.build:
        from app import build
        from ledger import build as lbuild
        build.main()
        lbuild.main()
    import uvicorn
    uvicorn.run("app.main:app", host=a.host, port=a.port, log_level="info")
