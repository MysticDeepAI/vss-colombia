"""Secondary interval for the grader's weighted precision and recall (human check, 2026-11-23).

score_annotations.py reports a Wilson interval whenever every row in the denominator has the same
weight. For recall that hides most of the uncertainty: the denominator (rows annotator 1 marked 1)
can sit entirely in the `pos` stratum, while the grader's misses are estimated from the two "no"
pools, of which only 25 + 25 rows were read. With 0 misses observed, Wilson gives an interval near
[0.92, 1.00] that does not account for those pools at all.

Here each stratum gets a Jeffreys posterior, Beta(k + 0.5, n - k + 0.5), for the share of rows that
annotator 1 marked 1, and the run-level counts are rebuilt from the pool sizes in key_meta.json:

    precision = share in `pos`
    recall    = P_pos * share_pos / sum over strata of (P_s * share_s)

This is a reading aid next to the pre-registered numbers; it does not replace them.

Usage, from the repo root:
  python latam_pilot/human_check_bayes.py --key-dir ../human_check --annotator1 sheet_annotator1_done.csv
"""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_blind_sheet import STRATA  # noqa: E402
from score_annotations import THRESHOLDS, read_key, read_labels  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key-dir", required=True)
    ap.add_argument("--annotator1", required=True)
    ap.add_argument("--draws", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    key, meta = read_key(args.key_dir)
    ids = [r["unit_id"] for r in key]
    h1 = read_labels(args.annotator1, set(ids), require_all_of=ids)
    counts = {s: [0, 0] for s in STRATA}  # [human 1, rows]
    for r in key:
        counts[r["stratum"]][0] += h1[r["unit_id"]]
        counts[r["stratum"]][1] += 1
    pools = meta["pool_sizes"]

    rng = random.Random(args.seed)
    prec, rec = [], []
    for _ in range(args.draws):
        share = {s: rng.betavariate(k + 0.5, n - k + 0.5) for s, (k, n) in counts.items() if n}
        tp = pools["pos"] * share["pos"]
        prec.append(share["pos"])
        rec.append(tp / sum(pools[s] * share[s] for s in share))
    out = {}
    for name, v in (("precision", prec), ("recall", rec)):
        v.sort()
        n = len(v)
        out[name] = (v[n // 2], v[int(0.025 * n)], v[int(0.975 * n)],
                     sum(x >= THRESHOLDS[name] for x in v) / n)
    print("strata (annotator 1 = 1 / rows): " + ", ".join(f"{s} {k}/{n}" for s, (k, n) in counts.items()))
    for name, (med, lo, hi, p) in out.items():
        print(f"{name:9s} median {med:.3f}  95% [{lo:.3f}, {hi:.3f}]  P(>= {THRESHOLDS[name]}) = {p:.2f}")
    return out


if __name__ == "__main__":
    main()
