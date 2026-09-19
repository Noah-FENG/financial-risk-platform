import argparse
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BATCHES_ROOT = PROJECT_ROOT / "data" / "batches"
DEFAULT_REPLAY_AUDIT_PATH = PROJECT_ROOT / "outcomes" / "replay_audit.csv"
REPLAY_AUDIT_COLUMNS = [
    "processed_month",
    "batch_loan_count",
    "cumulative_loan_count",
]


def discover_batch_files(batches_root: Path = BATCHES_ROOT) -> list[Path]:
    """Discover and return paths of monthly batch file in chronological order"""
    batches_files = sorted(batches_root.glob("issue_month=*/loans.parquet"))
    if not batches_files:
        raise FileNotFoundError(f"No batch files found in {batches_root}")
    return batches_files


def extract_issue_month(batch_file: Path) -> str:
    """Extract issue month from a batch file path."""
    partition_name = batch_file.parent.name
    prefix = "issue_month="
    if not partition_name.startswith(prefix):
        raise ValueError(f"Invalid batch directory name: {partition_name}")
    issue_month = partition_name.removeprefix(prefix)
    return issue_month


def validate_batch_sequence(batch_files: list[Path]) -> list[str]:
    """Validate that the batch files are in chronological order."""
    issue_months = [extract_issue_month(batch_file) for batch_file in batch_files]
    if len(issue_months) != len(set(issue_months)):
        raise ValueError("Duplicate issue months found in batch files.")
    try:
        periods = [pd.Period(issue_month, freq="M") for issue_month in issue_months]
    except ValueError as e:
        raise ValueError(f"Invalid issue month format: {e}") from e
    normalized_periods = [str(period) for period in periods]
    if normalized_periods != issue_months:
        raise ValueError("Issue months must use YYYY-MM format.")
    expected_periods = pd.period_range(start=periods[0], end=periods[-1], freq="M")

    if issue_months != [str(period) for period in expected_periods]:
        missing_months = set(expected_periods.astype(str)) - set(issue_months)
        raise ValueError(
            "Batch files are not in chronological order or have missing months."
            f" Missing months: {missing_months}"
        )
    return issue_months


def select_batch_files(
    batch_files: list[Path],
    start_month: str | None = None,
    end_month: str | None = None,
) -> list[Path]:
    """select batch files between start_month and end_month (inclusive)"""
    issue_months = validate_batch_sequence(batch_files)
    if start_month is None:
        start_month = issue_months[0]

    if end_month is None:
        end_month = issue_months[-1]

    if start_month not in issue_months or end_month not in issue_months:
        raise ValueError(
            f"Start month {start_month} or end month {end_month} not found in batch files."
        )

    start_index = issue_months.index(start_month)
    end_index = issue_months.index(end_month)
    if start_index > end_index:
        raise ValueError(f"Start month {start_month} is after end month {end_month}.")
    return batch_files[start_index : end_index + 1]


def replay_batches(batch_files: list[Path]) -> Iterator[tuple[str, pd.DataFrame]]:
    """read and yield validated batches one month at a time."""
    validate_batch_sequence(batch_files)
    for batch_file in batch_files:
        issue_month = extract_issue_month(batch_file)
        batch = pd.read_parquet(batch_file)

        required_columns = {"id", "issue_month"}
        missing_columns = required_columns - set(batch.columns)

        if missing_columns:
            raise ValueError(
                f"Batch file {batch_file} is missing required columns: {missing_columns}"
            )

        if batch.empty:
            raise ValueError(f"Batch file {batch_file} is empty.")

        if not batch["issue_month"].eq(issue_month).all():
            raise ValueError(
                f"Batch file {batch_file} has inconsistent issue_month values."
            )

        if batch["id"].duplicated().any():
            raise ValueError(f"Batch file {batch_file} has duplicate IDs.")

        if batch["id"].isna().any():
            raise ValueError(f"Batch file {batch_file} has missing IDs.")

        yield issue_month, batch


def write_replay_audit(audit: pd.DataFrame, audit_path: Path) -> None:
    """Write a replay audit table without adding an index column."""
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(audit_path, index=False)


def run_replay(
    start_month: str | None = None,
    end_month: str | None = None,
    batches_root: Path = BATCHES_ROOT,
    audit_path: Path | None = DEFAULT_REPLAY_AUDIT_PATH,
) -> pd.DataFrame:
    """Replay selected origination batches and return one audit row per month.

    ``cumulative_loan_count`` is cumulative within this replay run.  A normal
    full replay therefore starts at the first available month; a backfill can
    supply a later ``start_month`` and receives a self-contained audit.
    """
    batch_files = discover_batch_files(batches_root)
    selected_files = select_batch_files(batch_files, start_month, end_month)

    audit_rows: list[dict[str, int | str]] = []
    cumulative_loan_count = 0
    for issue_month, batch in replay_batches(selected_files):
        batch_loan_count = len(batch)
        cumulative_loan_count += batch_loan_count
        audit_rows.append(
            {
                "processed_month": issue_month,
                "batch_loan_count": batch_loan_count,
                "cumulative_loan_count": cumulative_loan_count,
            }
        )

    audit = pd.DataFrame(audit_rows, columns=REPLAY_AUDIT_COLUMNS)
    if audit_path is not None:
        write_replay_audit(audit, audit_path)
    return audit


def parse_args() -> argparse.Namespace:
    """Read an optional inclusive replay range from the command line."""
    parser = argparse.ArgumentParser(description="Replay LendingClub monthly batches.")
    parser.add_argument(
        "--start-month", help="First month to replay, in YYYY-MM format."
    )
    parser.add_argument("--end-month", help="Last month to replay, in YYYY-MM format.")
    parser.add_argument(
        "--audit-path",
        type=Path,
        default=DEFAULT_REPLAY_AUDIT_PATH,
        help="Destination CSV for the replay audit.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    replay_audit = run_replay(
        start_month=args.start_month,
        end_month=args.end_month,
        audit_path=args.audit_path,
    )
    total_loans = replay_audit["cumulative_loan_count"].iloc[-1]
    print(f"Replay completed: {len(replay_audit)} months, {total_loans:,} rows")
