from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.research_workflow_v1 import ResearchFunnelTerminalState
from decision_kernel.runtime.disclosure_radar import group_disclosures_by_publication_date
from decision_kernel.runtime.disclosure_receipts import (
    DisclosureAssessmentReceipt,
    disclosure_batch_announcement_ids,
    filter_unassessed_disclosure_batches,
    merge_disclosure_assessment_receipts,
    parse_disclosure_assessment_receipts,
    serialize_disclosure_assessment_receipts,
    write_disclosure_assessment_receipts,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
SNAPSHOT_A = UUID("11111111-1111-1111-1111-111111111111")
SNAPSHOT_B = UUID("22222222-2222-2222-2222-222222222222")
RESEARCH_AS_OF = datetime(2026, 8, 26, 12, 0, tzinfo=SHANGHAI)
ASSESSED_AT = datetime(2026, 8, 28, 9, 0, tzinfo=SHANGHAI)


def _announcement(identifier: str, *, hour: int = 17) -> CninfoAnnouncement:
    return CninfoAnnouncement(
        announcement_id=identifier,
        stock_code="300750",
        org_id="gssz0000300750",
        title=f"官方公告 {identifier}",
        announcement_type=None,
        published_at=datetime(2026, 8, 27, hour, 0, tzinfo=SHANGHAI),
        source_locator=f"https://static.cninfo.com.cn/finalpage/2026-08-27/{identifier}.PDF",
    )


def _receipt(
    batch,
    *,
    snapshot_id: UUID = SNAPSHOT_A,
    result: ResearchFunnelTerminalState = ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
    assessed_at: datetime = ASSESSED_AT,
) -> DisclosureAssessmentReceipt:
    return DisclosureAssessmentReceipt(
        stock_code=batch.stock_code,
        announcement_ids=disclosure_batch_announcement_ids(batch),
        research_snapshot_id=snapshot_id,
        research_as_of=RESEARCH_AS_OF,
        assessment_result=result,
        assessed_at=assessed_at,
    )


def test_exact_wait_for_trigger_receipt_suppresses_same_batch_for_same_research() -> None:
    batch = group_disclosures_by_publication_date((_announcement("1225519101"),))[0]

    unassessed = filter_unassessed_disclosure_batches(
        (batch,),
        research_identity_by_stock={"300750": (SNAPSHOT_A, RESEARCH_AS_OF)},
        receipts=(_receipt(batch),),
    )

    assert unassessed == ()


def test_same_day_with_new_underlying_announcement_is_not_hidden_by_old_receipt() -> None:
    original = group_disclosures_by_publication_date((_announcement("A"),))[0]
    expanded = group_disclosures_by_publication_date(
        (_announcement("A"), _announcement("B", hour=18))
    )[0]

    unassessed = filter_unassessed_disclosure_batches(
        (expanded,),
        research_identity_by_stock={"300750": (SNAPSHOT_A, RESEARCH_AS_OF)},
        receipts=(_receipt(original),),
    )

    assert unassessed == (expanded,)


def test_receipt_from_other_research_snapshot_does_not_suppress_batch() -> None:
    batch = group_disclosures_by_publication_date((_announcement("1225519101"),))[0]

    unassessed = filter_unassessed_disclosure_batches(
        (batch,),
        research_identity_by_stock={"300750": (SNAPSHOT_B, RESEARCH_AS_OF)},
        receipts=(_receipt(batch, snapshot_id=SNAPSHOT_A),),
    )

    assert unassessed == (batch,)


def test_receipt_requires_sorted_exact_announcement_identity() -> None:
    try:
        DisclosureAssessmentReceipt(
            stock_code="300750",
            announcement_ids=("B", "A"),
            research_snapshot_id=SNAPSHOT_A,
            research_as_of=RESEARCH_AS_OF,
            assessment_result=ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
            assessed_at=ASSESSED_AT,
        )
    except ValueError as exc:
        assert "unique and sorted" in str(exc)
    else:
        raise AssertionError("unsorted receipt identity must fail closed")


def test_receipt_json_parser_preserves_exact_assessment_identity() -> None:
    payload = json.dumps(
        [
            {
                "source_lane": "CNINFO",
                "stock_code": "300750",
                "announcement_ids": ["1225519101"],
                "research_snapshot_id": str(SNAPSHOT_A),
                "research_as_of": RESEARCH_AS_OF.isoformat(),
                "assessment_result": "WAIT_FOR_TRIGGER",
                "assessed_at": ASSESSED_AT.isoformat(),
            }
        ]
    )

    receipts = parse_disclosure_assessment_receipts(payload)

    assert receipts == (
        DisclosureAssessmentReceipt(
            source_lane="CNINFO",
            stock_code="300750",
            announcement_ids=("1225519101",),
            research_snapshot_id=SNAPSHOT_A,
            research_as_of=RESEARCH_AS_OF,
            assessment_result=ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
            assessed_at=ASSESSED_AT,
        ),
    )


def test_receipt_json_parser_rejects_unknown_semantics_fields() -> None:
    payload = json.dumps(
        [
            {
                "source_lane": "CNINFO",
                "stock_code": "300750",
                "announcement_ids": ["1225519101"],
                "research_snapshot_id": str(SNAPSHOT_A),
                "research_as_of": RESEARCH_AS_OF.isoformat(),
                "assessment_result": "WAIT_FOR_TRIGGER",
                "assessed_at": ASSESSED_AT.isoformat(),
                "assessment_method": "future-version",
            }
        ]
    )

    try:
        parse_disclosure_assessment_receipts(payload)
    except ValueError as exc:
        assert "unknown fields" in str(exc)
    else:
        raise AssertionError("unknown receipt semantics must fail closed")


def test_receipt_json_parser_rejects_duplicate_exact_identity() -> None:
    batch = group_disclosures_by_publication_date((_announcement("1225519101"),))[0]
    receipt = _receipt(batch)
    raw = serialize_disclosure_assessment_receipts((receipt,))
    payload = json.loads(raw)
    payload.append(dict(payload[0]))

    try:
        parse_disclosure_assessment_receipts(json.dumps(payload))
    except ValueError as exc:
        assert "duplicate disclosure assessment receipt" in str(exc)
    else:
        raise AssertionError("duplicate receipt memory must fail closed")


def test_receipt_merge_is_idempotent_and_preserves_first_assessment_clock() -> None:
    batch = group_disclosures_by_publication_date((_announcement("1225519101"),))[0]
    first = _receipt(batch)
    repeated = _receipt(batch, assessed_at=ASSESSED_AT + timedelta(days=1))

    merged = merge_disclosure_assessment_receipts((first,), (repeated,))

    assert merged == (first,)


def test_receipt_merge_rejects_conflicting_terminal_assessment_for_same_identity() -> None:
    batch = group_disclosures_by_publication_date((_announcement("1225519101"),))[0]
    waiting = _receipt(batch)
    dropped = _receipt(
        batch,
        result=ResearchFunnelTerminalState.DROP_FOR_NOW,
        assessed_at=ASSESSED_AT + timedelta(hours=1),
    )

    try:
        merge_disclosure_assessment_receipts((waiting,), (dropped,))
    except ValueError as exc:
        assert "conflicting disclosure assessment receipt" in str(exc)
    else:
        raise AssertionError("conflicting receipt assessments must fail closed")


def test_receipt_serialization_is_deterministic_and_round_trips() -> None:
    later_batch = group_disclosures_by_publication_date((_announcement("B", hour=18),))[0]
    earlier_batch = group_disclosures_by_publication_date((_announcement("A", hour=17),))[0]
    later = _receipt(later_batch, snapshot_id=SNAPSHOT_B)
    earlier = _receipt(earlier_batch, snapshot_id=SNAPSHOT_A)

    serialized = serialize_disclosure_assessment_receipts((later, earlier))

    assert serialized.endswith("\n")
    assert serialized.index('"A"') < serialized.index('"B"')
    assert parse_disclosure_assessment_receipts(serialized) == (earlier, later)
    assert serialize_disclosure_assessment_receipts((earlier, later)) == serialized


def test_receipt_writer_atomically_replaces_explicit_json_file(tmp_path) -> None:
    batch = group_disclosures_by_publication_date((_announcement("1225519101"),))[0]
    receipt = _receipt(batch)
    path = tmp_path / "state" / "receipts.json"
    path.parent.mkdir(parents=True)
    path.write_text("stale", encoding="utf-8")

    write_disclosure_assessment_receipts(path, (receipt,))

    assert parse_disclosure_assessment_receipts(path.read_text(encoding="utf-8")) == (receipt,)
    assert not (path.parent / ".receipts.json.tmp").exists()
