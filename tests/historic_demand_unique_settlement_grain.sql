select
    settlement_date,
    settlement_period,
    count(*) as row_count
from {{ ref('stg_neso_historic_demand') }}
group by
    settlement_date,
    settlement_period
having count(*) > 1