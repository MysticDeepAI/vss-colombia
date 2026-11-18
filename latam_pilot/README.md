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

## Status (2026-11-18)

- The 10 MX/AR pairs in `dataset/minimal_pairs_mx_ar.json` are frozen with tag `dataset-v1`. No edits after this;
  any change becomes `dataset-v2`.
- Native review was skipped for now, so every pair's `native_review.status` stays `pending`. If it is done later,
  record the answers and tag `dataset-v2`.

## Next steps

1. Jhoan (pipeline): `load_dataset` in `main.py` loops over `("es", "en")`; the MX/AR pairs are Spanish-only, so
   it must loop over the languages each pair has.
2. Jhoan (graders): decide whether the AV just repeating the keyword (e.g. "IMSS", "ANSES") counts as naming the
   country, and write that rule into the per-country grader prompts.
3. Nicolás: blind annotation sheet and annotation scoring scripts, ready before the run.
