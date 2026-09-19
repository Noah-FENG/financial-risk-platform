import pandas as pd
from pandas.testing import assert_frame_equal

from src.replay import REPLAY_AUDIT_COLUMNS, run_replay


def write_batch(
    batches_root, issue_month: str, loan_ids: list[int], valid: bool = True
) -> None:
    """Create a minimal monthly Parquet batch for an isolated replay test."""
    batch_directory = batches_root / f"issue_month={issue_month}"
    batch_directory.mkdir()
    if valid:
        batch = pd.DataFrame({"id": loan_ids, "issue_month": issue_month})
    else:
        batch = pd.DataFrame({"unexpected_column": loan_ids})
    batch.to_parquet(batch_directory / "loans.parquet", index=False)


def test_run_replay_returns_a_monthly_audit_and_writes_it(tmp_path):
    batches_root = tmp_path / "batches"
    batches_root.mkdir()
    write_batch(batches_root, "2020-01", [1, 2])
    write_batch(batches_root, "2020-02", [3])
    audit_path = tmp_path / "replay_audit.csv"

    audit = run_replay(batches_root=batches_root, audit_path=audit_path)

    expected = pd.DataFrame(
        {
            "processed_month": ["2020-01", "2020-02"],
            "batch_loan_count": [2, 1],
            "cumulative_loan_count": [2, 3],
        }
    )
    assert audit.columns.tolist() == REPLAY_AUDIT_COLUMNS
    assert_frame_equal(audit, expected)
    assert_frame_equal(pd.read_csv(audit_path), expected)


def test_replay_stops_at_the_cutoff_without_reading_future_batches(tmp_path):
    batches_root = tmp_path / "batches"
    batches_root.mkdir()
    write_batch(batches_root, "2020-01", [1])
    write_batch(batches_root, "2020-02", [2])
    write_batch(batches_root, "2020-03", [3], valid=False)

    audit = run_replay(
        end_month="2020-02",
        batches_root=batches_root,
        audit_path=None,
    )

    assert audit["processed_month"].tolist() == ["2020-01", "2020-02"]
    assert audit["cumulative_loan_count"].tolist() == [1, 2]


def test_replay_audit_is_identical_on_a_repeat_run(tmp_path):
    batches_root = tmp_path / "batches"
    batches_root.mkdir()
    write_batch(batches_root, "2020-01", [1, 2])
    write_batch(batches_root, "2020-02", [3, 4])
    audit_path = tmp_path / "replay_audit.csv"

    first_audit = run_replay(batches_root=batches_root, audit_path=audit_path)
    first_file = pd.read_csv(audit_path)
    second_audit = run_replay(batches_root=batches_root, audit_path=audit_path)
    second_file = pd.read_csv(audit_path)

    assert_frame_equal(first_audit, second_audit)
    assert_frame_equal(first_file, second_file)
