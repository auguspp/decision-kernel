"""One six-object CNINFO appointment capture; no replay of consumed Relay batches.

Reuse the AKShare getPrbookInfo query, original create-only custody and Relay's
pure JSON/clock helpers. No date certification, source fallback or publication.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path

import requests
from decision_kernel.runtime import tushare_relay as relay

PERIOD = "20260930"
URL = "https://www.cninfo.com.cn/new/information/getPrbookInfo"
MAX_BODY = 256 * 1024
WORKFLOW = ".github/workflows/b2-disclosure-appointments.yml"
CLIENT_BLOB = "d2ee02a81648eafe7204a47e7f8e41b56c3c48fd"
COMPANIES = (
    ("603986.SH", "兆易创新", "ODDS_WATCH"),
    ("688277.SH", "天智航", "FOLLOWED"),
    ("600276.SH", "恒瑞医药", "ODDS_WATCH"),
    ("002674.SZ", "兴业科技", "ODDS_WATCH"),
    ("600598.SH", "北大荒", "ODDS_WATCH"),
    ("002050.SZ", "三花智控", "ODDS_WATCH"),
)
SCOPE = {
    "ref": "ef200ed55061aeb019caefca534ba3729b6a467b",
    "path": "docs/readings/2026-09-29-research-agenda-r3.md",
    "git_blob": "db18acced6010040233b1efb0c80e66672cb7e10",
    "sha256": "67a949fb982466e6f8c5bb07d9f18b7fc7bff89d840c6326ab8db9084bc2e4e0",
}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")


def save(path, raw):
    secret = os.environ.get(relay.SECRET_ENV, "").encode("utf-8")
    if secret and secret in raw:
        raise ValueError("B2_CREDENTIAL_REFLECTION")
    with path.open("xb") as stream:
        stream.write(raw)
    if path.read_bytes() != raw:
        raise OSError("B2_SAVE_READBACK")


def public_request(params, *, clock=relay.now, session_factory=requests.Session):
    """One POST, one fresh credential-free session; preserve complete/partial bytes."""
    result = {"requested_at": clock(), "http_status": None, "headers": {},
              "raw": None, "body_complete": False, "error_type": None}
    chunks = []
    length = 0
    try:
        with session_factory() as session:
            session.trust_env = False  # No netrc or environment proxy credentials.
            with session.post(URL, params=params, headers={"Accept": "application/json",
                    "Accept-Encoding": "identity"}, timeout=(5, 15),
                    allow_redirects=False, stream=True) as response:
                result["http_status"] = response.status_code
                result["headers"] = {k: response.headers[k] for k in
                    ("Content-Type", "Content-Length", "Content-Encoding", "Date", "Retry-After")
                    if k in response.headers}
                relay.require(response.headers.get("Content-Encoding", "identity")
                              in ("identity", ""), "B2_ENCODING")
                for chunk in response.iter_content(chunk_size=16384):
                    room = MAX_BODY - length
                    chunks.append(chunk[:room])
                    length += len(chunk)
                    relay.require(length <= MAX_BODY, "B2_BODY_LIMIT")
                result["body_complete"] = True
    except (requests.RequestException, ValueError) as exc:
        result["error_type"] = str(exc) if isinstance(exc, relay.RelayError) else type(exc).__name__
    finally:
        if chunks or result["body_complete"]:
            result["raw"] = b"".join(chunks)
        result["received_at"] = clock()  # Operation end, including stream/error handling.
    return result


def capture(output, identity, *, request=public_request, clock=relay.now):
    scope_raw = (Path(__file__).resolve().parents[2] / SCOPE["path"]).read_bytes()
    relay.require(sha256(scope_raw).hexdigest() == SCOPE["sha256"], "B2_SCOPE_BYTES")
    output = Path(output)
    output.mkdir()  # Existing or partial captures are never overwritten.
    plan = []
    for code, name, relationship in COMPANIES:
        plan.append({"code": code, "name": name, "relationship": relationship,
            "params": {"sectionTime": "2026-09-30", "firstTime": "", "lastTime": "",
                "market": "shkcp" if code == "688277.SH" else "sh" if code.endswith(".SH") else "sz",
                "stockCode": code[:6], "orderClos": "", "isDesc": "",
                "pagesize": "100", "pagenum": "1"}})
    save(output / "plan.json", encoded({"identity": identity, "scope_source": SCOPE,
        "source": URL, "method": "POST", "requests": plan, "started_at": clock(),
        "max_requests": 6, "retries": 0, "redirects": False,
        "source_identity": "CNINFO_PUBLIC_ENDPOINT_NOT_RELAY",
        "reuse": "AKShare stock_yjyg_cninfo.py@0191689d57c667b7c7a198fd0cf97316837ef311",
        "investment_authority": "NONE"}))
    outcomes, stopped = [], False
    for spec in plan:
        code = spec["code"]
        outcome = {"code": code, "status": "NOT_QUERIED_AFTER_STOP", "receipt": None}
        if not stopped:
            directory = output / code
            directory.mkdir()
            record = {"request": spec, "invoked_at": clock(),
                      "date_qualification": "NOT_PERFORMED", "official_appointment_qualified": False}
            try:
                received = request(spec["params"], clock=clock)
            except Exception as exc:
                received = {"http_status": None, "raw": None, "body_complete": False,
                            "error_type": type(exc).__name__}
            retained = deepcopy(received)
            raw = retained.pop("raw")
            retained.update(body=None, bytes=None, sha256=None)
            if raw is not None:
                relay.require(isinstance(raw, bytes) and len(raw) <= MAX_BODY, "B2_RAW_SIZE")
                save(directory / "response.body", raw)
                retained.update(body="response.body", bytes=len(raw), sha256=sha256(raw).hexdigest())
            record["response"] = retained
            status = "SOURCE_OR_TRANSPORT_GAP_RAW_RETAINED"
            if retained["http_status"] == 200 and retained["body_complete"] and not retained["error_type"]:
                try:
                    body = relay.decode(raw)
                    rows = body["prbookinfos"]
                    relay.require(type(rows) is list and len(rows) < 100 and
                                  all(type(row) is dict for row in rows), "B2_TABLE_SHAPE_OR_COVERAGE")
                    relay.require(body.get("error") in (None, ""), "B2_BUSINESS_ERROR")
                    record["row_count"] = len(rows)
                    status = "CAPTURED_REQUIRES_SOURCE_REVIEW" if rows else "EMPTY_RESPONSE_NOT_NO_APPOINTMENT"
                except (ValueError, TypeError, KeyError):
                    status = "RESPONSE_GAP_RAW_RETAINED"
            stopped = status not in ("CAPTURED_REQUIRES_SOURCE_REVIEW", "EMPTY_RESPONSE_NOT_NO_APPOINTMENT")
            record.update(status=status, finished_at=clock())
            save(directory / "receipt.json", encoded(record))
            outcome.update(status=status, receipt=f"{code}/receipt.json")
        outcomes.append(outcome)
    result = {"identity": identity, "source": URL, "finished_at": clock(), "outcomes": outcomes,
        "status": "STOPPED_WITH_GAPS" if stopped else "CAPTURED_REQUIRES_SOURCE_REVIEW",
        "official_appointment_qualified": False, "research_executed": False,
        "investment_authority": "NONE"}
    save(output / "capture.json", encoded(result))
    lines = ["# B2 巨潮六对象预约原始核对", "",
             "报告期20260930；仅保管原响应，证券/报告期/首次/变更/实际字段另审。",
             "不是重跑旧Relay；空返回、失败、未查询分别保留，无自动官方日期认证。", "",
             "| 证券 | 本次取得状态 |", "|---|---|"]
    lines.extend(f"| {o['code']} | {o['status']} |" for o in outcomes)
    save(output / "summary.md", ("\n".join(lines) + "\n").encode("utf-8"))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    expected = "auguspp/decision-kernel/" + WORKFLOW + "@refs/heads/main"
    relay.require(os.environ.get("GITHUB_WORKFLOW_REF") == expected
                  and os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
                  and os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "B2_INVOCATION_SCOPE")
    identity = {key: os.environ.get(key) for key in
        ("GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_REF", "GITHUB_RUN_ID",
         "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW_REF", "GITHUB_EVENT_NAME")}
    result = capture(args.output, identity)
    print(result["status"])
    return 0 if result["status"] == "CAPTURED_REQUIRES_SOURCE_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
