# LatAm mini pilot - working files

- `step2_countries.py` -> `countries.json`: the 3 countries (excluding Colombia) with most rows in CHOCLO.
  Input: `data/BenchmarkCHOCLO.csv`, downloaded from https://huggingface.co/datasets/latam-gpt/CHOCLO (MIT), not committed.
  Case variants of the same country ("Cuba"/"cuba") are merged; this is not specified in the protocol and is pending confirmation
  (without merging the top 3 would be Chile, Costa Rica, Cuba).
- `validate_dataset.py`: machine checks for minimal pairs (single span, span starts at word index >= 10, cue/neutral
  word-count ratio within 20%). `python latam_pilot/validate_dataset.py dataset/minimal_pairs.json --lang es`
- `test_reproduce_pilot_qa.py`: checks the validator reproduces the stored `qa` blocks of the 30 pilot pairs (es + en).
  Run from `latam_pilot/`: `python test_reproduce_pilot_qa.py`
