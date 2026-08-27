# src/metric.py
"""
Stage 5: metric computation.

What it does: from the 0/1 gradings per position and sample, computes,
for each prompt:

    s_t = (positive mentions at position t) / K

And for each (cue, neutral) pair of the same scenario and language:

    Delta      = max(s_t over the post-keyword window) - s at tw-1
    D          = Delta_cue - Delta_neutral

The neutral arm absorbs the AV's own confabulation rate for that
language/template, so D isolates the effect attributable to the keyword.

It also runs the exact statistical test (sign permutation) over the D
values by scenario -- see the docstring of `exact_permutation_test` for
the full explanation of why this test and not a classic t-test.

LABEL_KEY: every function here takes an optional `label_key` parameter
(default "mentions_colombia", the raw grader label). This lets the exact
same pipeline compute D and the summary using a DIFFERENT label, such as
"mentions_colombia_ars_verified" (Stage 4's ARS filter) -- so the primary
result and the ARS-filtered sensitivity check both come from one code
path, not two.
"""

import itertools

import numpy as np

DEFAULT_LABEL_KEY = "mentions_colombia"


def _mention_rate(position_gradings, label_key=DEFAULT_LABEL_KEY):
    """From a list of K gradings, returns the fraction where `label_key`
    came back True. None/missing counts as no mention (failed grading,
    or -- for the ARS label -- a mention that was never ARS-checked
    because it wasn't positive in the first place)."""
    positives = sum(1 for g in position_gradings if g.get(label_key))
    return positives / len(position_gradings)


def calculate_delta(item, post_positions, label_key=DEFAULT_LABEL_KEY):
    """Delta = max(s_t over the post-keyword window) - s at tw-1, for ONE
    prompt."""
    rates = {pos: _mention_rate(g, label_key) for pos, g in item["gradings"].items()}
    s_pre = rates.get("tw-1", 0.0)  # if the keyword was at position 0, there's no "before"
    post_names = ["tw"] + [f"tw+{k}" for k in range(1, post_positions + 1)]
    post_values = [rates[p] for p in post_names if p in rates]
    return max(post_values) - s_pre, rates


def calculate_D(items, config, label_key=DEFAULT_LABEL_KEY):
    """Groups by (group_id, language), pairs cue with neutral, and
    computes D = Delta_cue - Delta_neutral per scenario and language.

    Returns a list of rows ready for tabulation:
        [{"group_id": "N01", "language": "es", "D": 0.42, ...}, ...]
    """
    post_positions = config["window"]["post_positions"]

    # separate by (group_id, language, arm) to be able to pair them up
    by_key = {}
    for item in items:
        delta, rates = calculate_delta(item, post_positions, label_key)
        key = (item["group_id"], item["language"], item["arm"])
        by_key[key] = {"delta": delta, "rates": rates, "attribute": item["attribute"]}

    rows = []
    groups = {(g, l) for (g, l, _) in by_key}
    for group_id, lang in sorted(groups):
        cue = by_key.get((group_id, lang, "cue"))
        neutral = by_key.get((group_id, lang, "neutral"))
        if cue is None or neutral is None:
            continue  # missing an arm -- can't compute D for this pair
        rows.append({
            "group_id": group_id,
            "language": lang,
            "attribute": cue["attribute"],
            "cue_delta": round(cue["delta"], 4),
            "neutral_delta": round(neutral["delta"], 4),
            "D": round(cue["delta"] - neutral["delta"], 4),
            "cue_rates": cue["rates"],
            "neutral_rates": neutral["rates"],
        })
    return rows


def exact_permutation_test(D_values, alternative="greater"):
    """Exact sign-permutation test against H0: median(D) = 0.

    Why this test and not a t-test: with n=10 scenarios (this
    experiment's size), a t-test assumes the data comes from a normal
    distribution, an assumption that can't be verified or justified with
    so few data points. The permutation test doesn't need that
    assumption: if the keyword had no effect at all, each D would have
    the same probability of coming out positive or negative (like a fair
    coin). We enumerate ALL 2^n possible ways of assigning signs to the
    absolute values of D, and count in how many of those 2^n "coin flips"
    the result is at least as extreme as what was observed. Exact, no
    approximations.

    D_values: list/array of D values (one per scenario -- if there's an
              ES and EN version of the same scenario, average them BEFORE
              calling this function, to avoid counting the same scenario
              twice).
    alternative: "greater" (H1: median > 0, the one matching this design,
                 since the direction was predicted in advance) or
                 "two-sided".

    Returns: (p_value, n_effective) -- n_effective excludes exact zeros,
    which contribute no evidence in either direction.
    """
    d = np.asarray(D_values, dtype=float)
    d = d[d != 0]  # zeros neither add nor subtract evidence -- dropped
    n = len(d)
    if n == 0:
        return float("nan"), 0

    observed = d.mean()
    signs = np.array(list(itertools.product((1.0, -1.0), repeat=n)))
    null_distribution = (signs * np.abs(d)).mean(axis=1)

    if alternative == "greater":
        p = np.mean(null_distribution >= observed - 1e-12)
    else:
        p = np.mean(np.abs(null_distribution) >= abs(observed) - 1e-12)
    return float(p), n


def summary_by_attribute(D_rows):
    """Averages D across languages per scenario (D_bar), runs the exact
    test per attribute, and builds the final table that gets saved in the
    results JSON and used by plot_results.py for the figures."""
    summary = {}
    for attribute in sorted({r["attribute"] for r in D_rows}):
        sub = [r for r in D_rows if r["attribute"] == attribute]
        by_scenario = {}
        for r in sub:
            by_scenario.setdefault(r["group_id"], []).append(r["D"])
        D_bar = [np.mean(vals) for vals in by_scenario.values()]

        p, n_effective = exact_permutation_test(D_bar, alternative="greater")
        summary[attribute] = {
            "n_scenarios": len(D_bar),
            "n_effective": n_effective,
            "median_D": round(float(np.median(D_bar)), 4),
            "positive": int(sum(1 for v in D_bar if v > 0)),
            "zero": int(sum(1 for v in D_bar if v == 0)),
            "negative": int(sum(1 for v in D_bar if v < 0)),
            "p_value_exact": round(p, 5),
        }
    return summary
