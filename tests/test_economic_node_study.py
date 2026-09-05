from __future__ import annotations

import copy
import json
import socket
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import economic_node_study as study


SOURCES = Path("radar_inputs/economic-node-study-2026-09-05.json")
CAPTURE = datetime.fromisoformat("2026-09-05T04:51:30.793710+00:00")


def sources():
    return json.loads(SOURCES.read_text(encoding="utf-8"))


def observed(index):
    return study.qualify_release_excerpt(sources()[index])


def values(observation):
    return {item["metric_id"]: Decimal(item["value"]) for item in observation["metrics"] + observation["derived"]}


def test_reviewed_livestock_releases_preserve_collection_publication_and_capture():
    earlier, later = observed(0), observed(1)
    assert earlier["period"] == {"start": "2026-08-20", "end": "2026-08-20", "kind": "COLLECTION_DATE"}
    assert later["period"]["end"] == "2026-08-27"
    assert later["source_record"]["published_date"] == "2026-09-01"
    assert later["system_pit_eligible_from"] == "2026-09-05T04:51:30.793710Z"
    assert values(earlier) == {"live_hog_price": Decimal("11.52"), "corn_price": Decimal("2.46"), "fattening_pig_feed_price": Decimal("3.35")}
    assert values(later) == {"live_hog_price": Decimal("11.55"), "corn_price": Decimal("2.46"), "fattening_pig_feed_price": Decimal("3.35")}
    assert all(item["unit"] == "CNY_PER_KG" for item in later["metrics"])
    assert later["derived"] == []
    assert later["historical_first_vintage_proven"] is False
    assert later["next_release_due"] is None
    assert later["freshness"] == "NEXT_RELEASE_SCHEDULE_NOT_QUALIFIED"
    assert all(later[key] == "NONE" for key in study.AUTHORITY)
    claimed = later.pop("observation_hash")
    assert canonical_hash(later) == claimed


def test_express_monthly_not_cumulative_or_total_postal_fields():
    june, july = observed(2), observed(3)
    assert june["period"] == {"start": "2026-06-01", "end": "2026-06-30", "kind": "CALENDAR_MONTH"}
    assert july["period"]["end"] == "2026-07-31"
    assert values(june)["express_revenue"] == Decimal("1360.4")
    assert values(june)["express_volume"] == Decimal("175.1")
    assert values(july)["express_revenue"] == Decimal("1303.7")
    assert values(july)["express_volume"] == Decimal("170.8")
    assert values(june)["revenue_per_parcel_mix_proxy"] == Decimal("1360.4") / Decimal("175.1")
    assert values(july)["revenue_per_parcel_mix_proxy"] == Decimal("1303.7") / Decimal("170.8")
    assert "NOT_LIKE_FOR_LIKE_PRICE_OR_PROFIT" in july["derived"][0]["semantics"]
    source = sources()[3]
    source["capture_method"] = "SYNTHETIC_TEST_ONLY"
    source["excerpt"] += "\n1-7月，邮政行业业务收入累计完成10799.1亿元。其中，快递业务收入累计完成9017.7亿元。\n1-7月，邮政行业寄递业务量累计完成1274.4亿件。其中,快递业务量累计完成1174.7亿件。"
    assert values(study.qualify_release_excerpt(source)) == values(july)


def test_comparison_is_descriptive_and_cannot_migrate_fundamental_state():
    livestock = study.compare_release_observations(observed(0), observed(1), as_of=CAPTURE)
    by_id = {item["metric_id"]: item for item in livestock["changes"]}
    assert Decimal(by_id["live_hog_price"]["difference"]) == Decimal("0.03")
    assert Decimal(by_id["corn_price"]["difference"]) == 0
    express = study.compare_release_observations(observed(2), observed(3), as_of=CAPTURE)
    proxy = next(item for item in express["changes"] if item["metric_id"] == "revenue_per_parcel_mix_proxy")
    assert Decimal(proxy["change_ratio"]) == Decimal("-0.0175525675393722882166493254")
    assert express["seasonal_adjustment"] == "NONE"
    assert express["continuous_series_coverage"] == "NOT_ESTABLISHED"
    assert all(express[key] == "NONE" for key in study.AUTHORITY)


def test_historical_release_date_is_not_system_pit_availability():
    with pytest.raises(ValueError, match="actual system capture"):
        study.compare_release_observations(observed(0), observed(1), as_of=CAPTURE - timedelta(seconds=1))
    with pytest.raises(ValueError, match="timezone-aware"):
        study.compare_release_observations(observed(0), observed(1), as_of=datetime(2026, 9, 5))


@pytest.mark.parametrize("key,value", [
    ("source_url", "https://example.com/article"),
    ("source_url", "https://xmsyj.moa.gov.cn/jcyj/202608/t20260825_6486995.htm?token=not-a-real-token"),
    ("source_url", "http://xmsyj.moa.gov.cn/jcyj/202608/t20260825_6486995.htm"),
    ("source_url", "https://xmsyj.moa.gov.cn:443/jcyj/202608/t20260825_6486995.htm"),
    ("published_date", "2026-08-24"),
    ("published_time_precision", "EXACT_TIME_GUESSED"),
    ("captured_at", "2026-08-01T00:00:00Z"),
    ("captured_at", "2026-09-05T12:00:00"),
    ("capture_method", "AUTOMATIC_FULL_PAGE_CAPTURE"),
    ("source_kind", "UNKNOWN"),
])
def test_invalid_metadata_fails_closed(key, value):
    source = sources()[0]
    source[key] = value
    with pytest.raises(ValueError):
        study.qualify_release_excerpt(source)


@pytest.mark.parametrize("alteration", ["missing", "ambiguous", "unit", "scope", "future_period"])
def test_unsupported_source_statements_are_not_guessed(alteration):
    source = sources()[0]
    source["capture_method"] = "SYNTHETIC_TEST_ONLY"
    if alteration == "missing":
        source["excerpt"] = source["excerpt"].replace("全国玉米平均价格2.46元/公斤", "玉米数据未披露")
    elif alteration == "ambiguous":
        source["excerpt"] += "\n全国玉米平均价格2.50元/公斤"
    elif alteration == "unit":
        source["excerpt"] = source["excerpt"].replace("元/公斤", "元/吨")
    elif alteration == "scope":
        source["excerpt"] = source["excerpt"].replace("全国500个县", "某省50个县")
    else:
        source["excerpt"] = source["excerpt"].replace("采集日为8月20日", "采集日为8月30日")
    with pytest.raises(ValueError):
        study.qualify_release_excerpt(source)


def test_rehashed_forged_value_still_fails_source_reconstruction(tmp_path):
    payload = observed(3)
    payload["derived"][0]["value"] = "9.99"
    payload["observation_hash"] = canonical_hash({key: value for key, value in payload.items() if key != "observation_hash"})
    with pytest.raises(ValueError, match="source-derived"):
        study.write_study_observation(tmp_path / "study", payload)


def test_revisions_append_new_vintage_and_same_record_is_idempotent(tmp_path):
    earlier_source = sources()[0]
    earlier_source["capture_method"] = "SYNTHETIC_TEST_ONLY"
    later_source = copy.deepcopy(earlier_source)
    later_source["excerpt"] = later_source["excerpt"].replace("11.52", "11.53")
    later_source["captured_at"] = (CAPTURE + timedelta(days=1)).isoformat()
    earlier, later = (study.qualify_release_excerpt(item) for item in (earlier_source, later_source))
    comparison = study.compare_release_observations(earlier, later, as_of=CAPTURE + timedelta(days=1))
    assert comparison["comparison_kind"] == "REVISION_NOT_NEW_PERIOD"
    target = tmp_path / "study"
    first = study.write_study_observation(target, earlier)
    original = first.read_bytes()
    assert study.write_study_observation(target, earlier) == first
    second = study.write_study_observation(target, later)
    assert second != first and first.read_bytes() == original
    assert len(list(target.iterdir())) == 2
    first.write_bytes(b"damaged previous record")
    with pytest.raises(ValueError, match="no overwrite"):
        study.write_study_observation(target, earlier)
    assert first.read_bytes() == b"damaged previous record"


def test_nodes_and_provenance_cannot_be_mixed():
    with pytest.raises(ValueError, match="mix nodes"):
        study.compare_release_observations(observed(0), observed(3), as_of=CAPTURE)
    synthetic = sources()[1]
    synthetic["capture_method"] = "SYNTHETIC_TEST_ONLY"
    with pytest.raises(ValueError, match="provenance"):
        study.compare_release_observations(observed(0), study.qualify_release_excerpt(synthetic), as_of=CAPTURE)
    with pytest.raises(ValueError, match="reversed"):
        study.compare_release_observations(observed(1), observed(0), as_of=CAPTURE)


def test_cli_creates_only_a_study_record_without_network(tmp_path, monkeypatch):
    source = tmp_path / "source.json"
    source.write_text(json.dumps(sources()[0], ensure_ascii=False), encoding="utf-8")
    before = source.read_bytes()
    def forbidden(*args, **kwargs):
        raise AssertionError("economic study must not access the network")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    output = tmp_path / "study"
    assert study.main([str(source), "--output", str(output)]) == 0
    assert len(list(output.iterdir())) == 1
    assert source.read_bytes() == before
    assert not (output / "candidate-events.json").exists()
    with pytest.raises(SystemExit):
        study.main([str(source), "--output", str(output)])
