from datetime import timedelta

import holidays
import pandas as pd
from google.cloud import bigquery

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


PROJECT_ID = "gb-demand-forecasting-p04"
TARGET = "national_demand_mw"

CATEGORICAL_FEATURES = [
    "settlement_period",
    "day_of_week",
    "calendar_month",
    "is_england_wales_bank_holiday",
    "is_scotland_bank_holiday",
    "lag_2d_is_england_wales_bank_holiday",
    "lag_2d_is_scotland_bank_holiday",
    "lag_7d_is_england_wales_bank_holiday",
    "lag_7d_is_scotland_bank_holiday",
    "lag_14d_is_england_wales_bank_holiday",
    "lag_14d_is_scotland_bank_holiday",
]

NUMERIC_FEATURES = [
    "demand_lag_2d_mw",
    "demand_lag_7d_mw",
    "demand_lag_14d_mw",
]

FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def calculate_metrics(actual, predicted):
    error = predicted - actual

    return {
        "mae_mw": mean_absolute_error(actual, predicted),
        "rmse_mw": root_mean_squared_error(actual, predicted),
        "bias_mw": error.mean(),
        "mape_pct": (error.abs() / actual).mean() * 100,
    }


def build_dense_preprocessor():
    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    drop="first",
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
                CATEGORICAL_FEATURES,
            ),
            (
                "numeric",
                "passthrough",
                NUMERIC_FEATURES,
            ),
        ]
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
order by settlement_date, settlement_period
"""

df = client.query(
    feature_query,
    location="EU",
).to_dataframe()

df["settlement_date"] = pd.to_datetime(
    df["settlement_date"]
).dt.date


england_wales_holidays = holidays.UnitedKingdom(
    years=[2021, 2022, 2023, 2024, 2025, 2026],
    subdiv="England",
)

scotland_holidays = holidays.UnitedKingdom(
    years=[2021, 2022, 2023, 2024, 2025, 2026],
    subdiv="Scotland",
)


df["is_england_wales_bank_holiday"] = df["settlement_date"].map(
    lambda date: date in england_wales_holidays
)

df["is_scotland_bank_holiday"] = df["settlement_date"].map(
    lambda date: date in scotland_holidays
)


for lag_days in [2, 7, 14]:
    lag_dates = df["settlement_date"].map(
        lambda date: date - timedelta(days=lag_days)
    )

    df[f"lag_{lag_days}d_is_england_wales_bank_holiday"] = (
        lag_dates.map(
            lambda date: date in england_wales_holidays
        )
    )

    df[f"lag_{lag_days}d_is_scotland_bank_holiday"] = (
        lag_dates.map(
            lambda date: date in scotland_holidays
        )
    )


model_data = df.dropna(
    subset=FEATURE_COLUMNS + [TARGET]
).copy()


# The model specification remains frozen.
# The 2025 final test is complete, so all 2021-2025 history can now
# be used for fitting before the separate 2026 robustness evaluation.
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


assert training["settlement_date"].max().year == 2025
assert robustness["settlement_date"].min().year == 2026
assert robustness["settlement_date"].max().year == 2026
assert set(robustness["evaluation_split"].unique()) == {"robustness"}


X_training = training[FEATURE_COLUMNS]
y_training = training[TARGET]

X_robustness = robustness[FEATURE_COLUMNS]


# Frozen transparent model.
linear_model = Pipeline(
    steps=[
        ("preprocessor", build_dense_preprocessor()),
        ("regression", LinearRegression()),
    ]
)


# Frozen nonlinear challenger.
# The specification was fixed from 2024 validation before the 2025 test was opened.
# For this later robustness check, it is refitted using all 2021-2025 history.
nonlinear_model = Pipeline(
    steps=[
        ("preprocessor", build_dense_preprocessor()),
        (
            "regression",
            HistGradientBoostingRegressor(
                learning_rate=0.05,
                max_iter=200,
                max_leaf_nodes=31,
                l2_regularization=1.0,
                random_state=42,
            ),
        ),
    ]
)


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


# NESO operational day-ahead forecasts.
neso_query = """
select
    settlement_date,
    settlement_period,
    demand_forecast_mw as neso_forecast_mw
from `gb-demand-forecasting-p04.p04_dbt.stg_neso_forecast_performance`
where settlement_date >= date '2026-01-01'
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
assert len(comparison_common) + len(missing_neso_rows) == len(robustness)


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
print(f"NESO 2026 source rows:            {len(neso):,}")
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
