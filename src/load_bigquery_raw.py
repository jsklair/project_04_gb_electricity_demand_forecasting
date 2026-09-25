import csv
import json
from pathlib import Path

from google.cloud import bigquery


def read_csv_header(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        return next(reader)


def count_csv_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        next(reader)
        return sum(1 for _ in reader)


def build_raw_schema(columns):
    return [
        bigquery.SchemaField(column, "STRING")
        for column in columns
    ]


def main():
    project_root = Path(__file__).resolve().parents[1]

    sources_path = project_root / "config" / "neso_sources.json"
    bigquery_path = project_root / "config" / "bigquery.json"
    raw_dir = project_root / "data" / "raw"

    with sources_path.open(encoding="utf-8-sig") as file:
        sources = json.load(file)

    with bigquery_path.open(encoding="utf-8-sig") as file:
        bigquery_config = json.load(file)

    project_id = bigquery_config["project_id"]
    dataset_id = bigquery_config["dataset_id"]
    location = bigquery_config["location"]

    client = bigquery.Client(project=project_id)

    dataset_ref = bigquery.Dataset(
        f"{project_id}.{dataset_id}"
    )
    dataset_ref.location = location

    dataset = client.create_dataset(
        dataset_ref,
        exists_ok=True,
    )

    if dataset.location.upper() != location.upper():
        raise RuntimeError(
            f"Dataset location is {dataset.location}, "
            f"expected {location}"
        )

    print(
        f"BigQuery dataset ready: "
        f"{project_id}.{dataset_id} ({location})"
    )

    for source_name, source_config in sources.items():
        source_path = raw_dir / source_config["output_file"]

        if not source_path.exists():
            raise FileNotFoundError(
                f"Missing raw source file: {source_path}"
            )

        table_name = f"raw_{source_name}"
        table_id = (
            f"{project_id}.{dataset_id}.{table_name}"
        )

        columns = read_csv_header(source_path)
        local_rows = count_csv_rows(source_path)

        job_config = bigquery.LoadJobConfig(
            schema=build_raw_schema(columns),
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=False,
            allow_quoted_newlines=True,
        )

        print(f"\nLoading {source_name}...")

        with source_path.open("rb") as file:
            load_job = client.load_table_from_file(
                file,
                table_id,
                job_config=job_config,
                location=location,
            )

        load_job.result()

        table = client.get_table(table_id)

        if table.num_rows != local_rows:
            raise RuntimeError(
                f"{table_name}: BigQuery has "
                f"{table.num_rows:,} rows but local CSV has "
                f"{local_rows:,}"
            )

        print(f"  Table: {table_name}")
        print(f"  Rows: {table.num_rows:,}")
        print(f"  Columns: {len(table.schema)}")
        print("  Row-count check: PASS")

    print("\nAll raw NESO tables loaded successfully.")


if __name__ == "__main__":
    main()
