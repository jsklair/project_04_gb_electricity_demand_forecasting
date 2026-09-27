# dbt source layer

## Purpose

The production dbt project sits between the reproducible BigQuery raw layer and the analytical staging models used later in the forecasting pipeline.

This milestone establishes dbt against the real Project 04 BigQuery environment without introducing transformation logic prematurely.

## Environment

The production dbt project uses:

- dbt Core 1.12.5
- dbt BigQuery 1.12.0
- Python 3.13.14
- Google Cloud project `gb-demand-forecasting-p04`
- BigQuery location `EU`

The dbt profile uses local OAuth authentication.

`profiles.yml` is deliberately excluded from Git because authentication and local environment settings should not be committed to the public repository.

## Raw source

dbt reads from:

`gb-demand-forecasting-p04.p04_raw`

Seven source tables are defined under the `neso_raw` source:

- `forecast_performance`
- `historic_demand_2021`
- `historic_demand_2022`
- `historic_demand_2023`
- `historic_demand_2024`
- `historic_demand_2025`
- `historic_demand_2026`

The dbt source names are stable analytical references. Their `identifier` properties map them to the physical BigQuery tables prefixed with `raw_`.

## Source tests

The source layer currently applies deliberately modest `not_null` tests to fields that are required for later transformation.

Forecast-performance tests cover:

- `Date`
- `Settlement_Period`
- `Demand_Forecast`
- `Demand_Outturn`
- `Publish_Datetime`

Each annual historic-demand table tests:

- `SETTLEMENT_DATE`
- `SETTLEMENT_PERIOD`
- `ND`

Uniqueness is intentionally not asserted at the raw source layer. Earlier validation identified conflicting duplicate date/settlement-period grains in the NESO forecast-performance source, and those records should not be silently hidden by a generic source constraint.

The first production run completed:

`PASS=23 WARN=0 ERROR=0 SKIP=0`

## Next stage

The next milestone is the staging layer.

That work will:

- parse raw STRING fields into deliberate data types;
- standardise the different historic-demand date formats;
- reconcile annual schema changes;
- preserve 46- and 50-period daylight-saving days;
- make explicit decisions about the known forecast-source duplicate grains;
- prepare clean, documented inputs for later analytical/core models.
