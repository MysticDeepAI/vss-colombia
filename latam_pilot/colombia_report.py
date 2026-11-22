#!/usr/bin/env python3
"""Report for the Colombia 2x2 (layer x grader) of the exploratory plan, section 3.

Each cell is a results.json written by main.py. The summary is recomputed from `results_D` with
src.metric.summary_by_attribute, so every cell goes through the same code. Writes, per attribute,
median D, +/=/- and p in each cell, the D of each scenario side by side, and the robustness rule fixed
in the plan: nationality keeps median D > 0 and p < 0.05 in all three cells.

Usage, from the repo root:
  python latam_pilot/colombia_report.py \
      --cell L20_old=results/results.json \
      --cell L20_strict=results/colombia_L20_strict/results.json \
      --cell L21_strict=results/colombia_L21_strict/results.json \
      --out colombia_report.md
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.metric import summary_by_attribute  # noqa: E402


def load(path):
    rows = json.load(open(path, encoding="utf-8"))["results_D"]
    per_scenario = {}
    for r in rows:
        per_scenario.setdefault((r["attribute"], r["group_id"]), []).append(r["D"])
    return summary_by_attribute(rows), {k: float(np.mean(v)) for k, v in per_scenario.items()}


def robust(summaries):
    return all(s.get("nationality", {}).get("median_D", 0) > 0
               and s.get("nationality", {}).get("p_value_exact", 1) < 0.05 for s in summaries.values())


def to_markdown(cells):
    names = list(cells)
    lines = ["# Colombia 2x2 (exploratory): layer and grader", "",
             "| Attribute | Cell | median D | +/=/- | p |", "|---|---|---|---|---|"]
    attrs = sorted({a for s, _ in cells.values() for a in s})
    for a in attrs:
        for n in names:
            s = cells[n][0].get(a)
            if s:
                lines.append(f"| {a} | {n} | {s['median_D']:+.3f} | {s['positive']}/{s['zero']}/{s['negative']} "
                             f"| {s['p_value_exact']:.4f} |")
    lines += ["", "## D per scenario (mean over languages)", "",
              "| Attribute | Scenario | " + " | ".join(names) + " |", "|" + "---|" * (len(names) + 2)]
    keys = sorted(set.union(*(set(d) for _, d in cells.values())))
    for a, g in keys:
        vals = [cells[n][1].get((a, g)) for n in names]
        lines.append(f"| {a} | {g} | " + " | ".join("-" if v is None else f"{v:+.2f}" for v in vals) + " |")
    verdict = robust({n: s for n, (s, _) in cells.items()})
    lines += ["", f"Nationality median D > 0 and p < 0.05 in every cell: **{'yes' if verdict else 'no'}**.", ""]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cell", action="append", required=True, help="name=path/to/results.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cells = {n: load(p) for n, p in (c.split("=", 1) for c in args.cell)}
    md = to_markdown(cells)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
