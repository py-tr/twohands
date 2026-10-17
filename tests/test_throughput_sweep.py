"""scripts/throughput_sweep.py summary arithmetic, on synthetic rows (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import throughput_sweep as ts  # noqa: E402


def _row(level, t0, secs, status=200, retries=0, codes=()):
    return {"level": level, "t_submit": t0, "t_end": t0 + secs, "status": status, "http_s": secs - 1, "wall_s": secs,
            "retries": retries, "n_429": list(codes).count("429"), "tokens_in": 2600, "tokens_out": 800,
            "cost_usd": 0.000144 if status == 200 else None, "parsed_ok": status == 200, "images_sent": 7}


def test_percentile_nearest_rank():
    assert ts.pct([1, 2, 3, 4, 5, 6], 50) == 3
    assert ts.pct([1, 2, 3, 4, 5, 6], 95) == 6


def test_summary_best_level_and_national_hours():
    rows = [_row(1, 1000 + 60 * i, 60) for i in range(6)]                      # 6 forms in 360 s: 1/min
    rows += [_row(2, 2000 + 30 * i, 60) for i in range(8)]                     # 8 forms in 270 s
    rows += [_row(4, 3000, 60, status="error", retries=6, codes=["429"] * 6)]  # an error level is never "best"
    rows += [_row(4, 3000 + i, 60) for i in range(3)]
    d = ts.summarize(rows)
    lv = {x["in_flight"]: x for x in d["levels"]}
    assert lv[1]["forms_per_min"] == 1.0
    assert lv[4]["error_rate"] == 0.25 and lv[4]["n_429"] == 6
    assert d["best_in_flight"] == 2
    fpm = lv[2]["forms_per_min"]
    assert d["national_hours"] == round(169_005 / fpm / 60, 1)
    assert "shared endpoint" in d["line"] and "not GPU time" in d["line"]
