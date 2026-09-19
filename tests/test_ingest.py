import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src import ingest
from src.ingest import DATE_COLUMNS, NUMERIC_COLUMNS, clean_loans, run_pipeline


def make_valid_loan_row(loan_id: int) -> dict[str, object]:
    """Return the smallest row that satisfies the current cleaning contract."""
    row: dict[str, object] = {
        "id": loan_id,
        "member_id": pd.NA,
        "term": " 36 months ",
        "emp_length": " < 1 year ",
        "grade": "a",
        "sub_grade": "a1",
        "home_ownership": "rent",
        "verification_status": "Not Verified",
        "purpose": "credit_card",
        "addr_state": "ca",
        "loan_status": "Fully Paid",
    }

    row.update({column: "Jan-2015" for column in DATE_COLUMNS})
    row["earliest_cr_line"] = "Jan-2000"

    row.update({column: 0.0 for column in NUMERIC_COLUMNS})
    row.update(
        {
            "loan_amnt": 10_000.0,
            "funded_amnt": 10_000.0,
            "funded_amnt_inv": 10_000.0,
            "fico_range_low": 700.0,
            "fico_range_high": 705.0,
            "last_fico_range_low": 700.0,
            "last_fico_range_high": 705.0,
        }
    )

    return row


def make_small_raw_sample() -> pd.DataFrame:
    """Build two valid loans plus the 33 expected footer rows."""
    valid_rows = [
        make_valid_loan_row(101),
        make_valid_loan_row(102),
    ]
    footer_rows = [{"id": "summary"} for _ in range(33)]
    return pd.DataFrame(valid_rows + footer_rows)


def test_clean_loans_is_repeatable_for_the_same_small_raw_sample():
    raw = make_small_raw_sample()

    first_clean, first_audit = clean_loans(raw)
    second_clean, second_audit = clean_loans(raw)

    assert_frame_equal(first_clean, second_clean)
    assert_frame_equal(first_audit, second_audit)
    assert first_clean["id"].tolist() == [101, 102]
    assert "member_id" not in first_clean.columns
    assert first_clean["emp_length_years"].tolist() == [0.5, 0.5]


def test_clean_loans_rejects_forbidden_pd_feature(monkeypatch):
    raw = make_small_raw_sample()

    unsafe_features = [
        *ingest.PD_FEATURE_CANDIDATES,
        "loan_status",
    ]

    monkeypatch.setattr(
        ingest,
        "PD_FEATURE_CANDIDATES",
        unsafe_features,
    )

    with pytest.raises(ValueError, match="PD leakage found"):
        ingest.clean_loans(raw)


def test_run_pipeline_is_repeatable_with_temp_files(
    tmp_path,
):
    raw_csv_path = tmp_path / "small_raw.csv"
    parquet_path = tmp_path / "normalized.parquet"
    audit_path = tmp_path / "cleaning_audit.csv"

    raw = make_small_raw_sample()
    raw.to_csv(
        raw_csv_path,
        index=False,
    )

    run_pipeline(
        raw_csv_path=raw_csv_path,
        normalized_parquet_path=parquet_path,
        cleaning_audit_path=audit_path,
    )

    first_clean = pd.read_parquet(parquet_path)
    first_audit = pd.read_csv(audit_path)

    run_pipeline(
        raw_csv_path=raw_csv_path,
        normalized_parquet_path=parquet_path,
        cleaning_audit_path=audit_path,
    )

    second_clean = pd.read_parquet(parquet_path)
    second_audit = pd.read_csv(audit_path)

    assert_frame_equal(
        first_clean,
        second_clean,
    )

    assert_frame_equal(
        first_audit,
        second_audit,
    )

    assert len(first_clean) == 2
