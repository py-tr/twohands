.PHONY: eval test

# Every number on the site recomputed from the committed raw results, checked against what the app shows.
# Without make: python -m twohands.eval; python scripts/gemma_vs_qwen.py; python scripts/build_report.py --check
eval:
	python -m twohands.eval
	python scripts/gemma_vs_qwen.py
	python scripts/build_report.py --check

test:
	python -m pytest -q
