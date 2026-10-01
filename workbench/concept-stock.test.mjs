import test from 'node:test';
import assert from 'node:assert/strict';
import {stockComparisonView,checkedMembers,makeStockComparisonLoader} from './concept-stock.mjs';
function fixture(){
  const day='2026-09-28',coverage={planned_issuers:3,dispositioned_issuers:3,price_path_checked_issuers:2,
    qualified_issuers:1,conditions_not_met_issuers:1,unavailable_issuers:1};
  const statuses=['CONTRACT_CHECKED_RAW_READING','CONDITIONS_NOT_MET','DATA_QUALIFICATION_FAILED'];
  const rows=statuses.map((status,i)=>{
    const windows=Object.fromEntries(['5','20','60'].map(n=>[n,{base_session:'2026-07-01',end_session:day,usable_for_raw_comparison:true}]));
    const returns={'5':i===0?'0.1':'-0.1','20':i===0?'0.2':'0.3','60':null};
    return {thscode:`60000${i}.SH`,company_name:'TEST_ONLY '+i,status,excluded_reasons:i===1?['TEST_ONLY_5D_NOT_POSITIVE']:[],
      input_failure:i===2?{reason_code:'TEST_ONLY_DATA_GAP'}:null,
      current_origins:[{current_member_sectors:['881125.TI'],sector_codes:['881125.TI'],direction_sources:[{
        family:'BROAD_881',thscode:'881125.TI',name:'TEST_ONLY 行业'}]}],
      stock_path:i===2?null:{price_convention:'RAW_UNADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN',returns,
        input_checks:{history_window_checks:structuredClone(windows),action_window_checks:structuredClone(windows)}},
      market_comparison:i===2?{}:Object.fromEntries(['5','20','60'].map(n=>[n,returns[n]===null?null:{stock_return:returns[n],benchmark_return:'0',excess_return:returns[n]}]))};
  });
  const p={market_session:day,observed_at:'2026-09-28T12:00:00Z',status:'PARTIAL_STOCKS_FOR_SHADOW_READING',
    scope:'BOUNDED_SURFACED_SECTOR_MARKET_EXPRESSION_NOT_ALL_A_SHARES',
    semantics:'BOUNDED_MARKET_EXPRESSION_NOT_BUSINESS_BENEFIT_OR_RECOMMENDATION',reference_input_provenance:'HITHINK_REQUEST_BOUND_RAW_OBSERVATION',
    policy:{version:'stock-market-expression-window-qualified-v8'},price_path_is_not_total_return:true,
    ...Object.fromEntries(['research_authority','human_attention_authority','signal_transition_authority','investment_authority'].map(k=>[k,'NONE'])),
    automatic_research_routing:false,creates_canonical_wake:false,coverage,all_stock_observations:rows};
  const report={projection:p,projection_hash:'a'.repeat(64)};
  const saved={market_session:day,observed_at:p.observed_at,status:p.status,scope:p.scope,projection_hash:report.projection_hash,
    coverage:structuredClone(coverage),dispositions:rows.map(r=>({thscode:r.thscode,status:r.status})),
    details:{'reading/stock-reading.json':{read_path:'details/stock/1/reading/stock-reading.json'}}};
  const membership={data:{market_session:day},sets:new Map([['111111',new Set(['600000.SH','600001.SH','600002.SH','600003.SH'])],
    ['222222',new Set(['600002.SH'])],['333333',new Set(['600003.SH'])]])};
  return {report,saved,membership};
}
const parse=f=>stockComparisonView(JSON.stringify(f.report),f.saved);
test('all dispositions and actual member denominators survive; higher return does not mean qualified',()=>{
  const f=fixture(),before=JSON.stringify(f.report),v=checkedMembers(f.membership,'111111',parse(f));
  assert.deepEqual(v.rows.map(r=>r.ticker),['600001.SH','600000.SH','600002.SH']);
  assert.equal(v.rows[0].status,'CONDITIONS_NOT_MET');assert.equal(v.rows[0].windows['5'].value,'-0.1');
  assert.equal(v.rows[0].windows['60'],null);assert.deepEqual(v.rows[0].reasons,['TEST_ONLY_5D_NOT_POSITIVE']);
  assert.equal(v.checked,3);assert.equal(v.total,4);assert.equal(v.notChecked,1);assert.equal(v.qualified,1);
  assert.equal(v.notMet,1);assert.equal(v.unavailable,1);assert.equal(v.ranked,true);assert.equal(JSON.stringify(f.report),before);
  const none=checkedMembers(f.membership,'333333',parse(f));assert.equal(none.checked,0);assert.equal(none.notChecked,1);
  const gap=checkedMembers(f.membership,'222222',parse(f));assert.equal(gap.unavailable,1);assert.equal(gap.ranked,false);
});
for(const [label,damage] of [
  ['foreign hash',f=>f.saved.projection_hash='b'.repeat(64)],
  ['date mismatch',f=>f.saved.market_session='2026-09-24'],
  ['authority',f=>f.report.projection.investment_authority='BUY'],
  ['automatic research',f=>f.report.projection.automatic_research_routing=true],
  ['different scope',f=>f.report.projection.scope='ALL_MEMBERS'],
  ['policy unknown',f=>f.report.projection.policy.version='unreviewed'],
  ['missing full observation',f=>f.report.projection.all_stock_observations.pop()],
  ['duplicate row',f=>f.report.projection.all_stock_observations[1]=f.report.projection.all_stock_observations[0]],
  ['duplicate disposition',f=>f.saved.dispositions[1]=f.saved.dispositions[0]],
  ['mislabeled qualification',f=>f.saved.dispositions[1].status='CONTRACT_CHECKED_RAW_READING'],
  ['coverage inflation',f=>f.report.projection.coverage.price_path_checked_issuers=3],
  ['fake unavailable price',f=>f.report.projection.all_stock_observations[2].stock_path=f.report.projection.all_stock_observations[0].stock_path],
  ['float value',f=>f.report.projection.all_stock_observations[0].stock_path.returns['20']=0.2],
  ['nonfinite',f=>f.report.projection.all_stock_observations[0].stock_path.returns['20']='Infinity'],
  ['bad action window',f=>f.report.projection.all_stock_observations[0].stock_path.input_checks.action_window_checks['20'].usable_for_raw_comparison=false],
  ['bad history window',f=>f.report.projection.all_stock_observations[0].stock_path.input_checks.history_window_checks['20'].end_session='2026-09-24'],
  ['wrong market price',f=>f.report.projection.all_stock_observations[0].market_comparison['20'].stock_return='9'],
  ['unbound direction',f=>f.report.projection.all_stock_observations[0].current_origins[0].current_member_sectors=[]],
  ['mixed taxonomy',f=>f.report.projection.all_stock_observations[0].current_origins[0].direction_sources[0].thscode='880951'],
  ['wrong industry family',f=>f.report.projection.all_stock_observations[0].current_origins[0].direction_sources[0].family='GRANULAR_884']
])test('reject '+label,()=>{const f=fixture();damage(f);assert.throws(()=>parse(f));});
function set20(f,i,value){const row=f.report.projection.all_stock_observations[i];row.stock_path.returns['20']=value;
  row.market_comparison['20']={stock_return:value,benchmark_return:'0',excess_return:value};}
for(const [a,b,first] of [['0.2000000000000000000002','0.2000000000000000000001','600000.SH'],
  ['-0.2','-0.1','600001.SH'],['-0.000','0','600000.SH'],['0.20','0.2','600000.SH']])test('exact decimal comparison '+a+' / '+b,()=>{
  const f=fixture();set20(f,0,a);set20(f,1,b);
  assert.equal(checkedMembers(f.membership,'111111',parse(f)).rows[0].ticker,first);
});
test('stale member/Stock date and differing price windows are historical references, not rankings',()=>{
  const f=fixture();f.membership.data.market_session='2026-09-24';
  const x=checkedMembers(f.membership,'111111',parse(f));assert.equal(x.sameDay,false);assert.equal(x.ranked,false);
  assert.equal(x.rows[0].ticker,'600000.SH');
  f.membership.data.market_session='2026-09-28';
  for(const k of ['history_window_checks','action_window_checks'])f.report.projection.all_stock_observations[1].stock_path.input_checks[k]['20'].base_session='2026-07-02';
  assert.equal(checkedMembers(f.membership,'111111',parse(f)).ranked,false);
});
test('source identities retain all distinct sector routes without merging families',()=>{
  const f=fixture(),origin=f.report.projection.all_stock_observations[0].current_origins[0];
  origin.current_member_sectors.push('884243.TI');origin.sector_codes.push('884243.TI');
  origin.direction_sources.push({family:'GRANULAR_884',thscode:'884243.TI',name:'TEST_ONLY 细分'});
  assert.deepEqual(parse(f).rows.get('600000.SH').directions.map(r=>r.family),['BROAD_881','GRANULAR_884']);
  origin.direction_sources.push({...origin.direction_sources[0],name:'OTHER'});assert.throws(()=>parse(f));
});
test('v9 accepts reported-action price-reference adjustment without weakening window checks',()=>{
  const f=fixture(),row=f.report.projection.all_stock_observations[0];
  f.report.projection.policy.version='stock-market-expression-window-qualified-v9';
  row.stock_path.price_convention='REPORTED_ACTION_REFERENCE_ADJUSTED_NOT_TOTAL_RETURN';
  const a=row.stock_path.input_checks.action_window_checks['20'];
  a.usable_for_raw_comparison=false;a.usable_for_price_reference_adjusted_comparison=true;
  a.comparison_basis='REPORTED_ACTION_REFERENCE_ADJUSTED';
  const parsed=parse(f).rows.get('600000.SH');
  assert.equal(parsed.basis,'REPORTED_ACTION_REFERENCE_ADJUSTED_NOT_TOTAL_RETURN');
  a.usable_for_price_reference_adjusted_comparison=false;
  assert.throws(()=>parse(f));
});
test('v9 accepts one bounded forward-adjusted fallback only with retained 3002 gap metadata',()=>{
  const f=fixture(),row=f.report.projection.all_stock_observations[0],checks=row.stock_path.input_checks;
  f.report.projection.policy.version='stock-market-expression-window-qualified-v9';
  row.stock_path.price_convention='PROVIDER_FORWARD_ADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN';
  checks.corporate_action_query_succeeded=false;
  checks.corporate_action_query={provider_business_code:3002};
  checks.adjusted_history_fallback={status:'USED',event_details_inferred:false,
    history_window_checks:structuredClone(checks.history_window_checks)};
  checks.action_window_checks=null;
  const parsed=parse(f).rows.get('600000.SH');
  assert.equal(parsed.basis,'PROVIDER_FORWARD_ADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN');
  checks.adjusted_history_fallback.event_details_inferred=true;
  assert.throws(()=>parse(f));
});
test('request failure remains unavailable rather than becoming conditions-not-met',()=>{
  const f=fixture(),row=f.report.projection.all_stock_observations[2];
  row.status='REQUEST_FAILED';f.saved.dispositions[2].status='REQUEST_FAILED';
  row.input_failure.reason_code='PROVIDER_BUSINESS_REQUEST_FAILED';
  const parsed=parse(f);
  assert.equal(parsed.rows.get('600002.SH').status,'REQUEST_FAILED');
  assert.equal(checkedMembers(f.membership,'222222',parsed).unavailable,1);
});
test('one lazy same-R read; old versions do not fetch, failure never reruns on another selection',async()=>{
  const f=fixture();let calls=0;
  const loader=makeStockComparisonLoader({payload:{lanes:{stock:{last_qualified_result:f.saved}}},readFile:async d=>{
    calls++;assert.equal(d,f.saved.details['reading/stock-reading.json']);return {text:JSON.stringify(f.report)};}});
  assert.equal(calls,0);assert.equal(loader(),loader());await loader();assert.equal(calls,1);
  const legacy=makeStockComparisonLoader({payload:{},readFile:()=>{throw Error('must not fetch');}});assert.equal(await legacy(),null);
  const bad=makeStockComparisonLoader({payload:{lanes:{stock:{last_qualified_result:f.saved}}},readFile:async()=>{calls++;throw Error('FILE_INTEGRITY_MISMATCH');}});
  await assert.rejects(bad(),/INTEGRITY/);await assert.rejects(bad(),/INTEGRITY/);assert.equal(calls,2);
});
