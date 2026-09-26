"""Temporary, Human-authorized vendor qualification; never a production provider.
One request per listed endpoint, no paging/retry/redirect/fallback or portfolio writes.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import quote, unquote
import requests

BASE = 'https://tl.kaixin8.top/tushare/pro/'
MAX_BODY = 1024 * 1024
MAX_TOTAL = 24 * MAX_BODY
MAX_SECONDS = 580
DAY = '20260924'
PERIOD = '20260630'
WINDOW = {'start_date': '20260628', 'end_date': DAY}
PLAN = [
 ('daily', {'ts_code':'000001.SZ','start_date':DAY,'end_date':DAY}, ['ts_code','trade_date','close']),
 ('hm_list', {}, ['name','orgs']),
 ('hm_detail', {'trade_date':DAY,'limit':100}, ['trade_date','ts_code','hm_name','hm_orgs','net_amount']),
 ('report_rc', {'ts_code':'000651.SZ',**WINDOW,'limit':50}, ['ts_code','report_date','org_name','quarter','np']),
 ('stk_surv', {'ts_code':'603986.SH',**WINDOW,'limit':50}, ['ts_code','surv_date','rece_org','fund_visitors']),
 ('trade_cal', {'exchange':'SSE','start_date':'20260921','end_date':'20261009'}, ['cal_date','is_open']),
 ('adj_factor', {'ts_code':'603986.SH','trade_date':DAY}, ['ts_code','trade_date','adj_factor']),
 ('daily_basic', {'ts_code':'603986.SH','trade_date':DAY}, ['ts_code','trade_date','total_mv']),
 ('index_classify', {'level':'L1','src':'SW2021'}, ['index_code','industry_name']),
 ('index_member_all', {'ts_code':'603986.SH','limit':10}, ['ts_code','l1_code','l2_code']),
 ('sw_daily', {'ts_code':'801080.SI','trade_date':DAY}, ['ts_code','trade_date','close']),
 ('ths_index', {'exchange':'A','type':'I','limit':10}, ['ts_code','name']),
 ('ths_daily', {'ts_code':'881101.TI','trade_date':DAY}, ['ts_code','trade_date','close']),
 ('income', {'ts_code':'603986.SH','period':PERIOD,'limit':5}, ['ts_code','ann_date','end_date','revenue']),
 ('balancesheet', {'ts_code':'603986.SH','period':PERIOD,'limit':5}, ['ts_code','ann_date','end_date','total_assets']),
 ('cashflow', {'ts_code':'603986.SH','period':PERIOD,'limit':5}, ['ts_code','ann_date','end_date','n_cashflow_act']),
 ('fina_mainbz', {'ts_code':'603986.SH','period':PERIOD,'type':'P','limit':10}, ['ts_code','end_date','bz_item','bz_sales']),
 ('disclosure_date', {'ts_code':'603986.SH','end_date':'20260930','limit':5}, ['ts_code','end_date','pre_date']),
 ('top10_floatholders', {'ts_code':'603986.SH','period':PERIOD,'limit':10}, ['ts_code','end_date','holder_name','hold_amount']),
 ('fund_portfolio', {'ts_code':'510300.SH','period':PERIOD,'limit':10}, ['ts_code','end_date','symbol','amount']),
 ('repurchase', {'ts_code':'688525.SH','start_date':'20260901','end_date':DAY,'limit':10}, ['ts_code','ann_date','proc','amount']),
 ('fut_wsr', {'trade_date':DAY,'symbol':'CU','limit':10}, ['trade_date','symbol','vol']),
 ('fut_holding', {'trade_date':DAY,'symbol':'IF','limit':10}, ['trade_date','symbol','broker']),
 ('cn_pmi', {'m':'202608','limit':1}, ['month']),
 ('shibor', {'date':DAY}, ['date','on','1y']),
 ('us_tycr', {'start_date':DAY,'end_date':DAY}, ['date','y10']),
 ('index_global', {'ts_code':'SPX','start_date':DAY,'end_date':DAY}, ['ts_code','trade_date','close']),
 ('eco_cal', {'date':DAY,'currency':'CNY','limit':5}, ['date','event']),
 ('hk_daily', {'ts_code':'00700.HK','start_date':DAY,'end_date':DAY}, ['ts_code','trade_date','close']),
 ('us_daily', {'ts_code':'NVDA','start_date':DAY,'end_date':DAY}, ['ts_code','trade_date','close']),
 ('dividend', {'ts_code':'603986.SH','end_date':PERIOD,'limit':5}, ['ts_code','end_date','ex_date']),
 ('fina_indicator', {'ts_code':'603986.SH','period':PERIOD,'limit':5}, ['ts_code','ann_date','end_date','roe']),
]


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode()
    path.write_bytes(data + b'\n')


def sensitive(value, key):
    if isinstance(value, str):
        return key in unquote(value)
    if isinstance(value, list):
        return any(sensitive(x,key) for x in value)
    if isinstance(value, dict):
        for name,item in value.items():
            label = re.sub(r'[^a-z]', '', str(name).lower())
            if label in {'token','apikey','xapikey','authorization','secret','password','cookie','setcookie'} and item not in (None,''):
                return True
            if sensitive(str(name),key) or sensitive(item,key):
                return True
    return False


def unpack(value):
    """Inspect a returned envelope; do not assume the reseller is Tushare itself."""
    if isinstance(value, dict):
        code = value.get('code')
        if code is not None and code not in (0,200,'0','200'):
            return [], [], 'BUSINESS_ERROR'
        if value.get('success') is False:
            return [], [], 'BUSINESS_ERROR'
        data = value.get('data', value.get('result', value))
    else:
        data = value
    if isinstance(data, dict):
        fields, items = data.get('fields'), data.get('items')
        if isinstance(fields,list) and all(isinstance(x,str) for x in fields) and isinstance(items,list):
            if len(set(fields)) != len(fields):
                return fields, [], 'DUPLICATE_FIELDS'
            if all(isinstance(x,list) and len(x)==len(fields) for x in items):
                return fields, [dict(zip(fields,x)) for x in items], 'FIELDS_ITEMS'
            if all(isinstance(x,dict) for x in items):
                return fields, items, 'DICT_ITEMS'
            return fields, [], 'ROW_SHAPE_MISMATCH'
        for field in ('items','records','rows','list','data'):
            rows = data.get(field)
            if isinstance(rows,list) and all(isinstance(x,dict) for x in rows):
                return sorted(set().union(*(x.keys() for x in rows))), rows, 'DICT_ROWS'
    if isinstance(data,list) and all(isinstance(x,dict) for x in data):
        return sorted(set().union(*(x.keys() for x in data))), data, 'DICT_ROWS'
    return [], [], 'UNKNOWN_ENVELOPE'


def error_category(value):
    message = ''
    if isinstance(value,dict):
        message = ' '.join(str(value.get(k,'')) for k in ('msg','message','error','detail')).lower()
    if any(x in message for x in ('无效token','token无效','invalid token','invalid api','key无效','密钥无效','认证失败','unauthorized','authentication')):
        return 'AUTHENTICATION_STOP', True
    if any(x in message for x in ('频次','频率','每分钟','rate limit','too many','每日次数','quota exceeded')):
        return 'RATE_OR_QUOTA_STOP', True
    if any(x in message for x in ('积分','权限','permission','points','开通','not subscribed')):
        return 'ENDPOINT_PERMISSION_NOT_ESTABLISHED', False
    if any(x in message for x in ('参数','parameter','argument')):
        return 'PARAMETER_REJECTED', False
    if any(x in message for x in ('不存在','not found','unknown api','unsupported','不支持')):
        return 'ENDPOINT_UNSUPPORTED', False
    return 'UNCLASSIFIED_BUSINESS_ERROR', False


def inspect(value, api, params, required):
    fields, rows, shape = unpack(value)
    if shape == 'BUSINESS_ERROR':
        category, stop = error_category(value)
        code = value.get('code')
        return {'status':category,'business_code':code if isinstance(code,(int,str)) and len(str(code))<24 else None}, stop
    result = {'shape':shape,'fields':fields,'rows':len(rows),'status':'EMPTY_SAMPLE' if not rows else 'NONEMPTY_SAMPLE'}
    if shape in {'UNKNOWN_ENVELOPE','ROW_SHAPE_MISMATCH','DUPLICATE_FIELDS'}:
        result['status'] = shape
        return result, False
    missing = [x for x in required if x not in fields]
    result['missing_expected_fields'] = missing
    if missing and rows:
        result['status'] = 'NONEMPTY_SCHEMA_GAP'
    mismatches=[]
    for field in ('ts_code','trade_date','period'):
        output = 'end_date' if field=='period' else field
        if field in params and output in fields:
            bad=sum(str(x.get(output,'')) != str(params[field]) for x in rows)
            if bad:mismatches.append({'field':output,'rows':bad})
    result['filter_mismatches']=mismatches
    if mismatches:result['status']='FILTER_MISMATCH'
    result['nonempty_counts']={x:sum(row.get(x) not in (None,'') for row in rows) for x in required if x in fields}
    result['sample']=rows[:3]
    result['row_count_reached_requested_limit']=bool(rows and 'limit' in params and len(rows)>=params['limit'])
    result['full_coverage_verified']=False
    return result,False


def main():
    root=Path(os.environ['PROBE_OUTPUT']);root.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    report={'started_at':now(),'provider':'THIRD_PARTY_TUSHARE_COMPATIBLE_NOT_OFFICIAL',
            'base_url':BASE,'main_baseline':'b87b5ea3af2532a5d9824258da7e5fb8889229ec',
            'head_sha':os.getenv('GITHUB_SHA'),'run_id':os.getenv('GITHUB_RUN_ID'),'attempt':os.getenv('GITHUB_RUN_ATTEMPT'),
            'tls_verify':True,'redirects':False,'retries':0,'fallback_enabled':False,
            'max_requests':32,'scope':'SINGLE_PAGE_CAPABILITY_SAMPLES_NOT_PRODUCTION',
            'results':[],'requests_started':0,'http_responses':0,'raw_bytes':0,'stop_reason':None,
            'production_modified':False,'investment_authority':'NONE'}
    key=os.environ.get('TUSHARE_PROXY_API_KEY','').strip()
    if not (8<=len(key)<=512) or any(ord(x)<33 or ord(x)>126 for x in key):
        report['stop_reason']='MISSING_OR_INVALID_SECRET_FORMAT'
        write_json(root/'report.json',report)
        return 2
    if datetime.now(timezone.utc)>=datetime(2026,9,27,tzinfo=timezone.utc):
        report['stop_reason']='PROBE_EXPIRED';write_json(root/'report.json',report);return 2
    assert len(PLAN)==32 and len({x[0] for x in PLAN})==32
    secret_forms=(key.encode(),quote(key,safe='').encode(),base64.b64encode(key.encode()))
    with requests.Session() as session:
        session.trust_env=False
        session.headers.update({'X-API-Key':key,'Accept':'application/json','User-Agent':'DecisionKernel-Bounded-Qualification/1'})
        session.mount('https://',requests.adapters.HTTPAdapter(max_retries=0))
        for api,params,required in PLAN:
            if report['stop_reason']:
                report['results'].append({'api':api,'params':params,'status':'NOT_RUN','because':report['stop_reason']})
                continue
            if time.monotonic()-start>MAX_SECONDS:
                report['stop_reason']='TIME_BUDGET'
                report['results'].append({'api':api,'params':params,'status':'NOT_RUN','because':'TIME_BUDGET'})
                continue
            assert re.fullmatch('[a-z0-9_]+',api)
            item={'api':api,'params':params,'started_at':now()};stamp=time.monotonic()
            report['requests_started']+=1
            try:
                session.cookies.clear()
                with session.get(BASE+api,params=params,verify=True,allow_redirects=False,timeout=(5,15),stream=True) as response:
                    report['http_responses']+=1;item['http_status']=response.status_code
                    if response.status_code in (401,403,429) or 300<=response.status_code<400:
                        item['status']='HTTP_POLICY_STOP';report['stop_reason']='HTTP_'+str(response.status_code)
                    elif response.status_code!=200:
                        item['status']='HTTP_ERROR'
                    else:
                        parts=[];size=0
                        for chunk in response.iter_content(16384):
                            size+=len(chunk)
                            if size>MAX_BODY or time.monotonic()-stamp>25:raise ValueError('RESPONSE_BOUND')
                            parts.append(chunk)
                        raw=b''.join(parts)
                        if any(part in raw for part in secret_forms):raise ValueError('CREDENTIAL_ECHO_STOP')
                        value=json.loads(raw.decode('utf-8-sig'),parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
                        if sensitive(value,key):raise ValueError('SENSITIVE_RESPONSE_STOP')
                        if report['raw_bytes']+size>MAX_TOTAL:raise ValueError('TOTAL_BOUND')
                        outcome,stop=inspect(value,api,params,required);item.update(outcome)
                        name=api+'.json';(root/name).write_bytes(raw)
                        item.update(raw_file=name,raw_bytes=size,raw_sha256=hashlib.sha256(raw).hexdigest())
                        report['raw_bytes']+=size
                        if stop:report['stop_reason']=outcome['status']
            except requests.exceptions.SSLError as exc:
                item['status']='TLS_VALIDATION_FAILED'
                message=str(exc).lower()
                item['tls_detail']=('CERTIFICATE_VERIFY_FAILED' if 'certificate verify failed' in message else 'TLS_HANDSHAKE_FAILED')
                report['stop_reason']=item['status']
            except requests.exceptions.Timeout:
                item['status']='TIMEOUT';report['stop_reason']='TRANSPORT_TIMEOUT_NO_RETRY'
            except requests.exceptions.ConnectionError:
                item['status']='CONNECTION_FAILED';report['stop_reason']='CONNECTION_FAILED_NO_RETRY'
            except requests.exceptions.RequestException:
                item['status']='REQUEST_FAILED';report['stop_reason']='REQUEST_FAILED_NO_RETRY'
            except (ValueError,UnicodeError,RecursionError) as exc:
                allowed={'RESPONSE_BOUND','CREDENTIAL_ECHO_STOP','SENSITIVE_RESPONSE_STOP','TOTAL_BOUND'}
                item['status']=str(exc) if str(exc) in allowed else 'INVALID_JSON_OR_SHAPE'
                if item['status'] in allowed:report['stop_reason']=item['status']
            item['finished_at']=now();item['elapsed_seconds']=round(time.monotonic()-stamp,3)
            report['results'].append(item);write_json(root/'report.json',report)
            print(json.dumps({'api':api,'status':item['status'],'rows':item.get('rows'),'seconds':item['elapsed_seconds']}),flush=True)
            if not report['stop_reason']:time.sleep(1)
    report['finished_at']=now();write_json(root/'report.json',report)
    lines=['# Third-party Tushare capability probe','', 'Samples only; not an official entitlement or production acceptance.', '', '| API | HTTP | Result | Rows | Seconds |','|---|---:|---|---:|---:|']
    for row in report['results']:
        lines.append('| '+ ' | '.join(str(row.get(x,'')) for x in ('api','http_status','status','rows','elapsed_seconds'))+' |')
    lines+=['','Stop reason: '+str(report['stop_reason']),'Credential values and request headers were not exported.']
    (root/'summary.md').write_text('\n'.join(lines)+'\n')
    return 2 if report['stop_reason'] else 0


if __name__=='__main__':
    raise SystemExit(main())
