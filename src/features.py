import pandas as pd

DEFAULT_STATUSES = {
    "Charged Off",
    "Default",
}
NON_DEFAULT_STATUSES = {
    "Fully Paid",
}

PD_TERMINAL_STATUSES = DEFAULT_STATUSES | NON_DEFAULT_STATUSES


def add_censoring_fields(
    loans: pd.DataFrame,
    snapshot_date: str,
) -> pd.DataFrame:
    """Add observation-window and maturity fields."""

    result = loans.copy()

    snapshot_month = pd.Period(
        snapshot_date,
        freq="M",
    )

    issue_months = result["issue_d"].dt.to_period("M")

    result["observation_months"] = (
        (snapshot_month.year - issue_months.dt.year) * 12
        + snapshot_month.month
        - issue_months.dt.month
    )

    result["is_matured"] = result["observation_months"] >= result["term_months"]
    result["is_pd_eligible"] = result["is_matured"] & result["loan_status"].isin(
        PD_TERMINAL_STATUSES
    )
    result["is_censored"] = ~result["is_pd_eligible"]
    result["target_default"] = pd.Series(pd.NA, index=result.index, dtype="Int64")
    non_default_mask = result["is_pd_eligible"] & result["loan_status"].isin(
        NON_DEFAULT_STATUSES
    )
    default_mask = result["is_pd_eligible"] & result["loan_status"].isin(
        DEFAULT_STATUSES
    )
    result.loc[
        non_default_mask,
        "target_default",
    ] = 0
    result.loc[
        default_mask,
        "target_default",
    ] = 1

    return result
