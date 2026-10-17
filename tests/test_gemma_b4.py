"""PROTOCOL.md Amendment 8 (read B, Gemma page + 4 tiles on the 300): the committed score recomputes unchanged."""
import json
import sys

from twohands import REPO

sys.path.insert(0, str(REPO / "scripts"))


def test_score_b4_check_passes():
    import gemma_tf_reads2
    assert gemma_tf_reads2.main(["score-b4", "--check"]) == 0


def test_amendment8_numbers():
    d = json.loads((REPO / "results" / "gemma_b4_300.json").read_text(encoding="utf-8"))
    gg, gq = d["a_two_reader"]["gemma_gemma"], d["a_two_reader"]["gemma_qwen"]
    assert (gq["accepted"], gq["errors"], gq["fields"]) == (89, 0, 1958)      # as reported (results/two_reader_300.md)
    assert d["b_tiling"]["A_6tiles"]["accepted"] == 55 and d["b_tiling"]["A_6tiles"]["errors"] == 2  # the headline
    assert d["rows"]["B"] == 300 and d["pending_adjudication"] == 0
    assert all("[AI adjudicator's reading]" in w or "[confirmed" in w for w in gg["wrong"])
    md = (REPO / "results" / "gemma_b4_300.md").read_text(encoding="utf-8")
    for party in ("PVEM", "MORENA", "PRI_PRD", "PT_MORENA"):
        assert party not in md
