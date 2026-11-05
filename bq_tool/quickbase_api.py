"""Quickbase REST API extraction with pagination, retries and field-label mapping."""
import logging
import re

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import QuickbaseConfig

log = logging.getLogger(__name__)

QB_FIELDS_URL = "https://api.quickbase.com/v1/fields"
QB_QUERY_URL = "https://api.quickbase.com/v1/records/query"


class QuickbaseError(RuntimeError):
    pass


def _headers(cfg: QuickbaseConfig) -> dict:
    return {
        "QB-Realm-Hostname": cfg.realm,
        "Authorization": f"QB-USER-TOKEN {cfg.user_token}",
        "Content-Type": "application/json",
    }


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, (requests.ConnectionError, requests.Timeout))


@retry(
    retry=retry_if_exception_type((requests.HTTPError, requests.ConnectionError, requests.Timeout)),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _request(method: str, url: str, **kwargs) -> dict | list:
    resp = requests.request(method, url, timeout=120, **kwargs)
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        if not _is_retryable(exc):
            raise QuickbaseError(f"Quickbase request failed ({resp.status_code}): {resp.text[:300]}") from exc
        raise
    return resp.json()


def sanitize_column(label: str, taken: set[str]) -> str:
    """Make a Quickbase field label safe for BigQuery (letters/digits/underscore) and unique."""
    name = re.sub(r"[^0-9a-zA-Z_]+", "_", label.strip()).strip("_").lower() or "field"
    if name[0].isdigit():
        name = f"f_{name}"
    base, i = name, 2
    while name in taken:
        name, i = f"{base}_{i}", i + 1
    taken.add(name)
    return name


def get_field_map(cfg: QuickbaseConfig) -> dict[str, str]:
    """Return {field id -> BigQuery-safe column name} for the table."""
    payload = _request("GET", QB_FIELDS_URL, headers=_headers(cfg), params={"tableId": cfg.table_id})
    fields = payload if isinstance(payload, list) else payload.get("fields", [])
    taken: set[str] = set()
    return {str(f["id"]): sanitize_column(f.get("label") or f.get("fieldName") or str(f["id"]), taken) for f in fields}


def flatten_record(record: dict, field_map: dict[str, str]) -> dict:
    """{'3': {'value': 1}} -> {'record_id': 1}; unknown field ids keep their id as the key."""
    out = {}
    for fid, cell in record.items():
        value = cell["value"] if isinstance(cell, dict) and "value" in cell else cell
        out[field_map.get(str(fid), f"field_{fid}")] = value
    return out


def iter_records(cfg: QuickbaseConfig):
    """Yield flattened records page by page until every record has been fetched."""
    field_map = get_field_map(cfg)
    select = [int(fid) for fid in field_map]
    skip, total = 0, None
    while total is None or skip < total:
        body = {"from": cfg.table_id, "select": select, "options": {"top": cfg.page_size, "skip": skip}}
        page = _request("POST", QB_QUERY_URL, headers=_headers(cfg), json=body)
        rows = page.get("data", [])
        total = page.get("metadata", {}).get("totalRecords", skip + len(rows))
        if not rows:
            break
        log.info("Fetched %d/%d records", skip + len(rows), total)
        for row in rows:
            yield flatten_record(row, field_map)
        skip += len(rows)
