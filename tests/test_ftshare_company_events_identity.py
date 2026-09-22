"""Observed finite identity representation and request-window regressions."""
from datetime import date
import pytest
from decision_kernel.runtime import ftshare_company_events as e
from test_ftshare_company_events import capture, response, row, TICKER, START, END, NOW


@pytest.mark.parametrize('code,ok', [('603507',True),('603507.SH',True),('603507.SZ',False),
    ('000920.SZ',False),('603507.SH.extra',False),('603507.SH ',False)])
def test_change_code_supports_only_exact_documented_or_observed_identity(tmp_path,code,ok):
    c=capture(tmp_path,'holder_changes',response('holder_changes',[row('holder_changes',trade_code=code)]))
    assert c['status']==('COMPLETE' if ok else 'IDENTITY_MISMATCH')


def test_boolean_page_identity_rejected(tmp_path):
    c=capture(tmp_path,raw=response('contracts',pageNum=True))
    assert c['status']=='PAGINATION_MISMATCH'


@pytest.mark.parametrize('invalid', [date(2026,9,23),date(2025,1,1)])
def test_window_rejected_before_network(tmp_path,invalid):
    calls=[]
    with pytest.raises(e.DataError):
        e.prepare(ticker=TICKER,start_date=START,end_date=invalid,output=tmp_path/'all',
            fetch=lambda *a:calls.append(a),clock=lambda:NOW)
    assert calls==[]


def test_pure_context_window_validation():
    with pytest.raises(e.DataError,match='REQUEST_IDENTITY_OR_WINDOW'):
        e.window_context({'family':'contracts','status':'EMPTY'},start_date=END,end_date=START)
