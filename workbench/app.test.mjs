/** Controller integration tests: actual app/reader with a minimal DOM sink.
 * Synthetic GET responses and controlled promises; NOT browser, CSS, auth,
 * secure-context, MIME/CSP, clipboard permission or live Sites acceptance.
 * No network, extra package, runtime export or production fault-injection route.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {setTimeout as pause} from 'node:timers/promises';
import {REPO, READ_REF} from './reading.mjs';

const R1 = 'a'.repeat(40), R2 = 'b'.repeat(40), M = 'c'.repeat(40);
const hash = text => createHash('sha256').update(text).digest('hex');
const json = value => new Response(JSON.stringify(value));
function deferred() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return {promise, resolve};
}
// Only the DOM methods used as output sinks by app.mjs. Not an HTML engine.
class Node {
  constructor(tag = '#text', text = '') { this.tagName = tag; this.children = []; this.text = text; this.value = ''; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.text = ''; this.children = children; }
  insertBefore(child, previous) {
    const index = this.children.indexOf(previous);
    assert.ok(index >= 0); this.children.splice(index, 0, child);
  }
  get lastChild() { return this.children.at(-1); }
  set textContent(text) { this.text = String(text); this.children = []; }
  get textContent() { return this.text + this.children.map(n => n.textContent ?? String(n)).join(''); }
  setAttribute(name, value) { this[name] = value; }
  scrollIntoView() {} // This suite does not assert scrolling/layout.
}
function find(node, predicate) {
  if (predicate(node)) return node;
  for (const child of node.children ?? []) {
    const result = find(child, predicate); if (result) return result;
  }
}
async function waitFor(predicate) {
  for (let i = 0; i < 1000; i++) { if (predicate()) return; await pause(1); }
  assert.fail('App did not settle within the bounded local test');
}
let instance = 0;
async function withApp(run, fixture = {}) {
  const ids = Object.fromEntries(['nav', 'modules', 'detail', 'content', 'heading', 'subtitle', 'refresh', 'identity']
    .map(id => [id, new Node('div')]));
  const calls = [], completions = [], overrides = new Map();
  const texts = {first: 'FIRST ORIGINAL\n', second: 'SECOND ORIGINAL\n'};
  let activeRef = R1;
  const descriptor = (ref, name) => {
    const text = `${ref}:${texts[name]}`;
    return {read_path: `docs/odds-${name}.txt`, bytes: Buffer.byteLength(text), sha256: hash(text)};
  };
  const body = (ref, name) => `${ref}:${texts[name]}`;
  const file = (ref, name) => `https://raw.githubusercontent.com/${REPO}/${ref}/docs/odds-${name}.txt`;
  const fetcher = async (url, options) => {
    assert.equal(options.method, 'GET'); assert.equal(options.credentials, 'omit');
    assert.equal(options.body, undefined); assert.equal(options.headers?.Authorization, undefined);
    calls.push(url);
    let result;
    if (overrides.has(url)) result = await overrides.get(url)();
    else if (url.endsWith(`/git/ref/heads/${READ_REF}`)) result = json({ref: `refs/heads/${READ_REF}`, object: {type: 'commit', sha: activeRef}});
    else if (url.endsWith('/current-state.json')) {
      const ref = url.split('/').at(-2);
      assert.ok([R1, R2].includes(ref));
      result = json({schema_version: 1, entry_ref: READ_REF, code_commit: M,
        semantics: 'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',
        reading_hash: 'd'.repeat(64), lanes: {}, checks: {},
        signal_transition_authority: 'NONE', human_attention_authority: 'NONE',
        research_authority: 'NONE', investment_authority: 'NONE',
        research: {first: descriptor(ref, 'first'), second: descriptor(ref, 'second')},
        ...(fixture.payload?.(ref) || {})});
    } else if (url.endsWith('/issues/575')) result = json({number: 575, comments: fixture.comments?.length || 0,
      html_url: `https://github.com/${REPO}/issues/575`});
    else if (url.includes('/issues/575/comments?')) result = json(fixture.comments || []);
    else if (url.endsWith('/issues/581')) result = json({number: 581, title: 'Fixture', body: 'Synthetic health',
      html_url: `https://github.com/${REPO}/issues/581`, updated_at: '2026-09-25T00:00:00Z'});
    else if (fixture.files && url.startsWith(`https://raw.githubusercontent.com/${REPO}/`)) {
      const relative = url.slice(`https://raw.githubusercontent.com/${REPO}/`.length);
      const ref = relative.slice(0, 40), path = relative.slice(41);
      const text = fixture.files(ref)[path];
      assert.notEqual(text, undefined, `Unexpected fixture source: ${path}`); result = new Response(text);
    } else {
      const match = url.match(/\/([ab]{40})\/docs\/odds-(first|second)\.txt$/);
      assert.ok(match, `Unexpected transport: ${url}`); result = new Response(body(match[1], match[2]));
    }
    completions.push(url); return result;
  };
  const globals = {document: {head: new Node('head'), getElementById: id => ids[id], createElement: tag => new Node(tag),
    createTextNode: text => new Node('#text', text)}, fetch: fetcher};
  const saved = Object.fromEntries(Object.keys(globals).map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
  try {
    for (const [key, value] of Object.entries(globals)) Object.defineProperty(globalThis, key, {value, configurable: true});
    await import(`./app.mjs?controller-test=${++instance}`);
    await waitFor(() => ids.refresh.disabled === false);
    const tab = label => {
      const item = find(ids.nav, n => n.tagName === 'button' && n.textContent === label);
      assert.ok(item, label); return item.onclick();
    };
    const select = name => {
      const item = find(ids.content, n => n.tagName === 'button' && n.textContent === `读取 · docs/odds-${name}.txt`);
      assert.ok(item, name); return item.onclick();
    };
    const initialText = ids.content.textContent;
    tab('Odds / Watch');
    await run({initialText, ids, tab, select, calls, completions, overrides, file, body,
      setRef(ref) { activeRef = ref; }, refresh: () => ids.refresh.onclick()});
  } finally {
    for (const key of Object.keys(globals)) {
      if (saved[key]) Object.defineProperty(globalThis, key, saved[key]); else delete globalThis[key];
    }
  }
}

for (const outcome of ['success', 'failure']) test(`late first ${outcome} cannot replace newer selected original`, async () => {
  await withApp(async ({ids, select, overrides, file, body, completions}) => {
    const pending = deferred(); overrides.set(file(R1, 'first'), () => pending.promise);
    const first = select('first');
    try {
      await select('second'); assert.ok(ids.detail.textContent.includes(body(R1, 'second')));
    } finally { pending.resolve(outcome === 'success' ? new Response(body(R1, 'first')) : new Response('', {status: 503})); }
    await first;
    assert.ok(completions.indexOf(file(R1, 'second')) < completions.indexOf(file(R1, 'first')));
    assert.ok(ids.detail.textContent.includes(body(R1, 'second')));
    assert.ok(!ids.detail.textContent.includes(body(R1, 'first')));
    assert.ok(!ids.detail.textContent.includes('HTTP_503'));
  });
});
test('cross-R refresh clears detail and rejects late old-R response without mixing requests', async () => {
  await withApp(async ({ids, select, overrides, file, body, setRef, refresh, calls}) => {
    const pending = deferred(); overrides.set(file(R1, 'first'), () => pending.promise);
    const old = select('first');
    try {
      setRef(R2); const refreshed = refresh(); assert.equal(ids.detail.textContent, ''); await refreshed;
      assert.ok(ids.identity.textContent.includes(R2)); await select('second');
    } finally { pending.resolve(new Response(body(R1, 'first'))); }
    await old;
    assert.ok(ids.detail.textContent.includes(body(R2, 'second')));
    assert.ok(!ids.detail.textContent.includes(body(R1, 'first')));
    assert.equal(calls.filter(url => url.includes('/git/ref/')).length, 2);
    assert.ok(calls.includes(file(R1, 'first')) && calls.includes(file(R2, 'second')));
    assert.ok(!calls.includes(file(R2, 'first')) && !calls.includes(file(R1, 'second')));
  });
});
test('navigation invalidates a pending original rather than displaying it on another tab', async () => {
  await withApp(async ({ids, select, overrides, file, body, tab}) => {
    const pending = deferred(); overrides.set(file(R1, 'first'), () => pending.promise);
    const old = select('first');
    try { tab('系统健康'); assert.equal(ids.detail.textContent, ''); }
    finally { pending.resolve(new Response(body(R1, 'first'))); }
    await old; assert.equal(ids.detail.textContent, ''); assert.equal(ids.heading.textContent, '系统健康');
  });
});
test('equal-length corruption shows integrity failure, no original and no copy-success control', async () => {
  await withApp(async ({ids, select, overrides, file, body}) => {
    await select('second'); assert.ok(ids.detail.textContent.includes(body(R1, 'second')));
    overrides.set(file(R1, 'first'), () => new Response(body(R1, 'first').replace('FIRST', 'WRONG')));
    await select('first');
    assert.ok(ids.detail.textContent.includes('FILE_INTEGRITY_MISMATCH'));
    assert.ok(!ids.detail.textContent.includes(body(R1, 'second')));
    assert.ok(!find(ids.detail, n => n.tagName === 'button'));
  });
});

// The actual saved manual-heading case previously disappeared from the main view.
// This is a bounded source fragment fixture, not a live research invocation.
test('manual Quick is visible as research, not lost under nonstandard supplements', async () => {
  const text = '## MANUAL E2E HOSTED QUICK 2026-09-25\n\n# 实际研究交付\n\n## 结论\n\n这是可选Full建议，不是买入建议；原因仍有UNKNOWN。\n\n## 范围\n\n未开展Full。';
  await withApp(async ({ids, tab, initialText}) => {
    assert.ok(initialText.includes('手动 Quick'));
    assert.ok(initialText.includes('结论开头 · 原文摘录'));
    assert.ok(initialText.includes('这是可选Full建议，不是买入建议；原因仍有UNKNOWN。'));
    assert.ok(!initialText.includes('本次读取范围没有可识别的 Quick'));
    tab('注意力');
    assert.ok(ids.content.textContent.includes('未开展Full。'));
    assert.ok(ids.identity.textContent.includes('北京时间'));
  }, {comments: [{id: 5829920878, body: text,
    html_url: `https://github.com/${REPO}/issues/575#issuecomment-5829920878`,
    created_at: '2026-09-25T09:14:34Z', updated_at: '2026-09-25T09:14:34Z'}]});
});
test('untrusted text stays literal in paragraph display; no HTML/image execution nodes', async () => {
  await withApp(async ({ids, overrides, tab}) => {
    const url = `https://api.github.com/repos/${REPO}/issues/581`;
    overrides.set(url, () => json({number:581,title:'Health',body:'# Test\n\n<script>bad()</script><img src=x onerror=bad()>',
      updated_at:'2026-09-25T00:00:00Z',html_url:`https://github.com/${REPO}/issues/581`}));
    await ids.refresh.onclick(); tab('系统健康');
    assert.ok(ids.content.textContent.includes('<script>bad()</script>'));
    assert.ok(!find(ids.content,n=>['script','img','iframe'].includes(n.tagName)));
  });
});

function continuityFixture() {
  const texts = {'original.json': '{"note":"synthetic request"}', 'response.md': '## 既有回应\n\n仅针对原版本，不是新接受。',
    'research.md': '# 原研究\n\n保留研究假设。', 'correction.md': '# 方法更正\n\n旧梯度不得自动激活。'};
  const source = (name, ref) => ({read_path: `sources/${name}`, path: name, ref,
    git_blob: 'e'.repeat(40), bytes: Buffer.byteLength(texts[name]), sha256: hash(texts[name])});
  const rows = ref => {
    const old = {request_id: '1'.repeat(64), security_id: '600276.SH', ticker: '600276',
      as_of: '2026-09-01T01:00:00Z', terminal_state: 'DEEPEN_REQUIRED', reason: '旧版请求',
      source: source('original.json', ref), resolution: source('response.md', ref)};
    const active = {...old, request_id: '2'.repeat(64), reason: '新版明确请求；不是沿用旧版接受。', resolution: null};
    return {old, active};
  };
  const company = ref => ({thscode: '600276.SH', saved_watch: {company_name: '恒瑞医药'},
    archives: [], human_acceptance: 'REFER_TO_EXACT_ORIGINAL_RECORD_NOT_TRANSFERRED', assets: [
      {id: 'original-research', use: 'RETAINED_RESEARCH_PACKAGE', source: source('research.md', ref)},
      {id: 'human-old', use: 'HUMAN_DECISION_CHECKPOINT', source: source('response.md', ref)},
      {id: 'correction', use: 'RESEARCH_CORRECTION', source: source('correction.md', ref)}]});
  const catalogue = ref => JSON.stringify({projection: {automatic_admission: false, companies: [company(ref)]}});
  return {
    payload(ref) {
      const {active, old} = rows(ref), text = catalogue(ref);
      return {pending: [active], research: {
        handoffs: {active: [active], resolved_history: [old], background: [], gaps: [],
          registration_scope: 'EXPLICIT_INPUTS_ONLY_NOT_ALL_RESEARCH_OR_ALL_MARKET'},
        asset_reentry: {structured: {read_path: 'details/research/asset-reentry.json', bytes: Buffer.byteLength(text), sha256: hash(text)}}}};
    },
    files(ref) { return Object.fromEntries([...Object.entries(texts).map(([name, text]) => [`sources/${name}`, text]),
      ['details/research/asset-reentry.json', catalogue(ref)]]); }
  };
}

test('actual controller: pending item to same-company correction/original/response and exact copy; refreshing does not carry old selection', async () => {
  await withApp(async ({ids, tab, calls, setRef, refresh}) => {
    tab('注意力');
    assert.ok(ids.content.textContent.includes('明确待你回应（1）'));
    assert.ok(ids.content.textContent.includes('已有处置记录（1）'));
    const open = find(ids.content, n => n.tagName === 'button' && n.textContent === '恢复这个事项');
    open.onclick();
    await waitFor(() => ids.content.textContent.includes('先看更正与方法限制'));
    assert.ok(ids.content.textContent.includes('新版明确请求'));
    const text = ids.content.textContent;
    assert.ok(text.indexOf('先看更正与方法限制') < text.indexOf('已有研究与条件版本'));
    assert.ok(text.indexOf('已有研究与条件版本') < text.indexOf('你的历史回应（不转移接受）'));
    const original = find(ids.content, n => n.tagName === 'button' && n.textContent === '读取 · 精确原请求');
    await original.onclick(); assert.ok(ids.detail.textContent.includes('synthetic request'));
    const reply = find(ids.content, n => n.tagName === 'button' && n.textContent === '读取 · response.md');
    await reply.onclick(); assert.ok(ids.detail.textContent.includes('仅针对原版本，不是新接受。'));
    const copy = find(ids.content, n => n.tagName === 'button' && n.textContent === '复制事项接续（未写回）');
    await copy.onclick();
    assert.ok(ids.content.textContent.includes('新的回应尚未提供'));
    assert.ok(ids.content.textContent.includes('2'.repeat(64)));
    assert.ok(ids.content.textContent.includes(`/blob/${R1}/sources/response.md`));
    assert.ok(ids.content.textContent.includes('明确')); // no click-based closure
    setRef(R2); await refresh();
    assert.ok(!ids.content.textContent.includes('当前事项 ·'));
    assert.ok(!ids.content.textContent.includes('reading_commit'));
    assert.equal(ids.detail.textContent, ''); tab('注意力');
    assert.ok(ids.content.textContent.includes('明确待你回应（1）'));
    assert.ok(calls.filter(u => u.includes('/sources/')).every(u => u.includes(`/${R1}/`)));
  }, continuityFixture());
});

test('actual controller: Quick outage does not hide a registered request; history opens its own bound resolution', async () => {
  await withApp(async ({ids, overrides, refresh, tab}) => {
    overrides.set(`https://api.github.com/repos/${REPO}/issues/575`, () => new Response('', {status: 503}));
    await refresh(); tab('注意力');
    assert.ok(ids.content.textContent.includes('明确待你回应（1）'));
    assert.ok(ids.content.textContent.includes('研究更新：本次未取得'));
    const group = find(ids.content, n => n.tagName === 'details' && n.children[0]?.textContent === '已有处置记录（1）');
    find(group, n => n.tagName === 'button' && n.textContent === '恢复这个事项').onclick();
    const originalReply = find(ids.content, n => n.tagName === 'button' && n.textContent === '读取 · 此版本已登记的处置');
    assert.ok(originalReply); await originalReply.onclick();
    assert.ok(ids.detail.textContent.includes('仅针对原版本，不是新接受。'));
    assert.ok(!find(ids.content, n => n.tagName === 'button' && n.textContent === '标记已处理'));
  }, continuityFixture());
});

test('actual controller: catalogue error preserves the selected original and a response read failure never invents closure', async () => {
  await withApp(async ({ids, overrides, tab}) => {
    overrides.set(`https://raw.githubusercontent.com/${REPO}/${R1}/details/research/asset-reentry.json`, () => new Response('', {status: 503}));
    tab('注意力');
    const group = find(ids.content, n => n.tagName === 'details' && n.children[0]?.textContent === '已有处置记录（1）');
    find(group, n => n.tagName === 'button').onclick();
    await waitFor(() => ids.content.textContent.includes('公司研究目录：本次未取得'));
    const original = find(ids.content, n => n.tagName === 'button' && n.textContent === '读取 · 精确原请求');
    await original.onclick(); assert.ok(ids.detail.textContent.includes('synthetic request'));
    overrides.set(`https://raw.githubusercontent.com/${REPO}/${R1}/sources/response.md`, () => new Response('', {status: 503}));
    const reply = find(ids.content, n => n.tagName === 'button' && n.textContent === '读取 · 此版本已登记的处置');
    await reply.onclick(); assert.ok(ids.detail.textContent.includes('HTTP_503'));
    tab('注意力'); assert.ok(ids.content.textContent.includes('已有处置记录（1）'));
    assert.ok(ids.content.textContent.includes('明确待你回应（1）'));
  }, continuityFixture());
});
