"""Temporary bounded source qualification, not a production Radar or research."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import time
import requests

ROOT = Path(os.environ['RUNNER_TEMP']) / 'smart-money-probe'
ROOT.mkdir(parents=True, exist_ok=False)
EM = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
FT = 'https://market.ft.tech/gateway/api/v1/market/data/'
HT = 'https://fuyao.aicubes.cn/api/a-share/special-data/dragon-tiger-list'
SPECS = [
 ('ft-seats','FT',FT+'abnormal-trading-details',{'date':'2026-09-24','page':'1','page_size':'50'}),
 ('ft-holders-latest','FT',FT+'holder/stock-holder-ften',{'is_last':'true','page':'1','page_size':'50'}),
 ('ft-holder-history','FT',FT+'holder/stock-holder-ften',{'stock_code':'600111.SH'}),
 ('ft-northbound','FT',FT+'northbound',{'date':'20260924'}),
 ('ht-hot-24','HT',HT,{'board_type':'hot_money','date':'2026-09-24'}),
 ('ht-hot-23','HT',HT,{'board_type':'hot_money','date':'2026-09-23'}),
 ('ht-org-24','HT',HT,{'board_type':'org','date':'2026-09-24'}),
 ('em-activity','EM',EM,{'reportName':'RPT_ORG_SURVEY','columns':'ALL','sortColumns':'NOTICE_DATE,RECEIVE_START_DATE,SECURITY_CODE,NUMBERNEW','sortTypes':'-1,-1,1,-1','pageSize':'20','pageNumber':'1','source':'WEB','client':'WEB','filter':'(IS_SOURCE="1")(NOTICE_DATE>=\'2026-09-01\')(NOTICE_DATE<=\'2026-09-25\')'}),
 ('em-reports','EM','https://reportapi.eastmoney.com/report/list',{'industryCode':'*','pageSize':'20','industry':'*','rating':'*','ratingChange':'*','beginTime':'2026-09-01','endTime':'2026-09-25','pageNo':'1','fields':'','qType':'0','orgCode':'','code':'','rcode':'','p':'1','pageNum':'1','pageNumber':'1'}),
 ('em-repurchase','EM',EM,{'reportName':'RPTA_WEB_GETHGLIST_NEW','columns':'ALL','sortColumns':'UPD,DIM_DATE,DIM_SCODE','sortTypes':'-1,-1,-1','pageSize':'20','pageNumber':'1','source':'WEB'}),
 ('em-placement','EM',EM,{'reportName':'RPT_SEO_DETAIL','columns':'ALL','sortColumns':'ISSUE_DATE','sortTypes':'-1','pageSize':'20','pageNumber':'1','source':'WEB','client':'WEB'}),
 ('em-holders','EM',EM,{'reportName':'RPT_FREEHOLDERS_BASIC_INFO','columns':'ALL','sortColumns':'HOLDER_NUM,HOLDER_NEW','sortTypes':'-1,-1','pageSize':'20','pageNumber':'1','source':'WEB','client':'WEB','filter':'(END_DATE=\'2026-06-30\')'}),
]
SECRETS = {'FT':os.environ.get('FTSHARE_API_KEY',''),'HT':os.environ.get('HITHINK_FINANCE_API_KEY','')}
HEADERS = {'FT':'FTSHARE_API_KEY','HT':'X-api-key'}
stop=set(); prior={}; rows=[]; begin=time.monotonic()
clock=lambda:datetime.now(timezone.utc).isoformat()
assert os.environ.get('GITHUB_REF') == 'refs/heads/work/smart-money-20260926'
assert os.environ.get('GITHUB_RUN_ATTEMPT') == '1'
assert datetime.now(timezone.utc) < datetime(2026,9,27,tzinfo=timezone.utc)

def sketch(value, depth=0):
    if depth>3:return type(value).__name__
    if isinstance(value,dict):
        return {k:(sketch(v,depth+1) if isinstance(v,(dict,list)) else v) for k,v in list(value.items())[:100]}
    if isinstance(value,list):return {'length':len(value),'first_two':[sketch(v,depth+1) for v in value[:2]]}
    return value

for ident,provider,url,params in SPECS:
    rec={'id':ident,'provider':provider,'url':url,'params':params,'requested_at':None,'received_at':None}
    if provider in stop or time.monotonic()-begin>300 or provider in SECRETS and not SECRETS[provider]:
        rec['status']='NOT_ATTEMPTED_POLICY_OR_BUDGET';rows.append(rec);continue
    if provider in prior:
        time.sleep(max(0, (20 if provider=='HT' else 1)- (time.monotonic()-prior[provider])))
    headers={'Accept':'application/json','Accept-Encoding':'identity','User-Agent':'DecisionKernel-smart-money-qualification'}
    if provider in HEADERS:headers[HEADERS[provider]]=SECRETS[provider]
    rec['requested_at']=clock()
    try:
        with requests.Session() as session:
            session.trust_env=False
            with session.get(url,params=params,headers=headers,allow_redirects=False,stream=True,timeout=(10,20)) as response:
                rec['http_status']=response.status_code
                assert response.url==requests.Request('GET',url,params=params).prepare().url
                assert response.headers.get('Content-Encoding','identity').lower() in ('','identity')
                chunks=[];total=0
                for chunk in response.iter_content(65536):
                    total+=len(chunk)
                    if total>4*1024*1024:raise ValueError('BODY_LIMIT')
                    chunks.append(chunk)
                raw=b''.join(chunks)
        rec['received_at']=clock()
        if any(k and k.encode() in raw for k in SECRETS.values()):raise ValueError('CREDENTIAL_REFLECTION')
        if rec['http_status'] in (401,403,429):stop.add(provider)
        if 300<=rec['http_status']<400:stop.add(provider)
        (ROOT/(ident+'.body')).write_bytes(raw)
        rec.update(status='RAW_RETAINED_NOT_QUALIFIED',bytes=len(raw),sha256=sha256(raw).hexdigest())
        try:
            parsed=json.loads(raw)
            rec['shape']=sketch(parsed)
            if isinstance(parsed,dict) and parsed.get('code') in (401,403,429):stop.add(provider)
        except (ValueError,TypeError):rec['shape']='NOT_JSON'
    except (requests.RequestException,ValueError,OSError) as exc:
        rec.update(status='UNAVAILABLE',error_type=type(exc).__name__,received_at=clock())
        if isinstance(exc,ValueError):stop.add(provider)
    prior[provider]=time.monotonic();rows.append(rec)
result={'code':os.environ['GITHUB_SHA'],'run_id':os.environ['GITHUB_RUN_ID'],'attempt':1,'finished_at':clock(),'requests':rows,'research_executed':False,'investment_authority':'NONE'}
(ROOT/'probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
