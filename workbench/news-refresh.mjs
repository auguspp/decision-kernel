/** Explicit click only. These controls never call a model or poll in the background. */
import {REPO} from './reading.mjs';
import {localTime} from './product.mjs';
const ENDPOINT = '/api/actions/news-refresh';
const states = new WeakMap();
const positive = n => Number.isSafeInteger(n) && n > 0;
const safeRunURL = (id, url) => positive(id) && url === `https://github.com/${REPO}/actions/runs/${id}`;

export function refreshPresentation(result) {
  if (result?.kind === 'submitted') return {title:'新闻刷新已提交', detail:'尚不代表采集或发布完成。请检查本次更新。'};
  if (result?.kind === 'uncertain') return {title:'提交或运行尚未确认', detail:'不要重复提交；先检查本次更新。原新闻仍按原日期保留。'};
  if (result?.kind === 'rejected') return {title:'刷新请求被拒绝', detail:'没有确认新的采集；请检查站点凭证和权限，不自动重试。'};
  if (result?.kind === 'not_admitted') return {title:'本次刷新未获准采集', detail:'代码或运行顺序已变化，或发现重跑。保留原记录，不自动再次采集。'};
  if (result?.kind === 'blocked') {
    const details = {
      REFRESH_NOT_CONFIGURED:'原站刷新功能尚未配置，现有新闻仍可阅读。',
      OWNER_REQUIRED:'未确认站点本人身份，没有提交刷新。',
      NEWS_ALREADY_IN_FLIGHT:'已有新闻任务在途，本次没有再提交。',
      MAIN_CI_NOT_READY:'当前代码检查尚未通过，本次没有提交。',
      WORKFLOW_CHANGED:'后台工作流已变化，需核对站点接入版本；没有提交。',
      PRECONDITION_CHANGED:'准备期间已有新运行或代码变化，本次没有再提交。',
      PERMIT_EXPIRED:'本次提交准备已过期，没有按过期请求再执行。'
    };
    return {title:'本次没有提交刷新', detail:details[result.code] || '前置检查未确认，请核对后再明确发起，不自动重试。'};
  }
  if (result?.kind === 'run' && result.run) {
    const r = result.run;
    if (r.status !== 'completed') return {title:r.status === 'in_progress' ? '新闻采集进行中' : '新闻任务等待执行', detail:'实际运行状态；旧新闻仍保留，不启动 Quick。'};
    if (r.conclusion !== 'success') return {title:'本次新闻采集未成功完成', detail:'失败、取消或跳过不等于没有消息；原数据不清空，不自动重跑。'};
    if (result.publication === 'same_run_bytes_read') return {
      title:result.failed_sources ? '本次结果已保存，部分来源未取得' : '本次新闻结果已发布并读回',
      detail:`采集截止：${localTime(result.captured_through)}；${result.window_titles === null ? '没有可确认的标题数量' : `${result.window_titles} 条窗口标题（不是新增事件数）`}。未开展 Quick。`
    };
    if (result.publication === 'browser_readback_required') return {
      title:'本次新闻采集成功',
      detail:'运行已成功；发布与正文由页面现有固定 R reader 核验。请读取最新保存结果，不把运行成功本身当作页面已更新。'
    };
    return {title:'采集任务成功，发布资料尚未确认', detail:'请读取最新保存结果确认发布；不自动再次采集。'};
  }
  return {title:'刷新状态未识别', detail:'没有确认完成；请检查本次更新，不自动重新提交。'};
}
async function send(input, fetcher) {
  const response = await fetcher(ENDPOINT, {method:'POST', credentials:'same-origin', redirect:'error', cache:'no-store',
    signal:AbortSignal.timeout(30000), headers:{'Content-Type':'application/json', 'X-Decision-Kernel-Intent':'news-refresh'},
    body:JSON.stringify(input)});
  if (!/^application\/json(?:\s*;|$)/i.test(response.headers.get('content-type') || '')) throw new Error('HOST_ROUTE_UNCONFIRMED');
  const declared = response.headers.get('content-length');
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > 16384)) throw new Error('RESPONSE_LIMIT');
  const reader = response.body?.getReader(); if (!reader) throw new Error('EMPTY_RESPONSE');
  const parts = []; let size = 0, timer;
  const deadline = new Promise((_,reject) => { timer = setTimeout(() => reject(new Error('BODY_TIMEOUT')), 10000); });
  try {
    while (true) { const {value,done} = await Promise.race([reader.read(),deadline]); if (done) break;
      size += value.byteLength; if (size > 16384) throw new Error('RESPONSE_LIMIT'); parts.push(value); }
  } catch (e) { await reader.cancel().catch(() => {}); throw e; } finally { clearTimeout(timer); reader.releaseLock(); }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const part of parts) { bytes.set(part, offset); offset += part.byteLength; }
  const result = JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(bytes));
  if (!['ready','submitted','uncertain','blocked','rejected','run','not_admitted'].includes(result?.kind) ||
    !response.ok && result.kind !== 'blocked') throw new Error('HOST_RESPONSE_UNCONFIRMED');
  return result;
}

export function newsRefreshControl(ctx, fetcher = globalThis.fetch) {
  const {ui,active,reading} = ctx, {el,button,link,folded} = ui;
  if (!states.has(reading)) states.set(reading, {busy:false,ticket:null,runId:null,result:null,allowNew:false});
  const state = states.get(reading), node = el('section',undefined,'human-material'), status = el('div');
  status.setAttribute('role','status');
  node.append(el('h4','刷新最新新闻'), el('p','只更新现有新闻来源，不开展 Quick。需原站已接入本人校验和受限凭证。','small'));
  const start = button('刷新最新新闻', async () => {
    if (!active() || state.busy || state.ticket && !canStartAgain()) return;
    state.busy = true; state.ticket = null; state.runId = null; state.result = null; state.allowNew = false; draw('正在检查刷新条件…');
    try {
      const prepared = await send({op:'prepare'}, fetcher);
      if (!active()) return; // Navigation while preparing is not permission for a late submission.
      if (prepared.kind !== 'ready') { state.result = prepared; return; }
      if (!prepared.ticket?.permit || typeof prepared.ticket.signature !== 'string') throw new Error('PREPARE_UNCONFIRMED');
      state.ticket = prepared.ticket;
      // Keep the permit even if submission or its response is lost. Never retry automatically.
      state.result = {kind:'uncertain'}; draw('正在提交一次新闻刷新…');
      state.result = await send({op:'submit',ticket:state.ticket,run_id:null}, fetcher);
      state.allowNew = ['blocked','rejected'].includes(state.result.kind) || state.result.run?.status === 'completed';
      if (positive(state.result.run_id)) state.runId = state.result.run_id;
    } catch { state.result = state.ticket ? {kind:'uncertain'} : {kind:'blocked',code:'REFRESH_NOT_CONFIGURED'}; }
    finally { state.busy = false; if (active()) draw(); }
  });
  const inspect = button('检查本次更新', async () => {
    if (!active() || state.busy || !state.ticket) return;
    state.busy = true; draw('正在核对本次运行与发布资料…');
    try {
      state.result = await send({op:'status',ticket:state.ticket,run_id:state.runId}, fetcher);
      if (!['run','not_admitted','uncertain'].includes(state.result.kind)) state.result = {kind:'uncertain',code:'STATUS_UNCONFIRMED'};
      if (state.result.run?.status === 'completed') state.allowNew = true;
      if (positive(state.result.run?.id)) state.runId = state.result.run.id;
    } catch { state.result = {kind:'uncertain'}; }
    finally { state.busy = false; if (active()) draw(); }
  });
  function canStartAgain() { return state.allowNew; }
  function draw(message = null) {
    start.disabled = state.busy || Boolean(state.ticket && !canStartAgain());
    start.textContent = state.ticket && canStartAgain() ? '明确再刷新一次新闻' : '刷新最新新闻';
    inspect.disabled = state.busy || !state.ticket; inspect.hidden = !state.ticket;
    if (message) { status.replaceChildren(el('p',message)); return; }
    status.replaceChildren(); if (!state.result) return;
    const view = refreshPresentation(state.result); status.append(el('p',view.title),el('p',view.detail));
    const r = state.result.run, id = r?.id || state.result.run_id, url = r?.html_url || state.result.run_url;
    if (safeRunURL(id,url)) status.append(link('查看本次运行',url));
    if (['same_run_bytes_read','browser_readback_required'].includes(state.result.publication)) status.append(button('读取最新保存结果', () => {
      if (active()) document.getElementById('refresh')?.click(); // Existing immutable-reader refresh, not another dispatch.
    }));
    status.append(folded('本次更新的依据',JSON.stringify(state.result,null,2)));
  }
  node.append(start,inspect,status); draw(); return node;
}
