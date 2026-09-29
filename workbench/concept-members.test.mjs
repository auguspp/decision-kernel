import test from 'node:test';
import assert from 'node:assert/strict';
import {conceptView,membershipView,overlaps,stockStatus,trendView,conceptOverview} from './concept-members.mjs';
const auth=Object.fromEntries(['research_authority','odds_authority','action_authority','investment_authority'].map(k=>[k,'NONE']));
const tax='TDX_CATEGORY_CONCEPT_SOURCE_NATIVE_NOT_EASTMONEY_BK_OR_HITHINK_TI';
export function fixture(){
  const rows=['1','2','3'].map((n,i)=>({code:n.repeat(6),name:'TEST '+n,full_code:'sh'+n.repeat(6),market_session:'2026-09-28',
    periods:Object.fromEntries(['today','5d','10d'].map(k=>[k,{change_percent:i===2?null:'-1.25'}]))}));
  const report={projection:{...auth,version:'tdx-concept-snapshot-v1',taxonomy:tax,kind:'MARKET_EXPRESSION',qualification:'CONTEXT_ONLY',market_session:'2026-09-28',catalog_count:3,observations:rows},projection_hash:'a'.repeat(64)};
  const p={...auth,version:'tdx-concept-membership-v1',taxonomy:tax,market_session:'2026-09-28',source_prepared_date:'2026-09-28',source_observed_at:'2026-09-28T08:00:00Z',observation_hash:report.projection_hash,capture_hash:'d'.repeat(64),membership_time_basis:'SAVED_SOURCE_PREPARATION_NOT_HISTORICAL_EFFECTIVE_MEMBERSHIP',historical_membership:'NOT_ESTABLISHED',member_ranking:'NOT_COMPUTED',business_benefit:'NOT_ESTABLISHED',source_calls:0,parser_version:'3.2.2',catalog_count:3,relation_count:5,
    concepts:rows.map((r,i)=>({code:r.code,name:r.name,members:i===0?['600001.SH','000001.SZ']:i===1?['000001.SZ']:['600001.SH','920001.BJ']})),securities:{'600001.SH':{name:'<script>TEST</script>',in_source_catalog:true},'000001.SZ':{name:'B',in_source_catalog:true},'920001.BJ':{name:null,in_source_catalog:false}}};
  const members={projection:p,projection_hash:'b'.repeat(64)};
  const saved={result:{projection_hash:report.projection_hash,market_session:'2026-09-28',catalog_count:3},membership:{status:'VERIFIED_SAVED_MEMBERSHIP',projection_hash:members.projection_hash,catalog_count:3,relation_count:5}};
  return {report,members,saved};
}
test('all concepts and source members stay separate; overlap retains two denominators and actual shared members',()=>{
  const f=fixture(),before=JSON.stringify(f),o=conceptView(JSON.stringify(f.report),f.saved),m=membershipView(JSON.stringify(f.members),f.saved.membership,o);
  const result=overlaps(m,'111111');assert.equal(result.length,2);
  assert.deepEqual(result[0],{code:'222222',name:'TEST 2',shared:['000001.SZ'],ownCount:2,otherCount:1,unionCount:2});
  assert.equal(m.data.securities['920001.BJ'].in_source_catalog,false);assert.equal(JSON.stringify(f),before);
});
for(const [name,damage] of [
 ['foreign taxonomy',f=>f.members.projection.taxonomy='HITHINK'],['bad date',f=>f.members.projection.market_session='2026-09-25'],
 ['wrong observation',f=>f.members.projection.observation_hash='c'.repeat(64)],['duplicate member',f=>f.members.projection.concepts[0].members.push('600001.SH')],
 ['missing security',f=>delete f.members.projection.securities['600001.SH']],['renamed board',f=>f.members.projection.concepts[0].name='OTHER'],
 ['invented research',f=>f.members.projection.business_benefit='CONFIRMED'],['missing row',f=>f.report.projection.observations.pop()],
 ['promoted authority',f=>f.members.projection.investment_authority='BUY'],['not saved',f=>f.saved.membership.status='UNAVAILABLE_OR_REJECTED']])test('reject '+name,()=>{
  const f=fixture();damage(f);assert.throws(()=>membershipView(JSON.stringify(f.members),f.saved.membership,conceptView(JSON.stringify(f.report),f.saved)));
});
test('stock statuses and dates never collapse absence, condition failure, data gap and historical qualification',()=>{
  const lane={last_qualified_result:{market_session:'2026-09-24',dispositions:[{thscode:'600001.SH',status:'CONTRACT_CHECKED_RAW_READING'},{thscode:'000001.SZ',status:'CONDITIONS_NOT_MET'},{thscode:'920001.BJ',status:'DATA_QUALIFICATION_FAILED'}]}};
  assert.match(stockStatus('600001.SH',lane),/通过.*2026-09-24/);assert.match(stockStatus('000001.SZ',lane),/条件未满足/);
  assert.match(stockStatus('920001.BJ',lane),/不可用/);assert.match(stockStatus('600002.SH',lane),/不在.*范围/);
  lane.last_qualified_result.dispositions.push({...lane.last_qualified_result.dispositions[0]});assert.match(stockStatus('600001.SH',lane),/冲突/);
});

function trendFixture(){
  const f=fixture();
  const coverage={horizons:{'5':3,'20':3,'60':2},phase_rows:2,unavailable_rows:0};
  const data={...auth,version:'tdx-concept-trend-v1',taxonomy:tax,kind:'MARKET_EXPRESSION',qualification:'CONTEXT_ONLY',
    observation_hash:f.report.projection_hash,base_capture_hash:'c'.repeat(64),source_hash:'d'.repeat(64),
    source_observed_at:'2026-09-28T08:30:00Z',market_session:'2026-09-28',
    benchmark:{full_code:'sh000300',source:'SAME_TDX_HOST',history_start:'2026-04-01',history_end:'2026-09-28',history_points:126},
    return_unit:'FRACTION_NOT_PERCENT',source_calls_during_replay:0,
    policy:{phase_basis:'DESCRIPTIVE_20D_EXCESS_NOT_INVESTMENT_SIGNAL',session_basis:'RETURNED_BENCHMARK_SESSIONS_NOT_EXCHANGE_CALENDAR',custody:'EXTRACTED_SDK_TIME_AND_INTEGER_CLOSE_NOT_RAW_WIRE'},
    historical_universe:'CURRENT_CATALOG_NOT_HISTORICAL_MEMBERSHIP',trend_age:'POSITIVE_20D_EXCESS_RUN_WITH_LEFT_CENSOR_NOT_THEME_LIFETIME',
    catalog_count:3,coverage,observations:f.report.projection.observations.map((c,i)=>({code:c.code,name:c.name,full_code:c.full_code,
      horizons:Object.fromEntries([5,20,60].map(n=>[n,i===2 && n===60?null:{index_return:'0.03',benchmark_return:'0.01',excess_return:'0.02'}])),
      phase:i===2?'UNKNOWN':i===0?'STRENGTHENING':'MATURE_OR_DIVERGING',phase_reason:'TEST_ONLY',gap:null,
      history_points:i===2?30:126,history_start:'2026-04-01',history_end:'2026-09-28',previous_session:'2026-09-25',
      previous_20d_excess:'0.01',excess_acceleration_5_sessions_20d:'0.01',positive_20d_excess_persistence_sessions:5,
      positive_20d_excess_run_started:'2026-09-22',positive_20d_excess_persistence_left_censored:false}))};
  return {...f,trend:{projection:data,projection_hash:'e'.repeat(64)},savedTrend:{status:'VERIFIED_SAVED_LONG_HISTORY',projection_hash:'e'.repeat(64),catalog_count:3,coverage:structuredClone(coverage)}};
}
test('long-path reader retains full catalog, weakening and unknown horizons beside original members',()=>{
  const f=trendFixture(),view=trendView(JSON.stringify(f.trend),f.savedTrend,conceptView(JSON.stringify(f.report),f.saved));
  assert.equal(view.rows.size,3);assert.equal(view.rows.get('222222').phase,'MATURE_OR_DIVERGING');
  assert.equal(view.rows.get('333333').horizons['60'],null);
  assert.equal(membershipView(JSON.stringify(f.members),f.saved.membership,conceptView(JSON.stringify(f.report),f.saved)).sets.size,3);
});
for(const [name,damage] of [
  ['source binding',f=>f.trend.projection.observation_hash='f'.repeat(64)],
  ['benchmark',f=>f.trend.projection.benchmark.full_code='sh000001'],
  ['period rename',f=>f.trend.projection.return_unit='PERCENT'],
  ['missing concept',f=>f.trend.projection.observations.pop()],
  ['invented phase',f=>f.trend.projection.observations[0].phase='BUY'],
  ['insufficient history',f=>f.trend.projection.observations[2].phase='STRENGTHENING'],
  ['mixed security',f=>f.trend.projection.observations[0].full_code='sz111111'],
  ['count mismatch',f=>f.savedTrend.coverage.horizons['60']=3],
  ['age',f=>f.trend.projection.observations[0].positive_20d_excess_persistence_sessions=300],
  ['bad decimal',f=>f.trend.projection.observations[0].horizons['20'].excess_return='NaN'],
  ['gap promoted',f=>f.trend.projection.observations[0].gap='SOURCE_FAILED']
])test('long-path rejection: '+name,()=>{
  const f=trendFixture();damage(f);assert.throws(()=>trendView(JSON.stringify(f.trend),f.savedTrend,conceptView(JSON.stringify(f.report),f.saved)));
});


test('overview counts the full source beyond the first page, preserving zero, negative zero and unknown',()=>{
  const f=fixture(),before=JSON.stringify(f),o=conceptView(JSON.stringify(f.report),f.saved);
  const values=['1','-2','0','-0.000',null,'0.'+'0'.repeat(350)+'1','-0.'+'0'.repeat(350)+'1'];
  o.rows=Array.from({length:35},(_,i)=>({...o.rows[0],code:String(100000+i),periods:Object.fromEntries(
    ['today','5d','10d'].map(k=>[k,{change_percent:values[i%values.length]}]))}));
  const v=conceptOverview(o);assert.equal(v.total,35);assert.equal(v.groups,null);
  for(const b of v.breadth){
    assert.deepEqual([b.up,b.down,b.flat,b.unknown],[10,10,10,5]);
    const ids=Object.values(b.codes).flat();assert.equal(ids.length,35);assert.equal(new Set(ids).size,35);
    for(const side of ['up','down','flat','unknown'])assert.equal(b.codes[side].length,b[side]);
  }
  assert.equal(JSON.stringify(f),before);
});

test('overview reuses saved phases, keeps unknown and all identities, never short-return phase inference',()=>{
  const f=trendFixture(),o=conceptView(JSON.stringify(f.report),f.saved),t=trendView(JSON.stringify(f.trend),f.savedTrend,o);
  const before=JSON.stringify(f),v=conceptOverview(o,t);
  assert.deepEqual(v.groups.map(g=>g.label),['持续强化','强中分歧','阶段未知']);
  assert.deepEqual(v.groups.flatMap(g=>g.codes),['111111','222222','333333']);
  // All short-period values are negative or unknown; they must not replace the saved phases.
  assert.equal(v.breadth[0].down,2);assert.equal(v.breadth[0].unknown,1);
  assert.equal(JSON.stringify(f),before);
});

test('overview examples keep source order while every grouped identity remains reachable',()=>{
  const f=trendFixture(),o=conceptView(JSON.stringify(f.report),f.saved),t=trendView(JSON.stringify(f.trend),f.savedTrend,o);
  for(const r of t.rows.values()){r.phase='STRENGTHENING';r.phase_reason='SAVED_DESCRIPTION';}
  o.rows.reverse();const v=conceptOverview(o,t);
  assert.deepEqual(v.groups[0].codes,['333333','222222','111111']);
  assert.deepEqual(v.groups[0].examples,['TEST 3','TEST 2']);
});

test('overview distinguishes a new exit from an already weak path using the existing reason labels',()=>{
  const f=trendFixture(),o=conceptView(JSON.stringify(f.report),f.saved),t=trendView(JSON.stringify(f.trend),f.savedTrend,o);
  const a=t.rows.get('111111'),b=t.rows.get('222222');
  a.phase=b.phase='WEAKENING_OR_EXIT';
  a.phase_reason='TWENTY_DAY_EXCESS_EXITED_POSITIVE_STATE';
  b.phase_reason='NONPOSITIVE_20D_EXCESS_STILL_WEAKENING_NOT_NEW_EXIT';
  assert.deepEqual(conceptOverview(o,t).groups.map(g=>g.label),['20日相对强势条件已退出','相对走势仍弱，不是本次新退出','阶段未知']);
});

test('overview remains available without members or long history; unknown is not flat or quiet',()=>{
  const f=fixture(),o=conceptView(JSON.stringify(f.report),f.saved);
  for(const r of o.rows)for(const h of Object.values(r.periods))h.change_percent=null;
  const v=conceptOverview(o);
  assert.equal(v.groups,null);assert.equal(v.total,3);
  for(const b of v.breadth)assert.deepEqual([b.up,b.down,b.flat,b.unknown],[0,0,0,3]);
});
