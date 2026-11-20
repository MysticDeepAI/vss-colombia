"""validate_pairs.py - machine checks for minimal pairs (dataset schema v2.2), rules of the 13 Nov plan.

Usage (from the repo root):
  python latam_pilot/validate_pairs.py PAIRS.json [--ids N01,N02] [--langs es] [--write] [--report out.json]

Each pair is checked in every language it has (the keys of `prompts`), or only in --langs.
--write stores each checked pair's result as its `qa` block, back in PAIRS.json.
Exit code 1 if any checked pair has hard_fail.

Words = whitespace-separated tokens, punctuation attached; word indices are 0-based.

Hard fails
  (a) single span  cue and neutral differ in exactly one contiguous stretch of words (difflib).
  (b) position     that stretch starts at word index >= 10.
  (c) keyword      each arm's keyword (keyword.cue_<lang> / keyword.neutral_<lang>) appears exactly once
                   in that arm's prompt, as whole words (case-sensitive).
  (d) giveaway     neither arm names a country, a nationality word or a region word (latino,
                   latinoamericano, hispano, ...). Accents are ignored. Country names must be capitalised
                   to count, so "chile" (the pepper) and "cuba" pass while "Chile" and "Cuba" fail.
                   The plan only asks for the cue arm; the neutral arm is checked too.
                   Exception from the pilot design (criterion C6): a non-nationality pair with
                   risks.explicit_country = true gets a warning instead.
  (e) schema       the v2.2 fields are present and non-empty.
Warnings (never fail)
  - the changed stretch is more than twice as long (in words) on one side as on the other;
  - pure insertion/deletion (one side's changed stretch is empty).
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

MIN_START = 10          # (b)
SPAN_RATIO_WARN = 2.0   # warning when one changed stretch is more than 2x the other (in words)

# ---------------------------------------------------------------- (d) giveaway words
# Matched on accent-stripped text: "México" = "Mexico", "nicaragüense" = "nicaraguense".
# Country names are case-sensitive ("chile" the pepper, "cuba" the vat, "usa" the verb are fine).
COUNTRY_NAMES = [
    "Argentina", "Bolivia", "Brasil", "Brazil", "Chile", "Colombia", "Costa Rica", "Cuba", "Ecuador",
    "El Salvador", "Espana", "Spain", "Estados Unidos", "United States", "USA", "Guatemala", "Honduras",
    "Mexico", "Mejico", "Nicaragua", "Panama", "Paraguay", "Peru", "Puerto Rico", "Republica Dominicana",
    "Dominican Republic", "Uruguay", "Venezuela", "Guinea Ecuatorial", "Equatorial Guinea",
]
# Nationality words, any case. Stems take any ending (mexicano/a/os/as, Mexican, ...).
NATIONALITY_STEMS = [
    "mexican", "mejican", "argentin", "colombian", "chilen", "chilean", "peruan", "peruvian",
    "venezolan", "venezuelan", "bolivian", "ecuatorian", "ecuadorian", "ecuadorean", "paraguay",
    "uruguay", "cuban", "dominican", "puertorriquen", "portorriquen", "salvadoren", "salvadoran",
    "guatemaltec", "guatemalan", "hondure", "honduran", "nicaraguens", "nicaraguan", "costarricens",
    "costarriquen", "panamen", "panamanian", "brasilen", "brasiler", "brazilian", "estadounidens",
    "norteamerican", "ecuatoguinean",
]
NATIONALITY_WORDS = [  # whole words, any case
    r"espanol(?:a|es|as)?", r"spaniards?", r"spanish", r"americans?", r"gring[oa]s?", r"yanquis?",
    r"yankees?", r"tic[oa]s?", r"nicas?", r"chapin(?:a|es|as)?", r"catrach[oa]s?", r"boricuas?",
    r"puerto\s+ricans?", r"costa\s+ricans?",
]
REGION_WORDS = [  # any case
    r"latin\w*", r"hispan\w*", r"(?:ibero|sud|sur|centro|meso|norte)\s?americ\w*",
    r"america\s+(?:latina|del\s+sur|central)", r"(?:south|central|north)\s+america\w*",
    r"caribe[n]\w*", r"caribbean", r"andin[oa]s?", r"andean", r"rioplatens\w*",
]
COUNTRY_RE = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(c) for c in COUNTRY_NAMES) + r"|EE\.?\s?UU\.?)(?!\w)")
WORDS_RE = re.compile(
    r"(?<!\w)(?:" + "|".join([s + r"\w*" for s in NATIONALITY_STEMS] + NATIONALITY_WORDS + REGION_WORDS)
    + r")(?!\w)", re.IGNORECASE)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize("NFC", "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn"))


def find_giveaways(text: str) -> list:
    plain = strip_accents(text)
    hits = [m.group(0) for m in COUNTRY_RE.finditer(plain)] + [m.group(0) for m in WORDS_RE.finditer(plain)]
    return sorted(set(hits))


# ---------------------------------------------------------------- (c) keyword
def count_whole(phrase: str, text: str) -> int:
    return len(re.findall(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


# ---------------------------------------------------------------- (a), (b) changed stretch
def check_arms(cue: str, neutral: str) -> dict:
    a, b = cue.split(), neutral.split()
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    diffs = [op for op in sm.get_opcodes() if op[0] != "equal"]
    # the changed stretch = what is left after removing the common start and the common end
    p = 0
    while p < min(len(a), len(b)) and a[p] == b[p]:
        p += 1
    s = 0
    while s < min(len(a), len(b)) - p and a[-1 - s] == b[-1 - s]:
        s += 1
    identical = not diffs
    return {
        "single_span": len(diffs) == 1,
        "span_cue": " ".join(a[p:len(a) - s]),
        "span_neutral": " ".join(b[p:len(b) - s]),
        "span_start_word_index": None if identical else p,
        "cue_word_count": len(a),
        "neutral_word_count": len(b),
        "identical": identical,
    }


# ---------------------------------------------------------------- (e) schema v2.2
TOP_FIELDS = ("id", "attribute", "scenario", "cue_type", "expected_mechanism")
KEYWORD_FIELDS = ("pos", "semantic_field")
RISK_TEXT_FIELDS = ("neutral_association", "cue_ambiguity")
RISK_FLAG_FIELDS = ("coactivation_flag", "explicit_country")


def _text(x) -> bool:
    return isinstance(x, str) and x.strip() != ""


def schema_problems(pair: dict, langs: list) -> list:
    out = [f"'{f}' missing or empty" for f in TOP_FIELDS if not _text(pair.get(f))]
    kw = pair.get("keyword") if isinstance(pair.get("keyword"), dict) else {}
    risks = pair.get("risks") if isinstance(pair.get("risks"), dict) else {}
    prompts = pair.get("prompts") if isinstance(pair.get("prompts"), dict) else {}
    out += [f"'keyword.{f}' missing or empty" for f in KEYWORD_FIELDS if not _text(kw.get(f))]
    out += [f"'risks.{f}' missing or empty" for f in RISK_TEXT_FIELDS if not _text(risks.get(f))]
    out += [f"'risks.{f}' must be true/false" for f in RISK_FLAG_FIELDS if not isinstance(risks.get(f), bool)]
    if not prompts:
        out.append("'prompts' missing or empty")
    for lang in langs:
        arms = prompts.get(lang) if isinstance(prompts.get(lang), dict) else {}
        for arm in ("cue", "neutral"):
            if not _text(arms.get(arm)):
                out.append(f"'prompts.{lang}.{arm}' missing or empty")
            if not _text(kw.get(f"{arm}_{lang}")):
                out.append(f"'keyword.{arm}_{lang}' missing or empty")
    return out


# ---------------------------------------------------------------- one pair
def validate_pair(pair: dict, langs: list = None) -> dict:
    """Return the pair's qa block: per-language measurements, then fails, warnings, hard_fail."""
    prompts = pair.get("prompts") if isinstance(pair.get("prompts"), dict) else {}
    kw = pair.get("keyword") if isinstance(pair.get("keyword"), dict) else {}
    langs = list(langs) if langs else list(prompts)
    fails = [f"(e) {p}" for p in schema_problems(pair, langs)]
    warnings = []
    risks = pair.get("risks") if isinstance(pair.get("risks"), dict) else {}
    country_allowed = (not str(pair.get("attribute", "")).startswith("nationality")
                       and risks.get("explicit_country") is True)
    qa = {"validator": "validate_pairs.py"}

    for lang in langs:
        arms = prompts.get(lang) if isinstance(prompts.get(lang), dict) else {}
        if not (_text(arms.get("cue")) and _text(arms.get("neutral"))):
            continue  # already reported under (e)
        r = check_arms(arms["cue"], arms["neutral"])
        for k in ("single_span", "span_cue", "span_neutral", "span_start_word_index",
                  "cue_word_count", "neutral_word_count"):
            qa[f"{lang}_{k}"] = r[k]

        if r["identical"]:
            fails.append(f"(a) {lang}: cue and neutral are identical")
        else:
            if not r["single_span"]:
                fails.append(f"(a) {lang}: cue and neutral differ in more than one stretch of words")
            if r["span_start_word_index"] < MIN_START:
                fails.append(f"(b) {lang}: the changed stretch starts at word {r['span_start_word_index']} "
                             f"(must be {MIN_START} or later)")
            n_cue, n_neu = len(r["span_cue"].split()), len(r["span_neutral"].split())
            if n_cue == 0 or n_neu == 0:
                warnings.append(f"{lang}: pure insertion/deletion (one side's changed stretch is empty)")
            elif max(n_cue, n_neu) > SPAN_RATIO_WARN * min(n_cue, n_neu):
                warnings.append(f"{lang}: changed stretch is {n_cue} words in cue vs {n_neu} in neutral "
                                f"(more than {SPAN_RATIO_WARN:g}x)")

        for arm in ("cue", "neutral"):
            phrase = kw.get(f"{arm}_{lang}")
            if _text(phrase):
                n = count_whole(phrase, arms[arm])
                qa[f"{lang}_keyword_count_{arm}"] = n
                if n != 1:
                    fails.append(f"(c) {lang}: keyword.{arm}_{lang} '{phrase}' appears {n} times as whole "
                                 f"words in the {arm} prompt (must be exactly 1)")

        giveaways = {arm: find_giveaways(arms[arm]) for arm in ("cue", "neutral")}
        qa[f"{lang}_giveaways"] = giveaways
        for arm, hits in giveaways.items():
            if not hits:
                continue
            msg = f"(d) {lang}: the {arm} prompt names a country, nationality or region: {', '.join(hits)}"
            if country_allowed:
                warnings.append(msg + " (allowed: non-nationality pair with risks.explicit_country)")
            else:
                fails.append(msg)

    qa["fails"] = fails
    qa["warnings"] = warnings
    qa["hard_fail"] = bool(fails)
    return qa


# ---------------------------------------------------------------- command line
def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="Machine checks for minimal pairs (schema v2.2).")
    ap.add_argument("pairs_json")
    ap.add_argument("--ids", help="comma-separated pair ids to check (default: all)")
    ap.add_argument("--langs", help="comma-separated languages to check (default: every language a pair has)")
    ap.add_argument("--write", action="store_true", help="store each checked pair's qa block in PAIRS.json")
    ap.add_argument("--report", help="also save all qa blocks to this JSON file")
    args = ap.parse_args()

    path = Path(args.pairs_json)
    raw = path.read_bytes().decode("utf-8")
    data = json.loads(raw)
    ids = args.ids.split(",") if args.ids else None
    langs = args.langs.split(",") if args.langs else None
    pairs = [p for p in data["pairs"] if ids is None or p.get("id") in ids]
    if ids:
        unknown = sorted(set(ids) - {p.get("id") for p in pairs})
        if unknown:
            sys.exit(f"unknown pair ids: {', '.join(unknown)}")

    report, n_fail = {}, 0
    for pair in pairs:
        pid = pair.get("id", "?")
        qa = validate_pair(pair, langs)
        report[pid] = qa
        n_fail += qa["hard_fail"]
        spans = "  ".join(f"{lang}: start={qa.get(f'{lang}_span_start_word_index')} "
                          f"'{qa.get(f'{lang}_span_cue')}' | '{qa.get(f'{lang}_span_neutral')}'"
                          for lang in (langs or list(pair.get("prompts") or {})))
        print(f"{pid:6s} {'FAIL' if qa['hard_fail'] else 'ok':4s}  {spans}")
        for m in qa["fails"]:
            print(f"         FAIL  {m}")
        for m in qa["warnings"]:
            print(f"         warn  {m}")
        if args.write:
            pair["qa"] = qa
    print(f"\n{len(pairs)} pairs checked, {n_fail} with hard_fail")

    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write:
        newline = "\r\n" if "\r\n" in raw else "\n"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline=newline)
        print(f"qa blocks written to {path}")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
