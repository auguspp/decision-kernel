from __future__ import annotations

import json
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import decision_kernel.cli as cli
from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import cninfo_http
from decision_kernel.runtime.cninfo_http import CninfoDisclosureBatch
from decision_kernel.runtime.disclosure_attempt_history import (
    disclosure_prefetch_identity,
    empty_attempt_history,
)
from decision_kernel.runtime.disclosure_radar import group_disclosures_by_publication_date


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


def _write_history(tmp_path: Path, attempts=()) -> Path:
    payload = empty_attempt_history()
    payload["attempts"] = [
        {"prefetch_hash": prefetch, "assessment_input_hashes": sorted(keys)}
        for prefetch, keys in sorted(attempts)
    ]
    payload["reserved_packet_count"] = sum(
        len(row["assessment_input_hashes"]) for row in payload["attempts"]
    )
    unsigned = dict(payload)
    unsigned.pop("history_hash")
    payload["history_hash"] = canonical_hash(unsigned)
    path = tmp_path / "attempt-history.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


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
    history = _write_history(tmp_path)
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
            "--attempt-history",
            str(history),
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
    assert "PACKET WINDOW: 1 unseen-lineage / 0 attempted-lineage / 1 preparation-selected / 0 deferred-by-capacity / 1 unassessed" in output
    assert "EXACT ATTEMPT REVALIDATION: 0 unchanged-not-reemitted" in output
    assert "ASSESSMENT PACKETS: 1 prepared" in output
    assert f"PACKET: {packet_path} | input_hash={'d' * 64}" in output
    assert "DISCLOSURE ASSESSMENT STATUS: UNASSESSED" in output
    assert "INVESTMENT AUTHORITY: NONE" in output


def test_packet_limit_prepares_oldest_window_and_reports_deferred(monkeypatch, tmp_path) -> None:
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

    prepared = []

    def fake_prepare(*, research_snapshot, batch, prepared_at):
        prepared.append(batch.publication_date)
        return SimpleNamespace(assessment_input_hash="e" * 64)

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", fake_fetch)
    monkeypatch.setattr(cli, "prepare_disclosure_assessment_packet", fake_prepare)
    monkeypatch.setattr(cli, "serialize_disclosure_assessment_packet", lambda _packet: "{}\n")
    stdout = StringIO()
    stderr = StringIO()
    history = _write_history(tmp_path)

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
            "--attempt-history",
            str(history),
        ],
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert prepared == [date(2026, 9, 1)]
    assert "2 unassessed" in stdout.getvalue()
    assert "2 unseen-lineage / 0 attempted-lineage / 1 preparation-selected / 1 deferred-by-capacity / 2 unassessed" in stdout.getvalue()
    assert len(list((tmp_path / "packets").glob("*.json"))) == 1


def test_attempt_history_prioritizes_unseen_work_without_starvation(monkeypatch, tmp_path) -> None:
    announcements = (
        _announcement("FIRST", published_at=datetime(2026, 9, 1, 18, 0, tzinfo=SHANGHAI)),
        _announcement("SECOND", published_at=datetime(2026, 9, 2, 18, 0, tzinfo=SHANGHAI)),
    )

    def fake_fetch(*, stock_code: str, start_date: date, end_date: date, **_kwargs):
        return CninfoDisclosureBatch(
            stock_code=stock_code, org_id="ORG:600036", start_date=start_date,
            end_date=end_date, announcements=announcements,
        )

    snapshot = cli._research_snapshot_from_raw_package(
        Path("dogfood/600036-cmb.json").read_text(encoding="utf-8")
    )
    first_batch = group_disclosures_by_publication_date((announcements[0],))[0]
    attempted = disclosure_prefetch_identity(research_snapshot=snapshot, batch=first_batch)
    history = _write_history(tmp_path, ((attempted, ("a" * 64,)),))
    prepared = []

    def fake_prepare(*, research_snapshot, batch, prepared_at):
        prepared.append(batch.publication_date)
        return SimpleNamespace(assessment_input_hash="f" * 64)

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", fake_fetch)
    monkeypatch.setattr(cli, "prepare_disclosure_assessment_packet", fake_prepare)
    monkeypatch.setattr(cli, "serialize_disclosure_assessment_packet", lambda _packet: "{}\n")
    stdout, stderr = StringIO(), StringIO()

    code = cli.main([
        "scan-disclosures", "dogfood/600036-cmb.json", "--through", "2026-09-02",
        "--packet-dir", str(tmp_path / "packets"), "--packet-limit", "1",
        "--attempt-history", str(history),
    ], stdout=stdout, stderr=stderr)

    assert code == 0 and stderr.getvalue() == ""
    assert prepared == [date(2026, 9, 2)]
    assert "1 unseen-lineage / 1 attempted-lineage / 1 preparation-selected / 1 deferred-by-capacity / 2 unassessed" in stdout.getvalue()


def test_attempted_lineage_revalidation_keeps_changed_evidence_new(monkeypatch, tmp_path) -> None:
    announcement = _announcement("ONLY", published_at=datetime(2026, 9, 1, 18, 0, tzinfo=SHANGHAI))
    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", lambda **kwargs:
        CninfoDisclosureBatch(stock_code="600036", org_id="ORG:600036",
                              start_date=kwargs["start_date"], end_date=kwargs["end_date"],
                              announcements=(announcement,)))
    snapshot = cli._research_snapshot_from_raw_package(
        Path("dogfood/600036-cmb.json").read_text(encoding="utf-8")
    )
    only_batch = group_disclosures_by_publication_date((announcement,))[0]
    prefetch = disclosure_prefetch_identity(research_snapshot=snapshot, batch=only_batch)
    history = _write_history(tmp_path, ((prefetch, ("a" * 64,)),))
    monkeypatch.setattr(cli, "prepare_disclosure_assessment_packet", lambda **kwargs:
        SimpleNamespace(assessment_input_hash="b" * 64))
    monkeypatch.setattr(cli, "serialize_disclosure_assessment_packet", lambda _packet: "{}\n")
    stdout, stderr = StringIO(), StringIO()

    code = cli.main([
        "scan-disclosures", "dogfood/600036-cmb.json", "--through", "2026-09-02",
        "--packet-dir", str(tmp_path / "packets"), "--packet-limit", "1",
        "--attempt-history", str(history),
    ], stdout=stdout, stderr=stderr)

    assert code == 0 and stderr.getvalue() == ""
    assert "ASSESSMENT PACKETS: 1 prepared" in stdout.getvalue()
    assert "EXACT ATTEMPT REVALIDATION: 0 unchanged-not-reemitted" in stdout.getvalue()
    assert len(list((tmp_path / "packets").glob("*.json"))) == 1


def test_exact_attempt_revalidation_does_not_reemit_same_packet(monkeypatch, tmp_path) -> None:
    announcement = _announcement("ONLY", published_at=datetime(2026, 9, 1, 18, 0, tzinfo=SHANGHAI))
    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", lambda **kwargs:
        CninfoDisclosureBatch(stock_code="600036", org_id="ORG:600036",
                              start_date=kwargs["start_date"], end_date=kwargs["end_date"],
                              announcements=(announcement,)))
    snapshot = cli._research_snapshot_from_raw_package(
        Path("dogfood/600036-cmb.json").read_text(encoding="utf-8")
    )
    only_batch = group_disclosures_by_publication_date((announcement,))[0]
    prefetch = disclosure_prefetch_identity(research_snapshot=snapshot, batch=only_batch)
    exact = "a" * 64
    history = _write_history(tmp_path, ((prefetch, (exact,)),))
    monkeypatch.setattr(cli, "prepare_disclosure_assessment_packet", lambda **kwargs:
        SimpleNamespace(assessment_input_hash=exact))
    stdout, stderr = StringIO(), StringIO()

    code = cli.main([
        "scan-disclosures", "dogfood/600036-cmb.json", "--through", "2026-09-02",
        "--packet-dir", str(tmp_path / "packets"), "--packet-limit", "1",
        "--attempt-history", str(history),
    ], stdout=stdout, stderr=stderr)

    assert code == 0 and stderr.getvalue() == ""
    assert "EXACT ATTEMPT REVALIDATION: 1 unchanged-not-reemitted" in stdout.getvalue()
    assert "ASSESSMENT PACKETS: 0 prepared" in stdout.getvalue()
    assert not (tmp_path / "packets").exists()


def test_corrupt_or_missing_attempt_history_fails_before_cninfo(monkeypatch, tmp_path) -> None:
    calls = 0

    def should_not_fetch(**_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("attempt history must be validated before CNINFO")

    monkeypatch.setattr(cninfo_http, "fetch_cninfo_disclosures", should_not_fetch)
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version":1}', encoding="utf-8")
    for history in (bad, tmp_path / "missing.json"):
        stdout, stderr = StringIO(), StringIO()
        code = cli.main([
            "scan-disclosures", "dogfood/600036-cmb.json", "--through", "2026-09-02",
            "--packet-dir", str(tmp_path / ("packets-" + history.stem)),
            "--attempt-history", str(history),
        ], stdout=stdout, stderr=stderr)
        assert code == 2
        assert stdout.getvalue() == ""
        assert "ERROR" in stderr.getvalue()
    assert calls == 0


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
