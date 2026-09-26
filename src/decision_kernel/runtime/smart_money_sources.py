"""Reviewed public-capital source contracts; no actor skill or investment inference.

Protocols: existing HiThink/FTShare plus AKShare's Eastmoney contracts. The
specific endpoints, units and caveats are documented in smart-money-radar.md.
This is a finite reader, not a configurable provider/agent framework.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from zoneinfo import ZoneInfo

from ..identity import canonical_hash, canonical_json

VERSION = 'smart-money-observation-v1'
PROJECTION_REVISION = 'smart-money-projection-3'
REQUEST_REVISION = 2
WORKFLOW = '.github/workflows/radar-smart-money.yml'
ZONE = ZoneInfo('Asia/Shanghai')
HT = 'https://fuyao.aicubes.cn/api/a-share/'
FT = 'https://market.ft.tech/gateway/api/v1/market/data/'
EM = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
REPORTS = 'https://reportapi.eastmoney.com/report/list'
FAMILIES = ('hot_money', 'institutional', 'seats', 'northbound', 'holdings',
            'north_holdings', 'activity', 'forecasts', 'executives', 'holder_changes', 'repurchases', 'placements')
PAGE_SIZE = 1000
MAX_PAGES = 128
MAX_REQUESTS = 300
MAX_BODY = 4 * 1024 * 1024
MAX_TOTAL_RAW = 80 * 1024 * 1024
AUTHORITY = {'investment_authority': 'NONE', 'automatic_full': False,
             'odds_recomputed': False, 'stock_price_gate_required': False}
HOLDER_COLUMNS = ('SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,END_DATE,HOLDER_NAME,HOLDER_CODE,'
    'HOLDER_NEW,HOLDER_TYPE,HOLDER_RANK,SHARES_TYPE,HOLD_NUM,FREE_HOLDNUM_RATIO,HOLD_RATIO,'
    'HOLD_NUM_CHANGE,XZCHANGE,NOTICE_DATE,UPDATE_DATE')
ACTIVITY_COLUMNS = ('SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,NOTICE_DATE,RECEIVE_START_DATE,'
    'RECEIVE_END_DATE,RECEIVE_OBJECT,OBJECT_CODE,RECEIVE_WAY_EXPLAIN,INVESTIGATORS,'
    'ORG_TYPE,ORG_TYPE_CODE,URL,NUMBERNEW')


class SourceError(ValueError):
    """Only fixed safe codes, never raw response/credential text."""


def require(ok, code):
    if not ok:
        raise SourceError(code)


def day(value):
    require(isinstance(value, str), 'DATE_TYPE')
    value = value[:10]
    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None, 'DATE_FORMAT')
    return date.fromisoformat(value)


def clock(value):
    require(isinstance(value, str), 'CLOCK_TYPE')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'CLOCK_ZONE')
    return result.astimezone(timezone.utc)


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return (canonical_json(value) + '\n').encode()


def decode(raw):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, 'DUPLICATE_JSON_KEY')
            result[k] = v
        return result
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BODY, 'BODY_SIZE')
    return json.loads(raw.decode('utf-8-sig'), parse_float=Decimal,
                      parse_constant=lambda _: (_ for _ in ()).throw(SourceError('NONFINITE_JSON')),
                      object_pairs_hook=unique)


def text(value, *, required=False):
    if value is None or value == '':
        require(not required, 'TEXT_MISSING')
        return None
    require(isinstance(value, (str, int)) and not isinstance(value, bool), 'TEXT_TYPE')
    out = str(value).strip()
    require(0 < len(out) <= 16000 and '\x00' not in out, 'TEXT_SIZE')
    return out


def number(value):
    if value is None or value in ('', '--', '-', '不变', '新进'):
        return None
    require(not isinstance(value, (bool, float)), 'NUMBER_REPRESENTATION')
    try:
        x = Decimal(str(value).replace(',', ''))
    except InvalidOperation:
        raise SourceError('NUMBER_FORMAT') from None
    require(x.is_finite(), 'NUMBER_FINITE')
    return str(x.normalize()) if x else '0'


def ticker(value, market=None):
    value = text(value, required=True)
    if re.fullmatch(r'\d{6}\.(SH|SZ|BJ)', value):
        code,suffix=value.split('.')
        allowed={'SH':code[0] in '56' or code.startswith('900'),'SZ':code[0] in '0123','BJ':code[0] in '48' or code.startswith('92')}
        require(allowed[suffix],'SECURITY_EXCHANGE_CONFLICT')
        if market is not None:require({'SHANGHAI':'SH','SHENZHEN':'SZ','BEIJING':'BJ'}.get(market)==suffix,'SECURITY_MARKET_CONFLICT')
        return value
    require(re.fullmatch(r'\d{6}', value) is not None, 'SECURITY_CODE')
    require(market is None or market in {'SHANGHAI','SHENZHEN','BEIJING'}, 'SECURITY_MARKET_UNRESOLVED')
    suffix = {'SHANGHAI':'SH', 'SHENZHEN':'SZ', 'BEIJING':'BJ'}.get(market)
    if suffix is None:
        if value[0] == '6': suffix = 'SH'
        elif value[0] in '03': suffix = 'SZ'
        elif value[0] in '48' or value.startswith('92'): suffix = 'BJ'
    require(suffix is not None, 'SECURITY_EXCHANGE_UNRESOLVED')
    return ticker(value + '.' + suffix, market)


def periods(asof):
    """Latest two ENDED calendar quarters, not asserted publication deadlines."""
    end = date(asof.year, 3 * ((asof.month - 1) // 3) + 1, 1) - timedelta(days=1)
    prior = date(end.year, 3 * ((end.month - 1) // 3) + 1, 1) - timedelta(days=1)
    return (prior.isoformat(), end.isoformat())


def spec(family, partition, begin, end, page=1, *, revision=REQUEST_REVISION):
    require(family in FAMILIES and type(page) is int and 1 <= page <= MAX_PAGES, 'SOURCE_SCOPE')
    first, last = day(begin), day(end)
    require(first <= last and (last-first).days <= 366, 'SOURCE_WINDOW')
    require(type(revision) is int and revision in (1,2), 'REQUEST_REVISION')
    base = {'family': family, 'partition': partition, 'begin': begin, 'end': end, 'page': page}
    if revision==2:base['contract_revision']=2
    if family in {'hot_money','institutional'}:
        require(page == 1 and first <= day(partition) <= last, 'BOARD_SCOPE')
        return {**base, 'provider':'HT', 'url': HT+'special-data/dragon-tiger-list',
                'params':{'board_type':'hot_money' if family=='hot_money' else 'org', 'date':partition}}
    if family in {'seats','northbound'}:
        require(first <= day(partition) <= last, 'DAILY_SCOPE')
        params = {'date':day(partition).strftime('%Y%m%d')}
        if family=='seats': params.update(page=str(page), page_size='200')
        else: require(page==1, 'NORTHBOUND_PAGE')
        return {**base, 'provider':'FT', 'url':FT+('abnormal-trading-details' if family=='seats' else 'northbound'), 'params':params}
    if family == 'north_holdings':
        parts=partition.split('@');require(parts[0] in {'SH','SZ'} and len(parts)<=2 and page==1,'HKEX_SCOPE')
        if len(parts)==2:require(parts[1] in periods(last),'HKEX_HISTORICAL_PERIOD')
        from .smart_money_documents import HKEX
        query = ({'query_asof':min(last,day(parts[1])+timedelta(days=30)).isoformat()}
                 if revision>=2 and len(parts)==2 else {})
        return {**base,**query,'provider':'HKEX','url':HKEX,'params':{'t':parts[0].lower()},
                'method':'POST' if len(parts)==2 else 'GET'}
    if family == 'executives':
        return {**base, 'provider':'FT', 'url':FT+'holder/stock-ggmx',
                'params':{'start_date':first.strftime('%Y%m%d'), 'end_date':last.strftime('%Y%m%d'),
                          'page':str(page), 'page_size':'200'}}
    if family == 'forecasts':
        return {**base, 'provider':'EM', 'url':REPORTS, 'params':{'industryCode':'*', 'pageSize':'100',
            'industry':'*','rating':'*','ratingChange':'*','beginTime':begin,'endTime':end,
            'pageNo':str(page),'fields':'','qType':'0','orgCode':'','code':'','rcode':'','p':'1',
            'pageNum':str(page),'pageNumber':str(page)}}
    configs = {
        'holdings': ('RPT_F10_EH_FREEHOLDERS',HOLDER_COLUMNS,'SECURITY_CODE,HOLDER_RANK,HOLDER_CODE','1,1,1',
                     f"(END_DATE='{partition}')"),
        'activity': ('RPT_ORG_SURVEY',ACTIVITY_COLUMNS,'NOTICE_DATE,RECEIVE_START_DATE,SECURITY_CODE,NUMBERNEW','-1,-1,1,-1',
                     f"(IS_SOURCE=\"1\")(NOTICE_DATE>='{begin}')(NOTICE_DATE<='{end}')"),
        'holder_changes': ('RPT_SHARE_HOLDER_INCREASE','ALL','END_DATE,SECURITY_CODE,EITIME','-1,-1,-1',
                           f"(END_DATE>='{begin}')(END_DATE<='{end}')"),
        'repurchases': ('RPTA_WEB_GETHGLIST_NEW','ALL','UPD,DIM_DATE,DIM_SCODE','-1,-1,-1',
                        f"(UPD>='{begin}')(UPD<='{end} 23:59:59')"),
        'placements': ('RPT_SEO_DETAIL','ALL','ISSUE_DATE,SECURITY_CODE','-1,1',
                       f"(ISSUE_DATE>='{begin}')(ISSUE_DATE<='{end}')(SEO_TYPE=\"1\")"),
    }
    if family=='holdings': require(day(partition) <= last and partition in periods(last), 'HOLDER_PERIOD')
    report, columns, sort, order, where = configs[family]
    if family=='activity' and revision>=2:
        # Existing AKShare event-summary protocol avoids scanning each
        # participant as a separate event. Roster breadth remains explicit.
        report,columns='RPT_ORG_SURVEYNEW','ALL'
        sort,order='NOTICE_DATE,SUM,RECEIVE_START_DATE,SECURITY_CODE','-1,-1,-1,1'
        where='(NUMBERNEW="1")'+where
    size=500 if revision==2 and family in {'activity','holder_changes','repurchases'} else PAGE_SIZE
    return {**base, 'provider':'EM', 'url':EM, 'params':{'reportName':report, 'columns':columns,
        'sortColumns':sort,'sortTypes':order,'pageSize':str(size),'pageNumber':str(page),
        'source':'WEB','client':'WEB','filter':where}}


def calendar_spec():
    return {'family':'calendar','partition':'calendar','provider':'HT',
            'url':HT+'calendar/trading-days','params':{},'page':1}


def page_data(value, request):
    """Returned counters are validated; a green HTTP status is not data success."""
    require(isinstance(value, dict), 'ENVELOPE')
    f, p = request['family'], request['provider']
    if f=='north_holdings':
        return value['rows'], value['count'], 1
    if f=='forecasts':
        rows, count, pages = value.get('data'), value.get('hits'), value.get('TotalPage')
        require(value.get('pageNo') == request['page'], 'RETURNED_PAGE')
    elif p=='EM':
        require(value.get('success') is True and type(value.get('code')) is int and value.get('code') == 0 and isinstance(value.get('result'),dict), 'PROVIDER_DATA_UNAVAILABLE')
        data=value['result'];rows,count,pages=data.get('data'),data.get('count'),data.get('pages')
    elif p=='FT' and f in {'seats','executives'}:
        require(type(value.get('code')) is int and value.get('code') in (0,200) and isinstance(value.get('data'),dict), 'PROVIDER_DATA_UNAVAILABLE')
        data=value['data'];rows,count,pages=data.get('records'),data.get('total'),data.get('pages')
        require(data.get('pageNum')==request['page'] and data.get('pageSize')==200, 'RETURNED_PAGE')
    elif p=='HT':
        require(type(value.get('code')) is int and value['code']==0 and isinstance(value.get('data'),dict), 'PROVIDER_DATA_UNAVAILABLE')
        data=value['data'];kind='hot_money' if f=='hot_money' else 'org'
        require(data.get('trade_date')==request['partition'] and data.get('board_type')==kind, 'BOARD_DATE_OR_TYPE')
        require(data.get('timestamp') == int(datetime.combine(day(request['partition']),datetime.min.time(),ZONE).timestamp())*1000,
                'BOARD_DATE_KEY')
        rows = data.get('hot_money_items' if f=='hot_money' else 'stock_items')
        require(isinstance(rows,list) and len(rows)<=4096, 'BOARD_ROWS')
        return rows, len(rows), 1
    else:
        require(f=='northbound' and type(value.get('code')) is int and value.get('code') in (0,200), 'PROVIDER_DATA_UNAVAILABLE')
        data=value.get('data'); require(isinstance(data,dict), 'NORTHBOUND_DATA')
        require(data.get('date')==day(request['partition']).strftime('%Y%m%d') and data.get('currency')=='CNY', 'NORTHBOUND_DATE_CURRENCY')
        return [data],1,1
    size=int(request['params'].get('pageSize',request['params'].get('page_size','100')))
    require(type(count) is int and count>=0 and type(pages) is int and pages>=0, 'PAGE_COUNTERS')
    require(pages == (count+size-1)//size or count==0 and pages in (0,1), 'PAGE_COUNTERS')
    expected=min(size,max(0,count-(request['page']-1)*size))
    require(isinstance(rows,list) and len(rows)==expected, 'PAGE_ROW_COUNT')
    return rows,count,pages


def _date_field(row, key, end, *, required=False):
    v=row.get(key)
    if not v:
        require(not required, 'DISCLOSURE_DATE_MISSING')
        return None
    d=day(v);require(d<=day(end), 'FUTURE_SOURCE_DATE')
    return d.isoformat()


def _entry(f, key, code, name, actor, actor_name, when, published, values, ref):
    key=[f,*key]
    item={'id':canonical_hash(key), 'ticker':code, 'company':name, 'actor_id':actor,
          'actor_name':actor_name, 'date':when, 'disclosed':published, 'values':values, 'source_rows':[ref]}
    item['version']=canonical_hash({k:v for k,v in item.items() if k not in {'source_rows','version'}})
    return item


def normalize(rawrow, request, index, request_index, envelope=None):
    """Normalize only fields whose meaning was inspected; originals stay separate."""
    require(isinstance(rawrow,dict), 'ROW_TYPE')
    r=rawrow;f=request['family'];end=request['end'];part=request['partition'];ref=[request_index,index]
    out=[]
    if f=='hot_money':
        actor_name=text(r.get('name'),required=True);actor='HT:LABEL:'+actor_name
        require(isinstance(r.get('rows'),list), 'HOT_LABEL_ROWS')
        for n,x in enumerate(r['rows']):
            code=ticker(x.get('thscode'));window=x.get('range_days');require(type(window)is int and window in (1,3),'WINDOW')
            values={'net_cny':number(x.get('hot_money_item_net_value')), 'window_days':window,
                'identity':'VENDOR_LABEL_NOT_VERIFIED_PERSON', 'seat_mapping':'NOT_SUPPLIED_BY_THIS_SOURCE',
                'holding':'NOT_INFERRED', 'source_reason':text(x.get('limit_reason'))}
            out.append(_entry(f,[actor,code,part,window],code,text(x.get('name')),actor,actor_name,part,None,values,[request_index,index,n]))
        return out
    if f=='institutional':
        code=ticker(r.get('thscode'));window=r.get('range_days');require(type(window)is int and window in (1,3),'WINDOW')
        vals={'net_cny':number(r.get('org_net_value')), 'buyers':number(r.get('org_buy_num')),
              'sellers':number(r.get('org_sell_num')), 'window_days':window,
              'identity':'INSTITUTIONAL_SEATS_NOT_IDENTIFIABLE_FUND', 'holding':'NOT_INFERRED'}
        return [_entry(f,[code,part,window],code,text(r.get('name')),'HT:ORG:UNSPECIFIED','机构席位',part,None,vals,ref)]
    if f=='seats':
        code=ticker(r.get('symbol')); group=canonical_hash(sorted(
            {str(x.get('name')) for side in ('top_buyers','top_sellers') for x in r.get(side,[])}))
        unique={}
        for side in ('top_buyers','top_sellers'):
            require(isinstance(r.get(side),list) and len(r[side])<=10,'SEAT_ROWS')
            for n,x in enumerate(r[side]):
                seat=text(x.get('name'),required=True);values={k+'_cny':number(x.get(k)) for k in ('buy','sell','net')}
                if all(values[k] is not None for k in ('buy_cny','sell_cny','net_cny')):
                    require(abs(Decimal(values['buy_cny'])-Decimal(values['sell_cny'])-Decimal(values['net_cny']))<=Decimal('0.02'),'SEAT_ARITHMETIC')
                anonymous=seat in {'机构专用','深股通专用','沪股通专用'}
                identity=canonical_hash([seat,side,n] if anonymous else [seat,values])
                if identity in unique:
                    unique[identity]['values']['shown_on'].append(side)
                    unique[identity]['source_rows'].append([request_index,index,side,n])
                    continue
                values.update(window_days=None, window_status='SOURCE_DID_NOT_RETURN_WINDOW', shown_on=[side],
                              identity='BROKERAGE_SEAT_NOT_BENEFICIAL_OWNER', holding='NOT_INFERRED')
                if anonymous:
                    values.update(identity='ANONYMOUS_DISCLOSED_SEAT_ROW',anonymous_row=True,
                                  independent_actor_count=None,additive_across_sides=False)
                item=_entry(f,[code,part,group,seat,*([side,n] if anonymous else [])],code,None,
                            'SEAT_LABEL:'+seat if anonymous else 'SEAT:'+seat,seat,part,None,values,[request_index,index,side,n])
                unique[identity]=item
        for item in unique.values():
            item['version']=canonical_hash({k:v for k,v in item.items() if k not in {'source_rows','version'}})
        return list(unique.values())
    if f=='northbound':
        require(set(r.get('channels',{}))=={'SH','SZ'}, 'CONNECT_CHANNELS')
        total=number(r.get('total_amount'));parts=[number(r['channels'][k].get('amount')) for k in ('SH','SZ')]
        require(total is not None and all(x is not None for x in parts) and Decimal(total)==sum(Decimal(x) for x in parts),'CONNECT_TOTAL')
        vals={'turnover_cny':total,'sh_turnover_cny':parts[0],'sz_turnover_cny':parts[1],
              'sh_trades':r['channels']['SH'].get('trade_count'),'sz_trades':r['channels']['SZ'].get('trade_count'),
              'net_buy_cny':None,'meaning':'TURNOVER_NOT_NET_FLOW', 'individual_daily_holdings':'NOT_PUBLIC_CURRENT_FIELD'}
        return [_entry(f,[part],None,None,'CONNECT:NORTHBOUND','北向互联互通',part,None,vals,ref)]
    if f=='north_holdings':
        code=ticker(r['code']);period=r['period']
        vals={'shares':r['shares'],'percentage':r['percent'],'connect_code':r['connect_code'],
              'identity':'AGGREGATE_CCASS_NOT_ONE_INVESTOR','frequency':'QUARTERLY',
              'denominator':'LISTED_TRADED_SECURITIES_REFERENCE_ONLY_NOT_TOTAL_ISSUED_SHARES',
              'security_type':'FUND_OR_ETF_NAME' if 'ETF' in r['name'].upper() else 'SOURCE_LISTED_SECURITY',
              'net_buy_cny':None,'current_holdings':'NOT_ESTABLISHED'}
        return [_entry(f,[code,period],code,r['name'],'CONNECT:NORTHBOUND','北向CCASS合计',period,None,vals,ref)]
    if f=='holdings':
        code=ticker(r.get('SECUCODE'));require(code[:6]==r.get('SECURITY_CODE'),'SECURITY_IDENTITY')
        report=_date_field(r,'END_DATE',end,required=True);require(report==part,'REPORT_PERIOD')
        published=_date_field(r,'NOTICE_DATE',end,required=True);require(report<=published,'DISCLOSURE_BEFORE_PERIOD')
        hid=text(r.get('HOLDER_CODE'));name=text(r.get('HOLDER_NAME'),required=True)
        actor='EM:HOLDER:'+hid if hid else 'EM:ISSUER_NAME:'+code+':'+name
        holder_key=hid or 'ISSUER_NAME:'+name
        vals={'shares':number(r.get('HOLD_NUM')),'float_pct':number(r.get('FREE_HOLDNUM_RATIO')),
              'total_pct':number(r.get('HOLD_RATIO')),'rank':r.get('HOLDER_RANK'),
              'holder_type':text(r.get('HOLDER_TYPE')),'share_class':text(r.get('SHARES_TYPE')),
              'reported_change':text(r.get('HOLD_NUM_CHANGE')),'reported_change_shares':number(r.get('XZCHANGE')),
              'identity':'PROVIDER_HOLDER_CODE_NOT_CERTIFIED_PERSON' if hid else 'ISSUER_SCOPED_NAME_NOT_CERTIFIED_PERSON',
              'name_match_group':canonical_hash(name),'current_holding':'NOT_ESTABLISHED',
              'nominee':text(r.get('HOLDER_NAME'))=='香港中央结算有限公司'}
        require(vals['shares'] is not None and Decimal(vals['shares'])>=0,'HOLDING_AMOUNT')
        # A provider ID can represent multiple named accounts; a missing ID
        # cannot turn two equal names/ranks into one actual natural person.
        account=[name,vals['share_class']] if hid else [name,vals['share_class'],vals['rank']]
        vals['account_identity']='SOURCE_NAMED_ACCOUNT' if hid else 'UNRESOLVED_PERSON_RANKED_ROW'
        return [_entry(f,[code,holder_key,report,*account],code,text(r.get('SECURITY_NAME_ABBR')),actor,name,report,published,vals,ref)]
    if f=='activity':
        code=ticker(r.get('SECUCODE'));require(code[:6]==r.get('SECURITY_CODE'),'SECURITY_IDENTITY')
        published=_date_field(r,'NOTICE_DATE',end,required=True);when=_date_field(r,'RECEIVE_START_DATE',end,required=True)
        require(day(request['begin'])<=day(published) and when<=published,'ACTIVITY_WINDOW')
        doc=text(r.get('URL'));obj=text(r.get('OBJECT_CODE'));name=text(r.get('RECEIVE_OBJECT'))
        summary=request['params'].get('reportName')=='RPT_ORG_SURVEYNEW'
        event=canonical_hash([code,doc,when,r.get('RECEIVE_END_DATE')]) if doc else (
            canonical_hash([code,when,r.get('RECEIVE_END_DATE'),r.get('RECEIVE_TIME_EXPLAIN'),
                            r.get('RECEIVE_WAY_EXPLAIN'),r.get('RECEIVE_PLACE')]) if summary else None)
        actor='EM:ORG:'+obj if obj else 'UNRESOLVED:'+canonical_hash([code,event,name])
        vals={'event_id':event,'event_identity':('DISCLOSURE_AND_DATE_GROUP' if doc else
              'PROVIDER_REPORTED_ACTIVITY_GROUP' if summary else 'NOT_ESTABLISHED'),
              'roster_scope':'SUMMARY_REPRESENTATIVE_NOT_COMPLETE_ROSTER' if summary else 'PARTICIPANT_DETAIL',
              'provider_reported_institution_entries':number(r.get('SUM')) if summary else None,
              'disclosure_id':doc,'institution_code':obj,'institution_type':text(r.get('ORG_TYPE')),
              'form':text(r.get('RECEIVE_WAY_EXPLAIN')),'participants':text(r.get('INVESTIGATORS')),
              'institution_identity':'PROVIDER_CODE' if obj else 'UNRESOLVED_GENERIC_OR_TEXT',
              'identity':'NOT_CAPITAL_INVESTMENT'}
        return [_entry(f,[code,event,obj,name,r.get('INVESTIGATORS')],code,text(r.get('SECURITY_NAME_ABBR')),actor,name,when,published,vals,ref)]
    if f=='forecasts':
        code=ticker(r.get('stockCode'),r.get('market'));org=text(r.get('orgCode'),required=True)
        published=_date_field(r,'publishDate',end,required=True);require(day(request['begin'])<=day(published),'REPORT_WINDOW')
        rid=text(r.get('infoCode'),required=True);require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}',rid) is not None,'REPORT_ID')
        vals={'report_id':rid,'title':text(r.get('title')),'rating':text(r.get('orgRating')),
            'eps_slots':[number(r.get(k)) for k in ('predictThisYearEps','predictNextYearEps','predictNextTwoYearEps')],
            'provider_current_year':(envelope or {}).get('currentYear'),'target_period':'NOT_REPORT_VERIFIED',
            'currency':None,'share_basis':None,'revision_qualification':'UNRESOLVED_PERIOD_CURRENCY_SHARE_BASIS',
            'first_coverage':('REPORT_TITLE_CLAIMS_INITIAL_COVERAGE' if '首次覆盖' in str(r.get('title','')) else 'FIRST_SEEN_IS_NOT_FIRST_COVERAGE')}
        return [_entry(f,[rid],code,text(r.get('stockName')),'EM:BROKER:'+org,text(r.get('orgSName') or r.get('orgName')),published,published,vals,ref)]
    if f=='executives':
        code=ticker(r.get('stock_code'));when=_date_field(r,'change_date',end,required=True)
        require(day(request['begin'])<=day(when),'EXECUTIVE_WINDOW')
        pub=_date_field(r,'notice_date',end,required=True);person=text(r.get('changer'),required=True)
        vals={'direction':text(r.get('change_direction')),'shares':number(r.get('change_shares')),
              'amount_cny':number(r.get('change_amount')),'average_cny':number(r.get('avg_price')),
              'position':text(r.get('position')),'relation':text(r.get('relation')),
              'reason':text(r.get('change_reason')),'after_shares':number(r.get('shares_after')),
              'related_executive_name':text(r.get('executive_name')),
              'identity':'ISSUER_SCOPED_NAME_NO_CROSS_ISSUER_PERSON_MERGE','phase':'REPORTED_EXECUTION_NOT_PLAN'}
        return [_entry(f,[code,person,when,r.get('change_shares'),r.get('change_amount'),
                         r.get('executive_name'),r.get('position'),r.get('relation')],code,text(r.get('stock_name')),
                       'ISSUER_PERSON:'+code+':'+person,person,when,pub,vals,ref)]
    if f=='holder_changes':
        # Keep actual inspected provider fields: the aggregate quantity unit is
        # deliberately not inferred from magnitude or a different API's name.
        code=ticker(r.get('SECURITY_CODE'));when=_date_field(r,'END_DATE',end,required=True)
        require(day(request['begin'])<=day(when),'HOLDER_CHANGE_WINDOW')
        person=text(r.get('HOLDER_NAME'),required=True)
        pub=_date_field(r,'NOTICE_DATE',end) or _date_field(r,'ANNOUNCEMENT_DATE',end)
        vals={'direction':text(r.get('DIRECTION')),'quantity_raw':number(r.get('CHANGE_NUM')),
              'quantity_unit':'NOT_ESTABLISHED','start':_date_field(r,'START_DATE',end),
              'after_raw':number(r.get('AFTER_HOLDER_NUM')),'phase':'DISCLOSED_CHANGE_INTERVAL_NOT_DAILY_TRADE',
              'identity':'ISSUER_SCOPED_NAME_NO_PERSON_CERTIFICATION'}
        return [_entry(f,[code,person,when,vals['start'],vals['quantity_raw']],code,text(r.get('SECURITY_NAME_ABBR')),
                       'ISSUER_HOLDER:'+code+':'+person,person,when,pub,vals,ref)]
    if f=='repurchases':
        code=ticker(r.get('DIM_SCODE'));scheme=text(r.get('REPURCODE'),required=True)
        pub=_date_field(r,'UPD',end,required=True);require(day(request['begin'])<=day(pub),'REPURCHASE_UPDATE_WINDOW')
        finish_raw=text(r.get('FINISHDATE'))
        finish_day=day(finish_raw).isoformat() if finish_raw else None
        future_finish=bool(finish_day and day(finish_day)>day(end))
        vals={'scheme_id':scheme,'phase_code':text(r.get('REPURPROGRESS')),
              'planned_min_cny':number(r.get('REPURAMOUNTLOWER')),'planned_max_cny':number(r.get('REPURAMOUNTLIMIT')),
              'executed_cumulative_cny':number(r.get('REPURAMOUNT')),'executed_cumulative_shares':number(r.get('REPURNUM')),
              'start':_date_field(r,'REPURSTARTDATE',end),'actual_finish':None if future_finish else finish_day,
              'finish_date_raw':finish_raw,
              'field_gaps':['FUTURE_FINISH_FIELD_NOT_ACTUAL_COMPLETION'] if future_finish else [],
              'planned_deadline_raw':text(r.get('REPURENDDATE')),
              'purpose':text(r.get('REPUROBJECTIVE')),'actual_cancelled_shares':None,
              'identity':'ISSUER_BUYBACK','meaning':'CUMULATIVE_SCHEME_NOT_ADDITIVE_DISCLOSURES'}
        amount,shares=vals['executed_cumulative_cny'],vals['executed_cumulative_shares']
        vals['average_execution_price_derived_cny']=(str(Decimal(amount)/Decimal(shares))
            if amount is not None and shares is not None and Decimal(shares)>0 else None)
        return [_entry(f,[code,scheme],code,text(r.get('SECURITYSHORTNAME')),
                       'ISSUER:'+code,code,vals['actual_finish'] or pub,pub,vals,ref)]
    if f=='placements':
        code=ticker(r.get('SECUCODE') or r.get('SECURITY_CODE'));when=_date_field(r,'ISSUE_DATE',end,required=True)
        require(day(request['begin'])<=day(when) and str(r.get('SEO_TYPE'))=='1','PLACEMENT_SCOPE')
        ident=text(r.get('FINANCE_CODE'),required=True);terms=text(r.get('PRICE_PRINCIPLE'))
        noncash=bool(terms and ('购买资产' in terms or '购买其持有' in terms))
        vals={'issue_id':ident,'shares':number(r.get('ISSUE_NUM')),'price_cny':number(r.get('ISSUE_PRICE')),
              'reported_gross_amount_cny':number(r.get('TOTAL_RAISE_FUNDS')),
              'reported_net_amount_cny':number(r.get('NET_RAISE_FUNDS')),
              'actual_cash_received_cny':None,'consideration':'ASSET_PURCHASE_DESCRIBED' if noncash else 'CASH_RECEIPT_NOT_INDEPENDENTLY_ESTABLISHED',
              'subscription_objects':text(r.get('ISSUE_OBJECT')),'lockup_text':text(r.get('LOCKIN_PERIOD')),
              'price_terms':terms,'phase':'REPORTED_ISSUANCE','identity':'ISSUANCE_OBJECT_TEXT_NOT_INFERRED_ACTORS'}
        return [_entry(f,[code,ident],code,text(r.get('SECURITY_NAME_ABBR')),'ISSUER:'+code,code,when,None,vals,ref)]
    raise SourceError('UNSUPPORTED_FAMILY')


def economic_rows(rows):
    """Collapse exact duplicate versions, retain conflicts and all locators."""
    unique={}
    for item in rows:
        key=(item['id'],item['version'])
        if key in unique: unique[key]['source_rows'].extend(item['source_rows'])
        else: unique[key]=item
    values=list(unique.values())
    ids={}
    for r in values: ids.setdefault(r['id'],set()).add(r['version'])
    return values, sum(len(v)>1 for v in ids.values())


def aggregate_activity(rows):
    """One public disclosure/date group, with an explicit participant roster.

    Missing institution codes remain unresolved names, not distinct institutions.
    One disclosure can contain several sessions; the date interval stays part of
    its identity. No natural-person count is inferred by splitting text.
    """
    groups={}
    for r in rows:
        key=r['values']['event_id'] or 'UNRESOLVED:'+r['id']
        g=groups.setdefault(key,{'id':key,'ticker':r['ticker'],'company':r['company'],
            'actor_id':'ACTIVITY_EVENT:'+key,'actor_name':'机构活动',
            'date':r['date'],'disclosed':r['disclosed'],
            'values':{'event_id':r['values']['event_id'],
                      'event_identity':r['values']['event_identity'],
                      'disclosure_id':r['values']['disclosure_id'],'form':r['values']['form'],
                      'roster':[],'participants_count':None,'distinct_institutions':None,
                      'identity':'ATTENTION_NOT_CAPITAL_INVESTMENT'},'source_rows':[]})
        require(g['ticker']==r['ticker'] and g['date']==r['date'],
                'ACTIVITY_EVENT_CONFLICT')
        # One returned activity may have several publication-date claims. Keep
        # all claims and source rows, not a fabricated earliest-public timestamp.
        claims=g['values'].setdefault('disclosure_date_claims',[])
        if r['disclosed'] not in claims:claims.append(r['disclosed'])
        g['source_rows'].extend(r['source_rows'])
        scope=r['values'].get('roster_scope','PARTICIPANT_DETAIL')
        require(g['values'].get('roster_scope',scope)==scope,'ACTIVITY_ROSTER_SCOPE_CONFLICT')
        g['values']['roster_scope']=scope
        counts=g['values'].setdefault('reported_institution_entry_claims',[])
        count=r['values'].get('provider_reported_institution_entries')
        if count not in counts:counts.append(count)
        g['values']['roster'].append({'actor_id':r['actor_id'],'name':r['actor_name'],
            'institution_code':r['values']['institution_code'],
            'institution_type':r['values']['institution_type'],
            'participant_text':r['values']['participants']})
    for g in groups.values():
        claims=g['values']['disclosure_date_claims']
        claims.sort(key=lambda x:x or '')
        g['disclosed']=claims[0] if len(claims)==1 else None
        g['values']['disclosure_date_status']=('SINGLE_SOURCE_DATE_CLAIM' if len(claims)==1
                                               else 'MULTIPLE_SOURCE_DATES_NOT_RESOLVED')
        counts=g['values']['reported_institution_entry_claims']
        counts.sort(key=lambda x:x or '')
        g['values']['provider_reported_institution_entries']=counts[0] if len(counts)==1 else None
        roster={canonical_hash(r):r for r in g['values']['roster']}
        g['values']['roster']=list(roster.values())
        codes={r['institution_code'] for r in roster.values() if r['institution_code']}
        g['values']['known_institution_codes']=len(codes)
        g['values']['unresolved_roster_rows']=sum(not r['institution_code'] for r in roster.values())
        if (g['values'].get('roster_scope')=='PARTICIPANT_DETAIL'
                and all(r['institution_code'] for r in roster.values())):
            g['values']['distinct_institutions']=len(codes)
        g['version']=canonical_hash({k:v for k,v in g.items() if k not in {'source_rows','version'}})
    return list(groups.values())
