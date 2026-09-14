"""Exercise the saved full-context read INSIDE the existing capture function.

Synthetic transport boundary only. No live CNINFO/GitHub/provider calls, successor
reservation or formal Research. A sentinel stops before document representation.
The real 636462-byte Guangha file is checked separately, not replaced by this fixture.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
from types import SimpleNamespace
import socket

import pytest

from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_full_input as full
from decision_kernel.runtime import stock_source_successor as successor


TICKER = "300711"
CODE = "300711.SZ"
COMMIT = "a" * 40
REPORT = "synthetic-report"
STAMP = "2026-09-14T04:00:00+00:00"


class ReachedSavedDocument(RuntimeError):
    pass


@dataclass(frozen=True)
class Announcement:
    announcement_id: str = REPORT
    title: str = "2026年半年度报告"
    published_at: datetime = datetime(2026, 8, 28, tzinfo=timezone.utc)
    source_locator: str = "https://static.cninfo.com.cn/synthetic-only.pdf"


def context_bytes():
    # Over 512 KiB, but within the EXISTING decoded-input bound. Include both
    # supporting and contrary text; neither may disappear at this adapter seam.
    return full._raw({
        "stock_observation": {"row": {"thscode": CODE}},
        "issuer_inventory": {"stock_code": TICKER, "selected_ids": [REPORT],
                             "report_id": REPORT},
        "issuer_documents": [{"announcement_id": REPORT, "page_count": 1,
            "pages": [{"page_number": 1, "text": "300711 报告 支持与反证 UNKNOWN\n" * 14000}]}],
    })


def setup_capture(tmp_path, monkeypatch, raw):
    def forbidden(*args, **kwargs):
        pytest.fail("saved-context regression must not contact a network or provider")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(successor.cninfo, "_request_json", forbidden)
    monkeypatch.setattr(successor.cninfo, "fetch_cninfo_pdf_bytes", forbidden)
    monkeypatch.setattr(once, "model_call", forbidden)
    row = Announcement()
    batch = SimpleNamespace(stock_code=TICKER, org_id="synthetic-org",
        start_date=date(2025, 8, 10), end_date=date(2026, 9, 14), announcements=(row,))
    fetches = []
    def fetch(**kwargs):
        fetches.append(kwargs)
        return batch
    monkeypatch.setattr(successor.cninfo, "fetch_cninfo_disclosures", fetch)
    reached = []
    def saved(session, thscode, identifier):
        reached.append((thscode, identifier))
        assert session.files[CODE + "/sources/prepared-context.json"] == raw
        raise ReachedSavedDocument("complete-context gate passed, representation not executed")
    monkeypatch.setattr(successor, "_saved_document", saved)
    binding = {"thscode": CODE, "material": {"selected_ids": [REPORT],
        "prepared_context_bytes": len(raw), "prepared_context_sha256": once.sha(raw)}}
    prefix = CODE + "/sources/"
    files = {prefix + "prepared-context.json": raw,
        prefix + "inventory.json": full._raw({"selected_ids": [REPORT], "report_id": REPORT}),
        prefix + "source-preparation.json": full._raw({"selected_ids": [REPORT]})}
    session = successor.Session({}, {"items": [binding]}, files, {}, COMMIT, "b"*40, b"{}", {})
    kwargs = dict(session=session, ticker=TICKER, observation={"row": {"thscode": CODE}},
        api=object(), code_commit=COMMIT, output=tmp_path / "sources", clock=lambda: STAMP)
    return kwargs, binding, reached, fetches


def test_capture_reads_complete_saved_context_through_existing_full_input_gate(tmp_path, monkeypatch):
    raw = context_bytes()
    assert identity.MAX_BYTES == full.STORED_BYTES == 512 * 1024
    assert identity.MAX_BYTES < len(raw) <= full.DECODED_BYTES
    with pytest.raises(identity.ExecutionIdentityError, match="EXECUTION_INPUT_SIZE_INVALID"):
        identity._json(raw)
    args, _, reached, fetches = setup_capture(tmp_path, monkeypatch, raw)
    with pytest.raises(ReachedSavedDocument):
        successor.capture(**args)
    assert reached == [(CODE, REPORT)] and len(fetches) == 1
    assert args["session"].files[CODE + "/sources/prepared-context.json"] == raw
    assert list(args["output"].iterdir()) == [args["output"] / "inventory.json"]


def test_capture_still_requires_exact_predecessor_bytes(tmp_path, monkeypatch):
    raw = context_bytes()
    args, binding, reached, _ = setup_capture(tmp_path, monkeypatch, raw)
    binding["material"]["prepared_context_sha256"] = "0" * 64
    with pytest.raises(once.TrialError, match="saved context bytes differ"):
        successor.capture(**args)
    assert reached == []


@pytest.mark.parametrize("case,reason", [
    ("wrong_ticker", "issuer/document inventory"),
    ("missing_page", "page inventory"),
    ("duplicate_document", "issuer/document inventory"),
    ("noncanonical", "serialization differs"),
    ("duplicate_key", "duplicate JSON key"),
    ("nonfinite", "nonfinite JSON value"),
    ("over_decoded_bound", "byte bound"),
])
def test_capture_rejects_invalid_complete_context_even_with_matching_hash(tmp_path, monkeypatch, case, reason):
    raw = context_bytes()
    value = full._context(raw, TICKER)
    if case == "wrong_ticker":
        value["issuer_inventory"]["stock_code"] = "603353"
    elif case == "missing_page":
        value["issuer_documents"][0]["pages"] = []
    elif case == "duplicate_document":
        value["issuer_documents"].append(value["issuer_documents"][0])
    elif case == "over_decoded_bound":
        value["issuer_documents"][0]["pages"][0]["text"] = "x" * (full.DECODED_BYTES + 1)
    raw = full._raw(value)
    if case == "noncanonical":
        raw += b" "
    elif case == "duplicate_key":
        raw = b'{"stock_observation": {},' + raw[1:]
    elif case == "nonfinite":
        raw = b'{"invalid_number": NaN,' + raw[1:]
    args, _, reached, _ = setup_capture(tmp_path, monkeypatch, raw)
    with pytest.raises(ValueError, match=reason):
        successor.capture(**args)
    assert reached == []
