#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py -- entry point for the VSS Colombia experiment.

Runs the 4 stages in order and saves the final result in
results/results.json (the exact path comes from config.yaml). This file
contains NO business logic -- each stage lives in its own module inside
src/, and here they're only called in order, saving progress as it comes
in. Deliberately simple so it's easy to read top to bottom.

Usage:
    python main.py                   # runs all 4 stages
    python main.py --to extraction   # stops after Stage 1
                                      # (useful to review activations
                                      # before spending time on the AV)
    python main.py --from grading --input results/partial.json
                                      # resumes from a partial JSON already
                                      # saved, without repeating extraction
                                      # or verbalization

Once it finishes, run separately:
    python plot_results.py
to generate figures from results/results.json.
"""

import argparse
import json

import yaml

from src import ars, extraction, grading, metric, verbalization

STAGES = ["extraction", "verbalization", "grading", "ars", "metric"]


def load_config(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_dataset(config):
    """Flattens the minimal-pairs JSON (30 pairs x 2 languages x 2 arms)
    into a flat list of 120 individual prompts, the format the stages in
    src/ expect."""
    with open(config["paths"]["dataset"], encoding="utf-8") as f:
        data = json.load(f)

    items = []
    for pair in data["pairs"]:
        for language in ("es", "en"):
            for arm in ("cue", "neutral"):
                items.append({
                    "id": f"{pair['id']}_{arm}_{language}",
                    "group_id": pair["id"],
                    "arm": arm,
                    "language": language,
                    "attribute": pair["attribute"],
                    "keyword": pair["keyword"][f"{arm}_{language}"],
                    "prompt": pair["prompts"][language][arm],
                })
    return items


def save_json(data, path):
    """Saves to disk after each stage -- if something fails later, the
    already-completed work isn't lost. numpy arrays aren't directly JSON
    serializable, so they're converted to lists before saving."""

    def convert(obj):
        if hasattr(obj, "tolist"):
            return obj.tolist()
        raise TypeError(f"Don't know how to serialize: {type(obj)}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=convert)
    print(f"  -> saved to {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--from", dest="from_stage", choices=STAGES, default="extraction",
                        help="stage to start from (default: from the beginning)")
    parser.add_argument("--to", dest="to_stage", choices=STAGES, default="metric",
                        help="stage to stop at (default: through the end)")
    parser.add_argument("--input", default=None,
                        help="partial JSON from a previous run, required "
                             "if --from is not 'extraction'")
    args = parser.parse_args()

    config = load_config(args.config)
    from_idx = STAGES.index(args.from_stage)
    to_idx = STAGES.index(args.to_stage)

    # --- Stage 1: extraction --------------------------------------------
    if from_idx <= 0:
        print("\n=== Stage 1/5: activation extraction ===")
        items = load_dataset(config)
        items = extraction.extract_activations(items, config)
        save_json(items, config["paths"]["results"].replace(".json", "_stage1.json"))
    else:
        assert args.input, "--input is required if not starting from extraction"
        with open(args.input, encoding="utf-8") as f:
            items = json.load(f)

    if to_idx == 0:
        return

    # --- Stage 2: verbalization ------------------------------------------
    if from_idx <= 1:
        print("\n=== Stage 2/5: verbalization (AV) ===")
        items = verbalization.verbalize(items, config)
        save_json(items, config["paths"]["results"].replace(".json", "_stage2.json"))

    if to_idx == 1:
        return

    # --- Stage 3: grading --------------------------------------------------
    if from_idx <= 2:
        print("\n=== Stage 3/5: grading ===")
        items = grading.grade(items, config)
        save_json(items, config["paths"]["results"].replace(".json", "_stage3.json"))

    if to_idx == 2:
        return

    # --- Stage 4: ARS (optional) --------------------------------------------
    if from_idx <= 3:
        if config.get("ars", {}).get("enabled", False):
            print("\n=== Stage 4/5: ARS (AR-verified salience) ===")
            ar_checkpoint_id = config["ars"]["ar_checkpoint"]
            layer_index = config["ars"]["layer_index"]
            print(f"[ars] loading AR from {ar_checkpoint_id} ...")
            ar_model, ar_tokenizer = ars._load_ar(ar_checkpoint_id)

            for i, item in enumerate(items, 1):
                ars.compute_ars_for_item(item, ar_model, ar_tokenizer,
                                         ars.CRITIC_SUFFIX_IDS)
                if i % 20 == 0 or i == len(items):
                    print(f"  [{i}/{len(items)}] items ARS-checked")

            tau = ars.calibrate_threshold(
                items, percentile=config["ars"]["neutral_percentile"])
            print(f"[ars] threshold calibrated at the "
                 f"{config['ars']['neutral_percentile']}th percentile "
                 f"of the neutral arm: tau={tau:.4f}" if tau is not None else
                 "[ars] no neutral-arm ARS values to calibrate against -- "
                 "skipping the filter (raw ars scores are still saved).")
            if tau is not None:
                ars.apply_ars_filter(items, tau)
            print("[ars] done.")
        else:
            print("\n=== Stage 4/5: ARS -- SKIPPED (ars.enabled: false in config.yaml) ===")
        save_json(items, config["paths"]["results"].replace(".json", "_stage4.json"))

    if to_idx == 3:
        return

    # --- Stage 5: metric and statistics -------------------------------------
    print("\n=== Stage 5/5: metric computation ===")
    D_rows = metric.calculate_D(items, config)  # primary: raw grader label
    summary = metric.summary_by_attribute(D_rows)

    final_result = {
        "config": config,
        "results_D": D_rows,
        "summary_by_attribute": summary,
    }

    ars_was_run = any("ars" in g for it in items
                      for position_gradings in it["gradings"].values()
                      for g in position_gradings)
    ars_filter_applied = any("mentions_colombia_ars_verified" in g for it in items
                             for position_gradings in it["gradings"].values()
                             for g in position_gradings)
    if ars_was_run and ars_filter_applied:
        print("\n--- ARS-filtered sensitivity check ---")
        D_rows_ars = metric.calculate_D(
            items, config, label_key="mentions_colombia_ars_verified")
        summary_ars = metric.summary_by_attribute(D_rows_ars)
        final_result["results_D_ars_filtered"] = D_rows_ars
        final_result["summary_by_attribute_ars_filtered"] = summary_ars
        for attribute, r in summary_ars.items():
            print(f"  {attribute:12s}  median D (ARS-filtered)={r['median_D']:+.3f}  "
                 f"p={r['p_value_exact']:.4f}")

    save_json(final_result, config["paths"]["results"])

    print("\n=== Summary (primary) ===")
    for attribute, r in summary.items():
        print(f"  {attribute:12s}  median D={r['median_D']:+.3f}  "
              f"({r['positive']}+/{r['zero']}=/{r['negative']}-)  "
              f"p={r['p_value_exact']:.4f}")

    print(f"\nDone. Now run: python plot_results.py")


if __name__ == "__main__":
    main()