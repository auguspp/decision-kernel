"""Real Inbox/Watch composition with bounded source failure injection."""
from datetime import datetime, timedelta
import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from decision_kernel.runtime import attention_inbox_with_odds_watch as app, hithink_http as h, odds_watch
from test_hithink_history_window import _sessions, _calendar_envelope, _history_envelope, SHANGHAI
from test_inbox_calendar_recovery import Response

ROOT = Path(__file__).resolve().parents[1]
# The second retained research package was created on September 2. Its synthetic
# market must follow that cutoff; never weaken production PIT checks for a test.
OBSERVED = datetime(2026, 9, 11, 16, 30, tzinfo=SHANGHAI)
SESSIONS = tuple(day + timedelta(days=14) for day in _sessions())
SECRET = 'gap-test-secret-never-render'


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None): return OBSERVED.astimezone(tz)
    monkeypatch.setattr(app, 'datetime', FixedDateTime)
    monkeypatch.setenv(h.HITHINK_API_KEY_ENV, SECRET)
    monkeypatch.delenv(h.HITHINK_SECTOR_PACING_ENV, raising=False)
    h._request_hithink_calendar.cache_clear()
    yield
    h._request_hithink_calendar.cache_clear()
    assert h._calendar_recovery.get() is None


def arguments(tmp_path):
    return [str(ROOT/'dogfood/600519-moutai.json'),
            str(ROOT/'research_cases/002050-sanhua-deep-research-v1.json'),
            '--output', str(tmp_path/'inbox.html'), '--summary', str(tmp_path/'summary.md'),
            '--odds-watch-config', str(ROOT/'decision_inputs/odds-watch-v0.json'),
            '--odds-watch-registry', str(ROOT/'current_state/registry.json'),
            '--odds-watch-output', str(tmp_path/'watch')]


@pytest.mark.parametrize('failed_ticker', ['600519.SH', '002050.SZ'])
def test_one_price_gap_preserves_other_real_decisions_and_watch_without_retry(monkeypatch, tmp_path, failed_ticker):
    calls = []
    def open_(request, timeout):
        path = urlsplit(request.full_url).path
        if path == h.HITHINK_CALENDAR_PATH:
            calls.append('calendar')
            return Response(_calendar_envelope(SESSIONS))
        ticker = parse_qs(urlsplit(request.full_url).query)['thscode'][0]
        calls.append(ticker)
        if ticker == failed_ticker:
            raise URLError(TimeoutError(SECRET))
        body = _history_envelope(SESSIONS); body['data']['thscode'] = ticker
        return Response(body)
    monkeypatch.setattr(h, 'urlopen', open_)
    out = io.StringIO()
    assert app.main(arguments(tmp_path), stdout=out) == 0
    assert calls.count('calendar') == 1
    assert calls.count(failed_ticker) == 1
    report = odds_watch.read_and_validate(tmp_path/'watch/watch.json')
    assert report['watch']['price_gap_count'] == (1 if failed_ticker == '002050.SZ' else 0)
    assert report['watch']['authority'] == odds_watch.AUTHORITY
    rows = report['watch']['active_cases']
    assert any(row['price'] is not None for row in rows)
    for row in rows:
        if row['ticker'] == failed_ticker:
            assert row['status'] == 'PRICE_UNAVAILABLE_NOT_QUIET'
            assert row['price'] is None and row['triggered_conditions'] == []
    summary = (tmp_path/'summary.md').read_text()
    page = (tmp_path/'inbox.html').read_text()
    assert '完成 1/2' in summary and failed_ticker in summary
    assert 'DEGRADED_SOURCE_GAPS' in out.getvalue()
    assert '今天没有需要你关注的东西' not in summary
    assert 'card empty' not in page
    assert SECRET not in summary + page + out.getvalue()


@pytest.mark.parametrize('code', [401, 403, 429])
def test_account_rejection_cannot_repeat_via_next_ticker(monkeypatch, tmp_path, code):
    calls = []
    def open_(request, timeout):
        path = urlsplit(request.full_url).path; calls.append(path)
        if path == h.HITHINK_CALENDAR_PATH:
            return Response(_calendar_envelope(SESSIONS))
        raise HTTPError(request.full_url, code, SECRET, {}, None)
    monkeypatch.setattr(h, 'urlopen', open_)
    assert app.main(arguments(tmp_path), stdout=io.StringIO()) == 0
    assert calls == [h.HITHINK_CALENDAR_PATH, h.HITHINK_HISTORY_PATH]
    report = odds_watch.read_and_validate(tmp_path/'watch/watch.json')
    assert report['watch']['price_gap_count'] == 5
    assert report['watch']['attention_case_count'] == 0
    assert '完成 0/2' in (tmp_path/'summary.md').read_text()
    assert SECRET not in (tmp_path/'summary.md').read_text()


@pytest.mark.parametrize('invalid', ['config', 'package'])
def test_integrity_errors_remain_fail_closed_before_delivery(monkeypatch, tmp_path, invalid):
    monkeypatch.setattr(h, 'urlopen', lambda *a, **k: pytest.fail('unexpected source call'))
    args = arguments(tmp_path)
    broken = tmp_path/'invalid.json'; broken.write_text('{}')
    if invalid == 'config':
        args[args.index('--odds-watch-config') + 1] = str(broken)
    else:
        args[0] = str(broken)
    assert app.main(args, stderr=io.StringIO()) == 2
    assert not (tmp_path/'inbox.html').exists()
    assert not (tmp_path/'watch').exists()


def test_unexpected_programming_failure_is_not_renamed_a_price_gap(monkeypatch, tmp_path):
    def broken(*args, **kwargs): raise RuntimeError('unexpected bug')
    monkeypatch.setattr(app.attention_inbox, '_run_research_package', broken)
    with pytest.raises(RuntimeError, match='unexpected bug'):
        app.main(arguments(tmp_path))
    assert not (tmp_path/'inbox.html').exists()


def test_coverage_does_not_claim_five_prices_checked_when_one_is_missing():
    report = {'watch': {'active_case_count': 5, 'price_gap_count': 1, 'attention_case_count': 0}}
    text = app.coverage_text(4, 4, [], report)
    assert '已完成判断 4' in text and '未触界 4，无法判断 1' in text
    assert '确认触界 0' in text and '部分可用交付' in text
