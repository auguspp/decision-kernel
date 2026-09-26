import test from 'node:test';
import assert from 'node:assert/strict';
import {localTime, recordRole, recordView, recordsView, outline, documentView, priceCondition, marketEntries, companyStatus, useLabel} from './product.mjs';

test('timezone display uses explicit UTC+8; date-only/unknown inputs never acquire a clock', () => {
  assert.equal(localTime('2026-09-25T23:12:00Z'), '2026/09/26 07:12 北京时间');
  for (const input of [null, '', '2026-09-25', '2026-09-25T23:12:00', 'bad']) assert.equal(localTime(input),'时间未知');
});
test('known manual and daily headings have separate roles; unknown records retained', () => {
  assert.equal(recordRole('## DAILY HOSTED QUICK 2026-09-25\n').label,'日常 Quick');
  assert.equal(recordRole('\n## MANUAL E2E HOSTED QUICK 2026-09-25\n').label,'手动 Quick');
  assert.equal(recordRole('## MANUAL E2E BRIEF 2026-09-25').kind,'brief');
  for (const text of ['## DAILY HOSTED QUICK 2026-02-30', '> ## DAILY HOSTED QUICK 2026-09-25',
    '## NOT RESEARCH\n## DAILY HOSTED QUICK 2026-09-25', '## DAILY HOSTED QUICK 2026-09-25 FAKE']) {
    assert.equal(recordRole(text).kind,'supplement');
  }
});
test('exact authored conclusion excerpt is not a synthesized recommendation', () => {
  const raw = '## MANUAL E2E HOSTED QUICK 2026-09-25\n\n# 原标题\n\n## 结论\n\n**不开展Full；原因UNKNOWN。**\n\n## 限制\n\n尚无经营证据。';
  const v = recordView({id:1,text:raw});
  assert.equal(v.title,'原标题'); assert.equal(v.excerpt,'**不开展Full；原因UNKNOWN。**');
  assert.equal(v.record.text,raw); assert.ok(v.sections.some(s=>s.text==='尚无经营证据。'));
  assert.equal(recordView({text:'## DAILY HOSTED QUICK 2026-09-25\n正文未分节'}).excerpt,null);
});
test('fenced code headings cannot become conclusion sections', () => {
  const text = '# A\n```md\n## 结论\n假的\n```\n## 范围\n真的';
  const result = outline(text);
  assert.equal(result.length,2); assert.equal(result[1].title,'范围');
  assert.equal(recordView({text}).excerpt,null);
});
test('all comments survive grouping; modified-time order is not event-time order', () => {
  const rows = [
    {id:1,text:'## DAILY HOSTED QUICK 2026-09-24',updatedAt:'2026-09-26T00:00:00Z'},
    {id:2,text:'## MANUAL E2E HOSTED QUICK 2026-09-25',updatedAt:'2026-09-25T00:00:00Z'},
    {id:3,text:'## 更正：不要使用旧数字',updatedAt:'2026-09-26T00:01:00Z'}];
  const v=recordsView({items:[rows[0]],supplements:rows.slice(1)});
  assert.deepEqual(v.research.map(r=>r.record.id),[1,2]);
  assert.deepEqual(v.other.map(r=>r.record.id),[3]); assert.equal(v.research[0].date,'2026-09-24');
});
test('price display retains a saved band; no derived proximity/buy signal', () => {
  const w = {currency:'CNY',next_unreached_condition:{kind:'RE_UNDERWRITE',lower_price:'15',upper_price:'17'}};
  const before=JSON.stringify(w);
  assert.ok(priceCondition(w).includes('15–17 CNY')); assert.ok(priceCondition(w).includes('不是买入指令'));
  assert.equal(JSON.stringify(w),before); assert.equal(priceCondition({}),'下一价格条件未提供');
});
function conditional() {
  return {artifact: {adapter_version:'probability-free-conditional-worlds-v1',schema_version:1,
    calculation_convention:'UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1',
    limitations:['NO_PROBABILITIES','NOT_ANNUALIZED'], human_acceptance:'NOT_ESTABLISHED',canonical_odds:'NOT_ESTABLISHED',
    price_context:{price:'42.93',currency:'CNY',price_timestamp:'2026-09-10T07:00:00Z'},
    valuation_horizon_date:'2029-09-10', cardinal_probability:'NOT_ESTABLISHED',
    conditional_worlds:{world_set:{worlds:[{id:'w',name:'原情景',operating_conditions:['现金兑现仍待验证']}]}},
    world_results:[{world_id:'w',world_name:'原情景',terminal_equity_value_per_share:'39.2',total_payoff_per_share:'39.2',
      undiscounted_holding_period_return:'-0.08688562776613091078'}]}};
}
test('typed conditional display preserves original decimals, prerequisites and unknown acceptance', () => {
  const data=conditional(),text=JSON.stringify(data),v=documentView(text);
  assert.equal(v.kind,'conditional'); assert.equal(v.rows[0].returnFraction,'-0.08688562776613091078');
  assert.equal(v.rows[0].conditions[0],'现金兑现仍待验证'); assert.deepEqual(v.limits,['NO_PROBABILITIES','NOT_ANNUALIZED']);
  assert.equal(v.facts.find(f=>f[0]==='原 Human 接受状态')[1],'NOT_ESTABLISHED');
  assert.equal(JSON.stringify(data),text);
});
test('unknown/ambiguous/malformed formats do not acquire invented summaries', () => {
  assert.equal(documentView('{bad'),null); assert.equal(documentView('{"price":42.93}'),null);
  const bad=conditional();bad.artifact.world_results[0].world_id='other';assert.equal(documentView(JSON.stringify(bad)),null);
  const duplicate=conditional();duplicate.artifact.world_results.push(duplicate.artifact.world_results[0]);
  assert.equal(documentView(JSON.stringify(duplicate)),null);
  for (const mutate of [d=>d.artifact.world_results.push(null),
    d=>d.artifact.conditional_worlds.world_set.worlds.push(null),
    d=>d.artifact.limitations.push({fake:'text'}), d=>d.artifact.price_context.price={fake:42}]) {
    const malformed=conditional();mutate(malformed);assert.equal(documentView(JSON.stringify(malformed)),null);
  }
  assert.equal(documentView('{"format":"research-commit-only-v0","research_status":{"fake":true}}'),null);
});
test('commit receipt never becomes research prose or automatic Human acceptance', () => {
  const v=documentView(JSON.stringify({format:'research-commit-only-v0',research_status:'COMMITTED',odds_status:'NOT_COMPUTED'}));
  assert.equal(v.kind,'receipt');assert.ok(v.notice.includes('不是研究正文'));assert.equal(v.facts[3][1],undefined);
});
test('market summaries resolve from pinned inventory; no match or ambiguity stays gap', () => {
  const a={read_path:'details/sector/123/summary.md'},b={read_path:'details/sector/456/summary.md'};
  assert.equal(marketEntries({references:[a]})[0].source,a);
  assert.equal(marketEntries({references:[a,b]})[0].source,null);
  assert.equal(marketEntries({references:[]})[0].source,null);
});
test('labels describe history rather than current status, holdings, or accepted forecasts', () => {
  assert.equal(useLabel({use:'HUMAN_DECISION_CHECKPOINT'}),'你的历史回应');
  assert.equal(useLabel({use:'FUTURE_UNKNOWN_TYPE'}),'FUTURE_UNKNOWN_TYPE');
  assert.ok(companyStatus({next_step:'WAITING_SAVED_PRICE_BOUNDARY_NOT_THESIS_NO_CHANGE'}).includes('仍需重审'));
});
