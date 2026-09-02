from __future__ import annotations

from datetime import date, datetime
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import decision_kernel.cli as cli
from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.runtime import cninfo_http
from decision_kernel.runtime.cninfo_http import CninfoDisclosureBatch


SHANGHAI = ZoneInfo("Asia/Shanghai")


def _announcement(identifier: str, *, published_at: datetime) -> CninfoAnnouncement:
    return CninfoAnnouncement(
        announcement_id=identifier,
        stock_code="600036",
        org_id="ORG:600036",
        title=f"官方公告 {identifier}",
        announcement_type=None,
        published_at=published_at,
        source_locator=f"https://static.cninfo.com.cn/finalpage/2026-09-01/{identifier}.PDF",
    )


def test_scan_can_emit_one_packet_per_still_unassessed_batch(monkeypatch, tmp_path) -> None:
    announcement = _announcement(
        "NEW",
        published_at=datetime(2026, 9, 1, 18, 0, tzinfo=SHANGHAI),
    )

    def fake_fetch(*, stock_code: str, start_date: date, end_date: date, **_kwargs):
        return CninfoDisclosureBatch(
            stock_code=stock_code,
            org_id="ORG:600036",
            start_date=start_date,
            end_date=end_date,
            announcements=(announcement,),
        )

    prepared = []

    def fake_prepare(*, research_snapshot, batch, prepared_at):
        prepared.append((research_snapshot.ticker, batch.publication_date, prepared_at))
        return SimpleNamespace(assessment_input_hash="d" * 64)

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", fake_fetch)
    monkeypatch.setattr(cli, "prepare_disclosure_assessment_packet", fake_prepare)
    monkeypatch.setattr(
        cli,
        "serialize_disclosure_assessment_packet",
        lambda _packet: '{"disclosure_assessment_status":"UNASSESSED"}\n',
    )
    packet_dir = tmp_path / "packets"
    stdout = StringIO()
    stderr = StringIO()

    exit_code = cli.main(
        [
            "scan-disclosures",
            "dogfood/600036-cmb.json",
            "--through",
            "2026-09-02",
            "--packet-dir",
            str(packet_dir),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert len(prepared) == 1
    assert prepared[0][0:2] == ("600036", date(2026, 9, 1))
    packet_path = packet_dir / "600036-2026-09-01-dddddddddddddddd.json"
    assert packet_path.read_text(encoding="utf-8") == (
        '{"disclosure_assessment_status":"UNASSESSED"}\n'
    )
    output = stdout.getvalue()
    assert "ASSESSMENT PACKETS: 1 prepared" in output
    assert f"PACKET: {packet_path} | input_hash={'d' * 64}" in output
    assert "DISCLOSURE ASSESSMENT STATUS: UNASSESSED" in output
    assert "INVESTMENT AUTHORITY: NONE" in output


def test_packet_limit_fails_closed_before_any_pdf_preparation(monkeypatch, tmp_path) -> None:
    announcements = (
        _announcement(
            "FIRST",
            published_at=datetime(2026, 9, 1, 18, 0, tzinfo=SHANGHAI),
        ),
        _announcement(
            "SECOND",
            published_at=datetime(2026, 9, 2, 18, 0, tzinfo=SHANGHAI),
        ),
    )

    def fake_fetch(*, stock_code: str, start_date: date, end_date: date, **_kwargs):
        return CninfoDisclosureBatch(
            stock_code=stock_code,
            org_id="ORG:600036",
            start_date=start_date,
            end_date=end_date,
            announcements=announcements,
        )

    prepare_calls = 0

    def should_not_prepare(**_kwargs):
        nonlocal prepare_calls
        prepare_calls += 1
        raise AssertionError("packet preparation must not start after the cap is exceeded")

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", fake_fetch)
    monkeypatch.setattr(cli, "prepare_disclosure_assessment_packet", should_not_prepare)
    stdout = StringIO()
    stderr = StringIO()

    exit_code = cli.main(
        [
            "scan-disclosures",
            "dogfood/600036-cmb.json",
            "--through",
            "2026-09-02",
            "--packet-dir",
            str(tmp_path / "packets"),
            "--packet-limit",
            "1",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert prepare_calls == 0
    assert stdout.getvalue() == ""
    assert "2 unassessed > 1; no packets written" in stderr.getvalue()
    assert not (tmp_path / "packets").exists()


def test_nonpositive_packet_limit_fails_before_cninfo_network(monkeypatch, tmp_path) -> None:
    calls = 0

    def should_not_fetch(**_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("invalid packet budget must fail before CNINFO")

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", should_not_fetch)
    stdout = StringIO()
    stderr = StringIO()

    exit_code = cli.main(
        [
            "scan-disclosures",
            "dogfood/600036-cmb.json",
            "--through",
            "2026-09-02",
            "--packet-dir",
            str(tmp_path / "packets"),
            "--packet-limit",
            "0",
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert calls == 0
    assert stdout.getvalue() == ""
    assert "packet limit must be positive" in stderr.getvalue()
