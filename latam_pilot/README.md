# LatAm mini pilot - working files

**Countries: México and Argentina**, with Colombia as the anchor (13 Nov plan, following Samuel's advice to start with
three contrasting sub-regions: Andean, Mesoamerican, Rioplatense). The earlier step 2 (picking the top 3 countries from
CHOCLO) was removed on 2026-11-16; the old version is in tag `countries-v1`.

- `validate_dataset.py`: machine checks for minimal pairs (single span, span starts at word index >= 10, cue/neutral
  word-count ratio within 20%). `python latam_pilot/validate_dataset.py dataset/minimal_pairs.json --lang es`
- `test_reproduce_pilot_qa.py`: checks the validator reproduces the stored `qa` blocks of the 30 pilot pairs (es + en).
  Run from `latam_pilot/`: `python test_reproduce_pilot_qa.py`
