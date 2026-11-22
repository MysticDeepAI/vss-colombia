#!/usr/bin/env python3
"""Grades again only the explanations whose grader call failed (api_error), in place.

For runs where the API failed part of the way (e.g. no credit left), so the rest of the labels are kept
and only the missing ones cost API calls. Same prompt, model and keyword rule as src/grading.py. Labels
that the grader did return (including not_parseable) are left as they are.

Writes the stage-3 JSON back to the same path, after saving the original next to it as
*_before_regrade.json. Then recompute the metric with:
  python main.py --config <config> --from ars --input <stage3>

Usage, from the repo root:
  python latam_pilot/regrade_failed.py --config latam_pilot/configs/colombia_L21_strict.yaml \
      --input results/colombia_L21_strict/results_stage3.json
"""
import argparse
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.grading import build_prompt, _grade_with_claude  # noqa: E402

MAX_CHARS = 800  # same trim as src/grading.py


def failed_entries(items):
    for item in items:
        for pos, gs in item["gradings"].items():
            for i, g in enumerate(gs):
                if (g or {}).get("error", "").startswith("api_error"):
                    yield item, pos, i, item["explanations"][pos][i]


def regrade(items, config, client, workers=8):
    rule = config["grader"].get("keyword_rule", "strict")
    model_name = config["grader"]["claude_model"]
    todo = list(failed_entries(items))

    def one(entry):
        item, pos, i, text = entry
        prompt = build_prompt(item.get("target", "Colombia"), rule, text[:MAX_CHARS])
        return entry, _grade_with_claude(prompt, text[:MAX_CHARS], client, model_name)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n, fut in enumerate(as_completed([pool.submit(one, e) for e in todo]), 1):
            (item, pos, i, _), result = fut.result()
            item["gradings"][pos][i] = result
            if n % 50 == 0 or n == len(todo):
                print(f"  [{n}/{len(todo)}] regraded")
    return len(todo)


def count_missing(items):
    return sum(1 for it in items for gs in it["gradings"].values() for g in gs
               if g.get("mentions_target") is None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True)
    ap.add_argument("--input", required=True, help="stage-3 JSON written by main.py")
    args = ap.parse_args()
    config = yaml.safe_load(open(args.config, encoding="utf-8"))
    path = Path(args.input)
    items = json.load(open(path, encoding="utf-8"))
    total = sum(len(gs) for it in items for gs in it["gradings"].values())
    print(f"[regrade_failed] {count_missing(items)}/{total} without a label before")

    backup = path.with_name(path.stem + "_before_regrade.json")
    if not backup.exists():
        shutil.copyfile(path, backup)

    import anthropic
    n = regrade(items, config, anthropic.Anthropic(max_retries=5),
                workers=max(1, int(config["grader"].get("max_workers", 1))))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    print(f"[regrade_failed] regraded {n}; {count_missing(items)}/{total} without a label after")


if __name__ == "__main__":
    main()
