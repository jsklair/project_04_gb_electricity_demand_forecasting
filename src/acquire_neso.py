import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

API_URL = "https://api.neso.energy/api/3/action/datastore_search"
PAGE_SIZE = 10000


def fetch_page(resource_id, limit, offset):
    query = urlencode(
        {
            "resource_id": resource_id,
            "limit": limit,
            "offset": offset,
        }
    )

    with urlopen(f"{API_URL}?{query}") as response:
        payload = json.load(response)

    if not payload.get("success"):
        raise RuntimeError("NESO API returned success=false")

    return payload["result"]


def download_resource(resource_name, config, output_dir, row_limit=None):
    resource_id = config["resource_id"]
    output_path = output_dir / config["output_file"]

    rows = []
    offset = 0

    while True:
        remaining = None if row_limit is None else row_limit - len(rows)

        if remaining is not None and remaining <= 0:
            break

        page_limit = PAGE_SIZE if remaining is None else min(PAGE_SIZE, remaining)

        result = fetch_page(resource_id, page_limit, offset)
        records = result["records"]

        if not records:
            break

        rows.extend(records)
        offset += len(records)

        if len(records) < page_limit:
            break

    if not rows:
        raise RuntimeError(f"No records returned for {resource_name}")

    field_names = [field["id"] for field in result["fields"]]

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "source_name": resource_name,
        "resource_id": resource_id,
        "output_file": str(output_path),
        "rows_downloaded": len(rows),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Download configured NESO Data Portal resources."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum rows per source for testing.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "config" / "neso_sources.json"
    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    with config_path.open(encoding="utf-8-sig") as file:
        sources = json.load(file)

    manifest = []

    for source_name, source_config in sources.items():
        print(f"Downloading {source_name}...")
        result = download_resource(
            source_name,
            source_config,
            output_dir,
            row_limit=args.limit,
        )
        manifest.append(result)
        print(f"  {result['rows_downloaded']:,} rows")

    manifest_path = output_dir / "acquisition_manifest.json"

    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

    print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
