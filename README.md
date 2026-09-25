# Project 04: Great Britain Day-Ahead Electricity Demand Forecasting

An in-progress forecasting project using NESO electricity-demand data to test how well a transparent model can predict Great Britain National Demand at half-hourly settlement-period level.

## Analytical question

Using only information that would have been available when the day-ahead forecast was issued, how accurately can a transparent model forecast Great Britain National Demand for each half-hourly settlement period, where are its errors concentrated, and how does it compare with a seasonal benchmark and NESO's operational day-ahead forecast?

## Current status

Project setup, source validation, reproducible NESO data acquisition and BigQuery raw ingestion are complete.

The initial feasibility work confirmed:

- live NESO API access;
- usable day-ahead forecast and historic-demand resources;
- reliable forecast publication timestamps;
- correct handling of 46- and 50-period daylight-saving days;
- reconciliation of NESO's published forecast errors;
- BigQuery and dbt working together successfully for transformation and testing.

The next stage is building the production dbt source and staging layer over the BigQuery raw tables.

## Planned workflow

1. Acquire NESO source data through the public API.
2. Store raw source data in BigQuery with provenance metadata.
3. Use dbt for staging, validation and analytical transformation.
4. Build leakage-safe forecasting features.
5. Establish seasonal and naive forecasting baselines.
6. Fit a transparent forecasting model.
7. Compare model performance with NESO's operational day-ahead forecast.
8. Investigate where forecast errors are concentrated.
9. Publish a concise set of charts, findings and reproducible project documentation.

## Technology

- Python
- SQL
- BigQuery
- dbt
- Git and GitHub

## Data source

National Energy System Operator (NESO) Data Portal.

See [`docs/source_architecture.md`](docs/source_architecture.md) for the initial source and architecture specification.

## Project documentation

- [`docs/project_plan.md`](docs/project_plan.md)
- [`docs/source_architecture.md`](docs/source_architecture.md)
- [`docs/data_acquisition.md`](docs/data_acquisition.md)

This project is in active development.
