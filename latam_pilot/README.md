# LatAm mini pilot - working files

**Countries: México and Argentina**, with Colombia as the anchor (13 Nov plan, following Samuel's advice to start with
three contrasting sub-regions: Andean, Mesoamerican, Rioplatense). The earlier step 2 (picking the top 3 countries from
CHOCLO) was removed on 2026-11-16; the old version is in tag `countries-v1`.

- `validate_pairs.py`: machine checks for minimal pairs, rules of the 13 Nov plan. A pair fails if:
  (a) cue and neutral differ in more than one stretch of words; (b) that stretch starts before word 10;
  (c) a keyword does not appear exactly once, as whole words, in its prompt; (d) either prompt names a country,
  a nationality or a region word such as "latino" (accents ignored; country names only count when capitalised,
  so "chile" the pepper passes); (e) a v2.2 field is missing. Warns if one changed stretch is more than twice
  as long as the other. Checks every language a pair has.
  `python latam_pilot/validate_pairs.py dataset/minimal_pairs.json --ids N01,N02 --langs es`
  Add `--write` to store each pair's result as its `qa` block.
- `test_validate_pairs.py`: the 10 Colombia nationality pairs (N01-N10, Spanish) pass; the span numbers match
  the stored `qa` of all 30 pilot pairs; one made-up broken pair per rule fails on that rule.
  Run from `latam_pilot/`: `python test_validate_pairs.py`
- `check_tokens.py`: token check with the Qwen2.5-7B-Instruct tokenizer, using the chat template and the same
  keyword search as `src/extraction.py`. Per pair: is the keyword found, keyword tokens in cue vs neutral, and are
  the token before the keyword and the 5 after it identical in both arms. Needs only `transformers` + `jinja2`
  (no torch, no GPU). `python latam_pilot/check_tokens.py dataset/minimal_pairs_mx_ar.json`
  Result for the 10 MX/AR pairs: `check_tokens_mx_ar.txt` (10/10 OK; keyword found in all 20 prompts; window
  tokens identical within every pair; cue - neutral keyword gap 0 or +1 token).
- `make_blind_sheet.py`: blind sheet for the human check of the grader. From a graded results file it picks
  100 explanations: up to 50 the grader marked "yes", the rest "no" (half from the cue arm at tw..tw+5, half from
  tw-1 and the neutral arm), shuffled with a fixed seed. Writes `sheet_annotator1.csv` (all rows),
  `sheet_annotator2.csv` (first 40 rows), and the key (`key.csv`, `key_meta.json`) that stays closed until both
  annotators finish. Put the output folder outside the repo.
  `python latam_pilot/make_blind_sheet.py <run>/results_stage3.json --out-dir ../human_check --grader-name claude_api`
- `score_annotations.py`: reads the filled sheets (label 1 or 0; CSV from Excel or Google Sheets) and reports
  kappa between the two people, the grader's confusion table, precision and recall with 95% intervals, the 10 most
  informative disagreements, and the thresholds (kappa >= 0.70, precision >= 0.90, recall >= 0.80).
  The sheet over-samples the grader's "yes" answers, so raw recall on the sheet is too optimistic; the script
  also gives numbers weighted back to the whole run, and checks the thresholds on those. Add the second grader with
  `--grader qwen_local=<its results file>`.
- `test_annotation_scripts.py`: builds a sheet from the Colombia pilot explanations (`results/results_stage3.json`)
  and scores made-up annotations, including a hand-worked recall example. Run from `latam_pilot/`.

## Status (2026-11-18)

- The 10 MX/AR pairs in `dataset/minimal_pairs_mx_ar.json` are frozen with tag `dataset-v2`, which replaces
  `dataset-v1`. Changes: pair 3 sentence is now "una fiesta con mariachi / tango" (was "una noche de ..."); pair 4
  replaced by a board game in one shared sentence (El Turista / El Estanciero, was posada / mate); AR02 says
  "el ANSES". Pair checker and token check pass on all 10. No edits after this; any change becomes `dataset-v3`.
- The pair mix differs from the 13 Nov plan: pair 3 there is a medium food cue, here it is a strong music cue,
  so the set has 3 strong, 1 medium and 1 dialect pair.
- Native review was skipped for now, so every pair's `native_review.status` stays `pending`. If it is done later,
  record the answers and tag `dataset-v3`.

## dataset-v3 (2026-11-22)

- AR03 cue changed from "tango" to "cuarteto". The native AR reviewer (2026-11-18) said a house
  party with tango is not common and suggested cumbia; cumbia was tried, but LatamGPT read it as Colombian in a
  blind check, so the team chose cuarteto; the native reviewer approved it on 2026-11-22. "en la casa" kept as is.
  AR02 already said "el ANSES". Grader refs for Argentina now also list "cuarteto".
- `validate_pairs.py --write`: 10/10 pairs pass. Token check (2026-11-22, Python 3.13.11, transformers 4.57.6):
  10/10 OK, keyword found in all 20 prompts, window tokens identical within every pair; cue - neutral keyword
  gap 0 to +2 tokens (AR03 and AR04 +2). Output in `check_tokens_mx_ar.txt`.
- Frozen with tag `dataset-v3` (2026-11-22). Any later change becomes `dataset-v4`.
- `latamgpt_check_2026-11-22.md`: LatamGPT (Copuchat) check of the 10 pairs and the grader prompt, verbatim.
  Blind country guess: 9/10 cue prompts right; AR03 "cumbia" read as Colombia; neutral prompts also get a
  country. Grader lists and rule judged fine.
- `latamgpt_check_round2_2026-11-22.md`: second round (suggested improvements, neutral prompts, AR03
  alternatives, grader lists). Points to check with a native reader: "en la casa" in the pair 3 frame, and
  "jubilación" in the AR02 neutral arm.
- `annotation_guide.md`: rule for the human check (same strict rule as the grader), examples and edge cases.
- `human_check_process.md`: the human check step by step (700 explanations, 100-row sheet, 2 annotators,
  thresholds) plus an optional LatamGPT third rater on the 40 shared rows (needs a new OK before sending).
- `latamgpt_summary.md`: write-up of both LatamGPT rounds for the paper (what was done, facts, interpretation,
  limitations).
- `choclo_cue_candidates.md`: short list of food and tradition cue candidates for MX and AR taken from the CHOCLO
  benchmark, for a later version. Not in the dataset.

## Next steps

1. Jhoan (pipeline): `load_dataset` in `main.py` loops over `("es", "en")`; the MX/AR pairs are Spanish-only, so
   it must loop over the languages each pair has.
2. Jhoan (graders): decide whether the AV just repeating the keyword (e.g. "IMSS", "ANSES") counts as naming the
   country, and write that rule into the per-country grader prompts.
3. Nicolás: blind sheet and scoring scripts are ready (tested on the Colombia pilot). After the run: build the
   sheet from the claude_api results, label the 100 rows, send the first 40 to the second person, then score.
   Annotation guide: `annotation_guide.md` (2026-11-22).
