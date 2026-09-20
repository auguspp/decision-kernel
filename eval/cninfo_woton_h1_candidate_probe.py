"""One bounded cninfo-mcp query/download adaptation, not Research admission.

Run from the repository root with ``python -m eval.cninfo_woton_h1_candidate_probe``.
Only the reviewed query shape is reused; no upstream package is downloaded or run.

Query-shape prior art: youhaozhao/cninfo-mcp@f0108154966b50fe94d5d31e5c381a586b8c53d6,
python/spider.py::_build_report_query (MIT), Copyright (c) 2026 youhaozhao.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import html
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

from decision_kernel.adapters.pdf_text import extract_pdf_text
from decision_kernel.runtime.hithink_dump_trial import DumpTrialError, _check_response, _session
from eval.cninfo_pdf_transport_probe import _clock, _raw, _save, _sha, native_identity

QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
UPSTREAM = "youhaozhao/cninfo-mcp@f0108154966b50fe94d5d31e5c381a586b8c53d6"
SEMANTICS = "BOUNDED_WOTON_H1_CNINFO_MCP_THIN_ADAPTER_NOT_RESEARCH"
SINA_SHA256 = "27c74e31c8aaf5a38d27b688f0841d81797816420b591647bfb6763e485b7728"
SCOPE = {"ticker": "000920", "issuer": "沃顿科技股份有限公司", "report_type": "semiannual",
         "report_year": 2026, "query_window": ["2026-07-01", "2026-09-20"]}
LIMITS = {"directory_requests": 2, "pdf_requests": 3, "requests": 5,
          "directory_bytes": 512 * 1024, "pdf_bytes": 4 * 1024 * 1024,
          "total_response_bytes": 12 * 1024 * 1024, "acquisition_seconds": 180,
          "pdf_pages": 250, "extracted_chars": 1_000_000}
AUTHORITY = {"production_qualification": "NOT_ESTABLISHED", "research_authority": "NONE",
             "human_attention_authority": "NONE", "investment_authority": "NONE",
             "research_execution_allowed": False, "model_calls": 0,
             "research_work_writes": 0, "market_state_writes": 0, "events_created": 0}
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
QUERY_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Encoding": "identity", "User-Agent": USER_AGENT,
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-HK;q=0.6,zh-TW;q=0.5",
    "Host": "www.cninfo.com.cn", "Origin": "http://www.cninfo.com.cn",
    "Referer": "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
    "X-Requested-With": "XMLHttpRequest",
}
PDF_HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}


def build_query(page):
    if type(page) is not int or page not in (1, 2):
        raise ValueError("FIXED_QUERY_PAGE_REQUIRED")
    return {"pageNum": page, "pageSize": 30, "tabName": "fulltext", "column": "szse",
            "stock": "", "searchkey": "000920", "secid": "", "plate": "sz",
            "category": "category_bndbg_szsh", "trade": "",
            "seDate": "2026-07-01~2026-09-20"}


def _attachment(value, announcement_id):
    if not isinstance(value, str) or not value or re.search(r"[\s\\\x00-\x1f\x7f]", value):
        raise ValueError("UNSAFE_ATTACHMENT")
    part = urlsplit(urljoin("https://static.cninfo.com.cn/", value))
    if (part.scheme != "https" or part.hostname != "static.cninfo.com.cn"
            or part.username is not None or part.password is not None or part.port not in (None, 443)
            or part.query or part.fragment
            or not re.fullmatch(r"/finalpage/\d{4}-\d{2}-\d{2}/" + re.escape(announcement_id) + r"\.[Pp][Dd][Ff]", part.path)):
        raise ValueError("UNSAFE_ATTACHMENT")
    return urlunsplit(("https", "static.cninfo.com.cn", part.path, "", ""))


def _candidate(row):
    if not isinstance(row, dict) or row.get("secCode") != "000920":
        return {"eligible": False, "reason": "OTHER_OR_UNKNOWN_SECURITY"}
    title = row.get("announcementTitle")
    if not isinstance(title, str) or len(title) > 1000:
        return {"eligible": False, "reason": "INVALID_TITLE"}
    compact = re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]*>", "", title)))
    pattern = (r"(?:(?:沃顿科技股份有限公司|沃顿科技)[:：]?)?2026年?"
               r"(?:半年度报告|中期报告|半年报)(?:[（(][^()（）]{1,60}[)）]){0,2}")
    if (any(word in compact for word in ("摘要", "英文", "公告", "说明", "致歉", "取消", "确认意见"))
            or not re.fullmatch(pattern, compact)):
        return {"eligible": False, "reason": "NOT_2026_H1_FULL_REPORT", "title": title}
    try:
        published = row.get("announcementTime")
        if type(published) is int:
            published = datetime.fromtimestamp(published / 1000, timezone(timedelta(hours=8))).date().isoformat()
        if (not isinstance(published, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", published)
                or not SCOPE["query_window"][0] <= published <= SCOPE["query_window"][1]):
            raise ValueError("PUBLICATION_OUTSIDE_WINDOW")
        datetime.strptime(published, "%Y-%m-%d")
        announcement_id = row.get("announcementId")
        if not isinstance(announcement_id, str) or not re.fullmatch(r"[0-9]{1,32}", announcement_id):
            raise ValueError("INVALID_ANNOUNCEMENT_ID")
        locator = _attachment(row.get("adjunctUrl"), announcement_id)
    except (ValueError, OverflowError, OSError):
        return {"eligible": False, "reason": "INVALID_DATE_OR_ATTACHMENT_IDENTITY", "title": title}
    return {"eligible": True, "reason": "FULL_REPORT_CANDIDATE_NOT_DOCUMENT_QUALIFICATION",
            "announcement_id": announcement_id, "title": title, "published_date": published,
            "source_locator": locator,
            "revision_label_present": any(word in compact for word in ("修订", "更正", "更新", "补充"))}


def _directory(raw):
    data = json.loads(raw)
    if (not isinstance(data, dict) or "announcements" not in data
            or (data["announcements"] is not None and not isinstance(data["announcements"], list))):
        raise ValueError("INVALID_DIRECTORY_RESPONSE")
    rows = data["announcements"] or []
    if len(rows) > 30 or any(not isinstance(row, dict) for row in rows):
        raise ValueError("INVALID_DIRECTORY_ROWS")
    if "hasMore" in data and type(data["hasMore"]) is not bool:
        raise ValueError("INVALID_HAS_MORE")
    total = data.get("totalAnnouncement")
    if total is not None and (type(total) is not int or total < 0):
        raise ValueError("INVALID_TOTAL")
    if data["announcements"] is None and total is None and "hasMore" not in data:
        raise ValueError("UNQUALIFIED_NULL_DIRECTORY")
    return rows, data.get("hasMore"), total


def _catalog(output, records):
    decisions, candidates, seen, need_more, failure = [], [], set(), True, None
    received = 0
    queries = [row for row in records if row["kind"] == "DIRECTORY"]
    for record in queries:
        if not need_more:
            raise ValueError("UNNECESSARY_DIRECTORY_REQUEST")
        if record["body_file"] is None:
            failure = record["reason"] or "DIRECTORY_NOT_RETAINED"
            break
        try:
            rows, has_more, total = _directory((output / record["body_file"]).read_bytes())
        except (ValueError, UnicodeDecodeError):
            failure = "DIRECTORY_DECODE_OR_SHAPE_FAILED"
            break
        received += len(rows)
        for index, row in enumerate(rows):
            selected = {"query_sequence": record["sequence"], "row_index": index, **_candidate(row)}
            decisions.append(selected)
            if selected["eligible"]:
                key = (selected["announcement_id"], selected["source_locator"])
                if key not in seen:
                    seen.add(key)
                    candidates.append(selected)
        need_more = has_more is True or len(rows) == 30 or (total is not None and total > received)
    return {"status": ("DIRECTORY_FAILED" if failure else "MORE_ROWS_NOT_READ" if need_more
                       else "BOUNDED_QUERY_END_OBSERVED_NOT_INVENTORY_CERTIFICATION"),
            "failure": failure, "decisions": decisions, "candidates": candidates,
            "match_status": ("CANDIDATES_RETAINED" if candidates else "UNKNOWN" if failure or need_more
                             else "NO_MATCH_IN_RETURNED_ROWS"),
            "version_selection": "MULTIPLE_CANDIDATES_NO_CANONICAL_VERSION_SELECTED" if len(candidates) > 1
                                 else "NO_CANONICAL_VERSION_SELECTED"}


def _extract(raw):
    return asdict(extract_pdf_text(raw, max_pdf_bytes=LIMITS["pdf_bytes"],
                  max_pages=LIMITS["pdf_pages"], max_extracted_chars=LIMITS["extracted_chars"]))


def _document(output, record, *, retain_extraction=False):
    result = {"request_sequence": record["sequence"], "candidate": record["candidate"],
              "status": "PDF_NOT_RETAINED", "extraction_file": None, "extraction_sha256": None,
              "identity": None, "parse_error_type": None, "sina_comparison": "NOT_COMPARED",
              "page_count": None, "text_sha256": None}
    if record["body_file"] is None:
        return result
    raw = (output / record["body_file"]).read_bytes()
    result["sina_comparison"] = "SAME_BYTES" if _sha(raw) == SINA_SHA256 else "DIFFERENT_BYTES"
    try:
        parsed = _extract(raw)
    except Exception as exc:
        result["status"] = "BODY_RETAINED_PDF_PARSE_FAILED"
        result["parse_error_type"] = type(exc).__name__
        return result
    filename = f"extraction-{record['sequence']}.json"
    if retain_extraction:
        _save(output / filename, parsed)
    elif not (output / filename).is_file() or (output / filename).read_bytes() != _raw(parsed):
        raise ValueError("EXTRACTION_DIFFERS_FROM_RETAINED_PDF")
    cover = re.sub(r"\s+", "", "\n".join(page["text"] for page in parsed["pages"][:2]))
    text = "\n".join(page["text"] for page in parsed["pages"])
    compact_text = re.sub(r"\s+", "", text)
    identity = {"issuer_in_cover": "沃顿科技股份有限公司" in cover,
                "period_in_cover": bool(re.search(r"2026年?(?:半年度报告|中期报告)", cover)),
                "ticker_in_text": bool(re.search(r"(?<![0-9])000920(?![0-9])", text)),
                "statement_period": bool(re.search(r"合并利润表.{0,120}?项目2026年半年度", compact_text))}
    result.update(extraction_file=filename, extraction_sha256=_sha(_raw(parsed)), identity=identity,
                  page_count=parsed["page_count"], text_sha256=parsed["text_sha256"],
                  status="PDF_PARSED_IDENTITY_CHECKED_NOT_RESEARCH" if all(identity.values())
                         else "PDF_RETAINED_DOCUMENT_IDENTITY_MISMATCH")
    return result


def run_probe(output: Path, identity: dict, *, session_factory=_session, monotonic=time.monotonic):
    if output.is_symlink() or any(parent.is_symlink() for parent in output.parents):
        raise ValueError("UNSAFE_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    plan = {"semantics": SEMANTICS, "created_at": _clock(), "identity": identity,
            "scope": SCOPE, "limits": LIMITS, "upstream": UPSTREAM, "reuse_decision": "THIN_ADAPTER",
            "query_forms": [build_query(1), build_query(2)], "query_headers": QUERY_HEADERS,
            "pdf_headers": PDF_HEADERS, "sina_pdf_sha256": SINA_SHA256,
            "runtime": {"python": platform.python_version(), "requests": version("requests"),
                        "pypdf": version("pypdf")},
            "scope_receipt": "https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5750797689",
            "time_budget_semantics": "CHECK_BEFORE_REQUEST_AND_DURING_STREAM_NOT_A_HARD_WALL_DEADLINE",
            "adaptations": ["fixed security/report/window", "one exchange", "fixed user agent",
                "identity encoding for byte limits", "no retries or redirects", "bounded streaming",
                "retain revised full-report candidates", "source bytes before original Kernel parser"],
            "org_search": False, "retry": False, "redirect": False, "shared_cookies": False,
            "environment_proxy_credentials": False, **AUTHORITY}
    _save(output / "plan.json", plan)
    records, documents, stop, total_response_bytes = [], [], None, 0
    started = monotonic()

    def transfer(kind, locator, *, page=None, candidate=None):
        nonlocal stop, total_response_bytes
        if stop:
            return None
        remaining = LIMITS["acquisition_seconds"] - (monotonic() - started)
        if remaining <= 0 or len(records) >= LIMITS["requests"]:
            stop = "ELAPSED_BUDGET" if remaining <= 0 else "REQUEST_BUDGET"
            return None
        record = {"sequence": len(records) + 1, "kind": kind, "url": locator,
                  "method": "POST" if kind == "DIRECTORY" else "GET", "page": page,
                  "candidate": candidate, "started_at": _clock(), "finished_at": None,
                  "status": "IN_PROGRESS", "http_status": None, "received_bytes": 0,
                  "body_file": None, "body_sha256": None, "reason": None}
        records.append(record)
        _save(output / "journal.json", records)
        cap = LIMITS["directory_bytes"] if kind == "DIRECTORY" else LIMITS["pdf_bytes"]
        try:
            with session_factory() as session:
                request = session.post if kind == "DIRECTORY" else session.get
                kwargs = {"headers": dict(QUERY_HEADERS if kind == "DIRECTORY" else PDF_HEADERS),
                          "timeout": (min(10, remaining), min(30, remaining)),
                          "stream": True, "allow_redirects": False}
                if kind == "DIRECTORY":
                    kwargs["data"] = build_query(page)
                with request(locator, **kwargs) as response:
                    status = response.status_code
                    record["http_status"] = status if type(status) is int and 100 <= status <= 599 else None
                    length = _check_response(response)
                    if length is not None and length > cap:
                        raise DumpTrialError("RESPONSE_BYTE_LIMIT")
                    if length is not None and total_response_bytes + length > LIMITS["total_response_bytes"]:
                        raise DumpTrialError("TOTAL_RESPONSE_BYTE_LIMIT")
                    chunks = []
                    for chunk in response.iter_content(chunk_size=65536):
                        record["received_bytes"] += len(chunk)
                        total_response_bytes += len(chunk)
                        if total_response_bytes > LIMITS["total_response_bytes"]:
                            raise DumpTrialError("TOTAL_RESPONSE_BYTE_LIMIT")
                        if record["received_bytes"] > cap:
                            raise DumpTrialError("RESPONSE_BYTE_LIMIT")
                        if monotonic() - started >= LIMITS["acquisition_seconds"]:
                            raise DumpTrialError("ELAPSED_BUDGET")
                        chunks.append(chunk)
                    if length is not None and length != record["received_bytes"]:
                        raise DumpTrialError("RESPONSE_LENGTH_MISMATCH")
                    body = b"".join(chunks)
                    extension = "pdf" if kind == "PDF" and body.startswith(b"%PDF-") else "bin"
                    filename = f"response-{record['sequence']}.{extension}"
                    with (output / filename).open("xb") as stream:
                        stream.write(body)
                    record.update(body_file=filename, body_sha256=_sha(body), status="RESPONSE_RETAINED")
        except DumpTrialError as exc:
            record.update(status="REJECTED", reason=exc.code)
            if record["http_status"] == 429:
                stop = "HTTP_429_STOP"
            elif exc.code in {"TOTAL_RESPONSE_BYTE_LIMIT", "ELAPSED_BUDGET"}:
                stop = exc.code
        except requests.RequestException as exc:
            record.update(status="TRANSPORT_FAILED", reason="REQUEST_TIMEOUT" if isinstance(exc, requests.Timeout)
                          else "CONNECTION_FAILED" if isinstance(exc, requests.ConnectionError) else "REQUEST_FAILED")
            stop = record["reason"]
        record["finished_at"] = _clock()
        _save(output / "journal.json", records)
        return record

    internal_failure = None
    try:
        for page in (1, 2):
            record = transfer("DIRECTORY", QUERY_URL, page=page)
            catalog = _catalog(output, records)
            if record is None or catalog["status"] != "MORE_ROWS_NOT_READ":
                break
        if catalog["status"] != "DIRECTORY_FAILED":
            for candidate in catalog["candidates"][:LIMITS["pdf_requests"]]:
                record = transfer("PDF", candidate["source_locator"], candidate=candidate)
                if record is None:
                    break
                documents.append(_document(output, record, retain_extraction=True))
    except Exception as exc:
        # Preserve bytes and a finite local failure category, never remote exception text.
        internal_failure = type(exc).__name__
    catalog = _catalog(output, records)
    result = {"semantics": SEMANTICS, "plan_sha256": _sha((output / "plan.json").read_bytes()),
              "finished_at": _clock(), "records": records, "catalog": catalog, "documents": documents,
              "attempted_requests": len(records), "received_response_bytes": total_response_bytes,
              "elapsed_seconds": max(0, monotonic() - started),
              "unattempted_candidates": catalog["candidates"][sum(row["kind"] == "PDF" for row in records):],
              "stop_reason": stop, "internal_failure": internal_failure,
              "remote_failure_cause": "UNKNOWN", **AUTHORITY}
    result["result_sha256"] = _sha(_raw(result))
    _save(output / "result.json", result)
    summary = ["# Woton 2026 H1 source candidate verification", "",
               "THIN_ADAPTER; no Research, model call, research slot or production recovery.", "",
               f"Query: {catalog['status']}; candidates: {len(catalog['candidates'])}; requests: {len(records)}.",
               f"Version status: {catalog['version_selection']}.", ""]
    summary += [f"- {doc['candidate']['announcement_id']}: {doc['status']}; Sina: {doc['sina_comparison']}." for doc in documents]
    summary += [f"- Unattempted candidates: {len(result['unattempted_candidates'])}; stop: {stop}; local failure: {internal_failure}."]
    with (output / "summary.md").open("x", encoding="utf-8") as stream:
        stream.write("\n".join(summary) + "\n")
    return result


def verify(output: Path):
    if output.is_symlink() or any(path.is_symlink() for path in output.iterdir()):
        raise ValueError("UNSAFE_RETAINED_PATH")
    plan = json.loads((output / "plan.json").read_bytes())
    result = json.loads((output / "result.json").read_bytes())
    digest = result.pop("result_sha256")
    if digest != _sha(_raw(result)) or result["plan_sha256"] != _sha((output / "plan.json").read_bytes()):
        raise ValueError("RESULT_OR_PLAN_HASH_MISMATCH")
    if (plan["scope"] != SCOPE or plan["limits"] != LIMITS or plan["upstream"] != UPSTREAM
            or plan["query_forms"] != [build_query(1), build_query(2)]
            or plan["query_headers"] != QUERY_HEADERS or plan["pdf_headers"] != PDF_HEADERS
            or plan["sina_pdf_sha256"] != SINA_SHA256 or plan["reuse_decision"] != "THIN_ADAPTER"
            or any(plan.get(key) is not False for key in ("org_search", "retry", "redirect", "shared_cookies", "environment_proxy_credentials"))
            or any(obj.get("semantics") != SEMANTICS or any(obj.get(k) != v for k, v in AUTHORITY.items())
                   for obj in (plan, result))):
        raise ValueError("FIXED_SCOPE_OR_AUTHORITY_CHANGED")
    records = result["records"]
    queries = [row for row in records if row["kind"] == "DIRECTORY"]
    pdfs = [row for row in records if row["kind"] == "PDF"]
    if (not 0 <= len(queries) <= 2 or len(pdfs) > 3 or len(records) > 5
            or records != queries + pdfs or result["attempted_requests"] != len(records)
            or (records and json.loads((output / "journal.json").read_bytes()) != records)):
        raise ValueError("REQUEST_OR_JOURNAL_CONTRACT_CHANGED")
    for sequence, row in enumerate(records, 1):
        if row["sequence"] != sequence or row["status"] == "IN_PROGRESS" or not row["finished_at"]:
            raise ValueError("INCOMPLETE_REQUEST")
        if row["kind"] == "DIRECTORY" and (row["url"] != QUERY_URL or row["page"] != sequence or row["method"] != "POST"):
            raise ValueError("DIRECTORY_REQUEST_CHANGED")
        if row["body_file"] is not None:
            if (row["body_file"] not in (f"response-{sequence}.bin", f"response-{sequence}.pdf")
                    or row["status"] != "RESPONSE_RETAINED" or row["http_status"] != 200):
                raise ValueError("UNSAFE_BODY_REFERENCE")
            raw = (output / row["body_file"]).read_bytes()
            extension = "pdf" if row["kind"] == "PDF" and raw.startswith(b"%PDF-") else "bin"
            cap = LIMITS["directory_bytes"] if row["kind"] == "DIRECTORY" else LIMITS["pdf_bytes"]
            if (row["body_file"] != f"response-{sequence}.{extension}" or len(raw) != row["received_bytes"]
                    or len(raw) > cap or _sha(raw) != row["body_sha256"]):
                raise ValueError("RETAINED_BODY_HASH_OR_SIZE_MISMATCH")
    catalog = _catalog(output, records)
    if result["catalog"] != catalog or (catalog["status"] == "DIRECTORY_FAILED" and pdfs):
        raise ValueError("DIRECTORY_SELECTION_CHANGED")
    for row, candidate in zip(pdfs, catalog["candidates"]):
        if row["candidate"] != candidate or row["url"] != candidate["source_locator"] or row["method"] != "GET":
            raise ValueError("PDF_NOT_BOUND_TO_ACTUAL_DIRECTORY")
    if len(pdfs) > len(catalog["candidates"]) or result["documents"] != [_document(output, row) for row in pdfs]:
        raise ValueError("DOCUMENT_CHECK_DIFFERS")
    if (result["received_response_bytes"] != sum(row["received_bytes"] for row in records)
            or sum(row["received_bytes"] for row in records if row["body_file"] is not None) > LIMITS["total_response_bytes"]
            or result["unattempted_candidates"] != catalog["candidates"][len(pdfs):]):
        raise ValueError("PDF_BUDGET_OR_UNATTEMPTED_SET_CHANGED")
    return "RETAINED_SOURCE_PROBE_RECHECKED_NOT_RESEARCH_OR_INVENTORY_CERTIFICATION"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.verify_only:
        identity = native_identity()
        result = run_probe(args.output, identity)
    print(verify(args.output))
    if not args.verify_only:
        observations = {
            "identity": {"code_commit": identity["GITHUB_SHA"], "run_id": identity["GITHUB_RUN_ID"]},
            "directory": {"status": result["catalog"]["status"],
                          "match_status": result["catalog"]["match_status"],
                          "candidate_count": len(result["catalog"]["candidates"])},
            "requests": [{key: row[key] for key in ("sequence", "kind", "url", "http_status",
                "received_bytes", "body_sha256", "reason", "started_at", "finished_at")}
                for row in result["records"]],
            "documents": [{"announcement_id": doc["candidate"]["announcement_id"],
                **{key: doc[key] for key in ("status", "identity", "page_count", "text_sha256", "sina_comparison")}}
                for doc in result["documents"]],
            **{key: result[key] for key in ("attempted_requests", "stop_reason", "internal_failure",
                                           "model_calls", "research_work_writes")},
        }
        print("SOURCE_PROBE_OBSERVATIONS=" + json.dumps(observations, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
