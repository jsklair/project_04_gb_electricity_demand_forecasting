# Source and Architecture Specification

## Primary sources

### NESO Day Ahead Half Hourly Demand Forecast Performance

Resource ID:

`08e41551-80f8-4e28-a416-ea473a695db9`

Key fields confirmed through the live API:

- `Date`
- `Datetime`
- `Settlement_Period`
- `Demand_Forecast`
- `Demand_Outturn`
- `TRIAD_Avoidance_Estimate`
- `TRIAD_Avoidance_Corrected_Demand_Outturn`
- `APE`
- `Absolute_Error`
- `Publish_Datetime`

`Publish_Datetime` will be treated as the key information timestamp when determining whether a forecasting feature was available at issue time.

A source-validation check confirmed that NESO's published `Absolute_Error` and `APE` use the TRIAD-avoidance-corrected demand outturn when the adjustment is non-zero.

### NESO Historic Demand Data

The project will use NESO annual Historic Demand resources for the required historical period.

The 2026 resource used during source validation was:

`8a4a771c-3929-4e56-93ad-cdf13219dea5`

Relevant fields include:

- `SETTLEMENT_DATE`
- `SETTLEMENT_PERIOD`
- `ND`
- `FORECAST_ACTUAL_INDICATOR`

Historic demand may be revised after initial publication. The project will therefore record source/resource metadata and will not claim perfect historical-vintage reconstruction where it cannot be demonstrated.

NESO has also documented a 2026 forecasting-system change and a known Scottish-transfer-data issue. This will be treated as a robustness and data-quality consideration rather than silently ignored.

## Settlement-period validation

Live source checks confirmed:

- 31 October 2021: 50 settlement periods;
- 27 March 2022: 46 settlement periods.

The pipeline must therefore preserve genuine daylight-saving settlement structures rather than forcing every day to 48 rows.

## Proposed architecture

NESO public APIs
→ Python acquisition
→ BigQuery raw/source tables
→ dbt staging and core transformations
→ feature and evaluation marts
→ Python forecasting and evaluation
→ public charts, findings and documentation

## BigQuery and dbt feasibility

A separate local proof of concept was completed before this repository was created.

It demonstrated:

- BigQuery connectivity;
- dbt authentication;
- successful dbt model execution;
- creation and querying of a BigQuery view;
- three `not_null` tests;
- one settlement-date/settlement-period grain test;
- final dbt test result of 4 passes, 0 warnings and 0 errors.

BigQuery and dbt are therefore retained for the main project.

## Leakage control

A feature register will record:

| Feature | Source | Information timestamp | Available at forecast issue? | Decision | Rationale |
| --- | --- | --- | --- | --- | --- |

Observed future information will not be used as a forecasting feature.

Demand lags will only be included where the required observation would definitely have been available by the relevant forecast publication time.

## External calendar data

UK bank-holiday data may be added from GOV.UK if profiling shows that it is useful.

England and Wales and Scotland will be treated separately where relevant.

## Weather

Weather is not part of the initial minimum viable model.

It will only be added if there is a clear analytical reason and if archived forecast data available at the forecast issue time can be sourced. Observed future weather would constitute leakage and will not be used.
