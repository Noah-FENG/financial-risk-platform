with parameters as (
    -- The exact source snapshot date is undocumented. March 2019 is used as
    -- a month-level assumption because it is the latest observed payment month.
    select date '2019-03-01' as snapshot_month
),

source_loans as (
    select
        id as loan_id,
        issue_d,
        term_months,
        funded_amnt,
        loan_status,
        out_prncp,
        total_pymnt,
        total_rec_prncp,
        total_rec_int,
        total_rec_late_fee,
        recoveries,
        collection_recovery_fee,
        last_pymnt_d,
        last_pymnt_amnt
    from {{ ref('stg_loans') }}
),

observation_window as (
    select
        source_loans.*,
        parameters.snapshot_month,
        date_diff('month', issue_d, parameters.snapshot_month) as observation_months
    from source_loans
    cross join parameters
),

maturity as (
    select
        *,
        observation_months >= term_months as is_matured
    from observation_window
),

classified as (
    select
        *,
        is_matured
            and loan_status in ('Fully Paid', 'Charged Off', 'Default')
            as is_pd_eligible,
        case
            when loan_status = 'Fully Paid' then 'fully_paid'
            when loan_status in ('Charged Off', 'Default') then 'default'
        end as terminal_outcome,
        recoveries - collection_recovery_fee as net_recoveries
    from maturity
),

losses as (
    select
        *,
        case
            when terminal_outcome is not null then greatest(
                funded_amnt - total_rec_prncp - net_recoveries,
                0
            )
        end as realized_net_principal_loss
    from classified
)

select
    loan_id,
    loan_status,
    terminal_outcome,
    snapshot_month,
    observation_months,
    is_matured,
    is_pd_eligible,
    not is_pd_eligible as is_censored,
    case
        when is_pd_eligible and terminal_outcome = 'default' then 1
        when is_pd_eligible and terminal_outcome = 'fully_paid' then 0
    end as target_default,
    case
        when terminal_outcome = 'default' and last_pymnt_d is not null
            then date_diff('month', issue_d, last_pymnt_d)
    end as approx_default_age_months,
    out_prncp,
    total_pymnt,
    total_rec_prncp,
    total_rec_int,
    total_rec_late_fee,
    recoveries,
    collection_recovery_fee,
    net_recoveries,
    realized_net_principal_loss,
    case
        when funded_amnt > 0 and realized_net_principal_loss is not null
            then realized_net_principal_loss / funded_amnt
    end as realized_net_principal_loss_rate,
    last_pymnt_d,
    last_pymnt_amnt
from losses
