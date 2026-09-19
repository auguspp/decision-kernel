"""Bounded official-exchange discovery + PDF acquisition probe.

After two CNINFO acquisition surfaces were rejected on the GitHub runner, this
probe tests the primary exchange disclosure surfaces without changing production:
SZSE annList -> disc.static.szse.cn, and SSE queryCompanyBulletin -> static.sse.com.cn.

Four fixed identities only: one target + one retained control per exchange.
Data != Evidence; a successful official PDF acquisition is source capability, not truth.
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
from html import unescape
from importlib.metadata import version
from pathlib import Path

import requests
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError, _check_response, _session

SZSE_QUERY = "https://www.szse.cn/api/disc/announcement/annList"
SZSE_PDF_BASE = "https://disc.static.szse.cn/download"
SSE_QUERY = "https://query.sse.com.cn/security/stock/queryCompanyBulletin.do"
SSE_PDF_BASE = "https://static.sse.com.cn"

SAMPLES = (
    {
        "exchange": "SZSE", "code": "000920", "short_name": "沃顿科技",
        "cninfo_announcement_id": "1225486756", "date": "2026-08-21",
        "title": "关于2026年半年度利润分配预案的公告", "retained_cninfo_sha256": None,
    },
    {
        "exchange": "SZSE", "code": "300711", "short_name": "广哈通信",
        "cninfo_announcement_id": "1225486858", "date": "2026-08-21",
        "title": "中信证券股份有限公司关于广州广哈通信股份有限公司使用募集资金增资子公司以实施募投项目的核查意见",
        "retained_cninfo_sha256": "cc65030bd9e676f5289d2bc2649eb7ff23b26a5b406b08b88cd20392d45df342",
    },
    {
        "exchange": "SSE", "code": "603268", "short_name": "松发股份",
        "cninfo_announcement_id": "1225497616", "date": "2026-08-25",
        "title": "西南证券股份有限公司关于广东松发陶瓷股份有限公司使用部分暂时闲置募集资金进行现金管理及以协定存款方式存放募集资金的核查意见",
        "retained_cninfo_sha256": None,
    },
    {
        "exchange": "SSE", "code": "603353", "short_name": "和顺石油",
        "cninfo_announcement_id": "1225530965", "date": "2026-08-29",
        "title": "东方财富证券股份有限公司关于湖南和顺石油股份有限公司2026年股票期权激励计划（草案）之独立财务顾问报告",
        "retained_cninfo_sha256": "cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa",
    },
)

SZSE_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "identity",
    "Content-Type": "application/json",
    "Origin": "https://www.szse.cn",
    "Referer": "https://www.szse.cn/disclosure/listed/notice/index.html",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "X-Request-Type": "ajax",
    "X-Requested-With": "XMLHttpRequest",
}
SSE_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "identity",
    "Referer": "https://www.sse.com.cn/disclosure/listedinfo/announcement/",
    "User-Agent": SZSE_HEADERS["User-Agent"],
}
PDF_HEADERS = {
    "Accept": "application/pdf, application/octet-stream, */*",
    "Accept-Encoding": "identity",
    "User-Agent": SZSE_HEADERS["User-Agent"],
}
MAX_JSON_BYTES = 1024 * 1024
MAX_PDF_BYTES = 16 * 1024 * 1024
MAX_TOTAL_PDF_BYTES = 64 * 1024 * 1024
MAX_REQUESTS = 8
MAX_SECONDS = 240
SEMANTICS = "EXCHANGE_OFFICIAL_PDF_SOURCE_PROBE_NOT_PRODUCTION_RECOVERY"
AUTHORITY = {
    "production_qualification": "NOT_ESTABLISHED",
    "research_authority": "NONE",
    "human_attention_authority": "NONE",
    "investment_authority": "NONE",
    "market_state_writes": 0,
    "events_created": 0,
}


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
    if (
        env.get("GITHUB_REPOSITORY") != "auguspp/decision-kernel"
        or env.get("GITHUB_REF") != "refs/heads/main"
        or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or env.get("GITHUB_RUN_ATTEMPT") != "1"
        or not re.fullmatch(r"[0-9a-f]{40}", sha)
        or env.get("EXPECTED_CODE_SHA") != sha
        or not re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", ""))
    ):
        raise ValueError("EXACT_NATIVE_MAIN_FIRST_ATTEMPT_REQUIRED")
    if version("requests") != "2.34.2":
        raise ValueError("EXISTING_DUMP_STUDY_REQUESTS_PIN_REQUIRED")
    return {key: env[key] for key in (
        "GITHUB_REPOSITORY", "GITHUB_REF", "GITHUB_SHA", "GITHUB_EVENT_NAME",
        "GITHUB_RUN_ATTEMPT", "GITHUB_RUN_ID",
    )}


def _normalize_title(value, short_name):
    if not isinstance(value, str):
        return ""
    value = re.sub(r"</?em>", "", unescape(value), flags=re.I)
    value = re.sub(r"\s+", "", value).strip()
    for prefix in (f"{short_name}：", f"{short_name}:"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    return value


def _bounded_response_bytes(response, *, max_bytes):
    length = _check_response(response)
    if length is not None and length > max_bytes:
        raise DumpTrialError("RESPONSE_BYTE_LIMIT")
    chunks, count = [], 0
    for chunk in response.iter_content(chunk_size=65536):
        count += len(chunk)
        if count > max_bytes:
            raise DumpTrialError("RESPONSE_BYTE_LIMIT")
        chunks.append(chunk)
    if length is not None and count != length:
        raise DumpTrialError("RESPONSE_LENGTH_MISMATCH")
    return b"".join(chunks)


def _safe_szse_attach_path(value):
    return (
        isinstance(value, str)
        and value.startswith("/disc/")
        and value.upper().endswith(".PDF")
        and "?" not in value
        and "#" not in value
        and "%" not in value
        and "\\" not in value
        and not {".", ".."}.intersection(value.split("/"))
    )


def _safe_sse_url_path(value):
    return (
        isinstance(value, str)
        and value.startswith("/disclosure/listedinfo/announcement/")
        and value.lower().endswith(".pdf")
        and "?" not in value
        and "#" not in value
        and "%" not in value
        and "\\" not in value
        and not {".", ".."}.intersection(value.split("/"))
    )


def _szse_payload(sample):
    return {
        "seDate": [sample["date"], sample["date"]],
        "stock": [sample["code"]],
        "channelCode": ["listedNotice_disc"],
        "pageSize": 50,
        "pageNum": 1,
    }


def _sse_params(sample):
    return {
        "isPagination": "false",
        "productId": sample["code"],
        "keyWord": "",
        "securityType": "0101",
        "reportType2": "LSGG",
        "reportType": "ALL",
        "beginDate": sample["date"],
        "endDate": sample["date"],
    }


def _match_szse(payload, sample):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("SZSE_ANNOUNCEMENT_RESPONSE_SHAPE")
    if len(payload["data"]) > 100:
        raise ValueError("SZSE_RESPONSE_CAPACITY")
    matches = []
    for row in payload["data"]:
        if not isinstance(row, dict):
            continue
        codes = row.get("secCode")
        if isinstance(codes, str):
            codes = [codes]
        ann_id = row.get("annId")
        ann_id = str(ann_id) if isinstance(ann_id, (int, str)) and not isinstance(ann_id, bool) else ""
        publish = row.get("publishTime")
        if (
            isinstance(codes, list)
            and sample["code"] in codes
            and ann_id == sample["cninfo_announcement_id"]
            and isinstance(publish, str)
            and publish[:10] == sample["date"]
            and _normalize_title(row.get("title"), sample["short_name"])
                == _normalize_title(sample["title"], sample["short_name"])
        ):
            matches.append(row)
    if len(matches) != 1:
        return None, "NO_EXACT_MATCH" if not matches else "AMBIGUOUS_EXACT_MATCH"
    row = matches[0]
    if not _safe_szse_attach_path(row.get("attachPath")):
        return None, "UNSAFE_ATTACH_PATH"
    return {
        "exchange_announcement_id": str(row.get("annId")),
        "title": row.get("title"),
        "publish_time": row.get("publishTime"),
        "attach_path": row.get("attachPath"),
        "attach_format": row.get("attachFormat"),
        "attach_size_kb": row.get("attachSize"),
        "official_pdf_url": SZSE_PDF_BASE + row["attachPath"],
    }, None


def _sse_rows(payload):
    if not isinstance(payload, dict):
        raise ValueError("SSE_ANNOUNCEMENT_RESPONSE_SHAPE")
    if isinstance(payload.get("result"), list):
        return payload["result"]
    page = payload.get("pageHelp")
    if isinstance(page, dict) and isinstance(page.get("data"), list):
        return page["data"]
    raise ValueError("SSE_ANNOUNCEMENT_ROWS_MISSING")


def _match_sse(payload, sample):
    rows = _sse_rows(payload)
    if len(rows) > 100:
        raise ValueError("SSE_RESPONSE_CAPACITY")
    matches = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = row.get("SECURITY_CODE") or row.get("SECURITY_CODE_A")
        date = row.get("SSEDATE") or row.get("SSE_DATE")
        title = row.get("TITLE")
        if (
            str(code or "") == sample["code"]
            and isinstance(date, str)
            and date[:10] == sample["date"]
            and _normalize_title(title, sample["short_name"])
                == _normalize_title(sample["title"], sample["short_name"])
        ):
            matches.append(row)
    if len(matches) != 1:
        return None, "NO_EXACT_MATCH" if not matches else "AMBIGUOUS_EXACT_MATCH"
    row = matches[0]
    path = row.get("URL")
    if not _safe_sse_url_path(path):
        return None, "UNSAFE_URL_PATH"
    return {
        "exchange_announcement_id": None,
        "title": row.get("TITLE"),
        "publish_time": row.get("SSEDATE") or row.get("SSE_DATE"),
        "attach_path": path,
        "attach_format": "PDF",
        "attach_size_kb": None,
        "official_pdf_url": SSE_PDF_BASE + path,
    }, None


def _query_one(session, sample, output, *, request_counter):
    if sample["exchange"] == "SZSE":
        payload = _szse_payload(sample)
        response = session.post(
            SZSE_QUERY,
            data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            headers=dict(SZSE_HEADERS),
            timeout=(10, 30),
            stream=True,
            allow_redirects=False,
        )
        request_counter[0] += 1
        with response:
            status = response.status_code
            raw = _bounded_response_bytes(response, max_bytes=MAX_JSON_BYTES)
        raw_name = f"{sample['code']}-{sample['cninfo_announcement_id']}-szse-query.json"
        with (output / raw_name).open("xb") as stream:
            stream.write(raw)
        data = json.loads(raw.decode("utf-8"))
        match, reason = _match_szse(data, sample)
        return status, raw_name, _sha(raw), len(raw), match, reason
    params = _sse_params(sample)
    response = session.get(
        SSE_QUERY,
        params=params,
        headers=dict(SSE_HEADERS),
        timeout=(10, 30),
        stream=True,
        allow_redirects=False,
    )
    request_counter[0] += 1
    with response:
        status = response.status_code
        raw = _bounded_response_bytes(response, max_bytes=MAX_JSON_BYTES)
    raw_name = f"{sample['code']}-{sample['cninfo_announcement_id']}-sse-query.json"
    with (output / raw_name).open("xb") as stream:
        stream.write(raw)
    data = json.loads(raw.decode("utf-8"))
    match, reason = _match_sse(data, sample)
    return status, raw_name, _sha(raw), len(raw), match, reason


def _download_one(session, sample, match, output, *, request_counter, total_pdf_bytes):
    headers = {
        **PDF_HEADERS,
        "Referer": (
            "https://www.szse.cn/disclosure/listed/notice/index.html"
            if sample["exchange"] == "SZSE"
            else "https://www.sse.com.cn/disclosure/listedinfo/announcement/"
        ),
    }
    response = session.get(
        match["official_pdf_url"],
        headers=headers,
        timeout=(10, 45),
        stream=True,
        allow_redirects=False,
    )
    request_counter[0] += 1
    with response:
        status = response.status_code
        length = _check_response(response)
        if length is not None and length > MAX_PDF_BYTES:
            raise DumpTrialError("PDF_BYTE_LIMIT")
        if length is not None and total_pdf_bytes[0] + length > MAX_TOTAL_PDF_BYTES:
            raise DumpTrialError("TOTAL_PDF_BYTE_LIMIT")
        chunks, count = [], 0
        for chunk in response.iter_content(chunk_size=65536):
            count += len(chunk)
            total_pdf_bytes[0] += len(chunk)
            if count > MAX_PDF_BYTES:
                raise DumpTrialError("PDF_BYTE_LIMIT")
            if total_pdf_bytes[0] > MAX_TOTAL_PDF_BYTES:
                raise DumpTrialError("TOTAL_PDF_BYTE_LIMIT")
            chunks.append(chunk)
        if length is not None and count != length:
            raise DumpTrialError("RESPONSE_LENGTH_MISMATCH")
    body = b"".join(chunks)
    if not body.startswith(b"%PDF-"):
        raise DumpTrialError("PDF_MAGIC_MISSING")
    digest = _sha(body)
    filename = f"{sample['code']}-{sample['cninfo_announcement_id']}-{sample['exchange'].lower()}.pdf"
    with (output / filename).open("xb") as stream:
        stream.write(body)
    return status, filename, digest, len(body)


def run_probe(output: Path, identity: dict, *, session_factory=_session, monotonic=time.monotonic):
    output.mkdir(parents=True, exist_ok=False)
    plan = {
        "semantics": SEMANTICS,
        "created_at": _clock(),
        "identity": identity,
        "samples": SAMPLES,
        "max_requests": MAX_REQUESTS,
        "max_json_bytes": MAX_JSON_BYTES,
        "max_pdf_bytes": MAX_PDF_BYTES,
        "max_total_pdf_bytes": MAX_TOTAL_PDF_BYTES,
        "max_elapsed_seconds": MAX_SECONDS,
        "routes": {
            "SZSE": {"query": SZSE_QUERY, "pdf_base": SZSE_PDF_BASE},
            "SSE": {"query": SSE_QUERY, "pdf_base": SSE_PDF_BASE},
        },
        "prior_art": [
            "SZSE annList -> attachPath -> disc.static.szse.cn/download",
            "SSE queryCompanyBulletin -> URL -> static.sse.com.cn",
        ],
        "source_artifacts": {
            "10543485410": "ff5bf465ff2db0d3ecfee8c9bd3f87a22a1e7a56d21ec80bc8480b482d732866",
            "10320565453": "25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c",
            "10580793645": "f942ad6e9dded31ef8f97539ac51887926b99291ddd8bca51ca2111aee545cd5",
            "10581345775": "d4e615d8aeb81113232d9277c7c2bbd0892a4b5c43ce18d96505c2bbfe1867d2",
        },
        "runtime": {"python": platform.python_version(), "requests": version("requests")},
        "retry": False,
        "redirect": False,
        "shared_cookies": False,
        "environment_proxy_credentials": False,
        **AUTHORITY,
    }
    _save(output / "plan.json", plan)
    request_counter = [0]
    total_pdf_bytes = [0]
    exchange_stop = {"SZSE": None, "SSE": None}
    records = []
    started = monotonic()

    for sample in SAMPLES:
        record = {
            **sample,
            "started_at": _clock(),
            "query_http_status": None,
            "query_status": "NOT_ATTEMPTED",
            "query_reason": None,
            "query_raw_file": None,
            "query_raw_sha256": None,
            "query_raw_bytes": 0,
            "matched_metadata": None,
            "pdf_http_status": None,
            "pdf_status": "NOT_ATTEMPTED",
            "pdf_reason": None,
            "pdf_file": None,
            "official_pdf_sha256": None,
            "official_pdf_bytes": 0,
            "same_bytes_as_retained_cninfo": None,
        }
        records.append(record)
        if monotonic() - started >= MAX_SECONDS:
            exchange_stop[sample["exchange"]] = "ELAPSED_BUDGET"
        if exchange_stop[sample["exchange"]]:
            record.update(
                query_status="SKIPPED_EXCHANGE_STOP",
                query_reason=exchange_stop[sample["exchange"]],
                pdf_status="SKIPPED_EXCHANGE_STOP",
                pdf_reason=exchange_stop[sample["exchange"]],
                finished_at=_clock(),
            )
            _save(output / "journal.json", records)
            continue

        try:
            with session_factory() as session:
                status, raw_name, raw_sha, raw_len, match, reason = _query_one(
                    session, sample, output, request_counter=request_counter
                )
                record.update(
                    query_http_status=status,
                    query_status="MATCHED" if match else "NO_EXACT_MATCH",
                    query_reason=reason,
                    query_raw_file=raw_name,
                    query_raw_sha256=raw_sha,
                    query_raw_bytes=raw_len,
                    matched_metadata=match,
                )
                if match is None:
                    record.update(pdf_status="NOT_ATTEMPTED_NO_EXACT_MATCH", pdf_reason=reason)
                else:
                    pdf_status, pdf_file, pdf_sha, pdf_len = _download_one(
                        session, sample, match, output,
                        request_counter=request_counter,
                        total_pdf_bytes=total_pdf_bytes,
                    )
                    expected = sample["retained_cninfo_sha256"]
                    record.update(
                        pdf_http_status=pdf_status,
                        pdf_status="OFFICIAL_PDF_RETAINED_NOT_PRODUCTION_QUALIFIED",
                        pdf_file=pdf_file,
                        official_pdf_sha256=pdf_sha,
                        official_pdf_bytes=pdf_len,
                        same_bytes_as_retained_cninfo=(None if expected is None else expected == pdf_sha),
                    )
        except DumpTrialError as exc:
            if record["query_status"] == "NOT_ATTEMPTED":
                record.update(query_status="REJECTED", query_reason=exc.code,
                              query_http_status=exc.http_status)
            else:
                record.update(pdf_status="REJECTED", pdf_reason=exc.code,
                              pdf_http_status=exc.http_status)
            if exc.http_status == 429 or record["query_http_status"] == 429 or record["pdf_http_status"] == 429:
                exchange_stop[sample["exchange"]] = "HTTP_429_STOP"
            elif exc.code in {"TOTAL_PDF_BYTE_LIMIT", "ELAPSED_BUDGET"}:
                exchange_stop[sample["exchange"]] = exc.code
        except (requests.RequestException, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            if isinstance(exc, requests.Timeout):
                reason = "REQUEST_TIMEOUT"
            elif isinstance(exc, requests.ConnectionError):
                reason = "CONNECTION_FAILED"
            elif isinstance(exc, requests.RequestException):
                reason = "REQUEST_FAILED"
            elif isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError)):
                reason = "JSON_DECODE_FAILED"
            else:
                reason = str(exc) if str(exc) in {
                    "SZSE_ANNOUNCEMENT_RESPONSE_SHAPE", "SZSE_RESPONSE_CAPACITY",
                    "SSE_ANNOUNCEMENT_RESPONSE_SHAPE", "SSE_ANNOUNCEMENT_ROWS_MISSING",
                    "SSE_RESPONSE_CAPACITY",
                } else "LOCAL_RESPONSE_VALIDATION_FAILED"
            if record["query_status"] == "NOT_ATTEMPTED":
                record.update(query_status="FAILED", query_reason=reason)
            else:
                record.update(pdf_status="FAILED", pdf_reason=reason)
            if reason in {"REQUEST_TIMEOUT", "CONNECTION_FAILED", "REQUEST_FAILED"}:
                exchange_stop[sample["exchange"]] = reason
        record["finished_at"] = _clock()
        _save(output / "journal.json", records)

    result = {
        "semantics": SEMANTICS,
        "plan_sha256": _sha((output / "plan.json").read_bytes()),
        "finished_at": _clock(),
        "records": records,
        "attempted_requests": request_counter[0],
        "total_pdf_bytes": total_pdf_bytes[0],
        "exchange_stop": exchange_stop,
        "remote_failure_cause": "UNKNOWN",
        **AUTHORITY,
    }
    result["result_sha256"] = _sha(_raw(result))
    _save(output / "result.json", result)

    lines = [
        "# Exchange-official PDF source probe",
        "",
        "Source capability only; not production recovery or Research.",
        "",
        "| Exchange | Code | CNINFO id | Query | PDF | Same bytes as retained control |",
        "|---|---|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            f"| {record['exchange']} | {record['code']} | {record['cninfo_announcement_id']} | "
            f"{record['query_http_status']} / {record['query_status']} | "
            f"{record['pdf_http_status']} / {record['pdf_status']} | "
            f"{record['same_bytes_as_retained_cninfo']} |"
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
    if result["attempted_requests"] > MAX_REQUESTS or len(result["records"]) != len(SAMPLES):
        raise ValueError("REQUEST_OR_SAMPLE_BOUND_EXCEEDED")
    for sample, record in zip(SAMPLES, result["records"], strict=True):
        for key in ("exchange", "code", "cninfo_announcement_id", "date", "title", "retained_cninfo_sha256"):
            if record[key] != sample[key]:
                raise ValueError("FIXED_SAMPLE_CHANGED")
        raw_file = record["query_raw_file"]
        if raw_file is not None:
            path = output / raw_file
            if path.is_symlink() or len(path.read_bytes()) != record["query_raw_bytes"] or _sha(path.read_bytes()) != record["query_raw_sha256"]:
                raise ValueError("QUERY_RAW_IDENTITY_MISMATCH")
        pdf_file = record["pdf_file"]
        if pdf_file is not None:
            path = output / pdf_file
            body = path.read_bytes()
            if (
                path.is_symlink()
                or not body.startswith(b"%PDF-")
                or len(body) != record["official_pdf_bytes"]
                or _sha(body) != record["official_pdf_sha256"]
            ):
                raise ValueError("OFFICIAL_PDF_IDENTITY_MISMATCH")
            expected = record["retained_cninfo_sha256"]
            if record["same_bytes_as_retained_cninfo"] != (None if expected is None else expected == record["official_pdf_sha256"]):
                raise ValueError("CONTROL_COMPARISON_MISMATCH")
    return "RETAINED_EXCHANGE_SOURCE_PROBE_INTEGRITY_CHECKED_NOT_SOURCE_TRUTH"


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
