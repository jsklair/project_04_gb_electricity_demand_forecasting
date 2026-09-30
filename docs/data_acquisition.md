# NESO data acquisition

**Status:** This document records the completed source-acquisition milestone. Later BigQuery, dbt and modelling stages are complete and are described elsewhere in the repository.

## Purpose

Project 04 uses reproducible acquisition scripts to retrieve the required NESO demand and day-ahead forecast data directly from the NESO Data Portal API.

Raw downloaded files are deliberately excluded from Git. The repository contains the source configuration, acquisition code and validation logic needed to reproduce them.

## Sources

The configured sources are:

- NESO Day Ahead Half Hourly Demand Forecast Performance
- NESO Historic Demand Data for 2021
- NESO Historic Demand Data for 2022
- NESO Historic Demand Data for 2023
- NESO Historic Demand Data for 2024
- NESO Historic Demand Data for 2025
- NESO Historic Demand Data for 2026

Resource IDs are stored in `config/neso_sources.json`.

## Acquisition

Run the complete acquisition with `python src/acquire_neso.py`.

For a small connectivity or schema smoke test, run `python src/acquire_neso.py --limit 5`.

The acquisition script:

1. reads the configured NESO resource IDs;
2. calls the NESO CKAN datastore_search API;
3. paginates through each resource;
4. writes raw CSV snapshots to `data/raw/`;
5. writes a local acquisition manifest containing resource IDs, row counts and retrieval timestamps.

`data/raw/` is excluded from Git apart from `.gitkeep`.

## Validation

Run `python src/validate_neso.py`.

The validator checks:

- required fields;
- parseable settlement dates;
- date coverage;
- missing required values;
- duplicate date/settlement-period combinations;
- conflicting duplicate records;
- settlement-day row counts.

It also supports the differing date formats found in the annual NESO historic-demand files.

## Initial source observations

The first full acquisition produced:

| Source | Rows | Date coverage |
| --- | ---: | --- |
| Day-ahead forecast performance | 95,921 | 2021-04-01 to 2026-09-23 |
| Historic demand 2021 | 17,520 | 2021-01-01 to 2021-12-31 |
| Historic demand 2022 | 17,520 | 2022-01-01 to 2022-12-31 |
| Historic demand 2023 | 17,520 | 2023-01-01 to 2023-12-31 |
| Historic demand 2024 | 17,568 | 2024-01-01 to 2024-12-31 |
| Historic demand 2025 | 17,520 | 2025-01-01 to 2025-12-31 |
| Historic demand 2026 | 11,758 | 2026-01-01 to 2026-09-02 |

Completed historic-demand years contain the expected daylight-saving structure: one 46-period day, one 50-period day and otherwise 48-period days.

The forecast-performance source contains four conflicting duplicate date/settlement-period combinations:

- 2021-10-31, settlement period 4;
- 2021-10-31, settlement period 5;
- 2022-10-30, settlement period 2;
- 2022-10-30, settlement period 3.

In each case the duplicated records contain different forecast values. These records are retained and reported rather than arbitrarily deduplicated during acquisition.

The acquisition snapshot documented at this milestone contained only 19 forecast-performance rows for 2026-09-23. That partial latest day was retained as a source-quality observation rather than treated as a complete comparison date.

Historic-demand schemas also vary between years. In particular, `FORECAST_ACTUAL_INDICATOR` is present in the 2026 resource but not in the earlier annual resources. Validation therefore checks the common fields required for this project rather than assuming every annual schema is identical.

## Subsequent project stage

After this acquisition milestone, the reproducible raw sources were loaded into BigQuery and the production dbt source and staging layers were built. Those later stages are complete in the finished project; this document is retained as the record of the acquisition milestone and its source-quality findings.
