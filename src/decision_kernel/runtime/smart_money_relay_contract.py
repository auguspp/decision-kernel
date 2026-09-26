"""Interpret retained Relay tables, without requests, credentials or routing.

This finite consumer contract does not replace the HTTP client's receipt. Source
success, a readable page, source coverage and an investment inference differ.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import re

from . import smart_money_sources as s

REVISION = "relay-table-interpretation-1"
# Official interface limits are conservative warning boundaries for this relay,
# not proof that its actual multi-upstream route has the same pagination rules.
CONTRACTS = {
    "hm_list": (1000, ("name", "orgs"), None),
    "hm_detail": (2000, ("trade_date", "ts_code", "hm_name", "hm_orgs"), "trade_date"),
    "report_rc": (3000, ("report_date", "ts_code", "org_name", "quarter"), "report_date"),
    "top_list": (10000, ("trade_date", "ts_code", "reason"), "trade_date"),
    "top_inst": (10000, ("trade_date", "ts_code", "exalter", "side", "reason"), "trade_date"),
}
SOURCE_KEYS = ("provider", "source", "data_source")


def _day(value):
    if isinstance(value, str) and re.fullmatch(r"\d{8}", value):
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    s.require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value),
              "RELAY_ROW_DATE_FORMAT")
    return date.fromisoformat(value)


def qualify(body: dict, spec: dict, *, received_at: str) -> dict:
    """Keep raw values; qualify identity/date separately, never certify all rows."""
    api, params = spec["api"], spec["params"]
    s.require(api in CONTRACTS and isinstance(body, dict), "RELAY_TABLE_SCOPE")
    # Recheck business success independently of the historical client's label.
    s.require(type(body.get("code")) is int and body["code"] == 0
              and ("ok" not in body or body["ok"] is True)
              and body.get("error") in (None, ""), "RELAY_BUSINESS_NOT_SUCCESS")
    s.require(body.get("api_name") in (None, api), "RELAY_RESPONSE_API_MISMATCH")
    data = body.get("data")
    s.require(isinstance(data, dict), "RELAY_TABLE_ENVELOPE")
    fields, items = data.get("fields"), data.get("items")
    s.require(isinstance(fields, list) and 0 < len(fields) <= 512
              and all(isinstance(f, str) and 0 < len(f) <= 128 for f in fields),
              "RELAY_TABLE_FIELDS")
    s.require(len(set(fields)) == len(fields), "RELAY_DUPLICATE_FIELDS")
    s.require(isinstance(items, list) and len(items) <= 10000, "RELAY_TABLE_ROWS")
    s.require(all(isinstance(row, list) and len(row) == len(fields) for row in items),
              "RELAY_TABLE_ROW_SHAPE")
    # Existing canonical JSON turns exact Decimal values into strings. Do not
    # round via float, invent currency, or discard unexpected source columns.
    pending = [items, {k: body[k] for k in SOURCE_KEYS if k in body},
               {k: data[k] for k in SOURCE_KEYS if k in data}]
    while pending:
        value = pending.pop()
        if isinstance(value, Decimal):
            s.require(value.is_finite() and len(value.as_tuple().digits)
                      + abs(value.as_tuple().exponent) <= 256, "RELAY_DECIMAL_EXPANSION_BOUND")
        elif isinstance(value, dict):
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    rows = json.loads(s.encoded([dict(zip(fields, row, strict=True)) for row in items]))
    count = body.get("count")
    s.require(count is None or type(count) is int and count >= len(rows),
              "RELAY_COUNT_CONTRADICTION")
    cap, required, date_field = CONTRACTS[api]
    limit = int(params["limit"])
    s.require(limit > 0, "RELAY_TABLE_LIMIT")
    missing = sorted(set(required) - set(fields))
    issues = ([{"code": "MISSING_EXPECTED_FIELDS", "fields": missing}] if missing else [])
    if len(rows) >= min(cap, limit):
        issues.append({"code": "POSSIBLE_TRUNCATION", "boundary": min(cap, limit)})
    if count is not None and count > len(rows):
        issues.append({"code": "COUNT_EXCEEDS_SAVED_ROWS", "reported_count": count})
    allowed_day = _day(params[date_field]) if date_field else None
    received_day = s.clock(received_at).astimezone(s.ZONE).date()
    valid_indexes, row_gaps, field_gaps = [], [], []
    for index, row in enumerate(rows):
        problems = []
        if not missing:
            if date_field:
                try:
                    day = _day(row[date_field])
                    if day != allowed_day:
                        problems.append("REQUEST_DATE_MISMATCH")
                    if day > received_day:
                        problems.append("FUTURE_DISCLOSURE_DATE")
                except (ValueError, TypeError):
                    problems.append("ROW_DATE_INVALID")
            if "ts_code" in required and (not isinstance(row["ts_code"], str)
                    or re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", row["ts_code"]) is None):
                problems.append("SECURITY_IDENTITY_UNQUALIFIED")
            for key in set(required) - {"ts_code", date_field, "orgs", "hm_orgs", "side"}:
                if not isinstance(row[key], str) or not row[key].strip():
                    problems.append("REQUIRED_VALUE_MISSING")
                    break
            if api == "top_inst" and (type(row["side"]) not in (str, int)
                                      or str(row["side"]) not in {"0", "1"}):
                field_gaps.append({"row_index": index, "field": "side",
                                   "code": "SIDE_NOT_ESTABLISHED"})
        if missing or problems:
            row_gaps.append({"row_index": index, "codes": problems or ["MISSING_EXPECTED_FIELDS"]})
        else:
            valid_indexes.append(index)
    if field_gaps:
        issues.append({"code": "FIELD_GAPS", "count": len(field_gaps)})
    if row_gaps:
        issues.append({"code": "UNQUALIFIED_ROWS", "count": len(row_gaps)})
    claims = []
    for location, item in (("envelope", body), ("data", data)):
        for key in SOURCE_KEYS:
            if item.get(key) not in (None, ""):
                claims.append({"location": location, "field": key,
                               "value": json.loads(s.encoded(item[key]))})
    return {"interpretation_revision": REVISION,
            "qualification": "WITH_EXPLICIT_GAPS" if issues else "BOUNDED_PAGE_QUALIFIED",
            "rows": rows, "row_count": len(rows), "qualified_row_indexes": valid_indexes,
            "qualified_row_count": len(valid_indexes), "row_gaps": row_gaps, "field_gaps": field_gaps,
            "issues": issues, "source_claims": claims,
            "source_fields_present": sorted(set(fields) & set(SOURCE_KEYS)),
            "coverage": {"status": "EMPTY_RESPONSE_NOT_NO_ACTIVITY" if not rows
                         else "BOUNDED_RESPONSE_NOT_COMPLETE_MARKET",
                         "requested_limit": limit, "official_limit_warning": cap,
                         "reported_count": count, "complete_market": False},
            "number_representation": "EXACT_JSON_DECIMALS_AS_STRINGS_RAW_BYTES_RETAINED",
            "identity_limit": "VENDOR_LABELS_NOT_VERIFIED_PEOPLE_OR_EFFECTIVE_DATES",
            "forecast_limit": "REPORT_DATE_NOT_TARGET_QUARTER_OR_PROVIDER_UPDATE_TIME"}
