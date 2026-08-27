#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_results.py -- generates figures from results/results.json.

Deliberately separate from main.py: running the full pipeline (hours,
needs a GPU) and generating figures (seconds, only needs the JSON) are
two different tasks. This lets you, for example, tweak a figure's style
without rerunning the experiment -- or generate figures on a laptop with
no GPU from the JSON produced on the cluster.

Usage:
    python plot_results.py                          # uses config.yaml
    python plot_results.py --input other_run.json    # a different file
    python plot_results.py --outdir draft_figures/   # a different output folder
"""

import argparse
import json
import os

import matplotlib.pyplot as plt
import pandas as pd
import yaml

POSITION_ORDER = ["tw-1", "tw", "tw+1", "tw+2", "tw+3", "tw+4", "tw+5"]
X_AXIS_LABELS = ["t$_w$-1", "t$_w$", "+1", "+2", "+3", "+4", "+5"]


def load_results(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def positional_curves_figure(data, outdir):
    """One row of plots, one per attribute: mean Colombia-mention rate
    (s_t) at each window position, split by cue vs. neutral arm and
    Spanish vs. English. This is the experiment's central figure: it
    shows where and how much the representation lights up."""
    rows = data["results_D"]
    attributes = sorted({r["attribute"] for r in rows})

    # flatten cue_rates / neutral_rates into a long dataframe for easy averaging
    records = []
    for r in rows:
        for arm, rates in (("cue", r["cue_rates"]), ("neutral", r["neutral_rates"])):
            for pos, value in rates.items():
                records.append({"attribute": r["attribute"], "language": r["language"],
                                "arm": arm, "pos": pos, "s_t": value})
    df = pd.DataFrame(records)

    fig, axes = plt.subplots(1, len(attributes), figsize=(4.3 * len(attributes), 4),
                             sharey=True)
    if len(attributes) == 1:
        axes = [axes]

    styles = {
        ("cue", "es"): ("#B08D3C", "-", "o", "ES cue"),
        ("neutral", "es"): ("#B08D3C", "--", "s", "ES neutral"),
        ("cue", "en"): ("#555555", "-", "o", "EN cue"),
        ("neutral", "en"): ("#555555", "--", "s", "EN neutral"),
    }

    for ax, attribute in zip(axes, attributes):
        for (arm, language), (color, style, marker, label) in styles.items():
            sub = df[(df.attribute == attribute) & (df.arm == arm) & (df.language == language)]
            mean = sub.groupby("pos")["s_t"].mean().reindex(POSITION_ORDER)
            ax.plot(range(7), mean.values, style, color=color, marker=marker,
                   markersize=5, linewidth=1.8, label=label)
        ax.set_title(attribute)
        ax.set_xticks(range(7))
        ax.set_xticklabels(X_AXIS_LABELS)
        ax.grid(alpha=0.25)

    axes[0].set_ylabel("Mean Colombia-mention rate (s$_t$)")
    axes[len(axes) // 2].set_xlabel("Position relative to the keyword")
    axes[-1].legend(loc="upper right", fontsize=8)
    fig.suptitle("Positional curves by attribute", y=1.02)
    plt.tight_layout()

    path = os.path.join(outdir, "positional_curves.png")
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {path}")


def D_by_scenario_figure(data, outdir):
    """A simple forest plot: each scenario's D value, sorted, with a
    vertical line at 0. Lets you see at a glance how many pairs came out
    positive, how many negative, and whether there's any outlier."""
    rows = data["results_D"]
    df = pd.DataFrame(rows)
    attributes = sorted(df["attribute"].unique())

    fig, axes = plt.subplots(1, len(attributes), figsize=(4 * len(attributes), 5), sharex=True)
    if len(attributes) == 1:
        axes = [axes]

    for ax, attribute in zip(axes, attributes):
        sub = df[df.attribute == attribute].sort_values("D")
        labels = sub["group_id"] + " (" + sub["language"] + ")"
        colors = ["#2E7D32" if d > 0 else ("#C62828" if d < 0 else "#999999") for d in sub["D"]]
        ax.barh(labels, sub["D"], color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(attribute)
        ax.set_xlabel("D (cue - neutral)")

    plt.tight_layout()
    path = os.path.join(outdir, "D_by_scenario.png")
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {path}")


def summary_table(data, outdir):
    """Saves summary_by_attribute (already computed in main.py's Stage 4)
    as a CSV, ready to paste into the paper or the post."""
    summary = data["summary_by_attribute"]
    df = pd.DataFrame(summary).T
    df.index.name = "attribute"
    path = os.path.join(outdir, "summary_table.csv")
    df.to_csv(path)
    print(f"  -> {path}")
    print("\n" + df.to_string())


def ars_comparison_table(data, outdir):
    """If Stage 4 (ARS) ran, saves a side-by-side comparison of the
    primary result (raw grader label) against the ARS-filtered one --
    this is the sensitivity check for confabulation. Does nothing if ARS
    wasn't enabled for this run (keeps plot_results.py working the same
    on runs with or without it)."""
    if "summary_by_attribute_ars_filtered" not in data:
        return False

    primary = data["summary_by_attribute"]
    ars_filtered = data["summary_by_attribute_ars_filtered"]

    rows = []
    for attribute in sorted(primary.keys()):
        p, a = primary[attribute], ars_filtered.get(attribute, {})
        rows.append({
            "attribute": attribute,
            "median_D_primary": p.get("median_D"),
            "p_primary": p.get("p_value_exact"),
            "median_D_ars_filtered": a.get("median_D"),
            "p_ars_filtered": a.get("p_value_exact"),
        })
    df = pd.DataFrame(rows).set_index("attribute")
    path = os.path.join(outdir, "ars_comparison_table.csv")
    df.to_csv(path)
    print(f"  -> {path}")
    print("\n--- Primary vs. ARS-filtered (sensitivity check) ---")
    print(df.to_string())
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--input", default=None,
                        help="path to the results JSON (default: the one in config.yaml)")
    parser.add_argument("--outdir", default=None,
                        help="output folder (default: the one in config.yaml)")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    input_path = args.input or config["paths"]["results"]
    outdir = args.outdir or config["paths"]["figures_dir"]
    os.makedirs(outdir, exist_ok=True)

    print(f"Reading {input_path} ...")
    data = load_results(input_path)

    print("\nGenerating figures:")
    positional_curves_figure(data, outdir)
    D_by_scenario_figure(data, outdir)
    summary_table(data, outdir)
    ars_comparison_table(data, outdir)

    print(f"\nDone. Everything in {outdir}/")


if __name__ == "__main__":
    main()
