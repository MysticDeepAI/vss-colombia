"""Tests for make_blind_sheet.py and score_annotations.py. Run from latam_pilot/:
python test_annotation_scripts.py

Uses the real AV explanations of the Colombia pilot (results/results_stage3.json, graded by
qwen_local) to build a sheet, and made-up annotations to score it.
1. Statistics match known values (Wilson interval, Cohen's kappa).
2. The sheet has the planned shape and no hint of arm, position or grader label; same seed gives
   the same sheet; an existing key is not overwritten.
3. Scoring: a perfect annotator gives precision = recall = 1; a hand-worked example gives the
   expected raw and weighted recall; bad or missing labels are reported; Excel-style CSV reads.
"""
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

import make_blind_sheet as mbs
import score_annotations as sa

HERE = Path(__file__).resolve().parent
PILOT_RESULTS = HERE.parent / "results" / "results_stage3.json"
TMP = Path(tempfile.mkdtemp(prefix="annot_test_"))
_built = {}


def built_sheet(seed=2026, name="sheet"):
    """Builds (once per seed) a sheet from the Colombia pilot results."""
    if seed not in _built:
        out = TMP / f"{name}_{seed}"
        mbs.main([str(PILOT_RESULTS), "--out-dir", str(out), "--grader-name", "qwen_local", "--seed", str(seed)])
        _built[seed] = out
    return _built[seed]


def write_annotations(path, rows, delimiter=",", encoding="utf-8-sig"):
    with open(path, "w", encoding=encoding, newline="") as f:
        w = csv.writer(f, delimiter=delimiter)
        w.writerow(["unit_id", "target_country", "text", "label", "notes"])
        for uid, label in rows:
            w.writerow([uid, "Colombia", "some text", label, ""])


def key_rows(out):
    return sa.read_csv_rows(out / "key.csv")


# ---------------------------------------------------------------- statistics
def test_wilson_known_value():
    lo, hi = sa.wilson(9, 10)
    assert abs(lo - 0.5958) < 1e-3 and abs(hi - 0.9821) < 1e-3, (lo, hi)


def test_kappa_known_value():
    # 2x2 table: both yes 20, A yes/B no 5, A no/B yes 10, both no 15 -> kappa 0.4
    a = [1] * 20 + [1] * 5 + [0] * 10 + [0] * 15
    b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15
    assert abs(sa.cohen_kappa(a, b) - 0.4) < 1e-9


def test_kappa_identical_is_one():
    assert sa.cohen_kappa([1, 0, 1, 1, 0], [1, 0, 1, 1, 0]) == 1.0


# ---------------------------------------------------------------- the sheet
def test_sheet_shape_on_pilot():
    out = built_sheet()
    s1 = sa.read_csv_rows(out / "sheet_annotator1.csv")
    s2 = sa.read_csv_rows(out / "sheet_annotator2.csv")
    key = key_rows(out)
    assert len(s1) == 100 and len(key) == 100, (len(s1), len(key))
    assert list(s1[0].keys()) == mbs.SHEET_COLUMNS, list(s1[0].keys())
    assert [r["unit_id"] for r in s1] == [f"U{i:03d}" for i in range(1, 101)]
    assert s2 == s1[:40], "second sheet must be the first 40 rows"
    assert all(r["label"] == "" for r in s1)
    strata = [r["stratum"] for r in key]
    assert strata.count("pos") == 50 and strata.count("neg_cue_window") == 25 and strata.count("neg_other") == 25, \
        {s: strata.count(s) for s in mbs.STRATA}
    assert all(r["grader_label"] == ("1" if r["stratum"] == "pos" else "0") for r in key)
    assert all(r["arm"] == "cue" and r["position"] != "tw-1" for r in key if r["stratum"] == "neg_cue_window")
    texts = {r["unit_id"]: r["text"] for r in s1}
    assert all(texts[r["unit_id"]] for r in key)


def test_sheet_positives_are_mixed_through_the_sheet():
    key = key_rows(built_sheet())
    first_half = sum(r["stratum"] == "pos" for r in key[:50])
    assert 15 <= first_half <= 35, first_half  # shuffled, not grouped


def test_same_seed_same_sheet_other_seed_differs():
    a = (built_sheet(2026) / "key.csv").read_bytes()
    out_again = TMP / "again"
    mbs.main([str(PILOT_RESULTS), "--out-dir", str(out_again), "--grader-name", "qwen_local", "--seed", "2026"])
    assert (out_again / "key.csv").read_bytes() == a
    assert (built_sheet(7) / "key.csv").read_bytes() != a


def test_existing_key_is_not_overwritten():
    try:
        mbs.main([str(PILOT_RESULTS), "--out-dir", str(built_sheet()), "--seed", "1"])
    except SystemExit as e:
        assert "already exists" in str(e), e
        return
    raise AssertionError("expected a refusal")


# ---------------------------------------------------------------- scoring
def test_perfect_annotator_scores_one():
    out = built_sheet()
    key = key_rows(out)
    truth = [(r["unit_id"], r["grader_label"]) for r in key]
    write_annotations(TMP / "a1.csv", truth)
    write_annotations(TMP / "a2.csv", truth[:40])
    res = sa.main(["--key-dir", str(out), "--annotator1", str(TMP / "a1.csv"), "--annotator2", str(TMP / "a2.csv"),
                   "--out-dir", str(TMP / "score_perfect"), "--bootstrap", "200"])
    g = res["graders"]["qwen_local"]
    assert g["precision"]["weighted"] == 1.0 and g["recall"]["weighted"] == 1.0, g
    assert g["precision"]["raw"] == 1.0 and g["recall"]["raw"] == 1.0, g
    assert res["kappa"]["value"] == 1.0 and res["kappa"]["n_shared"] == 40, res["kappa"]
    assert (TMP / "score_perfect" / "human_check_report.md").exists()


def test_second_grader_read_from_results_file():
    out = built_sheet()
    write_annotations(TMP / "a1_two.csv", [(r["unit_id"], 1) for r in key_rows(out)])
    res = sa.main(["--key-dir", str(out), "--annotator1", str(TMP / "a1_two.csv"),
                   "--grader", f"qwen_again={PILOT_RESULTS}", "--out-dir", str(TMP / "score_two"), "--bootstrap", "200"])
    assert res["graders"]["qwen_again"]["confusion"] == res["graders"]["qwen_local"]["confusion"], res["graders"]


def test_weighted_recall_hand_example():
    # 10 grader-yes rows from a pool of 10 (weight 1), all truly yes;
    # 10 grader-no rows from a pool of 100 (weight 10), one truly yes.
    # raw recall = 10/11; whole-run recall = 10 / (10 + 1*10) = 0.5; precision = 1.
    d = TMP / "hand"
    d.mkdir()
    rows = []
    for i in range(20):
        pos = i < 10
        rows.append({"unit_id": f"U{i + 1:03d}", "item_id": f"X{i}", "group_id": "X", "arm": "cue",
                     "language": "es", "position": "tw+1", "sample": 0,
                     "stratum": "pos" if pos else "neg_cue_window", "weight": 1.0 if pos else 10.0,
                     "grader_label": 1 if pos else 0, "grader_raw": "true" if pos else "false",
                     "grader_quote": "", "target_country": "México", "text": f"text {i}"})
    mbs.write_csv(d / "key.csv", mbs.KEY_COLUMNS, rows)
    (d / "key_meta.json").write_text(json.dumps({
        "results_file": "made-up", "seed": 0, "grader_name": "g", "label_field": "mentions_target",
        "pool_sizes": {"pos": 10, "neg_cue_window": 100, "neg_other": 0},
        "sampled": {"pos": 10, "neg_cue_window": 10, "neg_other": 0}}), encoding="utf-8")
    write_annotations(d / "a1.csv", [(r["unit_id"], 1 if i <= 10 else 0) for i, r in enumerate(rows)])
    res = sa.main(["--key-dir", str(d), "--annotator1", str(d / "a1.csv"), "--out-dir", str(d / "out"),
                   "--bootstrap", "200"])
    rec, prec = res["graders"]["g"]["recall"], res["graders"]["g"]["precision"]
    assert abs(rec["raw"] - 10 / 11) < 1e-9 and abs(rec["weighted"] - 0.5) < 1e-9, rec
    assert prec["weighted"] == 1.0 and prec["ci_method"] == "Wilson", prec
    assert rec["ci_method"].startswith("stratified bootstrap"), rec


def test_missing_and_bad_labels_are_reported():
    key = key_rows(built_sheet())
    rows = [(r["unit_id"], r["grader_label"]) for r in key]
    rows[3] = (rows[3][0], "")
    rows[7] = (rows[7][0], "si")
    del rows[10]
    write_annotations(TMP / "bad.csv", rows)
    try:
        sa.main(["--key-dir", str(built_sheet()), "--annotator1", str(TMP / "bad.csv"), "--out-dir", str(TMP / "x")])
    except SystemExit as e:
        msg = str(e)
        assert "U004 (empty)" in msg and "U008 ('si')" in msg and "rows missing: U011" in msg, msg
        return
    raise AssertionError("expected an error")


def test_excel_semicolon_cp1252_csv_reads():
    key = key_rows(built_sheet())
    rows = [(r["unit_id"], r["grader_label"]) for r in key]
    write_annotations(TMP / "excel.csv", rows, delimiter=";", encoding="cp1252")
    labels = sa.read_labels(TMP / "excel.csv", {r["unit_id"] for r in key}, require_all_of=[r["unit_id"] for r in key])
    assert len(labels) == 100


# ---------------------------------------------------------------- runner
if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    if not PILOT_RESULTS.exists():
        print(f"missing {PILOT_RESULTS}; the sheet tests need the Colombia pilot results")
        sys.exit(1)
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except (AssertionError, SystemExit, Exception) as e:
            failed += 1
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    shutil.rmtree(TMP, ignore_errors=True)
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed")
    sys.exit(1 if failed else 0)
