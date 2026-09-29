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


def build_preprocessor(dense):
    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    drop="first",
                    handle_unknown="ignore",
                    sparse_output=not dense,
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

query = """
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
where evaluation_split in ('development', 'validation')
order by settlement_date, settlement_period
"""

df = client.query(query, location="EU").to_dataframe()

# Only development and validation data are loaded here.
# The 2025 final test remains untouched until model specification is frozen.
df["settlement_date"] = pd.to_datetime(df["settlement_date"]).dt.date

england_wales_holidays = holidays.UnitedKingdom(
    years=[2021, 2022, 2023, 2024],
    subdiv="England",
)

scotland_holidays = holidays.UnitedKingdom(
    years=[2021, 2022, 2023, 2024],
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

    df[f"lag_{lag_days}d_is_england_wales_bank_holiday"] = lag_dates.map(
        lambda date: date in england_wales_holidays
    )

    df[f"lag_{lag_days}d_is_scotland_bank_holiday"] = lag_dates.map(
        lambda date: date in scotland_holidays
    )

model_data = df.dropna(
    subset=FEATURE_COLUMNS + [TARGET]
).copy()

development = model_data[
    model_data["evaluation_split"] == "development"
].copy()

validation = model_data[
    model_data["evaluation_split"] == "validation"
].copy()

X_development = development[FEATURE_COLUMNS]
y_development = development[TARGET]

X_validation = validation[FEATURE_COLUMNS]
y_validation = validation[TARGET]

# Compare sparse and dense ordinary least-squares representations because
# scikit-learn uses different numerical solver paths for the two inputs.
# The difference is diagnostic only: both models use the same features and
# training rows, and the dense result is used as the corrected linear benchmark.

linear_sparse = Pipeline(
    steps=[
        ("preprocessor", build_preprocessor(dense=False)),
        ("regression", LinearRegression()),
    ]
)

linear_dense = Pipeline(
    steps=[
        ("preprocessor", build_preprocessor(dense=True)),
        ("regression", LinearRegression()),
    ]
)

nonlinear_model = Pipeline(
    steps=[
        ("preprocessor", build_preprocessor(dense=True)),
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

linear_sparse.fit(X_development, y_development)
linear_dense.fit(X_development, y_development)
nonlinear_model.fit(X_development, y_development)

validation["seasonal_naive_forecast_mw"] = validation["demand_lag_7d_mw"]

validation["linear_sparse_forecast_mw"] = linear_sparse.predict(
    X_validation
)

validation["linear_dense_forecast_mw"] = linear_dense.predict(
    X_validation
)

validation["nonlinear_forecast_mw"] = nonlinear_model.predict(
    X_validation
)

models = {
    "Seasonal naive (7-day lag)": "seasonal_naive_forecast_mw",
    "Linear regression - sparse": "linear_sparse_forecast_mw",
    "Linear regression - dense": "linear_dense_forecast_mw",
    "Histogram gradient boosting": "nonlinear_forecast_mw",
}

metrics = {}

for model_name, forecast_column in models.items():
    metrics[model_name] = calculate_metrics(
        y_validation,
        validation[forecast_column],
    )

print(f"Development rows: {len(development):,}")
print(f"Validation rows:  {len(validation):,}")
print()

print("2024 validation comparison")
print("--------------------------")

for model_name, model_metrics in metrics.items():
    print(model_name)
    print(f"  MAE:  {model_metrics['mae_mw']:,.2f} MW")
    print(f"  RMSE: {model_metrics['rmse_mw']:,.2f} MW")
    print(f"  Bias: {model_metrics['bias_mw']:,.2f} MW")
    print(f"  MAPE: {model_metrics['mape_pct']:.3f}%")
    print()

dense_mae = metrics["Linear regression - dense"]["mae_mw"]
nonlinear_mae = metrics["Histogram gradient boosting"]["mae_mw"]

mae_improvement_pct = (
    (dense_mae - nonlinear_mae)
    / dense_mae
    * 100
)

print("Nonlinear improvement over dense linear regression")
print("--------------------------------------------------")
print(f"MAE improvement: {mae_improvement_pct:.2f}%")
print()

prediction_difference = (
    validation["linear_dense_forecast_mw"]
    - validation["linear_sparse_forecast_mw"]
).abs()

print("Sparse vs dense linear-regression diagnostic")
print("--------------------------------------------")
print(
    "Mean absolute prediction difference: "
    f"{prediction_difference.mean():,.2f} MW"
)
print(
    "Maximum absolute prediction difference: "
    f"{prediction_difference.max():,.2f} MW"
)
