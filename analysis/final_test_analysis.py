import pandas as pd
from google.cloud import bigquery

from forecasting_utils import (
    FEATURE_COLUMNS,
    PROJECT_ID,
    TARGET,
    add_bank_holiday_features,
    build_hist_gradient_boosting_model,
    build_linear_model,
    calculate_metrics,
)


client = bigquery.Client(project=PROJECT_ID)

feature_query = """
select
    settlement_date,
    settlement_period,
    national_demand_mw,
    day_of_week,
    calendar_month,
    demand_lag_2d_mw,
    demand_lag_7d_mw,
    demand_lag_14d_mw,
    evaluation_split
from `gb-demand-forecasting-p04.p04_dbt.int_demand_model_features`
where evaluation_split in (
    'development',
    'validation',
    'final_test'
)
order by settlement_date, settlement_period
"""

df = client.query(
    feature_query,
    location="EU",
).to_dataframe()

df["settlement_date"] = pd.to_datetime(
    df["settlement_date"]
).dt.date

df = add_bank_holiday_features(df)

model_data = df.dropna(
    subset=FEATURE_COLUMNS + [TARGET]
).copy()

# Model choice and features were frozen using development and validation data.
# The models are refitted on all available pre-test data: 2021-2024.
training = model_data[
    model_data["evaluation_split"].isin(
        ["development", "validation"]
    )
].copy()

final_test = model_data[
    model_data["evaluation_split"] == "final_test"
].copy()

# Guardrails against accidentally evaluating the wrong period or sample.
assert training["settlement_date"].max().year == 2024
assert final_test["settlement_date"].min().year == 2025
assert final_test["settlement_date"].max().year == 2025
assert set(final_test["evaluation_split"].unique()) == {"final_test"}
assert len(final_test) == 17512

X_training = training[FEATURE_COLUMNS]
y_training = training[TARGET]

X_final_test = final_test[FEATURE_COLUMNS]

# Both specifications were frozen from 2024 validation before the 2025
# final test was opened.
linear_model = build_linear_model(dense=True)
nonlinear_model = build_hist_gradient_boosting_model()

linear_model.fit(
    X_training,
    y_training,
)

nonlinear_model.fit(
    X_training,
    y_training,
)

final_test["seasonal_naive_forecast_mw"] = (
    final_test["demand_lag_7d_mw"]
)

final_test["linear_forecast_mw"] = linear_model.predict(
    X_final_test
)

final_test["nonlinear_forecast_mw"] = nonlinear_model.predict(
    X_final_test
)

# NESO's operational day-ahead forecast is rescored against the same
# historic National Demand target used for the portfolio models.
neso_query = """
select
    settlement_date,
    settlement_period,
    demand_forecast_mw as neso_forecast_mw
from `gb-demand-forecasting-p04.p04_dbt.stg_neso_forecast_performance`
where settlement_date >= date '2025-01-01'
  and settlement_date < date '2026-01-01'
order by settlement_date, settlement_period
"""

neso = client.query(
    neso_query,
    location="EU",
).to_dataframe()

neso["settlement_date"] = pd.to_datetime(
    neso["settlement_date"]
).dt.date

# 2025 should have one NESO forecast per settlement-date/period grain.
duplicate_neso_grains = neso.duplicated(
    subset=[
        "settlement_date",
        "settlement_period",
    ],
    keep=False,
)

assert not duplicate_neso_grains.any()

comparison = final_test.merge(
    neso,
    on=[
        "settlement_date",
        "settlement_period",
    ],
    how="left",
    validate="one_to_one",
)

# Every model-eligible 2025 row must also have a NESO forecast.
missing_neso = comparison["neso_forecast_mw"].isna().sum()

assert missing_neso == 0
assert len(comparison) == 17512

models = {
    "Seasonal naive (7-day lag)": "seasonal_naive_forecast_mw",
    "Linear regression": "linear_forecast_mw",
    "Histogram gradient boosting": "nonlinear_forecast_mw",
    "NESO operational forecast": "neso_forecast_mw",
}

metrics = {}

for model_name, forecast_column in models.items():
    metrics[model_name] = calculate_metrics(
        comparison[TARGET],
        comparison[forecast_column],
    )

print("2025 LIKE-FOR-LIKE FINAL TEST")
print("=============================")
print()
print(f"Training rows (2021-2024):       {len(training):,}")
print(f"Model-eligible 2025 rows:         {len(final_test):,}")
print(f"NESO 2025 source rows:            {len(neso):,}")
print(f"Common comparison rows:           {len(comparison):,}")
print(f"Missing NESO forecasts in sample: {missing_neso:,}")
print()

print("2025 metrics against historic National Demand")
print("---------------------------------------------")

for model_name, model_metrics in metrics.items():
    print(model_name)
    print(f"  MAE:  {model_metrics['mae_mw']:,.2f} MW")
    print(f"  RMSE: {model_metrics['rmse_mw']:,.2f} MW")
    print(f"  Bias: {model_metrics['bias_mw']:,.2f} MW")
    print(f"  MAPE: {model_metrics['mape_pct']:.3f}%")
    print()

nonlinear_mae = metrics[
    "Histogram gradient boosting"
]["mae_mw"]

neso_mae = metrics[
    "NESO operational forecast"
]["mae_mw"]

neso_advantage_pct = (
    (nonlinear_mae - neso_mae)
    / nonlinear_mae
    * 100
)

print("NESO comparison")
print("---------------")
print(
    "NESO MAE reduction versus histogram gradient boosting: "
    f"{neso_advantage_pct:.2f}%"
)

# ---------------------------------------------------------------------------
# Frozen-model error analysis
#
# Everything below is diagnostic only. The 2025 result has already been
# opened and the model specifications remain frozen. These diagnostics are
# not used to alter features, model family or hyperparameters.
# ---------------------------------------------------------------------------

# BigQuery DAYOFWEEK uses Sunday=1 and Saturday=7.
comparison["is_weekend"] = comparison["day_of_week"].isin([1, 7])

forecast_columns = {
    "naive": "seasonal_naive_forecast_mw",
    "linear": "linear_forecast_mw",
    "nonlinear": "nonlinear_forecast_mw",
    "neso": "neso_forecast_mw",
}

for short_name, forecast_column in forecast_columns.items():
    comparison[f"{short_name}_error_mw"] = (
        comparison[forecast_column]
        - comparison[TARGET]
    )

    comparison[f"{short_name}_abs_error_mw"] = (
        comparison[f"{short_name}_error_mw"].abs()
    )

print()
print("2025 MAE by month")
print("-----------------")

monthly = (
    comparison
    .groupby("calendar_month")
    .agg(
        rows=(TARGET, "size"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
        linear_mae_mw=("linear_abs_error_mw", "mean"),
        nonlinear_mae_mw=("nonlinear_abs_error_mw", "mean"),
        neso_mae_mw=("neso_abs_error_mw", "mean"),
    )
    .round(2)
)

print(monthly.to_string())

print()
print("2025 MAE by weekday / weekend")
print("-----------------------------")

weekend_summary = (
    comparison
    .groupby("is_weekend")
    .agg(
        rows=(TARGET, "size"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
        linear_mae_mw=("linear_abs_error_mw", "mean"),
        nonlinear_mae_mw=("nonlinear_abs_error_mw", "mean"),
        neso_mae_mw=("neso_abs_error_mw", "mean"),
    )
    .round(2)
)

print(weekend_summary.to_string())

print()
print("2025 MAE by target-date bank-holiday status")
print("-------------------------------------------")

holiday_summary = (
    comparison
    .groupby(
        [
            "is_england_wales_bank_holiday",
            "is_scotland_bank_holiday",
        ]
    )
    .agg(
        rows=(TARGET, "size"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
        linear_mae_mw=("linear_abs_error_mw", "mean"),
        nonlinear_mae_mw=("nonlinear_abs_error_mw", "mean"),
        neso_mae_mw=("neso_abs_error_mw", "mean"),
    )
    .round(2)
)

print(holiday_summary.to_string())

print()
print("Worst settlement periods for gradient boosting")
print("----------------------------------------------")

settlement_summary = (
    comparison
    .groupby("settlement_period")
    .agg(
        rows=(TARGET, "size"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
        linear_mae_mw=("linear_abs_error_mw", "mean"),
        nonlinear_mae_mw=("nonlinear_abs_error_mw", "mean"),
        neso_mae_mw=("neso_abs_error_mw", "mean"),
    )
    .sort_values(
        "nonlinear_mae_mw",
        ascending=False,
    )
    .head(15)
    .round(2)
)

print(settlement_summary.to_string())

# Demand quartiles are retrospective diagnostic groups only.
# They are based on the realised 2025 target and are not model features.
comparison["demand_quartile"] = pd.qcut(
    comparison[TARGET],
    q=4,
    labels=[
        "Q1 lowest demand",
        "Q2",
        "Q3",
        "Q4 highest demand",
    ],
)

print()
print("2025 MAE by realised demand quartile")
print("------------------------------------")

demand_summary = (
    comparison
    .groupby(
        "demand_quartile",
        observed=True,
    )
    .agg(
        rows=(TARGET, "size"),
        mean_demand_mw=(TARGET, "mean"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
        linear_mae_mw=("linear_abs_error_mw", "mean"),
        nonlinear_mae_mw=("nonlinear_abs_error_mw", "mean"),
        neso_mae_mw=("neso_abs_error_mw", "mean"),
    )
    .round(2)
)

print(demand_summary.to_string())

print()
print("2025 daily error: worst days for gradient boosting")
print("--------------------------------------------------")

daily_summary = (
    comparison
    .groupby("settlement_date")
    .agg(
        rows=(TARGET, "size"),
        mean_demand_mw=(TARGET, "mean"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
        linear_mae_mw=("linear_abs_error_mw", "mean"),
        nonlinear_mae_mw=("nonlinear_abs_error_mw", "mean"),
        neso_mae_mw=("neso_abs_error_mw", "mean"),
        nonlinear_bias_mw=("nonlinear_error_mw", "mean"),
        neso_bias_mw=("neso_error_mw", "mean"),
    )
    .sort_values(
        "nonlinear_mae_mw",
        ascending=False,
    )
    .head(15)
    .round(2)
)

print(daily_summary.to_string())

print()
print("Point-by-point forecast comparison")
print("----------------------------------")

nonlinear_beats_naive = (
    comparison["nonlinear_abs_error_mw"]
    < comparison["naive_abs_error_mw"]
).mean() * 100

nonlinear_beats_linear = (
    comparison["nonlinear_abs_error_mw"]
    < comparison["linear_abs_error_mw"]
).mean() * 100

nonlinear_beats_neso = (
    comparison["nonlinear_abs_error_mw"]
    < comparison["neso_abs_error_mw"]
).mean() * 100

print(
    "Gradient boosting beats seasonal naive: "
    f"{nonlinear_beats_naive:.2f}% of settlement periods"
)

print(
    "Gradient boosting beats linear regression: "
    f"{nonlinear_beats_linear:.2f}% of settlement periods"
)

print(
    "Gradient boosting beats NESO: "
    f"{nonlinear_beats_neso:.2f}% of settlement periods"
)

print()
print("Largest individual gradient-boosting errors")
print("-------------------------------------------")

largest_errors = (
    comparison[
        [
            "settlement_date",
            "settlement_period",
            TARGET,
            "nonlinear_forecast_mw",
            "neso_forecast_mw",
            "nonlinear_error_mw",
            "neso_error_mw",
            "nonlinear_abs_error_mw",
            "neso_abs_error_mw",
        ]
    ]
    .sort_values(
        "nonlinear_abs_error_mw",
        ascending=False,
    )
    .head(20)
)

print(largest_errors.to_string(index=False))
