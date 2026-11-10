"""Check that validate_dataset.py reproduces the `qa` blocks stored in the pilot's 30 pairs
(es and en, 60 comparisons). Run: python test_reproduce_pilot_qa.py"""
import json
import sys
from pathlib import Path

from validate_dataset import validate_pair

HERE = Path(__file__).resolve().parent
data = json.loads((HERE.parent / "dataset" / "minimal_pairs.json").read_text(encoding="utf-8"))

mismatches, total = [], 0
for pair in data["pairs"]:
    for lang in ("es", "en"):
        mine = validate_pair(pair, lang)
        stored = pair["qa"]
        expected = {
            "single_span": stored[f"{lang}_single_span"],
            "span_cue": stored[f"{lang}_span_cue"],
            "span_neutral": stored[f"{lang}_span_neutral"],
            "span_start_word_index": stored[f"{lang}_span_start_word_index"],
            "cue_word_count": stored[f"{lang}_cue_word_count"],
            "neutral_word_count": stored[f"{lang}_neutral_word_count"],
        }
        total += 1
        for k, v in expected.items():
            if mine[k] != v:
                mismatches.append((pair["id"], lang, k, mine[k], v))

print(f"{total} pair-language comparisons, {len(mismatches)} field mismatches")
for m in mismatches:
    print("  MISMATCH", m)
sys.exit(1 if mismatches else 0)
