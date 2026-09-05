from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime, timezone

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime.hithink_dump_inspection import inspect_daily_k_rows
from decision_kernel.runtime import stock_field_source_study as study

NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def report():
    codes = ("000408.SZ", "001316.SZ", "920371.BJ")
    days = (date(2026, 9, 3), date(2026, 9, 4))
    rows = [{"thscode": code, "currency": "CNY", "interval": "1d", "adjusted": "none",
             "date_ms": int(datetime(day.year, day.month, day.day, tzinfo=study.TZ).timestamp()*1000),
             "open_price": "101", "high_price": "103", "low_price": "100",
             "close_price": "101" if day == days[0] else "102", "volume": "10", "turnover": "1000"}
            for code in codes for day in days]
    snapshot = {"market_session": "2026-09-04", "points": [
        {"thscode": code, "last_price": "102", "prev_price": "100" if code != "920371.BJ" else "101",
         "turnover": "1100" if code == "920371.BJ" else "1000"} for code in codes]}
    value = {"input_file_sha256": dict.fromkeys(("parquet", "sessions", "universe", "snapshot"), "a"*64),
             "inspection": inspect_daily_k_rows(rows, expected_sessions=days, current_universe=codes, reference_snapshot=snapshot)}
    value["report_hash"] = canonical_hash(value)
    return value


def reply(spec):
    url, code = spec["url"], spec["params"].get("thscode")
    if url == study.EVENTS:
        value = {"code": 0, "data": {"thscode": code, "ticker": code[:6], "item": []}}
    elif url == study.HISTORY:
        value = {"code": 0, "data": {"item": []}}
    elif url == study.SYMBOLS:
        value = {"stockList": [{"code": code, "orgId": "gssz"+code} for code in ("000408", "001316")]}
    elif url == study.NOTICES:
        code = spec["params"]["stock"].split(",")[0]
        value = {"hasMore": False, "announcements": [{"secCode": code,
                 "announcementTitle": "2026年半年度权益分派实施公告",
                 "adjunctUrl": f"finalpage/2026-08-28/{code}.PDF"}]}
    else:
        return 200, b"%PDF-1.7\nSYNTHETIC_CONTAINER_ONLY\n%%EOF"
    return 200, json.dumps(value, ensure_ascii=False).encode()


def run(tmp_path, request=reply, **kwargs):
    return study.capture_sources(study.build_plan(report()), tmp_path / "new", api_key="fixture-secret",
        request=request, now=lambda: NOW, provenance="SYNTHETIC_TEST_ONLY", **kwargs)


def test_plan_is_deterministic_targeted_and_does_not_mutate_report():
    source = report()
    before = copy.deepcopy(source)
    plan = study.build_plan(source)
    assert source == before
    assert study.build_plan(source) == plan
    assert [r["params"]["thscode"] for r in plan["provider_requests"]] == ["000408.SZ", "001316.SZ", "920371.BJ"]
    assert plan["provider_requests"][0]["params"]["from"] == "2026-09-04"
    assert plan["provider_requests"][-1]["params"]["adjust"] == "none"
    assert plan["source_disposition"] == "DIFFERENCES_REQUIRE_REVIEW"
    assert plan["production_qualification"] == "NOT_ESTABLISHED"
    assert canonical_hash({k:v for k,v in plan.items() if k != "plan_hash"}) == plan["plan_hash"]


def test_raw_capture_preserves_bodies_clocks_and_no_acceptance(tmp_path):
    result = run(tmp_path)
    assert result["status"] == "CAPTURE_COMPLETE_REVIEW_REQUIRED"
    assert len(result["requests"]) == len(result["files"]) == 8
    assert result["provenance"] == "SYNTHETIC_TEST_ONLY"
    assert result["causes_automatically_accepted"] == result["events_created"] == 0
    assert result["source_disposition"] == "DIFFERENCES_REQUIRE_REVIEW"
    assert result["production_qualification"] == "NOT_ESTABLISHED"
    for row in result["files"]:
        raw = (tmp_path / "new" / row["name"]).read_bytes()
        assert len(raw) == row["bytes"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    assert result["study_hash"] == canonical_hash({k:v for k,v in result.items() if k != "study_hash"})


@pytest.mark.parametrize("status", [301, 403, 429, 500])
def test_http_failures_have_status_no_error_body_and_no_retry(tmp_path, status):
    calls = []
    def request(spec):
        calls.append(spec["id"])
        return (status, b"NEVER_RETAIN_ERROR_BODY") if spec["url"] == study.EVENTS else reply(spec)
    result = run(tmp_path, request)
    assert len(calls) == len(set(calls)) == 8
    assert result["status"] == "INCOMPLETE_SOURCE_STUDY"
    assert result["requests"][0]["http_status"] == status
    assert result["requests"][0]["file"] is None
    assert all(b"NEVER_RETAIN_ERROR_BODY" not in p.read_bytes() for p in (tmp_path/"new").iterdir())


@pytest.mark.parametrize("raw", [b'{"token":"secret"}', b'{"x":"fixture-secret"}', b'{"x":NaN}', b'[]', b'not-json'])
def test_unsafe_or_malformed_body_not_archived(tmp_path, raw):
    result = run(tmp_path, lambda spec: (200, raw) if spec["url"] == study.EVENTS else reply(spec))
    assert result["status"] == "INCOMPLETE_SOURCE_STUDY"
    assert result["requests"][0]["file"] is None


def test_valid_raw_error_envelope_retained_without_becoming_event(tmp_path):
    result = run(tmp_path, lambda spec: (200, b'{"code":1003,"data":{"item":[]}}') if spec["url"] == study.EVENTS else reply(spec))
    assert result["requests"][0]["file"] is not None
    assert result["requests"][0]["error_type"] == "ValueError"
    assert result["status"] == "INCOMPLETE_SOURCE_STUDY"


def test_wrong_event_identity_retains_original_and_fails(tmp_path):
    raw = b'{"code":0,"data":{"thscode":"000001.SZ","item":[]}}'
    result = run(tmp_path, lambda spec: (200, raw) if spec["url"] == study.EVENTS else reply(spec))
    assert result["requests"][0]["file"] is not None
    assert result["status"] == "INCOMPLETE_SOURCE_STUDY"


@pytest.mark.parametrize("body", [
    {"hasMore": True, "announcements": []},
    {"announcements": []},
    {"announcements": [{"secCode": "000408", "announcementTitle": "2026权益分派实施公告", "adjunctUrl": "https://evil.test/a.pdf"}]},
    {"announcements": [{"secCode": "000408", "announcementTitle": "2026权益分派实施公告", "adjunctUrl": "finalpage/../secret.PDF"}]},
])
def test_notice_selection_rejects_incomplete_missing_or_untrusted_path(body):
    with pytest.raises(ValueError):
        study.notice_pdf("000408.SZ", body)


def test_no_live_mock_or_production_output_or_overwrite(tmp_path):
    plan = study.build_plan(report())
    with pytest.raises(ValueError, match="SYNTHETIC"):
        study.capture_sources(plan, tmp_path/"a", api_key="x", request=reply)
    with pytest.raises(ValueError, match="ISOLATED"):
        study.capture_sources(plan, tmp_path/"decision-state"/"a", api_key="x")
    run(tmp_path)
    before = (tmp_path/"new"/"report.json").read_bytes()
    with pytest.raises(ValueError, match="ISOLATED"):
        run(tmp_path)
    assert (tmp_path/"new"/"report.json").read_bytes() == before


@pytest.mark.parametrize("url", ["http://fuyao.aicubes.cn/api/a-share/prices/historical", "https://evil.test/a", "https://static.cninfo.com.cn/finalpage/2026-08-28/1.PDF?token=x"])
def test_transport_rejects_unreviewed_destinations_before_network(url):
    with pytest.raises(ValueError, match="DESTINATION"):
        study.request_spec({"method":"GET","url":url,"params":{}}, api_key="fixture-secret")


def test_transport_scopes_key_to_provider_and_disables_redirects(monkeypatch):
    calls = []
    class Response:
        status_code, headers = 200, {}
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def iter_content(self, **kwargs): yield b'{}'
    class Session:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def request(self, method, url, **kwargs):
            calls.append((url,kwargs))
            return Response()
    monkeypatch.setattr(study, "_session", Session)
    study.request_spec({"method":"GET", "url":study.EVENTS, "params":{"thscode":"000408.SZ"}}, api_key="fixture-secret")
    study.request_spec({"method":"GET", "url":study.SYMBOLS, "params":{}}, api_key="fixture-secret")
    assert calls[0][1]["headers"]["X-api-key"] == "fixture-secret"
    assert "X-api-key" not in calls[1][1]["headers"]
    assert all(call[1]["allow_redirects"] is False for call in calls)
