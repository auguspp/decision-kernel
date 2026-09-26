"""One finite, replayable Smart Money daily collection. No research or trading.

All calls are rebuilt from reviewed source contracts. Raw originals, page counts,
row-level rejections and absent partitions survive as explicit observations.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import time

import requests

from ..adapters.hithink import normalize_hithink_calendar, latest_completed_a_share_session
from ..identity import canonical_hash
from .hithink_dump_trial import _session
from . import smart_money_sources as s
from . import smart_money_documents as docs

MAX_SECONDS = 1200
KEYS = {'FT':('FTSHARE_API_KEY','FTSHARE_API_KEY'), 'HT':('HITHINK_FINANCE_API_KEY','X-api-key')}
TRANSIENT = {'TRANSPORT_TIMEOUT','TRANSPORT_CONNECTION','HTTP_502','HTTP_503','HTTP_504','SOURCE_BUSY'}
STOP_CODES = {401,403,429}


def identity(env):
    expected={'GITHUB_REPOSITORY':'auguspp/decision-kernel','GITHUB_REF':'refs/heads/main',
              'GITHUB_WORKFLOW':'radar-smart-money','GITHUB_RUN_ATTEMPT':'1'}
    s.require(all(env.get(k)==v for k,v in expected.items()), 'EXECUTION_IDENTITY')
    s.require(env.get('GITHUB_EVENT_NAME') in {'schedule','workflow_dispatch'}, 'EXECUTION_EVENT')
    s.require(re.fullmatch('[0-9a-f]{40}',env.get('GITHUB_SHA','')) is not None and
              re.fullmatch('[1-9][0-9]{0,19}',env.get('GITHUB_RUN_ID','')) is not None,'EXECUTION_IDENTITY')
    return {'repository':expected['GITHUB_REPOSITORY'],'workflow':s.WORKFLOW,'ref':expected['GITHUB_REF'],
            'event':env['GITHUB_EVENT_NAME'],'code_commit':env['GITHUB_SHA'],'run_id':int(env['GITHUB_RUN_ID']),'attempt':1}


def validate_identity(value):
    s.require(isinstance(value,dict) and set(value)=={'repository','workflow','ref','event','code_commit','run_id','attempt'},'IDENTITY_FIELDS')
    env={'GITHUB_REPOSITORY':value['repository'],'GITHUB_REF':value['ref'],'GITHUB_WORKFLOW':'radar-smart-money',
         'GITHUB_RUN_ATTEMPT':str(value['attempt']),'GITHUB_EVENT_NAME':value['event'],
         'GITHUB_SHA':value['code_commit'],'GITHUB_RUN_ID':str(value['run_id'])}
    s.require(type(value['run_id']) is int and type(value['attempt']) is int and identity(env)==value,'IDENTITY_TYPES')
    return value


def request_raw(spec):
    """Credentials are used only on their one reviewed host; no redirects/proxy."""
    if spec['family']=='calendar': s.require(spec==s.calendar_spec(),'REQUEST_SPEC')
    elif spec['family']=='forecast_pdf':s.require(spec==docs.pdf_spec(spec['partition'],spec['begin'],spec['end']),'REQUEST_SPEC')
    elif spec['family']=='north_holdings' and '@' in spec['partition']:
        base=s.spec(*(spec[k] for k in ('family','partition','begin','end','page')))
        s.require({k:v for k,v in spec.items() if k not in {'form','form_source'}}==base,'HKEX_POST_SPEC')
        s.require(re.fullmatch('raw-[0-9]{4}\\.body',spec['form_source']) is not None,'HKEX_FORM_SOURCE')
        s.require(spec['form'].get('__EVENTTARGET')=='btnSearch' and
                  spec['form'].get('txtShareholdingDate')==spec['partition'].split('@')[1].replace('-','/'),'HKEX_POST_DATE')
    else: s.require(spec==s.spec(*(spec[k] for k in ('family','partition','begin','end','page'))),'REQUEST_SPEC')
    header={'Accept-Encoding':'identity','User-Agent':'Mozilla/5.0 DecisionKernel-SmartMoney/1', 'Accept':'application/json'}
    secrets=[]
    if spec['provider'] in KEYS:
        envname,hname=KEYS[spec['provider']]; key=os.environ.get(envname,'')
        s.require(bool(key) and key.isascii() and all(32<ord(c)<127 for c in key),'CREDENTIAL_UNAVAILABLE')
        header[hname]=key;secrets.append(key.encode())
    with _session() as client:
        with client.request(spec.get('method','GET'),spec['url'],params=spec['params'],
                        **({'data':spec['form']} if spec.get('method')=='POST' else {}),headers=header,stream=True,
                        timeout=(10,25),allow_redirects=False) as response:
            s.require(response.url==requests.Request('GET',spec['url'],params=spec['params']).prepare().url,'DESTINATION_CHANGED')
            s.require(response.headers.get('Content-Encoding','identity').lower() in {'','identity'},'ENCODING_CHANGED')
            length=response.headers.get('Content-Length')
            s.require(length is None or length.isdigit() and int(length)<=s.MAX_BODY,'BODY_SIZE')
            chunks=[];size=0
            for chunk in response.iter_content(65536):
                size+=len(chunk);s.require(size<=s.MAX_BODY,'BODY_SIZE');chunks.append(chunk)
            raw=b''.join(chunks)
            s.require(length is None or len(raw)==int(length),'BODY_LENGTH')
            s.require(not any(key in raw for key in secrets),'CREDENTIAL_REFLECTION')
            return response.status_code,raw


def make_plan(asof, calendar_value, previous=None):
    """Look back on real trading sessions; known missed dates are never forgotten."""
    cutoff=s.clock(asof); end=cutoff.astimezone(s.ZONE).date(); start=end-timedelta(days=90)
    trade_days=[];calendar_error=None
    if calendar_value is not None:
        try:
            sessions=normalize_hithink_calendar(calendar_value)
            latest=latest_completed_a_share_session(sessions,observed_at=cutoff)
            trade_days=[d.isoformat() for d in sessions if d<=latest][-5:]
        except (ValueError,TypeError,KeyError) as exc:
            calendar_error=type(exc).__name__
    else: calendar_error='CALENDAR_UNAVAILABLE'
    previous=previous or {}
    s.require(not previous or previous.get('version')==s.VERSION,'PREVIOUS_PLAN_VERSION')
    pending=previous.get('unresolved',[])
    s.require(isinstance(pending,list) and len(pending)<=4096,'PENDING_SCOPE')
    missed=[]
    for gap in pending:
        if gap.get('family') in {'hot_money','institutional','seats','northbound'}:
            d=gap.get('partition')
            if isinstance(d,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',d):
                s.require(s.day(d)<=end,'FUTURE_PENDING')
                if (end-s.day(d)).days<=365: missed.append(d)
    # Prior history does not override calendar qualification. Missing calendar
    # cannot launch dated market requests, but public disclosures still run.
    if trade_days:
        known=set(d.isoformat() for d in sessions if d<=latest)
        # If the caller was absent for more than five sessions, recover the
        # sessions after its last actual check, not merely the latest window.
        prior_cutoff=previous.get('cutoff')
        if prior_cutoff:
            prior_day=s.clock(prior_cutoff).astimezone(s.ZONE).date().isoformat()
            s.require(s.clock(prior_cutoff)<=cutoff,'FUTURE_PREVIOUS_CHECK')
            missed.extend(d for d in known if prior_day<d<=latest.isoformat())
        trade_days=sorted((set(trade_days)|set(missed)) & known)
    partitions=[]
    for f in s.FAMILIES:
        if f in {'hot_money','institutional','seats','northbound'}:
            for d in trade_days[:20]: partitions.append({'family':f,'partition':d,'begin':d,'end':d})
        elif f=='north_holdings':
            for ch in ('SH','SZ'):
                for key in (ch,ch+'@'+s.periods(end)[0]):
                    partitions.append({'family':f,'partition':key,'begin':start.isoformat(),'end':end.isoformat()})
        elif f=='holdings':
            for d in s.periods(end): partitions.append({'family':f,'partition':d,'begin':start.isoformat(),'end':end.isoformat()})
        else:
            prior_starts=[g['begin'] for g in pending if g.get('family')==f
                and g.get('partition')=='disclosures' and g.get('begin')
                and 0<=(end-s.day(g['begin'])).days<=366]
            first=min([start.isoformat(),*prior_starts])
            partitions.append({'family':f,'partition':'disclosures','begin':first,'end':end.isoformat()})
    pending_pairs={(x.get('family'),x.get('partition')) for x in pending}
    partitions.sort(key=lambda x: (x['family'],x['partition']) not in pending_pairs if x['family']!='north_holdings' else True)
    # A full quarterly table already acquired is reused for at most six days.
    # Its actual acquisition date remains visible. No claim of daily changes.
    completed=previous.get('completed_partitions',[])
    deferred=[];active=[]
    for p in partitions:
        old=next((x for x in completed if x.get('family')==p['family'] and x.get('partition')==p['partition']),None)
        if (p['family']=='holdings' and old and (p['family'],p['partition']) not in pending_pairs
                and 0<=(cutoff-s.clock(old['cutoff'])).total_seconds()<6*86400):
            deferred.append({**p,'previous_cutoff':old['cutoff'],'reason':'QUARTER_BASELINE_REUSED_WITH_EXPLICIT_AGE'})
        else:active.append(p)
    partitions=active
    return {'deferred_partitions':deferred,'asof':asof,'target_date':end.isoformat(),'partitions':partitions,'calendar_error':calendar_error,
            'trading_sessions':trade_days[:20],'unprocessed_trading_sessions':trade_days[20:],
            'prior_unresolved':pending,'scope':'LATEST_TWO_ENDED_REPORT_PERIODS_AND_90D_DISCLOSURES; INITIAL_FIVE_SESSIONS_PLUS_KNOWN_GAPS'}


def _http_reason(status, raw):
    if status!=200: return 'HTTP_'+str(status)
    try:
        obj=s.decode(raw)
        if isinstance(obj,dict) and obj.get('code') in STOP_CODES: return 'BUSINESS_'+str(obj['code'])
    except (ValueError,TypeError): pass
    return None


def payload(raw, request):
    return docs.northbound_table(raw,request) if request['family']=='north_holdings' else s.decode(raw)


def _parse_partition(records, files, scope):
    """Pure original-byte reconstruction; never trust recorded success/counts."""
    rows=[];total=pages=None;received=0;errors=[];seen_raw=set();duplicate_raw=0;failure=None;page_fingerprints=set();source_counts=[]
    for n,record in enumerate(records,1):
        expected=s.spec(scope['family'],scope['partition'],scope['begin'],scope['end'],n)
        if expected.get('method')=='POST':
            source=record['request'].get('form_source','')
            s.require(re.fullmatch('raw-[0-9]{4}\\.body',source) is not None,'HKEX_FORM_SOURCE')
            s.require(int(source[4:8])<record['index'],'HKEX_FORM_CHRONOLOGY')
            channel,period=expected['partition'].split('@')
            expected={**expected,'form_source':source,'form':docs.post_form(files[source],channel,period)}
        s.require(record['request']==expected,'PAGE_PLAN_DIFFERS')
        if record['body'] is None:
            failure=record['error'];break
        raw=files[record['body']];failure=_http_reason(record['http_status'],raw)
        if failure: break
        try:
            obj=payload(raw,expected);page_rows,count,npages=s.page_data(obj,expected)
            if total is None: total,pages=count,npages
            s.require(count==total and npages==pages,'PAGE_DENOMINATOR_DRIFT')
            s.require(n<=max(1,pages),'EXTRA_PAGE')
            page_fingerprint=canonical_hash(page_rows)
            s.require(not page_rows or page_fingerprint not in page_fingerprints,'DUPLICATE_PAGE')
            page_fingerprints.add(page_fingerprint)
            if expected['provider']=='HT':
                source_counts.append({k:obj['data'].get(k) for k in ('count','stock_count')})
            received+=len(page_rows)
            for i,row in enumerate(page_rows):
                fingerprint=canonical_hash(row)
                if fingerprint in seen_raw: duplicate_raw+=1
                seen_raw.add(fingerprint)
                try: rows.extend(s.normalize(row,expected,i,record['index'],obj))
                except (ValueError,KeyError,TypeError,IndexError) as exc:
                    reason=exc.args[0] if type(exc) is s.SourceError else type(exc).__name__
                    errors.append({'source_row':[record['index'],i],'reason':str(reason)[:100]})
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            failure=exc.args[0] if type(exc)is s.SourceError else type(exc).__name__;break
    dedup,conflicts=s.economic_rows(rows)
    if scope['family']=='activity':
        try:dedup=s.aggregate_activity(dedup)
        except (ValueError,KeyError,TypeError):
            failure='ACTIVITY_EVENT_CONFLICT';dedup=[]
    complete=bool(records and failure is None and pages is not None and len(records)==max(1,pages)
                  and received==total and not errors and conflicts==0)
    if not records: failure='NOT_ATTEMPTED'
    elif failure is None and pages is not None and len(records)<max(1,pages): failure='PAGE_OR_TIME_BUDGET'
    return {'family':scope['family'],'partition':scope['partition'],'begin':scope['begin'],'end':scope['end'],
            'status':'QUALIFIED_SOURCE_SCOPE' if complete else 'PARTIAL_OR_UNAVAILABLE',
            'complete':complete,'provider_total':total,'provider_pages':pages,'returned_rows':received,
            'normalized_rows':len(dedup),'duplicate_page_rows':duplicate_raw,'conflicting_identities':conflicts,
            'row_errors':errors,'failure':failure,'rows':dedup,'source_disclosure_counts':source_counts,
            'coverage_meaning':'PROVIDER_RETURN_NOT_INDEPENDENT_EXCHANGE_EXHAUSTIVENESS'}


def _validate_record(record, files, previous_clock, cutoff):
    s.require(set(record)=={'index','request','requested_at','received_at','body','bytes','sha256','http_status','error'},'RECORD_FIELDS')
    a,b=s.clock(record['requested_at']),s.clock(record['received_at'])
    s.require(previous_clock<=a<=b<=cutoff,'REQUEST_CLOCKS')
    if record['body'] is None:
        s.require(record['bytes'] is None and record['sha256'] is None and record['http_status'] is None and
                  isinstance(record['error'],str) and re.fullmatch(r'[A-Z_]{1,80}',record['error']),'ERROR_RECEIPT')
    else:
        s.require(record['body']==f"raw-{record['index']:04d}.body" and record['error'] is None,'BODY_PATH')
        raw=files[record['body']]
        s.require(isinstance(raw,bytes) and 0<=len(raw)<=s.MAX_BODY and record['bytes']==len(raw)
                  and record['sha256']==sha256(raw).hexdigest(),'BODY_IDENTITY')
        s.require(type(record['http_status']) is int and 100<=record['http_status']<=599,'HTTP_STATUS')
    return b


def rebuild(manifest, files, *, expected_identity=None, cutoff=None):
    s.require(manifest.get('version')==s.VERSION and manifest.get('authority')==s.AUTHORITY,'CAPTURE_VERSION')
    validate_identity(manifest['identity'])
    if expected_identity is not None:s.require(manifest['identity']==expected_identity,'CAPTURE_RUN')
    s.require(manifest['capture_hash']==canonical_hash({k:v for k,v in manifest.items() if k!='capture_hash'}),'CAPTURE_HASH')
    begin,finish=s.clock(manifest['started_at']),s.clock(manifest['finished_at'])
    s.require(begin<=finish and (cutoff is None or finish<=s.clock(cutoff)),'CAPTURE_CLOCKS')
    records=manifest['records'];s.require(isinstance(records,list) and len(records)<=s.MAX_REQUESTS,'REQUEST_BUDGET')
    names={'capture.json'};prior=begin;totalbytes=0
    for i,record in enumerate(records):
        s.require(record['index']==i,'REQUEST_INDEX')
        prior=_validate_record(record,files,prior,finish)
        if record['body'] is not None:names.add(record['body']);totalbytes+=record['bytes']
    s.require(names==set(files) and totalbytes<=s.MAX_TOTAL_RAW,'CAPTURE_FILE_SCOPE')
    s.require(records and records[0]['request']==s.calendar_spec(),'CALENDAR_FIRST')
    cal=None
    if records[0]['body'] is not None and _http_reason(records[0]['http_status'],files[records[0]['body']]) is None:
        try: cal=s.decode(files[records[0]['body']])
        except (ValueError,TypeError): pass
    plan=make_plan(manifest['started_at'],cal,manifest.get('previous_state'))
    s.require(plan==manifest['plan'],'CAPTURE_PLAN_DIFFERS')
    expected_order=[(p['family'],p['partition']) for p in plan['partitions']]
    groups={};last=-1;stopped=set();pdf_records=[]
    previous=manifest.get('previous_state') or {}
    if previous.get('target_date')==plan['target_date']:
        stopped.update(previous.get('policy_stops',[]))
    s.require(stopped <= {'HT','FT','EM','HKEX'},'PRIOR_POLICY_STOPS')
    for record in records:
        request=record['request'];provider=request['provider']
        if request['family']=='forecast_pdf':
            pdf_records.append(record)
        elif record is not records[0]:
            s.require(not pdf_records,'SOURCE_AFTER_PDF')
            pair=request['family'],request['partition'];s.require(pair in expected_order,'UNPLANNED_PARTITION')
            pos=expected_order.index(pair);s.require(pos>=last,'PARTITION_ORDER');last=pos
            groups.setdefault(pair,[]).append(record)
        if provider in stopped:
            s.require(record['body'] is None and record['error']=='PROVIDER_POLICY_STOP','POLICY_STOP_BYPASS')
        if record['body'] is not None:
            reason=_http_reason(record['http_status'],files[record['body']])
            if reason in {'HTTP_401','HTTP_403','HTTP_429','BUSINESS_401','BUSINESS_403','BUSINESS_429'}:stopped.add(provider)
            if 300<=record['http_status']<400:stopped.add(provider)
        elif record['error'] in {'CREDENTIAL_REFLECTION','DESTINATION_CHANGED'}:stopped.add(provider)
    partitions=[_parse_partition(groups.get((p['family'],p['partition']),[]),files,p) for p in plan['partitions']]
    report_rows=[r for p in partitions if p['family']=='forecasts' for r in p['rows']]
    selected_pdfs=docs.select_reports(report_rows)
    s.require(len(pdf_records)<=len(selected_pdfs),'UNPLANNED_PDF_COUNT')
    pdf_results=[]
    for i,r in enumerate(selected_pdfs):
        if i>=len(pdf_records):
            pdf_results.append({'report_id':r['values']['report_id'],'status':'NOT_ATTEMPTED_PDF_BUDGET'})
            continue
        record=pdf_records[i]
        forecast_scope=next(p for p in plan['partitions'] if p['family']=='forecasts')
        expected=docs.pdf_spec(r['values']['report_id'],forecast_scope['begin'],forecast_scope['end'])
        s.require(record['request']==expected,'PDF_SELECTION_DIFFERS')
        if record['body'] is None or record['http_status']!=200:
            pdf_results.append({'report_id':r['values']['report_id'],'status':'PDF_SOURCE_UNAVAILABLE','source_row':record['index']})
            continue
        try:
            answer=docs.reported_revisions(files[record['body']],r)
            answer['source_row']=record['index'];pdf_results.append(answer)
        except (ValueError,TypeError,KeyError,RuntimeError) as exc:
            pdf_results.append({'report_id':r['values']['report_id'],'status':'PDF_NOT_QUALIFIED','error_type':type(exc).__name__,'source_row':record['index']})
    available=sum(bool(p['rows']) or p['complete'] for p in partitions)
    unresolved=[{k:p[k] for k in ('family','partition','begin','end','failure')}
                for p in partitions if not p['complete']]
    for missed in plan['unprocessed_trading_sessions']:
        unresolved.extend({'family':f,'partition':missed,'begin':missed,'end':missed,'failure':'RESOURCE_BUDGET'}
                          for f in ('hot_money','institutional','seats','northbound'))
    if plan['calendar_error']:
        unresolved.extend({'family':f,'partition':'CALENDAR_UNAVAILABLE','failure':plan['calendar_error']}
                          for f in ('hot_money','institutional','seats','northbound'))
    for gap in plan['prior_unresolved']:
        family,part=gap.get('family'),gap.get('partition')
        if part=='CALENDAR_UNAVAILABLE' and plan['trading_sessions']:
            continue
        candidates=[p for p in partitions if p['family']==family and p['partition']==part]
        covered=any(p['complete'] and
            (not gap.get('begin') or p['begin']<=gap['begin']) and
            (not gap.get('end') or p['end']>=gap['end']) for p in candidates)
        same_current=any(g['family']==family and g['partition']==part
            and g.get('begin')==gap.get('begin') and g.get('end')==gap.get('end') for g in unresolved)
        if not covered and not same_current:
            unresolved.append(gap)
    return {'version':s.VERSION,'target_date':plan['target_date'],'cutoff':manifest['finished_at'],
            'trading_sessions':plan['trading_sessions'],'partitions':partitions,'unresolved':unresolved,
            'policy_stops':sorted(stopped),
            'deferred_partitions':plan['deferred_partitions'],
            'forecast_documents':pdf_results,'pdf_selection_scope':'AT_MOST_TWO_LATEST_PER_FIRST_SIX_RETURNED_BROKERS_WITH_EPS_NOT_FULL_REPORT_COVERAGE',
            'capture_hash':manifest['capture_hash'],'requests':len(records),'source_calls_during_replay':0,
            'status':'READY' if not unresolved else 'PARTIAL_WITH_EXPLICIT_GAPS' if available else 'UNAVAILABLE_NOT_QUIET',
            'available_partitions':available,'identity':manifest['identity'], **s.AUTHORITY}


def capture(output, execution, *, previous_state=None, skip_hithink=False, transport=request_raw,
            clock=s.now, monotonic=time.monotonic, sleep=time.sleep):
    validate_identity(execution);output=Path(output)
    s.require(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents)),'OUTPUT_EXISTS_OR_SYMLINK')
    output.mkdir(parents=True)
    start=clock();started=monotonic();records=[];files={};stopped=set();last={};rawbytes=0
    today=s.clock(start).astimezone(s.ZONE).date().isoformat()
    if (previous_state or {}).get('target_date')==today:
        stopped.update((previous_state or {}).get('policy_stops',[]))
    s.require(stopped <= {'HT','FT','EM','HKEX'},'PRIOR_POLICY_STOPS')
    manifest={'version':s.VERSION,'identity':execution,'started_at':start,'finished_at':None,
              'previous_state':deepcopy(previous_state),'records':records,'authority':s.AUTHORITY}
    def save():
        manifest['finished_at']=clock()
        manifest['capture_hash']=canonical_hash({k:v for k,v in manifest.items() if k!='capture_hash'})
        (output/'capture.json').write_bytes(s.encoded(manifest))
    def get(request):
        nonlocal rawbytes
        i=len(records);provider=request['provider'];error=None
        if provider in stopped:error='PROVIDER_POLICY_STOP'
        elif provider=='HT' and skip_hithink:error='SOURCE_BUSY'
        elif len(records)>=s.MAX_REQUESTS or monotonic()-started>MAX_SECONDS or rawbytes+s.MAX_BODY>s.MAX_TOTAL_RAW:error='RESOURCE_BUDGET'
        if not error and provider in last:
            sleep(max(0,(20 if provider=='HT' else .25)-(monotonic()-last[provider])))
        record={'index':i,'request':request,'requested_at':clock(),'received_at':None,
                'body':None,'bytes':None,'sha256':None,'http_status':None,'error':error}
        try:
            if error is None:
                status,raw=transport(request)
                s.require(type(status)is int and isinstance(raw,bytes) and len(raw)<=s.MAX_BODY,'TRANSPORT_CONTRACT')
                for envname,_ in KEYS.values():
                    key=os.environ.get(envname,'')
                    s.require(not key or key.encode() not in raw,'CREDENTIAL_REFLECTION')
                record.update(body=f'raw-{i:04d}.body',bytes=len(raw),sha256=sha256(raw).hexdigest(),http_status=status)
                files[record['body']]=raw;(output/record['body']).write_bytes(raw);rawbytes+=len(raw)
                reason=_http_reason(status,raw)
                if status in STOP_CODES or 300<=status<400 or reason in {'BUSINESS_401','BUSINESS_403','BUSINESS_429'}:stopped.add(provider)
        except requests.Timeout:record['error']='TRANSPORT_TIMEOUT'
        except requests.ConnectionError:record['error']='TRANSPORT_CONNECTION'
        except requests.RequestException:record['error']='TRANSPORT_ERROR'
        except s.SourceError as exc:
            record['error']=str(exc)
            if str(exc) in {'CREDENTIAL_REFLECTION','DESTINATION_CHANGED'}:stopped.add(provider)
        record['received_at']=clock();records.append(record);last[provider]=monotonic()
        # Checkpoints survive later process failure; source status is rebuilt.
        if 'plan' in manifest:save()
        return record
    record=get(s.calendar_spec());cal=None
    if record['body'] is not None and _http_reason(record['http_status'],files[record['body']]) is None:
        try: cal=s.decode(files[record['body']])
        except (ValueError,TypeError): pass
    manifest['plan']=make_plan(start,cal,previous_state);save()
    for part in manifest['plan']['partitions']:
        total=pages=None
        for page in range(1,s.MAX_PAGES+1):
            if len(records)>=s.MAX_REQUESTS:break
            req=s.spec(part['family'],part['partition'],part['begin'],part['end'],page)
            if req.get('method')=='POST':
                channel,period=req['partition'].split('@')
                parent=next((r for r in records if r['request']['family']=='north_holdings' and
                             r['request']['partition']==channel and r['body'] and r['http_status']==200),None)
                if parent is None:break
                try:req={**req,'form_source':parent['body'],'form':docs.post_form(files[parent['body']],channel,period)}
                except (ValueError,KeyError,TypeError):break
            rec=get(req)
            if rec['body'] is None or _http_reason(rec['http_status'],files[rec['body']]):break
            try:
                obj=payload(files[rec['body']],req);_,count,npages=s.page_data(obj,req)
                if total is None:total,pages=count,npages
                s.require(total==count and pages==npages,'PAGE_DENOMINATOR_DRIFT')
                if page>=max(1,pages):break
            except (ValueError,KeyError,TypeError):break
    report_records=[r for r in records if r['request']['family']=='forecasts']
    scope=next(p for p in manifest['plan']['partitions'] if p['family']=='forecasts')
    report_part=_parse_partition(report_records,files,scope)
    for r in docs.select_reports(report_part['rows']):
        if len(records)>=s.MAX_REQUESTS:break
        get(docs.pdf_spec(r['values']['report_id'],scope['begin'],scope['end']))
    save();files['capture.json']=(output/'capture.json').read_bytes()
    observation=rebuild(manifest,files,expected_identity=execution,cutoff=manifest['finished_at'])
    return observation


def replay(files, execution, *, cutoff):
    s.require('capture.json' in files,'CAPTURE_MISSING')
    return rebuild(s.decode(files['capture.json']),files,expected_identity=execution,cutoff=cutoff)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--previous-state',type=Path)
    parser.add_argument('--skip-hithink',action='store_true')
    args=parser.parse_args(argv)
    previous=None
    if args.previous_state:
        raw=args.previous_state.read_bytes();s.require(len(raw)<=512*1024,'PREVIOUS_STATE_SIZE')
        previous=json.loads(raw)
    result=capture(args.output,identity(os.environ),previous_state=previous,skip_hithink=args.skip_hithink)
    print(json.dumps({k:result[k] for k in ('version','status','target_date','capture_hash','requests','available_partitions','unresolved')},ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
