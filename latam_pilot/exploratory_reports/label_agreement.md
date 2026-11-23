# Label agreement on the same explanations

## MX/AR layer 21: `main` vs `regrade` (same grader, twice)

| Subset | n | agreement | kappa | positives main | positives regrade | 1->0 | 0->1 |
|---|---|---|---|---|---|---|---|
| all | 700 | 0.999 | 0.993 | 77 | 78 | 0 | 1 |
| arm=cue | 350 | 0.997 | 0.990 | 57 | 58 | 0 | 1 |
| arm=neutral | 350 | 1.000 | 1.000 | 20 | 20 | 0 | 0 |

## Colombia layer 20: `old` (qwen_local) vs `strict` (claude_api, strict)

| Subset | n | agreement | kappa | positives old | positives strict | 1->0 | 0->1 |
|---|---|---|---|---|---|---|---|
| all | 4200 | 0.954 | 0.536 | 129 | 310 | 7 | 188 |
| arm=cue | 2100 | 0.927 | 0.558 | 118 | 257 | 7 | 146 |
| arm=neutral | 2100 | 0.980 | 0.338 | 11 | 53 | 0 | 42 |

The changed explanations are listed by `label_agreement.py --examples N` (not copied here).
