# Financial Risk Analytics Platform

A reproducible LendingClub data and risk analytics project using accepted loans issued from 2007 through 2018.

The project is designed to answer three connected questions:

1. Which origination vintages began to perform worse at the same loan age?
2. Within the same Grade and term, did pricing adjust as realized credit losses changed?
3. Did deterioration coincide with shifts in borrower characteristics or the originated loan mix?

The final V1 will also build a baseline Logistic PD model and evaluate it on future periods rather than a random train/test split.

## Current Status

Phase 1 and Phase 2 are complete. The project is ready to begin Phase 3; no Phase 3 risk findings or final figures have been produced yet.

| Stage | Status | Evidence / next output |
|---|---|---|
| Phase 1 — L0 Foundation | Complete | Normalized Parquet, 139 monthly partitions, chronological replay, L0 tests |
| Phase 2 — L1 Data Model | Complete and verified | 6 dbt views + 39 data tests; `PASS=45` on 2026-09-30 |
| Phase 3 — L2 Risk Analytics | Ready to start | Metric Contract, three analysis marts, Figure A/B/C |
| Phase 4 — L3 PD Model | Not started | Logistic PD V0, temporal/OOT validation, calibration, PSI |
| Phase 5 — Finalization | Not started | End-to-end rebuild, repeatability, final documentation and presentation |

### Verified data baseline

| Check | Result |
|---|---:|
| Raw rows | 2,260,701 |
| Valid loans | 2,260,668 |
| Removed footer rows | 33 |
| Monthly partitions | 139 |
| Origination range | 2007-06 to 2018-12 |
| Full replay rows | 2,260,668 |
| L0 pytest, 2026-09-30 | 7 passed |
| Ruff format and lint, 2026-09-30 | Passed |
| Latest full dbt build, 2026-09-30 | 45 passed, 0 errors, 0 skipped |

The 2026-09-30 GitHub-publication validation reran pytest, Ruff, and the full dbt build. Ingestion and replay were not rerun because they would regenerate large local artifacts; their recorded audit outputs remain under `outcomes/`.

## Architecture

```text
Raw LendingClub CSV
→ cleaning and validation
→ normalized Parquet
→ issue-month partitions
→ chronological replay and audit
→ DuckDB / dbt staging
→ dimensions and facts
→ Phase 3 analytical marts and figures
→ Phase 4 temporal PD model
```

The raw CSV remains unchanged. The formal project grain is one row per loan unless a downstream mart explicitly documents an aggregated grain.

## Repository Guide

| Path | Contents |
|---|---|
| `src/` | Ingestion, monthly replay, and maturity/censoring helpers |
| `dbt/` | Tested staging, dimension, and fact models for DuckDB |
| `tests/` | Synthetic pipeline, replay, leakage, censoring, and repeatability tests |
| `outcomes/` | Small audit summaries; no loan-level data |
| `docs/` | Data dictionary, cleaning rules, learning review, and evidence-backed project status |
| `main.ipynb` | Preserved exploratory work for cleaning, partitioning, and replay |
| `data/README.md` | Local-data setup; raw and generated data are intentionally excluded from Git |

## L0 Data Pipeline

Main files:

- `src/ingest.py`: cleaning and CSV-to-Parquet ingestion
- `src/replay.py`: chronological monthly replay and cutoff backfill
- `src/features.py`: maturity and censoring helpers
- `tests/`: synthetic ingestion, replay, leakage, censoring, and repeatability checks

Formal outputs:

- `data/processed/accepted_loans_normalized.parquet`
- `data/batches/issue_month=YYYY-MM/loans.parquet`
- `outcomes/cleaning_audit.csv`
- `outcomes/monthly_batch_audit.csv`
- `outcomes/replay_audit.csv`

## L1 Analytics Data Model

The dbt project reads the normalized Parquet file and builds views in `data/analytics.duckdb`.

| Model | Type | Grain | Purpose |
|---|---|---|---|
| `stg_loans` | staging | one loan | Stable analytical entry point |
| `dim_loan` | dimension | one loan | Amount, term, rate, Grade, sub-grade, purpose |
| `dim_borrower` | dimension | one loan application | Origination-time borrower characteristics |
| `dim_date` | dimension | one observed issue month | Calendar and vintage labels |
| `fact_origination` | fact | one loan origination | Issue date and issue month |
| `fact_loan_outcome` | fact | one loan | Terminal outcome, censoring, approximate default age, realized loss |

The latest full `dbt build` completed on 2026-09-30:

```text
Finished running 39 data tests, 6 view models
Done. PASS=45 WARN=0 ERROR=0 SKIP=0 TOTAL=45
```

Tests currently cover `not_null`, `unique`, `accepted_values`, and `relationships` rules.

## Phase 3 Entry Point

Phase 3 begins by defining a Metric Contract before implementing analytical SQL. The three analyses require different samples and grains:

| Analysis | Sample rule | Planned grain |
|---|---|---|
| Vintage performance | Loans observable at each selected MOB | `vintage × MOB × grade × term` |
| Grade pricing | Mature terminal loans within the same Grade and term | `vintage × grade × term` |
| Borrower / policy drift | All valid originations | `issue_quarter`, with Grade/term breakouts |

Planned outputs:

- `mart_vintage_performance` and Figure A: approximate cumulative default incidence by vintage and MOB
- `mart_grade_pricing` and Figure B: funded-weighted pricing and realized credit loss within Grade
- `mart_policy_drift` and Figure C: borrower characteristics and originated portfolio mix

These marts and figures do not exist yet. No deterioration date, pricing adequacy result, or policy-drift conclusion has been established.

## Run

Install dependencies from the repository root:

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

Build all dbt views and execute their tests from the repository root:

```powershell
uv run dbt build --project-dir dbt --profiles-dir dbt
```

Run L0 checks:

```powershell
uv run pytest -q
uv run ruff format --check src tests
uv run ruff check src tests
```

## Data Boundaries

### Static snapshot and replay

The accepted-loan data is a static loan-level snapshot, not a monthly repayment panel. Monthly replay reconstructs origination order; it does not make final outcomes historically available at each replay cutoff.

The exact source snapshot date is not documented. `fact_loan_outcome` currently uses `2019-03-01` as an explicit assumption because it is the latest observed payment month.

`last_pymnt_d` provides only an approximate default age and must not be presented as the true charge-off date.

### Leakage

PD features may only use information available at origination. Loan status, payments, recoveries, post-origination FICO, hardship, and settlement fields may be used for outcome analysis but not as origination-time PD predictors.

### Censoring

Current and insufficiently observed loans cannot automatically be labeled as non-defaults. Phase 3 vintage analysis requires MOB-specific observability, while mature outcome and PD analyses require their own eligibility rules.

### Interpretation

`realized_net_principal_loss` is a net principal shortfall measure, not net profit or full investment return. Accepted-loan data can describe changes in the originated portfolio, but it cannot by itself prove that approval policy changed or that those changes caused later defaults.

## Project Scope

V1 intentionally prioritizes correctness, reproducibility, and explainability. Spark, orchestration platforms, cloud deployment, Docker, boosted-tree models, SHAP, dashboards, LLMs, and APIs are outside the Fall 2026 scope.

See `PROJECT_CHARTER.md` for the authoritative goals, milestones, and definition of done, and `docs/PROJECT_STATUS.md` for the current evidence-backed progress record.
