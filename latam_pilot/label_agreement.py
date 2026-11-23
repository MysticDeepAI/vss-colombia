#!/usr/bin/env python3
"""Label agreement between two gradings of the SAME explanations (exploratory, secondary).

Used for the two regrades of the exploratory plan: MX/AR main vs regrade (same grader twice) and the
Colombia pilot with the old grader vs the strict grader (layer 20, same AV texts). Checks that the
explanation texts are identical before comparing. Reports, overall and by arm: n, agreement, Cohen's
kappa, how many labels go 0 -> 1 and 1 -> 0, and a few changed explanations to read.

Labels: `mentions_target`, or `mentions_colombia` in the original Colombia pilot. Missing labels
(None) count as 0, as in the metric.

Usage, from the repo root:
  python latam_pilot/label_agreement.py A_stage3.json B_stage3.json --names old,strict \
      --examples 8 --out agreement.md
"""
import argparse
import json
from pathlib import Path


def label(g):
    g = g or {}
    v = g.get("mentions_target", g.get("mentions_colombia"))
    return 1 if v else 0


def pairs(a_items, b_items):
    b_by_id = {it["id"]: it for it in b_items}
    for ia in a_items:
        ib = b_by_id[ia["id"]]
        for pos, texts in ia["explanations"].items():
            assert texts == ib["explanations"][pos], f"explanations differ: {ia['id']} {pos}"
            for j, text in enumerate(texts):
                yield ia, pos, j, text, label(ia["gradings"][pos][j]), label(ib["gradings"][pos][j])


def stats(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    n11 = sum(1 for r in rows if r[4] and r[5])
    n00 = sum(1 for r in rows if not r[4] and not r[5])
    n10 = sum(1 for r in rows if r[4] and not r[5])
    n01 = sum(1 for r in rows if not r[4] and r[5])
    po = (n11 + n00) / n
    pa, pb = (n11 + n10) / n, (n11 + n01) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    return {"n": n, "agree": po, "kappa": kappa, "pos_a": n11 + n10, "pos_b": n11 + n01,
            "a1_b0": n10, "a0_b1": n01}


def to_markdown(rows, names, n_examples):
    a, b = names
    lines = [f"# Label agreement: `{a}` vs `{b}` (same explanations)", "",
             f"| Subset | n | agreement | kappa | positives {a} | positives {b} | 1->0 | 0->1 |",
             "|---|---|---|---|---|---|---|---|"]
    subsets = [("all", rows)] + [(f"arm={arm}", [r for r in rows if r[0]["arm"] == arm])
                                 for arm in sorted({r[0]["arm"] for r in rows})]
    for name, sub in subsets:
        s = stats(sub)
        if s["n"]:
            lines.append(f"| {name} | {s['n']} | {s['agree']:.3f} | {s['kappa']:.3f} | {s['pos_a']} | "
                         f"{s['pos_b']} | {s['a1_b0']} | {s['a0_b1']} |")
    changed = [r for r in rows if r[4] != r[5]]
    if n_examples and changed:
        lines += ["", f"## Changed labels (first {min(n_examples, len(changed))} of {len(changed)})", ""]
        for it, pos, j, text, la, lb in changed[:n_examples]:
            snippet = " ".join(text.split())[:300].replace("|", "/")
            lines.append(f"- `{it['id']}` {it['arm']} {pos} #{j}: {a}={la}, {b}={lb}. {snippet}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--names", default="a,b")
    ap.add_argument("--examples", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rows = list(pairs(json.load(open(args.a, encoding="utf-8")), json.load(open(args.b, encoding="utf-8"))))
    md = to_markdown(rows, args.names.split(","), args.examples)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
