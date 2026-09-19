"""Six fixed public PDF requests, using the unchanged Kernel byte transport.

Isolated experiment only (#297/5740234240); never a production successor.
Input locators were recovered from artifacts 10543485410 and 10320565453.
The candidate header values are prior art from carrotly-ai/disclosures@44e819f.
No arbitrary URL, fallback provider, auth, retry, cookie reuse, or OCR interface.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

BASE = "a6bb4b4c5bb371124aeb66132b3b45dad477fac4"
BRANCH = "eval/cninfo-pdf-transport-20260919"
SOURCE_BLOBS = {
    "src/decision_kernel/runtime/cninfo_http.py": "a8b44309e4f2d1e6db6dd7fdcd58fa74103367d6",
    "src/decision_kernel/runtime/hithink_dump_trial.py": "ce39a5b95df4fdab4072afe53c1c1569314c8f60",
}
ROWS = (
    ("000920.SZ", "1225486756", "2026-08-21", None),
    ("603268.SH", "1225497616", "2026-08-25", None),
    ("603353.SH", "1225530965", "2026-08-29", "cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa"),
)
VARIANTS = ("current", "disclosures_headers")
CANDIDATE_HEADERS = {
    "Accept": "application/pdf, application/octet-stream, */*",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
}
MAX_PDF, MAX_TOTAL = 16 * 1024 * 1024, 48 * 1024 * 1024
AUTHORITY = {"production_qualification": "NOT_ESTABLISHED", "research_authority": "NONE",
             "human_attention_authority": "NONE", "investment_authority": "NONE"}


def now():
    return datetime.now(timezone.utc).isoformat()


def raw(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def save(path, value):
    with path.open("xb") as stream:
        stream.write(raw(value))


def dns_failure(error):
    """Inspect exception types only, never error text, headers or remote bodies."""
    todo, seen = [error], set()
    while todo and len(seen) < 12:
        error = todo.pop()
        if id(error) in seen:
            continue
        seen.add(id(error))
        if isinstance(error, socket.gaierror):
            return True
        for item in (getattr(error, "__cause__", None), getattr(error, "__context__", None),
                     getattr(error, "reason", None), *getattr(error, "args", ())):
            if isinstance(item, BaseException):
                todo.append(item)
    return False


class ProbeLimit(RuntimeError):
    pass


def capture(output: Path):
    from decision_kernel.runtime import cninfo_http as cninfo
    from decision_kernel.runtime import hithink_dump_trial as transport
    import requests
    from requests.adapters import HTTPAdapter

    output.mkdir(parents=True, exist_ok=False)
    factory = transport._session
    started = time.monotonic()
    plan = {"base_commit": BASE, "created_at": now(), "source_blobs": SOURCE_BLOBS,
            "input_artifact_sha256": {
                "10543485410": "ff5bf465ff2db0d3ecfee8c9bd3f87a22a1e7a56d21ec80bc8480b482d732866",
                "10320565453": "25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c"},
            "rows": ROWS, "variants": VARIANTS, "candidate_headers": CANDIDATE_HEADERS,
            "max_requests": 6, "max_pdf_bytes": MAX_PDF, "max_total_stream_bytes": MAX_TOTAL,
            "timeout": [10, 45], "per_body_wall_seconds": 60,
            "runtime": {"python": platform.python_version(), "requests": version("requests")},
            "code_sha": os.environ.get("GITHUB_SHA"), "run_id": os.environ.get("GITHUB_RUN_ID"),
            "attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "event": os.environ.get("GITHUB_EVENT_NAME"),
            "semantics": "ISOLATED_PDF_TRANSPORT_COMPARISON_NOT_PRODUCTION_RECOVERY", **AUTHORITY}
    save(output / "plan.json", plan)
    results, total, stop = [], 0, None
    for issuer, ann, day, expected in ROWS:
        url = f"https://static.cninfo.com.cn/finalpage/{day}/{ann}.PDF"
        for variant in VARIANTS:
            record = {"issuer": issuer, "announcement_id": ann, "url": url, "variant": variant,
                      "expected_sha256": expected, "started_at": now(), "http_status": None,
                      "application_get_calls": 0, "stream_bytes": 0, "dns_failure": False,
                      "body_file": None, "body_sha256": None, "body_bytes": 0}
            if stop is not None:
                record.update(status="NOT_ATTEMPTED", stop_reason=stop, finished_at=now())
                results.append(record)
                continue
            call_start = time.monotonic()

            def instrumented_session():
                session = factory()
                if session.trust_env or session.auth is not None or session.cookies or session.proxies:
                    session.close()
                    raise ProbeLimit("UNSAFE_SESSION")
                session.mount("https://", HTTPAdapter(max_retries=0))
                original_request = session.request

                def request(method, destination, **kwargs):
                    nonlocal total
                    if method != "GET" or destination != url or record["application_get_calls"]:
                        raise ProbeLimit("UNPLANNED_REQUEST")
                    if kwargs != {"headers": {"Accept": "application/pdf", "Accept-Encoding": "identity"},
                                  "timeout": (10, 45), "stream": True, "allow_redirects": False}:
                        raise ProbeLimit("ORIGINAL_TRANSPORT_CONTRACT_CHANGED")
                    if variant == "disclosures_headers":
                        kwargs["headers"] = {**kwargs["headers"], **CANDIDATE_HEADERS}
                    record["request_headers"] = dict(kwargs["headers"])
                    record["application_get_calls"] += 1
                    try:
                        response = original_request(method, destination, **kwargs)
                    except requests.RequestException as exc:
                        record["dns_failure"] = dns_failure(exc)
                        raise
                    status = response.status_code
                    record["http_status"] = status if type(status) is int and 100 <= status <= 599 else None
                    iterator = response.iter_content

                    def chunks(**options):
                        nonlocal total
                        for chunk in iterator(**options):
                            record["stream_bytes"] += len(chunk)
                            total += len(chunk)
                            if total > MAX_TOTAL or time.monotonic() - call_start > 60:
                                raise ProbeLimit("PROBE_STREAM_OR_WALL_BUDGET")
                            yield chunk
                    response.iter_content = chunks
                    return response
                session.request = request
                return session

            try:
                remaining = MAX_TOTAL - total
                if remaining <= 0 or time.monotonic() - started > 360:
                    raise ProbeLimit("PROBE_TOTAL_BUDGET")
                with patch.object(transport, "_session", instrumented_session):
                    body = cninfo.fetch_cninfo_pdf_bytes(source_locator=url,
                            max_bytes=min(MAX_PDF, remaining), timeout_seconds=45)
                digest = sha(body)
                name = f"{ann}-{variant}.pdf"
                with (output / name).open("xb") as stream:
                    stream.write(body)
                record.update(status="PDF_RETAINED", body_file=name, body_sha256=digest, body_bytes=len(body),
                              expected_hash_match=None if expected is None else digest == expected)
                if expected is not None and digest != expected:
                    stop = "CONTROL_CONTENT_CHANGED"
            except cninfo.CninfoRuntimeError as exc:
                record.update(status="REJECTED", diagnostic=cninfo.pdf_failure_diagnostic(exc))
                if record["dns_failure"]:
                    stop = "ENVIRONMENT_DNS_FAILURE"
                elif record["http_status"] == 429:
                    stop = "RATE_LIMIT_STOP"
            except ProbeLimit as exc:
                stop = str(exc)
                record.update(status="PROBE_LIMIT", stop_reason=stop)
            record.update(finished_at=now(), elapsed_seconds=round(time.monotonic() - call_start, 3))
            results.append(record)
            save(output / f"attempt-{len(results)}.json", record)
    result = {"plan_sha256": sha(raw(plan)), "finished_at": now(), "results": results,
              "request_count": sum(r["application_get_calls"] for r in results), "stream_bytes": total,
              "stop_reason": stop, "remote_cause": "UNKNOWN", "historical_http_status": "UNKNOWN",
              "semantics": plan["semantics"], **AUTHORITY}
    result["result_sha256"] = sha(raw(result))
    save(output / "result.json", result)
    verify(output)
    return result


def verify(output: Path):
    plan_bytes = (output / "plan.json").read_bytes()
    plan = json.loads(plan_bytes)
    result = json.loads((output / "result.json").read_bytes())
    claimed = result.pop("result_sha256")
    assert sha(raw(result)) == claimed and sha(plan_bytes) == result["plan_sha256"]
    assert plan["base_commit"] == BASE and plan["source_blobs"] == SOURCE_BLOBS
    assert plan["rows"] == [list(r) for r in ROWS] and plan["variants"] == list(VARIANTS)
    assert all(plan[k] == v == result[k] for k, v in AUTHORITY.items())
    assert result["remote_cause"] == result["historical_http_status"] == "UNKNOWN"
    assert len(result["results"]) == 6
    assert result["request_count"] == sum(r["application_get_calls"] for r in result["results"]) <= 6
    for record, (row, variant) in zip(result["results"], [(r, v) for r in ROWS for v in VARIANTS], strict=True):
        issuer, ann, day, expected = row
        assert (record["issuer"], record["announcement_id"], record["variant"], record["expected_sha256"]) == (issuer, ann, variant, expected)
        assert record["url"] == f"https://static.cninfo.com.cn/finalpage/{day}/{ann}.PDF"
        assert record["application_get_calls"] in (0, 1)
        if record["status"] == "PDF_RETAINED":
            assert record["http_status"] == 200 and record["application_get_calls"] == 1
            assert record["body_file"] == f"{ann}-{variant}.pdf"
            body = (output / record["body_file"]).read_bytes()
            assert body.startswith(b"%PDF-") and len(body) == record["body_bytes"] <= MAX_PDF
            assert sha(body) == record["body_sha256"]
            assert record["expected_hash_match"] == (None if expected is None else sha(body) == expected)
        else:
            assert record["status"] in {"REJECTED", "NOT_ATTEMPTED", "PROBE_LIMIT"}
            assert record["body_file"] is record["body_sha256"] is None and record["body_bytes"] == 0
            if record["status"] == "NOT_ATTEMPTED":
                assert record["application_get_calls"] == 0
    return "RETAINED_PROBE_VERIFIED_NOT_SOURCE_TRUTH"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("capture", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "verify":
        print(verify(args.output))
    else:
        for item in capture(args.output)["results"]:
            print(item["issuer"], item["variant"], item["http_status"], item["status"], item["body_bytes"], item["body_sha256"])
