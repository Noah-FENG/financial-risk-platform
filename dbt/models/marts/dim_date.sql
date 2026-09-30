with unique_months as (
    SELECT
        distinct issue_month
    from {{ ref('fact_origination') }}
    where issue_month is not null
),

parsed_dates as (
    select
        issue_month,
        cast(concat(issue_month,'-01') as date) as month_start_date
    from unique_months
)

select
    issue_month,
    month_start_date,
    extract(year from month_start_date) as year,
    extract(month from month_start_date) as month,
    quarter(month_start_date) as quarter,
    concat(year(month_start_date), '-Q', quarter(month_start_date)) as vintage_quarter
from parsed_dates
order by month_start_date