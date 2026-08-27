#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_anticipation_cases.py -- qualitative search for the EPS/vodka-ruso
phenomenon: the model representing nationality/migration/class content
BEFORE any sensitive keyword, from indirect contextual cues alone.

Why this is a DIFFERENT question from VSS: the D metric measures whether
a SPECIFIC keyword, at the moment it's read, triggers more representation
than its neutral twin. It cannot detect anticipation, because cue and
neutral arms are IDENTICAL text up to the keyword -- there's structurally
nothing to compare before that point.

This script instead looks ONLY at the neutral arm's tw-1 position (the
token right before where the keyword WOULD have been, in a prompt that
never contains any Colombian keyword anywhere). If migration/nationality/
class content shows up there anyway, it can only be coming from indirect
context (register, implied occupation, phrasing) -- genuine anticipation,
not a keyword trigger. This mirrors the pilot's qualitative case studies
(A01, B01, C01), just applied to the new 120-prompt dataset.

This is EXPLORATORY: it surfaces candidate excerpts for manual reading,
the same way the pilot did. It does not replace VSS, and it doesn't
produce a formal statistic -- just a shortlist worth reading by hand.
"""

import argparse
import json
import re

# Curated term lists, grouped for readable output. Deliberately broad --
# false positives are cheap to skip when reading by hand; false negatives
# (missing a real case) are the expensive mistake here.
TERMS = {
    "migration": [
        "migrant", "immigrant", "immigration", "foreign", "foreigner",
        "abroad", "moved to", "moving to", "relocat", "emigrat",
        "newcomer", "expat",
    ],
    "other_country": [
        "spain", "spanish", "united states", "u.s.", "usa", "american",
        "mexico", "mexican", "argentina", "argentinian", "venezuela",
        "venezuelan", "turkey", "turkish", "canada", "canadian",
        "peru", "peruvian", "ecuador", "ecuadorian", "chile", "chilean",
    ],
    "ses": [
        "poor", "poverty", "low-income", "low income", "working class",
        "wealthy", "affluent", "welfare", "underprivileged",
    ],
}

ALL_TERMS = [(cat, t) for cat, terms in TERMS.items() for t in terms]


def find_matches(text):
    """Returns list of (category, term) found in text (case-insensitive)."""
    lower = text.lower()
    return [(cat, term) for cat, term in ALL_TERMS if term in lower]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/results_stage4.json",
                    help="a stage file that has 'explanations' -- stage2, "
                         "stage3, or stage4 all work, since none of them "
                         "remove that field")
    ap.add_argument("--position", default="tw-1",
                    help="which position to scan (default: tw-1, the "
                         "pre-keyword baseline)")
    ap.add_argument("--out", default="results/anticipation_candidates.txt")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        items = json.load(f)

    neutral_items = [it for it in items if it["arm"] == "neutral"]
    print(f"Scanning {len(neutral_items)} neutral-arm items, "
         f"position={args.position} ...")

    candidates = []
    for item in neutral_items:
        samples = item.get("explanations", {}).get(args.position, [])
        for i, text in enumerate(samples):
            matches = find_matches(text)
            if matches:
                candidates.append({
                    "pair_id": item["group_id"],
                    "language": item["language"],
                    "attribute": item["attribute"],
                    "sample_idx": i,
                    "matched_terms": matches,
                    "text": text,
                })

    print(f"Found {len(candidates)} candidate excerpts across "
         f"{len({(c['pair_id'], c['language']) for c in candidates})} "
         f"distinct (scenario, language) pairs.\n")

    # counts by category, for a rough sense of what's driving the hits
    by_category = {}
    for c in candidates:
        for cat, _ in c["matched_terms"]:
            by_category[cat] = by_category.get(cat, 0) + 1
    print("Matches by category (a single excerpt can match more than one):")
    for cat, n in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {n}")

    # write full candidates to file for manual reading, grouped by scenario
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"Anticipation candidates -- position={args.position}, "
               f"neutral arm only\n")
        f.write(f"Input: {args.input}\n")
        f.write(f"Total candidates: {len(candidates)}\n")
        f.write("=" * 70 + "\n\n")
        for c in sorted(candidates, key=lambda x: (x["pair_id"], x["language"])):
            terms_str = ", ".join(f"{cat}:{term}" for cat, term in c["matched_terms"])
            f.write(f"[{c['pair_id']} / {c['language']} / {c['attribute']} / "
                    f"sample {c['sample_idx']}]\n")
            f.write(f"Matched: {terms_str}\n")
            f.write(f"Text: {c['text']}\n")
            f.write("-" * 70 + "\n")

    print(f"\nFull excerpts written to {args.out} -- read these by hand, "
         "the same way the pilot's case studies (A01, B01, C01) were built.")
    print("A term match here is a CANDIDATE, not a confirmed case -- "
         "many will be false positives (e.g. 'poor' used in an unrelated "
         "sense). The value is in finding the real ones, not the raw count.")


if __name__ == "__main__":
    main()