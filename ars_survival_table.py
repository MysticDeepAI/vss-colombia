#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ars_survival_table.py -- generates the ARS mention-survival table, in
English, in the same style as the other result tables from
plot_results.py (a CSV to paste into the paper, plus a console preview).

Reports, per attribute: how many grader-flagged positive mentions were
ARS-checked, how many survived the confabulation filter, and the
survival rate -- the table that supports the ARS paragraph in the post.

The threshold tau is RECOMPUTED from the data (same calibration as the
pipeline: Nth percentile of ARS values on the neutral arm, pooled across
all attributes -- a single global threshold, not one per attribute),
rather than hardcoded, so the table stays correct if the underlying run
changes.

Usage:
    python3 ars_survival_table.py --input results/results_stage4.json \
        --percentile 90 --outdir results/figures
"""

import argparse
import json
import os

import numpy as np
import pandas as pd


def calibrate_tau(items, percentile):
    """Same calibration as src/ars.py's calibrate_threshold(): the Nth
    percentile of ARS values on the neutral arm, pooled across all
    attributes -- by design, no genuine Colombian content should be
    there, so any 'necessity' the AR assigns is noise floor."""
    neutral_ars = [
        g["ars"]
        for item in items if item["arm"] == "neutral"
        for gradings in item["gradings"].values()
        for g in gradings if "ars" in g
    ]
    if not neutral_ars:
        return None
    return float(np.percentile(neutral_ars, percentile))


def build_table(items):
    rows = []
    for attribute in sorted({it["attribute"] for it in items}):
        n_flagged = 0
        n_survived = 0
        for item in items:
            if item["attribute"] != attribute:
                continue
            for gradings in item["gradings"].values():
                for g in gradings:
                    if g.get("mentions_colombia") and g.get("quote_verified") and "ars" in g:
                        n_flagged += 1
                        if g.get("mentions_colombia_ars_verified"):
                            n_survived += 1
        survival_rate = n_survived / n_flagged if n_flagged else float("nan")
        rows.append({
            "Attribute": attribute,
            "Mentions flagged": n_flagged,
            "Survived ARS filter": n_survived,
            "Survival rate": survival_rate,
        })
    return pd.DataFrame(rows).set_index("Attribute")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="results/results_stage4.json")
    ap.add_argument("--percentile", type=float, default=90)
    ap.add_argument("--outdir", default="results/figures")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        items = json.load(f)

    tau = calibrate_tau(items, args.percentile)
    df = build_table(items)

    os.makedirs(args.outdir, exist_ok=True)
    csv_path = os.path.join(args.outdir, "ars_survival_table.csv")
    df.to_csv(csv_path, float_format="%.3f")

    print(f"Threshold tau ({args.percentile:.0f}th percentile of neutral-arm "
         f"ARS values): {tau:.4f}\n")
    print(df.to_string(formatters={"Survival rate": lambda v: f"{v:.1%}"}))
    print(f"\n-> saved to {csv_path}")

    print("\n--- Markdown, ready to paste into the post ---")
    df_md = df.copy()
    df_md["Survival rate"] = df_md["Survival rate"].apply(lambda v: f"{v:.0%}")
    print(df_md.to_markdown())


if __name__ == "__main__":
    main()