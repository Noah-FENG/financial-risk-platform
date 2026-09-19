import pandas as pd

from src.features import add_censoring_fields


def test_add_censoring_fields_calculates_maturity():
    loans = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "issue_d": pd.to_datetime(
                [
                    "2015-01-01",
                    "2015-02-01",
                    "2013-01-01",
                    "2014-01-01",
                ]
            ),
            "term_months": pd.Series(
                [36, 36, 60, 36],
                dtype="Int64",
            ),
            "loan_status": [
                "Fully Paid",
                "Fully Paid",
                "Charged Off",
                "Current",
            ],
        }
    )

    result = add_censoring_fields(
        loans,
        snapshot_date="2018-01-31",
    )

    assert result["observation_months"].tolist() == [
        36,
        35,
        60,
        48,
    ]

    assert result["is_matured"].tolist() == [
        True,
        False,
        True,
        True,
    ]

    assert result["is_pd_eligible"].tolist() == [
        True,
        False,
        True,
        False,
    ]

    assert result["is_censored"].tolist() == [
        False,
        True,
        False,
        True,
    ]

    assert result.loc[
        [0, 2],
        "target_default",
    ].tolist() == [0, 1]

    assert (
        result.loc[
            [1, 3],
            "target_default",
        ]
        .isna()
        .all()
    )

    assert str(result["target_default"].dtype) == "Int64"
