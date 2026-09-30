from datetime import date
from pathlib import Path

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


ROBUSTNESS_END_DATE = date(2026, 9, 2)

TABLES_DIR = (
    Path(__file__).resolve().parents[1]
    / "outputs"
    / "tables"
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
    'final_test',
    'robustness'
)
  and settlement_date <= date '2026-09-02'
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

# The specification remains frozen. The completed 2025 final-test year can
# now be included in fitting for this subsequent 2026 robustness check.
training = model_data[
    model_data["evaluation_split"].isin(
        [
            "development",
            "validation",
            "final_test",
        ]
    )
].copy()

robustness = model_data[
    model_data["evaluation_split"] == "robustness"
].copy()

# Guardrails keep this robustness exercise separate from model development
# and fix the published evaluation window at 2 September 2026.
assert training["settlement_date"].max().year == 2025
assert robustness["settlement_date"].min().year == 2026
assert robustness["settlement_date"].max() == ROBUSTNESS_END_DATE
assert set(robustness["evaluation_split"].unique()) == {"robustness"}

X_training = training[FEATURE_COLUMNS]
y_training = training[TARGET]

X_robustness = robustness[FEATURE_COLUMNS]

# Both model specifications remain unchanged from the earlier validation
# stage; only the fitting sample expands to include completed 2025 history.
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

robustness["seasonal_naive_forecast_mw"] = (
    robustness["demand_lag_7d_mw"]
)

robustness["linear_forecast_mw"] = linear_model.predict(
    X_robustness
)

robustness["nonlinear_forecast_mw"] = nonlinear_model.predict(
    X_robustness
)

# Restrict NESO data to the same fixed robustness window. This prevents a
# later warehouse refresh from silently extending the published analysis.
neso_query = """
select
    settlement_date,
    settlement_period,
    demand_forecast_mw as neso_forecast_mw
from `gb-demand-forecasting-p04.p04_dbt.stg_neso_forecast_performance`
where settlement_date >= date '2026-01-01'
  and settlement_date <= date '2026-09-02'
order by settlement_date, settlement_period
"""

neso = client.query(
    neso_query,
    location="EU",
).to_dataframe()

neso["settlement_date"] = pd.to_datetime(
    neso["settlement_date"]
).dt.date

duplicate_neso_grains = neso.duplicated(
    subset=[
        "settlement_date",
        "settlement_period",
    ],
    keep=False,
)

assert not duplicate_neso_grains.any()

comparison = robustness.merge(
    neso,
    on=[
        "settlement_date",
        "settlement_period",
    ],
    how="left",
    validate="one_to_one",
)

missing_neso_rows = comparison[
    comparison["neso_forecast_mw"].isna()
].copy()

comparison_common = comparison.dropna(
    subset=["neso_forecast_mw"]
).copy()

assert len(comparison_common) > 0
assert (
    len(comparison_common) + len(missing_neso_rows)
    == len(robustness)
)

print("2026 ROBUSTNESS EVALUATION")
print("==========================")
print()
print(f"Training rows (2021-2025):       {len(training):,}")
print(f"Model-eligible robustness rows:   {len(robustness):,}")
print(
    "Robustness date range:           "
    f"{robustness['settlement_date'].min()} to "
    f"{robustness['settlement_date'].max()}"
)
print(f"NESO source rows in fixed window: {len(neso):,}")
print(f"Rows without matching NESO:       {len(missing_neso_rows):,}")
print(f"Common four-model sample:         {len(comparison_common):,}")
print(
    "Common comparison date range:    "
    f"{comparison_common['settlement_date'].min()} to "
    f"{comparison_common['settlement_date'].max()}"
)
print()

if len(missing_neso_rows) > 0:
    print("NESO coverage exclusions")
    print("------------------------")

    excluded_dates = (
        missing_neso_rows
        .groupby("settlement_date")
        .size()
        .rename("excluded_rows")
    )

    print(excluded_dates.to_string())
    print()
else:
    excluded_dates = pd.Series(
        dtype="int64",
        name="excluded_rows",
    )

# ---------------------------------------------------------------------------
# Portfolio-model robustness on all model-eligible 2026 rows
# ---------------------------------------------------------------------------

portfolio_models = {
    "Seasonal naive (7-day lag)": "seasonal_naive_forecast_mw",
    "Linear regression": "linear_forecast_mw",
    "Histogram gradient boosting": "nonlinear_forecast_mw",
}

portfolio_metrics = {}

for model_name, forecast_column in portfolio_models.items():
    portfolio_metrics[model_name] = calculate_metrics(
        robustness[TARGET],
        robustness[forecast_column],
    )

print("Portfolio models: all eligible 2026 robustness rows")
print("---------------------------------------------------")

for model_name, model_metrics in portfolio_metrics.items():
    print(model_name)
    print(f"  MAE:  {model_metrics['mae_mw']:,.2f} MW")
    print(f"  RMSE: {model_metrics['rmse_mw']:,.2f} MW")
    print(f"  Bias: {model_metrics['bias_mw']:,.2f} MW")
    print(f"  MAPE: {model_metrics['mape_pct']:.3f}%")
    print()

# ---------------------------------------------------------------------------
# Fair four-model comparison on common rows only
# ---------------------------------------------------------------------------

common_models = {
    "Seasonal naive (7-day lag)": "seasonal_naive_forecast_mw",
    "Linear regression": "linear_forecast_mw",
    "Histogram gradient boosting": "nonlinear_forecast_mw",
    "NESO operational forecast": "neso_forecast_mw",
}

common_metrics = {}

for model_name, forecast_column in common_models.items():
    common_metrics[model_name] = calculate_metrics(
        comparison_common[TARGET],
        comparison_common[forecast_column],
    )

print("Like-for-like common-sample comparison")
print("--------------------------------------")

for model_name, model_metrics in common_metrics.items():
    print(model_name)
    print(f"  MAE:  {model_metrics['mae_mw']:,.2f} MW")
    print(f"  RMSE: {model_metrics['rmse_mw']:,.2f} MW")
    print(f"  Bias: {model_metrics['bias_mw']:,.2f} MW")
    print(f"  MAPE: {model_metrics['mape_pct']:.3f}%")
    print()

nonlinear_mae = common_metrics[
    "Histogram gradient boosting"
]["mae_mw"]

neso_mae = common_metrics[
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
print()

# ---------------------------------------------------------------------------
# Monthly common-sample robustness
# ---------------------------------------------------------------------------

for short_name, forecast_column in {
    "naive": "seasonal_naive_forecast_mw",
    "linear": "linear_forecast_mw",
    "nonlinear": "nonlinear_forecast_mw",
    "neso": "neso_forecast_mw",
}.items():
    comparison_common[f"{short_name}_abs_error_mw"] = (
        comparison_common[forecast_column]
        - comparison_common[TARGET]
    ).abs()

print("Common-sample MAE by month")
print("--------------------------")

monthly = (
    comparison_common
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

# ---------------------------------------------------------------------------
# Reproducible publication tables
# ---------------------------------------------------------------------------

TABLES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

portfolio_metrics_table = (
    pd.DataFrame.from_dict(
        portfolio_metrics,
        orient="index",
    )
    .rename_axis("model")
    .reset_index()
)

portfolio_metrics_table.insert(
    0,
    "sample",
    "all_model_eligible",
)

portfolio_metrics_table.insert(
    1,
    "rows",
    len(robustness),
)

portfolio_metrics_table.insert(
    2,
    "start_date",
    robustness["settlement_date"].min(),
)

portfolio_metrics_table.insert(
    3,
    "end_date",
    robustness["settlement_date"].max(),
)

common_metrics_table = (
    pd.DataFrame.from_dict(
        common_metrics,
        orient="index",
    )
    .rename_axis("model")
    .reset_index()
)

common_metrics_table.insert(
    0,
    "sample",
    "common_neso_comparison",
)

common_metrics_table.insert(
    1,
    "rows",
    len(comparison_common),
)

common_metrics_table.insert(
    2,
    "start_date",
    comparison_common["settlement_date"].min(),
)

common_metrics_table.insert(
    3,
    "end_date",
    comparison_common["settlement_date"].max(),
)

robustness_metrics_table = pd.concat(
    [
        portfolio_metrics_table,
        common_metrics_table,
    ],
    ignore_index=True,
)

robustness_metrics_table.to_csv(
    TABLES_DIR / "robustness_metrics_2026.csv",
    index=False,
)

monthly.reset_index().to_csv(
    TABLES_DIR / "robustness_monthly_mae_2026.csv",
    index=False,
)

coverage_exclusions = (
    excluded_dates
    .rename_axis("settlement_date")
    .reset_index()
)

coverage_exclusions.to_csv(
    TABLES_DIR / "robustness_neso_coverage_exclusions_2026.csv",
    index=False,
)

print()
print("Saved robustness publication tables")
print("-----------------------------------")

for filename in [
    "robustness_metrics_2026.csv",
    "robustness_monthly_mae_2026.csv",
    "robustness_neso_coverage_exclusions_2026.csv",
]:
    print(
        (TABLES_DIR / filename)
        .relative_to(TABLES_DIR.parent.parent)
    )
