"""Actual capture/rebuild and reader functions with wholly synthetic transport."""
from copy import deepcopy
from datetime import datetime,timedelta
from hashlib import sha256
import io,json,socket,zipfile
from pathlib import Path
import pytest
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import smart_money_sources as s,smart_money_capture as c,smart_money_view as v
from decision_kernel.runtime import smart_money_documents as doc,smart_money_reading as reading
from test_smart_money_continuity import NOW,IDENT,calendar,part,obs,row
from test_radar_company_reading import collector,baseline

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*a,**k):raise AssertionError('unexpected network')
    monkeypatch.setattr(socket.socket,'connect',reject)
    monkeypatch.setattr(socket,'getaddrinfo',reject)


def hkex(channel='SH',period='2026-06-30'):
    fields={'__EVENTTARGET':'','__EVENTARGUMENT':'','__VIEWSTATE':'public-state','__VIEWSTATEGENERATOR':'g',
      'today':'2026/09/26','sortBy':'stockcode','sortDirection':'asc','originalShareholdingDate':'2026/09/26',
      'alertMsg':'','txtShareholdingDate':period.replace('-','/')}
    form='<form id="form1" method="post" action="./mutualmarket.aspx?t='+channel.lower()+'">'+''.join(f'<input name="{k}" value="{val}">' for k,val in fields.items())+'</form>'
    return (form+f'<h2 class="ccass-heading">Shareholding Date: {period.replace("-","/")}</h2>'
     '<table id="mutualmarket-result"><thead><tr><th>Stock Code</th><th>Name</th><th>Shareholding in CCASS</th>'
     f'<th>Percent {"SSE" if channel=="SH" else "SZSE"}</th></tr></thead><tbody><tr>'+
     ''.join('<td><div class="mobile-list-body">'+x+'</div></td>' for x in ['90001','SYNTHETIC #'+('600001' if channel=='SH' else '000001'),'1,000','0.01%'])+
     '</tr></tbody></table>').encode()


def transport(spec):
    f=spec['family']
    if f=='calendar':return 200,s.encoded(calendar())
    if f=='north_holdings':
        ch,*period=spec['partition'].split('@');return 200,hkex(ch,period[0] if period else '2026-06-30')
    if f in ('hot_money','institutional'):
        d=spec['partition'];stamp=int(datetime.fromisoformat(d+'T00:00:00+08:00').timestamp())*1000
        body={'code':0,'data':{'trade_date':d,'timestamp':stamp,'board_type':'hot_money' if f=='hot_money' else 'org',
             'count':0,'stock_count':0,'stock_items':[],'hot_money_items':[]}}
    elif f=='northbound':
        body={'code':200,'data':{'date':spec['params']['date'],'currency':'CNY',
             'total_amount':'100','channels':{'SH':{'amount':'60'},'SZ':{'amount':'40'}}}}
    elif f in ('seats','executives'):
        body={'code':200,'data':{'pageNum':spec['page'],'pageSize':200,'records':[],'total':0,'pages':0}}
    elif f=='forecasts':body={'pageNo':spec['page'],'data':[],'hits':0,'TotalPage':0}
    else:body={'success':True,'code':0,'result':{'data':[],'count':0,'pages':0}}
    return 200,s.encoded(body)


def captured(tmp,fetch=transport,previous=None):
    ticks=iter((datetime.fromisoformat(NOW)+timedelta(seconds=i/10)).isoformat() for i in range(3000))
    output=tmp/'capture'
    result=c.capture(output,IDENT,previous_state=previous,transport=fetch,clock=lambda:next(ticks),
       monotonic=lambda:0,sleep=lambda x:None)
    files={p.name:p.read_bytes() for p in output.iterdir()}
    return result,files


def test_real_capture_and_rebuild_all_twelve_families(tmp_path):
    result,files=captured(tmp_path)
    rebuilt=c.replay(files,IDENT,cutoff='2026-09-26T03:00:00Z')
    assert result==rebuilt and result['status']=='READY'
    assert {p['family'] for p in result['partitions']}==set(s.FAMILIES)
    assert result['requests']==33 and result['source_calls_during_replay']==0
    h=v.history(result);chunks,meta=v.encode_chunks(h)
    assert v.decode_chunks(meta,chunks)==h
    st=v.state(result);assert st['last_source_run_id']==IDENT['run_id']


@pytest.mark.parametrize('kind',['path','hash','bytes','index','request_day','future_clock','policy','extra_file','wrong_run'])
def test_manifest_rehash_cannot_bypass_source_identity(tmp_path,kind):
    _,files=captured(tmp_path);m=s.decode(files['capture.json']);r=m['records'][1]
    if kind=='path':r['body']='../../steal'
    elif kind=='hash':r['sha256']='0'*64
    elif kind=='bytes':r['bytes']+=1
    elif kind=='index':r['index']=True
    elif kind=='request_day':r['request']['params']['date']='2026-09-25'
    elif kind=='future_clock':r['received_at']='2026-10-01T00:00:00Z'
    elif kind=='policy':m['previous_state']={'version':s.VERSION,'target_date':'2026-09-26','policy_stops':['HT']}
    elif kind=='extra_file':files['execute.py']=b'print("not executed")'
    elif kind=='wrong_run':m['identity']['run_id']+=1
    m['capture_hash']=canonical_hash({k:x for k,x in m.items() if k!='capture_hash'});files['capture.json']=s.encoded(m)
    with pytest.raises((ValueError,KeyError,TypeError)):c.replay(files,IDENT,cutoff='2026-09-26T03:00:00Z')


def test_calendar_failure_keeps_public_sources_and_pending_start(tmp_path):
    def fetch(spec):
        if spec['family']=='calendar':return 503,b'upstream unavailable'
        return transport(spec)
    result,_=captured(tmp_path,fetch)
    assert result['status']=='PARTIAL_WITH_EXPLICIT_GAPS' and result['calendar_pending_since']=='2026-09-26'
    assert any(p['family']=='holdings' and p['complete'] for p in result['partitions'])
    assert not any(p['family']=='hot_money' for p in result['partitions'])
    assert v.state(result)['late_confirmation_complete'] is False


def test_policy_failure_stops_same_provider_but_not_others(tmp_path):
    calls=[]
    def fetch(spec):
        calls.append(spec['provider'])
        if spec['family']=='hot_money':return 403,b'forbidden'
        return transport(spec)
    result,files=captured(tmp_path,fetch)
    assert calls.count('HT')==2 and 'FT' in calls and 'EM' in calls
    assert result['policy_stops']==['HT']
    assert c.replay(files,IDENT,cutoff='2026-09-26T03:00:00Z')==result


@pytest.mark.parametrize('damage',['date','header','form','code','future'])
def test_hkex_schema_never_uses_default_request_day(damage):
    raw=hkex();request=s.spec('north_holdings','SH','2026-06-28','2026-09-26')
    if damage=='date':raw=raw.replace(b'Shareholding Date:',b'Download Date:')
    elif damage=='header':raw=raw.replace(b'Percent SSE',b'Percent SZSE')
    elif damage=='form':raw=raw.replace(b'value="2026/06/30"',b'value="2026/09/26"')
    elif damage=='code':raw=raw.replace(b'#600001',b'NONAME')
    else:raw=raw.replace(b'2026/06/30',b'2026/12/31')
    with pytest.raises(ValueError):doc.northbound_table(raw,request)


def test_hkex_actual_quarter_not_page_default_date():
    request=s.spec('north_holdings','SH','2026-06-28','2026-09-26')
    result=doc.northbound_table(hkex(),request)
    assert result['period']=='2026-06-30'
    with pytest.raises(ValueError):doc.northbound_table(hkex(),s.spec('north_holdings','SH@2026-03-31','2026-06-28','2026-09-26'))
    form=doc.post_form(hkex(),'SH','2026-03-31');assert form['txtShareholdingDate']=='2026/03/31'


def test_duplicate_rows_across_pages_prevent_full_coverage():
    scope={'family':'holdings','partition':'2026-06-30','begin':'2026-06-28','end':'2026-09-26'}
    base={'SECUCODE':'600001.SH','SECURITY_CODE':'600001','END_DATE':'2026-06-30','NOTICE_DATE':'2026-08-30',
          'HOLDER_NAME':'SYNTHETIC','HOLD_NUM':100}
    rows=[{**base,'HOLDER_CODE':str(i)} for i in range(1000)]
    files={};records=[]
    for i,rr in enumerate((rows,rows[:500])):
        req=s.spec(*[scope[k] for k in ('family','partition','begin','end')],i+1)
        raw=s.encoded({'code':0,'success':True,'result':{'data':rr,'count':1500,'pages':2}})
        name=f'raw-{i:04d}.body';files[name]=raw;records.append({'index':i,'request':req,'body':name,'http_status':200})
    result=c._parse_partition(records,files,scope)
    assert not result['complete'] and result['failure']=='DUPLICATE_SOURCE_ROWS'


def test_disclosed_own_document_revision_not_old_vintage_certification(monkeypatch):
    import pypdf
    class Page:
        def extract_text(self):return '国信证券000651预计2026-2028年归母净利润为283/297/316亿（前值为352/368/-亿）'
    class Reader:
        def __init__(self,*a,**k):self.pages=[Page()];self.is_encrypted=False
    monkeypatch.setattr(pypdf,'PdfReader',Reader)
    report={'ticker':'000651.SZ','actor_name':'国信证券','actor_id':'BROKER:X','disclosed':'2026-09-24','values':{'report_id':'AP202609240000000001'}}
    result=doc.reported_revisions(b'%PDF-synthetic',report)
    assert len(result['revisions'])==2
    assert all(r['old_original_report']=='NOT_INDEPENDENTLY_RECOVERED' for r in result['revisions'])
    assert [r['target_year'] for r in result['revisions']]==[2026,2027]


def setup_reader(tmp_path):
    result,files=captured(tmp_path)
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in files.items():z.writestr(name,raw)
    raw=b.getvalue();run={'id':IDENT['run_id'],'head_sha':IDENT['code_commit'],'head_branch':'main','path':s.WORKFLOW,
       'repository':{'full_name':IDENT['repository']},'head_repository':{'full_name':IDENT['repository']},
       'event':'workflow_dispatch','run_attempt':1,'status':'completed','conclusion':'success',
       'created_at':'2026-09-26T01:59:00Z','updated_at':'2026-09-26T02:05:00Z'}
    job={'name':'capture-smart-money','id':42,'head_sha':run['head_sha'],'run_id':run['id'],'run_attempt':1,'conclusion':'success'}
    art={'id':900,'name':f"smart-money-{run['id']}-1",'size_in_bytes':len(raw),'digest':'sha256:'+sha256(raw).hexdigest(),
         'expired':False,'workflow_run':{'id':run['id'],'head_sha':run['head_sha']}}
    from test_radar_company_reading import API
    api=API({reading.QUERY:{'total_count':1,'workflow_runs':[run]},f"actions/runs/{run['id']}":run,
        f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100":{'total_count':1,'jobs':[job]},
        f"actions/runs/{run['id']}/artifacts?per_page=100":{'total_count':1,'artifacts':[art]}},raw)
    col=collector(api,tmp_path);col.now=lambda:'2026-09-26T03:00:00Z';col.previous=None;col.previous_commit=None
    package,_,_=baseline(col)
    return col,package,run,job,art,result


def test_normal_reading_replays_zip_retains_base_and_new_navigation(tmp_path):
    col,base,_,_,_,obs=setup_reader(tmp_path)
    result=reading.attach(col,base)
    assert result['lanes']==base['lanes']
    assert result['research']['smart_money']['capture_hash']==obs['capture_hash']
    assert result['research']['smart_money']['status']=='READY'
    assert b'smart-money.md' in col.files['README.md']


@pytest.mark.parametrize('damage',['job_failed','job_wrong_head','artifact_hash','artifact_expired','foreign','run_pending'])
def test_reading_failure_is_not_zero_or_an_erased_baseline(tmp_path,damage):
    col,base,run,job,art,_=setup_reader(tmp_path)
    if damage=='job_failed':job['conclusion']='failure'
    elif damage=='job_wrong_head':job['head_sha']='b'*40
    elif damage=='artifact_hash':art['digest']='sha256:'+'0'*64
    elif damage=='artifact_expired':art['expired']=True
    elif damage=='foreign':run['head_repository']['full_name']='another/repo'
    elif damage=='run_pending':run['status']='in_progress';run['conclusion']=None
    result=reading.attach(col,base)
    assert result['lanes']==base['lanes']
    status=result['research']['smart_money']['status']
    assert status!='READY'
    if damage=='job_failed':assert status=='PARTIAL_FAILED_EXECUTION'


def test_bound_pending_capture_recovery_cannot_deadlock_on_skip_attempt(tmp_path):
    col,base,old,job,art,_=setup_reader(tmp_path)
    rid=old['id']+1;latest={**deepcopy(old),'id':rid,'created_at':'2026-09-26T02:06:00Z','updated_at':'2026-09-26T02:08:00Z'}
    control={'run_id':rid,'code_commit':old['head_sha'],'decision':'SKIP_AWAITING_PRIOR_CAPTURE_READING','pending_source_run_id':old['id']}
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('control.json',json.dumps(control))
    raw=b.getvalue();ctrl={'id':901,'name':f'smart-money-control-{rid}-1','size_in_bytes':len(raw),
      'digest':'sha256:'+sha256(raw).hexdigest(),'expired':False,'workflow_run':{'id':rid,'head_sha':old['head_sha']}}
    original=col.api.raw_archive
    def archive(a):col.api.calls+=1;return raw if a['id']==901 else original
    col.api.archive=archive
    col.api.responses[reading.QUERY]={'total_count':2,'workflow_runs':[latest,old]}
    col.api.responses[f'actions/runs/{rid}']=latest
    col.api.responses[f'actions/runs/{rid}/attempts/1/jobs?per_page=100']={'total_count':1,'jobs':[{**job,'run_id':rid}]}
    col.api.responses[f'actions/runs/{rid}/artifacts?per_page=100']={'total_count':1,'artifacts':[ctrl]}
    result=reading.attach(col,base)['research']['smart_money']
    assert result['status']=='READY' and result['latest_attempt']['id']==rid
    overview=json.loads(col.files[reading.PREFIX+'overview.json'])
    assert overview['origins'][result['capture_hash']]['run']['id']==old['id']


def test_optional_composition_failure_preserves_siblings_and_old_locator(tmp_path,monkeypatch):
    col,base,_,_,_,_=setup_reader(tmp_path)
    old={'status':'READY','details':{'some':'old'}};col.previous={'research':{'smart_money':old}};col.previous_commit='b'*40
    monkeypatch.setattr(reading,'previous',lambda col:(None,'NO_PREVIOUS_CAPTURE'))
    def fail(*a,**k):raise ValueError('rendering failure')
    monkeypatch.setattr(v,'browser',fail)
    result=reading.attach(col,base)
    assert result['lanes']==base['lanes']
    assert result['research']['smart_money']['status']=='OPTIONAL_PUBLICATION_GAP'
    assert result['research']['smart_money']['prior_retained_entry']=={'commit':'b'*40,'entry':old}


def test_report_pairs_never_compare_different_issuers_as_one_company():
    rows=[]
    for code,date in [('600001.SH','2026-09-20'),('600002.SH','2026-09-21'),('600001.SH','2026-09-22')]:
        rows.append({'actor_id':'BROKER:X','ticker':code,'disclosed':date,
                     'values':{'eps_slots':['1',None,None],'report_id':code+date}})
    selected=doc.select_reports(rows)
    assert len(selected)==3
    assert [r['disclosed'] for r in selected if r['ticker']=='600001.SH']==['2026-09-22','2026-09-20']
