"""Three fixed GETs against CNINFO's official announcement-download endpoint.

Prior art uses /new/announcement/download?bulletinId=<id>&announceTime=<date>
instead of direct static-CDN acquisition. This probe changes only that official
request surface. It never follows redirects, retries, authenticates, or runs Research.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlsplit

import requests
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError, _check_response, _session

ENDPOINT = "https://www.cninfo.com.cn/new/announcement/download"
SAMPLES = (
    ("000920.SZ", "1225486756", "2026-08-21", None),
    ("603268.SH", "1225497616", "2026-08-25", None),
    ("603353.SH", "1225530965", "2026-08-29",
     "cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa"),
)
HEADERS = {
    "Accept": "application/pdf, application/octet-stream, */*",
    "Accept-Encoding": "identity",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://www.cninfo.com.cn/",
}
MAX_PDF_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 48 * 1024 * 1024
MAX_SECONDS = 180
SEMANTICS = "OFFICIAL_ANNOUNCEMENT_DOWNLOAD_ENDPOINT_PROBE_NOT_PRODUCTION_RECOVERY"
AUTHORITY = {"production_qualification": "NOT_ESTABLISHED", "research_authority": "NONE",
             "human_attention_authority": "NONE", "investment_authority": "NONE",
             "market_state_writes": 0, "events_created": 0}


def _raw(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _clock():
    return datetime.now(timezone.utc).isoformat()


def _save(path, obj):
    mode = "wb" if path.name == "journal.json" else "xb"
    with path.open(mode) as stream:
        stream.write(_raw(obj))


def native_identity(environ=None):
    env = os.environ if environ is None else environ
    sha = env.get("GITHUB_SHA", "")
    if (env.get("GITHUB_REPOSITORY") != "auguspp/decision-kernel"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"
            or not re.fullmatch(r"[0-9a-f]{40}", sha)
            or env.get("EXPECTED_CODE_SHA") != sha
            or not re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", ""))):
        raise ValueError("EXACT_NATIVE_MAIN_FIRST_ATTEMPT_REQUIRED")
    if version("requests") != "2.34.2":
        raise ValueError("EXISTING_DUMP_STUDY_REQUESTS_PIN_REQUIRED")
    return {key: env[key] for key in (
        "GITHUB_REPOSITORY", "GITHUB_REF", "GITHUB_SHA", "GITHUB_EVENT_NAME",
        "GITHUB_RUN_ATTEMPT", "GITHUB_RUN_ID")}


def _redirect_diagnostic(value, *, announcement_id, announce_date):
    result = {"present": False, "https": None, "official_static_host": None,
              "expected_finalpage_path": None}
    if not isinstance(value, str) or not value or len(value) > 2048:
        return result
    try:
        part = urlsplit(value)
    except ValueError:
        return result
    result.update(
        present=True,
        https=part.scheme.lower() == "https",
        official_static_host=(part.hostname or "").lower() == "static.cninfo.com.cn",
        expected_finalpage_path=part.path == f"/finalpage/{announce_date}/{announcement_id}.PDF",
    )
    return result


def run_probe(output: Path, identity: dict, *, session_factory=_session, monotonic=time.monotonic):
    output.mkdir(parents=True, exist_ok=False)
    plan = {
        "semantics": SEMANTICS,
        "created_at": _clock(),
        "identity": identity,
        "endpoint": ENDPOINT,
        "samples": SAMPLES,
        "headers": HEADERS,
        "max_requests": 3,
        "max_pdf_bytes": MAX_PDF_BYTES,
        "max_total_bytes": MAX_TOTAL_BYTES,
        "max_elapsed_seconds": MAX_SECONDS,
        "retry": False,
        "redirect": False,
        "shared_cookies": False,
        "environment_proxy_credentials": False,
        "prior_art": [
            "jingmian/cninfo_spider: /new/announcement/download bulletinId/announceTime",
            "Aliyun RPA ChromeTab download_by_url CNINFO announcement download example",
        ],
        "runtime": {"python": platform.python_version(), "requests": version("requests")},
        "source_artifacts": {
            "10543485410": "ff5bf465ff2db0d3ecfee8c9bd3f87a22a1e7a56d21ec80bc8480b482d732866",
            "10320565453": "25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c",
            "10580793645": "f942ad6e9dded31ef8f97539ac51887926b99291ddd8bca51ca2111aee545cd5",
        },
        **AUTHORITY,
    }
    _save(output / "plan.json", plan)
    records, total, stop = [], 0, None
    started = monotonic()
    for issuer, announcement_id, announce_date, expected_sha in SAMPLES:
        row = {
            "issuer": issuer,
            "announcement_id": announcement_id,
            "announce_date": announce_date,
            "expected_pdf_sha256": expected_sha,
            "started_at": _clock(),
            "status": "NOT_ATTEMPTED",
            "http_status": None,
            "received_bytes": 0,
            "pdf_file": None,
            "pdf_sha256": None,
            "reason": None,
            "redirect": {"present": False, "https": None, "official_static_host": None,
                         "expected_finalpage_path": None},
        }
        records.append(row)
        if monotonic() - started >= MAX_SECONDS:
            stop = "ELAPSED_BUDGET"
        if stop:
            row.update(reason=stop, finished_at=_clock())
            _save(output / "journal.json", records)
            continue
        row["status"] = "IN_PROGRESS"
        _save(output / "journal.json", records)
        params = {"bulletinId": announcement_id, "announceTime": announce_date}
        try:
            with session_factory() as session:
                with session.get(ENDPOINT, params=params, headers=dict(HEADERS),
                                 timeout=(10, 45), stream=True, allow_redirects=False) as response:
                    status = response.status_code
                    row["http_status"] = status if type(status) is int and 100 <= status <= 599 else None
                    row["redirect"] = _redirect_diagnostic(
                        response.headers.get("Location"),
                        announcement_id=announcement_id,
                        announce_date=announce_date,
                    )
                    length = _check_response(response)
                    if length is not None and length > MAX_PDF_BYTES:
                        raise DumpTrialError("PDF_BYTE_LIMIT")
                    if length is not None and total + length > MAX_TOTAL_BYTES:
                        raise DumpTrialError("TOTAL_BYTE_LIMIT")
                    chunks = []
                    for chunk in response.iter_content(chunk_size=65536):
                        row["received_bytes"] += len(chunk)
                        total += len(chunk)
                        if row["received_bytes"] > MAX_PDF_BYTES:
                            raise DumpTrialError("PDF_BYTE_LIMIT")
                        if total > MAX_TOTAL_BYTES:
                            raise DumpTrialError("TOTAL_BYTE_LIMIT")
                        if monotonic() - started >= MAX_SECONDS:
                            raise DumpTrialError("ELAPSED_BUDGET")
                        chunks.append(chunk)
                    if length is not None and length != row["received_bytes"]:
                        raise DumpTrialError("RESPONSE_LENGTH_MISMATCH")
                    body = b"".join(chunks)
                    if not body.startswith(b"%PDF-"):
                        raise DumpTrialError("PDF_MAGIC_MISSING")
                    digest = _sha(body)
                    filename = f"{announcement_id}-announcement-download.pdf"
                    with (output / filename).open("xb") as stream:
                        stream.write(body)
                    row.update(status="PDF_BYTES_RETAINED_NOT_QUALIFIED", pdf_file=filename,
                               pdf_sha256=digest)
                    if expected_sha is not None and expected_sha != digest:
                        row.update(status="CONTROL_HASH_MISMATCH", reason="CONTROL_HASH_MISMATCH")
                        stop = "CONTROL_HASH_MISMATCH"
        except DumpTrialError as exc:
            row.update(status="REJECTED", reason=exc.code)
            if row["http_status"] == 429:
                stop = "HTTP_429_STOP"
            elif exc.code in {"TOTAL_BYTE_LIMIT", "ELAPSED_BUDGET"}:
                stop = exc.code
        except requests.RequestException as exc:
            row.update(status="TRANSPORT_FAILED", reason=(
                "REQUEST_TIMEOUT" if isinstance(exc, requests.Timeout) else
                "CONNECTION_FAILED" if isinstance(exc, requests.ConnectionError) else "REQUEST_FAILED"))
            stop = row["reason"]
        row["finished_at"] = _clock()
        _save(output / "journal.json", records)
    result = {
        "semantics": SEMANTICS,
        "plan_sha256": _sha((output / "plan.json").read_bytes()),
        "finished_at": _clock(),
        "records": records,
        "received_bytes": total,
        "attempted_requests": sum(r["status"] != "NOT_ATTEMPTED" for r in records),
        "stop_reason": stop,
        "remote_failure_cause": "UNKNOWN",
        "historical_http_status": "UNKNOWN",
        **AUTHORITY,
    }
    result["result_sha256"] = _sha(_raw(result))
    _save(output / "result.json", result)
    lines = [
        "# Official CNINFO announcement-download endpoint probe",
        "",
        "Not production recovery or Research.",
        "",
        "| Announcement | HTTP | Result | Redirect to expected static path |",
        "|---|---:|---|---|",
    ]
    for row in records:
        lines.append(
            f"| {row['announcement_id']} | {row['http_status']} | {row['status']} | "
            f"{row['redirect']['official_static_host'] and row['redirect']['expected_finalpage_path']} |"
        )
    with (output / "summary.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    return result


def verify(output: Path):
    result = json.loads((output / "result.json").read_bytes())
    digest = result.pop("result_sha256")
    if digest != _sha(_raw(result)) or result["plan_sha256"] != _sha((output / "plan.json").read_bytes()):
        raise ValueError("RESULT_OR_PLAN_HASH_MISMATCH")
    if result["semantics"] != SEMANTICS or any(result.get(k) != v for k, v in AUTHORITY.items()):
        raise ValueError("SEMANTICS_OR_AUTHORITY_CHANGED")
    if [r["announcement_id"] for r in result["records"]] != [s[1] for s in SAMPLES]:
        raise ValueError("FIXED_SAMPLE_MATRIX_CHANGED")
    if not 0 <= result["attempted_requests"] <= 3 or any(r["status"] == "IN_PROGRESS" for r in result["records"]):
        raise ValueError("INCOMPLETE_OR_OVERSIZED_ATTEMPT")
    for row in result["records"]:
        redirect = row["redirect"]
        if set(redirect) != {"present", "https", "official_static_host", "expected_finalpage_path"}:
            raise ValueError("UNBOUNDED_REDIRECT_DIAGNOSTIC")
        if row["pdf_file"] is not None:
            filename = f"{row['announcement_id']}-announcement-download.pdf"
            path = output / filename
            if row["pdf_file"] != filename or path.is_symlink():
                raise ValueError("UNSAFE_OUTPUT_PATH")
            body = path.read_bytes()
            if not body.startswith(b"%PDF-") or len(body) != row["received_bytes"] or _sha(body) != row["pdf_sha256"]:
                raise ValueError("RETAINED_PDF_IDENTITY_MISMATCH")
    return "RETAINED_DOWNLOAD_ENDPOINT_PROBE_INTEGRITY_CHECKED_NOT_SOURCE_TRUTH"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if not args.verify_only:
        run_probe(args.output, native_identity())
    print(verify(args.output))


if __name__ == "__main__":
    main()
