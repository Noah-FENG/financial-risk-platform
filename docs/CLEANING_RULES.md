# LendingClub Step 3C — Cleaning Rules

## 1. Purpose and scope

This document is the Step 3C cleaning contract for the 43 core raw columns in `field_groups`. It turns the observations from Step 3B into rules for the derived, normalized dataset. It does **not** alter the raw CSV.

The normalized dataset has one row per valid loan. It preserves both origination-time and post-origination columns, because the latter are needed for historical outcome analysis. The two groups must remain separate when a future PD feature list is created.

## 2. Global rules

1. Keep the source CSV unchanged. All transformations write a new derived DataFrame and, later, normalized Parquet.
2. Define a valid loan by a numeric `id`. The current input contains 33 non-loan footer rows whose `id` cannot be converted to a number; exclude only those rows from the derived dataset and log the count.
3. Do not treat a missing value, zero, empty string, invalid value, or parsing failure as the same thing. Record each separately in the cleaning audit.
4. Use `errors="coerce"` only together with an explicit count of the resulting non-empty parsing failures. `issue_d` must have no missing or invalid values after footer removal.
5. At this stage, flags describe data-quality issues; they do not delete, cap, winsorize, or impute observations unless a later documented business rule authorizes it.
6. Preserve post-origination fields in the normalized dataset for historical analysis, but block them from the future PD feature list.

## 3. Field-level rules

### 3.1 Loan key and origination terms

| Field | Standardized type / unit | Cleaning and validation rule | Missing or anomaly action | PD use |
|---|---|---|---|---|
| `id` | `int64`; loan identifier | Convert with `pd.to_numeric(..., errors="coerce")`. A value that cannot be converted is not a loan ID. | Exclude the row from the derived dataset; after cleaning, require no null or duplicate `id`. | Never a feature; key only. |
| `member_id` | Nullable identifier | Preserve as a nullable identifier; do not treat it as a quantitative variable. | Current Step 3B profile shows 100% missing. Keep this fact in the audit and exclude the field from analysis and PD lists. | Never a feature. |
| `loan_amnt` | `float`; USD | Convert to numeric and retain nominal dollars. | Flag null, non-numeric, or non-positive values; do not delete or scale. | Candidate: known at origination. |
| `funded_amnt` | `float`; USD | Convert to numeric and retain nominal dollars. | Flag null, non-numeric, or non-positive values; later compare with `loan_amnt`. | Candidate: known at origination. |
| `funded_amnt_inv` | `float`; USD | Convert to numeric and retain nominal dollars. | Flag null, non-numeric, or negative values; later compare with `funded_amnt`. | Candidate: known at origination. |
| `term` | trimmed string | Strip whitespace and retain the source text for traceability. | Audit unexpected values. | Candidate: known at origination. |
| `term_months` | `Int64`; months; derived | Extract the number from `term`. Only `36` and `60` are accepted. | Raise an error for an invalid or missing derived term rather than silently replacing it. | Candidate: known at origination. |
| `issue_d` | `datetime64[ns]`; monthly date | Parse with format `%b-%Y`; derive `issue_month` in `YYYY-MM` form. | Non-empty parse failures and missing values are errors after footer removal. | Candidate: known at origination. |

### 3.2 Pricing and borrower profile

| Field | Standardized type / unit | Cleaning and validation rule | Missing or anomaly action | PD use |
|---|---|---|---|---|
| `int_rate` | `float`; percentage points | Convert to numeric. Preserve `13.99` as 13.99%; derive `int_rate_decimal = int_rate / 100`. | Flag null, non-numeric, non-positive, or over-100 values. | Model B candidate only. |
| `installment` | `float`; USD per month | Convert to numeric. | Flag null, non-numeric, or non-positive values. | Known at origination; include only if later model design permits. |
| `grade` | trimmed uppercase category, `A`–`G` | Strip whitespace, uppercase, and audit categories. | Flag values outside `A`–`G`; do not recode them. | Model B candidate only. |
| `sub_grade` | trimmed uppercase category, `A1`–`G5` | Strip whitespace, uppercase, and audit categories. | Flag malformed values; later check that its first letter equals `grade`. | Model B candidate only. |
| `annual_inc` | `float`; USD per year | Convert to numeric and retain nominal dollars. | Flag null, non-numeric, non-positive values, and values above the clean-sample 99.9th percentile. Do not cap or drop. | Candidate: known at origination. |
| `emp_length` | trimmed category | Strip whitespace and retain source text. | Preserve missingness. Audit unexpected labels. | Candidate: known at origination. |
| `emp_length_years` | `Float64`; years; derived | Map `< 1 year` to `0.5`, extract integer values from other labels, and map `10+ years` to `10`. | Keep missing values missing; do not impute. | Candidate: known at origination. |
| `home_ownership` | trimmed uppercase category | Strip whitespace, uppercase, and audit categories. | Preserve missingness and flag unexpected labels. | Candidate: known at origination. |
| `verification_status` | trimmed category | Strip whitespace and audit categories. | Preserve missingness and flag unexpected labels. | Candidate: known at origination. |
| `purpose` | trimmed category | Strip whitespace and audit categories. | Preserve missingness and flag unexpected labels. | Candidate: known at origination. |
| `addr_state` | trimmed uppercase category | Strip whitespace, uppercase, and check for two-character state-style codes. | Flag missing or unexpected values; do not infer a state. | Candidate: known at origination. |
| `dti` | `float`; percentage points | Convert to numeric and derive `dti_decimal = dti / 100`. | Flag values below 0 or above 100; do not drop or cap. | Candidate: known at origination. |

### 3.3 Credit history at origination

| Field | Standardized type / unit | Cleaning and validation rule | Missing or anomaly action | PD use |
|---|---|---|---|---|
| `delinq_2yrs` | `float`; count | Convert to numeric. | Flag null, negative, or non-integer-like values. | Candidate: known at origination. |
| `earliest_cr_line` | `datetime64[ns]`; monthly date | Parse with `%b-%Y`. | Preserve nulls; flag non-empty parse failures and dates later than `issue_d`. | Candidate: known at origination. |
| `fico_range_low` | `float`; FICO score | Convert to numeric. | Flag null or values outside the expected score range; later check against `fico_range_high`. | Candidate: known at origination. |
| `fico_range_high` | `float`; FICO score | Convert to numeric. | Flag null or values outside the expected score range; later check against `fico_range_low`. | Candidate: known at origination. |
| `inq_last_6mths` | `float`; count | Convert to numeric. | Flag null, negative, or non-integer-like values. | Candidate: known at origination. |
| `open_acc` | `float`; count | Convert to numeric. | Flag null, negative, or non-integer-like values. | Candidate: known at origination. |
| `pub_rec` | `float`; count | Convert to numeric. | Flag null, negative, or non-integer-like values. | Candidate: known at origination. |
| `revol_bal` | `float`; USD | Convert to numeric and retain nominal dollars. | Flag null, non-numeric, or negative values. | Candidate: known at origination. |
| `revol_util` | `float`; percentage points | Convert to numeric and derive `revol_util_decimal = revol_util / 100`. | Flag values below 0 or above 100; do not drop or cap. | Candidate: known at origination. |
| `total_acc` | `float`; count | Convert to numeric. | Flag null, negative, or non-integer-like values. | Candidate: known at origination. |
| `pub_rec_bankruptcies` | `float`; count | Convert to numeric. | Preserve nulls; flag negative or non-integer-like values. | Candidate: known at origination. |

### 3.4 Loan outcomes

| Field | Standardized type / unit | Cleaning and validation rule | Missing or anomaly action | PD use |
|---|---|---|---|---|
| `loan_status` | trimmed category | Strip whitespace and retain the source status; audit observed categories. | Footer rows are already removed by the `id` rule. Any remaining null requires investigation. Do not create a 0/1 target here. | Never a feature; future target source only. |
| `out_prncp` | `float`; USD | Convert to numeric. | Flag null, non-numeric, or negative values. | Never a feature. |
| `total_pymnt` | `float`; USD | Convert to numeric. | Flag null, non-numeric, or negative values. | Never a feature. |
| `total_rec_prncp` | `float`; USD | Convert to numeric. | Flag null, non-numeric, or negative values; later compare with principal amounts. | Never a feature. |
| `total_rec_int` | `float`; USD | Convert to numeric. | Flag null, non-numeric, or negative values. | Never a feature. |
| `total_rec_late_fee` | `float`; USD | Convert to numeric. | Flag null, non-numeric, or negative values. | Never a feature. |
| `recoveries` | `float`; USD | Convert to numeric. | Flag null, non-numeric, or negative values. | Never a feature. |
| `collection_recovery_fee` | `float`; USD | Convert to numeric. | Flag null, non-numeric, or negative values. | Never a feature. |

### 3.5 Post-origination updates

| Field | Standardized type / unit | Cleaning and validation rule | Missing or anomaly action | PD use |
|---|---|---|---|---|
| `last_pymnt_d` | `datetime64[ns]`; monthly date | Parse with `%b-%Y`. | Nulls may be valid; flag non-empty parse failures. | Never a feature. |
| `last_pymnt_amnt` | `float`; USD | Convert to numeric. | Flag null, non-numeric, or negative values. | Never a feature. |
| `next_pymnt_d` | `datetime64[ns]`; monthly date | Parse with `%b-%Y`. | Null is expected for terminal loans; flag non-empty parse failures. | Never a feature. |
| `last_credit_pull_d` | `datetime64[ns]`; monthly date | Parse with `%b-%Y`. | Preserve nulls and flag non-empty parse failures. | Never a feature. |
| `last_fico_range_high` | `float`; FICO score | Convert to numeric. | Preserve nulls; later check it is not below `last_fico_range_low`. | Never a feature. |
| `last_fico_range_low` | `float`; FICO score | Convert to numeric. | Preserve nulls; later check it is not above `last_fico_range_high`. | Never a feature. |

## 4. Cross-field validation rules

Run these checks after the individual conversions above. Except for the invalid-`id` footer rule, they produce flags and audit counts rather than automatically deleting observations.

| Rule | Check |
|---|---|
| Loan grain | `id` is non-null and unique after cleaning. |
| Term | `term_months` is only 36 or 60. |
| Time axis | `issue_d` is present and valid for every cleaned loan. |
| Credit-history order | `earliest_cr_line <= issue_d` when both dates are present. |
| Origination FICO interval | `fico_range_low <= fico_range_high` when both values are present. |
| Post-origination FICO interval | `last_fico_range_low <= last_fico_range_high` when both values are present. |
| Grade consistency | The first character of `sub_grade` equals `grade` when both are present. |
| Funding amounts | Flag `funded_amnt > loan_amnt` or `funded_amnt_inv > funded_amnt`; investigate before taking action. |
| Percentage values | Preserve and count `dti` and `revol_util` values outside 0–100 rather than assuming they are safe to delete. |
| Feature leakage | Confirm that the future PD feature list has no overlap with outcome or post-origination columns. |

## 5. Later feature-engineering and outcome fields

These are deliberately not created during basic ingestion. Feature fields belong to a later feature-engineering step; outcome fields require a documented data snapshot date and the project censoring rule.

| Derived field | Inputs | Rule |
|---|---|---|
| `fico_mid` | `fico_range_low`, `fico_range_high` | Calculate `(fico_range_low + fico_range_high) / 2` during later feature engineering. If either endpoint is missing, keep `fico_mid` missing. |
| `is_matured` | `issue_d`, `term_months`, configured `snapshot_date` | A 36-month loan needs at least 36 months of observation; a 60-month loan needs at least 60. |
| `is_pd_eligible` | `is_matured`, `loan_status` | Only matured `Fully Paid`, `Charged Off`, or `Default` loans are eligible for the basic terminal PD sample. |
| `target_default` | `loan_status`, `is_pd_eligible` | `Charged Off` / `Default` = 1; `Fully Paid` = 0; all other rows remain missing and are excluded from that target. |
| `approx_default_age_months` | `issue_d`, `last_pymnt_d`, `loan_status` | A documented proxy for vintage analysis only; it is not a true monthly repayment-panel default time. |

## 6. Step 3C acceptance criteria

Before extracting logic into `src/ingest.py`, confirm all of the following:

1. The source CSV remains unchanged.
2. Exactly 33 current footer rows are excluded using the numeric-`id` rule.
3. `df_clean` has one row per loan, with no missing or duplicated `id`.
4. `issue_d` and `term_months` are valid for all cleaned loans.
5. The cleaning audit reports conversion failures, missingness, and quality flags.
6. No outcome or post-origination column is in the prospective PD feature list.
7. Re-running the same transformation on the same raw CSV produces identical normalized output.
