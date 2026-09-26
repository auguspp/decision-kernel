"""Final finite protocol clarification; no research conclusion, redirects or credentials."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, os, re, requests, time
from bs4 import BeautifulSoup

root=Path(os.environ['RUNNER_TEMP'])/'smart-money-probe';root.mkdir(exist_ok=False)
assert os.environ['GITHUB_REF']=='refs/heads/work/smart-money-20260926' and os.environ['GITHUB_RUN_ATTEMPT']=='1'
assert datetime.now(timezone.utc)<datetime(2026,9,27,tzinfo=timezone.utc)
rows=[];stopped=set()
def get(name,url,params):
    host=url.split('/')[2]
    assert host in {'www3.hkexnews.hk','datacenter-web.eastmoney.com','reportapi.eastmoney.com','pdf.dfcfw.com'}
    if host in stopped:return None
    record={'id':name,'url':url,'params':params,'requested_at':datetime.now(timezone.utc).isoformat()}
    try:
        with requests.Session() as s:
            s.trust_env=False
            with s.get(url,params=params,allow_redirects=False,stream=True,timeout=(10,25),headers={'Accept-Encoding':'identity','User-Agent':'Mozilla/5.0 DecisionKernel-public-source-review'}) as r:
                assert r.url==requests.Request('GET',url,params=params).prepare().url
                chunks=[];size=0
                for c in r.iter_content(65536):
                    size+=len(c);assert size<=4*1024*1024;chunks.append(c)
                raw=b''.join(chunks);status=r.status_code
        record.update(received_at=datetime.now(timezone.utc).isoformat(),status=status,bytes=len(raw),sha256=sha256(raw).hexdigest())
        (root/(name+'.body')).write_bytes(raw)
        if status in {401,403,429} or 300<=status<400:stopped.add(host)
        rows.append(record)
        return raw if status==200 else None
    except Exception as e:
        record.update(error_type=type(e).__name__,received_at=datetime.now(timezone.utc).isoformat());rows.append(record);return None
for channel in ['sh','sz']:
    # Exact target read from the retained public HTML meta refresh, not a host guess.
    raw=get('hkex-'+channel,'https://www3.hkexnews.hk/sdw/search/mutualmarket.aspx',{'t':channel})
    if raw:
        h=BeautifulSoup(raw,'html.parser')
        print('HKEX',channel,json.dumps({'title':h.title.get_text(' ',strip=True) if h.title else None,
          'inputs':[{k:t.get(k) for k in ('id','name','type','value')} for t in h.select('input')],
          'forms':[{k:f.get(k) for k in ('method','action','id')} for f in h.select('form')],
          'tables':[str(t)[:8000] for t in h.select('table')[:1]],
          'dates':[str(x) for x in h.find_all(id=re.compile('Date',re.I))][:20]},ensure_ascii=False))
    time.sleep(1)
raw=get('em-holder-changes','https://datacenter-web.eastmoney.com/api/data/v1/get',{'reportName':'RPT_SHARE_HOLDER_INCREASE','columns':'ALL','sortColumns':'END_DATE,SECURITY_CODE,EITIME','sortTypes':'-1,-1,-1','pageSize':'20','pageNumber':'1','source':'WEB','client':'WEB','filter':"(END_DATE>='2026-09-01')(END_DATE<='2026-09-26')"})
if raw:
    v=json.loads(raw);print('HOLDER_CHANGE',json.dumps({**v,'result':{**v.get('result',{}),'data':v.get('result',{}).get('data',[])[:2]}},ensure_ascii=False))
raw=get('gree-reports','https://reportapi.eastmoney.com/report/list',{'industryCode':'*','pageSize':'20','industry':'*','rating':'*','ratingChange':'*','beginTime':'2026-01-01','endTime':'2026-09-26','pageNo':'1','fields':'','qType':'0','orgCode':'80000007','code':'000651','rcode':'','p':'1','pageNum':'1','pageNumber':'1'})
if raw:
    v=json.loads(raw);print('FORECAST_PEERS',json.dumps(v,ensure_ascii=False))
    selected=[r for r in v.get('data',[]) if r.get('stockCode')=='000651' and r.get('orgCode')=='80000007']
    for i,r in enumerate(selected[:2]):
        rid=r['infoCode'];assert re.fullmatch('AP[0-9]{18}',rid)
        pdf=get('forecast-'+str(i),'https://pdf.dfcfw.com/pdf/H3_'+rid+'_1.pdf',{})
        if pdf: print('PDF',rid,len(pdf),sha256(pdf).hexdigest(),pdf[:5]==b'%PDF-')
(root/'qualification.json').write_text(json.dumps({'code':os.environ['GITHUB_SHA'],'run':os.environ['GITHUB_RUN_ID'],'records':rows},ensure_ascii=False,indent=2))
