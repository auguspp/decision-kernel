"""Optional industry delivery failures must not erase other saved modules."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import industry_fundamentals as source
from decision_kernel.runtime import industry_fundamentals_reading as reader

AT='2026-10-08T01:00:00+00:00'

def fixture(tmp_path, monkeypatch):
    baseline=m.assemble(code_commit='a'*40, checked_at=AT, check_started_at=AT,
        lanes={}, research={'handoffs': {'active': []}, 'unrelated': {'status':'KEPT'}},
        capabilities=[], refresh_identity={})
    c=delivery.Collector(SimpleNamespace(calls=0,max_calls=1000),'a'*40,tmp_path,now=lambda:AT)
    c.files={'current-state.json':m.read_package_bytes(baseline),
             'README.md':m.render_summary(baseline).encode()+b'\nother module retained\n',
             'other.json':b'original'}
    c.archive_cache={1: ({'old': b'old'}, {'id': 1})}
    observation={'version':source.VERSION,'coverage':{'available_families':1},'cutoff':AT,'series':[]}
    def capture(col):
        col.api.calls+=1  # Reading occurred; rollback must not refund it.
        col.files['sources/new.zip']=b'new'
        col.archive_cache[2]=({'new':b'new'}, {'id':2})
        return {'status':'AVAILABLE','observation':observation,'capture_hash':'b'*64}
    monkeypatch.setattr(reader,'previous',lambda _: (None,'NO_PREVIOUS_CAPTURE'))
    monkeypatch.setattr(reader,'native',capture)
    monkeypatch.setattr(source,'compare',lambda *_: {})
    monkeypatch.setattr(source,'render',lambda *_: 'industry data')
    return c,baseline


@pytest.mark.parametrize('failure',['compare','render','retain-second','capacity'])
def test_optional_failure_keeps_other_modules_and_current_gap(tmp_path,monkeypatch,failure):
    c,b=fixture(tmp_path,monkeypatch); original=deepcopy(b); files=dict(c.files); cache=deepcopy(c.archive_cache)
    def fail(*args,**kwargs): raise ValueError('PRIVATE_SOURCE_BODY_MUST_NOT_LEAK')
    if failure in ('compare','render'): monkeypatch.setattr(source,failure,fail)
    elif failure=='retain-second':
        retain=c.retain
        def second(path,raw):
            result=retain(path,raw)
            if path==reader.DETAIL: fail()
            return result
        monkeypatch.setattr(c,'retain',second)
    else:
        # Fits the original root and bounded inline gap, not a newly retained body.
        monkeypatch.setattr(source,'render',lambda *_: 'x'*16000)
        monkeypatch.setattr(delivery,'MAX_RETAINED_OUTPUT',sum(map(len,files.values()))+6000)
    out=reader.attach(c,b)
    m.validate_read_package(out)
    assert b==original and out['lanes']==b['lanes'] and out['research']['unrelated']==b['research']['unrelated']
    assert out['research']['industry_fundamentals']['status']=='INDUSTRIAL_ATTACHMENT_GAP_NOT_QUIET'
    assert 'details' not in out['research']['industry_fundamentals']
    assert c.archive_cache==cache and c.api.calls==1
    assert c.files['other.json']==files['other.json']
    assert not {reader.REPORT,reader.DETAIL,'sources/new.zip'} & c.files.keys()
    assert b'other module retained' in c.files['README.md']
    assert b'PRIVATE_SOURCE_BODY' not in b''.join(c.files.values())
    assert '产业读取未完成'.encode() in c.files['README.md']
    assert m.json_bytes(out)==m.json_bytes(__import__('json').loads(c.files['current-state.json']))


def test_no_space_even_for_gap_restores_exact_baseline(tmp_path,monkeypatch):
    c,b=fixture(tmp_path,monkeypatch); files=dict(c.files); cache=deepcopy(c.archive_cache)
    monkeypatch.setattr(delivery,'MAX_RETAINED_OUTPUT',sum(map(len,files.values())))
    out=reader.attach(c,b)
    assert out is b and c.files==files and c.archive_cache==cache and c.api.calls==1


def test_publication_reserve_is_not_consumed_by_gap(tmp_path,monkeypatch):
    c,b=fixture(tmp_path,monkeypatch); files=dict(c.files); cache=deepcopy(c.archive_cache)
    c.api.max_calls=len(files)+5
    out=reader.attach(c,b)
    assert out is b and c.files==files and c.archive_cache==cache and c.api.calls==1


def test_valid_attachment_keeps_body_and_uses_existing_root(tmp_path,monkeypatch):
    c,b=fixture(tmp_path,monkeypatch)
    out=reader.attach(c,b)
    m.validate_read_package(out)
    assert out['research']['industry_fundamentals']['status']=='AVAILABLE'
    assert reader.REPORT in c.files and reader.DETAIL in c.files
    assert b'other module retained' in c.files['README.md'] and c.api.calls==1


def test_invalid_core_is_not_hidden_as_optional_gap(tmp_path,monkeypatch):
    c,b=fixture(tmp_path,monkeypatch); b['investment_authority']='TRADE'
    with pytest.raises(ValueError): reader.attach(c,b)
    assert c.api.calls==0


def test_previous_capture_locator_survives_repeated_attachment_failure(tmp_path,monkeypatch):
    c,b=fixture(tmp_path,monkeypatch)
    value={'observation':{'version':source.VERSION},'last_capture_hash':'b'*64}
    report={'projection':value,'projection_hash':reader.canonical_hash(value)}
    raw=m.json_bytes(report)
    ref={'read_path':reader.REPORT,'bytes':len(raw),'sha256':m.sha256(raw),'git_blob':m.blob_sha(raw),
         'read_ref_rule':'USE_THE_SAME_PINNED_READING_COMMIT'}
    location={'commit':'c'*40,'file':ref}
    c.previous={'research':{'industry_fundamentals':{'details':{'json':ref}}}}
    c.previous_commit='c'*40
    def fail(*_): raise ValueError('not disclosed')
    monkeypatch.setattr(source,'render',fail)
    out=reader.attach(c,b)
    assert out['research']['industry_fundamentals']['previous_saved_reading']==location
    c.previous=out; c.previous_commit='d'*40
    again=reader.attach(c,b)
    assert again['research']['industry_fundamentals']['previous_saved_reading']==location


def test_previous_reader_follows_exact_saved_locator_and_checks_bytes(tmp_path,monkeypatch):
    # No fixture monkeypatch: exercise the original previous() reader directly.
    value={'observation':{'version':source.VERSION},'last_capture_hash':'b'*64}
    raw=m.json_bytes({'projection':value,'projection_hash':reader.canonical_hash(value)})
    ref={'read_path':reader.REPORT,'bytes':len(raw),'sha256':m.sha256(raw),'git_blob':m.blob_sha(raw),
         'read_ref_rule':'USE_THE_SAME_PINNED_READING_COMMIT'}
    def file(path,commit):
        assert (path,commit)==(reader.REPORT,'c'*40)
        return raw
    c=SimpleNamespace(previous={'research':{'industry_fundamentals':{
        'previous_saved_reading':{'commit':'c'*40,'file':ref}}}},previous_commit='d'*40,
        api=SimpleNamespace(file=file))
    old,state=reader.previous(c)
    assert old==value and state=='EXACT_PREVIOUS_READING_'+'c'*40
    ref['sha256']='0'*64
    assert reader.previous(c)==(None,'PREVIOUS_CAPTURE_UNAVAILABLE_NOT_NO_CHANGE')


@pytest.mark.parametrize('failure',['render','retain-second','capacity','api-capacity'])
def test_breadth_failure_isolated_before_next_industrial_reader(tmp_path,monkeypatch,failure):
    from decision_kernel.runtime import industry_breadth_reading as breadth
    c,b=fixture(tmp_path,monkeypatch); files=dict(c.files); cache=deepcopy(c.archive_cache)
    monkeypatch.setattr(breadth,'history',lambda *_:{'status':'NO_HISTORY','snapshot':None})
    def capture(col):
        col.api.calls+=1; col.files['sources/breadth.zip']=b'breadth'
        col.archive_cache[3]=({'new':b'new'},{'id':3})
        return {'status':'SYNTHETIC_NOT_QUIET','snapshot':None}
    monkeypatch.setattr(breadth,'native',capture)
    monkeypatch.setattr(breadth,'render',lambda *_:'synthetic breadth')
    def fail(*_): raise ValueError('PRIVATE_SOURCE_BODY_MUST_NOT_LEAK')
    if failure=='render': monkeypatch.setattr(breadth,'render',fail)
    elif failure=='retain-second':
        retain=c.retain
        def second(path,raw):
            result=retain(path,raw)
            if path==breadth.DETAIL: fail()
            return result
        monkeypatch.setattr(c,'retain',second)
    elif failure=='capacity':
        monkeypatch.setattr(breadth,'render',lambda *_:'x'*16000)
        monkeypatch.setattr(delivery,'MAX_RETAINED_OUTPUT',sum(map(len,files.values()))+6000)
    else: c.api.max_calls=len(files)+5
    out=breadth.attach(c,b)
    assert c.archive_cache==cache and c.api.calls==1 and c.files['other.json']==b'original'
    assert not {breadth.REPORT,breadth.DETAIL,'sources/breadth.zip'} & c.files.keys()
    if failure=='api-capacity':
        assert out is b and c.files==files
        return
    assert out['research']['industry_breadth']['status']=='INDUSTRY_BREADTH_ATTACHMENT_GAP_NOT_QUIET'
    # A sibling can still append its valid reading, without hiding this gap.
    monkeypatch.setattr(delivery,'MAX_RETAINED_OUTPUT',128*1024*1024)
    final=reader.attach(c,out)
    assert final['research']['industry_fundamentals']['status']=='AVAILABLE'
    assert final['research']['industry_breadth']==out['research']['industry_breadth']
    assert b'PRIVATE_SOURCE_BODY' not in b''.join(c.files.values())
    m.validate_read_package(final)
