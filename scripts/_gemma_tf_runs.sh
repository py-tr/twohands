set -x
python -u scripts/confirm_read.py --model gemma --workers 2 --set confirm100
python -u -m twohands.run --schema mx_senado_2024 --manifest results/manifest_senado100.json --models gemma
python -u -m twohands.run --schema mx_bcs_dl_2024,mx_bcs_ayto_2024 --manifest results/manifest_ieebcs300.json --models gemma
echo ALLDONE
