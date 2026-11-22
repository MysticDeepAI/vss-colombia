#!/usr/bin/env python3
"""Noise report for the exploratory repeats of the MX/AR run (layer 21).

Compares D per pair across several results.json files written by main.py:
  - full repeats (extraction -> AV -> grader): total run-to-run noise;
  - a regrade of the same explanations (--from grading): grader noise only.

For each pair: D in every run, mean, SD and whether the sign changes. Then the counts the plan fixes
in advance: how many pairs change sign, and how often a pair with |D| <= 0.4 in the main run moves by
more than 0.4.

Usage, from the repo root:
  python latam_pilot/noise_report.py \
      --run main=results/mx_ar_L21/results.json \
      --run rep2=results/mx_ar_L21_rep2/results.json \
      --run rep3=results/mx_ar_L21_rep3/results.json \
      --run regrade=results/mx_ar_L21_regrade/results.json \
      --full main,rep2,rep3 --grader-only main,regrade --out noise_report.md
"""
import argparse
import json
from pathlib import Path

import numpy as np

WEAK = 0.4


def load(path):
    rows = json.load(open(path, encoding="utf-8"))["results_D"]
    out = {}
    for r in rows:
        out.setdefault(r["group_id"], []).append(r["D"])
    return {g: float(np.mean(v)) for g, v in out.items()}


def sign(x):
    return 0 if x == 0 else (1 if x > 0 else -1)


def compare(runs, names):
    pairs = sorted(set.intersection(*(set(runs[n]) for n in names)))
    rows, sign_changes, weak_moves, weak_total = [], 0, 0, 0
    main = names[0]
    for p in pairs:
        vals = [runs[n][p] for n in names]
        changed = len({sign(v) for v in vals}) > 1
        sign_changes += changed
        if abs(runs[main][p]) <= WEAK:
            for n in names[1:]:
                weak_total += 1
                weak_moves += abs(runs[n][p] - runs[main][p]) > WEAK
        rows.append((p, vals, float(np.mean(vals)), float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0, changed))
    return {"names": names, "rows": rows, "sign_changes": sign_changes, "n_pairs": len(pairs),
            "weak_moves": weak_moves, "weak_total": weak_total}


def to_markdown(title, c):
    head = "| Pair | " + " | ".join(c["names"]) + " | mean | SD | sign changes |"
    lines = [f"## {title}", "", head, "|" + "---|" * (len(c["names"]) + 4)]
    for p, vals, m, sd, ch in c["rows"]:
        lines.append(f"| {p} | " + " | ".join(f"{v:+.2f}" for v in vals) + f" | {m:+.2f} | {sd:.2f} | {'yes' if ch else ''} |")
    lines += ["", f"Pairs that change sign: {c['sign_changes']} of {c['n_pairs']}.",
              f"Comparisons where a pair with |D| <= {WEAK} in `{c['names'][0]}` moves by more than {WEAK}: "
              f"{c['weak_moves']} of {c['weak_total']}.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="append", required=True, help="name=path/to/results.json")
    ap.add_argument("--full", required=True, help="comma-separated names, main run first")
    ap.add_argument("--grader-only", default=None, help="comma-separated names, main run first")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    runs = {n: load(p) for n, p in (r.split("=", 1) for r in args.run)}
    md = ["# Noise report (exploratory, layer 21)", ""]
    md.append(to_markdown("Full repeats (AV + grader noise)", compare(runs, args.full.split(","))))
    if args.grader_only:
        md.append(to_markdown("Same explanations, graded again (grader noise only)",
                              compare(runs, args.grader_only.split(","))))
    text = "\n".join(md)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
