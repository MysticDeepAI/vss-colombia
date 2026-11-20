"""Blind annotation sheet for the human check of the grader (13 Nov plan, Wed 18 step 4).

Takes a graded results file from the pipeline (items with `explanations` and `gradings`, e.g.
results_stage3.json) and picks the explanations a person will label by hand. One unit = one
explanation text = (prompt, position, sample).

Selection (fixed seed):
  - up to `--max-pos` (50) units the grader marked "yes"; if there are fewer, all of them;
  - the rest are units the grader marked "no", half from the cue arm at positions tw..tw+5
    and half from everything else (tw-1 of either arm, and the neutral arm);
  - if one pool runs short, the other fills the gap.
Everything is shuffled together and numbered U001, U002, ... in sheet order.

Output folder (keep the key closed until the annotation is finished):
  sheet_annotator1.csv  all units: unit_id, target_country, text, label (empty), notes
  sheet_annotator2.csv  the first `--n-second` (40) rows, for the second person
  key.csv               what each unit is (prompt, arm, position, sample), the grader's label,
                        its sampling stratum and weight (used by score_annotations.py)
  key_meta.json         seed, source file and its sha256, pool sizes, counts

The sheets carry no hint of arm, position or grader label. Grader labels that are missing
(unparseable answers) count as "no", the same way src/metric.py counts them.

Usage, from the repo root:
  python latam_pilot/make_blind_sheet.py results/results_stage3.json --out-dir ../human_check \
      --grader-name claude_api --seed 2026
"""
import argparse
import csv
import datetime
import hashlib
import json
import math
import random
import sys
from pathlib import Path

LABEL_FIELDS = ("mentions_target", "mentions_colombia")
COUNTRY_BY_ATTRIBUTE = {"nationality_mx": "México", "nationality_ar": "Argentina"}
COUNTRY_BY_LABEL_FIELD = {"mentions_colombia": "Colombia"}
SHEET_COLUMNS = ["unit_id", "target_country", "text", "label", "notes"]
KEY_COLUMNS = ["unit_id", "item_id", "group_id", "arm", "language", "position", "sample",
               "stratum", "weight", "grader_label", "grader_raw", "grader_quote", "target_country"]
STRATA = ("pos", "neg_cue_window", "neg_other")


def detect_label_field(items):
    for item in items:
        for gradings in (item.get("gradings") or {}).values():
            for g in gradings:
                if isinstance(g, dict):
                    for f in LABEL_FIELDS:
                        if f in g:
                            return f
    raise SystemExit(f"no grader label found (looked for {', '.join(LABEL_FIELDS)})")


def target_country_of(item, label_field, override=None):
    if override:
        return override
    if item.get("target_country"):
        return item["target_country"]
    if item.get("attribute") in COUNTRY_BY_ATTRIBUTE:
        return COUNTRY_BY_ATTRIBUTE[item["attribute"]]
    if label_field in COUNTRY_BY_LABEL_FIELD:
        return COUNTRY_BY_LABEL_FIELD[label_field]
    raise SystemExit(f"cannot tell the target country of {item.get('id')}; pass --target-country")


def load_units(results_path, label_field=None, langs=None, target_country=None):
    """Returns (units, label_field). One unit per explanation text that has a grading."""
    items = json.load(open(results_path, encoding="utf-8"))
    if not isinstance(items, list):
        raise SystemExit(f"{results_path}: expected a list of items (a results_stageN.json file)")
    label_field = label_field or detect_label_field(items)
    units = []
    for item in items:
        if langs and item.get("language") not in langs:
            continue
        explanations = item.get("explanations") or {}
        gradings = item.get("gradings") or {}
        if not explanations or not gradings:
            continue
        country = target_country_of(item, label_field, target_country)
        for position, texts in explanations.items():
            pos_gradings = gradings.get(position) or []
            for k, text in enumerate(texts):
                if not text or k >= len(pos_gradings):
                    continue
                g = pos_gradings[k] or {}
                raw = g.get(label_field)
                units.append({
                    "item_id": item["id"],
                    "group_id": item.get("group_id", ""),
                    "arm": item.get("arm", ""),
                    "language": item.get("language", ""),
                    "position": position,
                    "sample": k,
                    "text": text,
                    "grader_label": 1 if raw else 0,
                    "grader_raw": "null" if raw is None else str(bool(raw)).lower(),
                    "grader_quote": g.get("quote") or "",
                    "target_country": country,
                })
    return units, label_field


def stratum_of(unit):
    if unit["grader_label"] == 1:
        return "pos"
    if unit["arm"] == "cue" and unit["position"] != "tw-1":
        return "neg_cue_window"
    return "neg_other"


def select(units, n_total, max_pos, rng):
    pools = {s: [u for u in units if stratum_of(u) == s] for s in STRATA}
    n_pos = min(max_pos, len(pools["pos"]), n_total)
    n_neg = n_total - n_pos
    n_a = min(math.ceil(n_neg / 2), len(pools["neg_cue_window"]))
    n_b = min(n_neg - n_a, len(pools["neg_other"]))
    n_a = min(n_neg - n_b, len(pools["neg_cue_window"]))
    take = {"pos": n_pos, "neg_cue_window": n_a, "neg_other": n_b}
    chosen = []
    for s in STRATA:
        picked = rng.sample(pools[s], take[s])
        weight = len(pools[s]) / take[s] if take[s] else 0.0
        for u in picked:
            chosen.append({**u, "stratum": s, "weight": weight})
    rng.shuffle(chosen)
    for i, u in enumerate(chosen, 1):
        u["unit_id"] = f"U{i:03d}"
    pool_sizes = {s: len(pools[s]) for s in STRATA}
    return chosen, pool_sizes, take


def write_csv(path, columns, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_ALL, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", help="graded results file (list of items with explanations + gradings)")
    ap.add_argument("--out-dir", required=True, help="folder for the sheets and the key (kept out of git)")
    ap.add_argument("--grader-name", default="claude_api", help="name of the grader whose labels drive the sampling")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--n", type=int, default=100, help="units on the sheet")
    ap.add_argument("--max-pos", type=int, default=50, help="most grader-'yes' units to include")
    ap.add_argument("--n-second", type=int, default=40, help="rows for the second annotator")
    ap.add_argument("--langs", default=None, help="comma list, e.g. es (default: all)")
    ap.add_argument("--label-field", default=None, help="default: mentions_target or mentions_colombia")
    ap.add_argument("--target-country", default=None, help="force one target country for every unit")
    ap.add_argument("--force", action="store_true", help="overwrite an existing key in --out-dir")
    args = ap.parse_args(argv)

    out = Path(args.out_dir)
    if (out / "key.csv").exists() and not args.force:
        raise SystemExit(f"{out / 'key.csv'} already exists; a new sheet would replace it. Use --force if you mean it.")
    langs = set(args.langs.split(",")) if args.langs else None

    units, label_field = load_units(args.results, args.label_field, langs, args.target_country)
    if not units:
        raise SystemExit("no graded explanations found")
    rng = random.Random(args.seed)
    chosen, pool_sizes, take = select(units, args.n, args.max_pos, rng)

    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "sheet_annotator1.csv", SHEET_COLUMNS, chosen)
    write_csv(out / "sheet_annotator2.csv", SHEET_COLUMNS, chosen[:args.n_second])
    write_csv(out / "key.csv", KEY_COLUMNS, chosen)
    meta = {
        "created": datetime.date.today().isoformat(),
        "results_file": str(args.results),
        "results_sha256": sha256_of(args.results),
        "grader_name": args.grader_name,
        "label_field": label_field,
        "seed": args.seed,
        "n": len(chosen),
        "max_pos": args.max_pos,
        "n_second": min(args.n_second, len(chosen)),
        "langs": sorted(langs) if langs else "all",
        "units_in_run": len(units),
        "pool_sizes": pool_sizes,
        "sampled": take,
    }
    (out / "key_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{len(units)} graded explanations in the run ({label_field}, grader {args.grader_name}).")
    for s in STRATA:
        print(f"  {s:15s} pool {pool_sizes[s]:5d}  -> on the sheet {take[s]:3d}")
    if len(chosen) < args.n:
        print(f"WARNING: only {len(chosen)} units available, fewer than {args.n}.")
    if take["pos"] < args.max_pos:
        print(f"Note: only {take['pos']} grader-'yes' units exist, all of them are on the sheet.")
    print(f"Wrote {out}/sheet_annotator1.csv ({len(chosen)} rows), sheet_annotator2.csv "
          f"({meta['n_second']} rows), key.csv, key_meta.json.")
    print("Do not open key.csv until both annotators are done.")


if __name__ == "__main__":
    main()
