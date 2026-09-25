"""Synthetic, network-prohibited regression of the real Stock page/capture path."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import runpy
import shutil

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_discovery_page as page
from decision_kernel.runtime import stock_market_expression as market
from decision_kernel.runtime import stock_radar_reading as stock
from decision_kernel.runtime import radar_stock_candidates as pool
from decision_kernel.runtime import hithink_stock_reading as own
from decision_kernel.runtime.sector_parent_hints import load_sector_parent_hints
from decision_kernel.runtime.sector_radar_persistence import write_sector_radar_persistent_bundle
from test_stock_radar_reading import _prepared_upstream, _stock_response, ROOT, NOW
from test_stock_market_expression import _active_rows, _group, _leader, _sector_result
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def setup(shown=0):
    state, ledger, frozen_association = _prepared_upstream()
    association = deepcopy(frozen_association)
    # Discovery owns its plan below; do not build an unrelated Stock-first plan.
    base, calls = _stock_response(state, ())
    groups = [_group(state, family, row, leaders=[_leader(f'600{n:03d}.SH', f'Synthetic {n}')
              for n in range(i*5, i*5+5)]) for i, (family, row) in enumerate(_active_rows(state, ledger)[:3])]
    result = _sector_result(state, ledger, groups=groups)
    c = result['composition']; c['surfaced_groups'] = deepcopy(c['all_groups'][:shown])
    c['omitted_groups'] = deepcopy(c['all_groups'][shown:]); c['truncated_group_count'] = len(c['omitted_groups'])
    result['result_hash'] = canonical_hash({k:v for k,v in result.items() if k != 'result_hash'})
    selection = {'pool_hash': pool.build_stock_discovery_pool(result)['pool_hash'], 'offset': 0}
    histories = {}
    def provider(path, params):
        if path == own.SNAPSHOT:
            calls.append((path,params)); code=params['thscodes']; bars=histories[code]['data']['item']; last=bars[-1]
            return {'code':0,'data':{'timestamp':None,'total':5000,'item':[{
                'thscode':code,'ticker':code[:6],'last_price':last['close_price'], 'prev_price':bars[-2]['close_price'],
                **{k:last[k] for k in ('open_price','high_price','low_price','volume','turnover')}}]}}
        if path == own.ACTIONS:
            calls.append((path,params)); return {'code':0,'data':{'thscode':params['thscode'],'ticker':params['thscode'][:6],'item':[]}}
        response = base(path,params)
        if path == stock.members.HITHINK_SECTOR_CONSTITUENTS_PATH:
            response['data']['item'] = [{'thscode':f'600{n:03d}.SH','ticker':f'600{n:03d}','name':f'Synthetic {n}'}
                                       for n in range(15)]
        elif path == own.HISTORY:
            response['data']['timestamp'] = int(NOW.timestamp()*1000)
            for bar in response['data']['item']:
                bar.update(open_price=bar['close_price'],high_price=bar['close_price'],low_price=bar['close_price'])
            histories[params['thscode']] = deepcopy(response)
        return response
    return state, ledger, association, result, selection, provider, calls


def capture_setup(tmp_path, *, transport_change=None, shown=0, offset=0, public_path=False):
    state, ledger, association, result, selection, provider, calls = setup(shown)
    selection['offset'] = offset
    mod = runpy.run_path(str(ROOT/'.github/scripts/capture-stock-reading.py'))
    state_dir = tmp_path/'state'
    hints=load_sector_parent_hints(ROOT/'radar_inputs/sector-parent-hints-2026-09-05.json')
    write_sector_radar_persistent_bundle(state_dir,market_state=state,event_ledger=ledger,
        created_at=NOW,updated_at=NOW,source_repository='auguspp/decision-kernel',
        source_workflow='.github/workflows/sector-radar-shadow.yml',source_run_id=101,
        source_run_attempt=1,source_commit_sha='b'*40,parent_hint_mapping_hash=hints.mapping_hash,
        last_result_hash=None,last_operation_status='VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT')
    out=tmp_path/'reading'; clock=iter(NOW+timedelta(seconds=i*21) for i in range(100))
    wf = {'GITHUB_RUN_ID':'202','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'c'*40,
          'GITHUB_REPOSITORY':'auguspp/decision-kernel','GITHUB_REF':'refs/heads/main',
          'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_WORKFLOW':'hithink-stock-dump-trial'}
    before = mod['inventory'](state_dir)
    observed = mod['capture'](ROOT,state_dir,out,observed_at=NOW,workflow=wf,
        provenance=mod['PUBLIC'] if public_path else mod['SYNTHETIC'], credential='synthetic-no-network', transport=transport_change(provider) if transport_change else provider,
        now=lambda:next(clock),pause=lambda _:None,sector_result=result,
        sector_result_raw=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode(), discovery_page=selection)
    assert mod['inventory'](state_dir) == before
    return mod, out, observed, result, selection, calls


@pytest.fixture(scope='module')
def complete_page_capture_baseline(tmp_path_factory):
    """One real successful default page capture retained only as immutable test input."""
    blocker=pytest.MonkeyPatch()
    prohibit_network(blocker)
    try:
        root=tmp_path_factory.mktemp('stock-discovery-page-baseline')
        mod,out,capture,_,_,_=capture_setup(root)
        assert capture['status']==mod['COMPLETE']
        assert mod['verify'](out)['network_calls']==0
        return out
    finally:
        blocker.undo()


@pytest.fixture
def complete_page_capture_copy(tmp_path,complete_page_capture_baseline):
    """Private retained bytes for one tamper; original verify still runs per case."""
    out=tmp_path/'reading'
    shutil.copytree(complete_page_capture_baseline,out)
    mod=runpy.run_path(str(ROOT/'.github/scripts/capture-stock-reading.py'))
    return mod,out


@pytest.mark.parametrize('value', ['latest:0', 'a'*64+':-1','a'*64+':01','a'*64+':1.0','A'*64+':1',' '+ 'a'*64+':0',None,True])
def test_bad_selector_never_enters_a_plan(value):
    with pytest.raises(ValueError): page.parse_selection(value)


def test_default_and_explicit_selector_are_distinct():
    assert page.parse_selection('') is None
    assert page.parse_selection('a'*64+':12') == {'pool_hash':'a'*64,'offset':12}


@pytest.mark.parametrize('offset', [0,6,12,15])
def test_outside_homepage_page_uses_real_executor_and_existing_price_gate(offset):
    state, ledger, association, result, selection, provider, calls = setup()
    selection['offset']=offset
    p=market.prepare_market_expression_reading(ROOT,state,ledger,association,result,observed_at=NOW,discovery_page=selection)
    assert p['version']==stock.DISCOVERY_PAGE_VERSION
    assert len(p['issuers']) <= stock.MAX_ISSUERS and p['maximum_request_count'] <= 26
    assert all(not o['discovery_origin']['group_on_homepage'] for i in p['issuers'] for o in i['origins'])
    observed=stock.observe_stock_reading(p,state,request_json=provider,observed_at=NOW)
    assert len(calls)<=p['maximum_request_count']
    assert observed['projection']['coverage']['qualified_issuers']==len(p['issuers'])
    assert observed['projection']['coverage']['planned_issuers']==len(p['issuers'])
    assert observed['projection']['policy']['stock_gate']==stock.MARKET_EXPRESSION_POLICY['stock_gate']
    assert observed['projection']['automatic_research_routing'] is False
    text=market.render_market_expression_reading(observed)
    assert '完整发现池与本批检查分开' in text
    assert '不是全池检查完成' in text


@pytest.mark.parametrize('offset', [0,6])
def test_capture_rebuilds_selection_original_inputs_full_result_and_dispositions(tmp_path,offset):
    mod,out,capture,result,selection,calls=capture_setup(tmp_path,offset=offset)
    assert capture['status']==mod['COMPLETE'],capture
    assert capture['version']==mod['PAGE_VERSION']
    rebuilt=mod['verify'](out)
    assert rebuilt['network_calls']==0 and rebuilt['requests_replayed']==len(calls)
    d=mod['read'](out/'discovery-dispositions.json')
    assert d['total_pool_count']==15 and d['prior_count']==offset
    assert d['selected_count']+d['prior_count']+d['deferred_count']==15
    assert len({r['thscode'] for r in d['rows']})==15
    expected=pool.plan_stock_discovery_batch(result,**selection)
    assert {r['thscode'] for r in d['rows'] if r['status']=='DEFERRED_NOT_EXECUTED_BY_THIS_CAPTURE'}==set(expected['deferred_codes'])
    files={'reading/'+p.relative_to(out).as_posix():p.read_bytes() for p in out.rglob('*') if p.is_file()}
    page.validate_saved({'discovery_page':selection},capture,mod['read'](out/'stock-reading.json'),files)


def test_missing_one_history_is_isolated_without_dropping_pool(tmp_path):
    def change(provider):
        def get(path,params):
            response=provider(path,params)
            if path==own.HISTORY and params['thscode']=='600000.SH':
                response['data']['item'].pop(-2)
            return response
        return get
    mod,out,capture,_,_,_=capture_setup(tmp_path,transport_change=change)
    assert capture['status']==mod['PARTIAL'],capture
    assert capture['coverage']['unavailable_issuers']==1
    assert mod['verify'](out)['network_calls']==0
    d=mod['read'](out/'discovery-dispositions.json')
    assert d['rows'][0]['status']=='DATA_INSUFFICIENT'


def test_transport_failure_does_not_make_selected_or_deferred_conditions_not_met(tmp_path):
    def change(provider):
        def fail(*_):raise RuntimeError('UNTRUSTED_SECRET_EXCEPTION')
        return fail
    mod,out,capture,_,_,calls=capture_setup(tmp_path,transport_change=change)
    assert capture['status']==mod['FAILED'] and len(capture['requests'])==1
    assert mod['verify'](out)['network_calls']==0
    text=(out/'discovery-dispositions.json').read_text()
    assert 'DEFERRED_NOT_EXECUTED_BY_THIS_CAPTURE' in text and 'CONDITIONS_NOT_MET' not in text
    assert 'UNTRUSTED_SECRET_EXCEPTION' not in (out/'capture.json').read_text()


@pytest.mark.parametrize('what', ['selector','dispositions','original_origin','version'])
def test_rehashed_page_tamper_is_not_accepted(complete_page_capture_copy,what):
    mod,out=complete_page_capture_copy
    capture=mod['read'](out/'capture.json')
    if what=='selector':
        p=out/'inputs/discovery-page.json'; data=mod['read'](p); data['offset']=1
    elif what=='dispositions':
        p=out/'discovery-dispositions.json'; data=mod['read'](p); data['rows'][-1]['status']='CONTRACT_CHECKED_RAW_READING'
        data['dispositions_hash']=canonical_hash({k:v for k,v in data.items() if k!='dispositions_hash'})
    elif what=='original_origin':
        p=out/'plan.json'; data=mod['read'](p); data['issuers'][0]['origins'][0]['discovery_origin']['group_on_homepage']=True
        data['plan_hash']=canonical_hash({k:v for k,v in data.items() if k!='plan_hash'})
    else:
        p=out/'capture.json';data=capture;data['version']=mod['VERSION']
    p.write_bytes(mod['data'](data))
    capture=mod['read'](out/'capture.json');capture['files']={k:v for k,v in mod['inventory'](out).items() if k!='capture.json'}
    capture['capture_hash']=canonical_hash({k:v for k,v in capture.items() if k!='capture_hash'})
    (out/'capture.json').write_bytes(mod['data'](capture))
    with pytest.raises(ValueError):mod['verify'](out)


@pytest.mark.parametrize('mutation', ['hash','bool','date'])
def test_wrong_pool_does_not_reuse_cursor(mutation):
    state,ledger,association,result,selection,provider,calls=setup()
    if mutation=='hash':selection['pool_hash']='f'*64
    elif mutation=='bool':selection['offset']=True
    else:
        result['produced_at']=(NOW+timedelta(seconds=1)).isoformat()
        result['result_hash']=canonical_hash({k:v for k,v in result.items() if k!='result_hash'})
    with pytest.raises(ValueError):market.prepare_market_expression_reading(ROOT,state,ledger,association,result,observed_at=NOW,discovery_page=selection)
    assert not calls


def test_disabled_current_gate_cannot_be_revived_by_saved_entry():
    state,ledger,association,result,selection,provider,calls=setup()
    p=market.prepare_market_expression_reading(ROOT,state,ledger,association,result,observed_at=NOW,discovery_page=selection)
    for d in p['directions'].values():d['currently_gate_active']=False
    p['plan_hash']=canonical_hash({k:v for k,v in p.items() if k!='plan_hash'})
    observed=stock.observe_stock_reading(p,state,request_json=provider,observed_at=NOW)
    assert not observed['projection']['surfaced_stocks']
    assert not any(path==own.HISTORY for path,_ in calls)


def test_research_scope_isolation_does_not_expand_security_authority(monkeypatch):
    from decision_kernel.runtime import stock_research_intake as intake
    rows=[{'thscode':code,'company_name':code,'eligible_for_shadow_reading':True,
           'status':'CONTRACT_CHECKED_RAW_READING','input_failure':None,'excluded_reasons':[]}
          for code in ('920006.BJ','600184.SH')]
    p={'projection':{'version':stock.DISCOVERY_PAGE_VERSION,'all_stock_observations':rows}}
    monkeypatch.setattr(intake.reading,'validate_stock',lambda *a:{'coverage':{'planned_issuers':2,'qualified_issuers':2},
        'market_session':'2026-09-04','projection_hash':'a'*64})
    # Minimal trusted run metadata for concise_run; no remote calls or claims.
    run={'id':202,'status':'completed','conclusion':'success','head_sha':'c'*40,'event':'workflow_dispatch','run_attempt':1,'created_at':NOW.isoformat()}
    result=intake.plan(run,{'reading/stock-reading.json':stock.canonical_json(p).encode()})
    assert [i['thscode'] for i in result['items']]==['600184.SH']
    assert result['excluded'][0]['status']=='RESEARCH_SCOPE_UNSUPPORTED'
    with pytest.raises(ValueError):intake.security('920006.BJ')


def test_workflow_adds_only_opt_in_input_no_auto_page_or_new_schedule():
    text=(ROOT/'.github/workflows/hithink-stock-dump-trial.yml').read_text()
    assert 'stock-discovery-page:' in text and 'STOCK_DISCOVERY_PAGE: ${{ inputs.stock-discovery-page }}' in text
    assert 'default: \'\'' in text and 'schedule:' not in text and 'strategy:' not in text


def test_current_state_accepts_new_route_and_rejects_relabelled_legacy(tmp_path):
    from decision_kernel.runtime import current_state as reader
    mod,out,capture,result,selection,_=capture_setup(tmp_path,public_path=True)
    assert capture['status']==mod['COMPLETE']
    verified=mod['verify'](out)
    files={'reading/'+p.relative_to(out).as_posix():p.read_bytes() for p in out.rglob('*') if p.is_file()}
    for name in ('manifest.json','market-state.json','candidate-events.json'):
        files['market/'+name]=files['reading/inputs/state/'+name]
    request={'workflow':capture['workflow'],'market_run_id':'101','prepared_at':NOW.isoformat(),
             'discovery_page':selection}
    binding={'request_hash':canonical_hash(request),'run_id':'101','commit':'b'*40,'artifact_id':'7'}
    files.update({'request.json':mod['data'](request),'verification.json':mod['data'](verified),
        'market-binding.json':mod['data'](binding),
        'market-context-binding.json':mod['data']({**binding,'state_artifact_id':'7'}),
        'market-context/result.json':files['reading/inputs/sector-result.json']})
    run={'id':202,'path':reader.WORKFLOWS['stock'],'head_sha':'c'*40,'head_branch':'main',
         'repository':{'full_name':reader.REPOSITORY},'head_repository':{'full_name':reader.REPOSITORY},
         'status':'completed','conclusion':'success','event':'workflow_dispatch','run_attempt':1,
         'created_at':NOW.isoformat()}
    # PUBLIC is the production code path fed only synthetic envelopes, not a real source run.
    saved=reader.validate_stock(run,files)
    assert saved['coverage']['qualified_issuers']>0
    assert saved['issuer_universe']==stock.DISCOVERY_PAGE_POLICY['issuer_universe']
    bad=deepcopy(files); report=json.loads(bad['reading/stock-reading.json'])
    report['projection']['version']=stock.MARKET_EXPRESSION_VERSION
    report['projection']['policy']=stock.MARKET_EXPRESSION_POLICY
    report['projection_hash']=canonical_hash(report['projection'])
    bad['reading/stock-reading.json']=mod['data'](report)
    # Even repairing this file's inventory cannot reinterpret the new capture as old routing.
    tampered=json.loads(bad['reading/capture.json']); raw=bad['reading/stock-reading.json']
    tampered['files']['stock-reading.json']={'bytes':len(raw),'sha256':reader.sha256(raw)}
    tampered['capture_hash']=canonical_hash({k:v for k,v in tampered.items() if k!='capture_hash'})
    bad['reading/capture.json']=mod['data'](tampered)
    with pytest.raises(ValueError):reader.validate_stock(run,bad)
