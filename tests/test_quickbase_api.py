from unittest import mock

import pytest

from bq_tool import quickbase_api as qb
from bq_tool.config import QuickbaseConfig
from bq_tool.gcs import make_blob_name

CFG = QuickbaseConfig(realm="x.quickbase.com", user_token="t", table_id="tbl", page_size=2)


def test_sanitize_column_unique_and_safe():
    taken = set()
    assert qb.sanitize_column("Record ID#", taken) == "record_id"
    assert qb.sanitize_column("record id", taken) == "record_id_2"
    assert qb.sanitize_column("3rd Party", taken) == "f_3rd_party"
    assert qb.sanitize_column("###", taken) == "field"


def test_flatten_record_maps_ids():
    out = qb.flatten_record({"3": {"value": 7}, "9": {"value": "x"}, "50": 1}, {"3": "record_id", "9": "name"})
    assert out == {"record_id": 7, "name": "x", "field_50": 1}


def test_iter_records_paginates_until_total():
    fields = [{"id": 3, "label": "Record ID"}, {"id": 6, "label": "Name"}]
    pages = [
        {"data": [{"3": {"value": 1}, "6": {"value": "a"}}, {"3": {"value": 2}, "6": {"value": "b"}}], "metadata": {"totalRecords": 3}},
        {"data": [{"3": {"value": 3}, "6": {"value": "c"}}], "metadata": {"totalRecords": 3}},
    ]
    with mock.patch.object(qb, "_request", side_effect=[fields, *pages]) as req:
        rows = list(qb.iter_records(CFG))
    assert [r["record_id"] for r in rows] == [1, 2, 3]
    assert req.call_args_list[2].kwargs["json"]["options"]["skip"] == 2


def test_iter_records_handles_empty_table():
    with mock.patch.object(qb, "_request", side_effect=[[{"id": 3, "label": "ID"}], {"data": [], "metadata": {"totalRecords": 0}}]):
        assert list(qb.iter_records(CFG)) == []


def test_blob_name():
    from datetime import datetime, timezone

    ts = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert make_blob_name("exports/", True, ts) == "exports/qb_records_20250102T030405Z.jsonl.gz"
    assert make_blob_name("exports", False, ts).endswith(".jsonl")
