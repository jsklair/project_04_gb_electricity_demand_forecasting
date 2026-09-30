---
title: Project 04
---

# Great Britain Day-Ahead Electricity Demand Forecasting

This project tests how accurately Great Britain's electricity demand can be forecast **half-hour by half-hour, one day ahead**.

The model is only allowed to use information that could genuinely have been available when each forecast was issued. This prevents **data leakage**, where a model accidentally benefits from information from the future.

The analysis uses electricity-demand data from the **National Energy System Operator (NESO)** and a reproducible pipeline built with BigQuery, dbt and Python.

## A few terms before the results

**National Demand**  
NESO's measure of Great Britain's electricity generation requirement, measured in megawatts.

**Settlement period**  
One half-hour interval. A normal day contains 48 settlement periods, although UK clock-change days can contain 46 or 50.

**MW**  
Megawatts, the unit used for both electricity demand and forecast error in this analysis.

**MAE — mean absolute error**  
The average size of a forecast miss, regardless of whether the forecast was too high or too low. Lower is better.

**Benchmark**  
A simple reference forecast used to test whether a more sophisticated model genuinely improves accuracy.

**Data leakage**  
Using information that would not actually have been available when the forecast was made.

## The question

Using only information that would have been available when the day-ahead forecast was issued, how accurately can a deliberately constrained model forecast National Demand for each half-hour period, where are its errors concentrated, and how does it compare with a simple benchmark and NESO's operational forecast?

## What did the model achieve?

The best model built in the project was **histogram gradient boosting**, a non-linear tree-based machine-learning method.

On the untouched 2025 test period, it was about **1,576 MW away from actual National Demand on average**.

A simple forecast that just reused demand from the same half-hour one week earlier missed by about **2,179 MW** on average. Linear regression reduced this to about **1,649 MW**, and gradient boosting reduced it a little further to **1,576 MW**.

NESO's operational forecast was considerably more accurate, with an average absolute error of about **679 MW**.

| Forecast | Average absolute error |
|---|---:|
| Same half-hour one week earlier | 2,179 MW |
| Linear regression | 1,649 MW |
| Gradient boosting | 1,576 MW |
| NESO operational forecast | **679 MW** |

The gradient-boosting model therefore reduced average error by **27.7%** compared with the simple one-week benchmark, but only by **4.4%** compared with linear regression.

That distinction matters: most of the gain came from moving beyond the simple benchmark. The more complex non-linear model added a smaller improvement beyond the linear model.

NESO's average error was **56.9% lower** than the gradient-boosting model's. The project model is therefore an independently reproducible benchmark and analytical case study rather than a substitute for NESO's operational forecasting process.

All four forecasts are evaluated against the same historic National Demand target and the same 17,512 half-hour records.

![2025 final-test forecast accuracy](https://raw.githubusercontent.com/jsklair/project_04_gb_electricity_demand_forecasting/main/outputs/figures/01_final_test_mae.png)

## Where do the errors occur?

The annual average hides a clear month-to-month pattern.

Gradient boosting has lower error than linear regression in every month of the 2025 test period. January is the least accurate month for both project models.

![Monthly forecast accuracy](https://raw.githubusercontent.com/jsklair/project_04_gb_electricity_demand_forecasting/main/outputs/figures/02_monthly_mae_2025.png)

There is also a clear pattern within the day.

Gradient-boosting error is highest around settlement periods 25–29, which corresponds to roughly **12:00–14:30** on a standard 48-period day.

![Settlement-period forecast accuracy](https://raw.githubusercontent.com/jsklair/project_04_gb_electricity_demand_forecasting/main/outputs/figures/03_settlement_period_mae_2025.png)

Some individual days are much harder than the annual average suggests.

The worst gradient-boosting day in 2025 was **8 January**, when the model missed actual demand by an average of approximately **5,662 MW** across the day.

The first panel below is not a hand-picked good example. It is selected mechanically as the day whose gradient-boosting error is nearest the median daily error for 2025.

![Near-median and worst forecast days](https://raw.githubusercontent.com/jsklair/project_04_gb_electricity_demand_forecasting/main/outputs/figures/04_daily_forecast_examples_2025.png)

These patterns are descriptive. I have not attributed the large January errors to weather, system events or other causes without supporting evidence.

## Does the result persist in later data?

I also ran a **robustness check**: a separate later-period test designed to see whether the main result still holds without changing the model after seeing the later data.

The fixed robustness window runs from **1 January to 2 September 2026**.

Across all 11,752 half-hour periods with the required model inputs:

| Forecast | Average absolute error |
|---|---:|
| Same half-hour one week earlier | 2,146 MW |
| Linear regression | 1,687 MW |
| Gradient boosting | **1,597 MW** |

There is no matching NESO forecast for the 48 model rows on 2 September in the captured comparison data.

For the 11,704 periods through 1 September where all four forecasts can be compared fairly:

| Forecast | Average absolute error |
|---|---:|
| Same half-hour one week earlier | 2,146 MW |
| Linear regression | 1,683 MW |
| Gradient boosting | 1,594 MW |
| NESO operational forecast | **790 MW** |

The same broad pattern holds in the later period: gradient boosting remains the most accurate of the three project models, but NESO remains considerably more accurate.

NESO's average absolute error is **50.4% lower** than gradient boosting on this common sample.

## How was the test kept fair?

Forecasting projects can look artificially accurate if future information is allowed to leak into the model.

The governing rule here was:

> Would this exact information genuinely have been available when the day-ahead forecast was issued?

That rule affects both the train/test design and the model inputs.

The data are divided chronologically:

| Period | Role |
|---|---|
| 2021–2023 | Model development |
| 2024 | Validation and model selection |
| 2025 | Untouched final test |
| 2026 | Separate later-period robustness check |

The features, model family and settings were fixed before the 2025 final test was examined.

A 1-day demand history feature was deliberately excluded because the previous day's complete demand profile would not always have been available when the day-ahead forecast was issued.

Observed target-day weather was also excluded because realised weather would give the model information from the future.

The final models use calendar information, bank-holiday indicators and demand from the same half-hour **2, 7 and 14 days earlier**.

The project does not reconstruct the exact historical publication vintage of every historic demand value, so later revisions to historical demand remain an explicit limitation.

## Data and analytical pipeline

The project combines several parts of a modern analytical workflow:

```text
NESO public API
        |
        v
Python acquisition and validation
        |
        v
BigQuery raw layer
        |
        v
dbt staging and modelling
        |
        v
analysis-ready forecasting data
        |
        v
Python model validation and evaluation
        |
        v
reproducible tables and figures
```

The pipeline preserves legitimate 46-, 48- and 50-period clock-change days rather than forcing every day into 48 rows.

NESO's operational forecast is rescored against the same historic National Demand target as the project models, giving a like-for-like comparison.

## Limitations

This is deliberately a constrained analytical benchmark rather than an attempt to recreate NESO's production forecasting system.

The main limitations are:

- the feature set is intentionally narrow;
- archived target-day weather forecasts are not included;
- exact historical publication vintages of lagged demand observations are not reconstructed;
- unusual operational or behavioural events are not explicitly modelled;
- the 2026 robustness period covers only part of the year;
- observed patterns in forecast error do not establish their underlying cause.

## Technical implementation

The project uses:

**Python · pandas · scikit-learn · Matplotlib · SQL · BigQuery · dbt · Git/GitHub**

The repository contains reproducible source acquisition, validation, warehouse loading, dbt models, leakage controls, model validation, final-test analysis, robustness analysis and publication outputs.

[View the full GitHub repository](https://github.com/jsklair/project_04_gb_electricity_demand_forecasting)

[Read the detailed README](https://github.com/jsklair/project_04_gb_electricity_demand_forecasting#readme)
