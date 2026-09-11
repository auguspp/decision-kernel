"""Bounded 5-code THS public-history source-identity probe.

This is evidence collection only. It never writes production market state, cache,
events, Research, Odds, or Action. It performs at most one public THS request for
each frozen code and has no retry path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Mapping

from decision_kernel.adapters.hithink import normalize_hithink_calendar
from decision_kernel.adapters.hithink_index import normalize_hithink_completed_index_history
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import hithink_http, hithink_index_http

REPOSITORY = "auguspp/decision-kernel"
WORKFLOW = ".github/workflows/sector-public-history-probe.yml"
PROBE_ID = "sector-public-history-20260911-v1"
CODES = ("881101.TI", "881270.TI", "884001.TI", "884002.TI", "884023.TI")
TARGET_DATES = ("2026-09-09", "2026-09-10")
FIELDS = ("close", "volume", "turnover")
PUBLIC_REQUEST_MAX = 5
THS_YEAR = 2026
THS_URL = "https://d.10jqka.com.cn/v4/line/bk_{code}/01/2026.js"
AKSHARE_VERSION = "1.18.94"
AKSHARE_COMMIT = "8e95744b79ae22326308ccd2b4e62650c5b53c55"
HITHINK_RUN_ID = 34566950303
HITHINK_ARTIFACT_ID = 10187281705
HITHINK_ARTIFACT_NAME = "sector-recovery-34566950303-1"
HITHINK_ARTIFACT_BYTES = 520455
HITHINK_ARTIFACT_SHA256 = "aedf5fc5507fa33c00f316be72c14b50962486961ba7199e097d2628205dc60b"
AUTHORITY = {
    "production_state_writes": 0,
    "cache_writes": 0,
    "events_created": 0,
    "research_writes": 0,
    "odds_writes": 0,
    "action_writes": 0,
    "restore_authority": False,
    "investment_authority": "NONE",
}


class ProbeError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProbeError(message)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    require(path.is_file() and not path.is_symlink(), f"MISSING_FILE:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def decimal_value(raw: Any, *, field: str, positive: bool = False) -> Decimal:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ProbeError(f"NON_NUMERIC_{field.upper()}") from exc
    require(value.is_finite(), f"NON_FINITE_{field.upper()}")
    require(value > 0 if positive else value >= 0, f"INVALID_{field.upper()}")
    return value


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def invocation(env: Mapping[str, str]) -> dict[str, str]:
    expected = {
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW_REF": REPOSITORY + "/" + WORKFLOW + "@refs/heads/main",
    }
    require(all(env.get(key) == value for key, value in expected.items()), "FRESH_MAIN_PROBE_ONLY")
    require(re.fullmatch(r"[0-9a-f]{40}", env.get("GITHUB_SHA", "")) is not None, "INVALID_GITHUB_SHA")
    require(env.get("GITHUB_RUN_ID", "").isdigit(), "INVALID_GITHUB_RUN_ID")
    return {key: env[key] for key in (
        "GITHUB_REPOSITORY", "GITHUB_REF", "GITHUB_EVENT_NAME", "GITHUB_RUN_ATTEMPT",
        "GITHUB_WORKFLOW_REF", "GITHUB_SHA", "GITHUB_RUN_ID"
    )}


def find_hithink_root(download_root: Path) -> Path:
    matches = list(download_root.rglob("capture/report.json"))
    require(len(matches) == 1, "UNIQUE_HITHINK_REPORT_REQUIRED")
    return matches[0].parent.parent


def validate_artifact_metadata(path: Path) -> dict[str, Any]:
    value = load_json(path)
    require(value.get("id") == HITHINK_ARTIFACT_ID, "HITHINK_ARTIFACT_ID_MISMATCH")
    require(value.get("name") == HITHINK_ARTIFACT_NAME, "HITHINK_ARTIFACT_NAME_MISMATCH")
    require(value.get("size_in_bytes") == HITHINK_ARTIFACT_BYTES, "HITHINK_ARTIFACT_SIZE_MISMATCH")
    require(value.get("expired") is False, "HITHINK_ARTIFACT_EXPIRED")
    require(value.get("digest") == "sha256:" + HITHINK_ARTIFACT_SHA256, "HITHINK_ARTIFACT_DIGEST_MISMATCH")
    workflow_run = value.get("workflow_run") or {}
    require(workflow_run.get("id") == HITHINK_RUN_ID, "HITHINK_ARTIFACT_RUN_MISMATCH")
    return {
        "id": value["id"],
        "name": value["name"],
        "bytes": value["size_in_bytes"],
        "digest": value["digest"],
        "run_id": workflow_run["id"],
    }


def load_hithink_points(hithink_root: Path) -> tuple[dict[str, dict[str, dict[str, Decimal]]], dict[str, Any]]:
    report_path = hithink_root / "capture" / "report.json"
    report = load_json(report_path)
    claimed = report.pop("report_hash", None)
    require(isinstance(claimed, str) and claimed == canonical_hash(report), "HITHINK_REPORT_HASH_MISMATCH")
    require(report.get("format") == "sector-gap-20260911-v1", "WRONG_HITHINK_RECOVERY_FORMAT")
    require(report.get("status") == "FAILED_CLOSED", "HITHINK_SOURCE_NOT_RETAINED_FAILURE")
    require(report.get("technical_retries") == 0, "HITHINK_SOURCE_RETRY_SEMANTICS_CHANGED")
    binding = report.get("binding") or {}
    workflow = binding.get("workflow") or {}
    require(str(workflow.get("GITHUB_RUN_ID")) == str(HITHINK_RUN_ID), "HITHINK_SOURCE_RUN_MISMATCH")
    require(all(report.get(key) == value for key, value in {
        "production_state_writes": 0,
        "events_created": 0,
        "restore_authority": False,
    }.items()), "HITHINK_SOURCE_AUTHORITY_CHANGED")

    requests = report.get("requests")
    require(isinstance(requests, list), "HITHINK_REQUEST_LEDGER_MISSING")
    calendar_rows = [row for row in requests if row.get("path") == hithink_http.HITHINK_CALENDAR_PATH]
    require(len(calendar_rows) == 1 and calendar_rows[0].get("response_file"), "HITHINK_CALENDAR_SOURCE_MISSING")
    calendar = load_json(hithink_root / "capture" / calendar_rows[0]["response_file"])
    sessions = normalize_hithink_calendar(calendar)
    observed_at = datetime.fromisoformat(str(report["observed_at"]))

    result: dict[str, dict[str, dict[str, Decimal]]] = {}
    source_rows: dict[str, Any] = {}
    for code in CODES:
        rows = [row for row in requests if row.get("path") == hithink_index_http.HITHINK_INDEX_HISTORY_PATH
                and (row.get("params") or {}).get("thscode") == code]
        require(len(rows) == 1 and rows[0].get("response_file") and not rows[0].get("error_type"),
                f"HITHINK_SUCCESS_SOURCE_MISSING:{code}")
        response_path = hithink_root / "capture" / rows[0]["response_file"]
        raw = response_path.read_bytes()
        expected_file = (report.get("files") or {}).get(rows[0]["response_file"])
        require(expected_file and expected_file.get("bytes") == len(raw)
                and expected_file.get("sha256") == sha256_bytes(raw), f"HITHINK_FILE_HASH_MISMATCH:{code}")
        history = normalize_hithink_completed_index_history(
            json.loads(raw), thscode=code, sessions=sessions, observed_at=observed_at
        )
        by_date = {point.as_of.date().isoformat(): point for point in history.points}
        require(all(day in by_date for day in TARGET_DATES), f"HITHINK_TARGET_DATE_MISSING:{code}")
        result[code] = {
            day: {
                "close": by_date[day].close,
                "volume": by_date[day].volume,
                "turnover": by_date[day].turnover,
            }
            for day in TARGET_DATES
        }
        source_rows[code] = {
            "request": rows[0],
            "response_file": rows[0]["response_file"],
            "response_sha256": sha256_bytes(raw),
            "response_bytes": len(raw),
        }
    source = {
        "run_id": HITHINK_RUN_ID,
        "artifact_id": HITHINK_ARTIFACT_ID,
        "report_sha256": sha256_bytes(report_path.read_bytes()),
        "report_status": report["status"],
        "observed_at": report["observed_at"],
        "rows": source_rows,
    }
    return result, source


def build_akshare_cookie() -> str:
    from akshare.stock_feature.stock_board_industry_ths import _get_file_content_ths
    import py_mini_racer

    js = py_mini_racer.MiniRacer()
    js.eval(_get_file_content_ths("ths.js"))
    value = str(js.call("v")).strip()
    require(value, "AKSHARE_COOKIE_EMPTY")
    return value


def default_demjson_decoder(text: str) -> Any:
    from akshare.utils import demjson

    return demjson.decode(text)


def normalize_ths_text(
    text: str,
    *,
    code: str,
    decoder: Callable[[str], Any] = default_demjson_decoder,
) -> tuple[dict[str, dict[str, Decimal]], dict[str, Any]]:
    bare = code.removesuffix(".TI")
    require(re.fullmatch(r"(?:881|884)\d{3}", bare) is not None, "INVALID_PROBE_CODE")
    start = text.find("{")
    end = text.rfind("}")
    require(start > 0 and end > start, f"THS_WRAPPER_MISSING:{code}")
    prefix = text[:start]
    suffix = text[end + 1 :]
    require(f"bk_{bare}" in prefix, f"THS_IDENTITY_WRAPPER_MISMATCH:{code}")
    payload = decoder(text[start : end + 1])
    require(isinstance(payload, Mapping), f"THS_PAYLOAD_NOT_OBJECT:{code}")
    data = payload.get("data")
    require(isinstance(data, str) and data.strip(), f"THS_DATA_MISSING:{code}")

    rows: dict[str, dict[str, Decimal]] = {}
    row_widths: set[int] = set()
    for row in data.split(";"):
        if not row:
            continue
        columns = row.split(",")
        row_widths.add(len(columns))
        require(len(columns) in {11, 12}, f"THS_FIELD_WIDTH_MISMATCH:{code}")
        date_raw = columns[0].strip()
        if not re.fullmatch(r"\d{8}", date_raw):
            raise ProbeError(f"THS_DATE_INVALID:{code}")
        day = datetime.strptime(date_raw, "%Y%m%d").date().isoformat()
        require(day not in rows, f"THS_DUPLICATE_DATE:{code}:{day}")
        rows[day] = {
            "close": decimal_value(columns[4], field="close", positive=True),
            "volume": decimal_value(columns[5], field="volume"),
            "turnover": decimal_value(columns[6], field="turnover"),
        }
    require(all(day in rows for day in TARGET_DATES), f"THS_TARGET_DATE_MISSING:{code}")
    return {day: rows[day] for day in TARGET_DATES}, {
        "wrapper_prefix": prefix,
        "wrapper_suffix": suffix,
        "row_widths": sorted(row_widths),
        "payload_name": payload.get("name"),
        "payload_total": payload.get("total"),
    }


def compare_points(
    hithink: Mapping[str, Mapping[str, Mapping[str, Decimal]]],
    ths: Mapping[str, Mapping[str, Mapping[str, Decimal]]],
) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    exact = True
    for code in CODES:
        for day in TARGET_DATES:
            for field in FIELDS:
                left = hithink[code][day][field]
                right = ths[code][day][field]
                matched = left == right
                exact = exact and matched
                rows.append({
                    "thscode": code,
                    "date": day,
                    "field": field,
                    "hithink": decimal_text(left),
                    "ths_public": decimal_text(right),
                    "exact_match": matched,
                })
    return rows, exact


def capture(root: Path, env: Mapping[str, str]) -> dict[str, Any]:
    identity = invocation(env)
    out = root / "output"
    out.mkdir(parents=True, exist_ok=False)
    artifact = validate_artifact_metadata(root / "metadata" / "source-artifact.json")
    hithink_root = find_hithink_root(root / "hithink")
    hithink, hithink_source = load_hithink_points(hithink_root)

    report: dict[str, Any] = {
        "probe_id": PROBE_ID,
        "status": "RECORDING",
        "workflow": identity,
        "reuse_decision": "THIN_ADAPTER",
        "akshare": {
            "version": AKSHARE_VERSION,
            "source_commit": AKSHARE_COMMIT,
            "reused_components": ["ths.js cookie generation", "akshare.utils.demjson"],
        },
        "hithink_artifact": artifact,
        "hithink_source": hithink_source,
        "codes": list(CODES),
        "dates": list(TARGET_DATES),
        "fields": list(FIELDS),
        "public_request_max": PUBLIC_REQUEST_MAX,
        "technical_retries": 0,
        "requests": [],
        "files": {},
        **AUTHORITY,
    }
    write_json(out / "report.json", {**report, "report_hash": canonical_hash(report)})

    ths_values: dict[str, dict[str, dict[str, Decimal]]] = {}
    normalized_for_file: dict[str, Any] = {}
    cookie = build_akshare_cookie()

    import akshare
    import requests

    require(getattr(akshare, "__version__", None) == AKSHARE_VERSION, "AKSHARE_VERSION_MISMATCH")
    session = requests.Session()
    for scheme in ("https://", "http://"):
        require(session.get_adapter(scheme).max_retries.total == 0, "REQUESTS_RETRY_ADAPTER_CHANGED")

    for index, code in enumerate(CODES, start=1):
        require(len(report["requests"]) < PUBLIC_REQUEST_MAX, "PUBLIC_REQUEST_LIMIT_REACHED")
        bare = code[:-3]
        url = THS_URL.format(code=bare)
        row: dict[str, Any] = {
            "request_index": index,
            "thscode": code,
            "url": url,
            "status_code": None,
            "raw_file": None,
            "error": None,
        }
        report["requests"].append(row)
        try:
            response = session.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
                    "Referer": "http://q.10jqka.com.cn",
                    "Host": "d.10jqka.com.cn",
                    "Cookie": f"v={cookie}",
                },
                timeout=10.0,
                allow_redirects=False,
            )
            row["status_code"] = response.status_code
            raw = response.content
            raw_name = f"raw/{bare}-2026.js"
            raw_path = out / raw_name
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw)
            row["raw_file"] = raw_name
            report["files"][raw_name] = {"bytes": len(raw), "sha256": sha256_bytes(raw)}
            require(response.status_code == 200, f"THS_HTTP_STATUS:{code}:{response.status_code}")
            require(response.url == url, f"THS_EFFECTIVE_URL_MISMATCH:{code}")
            values, parse_meta = normalize_ths_text(response.text, code=code)
            ths_values[code] = values
            normalized_for_file[code] = {
                "dates": {
                    day: {field: decimal_text(values[day][field]) for field in FIELDS}
                    for day in TARGET_DATES
                },
                "parse": parse_meta,
                "url": url,
            }
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}:{str(exc)[:400]}"
        finally:
            write_json(out / "report.json", {**report, "report_hash": canonical_hash(report)})

    request_count_ok = len(report["requests"]) == len(CODES) == PUBLIC_REQUEST_MAX
    all_codes_parsed = set(ths_values) == set(CODES)
    comparison_rows: list[dict[str, Any]] = []
    exact_match = False
    if all_codes_parsed:
        comparison_rows, exact_match = compare_points(hithink, ths_values)

    normalized = {
        "probe_id": PROBE_ID,
        "codes": normalized_for_file,
        "public_request_count": len(report["requests"]),
        "public_request_max": PUBLIC_REQUEST_MAX,
        "technical_retries": 0,
        **AUTHORITY,
    }
    write_json(out / "normalized.json", {**normalized, "normalization_hash": canonical_hash(normalized)})
    comparison = {
        "probe_id": PROBE_ID,
        "status": "EXACT_MATCH" if request_count_ok and all_codes_parsed and exact_match else "FAILED_CLOSED",
        "comparison_rows": comparison_rows,
        "expected_comparison_count": len(CODES) * len(TARGET_DATES) * len(FIELDS),
        "actual_comparison_count": len(comparison_rows),
        "exact_match": bool(request_count_ok and all_codes_parsed and exact_match),
        "source_identity_qualification_only": True,
        "automatic_expansion_authority": False,
        "checkpoint_promotion_authority": False,
        **AUTHORITY,
    }
    write_json(out / "comparison.json", {**comparison, "comparison_hash": canonical_hash(comparison)})
    for name in ("normalized.json", "comparison.json"):
        raw = (out / name).read_bytes()
        report["files"][name] = {"bytes": len(raw), "sha256": sha256_bytes(raw)}
    report["status"] = comparison["status"]
    report["public_request_count"] = len(report["requests"])
    report["exact_match"] = comparison["exact_match"]
    report["comparison_hash"] = canonical_hash(comparison)
    write_json(out / "report.json", {**report, "report_hash": canonical_hash(report)})
    return report


def verify(root: Path) -> dict[str, Any]:
    out = root / "output"
    report = load_json(out / "report.json")
    claimed_report_hash = report.pop("report_hash")
    require(claimed_report_hash == canonical_hash(report), "REPORT_HASH_MISMATCH")
    require(report["probe_id"] == PROBE_ID, "PROBE_ID_MISMATCH")
    require(report["codes"] == list(CODES) and report["dates"] == list(TARGET_DATES)
            and report["fields"] == list(FIELDS), "PROBE_SCOPE_CHANGED")
    require(report["public_request_max"] == PUBLIC_REQUEST_MAX
            and report["technical_retries"] == 0, "REQUEST_BUDGET_CHANGED")
    require(len(report["requests"]) <= PUBLIC_REQUEST_MAX, "PUBLIC_REQUEST_LIMIT_EXCEEDED")
    require(all(report.get(key) == value for key, value in AUTHORITY.items()), "AUTHORITY_CHANGED")
    for name, metadata in report["files"].items():
        raw = (out / name).read_bytes()
        require(len(raw) == metadata["bytes"] and sha256_bytes(raw) == metadata["sha256"], f"FILE_HASH_MISMATCH:{name}")

    normalized = load_json(out / "normalized.json")
    n_hash = normalized.pop("normalization_hash")
    require(n_hash == canonical_hash(normalized), "NORMALIZATION_HASH_MISMATCH")
    comparison = load_json(out / "comparison.json")
    c_hash = comparison.pop("comparison_hash")
    require(c_hash == canonical_hash(comparison), "COMPARISON_HASH_MISMATCH")
    require(report["comparison_hash"] == c_hash, "REPORT_COMPARISON_BINDING_MISMATCH")
    require(comparison["source_identity_qualification_only"] is True
            and comparison["automatic_expansion_authority"] is False
            and comparison["checkpoint_promotion_authority"] is False, "QUALIFICATION_BOUNDARY_CHANGED")
    proof = {
        "status": "EVIDENCE_VERIFIED",
        "probe_status": report["status"],
        "network_calls": 0,
        "public_request_count": report.get("public_request_count", len(report["requests"])),
        "report_hash": claimed_report_hash,
        "normalization_hash": n_hash,
        "comparison_hash": c_hash,
        "exact_match": comparison["exact_match"],
        **AUTHORITY,
    }
    write_json(out / "verification.json", {**proof, "verification_hash": canonical_hash(proof)})
    return proof


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("capture", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.operation == "capture":
            report = capture(args.root, os.environ)
            print(f"capture: {report['status']}; requests={report.get('public_request_count', len(report['requests']))}")
            return 0 if report["status"] == "EXACT_MATCH" else 2
        proof = verify(args.root)
        print(canonical_json(proof))
        return 0
    except Exception as exc:
        print(f"{args.operation}: FAILED_CLOSED / {type(exc).__name__}: {str(exc)[:500]}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
