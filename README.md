# Great Britain Day-Ahead Electricity Demand Forecasting

A leakage-aware forecasting case study using National Energy System Operator (NESO) electricity-demand data, BigQuery, dbt and Python.

The aim is not to reproduce NESO's production forecasting system. It is to test how much useful day-ahead signal can be captured with a deliberately constrained, reproducible modelling approach using information that could reasonably have been available when the forecast was issued.

## Analytical question

> Using only information that would have been available when the day-ahead forecast was issued, how accurately can a transparent model forecast Great Britain National Demand for each half-hourly settlement period, where are its errors concentrated, and how does it compare with a seasonal benchmark and NESO's operational day-ahead forecast?

## Headline result

On the untouched 2025 final test, histogram gradient boosting reduced mean absolute error by **27.7%** versus a 7-day seasonal naïve benchmark and by **4.4%** versus the final linear regression benchmark.

NESO's operational day-ahead forecast remained substantially more accurate, with MAE of **679 MW** compared with **1,576 MW** for gradient boosting.

| Forecast | MAE (MW) | RMSE (MW) | Bias (MW) | MAPE |
|---|---:|---:|---:|---:|
| Seasonal naïve, 7-day lag | 2,178.73 | 2,917.34 | -42.43 | 8.439% |
| Linear regression | 1,648.63 | 2,137.38 | +43.59 | 6.568% |
| Histogram gradient boosting | 1,575.51 | 2,099.93 | -23.20 | 6.231% |
| NESO operational forecast | **678.94** | **910.91** | +14.13 | **2.688%** |

All four forecasts are scored against the same historic National Demand target and the same 17,512 eligible 2025 settlement periods.

![2025 final-test forecast accuracy](outputs/figures/01_final_test_mae.png)

The portfolio model materially improves on the simple benchmarks, but a large gap remains between it and NESO's operational forecast.

## Where the errors occur

The overall MAE also hides a clear month-to-month pattern.

Gradient boosting has lower MAE than the linear regression in every month of the 2025 final test. January is the least accurate month for both portfolio models.

![2025 forecast error by month](outputs/figures/02_monthly_mae_2025.png)

There is also a clear within-day pattern. Gradient-boosting error is highest around settlement periods 25–29, roughly 12:00–14:30 on a standard 48-period day.

![2025 forecast error by settlement period](outputs/figures/03_settlement_period_mae_2025.png)

There are also days with much larger errors. The worst gradient-boosting day in 2025 was 8 January, with daily MAE of approximately **5,662 MW**.

To avoid selecting an artificially flattering comparison day, the first panel below is chosen mechanically as the date whose gradient-boosting daily MAE is closest to the 2025 median.

![Near-median and worst gradient-boosting error days](outputs/figures/04_daily_forecast_examples_2025.png)

These patterns are descriptive. I have not attributed the large January errors to weather, system events or other causes without evidence that would support that conclusion.

## 2026 robustness check

After the 2025 final test was complete, the frozen model specifications were refitted using all available 2021–2025 history and evaluated separately on 2026 data.

The robustness window is fixed at **1 January to 2 September 2026**.

Across all 11,752 model-eligible settlement periods:

| Forecast | MAE (MW) |
|---|---:|
| Seasonal naïve, 7-day lag | 2,146.38 |
| Linear regression | 1,686.67 |
| Histogram gradient boosting | **1,597.45** |

NESO forecasts are unavailable for all 48 settlement periods on 2 September, so the four-way comparison uses the common **11,704-row** sample through 1 September:

| Forecast | MAE (MW) |
|---|---:|
| Seasonal naïve, 7-day lag | 2,146.05 |
| Linear regression | 1,682.79 |
| Histogram gradient boosting | 1,593.92 |
| NESO operational forecast | **789.97** |

The model ordering therefore remains stable in the later period. NESO's MAE is **50.4% lower** than gradient boosting on the common 2026 sample.

September contains only one common comparison day, so its monthly result should not be interpreted as representative of the month.

## Modelling approach

The modelling design was fixed around chronological validation rather than a random train/test split:

| Period | Role |
|---|---|
| 2021–2023 | Development |
| 2024 | Validation and model selection |
| 2025 | Untouched final test |
| 2026 | Separate robustness period |

The final model progression was deliberately limited to:

1. **7-day seasonal naïve benchmark**
2. **ordinary linear regression**
3. **one histogram gradient-boosting challenger**

The nonlinear model was included only after improving on the final dense linear benchmark during 2024 validation.

No feature, model-family or hyperparameter changes were made after the 2025 final test was opened.

### Final features

The models use:

- settlement period;
- day of week;
- calendar month;
- England/Wales bank-holiday status;
- Scotland bank-holiday status;
- equivalent bank-holiday flags for lagged dates;
- 2-day historic demand lag;
- 7-day historic demand lag;
- 14-day historic demand lag.

The gradient-boosting specification was frozen at:

```text
HistGradientBoostingRegressor(
    learning_rate=0.05,
    max_iter=200,
    max_leaf_nodes=31,
    l2_regularization=1.0,
    random_state=42
)
```

## Leakage control

The main modelling rule was simple:

> Would this exact information genuinely have been available when the day-ahead forecast was issued?

NESO's `Publish_Datetime` is retained through the staging layer as the forecast-origin timestamp used to reason about what information could legitimately have been available.

That ruled out several apparently useful predictors.

In particular, a 1-day demand lag was not used because the previous day's complete demand profile would not always have been available at forecast issue time.

Observed target-day weather was also excluded. Using realised future weather would give the model information unavailable to a genuine day-ahead forecaster. A future extension could use archived weather forecasts issued before the relevant forecast origin instead.

The 2-, 7- and 14-day historic-demand lags are treated as available historical information, although the project does not reconstruct the exact publication vintage of every historical demand observation. That remains an explicit limitation.

See [`docs/leakage_register.md`](docs/leakage_register.md) for the feature-level leakage decisions.

## Data pipeline

The project uses a reproducible warehouse-style workflow rather than analysing downloaded files directly.

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
dbt staging models
        |
        v
analysis-ready forecasting model
        |
        v
Python validation, final test and robustness analysis
        |
        v
reproducible tables and figures
```

Raw source fields are loaded into BigQuery before parsing and standardisation in dbt. The staging layer handles year-specific source differences explicitly and preserves legitimate 46-, 48- and 50-period daylight-saving days.

The final modelling layer has one row per settlement date and settlement period with the target, calendar fields, leakage-safe lag features and chronological evaluation split.

## NESO comparison

NESO's operational forecast is evaluated against the same historic `national_demand_mw` target used for the portfolio models rather than relying on NESO's published error field.

This provides a like-for-like comparison at settlement-period level.

Known malformed forecast-performance grains on 31 October 2021 and 30 October 2022 are preserved in the source pipeline rather than silently deduplicated. They are excluded only where necessary from NESO benchmark comparison.

## Linear-model implementation check

During 2024 validation, a numerical implementation issue was identified between sparse and dense ordinary least-squares solver paths.

The original sparse implementation produced validation MAE of **1,610.05 MW**, while the dense implementation produced **1,593.40 MW** from the same feature specification and training data.

The dense implementation was therefore fixed as the final linear benchmark before the 2025 test was opened. The earlier result remains visible in the Git history rather than being silently overwritten.

## Repository structure

```text
analysis/
    forecasting_utils.py
    model_validation.py
    final_test_analysis.py
    robustness_2026.py
    publication_figures.py

src/
    acquire_neso.py
    validate_neso.py
    load_bigquery_raw.py

models/
    sources/
    staging/
    intermediate/

tests/
    dbt data-quality tests

outputs/
    figures/
    tables/

docs/
    source and architecture documentation
    leakage register
    project plan
```

The main analytical scripts have distinct roles:

- `model_validation.py` reproduces the 2024 validation and model-comparison stage;
- `final_test_analysis.py` evaluates the frozen models and NESO on 2025 and writes publication tables;
- `robustness_2026.py` performs the separate 2026 robustness evaluation;
- `publication_figures.py` generates the published figures from the validated CSV outputs rather than retraining models.

## Reproducibility

Python dependencies are pinned in [`requirements.txt`](requirements.txt).

The project requires access to the configured Google Cloud / BigQuery project. dbt uses a local `profiles.yml`, which is intentionally excluded from Git.

Raw NESO downloads are deliberately excluded from Git and are reacquired from the public API. Because the source can be revised after publication, a fresh acquisition at a later date is not guaranteed to reproduce the exact source bytes used for the published analysis.

The broad reproduction sequence is:

```powershell
.\.venv\Scripts\python.exe .\src\acquire_neso.py
.\.venv\Scripts\python.exe .\src\validate_neso.py
.\.venv\Scripts\python.exe .\src\load_bigquery_raw.py

.\.venv\Scripts\dbt.exe run --profiles-dir .
.\.venv\Scripts\dbt.exe test --profiles-dir .

.\.venv\Scripts\python.exe .\analysis\model_validation.py
.\.venv\Scripts\python.exe .\analysis\final_test_analysis.py
.\.venv\Scripts\python.exe .\analysis\robustness_2026.py
.\.venv\Scripts\python.exe .\analysis\publication_figures.py
```

Supporting implementation notes are available in:

- [`docs/source_architecture.md`](docs/source_architecture.md)
- [`docs/data_acquisition.md`](docs/data_acquisition.md)
- [`docs/bigquery_raw_ingestion.md`](docs/bigquery_raw_ingestion.md)
- [`docs/dbt_source_layer.md`](docs/dbt_source_layer.md)
- [`docs/leakage_register.md`](docs/leakage_register.md)

## Limitations

The main limitations are:

- the model intentionally uses a narrow feature set and does not attempt to reproduce NESO's operational information environment;
- archived target-day weather forecasts are not included;
- exact contemporaneous publication vintages of historic demand observations are not reconstructed;
- bank-holiday treatment is deterministic and cannot capture every unusual operational or behavioural event;
- the 2026 robustness period is partial rather than a complete calendar year;
- no matching NESO forecast rows are available for 2 September 2026 in the captured fixed robustness window;
- observed error patterns do not by themselves establish their underlying cause.

The project is therefore best interpreted as a leakage-controlled independent forecasting benchmark and error-analysis case study, rather than as a proposed replacement for an operational electricity-demand forecasting system.

## Technology

- Python
- pandas
- scikit-learn
- Matplotlib
- SQL
- BigQuery
- dbt
- Git and GitHub

## Data source

National Energy System Operator (NESO) Data Portal.

Source definitions, retrieval details and validation decisions are documented in [`docs/source_architecture.md`](docs/source_architecture.md) and [`docs/data_acquisition.md`](docs/data_acquisition.md).
