---
title: Project 04
---

# Great Britain Day-Ahead Electricity Demand Forecasting

A leakage-aware forecasting case study using National Energy System Operator (NESO) electricity-demand data, BigQuery, dbt and Python.

The question is straightforward:

> Using only information that would have been available when the day-ahead forecast was issued, how accurately can a transparent model forecast Great Britain National Demand for each half-hourly settlement period, where are its errors concentrated, and how does it compare with a seasonal benchmark and NESO's operational day-ahead forecast?

## Headline result

On the untouched 2025 final test, histogram gradient boosting reduced mean absolute error by **27.7%** compared with a 7-day seasonal naïve benchmark and by **4.4%** compared with the final linear regression benchmark.

NESO's operational day-ahead forecast remained substantially more accurate.

| Forecast | MAE (MW) |
|---|---:|
| Seasonal naïve, 7-day lag | 2,178.73 |
| Linear regression | 1,648.63 |
| Histogram gradient boosting | 1,575.51 |
| NESO operational forecast | **678.94** |

All four forecasts are scored against the same historic National Demand target and the same 17,512 eligible 2025 settlement periods.

![2025 final-test forecast accuracy](https://raw.githubusercontent.com/jsklair/project_04_gb_electricity_demand_forecasting/main/outputs/figures/01_final_test_mae.png)

The portfolio model materially improves on the simple benchmarks, but a large gap remains between it and NESO's operational forecast.

## Where the errors occur

The headline MAE hides useful structure.

Gradient boosting has lower MAE than the linear model in every month of the 2025 final test. January is the least accurate month for both portfolio models.

![Monthly forecast accuracy](https://raw.githubusercontent.com/jsklair/project_04_gb_electricity_demand_forecasting/main/outputs/figures/02_monthly_mae_2025.png)

There is also a clear within-day pattern. Gradient-boosting error is highest around settlement periods 25–29, roughly **12:00–14:30** on a standard 48-period day.

![Settlement-period forecast accuracy](https://raw.githubusercontent.com/jsklair/project_04_gb_electricity_demand_forecasting/main/outputs/figures/03_settlement_period_mae_2025.png)

Some individual days are much harder than the average suggests.

The worst gradient-boosting day in 2025 was **8 January**, with daily MAE of approximately **5,662 MW**.

The first panel below is not hand-picked as a flattering example. It is selected mechanically as the day whose gradient-boosting MAE is nearest the 2025 daily median.

![Near-median and worst forecast days](https://raw.githubusercontent.com/jsklair/project_04_gb_electricity_demand_forecasting/main/outputs/figures/04_daily_forecast_examples_2025.png)

These patterns are descriptive. I have not attributed the large January errors to weather, system events or other causes without supporting evidence.

## Does the result persist?

After the 2025 final test was complete, the frozen model specifications were refitted using all available 2021–2025 history and evaluated separately on a fixed 2026 robustness window.

Across all 11,752 model-eligible settlement periods from 1 January to 2 September 2026:

| Forecast | MAE (MW) |
|---|---:|
| Seasonal naïve, 7-day lag | 2,146.38 |
| Linear regression | 1,686.67 |
| Histogram gradient boosting | **1,597.45** |

NESO forecasts are unavailable for the 48 settlement periods on 2 September in the captured comparison data.

On the common 11,704-row sample through 1 September:

| Forecast | MAE (MW) |
|---|---:|
| Seasonal naïve, 7-day lag | 2,146.05 |
| Linear regression | 1,682.79 |
| Histogram gradient boosting | 1,593.92 |
| NESO operational forecast | **789.97** |

The ordering of the three portfolio models therefore remains stable in the later period. NESO's MAE is **50.4% lower** than gradient boosting on the common sample.

## Validation design

The project uses chronological validation rather than a random train/test split.

| Period | Role |
|---|---|
| 2021–2023 | Development |
| 2024 | Validation and model selection |
| 2025 | Untouched final test |
| 2026 | Separate robustness period |

The final model progression was deliberately limited to:

1. a 7-day seasonal naïve benchmark;
2. ordinary linear regression;
3. one histogram gradient-boosting challenger.

No feature, model-family or hyperparameter changes were made after the 2025 final test was opened.

## Leakage control

The governing question throughout the modelling work was:

> Would this exact information genuinely have been available when the day-ahead forecast was issued?

That has practical consequences.

A 1-day demand lag is not used because the previous day's complete demand profile would not always have been available when the day-ahead forecast was issued.

Observed target-day weather is also excluded because realised future weather would give the model information that a genuine forecaster would not have had.

The final models use calendar information, bank-holiday indicators and same-period demand lags at 2, 7 and 14 days.

The historic lag values carry an explicit limitation: the project does not reconstruct the exact publication vintage of every historical demand observation.

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

Legitimate 46-, 48- and 50-period daylight-saving days are preserved rather than forced into a standard 48-period structure.

NESO's operational forecast is recalculated against the same historic National Demand target used for the portfolio models, providing a like-for-like comparison.

## Limitations

This is deliberately a constrained analytical benchmark rather than an attempt to recreate NESO's production forecasting system.

The main limitations are:

- the feature set is intentionally narrow;
- archived target-day weather forecasts are not included;
- exact historical publication vintages of lagged demand observations are not reconstructed;
- unusual operational or behavioural events are not explicitly modelled;
- the 2026 robustness period covers only part of the year;
- observed error patterns do not establish their underlying cause.

## Technical implementation

The project uses:

**Python · pandas · scikit-learn · Matplotlib · SQL · BigQuery · dbt · Git/GitHub**

The repository contains reproducible source acquisition, validation, warehouse loading, dbt models, leakage controls, model validation, final-test analysis, robustness analysis and publication outputs.

[View the full GitHub repository](https://github.com/jsklair/project_04_gb_electricity_demand_forecasting)

[Read the detailed README](https://github.com/jsklair/project_04_gb_electricity_demand_forecasting#readme)
