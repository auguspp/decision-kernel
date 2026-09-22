"""One explicit batch of existing sources + FTShare market/sector/industry + CNEquity.

No scheduler, new research executor or canonical price-source switch. Raw
captures, field comparisons and failures remain distinct from research admission.
"""
from __future__ import annotations
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from . import ftshare_market_inputs as market
from .ftshare_financial import raw_json, decode
from .ftshare_discovery import _require as require, now, _clock
from .sector_radar import SectorPricePoint, SectorPriceSeries, _validate_series
from .external_radar_observations import INDUSTRY_KIND, AUTHORITY, _seal
from .reviewed_question_reading import _text as md

VERSION = 'provider-batch-v1'
TZ = ZoneInfo('Asia/Shanghai')
STOPS = {'AUTHENTICATION_UNAVAILABLE','AUTHENTICATION_FAILED','ENTITLEMENT_DENIED',
         'RATE_LIMITED','CREDENTIAL_REFLECTION_REJECTED','REDIRECT_REJECTED'}


def day(value):
    text = str(value)
    if re.fullmatch(r'[0-9]{8}', text):
        text = text[:4] + '-' + text[4:6] + '-' + text[6:]
    require(re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', text), 'DATE_INVALID')
    return date.fromisoformat(text)


def number(value, *, positive=False):
    require(not isinstance(value, bool) and isinstance(value, (str,int,float,Decimal)), 'NUMBER_UNKNOWN')
    result = Decimal(str(value))
    require(result.is_finite() and (not positive or result > 0), 'NUMBER_INVALID')
    return result


def plan(config):
    require(isinstance(config, dict) and set(config) == {'ticker','session','sw_code','sw_name',
            'concept_code','concept_name','contracts'}, 'BATCH_FIELDS_INVALID')
    ticker, session = config['ticker'], day(config['session'])
    stamp = session.strftime('%Y%m%d'); page = {'page':1,'page_size':200}
    contracts = config['contracts']
    require(isinstance(contracts, dict) and set(contracts) == {'LC','CU','RB'}, 'THREE_VARIETIES_REQUIRED')
    require(all(isinstance(config[k], str) and 0 < len(config[k]) <= 80 for k in
                ('sw_name','concept_name')), 'NAME_INVALID')
    queries = [
        ('stock','stock',{'code':ticker,'trade_date':stamp,**page}),
        ('flow','flow',{'symbol':ticker,'trade_date':stamp,**page}),
        ('sw_members','sw_members',{'industry_code':config['sw_code']}),
        ('sw_metrics','sw_metrics',{'industry_code':config['sw_code'],'start_date':stamp,'end_date':stamp,**page}),
        ('concept_members','concept_members',{'board_code':config['concept_code']}),
        ('concept_prices','concept_prices',{'board_code':config['concept_code'],'start_date':stamp,'end_date':stamp,**page})]
    start = int(datetime.combine(session - timedelta(days=30), time(), TZ).timestamp()*1000)
    end = int(datetime.combine(session, time(23,59,59), TZ).timestamp()*1000)
    for variety in ('LC','CU','RB'):
        contract = contracts[variety]
        require(isinstance(contract, str) and contract.startswith(variety), 'CONTRACT_VARIETY_MISMATCH')
        queries += [(variety+'_base','futures_base',{'symbol':contract,'trade_date':stamp}),
                    (variety+'_prices','futures_prices',{'symbol':contract,'interval':'daily','start':start,'end':end,'limit':64}),
                    (variety+'_warehouse','warehouse',{'symbol':variety,'trade_date':stamp,**page})]
    for _, route, params in queries:
        market.validate_request(route, params)
    return queries


def records(capture):
    require(capture.get('status') in {'COMPLETE','EMPTY'}, 'SOURCE_UNAVAILABLE')
    return capture['rows']


def _base(kind, capture):
    return {'kind':kind, 'status':'CONTEXT_READY', 'provider':'FTSHARE',
            'capture_status':capture['status'], 'retrieved_at':capture['finished_at'],
            'historical_availability':'NOT_ESTABLISHED', 'qualification':'CONTEXT_ONLY',
            'research_execution_allowed':False, 'investment_authority':'NONE'}


def stock_context(capture, ticker, session):
    values = records(capture)
    require(len(values) == 1, 'ONE_STOCK_SESSION_REQUIRED')
    row = values[0]['data']
    require(row.get('symbol') == ticker and day(row.get('trade_date')) == session, 'STOCK_IDENTITY_OR_SESSION')
    prices = {k:number(row.get(k), positive=True) for k in ('open','high','low','close','prev_close')}
    require(prices['low'] <= min(prices['open'],prices['close']) <= max(prices['open'],prices['close']) <= prices['high'], 'OHLC_INVALID')
    require(type(row.get('volume')) is int and row['volume'] >= 0 and number(row.get('turnover')) >= 0, 'VOLUME_OR_AMOUNT_INVALID')
    return {**_base('MARKET_EXPRESSION_CONTEXT',capture), 'ticker':ticker, 'session':str(session),
            'prices':prices, 'volume':row['volume'], 'volume_unit':'SHARES', 'turnover':number(row['turnover']),
            'currency':'CNY', 'adjustment':'PROVIDER_RAW_NOT_CANONICAL_ADJUSTMENT',
            'cum_adjust_factor':'UNUSABLE_BY_DOCUMENTED_CONTRACT', 'source_record':values[0]}


def compare_stock(context, reference):
    """Visible residuals only. Never modifies the original market qualification."""
    require(reference.get('ticker') == context['ticker'] and reference.get('session') == context['session']
            and reference.get('volume_unit') == 'SHARES' and reference.get('currency') == 'CNY'
            and reference.get('adjustment') == 'NONE'
            and re.fullmatch(r'[a-f0-9]{64}', str(reference.get('source_sha256',''))), 'REFERENCE_IDENTITY_OR_UNITS')
    differences = {k:number(v) - number(reference['prices'][k]) for k,v in context['prices'].items()}
    return {'kind':'SAME_SESSION_PROVIDER_COMPARISON', 'ticker':context['ticker'], 'session':context['session'],
            'price_residuals':differences, 'volume_residual':context['volume'] - number(reference['volume']),
            'turnover_residual':context['turnover'] - number(reference['turnover']),
            'reference_sha256':reference['source_sha256'], 'qualification_changed':False,
            'provider_equivalence':'NOT_ESTABLISHED_BY_ONE_SAMPLE'}


def flow_context(capture, ticker, session):
    values = records(capture)
    require(len(values) == 1, 'ONE_FLOW_SESSION_REQUIRED')
    row=values[0]['data']
    require(row.get('code') == ticker[:6] and row.get('market') == ('1' if ticker.endswith('.SH') else '0')
            and day(row.get('trade_date')) == session, 'FLOW_IDENTITY_OR_SESSION')
    return {**_base('MARKET_FLOW_CONTEXT',capture), 'ticker':ticker, 'session':str(session),
            'method':'EASTMONEY_CLASSIFIED_ORDER_FLOW_NOT_ISSUER_CASHFLOW', 'unit':'CNY',
            'main':number(row.get('main_net')), 'source_record':values[0],
            'cross_provider_flow_equivalence':'NOT_ESTABLISHED'}


def membership_context(capture, code, session, *, concept=False):
    values=records(capture); members=[]; grouped={}
    if concept:
        require(len(capture['metadata']) == 1 and capture['metadata'][0].get('board_code') == code,
                'BOARD_IDENTITY')
    for item in values:
        row=item['data']; symbol=row.get('stock_code' if concept else 'stockCode')
        require(isinstance(symbol,str) and re.fullmatch(r'[0-9]{6}',symbol), 'MEMBER_IDENTITY')
        if not concept:
            require(code in {row.get('swLevel1Code'),row.get('swLevel2Code'),row.get('swLevel3Code')}, 'SW_IDENTITY')
            entry=day(row['inDate']); exit_=day(row['outDate']) if row.get('outDate') else None
            require(exit_ is None or exit_ >= entry, 'MEMBERSHIP_INTERVAL_INVALID')
            if entry > session or exit_ is not None and exit_ <= session:
                continue
        if symbol in grouped:
            previous=grouped[symbol]['source_records'][0]['data']
            require(not concept and all(previous.get(k)==row.get(k) for k in ('inDate','outDate','stockName'))
                    and all(previous.get(k)==row.get(k) for k in ('swLevel1Code','swLevel2Code')
                            if previous.get(k)==code or row.get(k)==code), 'MEMBERSHIP_CONFLICT')
            grouped[symbol]['source_records'].append(item)
        else:
            entry={'security_code':symbol,'source_records':[item]}
            grouped[symbol]=entry;members.append(entry)
    return {**_base('CONSTITUENT_CONTEXT',capture), 'provider_code':code,
            'identity_namespace':'EASTMONEY_BK' if concept else 'SHENWAN_SI', 'members':members,
            'effective_scope':'CURRENT_AT_RETRIEVAL_NOT_HISTORICAL' if concept else 'PROVIDER_RECONSTRUCTED_INTERVAL',
            'as_of':str(session) if not concept else None, 'stock_price_gate_changed':False}


def sector_context(capture, code, name, session, *, concept=False):
    values=records(capture); points=[]
    require(len(values) == 1, 'ONE_SECTOR_SESSION_REQUIRED')
    for item in values:
        row=item['data']
        require(row.get('board_code' if concept else 'industryCode') == code and
                day(row.get('date' if concept else 'tradeDate')) == session, 'SECTOR_IDENTITY_OR_SESSION')
        if concept:
            points.append(SectorPricePoint(session,number(row['close'],positive=True),number(row['turnover'])))
    series = SectorPriceSeries(code,name,tuple(points)) if points else None
    if series:
        _validate_series(series)  # Original sector market-input validator, no renamed TI identity.
    return {**_base('SECTOR_MARKET_INPUT_CONTEXT',capture), 'provider_code':code,
            'typed_price_series':asdict(series) if series else None, 'records':values,
            'ranking_qualification':'NOT_ESTABLISHED_WITHOUT_REQUIRED_HISTORY_AND_CROSS_SECTION',
            'missing_price':'SW_METRICS_MAY_NOT_CONTAIN_PRICE' if not points else None}


def industry_context(variety, contract, session, captures):
    base=records(captures[variety+'_base']); prices=records(captures[variety+'_prices'])
    warehouse=records(captures[variety+'_warehouse']); exchange='GFEX' if variety=='LC' else 'SHFE'
    require(len(base)==1, 'CONTRACT_BASE_REQUIRED')
    identity=base[0]['data']
    require(identity.get('symbol')==contract and identity.get('product')==variety
            and identity.get('exchange')==exchange and day(identity.get('trade_date'))==session,
            'CONTRACT_IDENTITY')
    require(identity.get('put_price')=='人民币元/吨' and identity.get('trade_unit')=='吨', 'CONTRACT_UNITS_UNKNOWN')
    dates=[]; invalid_ohlc=[]
    for item in prices:
        row=item['data']; point=day(row.get('trade_date')); dates.append(point)
        require(row.get('symbol') in {contract,contract.split('.')[0].lower()} and session-timedelta(days=30) <= point <= session,
                'CONTRACT_PRICE_IDENTITY')
        require(row.get('dominant_contract') is None and row.get('forward_factor') is None
                and row.get('backward_factor') is None, 'CONTRACT_NOT_CONTINUOUS')
        for field in ('open','high','low','close'):
            number(row.get(field),positive=True)
        if not number(row['low']) <= min(number(row['open']),number(row['close'])) <= max(number(row['open']),number(row['close'])) <= number(row['high']):
            invalid_ohlc.append(str(point))
    require(dates and dates==sorted(set(dates)) and dates[-1]==session, 'PRICE_SESSION_COVERAGE')
    require(warehouse, 'WAREHOUSE_NOT_RETURNED')
    for item in warehouse:
        row=item['data']
        require(row.get('symbol')==variety and row.get('exchange')==exchange
                and day(row.get('trade_date'))==session, 'WAREHOUSE_IDENTITY_OR_SESSION')
        require(row.get('unit') in {'手','吨'}, 'WAREHOUSE_UNIT_UNKNOWN')
        require(number(row.get('vol'))>=0, 'WAREHOUSE_VOLUME_INVALID')
    payload={'kind':INDUSTRY_KIND, 'adapter_version':VERSION, 'provider':'FTSHARE',
             'variety':variety, 'contract':contract, 'contract_mode':'FIXED_CONTRACT_NOT_MAIN_CONTINUOUS',
             'session':str(session), 'price_unit':'CNY_PER_TONNE', 'contract_multiplier':number(identity['multiplier'],positive=True),
             'base':base, 'prices':prices, 'warehouses':warehouse, 'warehouse_aggregation':'NONE_UNITS_AND_SUBTOTALS_PRESERVED',
             'price_validation':'INVALID_OHLC' if invalid_ohlc else 'VALIDATED_SOURCE_FIELDS',
             'invalid_ohlc_dates':invalid_ohlc, 'prices_usable':not invalid_ohlc,
             'basis':'NOT_ACQUIRED', 'roll_semantics':'NO_ROLL_SINGLE_CONTRACT',
             'historical_availability':'NOT_ESTABLISHED', 'beneficiary_inference':False,
             'industry_inflection':'NOT_ESTABLISHED', **AUTHORITY}
    return {'kind':INDUSTRY_KIND,'status':'PARTIAL_INDUSTRY_CONTEXT' if invalid_ohlc else 'CONTEXT_READY',
            'observation':_seal(payload)}


def project(config, captures, *, reference=None):
    plan(config); session=day(config['session']); ticker=config['ticker']
    result={'kind':'CONSOLIDATED_PROVIDER_CONTEXT','version':VERSION,'config':config,'families':{},
            'model_calls':0,'investment_authority':'NONE','default_provider_changed':False,
            'research_admission':'NOT_GRANTED','automatic_daily_research':'NOT_ENABLED'}
    jobs=[('market',lambda:stock_context(captures['stock'],ticker,session)),
          ('flow',lambda:flow_context(captures['flow'],ticker,session)),
          ('sector_members',lambda:membership_context(captures['sw_members'],config['sw_code'],session)),
          ('sector_metrics',lambda:sector_context(captures['sw_metrics'],config['sw_code'],config['sw_name'],session)),
          ('concept_members',lambda:membership_context(captures['concept_members'],config['concept_code'],session,concept=True)),
          ('concept_market',lambda:sector_context(captures['concept_prices'],config['concept_code'],config['concept_name'],session,concept=True))]
    jobs += [(v,lambda v=v:industry_context(v,config['contracts'][v],session,captures)) for v in ('LC','CU','RB')]
    for label, operation in jobs:
        try:result['families'][label]=operation()
        except (ValueError,TypeError,KeyError,ArithmeticError) as exc:
            result['families'][label]={'status':'SOURCE_UNAVAILABLE','error_type':type(exc).__name__,
                'reason':str(exc) if re.fullmatch(r'[A-Z_]{1,96}',str(exc)) else 'VALIDATION_FAILED'}
    result['capture_statuses']={key:value['status'] for key,value in captures.items()}
    if reference is not None and result['families']['market']['status']=='CONTEXT_READY':
        result['market_comparison']=compare_stock(result['families']['market'],reference)
    result['status']='BATCH_CONTEXT_READY' if all(v['status']=='CONTEXT_READY' for v in result['families'].values()) else 'PARTIAL_BATCH_CONTEXT'
    return result


def save(result, output):
    raw=raw_json(result); require(len(raw)<=448*1024,'BATCH_CONTEXT_TOO_LARGE')
    (output/'provider-batch.json').write_bytes(raw)
    lines=['# 统一数据输入','', '资料与核对结果，不是投资信号、已完成研究或全市场覆盖。','',
           '| 范围 | 状态 |','|---|---|']
    lines += [f'| {md(k)} | {md(v["status"])} |' for k,v in result['families'].items()]
    lines += ['', 'FTShare 行情未替换既有来源；概念成分是取得时快照；申万成分保留区间。',
              'LC/CU/RB 使用明确单合约，仓单保留原单位；未计算基差、主连续换月或行业拐点。',
              'CNEquity 复用原生本地读取，原始供应商身份不变；未获得的历史时点或复权依据不补造。','']
    (output/'provider-batch.md').write_text('\n'.join(lines),encoding='utf-8')


def prepare(config, output, *, fetch=market.request, clock=now, company=None, reference=None, lake=None):
    queries=plan(config); output=Path(output)
    if company is not None:
        require(isinstance(company,dict) and set(company)=={'year','report_type','start_date','end_date'}
                and type(company['year']) is int and 1990 <= company['year'] <= day(config['session']).year
                and company['report_type'] in {'q1','q2','q3','annual'}
                and 0 <= (day(company['end_date'])-day(company['start_date'])).days <= 366
                and day(company['end_date']) <= day(config['session']), 'COMPANY_SCOPE_INVALID')
    require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents),'UNSAFE_OUTPUT')
    require(day(config['session']) < _clock(clock()).astimezone(TZ).date(), 'COMPLETED_SESSION_REQUIRED')
    output.mkdir(parents=True,exist_ok=False); captured={}; stopped=None
    for label,route,params in queries:
        if stopped:
            captured[label]={'status':'NOT_ATTEMPTED_AFTER_'+stopped,'rows':[]}; continue
        captured[label]=market.capture(route,params,output/'raw'/label,fetch=fetch,clock=clock)
        if captured[label]['status'] in STOPS:stopped=captured[label]['status']
    result=project(config,captured,reference=reference)
    if company:
        from . import stock_research_sources as original
        require(isinstance(company,dict) and set(company)=={'year','report_type','start_date','end_date'},'COMPANY_SCOPE_INVALID')
        for name, function, kwargs in [
            ('financial',original.prepare_financial_context,{'year':company['year'],'report_type':company['report_type']}),
            ('company_events',original.prepare_company_event_context,{'start_date':day(company['start_date']),'end_date':day(company['end_date'])})]:
            if stopped:
                result['families'][name]={'status':'NOT_ATTEMPTED_AFTER_'+stopped}; continue
            try:
                item=function(ticker=config['ticker'],output=output/name,clock=clock,**kwargs)
                result['families'][name]={'status':item['status'],'file':str(Path(name)/('financial-context.json' if name=='financial' else 'company-event-context.json'))}
                for child in (output/name).rglob('capture.json'):
                    state=decode(child.read_bytes()).get('status')
                    if state in STOPS:stopped=state
            except (ValueError,TypeError,OSError) as exc:
                result['families'][name]={'status':'SOURCE_UNAVAILABLE','error_type':type(exc).__name__,
                'reason':str(exc) if re.fullmatch(r'[A-Z_]{1,96}',str(exc)) else 'VALIDATION_FAILED'}
    if lake:
        from .cnequity_bridge import read_lake
        try:
            item=read_lake(output=output/'cnequity',**lake)
            result['families']['cnequity']={'status':item['status'],'file':'cnequity/cnequity-context.json'}
        except (ValueError,TypeError,OSError,ImportError) as exc:
            result['families']['cnequity']={'status':'SOURCE_UNAVAILABLE','error_type':type(exc).__name__,
                'reason':str(exc) if re.fullmatch(r'[A-Z_]{1,96}',str(exc)) else 'VALIDATION_FAILED'}
    ready={'CONTEXT_READY','FINANCIAL_CONTEXT_PREPARED_NOT_ADMITTED','COMPANY_CONTEXT_PREPARED_NOT_ADMITTED'}
    result['status']='BATCH_CONTEXT_READY' if all(v['status'] in ready for v in result['families'].values()) else 'PARTIAL_BATCH_CONTEXT'
    result['finished_at']=clock()
    save(result,output)
    return result


def main(argv=None):
    """Called by the original stock_research_sources --mode batch entry."""
    import argparse
    parser=argparse.ArgumentParser(description='One bounded provider-input batch; no model execution')
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    require(args.config.is_file() and not args.config.is_symlink() and args.config.stat().st_size<=8192,
            'BATCH_CONFIG_INVALID')
    config=decode(args.config.read_bytes())
    require(isinstance(config,dict) and set(config)<={'market','company','reference','lake'}
            and 'market' in config, 'BATCH_CONFIG_FIELDS_INVALID')
    lake=config.get('lake')
    if lake:
        require(isinstance(lake,dict) and set(lake)<={'data_root','dataset','start','end','symbols','as_of','adjust','revision_map'}
                and {'data_root','dataset','start','end','symbols'}<=set(lake),'LAKE_SCOPE_INVALID')
        lake=dict(lake)
        for name in ('start','end','as_of'):
            if lake.get(name) is not None:lake[name]=day(lake[name])
    result=prepare(config['market'],args.output,company=config.get('company'),reference=config.get('reference'),lake=lake)
    print(result['status'])
    return 0 if result['status']=='BATCH_CONTEXT_READY' else 1


if __name__=='__main__':
    raise SystemExit(main())
