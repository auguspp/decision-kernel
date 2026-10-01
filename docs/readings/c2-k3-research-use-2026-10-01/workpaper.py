"""One frozen K3 comparison workpaper, not a detector or historical-member model.
Explicit local execution only; qualified project identity code must be on PYTHONPATH.
Input order: original K3 ZIP, original Stock ZIP, fixed-R membership JSON,
fixed-R current-state JSON, absent output directory. No source calls or old scripts.
"""
from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import io
import json
from pathlib import Path
from statistics import median
import sys
import zipfile
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime.current_state import validate_read_package

K3_SHA = 'f985274834e5ca99f995912148fe1af1ebf83f3e0ad7dee05ea8aeeb4807bfde'
STOCK_SHA = '47f4ea4d31f4d575ebb5d16c64269aaaafc280d6ed5e07dc4cce35e6c333fec8'
MEMBER_SHA = '40705d9cba1c33401b3b66112d9ee6de6deb15291b0bb58c5d3af2cd4375956b'
ROOT_SHA = '18d74cec4d84716b7fe1c06eeda645cde088f3661a852e395a4d183b1b744e96'
CAPTURE = '60c2a60017ba3f3aca53e9fe4467e3ea397d807c8484df8fa707789571e301ef'
REPORT = '8ecf93277fa762859ce7f46371444129f7953bcf82518938c3f7733e804015f7'
READING = '9327c06eff231bd6b2f2025c4f15b291ad9e3b7f'

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

def digest(raw):
    return sha256(raw).hexdigest()

def load(raw):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            require(k not in out, 'duplicate JSON key')
            out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=unique)

def sealed(value, field, expected=None):
    require(value[field] == canonical_hash({k:v for k,v in value.items() if k != field}), 'seal '+field)
    require(expected is None or value[field] == expected, 'independent pin '+field)

def archive(path, expected, size):
    raw = Path(path).read_bytes()
    require(len(raw) == size and digest(raw) == expected, 'original ZIP identity')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        require(len(names) == len(set(names)) and z.testzip() is None, 'original ZIP inventory/CRC')
        return {n:z.read(n) for n in names if not n.endswith('/')}

def bound_files(files, prefix, manifest):
    for name, d in manifest['files'].items():
        raw = files[prefix+name]
        require(len(raw) == d['bytes'] and digest(raw) == d['sha256'], 'source inventory '+name)

def equal_number(a, b):
    return a is b if a is None or b is None else Decimal(str(a)) == Decimal(str(b))

def frac(row):
    # U rows remain unknown; never turn null/zero quote histories into returns.
    return None if row['disposition'] == 'U' else Fraction(row['last_price'])/Fraction(row['prev_price'])-1

def dec(value):
    if value is None: return None
    with localcontext() as ctx:
        ctx.prec = 50
        return format(Decimal(value.numerator)/Decimal(value.denominator), 'f')

def build(k3, old, membership, reading):
    validate_read_package(reading)
    require(reading['reading_hash'] == ROOT_SHA, 'fixed reading root')
    require(reading['research']['tdx_concept_context']['membership']['file']['sha256']==MEMBER_SHA, 'same-R membership')
    require(reading['lanes']['stock']['last_qualified_result']['archive']['sha256']==STOCK_SHA, 'same-R Stock ZIP')
    cap = load(k3['independent-stock-capture/capture.json']); sealed(cap, 'capture_hash', CAPTURE)
    bound_files(k3, 'independent-stock-capture/', cap)
    obs = load(k3['independent-stock-capture/observations.json']); sealed(obs, 'report_hash', REPORT)
    sel = obs['selection']; sealed(sel, 'selection_hash')
    require(sel['selection_hash'] == cap['selection_hash'], 'selection binding')
    require(sel == load(k3['independent-stock-capture/selection.json']), 'saved selection differs')
    require(obs['context']['comparison_session'] == '2026-09-30', 'comparison session')
    columns, rows = obs['inventory']['columns'], obs['inventory']['rows']
    require(canonical_hash(rows) == obs['inventory']['rows_hash'], 'inventory row hash')
    quotes = {r[0]:dict(zip(columns,r)) for r in rows}
    require(len(quotes) == len(rows) == sel['complete_denominator'] == 5578, 'full denominator')
    pages = [load(k3['independent-stock-capture/'+p['file']])['data']['item'] for p in obs['pages']]
    require(sum(map(len,pages)) == len(rows), 'complete page counts')
    for r in quotes.values():
        source = pages[r['page_index']][r['row_position']]
        require(source['thscode']==r['thscode'] and all(equal_number(source[k],r[k]) for k in ('last_price','prev_price')), 'original quote join')
    with localcontext() as ctx:
        ctx.prec = 28
        ordered = sorted((r for r in quotes.values() if r['disposition'] != 'U'),
                         key=lambda r:(-abs(Decimal(r['last_price'])/Decimal(r['prev_price'])-1),r['thscode']))
    selected = [r['thscode'] for r in sel['selected']]
    require(selected == [r['thscode'] for r in ordered[:3]], 'fixed K3 selection')
    require(Counter(r['disposition'] for r in quotes.values()) == Counter(S=3,D=5557,U=18), 'retained unpriced/deferred')
    audit = load(old['market-context/input-audit/manifest.json']); sealed(audit,'audit_hash','81a3eaeb66b18bf03679756c3d4cdacf339b6b05f7e2e9ba61e8069cba8958f7')
    bound_files(old,'market-context/input-audit/',audit)
    stockcap = load(old['reading/capture.json']); sealed(stockcap,'capture_hash','2aa308ce96a5d020141b086f0b0d26379610bf85dc9afe1b3569d8d09477f446')
    bound_files(old,'reading/',stockcap)
    result_raw = old['reading/inputs/sector-result.json']; result = load(result_raw); sealed(result,'result_hash')
    rd = reading['lanes']['sector']['last_qualified_result']['details']['result.json']
    require(len(result_raw) == rd['bytes'] and digest(result_raw) == rd['sha256'], 'same-R Sector result')
    stock = load(old['reading/stock-reading.json']); require(stock['projection_hash'] == canonical_hash(stock['projection']), 'Stock projection')
    stock = stock['projection']
    require(stock['sector_result_hash'] == result['result_hash'] and stock['market_session'] == result['market_session'] == '2026-09-30', 'comparator dates/lineage')
    # Use exact saved leader lists; this is a set census, not a replacement pool builder.
    breadths = [b for g in result['composition']['all_groups'] for b in [g['primary_breadth'],*g['granular_driver_breadth']] if b]
    leaders = sorted({r['thscode'] for b in breadths for r in b['leaders']})
    member_sets, old_quotes = {}, {}
    for r in audit['requests']:
        raw = load(old['market-context/input-audit/'+r['response_file']])
        if r['path'].endswith('/ths-stock-list'):
            codes = [v['thscode'] for v in raw['data']['item']]
            require(len(codes)==len(set(codes)), 'duplicate same-direction member')
            member_sets[r['params']['thscode']] = sorted(codes)
        elif r['path']=='/api/a-share/prices/snapshot':
            for q in raw['data']['item']:
                require(q['thscode'] not in old_quotes,'duplicate old quote')
                old_quotes[q['thscode']] = q
    union = set().union(*(set(v) for v in member_sets.values()))
    require(set(old_quotes) == set(quotes), 'source universe changed')
    quote_differences = [c for c in sorted(quotes) if any(not equal_number(quotes[c][k],old_quotes[c][k]) for k in ('last_price','prev_price'))]
    require(membership['projection_hash'] == canonical_hash(membership['projection']), 'membership projection')
    mp = membership['projection']; require(mp['market_session']=='2026-09-30' and mp['historical_membership']=='NOT_ESTABLISHED','membership time basis')
    require(len(mp['concepts'])==mp['catalog_count']==269 and sum(len(x['members']) for x in mp['concepts'])==mp['relation_count']==46632,'complete concept graph')
    comparisons = []
    for original in mp['concepts']:
        targets = sorted(set(selected).intersection(original['members']))
        if not targets: continue
        codes = original['members']; require(len(codes)==len(set(codes)),'duplicate concept member')
        panel = []
        for code in codes:
            q = quotes.get(code)
            value = frac(q) if q else None
            panel.append({'thscode':code,'name':mp['securities'][code]['name'],
              'last_price':q['last_price'] if q else None,'previous_price':q['prev_price'] if q else None,
              'quote_change':dec(value),'source_page_index':q['page_index'] if q else None,
              'source_row_position':q['row_position'] if q else None,
              'status':'NO_SNAPSHOT_IDENTITY' if q is None else 'UNPRICED' if value is None else 'QUOTE_ONLY_NOT_OWN_HISTORY_QUALIFIED'})
        values = [frac(quotes[c]) for c in codes if c in quotes and frac(quotes[c]) is not None]
        comparisons.append({'concept':original['code'],'name':original['name'],'members':len(codes),
          'priced_quotes':len(values),'unpriced':sum(p['status']=='UNPRICED' for p in panel),
          'absent_from_snapshot':sum(p['status']=='NO_SNAPSHOT_IDENTITY' for p in panel),
          'up':sum(v>0 for v in values),'flat':sum(v==0 for v in values),'down':sum(v<0 for v in values),
          'median_quote_change':dec(median(values)) if values else None,
          'targets':[{'thscode':c,'higher_quote_count':sum(v>frac(quotes[c]) for v in values),
             'equal_quote_count':sum(v==frac(quotes[c]) for v in values),
             'rank_among_priced_quotes':1+sum(v>frac(quotes[c]) for v in values)} for c in targets],
          'member_codes_hash':canonical_hash(codes),
          'quoted_member_codes_hash':canonical_hash([p['thscode'] for p in panel if p['quote_change'] is not None]),
          'unknown_member_codes':[p['thscode'] for p in panel if p['quote_change'] is None]})
    prior = {x['thscode']:x['status'] for x in stock['all_stock_observations']}
    cases = []
    for raw in obs['selected_observations']:
        c=raw['thscode']; path=raw['stock_path']
        history_record=next(r for r in raw['sources'] if r['path']=='/api/a-share/prices/historical')
        history=load(k3['independent-stock-capture/'+history_record['response_file']])['data']['item']
        cases.append({'thscode':c,'source_name':mp['securities'].get(c,{}).get('name'),
          'in_saved_sector_leaders':c in leaders,'in_captured_sector_members':c in union,
          'prior_stock_disposition':prior.get(c,'NOT_IN_THIS_CHECK_SCOPE'),
          'independent_disposition':raw['status'],'reason_code':raw['reason_code'],
          'input_failure':raw['input_failure'],'history_bar_count':len(history),
          'signed_snapshot_change':next(x['signed_quote_change'] for x in sel['selected'] if x['thscode']==c),
          'raw_returns':path['returns'] if path else None,
          'daily_raw_return':path['daily_raw_return'] if path else None,
          'twenty_day_return_five_sessions_ago':path['twenty_day_return_five_sessions_ago'] if path else None,
          'turnover_pulse_5_vs_prior_20':path['turnover_pulse_5_vs_prior_20'] if path else None,
          'raw_60d_status':path['input_checks']['action_window_checks']['60']['status'] if path else None,
          'raw_60d_reported_action_dates':path['input_checks']['action_window_checks']['60']['reported_event_dates'] if path else None,
          'source_response_paths':[r['response_file'] for r in raw['sources']],'same_source_concepts':[x['concept'] for x in comparisons if c in [t['thscode'] for t in x['targets']]]})
    body={'kind':'FROZEN_K3_COVERAGE_AND_CONTEMPORANEOUS_QUOTE_COMPARISON','version':1,
      'reading_commit':READING,'comparison_session':'2026-09-30','independent_capture_hash':CAPTURE,
      'independent_report_hash':REPORT,'selection_hash':sel['selection_hash'],'membership_hash':membership['projection_hash'],
      'source_coverage':obs['coverage'],'capture_request_count':len(cap['requests']),
      'sector_comparator':{'groups':len(result['composition']['all_groups']),'directions':len(breadths),
        'leader_count':len(leaders),'leaders':leaders,'captured_memberships':{c:{'count':len(v),'sorted_codes_hash':canonical_hash(v)} for c,v in member_sets.items()},'member_union_count':len(union),
        'scope':'THIS_RESULT_LEADERS_AND_11_CAPTURED_SETS_NOT_ALL_SECTORS_OR_LIFETIME_DISCOVERY'},
      'prior_stock_dispositions':prior,'snapshot_comparison':{'identities':len(quotes),'quote_pair_differences':quote_differences,
        'meaning':'LATER_ACQUISITION_NOT_A_NEW_TRADING_SESSION'},
      'cases':cases,'concept_comparisons':comparisons,
      'limits':{'member_time':mp['membership_time_basis'],'historical_membership':'NOT_ESTABLISHED',
        'all_member_5_20_60_roles':'NOT_ESTABLISHED','quote_rank':'CURRENT_STORED_QUOTE_ONLY_NOT_TRADE_DATE_OR_BUSINESS_LEADER',
        'all_c_acceptance':'NOT_ESTABLISHED','independent_research_value':'CASE_USE_SEPARATE_NOT_SELECTION_PASS_RATE',
        'source_qualification':'REUSES_RETAINED_691_CHECKS_NOT_A_FRESH_FULL_PROVIDER_REQUALIFICATION',
        'lossy_summary':'FULL_SELECTED_CONCEPTS_COMPUTED; RAW_ROWS_REMAIN_AT_PINNED_SOURCE',
        'source_requests':0,'new_model_jobs':0,'investment_authority':'NONE','watch_registration':False}}
    body['report_hash']=canonical_hash(body)
    return body

def main():
    k3_path,stock_path,member_path,root_path,out_path=map(Path,sys.argv[1:])
    k3=archive(k3_path,K3_SHA,347205);stock=archive(stock_path,STOCK_SHA,3449794)
    raw=member_path.read_bytes();require(digest(raw)==MEMBER_SHA and len(raw)==903923,'fixed membership bytes')
    report=build(k3,stock,load(raw),load(root_path.read_bytes()))
    encoded=(canonical_json(report)+'\n').encode(); require(len(encoded)<=512*1024,'derived bound')
    out_path.mkdir(exist_ok=False)
    with (out_path/'comparison.json').open('xb') as stream: stream.write(encoded)
    print(report['report_hash'],len(encoded))
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','concept_comparisons','sector_comparator')},ensure_ascii=False))
    print('sector',report['sector_comparator']['groups'],report['sector_comparator']['directions'],report['sector_comparator']['leader_count'],report['sector_comparator']['member_union_count'])
    print('concepts',json.dumps([{k:v for k,v in x.items() if k not in ('rows','quoted_member_codes')} for x in report['concept_comparisons']],ensure_ascii=False))
if __name__=='__main__':main()
