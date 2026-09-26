"""Finite delta probe; original successful samples are read, not recaptured."""
from datetime import datetime, timezone
from hashlib import sha256
import json, os, time, zipfile
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT=Path(os.environ['RUNNER_TEMP'])/'smart-money-probe'
ROOT.mkdir(exist_ok=False)
assert os.environ['GITHUB_REF']=='refs/heads/work/smart-money-20260926' and os.environ['GITHUB_RUN_ATTEMPT']=='1'
assert datetime.now(timezone.utc)<datetime(2026,9,27,tzinfo=timezone.utc)
FT='https://market.ft.tech/gateway/api/v1/market/data/'
EM='https://datacenter-web.eastmoney.com/api/data/v1/get'
SPECS=[
 ('ft-seats-fixed','FT',FT+'abnormal-trading-details',{'date':'20260924','page':'1','page_size':'20'}),
 ('ft-executives','FT',FT+'holder/stock-ggmx',{'start_date':'20260901','end_date':'20260925','page':'1','page_size':'20'}),
 ('ft-holder-changes','FT',FT+'holder/stock-ggcg-em',{'symbol':'全部','page':'1','page_size':'20'}),
 ('em-holder-details','EM',EM,{'reportName':'RPT_F10_EH_FREEHOLDERS','columns':'ALL','sortColumns':'UPDATE_DATE,SECURITY_CODE,HOLDER_RANK','sortTypes':'-1,1,1','pageSize':'20','pageNumber':'1','source':'WEB','client':'WEB','filter':'(END_DATE=\'2026-06-30\')'}),
 ('hkex-sh','HKEX','https://www3.hkexnews.hk/sdw/mutualmarket/SH.htm',{}),
 ('hkex-sz','HKEX','https://www3.hkexnews.hk/sdw/mutualmarket/SZ.htm',{}),
]
key=os.environ.get('FTSHARE_API_KEY','');stopped=set();rows=[]
clock=lambda:datetime.now(timezone.utc).isoformat()

def brief(v,depth=0):
    if depth>5:return type(v).__name__
    if isinstance(v,dict):return {k:brief(x,depth+1) for k,x in v.items() if k not in {'CONTENT','REPUROBJECTIVE','PRICE_PRINCIPLE','REMARK','BZ'}}
    if isinstance(v,list):return {'length':len(v),'first': [brief(x,depth+1) for x in v[:2]]}
    return v[:500] if isinstance(v,str) else v

for ident,provider,url,params in SPECS:
    r={'id':ident,'url':url,'params':params,'provider':provider,'requested_at':clock()}
    if provider in stopped or provider=='FT' and not key:
        r['status']='NOT_ATTEMPTED_POLICY';rows.append(r);continue
    headers={'User-Agent':'Mozilla/5.0 DecisionKernel-bounded-source-review','Accept-Encoding':'identity'}
    if provider=='FT':headers['FTSHARE_API_KEY']=key
    try:
        with requests.Session() as s:
            s.trust_env=False
            with s.get(url,params=params,headers=headers,timeout=(10,25),allow_redirects=False,stream=True) as resp:
                assert resp.url==requests.Request('GET',url,params=params).prepare().url
                chunks=[];size=0
                for c in resp.iter_content(65536):
                    size+=len(c);assert size<=4*1024*1024;chunks.append(c)
                raw=b''.join(chunks);status=resp.status_code
        assert not key or key.encode() not in raw
        r.update(received_at=clock(),http_status=status,bytes=len(raw),sha256=sha256(raw).hexdigest())
        (ROOT/(ident+'.body')).write_bytes(raw)
        if status in (401,403,429) or 300<=status<400:stopped.add(provider)
        try:
            p=json.loads(raw);r['shape']=brief(p)
            if p.get('code') in (401,403,429):stopped.add(provider)
        except (ValueError,AttributeError):
            soup=BeautifulSoup(raw,'html.parser')
            r['html']={'title':soup.title.get_text(' ',strip=True) if soup.title else None,
               'table_rows':[[td.get_text(' ',strip=True) for td in tr.find_all(['td','th'])] for tr in soup.select('tr')[:8]],
               'inputs':[{k:x.get(k) for k in ('id','name','value','type')} for x in soup.select('input')[:20]],
               'scripts':[x.get('src') for x in soup.select('script[src]')],
               'iframes':[x.get('src') for x in soup.select('iframe')]}
        r['status']='RETAINED_NOT_YET_QUALIFIED'
    except Exception as exc:r.update(status='UNAVAILABLE',error_type=type(exc).__name__,received_at=clock())
    rows.append(r);time.sleep(1)
prior=Path(os.environ['RUNNER_TEMP'])/'prior-smart-money.zip'
raw=prior.read_bytes()
assert sha256(raw).hexdigest()=='f4466c6e9999e1895ba4d3bbd46bc212ddd0ac3ada85f956362704dad7b57cf0'
with zipfile.ZipFile(prior) as z:
    assert z.testzip() is None
    for name in ('ft-holders-latest','ft-holder-history','ht-hot-24'):
        p=json.loads(z.read(name+'.body'))
        if name.startswith('ft'):
            r=p['data']['items'][0];print('PRIOR_HOLDER',name,json.dumps({**r,'fen_holders':r['fen_holders'][:3]},ensure_ascii=False))
        else:
            print('PRIOR_HOT',json.dumps(p['data']['hot_money_items'][0],ensure_ascii=False))
print('DELTA_PROBE',json.dumps({'run_id':os.environ['GITHUB_RUN_ID'],'code':os.environ['GITHUB_SHA'],'records':rows},ensure_ascii=False,indent=2))
(ROOT/'delta.json').write_text(json.dumps({'records':rows},ensure_ascii=False,indent=2))
