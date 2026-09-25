# BigQuery raw ingestion

## Purpose

The reproducible NESO CSV snapshots are loaded into a dedicated BigQuery raw dataset before any cleaning, type conversion or analytical transformation.

The raw layer deliberately preserves source values as supplied by NESO. Transformation and business logic belong downstream in dbt.

## BigQuery environment

Google Cloud project:

`gb-demand-forecasting-p04`

Raw dataset:

`p04_raw`

Location:

`EU`

Configuration is stored in `config/bigquery.json`.

## Python environment

The project uses Python 3.13.14.

Install the BigQuery dependency with:

`pip install -r requirements.txt`

Application Default Credentials are used for local authentication. Credentials are not stored in the repository.

## Loading the raw data

First acquire the NESO source files:

`python src/acquire_neso.py`

Then load them to BigQuery:

`python src/load_bigquery_raw.py`

The loader:

1. reads the configured NESO sources;
2. creates the `p04_raw` dataset if it does not already exist;
3. checks that the dataset is in the expected EU location;
4. creates one raw table per configured source;
5. loads every source field as STRING;
6. replaces the previous raw snapshot using `WRITE_TRUNCATE`;
7. compares each BigQuery table row count with its local CSV source;
8. stops with an error if the counts do not reconcile.

Loading source fields as STRING is intentional. The raw layer should preserve the supplied source representation rather than embed cleaning or type assumptions. Type conversion and standardisation will be handled explicitly in dbt staging models.

## Raw tables

The first successful full load created:

| BigQuery table | Rows | Columns |
| --- | ---: | ---: |
| `raw_forecast_performance` | 95,921 | 12 |
| `raw_historic_demand_2021` | 17,520 | 22 |
| `raw_historic_demand_2022` | 17,520 | 22 |
| `raw_historic_demand_2023` | 17,520 | 23 |
| `raw_historic_demand_2024` | 17,568 | 23 |
| `raw_historic_demand_2025` | 17,520 | 23 |
| `raw_historic_demand_2026` | 11,758 | 24 |

All seven local-to-BigQuery row-count checks passed.

The differing column counts across annual historic-demand resources reflect source-schema changes and are preserved in the raw layer rather than forced into a common schema prematurely.

## Next stage

The next stage is the production dbt layer:

- define the BigQuery raw tables as dbt sources;
- standardise dates, settlement periods and numeric fields in staging models;
- reconcile the varying annual historic-demand schemas;
- add dbt source and data-quality tests;
- preserve known source anomalies until their treatment is explicitly decided.
