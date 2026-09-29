select
    settlement_date,
    settlement_period,
    count(*) as row_count
from {{ ref('int_demand_model_features') }}
group by
    settlement_date,
    settlement_period
having count(*) > 1