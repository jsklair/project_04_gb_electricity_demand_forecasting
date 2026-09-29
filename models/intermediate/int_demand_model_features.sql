with demand as (

    select
        settlement_date,
        settlement_period,
        national_demand_mw
    from {{ ref('stg_neso_historic_demand') }}

),

features as (

    select
        cur.settlement_date,
        cur.settlement_period,
        cur.national_demand_mw,

        extract(year from cur.settlement_date) as calendar_year,
        extract(month from cur.settlement_date) as calendar_month,
        extract(dayofweek from cur.settlement_date) as day_of_week,
        extract(dayofyear from cur.settlement_date) as day_of_year,

        extract(dayofweek from cur.settlement_date) in (1, 7)
            as is_weekend,

        lag_2d.national_demand_mw as demand_lag_2d_mw,
        lag_7d.national_demand_mw as demand_lag_7d_mw,
        lag_14d.national_demand_mw as demand_lag_14d_mw,

        case
            when cur.settlement_date < date '2024-01-01'
                then 'development'
            when cur.settlement_date < date '2025-01-01'
                then 'validation'
            when cur.settlement_date < date '2026-01-01'
                then 'final_test'
            else 'robustness'
        end as evaluation_split

    from demand as cur

    left join demand as lag_2d
        on lag_2d.settlement_date = date_sub(cur.settlement_date, interval 2 day)
        and lag_2d.settlement_period = cur.settlement_period

    left join demand as lag_7d
        on lag_7d.settlement_date = date_sub(cur.settlement_date, interval 7 day)
        and lag_7d.settlement_period = cur.settlement_period

    left join demand as lag_14d
        on lag_14d.settlement_date = date_sub(cur.settlement_date, interval 14 day)
        and lag_14d.settlement_period = cur.settlement_period

)

select *
from features