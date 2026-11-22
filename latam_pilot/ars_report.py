#!/usr/bin/env python3
"""Report for the exploratory ARS run (our own ARS on top of the official NLACritic).

Reads a stage-4 JSON written by main.py with ars.enabled (fields `ars`, `ars_control`, `ars_net` on
each verified positive) and writes a markdown report with:

  1. ARS, ARS_control and ARS_net by arm (n, median, quartiles) and the share of positives whose
     quoted claim helps more than removing the same amount of other text (ARS_net > 0).
  2. The percentile sweep fixed in the plan (80, 90, 95 of the NEUTRAL arm's ARS): tau, survivors
     per arm, and the D summary recomputed with only the surviving positives.

Usage, from the repo root:
  python latam_pilot/ars_report.py results/mx_ar_L21_ars/results_stage4.json \
      --out results/mx_ar_L21_ars/ars_report.md
"""
import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.metric import calculate_D, summary_by_attribute  # noqa: E402

PERCENTILES = (80, 90, 95)
LABEL = "mentions_target_ars_sweep"


def _scored(items):
    for it in items:
        for gs in it["gradings"].values():
            for g in gs:
                if "ars" in g:
                    yield it["arm"], g


def describe(values):
    if not values:
        return "n=0"
    q1, med, q3 = np.percentile(values, [25, 50, 75])
    return f"n={len(values)}, median={med:+.4f}, IQR=[{q1:+.4f}, {q3:+.4f}]"


def by_arm(items):
    out = {}
    for arm in ("cue", "neutral"):
        rows = [g for a, g in _scored(items) if a == arm]
        net = [g["ars_net"] for g in rows if "ars_net" in g]
        out[arm] = {
            "ars": describe([g["ars"] for g in rows]),
            "ars_control": describe([g["ars_control"] for g in rows if "ars_control" in g]),
            "ars_net": describe(net),
            "share_net_positive": (sum(1 for v in net if v > 0) / len(net)) if net else None,
        }
    return out


def sweep(items, config):
    neutral = [g["ars"] for a, g in _scored(items) if a == "neutral"]
    results = []
    for pct in PERCENTILES:
        if not neutral:
            results.append({"percentile": pct, "tau": None})
            continue
        tau = float(np.percentile(neutral, pct))
        work = copy.deepcopy(items)
        survivors = {"cue": 0, "neutral": 0}
        for it in work:
            for gs in it["gradings"].values():
                for g in gs:
                    ok = bool(g.get("mentions_target")) and "ars" in g and g["ars"] > tau
                    g[LABEL] = ok
                    if ok:
                        survivors[it["arm"]] += 1
        summary = summary_by_attribute(calculate_D(work, config, label_key=LABEL))
        results.append({"percentile": pct, "tau": tau, "survivors": survivors, "summary": summary})
    return results


def to_markdown(arms, sw):
    lines = ["# ARS report (exploratory; our ARS on the official NLACritic)", "",
             "## Distributions by arm", "", "| Arm | ARS | ARS_control | ARS_net | ARS_net > 0 |",
             "|---|---|---|---|---|"]
    for arm, r in arms.items():
        share = "-" if r["share_net_positive"] is None else f"{r['share_net_positive']:.2f}"
        lines.append(f"| {arm} | {r['ars']} | {r['ars_control']} | {r['ars_net']} | {share} |")
    lines += ["", "## Percentile sweep (threshold from the neutral arm)", "",
              "| Percentile | tau | survivors cue | survivors neutral | attribute | median D | +/=/- | p |",
              "|---|---|---|---|---|---|---|---|"]
    for r in sw:
        if r["tau"] is None:
            lines.append(f"| {r['percentile']} | - | - | - | - | - | - | - |")
            continue
        for attr, s in r["summary"].items():
            lines.append(f"| {r['percentile']} | {r['tau']:+.4f} | {r['survivors']['cue']} | "
                         f"{r['survivors']['neutral']} | {attr} | {s['median_D']:+.3f} | "
                         f"{s['positive']}/{s['zero']}/{s['negative']} | {s['p_value_exact']:.4f} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage4")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    import yaml
    config = yaml.safe_load(open(args.config, encoding="utf-8"))
    items = json.load(open(args.stage4, encoding="utf-8"))
    md = to_markdown(by_arm(items), sweep(items, config))
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
