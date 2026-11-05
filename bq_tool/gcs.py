"""Stream records to Google Cloud Storage as (optionally gzipped) newline-delimited JSON."""
import gzip
import json
from datetime import datetime, timezone
from typing import Iterable

from google.cloud import storage
from google.oauth2 import service_account

from .config import GcpConfig


def make_blob_name(prefix: str, compress: bool, now: datetime | None = None) -> str:
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix.strip('/')}/qb_records_{ts}.{'jsonl.gz' if compress else 'jsonl'}"


def storage_client(cfg: GcpConfig) -> storage.Client:
    if cfg.credentials_path:
        creds = service_account.Credentials.from_service_account_file(cfg.credentials_path)
        return storage.Client(credentials=creds, project=cfg.project)
    return storage.Client(project=cfg.project)  # Application Default Credentials


def upload_records_jsonl(records: Iterable[dict], cfg: GcpConfig) -> tuple[str, int]:
    """Upload records and return (gs:// URI, record count). Records are streamed, never fully held in memory."""
    blob_name = make_blob_name(cfg.prefix, cfg.compress)
    blob = storage_client(cfg).bucket(cfg.bucket).blob(blob_name)
    blob.chunk_size = 5 * 1024 * 1024
    blob.content_type = "application/x-ndjson"
    count = 0
    with blob.open("wb") as raw:
        sink = gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=6, mtime=0) if cfg.compress else raw
        try:
            for rec in records:
                sink.write((json.dumps(rec, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
                count += 1
        finally:
            if cfg.compress:
                sink.close()
    return f"gs://{cfg.bucket}/{blob_name}", count
