from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "accepted_2007_to_2018Q4.csv"

NORMALIZED_PARQUET_PATH = (
    PROJECT_ROOT / "data" / "processed" / "accepted_loans_normalized.parquet"
)

CLEANING_AUDIT_PATH = PROJECT_ROOT / "outcomes" / "cleaning_audit.csv"

DATE_COLUMNS = [
    "issue_d",
    "earliest_cr_line",
    "last_pymnt_d",
    "next_pymnt_d",
    "last_credit_pull_d",
]

NUMERIC_COLUMNS = [
    "loan_amnt",
    "funded_amnt",
    "funded_amnt_inv",
    "int_rate",
    "installment",
    "annual_inc",
    "dti",
    "fico_range_low",
    "fico_range_high",
    "delinq_2yrs",
    "inq_last_6mths",
    "open_acc",
    "pub_rec",
    "revol_bal",
    "revol_util",
    "total_acc",
    "pub_rec_bankruptcies",
    "out_prncp",
    "total_pymnt",
    "total_rec_prncp",
    "total_rec_int",
    "total_rec_late_fee",
    "recoveries",
    "collection_recovery_fee",
    "last_pymnt_amnt",
    "last_fico_range_low",
    "last_fico_range_high",
]

PD_FEATURE_CANDIDATES = [
    "loan_amnt",
    "funded_amnt",
    "funded_amnt_inv",
    "term_months",
    "int_rate",
    "installment",
    "grade",
    "sub_grade",
    "annual_inc",
    "emp_length_years",
    "home_ownership",
    "verification_status",
    "purpose",
    "addr_state",
    "dti",
    "fico_range_low",
    "fico_range_high",
    "delinq_2yrs",
    "inq_last_6mths",
    "open_acc",
    "pub_rec",
    "revol_bal",
    "revol_util",
    "total_acc",
    "pub_rec_bankruptcies",
]

FORBIDDEN_PD_COLUMNS = [
    "loan_status",
    "out_prncp",
    "total_pymnt",
    "total_rec_prncp",
    "total_rec_int",
    "total_rec_late_fee",
    "recoveries",
    "collection_recovery_fee",
    "last_pymnt_d",
    "last_pymnt_amnt",
    "next_pymnt_d",
    "last_credit_pull_d",
    "last_fico_range_low",
    "last_fico_range_high",
]


def add_audit(
    audit_rows: list[dict[str, object]],
    section: str,
    metric: str,
    count: int,
) -> None:
    audit_rows.append(
        {
            "section": section,
            "metric": metric,
            "count": int(count),
        }
    )


def clean_loans(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the validated Step 3C cleaning rules."""

    required_columns = {
        "id",
        "member_id",
        "term",
        "emp_length",
        "grade",
        "sub_grade",
        "home_ownership",
        "verification_status",
        "purpose",
        "addr_state",
        "loan_status",
        *DATE_COLUMNS,
        *NUMERIC_COLUMNS,
    }

    missing_columns = required_columns - set(raw.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    audit_rows: list[dict[str, object]] = []
    original_len = len(raw)

    # 1. 有效贷款记录与主键
    df_clean = raw.copy()

    id_as_number = pd.to_numeric(
        df_clean["id"],
        errors="coerce",
    )

    footer_mask = id_as_number.isna()
    footer_rows_removed = int(footer_mask.sum())

    if footer_rows_removed != 33:
        raise ValueError(f"Expected 33 footer rows, but found {footer_rows_removed}.")

    df_clean = df_clean.loc[~footer_mask].copy()
    df_clean["id"] = id_as_number.loc[df_clean.index].astype("int64")

    if df_clean["id"].isna().any():
        raise ValueError("Missing id remains after cleaning.")

    if df_clean["id"].duplicated().any():
        raise ValueError("Duplicate id found after cleaning.")

    if not df_clean["member_id"].isna().all():
        raise ValueError(
            "member_id is not fully missing; investigate before dropping it."
        )

    df_clean = df_clean.drop(columns=["member_id"])

    # 2. term 与 issue_month
    df_clean["term"] = df_clean["term"].astype("string").str.strip()

    df_clean["term_months"] = df_clean["term"].str.extract(r"(\d+)")[0].astype("Int64")

    invalid_term_mask = (
        ~df_clean["term_months"].isin([36, 60]) | df_clean["term_months"].isna()
    )

    if invalid_term_mask.any():
        raise ValueError("Invalid term_months found.")

    # 3. 日期字段
    for col in DATE_COLUMNS:
        source_value = df_clean[col].copy()

        parsed_value = pd.to_datetime(
            source_value,
            format="%b-%Y",
            errors="coerce",
        )

        parse_failure_mask = parsed_value.isna() & source_value.notna()

        add_audit(
            audit_rows,
            "date_parsing",
            f"{col}__missing_count_after_parse",
            int(parsed_value.isna().sum()),
        )

        add_audit(
            audit_rows,
            "date_parsing",
            f"{col}__parse_failure_count",
            int(parse_failure_mask.sum()),
        )

        if parse_failure_mask.any():
            raise ValueError(f"Non-empty values in {col} failed date parsing.")

        df_clean[col] = parsed_value

    if df_clean["issue_d"].isna().any():
        raise ValueError("issue_d contains missing or invalid values.")

    df_clean["issue_month"] = df_clean["issue_d"].dt.to_period("M").astype("string")

    # 4. 数值字段
    for col in NUMERIC_COLUMNS:
        source_value = df_clean[col].copy()

        parsed_value = pd.to_numeric(
            source_value,
            errors="coerce",
        )

        parse_failure_mask = parsed_value.isna() & source_value.notna()

        add_audit(
            audit_rows,
            "numeric_parsing",
            f"{col}__missing_count_after_parse",
            int(parsed_value.isna().sum()),
        )

        add_audit(
            audit_rows,
            "numeric_parsing",
            f"{col}__parse_failure_count",
            int(parse_failure_mask.sum()),
        )

        if parse_failure_mask.any():
            raise ValueError(f"Non-empty values in {col} failed numeric parsing.")

        df_clean[col] = parsed_value

    # 百分比点，例如 13.99，转换成可计算的小数
    df_clean["int_rate_decimal"] = df_clean["int_rate"] / 100
    df_clean["dti_decimal"] = df_clean["dti"] / 100
    df_clean["revol_util_decimal"] = df_clean["revol_util"] / 100

    # 5. 分类字段与就业年限
    for col in [
        "emp_length",
        "verification_status",
        "purpose",
        "loan_status",
    ]:
        df_clean[col] = df_clean[col].astype("string").str.strip()

    for col in [
        "grade",
        "sub_grade",
        "home_ownership",
        "addr_state",
    ]:
        df_clean[col] = df_clean[col].astype("string").str.strip().str.upper()

    emp_years = df_clean["emp_length"].str.extract(r"(\d+)")[0].astype("Float64")

    df_clean["emp_length_years"] = emp_years.mask(
        df_clean["emp_length"].eq("< 1 year"),
        0.5,
    )

    # 6. 数据质量 flag：只标记，不删除
    annual_inc_p999 = df_clean["annual_inc"].quantile(0.999)

    df_clean["annual_inc_nonpositive_flag"] = df_clean["annual_inc"].le(0)

    df_clean["annual_inc_top_0_1pct_flag"] = df_clean["annual_inc"].gt(annual_inc_p999)

    df_clean["dti_out_of_range_flag"] = df_clean["dti"].lt(0) | df_clean["dti"].gt(100)

    df_clean["revol_util_out_of_range_flag"] = df_clean["revol_util"].lt(0) | df_clean[
        "revol_util"
    ].gt(100)

    for metric, column in [
        ("annual_inc_nonpositive", "annual_inc_nonpositive_flag"),
        ("annual_inc_top_0_1pct", "annual_inc_top_0_1pct_flag"),
        ("dti_out_of_range", "dti_out_of_range_flag"),
        ("revol_util_out_of_range", "revol_util_out_of_range_flag"),
    ]:
        add_audit(
            audit_rows,
            "quality_flags",
            metric,
            int(df_clean[column].sum()),
        )

    # 7. 分类字段验证
    invalid_grade_mask = df_clean["grade"].notna() & ~df_clean["grade"].isin(
        list("ABCDEFG")
    )

    invalid_sub_grade_mask = df_clean["sub_grade"].notna() & ~df_clean[
        "sub_grade"
    ].str.fullmatch(r"[A-G][1-5]")

    invalid_state_mask = df_clean["addr_state"].notna() & ~df_clean[
        "addr_state"
    ].str.fullmatch(r"[A-Z]{2}")

    for metric, mask in [
        ("invalid_grade_count", invalid_grade_mask),
        ("invalid_sub_grade_count", invalid_sub_grade_mask),
        ("invalid_state_format_count", invalid_state_mask),
    ]:
        add_audit(
            audit_rows,
            "category_validation",
            metric,
            int(mask.sum()),
        )

        if mask.any():
            raise ValueError(f"Category validation failed: {metric}")

    # 8. 跨字段验证
    df_clean["fico_range_order_flag"] = (
        df_clean["fico_range_low"].notna()
        & df_clean["fico_range_high"].notna()
        & (df_clean["fico_range_low"] > df_clean["fico_range_high"])
    )

    df_clean["last_fico_range_order_flag"] = (
        df_clean["last_fico_range_low"].notna()
        & df_clean["last_fico_range_high"].notna()
        & (df_clean["last_fico_range_low"] > df_clean["last_fico_range_high"])
    )

    df_clean["credit_history_after_issue_flag"] = (
        df_clean["earliest_cr_line"].notna()
        & df_clean["issue_d"].notna()
        & (df_clean["earliest_cr_line"] > df_clean["issue_d"])
    )

    df_clean["grade_sub_grade_mismatch_flag"] = (
        df_clean["grade"].notna()
        & df_clean["sub_grade"].notna()
        & (df_clean["grade"] != df_clean["sub_grade"].str[0])
    )

    df_clean["funded_exceeds_loan_flag"] = (
        df_clean["funded_amnt"].notna()
        & df_clean["loan_amnt"].notna()
        & (df_clean["funded_amnt"] > df_clean["loan_amnt"])
    )

    df_clean["investor_funding_exceeds_funded_flag"] = (
        df_clean["funded_amnt_inv"].notna()
        & df_clean["funded_amnt"].notna()
        & (df_clean["funded_amnt_inv"] > df_clean["funded_amnt"])
    )

    for metric, column in [
        ("fico_range_low_greater_than_high", "fico_range_order_flag"),
        (
            "last_fico_range_low_greater_than_high",
            "last_fico_range_order_flag",
        ),
        (
            "earliest_credit_line_after_issue_date",
            "credit_history_after_issue_flag",
        ),
        (
            "grade_sub_grade_mismatch",
            "grade_sub_grade_mismatch_flag",
        ),
        (
            "funded_amount_exceeds_loan_amount",
            "funded_exceeds_loan_flag",
        ),
        (
            "investor_funding_exceeds_funded_amount",
            "investor_funding_exceeds_funded_flag",
        ),
    ]:
        count = int(df_clean[column].sum())

        add_audit(
            audit_rows,
            "cross_field_validation",
            metric,
            count,
        )

        if count != 0:
            raise ValueError(f"Cross-field validation failed: {metric}")

    # 9. PD leakage boundary
    missing_pd_candidates = set(PD_FEATURE_CANDIDATES) - set(df_clean.columns)

    if missing_pd_candidates:
        raise ValueError(f"Missing PD candidates: {sorted(missing_pd_candidates)}")

    leakage_overlap = set(PD_FEATURE_CANDIDATES) & set(FORBIDDEN_PD_COLUMNS)

    if leakage_overlap:
        raise ValueError(f"PD leakage found: {sorted(leakage_overlap)}")

    # 10. 最终验收
    add_audit(
        audit_rows,
        "final_validation",
        "raw_row_count",
        original_len,
    )

    add_audit(
        audit_rows,
        "final_validation",
        "clean_row_count",
        len(df_clean),
    )

    add_audit(
        audit_rows,
        "final_validation",
        "footer_rows_removed",
        footer_rows_removed,
    )

    add_audit(
        audit_rows,
        "final_validation",
        "missing_id_count",
        int(df_clean["id"].isna().sum()),
    )

    add_audit(
        audit_rows,
        "final_validation",
        "duplicate_id_count",
        int(df_clean["id"].duplicated().sum()),
    )

    add_audit(
        audit_rows,
        "final_validation",
        "missing_issue_d_count",
        int(df_clean["issue_d"].isna().sum()),
    )

    add_audit(
        audit_rows,
        "final_validation",
        "invalid_term_count",
        int((~df_clean["term_months"].isin([36, 60])).sum()),
    )

    cleaning_audit = (
        pd.DataFrame(audit_rows)
        .sort_values(["section", "metric"])
        .reset_index(drop=True)
    )

    return df_clean, cleaning_audit


def run_pipeline(
    raw_csv_path: Path = RAW_CSV_PATH,
    normalized_parquet_path: Path = NORMALIZED_PARQUET_PATH,
    cleaning_audit_path: Path = CLEANING_AUDIT_PATH,
) -> tuple[Path, Path]:
    raw = pd.read_csv(
        raw_csv_path,
        low_memory=False,
    )

    df_clean, cleaning_audit = clean_loans(raw)

    normalized_parquet_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cleaning_audit_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df_clean.to_parquet(
        normalized_parquet_path,
        index=False,
    )

    cleaning_audit.to_csv(
        cleaning_audit_path,
        index=False,
    )

    return normalized_parquet_path, cleaning_audit_path


if __name__ == "__main__":
    parquet_path, audit_path = run_pipeline()

    print(f"Normalized Parquet: {parquet_path}")
    print(f"Cleaning audit: {audit_path}")
