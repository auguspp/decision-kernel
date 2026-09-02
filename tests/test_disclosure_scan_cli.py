from __future__ import annotations

from datetime import date, datetime
from io import StringIO
from zoneinfo import ZoneInfo

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.cli import main
from decision_kernel.runtime import cninfo_http
from decision_kernel.runtime.cninfo_http import CninfoDisclosureBatch


SHANGHAI = ZoneInfo("Asia/Shanghai")


def _announcement(identifier: str, *, stock_code: str, published_at: datetime) -> CninfoAnnouncement:
    return CninfoAnnouncement(
        announcement_id=identifier,
        stock_code=stock_code,
        org_id=f"ORG:{stock_code}",
        title=f"官方公告 {identifier}",
        announcement_type=None,
        published_at=published_at,
        source_locator=(
            f"https://static.cninfo.com.cn/finalpage/2026-09-01/{identifier}.PDF"
        ),
    )


def test_scan_disclosures_reuses_frozen_research_clocks_for_generic_and_deep_packages(
    monkeypatch,
) -> None:
    calls: list[tuple[str, date, date]] = []
    covered = _announcement(
        "COVERED",
        stock_code="600036",
        published_at=datetime(2026, 8, 30, 7, 0, tzinfo=SHANGHAI),
    )
    uncovered = _announcement(
        "NEW",
        stock_code="600036",
        published_at=datetime(2026, 9, 1, 18, 0, tzinfo=SHANGHAI),
    )

    def fake_fetch(*, stock_code: str, start_date: date, end_date: date, **_kwargs):
        calls.append((stock_code, start_date, end_date))
        announcements = (covered, uncovered) if stock_code == "600036" else ()
        return CninfoDisclosureBatch(
            stock_code=stock_code,
            org_id=f"ORG:{stock_code}",
            start_date=start_date,
            end_date=end_date,
            announcements=announcements,
        )

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", fake_fetch)
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "scan-disclosures",
            "dogfood/600036-cmb.json",
            "research_cases/603986-gigadevice-deep-research-v1.json",
            "--through",
            "2026-09-02",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    output = stdout.getvalue()
    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert calls == [
        ("600036", date(2026, 8, 30), date(2026, 9, 2)),
        ("603986", date(2026, 9, 2), date(2026, 9, 2)),
    ]
    assert "1 research-uncovered / 2 dated batches / 2 announcements / 2 research cases" in output
    assert "UNCOVERED: 600036 招商银行" in output
    assert "NEW | 官方公告 NEW" in output
    assert "COVERED |" not in output
    assert "RESEARCH STATUS: UNASSESSED" in output
    assert "INVESTMENT AUTHORITY: NONE" in output


def test_scan_disclosures_rejects_duplicate_current_research_before_network(
    monkeypatch,
) -> None:
    calls = 0

    def should_not_fetch(**_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("network must not run for an invalid fixed universe")

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", should_not_fetch)
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "scan-disclosures",
            "dogfood/600036-cmb.json",
            "dogfood/600036-cmb.json",
            "--through",
            "2026-09-02",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert calls == 0
    assert stdout.getvalue() == ""
    assert "more than one current Research package for 600036" in stderr.getvalue()


def test_scan_disclosures_rejects_end_date_before_frozen_research_without_network(
    monkeypatch,
) -> None:
    calls = 0

    def should_not_fetch(**_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("network must not run when the scan end date is invalid")

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", should_not_fetch)
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [
            "scan-disclosures",
            "research_cases/603986-gigadevice-deep-research-v1.json",
            "--through",
            "2026-09-01",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert calls == 0
    assert stdout.getvalue() == ""
    assert "end date precedes frozen Research for 603986" in stderr.getvalue()
