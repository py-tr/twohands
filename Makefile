.PHONY: eval test

# Every number on the site recomputed from the committed raw results, checked against what the app shows.
# Without make: python -m twohands.eval; python scripts/gemma_vs_qwen.py; python scripts/build_report.py --check;
#   python scripts/ieebcs_score.py --check (the BCS head-to-head block of results/ieebcs_head_to_head.md; empty until the run);
#   python scripts/ballot_stock.py --check (gate v3 bands and results/ballot_stock.md, Amendment 7);
#   python scripts/confirm100_score.py --check (the pre-registered 100-form confirmation, results/confirm100.md);
#   python scripts/ine_metric.py --check (INE's 2024 acceptance metric as we read it, results/ine_metric.md);
#   python scripts/national_counts.py --check (the cost of the problem from INE's 2024 files, results/national_counts.md);
#   python scripts/price_check.py --check (the price, from app/pricing.py, in every doc that states it);
#   python scripts/amd_bench.py --check (the AMD evidence block from our logs, and the docs that quote it);
#   python scripts/build_agree200.py --check (the seeded blind check of 200 agreeing fields);
#   python scripts/why_gemma.py --check (the Gemma table and the caught misreads, from app/data/bakeoff_300.json)
eval:
	python -m twohands.eval
	python scripts/gemma_vs_qwen.py
	python scripts/build_report.py --check
	python scripts/ieebcs_score.py --check
	python scripts/ballot_stock.py --check
	python scripts/confirm100_score.py --check
	python scripts/ine_metric.py --check
	python scripts/national_counts.py --check
	python scripts/price_check.py --check
	python scripts/amd_bench.py --check
	python scripts/build_agree200.py --check
	python scripts/why_gemma.py --check

test:
	python -m pytest -q
