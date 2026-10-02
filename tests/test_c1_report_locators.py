"""Offline historical-reader fixtures; retired acquisition is not exercised."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import socket
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('c1_locators', ROOT/'.github/scripts/c1-report-locators.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ENV = {'GITHUB_REPOSITORY':m.saved.REPOSITORY, 'GITHUB_SHA':'a'*40, 'GITHUB_RUN_ID':'123',
       'GITHUB_RUN_ATTEMPT':'1', 'GITHUB_REF':'refs/heads/main', 'GITHUB_EVENT_NAME':'workflow_dispatch'}


def payload(spec):
    day = spec['params']['trade_date']
    row = [day, 'synthetic', m.TARGETS[day], '个股研报', 'synthetic author', '光迅科技',
           '002281.SZ', '长江证券', 'synthetic', 'https://example.invalid/report.pdf']
    return {'code':0, 'data':{'fields':list(m.FIELDS), 'items':[row]}, 'count':1}


def retained_fixture(root, *, native=False, invalid_first=False):
    """Construct explicit synthetic saved bytes, never invoke a capture/client."""
    root.mkdir()
    records = []
    start = datetime(2026, 10, 2, tzinfo=timezone.utc)
    for i, request in enumerate(m.plan(native=native)):
        if invalid_first and i:
            records.append({'spec':request, 'status':'NOT_ATTEMPTED_STOP', 'attempts':[]})
            continue
        body = payload(request)
        if native:
            body = {'code':0, 'data':{'fields':['日期','报告PDF链接'],
                    'items':[['2026-04-30','https://example.invalid/report.pdf']]}, 'count':1}
        elif invalid_first:
            body['data']['items'] = [[''] * len(m.FIELDS)] * 114
            body['count'] = 114
        raw = m.common.encoded(body); name = f'raw-{i}-1.json'
        (root/name).write_bytes(raw)
        attempt = {'attempt':1, 'classification':'SUCCESS', 'http_status':200,
                   'requested_at':(start+timedelta(seconds=i*2+1)).isoformat(),
                   'received_at':(start+timedelta(seconds=i*2+2)).isoformat(),
                   'headers':{}, 'business_code':0, 'business_error':None, 'business_msg':None,
                   'body':name, 'bytes':len(raw), 'sha256':m.saved.sha256(raw)}
        records.append({'spec':request, 'status':'SUCCESS', 'attempts':[attempt]})
    manifest = {'pilot':m.NATIVE_PILOT if native else m.PILOT, 'workflow':m.WORKFLOW,
                'identity':ENV, 'plan':m.plan(native=native), 'authority':m.AUTHORITY,
                'started_at':start.isoformat(), 'finished_at':(start+timedelta(seconds=10)).isoformat(),
                'records':records}
    if native: manifest['predecessor'] = m.PREDECESSOR
    manifest['capture_hash'] = m.common.digest(manifest)
    (root/'capture.json').write_bytes(m.common.encoded(manifest))
    result = m.rebuild(root, ENV)
    (root/'summary.json').write_bytes(m.common.encoded(result))
    return result


def test_historical_plan_is_not_an_execution_entry():
    p = m.plan()
    assert len(p) == 2 and {x['params']['trade_date'] for x in p} == {'20260430','20260910'}
    assert all(x['api']=='research_report' and x['params']['ts_code']=='002281.SZ' for x in p)
    assert all(x['params']['inst_csname']=='长江证券' for x in p)
    assert not hasattr(m, 'capture') and not hasattr(m, 'write')
    assert not (ROOT/m.WORKFLOW).exists()


@pytest.mark.parametrize('field,value',[('trade_date','20260930'),('ts_code','600000.SH'),
                                      ('inst_csname','另一券商'),('report_type','行业研报')])
def test_foreign_directory_not_accepted(field,value):
    spec=m.plan()[0]; b=payload(spec); b['data']['items'][0][m.FIELDS.index(field)]=value
    with pytest.raises(ValueError):m.inspect(m.common.encoded(b),spec)


@pytest.mark.parametrize('bad',[False,None,'0',3002])
def test_business_status_requires_integer_zero(bad):
    spec=m.plan()[0]; b=payload(spec); b['code']=bad
    with pytest.raises(ValueError):m.inspect(m.common.encoded(b),spec)


def test_empty_or_ambiguous_is_not_a_model():
    spec=m.plan()[0];b=payload(spec);b['data']['items']=[];b['count']=0
    assert m.inspect(m.common.encoded(b),spec)['status']=='TARGET_NOT_IN_RETURNED_PAGE'
    b=payload(spec);b['data']['items']*=2;b['count']=2
    assert m.inspect(m.common.encoded(b),spec)['status']=='TARGET_AMBIGUOUS'


def test_url_credentials_never_qualify():
    spec=m.plan()[0];b=payload(spec);b['data']['items'][0][-1]='https://user:secret@example.invalid/file.pdf'
    assert m.inspect(m.common.encoded(b),spec)['status']=='URL_UNQUALIFIED'


def test_legacy_empty_projection_remains_unqualified(tmp_path):
    root=tmp_path/'saved';r=retained_fixture(root,invalid_first=True)
    assert [o['status'] for o in r['outcomes']]==['DIRECTORY_UNQUALIFIED','NOT_ATTEMPTED_STOP']
    assert r['logical_queries_attempted']==r['http_receipts']==1
    assert not r['pdf_acquired'] and not r['full_model_qualified']
    assert m.common.encoded(m.rebuild(root,ENV))==(root/'summary.json').read_bytes()


def test_tampered_raw_refused(tmp_path):
    root=tmp_path/'saved';retained_fixture(root)
    (root/'raw-0-1.json').write_bytes(b'{}')
    with pytest.raises(ValueError):m.rebuild(root,ENV)


def test_extra_file_and_wrong_identity_refused(tmp_path):
    root=tmp_path/'saved';retained_fixture(root)
    with pytest.raises(ValueError):m.rebuild(root,{**ENV,'GITHUB_RUN_ID':'124'})
    (root/'extra.json').write_text('{}')
    with pytest.raises(ValueError):m.rebuild(root,ENV)


def test_native_history_keeps_unqualified_status_and_exact_predecessor(tmp_path):
    root=tmp_path/'saved';r=retained_fixture(root,native=True)
    assert r['pilot']==m.NATIVE_PILOT and r['pdf_acquired'] is False
    assert r['outcomes'][0]['request_filter_qualification']=='NOT_CHECKED'
    assert r==m.rebuild(root,ENV)
    manifest=json.loads((root/'capture.json').read_bytes())
    manifest['predecessor']['run_id']+=1;manifest['capture_hash']=m.common.digest(manifest)
    (root/'capture.json').write_bytes(m.common.encoded(manifest))
    with pytest.raises(ValueError,match='predecessor'):m.rebuild(root,ENV)


def test_native_mode_does_not_relax_original_directory_qualification():
    b={'code':0,'data':{'fields':['日期','报告PDF链接'], 'items':[]}, 'count':0}
    assert m.inspect(m.common.encoded(b),m.plan(native=True)[0])['status']=='NATIVE_SCHEMA_RETAINED_NOT_REPORT_QUALIFIED'
    with pytest.raises(ValueError):m.inspect(m.common.encoded(b),m.plan()[0])
    assert len(m.plan())==2 and len(m.plan(native=True))==1


def test_verify_cli_never_requests_or_writes(tmp_path,monkeypatch,capsys):
    root=tmp_path/'saved';retained_fixture(root)
    before={p.name:p.read_bytes() for p in root.iterdir()}
    for key,value in ENV.items():monkeypatch.setenv(key,value)
    monkeypatch.delenv(m.relay.SECRET_ENV,raising=False)
    monkeypatch.setattr(m.relay,'request',lambda *a,**k:pytest.fail('source request'))
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('network'))
    m.main(['verify','--root',str(root)])
    assert before=={p.name:p.read_bytes() for p in root.iterdir()}
    assert 'example.invalid' not in capsys.readouterr().out


def test_capture_cli_is_rejected_before_read_or_write(tmp_path,monkeypatch):
    root=tmp_path/'absent'
    monkeypatch.setattr(m,'rebuild',lambda *a,**k:pytest.fail('reader called'))
    with pytest.raises(SystemExit) as error:m.main(['capture','--root',str(root)])
    assert error.value.code==2 and not root.exists()
