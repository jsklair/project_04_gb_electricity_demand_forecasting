from datetime import timedelta

import holidays

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


PROJECT_ID = "gb-demand-forecasting-p04"
TARGET = "national_demand_mw"

LAG_DAYS = [2, 7, 14]

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


def add_bank_holiday_features(df):
    result = df.copy()

    data_years = sorted(
        {date.year for date in result["settlement_date"]}
    )

    # Include the preceding year because early-January lag dates can fall
    # in December of the previous calendar year.
    holiday_years = list(
        range(
            min(data_years) - 1,
            max(data_years) + 1,
        )
    )

    england_wales_holidays = holidays.UnitedKingdom(
        years=holiday_years,
        subdiv="England",
    )

    scotland_holidays = holidays.UnitedKingdom(
        years=holiday_years,
        subdiv="Scotland",
    )

    result["is_england_wales_bank_holiday"] = (
        result["settlement_date"].map(
            lambda date: date in england_wales_holidays
        )
    )

    result["is_scotland_bank_holiday"] = (
        result["settlement_date"].map(
            lambda date: date in scotland_holidays
        )
    )

    for lag_days in LAG_DAYS:
        lag_dates = result["settlement_date"].map(
            lambda date: date - timedelta(days=lag_days)
        )

        result[
            f"lag_{lag_days}d_is_england_wales_bank_holiday"
        ] = lag_dates.map(
            lambda date: date in england_wales_holidays
        )

        result[
            f"lag_{lag_days}d_is_scotland_bank_holiday"
        ] = lag_dates.map(
            lambda date: date in scotland_holidays
        )

    return result


def build_preprocessor(dense=True):
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


def build_linear_model(dense=True):
    return Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(dense=dense),
            ),
            (
                "regression",
                LinearRegression(),
            ),
        ]
    )


def build_hist_gradient_boosting_model():
    return Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(dense=True),
            ),
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
