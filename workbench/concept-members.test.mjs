import test from 'node:test';
import assert from 'node:assert/strict';
import {conceptView,membershipView,overlaps,stockStatus} from './concept-members.mjs';
const auth=Object.fromEntries(['research_authority','odds_authority','action_authority','investment_authority'].map(k=>[k,'NONE']));
const tax='TDX_CATEGORY_CONCEPT_SOURCE_NATIVE_NOT_EASTMONEY_BK_OR_HITHINK_TI';
export function fixture(){
  const rows=['1','2','3'].map((n,i)=>({code:n.repeat(6),name:'TEST '+n,market_session:'2026-09-28',
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
