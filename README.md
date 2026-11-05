# BQ__tool — Quickbase → GCS → BigQuery

A small, reliable **data-migration tool** that extracts every record from a [Quickbase](https://www.quickbase.com) table, stages it in **Google Cloud Storage** as gzip-compressed NDJSON, and optionally loads it into a **BigQuery** table.

```
Quickbase REST API ──▶ paginate + retry ──▶ GCS (jsonl.gz) ──▶ BigQuery (autodetected schema)
```

## Highlights
- **Complete extraction** – selects every field by ID and paginates using Quickbase's `totalRecords`
- **Resilient** – exponential-backoff retries (429/5xx/network) via `tenacity`
- **BigQuery-ready columns** – field labels are sanitised to `snake_case` and de-duplicated
- **Memory-safe** – records are streamed into GCS rather than held in memory
- **Flexible auth** – service-account key file *or* Application Default Credentials
- Typed config from environment variables, unit-tested extraction logic, GitHub Actions CI

## Project layout
```
bq_tool/
  config.py          environment-driven configuration
  quickbase_api.py   extraction, pagination, retries, field mapping
  gcs.py             streaming NDJSON upload to GCS
  bigquery_loader.py GCS -> BigQuery load job
  cli.py             command-line interface
tests/               pytest suite (network calls mocked)
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in Quickbase + GCP settings
```

### Required Quickbase settings
`QB_REALMID` (e.g. `acme.quickbase.com`), `QB_USER_TOKEN`, `QB_TABLEID`. Create a user token in *My preferences → Manage user tokens*.

## Usage
```bash
python -m bq_tool --dry-run          # count records, upload nothing
python -m bq_tool                    # Quickbase -> GCS
python -m bq_tool --load-bq -v       # Quickbase -> GCS -> BigQuery, with progress logging
```
Output object: `gs://<BUCKET>/<GCS_PREFIX>/qb_records_<UTC timestamp>.jsonl.gz`

## Configuration reference
| Variable | Required | Default | Description |
|---|---|---|---|
| `QB_REALMID`, `QB_USER_TOKEN`, `QB_TABLEID` | yes | – | Quickbase connection |
| `PAGE_SIZE` | no | `1000` | Records per API page |
| `BUCKET` | yes | – | Destination GCS bucket |
| `PROJECT_NAME` | no | ADC project | GCP project |
| `GCS_PREFIX` | no | `quickbase_exports/` | Object prefix |
| `COMPRESS_JSONL` | no | `true` | gzip the output |
| `GCP_CREDENTIALS_PATH` | no | ADC | Service-account JSON key |
| `BQ_DATASET`, `BQ_TABLE` | with `--load-bq` | – | BigQuery destination (table is replaced on each load) |

## Tests
```bash
pip install -r requirements-dev.txt && pytest
```

## Security
Never commit `.env` or service-account keys (both are git-ignored). Grant the service account only `Storage Object Creator` and `BigQuery Data Editor` / `Job User`.
