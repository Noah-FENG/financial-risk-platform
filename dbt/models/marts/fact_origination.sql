SELECT
    id as loan_id,
    issue_d,
    issue_month
from {{ref('stg_loans')}}