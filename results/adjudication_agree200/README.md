# Blind check of 200 agreeing fields

Pool: accepted forms of the two-reader tier (Amendment 2 d); graded fields where the model's digits equal the official capture (PREP 2024): **1,955 fields** (pool sha256 `c815b81f504a911a...`). Drawn: `random.Random(20261016).sample(pool, 200)` by `scripts/build_agree200.py`. No model call.

Each crop is cut from the masked page (never a raw image). A person reads them blind at `/check?set=agree200`: the page shows no model value and no capture value. Answers go to `app/state/spotcheck_agree200.json`; `/check/results?set=agree200` compares them with the agreed value.

Until all 200 are answered, every page says: fields where the model and the capture agree were not individually checked.
