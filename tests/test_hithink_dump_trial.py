from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import hithink_dump_trial as trial
from decision_kernel.runtime.hithink_dump_inspection import parquet_rows, inspect_daily_k_rows


TZ = ZoneInfo("Asia/Shanghai")
NOW = datetime(2026, 9, 5, 8, tzinfo=timezone.utc)
SESSIONS = tuple(date(2026, 8, 24) + timedelta(days=i) for i in range(12)
                 if (date(2026, 8, 24) + timedelta(days=i)).weekday() < 5)
URL = "https://example.s3.ap-southeast-1.amazonaws.com/dump.parquet?X-Amz-Signature=never-save-this"
SECRET = "fixture-credential-never-save-this"
CODES = ("600001.SH", "000001.SZ")


def ms(day, hour=0):
    return int(datetime.combine(day, time(hour), TZ).timestamp() * 1000)


def signed(url=URL, expires="2026-09-05T08:05:00Z"):
    return {"code": 0, "data": {"presigned_url": url, "presigned_url_expires_at": expires}}


def rows():
    return [{"thscode": code, "currency": "CNY", "interval": "1d", "adjusted": "none",
             "date_ms": ms(day), "open_price": 100.0 + i, "high_price": 101.0 + i,
             "low_price": 99.0 + i, "close_price": 100.0 + i, "volume": 100.0, "turnover": 1000.0}
            for i, day in enumerate(SESSIONS) for code in CODES]


@pytest.fixture
def parquet(tmp_path):
    path = tmp_path / "fixture.parquet"
    pq.write_table(pa.Table.from_pylist(rows()), path)
    return path


def responses():
    latest = SESSIONS[-1]
    benchmark_row = {"thscode": "000300.SH", "ticker": "1B0300", "last_price": "4548.05", "prev_price": "4530",
                     "price_change": "18.05", "price_change_ratio_pct": "0.3984547461",
                     "open_price": "4530", "high_price": "4550", "low_price": "4520", "volume": "100", "turnover": "1000"}
    return {
        trial.SIGNING_PATH: signed(),
        trial.hithink_http.HITHINK_CALENDAR_PATH: {"code": 0, "data": {"item": [{"date": d.strftime("%Y%m%d")} for d in SESSIONS]}},
        trial.hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH: {"code": 0, "data": {"timestamp": ms(latest, 16), "total": 1, "item": [benchmark_row]}},
        trial.hithink_index_http.HITHINK_INDEX_HISTORY_PATH: {"code": 0, "data": {
            "thscode": "000300.SH", "interval": "1d", "adjust": None, "timestamp": ms(latest),
            "item": [{"date_ms": ms(SESSIONS[-2]), "close_price": "4530", "volume": "100", "turnover": "1000"},
                     {"date_ms": ms(latest), "close_price": "4548.05", "volume": "100", "turnover": "1000"}]}},
        trial.hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH: {"code": 0, "data": {
            "timestamp": ms(latest, 16), "total": 2, "item": [
                {"thscode": code, "ticker": code[:6], "last_price": "109", "prev_price": "108", "turnover": "1000"} for code in CODES]}},
    }


def execute(root, parquet, payloads=None):
    payloads = responses() if payloads is None else payloads
    calls = []
    def request(path, params):
        calls.append(path)
        item = payloads[path]
        if isinstance(item, Exception):
            raise item
        return copy.deepcopy(item)
    def download(url, path):
        assert url == URL
        calls.append("SIGNED_OBJECT_WITHOUT_API_KEY")
        data = parquet.read_bytes()
        path.write_bytes(data)
        return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "http_status": 200}
    result = trial.run_trial(root, api_key=SECRET, provenance=trial.SYNTHETIC,
                             request=request, download=download, now=lambda: NOW)
    return result, calls


def test_full_trial_uses_existing_qualifiers_and_real_parquet_reader(parquet, tmp_path):
    root = tmp_path / "study"
    result, calls = execute(root, parquet)
    assert result["status"] == "CHECKED_FIELDS_MATCH"
    assert result["provenance"] == trial.SYNTHETIC
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    assert result["inspection"]["row_count"] == 20
    assert result["inspection"]["checked_priced_latest_identities"] == 2
    assert result["market_state_writes"] == result["events_created"] == 0
    assert result["human_attention_authority"] == result["research_authority"] == result["investment_authority"] == "NONE"
    assert calls == [trial.SIGNING_PATH, "SIGNED_OBJECT_WITHOUT_API_KEY", trial.hithink_http.HITHINK_CALENDAR_PATH,
                     trial.hithink_index_http.HITHINK_INDEX_SNAPSHOT_PATH, trial.hithink_index_http.HITHINK_INDEX_HISTORY_PATH,
                     trial.hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH]
    assert (root / "daily-k-10d.parquet").read_bytes() == parquet.read_bytes()
    inspection = inspect_daily_k_rows(parquet_rows(root / "daily-k-10d.parquet"), expected_sessions=SESSIONS,
        current_universe=json.loads((root / "universe.json").read_text()),
        reference_snapshot=json.loads((root / "snapshot.json").read_text()))
    assert inspection == result["inspection"]
    saved = json.loads((root / "report.json").read_text())
    assert saved == result
    claimed = saved.pop("report_hash")
    assert canonical_hash(saved) == claimed
    for name, info in saved["files"].items():
        content = (root / name).read_bytes()
        assert len(content) == info["bytes"] and hashlib.sha256(content).hexdigest() == info["sha256"]
    for path in root.iterdir():
        assert SECRET.encode() not in path.read_bytes()
        assert b"never-save-this" not in path.read_bytes()
        assert b"presigned_url" not in path.read_bytes()


@pytest.mark.parametrize("url", ["http://example.s3.amazonaws.com/f?x=1", "https://evil.invalid/f?x=1",
    "https://127.0.0.1/f?x=1", "https://example.s3.amazonaws.com@evil.invalid/f?x=1",
    "https://example.s3.amazonaws.com.evil.invalid/f?x=1", "https://example.s3.amazonaws.com:443/f?x=1",
    URL + "#x", URL.replace("?", "\n?")])
def test_unreviewed_signed_destinations_rejected(url):
    with pytest.raises(trial.DumpTrialError):
        trial.signing_identity(signed(url), now=NOW)


@pytest.mark.parametrize("expires", ["2026-09-05T08:00:00Z", "2026-09-05T07:59:59Z", "2026-09-05T08:05:00", "invalid"])
def test_expired_or_ambiguous_link_never_resigned(expires):
    with pytest.raises(ValueError):
        trial.signing_identity(signed(expires=expires), now=NOW)


def test_download_is_retained_but_reference_rejection_is_not_success(parquet, tmp_path):
    payloads = responses()
    payloads[trial.hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH]["data"]["timestamp"] = ms(date(2026, 9, 5), 16)
    result, calls = execute(tmp_path / "study", parquet, payloads)
    assert result["status"] == "FAILED_CLOSED"
    assert result["stage"] == "QUALIFIED_REFERENCE"
    assert result["download_completed"] and result["inspection"] is None
    assert result["reference_requests"][-1]["response_file"] is not None
    assert len(calls) == 6
    assert not (tmp_path / "decision-state").exists()


def test_field_differences_remain_non_success_without_price_tolerance(parquet, tmp_path):
    payloads = responses()
    payloads[trial.hithink_sector_breadth_http.HITHINK_A_SHARE_SNAPSHOT_PATH]["data"]["item"][0]["last_price"] = "109.00001"
    result, _ = execute(tmp_path / "study", parquet, payloads)
    assert result["status"] == "DIFFERENCES_REQUIRE_REVIEW"
    assert result["inspection"]["reference_mismatches"][0]["field"] == "close_price"


def test_signing_failure_does_not_download_or_store_signed_material(parquet, tmp_path):
    payloads = responses()
    payloads[trial.SIGNING_PATH] = {"code": 2004, "message": SECRET, "data": None}
    result, calls = execute(tmp_path / "study", parquet, payloads)
    assert calls == [trial.SIGNING_PATH]
    assert result["signing_provider_code"] == 2004
    assert result["status"] == "FAILED_CLOSED" and not result["download_completed"]
    assert not (tmp_path / "study" / "daily-k-10d.parquet").exists()
    assert SECRET not in (tmp_path / "study" / "report.json").read_text()


def test_bad_parquet_columns_rejected_before_reference_network(tmp_path):
    path = tmp_path / "bad.parquet"
    pq.write_table(pa.table({"arbitrary": [1]}), path)
    result, calls = execute(tmp_path / "study", path)
    assert len(calls) == 2 and result["status"] == "FAILED_CLOSED"
    assert result["error_code"] == "PARQUET_SCHEMA_DISAGREES"


def test_output_cannot_replace_previous_study_or_enter_market_state(parquet, tmp_path):
    root = tmp_path / "study"
    execute(root, parquet)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    with pytest.raises(trial.DumpTrialError):
        execute(root, parquet)
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
    with pytest.raises(trial.DumpTrialError):
        execute(tmp_path / "decision-state" / "trial", parquet)


def test_injected_live_transport_and_missing_key_fail_before_requests(tmp_path):
    with pytest.raises(trial.DumpTrialError):
        trial.run_trial(tmp_path / "live", api_key=SECRET, request=lambda *a: pytest.fail("no network"))
    with pytest.raises(trial.DumpTrialError):
        trial.run_trial(tmp_path / "missing", api_key=None)
    assert not (tmp_path / "live").exists() and not (tmp_path / "missing").exists()


def test_mature_dependencies_are_optional_and_parquet_is_physically_decoded(parquet):
    project = tomllib.loads(Path("pyproject.toml").read_text())["project"]
    assert project["optional-dependencies"]["dump-study"] == ["requests==2.34.2", "pyarrow==25.0.1"]
    assert not any(name.startswith(("pyarrow", "requests")) for name in project["dependencies"])
    assert len(list(parquet_rows(parquet))) == 20
    assert trial.parquet_metadata(parquet)["metadata_row_count"] == 20


class Response:
    def __init__(self, content, status=200, headers=None):
        self.content = content
        self.status_code = status
        self.headers = headers or {"Content-Length": str(len(content))}
        self.closed = False
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.closed = True
    def iter_content(self, chunk_size):
        assert self.status_code == 200, "HTTP error body must never be read"
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start:start + chunk_size]


class Session:
    def __init__(self, response, calls):
        self.response, self.calls = response, calls
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_streamed_signed_download_sends_no_provider_credentials(parquet, tmp_path, monkeypatch):
    response, calls = Response(parquet.read_bytes()), []
    monkeypatch.setattr(trial, "_session", lambda: Session(response, calls))
    path = tmp_path / "download.parquet"
    receipt = trial.download_object(URL, path)
    assert path.read_bytes() == parquet.read_bytes()
    assert receipt["sha256"] == hashlib.sha256(parquet.read_bytes()).hexdigest()
    assert response.closed and len(calls) == 1
    assert calls[0][1]["allow_redirects"] is False and calls[0][1]["stream"] is True
    assert "X-api-key" not in calls[0][1]["headers"]


@pytest.mark.parametrize("status", [301, 403, 404, 429, 500])
def test_http_failure_never_reads_body_retries_or_leaves_partial_file(status, tmp_path, monkeypatch):
    response, calls = Response(b"sensitive-error", status=status), []
    monkeypatch.setattr(trial, "_session", lambda: Session(response, calls))
    with pytest.raises(trial.DumpTrialError) as failure:
        trial.download_object(URL, tmp_path / "data.parquet")
    assert failure.value.http_status == status
    assert response.closed and len(calls) == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("headers", [{"Content-Length": "999999999"}, {"Content-Encoding": "gzip"}, {"Content-Length": "-1"}])
def test_file_limits_and_encoding_are_not_silently_bypassed(headers, tmp_path, monkeypatch):
    response, calls = Response(b"PAR1abcdefghPAR1", headers=headers), []
    monkeypatch.setattr(trial, "_session", lambda: Session(response, calls))
    with pytest.raises(trial.DumpTrialError):
        trial.download_object(URL, tmp_path / "data.parquet")
    assert response.closed and list(tmp_path.iterdir()) == []
