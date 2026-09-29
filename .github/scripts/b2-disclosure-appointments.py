"""Capture six explicitly scoped B2 appointment responses with the original Relay.

Source preparation only: no date certification, calendar/publisher mutation,
provider fallback, research, notification, or investment authority.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path

from decision_kernel.runtime import tushare_relay as relay

PERIOD = "20260930"
FIELDS = ("ts_code", "ann_date", "end_date", "pre_date", "actual_date", "modify_date")
COMPANIES = (
    ("688277.SH", "天智航", "FOLLOWED"),
    ("600276.SH", "恒瑞医药", "ODDS_WATCH"),
    ("002674.SZ", "兴业科技", "ODDS_WATCH"),
    ("600598.SH", "北大荒", "ODDS_WATCH"),
    ("002050.SZ", "三花智控", "ODDS_WATCH"),
    ("603986.SH", "兆易创新", "ODDS_WATCH"),
)
SCOPE = {
    "repository": "auguspp/decision-kernel",
    "ref": "202e95fe35817d01a172d04a106c5b30a6fd4b0b",
    "path": "docs/readings/2026-09-29-research-agenda-r2.md",
    "git_blob": "8016d8735c7b744173494579cb0eaba74b6450c6",
}
CLIENT_BLOB = "d2ee02a81648eafe7204a47e7f8e41b56c3c48fd"
WORKFLOW = ".github/workflows/b2-disclosure-appointments.yml"


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")


def save(path, raw):
    # Reflected secrets must never enter source artifacts, including safe headers.
    secret = os.environ.get(relay.SECRET_ENV, "").encode("utf-8")
    if secret and secret in raw:
        raise ValueError("B2_CREDENTIAL_REFLECTION")
    # Only new output paths; an incomplete capture is not overwritten on retry.
    with path.open("xb") as stream:
        stream.write(raw)
    if path.read_bytes() != raw:
        raise OSError("B2_SAVE_READBACK")


def inspect_body(raw, code):
    """Inspect table shape and requested identity; leave all date values raw."""
    body = relay.decode(raw)
    relay.require(type(body.get("code")) is int and body["code"] == 0
                  and body.get("ok", True) is True
                  and body.get("error") in (None, ""), "B2_BUSINESS_STATUS")
    relay.require(body.get("api_name") in (None, "disclosure_date"), "B2_API_IDENTITY")
    rows = relay.rows(body)
    fields = body["data"]["fields"]
    relay.require(len(fields) == len(set(fields)), "B2_DUPLICATE_FIELDS")
    missing = sorted(set(FIELDS) - set(fields))
    matches = [i for i, row in enumerate(rows)
               if row.get("ts_code") == code and row.get("end_date") == PERIOD]
    issues = []
    if missing:
        issues.append("MISSING_REQUESTED_FIELDS")
    if len(matches) != len(rows):
        issues.append("REQUEST_IDENTITY_MISMATCH")
    if len(rows) >= 100 or (body.get("count") is not None and body["count"] > len(rows)):
        issues.append("POSSIBLE_TRUNCATION_NO_PAGINATION")
    return {"rows": rows, "matching_row_indexes": matches, "missing_fields": missing,
            "issues": issues, "date_qualification": "NOT_PERFORMED",
            "revision_order": "NOT_INFERRED_NO_KEEP_LAST",
            "coverage": "EMPTY_RESPONSE_NOT_NO_APPOINTMENT" if not rows else
                        "BOUNDED_RESPONSE_NOT_COMPLETE_HISTORY"}


def capture(output, identity, *, request=None, clock=relay.now):
    """At most six original client calls; stop the remaining batch on any failure."""
    request = relay.request if request is None else request
    output = Path(output)
    output.mkdir()  # Fails before requests when this directory already exists.
    plan = [{"code": code, "name": name, "relationship": relation,
             "api": "disclosure_date", "params": {"ts_code": code, "end_date": PERIOD,
             "fields": ",".join(FIELDS), "limit": "100"}}
            for code, name, relation in COMPANIES]
    save(output / "plan.json", encoded({"identity": identity, "scope_source": SCOPE,
         "original_client_blob": CLIENT_BLOB, "source_host": relay.BASE,
         "source_identity": "THIRD_PARTY_RELAY_NOT_OFFICIAL_TUSHARE_OR_EXCHANGE",
         "started_at": clock(), "requests": plan, "investment_authority": "NONE"}))
    outcomes, stopped = [], False
    for spec in plan:
        code = spec["code"]
        outcome = {"code": code, "status": "NOT_QUERIED_AFTER_STOP", "receipt": None}
        if stopped:
            outcomes.append(outcome)
            continue
        directory = output / code
        directory.mkdir()
        record = {"request": spec, "invoked_at": clock(), "client_result": None}
        try:
            result = request(spec["api"], spec["params"])
        except Exception as exc:
            # Do not serialize exception text/URLs that may contain credentials.
            record.update(status="CLIENT_EXCEPTION", error_type=type(exc).__name__,
                          raw_receipt="UNAVAILABLE", finished_at=clock())
            if isinstance(exc, relay.RelayError) and str(exc) == "CREDENTIAL_UNAVAILABLE":
                record["status"] = "CREDENTIAL_UNAVAILABLE"
            stopped = True
        else:
            record["finished_at"] = clock()
            retained = deepcopy(result)
            for index, attempt in enumerate(retained["attempts"], 1):
                raw = attempt.pop("raw")
                attempt["body"] = None
                attempt["bytes"] = None
                attempt["sha256"] = None
                if raw is not None:
                    relay.require(isinstance(raw, bytes) and len(raw) <= relay.MAX_BODY,
                                  "B2_RAW_SIZE")
                    filename = f"attempt-{index}.body"
                    save(directory / filename, raw)
                    attempt.update(body=filename, bytes=len(raw), sha256=sha256(raw).hexdigest())
            record["client_result"] = retained
            record["status"] = result["status"]
            refusal = any(a.get("http_status") in (401, 403, 429)
                          for a in result["attempts"])
            if result["status"] != "SUCCESS" or refusal:
                stopped = True
            else:
                try:
                    relay.require(result["api"] == spec["api"] and
                                  result["params"] == spec["params"], "B2_REQUEST_RECEIPT")
                    record["table"] = inspect_body(result["attempts"][-1]["raw"], code)
                except (ValueError, TypeError, KeyError):
                    record["status"] = "RESPONSE_REJECTED_RAW_RETAINED"
                    stopped = True
                else:
                    record["status"] = ("FIELD_OR_COVERAGE_GAP_RAW_RETAINED"
                                        if record["table"]["issues"] else
                                        record["table"]["coverage"])
                    stopped = bool(record["table"]["issues"])
        save(directory / "receipt.json", encoded(record))
        outcome.update(status=record["status"], receipt=f"{code}/receipt.json")
        outcomes.append(outcome)
    result = {"identity": identity, "finished_at": clock(), "outcomes": outcomes,
              "status": "STOPPED_WITH_GAPS" if stopped else "CAPTURED_REQUIRES_SOURCE_REVIEW",
              "official_appointment_qualified": False, "research_executed": False,
              "investment_authority": "NONE"}
    save(output / "capture.json", encoded(result))
    lines = ["# B2 六对象预约原始取得", "",
             "报告期：20260930。第三方 Relay；原日期/修正值在原响应，尚未认证官方预约。",
             "空返回不证明没有预约，未查询不记为零；没有自动改日历、Research、Watch 或持仓。", "",
             "| 证券 | 本次取得状态 |", "|---|---|"]
    lines.extend(f"| {item['code']} | {item['status']} |" for item in outcomes)
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
    print(result["status"])  # No raw vendor text or credentials in the log.
    return 1 if result["status"] == "STOPPED_WITH_GAPS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
