/** Read-only GitHub consumer. No tokens, writes, research, or automatic polling.
 * One Reading holds one immutable R; issue observations retain separate clocks.
 * This checks transport/shape and selected-file bytes, NOT canonical reading_hash.
 */
export const REPO = 'auguspp/decision-kernel';
export const READ_REF = 'read-model/current-state';
// Actual saved news (~534KB) and sector context (~815KB) exceed the old 512KiB cap.
export const FILE_LIMIT = 1024 * 1024;
const API = `https://api.github.com/repos/${REPO}`;
const RAW = `https://raw.githubusercontent.com/${REPO}`;
const AUTHORITY = ['signal_transition_authority', 'human_attention_authority',
  'research_authority', 'investment_authority'];
const SHA = /^[0-9a-f]{40}$/;
const HASH = /^[0-9a-f]{64}$/;
const decoder = new TextDecoder('utf-8', {fatal: true});

function validClock(value) {
  return typeof value === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));
}
function require(ok, reason) { if (!ok) throw new Error(reason); }
export function commit(value) {
  require(typeof value === 'string' && SHA.test(value), 'UNPINNED_COMMIT');
  return value;
}
export function safePath(value) {
  require(typeof value === 'string' && value.length > 0 &&
    !/[\\%?#\x00-\x1f\x7f]/.test(value) &&
    value.split('/').every(p => p && p !== '.' && p !== '..'), 'UNSAFE_PATH');
  return value;
}
function escapedPath(path) { return safePath(path).split('/').map(encodeURIComponent).join('/'); }
export function fileUrl(ref, path) {
  return `https://github.com/${REPO}/blob/${commit(ref)}/${escapedPath(path)}`;
}
export function validateShape(value) {
  require(value && typeof value === 'object' && !Array.isArray(value), 'INVALID_READING');
  require(value.schema_version === 1 && value.entry_ref === READ_REF, 'UNSUPPORTED_READING');
  require(value.semantics === 'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',
    'UNSUPPORTED_SEMANTICS');
  commit(value.code_commit);
  require(HASH.test(value.reading_hash || ''), 'MISSING_DECLARED_READING_HASH');
  require(AUTHORITY.every(k => value[k] === 'NONE'), 'READING_AUTHORITY_MISMATCH');
  require(value.lanes && typeof value.lanes === 'object' && !Array.isArray(value.lanes), 'MISSING_LANES');
  return value;
}

async function bytes(url, fetcher, limit) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetcher(url, {method: 'GET', credentials: 'omit',
      redirect: 'error', referrerPolicy: 'no-referrer', cache: 'no-store', signal: controller.signal});
    require(response.ok, `HTTP_${response.status}`);
    const declared = response.headers.get('content-length');
    require(declared === null || Number(declared) <= limit, 'RESPONSE_TOO_LARGE');
    require(response.body, 'EMPTY_RESPONSE');
    const reader = response.body.getReader();
    const chunks = []; let length = 0;
    try {
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        length += value.byteLength;
        require(length <= limit, 'RESPONSE_TOO_LARGE');
        chunks.push(value);
      }
    } catch (error) { await reader.cancel().catch(() => {}); throw error; }
    finally { reader.releaseLock(); }
    const result = new Uint8Array(length); let offset = 0;
    for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.length; }
    return result;
  } finally { clearTimeout(timer); }
}
async function json(url, fetcher, limit = 1024 * 1024) {
  return JSON.parse(decoder.decode(await bytes(url, fetcher, limit)));
}
function deepFreeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value); Object.values(value).forEach(deepFreeze);
  }
  return value;
}
async function sha256(raw) {
  require(typeof globalThis.crypto?.subtle?.digest === 'function',
    'WEB_CRYPTO_UNAVAILABLE：当前环境无法执行 SHA-256 校验；目录与原件未通过核验。请在支持 Web Crypto 的安全上下文中复验，不要跳过校验。');
  return Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', raw)),
    b => b.toString(16).padStart(2, '0')).join('');
}

/** Descriptor inventory only: finding a locator does not mean reading its body. */
export function references(payload) {
  const found = new Map();
  function visit(value, location = '') {
    if (!value || typeof value !== 'object') return;
    if (!Array.isArray(value) && typeof value.read_path === 'string') {
      safePath(value.read_path);
      const previous = found.get(value.read_path);
      if (previous) {
        require(previous.sha256 === value.sha256 && previous.bytes === value.bytes,
          'CONFLICTING_FILE_DESCRIPTOR');
        previous.locations.push(location);
      } else found.set(value.read_path, {...value, location, locations: [location]});
    }
    for (const [key, child] of Object.entries(value)) {
      if (child && typeof child === 'object') visit(child, location ? `${location}.${key}` : key);
    }
  }
  visit(payload);
  return [...found.values()];
}

export async function openReading(fetcher = globalThis.fetch) {
  const ref = await json(`${API}/git/ref/heads/${READ_REF}`, fetcher);
  require(ref.ref === `refs/heads/${READ_REF}` && ref.object?.type === 'commit', 'WRONG_READING_REF');
  return openPinnedReading(commit(ref.object.sha), fetcher);
}
export async function openPinnedReading(ref, fetcher = globalThis.fetch) {
  commit(ref);
  const payload = validateShape(await json(`${RAW}/${ref}/current-state.json`, fetcher, 192 * 1024));
  const inventory = references(payload);
  const byPath = new Map(inventory.map(item => [item.read_path, item]));
  deepFreeze(payload); deepFreeze(inventory);
  async function readFile(descriptor) {
    const known = byPath.get(descriptor?.read_path);
    require(known && known.sha256 === descriptor.sha256 && known.bytes === descriptor.bytes,
      'UNREGISTERED_FILE');
    require(Number.isSafeInteger(known.bytes) && known.bytes >= 0 && known.bytes <= FILE_LIMIT &&
      HASH.test(known.sha256 || ''), 'UNSUPPORTED_FILE_DESCRIPTOR');
    const raw = await bytes(`${RAW}/${ref}/${escapedPath(known.read_path)}`, fetcher, FILE_LIMIT);
    require(raw.byteLength === known.bytes && await sha256(raw) === known.sha256, 'FILE_INTEGRITY_MISMATCH');
    return Object.freeze({text: decoder.decode(raw), ref, path: known.read_path,
      url: fileUrl(ref, known.read_path), sha256: known.sha256,
      validation: 'SELECTED_FILE_BYTES_SHA256_MATCH'});
  }
  let assetsPromise;
  return Object.freeze({ref, payload, references: inventory,
    checkedAt: new Date().toISOString(),
    validation: 'TRANSPORT_AND_SHAPE_ONLY_CANONICAL_READING_HASH_NOT_RECOMPUTED',
    readFile,
    // The only expandable catalogue is the existing, byte-verified asset reentry
    // projection. Its nested locators remain on this R; no arbitrary URL loader.
    readAssets() {
      if (!assetsPromise) assetsPromise = (async () => {
        const descriptor = byPath.get('details/research/asset-reentry.json');
        require(descriptor, 'ASSET_INDEX_NOT_REGISTERED');
        const file = await readFile(descriptor);
        const data = JSON.parse(file.text), projection = data?.projection;
        require(projection?.automatic_admission === false && Array.isArray(projection.companies),
          'UNSUPPORTED_ASSET_INDEX');
        const companies = projection.companies;
        require(companies.every(c => c && /^[0-9]{6}\.(SH|SZ|BJ)$/.test(c.thscode) &&
          Array.isArray(c.assets) && Array.isArray(c.archives)), 'INVALID_COMPANY_INDEX');
        require(new Set(companies.map(c => c.thscode)).size === companies.length, 'DUPLICATE_COMPANY');
        const nested = references(projection);
        for (const item of nested) {
          require(Number.isSafeInteger(item.bytes) && item.bytes >= 0 && HASH.test(item.sha256 || ''),
            'INVALID_NESTED_DESCRIPTOR');
          require(!item.repository || item.repository === REPO, 'FOREIGN_SOURCE_REPOSITORY');
          require(!item.read_ref_rule || item.read_ref_rule === 'USE_THE_SAME_PINNED_READING_COMMIT',
            'UNSUPPORTED_SOURCE_REF_RULE');
          const previous = byPath.get(item.read_path);
          require(!previous || (previous.sha256 === item.sha256 && previous.bytes === item.bytes),
            'CONFLICTING_FILE_DESCRIPTOR');
        }
        // Commit the read allowlist only after the whole expansion is checked.
        deepFreeze(data); deepFreeze(nested);
        for (const item of nested) if (!byPath.has(item.read_path)) byPath.set(item.read_path, item);
        return deepFreeze({companies, file, references: nested,
          meaning: 'SAVED_COMPANY_ASSOCIATIONS_NOT_HOLDINGS_OR_CURRENT_ACCEPTANCE'});
      })();
      return assetsPromise;
    }
  });
}

/** Independent mutable issue observation: never presented as part of pinned R. */
export async function readHealth(fetcher = globalThis.fetch) {
  const item = await json(`${API}/issues/581`, fetcher);
  require(item.number === 581 && item.html_url === `https://github.com/${REPO}/issues/581` &&
    typeof item.body === 'string' && validClock(item.updated_at), 'WRONG_HEALTH_ISSUE');
  return Object.freeze({title: item.title, text: item.body, updatedAt: item.updated_at,
    observedAt: new Date().toISOString(), url: item.html_url, independentOfReading: true});
}

/** Latest at most two comment pages, explicit bounded coverage; no all-history claim. */
export async function readQuick(fetcher = globalThis.fetch) {
  const issue = await json(`${API}/issues/575`, fetcher);
  require(issue.number === 575 && issue.html_url === `https://github.com/${REPO}/issues/575` &&
    Number.isSafeInteger(issue.comments) && issue.comments >= 0, 'WRONG_QUICK_ISSUE');
  const last = Math.max(1, Math.ceil(issue.comments / 100));
  const pages = last > 1 ? [last - 1, last] : [last];
  const rows = [];
  for (const page of pages) {
    const batch = await json(`${API}/issues/575/comments?per_page=100&page=${page}`, fetcher, 8 * 1024 * 1024);
    require(Array.isArray(batch) && batch.length <= 100, 'INVALID_COMMENT_PAGE');
    rows.push(...batch);
  }
  // Preserve all other comments as unclassified supplemental records. A late
  // correction must not vanish because it does not use the main Quick heading.
  const records = rows.map(row => {
    require(row && typeof row.body === 'string' && Number.isSafeInteger(row.id) && row.id > 0 &&
      row.html_url === `https://github.com/${REPO}/issues/575#issuecomment-${row.id}` &&
      validClock(row.updated_at) && validClock(row.created_at) &&
      Date.parse(row.updated_at) >= Date.parse(row.created_at), 'INVALID_QUICK_IDENTITY');
    return {id: row.id, text: row.body, url: row.html_url,
      createdAt: row.created_at, updatedAt: row.updated_at};
  });
  require(new Set(records.map(row => row.id)).size === records.length, 'MOVING_COMMENT_PAGES');
  records.sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt) || b.id - a.id);
  const primary = row => /^## DAILY HOSTED QUICK \d{4}-\d{2}-\d{2}(?:\s|$)/.test(row.text);
  const items = records.filter(primary), supplements = records.filter(row => !primary(row));
  return deepFreeze({items, supplements, pages, observedAt: new Date().toISOString(),
    issueUpdatedAt: issue.updated_at, independentOfReading: true,
    coverage: 'BOUNDED_PAGES_NOT_COMPLETE_HISTORY_OR_TODAY_COMPLETENESS'});
}

/** Optional consumers fail independently. Results are memory-only view state. */
export async function loadModules(loaders) {
  const entries = Object.entries(loaders);
  const outcomes = await Promise.allSettled(entries.map(([, load]) => Promise.resolve().then(load)));
  return Object.fromEntries(outcomes.map((result, index) => [entries[index][0],
    result.status === 'fulfilled' ? {status: 'READ', value: result.value} :
      {status: 'GAP', reason: String(result.reason?.message || 'READ_FAILED')} ]));
}
export function resumeText(ref, descriptor) {
  const url = fileUrl(ref, descriptor.read_path);
  return `请从当前项目研究入口恢复以下已保存材料，先读适用更正并说明实际范围，不自动开展Full、重算Odds或交易。\n固定读取版本：${ref}\n原件：${url}\n这是阅读/接续请求，不是接受研究或投资决定。`;
}

/** One explicit, independent status observation; never a dispatch or a timer.
 * The bounded list can expose an in-flight/failing attempt absent from pinned R.
 * It does not prove publication, full history, or owner authorization to execute.
 */
export async function readNewsExecution(fetcher = globalThis.fetch) {
  const data = await json(`${API}/actions/workflows/radar-newsnow-daily.yml/runs?branch=main&per_page=20`, fetcher);
  const observedAt = new Date().toISOString(), rows = data?.workflow_runs;
  require(Array.isArray(rows) && rows.length <= 20 && Number.isSafeInteger(data.total_count) &&
    data.total_count >= rows.length && (rows.length > 0 || data.total_count === 0), 'INCOMPLETE_NEWS_RUN_LIST');
  require(new Set(rows.map(r => r?.id)).size === rows.length, 'DUPLICATE_NEWS_RUN');
  for (const r of rows) {
    require(r && Number.isSafeInteger(r.id) && r.id > 0 &&
      r.html_url === `https://github.com/${REPO}/actions/runs/${r.id}` &&
      r.path === '.github/workflows/radar-newsnow-daily.yml' && r.head_branch === 'main' &&
      r.repository?.full_name === REPO && r.head_repository?.full_name === REPO &&
      SHA.test(r.head_sha || '') && Number.isSafeInteger(r.run_attempt) && r.run_attempt > 0 &&
      ['workflow_dispatch', 'workflow_run'].includes(r.event) && validClock(r.created_at) &&
      validClock(r.updated_at) && Date.parse(r.updated_at) >= Date.parse(r.created_at) &&
      Date.parse(r.updated_at) <= Date.parse(observedAt) && typeof r.status === 'string' &&
      (r.conclusion === null || typeof r.conclusion === 'string'), 'UNQUALIFIED_NEWS_RUN');
  }
  const latest = [...rows].sort((a,b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id)[0];
  // Return only explicit run metadata, never logs, credentials, or inferred stages.
  const pick = r => r ? Object.fromEntries(['id','html_url','path','head_sha','event','run_attempt',
    'created_at','updated_at','status','conclusion'].map(k => [k,r[k]])) : null;
  return deepFreeze({latest: pick(latest), observedAt, independentOfReading: true,
    scope: 'LATEST_CREATED_IN_BOUNDED_MAIN_QUERY_NOT_ALL_RUNNING_JOBS', count: rows.length});
}

/** Complete bounded native Inbox observation, independent of R. No clean zero on partial pages. */
export async function readInboxComments(fetcher = globalThis.fetch) {
  const root = `${API}/issues/601`;
  const before = await json(root, fetcher);
  const validIssue = v => v?.number === 601 && !v.pull_request && v.user?.id === 83357964 &&
    v.html_url === `https://github.com/${REPO}/issues/601` && Number.isSafeInteger(v.comments) &&
    v.comments >= 0 && v.comments <= 500 && validClock(v.updated_at);
  require(validIssue(before), 'INBOX_UNAVAILABLE_OR_OVER_500_COMMENTS');
  const rows = [], pages = Math.max(1,Math.ceil(before.comments/100));
  for (let page=1;page<=pages;page++) {
    const part=await json(`${root}/comments?per_page=100&page=${page}`,fetcher,2*1024*1024);
    require(Array.isArray(part) && part.length<=100,'INVALID_INBOX_PAGE'); rows.push(...part);
  }
  const after=await json(root,fetcher);
  require(validIssue(after) && after.comments===before.comments && after.updated_at===before.updated_at &&
    rows.length===before.comments && new Set(rows.map(c=>c?.id)).size===rows.length,'INBOX_CHANGED_OR_PARTIAL');
  for(const c of rows) require(Number.isSafeInteger(c?.id) && c.id>0 && typeof c.body==='string' && c.body.length<=16384 &&
    c.html_url===`https://github.com/${REPO}/issues/601#issuecomment-${c.id}` &&
    validClock(c.created_at) && validClock(c.updated_at) && Date.parse(c.updated_at)>=Date.parse(c.created_at), 'INVALID_INBOX_COMMENT');
  rows.sort((a,b)=>a.id-b.id);
  return deepFreeze({comments:rows,observedAt:new Date().toISOString(),independentOfReading:true});
}

/** A trusted Inbox receipt can refer to an already-retained Git document.
 * Exact bytes only, not a new Research/acceptance assessment or a URL executor.
 */
export async function readQuickResult(locator, fetcher = globalThis.fetch) {
  commit(locator?.commit); safePath(locator?.path);
  require(locator.path.startsWith('docs/') && /\.(md|txt|json)$/.test(locator.path) &&
    HASH.test(locator.sha256 || '') && Number.isSafeInteger(locator.bytes) &&
    locator.bytes>0 && locator.bytes<=FILE_LIMIT,'INVALID_QUICK_RESULT');
  const raw=await bytes(`${RAW}/${locator.commit}/${escapedPath(locator.path)}`,fetcher,FILE_LIMIT);
  require(raw.byteLength===locator.bytes && await sha256(raw)===locator.sha256,'QUICK_RESULT_INTEGRITY_MISMATCH');
  return Object.freeze({text:decoder.decode(raw),url:fileUrl(locator.commit,locator.path),validation:'SELECTED_FILE_BYTES_SHA256_MATCH'});
}
