from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"

METRICS_FILE = TABLES_DIR / "final_test_metrics_2025.csv"
MONTHLY_FILE = TABLES_DIR / "monthly_mae_2025.csv"
SETTLEMENT_PERIOD_FILE = TABLES_DIR / "settlement_period_mae_2025.csv"
DAILY_FILE = TABLES_DIR / "daily_mae_2025.csv"
PREDICTIONS_FILE = TABLES_DIR / "final_test_predictions_2025.csv"

MODEL_LABELS = {
    "Seasonal naive (7-day lag)": "Seasonal naïve",
    "Linear regression": "Linear regression",
    "Histogram gradient boosting": "Gradient boosting",
    "NESO operational forecast": "NESO operational forecast",
}

MONTH_LABELS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

# Use Matplotlib's default palette consistently across the publication set.
DEFAULT_COLOURS = plt.rcParams["axes.prop_cycle"].by_key()["color"]

MODEL_COLOURS = {
    "naive": DEFAULT_COLOURS[0],
    "linear": DEFAULT_COLOURS[1],
    "nonlinear": DEFAULT_COLOURS[2],
    "neso": DEFAULT_COLOURS[3],
}


def save_figure(fig: plt.Figure, filename: str) -> None:
    output_path = FIGURES_DIR / filename

    FIGURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(fig)

    print(
        f"Saved {output_path.relative_to(PROJECT_ROOT)}"
    )


def create_final_test_mae_chart() -> None:
    metrics = pd.read_csv(METRICS_FILE)

    expected_models = list(MODEL_LABELS)

    if metrics["model"].tolist() != expected_models:
        raise ValueError(
            "Unexpected model ordering or model names in "
            "final_test_metrics_2025.csv"
        )

    chart_data = metrics[["model", "mae_mw"]].copy()

    chart_data["display_model"] = (
        chart_data["model"].map(MODEL_LABELS)
    )

    fig, ax = plt.subplots(figsize=(9, 5.5))

    bars = ax.barh(
        chart_data["display_model"],
        chart_data["mae_mw"],
    )

    ax.invert_yaxis()

    ax.set_title(
        "2025 final-test forecast accuracy",
        loc="left",
        fontsize=15,
        fontweight="bold",
    )

    ax.set_xlabel("Mean absolute error (MW)")
    ax.set_ylabel("")

    ax.grid(
        axis="x",
        alpha=0.25,
    )

    ax.set_axisbelow(True)

    for bar, value in zip(
        bars,
        chart_data["mae_mw"],
        strict=True,
    ):
        ax.text(
            value + 35,
            bar.get_y() + bar.get_height() / 2,
            f"{value:,.0f} MW",
            va="center",
            fontsize=10,
        )

    max_mae = chart_data["mae_mw"].max()

    ax.set_xlim(
        0,
        max_mae * 1.18,
    )

    fig.text(
        0.125,
        0.015,
        "Lower MAE is better. All forecasts are scored against the same "
        "2025 historic National Demand target.",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[0, 0.05, 1, 1],
    )

    save_figure(
        fig,
        "01_final_test_mae.png",
    )


def create_monthly_mae_chart() -> None:
    monthly = pd.read_csv(MONTHLY_FILE)

    expected_months = list(range(1, 13))

    if monthly["calendar_month"].tolist() != expected_months:
        raise ValueError(
            "monthly_mae_2025.csv does not contain months 1-12 "
            "in the expected order"
        )

    fig, ax = plt.subplots(figsize=(10, 5.8))

    series = [
        (
            "naive_mae_mw",
            "Seasonal naïve",
            MODEL_COLOURS["naive"],
        ),
        (
            "linear_mae_mw",
            "Linear regression",
            MODEL_COLOURS["linear"],
        ),
        (
            "nonlinear_mae_mw",
            "Gradient boosting",
            MODEL_COLOURS["nonlinear"],
        ),
        (
            "neso_mae_mw",
            "NESO operational forecast",
            MODEL_COLOURS["neso"],
        ),
    ]

    for column, label, colour in series:
        ax.plot(
            MONTH_LABELS,
            monthly[column],
            marker="o",
            linewidth=2,
            label=label,
            color=colour,
        )

    ax.set_title(
        "2025 forecast error by month",
        loc="left",
        fontsize=15,
        fontweight="bold",
    )

    ax.set_xlabel("")
    ax.set_ylabel("Mean absolute error (MW)")

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    ax.set_axisbelow(True)

    ax.legend(
        frameon=False,
        ncol=2,
    )

    fig.text(
        0.125,
        0.015,
        "2025 final-test results by calendar month. Lower MAE is better.",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[0, 0.05, 1, 1],
    )

    save_figure(
        fig,
        "02_monthly_mae_2025.png",
    )


def create_settlement_period_chart() -> None:
    settlement = pd.read_csv(
        SETTLEMENT_PERIOD_FILE
    )

    if settlement["settlement_period"].duplicated().any():
        raise ValueError(
            "Duplicate settlement periods found in "
            "settlement_period_mae_2025.csv"
        )

    # SP49-50 occur only on the autumn 50-period clock-change day.
    # Restrict the public chart to SP1-48 so the displayed period means
    # are based on broadly comparable numbers of observations.
    chart_data = settlement[
        settlement["settlement_period"] <= 48
    ].copy()

    fig, ax = plt.subplots(figsize=(10, 5.8))

    series = [
        (
            "linear_mae_mw",
            "Linear regression",
            MODEL_COLOURS["linear"],
        ),
        (
            "nonlinear_mae_mw",
            "Gradient boosting",
            MODEL_COLOURS["nonlinear"],
        ),
        (
            "neso_mae_mw",
            "NESO operational forecast",
            MODEL_COLOURS["neso"],
        ),
    ]

    for column, label, colour in series:
        ax.plot(
            chart_data["settlement_period"],
            chart_data[column],
            linewidth=2,
            label=label,
            color=colour,
        )

    ax.set_title(
        "Forecast errors peak around settlement periods 25–29",
        loc="left",
        fontsize=15,
        fontweight="bold",
    )

    ax.set_xlabel("Settlement period")
    ax.set_ylabel("Mean absolute error (MW)")

    ax.set_xlim(1, 48)

    ax.set_xticks(
        [
            1,
            5,
            9,
            13,
            17,
            21,
            25,
            29,
            33,
            37,
            41,
            45,
            48,
        ]
    )

    ax.grid(
        axis="y",
        alpha=0.25,
    )

    ax.set_axisbelow(True)

    ax.legend(
        frameon=False,
    )

    fig.text(
        0.125,
        0.015,
        "On a standard 48-period day, SP25–29 covers roughly "
        "12:00–14:30. SP49–50 are omitted because they occur only "
        "on the autumn clock-change day.",
        fontsize=9,
    )

    fig.tight_layout(
        rect=[0, 0.05, 1, 1],
    )

    save_figure(
        fig,
        "03_settlement_period_mae_2025.png",
    )


def choose_example_dates(
    daily: pd.DataFrame,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    daily = daily.copy()

    daily["settlement_date"] = pd.to_datetime(
        daily["settlement_date"]
    )

    median_daily_mae = daily[
        "nonlinear_mae_mw"
    ].median()

    median_index = (
        daily["nonlinear_mae_mw"]
        .sub(median_daily_mae)
        .abs()
        .idxmin()
    )

    worst_index = (
        daily["nonlinear_mae_mw"]
        .idxmax()
    )

    median_error_date = daily.loc[
        median_index,
        "settlement_date",
    ]

    worst_date = daily.loc[
        worst_index,
        "settlement_date",
    ]

    return median_error_date, worst_date


def create_daily_example_chart() -> None:
    daily = pd.read_csv(DAILY_FILE)

    predictions = pd.read_csv(
        PREDICTIONS_FILE,
        parse_dates=["settlement_date"],
    )

    if len(predictions) != 17512:
        raise ValueError(
            "Unexpected row count in final_test_predictions_2025.csv"
        )

    median_error_date, worst_date = choose_example_dates(
        daily
    )

    example_dates = [
        (
            median_error_date,
            "Near-median gradient-boosting error day",
        ),
        (
            worst_date,
            "Worst gradient-boosting error day",
        ),
    ]

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(9, 8),
        sharex=False,
    )

    for ax, (example_date, description) in zip(
        axes,
        example_dates,
        strict=True,
    ):
        day = predictions[
            predictions["settlement_date"]
            == example_date
        ].copy()

        if day.empty:
            raise ValueError(
                f"No prediction rows found for {example_date.date()}"
            )

        daily_row = daily[
            pd.to_datetime(
                daily["settlement_date"]
            )
            == example_date
        ].iloc[0]

        ax.plot(
            day["settlement_period"],
            day["national_demand_mw"],
            linewidth=2.8,
            label="Actual demand",
            color=DEFAULT_COLOURS[0],
        )

        ax.plot(
            day["settlement_period"],
            day["nonlinear_forecast_mw"],
            linewidth=2,
            label="Gradient boosting",
            color=MODEL_COLOURS["nonlinear"],
        )

        ax.plot(
            day["settlement_period"],
            day["neso_forecast_mw"],
            linewidth=2,
            label="NESO operational forecast",
            color=MODEL_COLOURS["neso"],
        )

        ax.set_title(
            (
                f"{description}: "
                f"{example_date.day} "
                f"{example_date.strftime('%B %Y')} "
                f"(daily MAE "
                f"{daily_row['nonlinear_mae_mw']:,.0f} MW)"
            ),
            loc="left",
            fontsize=11,
            fontweight="bold",
        )

        ax.set_ylabel("National Demand (MW)")

        ax.grid(
            axis="y",
            alpha=0.25,
        )

        ax.set_axisbelow(True)

        ax.legend(
            frameon=False,
            ncol=3,
            fontsize=9,
        )

    axes[-1].set_xlabel("Settlement period")

    fig.suptitle(
        "Near-median and worst gradient-boosting error days in 2025",
        x=0.125,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )

    fig.text(
        0.125,
        0.015,
        "The first date is selected mechanically as the day whose "
        "gradient-boosting MAE is nearest the 2025 daily median.\n"
        "It represents typical error magnitude, not necessarily "
        "every aspect of demand shape.",
        fontsize=9,
)

    fig.tight_layout(
        rect=[0, 0.075, 1, 0.96],
    )

    save_figure(
        fig,
        "04_daily_forecast_examples_2025.png",
    )

    print(
        "Near-median HGB error date: "
        f"{median_error_date.date()}"
    )

    print(
        "Worst HGB error date: "
        f"{worst_date.date()}"
    )


def main() -> None:
    create_final_test_mae_chart()
    create_monthly_mae_chart()
    create_settlement_period_chart()
    create_daily_example_chart()


if __name__ == "__main__":
    main()
