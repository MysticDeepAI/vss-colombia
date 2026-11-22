# Cue candidates from CHOCLO (México and Argentina)

Source: [latam-gpt/CHOCLO](https://huggingface.co/datasets/latam-gpt/CHOCLO), MIT license, file
`BenchmarkCHOCLO.csv` (about 105k question/answer rows built with GPT-3.5 from Wikipedia and Wikidata;
about 10k rows each for Argentina, México and Colombia). Read on 2026-11-21.

## How the list was made

1. Kept rows with `Country` = argentina or méxico and `Category` = dish or tradition.
2. Dropped any entity that CHOCLO also lists under another country (names compared without case or accents).
3. Kept names of at most three words, without parentheses, whose answers describe a dish, drink, dance,
   festival, music genre or custom. That left 122 for Argentina and 248 for México.
4. Picked by hand the everyday items below. Proper names of people, very regional dishes and items that
   are clearly mislabelled were left out. CHOCLO's country labels are noisy (for example `bara brith` and
   `rugelach` appear under Argentina, Brazilian entities under Costa Rica), so "only one country" in CHOCLO
   does not prove the item is unambiguous.

None of these are in the dataset yet. They are candidates for a later version, to be checked by a native
reader of each country and then by `validate_pairs.py` and `check_tokens.py`.

## Argentina

| Candidate | CHOCLO category | Fits pair | Notes |
|---|---|---|---|
| choripán | dish | 1 (food) | already the AR01 cue |
| chocotorta | dish | 1 or 3 (birthday) | very Argentine, birthday cake |
| provoleta | dish | 1 | asado side |
| fugazza con queso | dish | 1 | pizzería dish |
| sándwich de miga | dish | 3 (birthday) | typical party food |
| morcipán | dish | 1 | street food, close to choripán |
| fernet con coca | dish | 3 | party drink; Córdoba too |
| facturas | dish | other | pastries with mate; word also means "invoices" |
| locro | dish | other | also Andean (Bolivia, Peru) |
| chacarera | tradition | 3 (music) | folk dance; also Bolivia |
| zamba | tradition | 3 (music) | folk dance; easy to confuse with Brazilian samba |
| ñoquis del 29 | dish | other | monthly custom, strong cue |

`cuarteto` (now the AR03 cue) is not a CHOCLO entity by itself; it appears only in the names of groups. Rows that mention `cumbia` (tried for AR03 and dropped) appear under several countries (Argentina, Bolivia, Colombia).

## México

| Candidate | CHOCLO category | Fits pair | Notes |
|---|---|---|---|
| chilaquiles | dish | 1 (food) | breakfast dish |
| cochinita pibil | dish | 1 | Yucatán |
| torta ahogada | dish | 1 | Guadalajara street food |
| pambazo | dish | 1 | street food |
| guajolota | dish | 1 | Mexico City street food |
| tlayuda | dish | 1 | Oaxaca |
| michelada | dish | 3 (party) | drink |
| tejuino | dish | other | drink, Jalisco |
| pan de muerto | dish / tradition | other | seasonal |
| son jarocho | tradition | 3 (music) | Veracruz music |
| jarabe tapatío | tradition | 3 (music) | dance |
| piñata | tradition | 3 (birthday) | common across Latin America; weak cue |

`esquites` (the MX01 cue) and `mariachi` (the MX03 cue) are CHOCLO entities listed only under México, which
supports the current choice; they dropped out of step 3 only because of the category or wording filter.

## Other uses

- Check that the model knows a cue's country before using it: ask Qwen the CHOCLO questions on that entity.
  If it does not know that the item is Argentine or Mexican, a low score on that pair says little about bias.
- Extend the grader's reference lists in `src/grading.py`.
