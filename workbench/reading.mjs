/** Read-only GitHub consumer. No tokens, writes, research, or automatic polling.
 * One Reading holds one immutable R; issue observations retain separate clocks.
 * This checks transport/shape and selected-file bytes, NOT canonical reading_hash.
 */
export const REPO = 'auguspp/decision-kernel';
export const READ_REF = 'read-model/current-state';
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
    require(Number.isSafeInteger(known.bytes) && known.bytes >= 0 && known.bytes <= 512 * 1024 &&
      HASH.test(known.sha256 || ''), 'UNSUPPORTED_FILE_DESCRIPTOR');
    const raw = await bytes(`${RAW}/${ref}/${escapedPath(known.read_path)}`, fetcher, 512 * 1024);
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
