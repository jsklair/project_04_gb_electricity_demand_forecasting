from datetime import timedelta

import holidays
import pandas as pd
from google.cloud import bigquery

from sklearn.compose import ColumnTransformer
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

# Only development (2021-2023) and validation (2024) are loaded here.
# The 2025 final test remains untouched while modelling decisions are made.
df["settlement_date"] = pd.to_datetime(df["settlement_date"]).dt.date

england_wales_holidays = holidays.UnitedKingdom(
    years=[2021, 2022, 2023, 2024],
    subdiv="England",
)

scotland_holidays = holidays.UnitedKingdom(
    years=[2021, 2022, 2023, 2024],
    subdiv="Scotland",
)

# Target-date holiday flags are known before forecast issue.
df["is_england_wales_bank_holiday"] = df["settlement_date"].map(
    lambda date: date in england_wales_holidays
)

df["is_scotland_bank_holiday"] = df["settlement_date"].map(
    lambda date: date in scotland_holidays
)

# A lagged demand value can behave unusually if the lagged date itself was
# a bank holiday. These flags let the model distinguish that situation.
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

# All three lag-demand values are required for this first transparent model.
model_data = df.dropna(
    subset=FEATURE_COLUMNS + [TARGET]
).copy()

development = model_data[
    model_data["evaluation_split"] == "development"
].copy()

validation = model_data[
    model_data["evaluation_split"] == "validation"
].copy()

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(
                drop="first",
                handle_unknown="ignore",
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

model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("regression", LinearRegression()),
    ]
)

model.fit(
    development[FEATURE_COLUMNS],
    development[TARGET],
)

validation["regression_forecast_mw"] = model.predict(
    validation[FEATURE_COLUMNS]
)

validation["seasonal_naive_forecast_mw"] = (
    validation["demand_lag_7d_mw"]
)

regression_metrics = calculate_metrics(
    validation[TARGET],
    validation["regression_forecast_mw"],
)

seasonal_naive_metrics = calculate_metrics(
    validation[TARGET],
    validation["seasonal_naive_forecast_mw"],
)

print(f"Development rows: {len(development):,}")
print(f"Validation rows:  {len(validation):,}")
print()

print("2024 validation metrics")
print("-----------------------")

for model_name, metrics in [
    ("Seasonal naive (7-day lag)", seasonal_naive_metrics),
    ("Linear regression", regression_metrics),
]:
    print(model_name)
    print(f"  MAE:  {metrics['mae_mw']:,.2f} MW")
    print(f"  RMSE: {metrics['rmse_mw']:,.2f} MW")
    print(f"  Bias: {metrics['bias_mw']:,.2f} MW")
    print(f"  MAPE: {metrics['mape_pct']:.3f}%")
    print()

validation["regression_abs_error_mw"] = (
    validation["regression_forecast_mw"]
    - validation[TARGET]
).abs()

validation["naive_abs_error_mw"] = (
    validation["seasonal_naive_forecast_mw"]
    - validation[TARGET]
).abs()

print("2024 bank-holiday validation")
print("----------------------------")

holiday_summary = (
    validation
    .groupby(
        [
            "is_england_wales_bank_holiday",
            "is_scotland_bank_holiday",
        ]
    )
    .agg(
        rows=(TARGET, "size"),
        regression_mae_mw=("regression_abs_error_mw", "mean"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
    )
    .round(2)
)

print(holiday_summary.to_string())
print()

print("Regression MAE by month")
print("-----------------------")

monthly = (
    validation
    .groupby("calendar_month")
    .agg(
        rows=(TARGET, "size"),
        regression_mae_mw=("regression_abs_error_mw", "mean"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
    )
    .round(2)
)

print(monthly.to_string())
print()

print("Worst settlement periods for regression")
print("---------------------------------------")

by_period = (
    validation
    .groupby("settlement_period")
    .agg(
        rows=(TARGET, "size"),
        regression_mae_mw=("regression_abs_error_mw", "mean"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
    )
    .sort_values(
        "regression_mae_mw",
        ascending=False,
    )
    .head(15)
    .round(2)
)

print(by_period.to_string())
print()

print("Largest 2024 regression errors")
print("------------------------------")

worst_errors = (
    validation[
        [
            "settlement_date",
            "settlement_period",
            TARGET,
            "regression_forecast_mw",
            "regression_abs_error_mw",
        ]
    ]
    .sort_values(
        "regression_abs_error_mw",
        ascending=False,
    )
    .head(20)
)

print(worst_errors.to_string(index=False))
print()

print("Selected January / Christmas diagnostics")
print("----------------------------------------")

selected_dates = validation[
    validation["settlement_date"].isin(
        [
            pd.Timestamp("2024-01-08").date(),
            pd.Timestamp("2024-01-09").date(),
            pd.Timestamp("2024-12-25").date(),
        ]
    )
]

selected_summary = (
    selected_dates
    .groupby("settlement_date")
    .agg(
        rows=(TARGET, "size"),
        regression_mae_mw=("regression_abs_error_mw", "mean"),
        naive_mae_mw=("naive_abs_error_mw", "mean"),
    )
    .round(2)
)

print(selected_summary.to_string())
print()

feature_names = (
    model
    .named_steps["preprocessor"]
    .get_feature_names_out()
)

coefficients = pd.Series(
    model.named_steps["regression"].coef_,
    index=feature_names,
)

print("Lag-demand coefficients")
print("-----------------------")

print(
    coefficients[
        coefficients.index.str.startswith("numeric__")
    ]
    .round(4)
    .to_string()
)
