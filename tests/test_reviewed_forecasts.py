"""Synthetic engineering qualification is not real broker-model acceptance."""
from copy import deepcopy
import json

import pytest

from decision_kernel.runtime import research_comparison as c
from decision_kernel.runtime import current_state as state


def fixture(measure='TOTAL_PARENT_PROFIT', subject='999991.SZ'):
    target={'start':'2027-01-01','end':'2027-12-31','fiscal_basis':'CALENDAR_YEAR'}
    mb={'measure':measure,'attribution':'PARENT_ATTRIBUTABLE','adjustment':'REPORTED_ESTIMATE',
        'mapping_note':'Explicitly synthetic normalized model basis'}
    share=({'application':'NOT_APPLICABLE'} if measure=='TOTAL_PARENT_PROFIT' else
        {'application':'PER_SHARE','share_class':'ORDINARY','denominator':'DILUTED',
         'split_basis':'NO_SPLIT_REBASING','model_basis':'IDENTICAL_REVIEWED_DENOMINATOR'})
    records=[]
    for i in range(2):
        records.append({'institution_name':'Synthetic Broker A','institution_code':'001',
            'record_id':f'provider-{i}','original_report_id':f'broker-{i}','value_kind':'FORECAST',
            'report_date':f'2026-0{i+1}-01','target_period':deepcopy(target),'metric_label':measure,
            'metric_basis':deepcopy(mb),'currency':'CNY','scale_label':'1','share_basis':deepcopy(share),
            'value':'1.10' if i==0 else '1.40'})
    value={'version':c.VERSION,'subject':subject,'question':'SYNTHETIC forecast qualification only',
        'predecessor':'synthetic-fixture-not-real-research','analysis_cutoff':None,
        'reviewed_at':'2026-09-30T00:00:00Z','sources':[], 'observations':[], 'comparisons':[],
        'remaining_evidence':'Real broker source/model qualification is not provided by fixtures',
        'authority':deepcopy(c.AUTHORITY)}
    for i in range(2):
        rec=records[i]
        report={'namespace':'SYNTHETIC_PROVIDER','record_id':rec['record_id'],
            'original_report_id':rec['original_report_id'],'label_date':rec['report_date'],
            'date_qualification':'ORIGINAL_REPORT_DATE','source_id':'s','record_locator':{'pointer':f'/records/{i}'}}
        bindings={key:{'source_id':'s','locator':{'pointer':f'/records/{i}/{key}'}}
            for key in ('institution_name','institution_code','record_id','original_report_id','report_date',
                        'target_period','metric_label','metric_basis','currency','scale_label','share_basis','value_kind')}
        bindings['metric_basis']['transform']='METRIC_BASIS_FIELDS'
        forecast={'contract':c.FORECAST_CONTRACT,'value_kind':'FORECAST',
            'value_kind_basis':'Synthetic forecast field declared explicitly, not an actual fact',
            'institution':{'reviewed_key':'reviewed:synthetic-a','displayed_name':rec['institution_name'],
                'provider_code':rec['institution_code'],'identity_basis':'PROVIDER_ID','mapping_note':'Fixture provider code'},
            'report':report,'target_period':deepcopy(target),'metric_label':measure,'metric_basis':deepcopy(mb),
            'currency':'CNY','scale_label':'1','share_basis':deepcopy(share),'bindings':bindings,
            'limitations':'SYNTHETIC_FIXTURE; not original market or broker data'}
        value['observations'].append({'id':str(i),'subject':subject,'source_id':'s',
            'locator':{'pointer':f'/records/{i}/value'},'value':rec['value'],'type':'NUMBER','status':'KNOWN',
            'metric':measure,'scope':'PARENT_ATTRIBUTABLE','restatement':'SYNTHETIC_UNCHANGED_BASIS',
            'basis_note':'Explicit synthetic reviewed input','currency':'CNY','scale':'1',
            'period':{'kind':'FLOW','start':target['start'],'end':target['end']},'forecast':forecast})
    value['comparisons']=[{'id':'forecast','kind':'FORECAST_COMPARISON','operation':'forecast_difference',
        'terms':[{'observation':'0','sign':-1},{'observation':'1','sign':1}],
        'compatibility_note':'Synthetic target and basis qualification',
        'interpretation':'Mechanical change only, not model adequacy or investment authority',
        'challenge_disposition':'Explicit synthetic positive and refusal controls',
        'limitations':'Never a complete model revision certification'}]
    return value,records


def bind(v,records):
    raw=json.dumps({'records':records},ensure_ascii=False,separators=(',',':')).encode()
    v['sources']=[{'id':'s','subject':v['subject'],'ref':'a'*40,'path':'docs/readings/synthetic/source.json',
        'git_blob':state.blob_sha(raw),'sha256':state.sha256(raw),'bytes':len(raw),
        'identity_basis':'SYNTHETIC source identity only','qualification':'SYNTHETIC_FIXTURE',
        'acquired_at':None,'published_at':None}]
    return {'s':raw}


def result(v,records):
    return c.build(v,bind(v,records))['comparisons'][0]['result']


@pytest.mark.parametrize('measure,subject,unit',[('TOTAL_PARENT_PROFIT','999991.SZ','CNY'),('EPS','999992.SZ','CNY/share')])
def test_two_synthetic_issuers_and_correct_units(measure,subject,unit):
    v,r=fixture(measure,subject);out=result(v,r)
    assert out['value']=='0.30' and out['unit']==unit
    assert out['relation']=='SAME_INSTITUTION_FORECAST_VINTAGE_CHANGE'
    assert out['source_qualifications']==['SYNTHETIC_FIXTURE']*2
    assert out['full_model_revision']=='NOT_CERTIFIED'


def test_currency_scale_conversion_and_total_denominator_not_applicable():
    v,r=fixture();r[0]['scale_label']='万元';v['observations'][0]['scale']='10000';v['observations'][0]['forecast']['scale_label']='万元'
    assert result(v,r)['value']=='-10998.60'
    v['observations'][0]['forecast']['share_basis']=None
    assert result(v,r)['status']=='NOT_COMPARABLE'


def test_duplicate_not_new_forecast_and_variant_not_new_report():
    v,r=fixture();r[1]=deepcopy(r[0]);f=v['observations'][1]['forecast']
    f['report'].update(record_id=r[1]['record_id'],original_report_id=r[1]['original_report_id'],label_date=r[1]['report_date'])
    v['observations'][1]['value']=r[1]['value']
    out=result(v,r);assert out['status']=='DUPLICATE_NOT_NEW_FORECAST' and out['value'] is None
    r[1]['value']='1.50';v['observations'][1]['value']='1.50'
    out=result(v,r);assert out['relation']=='SAME_RECORD_CONTENT_VARIANT_NOT_NEW_REPORT' and out['value']=='0.40'


def test_different_provider_codes_are_disagreement_not_revision():
    v,r=fixture();r[1]['institution_code']='002';r[1]['institution_name']='Synthetic Broker B'
    v['observations'][1]['forecast']['institution'].update(provider_code='002',displayed_name='Synthetic Broker B')
    out=result(v,r);assert out['relation']=='CROSS_INSTITUTION_ATTRIBUTION_NOT_REVISION' and out['value']=='0.30'


def test_different_names_or_provider_namespaces_do_not_prove_different_entities():
    v,r=fixture();v['observations'][1]['forecast']['report']['namespace']='OTHER_PROVIDER'
    out=result(v,r);assert out['relation']=='IDENTITY_UNRESOLVED' and out['status']=='NOT_COMPARABLE'
    v,r=fixture()
    for o in v['observations']:o['forecast']['institution']['identity_basis']='EXACT_DISPLAYED_NAME'
    r[1]['institution_name']='Synthetic Broker A short alias';v['observations'][1]['forecast']['institution']['displayed_name']=r[1]['institution_name']
    assert result(v,r)['relation']=='IDENTITY_UNRESOLVED'


def test_unknown_fiscal_target_is_not_invented_from_current_year():
    v,r=fixture('EPS');o=v['observations'][1];o['period']=None;o['forecast']['target_period']=None
    out=result(v,r);assert out['status']=='NOT_COMPARABLE' and 'new:target_period:UNKNOWN' in out['blockers']
    assert out['value'] is None


def test_different_targets_not_a_revision_even_under_one_report():
    v,r=fixture();target={'start':'2028-01-01','end':'2028-12-31','fiscal_basis':'CALENDAR_YEAR'}
    r[1]['target_period']=target;v['observations'][1]['forecast']['target_period']=target
    v['observations'][1]['period']={'kind':'FLOW','start':target['start'],'end':target['end']}
    out=result(v,r);assert out['relation']=='DIFFERENT_FORECAST_HORIZON' and out['value'] is None


@pytest.mark.parametrize('key,value',[('denominator','BASIC'),('split_basis','TWO_FOR_ONE'),('model_basis','UNKNOWN')])
def test_eps_basis_differences_or_unknown_refuse(key,value):
    v,r=fixture('EPS');r[1]['share_basis'][key]=value;v['observations'][1]['forecast']['share_basis'][key]=value
    out=result(v,r);assert out['status']=='NOT_COMPARABLE' and out['value'] is None


def test_claimed_currency_or_metric_basis_requires_bound_source_fact():
    v,r=fixture();v['observations'][1]['forecast']['currency']='USD';v['observations'][1]['currency']='USD'
    assert 'new:currency:SOURCE_BINDING_INVALID' in result(v,r)['blockers']
    v,r=fixture();v['observations'][1]['forecast']['bindings'].pop('metric_basis')
    assert 'new:metric_basis:SOURCE_BINDING_MISSING' in result(v,r)['blockers']


def test_source_bindings_cannot_take_identity_or_target_from_another_row():
    v,r=fixture();v['observations'][1]['forecast']['bindings']['institution_code']['locator']['pointer']='/records/0/institution_code'
    out=result(v,r);assert out['relation']=='IDENTITY_UNRESOLVED' and out['status']=='NOT_COMPARABLE'


def test_same_day_distinct_records_not_temporally_ordered():
    v,r=fixture();r[1]['report_date']=r[0]['report_date'];v['observations'][1]['forecast']['report']['label_date']=r[0]['report_date']
    out=result(v,r);assert out['relation']=='DISTINCT_RECORDS_NOT_TEMPORALLY_ORDERED'


def test_actual_values_and_future_report_dates_do_not_become_forecast_revision():
    v,r=fixture();v['observations'][1]['forecast']['value_kind']='REPORTED_ACTUAL'
    assert 'new:NOT_A_FORECAST' in result(v,r)['blockers']
    v,r=fixture();r[1]['report_date']='2030-01-01';v['observations'][1]['forecast']['report']['label_date']='2030-01-01'
    assert result(v,r)['status']=='NOT_COMPARABLE'


def test_original_report_identity_absent_is_not_fabricated():
    v,r=fixture()
    for o in v['observations']:o['forecast']['report']['original_report_id']=None
    out=result(v,r);assert out['relation']=='DISTINCT_PROVIDER_RECORDS_ORIGINAL_VINTAGE_UNESTABLISHED'
    assert out['original_broker_identity']=='NOT_ESTABLISHED'


def test_forecast_cannot_bypass_qualification_through_old_difference():
    v,r=fixture();v['comparisons'][0].update(kind='SOURCE_REVISION',operation='difference')
    with pytest.raises(ValueError,match='qualification path'):result(v,r)


def test_explicit_currency_alias_not_amount_scale_or_exchange_inference():
    v,r=fixture()
    for i in range(2):
        r[i]['currency']='人民币';v['observations'][i]['forecast']['bindings']['currency']['transform']='CURRENCY_ISO'
    assert result(v,r)['unit']=='CNY'
    r[1]['currency']='亿元'
    assert 'new:currency:SOURCE_BINDING_INVALID' in result(v,r)['blockers']


def test_text_record_cannot_bind_json_pointers_outside_its_scope():
    v,r=fixture();v['observations'][1]['forecast']['report']['record_locator']={'quote':'Synthetic Broker A'}
    out=result(v,r)
    assert out['status']=='NOT_COMPARABLE' and 'new:REPORT_RECORD_BINDING_INVALID' in out['blockers']


def test_mixed_report_and_fact_locator_modes_cannot_bypass_row_scope():
    v,r=fixture();r[0]['institution_code']='002';v['observations'][0]['forecast']['institution']['provider_code']='002'
    f=v['observations'][1]['forecast'];f['institution']['provider_code']='002'
    f['bindings']['institution_code']['locator']={'pointer':'/records/1/institution_code','quote':'002'}
    out=result(v,r);assert out['status']=='NOT_COMPARABLE'
    assert 'new:institution_code:SOURCE_BINDING_INVALID' in out['blockers']
    v,r=fixture();v['observations'][1]['forecast']['report']['record_locator'].update(quote='Synthetic Broker A')
    assert 'new:REPORT_RECORD_BINDING_INVALID' in result(v,r)['blockers']


@pytest.mark.parametrize('measure,label,scale',[('EPS','万元','10000'),('TOTAL_PARENT_PROFIT','元/股','1')])
def test_bound_unit_label_must_match_measurement_dimension(measure,label,scale):
    v,r=fixture(measure)
    for i in range(2):
        r[i]['scale_label']=label;v['observations'][i]['scale']=scale;v['observations'][i]['forecast']['scale_label']=label
    out=result(v,r);assert out['status']=='NOT_COMPARABLE' and out['value'] is None


@pytest.mark.parametrize('unknown',[' UNKNOWN ','   ',' not_established '])
def test_whitespace_unknown_basis_cannot_be_qualified(unknown):
    v,r=fixture();r[1]['metric_basis']['adjustment']=unknown;v['observations'][1]['forecast']['metric_basis']['adjustment']=unknown
    assert result(v,r)['status']=='NOT_COMPARABLE'


def test_tomorrow_label_without_qualified_clock_is_not_permitted_by_tolerance():
    v,r=fixture();r[1]['report_date']='2026-10-01';v['observations'][1]['forecast']['report']['label_date']='2026-10-01'
    assert 'new:REPORT_DATE_AFTER_REVIEWED_AT' in result(v,r)['blockers']


def test_provider_dates_cannot_establish_original_broker_vintage_order():
    v,r=fixture()
    for o in v['observations']:o['forecast']['report']['date_qualification']='PROVIDER_DATE_ONLY'
    out=result(v,r);assert out['relation']=='DISTINCT_PROVIDER_RECORDS_ORIGINAL_VINTAGE_UNESTABLISHED'
    assert out['original_broker_identity']=='ESTABLISHED_BY_SUPPLIED_BINDINGS'


@pytest.mark.parametrize('case,relation',[('accelink','DISTINCT_PROVIDER_RECORDS_ORIGINAL_VINTAGE_UNESTABLISHED'),('xingsen','CROSS_INSTITUTION_ATTRIBUTION_NOT_REVISION')])
def test_real_retained_cases_remain_numeric_refusals(case,relation):
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'docs/readings/c-reviewed-forecast-boundaries-2026-09-30'
    v=json.loads((root/(case+'-input.json')).read_text())
    report=c.build(v,{'s':(root/(case+'-source.json')).read_bytes()})
    assert report==json.loads((root/(case+'-report.json')).read_text())
    assert c.render(report)==(root/(case+'-report.md')).read_text()
    r=report['comparisons'][0]['result']
    assert r['relation']==relation and r['status']=='NOT_COMPARABLE' and r['value'] is None
    assert 'SYNTHETIC_FIXTURE' not in r['source_qualifications']
    if case=='accelink':assert not any('SHARE' in b for b in r['blockers'])
    else:assert 'new:PER_SHARE_BASIS_UNQUALIFIED' in r['blockers']


@pytest.mark.parametrize('case,prefix',[('accelink','a'),('xingsen','x')])
def test_published_legacy_semantic_report_hashes_and_markdown_unchanged(case,prefix):
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'docs/readings/c-cash-bridge-semantic-review-2026-09-30'
    v=json.loads((root/(case+'-input.json')).read_text())
    files={s['id']:(root/(prefix+'-'+s['id']+'-'+Path(s['path']).name)).read_bytes() for s in v['sources']}
    report=c.build(v,files)
    assert report==json.loads((root/(case+'-report.json')).read_text())
    assert c.render(report)==(root/(case+'-report.md')).read_text()


def test_report_locator_cannot_select_multi_record_list_or_dictionary_container():
    v,r=fixture();f=v['observations'][1]['forecast'];f['report']['record_locator']={'pointer':'/records'}
    f['bindings']['institution_code']['locator']={'pointer':'/records/0/institution_code'}
    assert 'new:REPORT_RECORD_BINDING_INVALID' in result(v,r)['blockers']
    v,r=fixture();files=bind(v,r);raw=json.dumps({'wrapper':{'old':r[0],'new':r[1]}}).encode()
    src=v['sources'][0];src.update(git_blob=state.blob_sha(raw),sha256=state.sha256(raw),bytes=len(raw))
    for i,o in enumerate(v['observations']):
        o['locator']={'pointer':'/wrapper/'+('old' if i==0 else 'new')+'/value'}
        o['forecast']['report']['record_locator']={'pointer':'/wrapper'}
    out=c.build(v,{'s':raw})['comparisons'][0]['result']
    assert out['status']=='NOT_COMPARABLE' and out['value'] is None


def test_same_provider_record_with_changed_institution_is_not_cross_broker_pair():
    v,r=fixture();r[1]['record_id']=r[0]['record_id'];r[1]['institution_code']='002';r[1]['institution_name']='Corrected Broker'
    f=v['observations'][1]['forecast'];f['report']['record_id']=r[1]['record_id'];f['institution'].update(provider_code='002',displayed_name='Corrected Broker')
    out=result(v,r);assert out['relation']=='SAME_RECORD_IDENTITY_CONFLICT_OR_CORRECTION'
    assert out['status']=='NOT_COMPARABLE' and out['value'] is None


def test_provider_code_claim_requires_binding_even_when_name_basis_is_used():
    v,r=fixture()
    for o in v['observations']:o['forecast']['institution']['identity_basis']='EXACT_DISPLAYED_NAME'
    v['observations'][1]['forecast']['institution']['provider_code']='unbound-official-id'
    out=result(v,r);assert out['status']=='NOT_COMPARABLE'
    assert 'new:institution_code:SOURCE_BINDING_INVALID' in out['blockers']


def test_forecast_role_is_bound_and_cannot_relabel_actual_source_value():
    v,r=fixture();r[1]['value_kind']='REPORTED_ACTUAL'
    assert 'new:value_kind:SOURCE_BINDING_INVALID' in result(v,r)['blockers']


def test_missing_forecast_value_is_unknown_not_zero():
    v,r=fixture();r[1]['value']=None
    v['observations'][1].update(status='UNKNOWN',value=None,missing_reason='Not reported')
    out=result(v,r);assert out['value'] is None and 'FORECAST_VALUE_UNKNOWN' in out['blockers']


def test_reviewed_alias_requires_meaningful_mapping_rationale():
    v,r=fixture();f=v['observations'][1]['forecast']['institution']
    f.update(identity_basis='REVIEWED_ALIAS',mapping_note='   ')
    out=result(v,r);assert 'new:ALIAS_MAPPING_RATIONALE_UNKNOWN' in out['blockers']


def test_forecast_field_role_cannot_borrow_a_sibling_forecast_value():
    v,r=fixture();r[1]['value_kind']='REPORTED_ACTUAL';r[1]['forecast_values']=['99']
    v['observations'][1]['forecast']['bindings']['value_kind']={'source_id':'s',
        'locator':{'pointer':'/records/1/forecast_values/0'},'transform':'FORECAST_FIELD'}
    out=result(v,r);assert out['status']=='NOT_COMPARABLE'
    assert 'new:value_kind:SOURCE_BINDING_INVALID' in out['blockers']


@pytest.mark.parametrize('namespace',['UNKNOWN','   ',' NOT_ESTABLISHED '])
def test_unknown_report_namespace_cannot_qualify_under_displayed_name_basis(namespace):
    v,r=fixture()
    for o in v['observations']:
        o['forecast']['institution']['identity_basis']='EXACT_DISPLAYED_NAME'
        o['forecast']['report']['namespace']=namespace
    out=result(v,r);assert out['status']=='NOT_COMPARABLE' and out['value'] is None
    assert 'new:REPORT_NAMESPACE_UNKNOWN' in out['blockers']
