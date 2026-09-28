-- The annual NESO files represent one logical historic-demand dataset, but
-- their date formats and available columns change over time. Each branch
-- standardises the raw strings while preserving every source row.

with demand_2021 as (

    select
        2021 as source_year,
        safe_cast(_id as int64) as source_row_id,
        safe.parse_date('%d-%b-%Y', SETTLEMENT_DATE) as settlement_date,
        safe_cast(SETTLEMENT_PERIOD as int64) as settlement_period,
        safe_cast(ND as float64) as national_demand_mw,
        safe_cast(TSD as float64) as total_system_demand_mw,
        safe_cast(ENGLAND_WALES_DEMAND as float64) as england_wales_demand_mw,
        safe_cast(EMBEDDED_WIND_GENERATION as float64) as embedded_wind_generation_mw,
        safe_cast(EMBEDDED_WIND_CAPACITY as float64) as embedded_wind_capacity_mw,
        safe_cast(EMBEDDED_SOLAR_GENERATION as float64) as embedded_solar_generation_mw,
        safe_cast(EMBEDDED_SOLAR_CAPACITY as float64) as embedded_solar_capacity_mw,
        safe_cast(NON_BM_STOR as float64) as non_bm_storage_mw,
        safe_cast(PUMP_STORAGE_PUMPING as float64) as pump_storage_pumping_mw,
        cast(null as float64) as scottish_transfer_mw,
        safe_cast(IFA_FLOW as float64) as ifa_flow_mw,
        safe_cast(IFA2_FLOW as float64) as ifa2_flow_mw,
        safe_cast(BRITNED_FLOW as float64) as britned_flow_mw,
        safe_cast(MOYLE_FLOW as float64) as moyle_flow_mw,
        safe_cast(EAST_WEST_FLOW as float64) as east_west_flow_mw,
        safe_cast(NEMO_FLOW as float64) as nemo_flow_mw,
        safe_cast(NSL_FLOW as float64) as nsl_flow_mw,
        safe_cast(ELECLINK_FLOW as float64) as eleclink_flow_mw,
        safe_cast(VIKING_FLOW as float64) as viking_flow_mw,
        safe_cast(GREENLINK_FLOW as float64) as greenlink_flow_mw,
        cast(null as string) as forecast_actual_indicator
    from {{ source('neso_raw', 'historic_demand_2021') }}

),

demand_2022 as (

    select
        2022 as source_year,
        safe_cast(_id as int64) as source_row_id,
        safe.parse_date('%d-%b-%Y', SETTLEMENT_DATE) as settlement_date,
        safe_cast(SETTLEMENT_PERIOD as int64) as settlement_period,
        safe_cast(ND as float64) as national_demand_mw,
        safe_cast(TSD as float64) as total_system_demand_mw,
        safe_cast(ENGLAND_WALES_DEMAND as float64) as england_wales_demand_mw,
        safe_cast(EMBEDDED_WIND_GENERATION as float64) as embedded_wind_generation_mw,
        safe_cast(EMBEDDED_WIND_CAPACITY as float64) as embedded_wind_capacity_mw,
        safe_cast(EMBEDDED_SOLAR_GENERATION as float64) as embedded_solar_generation_mw,
        safe_cast(EMBEDDED_SOLAR_CAPACITY as float64) as embedded_solar_capacity_mw,
        safe_cast(NON_BM_STOR as float64) as non_bm_storage_mw,
        safe_cast(PUMP_STORAGE_PUMPING as float64) as pump_storage_pumping_mw,
        cast(null as float64) as scottish_transfer_mw,
        safe_cast(IFA_FLOW as float64) as ifa_flow_mw,
        safe_cast(IFA2_FLOW as float64) as ifa2_flow_mw,
        safe_cast(BRITNED_FLOW as float64) as britned_flow_mw,
        safe_cast(MOYLE_FLOW as float64) as moyle_flow_mw,
        safe_cast(EAST_WEST_FLOW as float64) as east_west_flow_mw,
        safe_cast(NEMO_FLOW as float64) as nemo_flow_mw,
        safe_cast(NSL_FLOW as float64) as nsl_flow_mw,
        safe_cast(ELECLINK_FLOW as float64) as eleclink_flow_mw,
        safe_cast(VIKING_FLOW as float64) as viking_flow_mw,
        safe_cast(GREENLINK_FLOW as float64) as greenlink_flow_mw,
        cast(null as string) as forecast_actual_indicator
    from {{ source('neso_raw', 'historic_demand_2022') }}

),

demand_2023 as (

    select
        2023 as source_year,
        safe_cast(_id as int64) as source_row_id,
        safe.parse_date('%d-%b-%y', SETTLEMENT_DATE) as settlement_date,
        safe_cast(SETTLEMENT_PERIOD as int64) as settlement_period,
        safe_cast(ND as float64) as national_demand_mw,
        safe_cast(TSD as float64) as total_system_demand_mw,
        safe_cast(ENGLAND_WALES_DEMAND as float64) as england_wales_demand_mw,
        safe_cast(EMBEDDED_WIND_GENERATION as float64) as embedded_wind_generation_mw,
        safe_cast(EMBEDDED_WIND_CAPACITY as float64) as embedded_wind_capacity_mw,
        safe_cast(EMBEDDED_SOLAR_GENERATION as float64) as embedded_solar_generation_mw,
        safe_cast(EMBEDDED_SOLAR_CAPACITY as float64) as embedded_solar_capacity_mw,
        safe_cast(NON_BM_STOR as float64) as non_bm_storage_mw,
        safe_cast(PUMP_STORAGE_PUMPING as float64) as pump_storage_pumping_mw,
        safe_cast(SCOTTISH_TRANSFER as float64) as scottish_transfer_mw,
        safe_cast(IFA_FLOW as float64) as ifa_flow_mw,
        safe_cast(IFA2_FLOW as float64) as ifa2_flow_mw,
        safe_cast(BRITNED_FLOW as float64) as britned_flow_mw,
        safe_cast(MOYLE_FLOW as float64) as moyle_flow_mw,
        safe_cast(EAST_WEST_FLOW as float64) as east_west_flow_mw,
        safe_cast(NEMO_FLOW as float64) as nemo_flow_mw,
        safe_cast(NSL_FLOW as float64) as nsl_flow_mw,
        safe_cast(ELECLINK_FLOW as float64) as eleclink_flow_mw,
        safe_cast(VIKING_FLOW as float64) as viking_flow_mw,
        safe_cast(GREENLINK_FLOW as float64) as greenlink_flow_mw,
        cast(null as string) as forecast_actual_indicator
    from {{ source('neso_raw', 'historic_demand_2023') }}

),

demand_2024 as (

    select
        2024 as source_year,
        safe_cast(_id as int64) as source_row_id,
        safe_cast(SETTLEMENT_DATE as date) as settlement_date,
        safe_cast(SETTLEMENT_PERIOD as int64) as settlement_period,
        safe_cast(ND as float64) as national_demand_mw,
        safe_cast(TSD as float64) as total_system_demand_mw,
        safe_cast(ENGLAND_WALES_DEMAND as float64) as england_wales_demand_mw,
        safe_cast(EMBEDDED_WIND_GENERATION as float64) as embedded_wind_generation_mw,
        safe_cast(EMBEDDED_WIND_CAPACITY as float64) as embedded_wind_capacity_mw,
        safe_cast(EMBEDDED_SOLAR_GENERATION as float64) as embedded_solar_generation_mw,
        safe_cast(EMBEDDED_SOLAR_CAPACITY as float64) as embedded_solar_capacity_mw,
        safe_cast(NON_BM_STOR as float64) as non_bm_storage_mw,
        safe_cast(PUMP_STORAGE_PUMPING as float64) as pump_storage_pumping_mw,
        safe_cast(SCOTTISH_TRANSFER as float64) as scottish_transfer_mw,
        safe_cast(IFA_FLOW as float64) as ifa_flow_mw,
        safe_cast(IFA2_FLOW as float64) as ifa2_flow_mw,
        safe_cast(BRITNED_FLOW as float64) as britned_flow_mw,
        safe_cast(MOYLE_FLOW as float64) as moyle_flow_mw,
        safe_cast(EAST_WEST_FLOW as float64) as east_west_flow_mw,
        safe_cast(NEMO_FLOW as float64) as nemo_flow_mw,
        safe_cast(NSL_FLOW as float64) as nsl_flow_mw,
        safe_cast(ELECLINK_FLOW as float64) as eleclink_flow_mw,
        safe_cast(VIKING_FLOW as float64) as viking_flow_mw,
        safe_cast(GREENLINK_FLOW as float64) as greenlink_flow_mw,
        cast(null as string) as forecast_actual_indicator
    from {{ source('neso_raw', 'historic_demand_2024') }}

),

demand_2025 as (

    select
        2025 as source_year,
        safe_cast(_id as int64) as source_row_id,
        safe_cast(SETTLEMENT_DATE as date) as settlement_date,
        safe_cast(SETTLEMENT_PERIOD as int64) as settlement_period,
        safe_cast(ND as float64) as national_demand_mw,
        safe_cast(TSD as float64) as total_system_demand_mw,
        safe_cast(ENGLAND_WALES_DEMAND as float64) as england_wales_demand_mw,
        safe_cast(EMBEDDED_WIND_GENERATION as float64) as embedded_wind_generation_mw,
        safe_cast(EMBEDDED_WIND_CAPACITY as float64) as embedded_wind_capacity_mw,
        safe_cast(EMBEDDED_SOLAR_GENERATION as float64) as embedded_solar_generation_mw,
        safe_cast(EMBEDDED_SOLAR_CAPACITY as float64) as embedded_solar_capacity_mw,
        safe_cast(NON_BM_STOR as float64) as non_bm_storage_mw,
        safe_cast(PUMP_STORAGE_PUMPING as float64) as pump_storage_pumping_mw,
        safe_cast(SCOTTISH_TRANSFER as float64) as scottish_transfer_mw,
        safe_cast(IFA_FLOW as float64) as ifa_flow_mw,
        safe_cast(IFA2_FLOW as float64) as ifa2_flow_mw,
        safe_cast(BRITNED_FLOW as float64) as britned_flow_mw,
        safe_cast(MOYLE_FLOW as float64) as moyle_flow_mw,
        safe_cast(EAST_WEST_FLOW as float64) as east_west_flow_mw,
        safe_cast(NEMO_FLOW as float64) as nemo_flow_mw,
        safe_cast(NSL_FLOW as float64) as nsl_flow_mw,
        safe_cast(ELECLINK_FLOW as float64) as eleclink_flow_mw,
        safe_cast(VIKING_FLOW as float64) as viking_flow_mw,
        safe_cast(GREENLINK_FLOW as float64) as greenlink_flow_mw,
        cast(null as string) as forecast_actual_indicator
    from {{ source('neso_raw', 'historic_demand_2025') }}

),

demand_2026 as (

    select
        2026 as source_year,
        safe_cast(_id as int64) as source_row_id,
        safe_cast(SETTLEMENT_DATE as date) as settlement_date,
        safe_cast(SETTLEMENT_PERIOD as int64) as settlement_period,
        safe_cast(ND as float64) as national_demand_mw,
        safe_cast(TSD as float64) as total_system_demand_mw,
        safe_cast(ENGLAND_WALES_DEMAND as float64) as england_wales_demand_mw,
        safe_cast(EMBEDDED_WIND_GENERATION as float64) as embedded_wind_generation_mw,
        safe_cast(EMBEDDED_WIND_CAPACITY as float64) as embedded_wind_capacity_mw,
        safe_cast(EMBEDDED_SOLAR_GENERATION as float64) as embedded_solar_generation_mw,
        safe_cast(EMBEDDED_SOLAR_CAPACITY as float64) as embedded_solar_capacity_mw,
        safe_cast(NON_BM_STOR as float64) as non_bm_storage_mw,
        safe_cast(PUMP_STORAGE_PUMPING as float64) as pump_storage_pumping_mw,
        safe_cast(SCOTTISH_TRANSFER as float64) as scottish_transfer_mw,
        safe_cast(IFA_FLOW as float64) as ifa_flow_mw,
        safe_cast(IFA2_FLOW as float64) as ifa2_flow_mw,
        safe_cast(BRITNED_FLOW as float64) as britned_flow_mw,
        safe_cast(MOYLE_FLOW as float64) as moyle_flow_mw,
        safe_cast(EAST_WEST_FLOW as float64) as east_west_flow_mw,
        safe_cast(NEMO_FLOW as float64) as nemo_flow_mw,
        safe_cast(NSL_FLOW as float64) as nsl_flow_mw,
        safe_cast(ELECLINK_FLOW as float64) as eleclink_flow_mw,
        safe_cast(VIKING_FLOW as float64) as viking_flow_mw,
        safe_cast(GREENLINK_FLOW as float64) as greenlink_flow_mw,
        FORECAST_ACTUAL_INDICATOR as forecast_actual_indicator
    from {{ source('neso_raw', 'historic_demand_2026') }}

)

select * from demand_2021
union all
select * from demand_2022
union all
select * from demand_2023
union all
select * from demand_2024
union all
select * from demand_2025
union all
select * from demand_2026