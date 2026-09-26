"""Cross-family failure and page completeness regression tests, fully offline."""
from copy import deepcopy
import pytest
from decision_kernel.runtime import smart_money_reading as reading, smart_money_sources as s
from decision_kernel.runtime import smart_money_view as view
from test_smart_money import offline, captured
from test_smart_money_reading import setup,preserve_as_previous


def test_late_optional_renderer_failure_preserves_other_lanes_and_old_locator(tmp_path,monkeypatch):
    col,base,*_=setup(tmp_path);saved=reading.attach(col,base);refs=preserve_as_previous(col,saved)
    def broken(*a,**kw):raise ValueError('synthetic rendering fault')
    monkeypatch.setattr(view,'browser',broken)
    result=reading.attach(col,saved)
    assert result['lanes']==base['lanes']
    assert result['research']['smart_money']['status']=='OPTIONAL_PUBLICATION_GAP'
    assert result['research']['smart_money']['prior_retained_entry']['entry']['details']==refs


@pytest.mark.parametrize('damage',['wrong_rows','wrong_page_count','float_count'])
def test_declared_pages_must_match_actual_rows(damage):
    req=s.spec('holdings','2026-06-30','2026-06-28','2026-09-26',2)
    obj={'code':0,'success':True,'result':{'count':1001,'pages':2,'data':[{}]}}
    assert s.page_data(obj,req)==([{}],1001,2)
    if damage=='wrong_rows':obj['result']['data']=[]
    elif damage=='wrong_page_count':obj['result']['pages']=1
    else:obj['result']['count']=1001.0
    with pytest.raises(ValueError):s.page_data(obj,req)


def test_top_ten_absence_requires_both_complete_quarters(tmp_path):
    obs,_=captured(tmp_path);hist=view.history(obs)
    key='holdings|2026-03-31';hist['coverage'][key]['complete']=False
    assert view.top_ten_transitions(hist)['status']=='ABSENCE_COMPARISON_UNQUALIFIED'


def test_failed_old_family_does_not_become_zero_holding(tmp_path):
    obs,_=captured(tmp_path);old=view.history(obs)
    later=deepcopy(obs);later['capture_hash']='d'*64
    for p in later['partitions']:
        if p['family']=='holdings':p.update(rows=[],complete=False,normalized_rows=0,failure='SOURCE_UNAVAILABLE')
    newer=view.history(later,old)
    assert len(view.latest_rows(newer,'holdings'))==2
    assert not view.top_ten_transitions(newer)['entries']
