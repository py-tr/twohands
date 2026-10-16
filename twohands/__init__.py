"""Two Hands: the model reads, the paper decides."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# In-repo copies of the pilot ("spike") inputs and reads; provenance and sha256 in data/pilot/SOURCES.md.
PILOT_DATA = REPO / "data" / "pilot" / "tally-witness"
PILOT_RESULTS = REPO / "results" / "pilot" / "tally-witness"
