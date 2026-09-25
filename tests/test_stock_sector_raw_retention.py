"""Exact Sector input retention; synthetic market data and no network access."""
from __future__ import annotations

import json

import pytest

from test_sector_radar_audit import prohibit_network
from test_stock_market_expression import _one_unknown_plan
from test_stock_radar_capture import code, setup, stock_environment
from test_stock_radar_reading import NOW, ROOT, synthetic_references


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


@pytest.mark.parametrize('retain_original', [True, False])
def test_sector_context_capture_and_replay_keep_exact_supplied_bytes(tmp_path, retain_original):
    state, _, _, _, _, _, result = _one_unknown_plan()
    mod, state_dir, out, calls, _, run = setup(tmp_path)
    raw = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    assert raw != mod['data'](result), 'Fixture must reproduce the real formatting difference.'
    before = mod['inventory'](state_dir)
    kwargs = {'sector_result_raw': raw} if retain_original else {}
    report = run(sector_result=result, **kwargs,
                 reference_inputs=synthetic_references(state, ['600999.SH']))
    assert report['status'] == mod['COMPLETE'], report
    assert report['provenance'] == mod['SYNTHETIC']
    expected = raw if retain_original else mod['data'](result)
    assert (out/'inputs/sector-result.json').read_bytes() == expected
    assert mod['inventory'](state_dir) == before
    rebuilt = mod['verify'](out)
    assert rebuilt['status'] == 'ORIGINAL_STOCK_INPUTS_AND_PAGE_REBUILT'
    assert rebuilt['network_calls'] == 0
    assert rebuilt['requests_replayed'] == len(calls)
    projection = mod['read'](out/'stock-reading.json')['projection']
    assert projection['surfaced_stocks'][0]['business_linkage_status'] == 'UNKNOWN'
    assert projection['business_benefit_established'] is False
    assert projection['recommendation'] is None
    assert projection['research_authority'] == projection['investment_authority'] == 'NONE'


@pytest.mark.parametrize('raw', [b'{}', b'not json', '{}', b'null'])
def test_mismatched_sector_bytes_fail_before_any_transport_or_output(tmp_path, raw):
    # Byte/parsed-value agreement is checked before state loading. This sentinel
    # is not a qualified Sector result; the two real capture/replay cases above
    # retain that separate integration responsibility.
    mod = code()
    result = {'synthetic_preflight': True}
    out, calls = tmp_path/'reading', []
    reason = 'Expecting value' if raw == b'not json' else 'raw Sector context'
    with pytest.raises(ValueError, match=reason):
        mod['capture'](ROOT, tmp_path/'unused-state', out, observed_at=NOW,
            transport=lambda *args: calls.append(args), workflow={'test':'raw-preflight'},
            sector_result=result, sector_result_raw=raw)
    assert calls == []
    assert not out.exists()


def test_live_cli_passes_original_sector_bytes_not_a_reserialized_copy(tmp_path, monkeypatch):
    mod = code()  # CLI routing needs no synthetic market plan or state bundle.
    env = stock_environment()
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setenv('GITHUB_WORKSPACE', str(ROOT))
    monkeypatch.setenv('HITHINK_FINANCE_API_KEY', 'SYNTHETIC-CLI-CREDENTIAL')
    monkeypatch.delenv('GITHUB_STEP_SUMMARY', raising=False)
    root = tmp_path/'cli'
    (root/'market-context').mkdir(parents=True)
    # This test mocks bound_state and capture; the sentinel is routing-only,
    # not a qualified Sector result or a production authority claim.
    raw = b'{\n  "synthetic_context": true\n}\n'
    (root/'market-context/result.json').write_bytes(raw)
    mod['write'](root/'request.json', mod['intent'](env, NOW.isoformat()))
    seen = []
    def captured(*args, **kwargs):
        seen.append(kwargs)
        assert kwargs['sector_result'] == json.loads(raw)
        assert kwargs['sector_result_raw'] == raw
        assert kwargs['company_manifest'] == mod['LIVE_COMPANIES']
        return {'status': mod['COMPLETE']}
    scope = mod['main'].__globals__
    monkeypatch.setitem(scope, 'capture', captured)
    monkeypatch.setitem(scope, 'bound_state', lambda *args: None)
    assert mod['main'](['capture', '--root', str(root)]) == 0
    assert len(seen) == 1
