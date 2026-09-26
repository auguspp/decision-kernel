"""Lossless bounded history, separate observation types, and two-way reading.

Stored gzip chunks are plain JSON data. No archive code or source markup runs.
A company/participant lookup reads the same records used by the daily summary.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import gzip
from hashlib import sha256
from html import escape
import json

from ..identity import canonical_hash, canonical_json
from . import smart_money_sources as s

TITLES={
 'hot_money':'游资标签公开轨迹','institutional':'龙虎榜机构席位','seats':'原始营业部席位',
 'northbound':'北向成交（非净流入）','holdings':'具名个人与机构报告期持股',
 'north_holdings':'北向季度持股','activity':'机构调研活动','forecasts':'研报与预期版本',
 'executives':'高管实际持股变动','holder_changes':'股东披露增减持区间',
 'repurchases':'公司回购计划与执行','placements':'定增与战略资本发行'}
CHUNK_ROWS=15000
MAX_CHUNK=4*1024*1024
MAX_RECORDS=300000
MAX_EXPANDED=256*1024*1024


def compact_part(part):
    return {k:v for k,v in part.items() if k!='rows'}


def state(observation, old=None):
    old=old or {}
    completed={(p['family'],p['partition']):p for p in old.get('completed_partitions',[])}
    for p in observation['partitions']:
        if p['complete']:
            completed[p['family'],p['partition']]={k:p[k] for k in ('family','partition','begin','end')}
            completed[p['family'],p['partition']]['cutoff']=observation['cutoff']
    return {'version':s.VERSION,'target_date':observation['target_date'],
            'cutoff':observation['cutoff'],'capture_hash':observation['capture_hash'],
            'last_source_run_id':observation['identity']['run_id'],
            'calendar_enumerated_through':observation.get('calendar_enumerated_through'),
            'calendar_pending_since':observation.get('calendar_pending_since'),
            'late_confirmation_complete':bool(observation['trading_sessions'] and
                observation.get('calendar_enumerated_through') and
                (s.clock(observation['cutoff']).astimezone(s.ZONE).hour>=19 or
                 max(observation['trading_sessions'])<observation['target_date'])),
            'unresolved':observation['unresolved'],'policy_stops':observation.get('policy_stops',[]),
            'completed_partitions':list(completed.values()),
            'meaning':'SAVED_DELIVERY_PROGRESS_NOT_SOURCE_TRUTH'}


def history(observation, prior=None):
    """An older quarter/failed family never turns into a current zero position."""
    prior=prior or {}; current_hash=observation['capture_hash']
    if prior.get('capture_hash')==current_hash and prior.get('projection_revision')==s.PROJECTION_REVISION:
        return deepcopy(prior)
    reinterpret=bool(prior.get('capture_hash')==current_hash and prior.get('projection_revision')!=s.PROJECTION_REVISION)
    if reinterpret:
        prior=deepcopy(prior)
        prior['records']=[r for r in prior['records'] if r['origin']!=current_hash]
    store={(r['family'],r['data']['id'],r['data']['version']):deepcopy(r) for r in prior.get('records',[])}
    old_ids=defaultdict(set)
    for f,i,v in store:old_ids[f,i].add(v)
    first=not prior.get('capture_hash');changes=Counter();examples=[]
    for p in observation['partitions']:
        if p['complete'] and p['family'] in {'holdings','north_holdings'}:
            # An authoritative replacement of this source snapshot may remove a
            # row. Keep its historical bytes, but do not keep presenting it as
            # a member of the corrected current snapshot (or infer a sale).
            current_keys={(p['family'],r['id'],r['version']) for r in p['rows']}
            periods={r['date'] for r in p['rows']} or {p['partition']}
            for key,retained in store.items():
                same_partition=(p['family']!='north_holdings' or
                    retained['partition'].split('@')[0]==p['partition'].split('@')[0])
                if key[0]==p['family'] and same_partition and retained['data']['date'] in periods and key not in current_keys:
                    retained['withdrawn_from_source_snapshot_at']=observation['cutoff']
        for raw in p['rows']:
            key=p['family'],raw['id'],raw['version']
            if key in store:
                # Stable rows retain their original provenance and bytes. The current
                # family capture records how recently they were checked.
                store[key]['last_seen']=observation['cutoff']
                store[key].pop('withdrawn_from_source_snapshot_at',None)
                changes['UNCHANGED']+=1
                continue
            tag=('REINTERPRETED_SAME_SOURCE_NOT_NEW_EVENT' if reinterpret else
                 'BASELINE_FIRST_OBSERVED' if first else 'SOURCE_VERSION_CHANGED'
                 if old_ids.get(key[:2]) else 'NEWLY_OBSERVED_NOT_NEWLY_OCCURRED')
            entry={'family':p['family'],'partition':p['partition'],'data':deepcopy(raw),
                   'origin':current_hash,'first_seen':observation['cutoff'],'last_seen':observation['cutoff'],'change':tag}
            store[key]=entry;changes[tag]+=1
            if len(examples)<120:examples.append({'family':p['family'],'id':raw['id'],'ticker':raw['ticker'],
                'actor_name':raw['actor_name'],'date':raw['date'],'change':tag})
    # Retain last two ended-quarter bases and 90-day event history in the current
    # reading. All earlier immutable reading commits remain independently valid.
    from datetime import timedelta
    floor=(s.day(observation['target_date'])-timedelta(days=100)).isoformat()
    quarters=set(s.periods(s.day(observation['target_date'])))
    def visible_date(r):
        d=r['data'];claims=d['values'].get('disclosure_date_claims',[])
        return max([d['date'],d.get('disclosed') or '',*[x for x in claims if x]])
    # Current disclosure windows can legitimately describe much older events.
    # Do not discard a newly disclosed event by its historical activity date.
    rows=[r for r in store.values() if (r['family']=='holdings' and r['data']['date'] in quarters)
          or (r['family']=='north_holdings') or (r['family']!='holdings' and visible_date(r)>=floor)]
    s.require(len(rows)<=MAX_RECORDS,'HISTORY_RECORD_BOUND')
    rows.sort(key=lambda x:(x['family'],x['data']['date'],x['data']['ticker'] or '',x['data']['id'],x['data']['version']))
    coverage=deepcopy(prior.get('coverage',{}))
    for part in observation['partitions']:
        coverage[part['family']+'|'+part['partition']]={'complete':part['complete'],'cutoff':observation['cutoff'],
            'origin':current_hash,'begin':part['begin'],'end':part['end']}
    documents=deepcopy(prior.get('forecast_documents',[]))
    by_report={d['report_id']:d for d in documents}
    for doc in observation.get('forecast_documents',[]):
        retained=deepcopy(doc)
        retained['origin_capture_hash']=current_hash
        retained['origin_cutoff']=observation['cutoff']
        by_report[doc['report_id']]=retained
    return {'version':s.VERSION,'projection_revision':s.PROJECTION_REVISION,
            'forecast_documents':list(by_report.values()),
            'forecast_document_recovery':prior.get('forecast_document_recovery'),
            'reinterpretation':reinterpret,'capture_hash':current_hash,'cutoff':observation['cutoff'],
            'coverage':coverage,
            'records':rows,'changes':dict(changes),'change_examples':examples,
            'first_baseline':first,'display_retention':'100D_EVENTS_AND_TWO_ENDED_QUARTERS; OLDER_IMMUTABLE_GIT_HISTORY_UNCHANGED',
            'removed_from_current_display_not_deleted_history':len(store)-len(rows)}


def encode_chunks(value):
    rows=value['records'];chunks={};refs=[];groups=defaultdict(list)
    for row in rows:
        key=row['family']+('-'+row['partition'] if row['family']=='holdings' else '')
        groups[key].append(row)
    for group,members in sorted(groups.items()):
        for offset in range(0,len(members),CHUNK_ROWS):
            part=members[offset:offset+CHUNK_ROWS]
            raw=s.encoded(part);data=gzip.compress(raw,mtime=0)
            s.require(len(data)<=MAX_CHUNK,'SNAPSHOT_CHUNK_BOUND')
            key=f'data-{group}-{offset//CHUNK_ROWS:04d}.json.gz';chunks[key]=data
            refs.append({'name':key,'rows':len(part),'sha256':sha256(data).hexdigest(),
                         'bytes':len(data),'expanded_bytes':len(raw)})
    meta={k:v for k,v in value.items() if k!='records'}
    meta.update(chunks=refs,record_count=len(rows))
    return chunks,meta


def decode_chunks(meta, chunks):
    s.require(meta.get('version')==s.VERSION and isinstance(meta.get('chunks'),list)
              and len(meta['chunks'])<=len(s.FAMILIES)+2+MAX_RECORDS//CHUNK_ROWS,'HISTORY_MANIFEST')
    total=0;rows=[];seen=set()
    for index,ref in enumerate(meta['chunks']):
        import re
        s.require(re.fullmatch(r'data-[a-z_]+(?:-\d{4}-\d{2}-\d{2})?-\d{4}\.json\.gz',ref['name']) is not None and ref['name'] not in seen,'HISTORY_PATH')
        seen.add(ref['name']);data=chunks[ref['name']]
        s.require(len(data)==ref['bytes']<=MAX_CHUNK and sha256(data).hexdigest()==ref['sha256'],'HISTORY_CHUNK_IDENTITY')
        # Bound decompression before handing bytes to JSON.
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:raw=stream.read(min(ref['expanded_bytes']+1,MAX_EXPANDED+1))
        total+=len(raw)
        s.require(len(raw)==ref['expanded_bytes'] and total<=MAX_EXPANDED,'HISTORY_EXPANSION_BOUND')
        part=json.loads(raw)
        s.require(isinstance(part,list) and len(part)==ref['rows']<=CHUNK_ROWS,'HISTORY_CHUNK_ROWS')
        for r in part:
            d=r['data'];s.require(r['family'] in s.FAMILIES and d['version']==canonical_hash({k:v for k,v in d.items() if k not in {'version','source_rows'}}),'HISTORY_RECORD_IDENTITY')
        rows.extend(part)
    s.require(len(rows)==meta['record_count']<=MAX_RECORDS and set(chunks)==seen,'HISTORY_RECORD_COUNT')
    return {**{k:v for k,v in meta.items() if k not in ('chunks','record_count')},'records':rows}


def latest_rows(hist,family):
    byid={}
    for r in hist['records']:
        if r['family']!=family or r.get('withdrawn_from_source_snapshot_at'):continue
        # Same-id content conflicts within a capture remain concurrent; no
        # silent numeric comparison/aggregation of those records.
        old=byid.setdefault(r['data']['id'],[])
        old.append(r)
    out=[]
    for group in byid.values():
        at=max(s.clock(r['last_seen']) for r in group)
        out.extend(r['data'] for r in group if s.clock(r['last_seen'])==at)
    return out


def holdings_changes(hist,family='holdings'):
    groups=defaultdict(dict);conflicts=set()
    for r in latest_rows(hist,family):
        key=r['ticker'],r['actor_id'],r['actor_name'],r['values'].get('share_class')
        if r['date'] in groups[key]:conflicts.add(key)
        groups[key][r['date']]=r
    output=[]
    for key,periods in groups.items():
        if key in conflicts or len(periods)<2:continue
        before,after=[periods[d] for d in sorted(periods)[-2:]]
        a,b=before['values'].get('shares'),after['values'].get('shares')
        if a is None or b is None:continue
        change=Decimal(b)-Decimal(a)
        if change:
            output.append({'ticker':after['ticker'],'company':after['company'],'actor':after['actor_name'],
                'actor_id':after['actor_id'],'prior_period':before['date'],'period':after['date'],
                'previous_shares':a,'shares':b,'change_shares':str(change),
                'disclosed':after['disclosed'],'meaning':'REPORTED_HOLDING_CHANGE_NOT_PROVEN_TRADES_OR_CURRENT_POSITION'})
    return output


def top_ten_transitions(hist):
    rows=latest_rows(hist,'holdings');quarters=sorted({r['date'] for r in rows})[-2:]
    if len(quarters)<2 or not all(hist.get('coverage',{}).get('holdings|'+p,{}).get('complete') for p in quarters):
        return {'status':'ABSENCE_COMPARISON_UNQUALIFIED','entries':[],'departures':[]}
    bycompany=defaultdict(lambda:defaultdict(dict));ambiguous=set()
    for r in rows:
        if r['date'] in quarters:
            records=bycompany[r['ticker']][r['date']]
            key=(r['actor_id'],r['actor_name'],r['values'].get('share_class'))
            if key in records:ambiguous.add(r['ticker'])
            records[key]=r
    entries=[];departures=[]
    for code,periods in bycompany.items():
        if code in ambiguous:continue
        if not all(p in periods for p in quarters):continue
        old,new=(periods[p] for p in quarters)
        for key in new.keys()-old.keys():
            r=new[key];entries.append({'ticker':code,'actor_name':r['actor_name'],'actor_id':r['actor_id'],
                'period':quarters[1],'prior_period':quarters[0],'shares':r['values']['shares'],
                'meaning':'NEW_IN_DISCLOSED_TOP_TEN_NOT_PROVEN_NEW_PURCHASE'})
        for key in old.keys()-new.keys():
            r=old[key];departures.append({'ticker':code,'actor_name':r['actor_name'],'actor_id':r['actor_id'],
                'period':quarters[1],'prior_period':quarters[0],
                'meaning':'ABSENT_FROM_DISCLOSED_TOP_TEN_NOT_PROVEN_SALE_OR_ZERO'})
    return {'status':('CONCURRENT_SNAPSHOT_VERSIONS_NOT_COMPARABLE' if ambiguous else
        'COMPARABLE_PROVIDER_QUARTERS_NOT_COMPLETE_BENEFICIAL_OWNERSHIP'),
        'ambiguous_companies':sorted(ambiguous),'entries':entries,'departures':departures}


def attention_counts(hist,target):
    from datetime import timedelta
    last=s.day(target);a=(last-timedelta(days=29)).isoformat();b=(last-timedelta(days=89)).isoformat()
    coverage=hist.get('coverage',{}).get('activity|disclosures',{})
    comparable=bool(coverage.get('complete') and coverage.get('begin','9999')<=b
                    and coverage.get('end','')>=target)
    groups={}
    for r in latest_rows(hist,'activity'):
        if not b<=r['date']<=target or not r['values'].get('event_id'):continue
        g=groups.setdefault(r['ticker'],{'ticker':r['ticker'],'company':r['company'],'events_30d':0,
            'events_previous_60d':0,'known_org_codes':set(),'unresolved_roster_rows':0})
        g['events_30d' if r['date']>=a else 'events_previous_60d']+=1
        g['known_org_codes'].update(p['institution_code'] for p in r['values']['roster'] if p['institution_code'])
        g['unresolved_roster_rows']+=r['values']['unresolved_roster_rows']
    for g in groups.values():
        g['known_distinct_org_codes_90d']=len(g.pop('known_org_codes'))
        g['count_qualification']='COMPLETE_RETURN_WITH_DISCLOSURE_LAG_LIMITS' if comparable else 'OBSERVED_LOWER_BOUND'
        g['recent_vs_prior_monthly_rate']=(str(Decimal(g['events_30d'])*2/Decimal(g['events_previous_60d']))
            if comparable and g['events_previous_60d'] else None)
        g['meaning']='COUNTS_IN_CURRENT_RETRIEVED_SOURCE_NOT_COMPLETE_ORIGINAL_PUBLICATION_VINTAGE'
    return list(groups.values())


def summarize(obs,hist):
    families={}
    for f in s.FAMILIES:
        parts=[p for p in obs['partitions'] if p['family']==f]
        rows=latest_rows(hist,f)
        deferred=[p for p in obs.get('deferred_partitions',[]) if p['family']==f]
        families[f]={'title':TITLES[f],'current_partitions':len(parts),'complete_partitions':sum(p['complete'] for p in parts),
            'saved_records':len(rows),'companies':len({r['ticker'] for r in rows if r['ticker']}),
            'status':('DEFERRED_WITH_EXPLICIT_LAST_CAPTURE' if deferred and not parts else
                      'NOT_ACQUIRED' if not parts else 'COMPLETE_PROVIDER_SCOPES' if all(p['complete'] for p in parts) else 'PARTIAL_OR_UNAVAILABLE'),
            'earliest_period':min((r['date'] for r in rows),default=None),'latest_period':max((r['date'] for r in rows),default=None),
            'current_rows':sum(p['normalized_rows'] for p in parts),
            'out_of_scope_rows':sum(len(p.get('excluded_rows',[])) for p in parts),'deferred':deferred,
            'ambiguous_disclosure_groups':sum(r['values'].get('disclosure_date_status')=='MULTIPLE_SOURCE_DATES_NOT_RESOLVED' for r in rows),
            'field_gap_rows':sum(bool(r['values'].get('field_gaps')) for r in rows),
            'partitions':[compact_part(p) for p in parts]}
        families[f]['unresolved_partitions']=sum(g.get('family')==f for g in obs['unresolved'])
        if families[f]['unresolved_partitions'] and families[f]['status']=='COMPLETE_PROVIDER_SCOPES':
            families[f]['status']='CURRENT_SCOPES_AVAILABLE_WITH_HISTORICAL_GAPS'
        if f=='activity':
            families[f]['roster_coverage']='PROVIDER_EVENT_SUMMARIES_NOT_ALL_PARTICIPANT_ROWS'
            families[f]['event_groups']=sum(r['values'].get('event_id') is not None for r in rows)
            families[f]['unidentified_event_rows']=sum(r['values'].get('event_id') is None for r in rows)
            families[f]['known_institution_codes']=len({t['institution_code'] for r in rows for t in r['values']['roster'] if t['institution_code']})
            families[f]['unresolved_roster_rows']=sum(r['values']['unresolved_roster_rows'] for r in rows)
        if f=='holdings':
            families[f]['named_individual_provider_rows']=sum(r['values'].get('holder_type') in {'个人','自然人','境内自然人'} for r in rows)
            families[f]['verified_famous_investor_identity']='NOT_CERTIFIED_FROM_NAME_OR_TOP_TEN_APPEARANCE'
    changes=holdings_changes(hist);north=holdings_changes(hist,'north_holdings');transitions=top_ten_transitions(hist);attention=attention_counts(hist,obs['target_date'])
    return {'version':s.VERSION,'target_date':obs['target_date'],'cutoff':obs['cutoff'],'capture_hash':obs['capture_hash'],
        'status':obs['status'],'families':families,'unresolved':obs['unresolved'],
        'increment_counts':hist['changes'],'first_baseline':hist['first_baseline'],
        'top_ten_changes':{'status':transitions['status'],'entries':len(transitions['entries']),
            'departures':len(transitions['departures']),'ambiguous_companies':transitions.get('ambiguous_companies',[]),'entry_examples':transitions['entries'][:30],
            'departure_examples':transitions['departures'][:20]},
        'institutional_attention':{'companies':len(attention),'examples':attention[:30],
            'scope':'COMPLETE_LOOKUP_REBUILDS_ALL_COMPANIES_FROM_SAME_SAVED_ROWS'},
        'holding_comparisons':{'comparable_nonzero_pairs':len(changes),'examples':changes[:30],
            'not_inferred':['TRADING_DATE','CURRENT_HOLDING','TOP_TEN_ABSENCE_AS_EXIT','CORPORATE_ACTION_ADJUSTED_NET_BUY']},
        'north_holding_comparisons':{'comparable_nonzero_pairs':len(north),'examples':north[:20],
                                    'meaning':'QUARTERLY_SHARES_NOT_DAILY_NET_BUY'},
        'forecast_documents':hist.get('forecast_documents',obs.get('forecast_documents',[])),
        'forecast_document_recovery':hist.get('forecast_document_recovery'),
        'seat_label_binding':'VENDOR_LABELS_AND_ORIGINAL_SEATS_SEPARATE; NO_UNPROVEN_PERSON_JOIN',
        'first_seen_meaning':'NEWLY_INGESTED_MAY_HAVE_BEEN_PUBLIC_BEFORE; NOT_ALL_EVENTS_OCCUR_TODAY',**s.AUTHORITY}


def md(x):return escape(str(x if x is not None else 'UNKNOWN')).replace('|','&#124;').replace('\n',' ')


def render(overview,hist,*,failure=None):
    lines=['# 聪明钱观察：参与者公开行为与变化','',
           f"检查日 {overview['target_date']}；取得截止 {overview['cutoff']}；状态 {overview['status']}。",'',
           '**首次建立的旧资料基线，不是今天新发生的全部行为。**' if overview['first_baseline'] else
           '新取得、同期修订和已知未变分别保留；再次发布同一采集不算新事件。','']
    if failure:lines += ['**本次新采集未取得，以下保留旧日期与旧来源。** '+md(failure),'']
    lines += ['| 独立观察面 | 已保存记录/公司 | 当前覆盖 | 原统计/事件日期 |', '|---|---:|---|---|']
    for f,v in overview['families'].items():
        lines.append(f"| {v['title']} | {v['saved_records']} / {v['companies']} | {v['status']}；{v['complete_partitions']}/{v['current_partitions']}批 | {v['earliest_period']}—{v['latest_period']} |")
    if overview['families']['holdings'].get('out_of_scope_rows'):
        lines += ['', '来源表中另有 '+str(overview['families']['holdings']['out_of_scope_rows'])+' 条NQ记录，已逐条保留范围外处置，不伪装成沪深北股票。']
    lines += ['', '## 可直接继续研究的公开线索','', '以下按来源时间/原始顺序展示，不是投资排名；全部记录可按公司或参与者检索。','']
    for f in ('hot_money','institutional','executives','repurchases','placements'):
        rr=latest_rows(hist,f);latest=max((r['date'] for r in rr),default='')
        sample=[r for r in rr if r['date']==latest][:5]
        lines += ['### '+TITLES[f],'']
        for r in sample:
            v=r['values']
            if f in ('hot_money','institutional'):detail=f"{v.get('window_days')}日披露窗口；净额 {v.get('net_cny')} CNY"
            elif f=='executives':detail=f"{v.get('direction')} {v.get('shares')}股；原披露金额 {v.get('amount_cny')} CNY"
            elif f=='repurchases':detail=f"方案累计已执行 {v.get('executed_cumulative_cny')} CNY；计划 {v.get('planned_min_cny')}—{v.get('planned_max_cny')}；用途 {v.get('purpose')}"
            else:detail=f"发行 {v.get('shares')}股；{v.get('consideration')}；锁定条款 {v.get('lockup_text')}"
            lines.append(f"- {md(r['company'] or r['ticker'])} {md(r['ticker'])} / {md(r['actor_name'])} / {r['date']}：{md(detail)}。")
        if not sample:lines.append('本读取未取得可用记录，不代表没有行为。')
        lines.append('')
    lines += ['### 具名持有人跨期变化','',
              f"同一来源身份/公司/股类的非零持股差 {overview['holding_comparisons']['comparable_nonzero_pairs']} 对；不是净买入。"]
    for r in overview['holding_comparisons']['examples'][:8]:
        lines.append(f"- {md(r['actor'])} / {md(r['ticker'])}：{r['prior_period']} {r['previous_shares']}股 → {r['period']} {r['shares']}股；差 {r['change_shares']}股。")
    lines += ['', '### 机构调研与预测','',
              '调研按来源已披露活动分组；事件摘要覆盖与参与者明细覆盖分开。原披露文件未给出时保留来源时间/方式分组，不认证实际场次。代表机构一行不等于完整名单，泛称投资者不当已识别机构。',
              '研报EPS相对槽位不自动认定目标年/币种/股本口径；只有正文明确同时列示的新旧同指标，才显示为“券商在该文声称的修订”，不是已独立找回旧报告。']
    for doc in overview['forecast_documents']:
        for r in doc.get('revisions',[]):
            lines.append(f"- {md(r['actor_name'])} / {r['ticker']} / {r['target_year']}归母净利：原文前值 {r['old_as_quoted']} → {r['new']} {md(r['unit'])}；第{r['page']}页；旧报告未独立复验。")
    if overview.get('forecast_document_recovery'):
        lines.append('研报正文接续：'+md(overview['forecast_document_recovery'])+'；每份保留原采集截止，不冒称本批新读。')
    lines += ['', '## 覆盖缺口与解释边界','',
              '游资名称是供应商标签；原始营业部单独保留，未凭金额相等认证某自然人。1日/3日重叠榜不相加，未再次上榜不推断持有或退出。',
              '北向成交额不等于净流入；HKEX季度CCASS数量不是实时仓位，也不是某一个外资机构。',
              '自然人同名只允许查找关联，不能自动跨公司合并为同一牛散。前十大之外的持股不在观察范围，榜单消失不等于清仓。',
              '回购方案金额和累计实施分开；回购用途不证明已注销。定增认购对价或购买资产不等于收到现金。',
              '各日期分别表示报告期、公开行为日、披露日、取得日。新进入本库不是新建仓。所有数据只是研究线索。','']
    for f,v in overview['families'].items():
        if v.get('ambiguous_disclosure_groups') or v.get('field_gap_rows'):
            lines.append(f"- {TITLES[f]}：{v.get('ambiguous_disclosure_groups',0)}组披露日期有多个来源声明；{v.get('field_gap_rows',0)}条有局部字段缺口。原记录仍可读，不认定唯一发布日期或已完成日。")
    for g in overview['unresolved']:
        lines.append(f"- 未解决：{md(g.get('family'))} / {md(g.get('partition'))} / {md(g.get('begin'))}—{md(g.get('end'))}：{md(g.get('failure') or 'ROW_OR_IDENTITY_QUALIFICATION')}。")
    lines += ['', '[公司/参与者双向检索](smart-money/browse.html) · [结构化概览与来源定位](smart-money/overview.json) · [完整历史数据分块目录](smart-money/history.json)',
              '', 'Radar发现，Quick解释；无自动Full、Odds、买卖或仓位权限。']
    return '\n'.join(lines)+'\n'


def browser_chunks(chunks, meta):
    """Display-only projection; authoritative history chunks remain byte-identical.

    The browser never consumes the record identity hash. Keeping a second copy
    of that high-entropy field inflated the offline page beyond its 30 MiB cap.
    Preserve every record and every displayed/provenance field; original chunks
    retain the omitted id and have their own immutable references and digests.
    """
    import base64
    import io
    projected = []
    for ref in meta['chunks']:
        original = chunks[ref['name']]
        s.require(len(original) == ref['bytes'] <= MAX_CHUNK
                  and sha256(original).hexdigest() == ref['sha256'], 'HISTORY_CHUNK_IDENTITY')
        with gzip.GzipFile(fileobj=io.BytesIO(original)) as stream:
            raw = stream.read(min(ref['expanded_bytes'] + 1, MAX_EXPANDED + 1))
        s.require(len(raw) == ref['expanded_bytes'] <= MAX_EXPANDED, 'HISTORY_EXPANSION_BOUND')
        rows = json.loads(raw)
        s.require(isinstance(rows, list) and len(rows) == ref['rows'], 'HISTORY_CHUNK_ROWS')
        for row in rows:
            row['data'].pop('id')
        raw = s.encoded(rows)
        data = gzip.compress(raw, mtime=0)
        s.require(len(data) <= MAX_CHUNK, 'SNAPSHOT_CHUNK_BOUND')
        projected.append({'ref': {'name': ref['name'], 'rows': len(rows),
                                 'bytes': len(data), 'expanded_bytes': len(raw),
                                 'sha256': sha256(data).hexdigest()},
                          'original_ref': ref,
                          'base64': base64.b64encode(data).decode()})
    return projected


def browser(overview,chunks,meta,origins):
    """Self-contained searchable reading; gzip is data, no source code executed."""
    import base64
    manifest={'overview':overview,'history':meta,'origins':origins,
              'projection':'DISPLAY_RECORDS_WITHOUT_UNUSED_ID; ORIGINAL_HISTORY_CHUNKS_UNCHANGED',
              'chunks':browser_chunks(chunks,meta)}
    raw=json.dumps(manifest,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    script=r'''
'use strict';
const pack=JSON.parse(document.getElementById('payload').textContent);
let records=[], filtered=[], page=0;const pageSize=40;
const $=id=>document.getElementById(id);
function node(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;}
function render(){
  $('results').replaceChildren();
  const a=page*pageSize,b=Math.min(a+pageSize,filtered.length);
  $('count').textContent=`匹配 ${filtered.length} 条；当前 ${filtered.length?a+1:0}—${b}；历史版本不等于独立事件。`;
  for(const r of filtered.slice(a,b)){
    const d=r.data, card=node('article');
    card.append(node('h3',[d.company||d.ticker||'市场',d.ticker,d.actor_name||'来源身份未确定'].filter(Boolean).join(' · ')));
    card.append(node('p',`${r.family} | 观察/报告期 ${d.date} | 披露 ${d.disclosed||'UNKNOWN'} | 首次取得 ${r.first_seen} | 此版本最近原件 ${r.last_seen}`));
    const detail=node('details'); detail.append(node('summary','原值、参与者和来源定位（不是买卖建议）'));
    detail.append(node('pre',JSON.stringify({values:d.values,actor_id:d.actor_id,source_rows:d.source_rows,origin:pack.origins[r.origin],source_version:d.version},null,2)));
    if(r.withdrawn_from_source_snapshot_at)card.append(node('p',`历史记录：已从来源当前快照撤出（${r.withdrawn_from_source_snapshot_at}）；不等于清仓。`));
    card.append(detail);$('results').append(card);
  }
  $('prev').disabled=page===0;$('next').disabled=b>=filtered.length;
}
function search(){
  const q=$('query').value.trim().toLocaleLowerCase(),family=$('family').value;
  filtered=records.filter(r=>{
    if(family && r.family!==family)return false;
    if(!q)return true;
    const d=r.data;
    const text=[d.ticker,d.company,d.actor_name,d.actor_id,d.values.subscription_objects,...(d.values.roster||[]).flatMap(x=>[x.name,x.institution_code])].join(' ').toLocaleLowerCase();
    return text.includes(q);
  }).reverse();page=0;render();
}
async function init(){
  $('health').textContent=`${pack.overview.status} · 资料取得截止 ${pack.overview.cutoff} · 共 ${pack.history.record_count} 条保存版本`;
  for(const [id,f] of Object.entries(pack.overview.families)){
    const o=node('option',f.title);o.value=id;$('family').append(o);
  }
  for(const ch of pack.chunks){
    const bytes=Uint8Array.from(atob(ch.base64),c=>c.charCodeAt(0));
    if(bytes.length!==ch.ref.bytes)throw Error('保存数据长度不符');
    if(!globalThis.crypto?.subtle?.digest)throw Error('当前环境缺少安全摘要能力');
    const digest=new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes));
    const hex=Array.from(digest,b=>b.toString(16).padStart(2,'0')).join('');
    if(hex!==ch.ref.sha256)throw Error('保存数据SHA256不符');
    if(!Number.isSafeInteger(ch.ref.expanded_bytes)||ch.ref.expanded_bytes<0||ch.ref.expanded_bytes>268435456)throw Error('展开预算无效');
    const reader=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')).getReader();
    const pieces=[];let count=0;
    try{
      while(true){const {done,value}=await reader.read();if(done)break;count+=value.length;
        if(count>ch.ref.expanded_bytes){await reader.cancel();throw Error('展开超出声明长度');}pieces.push(value);}
    }finally{reader.releaseLock();}
    if(count!==ch.ref.expanded_bytes)throw Error('保存数据展开长度不符');
    const buf=new Uint8Array(count);let offset=0;for(const piece of pieces){buf.set(piece,offset);offset+=piece.length;}
    const part=JSON.parse(new TextDecoder().decode(buf));
    if(part.length!==ch.ref.rows)throw Error('保存数据行数不符');records.push(...part);
  }
  if(records.length!==pack.history.record_count)throw Error('完整记录数不符');
  $('query').disabled=false;$('family').disabled=false;search();
}
$('query').addEventListener('input',search);$('family').addEventListener('change',search);
$('prev').onclick=()=>{page--;render()};$('next').onclick=()=>{page++;render()};
init().catch(e=>{$('health').textContent='读取失败：'+e.message+'。不是没有活动。';});
'''
    digest=base64.b64encode(sha256(script.encode()).digest()).decode()
    page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-%s'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>聪明钱公开行为 · 双向阅读</title><style>body{font:16px/1.7 system-ui;max-width:1100px;margin:auto;padding:24px}article{border-top:1px solid #bbb;padding:12px 0}input,select,button{font:inherit;padding:8px;max-width:100%%}input{width:55%%}pre{white-space:pre-wrap;overflow-wrap:anywhere}h3{overflow-wrap:anywhere}@media(max-width:600px){body{padding:12px}input{width:94%%}}</style></head><body>
<h1>聪明钱观察：公司与参与者双向检索</h1><p id="health">正在展开本文件内的数据，不发网络请求。</p>
<p>此页为完整记录的显示投影；省略未展示的记录ID，原始身份与完整字段仍在同版历史分块中。输入公司、代码、营业部、游资标签、具名持有人或调研机构。名称匹配不是身份认证；同名个人不自动合并。北向为公开成交/季度持股，不是实时净买入。记录日期不一定是取得日，榜单缺席不证明退出。</p>
<label>检索 <input id="query" placeholder="公司 / 代码 / 游资标签 / 具名持有人" disabled></label>
<label>观察面 <select id="family" disabled><option value="">全部独立观察面</option></select></label>
<p id="count"></p><button id="prev" disabled>上一页</button> <button id="next" disabled>下一页</button><main id="results"></main>
<script id="payload" type="application/json">%s</script><script>%s</script></body></html>'''%(digest,raw,script)
    s.require(len(page.encode())<30*1024*1024,'BROWSER_OUTPUT_BOUND')
    return page
