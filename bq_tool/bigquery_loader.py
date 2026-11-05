"""Load an NDJSON file from GCS into a BigQuery table."""
from google.cloud import bigquery

from .config import GcpConfig


def load_gcs_to_bigquery(uri: str, cfg: GcpConfig, write_disposition: str = "WRITE_TRUNCATE") -> int:
    """Load `uri` into `dataset.table` (schema autodetected) and return the resulting row count."""
    if not (cfg.bq_dataset and cfg.bq_table):
        raise RuntimeError("BQ_DATASET and BQ_TABLE must be set to load into BigQuery")
    if cfg.credentials_path:
        from google.oauth2 import service_account as sa

        client = bigquery.Client(
            credentials=sa.Credentials.from_service_account_file(cfg.credentials_path), project=cfg.project
        )
    else:
        client = bigquery.Client(project=cfg.project)
    table_id = f"{client.project}.{cfg.bq_dataset}.{cfg.bq_table}"
    job = client.load_table_from_uri(
        uri,
        table_id,
        job_config=bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            autodetect=True,
            write_disposition=write_disposition,
        ),
    )
    job.result()  # wait; raises on failure
    return client.get_table(table_id).num_rows
