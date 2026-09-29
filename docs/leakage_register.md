# Leakage register

This register records whether candidate modelling information would genuinely
have been available when NESO's day-ahead forecast was issued.

The forecast-performance data show that every captured forecast was published
on the calendar day before its target settlement date. Publication times vary,
but are generally during the morning of the previous day.

| Feature | Source | Information timing | Decision | Rationale |
|---|---|---|---|---|
| Settlement period | Calendar / target definition | Known in advance | Use | Scheduled before forecast issue |
| Day of week | Calendar | Known in advance | Use | Deterministic calendar information |
| Month / day of year | Calendar | Known in advance | Use | Deterministic calendar information |
| Weekend flag | Calendar | Known in advance | Use | Deterministic calendar information |
| England and Wales bank-holiday flag | Calendar | Known in advance | Use | Published calendar information |
| Scotland bank-holiday flag | Calendar | Known in advance | Use | Published calendar information |
| Bank-holiday status of lagged dates | Calendar | Known in advance | Use | Helps distinguish unusually low or high lag values caused by holidays |
| Demand lag 1 day | Historic demand | Previous target day, partly incomplete at forecast issue | Do not use | Not universally available when the day-ahead forecast is issued |
| Demand lag 2 days | Historic demand | Fully elapsed before forecast issue | Use with limitation | Operationally time-safe, but current historic data may contain later revisions |
| Demand lag 7 days | Historic demand | Fully elapsed before forecast issue | Use with limitation | Operationally time-safe, but current historic data may contain later revisions |
| Demand lag 14 days | Historic demand | Fully elapsed before forecast issue | Use with limitation | Operationally time-safe, but current historic data may contain later revisions |
| Target-day observed demand | Historic demand | After forecast issue | Do not use as feature | Direct target leakage |
| Target-day observed weather | External weather source | After forecast issue | Do not use | Archived forecast weather would be required instead |
| NESO Demand Forecast | Forecast-performance source | Available at benchmark issue time | Benchmark only | Used for comparison, not as an input to the portfolio model |
| NESO Demand Outturn | Forecast-performance source | After target period | Evaluation only | Not available at forecast issue |
| TRIAD-corrected outturn | Forecast-performance source | After target period | Evaluation sensitivity only | Not available at forecast issue |

## Historical-vintage limitation

The historic-demand dataset may contain values revised after the original
settlement date. Lagged demand features therefore satisfy the time-availability
rule conceptually because the relevant days had already elapsed, but this
project does not reconstruct the exact historical publication vintage that
would have been visible to an operator at forecast issue time.

This limitation remains explicit in the methodology and final conclusions.

## Validation isolation

Model development uses 2021-2023 data.

Calendar year 2024 is used for model validation and feature decisions.

Calendar year 2025 is reserved as the final held-out test period and must not
be used to choose features, model specifications or hyperparameters.

The available 2026 data are treated separately as a robustness period because
NESO introduced a new forecasting system during that year.

## Benchmark comparability

The primary modelling target is historic `national_demand_mw`.

NESO forecast errors are recalculated against that same target so that the
portfolio model and NESO are compared on a consistent basis.

NESO's published `Absolute_Error` and `APE` are not used as the primary
like-for-like benchmark because some published errors use
TRIAD-corrected demand outturn.

The forecast-performance source contains malformed autumn daylight-saving
settlement-period grain on 31 October 2021 and 30 October 2022. Those two dates
are retained in the historic demand modelling data but excluded from the
like-for-like NESO benchmark comparison rather than being silently remapped.
