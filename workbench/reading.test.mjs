import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {REPO, READ_REF, commit, safePath, fileUrl, validateShape, references,
  openReading, openPinnedReading, readHealth, readQuick, loadModules, resumeText} from './reading.mjs';

// Synthetic transport fixtures, not historical Research or Human acceptance.
const R = 'a'.repeat(40), M = 'b'.repeat(40), API = `https://api.github.com/repos/${REPO}`;
const text = '研究原文 <script>not executable</script>\n';
const source = {read_path: 'sources/git/example/research.md', bytes: Buffer.byteLength(text),
  sha256: createHash('sha256').update(text).digest('hex')};
function state() { return {schema_version: 1, entry_ref: READ_REF, code_commit: M,
  semantics: 'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',
  reading_hash: 'c'.repeat(64), signal_transition_authority: 'NONE', human_attention_authority: 'NONE',
  research_authority: 'NONE', investment_authority: 'NONE', lanes: {}, research: {example: {source}}}; }
function transport(route) {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push(url);
    assert.equal(options.method, 'GET'); assert.equal(options.credentials, 'omit');
    assert.equal(options.redirect, 'error'); assert.equal(options.body, undefined);
    assert.equal(options.headers?.Authorization, undefined);
    const value = route(url);
    return new Response(typeof value === 'string' ? value : JSON.stringify(value));
  };
  return {calls, fetcher};
}
function fixture(url) {
  if (url.endsWith(`/git/ref/heads/${READ_REF}`)) return {ref: `refs/heads/${READ_REF}`, object: {type: 'commit', sha: R}};
  if (url.endsWith('/current-state.json')) return state();
  if (url.endsWith('/research.md')) return text;
  throw new Error(`unexpected request: ${url}`);
}

test('a batch resolves its movable reading ref exactly once', async () => {
  const {fetcher, calls} = transport(fixture);
  const reading = await openReading(fetcher);
  assert.equal(reading.ref, R); assert.equal(reading.payload.code_commit, M);
  const result = await reading.readFile(reading.references[0]);
  assert.equal(result.text, text); assert.match(result.validation, /SHA256_MATCH/);
  assert.equal(calls.filter(url => url.includes('/git/ref/')).length, 1);
  assert.ok(calls.slice(1).every(url => url.includes(`/${R}/`)));
  assert.match(reading.validation, /NOT_RECOMPUTED/);
});
test('reading values and descriptor inventory cannot silently change in memory', async () => {
  const reading = await openReading(transport(fixture).fetcher);
  assert.throws(() => { reading.payload.code_commit = R; }, TypeError);
  assert.throws(() => { reading.references[0].sha256 = 'd'.repeat(64); }, TypeError);
});
test('invalid refs and unsafe paths are rejected before transport', () => {
  for (const value of ['main', '', '../x', R + '/x', null]) assert.throws(() => commit(value));
  for (const value of ['../x', '/x', 'x//y', './x', 'x/../y', 'x\\y', '%2e%2e/x',
    'x?token=a', 'x#fragment', 'x\nname', 'x/']) assert.throws(() => safePath(value));
  assert.equal(safePath('docs/研究 文件.md'), 'docs/研究 文件.md');
  assert.match(fileUrl(R, 'docs/研究 文件.md'), /%20/);
});
test('unknown schema, semantics or any increased authority fails closed', () => {
  for (const patch of [{schema_version: 2}, {entry_ref: 'main'}, {code_commit: 'main'},
    {semantics: 'TRADING'}, {reading_hash: ''}, {lanes: null},
    {investment_authority: 'BUY'}, {research_authority: 'FULL'},
    {human_attention_authority: 'ACCEPTED'}, {signal_transition_authority: 'YES'}]) {
    assert.throws(() => validateShape({...state(), ...patch}));
  }
});
test('reference deduplication preserves conflicting descriptor failure', () => {
  assert.equal(references({a: source, b: {...source}}).length, 1);
  assert.throws(() => references({a: source, b: {...source, bytes: 12}}), /CONFLICTING/);
});
test('altered source, unknown paths and forged descriptors are not consumed', async () => {
  const reading = await openReading(transport(url => url.endsWith('/research.md') ? text + 'x' : fixture(url)).fetcher);
  await assert.rejects(() => reading.readFile(reading.references[0]), /INTEGRITY/);
  await assert.rejects(() => reading.readFile({...source, read_path: 'docs/other.md'}), /UNREGISTERED/);
  await assert.rejects(() => reading.readFile({...source, sha256: 'e'.repeat(64)}), /UNREGISTERED/);
});
test('hash mismatch with equal byte length is rejected', async () => {
  const reading = await openReading(transport(url => url.endsWith('/research.md') ? text.replace('not', 'bad') : fixture(url)).fetcher);
  await assert.rejects(() => reading.readFile(source), /INTEGRITY/);
});
test('HTTP failures are explicit and do not search an older reading', async () => {
  let count = 0;
  await assert.rejects(() => openReading(async () => { count++; return new Response('', {status: 429}); }), /HTTP_429/);
  assert.equal(count, 1);
});
test('read package byte bound is enforced with and without content-length', async () => {
  for (const headers of [{}, {'content-length': String(193 * 1024)}]) {
    await assert.rejects(() => openPinnedReading(R, async () => new Response('x'.repeat(193 * 1024), {headers})), /TOO_LARGE/);
  }
});
test('a wrong returned ref is rejected', async () => {
  await assert.rejects(() => openReading(transport(() => ({ref: 'refs/heads/main', object: {type: 'commit', sha: R}})).fetcher), /WRONG_READING_REF/);
});
test('optional consumers fail independently', async () => {
  const result = await loadModules({reading: async () => 'saved', health: () => { throw new Error('HTTP_503'); }});
  assert.equal(result.reading.status, 'READ'); assert.equal(result.health.status, 'GAP');
  assert.equal(result.health.reason, 'HTTP_503');
});
test('Quick reads bounded pages and preserves independent comment time and identity', async () => {
  const item = {id: 12, body: '## DAILY HOSTED QUICK 2026-09-25\n实际保存内容',
    html_url: `https://github.com/${REPO}/issues/575#issuecomment-12`,
    created_at: '2026-09-25T12:00:00Z', updated_at: '2026-09-26T01:00:00Z'};
  const {fetcher, calls} = transport(url => url.endsWith('/issues/575') ?
    {number: 575, html_url: `https://github.com/${REPO}/issues/575`, comments: 250, updated_at: item.updated_at} :
    url.endsWith('page=3') ? [item, {...item, id: 13, html_url: `https://github.com/${REPO}/issues/575#issuecomment-13`, body: '工程记录，不是研究'}] : []);
  const result = await readQuick(fetcher);
  assert.deepEqual(result.pages, [2, 3]); assert.equal(result.items[0].id, 12);
  assert.equal(result.items[0].updatedAt, item.updated_at);
  assert.equal(result.independentOfReading, true); assert.match(result.coverage, /NOT_COMPLETE/);
  assert.equal(calls.length, 3);
});
test('Quick issue or comment identity mismatch is a gap, not empty research', async () => {
  await assert.rejects(() => readQuick(transport(() => ({number: 297, comments: 0})).fetcher), /WRONG_QUICK/);
  const bad = {id: 9, body: '## DAILY HOSTED QUICK 2026-09-25\nx', html_url: 'https://example.org',
    created_at: '2026-09-25T00:00:00Z', updated_at: '2026-09-25T00:00:00Z'};
  await assert.rejects(() => readQuick(transport(url => url.endsWith('/issues/575') ?
    {number: 575, html_url: `https://github.com/${REPO}/issues/575`, comments: 1} : [bad]).fetcher), /INVALID_QUICK/);
});
test('health does not inherit pinned reading or infer state from issue title', async () => {
  const health = await readHealth(transport(() => ({number: 581,
    html_url: `https://github.com/${REPO}/issues/581`, title: 'closed',
    body: '真实缺口', updated_at: '2026-09-25T12:00:00Z'})).fetcher);
  assert.equal(health.text, '真实缺口'); assert.equal(health.independentOfReading, true);
  assert.equal(health.ref, undefined);
});
test('resume text references exact original, does not create acceptance', () => {
  const result = resumeText(R, source);
  assert.ok(result.includes(fileUrl(R, source.read_path)));
  assert.match(result, /不是接受研究或投资决定/);
});

import {locations, referenceMatches, watchSummary, companyMatches} from './presentation.mjs';
function descriptor(path, body) { return {read_path: path, bytes: Buffer.byteLength(body),
  sha256: createHash('sha256').update(body).digest('hex')}; }
function catalogueFixture(patch = data => data) {
  const company = {thscode: '600276.SH', assets: [{id: 'test-reference', source}], archives: [],
    human_acceptance: 'REFER_TO_EXACT_ORIGINAL_RECORD_NOT_TRANSFERRED'};
  const catalogue = patch({projection: {automatic_admission: false, companies: [company]}});
  const body = JSON.stringify(catalogue), index = descriptor('details/research/asset-reentry.json', body);
  const payload = state(); payload.research = {asset_reentry: {detail: index}};
  return {index, body, payload, ...transport(url => url.endsWith('/current-state.json') ? payload :
    url.endsWith('/asset-reentry.json') ? body : fixture(url))};
}
test('one locator retains all category aliases instead of dropping Research', () => {
  const [item] = references({lanes: {inbox: source}, research: {x: {...source, path: 'original/research.md'}}});
  assert.deepEqual(locations(item), ['lanes.inbox', 'research.x']);
  assert.equal(referenceMatches(item, 'research.x'), true);
});
test('verified existing company catalogue expands same-R reads once without accepting research', async () => {
  const fixture = catalogueFixture(), reading = await openPinnedReading(R, fixture.fetcher);
  await assert.rejects(() => reading.readFile(source), /UNREGISTERED/);
  const [first, second] = await Promise.all([reading.readAssets(), reading.readAssets()]);
  assert.equal(first, second); assert.equal(first.companies[0].thscode, '600276.SH');
  assert.equal(first.companies[0].human_acceptance, 'REFER_TO_EXACT_ORIGINAL_RECORD_NOT_TRANSFERRED');
  assert.equal((await reading.readFile(source)).text, text);
  assert.equal(fixture.calls.filter(url => url.endsWith('/asset-reentry.json')).length, 1);
  assert.ok(fixture.calls.every(url => url.includes(`/${R}/`)));
});
test('catalogue integrity failure cannot register a nested source', async () => {
  const fixture = catalogueFixture();
  const reader = await openPinnedReading(R, transport(url => url.endsWith('/current-state.json') ? fixture.payload :
    url.endsWith('/asset-reentry.json') ? fixture.body + ' ' : text).fetcher);
  await assert.rejects(() => reader.readAssets(), /INTEGRITY/);
  await assert.rejects(() => reader.readFile(source), /UNREGISTERED/);
});
test('catalogue failures are transactional and do not break the root reading', async () => {
  for (const patch of [
    data => { data.projection.automatic_admission = true; return data; },
    data => { data.projection.companies.push(data.projection.companies[0]); return data; },
    data => { data.projection.companies[0].thscode = 'name-only'; return data; },
    data => { data.projection.companies[0].assets.push({source: {...source, bytes: 1}}); return data; },
    data => { data.projection.companies[0].assets.push({source: {...source, read_path: 'x', repository: 'foreign/repo'}}); return data; },
    data => { data.projection.companies[0].assets.push({source: {...source, read_path: 'x', read_ref_rule: 'LATEST_MAIN'}}); return data; }
  ]) {
    const fixture = catalogueFixture(patch), reading = await openPinnedReading(R, fixture.fetcher);
    await assert.rejects(() => reading.readAssets());
    await assert.rejects(() => reading.readFile(source), /UNREGISTERED/);
    assert.equal(reading.payload.code_commit, M);
  }
});
test('missing optional company catalogue is a gap, not no research', async () => {
  const reading = await openReading(transport(fixture).fetcher);
  await assert.rejects(() => reading.readAssets(), /ASSET_INDEX_NOT_REGISTERED/);
  assert.equal((await reading.readFile(source)).text, text);
});
function comment(id, body, updated = '2026-09-25T12:00:00Z') {
  return {id, body, html_url: `https://github.com/${REPO}/issues/575#issuecomment-${id}`,
    created_at: '2026-09-25T10:00:00Z', updated_at: updated};
}
function quickTransport(rows) { return transport(url => url.endsWith('/issues/575') ?
  {number: 575, html_url: `https://github.com/${REPO}/issues/575`, comments: rows.length} : rows); }
test('nonstandard late appendices remain visible, not promoted into primary Quick results', async () => {
  const result = await readQuick(quickTransport([comment(1, '## DAILY HOSTED QUICK 2026-09-25\nOriginal'),
    comment(2, '## 迟到附录／更正\nNot a new main Quick'), comment(3, 'Engineering receipt')]).fetcher);
  assert.deepEqual(result.items.map(x => x.id), [1]);
  assert.deepEqual(result.supplements.map(x => x.id), [3, 2]);
});
test('duplicate supplemental IDs and unzoned or reversed clocks are rejected', async () => {
  for (const rows of [[comment(2, 'Supplement'), comment(2, 'Supplement')],
    [comment(3, 'Supplement', '2026-09-25T12:00:00')],
    [comment(4, 'Supplement', '2026-09-24T12:00:00Z')]]) {
    await assert.rejects(() => readQuick(quickTransport(rows).fetcher));
  }
});
test('health missing or unzoned update time does not silently pass', async () => {
  await assert.rejects(() => readHealth(transport(() => ({number: 581,
    html_url: `https://github.com/${REPO}/issues/581`, body: 'x', updated_at: '2026-09-25T12:00:00'})).fetcher), /WRONG_HEALTH/);
});
function watchItem(patch = {}) { return {watch_enabled: true, status: 'ACTIVE_ODDS_WATCH', price: '10',
  market_timestamp: '2026-09-24T15:00:00+08:00', triggered_conditions: [],
  next_unreached_condition: {attention_triggered: false, condition_state: 'ABOVE_CONDITION'}, ...patch}; }
function watchPayload(rows, count = rows.length) { return {lanes: {inbox: {last_qualified_result: {
  odds_watch: {report: {watch: {active_cases: rows, active_case_count: count}}}}}}}; }
test('five watches with one unread price are four evaluated, not five quiet', () => {
  const summary = watchSummary(watchPayload([watchItem(), watchItem(), watchItem(), watchItem(), watchItem({price: null})]));
  assert.deepEqual(summary.counts, {enabled: 5, evaluated: 4, triggered: 0, unknown: 1, inactive: 0});
});
test('missing condition results, invalid price, inactive and triggered watches stay distinct', () => {
  const summary = watchSummary(watchPayload([watchItem({triggered_conditions: null}), watchItem({price: ''}),
    watchItem({watch_enabled: false}), watchItem({triggered_conditions: [{attention_triggered: true}]})], 3));
  assert.deepEqual(summary.counts, {enabled: 3, evaluated: 1, triggered: 1, unknown: 2, inactive: 1});
  assert.equal(summary.countMismatch, false);
  assert.equal(watchSummary(watchPayload([], 5)).countMismatch, true);
  assert.equal(watchSummary({}).counts, null);
});
test('company search uses explicit saved identity and purpose, not inferred holdings', () => {
  const c = {thscode: '600276.SH', saved_watch: {company_name: '恒瑞医药'}, assets: [{id: 'research', purpose_note: '原研究'}]};
  assert.equal(companyMatches(c, '恒瑞'), true); assert.equal(companyMatches(c, '600276'), true);
  assert.equal(companyMatches(c, '持仓'), false);
});

test('one exact archived source survives the adapter without acquiring acceptance or Odds', async () => {
  // Actual 783-byte retained source at R=3c4818dc9ad7a068febb6889f53bf2546dccfeea.
  // Root/index envelopes below are SYNTHETIC, not a complete historical read-package replay.
  const savedR = '3c4818dc9ad7a068febb6889f53bf2546dccfeea';
  const body = '{"format":"research-commit-only-v0","human_acceptance":"NOT_ESTABLISHED_BY_THIS_OPERATION","information_bundle_hash":"a289d5776ec39068318b2feb277d60a71a4e68a6bc0af1853210a84ea53799a5","investment_authority":"NONE","market_status":"NOT_REQUESTED","odds_status":"NOT_COMPUTED","package_hash":"662bf206a1a3ec94d7889c6d1b00f2d378863c4487fcc2b56aff362103b859cc","publication_status":"LOCAL_ONLY_NOT_GITHUB_PUBLICATION","research_snapshot_id":"ea9b4e56-c998-5dcd-b8fa-3f1539612762","research_status":"COMMITTED","result":{"bytes":4704,"sha256":"bb1fc4634ca2d899ef0f69e4634cc26aa5d0df02bd04871cc8c5c0a00fc7f925"},"retention":{"bytes":214,"sha256":"2a766bea98166edaf5dcc7eb587f3e2bcaab0d1e3e33c47c82e464763d017e90"},"semantics":"COMMIT_OPERATION_NOT_RESEARCH_EXECUTION_OR_HUMAN_ACCEPTANCE"}\n';
  const path = 'sources/git/a3147841eeacb65c8cb4d4827bb7082e95bb6f63/commit.json';
  const exact = descriptor(path, body);
  assert.equal(exact.bytes, 783);
  assert.equal(exact.sha256, '08bb7d471162faf6948a2af579fde91f2897c0cb9a89d90f9cfe0ce8e9bb07bd');
  const payload = state(); payload.research = {retained_example: {source: exact}};
  const mock = transport(url => url.endsWith('/current-state.json') ? payload : body);
  const reading = await openPinnedReading(savedR, mock.fetcher), result = await reading.readFile(exact);
  const record = JSON.parse(result.text);
  assert.equal(record.research_status, 'COMMITTED');
  assert.equal(record.human_acceptance, 'NOT_ESTABLISHED_BY_THIS_OPERATION');
  assert.equal(record.odds_status, 'NOT_COMPUTED');
  assert.equal(record.investment_authority, 'NONE');
  assert.ok(mock.calls.every(url => url.includes(`/${savedR}/`)));
});
