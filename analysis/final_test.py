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
where evaluation_split in (
    'development',
    'validation',
    'final_test'
)
order by settlement_date, settlement_period
"""

df = client.query(query, location="EU").to_dataframe()

df["settlement_date"] = pd.to_datetime(
    df["settlement_date"]
).dt.date


# These calendars cover all fitting years plus the held-out 2025 test year.
england_wales_holidays = holidays.UnitedKingdom(
    years=[2021, 2022, 2023, 2024, 2025],
    subdiv="England",
)

scotland_holidays = holidays.UnitedKingdom(
    years=[2021, 2022, 2023, 2024, 2025],
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


# Model choice and features were frozen using development and validation data.
# The models are now refitted on all available pre-test data: 2021-2024.
training = model_data[
    model_data["evaluation_split"].isin(
        ["development", "validation"]
    )
].copy()

final_test = model_data[
    model_data["evaluation_split"] == "final_test"
].copy()


# Guardrails against accidentally evaluating the wrong period.
assert training["settlement_date"].max().year == 2024
assert final_test["settlement_date"].min().year == 2025
assert final_test["settlement_date"].max().year == 2025
assert set(final_test["evaluation_split"].unique()) == {"final_test"}


X_training = training[FEATURE_COLUMNS]
y_training = training[TARGET]

X_final_test = final_test[FEATURE_COLUMNS]
y_final_test = final_test[TARGET]


# Frozen transparent benchmark.
linear_model = Pipeline(
    steps=[
        ("preprocessor", build_dense_preprocessor()),
        ("regression", LinearRegression()),
    ]
)


# Frozen stronger nonlinear challenger.
# These hyperparameters were fixed from 2024 validation before the 2025 test was opened.
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


final_test["seasonal_naive_forecast_mw"] = (
    final_test["demand_lag_7d_mw"]
)

final_test["linear_forecast_mw"] = linear_model.predict(
    X_final_test
)

final_test["nonlinear_forecast_mw"] = nonlinear_model.predict(
    X_final_test
)


models = {
    "Seasonal naive (7-day lag)": "seasonal_naive_forecast_mw",
    "Linear regression": "linear_forecast_mw",
    "Histogram gradient boosting": "nonlinear_forecast_mw",
}

metrics = {}

for model_name, forecast_column in models.items():
    metrics[model_name] = calculate_metrics(
        y_final_test,
        final_test[forecast_column],
    )


print("FROZEN FINAL TEST")
print("=================")
print()
print(f"Training rows (2021-2024): {len(training):,}")
print(f"Final-test rows (2025):    {len(final_test):,}")
print()

print("2025 held-out test metrics")
print("--------------------------")

for model_name, model_metrics in metrics.items():
    print(model_name)
    print(f"  MAE:  {model_metrics['mae_mw']:,.2f} MW")
    print(f"  RMSE: {model_metrics['rmse_mw']:,.2f} MW")
    print(f"  Bias: {model_metrics['bias_mw']:,.2f} MW")
    print(f"  MAPE: {model_metrics['mape_pct']:.3f}%")
    print()


naive_mae = metrics["Seasonal naive (7-day lag)"]["mae_mw"]
linear_mae = metrics["Linear regression"]["mae_mw"]
nonlinear_mae = metrics["Histogram gradient boosting"]["mae_mw"]

linear_vs_naive_pct = (
    (naive_mae - linear_mae)
    / naive_mae
    * 100
)

nonlinear_vs_naive_pct = (
    (naive_mae - nonlinear_mae)
    / naive_mae
    * 100
)

nonlinear_vs_linear_pct = (
    (linear_mae - nonlinear_mae)
    / linear_mae
    * 100
)

print("MAE improvement")
print("---------------")
print(
    "Linear vs seasonal naive: "
    f"{linear_vs_naive_pct:.2f}%"
)
print(
    "Nonlinear vs seasonal naive: "
    f"{nonlinear_vs_naive_pct:.2f}%"
)
print(
    "Nonlinear vs linear: "
    f"{nonlinear_vs_linear_pct:.2f}%"
)
