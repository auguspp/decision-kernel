#!/usr/bin/env python3
"""One-shot public THS sector-history probe against retained HiThink originals.

Source qualification only. No provider credential, market-state write, candidate event,
Research, or investment authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

PROBE_SCHEMA_VERSION = 1
SEMANTICS = "PUBLIC_THS_HISTORY_CROSS_SOURCE_PROBE_ONLY"
PROBE_CODES = ("881101.TI", "881270.TI", "884001.TI", "884002.TI", "884023.TI")
PROBE_SESSIONS = ("2026-09-09", "2026-09-10")
SOURCE_RUN_ID = 34566950303
SOURCE_ARTIFACT_ID = 10187281705
SOURCE_ARTIFACT_DIGEST = "sha256:aedf5fc5507fa33c00f316be72c14b50962486961ba7199e097d2628205dc60b"
MAX_PUBLIC_REQUESTS = 5
AKSHARE_COMMIT = "8e95744b79ae22326308ccd2b4e62650c5b53c55"
_CODE = re.compile(r"^(?:881|884)\d{3}\.TI$")


class ProbeError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _decimal(value: Any, *, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ProbeError(f"{field} is not numeric") from exc
    if not result.is_finite():
        raise ProbeError(f"{field} is not finite")
    return result


def _session_from_ms(value: Any) -> str:
    try:
        stamp = int(value)
    except (TypeError, ValueError) as exc:
        raise ProbeError("HiThink date_ms is invalid") from exc
    from zoneinfo import ZoneInfo
    return datetime.fromtimestamp(stamp / 1000, tz=ZoneInfo("Asia/Shanghai")).date().isoformat()


def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeError(f"invalid JSON: {path}") from exc
    if not isinstance(value, Mapping):
        raise ProbeError(f"JSON root is not an object: {path}")
    return value


def _find_hithink_file(report: Mapping[str, Any], code: str) -> str:
    matches = [
        row for row in report.get("requests", [])
        if isinstance(row, Mapping)
        and row.get("path") == "/api/a-share-index/prices/historical"
        and isinstance(row.get("params"), Mapping)
        and row["params"].get("thscode") == code
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("response_file"), str):
        raise ProbeError(f"retained HiThink response missing or ambiguous for {code}")
    return str(matches[0]["response_file"])


def load_hithink_reference(source_root: Path) -> dict[str, dict[str, dict[str, str]]]:
    report = _load_json(source_root / "capture" / "report.json")
    binding = report.get("binding")
    if not isinstance(binding, Mapping):
        raise ProbeError("recovery report binding missing")
    workflow = binding.get("workflow")
    if not isinstance(workflow, Mapping) or str(workflow.get("GITHUB_RUN_ID")) != str(SOURCE_RUN_ID):
        raise ProbeError("recovery artifact run identity disagrees")
    if report.get("status") != "FAILED_CLOSED" or report.get("production_state_writes") != 0:
        raise ProbeError("recovery artifact has unexpected authority/status")
    files = report.get("files")
    if not isinstance(files, Mapping):
        raise ProbeError("recovery report file manifest missing")

    result: dict[str, dict[str, dict[str, str]]] = {}
    for code in PROBE_CODES:
        if not _CODE.fullmatch(code):
            raise ProbeError(f"invalid probe identity {code}")
        rel = _find_hithink_file(report, code)
        manifest = files.get(rel)
        if not isinstance(manifest, Mapping):
            raise ProbeError(f"HiThink response not manifested for {code}")
        path = source_root / "capture" / rel
        raw = path.read_bytes()
        if len(raw) != manifest.get("bytes") or _sha256(raw) != manifest.get("sha256"):
            raise ProbeError(f"retained HiThink bytes mismatch for {code}")
        envelope = json.loads(raw)
        data = envelope.get("data") if isinstance(envelope, Mapping) else None
        if not isinstance(data, Mapping) or data.get("thscode") != code or data.get("interval") != "1d":
            raise ProbeError(f"HiThink response identity disagrees for {code}")
        points: dict[str, dict[str, str]] = {}
        items = data.get("item")
        if not isinstance(items, list):
            raise ProbeError(f"HiThink item list missing for {code}")
        for row in items:
            if not isinstance(row, Mapping):
                raise ProbeError(f"HiThink row malformed for {code}")
            session = _session_from_ms(row.get("date_ms"))
            if session in PROBE_SESSIONS:
                points[session] = {
                    "close": str(_decimal(row.get("close_price"), field=f"{code}.close")),
                    "volume": str(_decimal(row.get("volume"), field=f"{code}.volume")),
                    "turnover": str(_decimal(row.get("turnover"), field=f"{code}.turnover")),
                }
        if tuple(sorted(points)) != PROBE_SESSIONS:
            raise ProbeError(f"HiThink probe sessions missing for {code}: {sorted(points)}")
        result[code] = points
    return result


def _parse_date(text: str) -> str:
    value = text.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ProbeError(f"THS row has unsupported date {value!r}")


def parse_ths_year_text(text: str, *, demjson_module: Any) -> dict[str, dict[str, str]]:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ProbeError("THS public response has no object payload")
    try:
        payload = demjson_module.decode(text[start : end + 1])
    except Exception as exc:
        raise ProbeError("THS public response cannot be decoded") from exc
    if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), str):
        raise ProbeError("THS public response has no data string")
    points: dict[str, dict[str, str]] = {}
    for raw_line in payload["data"].split(";"):
        if not raw_line.strip():
            continue
        fields = raw_line.split(",")
        if len(fields) < 7:
            raise ProbeError("THS public history row has fewer than seven fields")
        session = _parse_date(fields[0])
        if session in points:
            raise ProbeError(f"THS public history duplicates {session}")
        points[session] = {
            "close": str(_decimal(fields[4], field=f"{session}.close")),
            "volume": str(_decimal(fields[5], field=f"{session}.volume")),
            "turnover": str(_decimal(fields[6], field=f"{session}.turnover")),
        }
    return points


def compare(reference: Mapping[str, Any], public: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    matches: list[dict[str, str]] = []
    mismatches: list[dict[str, str]] = []
    for code in PROBE_CODES:
        for session in PROBE_SESSIONS:
            for field in ("close", "volume", "turnover"):
                expected = str(reference[code][session][field])
                actual = str(public[code][session][field])
                row = {"thscode": code, "session": session, "field": field, "hithink": expected, "public_ths": actual}
                if Decimal(expected) == Decimal(actual):
                    matches.append(row)
                else:
                    mismatches.append(row)
    return matches, mismatches


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fetch_public(code: str, *, ak_ths: Any, v_code: str) -> tuple[bytes, dict[str, Any]]:
    bare = code.split(".", 1)[0]
    url = f"https://d.10jqka.com.cn/v4/line/bk_{bare}/01/2026.js"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
        "Referer": "http://q.10jqka.com.cn",
        "Host": "d.10jqka.com.cn",
        "Cookie": f"v={v_code}",
    }
    try:
        response = ak_ths.requests.get(url, headers=headers, timeout=15, allow_redirects=False)
    except Exception as exc:
        raise ProbeError(f"public THS request failed for {code}: {type(exc).__name__}") from exc
    raw = bytes(response.content)
    meta = {"thscode": code, "url": url, "status": int(response.status_code), "bytes": len(raw), "sha256": _sha256(raw)}
    return raw, meta


def capture(source_root: Path, output_root: Path) -> int:
    output_root.mkdir(parents=True, exist_ok=False)
    reference = load_hithink_reference(source_root)
    _write_json(output_root / "hithink-reference.json", reference)
    public: dict[str, dict[str, dict[str, str]]] = {}
    requests: list[dict[str, Any]] = []
    error: str | None = None
    try:
        from akshare.stock_feature import stock_board_industry_ths as ak_ths
        js_code = ak_ths.py_mini_racer.MiniRacer()
        js_code.eval(ak_ths._get_file_content_ths("ths.js"))
        v_code = js_code.call("v")
        if not isinstance(v_code, str) or not v_code:
            raise ProbeError("AKShare THS cookie generator returned an invalid token")
        for code in PROBE_CODES:
            if len(requests) >= MAX_PUBLIC_REQUESTS:
                raise ProbeError("public request budget exceeded")
            raw, meta = _fetch_public(code, ak_ths=ak_ths, v_code=v_code)
            requests.append(meta)
            raw_path = output_root / "raw" / f"{code}.js"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(raw)
            if meta["status"] != 200:
                raise ProbeError(f"public THS returned HTTP {meta['status']} for {code}")
            if not raw:
                raise ProbeError(f"public THS returned empty body for {code}")
            points = parse_ths_year_text(raw.decode("utf-8"), demjson_module=ak_ths.demjson)
            selected = {session: points[session] for session in PROBE_SESSIONS if session in points}
            if tuple(sorted(selected)) != PROBE_SESSIONS:
                raise ProbeError(f"public THS probe sessions missing for {code}: {sorted(selected)}")
            public[code] = selected
    except Exception as exc:
        error = " ".join(str(exc).split())[:1000]

    if public:
        _write_json(output_root / "public-ths-normalized.json", public)
    matches: list[dict[str, str]] = []
    mismatches: list[dict[str, str]] = []
    if error is None:
        matches, mismatches = compare(reference, public)
    report = {
        "schema_version": PROBE_SCHEMA_VERSION,
        "semantics": SEMANTICS,
        "status": "MATCHED" if error is None and not mismatches else ("MISMATCH" if error is None else "FAILED_CLOSED"),
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "akshare_commit": AKSHARE_COMMIT,
        "probe_codes": list(PROBE_CODES),
        "probe_sessions": list(PROBE_SESSIONS),
        "public_requests": requests,
        "public_request_count": len(requests),
        "max_public_requests": MAX_PUBLIC_REQUESTS,
        "field_comparisons": len(matches) + len(mismatches),
        "exact_matches": len(matches),
        "mismatches": mismatches,
        "error": error,
        "production_state_writes": 0,
        "events_created": 0,
        "research_authority": "NONE",
        "investment_authority": "NONE",
        "restore_authority": False,
    }
    report["report_hash"] = _sha256(_canonical(report).encode("utf-8"))
    _write_json(output_root / "report.json", report)
    summary = [
        f"## THS public Sector history probe — `{report['status']}`",
        "",
        f"Five exact identities; sessions {', '.join(PROBE_SESSIONS)}; fields close / volume / turnover.",
        "",
        f"Public requests: {report['public_request_count']}/{MAX_PUBLIC_REQUESTS}; exact field matches: {report['exact_matches']}/{report['field_comparisons']}.",
        "",
        "Source qualification only. No production state, events, Research, or investment authority.",
    ]
    if error:
        summary.extend(["", f"Failure: `{error}`"])
    elif mismatches:
        summary.extend(["", f"Mismatches: **{len(mismatches)}**; inspect retained report before any expansion."])
    (output_root / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return 0 if report["status"] == "MATCHED" else 2


def verify(source_root: Path, output_root: Path) -> int:
    report = dict(_load_json(output_root / "report.json"))
    claimed = report.pop("report_hash", None)
    if not isinstance(claimed, str) or _sha256(_canonical(report).encode("utf-8")) != claimed:
        raise ProbeError("probe report hash mismatch")
    reference = load_hithink_reference(source_root)
    stored_reference = _load_json(output_root / "hithink-reference.json")
    if reference != stored_reference:
        raise ProbeError("retained HiThink reference does not rebuild")
    if report["public_request_count"] != len(report["public_requests"]) or report["public_request_count"] > MAX_PUBLIC_REQUESTS:
        raise ProbeError("public request accounting mismatch")
    from akshare.stock_feature import stock_board_industry_ths as ak_ths
    public: dict[str, dict[str, dict[str, str]]] = {}
    for code in PROBE_CODES:
        path = output_root / "raw" / f"{code}.js"
        raw = path.read_bytes()
        meta = [row for row in report["public_requests"] if row["thscode"] == code]
        if len(meta) != 1 or len(raw) != meta[0]["bytes"] or _sha256(raw) != meta[0]["sha256"]:
            raise ProbeError(f"retained public bytes mismatch for {code}")
        points = parse_ths_year_text(raw.decode("utf-8"), demjson_module=ak_ths.demjson)
        selected = {session: points[session] for session in PROBE_SESSIONS if session in points}
        if tuple(sorted(selected)) != PROBE_SESSIONS:
            raise ProbeError(f"offline public sessions missing for {code}")
        public[code] = selected
    stored_public = _load_json(output_root / "public-ths-normalized.json")
    if public != stored_public:
        raise ProbeError("retained public normalization does not rebuild")
    matches, mismatches = compare(reference, public)
    status = "MATCHED" if not mismatches else "MISMATCH"
    if report["status"] != status or report["exact_matches"] != len(matches) or report["mismatches"] != mismatches:
        raise ProbeError("offline comparison disagrees with capture report")
    print(f"offline verify: {status}; matches={len(matches)}; mismatches={len(mismatches)}; network=0")
    return 0 if status == "MATCHED" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("capture", "verify"))
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        return capture(args.source_root, args.output_root) if args.mode == "capture" else verify(args.source_root, args.output_root)
    except ProbeError as exc:
        print(f"probe: FAILED_CLOSED / {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
