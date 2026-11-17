"""Tests for validate_pairs.py. Run from latam_pilot/: python test_validate_pairs.py

1. The 10 nationality pairs of the Colombia pilot (N01-N10, Spanish) pass with no hard_fail (plan, step 7).
2. The changed-stretch numbers still match the qa blocks stored in all 30 pilot pairs (es and en).
3. A made-up good pair passes, and one broken copy per rule fails on that rule.
"""
import copy
import json
import sys
from pathlib import Path

from validate_pairs import validate_pair

HERE = Path(__file__).resolve().parent
PILOT = json.loads((HERE.parent / "dataset" / "minimal_pairs.json").read_text(encoding="utf-8"))["pairs"]

START = "Ayer salí tarde del trabajo y en la esquina de mi casa compré"   # 13 words
END = "para cenar. ¿Qué bebida me recomiendas para acompañarlos?"


def make_pair(cue_kw="unos tacos al pastor", neutral_kw="unos sándwiches de pollo", start=START, end=END,
              attribute="nationality_mx"):
    return {
        "id": "TEST", "attribute": attribute, "scenario": "dinner bought on the way home",
        "cue_type": "lexical-culinary",
        "keyword": {"cue_es": cue_kw, "neutral_es": neutral_kw, "pos": "NP, direct object",
                    "semantic_field": "dinner food"},
        "expected_mechanism": "test pair",
        "risks": {"neutral_association": "low", "cue_ambiguity": "low",
                  "coactivation_flag": False, "explicit_country": False},
        "prompts": {"es": {"cue": f"{start} {cue_kw} {end}", "neutral": f"{start} {neutral_kw} {end}"}},
    }


def fails_on(qa, rule):
    return any(f.startswith(f"({rule})") for f in qa["fails"])


# ---------------------------------------------------------------- pilot data
def test_pilot_nationality_pairs_pass():
    bad = {}
    for pair in PILOT:
        if pair["id"] in {f"N{i:02d}" for i in range(1, 11)}:
            qa = validate_pair(pair, ["es"])
            if qa["hard_fail"]:
                bad[pair["id"]] = qa["fails"]
    assert not bad, bad


def test_pilot_spans_match_stored_qa():
    mismatches = []
    for pair in PILOT:
        for lang in ("es", "en"):
            qa = validate_pair(pair, [lang])
            for k in ("single_span", "span_cue", "span_neutral", "span_start_word_index",
                      "cue_word_count", "neutral_word_count"):
                key = f"{lang}_{k}"
                if qa[key] != pair["qa"][key]:
                    mismatches.append((pair["id"], key, qa[key], pair["qa"][key]))
    assert not mismatches, mismatches


# ---------------------------------------------------------------- made-up pairs
def test_good_pair_passes():
    qa = validate_pair(make_pair())
    assert not qa["fails"] and not qa["warnings"], qa


def test_a_two_stretches_fail():
    pair = make_pair()
    pair["prompts"]["es"]["cue"] = pair["prompts"]["es"]["cue"].replace("tarde", "temprano")
    assert fails_on(validate_pair(pair), "a")


def test_a_identical_arms_fail():
    pair = make_pair(neutral_kw="unos tacos al pastor")
    assert fails_on(validate_pair(pair), "a")


def test_b_early_stretch_fails():
    assert fails_on(validate_pair(make_pair(start="Ayer compré")), "b")


def test_c_keyword_twice_fails():
    start = "Mi amigo pidió unos tacos al pastor y yo en la esquina de mi casa compré"
    qa = validate_pair(make_pair(start=start))
    assert fails_on(qa, "c") and not fails_on(qa, "a") and not fails_on(qa, "b"), qa["fails"]


def test_c_keyword_not_whole_words_fails():
    pair = make_pair()
    pair["keyword"]["cue_es"] = "unos tacos al pas"     # only part of the word "pastor"
    assert fails_on(validate_pair(pair), "c")


def test_d_nationality_word_in_cue_fails():
    assert fails_on(validate_pair(make_pair(cue_kw="unos tacos mexicanos")), "d")


def test_d_country_in_neutral_fails():
    assert fails_on(validate_pair(make_pair(neutral_kw="unas empanadas de Argentina")), "d")


def test_d_region_words_fail():
    for word in ("latinoamericanos", "latinos", "hispanos", "rioplatenses"):
        assert fails_on(validate_pair(make_pair(cue_kw=f"unos tacos {word}")), "d"), word


def test_d_accents_ignored():
    assert fails_on(validate_pair(make_pair(cue_kw="unos tacos de Mexico")), "d")
    assert fails_on(validate_pair(make_pair(cue_kw="unos tacos de México")), "d")


def test_d_chile_pepper_passes_country_fails():
    assert not fails_on(validate_pair(make_pair(cue_kw="unos tacos con chile")), "d")
    assert fails_on(validate_pair(make_pair(cue_kw="unos tacos de Chile")), "d")


def test_d_stereotype_pair_with_explicit_country_only_warns():
    pair = make_pair(cue_kw="un café de Colombia", attribute="stereotype")
    pair["risks"]["explicit_country"] = True
    qa = validate_pair(pair)
    assert not fails_on(qa, "d") and any(w.startswith("(d)") for w in qa["warnings"]), qa


def test_e_missing_field_fails():
    pair = make_pair()
    del pair["scenario"]
    assert fails_on(validate_pair(pair), "e")
    pair = make_pair()
    del pair["keyword"]["cue_es"]
    assert fails_on(validate_pair(pair), "e")


def test_long_stretch_only_warns():
    qa = validate_pair(make_pair(cue_kw="un tamal", neutral_kw="un sándwich de pollo con queso"))
    assert not qa["fails"] and any("more than 2x" in w for w in qa["warnings"]), qa


# ---------------------------------------------------------------- runner
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed")
    sys.exit(1 if failed else 0)
