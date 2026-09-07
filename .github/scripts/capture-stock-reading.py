"""One bounded HiThink stock reading attempt, with credential-free replay.

No producer, fallback provider, RSS or state writes. Original artifact binding is
retained. Supplied B daily-reference fixtures remain test-only. The actual path
uses HiThink own dated bars, latest quote and reported-action checks.
"""
from __future__ import annotations

import argparse
import json
import os
import runpy
import time
from datetime import datetime, timezone, timedelta
from html import escape
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import theme_radar_probe as probe
from decision_kernel.runtime import hithink_stock_reading
from decision_kernel.runtime.economic_release_inputs import load_release_inputs
from decision_kernel.runtime.economic_market_context import build_economic_market_context
from decision_kernel.runtime.sector_radar_audit import _check_safe_json, SectorRadarAuditError
from decision_kernel.runtime.sector_radar_persistence import load_sector_radar_persistent_bundle

ROOT = Path('stock-reading-run')
VERSION = 'stock-reading-capture-replay-v6'
LIVE_COMPANIES = 'radar_inputs/economic-company-links-livestock-v2.json'
PUBLIC, SYNTHETIC = 'LIVE_HITHINK', 'SYNTHETIC_TEST_ONLY'
COMPLETE, FAILED = 'COMPLETE_STOCK_READING', 'INCOMPLETE_STOCK_READING'
PARTIAL = 'COMPLETED_BATCH_WITH_STOCK_DATA_GAPS'
NOT_STARTED = 'STOCK_READING_NOT_STARTED'
INTENT_REASONS = {
    'STOCK_MARKET_RUN_ID_REQUIRED': '选择 stock-reading 时必须填写 stock-market-run-id：请输入要使用的、已成功的 sector-radar-shadow 运行编号，不是本次股票编号。',
    'STOCK_MARKET_RUN_ID_INVALID': 'stock-market-run-id 必须是一个完整的正整数运行编号，不能填 latest、网址、前后空格或其他文字。',
    'STOCK_MARKET_RUN_ID_IS_CURRENT_RUN': 'stock-market-run-id 不能是本次股票任务自身；必须明确选择已成功的 Sector 输入运行。',
}
REASONS = {
    **INTENT_REASONS,
    'STOCK_CALENDAR_COVERAGE_INSUFFICIENT': '本次交易日历未覆盖保存窗口和实际读取日期，不能证明最新完成交易日；不按星期推算或补日。',
    'STOCK_CALENDAR_STATE_WINDOW_DIFFERS': '真实交易日历与保存的行业状态窗口不一致；缺失的中间交易日不能跨日桥接。',
    'STOCK_STATE_NOT_LATEST_COMPLETED_SESSION': '实际日历显示已有更新的完成交易日；请先取得相应合格Sector状态，漏过中间日先qualified recovery。',
    'HISTORY_READY_AFTER_ACTUAL_RECEIPT': '个股历史就绪时间晚于该响应实际接收时间；后续请求经过的时间不能修复这次未来时钟。',
    'QUOTE_READY_AFTER_ACTUAL_RECEIPT': '报价就绪时间晚于这份报价实际接收时间；不会等待公司行为请求后再把未来时钟判为有效。',
    'QUOTE_ACTUAL_RECEIPT_REQUIRED': '非空报价就绪时间必须绑定该响应自己的有效接收时间，不能用后续检查时间替代。',
    'CURRENT_QUOTE_HISTORY_MISMATCH': '当前快照的关键价格／成交量不一致，或成交额差异超过明示有界容差；不修改历史原值，也不自动扩大容差。',
    'REPORTED_CORPORATE_ACTION_IN_WINDOW_REQUIRES_REVIEW': 'HiThink报告的公司行为跨过本次5日或20日筛选区间；该区间原始价格不可直接比较。本版不自动复权，不展示该股票卡片。',
    'UNPRICED_OR_NONTRADING_SESSION_IN_PATH': '个股窗口中存在无有效成交的交易日；不是已确认停牌或退市，不用前值补齐历史。',
    'PROVIDER_BUSINESS_REQUEST_FAILED': '供应商返回业务失败码；HTTP成功不等于本次数据请求成功。原响应通过安全检查后单独保留。',
    'QUALIFIED_DAILY_REFERENCE_HISTORY_UNAVAILABLE': '所供独立逐日前收参考价测试输入缺失；不能从昨日收盘补字段。此检查不是HiThink原始价格观察必须新增第二家供应商的理由。',
    'REFERENCE_WINDOW_OR_CURRENT_QUOTE_MISSING': '独立的61日参考价窗口或同日当前报价不完整。',
    'EXACT_61_COMPLETED_STOCK_SESSIONS_REQUIRED': '必须有该股票自己的连续61个明确完成交易日；不丢日、不填值、不用行业收益或10日dump替代。',
    'PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW': '原始前收参考价与上一日真实收盘不连续；保留公司行为／口径问题，不自动复权或加容差。',
    'TRANSPORT_REQUEST_FAILED': '请求或响应解码失败；没有自动重试，也没有使用替代来源。',
    'UNSAFE_RESPONSE_NOT_RETAINED': '响应未通过凭据／安全检查；危险内容未保存，不能离线重新认证被丢弃的原文。',
    'REQUIRED_INPUT_OR_FIELD_MISSING': '需要的输入文件或字段缺失；本次不能形成完整结果。',
    'INPUT_CLOCK_IDENTITY_OR_SCHEMA_REJECTED': '时间、身份、输入口径或结构检查未通过；具体步骤及已取得输入保留在附件中。',
    'REVERSED_FINISH_CLOCK': '完成时间早于最后接收时间，结果不可发布。',
}


class StockRequestFailure(RuntimeError):
    pass


class UnsafeStockResponse(ValueError):
    pass


def sibling(name):
    return runpy.run_path(str(Path(__file__).with_name(name)), run_name='stock_reading_helper')


def data(value):
    return (canonical_json(value)+'\n').encode('utf-8')


def read(path):
    from decision_kernel.runtime.economic_market_context import _read_json
    return _read_json(path)


def write(path, value):
    with path.open('xb') as f:
        f.write(data(value))


def company_scope(value):
    """Two explicit reviewed inputs, not latest/fallback or caller-nominated stocks."""
    if not isinstance(value, str) or value not in {stock.COMPANY_MANIFEST, LIVE_COMPANIES}:
        raise ValueError('an exact reviewed stock company manifest is required')
    return value


def inventory(root):
    helper = sibling('build-sector-radar-reading.py')
    files = {}
    total = 0
    probe._safe_path(root)
    if not root.is_dir():
        raise ValueError('complete stock reading directory required')
    for p in sorted(root.rglob('*')):
        probe._safe_path(p)
        if p.is_dir():
            continue
        raw = helper['_file'](p); total += len(raw)
        if len(files) >= helper['MAX_FILES'] or total > helper['MAX_BYTES']:
            raise ValueError('stock reading artifact exceeds inherited delivery budget')
        files[p.relative_to(root).as_posix()] = helper['_digest'](raw)
    return files


def load_inputs(root, at, *, company_manifest=stock.COMPANY_MANIFEST):
    company_manifest = company_scope(company_manifest)
    helper = sibling('build-sector-radar-reading.py')
    from decision_kernel.runtime.sector_parent_hints import load_sector_parent_hints
    hints = load_sector_parent_hints(root/helper['HINTS'])
    bundle = load_sector_radar_persistent_bundle(root/'state',
        expected_repository='auguspp/decision-kernel',
        expected_workflow='.github/workflows/sector-radar-shadow.yml',
        expected_parent_hint_mapping_hash=hints.mapping_hash)
    inputs = load_release_inputs(root/helper['SEED'],root/helper['REVIEWS'],as_of=at)
    association = build_economic_market_context(market_state=bundle.market_state,event_ledger=bundle.event_ledger,
        observations=inputs.seed_observations, reviewed_releases=inputs.review_paths,
        links=read(root/helper['LINKS']), as_of=at, generated_at=at)
    plan = stock.prepare_stock_reading(root,bundle.market_state,bundle.event_ledger,association,
        observed_at=at,company_manifest=company_manifest)
    return bundle, association, plan


def page(report, provenance):
    result = stock.render_stock_reading(report)
    notice = ('合成验收样本：公司名可能来自真实留存资料，成员、行情和参考价是测试数据，不是实际选股。'
              if provenance == SYNTHETIC else
              '本次 HiThink 数据读取；公司资料是留存摘录，未重新取得公司原文。原始价格观察不是复权或总回报认证。')
    return result.replace('<h1>', '<p class="notice">'+notice+'</p><h1>',1).encode('utf-8')


def failure_details(exc):
    if isinstance(exc, stock.StockReadingInputError):
        if exc.category not in stock.STATUS_LABELS or exc.reason_code not in REASONS:
            raise ValueError('unrecognized stock failure classification')
        return exc.category, exc.reason_code, exc.thscode
    if isinstance(exc, StockRequestFailure):
        return 'REQUEST_FAILED', 'TRANSPORT_REQUEST_FAILED', None
    if isinstance(exc, UnsafeStockResponse):
        return 'DATA_QUALIFICATION_FAILED', 'UNSAFE_RESPONSE_NOT_RETAINED', None
    if isinstance(exc, (FileNotFoundError, KeyError)):
        return 'DATA_INSUFFICIENT', 'REQUIRED_INPUT_OR_FIELD_MISSING', None
    return 'DATA_QUALIFICATION_FAILED', 'INPUT_CLOCK_IDENTITY_OR_SCHEMA_REJECTED', None


def failure_page(report):
    """A failed attempt is a readable first screen, never a successful empty scan."""
    report = stock._plain(report)
    e = lambda value: escape(str(value), quote=True)
    reason = report['reason_code']
    if reason not in REASONS or report['failure_category'] not in stock.STATUS_LABELS:
        raise ValueError('unknown failure page classification')
    rows = ''.join('<tr><td>'+e(row['company_name']+' '+row['thscode'])+'</td><td>'+e(row['status'])+'</td></tr>'
                   for row in report['planned_issuer_outcomes'])
    events = report['recorded_sector_events_latest_session']
    event_text = '尚未完成来源核验' if events is None else f'{events} 个已记录行业事件；没有新事件不等于没有仍强势路径'
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">'
        '<title>股票观察 · 本次未完成</title><style>body{font:16px/1.7 system-ui;margin:0;padding:20px;background:#f4f6f8;color:#20313d}main{max-width:920px;margin:auto;background:white;padding:24px}p,td,code{overflow-wrap:anywhere}table{width:100%;border-collapse:collapse}td{border-bottom:1px solid #ddd;padding:10px}h1{font-size:26px}@media(max-width:600px){body{padding:10px}main{padding:14px}}</style>'
        '<main><h1>股票观察 · 本次不凑名单</h1>'
        f'<h2>{e(stock.STATUS_LABELS[report["failure_category"]])}</h2>'
        '<p><strong>未形成合格股票名单；不是“扫描成功且零匹配”。值得看不等于值得买。</strong></p>'
        f'<p>{e(REASONS[reason])}</p><p>原因代码：<code>{e(reason)}</code></p>'
        f'<p>输入截止：{e(report["observed_at"])}；完成：{e(report["finished_at"])}；来源：{e(report["provenance"])}。</p>'
        f'<p>来源事件：{e(event_text)}。本层不创建新事件。</p>'
        '<p>只限已接入公司依据及其活跃方向，不是全A股盲筛。后续未完成项不视为条件不满足；之前已取得的输入也不冒充完整筛选。</p>'
        '<h2>完整计划与未完成项</h2><table><tr><th>计划公司</th><th>本次状态</th></tr>'+rows+'</table>'
        '<p>保留的请求与响应、精确输入及失败类别见 capture.json、plan.json 和 responses/；没有响应的请求不制造数据。</p>'
        '<p><strong>下一核查：</strong>先补齐上述资格缺口；不重复下载旧10日dump，不用合成页面或人工点名替代真实程序输出。</p>'
        '<footer>SHADOW OBSERVATION ONLY<br>HUMAN ATTENTION AUTHORITY = NONE<br>RESEARCH AUTHORITY = NONE<br>INVESTMENT AUTHORITY = NONE</footer></main></html>\n').encode('utf-8')


def capture(source_root, state_dir, output, *, observed_at, transport, workflow,
            provenance=SYNTHETIC, credential='', now=lambda:datetime.now(timezone.utc),
            pause=time.sleep, reference_inputs=None, company_manifest=stock.COMPANY_MANIFEST):
    # Historical library callers remain explicit/reproducible; the live CLI below
    # selects LIVE_COMPANIES. Never backdate v2 or silently fall back to v1.
    company_manifest = company_scope(company_manifest)
    for p in (source_root,state_dir,output):
        probe._safe_path(p)
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (source_root,state_dir)):
        raise ValueError('stock output must be new and outside source directories')
    stock._reference_inputs(reference_inputs)
    if (provenance not in {PUBLIC,SYNTHETIC} or (provenance==PUBLIC and not credential)
            or (provenance==PUBLIC and reference_inputs is not None)):
        raise ValueError('live capture cannot use synthetic normalized reference inputs')
    helper = sibling('build-sector-radar-reading.py')
    files, directories = helper['_source_files'](source_root,state_dir,as_of=observed_at,
        company_manifest=company_manifest)
    output.mkdir(parents=True)
    for name in directories:
        (output/'inputs'/name).mkdir(parents=True,exist_ok=True)
    for name, raw in files.items():
        p=output/'inputs'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    if reference_inputs is not None:
        _check_safe_json(reference_inputs, credential or None)
        write(output/'synthetic-reference-inputs.json', reference_inputs)
    report = {'version':VERSION,'status':FAILED,'observed_at':observed_at,'finished_at':None,
        'provenance':provenance,'workflow':workflow,'failure_type':None,'failure_category':None,
        'reason_code':None,'failed_thscode':None,'requests':[],
        'response_semantics':'DECODED_PROVIDER_JSON_NOT_ORIGINAL_HTTP_BYTES',
        'source_directories':directories,'plan_hash':None,'projection_hash':None,'coverage':None,
        'company_manifest':company_manifest,
        'reference_input_hash':canonical_hash(reference_inputs) if reference_inputs is not None else None,
        'planned_issuer_outcomes':[], 'recorded_sector_events_latest_session':None,
        'remote_upload_verified':False,**stock.LIMITS}
    last=observed_at
    try:
        bundle, association, plan = load_inputs(output/'inputs',observed_at,company_manifest=company_manifest)
        write(output/'association.json',association);write(output/'plan.json',plan)
        report['plan_hash']=plan['plan_hash']
        report['recorded_sector_events_latest_session']=plan['recorded_sector_events_latest_session']
        report['planned_issuer_outcomes']=[{'thscode':r['thscode'],'company_name':r['company_name'],
            'status':'NOT_COMPLETED_NO_SELECTION_CLAIM'} for r in plan['issuers']]
        def clock(value):
            nonlocal last
            stock.check_observation_clock(bundle.market_state,value)
            if not last <= value <= observed_at+timedelta(minutes=30):
                raise ValueError('request/receipt clock reversed or plan expired')
            last=value
        def request(path,params):
            if len(report['requests']) >= plan['maximum_request_count'] or len(report['requests']) >= stock.MAX_REQUESTS:
                raise ValueError('stock request budget reached; no partial success')
            if report['requests']:
                pause(20)
            clock(now())
            entry={'path':path,'params':dict(params),'requested_at':last,'received_at':None,
                   'response_file':None,'error_type':None,'http_status':None}
            report['requests'].append(entry)
            try:
                try:
                    value=transport(path,params)
                except (ValueError,RuntimeError,OSError,TypeError) as exc:
                    cause = exc.__cause__ or exc
                    status=getattr(cause,'http_status',None)
                    if type(status) is not int:status=getattr(cause,'code',None)
                    if type(status) is int and 100 <= status <= 599:entry['http_status']=status
                    raise StockRequestFailure('TRANSPORT_REQUEST_FAILED') from None
                entry['received_at']=now();clock(entry['received_at'])
                try:
                    _check_safe_json(value,credential or None)
                except (ValueError, SectorRadarAuditError):
                    raise UnsafeStockResponse('UNSAFE_RESPONSE_NOT_RETAINED') from None
                raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
                if len(raw)>8*1024*1024:
                    raise ValueError('decoded stock response exceeds audit byte budget')
                name=f'responses/{len(report["requests"]):02d}.json'
                p=output/name;p.parent.mkdir(exist_ok=True);p.write_bytes(raw)
                entry.update(response_file=name,http_status=200)
                return value
            except (ValueError,RuntimeError,OSError,TypeError) as exc:
                entry['error_type']=type(exc).__name__
                raise
        result=stock.observe_stock_reading(plan,bundle.market_state,request_json=request,
            observed_at=observed_at,cutoff_clock=lambda:last,reference_inputs=reference_inputs)
        report['projection_hash']=result['projection_hash']
        write(output/'stock-reading.json',result)
        (output/'index.html').write_bytes(page(result,provenance))
        if helper['_source_files'](source_root,state_dir,as_of=observed_at,
                company_manifest=company_manifest)!=(files,directories):
            raise ValueError('source inputs changed during stock reading')
        report['planned_issuer_outcomes']=[{'thscode':r['thscode'],'company_name':r['company_name'],
            'status':r['status']} for r in result['projection']['all_stock_observations']]
        report['coverage']=result['projection']['coverage']
        report['status']=COMPLETE if report['coverage']['scope_complete'] else PARTIAL
    except (ValueError,RuntimeError,OSError,KeyError,TypeError) as exc:
        report['failure_type']=type(exc).__name__
        report['failure_category'],report['reason_code'],report['failed_thscode']=failure_details(exc)
        report['projection_hash']=None
    report['finished_at']=now()
    if report['finished_at']<last:
        report.update(status=FAILED,failure_type='ReversedFinishClock',projection_hash=None,
            failure_category='DATA_QUALIFICATION_FAILED',reason_code='REVERSED_FINISH_CLOCK')
    if report['status']==FAILED:
        report['coverage']=None
        for row in report['planned_issuer_outcomes']:
            row['status'] = (report['failure_category'] if row['thscode']==report['failed_thscode']
                             else 'NOT_COMPLETED_NO_SELECTION_CLAIM')
        (output/'stock-reading.json').unlink(missing_ok=True)
        (output/'index.html').write_bytes(failure_page(report))
    report['files']=inventory(output)
    report['capture_hash']=canonical_hash(report)
    write(output/'capture.json',report)
    return read(output/'capture.json')


def verify(output):
    report=read(output/'capture.json')
    if (report['version']!=VERSION or not stock._hash_ok(report,'capture_hash')
            or any(report[k]!=v for k,v in stock.LIMITS.items()) or report['remote_upload_verified'] is not False
            or report['provenance'] not in {PUBLIC,SYNTHETIC}
            or report['files']!={k:v for k,v in inventory(output).items() if k!='capture.json'}):
        raise ValueError('stock capture identity or retained bytes differ')
    company_manifest = company_scope(report['company_manifest'])
    at=probe._clock(report['observed_at']);finished=probe._clock(report['finished_at'])
    if finished<at:raise ValueError('invalid finish clock')
    reference_path=output/'synthetic-reference-inputs.json'
    refs=read(reference_path) if reference_path.exists() else None
    stock._reference_inputs(refs)
    if (report['reference_input_hash']!=(canonical_hash(refs) if refs is not None else None)
            or (report['provenance']==PUBLIC and refs is not None)):
        raise ValueError('reference provenance changed; normalized fixtures are never live origin evidence')
    if report['status'] not in {COMPLETE,PARTIAL,FAILED}:
        raise ValueError('unknown capture status')
    bundle,association,plan=load_inputs(output/'inputs',at,company_manifest=company_manifest)
    if (plan!=read(output/'plan.json') or association!=read(output/'association.json')
            or report['plan_hash']!=plan['plan_hash']):
        raise ValueError('stock plan does not reconstruct from original source/state inputs')
    position=0;last=at
    def request(path,params):
        nonlocal position,last
        if position>=len(report['requests']):raise ValueError('unrecorded request; no network fallback')
        entry=report['requests'][position];position+=1
        requested=probe._clock(entry['requested_at'])
        if (entry['path']!=path or entry['params']!=params or not last<=requested<=finished
                or requested>at+timedelta(minutes=30)):
            raise ValueError('stock request identity or request clock differs')
        stock.check_observation_clock(bundle.market_state,requested)
        if entry['error_type'] is not None:
            if entry['response_file'] is not None:
                raise ValueError('discarded response cannot be claimed as retained input')
            if entry['error_type']=='StockRequestFailure':
                if entry['received_at'] is not None:
                    raise ValueError('transport failure cannot claim a decoded response receipt')
                raise StockRequestFailure('TRANSPORT_REQUEST_FAILED')
            if entry['error_type']=='UnsafeStockResponse':
                received=probe._clock(entry['received_at'])
                if not requested<=received<=finished or received>at+timedelta(minutes=30):
                    raise ValueError('discarded unsafe response has an invalid receipt clock')
                stock.check_observation_clock(bundle.market_state,received)
                raise UnsafeStockResponse('UNSAFE_RESPONSE_NOT_RETAINED')
            raise ValueError('recorded request/receipt qualification failed')
        received=probe._clock(entry['received_at'])
        if (entry['http_status']!=200 or entry['response_file']!=f'responses/{position:02d}.json'
                or not requested<=received<=finished or received>at+timedelta(minutes=30)):
            raise ValueError('stock response identity or actual clock differs')
        stock.check_observation_clock(bundle.market_state,received)
        value=read(output/entry['response_file']);_check_safe_json(value)
        last=received;return value
    try:
        result=stock.observe_stock_reading(plan,bundle.market_state,request_json=request,
            observed_at=at,cutoff_clock=lambda:last,reference_inputs=refs)
    except (ValueError,RuntimeError,OSError,KeyError,TypeError) as exc:
        if report['status']!=FAILED:
            raise
        expected_outcomes=[{'thscode':r['thscode'],'company_name':r['company_name'],
            'status':report['failure_category'] if r['thscode']==report['failed_thscode'] else 'NOT_COMPLETED_NO_SELECTION_CLAIM'}
            for r in plan['issuers']]
        if (report['planned_issuer_outcomes']!=expected_outcomes or report['coverage'] is not None
                or report['recorded_sector_events_latest_session']!=plan['recorded_sector_events_latest_session']
                or (report['failure_category'],report['reason_code'],report['failed_thscode'])!=failure_details(exc)
                or position!=len(report['requests']) or (output/'stock-reading.json').exists()
                or (output/'index.html').read_bytes()!=failure_page(report)):
            raise ValueError('incomplete stock attempt or negative page does not reconstruct') from None
        return {'status':'RETAINED_INCOMPLETE_ATTEMPT_NOT_STOCK_SELECTION','network_calls':0,
            'failure_category':report['failure_category'],'reason_code':report['reason_code'],
            'failure_replay':('RECORDED_FAILURE_ONLY_REMOTE_CAUSE_NOT_REPROVEN' if any(r['error_type'] for r in report['requests'])
                              else 'REPRODUCED_FROM_RETAINED_INPUTS'),
            'capture_hash':report['capture_hash'],**stock.LIMITS}
    expected_outcomes=[{'thscode':r['thscode'],'company_name':r['company_name'],'status':r['status']}
        for r in result['projection']['all_stock_observations']]
    coverage=result['projection']['coverage']
    expected_status=COMPLETE if coverage['scope_complete'] else PARTIAL
    if (report['planned_issuer_outcomes']!=expected_outcomes or report['coverage']!=coverage
            or report['recorded_sector_events_latest_session']!=plan['recorded_sector_events_latest_session']
            or report['status']!=expected_status or position!=len(report['requests']) or position>plan['maximum_request_count']
            or position>stock.MAX_REQUESTS or report['projection_hash']!=result['projection_hash']
            or report['failure_type'] is not None or report['failure_category'] is not None or report['reason_code'] is not None
            or (output/'stock-reading.json').read_bytes()!=data(result)
            or (output/'index.html').read_bytes()!=page(result,report['provenance'])):
        raise ValueError('stock result/page does not reconstruct from exact original inputs')
    return {'status':('ORIGINAL_STOCK_INPUTS_AND_PAGE_REBUILT' if coverage['scope_complete'] else
                      'STOCK_BATCH_WITH_DATA_GAPS_REBUILT'), 'capture_hash':report['capture_hash'],
            'projection_hash':result['projection_hash'],'stock_count':len(result['projection']['surfaced_stocks']),
            'provenance':report['provenance'],'requests_replayed':position,'network_calls':0,
            'coverage':coverage,**stock.LIMITS}


def intent(env, at):
    wf=sibling('capture-theme-probe.py')['workflow_identity'](env)
    if env.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or env.get('TRIAL_PURPOSE')!='stock-reading':
        raise ValueError('stock reading requires explicit manual intent')
    raw=env.get('STOCK_MARKET_RUN_ID','')
    if isinstance(raw,str) and not raw.strip():
        raise stock.StockReadingInputError('DATA_INSUFFICIENT','STOCK_MARKET_RUN_ID_REQUIRED')
    try:
        run=sibling('prepare-native-rss-successor.py')['number'](raw)
    except (ValueError,TypeError):
        raise stock.StockReadingInputError('DATA_QUALIFICATION_FAILED','STOCK_MARKET_RUN_ID_INVALID') from None
    if run==wf['GITHUB_RUN_ID']:
        raise stock.StockReadingInputError('DATA_QUALIFICATION_FAILED','STOCK_MARKET_RUN_ID_IS_CURRENT_RUN')
    return {'workflow':wf,'market_run_id':run,'prepared_at':at,'semantics':stock.SEMANTICS}


def initialize(root, env, at):
    """Retain safe intent diagnostics without inventing a scan or input binding."""
    probe._safe_path(root)
    try:
        value=intent(env,at)
    except stock.StockReadingInputError as exc:
        if exc.reason_code not in INTENT_REASONS:
            raise
        # intent checked the workflow first. Keep only that validated allowlist,
        # never the raw invalid field or the environment/credentials.
        value={'status':NOT_STARTED,'phase':'INTENT_VALIDATION',
            'reason_code':exc.reason_code,'failure_category':exc.category,
            'message':INTENT_REASONS[exc.reason_code], 'recorded_at':at,
            'workflow':sibling('capture-theme-probe.py')['workflow_identity'](env),
            'market_run_id':None,'market_requests':0,'stock_scan_completed':False,
            'remote_upload_verified':False,**stock.LIMITS}
        root.mkdir(exist_ok=False)
        write(root/'preflight.json',value)
        explanation=(value['message']+'\n\n'
            '本次仅在输入校验阶段停止：未绑定行情状态，未调用 HiThink，未执行股票扫描。'
            '不是成功零匹配，也不是行情认证失败或真实数据资格验收。'
            '没有使用 latest 或 bootstrap 替代输入。请修正参数后发起新的 Run workflow，不使用 Re-run jobs。\n'
            'SHADOW OBSERVATION ONLY; HUMAN ATTENTION / RESEARCH / INVESTMENT AUTHORITY = NONE\n')
        with (root/'README.txt').open('x',encoding='utf-8') as stream:
            stream.write(explanation)
        with (root/'index.html').open('x',encoding='utf-8') as stream:
            stream.write('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; base-uri \'none\'">'
                '<title>股票读取未开始</title><h1>股票读取未开始</h1><p>'
                +escape(explanation).replace('\n','<br>')+'</p></html>\n')
        with open(env['GITHUB_OUTPUT'],'a') as stream:
            stream.write('artifact_ready=true\n')
        return value
    root.mkdir(exist_ok=False);write(root/'request.json',value)
    with open(env['GITHUB_OUTPUT'],'a') as stream:
        stream.write('artifact_ready=true\nmarket_run_id='+value['market_run_id']+'\n')
    return value


def binding(root, request):
    return sibling('native-feed-acceptance.py')['metadata'](request,'market',read(root/'market-run.json'),read(root/'market-artifacts.json'))


def bound_state(root, request):
    bound=binding(root,request)
    if bound!=read(root/'market-binding.json'):raise ValueError('market binding changed')
    helper=sibling('build-sector-radar-reading.py')
    if {p.name for p in (root/'market').iterdir()}!=helper['STATE_FILES']:raise ValueError('exact market package required')
    b=load_sector_radar_persistent_bundle(root/'market',expected_repository='auguspp/decision-kernel',
                                        expected_workflow='.github/workflows/sector-radar-shadow.yml')
    m=b.manifest
    if str(m.source_run_id)!=bound['run_id'] or m.source_commit_sha!=bound['commit'] or m.source_run_attempt!=1:
        raise ValueError('state does not identify selected successful remote run')
    return b


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['init','metadata','capture','verify'])
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args(argv);root=args.root
    try:
        probe._safe_path(root)
        if args.mode=='init':
            value=initialize(root,os.environ,datetime.now(timezone.utc).isoformat())
        else:
            request=read(root/'request.json')
            if request['workflow']!=sibling('capture-theme-probe.py')['workflow_identity'](os.environ):
                raise ValueError('workflow identity changed')
            if args.mode=='metadata':
                value=binding(root,request);write(root/'market-binding.json',value)
                with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('artifact_id='+value['artifact_id']+'\n')
            else:
                bound_state(root,request)
                if args.mode=='capture':
                    key=os.environ.get('HITHINK_FINANCE_API_KEY','')
                    value=capture(Path(os.environ['GITHUB_WORKSPACE']),root/'market',root/'reading',
                        observed_at=datetime.now(timezone.utc),workflow=request['workflow'],provenance=PUBLIC,credential=key,
                        company_manifest=LIVE_COMPANIES,
                        transport=lambda p,q:hithink_stock_reading.request_json(api_key=key,path=p,params=q))
                else:
                    if os.environ.get('HITHINK_FINANCE_API_KEY'):raise ValueError('replay cannot receive market credentials')
                    value=verify(root/'reading');write(root/'verification.json',value)
        print(canonical_json(value))
        if args.mode=='capture' and os.environ.get('GITHUB_STEP_SUMMARY'):
            if value.get('status')==FAILED:
                text=('## 股票观察：'+stock.STATUS_LABELS[value['failure_category']]+'\n\n'
                    +REASONS[value['reason_code']]+'\n\n不是成功空名单。附件内 reading/index.html 为本次可读缺口页。\n')
            elif value.get('status')==PARTIAL:
                c=value['coverage']
                text=('## 股票批次已处理：存在单股数据隔离\n\n'
                    f"计划 {c['planned_issuers']}；已完成条件检查 {c['evaluated_issuers']}；"
                    f"通过 {c['qualified_issuers']}；条件不满足 {c['conditions_not_met_issuers']}；"
                    f"数据不可用 {c['unavailable_issuers']}。\n\n"
                    '**仅交付可用数据子集，不是全计划排名或完整零匹配。** '
                    '业务码3002仍是不可用输入，不代表已确认无公司行为。具体股票与原因见 reading/index.html / stock-reading.json。\n')
            else:
                text=''
            if text:
                with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(text)
        return 2 if value.get('status') in {FAILED,NOT_STARTED,'RETAINED_INCOMPLETE_ATTEMPT_NOT_STOCK_SELECTION'} else 0
    except (ValueError,RuntimeError,OSError,KeyError,TypeError) as exc:
        category,reason,_=failure_details(exc)
        print(canonical_json({'status':'STOCK_READING_UNAVAILABLE','error_type':type(exc).__name__,
                             'failure_category':category,'reason_code':reason}))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
