"""Scores the human check of the grader (13 Nov plan, Thu 19 step 3).

Inputs: the folder made by make_blind_sheet.py (key.csv + key_meta.json) and the filled sheets.
Annotators write 1 or 0 in the `label` column. The files can come back from Excel or Google
Sheets as comma-, semicolon- or tab-separated CSV.

Reports:
  - Cohen's kappa between annotator 1 and annotator 2 on the rows both labelled (the 40);
  - for each grader, against annotator 1: confusion table, precision and recall;
  - the 10 most informative grader-vs-human disagreements, and every human-vs-human one;
  - the thresholds fixed in the plan: kappa >= 0.70, precision >= 0.90, recall >= 0.80.

Why two sets of numbers: the sheet over-samples the grader's "yes" answers (up to half the
sheet, far more than in the run). Raw numbers describe only the rows on the sheet; raw recall
is too optimistic, because the grader's misses sit in the large "no" pool that is barely
sampled. The weighted numbers give each row the weight of the pool it was drawn from, so they
estimate the whole run, and the thresholds are checked on them. Intervals are 95%: Wilson when
all rows in the count have the same weight (a plain proportion), otherwise a stratified
bootstrap.

The sampling grader's labels come from key.csv. Other graders that labelled the same
explanations (e.g. qwen_local on the same results_stage2.json) are added with
--grader NAME=PATH to their graded results file.

Usage, from the repo root:
  python latam_pilot/score_annotations.py --key-dir ../human_check \
      --annotator1 ../human_check/sheet_annotator1_done.csv \
      --annotator2 ../human_check/sheet_annotator2_done.csv \
      --grader qwen_local=results_qwen/results_stage3.json --out-dir results/human_check
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_blind_sheet import STRATA, load_units  # noqa: E402

Z95 = 1.959963984540054
THRESHOLDS = {"kappa": 0.70, "precision": 0.90, "recall": 0.80}
VALID = {"1": 1, "0": 0, "1.0": 1, "0.0": 0}


# ---------- statistics ----------

def wilson(k, n, z=Z95):
    if n == 0:
        return None, None
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def cohen_kappa(a, b):
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe == 1:
        return 1.0 if po == 1 else None
    return (po - pe) / (1 - pe)


def weighted_ratio(rows, num, den):
    d = sum(r["weight"] for r in rows if den(r))
    if d == 0:
        return None
    return sum(r["weight"] for r in rows if den(r) and num(r)) / d


def metric_with_ci(rows, num, den, n_boot, rng):
    """Weighted estimate + 95% interval, plus the raw (unweighted) count."""
    den_rows = [r for r in rows if den(r)]
    k_raw = sum(1 for r in den_rows if num(r))
    n_raw = len(den_rows)
    est = weighted_ratio(rows, num, den)
    if est is None:
        return {"raw": None, "raw_k": 0, "raw_n": 0, "weighted": None, "ci": [None, None], "ci_method": "none"}
    if len({round(r["weight"], 9) for r in den_rows}) == 1:
        lo, hi = wilson(k_raw, n_raw)
        method = "Wilson"
    else:
        by_stratum = {s: [r for r in rows if r["stratum"] == s] for s in STRATA}
        reps = []
        for _ in range(n_boot):
            sample = []
            for s_rows in by_stratum.values():
                if s_rows:
                    sample.extend(rng.choices(s_rows, k=len(s_rows)))
            v = weighted_ratio(sample, num, den)
            if v is not None:
                reps.append(v)
        reps.sort()
        lo = reps[int(0.025 * (len(reps) - 1))] if reps else None
        hi = reps[int(0.975 * (len(reps) - 1))] if reps else None
        method = f"stratified bootstrap ({len(reps)} reps)"
    return {"raw": k_raw / n_raw if n_raw else None, "raw_k": k_raw, "raw_n": n_raw,
            "weighted": est, "ci": [lo, hi], "ci_method": method}


# ---------- input ----------

def read_csv_rows(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    header = text.splitlines()[0] if text else ""
    delim = max([",", ";", "\t"], key=header.count)
    return list(csv.DictReader(text.splitlines(keepends=True), delimiter=delim))


def read_labels(path, known_ids, require_all_of=None):
    rows = read_csv_rows(path)
    if rows and ("unit_id" not in rows[0] or "label" not in rows[0]):
        raise SystemExit(f"{path}: needs the columns unit_id and label")
    labels, bad, unknown = {}, [], []
    for r in rows:
        uid = (r.get("unit_id") or "").strip()
        if not uid:
            continue
        if uid not in known_ids:
            unknown.append(uid)
            continue
        v = (r.get("label") or "").strip()
        if v not in VALID:
            bad.append(f"{uid} ({v!r})" if v else f"{uid} (empty)")
            continue
        labels[uid] = VALID[v]
    problems = []
    if bad:
        problems.append(f"label must be 1 or 0: {', '.join(bad)}")
    if unknown:
        problems.append(f"unit_id not in the key: {', '.join(unknown)}")
    if require_all_of:
        missing = sorted(set(require_all_of) - set(labels) - {b.split()[0] for b in bad})
        if missing:
            problems.append(f"rows missing: {', '.join(missing)}")
    if problems:
        raise SystemExit(f"{path}:\n  " + "\n  ".join(problems))
    return labels


def read_key(key_dir):
    key_dir = Path(key_dir)
    meta = json.loads((key_dir / "key_meta.json").read_text(encoding="utf-8"))
    rows = read_csv_rows(key_dir / "key.csv")
    for r in rows:
        r["weight"] = float(r["weight"])
        r["sample"] = int(r["sample"])
        r["grader_label"] = int(r["grader_label"])
    return rows, meta


def grader_labels_from_results(path, key_rows):
    units, _ = load_units(path)  # label field detected in that file
    lookup = {(u["item_id"], u["position"], u["sample"]): u["grader_label"] for u in units}
    out, missing = {}, []
    for r in key_rows:
        k = (r["item_id"], r["position"], r["sample"])
        if k not in lookup:
            missing.append(r["unit_id"])
        else:
            out[r["unit_id"]] = lookup[k]
    if missing:
        raise SystemExit(f"{path}: no grading for {len(missing)} sheet units (e.g. {missing[:5]}); "
                         "was it graded on the same explanations?")
    return out


# ---------- report ----------

def fmt(x):
    return "n/a" if x is None else f"{x:.3f}"


def fmt_ci(ci):
    return "n/a" if ci[0] is None else f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def disagreement_rank(r):
    # most informative first: errors in the cue window move D directly (false "yes" inflates it,
    # missed "yes" shrinks it); then errors in the baseline (tw-1 / neutral); heavier rows first.
    in_window = r["arm"] == "cue" and r["position"] != "tw-1"
    false_yes = r["pred"] == 1
    return (0 if in_window else 1, 0 if false_yes else 1, -r["weight"], r["unit_id"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key-dir", required=True)
    ap.add_argument("--annotator1", required=True, help="filled sheet of annotator 1 (all rows)")
    ap.add_argument("--annotator2", default=None, help="filled sheet of annotator 2 (the shared rows)")
    ap.add_argument("--grader", action="append", default=[], metavar="NAME=PATH",
                    help="another grader's results file on the same explanations (repeatable)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-disagreements", type=int, default=10)
    args = ap.parse_args(argv)

    key, meta = read_key(args.key_dir)
    by_id = {r["unit_id"]: r for r in key}
    sheet = Path(args.key_dir) / "sheet_annotator1.csv"
    texts = {r["unit_id"]: r.get("text", "") for r in read_csv_rows(sheet if sheet.exists() else args.annotator1)}
    for uid, r in by_id.items():
        r["text"] = texts.get(uid, "")
    ids = list(by_id)
    h1 = read_labels(args.annotator1, by_id, require_all_of=ids)
    h2 = read_labels(args.annotator2, by_id) if args.annotator2 else {}

    graders = {meta.get("grader_name", "grader"): {r["unit_id"]: r["grader_label"] for r in key}}
    for spec in args.grader:
        if "=" not in spec:
            raise SystemExit(f"--grader expects NAME=PATH, got {spec!r}")
        name, path = spec.split("=", 1)
        graders[name] = grader_labels_from_results(path, key)

    rng = random.Random(args.seed)
    result = {"key_meta": meta, "n_units": len(key), "thresholds": THRESHOLDS, "graders": {}}
    lines = ["# Human check of the grader", "",
             f"Sheet: {len(key)} units from `{meta['results_file']}` (seed {meta['seed']}), "
             f"sampled on the labels of **{meta.get('grader_name')}**. "
             f"Truth = annotator 1. Thresholds fixed in advance: kappa >= {THRESHOLDS['kappa']}, "
             f"precision >= {THRESHOLDS['precision']}, recall >= {THRESHOLDS['recall']}.", "",
             "Pools in the run -> rows on the sheet: " +
             ", ".join(f"{s} {meta['pool_sizes'][s]} -> {meta['sampled'][s]}" for s in STRATA) + ".", ""]

    # agreement between the two people
    shared = [u for u in ids if u in h2]
    kappa = cohen_kappa([h1[u] for u in shared], [h2[u] for u in shared]) if shared else None
    agree = sum(h1[u] == h2[u] for u in shared)
    result["kappa"] = {"value": kappa, "n_shared": len(shared), "agreements": agree,
                       "meets_threshold": None if kappa is None else kappa >= THRESHOLDS["kappa"]}
    lines += ["## Annotator agreement", ""]
    if shared:
        lines += [f"Cohen's kappa on {len(shared)} shared rows: **{fmt(kappa)}** "
                  f"({agree}/{len(shared)} same label; threshold {THRESHOLDS['kappa']}: "
                  f"{'met' if kappa is not None and kappa >= THRESHOLDS['kappa'] else 'NOT met'}).", ""]
    else:
        lines += ["No annotator 2 file given, kappa not computed.", ""]

    # each grader against annotator 1
    for name, pred in graders.items():
        rows = [{**by_id[u], "truth": h1[u], "pred": pred[u]} for u in ids]
        tp = sum(r["pred"] == 1 and r["truth"] == 1 for r in rows)
        fp = sum(r["pred"] == 1 and r["truth"] == 0 for r in rows)
        fn = sum(r["pred"] == 0 and r["truth"] == 1 for r in rows)
        tn = sum(r["pred"] == 0 and r["truth"] == 0 for r in rows)
        prec = metric_with_ci(rows, lambda r: r["truth"] == 1, lambda r: r["pred"] == 1, args.bootstrap, rng)
        rec = metric_with_ci(rows, lambda r: r["pred"] == 1, lambda r: r["truth"] == 1, args.bootstrap, rng)
        res = {"confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, "precision": prec, "recall": rec}
        for m, v in (("precision", prec), ("recall", rec)):
            res[m]["meets_threshold"] = None if v["weighted"] is None else v["weighted"] >= THRESHOLDS[m]
        result["graders"][name] = res

        lines += [f"## Grader: {name}", "",
                  "|                | human yes | human no |",
                  "|----------------|-----------|----------|",
                  f"| grader yes     | {tp:9d} | {fp:8d} |",
                  f"| grader no      | {fn:9d} | {tn:8d} |", "",
                  "| metric | on the sheet (raw) | whole run (weighted) | 95% interval | threshold |",
                  "|--------|--------------------|----------------------|--------------|-----------|"]
        for m, v in (("precision", prec), ("recall", rec)):
            met = "n/a" if v["meets_threshold"] is None else ("met" if v["meets_threshold"] else "NOT met")
            lines.append(f"| {m} | {fmt(v['raw'])} ({v['raw_k']}/{v['raw_n']}) | {fmt(v['weighted'])} | "
                         f"{fmt_ci(v['ci'])} ({v['ci_method']}) | {THRESHOLDS[m]} {met} |")
        lines.append("")

        wrong = sorted([r for r in rows if r["pred"] != r["truth"]], key=disagreement_rank)
        res["n_disagreements"] = len(wrong)
        res["top_disagreements"] = [
            {k: r[k] for k in ("unit_id", "item_id", "arm", "position", "sample", "stratum",
                               "pred", "truth", "grader_quote", "text")} for r in wrong[:args.n_disagreements]]
        lines += [f"### {min(len(wrong), args.n_disagreements)} most informative of {len(wrong)} disagreements "
                  f"({name} vs annotator 1)", ""]
        for r in wrong[:args.n_disagreements]:
            kind = "grader yes, human no" if r["pred"] == 1 else "grader no, human yes"
            lines += [f"- **{r['unit_id']}** {r['item_id']} {r['position']} sample {r['sample']} - {kind}"
                      + (f" - grader quote: \"{r['grader_quote']}\"" if r["grader_quote"] else ""),
                      f"  > {' '.join(r['text'].split())}", ""]

    # human-vs-human disagreements
    hh = [u for u in shared if h1[u] != h2[u]]
    result["human_disagreements"] = [{"unit_id": u, "annotator1": h1[u], "annotator2": h2[u],
                                      "text": by_id[u]["text"]} for u in hh]
    if shared:
        lines += [f"## Annotator 1 vs annotator 2: {len(hh)} disagreements", ""]
        for u in hh:
            lines += [f"- **{u}** annotator 1 = {h1[u]}, annotator 2 = {h2[u]}",
                      f"  > {' '.join(by_id[u]['text'].split())}", ""]

    lines += ["## How to read this", "",
              "The sheet over-samples the grader's \"yes\" answers, so raw recall on the sheet is too optimistic. "
              "The weighted column estimates the whole run and is the one checked against the thresholds. "
              "With about 100 rows the intervals are wide; report them next to the numbers.", ""]

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "human_check_report.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "human_check_metrics.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"kappa: {fmt(kappa)} on {len(shared)} shared rows")
    for name, res in result["graders"].items():
        for m in ("precision", "recall"):
            v = res[m]
            print(f"{name:12s} {m:9s} raw {fmt(v['raw'])}  weighted {fmt(v['weighted'])}  {fmt_ci(v['ci'])}")
    print(f"Wrote {out / 'human_check_report.md'} and {out / 'human_check_metrics.json'}")
    return result


if __name__ == "__main__":
    main()
