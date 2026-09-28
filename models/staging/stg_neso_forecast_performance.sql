select
    safe_cast(_id as int64) as source_row_id,
    Month as month_name,
    safe_cast(Date as date) as settlement_date,
    safe_cast(Datetime as datetime) as settlement_datetime,
    safe_cast(Settlement_Period as int64) as settlement_period,
    safe_cast(Demand_Forecast as float64) as demand_forecast_mw,
    safe_cast(Demand_Outturn as float64) as demand_outturn_mw,
    safe_cast(TRIAD_Avoidance_Estimate as float64) as triad_avoidance_estimate_mw,
    safe_cast(TRIAD_Avoidance_Corrected_Demand_Outturn as float64)
        as triad_corrected_demand_outturn_mw,
    safe_cast(APE as float64) as neso_ape,
    safe_cast(Absolute_Error as float64) as neso_absolute_error_mw,
    safe_cast(Publish_Datetime as datetime) as publish_datetime
from {{ source('neso_raw', 'forecast_performance') }}