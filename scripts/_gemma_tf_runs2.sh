#!/usr/bin/env bash
# The second Gemma Token Factory chain (PROTOCOL.md Amendments 8 and 8b), queued after scripts/_gemma_tf_runs.sh:
# waits until results/gemma_tf_runs.log shows ALLDONE (polls every 60 s), then read B of the 300 (page + 4 tiles ->
# results/calls_gemma_b4.jsonl), then Colima (-> results/colima/calls_gemma.jsonl), each resumable by clave, then
# scores both. Launched with:
#   nohup bash scripts/_gemma_tf_runs2.sh >> results/gemma_tf_runs2.out 2>&1 &
# Budget: the bulk share of the shared key; 0.70 while the live worker is not deployed (twohands/budgets.py).
cd "$(dirname "$0")/.." || exit 1
export TWOHANDS_BULK_DAILY_USD="${TWOHANDS_BULK_DAILY_USD:-0.70}"
export PYTHONUNBUFFERED=1
echo "$(date -u +%FT%TZ) chain2 waiting for ALLDONE in results/gemma_tf_runs.log (pid $$)"
until grep -q '^ALLDONE' results/gemma_tf_runs.log 2>/dev/null; do sleep 60; done
echo "$(date -u +%FT%TZ) chain2 first chain done; starting"
set -x
python -u scripts/gemma_tf_reads2.py b4
python -u scripts/gemma_tf_reads2.py colima
python -u scripts/gemma_tf_reads2.py score-b4
python -u scripts/gemma_tf_reads2.py score-colima
set +x
echo "$(date -u +%FT%TZ) chain2 ALLDONE"
