"""Actual receipt qualification and the stock workflow's installed transport."""
from datetime import timedelta
from pathlib import Path
import tomllib

import pytest

from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import hithink_stock_reading as own
from test_hithink_stock_reading_integration import contract_provider
from test_stock_radar_reading import NOW
from test_stock_radar_capture import setup
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def test_stock_workflow_extra_installs_existing_exact_requests_version():
    extras=tomllib.loads(Path('pyproject.toml').read_text())['project']['optional-dependencies']
    request_pin=next(r for r in extras['dump-study'] if r.startswith('requests=='))
    assert request_pin in extras['feeds'] and request_pin in extras['dev']
    text=Path('.github/workflows/hithink-stock-dump-trial.yml').read_text()
    job=text.split('  stock-reading:\n',1)[1].split('  theme-probe:\n',1)[0]
    assert "pip install -e '.[feeds,discovery]'" in job


def test_later_quote_request_cannot_make_future_history_ready_time_valid():
    state,plan,provider,calls=contract_provider()
    times=iter(NOW+timedelta(seconds=i*20) for i in range(100))
    current=NOW
    def request(path,params):
        nonlocal current
        value=provider(path,params)
        current=next(times)
        if path==own.HISTORY:
            value['data']['timestamp']=int((current+timedelta(seconds=1)).timestamp()*1000)
        return value
    with pytest.raises(stock.StockReadingInputError,match='HISTORY_READY_AFTER_ACTUAL_RECEIPT'):
        stock.observe_stock_reading(plan,state,request_json=request,observed_at=NOW,cutoff_clock=lambda:current)
    assert calls[-1][0]==own.HISTORY
    assert not any(path in {own.SNAPSHOT,own.ACTIONS} for path,_ in calls)


def test_future_history_receipt_is_a_rebuildable_data_rejection_not_network_error(tmp_path):
    mod,_,out,_,_,run=setup(tmp_path)
    _,_,provider,calls=contract_provider()
    tick=iter(NOW+timedelta(seconds=i) for i in range(100))
    current=NOW
    def now():
        nonlocal current
        current=next(tick)
        return current
    def request(path,params):
        value=provider(path,params)
        if path==own.HISTORY:
            value['data']['timestamp']=int((current+timedelta(seconds=2)).timestamp()*1000)
        return value
    report=run(reference_inputs=None,transport=request,now=now)
    assert report['reason_code']=='HISTORY_READY_AFTER_ACTUAL_RECEIPT'
    assert report['failure_category']=='DATA_QUALIFICATION_FAILED'
    assert report['requests'][-1]['response_file'] is not None
    assert calls[-1][0]==own.HISTORY
    assert mod['verify'](out)['failure_replay']=='REPRODUCED_FROM_RETAINED_INPUTS'
    assert not (out/'stock-reading.json').exists()
