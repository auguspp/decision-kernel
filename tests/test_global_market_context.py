"""Controlled B1 contracts; synthetic rows are never production market evidence."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import global_market_context as g
from decision_kernel.runtime import tushare_relay as relay

NOW = "2026-09-27T08:00:00+00:00"
ASOF = "2026-09-26"
IDENTITY = {"repository": g.REPOSITORY, "workflow": g.WORKFLOW, "ref": "refs/heads/main",
            "event": "workflow_dispatch", "code_commit": "a" * 40, "run_id": 123, "attempt": 1}
KEY = "synthetic-b1-key"


def table(api, params):
    if api == "index_global":
        fields = ["ts_code", "trade_date", "close", "pct_chg"]
        items = [[params["ts_code"], "20260925", 101, 1],
                 [params["ts_code"], "20260921", 100, 0]]
    else:
        fields = ["date", *g.TENORS]
        items = [["20260925", *([1.25] * 8)], ["20260924", *([1.2] * 8)]]
    return {"code": 0, "msg": "ok", "data": {"fields": fields, "items": items}}


def request_fixture(transform=None):
    calls, sleeps = [], []
    def request(api, params, *, key, clock):
        def transport(api, params, key, *, clock):
            calls.append((api, deepcopy(params)))
            body, status = table(api, params), 200
            if transform:
                body, status = transform(body, len(calls))
            raw = body if isinstance(body, bytes) else g.encoded(body)
            return {"raw": raw, "http_status": status, "requested_at": clock(),
                    "received_at": clock(), "headers": {}}
        return relay.request(api, params, key=key, transport=transport, sleep=sleeps.append, clock=clock)
    return request, calls, sleeps


def saved(root):
    return {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}


def run_capture(tmp_path, monkeypatch, family="indices", transform=None):
    monkeypatch.setenv(relay.SECRET_ENV, KEY)
    request, calls, sleeps = request_fixture(transform)
    root = tmp_path / "capture"
    report = g.capture(root, IDENTITY, family, ASOF, request=request, now=lambda: NOW)
    return report, saved(root), calls, sleeps


@pytest.mark.parametrize("family,count,api", [("indices", 6, "index_global"), ("shibor", 1, "shibor")])
def test_independent_families_use_original_client_and_replay(tmp_path, monkeypatch, family, count, api):
    report, files, calls, sleeps = run_capture(tmp_path, monkeypatch, family)
    assert len(calls) == count and {c[0] for c in calls} == {api} and not sleeps
    assert report["status"] == "AVAILABLE"
    assert report["source_calls_during_replay"] == 0
    monkeypatch.delenv(relay.SECRET_ENV)
    assert g.replay(files, IDENTITY, NOW) == report
    assert "NONE" == report["authority"]["investment_authority"]
    assert not report["authority"]["automatic_admission"]
    assert KEY.encode() not in b"".join(files.values())


def test_dates_and_interval_returns_do_not_invent_exchange_sessions():
    spec = g.plan("indices", ASOF)[0]
    out = g.normalize(table(spec["api"], spec["params"]), spec)["observations"][0]
    assert out["value"] == "101" and out["unit"] == "INDEX_POINTS"
    assert out["previous_observed_date"] == "2026-09-21"
    assert out["source_date"] == "2026-09-25" and out["calendar_age_at_requested_end"] == 1
    assert out["observed_interval_change_pct"] == "1.000000"
    assert out["source_daily_pct_change"] == "1"
    assert out["market_status"] == "UNKNOWN_NO_EXCHANGE_CALENDAR" and out["publication_time"] is None


def test_shibor_percent_change_is_basis_points_not_percent_return():
    spec = g.plan("shibor", ASOF)[0]
    body = table("shibor", spec["params"])
    out = g.normalize(body, spec)["observations"]
    assert len(out) == 8 and all(r["currency"] == "CNY" and r["unit"] == "ANNUAL_PERCENT" for r in out)
    assert all(r["observed_interval_change_bp"] == "5.00" for r in out)
    body["data"]["items"][0][1] = None
    partial = g.normalize(body, spec)
    assert partial["status"] == "PARTIAL_VALUES"
    assert partial["observations"][0]["value"] is None
    assert partial["observations"][0]["observed_interval_change_bp"] is None


@pytest.mark.parametrize("mutation", ["wrong-symbol", "future", "too-old", "duplicate", "duplicate-field",
                                      "nonfinite", "boolean", "bad-date", "missing-field", "truncated", "negative-close"])
def test_foreign_future_or_malformed_rows_are_not_projected(mutation):
    spec = g.plan("indices", ASOF)[0]
    body = table("index_global", spec["params"])
    row = body["data"]["items"][0]
    if mutation == "wrong-symbol": row[0] = "OTHER"
    if mutation == "future": row[1] = "20260928"
    if mutation == "too-old": row[1] = "20260101"
    if mutation == "duplicate": body["data"]["items"].append(deepcopy(row))
    if mutation == "duplicate-field": body["data"]["fields"][3] = "close"
    if mutation == "nonfinite": row[2] = "NaN"
    if mutation == "boolean": row[2] = True
    if mutation == "bad-date": row[1] = "20260230"
    if mutation == "missing-field": body["data"]["fields"][0] = "symbol"
    if mutation == "truncated": body["count"] = 100
    if mutation == "negative-close": row[2] = -1
    with pytest.raises((ValueError, TypeError, KeyError)):
        g.normalize(body, spec)


@pytest.mark.parametrize("status,error", [(403, "forbidden"), (429, "rate_limited"), (401, "unauthorized")])
def test_service_refusal_stops_remaining_symbols_and_retains_failure(tmp_path, monkeypatch, status, error):
    report, files, calls, _ = run_capture(tmp_path, monkeypatch, transform=lambda b, n: ({"error": error}, status))
    assert len(calls) == 1 and report["status"] == "UNAVAILABLE"
    assert all(r["status"] == "NOT_ATTEMPTED_SERVICE_STOP" for r in report["outcomes"][1:])
    assert "raw-00-1.json" in files and "没有市场变化" in g.render(report)


def test_partial_failure_does_not_clear_another_instrument(tmp_path, monkeypatch):
    def source(body, n):
        if n == 2: return {"error": "forbidden"}, 403
        return body, 200
    report, files, calls, _ = run_capture(tmp_path, monkeypatch, transform=source)
    assert len(calls) == 2 and report["status"] == "PARTIAL" and report["available_values"] == 1
    assert report["outcomes"][0]["observations"][0]["value"] == "101"
    assert "raw-00-1.json" in files and "raw-01-1.json" in files


def test_empty_and_bad_source_body_not_market_quiet(tmp_path, monkeypatch):
    def source(body, n):
        if n == 1: body["data"]["items"] = []
        if n == 2: body["data"]["items"][0][0] = "OTHER"
        return body, 200
    report, _, _, _ = run_capture(tmp_path, monkeypatch, transform=source)
    assert report["outcomes"][0]["status"] == "EMPTY_RESPONSE_NOT_NO_CHANGE"
    assert report["outcomes"][1]["status"] == "TABLE_UNCONFIRMED"
    assert report["status"] == "PARTIAL"


def test_existing_client_temporary_queue_retry_is_not_expanded(tmp_path, monkeypatch):
    report, files, calls, sleeps = run_capture(tmp_path, monkeypatch, family="shibor",
        transform=lambda b, n: ({"code": 1, "msg": "timeout"}, 200) if n == 1 else (b, 200))
    assert len(calls) == 2 and sleeps == [30] and report["status"] == "AVAILABLE"
    assert "raw-00-1.json" in files and "raw-00-2.json" in files


def test_missing_credentials_never_attempted(tmp_path, monkeypatch):
    monkeypatch.delenv(relay.SECRET_ENV, raising=False)
    def never(*a, **k): pytest.fail("must not call source")
    root = tmp_path / "capture"
    report = g.capture(root, IDENTITY, "indices", ASOF, request=never, now=lambda: NOW)
    assert report["outcomes"][0]["status"] == "CREDENTIAL_UNAVAILABLE"
    assert report["outcomes"][0]["attempt_count"] == 0
    assert not any(name.startswith("raw-") for name in saved(root))


@pytest.mark.parametrize("failure", ["exception", "reflection", "wrong-request"])
def test_unsafe_or_uncertain_receipt_is_not_logged_or_retried(tmp_path, monkeypatch, failure):
    monkeypatch.setenv(relay.SECRET_ENV, KEY)
    original, calls, _ = request_fixture(lambda b, n: ({**b, "secret": KEY}, 200))
    def unsafe(api, params, **kwargs):
        if failure == "exception": raise RuntimeError(KEY)
        result = original(api, params, **kwargs)
        if failure == "wrong-request": result["api"] = "other"
        return result
    root = tmp_path / "capture"
    report = g.capture(root, IDENTITY, "indices", ASOF, request=unsafe, now=lambda: NOW)
    assert report["outcomes"][0]["status"] == "REQUEST_RECEIPT_UNAVAILABLE"
    assert report["outcomes"][0]["attempt_count"] is None
    assert KEY.encode() not in b"".join(saved(root).values())
    assert len(calls) <= 1


@pytest.mark.parametrize("change", ["raw", "run", "authority", "date", "path", "plan"])
def test_replay_checks_raw_and_declared_identity_even_when_manifest_rehashed(tmp_path, monkeypatch, change):
    _, files, _, _ = run_capture(tmp_path, monkeypatch)
    manifest = json.loads(files["capture.json"])
    if change == "raw": files["raw-00-1.json"] += b" "
    if change == "run": manifest["identity"]["run_id"] += 1
    if change == "authority": manifest["authority"]["investment_authority"] = "APPROVED"
    if change == "date": manifest["as_of_date"] = "2026-09-28"
    if change == "path": manifest["records"][0]["attempts"][0]["body"] = "../anything"
    if change == "plan": manifest["records"][0]["spec"]["params"]["ts_code"] = "OTHER"
    manifest["capture_hash"] = g.digest(manifest)
    files["capture.json"] = g.encoded(manifest)
    with pytest.raises((ValueError, KeyError)):
        g.replay(files, IDENTITY, NOW)


@pytest.mark.parametrize("asof", ["2026-09-27", "2026-09-28", "2026-01-01"])
def test_capture_is_recent_completed_dates_only(tmp_path, asof):
    with pytest.raises(ValueError):
        g.capture(tmp_path / "out", IDENTITY, "indices", asof, now=lambda: NOW)
    assert not (tmp_path / "out").exists()


def test_existing_output_and_foreign_execution_refused_before_side_effect(tmp_path):
    with pytest.raises(ValueError):
        g.capture(tmp_path, IDENTITY, "indices", ASOF, now=lambda: NOW)
    foreign = {**IDENTITY, "ref": "refs/heads/other"}
    with pytest.raises(ValueError):
        g.capture(tmp_path / "new", foreign, "indices", ASOF, now=lambda: NOW)
    assert not (tmp_path / "new").exists()


def test_family_is_explicit_and_no_generic_source_parameters():
    with pytest.raises(ValueError): g.plan("arbitrary_api", ASOF)
    assert {s["api"] for s in g.plan("shibor", ASOF)} == {"shibor"}
    assert all(set(s["params"]) == {"ts_code", "start_date", "end_date"} for s in g.plan("indices", ASOF))


def test_workflow_is_read_only_main_only_and_has_bounded_daily_schedule():
    source = (Path(__file__).resolve().parents[1] / ".github/workflows/radar-global-market.yml").read_text()
    assert "workflow_dispatch:" in source and "schedule:" in source and source.count("cron:") == 2
    assert "contents: write" not in source and "actions: write" not in source
    assert "github.run_attempt == 1" in source and "refs/heads/main" in source
    assert "EXPECTED_CODE" in source and "head_sha" in source and "ci.yml" in source
    assert "TUSHARE_PROXY_API_KEY: ${{ secrets.TUSHARE_PROXY_API_KEY }}" in source
    assert "global-market-${{ inputs.family }}-${{ github.run_id }}-${{ github.run_attempt }}" in source


@pytest.mark.parametrize("event", ["workflow_dispatch", "schedule"])
def test_authorized_daily_identity_preserves_real_event(event):
    candidate = {**IDENTITY, "event": event}
    g.validate_identity(candidate)
    assert candidate["event"] == event
    for wrong in ("push", "pull_request", "workflow_run"):
        with pytest.raises(ValueError):
            g.validate_identity({**candidate, "event": wrong})
    with pytest.raises(ValueError):
        g.validate_identity({**candidate, "ref": "refs/heads/other"})
