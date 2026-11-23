# ARS report (exploratory; our ARS on the official NLACritic)

## Distributions by arm

| Arm | ARS | ARS_control | ARS_net | ARS_net > 0 |
|---|---|---|---|---|
| cue | n=57, median=+0.0036, IQR=[+0.0003, +0.0090] | n=57, median=+0.0062, IQR=[+0.0016, +0.0151] | n=57, median=-0.0018, IQR=[-0.0103, +0.0032] | 0.46 |
| neutral | n=20, median=+0.0040, IQR=[+0.0002, +0.0085] | n=20, median=+0.0055, IQR=[-0.0004, +0.0145] | n=20, median=-0.0036, IQR=[-0.0144, +0.0069] | 0.35 |

## Percentile sweep (threshold from the neutral arm)

| Percentile | tau | survivors cue | survivors neutral | attribute | median D | +/=/- | p |
|---|---|---|---|---|---|---|---|
| 80 | +0.0098 | 12 | 4 | nationality_ar | +0.200 | 3/2/0 | 0.1250 |
| 80 | +0.0098 | 12 | 4 | nationality_mx | +0.000 | 2/2/1 | 0.3750 |
| 90 | +0.0107 | 11 | 2 | nationality_ar | +0.000 | 2/3/0 | 0.2500 |
| 90 | +0.0107 | 11 | 2 | nationality_mx | +0.000 | 2/3/0 | 0.2500 |
| 95 | +0.0118 | 9 | 1 | nationality_ar | +0.000 | 1/4/0 | 0.5000 |
| 95 | +0.0118 | 9 | 1 | nationality_mx | +0.000 | 2/3/0 | 0.2500 |
