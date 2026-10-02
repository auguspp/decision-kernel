"""Synthetic optional-pagination variants, not retained private IMA responses."""
from copy import deepcopy
import json

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import ima_private_probe as p


def run_fake(data):
    calls = []
    base = {"info_list": [{"id": "synthetic-private-base", "name": "Synthetic reports"}],
            "is_end": True, "next_cursor": ""}
    def send(spec):
        calls.append(deepcopy(spec))
        selected = base if len(calls) == 1 else data
        return 200, json.dumps({"code": 0, "data": selected}).encode()
    result = p.probe("Synthetic reports", "2098", send=send,
                     clock=lambda: "2099-01-01T00:00:00+00:00")
    return result, calls


@pytest.mark.parametrize("count", [0, 1, 100])
def test_both_pagination_fields_absent_are_unknown_not_complete(count, tmp_path):
    data = {"info_list": [{"media_id": f"synthetic-private-{i}",
                            "title": "synthetic-private-title.pdf",
                            "highlight_content": "synthetic-private-snippet"}
                           for i in range(count)]}
    before = deepcopy(data)
    result, calls = run_fake(data)
    assert len(calls) == result["source_calls"] == 2
    assert result["status"] == "CONNECTED_SEARCHABLE"
    doc = result["documents"]
    assert doc["match_count"] == count
    assert doc["is_end"] is None and doc["next_cursor_present"] is None
    assert doc["pagination_reported"] is False and doc["coverage"] == "UNKNOWN"
    assert data == before
    p.write_result(tmp_path / "out", result)
    receipt = (tmp_path / "out/receipt.json").read_text()
    summary = (tmp_path / "out/summary.md").read_text()
    assert "synthetic-private" not in receipt + summary
    assert "pagination not returned" in summary and "UNKNOWN" in summary
    copied = deepcopy(result)
    assert copied.pop("receipt_hash") == canonical_hash(copied)
    assert result["pdf_downloads"] == 0 and result["research_authority"] == "NONE"


@pytest.mark.parametrize("is_end,cursor", [(True, ""), (False, "synthetic-private-cursor")])
def test_explicit_pagination_retains_bool_without_exposing_cursor(is_end, cursor):
    result, calls = run_fake({"info_list": [], "is_end": is_end, "next_cursor": cursor})
    assert len(calls) == 2
    assert result["documents"]["is_end"] is is_end
    assert result["documents"]["next_cursor_present"] is bool(cursor)
    assert result["documents"]["pagination_reported"] is True
    assert result["documents"]["coverage"] == "UNKNOWN"
    assert "synthetic-private-cursor" not in p.encoded(result).decode()


@pytest.mark.parametrize("pagination", [
    {"is_end": True}, {"next_cursor": ""},
    {"is_end": None, "next_cursor": None},
    {"is_end": "false", "next_cursor": ""},
    {"is_end": 0, "next_cursor": ""},
    {"is_end": False, "next_cursor": 1},
    {"is_end": False, "next_cursor": "x" * 4097},
])
def test_present_invalid_or_partial_pagination_is_still_rejected(pagination):
    with pytest.raises(p.ProbeError, match="DOCUMENT_PAGINATION"):
        run_fake({"info_list": [], **pagination})


def test_missing_document_pagination_does_not_relax_rows_or_base_schema():
    with pytest.raises(p.ProbeError, match="MEDIA_ID"):
        run_fake({"info_list": [{"title": "synthetic-invalid.pdf"}]})
    with pytest.raises(p.ProbeError, match="DOCUMENT_ROWS"):
        p.document_rows({"info_list": [{}] * 101})
    with pytest.raises(p.ProbeError, match="BASE_PAGINATION"):
        p.base_rows({"info_list": [{"id": "synthetic", "name": "synthetic"}]})


def test_omitted_pagination_does_not_convert_business_error_to_success():
    with pytest.raises(p.ProbeError, match="BUSINESS_REJECTED"):
        p.payload(b'{"code":110030,"data":{"info_list":[]}}')
