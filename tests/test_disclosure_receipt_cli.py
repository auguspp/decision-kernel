from __future__ import annotations

from datetime import date, datetime
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.cli import build_parser, main
from decision_kernel.research_commit import ResearchCommitPackage
from decision_kernel.research_workflow_v1 import ResearchFunnelTerminalState
from decision_kernel.runtime import cninfo_http
from decision_kernel.runtime.cninfo_http import CninfoDisclosureBatch
from decision_kernel.runtime.disclosure_receipts import parse_disclosure_assessment_receipts


SHANGHAI = ZoneInfo("Asia/Shanghai")
PACKAGE_PATH = Path("dogfood/300750-catl.json")


def _announcement(identifier: str, *, published_at: datetime) -> CninfoAnnouncement:
    return CninfoAnnouncement(
        announcement_id=identifier,
        stock_code="300750",
        org_id="gssz0000300750",
        title=f"官方公告 {identifier}",
        announcement_type=None,
        published_at=published_at,
        source_locator=f"https://static.cninfo.com.cn/finalpage/2026-08-12/{identifier}.PDF",
    )


def test_record_disclosure_assessment_derives_exact_batch_and_research_identity(
    monkeypatch,
    tmp_path,
) -> None:
    first = _announcement(
        "A",
        published_at=datetime(2026, 8, 12, 17, 0, tzinfo=SHANGHAI),
    )
    second = _announcement(
        "B",
        published_at=datetime(2026, 8, 12, 18, 0, tzinfo=SHANGHAI),
    )
    calls: list[tuple[str, date, date]] = []

    def fake_fetch(*, stock_code: str, start_date: date, end_date: date, **_kwargs):
        calls.append((stock_code, start_date, end_date))
        return CninfoDisclosureBatch(
            stock_code=stock_code,
            org_id="gssz0000300750",
            start_date=start_date,
            end_date=end_date,
            announcements=(second, first),
        )

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", fake_fetch)
    receipts_path = tmp_path / "receipts.json"
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "record-disclosure-assessment",
            str(PACKAGE_PATH),
            "--publication-date",
            "2026-08-12",
            "--result",
            "WAIT_FOR_TRIGGER",
            "--receipts",
            str(receipts_path),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    snapshot = ResearchCommitPackage.model_validate_json(
        PACKAGE_PATH.read_text(encoding="utf-8")
    ).research_snapshot
    receipts = parse_disclosure_assessment_receipts(
        receipts_path.read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert calls == [("300750", date(2026, 8, 12), date(2026, 8, 12))]
    assert len(receipts) == 1
    assert receipts[0].announcement_ids == ("A", "B")
    assert receipts[0].research_snapshot_id == snapshot.id
    assert receipts[0].research_as_of == snapshot.as_of_datetime
    assert receipts[0].assessment_result is ResearchFunnelTerminalState.WAIT_FOR_TRIGGER
    assert "DISCLOSURE ASSESSMENT RECORDED: 300750 2026-08-12" in stdout.getvalue()
    assert "announcements=A,B" in stdout.getvalue()
    assert "INVESTMENT AUTHORITY: NONE" in stdout.getvalue()


def test_record_disclosure_assessment_is_idempotent_for_same_quiet_result(
    monkeypatch,
    tmp_path,
) -> None:
    announcement = _announcement(
        "A",
        published_at=datetime(2026, 8, 4, 17, 0, tzinfo=SHANGHAI),
    )

    def fake_fetch(*, stock_code: str, start_date: date, end_date: date, **_kwargs):
        return CninfoDisclosureBatch(
            stock_code=stock_code,
            org_id="gssz0000300750",
            start_date=start_date,
            end_date=end_date,
            announcements=(announcement,),
        )

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", fake_fetch)
    receipts_path = tmp_path / "receipts.json"
    argv = [
        "record-disclosure-assessment",
        str(PACKAGE_PATH),
        "--publication-date",
        "2026-08-04",
        "--result",
        "WAIT_FOR_TRIGGER",
        "--receipts",
        str(receipts_path),
    ]

    first_stdout = StringIO()
    assert main(argv, stdout=first_stdout, stderr=StringIO()) == 0
    first = parse_disclosure_assessment_receipts(
        receipts_path.read_text(encoding="utf-8")
    )

    second_stdout = StringIO()
    assert main(argv, stdout=second_stdout, stderr=StringIO()) == 0
    second = parse_disclosure_assessment_receipts(
        receipts_path.read_text(encoding="utf-8")
    )

    assert second == first
    assert "DISCLOSURE ASSESSMENT UNCHANGED" in second_stdout.getvalue()


def test_record_disclosure_assessment_rejects_invalid_existing_memory_before_network(
    monkeypatch,
    tmp_path,
) -> None:
    calls = 0

    def should_not_fetch(**_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("network must not run when existing receipt memory is invalid")

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", should_not_fetch)
    receipts_path = tmp_path / "receipts.json"
    receipts_path.write_text("{}", encoding="utf-8")
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "record-disclosure-assessment",
            str(PACKAGE_PATH),
            "--publication-date",
            "2026-08-04",
            "--result",
            "DROP_FOR_NOW",
            "--receipts",
            str(receipts_path),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert calls == 0
    assert stdout.getvalue() == ""
    assert "receipt file must be a JSON array" in stderr.getvalue()


def test_record_disclosure_assessment_rejects_date_before_research_without_network(
    monkeypatch,
    tmp_path,
) -> None:
    calls = 0

    def should_not_fetch(**_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("network must not run for a pre-Research assessment date")

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", should_not_fetch)
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "record-disclosure-assessment",
            str(PACKAGE_PATH),
            "--publication-date",
            "2026-07-26",
            "--result",
            "DROP_FOR_NOW",
            "--receipts",
            str(tmp_path / "receipts.json"),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert calls == 0
    assert stdout.getvalue() == ""
    assert "assessment date precedes frozen Research for 300750" in stderr.getvalue()


def test_record_disclosure_assessment_rejects_research_covered_batch(
    monkeypatch,
    tmp_path,
) -> None:
    calls = 0
    covered = _announcement(
        "COVERED",
        published_at=datetime(2026, 7, 27, 7, 0, tzinfo=SHANGHAI),
    )

    def fake_fetch(*, stock_code: str, start_date: date, end_date: date, **_kwargs):
        nonlocal calls
        calls += 1
        return CninfoDisclosureBatch(
            stock_code=stock_code,
            org_id="gssz0000300750",
            start_date=start_date,
            end_date=end_date,
            announcements=(covered,),
        )

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", fake_fetch)
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "record-disclosure-assessment",
            str(PACKAGE_PATH),
            "--publication-date",
            "2026-07-27",
            "--result",
            "DROP_FOR_NOW",
            "--receipts",
            str(tmp_path / "receipts.json"),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert calls == 1
    assert stdout.getvalue() == ""
    assert "requires exactly one research-uncovered official batch" in stderr.getvalue()


def test_record_disclosure_assessment_parser_excludes_deepen_required_receipts() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "record-disclosure-assessment",
                str(PACKAGE_PATH),
                "--publication-date",
                "2026-08-12",
                "--result",
                "DEEPEN_REQUIRED",
                "--receipts",
                "receipts.json",
            ]
        )
