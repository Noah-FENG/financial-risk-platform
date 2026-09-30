select id as loan_id,
        loan_amnt,
        funded_amnt,
        term_months,
        installment,
        int_rate,
        int_rate_decimal,
        grade,
        sub_grade,
        purpose
from {{ref('stg_loans')}}