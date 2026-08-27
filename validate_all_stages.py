#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_all_stages.py -- runs all 5 stages (extraction, verbalization,
grading, ars, metric) on a small subset (N01, N02) to validate the full
pipeline end to end, including the newly integrated ARS stage, before
committing to the 120-item run.
"""

import sys
import json

sys.path.insert(0, ".")
from main import load_config, load_dataset
from src import extraction, verbalization, grading, ars, metric


def main():
    config = load_config("config.yaml")
    all_items = load_dataset(config)
    subset = [it for it in all_items if it["group_id"] in ("N01", "N02")]
    print(f"Prompts en la prueba: {len(subset)}")
    for it in subset:
        print(f"  {it['id']}: keyword={it['keyword']!r}")

    print("\n=== Stage 1: extraction ===")
    items = extraction.extract_activations(subset, config)
    assert all("vectors" in it for it in items), "MISSING vectors key"
    assert all("tw" in it["vectors"] for it in items), "MISSING tw position"
    print(f"OK: {len(items)} items with vectors['tw'], dim={len(items[0]['vectors']['tw'])}")

    print("\n=== Stage 2: verbalization ===")
    items = verbalization.verbalize(items, config)
    assert all("explanations" in it for it in items), "MISSING explanations key"
    example = items[0]["explanations"]["tw"][0]
    print(f"OK: example explanation (item {items[0]['id']}):")
    print(f"  {example[:200]}")

    print("\n=== Stage 3: grading ===")
    items = grading.grade(items, config)
    assert all("gradings" in it for it in items), "MISSING gradings key"
    g0 = items[0]["gradings"]["tw"][0]
    print(f"OK: example grading: {g0}")

    n_positive = sum(1 for it in items for pos_g in it["gradings"].values()
                     for g in pos_g if g.get("mentions_colombia"))
    print(f"Total positive gradings in this subset: {n_positive}")

    print("\n=== Stage 4: ARS ===")
    if config.get("ars", {}).get("enabled", False):
        print(f"[ars] loading AR from {config['ars']['ar_checkpoint']} ...")
        ar_model, ar_tokenizer = ars._load_ar(config["ars"]["ar_checkpoint"])

        for item in items:
            ars.compute_ars_for_item(item, ar_model, ar_tokenizer, ars.CRITIC_SUFFIX_IDS)

        n_with_ars = sum(1 for it in items for pos_g in it["gradings"].values()
                         for g in pos_g if "ars" in g)
        print(f"OK: {n_with_ars} gradings got an ARS score (should equal the "
             f"{n_positive} positive gradings above)")
        assert n_with_ars == n_positive, "ARS should run on exactly the positive gradings"

        tau = ars.calibrate_threshold(items, percentile=config["ars"]["neutral_percentile"])
        if tau is not None:
            print(f"OK: threshold calibrated at tau={tau:.4f}")
            ars.apply_ars_filter(items, tau)
            n_survived = sum(1 for it in items for pos_g in it["gradings"].values()
                            for g in pos_g if g.get("mentions_colombia_ars_verified"))
            print(f"OK: {n_survived}/{n_positive} positive gradings survived the ARS filter")
        else:
            print("NOTE: no neutral-arm ARS values to calibrate against in this "
                 "small subset (expected with only 2 scenarios) -- this is fine, "
                 "just means the filter step is skipped here.")
    else:
        print("SKIPPED (config.yaml has ars.enabled: false -- "
             "set it to true to test this stage)")

    print("\n=== Stage 5: metric ===")
    D_rows = metric.calculate_D(items, config)
    summary = metric.summary_by_attribute(D_rows)
    assert all("D" in r for r in D_rows), "MISSING D key"
    print(f"OK: {len(D_rows)} D rows calculated")
    for r in D_rows:
        print(f"  {r['group_id']} ({r['language']}): D={r['D']:+.3f}")
    print(f"\nPrimary summary: {summary}")

    if config.get("ars", {}).get("enabled", False):
        ars_ran = any("ars" in g for it in items for g in
                      [x for pos_g in it["gradings"].values() for x in pos_g])
        filter_applied = any("mentions_colombia_ars_verified" in g for it in items
                             for pos_g in it["gradings"].values() for g in pos_g)
        if ars_ran and filter_applied:
            D_rows_ars = metric.calculate_D(
                items, config, label_key="mentions_colombia_ars_verified")
            summary_ars = metric.summary_by_attribute(D_rows_ars)
            print(f"ARS-filtered summary: {summary_ars}")
        elif ars_ran:
            print("NOTE: ARS scores were computed but the threshold couldn't be "
                 "calibrated in this small subset (no neutral-arm mentions) -- "
                 "no ARS-filtered summary to show. This is expected with only "
                 "2 scenarios; the full 120-item run will have enough neutral-arm "
                 "data to calibrate a real threshold.")

    print("\n=== ALL STAGES VALIDATED WITHOUT ERRORS ===")


if __name__ == "__main__":
    main()