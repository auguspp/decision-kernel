"""Source-release opportunities are not source truth, trading days, or delivery."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import socket

import pytest

from decision_kernel.runtime import global_public_context as g
from test_global_public_context import IDENT, ASOF, TIME, body, run


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a, **k):
        raise AssertionError('morning-date regression attempted networking')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


@pytest.mark.parametrize('family,at,ceiling', [
    ('treasury', '2026-10-07T23:07:00Z', '2026-10-07'),
    ('fx', '2026-10-07T23:27:00Z', '2026-10-07'),
    ('treasury', '2026-01-07T23:07:00Z', '2026-01-07'),
    ('fx', '2026-01-07T23:27:00Z', '2026-01-07'),
    ('treasury', '2026-10-07T21:59:59Z', '2026-10-06'),
    ('treasury', '2026-10-07T22:00:00Z', '2026-10-07'),
    ('treasury', '2026-01-07T22:59:59Z', '2026-01-06'),
    ('treasury', '2026-01-07T23:00:00Z', '2026-01-07'),
    ('fx', '2026-10-07T14:59:59Z', '2026-10-06'),
    ('fx', '2026-10-07T15:00:00Z', '2026-10-07'),
    ('fx', '2026-01-07T15:59:59Z', '2026-01-06'),
    ('fx', '2026-01-07T16:00:00Z', '2026-01-07'),
    ('treasury', '2026-03-15T22:30:00Z', '2026-03-15'),
    ('fx', '2026-03-15T15:30:00Z', '2026-03-14'),
    ('crypto', '2026-10-07T23:59:59Z', '2026-10-06'),
    ('crypto', '2026-10-08T00:00:00Z', '2026-10-07'),
    ('commodities', '2026-10-07T23:59:59Z', '2026-10-06'),
    ('fx', '2026-12-31T23:27:00Z', '2026-12-31'),
])
def test_date_ceiling_uses_family_and_actual_dst_not_singapore_yesterday(family, at, ceiling):
    assert g.date_policy(family, at)['max_as_of_date'] == ceiling
    # Equivalent offset spellings cannot change the result.
    same = datetime.fromisoformat(at).astimezone(timezone(timedelta(hours=8)))
    assert g.date_policy(family, same.isoformat()) == g.date_policy(family, at)


@pytest.mark.parametrize('family', ['treasury', 'fx'])
@pytest.mark.parametrize('as_of', [None, '2026-09-25'])
def test_actual_same_utc_day_reference_survives_capture_and_replay(tmp_path, family, as_of):
    at = '2026-09-25T23:27:00Z'
    calls = []
    def request(spec):
        calls.append(spec)
        return g.PublicResponse(spec['url'], 200, {}, body(spec))
    root = tmp_path / 'capture'
    report = g.capture(root, IDENT, family, as_of, request=request, time=lambda: at)
    files = {p.name: p.read_bytes() for p in root.iterdir()}
    assert report['as_of_date'] == '2026-09-25'
    assert all(v['source_date'] == '2026-09-25' for v in report['observations'])
    assert report['version'] == g.VERSION and report['date_policy']['timezone'] != 'UTC'
    assert all(v['publication_time'] is None for v in report['observations'])
    assert g.replay(files, IDENT, '2026-09-26T00:00:00Z') == report
    assert len(calls) == 1 and report['source_calls_during_replay'] == 0
    assert report['authority'] == g.AUTHORITY
    assert '不是实际发布时间' in g.render(report)


def test_weekend_missing_release_retains_actual_friday_and_nulls(tmp_path):
    at = '2026-09-27T23:27:00Z'
    def request(spec):
        raw = body(spec).replace(b'currency="USD" rate="1.5"', b'currency="XXX" rate="1.5"')
        return g.PublicResponse(spec['url'], 200, {}, raw)
    report = g.capture(tmp_path/'c', IDENT, 'fx', request=request, time=lambda:at)
    assert report['as_of_date'] == '2026-09-27'
    assert report['status'] == 'PARTIAL'
    usd = next(v for v in report['observations'] if v['symbol']=='EUR/USD')
    assert usd['source_date']=='2026-09-25' and usd['value'] is None
    assert usd['previous_date']=='2026-09-24' and usd['change'] is None
    assert all(v['source_date']=='2026-09-25' for v in report['observations'])


@pytest.mark.parametrize('family', ['crypto', 'commodities'])
def test_same_utc_day_bars_are_rejected_before_io(family, tmp_path):
    calls=[]
    with pytest.raises(ValueError, match='GP_RECENT_DATE'):
        g.capture(tmp_path/'not-created', IDENT, family, '2026-10-07',
                  request=lambda spec:calls.append(spec), time=lambda:'2026-10-07T23:59:59Z')
    assert calls==[] and not (tmp_path/'not-created').exists()


def test_start_time_owns_default_even_when_capture_crosses_midnight(tmp_path):
    clocks = iter(['2026-09-26T23:59:59Z'])
    def time():
        return next(clocks, '2026-09-27T00:00:01Z')
    report = g.capture(tmp_path/'c', IDENT, 'crypto',
                      request=lambda s:g.PublicResponse(s['url'],200,{},body(s)), time=time)
    assert report['as_of_date'] == '2026-09-25'
    assert report['observations'][0]['source_date']=='2026-09-24'
    assert report['date_policy']['max_as_of_date']=='2026-09-25'
    assert report['captured_through']=='2026-09-27T00:00:01Z'


@pytest.mark.parametrize('damage', ['missing','ceiling','zone','rule','legacy-tag','future-version'])
def test_resealed_policy_or_version_cannot_promote_dates(tmp_path, damage):
    _, files, _ = run(tmp_path)
    cap=g.decode(files['capture.json'])
    if damage=='missing': cap.pop('date_policy')
    elif damage=='ceiling': cap['date_policy']['max_as_of_date']='2027-01-01'
    elif damage=='zone': cap['date_policy']['timezone']='Asia/Shanghai'
    elif damage=='rule': cap['date_policy']['rule']='ALL_DATES_ALLOWED'
    elif damage=='legacy-tag': cap['version']=g.LEGACY_VERSION
    else: cap['version']='global-public-context-v3'
    cap['capture_hash']=g.seal(cap); files['capture.json']=g.encoded(cap)
    files.pop('summary.json');files.pop('summary.md')
    with pytest.raises(ValueError): g.replay(files, IDENT, TIME)


@pytest.mark.parametrize('family', list(g.FAMILIES))
def test_legacy_v1_has_no_new_policy_or_render_fields(tmp_path, family):
    report, files, _=run(tmp_path, family)
    # Synthetic v1 fixture keeps its original contract; real archives are also
    # replayed separately during delivery without rewriting their source bytes.
    cap=g.decode(files['capture.json']);cap['version']=g.LEGACY_VERSION;cap.pop('date_policy')
    cap['capture_hash']=g.seal(cap);files['capture.json']=g.encoded(cap)
    expected=deepcopy(report);expected['version']=g.LEGACY_VERSION
    expected['capture_hash']=cap['capture_hash'];expected.pop('date_policy')
    files['summary.json']=g.encoded(expected);files['summary.md']=g.render(expected).encode()
    assert g.replay(files, IDENT, TIME)==expected
    assert '日期资格（' not in g.render(expected)


def test_v1_same_day_stays_rejected_even_at_later_replay_cutoff(tmp_path):
    at='2026-09-25T23:27:00Z';root=tmp_path/'c'
    g.capture(root, IDENT, 'fx', request=lambda s:g.PublicResponse(s['url'],200,{},body(s)), time=lambda:at)
    files={p.name:p.read_bytes() for p in root.iterdir()}
    cap=g.decode(files['capture.json']);cap['version']=g.LEGACY_VERSION;cap.pop('date_policy')
    cap['capture_hash']=g.seal(cap);files['capture.json']=g.encoded(cap)
    files.pop('summary.json');files.pop('summary.md')
    with pytest.raises(ValueError, match='GP_RECENT_DATE'):
        g.replay(files, IDENT, '2026-10-08T00:00:00Z')


def test_workflow_reference_slots_and_all_routing_copies_agree():
    src=(Path(__file__).resolve().parents[1]/'.github/workflows/radar-global-public.yml').read_text()
    assert re.findall(r"cron: '([^']+)'", src)==['7 23 * * *','27 23 * * *','37 1 * * *','57 1 * * *']
    routes=re.findall(r"github.event.schedule == '([^']+)' && '([^']+)'",src)
    expected=[('7 23 * * *','treasury'),('27 23 * * *','fx'),('37 1 * * *','commodities'),('57 1 * * *','crypto')]
    assert routes==expected*3
    assert 'secrets.' not in src and 'contents: write' not in src
