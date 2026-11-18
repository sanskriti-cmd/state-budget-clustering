# Data notes

## Source

Reserve Bank of India, *State Finances: A Study of Budgets 2025-26* (released 23 January 2026).
Publication page: https://www.rbi.org.in/Scripts/AnnualPublications.aspx?head=State+Finances+%3A+A+Study+of+Budgets

| Indicator (CSV column) | Statement | Publication page |
|---|---|---|
| `education_share` : education expenditure, % of aggregate expenditure | Statement 26 | https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23735 |
| `health_share` : medical, public health and family welfare, % of aggregate expenditure | Statement 27 | https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23736 |
| `development_gsdp` : development expenditure, % of GSDP | Statement 35 | https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23744 |
| `social_sector_gsdp` : social-sector expenditure, % of GSDP | Statement 35 | same |
| `capital_outlay_gsdp` : capital outlay, % of GSDP | Statement 35 | same |

The same publication page links an **e-STATES database** Excel workbook, which is the better source for a
multi-year panel. Excel versions of each statement are linked on the publication page.

## Required file

`data/state_budget_features_2025_26_BE.csv` with one row per state/UT and these columns
(see `state_budget_features_template.csv`):

```
state,education_share,health_share,development_gsdp,social_sector_gsdp,capital_outlay_gsdp
```

Other column names are accepted if they contain the keywords `educ`, `health`/`medic`, `develop`,
`social`, `capital`/`capex` (exactly one column per keyword). Rows named "All States", "Total" or "India" are
removed automatically. Rows with a missing indicator are dropped, never imputed.

## Verification checklist (do this before running or submitting)

1. Open each Excel statement above and, for each of the 31 units, compare the 2025-26 **BE** value with the CSV.
2. Confirm the unit list: 28 states plus NCT Delhi, Jammu and Kashmir and Puducherry.
3. Confirm every value is a percentage (not a fraction, not in rupees) and refers to the **same stage (BE)**.
4. Keep Accounts, Revised Estimates and Budget Estimates in separate files; never mix them in one run.
5. Record the date you downloaded the files and the RBI file names.

## Extended panel schema (not used in the reported run)

For a state x year x stage panel add columns `year` (e.g. `2023-24`) and `stage` (`Accounts`, `RE` or `BE`) and run
`python run_experiments.py --data panel.csv --year 2023-24 --stage Accounts`. Further indicators described in
the paper's Table 2 (capital expenditure share, interest burden, committed burden, capital intensity) can be
added to `FEATURES` in `run_experiments.py`.

Monetary fields must be in one unit (RBI tables may use Rs crore or Rs lakh) before ratios are computed.
Missing values must stay missing, not become zero.

## Optional outcomes file (post-clustering only)

`data/outcomes.csv` with a `state` column and numeric columns such as literacy rate, infant mortality, life
expectancy, per-capita NSDP or an SDG-index score, obtained from an independent source and documented.
