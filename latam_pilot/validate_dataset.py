"""validate_dataset.py - machine checks for minimal pairs (dataset schema v2.2).

Rewrite of the pilot's missing validator (protocol step 3). Reproduces the `qa` block of the pilot's
30 pairs (see test_reproduce_pilot_qa.py). Words = whitespace-separated tokens, punctuation attached,
exact (case-sensitive) comparison; word indices are 0-based.

Checks (criteria C1, C3, C4 of dataset v2.2):
  C1  single_span   cue and neutral arms differ in exactly ONE contiguous block of words.
  C3  span_start    that block starts at word index >= 10.
  C4  length ratio  cue/neutral word-count ratio within +-20% (0.8 .. 1.2).
hard_fail = any of the three fails, or the two arms are identical.
Warnings (never fail, need a human look): keyword not found in its arm, target country named in the
cue arm, span is a pure insertion/deletion (one arm's span empty).

Usage:
  python validate_dataset.py PAIRS.json [--lang es] [--report out.json]
Exit code 1 if any pair has hard_fail.
Input format: v2.2 JSON, {"pairs":[{"id", "keyword":{cue_es, neutral_es}, "prompts":{"es":{cue, neutral}},
"target_country" (optional)}]}.
"""
import argparse
import difflib
import json
import sys
from pathlib import Path

MIN_START = 10          # C3: span must start at word index >= 10
MAX_LEN_DEVIATION = 0.20  # C4: |cue - neutral| / neutral <= 0.20


def words(text: str):
    return text.split()


def check_arms(cue: str, neutral: str) -> dict:
    a, b = words(cue), words(neutral)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    diffs = [op for op in sm.get_opcodes() if op[0] != "equal"]
    identical = not diffs
    # canonical span = what is left after stripping the common prefix and suffix
    p = 0
    while p < min(len(a), len(b)) and a[p] == b[p]:
        p += 1
    s = 0
    while s < min(len(a), len(b)) - p and a[-1 - s] == b[-1 - s]:
        s += 1
    span_cue = " ".join(a[p:len(a) - s])
    span_neu = " ".join(b[p:len(b) - s])
    single = len(diffs) == 1
    ratio_dev = abs(len(a) - len(b)) / len(b) if b else float("inf")
    return {
        "single_span": single,
        "span_cue": span_cue,
        "span_neutral": span_neu,
        "span_start_word_index": None if identical else p,
        "cue_word_count": len(a),
        "neutral_word_count": len(b),
        "cue_neutral_word_ratio": round(len(a) / len(b), 3) if b else None,
        "identical": identical,
        "_ratio_dev": ratio_dev,
    }


def validate_pair(pair: dict, lang: str = "es") -> dict:
    arms = pair["prompts"][lang]
    r = check_arms(arms["cue"], arms["neutral"])
    fails, warnings = [], []
    if r["identical"]:
        fails.append("arms identical")
    else:
        if not r["single_span"]:
            fails.append("C1: arms differ in more than one block of words")
        if r["span_start_word_index"] < MIN_START:
            fails.append(f"C3: span starts at word {r['span_start_word_index']} (< {MIN_START})")
    if r["_ratio_dev"] > MAX_LEN_DEVIATION:
        fails.append(f"C4: word counts {r['cue_word_count']} vs {r['neutral_word_count']} differ by more than 20%")
    if not r["identical"] and (not r["span_cue"] or not r["span_neutral"]):
        warnings.append("span is a pure insertion/deletion (one arm has no words in the span)")
    kw = pair.get("keyword", {})
    if kw.get(f"cue_{lang}") and kw[f"cue_{lang}"] not in arms["cue"]:
        warnings.append(f"keyword.cue_{lang} not found in the cue prompt")
    if kw.get(f"neutral_{lang}") and kw[f"neutral_{lang}"] not in arms["neutral"]:
        warnings.append(f"keyword.neutral_{lang} not found in the neutral prompt")
    tc = pair.get("target_country")
    if tc and tc.lower() in arms["cue"].lower():
        warnings.append(f"target country '{tc}' is named in the cue prompt (C6: cue must not name the country)")
    r.pop("_ratio_dev")
    r.pop("identical")
    r["hard_fail"] = bool(fails)
    r["fails"] = fails
    r["warnings"] = warnings
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pairs_json")
    ap.add_argument("--lang", default="es")
    ap.add_argument("--report")
    args = ap.parse_args()
    data = json.loads(Path(args.pairs_json).read_text(encoding="utf-8"))
    report = {}
    for pair in data["pairs"]:
        report[pair["id"]] = validate_pair(pair, args.lang)
    bad = 0
    for pid, r in report.items():
        flag = "FAIL" if r["hard_fail"] else "ok"
        bad += r["hard_fail"]
        print(f"{pid:6s} {flag:5s} start={r['span_start_word_index']} "
              f"words={r['cue_word_count']}/{r['neutral_word_count']} "
              f"span='{r['span_cue']}' | '{r['span_neutral']}'")
        for m in r["fails"] + r["warnings"]:
            print(f"         - {m}")
    print(f"\n{len(report)} pairs, {bad} hard_fail")
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
