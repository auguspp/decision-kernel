from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from decision_kernel.identity import canonical_hash, canonical_json


TZ = ZoneInfo("Asia/Shanghai")
MOA = "MOA_LIVESTOCK_WEEKLY"
SPB = "SPB_EXPRESS_MONTHLY"
SEMANTICS = "BOUNDED_PUBLIC_RELEASE_STUDY_NOT_A_PROSPECTIVE_MARKET_EVENT"
AUTHORITY = {"fundamental_state_authority": "NONE", "research_authority": "NONE",
             "human_attention_authority": "NONE", "investment_authority": "NONE"}
SOURCE_FIELDS = {"source_kind", "source_url", "title", "published_date",
                 "published_time_precision", "captured_at", "capture_method", "excerpt"}
MAX_EXCERPT_BYTES = 32 * 1024


def _aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("economic study clock must be timezone-aware")
    return value


def _one(pattern: str, text: str, label: str):
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one exact source statement; missing or ambiguous")
    return matches[0]


def _positive(value: str) -> Decimal:
    number = Decimal(value)
    if not number.is_finite() or number <= 0:
        raise ValueError("economic observation must be a positive reported value")
    return number


def qualify_release_excerpt(source: Mapping[str, Any]) -> dict[str, Any]:
    """Parse two exact public-release templates, not arbitrary web or LLM claims.

    Input is an explicitly reviewed excerpt, not a full-page or original HTTP-byte
    acquisition claim. The source URL and extraction hash do not authenticate it.
    """
    if not isinstance(source, Mapping) or set(source) != SOURCE_FIELDS:
        raise ValueError("economic source fields disagree")
    if any(not isinstance(value, str) or not value for value in source.values()):
        raise ValueError("economic source metadata must be nonempty strings")
    if source["capture_method"] not in {"REVIEWED_OFFICIAL_WEB_EXCERPT", "SYNTHETIC_TEST_ONLY"}:
        raise ValueError("unsupported excerpt provenance")
    if source["published_time_precision"] != "DATE_ONLY":
        raise ValueError("do not invent an intraday publication timestamp")
    published = date.fromisoformat(source["published_date"])
    if published.isoformat() != source["published_date"]:
        raise ValueError("publication date must use ISO date form")
    captured = _aware(datetime.fromisoformat(source["captured_at"].replace("Z", "+00:00")))
    if captured.astimezone(TZ).date() < published:
        raise ValueError("capture cannot precede public release")
    parsed = urlsplit(source["source_url"])
    if parsed.scheme != "https" or parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port:
        raise ValueError("source must be an exact credential-free official HTTPS page")
    kind = source["source_kind"]
    if kind == MOA:
        valid_url = parsed.hostname == "xmsyj.moa.gov.cn" and re.fullmatch(r"/jcyj/[0-9]{6}/t[0-9]{8}_[0-9]+\.htm", parsed.path)
    elif kind == SPB:
        valid_url = parsed.hostname == "www.spb.gov.cn" and re.fullmatch(r"/gjyzj/c100015/c100016/[0-9]{6}/[0-9a-f]{32}\.shtml", parsed.path)
    else:
        raise ValueError("unsupported economic node source")
    if not valid_url:
        raise ValueError("source page is outside the bounded official-source contract")
    text = source["excerpt"]
    if len(text.encode("utf-8")) > MAX_EXCERPT_BYTES or source["title"] not in text:
        raise ValueError("excerpt is oversized or lacks the declared title")
    compact = re.sub(r"[ \t\u3000]+", "", text)
    date_match = _one(r"日期[：:]([0-9]{4}-[0-9]{2}-[0-9]{2})", compact, "publication date")
    if date_match[1] != source["published_date"]:
        raise ValueError("declared and excerpt publication dates disagree")

    def metric(metric_id, label, pattern, unit):
        match = _one(pattern, compact, metric_id)
        return {"metric_id": metric_id, "label": label, "value": _positive(match[1]),
                "unit": unit, "source_statement": match[0], "value_semantics": "SOURCE_REPORTED_ROUNDED_VALUE"}

    derived = []
    if kind == MOA:
        title = re.fullmatch(r"([0-9]{1,2})月第[1-5]周畜产品和饲料集贸市场价格情况", source["title"])
        if not title or "全国500个县集贸市场和采集点" not in compact:
            raise ValueError("livestock release title or monitoring scope disagrees")
        collected = _one(r"采集日为([0-9]{1,2})月([0-9]{1,2})日", compact, "collection date")
        period_start = period_end = date(published.year, int(collected[1]), int(collected[2]))
        if int(title[1]) != period_end.month:
            raise ValueError("livestock title month disagrees with collection date")
        metrics = [
            metric("live_hog_price", "全国生猪平均价格", r"全国生猪平均价格([0-9]+(?:\.[0-9]+)?)元/公斤", "CNY_PER_KG"),
            metric("corn_price", "全国玉米平均价格", r"全国玉米平均价格([0-9]+(?:\.[0-9]+)?)元/公斤", "CNY_PER_KG"),
            metric("fattening_pig_feed_price", "育肥猪配合饲料平均价格", r"育肥猪配合饲料平均价格([0-9]+(?:\.[0-9]+)?)元/公斤", "CNY_PER_KG"),
        ]
        node_id, period_kind = "cn.livestock.price_feed", "COLLECTION_DATE"
        scope = "NATIONAL_500_COUNTY_MARKETS_AND_COLLECTION_POINTS"
        limitation = "Published price observations are not producer profit, farm cost, margin or company-specific economics."
    else:
        title = re.fullmatch(r"国家邮政局公布([0-9]{4})年(?:1-([0-9]{1,2})月|上半年)邮政行业运行情况", source["title"])
        if not title:
            raise ValueError("express release title disagrees")
        month = int(title[2]) if title[2] else 6
        year = int(title[1])
        period_start = date(year, month, 1)
        period_end = date(year, month, calendar.monthrange(year, month)[1])
        prefix = rf"(?:^|\n){month}月份，"
        revenue = metric("express_revenue", "全国当月快递业务收入",
            prefix + r"邮政行业业务收入[^\n]*?其中[，,]快递业务收入完成([0-9]+(?:\.[0-9]+)?)亿元", "CNY_100_MILLION")
        volume = metric("express_volume", "全国当月快递业务量",
            prefix + r"邮政行业寄递业务量[^\n]*?其中[，,]快递业务量完成([0-9]+(?:\.[0-9]+)?)亿件", "PARCELS_100_MILLION")
        metrics = [revenue, volume]
        with localcontext() as arithmetic:
            arithmetic.prec = 28
            ratio = revenue["value"] / volume["value"]
        derived = [{"metric_id": "revenue_per_parcel_mix_proxy", "value": ratio,
                    "unit": "CNY_PER_PARCEL", "inputs": ["express_revenue", "express_volume"],
                    "formula": "express_revenue / express_volume; both reported in 100 million units",
                    "semantics": "ROUNDED_AGGREGATE_MIX_PROXY_NOT_LIKE_FOR_LIKE_PRICE_OR_PROFIT"}]
        node_id, period_kind = "cn.express.unit_economics", "CALENDAR_MONTH"
        scope = "NATIONAL_EXPRESS_BUSINESS_NOT_TOTAL_POSTAL_BUSINESS"
        limitation = "Revenue per parcel is mix-sensitive, rounded and seasonal; it is not a like-for-like price or company profit."
    if period_end > published:
        raise ValueError("data period follows publication; cross-year ambiguity requires manual review")
    payload = {
        "schema_version": 1, "semantics": SEMANTICS,
        "source_record": dict(source), "excerpt_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "node_id": node_id, "scope": scope,
        "period": {"start": period_start, "end": period_end, "kind": period_kind},
        "metrics": metrics, "derived": derived, "limitations": limitation,
        "next_release_due": None, "freshness": "NEXT_RELEASE_SCHEDULE_NOT_QUALIFIED",
        "historical_first_vintage_proven": False,
        "system_pit_eligible_from": captured,
        **AUTHORITY,
    }
    payload["observation_hash"] = canonical_hash(payload)
    return json.loads(canonical_json(payload))


def _validate(observation: Mapping[str, Any]) -> None:
    if not isinstance(observation, Mapping) or "source_record" not in observation:
        raise ValueError("malformed economic observation")
    if observation != qualify_release_excerpt(observation["source_record"]):
        raise ValueError("economic observation differs from its source-derived record")


def compare_release_observations(before: Mapping[str, Any], after: Mapping[str, Any], *, as_of: datetime) -> dict[str, Any]:
    _aware(as_of)
    _validate(before)
    _validate(after)
    if any(datetime.fromisoformat(item["system_pit_eligible_from"].replace("Z", "+00:00")) > as_of for item in (before, after)):
        raise ValueError("comparison PIT precedes actual system capture")
    if (before["node_id"], before["scope"], before["source_record"]["capture_method"]) != (
        after["node_id"], after["scope"], after["source_record"]["capture_method"]):
        raise ValueError("do not mix nodes, scope or synthetic/public provenance")
    if before["period"]["end"] > after["period"]["end"] or before["source_record"]["published_date"] > after["source_record"]["published_date"]:
        raise ValueError("comparison order is reversed")
    if datetime.fromisoformat(before["system_pit_eligible_from"].replace("Z", "+00:00")) > datetime.fromisoformat(after["system_pit_eligible_from"].replace("Z", "+00:00")):
        raise ValueError("capture order is reversed")
    left = {row["metric_id"]: row for row in before["metrics"] + before["derived"]}
    right = {row["metric_id"]: row for row in after["metrics"] + after["derived"]}
    if set(left) != set(right) or any(left[key]["unit"] != right[key]["unit"] for key in left):
        raise ValueError("metric identity or unit changed")
    changes = []
    with localcontext() as arithmetic:
        arithmetic.prec = 28
        for key in sorted(left):
            previous, current = Decimal(left[key]["value"]), Decimal(right[key]["value"])
            changes.append({"metric_id": key, "unit": left[key]["unit"], "previous": previous,
                            "current": current, "difference": current - previous,
                            "change_ratio": current / previous - 1})
    payload = {"schema_version": 1, "semantics": "DESCRIPTIVE_RELEASE_COMPARISON_NOT_FUNDAMENTAL_STATE_MIGRATION",
               "comparison_kind": "REVISION_NOT_NEW_PERIOD" if before["period"] == after["period"] else "PERIOD_COMPARISON",
               "before_hash": before["observation_hash"], "after_hash": after["observation_hash"],
               "as_of": as_of, "changes": changes, "seasonal_adjustment": "NONE",
               "continuous_series_coverage": "NOT_ESTABLISHED", **AUTHORITY}
    payload["comparison_hash"] = canonical_hash(payload)
    return json.loads(canonical_json(payload))


def write_study_observation(directory: Path, observation: Mapping[str, Any]) -> Path:
    """Content-addressed, idempotent append only; never overwrite a vintage."""
    _validate(observation)
    if directory.is_symlink():
        raise ValueError("study directory must not be a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{observation['observation_hash']}.json"
    data = (canonical_json(dict(observation)) + "\n").encode("utf-8")
    if target.is_symlink():
        raise ValueError("study record must not be a symlink")
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError("existing study record bytes disagree; no overwrite")
        return target
    with target.open("xb") as stream:
        stream.write(data)
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Extract a bounded reviewed public-release excerpt; no network or Radar event write.")
    parser.add_argument("source_record", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.source_record.resolve().is_relative_to(args.output.resolve()):
        parser.error("output must be a new study directory outside the input")
    try:
        if args.source_record.stat().st_size > MAX_EXCERPT_BYTES * 2:
            raise ValueError("source record exceeds the operations byte budget")
        source = json.loads(args.source_record.read_text(encoding="utf-8"))
        observation = qualify_release_excerpt(source)
        target = write_study_observation(args.output, observation)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Economic study unavailable: {exc}\n")
    print(f"Study observation: {target.name}; no signal or investment authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
