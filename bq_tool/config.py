import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class QuickbaseConfig:
    realm: str
    user_token: str
    table_id: str
    page_size: int = 1000


@dataclass(frozen=True)
class GcpConfig:
    bucket: str
    project: str | None
    credentials_path: str | None
    prefix: str = "quickbase_exports/"
    compress: bool = True
    bq_dataset: str | None = None
    bq_table: str | None = None


def load_quickbase_config() -> QuickbaseConfig:
    load_dotenv()
    return QuickbaseConfig(
        realm=_require("QB_REALMID"),
        user_token=_require("QB_USER_TOKEN"),
        table_id=_require("QB_TABLEID"),
        page_size=int(os.environ.get("PAGE_SIZE", "1000")),
    )


def load_gcp_config() -> GcpConfig:
    load_dotenv()
    return GcpConfig(
        bucket=_require("BUCKET"),
        project=os.environ.get("PROJECT_NAME"),
        # Optional: falls back to Application Default Credentials when unset.
        credentials_path=os.environ.get("GCP_CREDENTIALS_PATH"),
        prefix=os.environ.get("GCS_PREFIX", "quickbase_exports/"),
        compress=os.environ.get("COMPRESS_JSONL", "true").lower() == "true",
        bq_dataset=os.environ.get("BQ_DATASET"),
        bq_table=os.environ.get("BQ_TABLE"),
    )
