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
    url.endsWith('page=3') ? [item, {body: '工程记录，不是研究'}] : []);
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
