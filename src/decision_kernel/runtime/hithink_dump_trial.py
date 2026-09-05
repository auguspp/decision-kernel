from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import time
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlsplit

from decision_kernel.adapters.hithink import latest_completed_a_share_session
from decision_kernel.identity import canonical_hash, canonical_json
from . import hithink_http, hithink_index_http, hithink_sector_breadth_http
from .hithink_dump_inspection import (
    COLUMNS, MAX_FILE_BYTES, MAX_ROWS, _file_hash, inspect_daily_k_rows, parquet_rows,
)
from .sector_radar_audit import _check_request, _check_safe_json


SIGNING_PATH = "/api/dump/market-dumps/daily-k-10d/download-url"
PINS = {"requests": "2.34.2", "pyarrow": "25.0.1"}
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_REFERENCE_BYTES = 32 * 1024 * 1024
MAX_REFERENCE_REQUESTS = 32
MAX_DECODED_BYTES = 512 * 1024 * 1024
DOWNLOAD_SECONDS = 180
LIVE = "LIVE_HITHINK_ISOLATED_DUMP_TRIAL"
SYNTHETIC = "SYNTHETIC_TEST_ONLY"
AUTHORITY = {"human_attention_authority": "NONE", "research_authority": "NONE",
             "investment_authority": "NONE", "market_state_writes": 0, "events_created": 0}
# The documented signing service returns S3 presigned objects. No arbitrary host,
# local address, URL redirect, third-party provider or caller-provided URL is used.
S3_HOST = re.compile(r"(?:[a-z0-9][a-z0-9.-]*\.)?s3(?:[.-][a-z0-9-]+)?\.amazonaws\.com(?:\.cn)?")


class DumpTrialError(ValueError):
    def __init__(self, code: str, *, http_status: int | None = None):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clock(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise DumpTrialError("AWARE_CLOCK_REQUIRED")
    return value


def reader_runtime() -> dict:
    installed = {name: version(name) for name in PINS}
    if installed != PINS:
        raise DumpTrialError("INSTALL_EXACT_DUMP_STUDY_EXTRA")
    return {**installed, "python": platform.python_version()}


def _session():
    import requests
    session = requests.Session()
    session.trust_env = False  # no .netrc or environment proxy credentials
    return session


def _check_response(response) -> int | None:
    status = response.status_code
    if type(status) is not int or status != 200:
        raise DumpTrialError("HTTP_REJECTED", http_status=status if type(status) is int and 100 <= status <= 599 else None)
    if response.headers.get("Content-Encoding", "identity").lower() not in {"", "identity"}:
        raise DumpTrialError("UNEXPECTED_CONTENT_ENCODING")
    length = response.headers.get("Content-Length")
    if length is not None and (not re.fullmatch(r"[0-9]+", length) or int(length) <= 0):
        raise DumpTrialError("INVALID_CONTENT_LENGTH")
    return None if length is None else int(length)


def request_json(path: str, params: dict, *, api_key: str) -> dict:
    if path == SIGNING_PATH:
        if params:
            raise DumpTrialError("SIGNING_ENDPOINT_TAKES_NO_PARAMETERS")
    else:
        _check_request(path, params)
    # A fresh session for each request avoids retaining server cookies. The key is
    # sent ONLY to the fixed provider origin, never to the presigned object host.
    with _session() as session:
        with session.get(hithink_http.HITHINK_BASE_URL + path, params=params,
                         headers={"X-api-key": api_key, "Accept": "application/json", "Accept-Encoding": "identity"},
                         timeout=(10, 20), stream=True, allow_redirects=False) as response:
            length = _check_response(response)
            if length is not None and length > MAX_JSON_BYTES:
                raise DumpTrialError("JSON_BYTE_BUDGET_EXCEEDED")
            chunks, count = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                count += len(chunk)
                if count > MAX_JSON_BYTES:
                    raise DumpTrialError("JSON_BYTE_BUDGET_EXCEEDED")
                chunks.append(chunk)
            if length is not None and count != length:
                raise DumpTrialError("JSON_LENGTH_MISMATCH")
    payload = json.loads(b"".join(chunks).decode("utf-8"))
    if not isinstance(payload, dict):
        raise DumpTrialError("JSON_OBJECT_REQUIRED")
    return payload


def signing_identity(payload: dict, *, now: datetime) -> tuple[str, datetime, str]:
    if type(payload.get("code")) is not int or payload["code"] != 0:
        raise DumpTrialError("SIGNING_PROVIDER_REJECTED")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise DumpTrialError("SIGNING_DATA_REQUIRED")
    url, raw_expiry = data.get("presigned_url"), data.get("presigned_url_expires_at")
    if not isinstance(url, str) or len(url) > 8192 or any(ord(c) < 33 for c in url):
        raise DumpTrialError("INVALID_SIGNED_URL")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
            or parsed.port is not None or parsed.fragment or not parsed.query
            or not S3_HOST.fullmatch(parsed.hostname or "") or not parsed.path.startswith("/")):
        raise DumpTrialError("UNREVIEWED_SIGNED_OBJECT_DESTINATION")
    if not isinstance(raw_expiry, str):
        raise DumpTrialError("SIGNED_EXPIRY_REQUIRED")
    expiry = _clock(datetime.fromisoformat(raw_expiry.replace("Z", "+00:00")))
    if expiry <= _clock(now):
        raise DumpTrialError("SIGNED_URL_EXPIRED_NO_RESIGN")
    return url, expiry, parsed.hostname


def download_object(url: str, path: Path) -> dict:
    """Requests streams; PyArrow decodes. No home-made file/network engine."""
    if path.exists():
        raise DumpTrialError("DOWNLOAD_DESTINATION_EXISTS")
    temporary = path.with_suffix(".partial")
    start, count = time.monotonic(), 0
    digest = hashlib.sha256()
    try:
        with _session() as session:
            with session.get(url, headers={"Accept": "application/octet-stream", "Accept-Encoding": "identity"},
                             timeout=(10, 30), stream=True, allow_redirects=False) as response:
                length = _check_response(response)
                if length is not None and length > MAX_FILE_BYTES:
                    raise DumpTrialError("DOWNLOAD_BYTE_BUDGET_EXCEEDED")
                with temporary.open("xb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        count += len(chunk)
                        if count > MAX_FILE_BYTES or time.monotonic() - start > DOWNLOAD_SECONDS:
                            raise DumpTrialError("DOWNLOAD_RESOURCE_BUDGET_EXCEEDED")
                        digest.update(chunk)
                        output.write(chunk)
                if length is not None and count != length:
                    raise DumpTrialError("DOWNLOAD_LENGTH_MISMATCH")
        with temporary.open("rb") as source:
            if count < 12 or source.read(4) != b"PAR1":
                raise DumpTrialError("PARQUET_CONTAINER_REQUIRED")
            source.seek(-4, 2)
            if source.read(4) != b"PAR1":
                raise DumpTrialError("PARQUET_CONTAINER_REQUIRED")
        temporary.replace(path)
        return {"bytes": count, "sha256": digest.hexdigest(), "http_status": 200}
    finally:
        if temporary.exists():
            temporary.unlink()


def parquet_metadata(path: Path) -> dict:
    import pyarrow.parquet as pq
    _file_hash(path, MAX_FILE_BYTES)
    with path.open("rb") as stream:
        parquet = pq.ParquetFile(stream, thrift_string_size_limit=1024 * 1024,
                                thrift_container_size_limit=1024 * 1024, arrow_extensions_enabled=False)
        names = parquet.schema_arrow.names
        if set(names) != COLUMNS or len(names) != len(COLUMNS):
            raise DumpTrialError("PARQUET_SCHEMA_DISAGREES")
        rows = parquet.metadata.num_rows
        decoded = sum(parquet.metadata.row_group(i).total_byte_size for i in range(parquet.num_row_groups))
        if not 0 < rows <= MAX_ROWS or decoded > MAX_DECODED_BYTES:
            raise DumpTrialError("PARQUET_METADATA_RESOURCE_BUDGET_EXCEEDED")
        return {"metadata_row_count": rows, "row_groups": parquet.num_row_groups,
                "declared_uncompressed_bytes": decoded,
                "columns": [{"name": field.name, "type": str(field.type)} for field in parquet.schema_arrow]}


def run_trial(root: Path, *, api_key: str | None, provenance: str = LIVE,
              request=None, download=None, now=None) -> dict:
    if provenance not in {LIVE, SYNTHETIC} or ((request is not None or download is not None) != (provenance == SYNTHETIC)):
        raise DumpTrialError("INJECTED_TRANSPORT_REQUIRES_SYNTHETIC_PROVENANCE")
    if not api_key:
        raise DumpTrialError("HITHINK_CREDENTIAL_REQUIRED")
    runtime = reader_runtime()
    if root.exists() or any(p.is_symlink() for p in (root, *root.parents)) or "decision-state" in root.resolve().parts:
        raise DumpTrialError("NEW_ISOLATED_OUTPUT_DIRECTORY_REQUIRED")
    root.mkdir(parents=True)
    now = now or _now
    started = _clock(now())
    request = request or (lambda path, params: request_json(path, params, api_key=api_key))
    download = download or download_object
    report = {"schema_version": 1, "provenance": provenance, "started_at": started.isoformat(),
              "status": "FAILED_CLOSED", "stage": "SIGNING", "production_qualification": "NOT_ESTABLISHED",
              "reader_runtime": runtime, "signing_endpoint": SIGNING_PATH, "download_completed": False,
              "reference_requests": [], "inspection": None, **AUTHORITY}
    files = {}
    json_bytes = 0

    def save(name, value):
        nonlocal json_bytes
        _check_safe_json(value, api_key)
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2).encode("utf-8") + b"\n"
        if len(data) > MAX_JSON_BYTES or json_bytes + len(data) > MAX_REFERENCE_BYTES:
            raise DumpTrialError("REFERENCE_BYTE_BUDGET_EXCEEDED")
        with (root / name).open("xb") as target:
            target.write(data)
        files[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        json_bytes += len(data)

    def reference_request(path, params):
        _check_request(path, params)
        calls = report["reference_requests"]
        if len(calls) >= MAX_REFERENCE_REQUESTS:
            raise DumpTrialError("REFERENCE_REQUEST_BUDGET_EXCEEDED")
        record = {"path": path, "params": dict(params), "started_at": _clock(now()).isoformat(),
                  "response_file": None, "completed_at": None}
        calls.append(record)
        try:
            payload = request(path, params)
            name = f"reference-{len(calls):02d}.json"
            save(name, payload)
            record["response_file"] = name
            return payload
        finally:
            record["completed_at"] = _clock(now()).isoformat()

    try:
        signed = request(SIGNING_PATH, {})
        report["signing_provider_code"] = signed.get("code") if type(signed.get("code")) is int else None
        url, expiry, host = signing_identity(signed, now=now())
        report.update(signed_expires_at=expiry.isoformat(), download_host=host, stage="DOWNLOAD")
        report["download_started_at"] = _clock(now()).isoformat()
        receipt = download(url, root / "daily-k-10d.parquet")
        # Neither the signing response nor usable URL is ever saved or logged.
        del signed, url
        report["download_completed_at"] = _clock(now()).isoformat()
        path = root / "daily-k-10d.parquet"
        actual_hash = _file_hash(path, MAX_FILE_BYTES)
        if receipt["sha256"] != actual_hash or receipt["bytes"] != path.stat().st_size:
            raise DumpTrialError("DOWNLOAD_RECEIPT_DISAGREES")
        files[path.name] = {"sha256": actual_hash, "bytes": path.stat().st_size}
        report.update(download_completed=True, stage="PARQUET_METADATA")
        report["parquet"] = parquet_metadata(path)
        report["stage"] = "QUALIFIED_REFERENCE"
        observed = _clock(now())
        report["reference_observed_at"] = observed.isoformat()
        calendar = hithink_http.fetch_hithink_trading_calendar(observed_at=observed, api_key=api_key, request_json=reference_request)
        latest = latest_completed_a_share_session(calendar, observed_at=observed)
        sessions = tuple(day for day in calendar if day <= latest)[-10:]
        if len(sessions) != 10:
            raise DumpTrialError("TEN_COMPLETED_SESSIONS_REQUIRED")
        save("sessions.json", [day.isoformat() for day in sessions])
        benchmark = hithink_index_http.fetch_hithink_qualified_index_snapshot_batch(
            thscodes=("000300.SH",), benchmark_thscode="000300.SH", observed_at=observed,
            api_key=api_key, request_json=reference_request, trading_sessions=calendar)
        if benchmark.market_session != latest:
            raise DumpTrialError("REFERENCE_BENCHMARK_SESSION_DISAGREES")
        save("benchmark.json", json.loads(canonical_json(asdict(benchmark))))
        stock_snapshot = hithink_sector_breadth_http.fetch_hithink_all_market_snapshot(
            market_session=latest, api_key=api_key, request_json=reference_request)
        universe = [point.thscode for point in stock_snapshot.points]
        snapshot = json.loads(canonical_json({"market_session": latest, "points": [asdict(p) for p in stock_snapshot.points]}))
        save("universe.json", universe)
        save("snapshot.json", snapshot)
        report["reference_scope"] = "PROVIDER_PAGINATED_CURRENT_A_SHARE_SET_NOT_INDEPENDENT_EXCHANGE_CENSUS"
        report["reference_summary"] = {"market_session": latest.isoformat(), "total": stock_snapshot.declared_total,
                                       "pages": stock_snapshot.page_count, "unpriced": stock_snapshot.unpriced_rows}
        report["stage"] = "ROW_INSPECTION"
        inspection = inspect_daily_k_rows(parquet_rows(path), expected_sessions=sessions,
                                         current_universe=universe, reference_snapshot=snapshot)
        if _file_hash(path, MAX_FILE_BYTES) != actual_hash:
            raise DumpTrialError("DUMP_CHANGED_DURING_INSPECTION")
        if latest_completed_a_share_session(calendar, observed_at=now()) != latest:
            raise DumpTrialError("COMPLETED_SESSION_CHANGED_DURING_TRIAL")
        report["inspection"] = inspection
        report["status"] = inspection["inspection_status"]
        report["stage"] = "INSPECTED_NOT_ADOPTED"
    except Exception as exc:
        # No library exception text/traceback: it can contain a usable signed URL.
        report["error_type"] = type(exc).__name__
        report["error_code"] = exc.code if isinstance(exc, DumpTrialError) else "EXISTING_COMPONENT_OR_TRANSPORT_REJECTED"
        report["http_status"] = exc.http_status if isinstance(exc, DumpTrialError) else None
    report["completed_at"] = _clock(now()).isoformat()
    report["files"] = files
    report["report_hash"] = canonical_hash(report)
    save("report.json", report)
    summary = (f"## Stock dump trial — {report['status']}\n\n"
               f"Stage: {report['stage']}\n\nDownload retained: {report['download_completed']}\n\n"
               "Production qualification = NOT_ESTABLISHED. No stock panel or multi-day breadth is activated.\n\n"
               "A matching snapshot is same-provider consistency, not independent market authentication. "
               "Overlapping vintages, corporate actions, missing/suspended/delisted coverage remain unqualified.\n\n"
               "SHADOW OBSERVATION ONLY · HUMAN ATTENTION AUTHORITY = NONE · RESEARCH AUTHORITY = NONE · INVESTMENT AUTHORITY = NONE\n")
    (root / "summary.md").write_text(summary, encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="One isolated HiThink recent-stock-dump trial; no market-state publication.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_trial(args.output, api_key=os.environ.get(hithink_http.HITHINK_API_KEY_ENV))
    except Exception as exc:
        parser.exit(2, f"Dump trial could not seal a report: {type(exc).__name__}\n")
    print(result["status"] + "; production qualification = NOT_ESTABLISHED")
    return 0 if result["status"] == "CHECKED_FIELDS_MATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
