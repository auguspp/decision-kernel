/** One optional route for the original Sites Worker; no scheduler or Research API.
 * Enable only after the real Sites edge strips untrusted identity headers and
 * the deployed Worker has no unprotected alternate URL. The enable flag is NOT
 * a substitute for that deployment check. No secrets or caller identity leave it.
 */
import {REPO} from '../reading.mjs';

export const NEWS_REFRESH_PATH = '/api/actions/news-refresh';
export const SITE_ORIGIN = 'https://decision-kernel-progress.a278038654.chatgpt.site';
export const WORKFLOW_SHA256 = 'c1ef99aeeddf9ef468f0dcd783446bbe1c61e07ad9f0443d354db8f77d9aa068';
const API = `https://api.github.com/repos/${REPO}`;
const WORKFLOW = 'radar-newsnow-daily.yml';
const WF_PATH = `.github/workflows/${WORKFLOW}`;
const RUNS = `actions/workflows/${WORKFLOW}/runs`;
const ACTIVE = ['queued', 'requested', 'waiting', 'pending', 'in_progress'];
const SHA = /^[a-f0-9]{40}$/, HASH = /^[a-f0-9]{64}$/, ID = /^[a-f0-9]{32}$/;
const encoder = new TextEncoder();
const positive = n => Number.isSafeInteger(n) && n > 0;
const keys = (v, names) => v && typeof v === 'object' && !Array.isArray(v) &&
  Object.keys(v).length === names.length && names.every(k => Object.hasOwn(v, k));
const fail = code => { throw new Error(code); };
const check = (ok, code) => { if (!ok) fail(code); };
const reply = (status, data) => new Response(JSON.stringify(data), {status, headers: {
  'Content-Type':'application/json; charset=utf-8', 'Cache-Control':'no-store',
  'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'no-referrer'
}});

/** Bounded streaming, also for responses: Content-Length alone is not a limit. */
async function textBody(source, limit) {
  const length = source.headers.get('content-length');
  check(length === null || /^\d+$/.test(length) && Number(length) <= limit, 'BODY_LIMIT');
  check(source.body, 'EMPTY_BODY');
  const reader = source.body.getReader(), parts = []; let size = 0, timer;
  const deadline = new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('BODY_TIMEOUT')), 10000); });
  try {
    while (true) {
      const {value, done} = await Promise.race([reader.read(), deadline]); if (done) break;
      size += value.byteLength; check(size <= limit, 'BODY_LIMIT'); parts.push(value);
    }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  finally { clearTimeout(timer); reader.releaseLock(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const part of parts) { bytes.set(part, offset); offset += part.byteLength; }
  return new TextDecoder('utf-8', {fatal:true}).decode(bytes);
}
async function jsonBody(source, limit = 1024 * 1024) {
  check(/^application\/json(?:\s*;|$)/i.test(source.headers.get('content-type') || ''), 'NON_JSON_RESPONSE');
  return JSON.parse(await textBody(source, limit));
}
async function sha256(text) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(text)))].map(b => b.toString(16).padStart(2, '0')).join('');
}
function clock(value) { return typeof value === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)); }
function runIdentity(r, path, now) {
  check(r && positive(r.id) && positive(r.run_number) && positive(r.run_attempt) &&
    r.path === path && r.repository?.full_name === REPO && r.head_repository?.full_name === REPO &&
    SHA.test(r.head_sha || '') && typeof r.head_branch === 'string' &&
    r.html_url === `https://github.com/${REPO}/actions/runs/${r.id}` &&
    clock(r.created_at) && clock(r.updated_at) && Date.parse(r.created_at) <= Date.parse(r.updated_at) &&
    Date.parse(r.updated_at) <= now && [...ACTIVE, 'completed'].includes(r.status) &&
    (r.status === 'completed' ? typeof r.conclusion === 'string' : r.conclusion === null), 'RUN_IDENTITY_UNCONFIRMED');
  return r;
}
function runList(data, path, now, max = 20) {
  const rows = data?.workflow_runs;
  check(Array.isArray(rows) && rows.length <= max && Number.isSafeInteger(data.total_count) &&
    data.total_count >= rows.length && (rows.length || data.total_count === 0) &&
    new Set(rows.map(r => r?.id)).size === rows.length &&
    new Set(rows.map(r => r?.run_number)).size === rows.length, 'RUN_LIST_INCOMPLETE');
  rows.forEach(r => runIdentity(r, path, now));
  return rows;
}
const pick = r => Object.fromEntries(['id','run_number','head_sha','path','event','run_attempt',
  'status','conclusion','html_url','created_at','updated_at'].map(k => [k, r[k]]));

function client(fetcher, token) {
  async function get(path) {
    // All api.github.com preflight reads use the existing scoped token. Public unauthenticated
    // API reads are IP-limited and unsafe on a shared Worker egress. Paths remain fixed here.
    const response = await fetcher(`${API}/${path}`, {method:'GET', redirect:'error', credentials:'omit',
      cache:'no-store', signal:AbortSignal.timeout(15000), headers:{Accept:'application/vnd.github+json',
        'X-GitHub-Api-Version':'2026-03-10', 'User-Agent':'decision-kernel-workbench',
        Authorization:`Bearer ${token}`}});
    if (!response.ok) {
      if (response.status === 403 && response.headers.get('x-ratelimit-remaining') === '0') fail('GITHUB_ACTIONS_RATE_LIMITED');
      if (response.status === 403) fail('GITHUB_ACTIONS_READ_FORBIDDEN');
      fail('GITHUB_READ_UNAVAILABLE');
    }
    return jsonBody(response);
  }
  async function workflow(code) {
    const response = await fetcher(`https://raw.githubusercontent.com/${REPO}/${code}/${WF_PATH}`, {
      method:'GET', redirect:'error', credentials:'omit', cache:'no-store', signal:AbortSignal.timeout(15000)});
    check(response.ok && await sha256(await textBody(response, 32768)) === WORKFLOW_SHA256, 'WORKFLOW_CHANGED');
    const metadata = await get(`actions/workflows/${WORKFLOW}`);
    check(metadata.path === WF_PATH && metadata.state === 'active' && positive(metadata.id), 'WORKFLOW_UNAVAILABLE');
  }
  return {get, workflow};
}
async function currentMainCI(c, now) {
  // ci.yml runs on every main push. The newest owned main push run therefore supplies both
  // the exact current code identity and its independent CI state using Actions permission only.
  const ci = runList(await c.get('actions/workflows/ci.yml/runs?branch=main&event=push&per_page=10'),
    '.github/workflows/ci.yml', now(), 10).sort((a,b) => b.run_number - a.run_number)[0];
  check(ci && ci.head_branch === 'main' && ci.event === 'push' && ci.run_attempt === 1 &&
    ci.status === 'completed' && ci.conclusion === 'success', 'MAIN_CI_NOT_READY');
  return ci;
}
async function snapshot(c, now) {
  const ci = await currentMainCI(c, now);
  const code = ci.head_sha;
  await c.workflow(code);
  // Query each native unfinished status, not merely the twenty newest successes.
  for (const status of ACTIVE) {
    const data = await c.get(`${RUNS}?status=${status}&per_page=1`);
    runList(data, WF_PATH, now(), 1);
    check(data.total_count === 0, 'NEWS_ALREADY_IN_FLIGHT');
  }
  // No branch filter: run_number is a workflow-wide counter, not a main counter.
  const latest = runList(await c.get(`${RUNS}?per_page=20`), WF_PATH, now()).sort((a,b) => b.run_number - a.run_number)[0];
  check(latest && latest.status === 'completed' && latest.run_number < 999999999999999, 'NEWS_BASELINE_UNCONFIRMED');
  const after = await currentMainCI(c, now);
  check(after.id === ci.id && after.head_sha === code && after.run_number === ci.run_number, 'MAIN_MOVED');
  return {code, previous_id:latest.id, previous_number:latest.run_number};
}
function permitValue(p) {
  check(keys(p, ['v','id','code','previous_id','previous_number','issued_at']) && p.v === 1 && ID.test(p.id || '') &&
    SHA.test(p.code || '') && positive(p.previous_id) && positive(p.previous_number) && p.previous_number < 999999999999999 &&
    Number.isSafeInteger(p.issued_at), 'INVALID_PERMIT');
  return {v:1, id:p.id, code:p.code, previous_id:p.previous_id, previous_number:p.previous_number, issued_at:p.issued_at};
}
async function signature(p, env, signatureHex = null) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(env.DECISION_KERNEL_GITHUB_TOKEN),
    {name:'HMAC', hash:'SHA-256'}, false, ['sign','verify']);
  const message = encoder.encode(`decision-kernel/news-refresh/v1\n${env.DECISION_KERNEL_OWNER_USER_ID}\n${JSON.stringify(p)}`);
  if (signatureHex !== null) {
    check(HASH.test(signatureHex), 'INVALID_PERMIT');
    const raw = new Uint8Array(signatureHex.match(/../g).map(b => parseInt(b, 16)));
    check(await crypto.subtle.verify('HMAC', key, raw, message), 'INVALID_PERMIT'); return;
  }
  return [...new Uint8Array(await crypto.subtle.sign('HMAC', key, message))].map(b => b.toString(16).padStart(2, '0')).join('');
}
async function checkTicket(ticket, env, now, submitting) {
  check(keys(ticket, ['permit','signature']), 'INVALID_PERMIT');
  const p = permitValue(ticket.permit); await signature(p, env, ticket.signature);
  check(p.issued_at <= now && now - p.issued_at <= (submitting ? 120000 : 30 * 86400000), 'PERMIT_EXPIRED'); return p;
}
function matching(r, p) {
  check(r.head_branch === 'main' && r.event === 'workflow_dispatch' && r.display_title === `site-news-refresh/${p.id}` &&
    r.actor?.id === 83357964, 'REQUEST_RUN_MISMATCH');
  return r;
}
async function findRun(c, p, now, runId = null) {
  if (runId !== null) return matching(runIdentity(await c.get(`actions/runs/${runId}`), WF_PATH, now()), p);
  const rows = runList(await c.get(`${RUNS}?per_page=20`), WF_PATH, now()).filter(r => r.display_title === `site-news-refresh/${p.id}`);
  check(rows.length <= 1, 'MULTIPLE_REQUEST_RUNS');
  return rows.length ? matching(rows[0], p) : null;
}
function reportRun(r, p, now) {
  const base = {kind:'run', run:pick(r), observed_at:new Date(now()).toISOString(), publication:'not_checked'};
  if (r.head_sha !== p.code || r.run_number !== p.previous_number + 1 || r.run_attempt !== 1)
    return {...base, kind:'not_admitted'};
  if (r.status !== 'completed' || r.conclusion !== 'success') return base;
  // Publication/body verification belongs to the existing browser pinned-R reader.
  // Do not duplicate its GitHub ref/body reads in the Worker status path.
  return {...base, publication:'browser_readback_required'};
}

/** At most one POST per same ticket in this isolate. Cross-isolate source safety
 * comes from the workflow's unique next-run-number check, NOT this memory map.
 */
const submissions = new Map();
async function submit(p, c, env, fetcher, now) {
  const existing = await findRun(c, p, now);
  if (existing) return reportRun(existing, p, now);
  const current = await snapshot(c, now);
  check(current.code === p.code && current.previous_id === p.previous_id && current.previous_number === p.previous_number, 'PRECONDITION_CHANGED');
  check(now() - p.issued_at <= 120000, 'PERMIT_EXPIRED');
  let response;
  try {
    response = await fetcher(`${API}/actions/workflows/${WORKFLOW}/dispatches`, {
      method:'POST', redirect:'error', credentials:'omit', signal:AbortSignal.timeout(15000),
      headers:{'Content-Type':'application/json', Accept:'application/vnd.github+json', 'X-GitHub-Api-Version':'2026-03-10',
        'User-Agent':'decision-kernel-workbench', Authorization:`Bearer ${env.DECISION_KERNEL_GITHUB_TOKEN}`},
      body:JSON.stringify({ref:'main', inputs:{site_request_id:p.id,
        site_expected_run_number:String(p.previous_number + 1), site_expected_code_commit:p.code}})
    });
  } catch { return {kind:'uncertain', code:'SUBMISSION_UNCONFIRMED'}; }
  if ([401,403,404,422,429].includes(response.status)) return {kind:'rejected', code:'GITHUB_DISPATCH_REJECTED'};
  if (response.status === 204) return {kind:'submitted', run:null, code:'RUN_NOT_IDENTIFIED'};
  if (response.status !== 200) return {kind:'uncertain', code:'SUBMISSION_UNCONFIRMED'};
  let id = null;
  try {
    const data = await jsonBody(response, 8192); id = data.workflow_run_id;
    check(positive(id) && data.run_url === `${API}/actions/runs/${id}` &&
      data.html_url === `https://github.com/${REPO}/actions/runs/${id}`, 'DISPATCH_RESPONSE_UNCONFIRMED');
    // The direct response is correlated; a later status read still verifies its native metadata.
    return {kind:'submitted', run_id:id, run_url:data.html_url};
  } catch { return {kind:'uncertain', code:'SUBMISSION_UNCONFIRMED'}; }
}

export async function handleNewsRefresh(request, env, options = {}) {
  const url = new URL(request.url);
  if (url.pathname !== NEWS_REFRESH_PATH) return null;
  if (url.origin !== SITE_ORIGIN || url.search) return reply(403, {kind:'blocked', code:'WRONG_ORIGIN'});
  if (request.method !== 'POST') return reply(405, {kind:'blocked', code:'METHOD_NOT_ALLOWED'});
  const owner = env?.DECISION_KERNEL_OWNER_USER_ID, token = env?.DECISION_KERNEL_GITHUB_TOKEN;
  if (env?.DECISION_KERNEL_ENABLE_NEWS_REFRESH !== '1' || typeof owner !== 'string' || !owner.trim() || owner.length > 240 ||
    typeof token !== 'string' || !token || /[\r\n]/.test(token)) return reply(503, {kind:'blocked', code:'REFRESH_NOT_CONFIGURED'});
  if (request.headers.get('oai-authenticated-user-id') !== owner) return reply(403, {kind:'blocked', code:'OWNER_REQUIRED'});
  if (request.headers.get('origin') !== SITE_ORIGIN || request.headers.get('x-decision-kernel-intent') !== 'news-refresh' ||
    !/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(request.headers.get('content-type') || '') ||
    request.headers.has('sec-fetch-site') && request.headers.get('sec-fetch-site') !== 'same-origin')
    return reply(403, {kind:'blocked', code:'SAME_ORIGIN_JSON_REQUIRED'});
  let input;
  try {
    input = JSON.parse(await textBody(request, 8192));
    check(input?.op === 'prepare' ? keys(input, ['op']) : ['submit','status'].includes(input?.op) &&
      keys(input, ['op','ticket','run_id']) && (input.run_id === null || positive(input.run_id)) &&
      (input.op !== 'submit' || input.run_id === null), 'INVALID_REQUEST');
  } catch { return reply(400, {kind:'blocked', code:'INVALID_REQUEST'}); }
  const now = options.now || Date.now, fetcher = options.fetcher || globalThis.fetch, c = client(fetcher, token);
  try {
    if (input.op === 'prepare') {
      const current = await snapshot(c, now);
      const p = {v:1, id:crypto.randomUUID().replaceAll('-', ''), ...current, issued_at:now()};
      return reply(200, {kind:'ready', ticket:{permit:p, signature:await signature(p, env)}});
    }
    const p = await checkTicket(input.ticket, env, now(), input.op === 'submit');
    if (input.op === 'status') {
      const r = await findRun(c, p, now, input.run_id);
      return reply(200, r ? await reportRun(r, p, now) : {kind:'uncertain', code:'RUN_NOT_IDENTIFIED'});
    }
    for (const [key, value] of submissions) if (value.done && now() - value.at > 300000) submissions.delete(key);
    const key = input.ticket.signature;
    if (!submissions.has(key)) {
      check(submissions.size < 64, 'TOO_MANY_PENDING_REQUESTS');
      const entry = {at:now(), done:false};
      entry.promise = submit(p, c, env, fetcher, now).finally(() => { entry.done = true; }); submissions.set(key, entry);
    }
    return reply(200, await submissions.get(key).promise);
  } catch (error) {
    // Do not expose upstream response bodies, token headers or raw exception text.
    const allowed = new Set(['INVALID_PERMIT','PERMIT_EXPIRED','NEWS_ALREADY_IN_FLIGHT','MAIN_CI_NOT_READY',
      'WORKFLOW_CHANGED','MAIN_MOVED','PRECONDITION_CHANGED','MULTIPLE_REQUEST_RUNS','TOO_MANY_PENDING_REQUESTS',
      'GITHUB_ACTIONS_RATE_LIMITED','GITHUB_ACTIONS_READ_FORBIDDEN']);
    return reply(409, {kind:'blocked', code:allowed.has(error.message) ? error.message : 'CHECK_UNCONFIRMED'});
  }
}