"""Reviewed comparison mechanics are separate from source/economic authority."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from decision_kernel.runtime import research_comparison as c
from decision_kernel.runtime import current_state as state


def sample(subject='002281.SZ'):
    raw=b'{"prior":1.10,"current":2.20,"unknown":"not checked","claim":"unchanged"}'
    s={'id':'s','subject':subject,'ref':'a'*40,'path':'docs/readings/case/source.json',
       'git_blob':state.blob_sha(raw),'sha256':state.sha256(raw),'bytes':len(raw),
       'identity_basis':'Explicit reviewed issuer assignment, not automatic filing identification',
       'qualification':'RETAINED_RESEARCH','acquired_at':None,'published_at':None}
    observations=[]
    for name,year,val in [('old','2025','1.10'),('new','2026','2.20')]:
        observations.append({'id':name,'subject':subject,'status':'KNOWN','type':'NUMBER',
           'source_id':'s','locator':{'pointer':'/prior' if name=='old' else '/current'},
           'value':val,'metric':'cfo','scope':'CONSOLIDATED','restatement':'AS_REPORTED',
           'basis_note':'same disclosed currency/scope/seasonal period', 'currency':'CNY','scale':'1',
           'period':{'kind':'FLOW','start':year+'-01-01','end':year+'-06-30'}})
    comparison={'id':'cash-change','kind':'PERIOD_CHANGE','operation':'difference',
        'terms':[{'observation':'old','sign':-1},{'observation':'new','sign':1}],
        'compatibility_note':'same seasonal period, as reported',
        'interpretation':'Reviewed cash change; not owner earnings',
        'challenge_disposition':'Alternative seasonality explanation remains incomplete',
        'limitations':'Retained research, issuer original bytes not recovered'}
    return {'version':c.VERSION,'subject':subject,'question':'Has cash conversion changed?',
        'predecessor':'https://github.com/owner/repo/blob/'+ 'a'*40 +'/old.md',
        'analysis_cutoff':None,'reviewed_at':'2026-09-30T00:00:00Z',
        'sources':[s],'observations':observations,'comparisons':[comparison],
        'remaining_evidence':'Future cash realization and full original-source audit',
        'authority':deepcopy(c.AUTHORITY)}, {'s':raw}


def result(v,files):
    return c.build(v,files)['comparisons'][0]['result']


@pytest.mark.parametrize('subject',['002281.SZ','002436.SZ'])
def test_same_consumer_and_no_new_event_on_duplicate(subject):
    v,f=sample(subject);a=c.build(v,f);b=c.build(v,f)
    assert a==b and result(v,f)['value']=='1.10'
    assert a['authority']==c.AUTHORITY
    assert a['sources'][0]['qualification']=='RETAINED_RESEARCH'


@pytest.mark.parametrize('change',[{'scope':'PARENT'},{'currency':'USD'},
    {'subject':'002436.SZ'},{'restatement':'RESTATED'},
    {'period':{'kind':'FLOW','start':'2026-01-01','end':'2026-03-31'}},
    {'period':{'kind':'STOCK','start':None,'end':'2026-06-30'}}])
def test_incompatible_basis_is_not_arithmetic(change):
    v,f=sample();v['observations'][1].update(change)
    with pytest.raises(ValueError):c.build(v,f)


@pytest.mark.parametrize('key,value',[('ref','main'),('git_blob','b'*40),('sha256','b'*64),
    ('bytes',99),('subject','002436.SZ')])
def test_source_identity_tampering_rejected(key,value):
    v,f=sample();v['sources'][0][key]=value
    with pytest.raises(ValueError):c.build(v,f)


def test_partial_missing_source_not_zero_or_global_success():
    v,f=sample();r=c.build(v,{})
    assert r['source_gaps']==['s']
    assert r['comparisons'][0]['result']=={'status':'SOURCE_BYTES_UNAVAILABLE','value':None}
    assert all(o['value'] is None for o in r['observations'])


def test_missing_to_known_is_coverage_not_growth():
    v,f=sample();old,new=v['observations'];old.update(status='UNKNOWN',value=None,
        missing_reason='not previously verified',locator={'pointer':'/unknown'},period=deepcopy(new['period']))
    v['comparisons'][0].update(kind='EVIDENCE_COVERAGE_CHANGE',operation='coverage')
    assert result(v,f)['value'] is None
    assert result(v,f)['meaning']=='NOT_ZERO_BASED_GROWTH_OR_NEW_COMPANY_EVENT'
    old['value']='0'
    with pytest.raises(ValueError):c.build(v,f)


def test_difference_cannot_disguise_coverage_as_revision():
    v,f=sample();v['comparisons'][0]['kind']='SOURCE_REVISION'
    with pytest.raises(ValueError,match='period'):c.build(v,f)


def test_scale_normalization_and_exact_lexemes():
    v,f=sample();v['observations'][0]['scale']='10000';v['observations'][1]['scale']='100000000'
    assert result(v,f)['value']=='219989000.00'
    assert c.parse(b'{"x":0.100000000000000001}')['x']==c.Decimal('0.100000000000000001')
    for raw in [b'{"x":1,"x":2}', b'{"x":NaN}']:
        with pytest.raises(ValueError):c.parse(raw)


def test_quarter_checks_cumulative_boundaries():
    v,f=sample();old,new=v['observations'];old['period']={'kind':'FLOW','start':'2026-01-01','end':'2026-03-31'}
    v['comparisons'][0].update(operation='quarter',kind='DERIVED_QUARTER')
    assert result(v,f)['value']=='1.10'
    old['period']['start']='2025-10-01'
    with pytest.raises(ValueError):c.build(v,f)


def test_cash_diagnostic_not_automatic_owner_earnings():
    v,f=sample();old,new=v['observations'];old['period']=deepcopy(new['period']);old['metric']='capex'
    v['comparisons'][0].update(kind='CASH_DIAGNOSTIC',operation='signed_sum')
    assert result(v,f)['value']=='1.10'
    v['comparisons'][0]['kind']='PERIOD_CHANGE'
    with pytest.raises(ValueError):c.build(v,f)


def test_unknown_value_is_gap_and_zero_denominator_is_different():
    v,f=sample();v['observations'][0].update(status='UNKNOWN',value=None,
        locator={'pointer':'/unknown'},missing_reason='not checked')
    assert result(v,f)['status']=='EVIDENCE_GAP'
    v,f=sample();v['observations'][0]['period']=deepcopy(v['observations'][1]['period'])
    v['observations'][0]['value']='0';v['observations'][0]['locator']={'quote':'"unknown"'}
    # A claimed zero absent from its quote must fail, not become known zero.
    with pytest.raises(ValueError):c.build(v,f)


def test_claim_unchanged_and_quote_identity():
    v,f=sample();old,new=v['observations'];old['period']=deepcopy(new['period'])
    for o in [old,new]:o.update(type='CLAIM',value='unchanged',locator={'pointer':'/claim'})
    v['comparisons'][0].update(kind='CHECKED_UNCHANGED',operation='claim')
    assert result(v,f)['status']=='UNCHANGED'
    new['locator']={'quote':'not present'}
    with pytest.raises(ValueError):c.build(v,f)


def test_unchecked_does_not_assert_no_change():
    v,f=sample();v['comparisons'][0].update(kind='NOT_CHECKED',operation='claim')
    assert result(v,f)=={'status':'NOT_CHECKED','value':None}


def test_render_escapes_source_instructions_and_no_authority_promotion():
    v,f=sample();v['question']='<script>run()</script>';r=c.build(v,f)
    assert '<script>' not in c.render(r) and '&lt;script&gt;' in c.render(r)
    v['authority']['investment_authority']='BUY'
    with pytest.raises(ValueError):c.build(v,f)


def test_pinned_file_cli_and_exclusive_output(tmp_path):
    v,f=sample();p=tmp_path/'input.json';raw=json.dumps(v).encode();p.write_bytes(raw)
    s=tmp_path/'source.json';s.write_bytes(f['s']);out=tmp_path/'output'
    args=[sys.executable,'-m','decision_kernel.runtime.research_comparison',str(p),
          '--sha256',state.sha256(raw),'--source','s='+str(s),'--output',str(out)]
    assert subprocess.run(args,capture_output=True).returncode==0
    assert json.loads((out/'comparison.json').read_text())['authority']==c.AUTHORITY
    assert subprocess.run(args,capture_output=True).returncode!=0
    with pytest.raises(ValueError):c.read_comparison(p,expected_sha256='0'*64,source_files=f)


@pytest.mark.parametrize('token',['1','10','-1'])
def test_quote_numeric_substring_is_not_value_binding(token):
    v,f=sample();raw=b'{"line":"amount -11.10"}';s=v['sources'][0]
    s.update(git_blob=state.blob_sha(raw),sha256=state.sha256(raw),bytes=len(raw));f={'s':raw}
    for o in v['observations']:o.update(value=token,locator={'quote':'amount -11.10'})
    with pytest.raises(ValueError,match='numeric token'):c.build(v,f)


def test_published_after_cutoff_and_future_acquisition_rejected():
    v,f=sample();v['analysis_cutoff']='2026-09-01T00:00:00Z';v['sources'][0]['published_at']='2026-09-02T00:00:00Z'
    with pytest.raises(ValueError,match='after cutoff'):c.build(v,f)
    v['sources'][0]['published_at']='2026-08-01T00:00:00Z';v['sources'][0]['acquired_at']='2026-10-01T00:00:00Z'
    with pytest.raises(ValueError,match='after review'):c.build(v,f)
    v['sources'][0]['acquired_at']='2026-09-29T00:00:00Z'
    assert c.build(v,f)['historical_knowledge']=='NOT_ESTABLISHED_BY_RETRIEVAL_CLOCK'


def test_multiyear_flow_cannot_masquerade_as_same_h1_window():
    v,f=sample();v['observations'][0]['period']['start']='2020-01-01'
    with pytest.raises(ValueError,match='year span'):c.build(v,f)
    v,f=sample();v['observations'][0]['period']['start']='20250101'
    with pytest.raises(ValueError,match='canonical'):c.build(v,f)


@pytest.mark.parametrize('quote,value',[('amount 1e6','1'),('amount −11.10','11.10'),
                                        ('amount (11.10)','11.10')])
def test_ambiguous_text_numeric_lexemes_rejected(quote,value):
    v,f=sample();raw=json.dumps({'line':quote},ensure_ascii=False).encode();s=v['sources'][0]
    s.update(git_blob=state.blob_sha(raw),sha256=state.sha256(raw),bytes=len(raw));f={'s':raw}
    for o in v['observations']:o.update(value=value,locator={'quote':quote})
    with pytest.raises(ValueError,match='numeric token'):c.build(v,f)


def test_actual_zero_ratio_and_missing_currency():
    v,f=sample();raw=b'{"prior":1.10,"current":0}';s=v['sources'][0]
    s.update(git_blob=state.blob_sha(raw),sha256=state.sha256(raw),bytes=len(raw));f={'s':raw}
    v['observations'][0]['period']=deepcopy(v['observations'][1]['period']);v['observations'][1]['value']='0'
    v['comparisons'][0].update(operation='ratio',kind='CASH_DIAGNOSTIC',
        terms=[{'observation':'old','sign':1},{'observation':'new','sign':1}])
    assert result(v,f)=={'status':'ZERO_DENOMINATOR','value':None}
    for o in v['observations']:o['currency']='NONE'
    with pytest.raises(ValueError,match='currency'):c.build(v,f)


@pytest.mark.parametrize('case,expected',[
 ('accelink',{'profit-change':'209809951.21','cfo-change':'-1128815703.73',
              'capex-change':'277159481.72','h1-cash-after-capex':'-1836537487.14'}),
 ('xingsen',{'q2-cfo':'249948242.60','q2-capex':'465013525.85','q2-refund':'306692108.30',
             'h1-cash-after-capex':'-723189558.44','historical-cfo-reused':'0.0000'})])
def test_real_two_company_artifacts_replay_same_generic_consumer(case,expected):
    root=Path(__file__).resolve().parents[1]/'docs/readings'/f'c-longitudinal-{case}-2026-09-30'
    v=json.loads((root/'input.json').read_text());files={}
    for s in v['sources']:
        files[s['id']]=(root/(s['id']+'-'+Path(s['path']).name)).read_bytes()
    report=c.build(v,files)
    assert report==json.loads((root/'comparison.json').read_text())
    values={x['id']:x['result']['value'] for x in report['comparisons']}
    for k,val in expected.items():assert values[k]==val
    assert all(x['qualification']=='RETAINED_RESEARCH' for x in report['sources'])
    if case=='xingsen':
        assert report['comparisons'][0]['result']['status']=='EVIDENCE_COVERAGE_CHANGE'
        assert report['comparisons'][-1]['result']['status']=='NOT_CHECKED'
    else:
        assert 'METHOD-READY' in files['review'].decode()
        assert '1236139694.4100003' in files['calc'].decode()  # Original float tail retained, not executed.


def test_caller_decimal_rounding_and_traps_do_not_change_output():
    from decimal import localcontext, ROUND_UP, Inexact
    v,f=sample();raw=b'{"prior":1,"current":3}';s=v['sources'][0]
    s.update(git_blob=state.blob_sha(raw),sha256=state.sha256(raw),bytes=len(raw));f={'s':raw}
    v['observations'][0].update(value='1',period=deepcopy(v['observations'][1]['period']))
    v['observations'][1]['value']='3'
    v['comparisons'][0].update(kind='CASH_DIAGNOSTIC',operation='ratio',
      terms=[{'observation':'old','sign':1},{'observation':'new','sign':1}])
    expected=c.build(v,f)
    with localcontext() as ctx:
        ctx.rounding=ROUND_UP;ctx.prec=3;ctx.traps[Inexact]=True
        assert c.build(v,f)==expected
    assert 'ratio' in c.render(expected)
    v,f=sample();assert 'CNY' in c.render(c.build(v,f))


def test_real_comparisons_use_existing_on_demand_owner_without_eager_growth():
    from decision_kernel.runtime.research_archive_index import split, validate
    root=Path(__file__).resolve().parents[1]
    registry=json.loads((root/'current_state/registry.json').read_text())
    eager,archives,gaps=split(registry)
    assert not gaps and len(eager['references'])==51
    for case in ['accelink','xingsen']:
        row=next(x for x in archives if x['id']==f'c-longitudinal-{case}-20260930')
        validate(row)
        assert row['use']=='RETAINED_RESEARCH_DOCUMENT'
        assert row['archive']=={'format':'RETAINED_FILES'}
        assert row['body_materialized_in_reading'] is False
        raw=(root/row['source']['path']).read_bytes()
        assert state.sha256(raw)==row['source']['sha256']
        assert state.blob_sha(raw)==row['source']['git_blob']
        assert row['source']['ref']=='83a40bfb408090015678d98bd192489db9226c3a'
