"""Single-issuer primary-byte acquisition; not Evidence or Research.

Reuse the existing CNINFO normalization and fixed public Requests session. Never
call the market paths in stock_field_source_study. Verification replays the same
bounded selection against retained response bytes, with no network transport.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from decision_kernel.adapters.cninfo import (
    normalize_cninfo_announcement_page, resolve_cninfo_org_id,
)
from decision_kernel.identity import canonical_hash, canonical_json
from .stock_field_source_study import (
    SYMBOLS, NOTICES, PDF_ORIGIN, PDF_PATH, TZ, MAX_BYTES, _session, _check_response,
)

CODE, SECURITY, ISSUER = "002050", "SZSE:002050", "三花智控"
START, END = "2026-08-01", "2026-09-09"
PAGE_SIZE, MAX_PAGES, MAX_BODIES = 30, 3, 4
MAX_REQUESTS, MAX_TOTAL_BYTES = 1 + MAX_PAGES + MAX_BODIES, 48 * 1024 * 1024
SEMANTICS = "PRIMARY_SOURCE_BYTES_ONLY_NOT_EVIDENCE_RESEARCH_OR_ADMISSION"
LIVE, SYNTHETIC = "PUBLIC_CNINFO_CAPTURE", "SYNTHETIC_TEST_ONLY"
COMPLETE, INCOMPLETE = "SOURCE_PACKAGE_CAPTURED_REVIEW_REQUIRED", "SOURCE_CAPTURE_INCOMPLETE"
AUTHORITY = {"research_authority": "NONE", "human_attention_authority": "NONE",
             "investment_authority": "NONE", "market_requests": 0,
             "market_state_writes": 0, "events_created": 0, "research_budget_used": 0}
FIRST = {"id": "issuer-map", "method": "GET", "url": SYMBOLS, "params": {}}


class CaptureError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def require(ok, code):
    if not ok:
        raise CaptureError(code)


def data(value):
    return (canonical_json(value) + "\n").encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def clock(value):
    out = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    require(isinstance(out, datetime) and out.tzinfo is not None and out.utcoffset() is not None,
            "AWARE_CLOCK_REQUIRED")
    return out.astimezone(timezone.utc)


def utc():
    return datetime.now(timezone.utc)


def unique(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, "DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def obj(raw):
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(CaptureError("NONFINITE_JSON")))
    require(isinstance(value, dict), "SOURCE_OBJECT_REQUIRED")
    return value


def plan():
    return {"schema_version": 1, "issuer": ISSUER, "stock_code": CODE, "security_id": SECURITY,
            "window": {"from": START, "through": END, "timezone": "Asia/Shanghai"},
            "window_meaning": "DATE_FILTER_OBSERVED_AT_CAPTURE_NOT_FUTURE_DAY_COMPLETENESS",
            "page_size": PAGE_SIZE, "max_pages": MAX_PAGES, "max_primary_bodies": MAX_BODIES,
            "max_requests": MAX_REQUESTS, "max_body_bytes": MAX_BYTES,
            "max_total_bytes": MAX_TOTAL_BYTES, "technical_retries": 0,
            "required_classes": ["FORMAL_CURRENT_PERIOD_ACTUALS",
                "RELEVANT_ROBOT_OR_THERMAL_PRIMARY_DISCLOSURE", "SUBSEQUENT_ISSUER_UPDATE_INVENTORY"],
            "formal_report": "2026年半年度报告",
            "ir_title_contains": "投资者关系活动记录表",
            "ir_publication_dates": ["2026-08-27", "2026-08-28"],
            "alternate_primary_routes": [], "semantics": SEMANTICS, **AUTHORITY}


def query(org, number):
    require(isinstance(org, str) and re.fullmatch(r"[A-Za-z0-9]+", org), "ISSUER_ORG_INVALID")
    require(type(number) is int and 1 <= number <= MAX_PAGES, "PAGE_BUDGET_EXCEEDED")
    return {"id": f"inventory-{number}", "method": "POST", "url": NOTICES, "params": {
        "pageNum": str(number), "pageSize": str(PAGE_SIZE), "column": "szse", "tabName": "fulltext",
        "plate": "", "stock": CODE + "," + org, "searchkey": "", "secid": "", "category": "",
        "trade": "", "seDate": START + "~" + END, "sortName": "", "sortType": "", "isHLtitle": "false"}}


def pdf_request(item, ordinal):
    url = item["source_locator"]
    require(isinstance(url, str) and url.startswith(PDF_ORIGIN)
            and PDF_PATH.fullmatch(url[len(PDF_ORIGIN):]) is not None, "ORIGINAL_PDF_LOCATOR_REQUIRED")
    return {"id": f"primary-{ordinal}", "method": "GET", "url": url, "params": {}}


def allowed(spec):
    if spec == FIRST:
        return
    if spec.get("url") == NOTICES:
        try:
            org = spec["params"]["stock"].split(",")[1]
            expected = query(org, int(spec["params"]["pageNum"]))
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise CaptureError("UNREVIEWED_REQUEST") from exc
        require(spec == expected, "UNREVIEWED_REQUEST")
        return
    url = spec.get("url", "")
    require(spec.get("method") == "GET" and spec.get("params") == {}
            and re.fullmatch(r"primary-[1-4]", spec.get("id", "")) is not None
            and url.startswith(PDF_ORIGIN) and PDF_PATH.fullmatch(url[len(PDF_ORIGIN):]) is not None
            and set(spec) == {"id", "method", "url", "params"}, "UNREVIEWED_REQUEST")


@dataclass(frozen=True)
class Response:
    status: int
    content_type: str | None
    body: bytes | None
    error: str | None = None


def public_request(spec):
    """Same public session as source study; add actual MIME/status retention.

    Fixed CNINFO endpoints only. Fresh cookie-free session, no environment
    credentials, authentication, redirects, retries or provider/price requests.
    """
    allowed(spec)
    headers = {"Accept-Encoding": "identity", "User-Agent": "decision-kernel-source-bridge/0",
               "Accept": "application/pdf" if spec["id"].startswith("primary-") else "application/json"}
    with _session() as session:
        require(session.trust_env is False, "CREDENTIAL_FREE_SESSION_REQUIRED")
        require(all(a.max_retries.total == 0 for a in session.adapters.values()), "RETRIES_FORBIDDEN")
        with session.request(spec["method"], spec["url"],
                data=spec["params"] if spec["method"] == "POST" else None,
                headers=headers, timeout=(10, 20), stream=True, allow_redirects=False) as res:
            status, mime = res.status_code, res.headers.get("Content-Type")
            require(type(status) is int and 100 <= status <= 599, "INVALID_HTTP_STATUS")
            if status != 200:
                return Response(status, mime, None, "HTTP_REJECTED")
            try:
                length = _check_response(res)
            except ValueError:
                return Response(status, mime, None, "HTTP_BODY_METADATA_REJECTED")
            if length is not None and length > MAX_BYTES:
                return Response(status, mime, None, "BODY_BYTE_LIMIT")
            chunks, size = [], 0
            for chunk in res.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    return Response(status, mime, None, "BODY_BYTE_LIMIT")
                chunks.append(chunk)
            body = b"".join(chunks)
            if length is not None and length != len(body):
                return Response(status, mime, body, "BODY_LENGTH_MISMATCH")
            return Response(status, mime, body)


def _page(payload, org, number, existing, total, observed_at):
    require(type(payload.get("hasMore")) is bool, "INVENTORY_PAGINATION_UNQUALIFIED")
    rows = payload.get("announcements")
    if rows is None and payload.get("totalAnnouncement") == 0:
        rows = []
    require(isinstance(rows, list) and len(rows) <= PAGE_SIZE, "INVENTORY_PAGE_BOUND")
    require(all(isinstance(r, dict) and r.get("secCode") == CODE and r.get("orgId") == org
                for r in rows), "ANNOUNCEMENT_ISSUER_MISMATCH")
    page = normalize_cninfo_announcement_page(payload, stock_code=CODE, org_id=org)
    require(total is None or page.total_announcement_count == total, "INVENTORY_TOTAL_CHANGED")
    total = page.total_announcement_count
    require(total <= PAGE_SIZE * MAX_PAGES, "INVENTORY_PAGE_BUDGET_EXCEEDED")
    result = []
    for item in page.announcements:
        require(item.announcement_id not in existing, "DUPLICATE_ANNOUNCEMENT_ID")
        existing.add(item.announcement_id)
        require(item.published_at is not None, "PUBLICATION_CLOCK_UNQUALIFIED")
        d = item.published_at.astimezone(TZ).date()
        require(date.fromisoformat(START) <= d <= date.fromisoformat(END), "ANNOUNCEMENT_OUTSIDE_WINDOW")
        require(clock(item.published_at) <= clock(observed_at), "FUTURE_PUBLICATION_CLOCK")
        record = asdict(item)
        record["published_at"] = item.published_at.isoformat()
        record["publication_clock_semantics"] = "CNINFO_REPORTED_TIMESTAMP_NOT_PROOF_OF_INTRADAY_AVAILABILITY"
        record["inventory_page"] = number
        result.append(record)
    count, more = len(existing), payload["hasMore"]
    require(count <= total and (not more or (len(rows) == PAGE_SIZE and count < total)),
            "INVENTORY_COUNT_INCONSISTENT")
    require(more or count == total, "INVENTORY_WINDOW_INCOMPLETE")
    require(not more or number < MAX_PAGES, "INVENTORY_PAGE_BUDGET_EXCEEDED")
    return result, total, more


def collect(get):
    """Deterministic selection; get returns actual or retained (bytes, record)."""
    result = {"issuer_resolution": None, "inventory": [], "inventory_complete": False,
              "inventory_total": None, "inventory_pages": [], "selected": [], "bodies": [],
              "status": INCOMPLETE, "problem": None, **AUTHORITY}
    try:
        raw, rec = get(FIRST)
        symbols = obj(raw)
        org = resolve_cninfo_org_id(symbols, stock_code=CODE)
        matches = [r for r in symbols["stockList"] if r.get("code") == CODE]
        require(len(matches) == 1 and matches[0].get("zwjc") == ISSUER, "ISSUER_NAME_OR_IDENTITY_AMBIGUOUS")
        result["issuer_resolution"] = {"stock_code": CODE, "security_id": SECURITY, "issuer": ISSUER,
            "org_id": org, "request_id": rec["id"], "mapping_sha256": sha(raw)}
        seen, total = set(), None
        for number in range(1, MAX_PAGES + 1):
            raw, rec = get(query(org, number))
            payload = obj(raw)
            rows, total, more = _page(payload, org, number, seen, total, rec["completed_at"])
            result["inventory"].extend(rows)
            result["inventory_total"] = total
            result["inventory_pages"].append({"request_id": rec["id"], "page": number,
                "returned_count": len(rows), "total_count": total, "has_more": more})
            if not more:
                result["inventory_complete"] = True
                break
        formal = [r for r in result["inventory"] if r["title"] in {
            "2026年半年度报告", "三花智控：2026年半年度报告", "三花智控:2026年半年度报告"}]
        require(len(formal) == 1, "FORMAL_REPORT_MISSING_OR_AMBIGUOUS")
        updates = [r for r in result["inventory"] if "投资者关系活动记录表" in r["title"]
            and clock(r["published_at"]).astimezone(TZ).date().isoformat() in plan()["ir_publication_dates"]]
        require(len(updates) <= 1, "RELEVANT_IR_AMBIGUOUS")
        selected = [("FORMAL_CURRENT_PERIOD_ACTUALS", formal[0])]
        if updates:
            selected.append(("RELEVANT_ROBOT_OR_THERMAL_PRIMARY_DISCLOSURE", updates[0]))
        result["selected"] = [{"source_class": c, **r} for c, r in selected]
        require(len(selected) <= MAX_BODIES, "PRIMARY_BODY_BUDGET_EXCEEDED")
        for number, (source_class, item) in enumerate(selected, 1):
            raw, rec = get(pdf_request(item, number))
            require(raw.startswith(b"%PDF-"), "PDF_CONTAINER_REQUIRED")
            mime = (rec["content_type"] or "").split(";")[0].strip().lower()
            require(mime in {"application/pdf", "application/octet-stream"}, "PDF_CONTENT_TYPE_UNQUALIFIED")
            result["bodies"].append({"source_class": source_class, "source_identity": {
                "stock_code": CODE, "security_id": SECURITY, "org_id": org,
                "announcement_id": item["announcement_id"], "title": item["title"]},
                "original_url": item["source_locator"], "published_at": item["published_at"],
                "publication_clock_semantics": item["publication_clock_semantics"],
                "capture_started_at": rec["started_at"], "captured_at": rec["completed_at"],
                "http_status": rec["http_status"], "content_type": rec["content_type"],
                "request_id": rec["id"], **rec["body"],
                "qualification": "RETAINED_PDF_BYTES_NOT_SEMANTIC_SOURCE_COMPLETENESS"})
        require(bool(updates), "RELEVANT_IR_MISSING_FROM_BOUNDED_INVENTORY")
        result["status"] = COMPLETE
    except CaptureError as exc:
        result["problem"] = exc.code
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        result["problem"] = "SOURCE_NORMALIZATION_REJECTED: " + type(exc).__name__
    return result


def _safe(root):
    require(not any(p.is_symlink() for p in (root, *root.parents)), "SYMLINK_FORBIDDEN")
    require(not {"decision-state", "research_cases", "current_state", "decisions"}.intersection(root.absolute().parts),
            "ISOLATED_READING_DIRECTORY_REQUIRED")


def _check_record(rec, *, previous, index, total_bytes, raw):
    require(rec["id"] == index and clock(rec["started_at"]) >= previous
            and clock(rec["completed_at"]) >= clock(rec["started_at"]), "CAPTURE_CLOCK_OR_ORDER_INVALID")
    require(rec["http_status"] is None or (type(rec["http_status"]) is int and 100 <= rec["http_status"] <= 599),
            "INVALID_HTTP_STATUS")
    require(rec["content_type"] is None or (isinstance(rec["content_type"], str)
            and len(rec["content_type"]) <= 2048 and "\r" not in rec["content_type"] and "\n" not in rec["content_type"]),
            "CONTENT_TYPE_INVALID")
    body = rec["body"]
    if body is not None:
        expected_name = f"{index:03d}." + ("pdf" if rec["spec"]["id"].startswith("primary-") else "json")
        require(body["path"] == expected_name and 0 < len(raw) <= MAX_BYTES
                and body == {"path": expected_name, "bytes": len(raw), "sha256": sha(raw)}, "RETAINED_BODY_MISMATCH")
        total_bytes += len(raw)
    else:
        require(raw is None, "UNINDEXED_BODY")
    require(total_bytes <= MAX_TOTAL_BYTES and index <= MAX_REQUESTS, "CAPTURE_BYTE_OR_REQUEST_BUDGET")
    if rec["error"] is not None:
        require(body is None or rec["http_status"] == 200, "FAILED_HTTP_BODY_NOT_ACCEPTED")
        raise CaptureError(rec["error"])
    require(rec["http_status"] == 200 and body is not None, "HTTP_OR_BODY_UNAVAILABLE")
    return total_bytes


def capture(root: Path, *, request=None, now=utc):
    _safe(root)
    require(not root.exists(), "NEW_SINGLE_CAPTURE_DIRECTORY_REQUIRED")
    provenance = LIVE if request is None else SYNTHETIC
    request = request or public_request
    root.mkdir(parents=True)
    (root / "plan.json").write_bytes(data(plan()))
    started = clock(now()).isoformat()
    previous, total_bytes, records = clock(started), 0, []
    journal = root / "request-journal.jsonl"

    def append(event):
        with journal.open("ab") as stream:
            stream.write(data(event)); stream.flush()

    def get(spec):
        nonlocal previous, total_bytes
        allowed(spec)
        require(len(records) < MAX_REQUESTS, "REQUEST_BUDGET_EXCEEDED")
        before = clock(now())
        require(before >= previous, "CAPTURE_CLOCK_OR_ORDER_INVALID")
        rec = {"id": len(records) + 1, "spec": spec, "started_at": before.isoformat(),
               "completed_at": None, "http_status": None, "content_type": None, "body": None, "error": None}
        append({"phase": "REQUEST", "id": rec["id"], "spec": spec, "started_at": rec["started_at"]})
        raw = None
        try:
            response = request(spec)
            rec.update(http_status=response.status, content_type=response.content_type, error=response.error)
            raw = response.body
            if raw is not None:
                require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BYTES, "BODY_BYTE_LIMIT")
                require(total_bytes + len(raw) <= MAX_TOTAL_BYTES, "TOTAL_BYTE_LIMIT")
                name = f"{rec['id']:03d}." + ("pdf" if spec["id"].startswith("primary-") else "json")
                with (root / name).open("xb") as stream:
                    stream.write(raw)
                rec["body"] = {"path": name, "bytes": len(raw), "sha256": sha(raw)}
        except Exception as exc:
            # Keep actual exception TYPE, never source error text, cookies or credentials.
            rec["error"] = exc.code if isinstance(exc, CaptureError) else "TRANSPORT_EXCEPTION: " + type(exc).__name__
            raw = None
        rec["completed_at"] = clock(now()).isoformat()
        records.append(rec)
        append({"phase": "RESPONSE", **rec})
        total_bytes = _check_record(rec, previous=previous, index=len(records), total_bytes=total_bytes, raw=raw)
        previous = clock(rec["completed_at"])
        return raw, rec

    outcome = collect(get)
    finished = clock(now()).isoformat()
    value = {"schema_version": 1, "semantics": SEMANTICS, "provenance": provenance,
             "plan_hash": canonical_hash(plan()), "capture_started_at": started, "capture_completed_at": finished,
             "requests": records, "outcome": outcome,
             "journal_sha256": sha(journal.read_bytes()) if journal.exists() else sha(b""),
             "research_cutoff": None, "proof_scope": "CAPTURED_HTTP_RECORDS_NOT_SOURCE_TRUTH_OR_ADMISSION"}
    if not journal.exists():
        journal.write_bytes(b"")
    value["capture_hash"] = canonical_hash(value)
    (root / "capture.json").write_bytes(data(value))
    return value


def verify(root: Path):
    """Recompute plan, request chain, issuer, pagination, selection and outcome offline."""
    _safe(root)
    for file in root.iterdir():
        require(file.is_file() and not file.is_symlink(), "UNEXPECTED_FILE_OR_SYMLINK")
    require((root / "capture.json").stat().st_size <= 2 * 1024 * 1024, "MANIFEST_BYTE_LIMIT")
    value = obj((root / "capture.json").read_bytes())
    require((root / "plan.json").read_bytes() == data(plan()) and value["plan_hash"] == canonical_hash(plan()),
            "PLAN_MISMATCH")
    require(value["schema_version"] == 1 and value["semantics"] == SEMANTICS
            and value["provenance"] in {LIVE, SYNTHETIC} and value["research_cutoff"] is None
            and value["proof_scope"] == "CAPTURED_HTTP_RECORDS_NOT_SOURCE_TRUTH_OR_ADMISSION"
            and value["capture_hash"] == canonical_hash({k: v for k, v in value.items() if k != "capture_hash"}),
            "CAPTURE_HASH_OR_IDENTITY_MISMATCH")
    require((root / "request-journal.jsonl").stat().st_size <= 2 * 1024 * 1024, "JOURNAL_BYTE_LIMIT")
    records = value["requests"]
    require(isinstance(records, list) and 1 <= len(records) <= MAX_REQUESTS, "REQUEST_BUDGET_EXCEEDED")
    expected_journal, expected_files = b"", {"plan.json", "capture.json", "request-journal.jsonl"}
    retained = {}
    for rec in records:
        expected_journal += data({"phase": "REQUEST", "id": rec["id"], "spec": rec["spec"], "started_at": rec["started_at"]})
        expected_journal += data({"phase": "RESPONSE", **rec})
        if rec["body"] is not None:
            name = rec["body"]["path"]
            require(isinstance(name, str) and re.fullmatch(r"[0-9]{3}\.(json|pdf)", name) is not None
                    and name not in expected_files, "BODY_PATH_INVALID")
            file = root / name
            require(file.stat().st_size <= MAX_BYTES, "BODY_BYTE_LIMIT")
            retained[name] = file.read_bytes(); expected_files.add(name)
    require({p.name for p in root.iterdir()} == expected_files, "FILE_INVENTORY_MISMATCH")
    require((root / "request-journal.jsonl").read_bytes() == expected_journal
            and value["journal_sha256"] == sha(expected_journal), "ORIGINAL_ACTION_JOURNAL_MISMATCH")
    position, total_bytes, previous = 0, 0, clock(value["capture_started_at"])
    require(clock(value["capture_completed_at"]) >= previous, "CAPTURE_CLOCK_OR_ORDER_INVALID")

    def replay(spec):
        nonlocal position, total_bytes, previous
        require(position < len(records), "REPLAY_MISSING_RESPONSE")
        rec = records[position]; position += 1
        allowed(spec)
        require(rec["spec"] == spec, "EXACT_REQUEST_CHAIN_MISMATCH")
        raw = retained[rec["body"]["path"]] if rec["body"] else None
        require(clock(rec["completed_at"]) <= clock(value["capture_completed_at"]), "CAPTURE_CLOCK_OR_ORDER_INVALID")
        total_bytes = _check_record(rec, previous=previous, index=position, total_bytes=total_bytes, raw=raw)
        previous = clock(rec["completed_at"])
        return raw, rec

    rebuilt = collect(replay)
    require(position == len(records) and rebuilt == value["outcome"], "OFFLINE_SELECTION_OR_OUTCOME_MISMATCH")
    return {"status": "OFFLINE_VERIFICATION_PASS", "capture_status": rebuilt["status"],
            "capture_hash": value["capture_hash"], "network_calls": 0, "research_execution": "NOT_EXECUTED",
            "source_truth_certified": False, "primary_bodies": len(rebuilt["bodies"])}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["capture", "verify"])
    p.add_argument("directory", type=Path)
    a = p.parse_args(argv)
    value = capture(a.directory) if a.command == "capture" else verify(a.directory)
    print(canonical_json(value))
    return 0 if a.command == "verify" or value["outcome"]["status"] == COMPLETE else 2


if __name__ == "__main__":
    raise SystemExit(main())
