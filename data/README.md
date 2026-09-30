# Local data directory

The repository intentionally excludes source data, generated Parquet files, monthly partitions, and the local DuckDB database. This keeps the GitHub repository lightweight and prevents large derived artifacts from being mistaken for source code.

To reproduce the L0 pipeline locally, place the LendingClub accepted-loan CSV at:

```text
data/raw/accepted_2007_to_2018Q4.csv
```

Then run the commands documented in the root `README.md`:

```powershell
uv run python src/ingest.py
uv run python src/replay.py
uv run dbt build --project-dir dbt --profiles-dir dbt
```

The generated local paths are:

```text
data/processed/accepted_loans_normalized.parquet
data/batches/issue_month=YYYY-MM/loans.parquet
data/analytics.duckdb
```

They are intentionally ignored by Git. The checked-in files under `outcomes/` are small audit summaries, not loan-level data.
