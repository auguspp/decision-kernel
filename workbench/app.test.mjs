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
        research: {first: descriptor(ref, 'first'), second: descriptor(ref, 'second')}});
    } else if (url.endsWith('/issues/575')) result = json({number: 575, comments: fixture.comments?.length || 0,
      html_url: `https://github.com/${REPO}/issues/575`});
    else if (url.includes('/issues/575/comments?')) result = json(fixture.comments || []);
    else if (url.endsWith('/issues/581')) result = json({number: 581, title: 'Fixture', body: 'Synthetic health',
      html_url: `https://github.com/${REPO}/issues/581`, updated_at: '2026-09-25T00:00:00Z'});
    else {
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
