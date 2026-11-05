"""Command line entry point:  python -m bq_tool [--load-bq] [--dry-run]"""
import argparse
import logging
import sys

from .bigquery_loader import load_gcs_to_bigquery
from .config import load_gcp_config, load_quickbase_config
from .gcs import upload_records_jsonl
from .quickbase_api import QuickbaseError, iter_records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bq_tool", description="Migrate a Quickbase table to GCS (and BigQuery).")
    parser.add_argument("--load-bq", action="store_true", help="After uploading, load the file into BigQuery")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and count records without uploading")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(asctime)s %(message)s")

    try:
        qb = load_quickbase_config()
        if args.dry_run:
            print(f"Dry run: {sum(1 for _ in iter_records(qb))} records available")
            return 0
        gcp = load_gcp_config()
        uri, count = upload_records_jsonl(iter_records(qb), gcp)
        print(f"Uploaded {count} records to {uri}")
        if args.load_bq:
            rows = load_gcs_to_bigquery(uri, gcp)
            print(f"BigQuery table {gcp.bq_dataset}.{gcp.bq_table} now has {rows} rows")
    except (RuntimeError, QuickbaseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
