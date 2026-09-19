# Financial Risk Analytics Platform

A reproducible LendingClub data and risk analytics project using accepted loans issued from 2007 through 2018.

The project will examine:

1. When loan performance began to deteriorate.
2. Whether interest rates compensated for realized credit risk.
3. Whether borrower quality or credit policy changed over time.

## Current Status

Phase 1 — L0 Foundation is complete.

| Check | Result |
|---|---:|
| Raw rows | 2,260,701 |
| Valid loans | 2,260,668 |
| Removed footer rows | 33 |
| Monthly partitions | 139 |
| Origination range | 2007-06 to 2018-12 |
| Full replay rows | 2,260,668 |
| Pytest | 7 passed |
| Ruff | Passed |

## L0 Pipeline

```text
Raw CSV
→ cleaning and validation
→ normalized Parquet
→ monthly partitions
→ chronological replay
→ replay audit
```

Main files:

- `src/ingest.py`: cleaning and CSV-to-Parquet ingestion
- `src/replay.py`: monthly replay and backfill
- `src/features.py`: maturity and censoring rules
- `tests/`: small synthetic pipeline tests

## Run

Install dependencies:

```powershell
uv sync
```

Run ingestion and full replay:

```powershell
uv run python src/ingest.py
uv run python src/replay.py
```

Run a selected replay range:

```powershell
uv run python src/replay.py --start-month 2015-01 --end-month 2015-06
```

Run checks:

```powershell
uv run pytest -q
uv run ruff format --check src tests
uv run ruff check src tests
```

## Data Boundaries

### Static snapshot

The accepted-loan data is a static loan-level snapshot, not a monthly repayment panel. Monthly replay reconstructs origination order; it does not make final outcomes historically available.

The exact source snapshot date is not explicitly documented and must be stated as an assumption in later outcome analysis.

### Leakage

PD features may only use information available at origination. Loan status, payments, recoveries, post-origination FICO, hardship, and settlement fields cannot be used as PD predictors.

### Censoring

Current or immature loans cannot automatically be labeled as non-defaults.

- 36-month loans require at least 36 months of observation.
- 60-month loans require at least 60 months of observation.
- `Fully Paid` becomes target `0`.
- `Charged Off` or `Default` becomes target `1`.
- Other or insufficiently observed loans keep a missing target.

## Next Phase

Phase 2 will build the DuckDB and dbt analytics layer.