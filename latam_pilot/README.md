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
