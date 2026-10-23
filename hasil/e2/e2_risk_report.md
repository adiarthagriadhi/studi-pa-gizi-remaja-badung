# E2 re-identification risk report (aggregate)

Records: 1898; variables: 81; K = 5

## Before suppression

| quasi-identifiers | classes | k=1 | k<3 | k<5 | min k |
|---|---|---|---|---|---|
| area × sex × grade | 18 | 0 | 0 | 0 | 67 |
| school × sex × grade (not released) | 31 | 1 | 1 | 1 | 1 |
| area × sex × grade × BMI category | 83 | 6 | 18 | 34 | 1 |
| released quasi-identifiers | 288 | 88 | 166 | 361 | 1 |
| all candidate quasi-identifiers (incl. not released) | 983 | 633 | 927 | 1345 | 1 |

## Suppression (cells set to missing)

- bmi_for_age_cat: 12
- parental_education: 160

Records with k < 5 (suppressed cells as wildcards): 0; minimum k: 5

## After suppression (exact match, missing treated as its own category; conservative view)

| quasi-identifiers | classes | k=1 | k<3 | k<5 | min k |
|---|---|---|---|---|---|
| area × sex × grade | 18 | 0 | 0 | 0 | 67 |
| area × sex × grade × BMI category | 79 | 3 | 9 | 29 | 1 |
| released quasi-identifiers | 222 | 26 | 58 | 269 | 1 |
