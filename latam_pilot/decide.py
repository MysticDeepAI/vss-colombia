#!/usr/bin/env python3
"""Applies the decision rule fixed before the run (13 Nov plan) to the D values of the mini-pilot.

Primary test: exact one-sided sign-permutation test on the pooled D values of the 10 pairs
(5 Mexico + 5 Argentina), zeros dropped (src/metric.py:exact_permutation_test).

  SUCCESS  p < 0.05, at least 3 of 5 pairs with D > 0 in each country, and no country with a
           negative median D
  PARTIAL  p < 0.05 but one of the other two conditions fails
  FAILURE  p >= 0.05

Contingency (decided in advance): if 6 or more of the 10 D values are exactly 0, the mention rate
is too coarse at K = 5 and the run is repeated with K = 10.

The Colombia pilot is shown for context only (--anchor results/results.json) and is never pooled
into the test.

Usage, from the repo root:
  python latam_pilot/decide.py results/mx_ar/results.json --out results/mx_ar/decision.md \
      --anchor results/results.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.metric import exact_permutation_test  # noqa: E402

ALPHA = 0.05
MIN_POSITIVE_PER_COUNTRY = 3
ZERO_LIMIT = 6
COUNTRY_BY_PREFIX = {"MX": "México", "AR": "Argentina"}


def decide(D_rows):
    """D_rows: the `results_D` list written by main.py. Pure function (no files)."""
    by_pair = {}
    for r in D_rows:
        by_pair.setdefault(r["group_id"], []).append(r["D"])
    D_bar = {g: float(np.mean(v)) for g, v in by_pair.items()}  # one value per pair

    countries = {}
    for g, d in D_bar.items():
        countries.setdefault(COUNTRY_BY_PREFIX.get(g[:2], g[:2]), {})[g] = d

    p, n_eff = exact_permutation_test(list(D_bar.values()), alternative="greater")
    per_country = {}
    for c, pairs in sorted(countries.items()):
        vals = list(pairs.values())
        per_country[c] = {"n": len(vals), "median_D": float(np.median(vals)),
                          "positive": sum(v > 0 for v in vals), "zero": sum(v == 0 for v in vals),
                          "negative": sum(v < 0 for v in vals), "pairs": pairs}

    enough_positive = all(v["positive"] >= MIN_POSITIVE_PER_COUNTRY for v in per_country.values())
    no_negative_median = all(v["median_D"] >= 0 for v in per_country.values())
    n_zero = sum(1 for v in D_bar.values() if v == 0)
    if p < ALPHA and enough_positive and no_negative_median:
        verdict = "SUCCESS"
    elif p < ALPHA:
        verdict = "PARTIAL"
    else:
        verdict = "FAILURE"
    return {"verdict": verdict, "p_value_exact": p, "n_pairs": len(D_bar), "n_effective": n_eff,
            "pooled_median_D": float(np.median(list(D_bar.values()))), "n_zero": n_zero,
            "repeat_with_K10": n_zero >= ZERO_LIMIT, "enough_positive_per_country": enough_positive,
            "no_negative_country_median": no_negative_median, "per_country": per_country}


def to_markdown(res, anchor=None):
    lines = [f"# Decision: {res['verdict']}", "",
             f"Pooled exact one-sided permutation test over {res['n_pairs']} pairs "
             f"({res['n_effective']} non-zero): p = {res['p_value_exact']:.5f}. "
             f"Pooled median D = {res['pooled_median_D']:+.3f}.", "",
             "| Country | n | median D | positive | zero | negative |", "|---|---|---|---|---|---|"]
    for c, v in res["per_country"].items():
        lines.append(f"| {c} | {v['n']} | {v['median_D']:+.3f} | {v['positive']} | {v['zero']} | {v['negative']} |")
    lines += ["", "D per pair: " + ", ".join(
        f"{g} {d:+.2f}" for v in res["per_country"].values() for g, d in v["pairs"].items()), "",
        f"Conditions: p < {ALPHA}: {res['p_value_exact'] < ALPHA}; at least "
        f"{MIN_POSITIVE_PER_COUNTRY} positive pairs in each country: {res['enough_positive_per_country']}; "
        f"no negative country median: {res['no_negative_country_median']}."]
    if res["repeat_with_K10"]:
        lines += ["", f"{res['n_zero']} of {res['n_pairs']} D values are zero (limit {ZERO_LIMIT}): "
                      "repeat the run with sampling.k_samples = 10."]
    if anchor:
        lines += ["", "Colombia pilot, for context only (not pooled): " + anchor]
    return "\n".join(lines) + "\n"


def anchor_text(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    s = data.get("summary_by_attribute", {}).get("nationality")
    if not s:
        return None
    return (f"nationality median D = {s['median_D']:+.2f}, {s['positive']} of {s['n_scenarios']} "
            f"positive, exact p = {s['p_value_exact']}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("results", help="results.json written by main.py")
    ap.add_argument("--out", default=None, help="where to write decision.md")
    ap.add_argument("--anchor", default=None, help="Colombia pilot results.json, context only")
    args = ap.parse_args()

    data = json.loads(Path(args.results).read_text(encoding="utf-8"))
    res = decide(data["results_D"])
    md = to_markdown(res, anchor_text(args.anchor) if args.anchor else None)
    print(md)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        Path(args.out).with_suffix(".json").write_text(json.dumps(res, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
