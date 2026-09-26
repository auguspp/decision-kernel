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

// Synthetic authority/identity cases; no Human investment response is created.
import {attentionView, companyMaterials, watchOrigin, attentionResume} from './product.mjs';
import {watchSummary} from './presentation.mjs';
const point = 'e'.repeat(40), checksum = 'f'.repeat(64);
const retained = (path = 'request.json') => ({read_path: `sources/${path}`, path, bytes: 12,
  sha256: checksum, git_blob: point, repository: 'auguspp/decision-kernel'});
const handoff = (id = '1'.repeat(64)) => ({request_id: id, security_id: '600276.SH', ticker: '600276',
  as_of: '2026-09-01T01:00:00Z', terminal_state: 'DEEPEN_REQUIRED', reason: '<script>not authority</script>',
  source: retained(), resolution: null});
const requestPayload = (active = [], resolved = [], background = [], gaps = []) => ({pending: active,
  research: {handoffs: {active, resolved_history: resolved, background, gaps,
    registration_scope: 'EXPLICIT_INPUTS_ONLY_NOT_ALL_RESEARCH_OR_ALL_MARKET'}}});
const noWatch = {available: true, rows: []};

test('only explicit active version is pending; resolution of another version does not close it', () => {
  const pending = handoff(), old = {...handoff('2'.repeat(64)), resolution: retained('old-response.md')};
  const p = requestPayload([pending], [old]);
  p.research.quick = {title: 'Full建议', human_acceptance: 'yes'};
  const before = JSON.stringify(p), v = attentionView(p, noWatch);
  assert.equal(v.requests.length, 1); assert.equal(v.history.length, 1);
  assert.equal(v.requests[0].resolution, null); assert.equal(v.history[0].resolution.read_path, 'sources/old-response.md');
  assert.equal(v.requests[0].reason, '<script>not authority</script>');
  assert.equal(JSON.stringify(p), before);
});

test('missing, partial and conflicting request inventories never become a clean zero', () => {
  assert.ok(attentionView({}, noWatch).gaps.length);
  const v = attentionView(requestPayload([], [], [], [{status: 'EXECUTION_ID_CONFLICT'}]), noWatch);
  assert.equal(v.requests.length, 0); assert.match(v.gaps.join(), /EXECUTION_ID_CONFLICT/);
  const duplicate = attentionView(requestPayload([handoff()], [{...handoff(), resolution: retained('response.md')}]), noWatch);
  assert.equal(duplicate.requests.length, 0); assert.equal(duplicate.history.length, 0); assert.ok(duplicate.gaps.length);
  const mismatch = requestPayload([handoff()]); mismatch.pending = [];
  assert.match(attentionView(mismatch, noWatch).gaps.join(), /摘要与登记明细不一致/);
});

test('malformed resolution or source stays a gap, not historical acceptance or a new pending item', () => {
  for (const row of [null, {...handoff(), source: retained('../escape')},
    {...handoff(), source: {...retained(), repository: 'elsewhere/repo'}},
    {...handoff(), as_of: '2026-09-01'}, {...handoff(), resolution: retained('response.md')},
    {...handoff(), terminal_state: 'WAIT'}]) {
    const v = attentionView(requestPayload([row]), noWatch);
    assert.equal(v.requests.length, 0); assert.ok(v.gaps.length);
  }
  const invalid = attentionView(requestPayload([], [handoff()]), noWatch);
  assert.equal(invalid.history.length, 0); assert.ok(invalid.gaps.length);
});

function savedWatch(ticker, extra = {}) {
  return {ticker, company_name: ticker, watch_enabled: true, status: 'ACTIVE_ODDS_WATCH', price: '50',
    market_timestamp: '2026-09-24T15:00:00+08:00', currency: 'CNY', triggered_conditions: [],
    next_unreached_condition: {id: 'original-boundary', upper_price: '40', attention_triggered: false, condition_state: 'ABOVE_CONDITION'},
    source: {registry_reference_id: 'human-checkpoint', source_path: 'decision.md', source_git_blob: point, source_ref: null}, ...extra};
}
function withWatches(items) {
  return {...requestPayload(), lanes: {inbox: {last_qualified_result: {odds_watch: {report: {
    watch: {active_cases: items, active_case_count: items.length}}}}}}};
}
test('saved price facts are separated from requests and price/read gaps do not become Human chores', () => {
  const p = withWatches([savedWatch('600276.SH'), savedWatch('603986.SH', {triggered_conditions: [{id: 'review', attention_triggered: true}]}),
    savedWatch('002674.SZ', {price: null, price_gap: 'READ_FAILED'})]);
  const before = JSON.stringify(p), v = attentionView(p, watchSummary(p));
  assert.equal(v.waiting.length, 1); assert.equal(v.review.length, 1); assert.equal(v.requests.length, 0);
  assert.equal(v.waiting[0].original.price, '50'); assert.match(v.gaps.join(), /不是待你补数据的请求/);
  assert.equal(JSON.stringify(p), before);
  const repeated = withWatches([savedWatch('600276.SH'), savedWatch('600276.SH')]);
  assert.equal(attentionView(repeated, watchSummary(repeated)).waiting.length, 0);
});

test('company material order uses explicit purpose, never a new current or accepted version', () => {
  const company = {assets: [
    {id: 'human-old', use: 'HUMAN_DECISION_CHECKPOINT'}, {id: 'latest-file', use: 'RETAINED_RESEARCH_PACKAGE'},
    {id: 'note', use: 'RESEARCH_CORRECTION'}, {id: 'x', use: 'UNKNOWN_ROLE'}]};
  const before = JSON.stringify(company), groups = companyMaterials(company);
  assert.deepEqual(groups.map(g => g.items[0].id), ['note', 'latest-file', 'human-old', 'x']);
  assert.equal(JSON.stringify(company), before);
});

test('watch source requires exact registry id, blob, path and security; null ref is not guessed', () => {
  const p = withWatches([savedWatch('600276.SH')]), item = attentionView(p, watchSummary(p)).waiting[0];
  const source = retained('decision.md'), company = {thscode: '600276.SH', assets: [{id: 'human-checkpoint', source}]};
  assert.equal(watchOrigin(item, company), source);
  assert.equal(watchOrigin(item, {...company, thscode: '603986.SH'}), null);
  assert.equal(watchOrigin(item, {...company, assets: [...company.assets, ...company.assets]}), null);
  const nextVersion = {...company, assets: [{id: 'human-checkpoint', source: {...source, git_blob: 'a'.repeat(40)}}]};
  assert.equal(watchOrigin(item, nextVersion), null);
});

test('copied recovery carries immutable R, exact source/version and no fabricated answer', () => {
  const item = attentionView(requestPayload([handoff()]), noWatch).requests[0];
  const text = attentionResume(point, item, {thscode: '600276.SH', assets: [
    {id: 'old-response', use: 'HUMAN_DECISION_CHECKPOINT', source: retained('decision.md')}]});
  assert.match(text, /新的回应尚未提供/); assert.match(text, /不要凭此文本新增回应/);
  const context = JSON.parse(text.slice(text.indexOf('{')));
  assert.equal(context.item_id, item.id); assert.equal(context.source.sha256, checksum);
  assert.ok(context.reading.includes(`/blob/${point}/current-state.json`));
  assert.ok(context.related_versions[0].source.includes(`/blob/${point}/`));
  assert.equal(context.registered_resolution, null); assert.equal(context.watch_conditions, null);
  assert.throws(() => attentionResume('main', item, null), /UNPINNED_COMMIT/);
  assert.throws(() => attentionResume(point, item, {thscode: '603986.SH', assets: []}), /ITEM_COMPANY_MISMATCH/);
});
