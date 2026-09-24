import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%b-%Y",
    "%d-%b-%y",
)


def parse_date(value):
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), date_format).date()
        except ValueError:
            pass

    raise ValueError(f"Unrecognised date format: {value}")


def validate_file(source_name, config, raw_dir):
    path = raw_dir / config["output_file"]

    if not path.exists():
        raise FileNotFoundError(f"Missing raw file: {path}")

    with path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"{source_name}: file contains no data")

    if source_name == "forecast_performance":
        date_field = "Date"
        period_field = "Settlement_Period"
        required_fields = {
            "Date",
            "Settlement_Period",
            "Demand_Forecast",
            "Demand_Outturn",
            "Publish_Datetime",
        }
    else:
        date_field = "SETTLEMENT_DATE"
        period_field = "SETTLEMENT_PERIOD"
        required_fields = {
            "SETTLEMENT_DATE",
            "SETTLEMENT_PERIOD",
            "ND",
        }

    available_fields = set(rows[0].keys())
    missing_fields = required_fields - available_fields

    if missing_fields:
        raise ValueError(
            f"{source_name}: missing required fields: "
            f"{', '.join(sorted(missing_fields))}"
        )

    parsed_dates = [parse_date(row[date_field]) for row in rows]

    grain_counts = Counter(
        (row[date_field], row[period_field])
        for row in rows
    )

    duplicate_grain = {
        grain: count
        for grain, count in grain_counts.items()
        if count > 1
    }

    conflicting_duplicates = []

    if duplicate_grain:
        grouped_rows = defaultdict(list)

        for row in rows:
            grain = (row[date_field], row[period_field])

            if grain in duplicate_grain:
                grouped_rows[grain].append(row)

        for grain, duplicate_rows in grouped_rows.items():
            unique_rows = {
                tuple(sorted(row.items()))
                for row in duplicate_rows
            }

            if len(unique_rows) > 1:
                conflicting_duplicates.append(grain)

    rows_per_date = Counter(parsed_dates)
    settlement_day_sizes = Counter(rows_per_date.values())

    missing_required_values = sum(
        1
        for row in rows
        if any(not row[field].strip() for field in required_fields)
    )

    return {
        "source": source_name,
        "rows": len(rows),
        "first_date": min(parsed_dates).isoformat(),
        "last_date": max(parsed_dates).isoformat(),
        "duplicate_grain_count": len(duplicate_grain),
        "conflicting_duplicate_count": len(conflicting_duplicates),
        "conflicting_duplicates": conflicting_duplicates,
        "rows_with_missing_required_values": missing_required_values,
        "settlement_day_sizes": dict(sorted(settlement_day_sizes.items())),
    }


def main():
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "config" / "neso_sources.json"
    raw_dir = project_root / "data" / "raw"

    with config_path.open(encoding="utf-8-sig") as file:
        sources = json.load(file)

    print("NESO acquisition validation")
    print("=" * 27)

    for source_name, source_config in sources.items():
        result = validate_file(source_name, source_config, raw_dir)

        print(f"\n{result['source']}")
        print(f"  Rows: {result['rows']:,}")
        print(
            f"  Date range: {result['first_date']} "
            f"to {result['last_date']}"
        )
        print(
            "  Duplicate date/period combinations: "
            f"{result['duplicate_grain_count']:,}"
        )
        print(
            "  Conflicting duplicate combinations: "
            f"{result['conflicting_duplicate_count']:,}"
        )
        print(
            "  Rows missing required values: "
            f"{result['rows_with_missing_required_values']:,}"
        )
        print(
            "  Settlement-day row counts: "
            f"{result['settlement_day_sizes']}"
        )

        if result["conflicting_duplicates"]:
            print("  Conflicting duplicate grains:")

            for date_value, period_value in result["conflicting_duplicates"]:
                print(
                    f"    {date_value}, "
                    f"settlement period {period_value}"
                )


if __name__ == "__main__":
    main()
