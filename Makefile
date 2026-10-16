.PHONY: eval test

# Every number on the site recomputed from the committed raw results, checked against what the app shows.
# Without make: python -m twohands.eval; python scripts/gemma_vs_qwen.py; python scripts/build_report.py --check;
#   python scripts/ieebcs_score.py --check (the BCS head-to-head block of results/ieebcs_head_to_head.md; empty until the run);
#   python scripts/ballot_stock.py --check (gate v3 bands and results/ballot_stock.md, Amendment 7)
eval:
	python -m twohands.eval
	python scripts/gemma_vs_qwen.py
	python scripts/build_report.py --check
	python scripts/ieebcs_score.py --check
	python scripts/ballot_stock.py --check

test:
	python -m pytest -q
