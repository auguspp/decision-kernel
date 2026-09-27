"""Regression for the real #615 publication failure; synthetic prices, no HTTP.

Yahoo metadata contains JSON fractional numbers. The source decoder intentionally
keeps Decimal while its native saved JSON uses exact strings. Both the initial
attachment and later prior-R replay must respect that serialization boundary.
"""
from copy import deepcopy
from decimal import Decimal
import json
import socket

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as m, global_market_reading as r
from decision_kernel.runtime import global_public_context as g
from test_global_market_reading import ready, previous, projection
import test_global_public_reading as fixtures


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail('canonical reading regression attempted source networking')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def decimal_metadata(monkeypatch):
    original = fixtures.body

    def response(spec):
        raw = original(spec)
        if spec['family'] != 'commodities':
            return raw
        obj = json.loads(raw)
        obj['chart']['result'][0]['meta'].update(
            regularMarketPrice='PRICE_LITERAL', chartPreviousClose='PREVIOUS_LITERAL',
            nested={'precise': ['PRECISE_LITERAL', None, 2], 'label': 'preserve me'})
        # Literal JSON numbers exercise the real parse_float=Decimal path, not
        # pre-stringified fake metadata. No binary float conversion in the fixture.
        return (json.dumps(obj).replace('"PRICE_LITERAL"', '101.25')
                .replace('"PREVIOUS_LITERAL"', '99.75')
                .replace('"PRECISE_LITERAL"', '0.123456789012345678901234567890')).encode()

    monkeypatch.setattr(fixtures, 'body', response)


@pytest.mark.parametrize('restore_from_git', [False, True])
def test_decimal_metadata_uses_native_canonical_json_without_losing_six_family_custody(
        tmp_path, monkeypatch, restore_from_git):
    c, baseline, relay = ready(tmp_path, monkeypatch)
    decimal_metadata(monkeypatch)
    public = fixtures.add_public(c, tmp_path)
    original_baseline = deepcopy(baseline)
    run, artifact, files, native = public['commodities']
    meta = native['outcomes'][0]['metadata']
    assert isinstance(meta['regularMarketPrice'], Decimal)
    assert meta['nested']['precise'][0] == Decimal('0.123456789012345678901234567890')
    # The old attachment sent this object to the plain package JSON encoder.
    with pytest.raises(TypeError, match='Decimal'):
        m.json_bytes(native)
    assert g.encoded(native) == files['summary.json']

    result = r.attach(c, baseline)
    m.validate_read_package(result)
    assert result['research']['global_market']['status'] == 'SAVED_CONTEXT'
    assert baseline == original_baseline and result['lanes'] == baseline['lanes']
    if restore_from_git:
        previous(c, result)
        for _, a, _, _ in {**relay, **public}.values():
            a['expired'] = True
        result = r.attach(c, result)
        m.validate_read_package(result)
        assert result['research']['global_market']['status'] == 'SAVED_CONTEXT'
        assert not any(isinstance(x, tuple) and x[0] == 'archive' for x in c.api.reads)

    value = json.loads(c.files[r.REPORT])
    p = projection(c)
    assert value['projection_hash'] == canonical_hash(p)
    assert set(p['families']) == set(r.FAMILIES) and not p['prior_read_gaps']
    assert all(v['snapshot'] for v in p['families'].values())
    if restore_from_git:
        assert all(v['latest_read_status'] == 'REUSED_RETAINED_CAPTURE' for v in p['families'].values())
    snap = p['families']['commodities']['snapshot']
    saved = snap['report']
    assert saved == json.loads(files['summary.json'])
    assert g.encoded(saved) == files['summary.json']
    assert saved['outcomes'][0]['metadata']['regularMarketPrice'] == '101.25'
    assert saved['outcomes'][0]['metadata']['nested'] == {
        'precise': ['0.123456789012345678901234567890', None, 2], 'label': 'preserve me'}
    assert c.files[snap['archive']['read_path']] == c.api.archives[artifact['id']]
    assert snap['run']['id'] == run['id']
    assert all(row['change'] is None for row in saved['observations'])
    assert all(v['snapshot']['report']['source_calls_during_replay'] == 0 for v in p['families'].values())
    assert p['authority'] == g.AUTHORITY and p['source_calls'] == 0
    assert not p['complete_global_coverage']
