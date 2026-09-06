"""Negative delivery keeps canonical clocks and does not certify invented receipts."""
import json
from datetime import timedelta

import pytest

from decision_kernel.identity import canonical_hash
from test_stock_radar_capture import code, setup
from test_stock_radar_reading import NOW
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def reseal(mod, out, report):
    (out/'index.html').write_bytes(mod['failure_page'](report))
    report['files']={k:v for k,v in mod['inventory'](out).items() if k!='capture.json'}
    report['capture_hash']=canonical_hash({k:v for k,v in report.items() if k!='capture_hash'})
    (out/'capture.json').write_bytes(mod['data'](report))


def test_negative_page_has_identical_clocks_before_and_after_json_roundtrip():
    mod=code()
    report={'failure_category':'REQUEST_FAILED','reason_code':'TRANSPORT_REQUEST_FAILED',
        'planned_issuer_outcomes':[], 'recorded_sector_events_latest_session':0,
        'observed_at':NOW, 'finished_at':NOW+timedelta(seconds=21), 'provenance':mod['SYNTHETIC']}
    assert mod['failure_page'](report)==mod['failure_page'](json.loads(mod['data'](report)))


@pytest.mark.parametrize('kind',['late_request','invented_receipt'])
def test_rehashed_transport_failure_cannot_change_clock_contract(tmp_path,kind):
    mod,_,out,_,_,run=setup(tmp_path)
    def failure(*args):raise OSError('not retained')
    report=run(transport=failure)
    if kind=='late_request':
        report['requests'][0]['requested_at']=(NOW+timedelta(minutes=31)).isoformat()
        report['finished_at']=(NOW+timedelta(minutes=32)).isoformat()
    else:
        report['requests'][0]['received_at']=(NOW+timedelta(seconds=1)).isoformat()
    reseal(mod,out,report)
    with pytest.raises(ValueError):mod['verify'](out)


def test_security_rejection_is_recorded_not_reconstructed_from_discarded_secret(tmp_path):
    mod,_,out,_,_,run=setup(tmp_path)
    report=run(transport=lambda *args:{'Authorization':'dummy-secret'},credential='dummy-secret')
    assert report['reason_code']=='UNSAFE_RESPONSE_NOT_RETAINED'
    assert report['requests'][0]['response_file'] is None
    assert 'dummy-secret' not in (out/'capture.json').read_text()
    replay=mod['verify'](out)
    assert replay['failure_replay']=='RECORDED_FAILURE_ONLY_REMOTE_CAUSE_NOT_REPROVEN'
    assert replay['reason_code']=='UNSAFE_RESPONSE_NOT_RETAINED' and replay['network_calls']==0
