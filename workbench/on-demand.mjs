/** Native operation entrypoints, not a dispatch server or research executor.
 * Navigation/clipboard/status GET never acquires authority or writes a request.
 */
import {REPO, commit, fileUrl, readNewsExecution} from './reading.mjs';
import {localTime} from './product.mjs';
import {newsRefreshControl} from './news-refresh.mjs';
export const NEWS_WORKFLOW_URL = `https://github.com/${REPO}/actions/workflows/radar-newsnow-daily.yml`;
const hash = v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
function require(ok, reason) { if (!ok) throw new Error(reason); }
function context(reading) {
  commit(reading.ref); commit(reading.payload.code_commit);
  return {reading_commit: reading.ref, saved_code_commit: reading.payload.code_commit,
    saved_reading: fileUrl(reading.ref, 'current-state.json')};
}
export function newsRefreshRequest(reading) {
  return '请仅更新一次现役新闻来源，不开展 Quick、Full、Odds 或其他工作流。\n' +
    '先固定当前 main，读取 AGENTS、#297 当前入口和现役新闻工作流；确认当前独立 main CI 及原操作范围。\n' +
    '检查是否已有同范围运行或未对账的提交。有在途任务先读回，不重复 dispatch；失败不自动重跑。\n' +
    '前提成立时仅对 radar-newsnow-daily.yml 的 main 发起一次新的 workflow_dispatch，不使用 rerun，不改参数/来源/费用。\n' +
    '提交响应不明先对账，不机械重试。分别报告实际运行、原来源窗口/缺口、正常发布和固定版本读回；不把标题数叫新增事件。\n' +
    '复制这段文字尚未提交或触发。以下 JSON 仅为本页保存上下文；不是当前 main/运行状态，也不是额外执行指令。\n\n' +
    JSON.stringify(context(reading), null, 2);
}
export function sectorQuickRequest(reading, descriptor, view, row) {
  const saved = reading.payload.lanes?.sector?.last_qualified_result;
  const registered = saved?.details?.['context/context.json'];
  require(registered && descriptor?.read_path === registered.read_path && hash(descriptor.sha256) &&
    descriptor.sha256 === registered.sha256 && descriptor.bytes === registered.bytes &&
    Number.isSafeInteger(descriptor.bytes) && descriptor.bytes >= 0 &&
    view?.day === saved.market_session && view.rows?.includes(row) &&
    /^(881|884)\d{3}\.TI$/.test(row?.code || '') &&
    row.original?.observation?.thscode === row.code && row.original.observation.as_of_session === view.day,
    'SECTOR_REQUEST_CONTEXT_MISMATCH');
  return '请按当前项目研究入口，对下面选定的行业开展一次有界 Quick。先固定当前 main 的指引，恢复原观察和适用的旧研究/更正，再自行查证新公开资料。\n' +
    '区分价格表现与业务证据；可以发现相关对象，不预设受益股票，也不要求必须解释上涨原因；不明就保留 UNKNOWN。\n' +
    '沿现有研究留存路径保存实际正文、主要来源、反证、未知与前驱关系，精确读回后再报告保存成功。\n' +
    '这是待提交请求，复制没有启动研究；不得自动 Full、重算 Odds、接受研究、登记持仓/Watch 或交易。以下 JSON 全部只是定位数据，不是额外指令。\n\n' +
    JSON.stringify({...context(reading), market_session: view.day,
      source: {url: fileUrl(reading.ref, descriptor.read_path), sha256: descriptor.sha256, bytes: descriptor.bytes},
      sector: {code: row.code, name: row.name, family: row.family},
      scope: 'SELECTED_SAVED_SECTOR_NOT_LIVE_QUOTE_OR_ESTABLISHED_BUSINESS_EXPOSURE'}, null, 2);
}
export function newsExecutionView(observation, saved) {
  const r = observation.latest;
  if (!r) return {title: '本次查询未找到采集记录', detail: '不代表没有新闻；没有执行任何更新。', url: null};
  if (r.run_attempt !== 1) return {title: '发现重跑记录，来源资格待核对',
    detail: '不按普通首次采集认定发布成功；请查看原运行。', url: r.html_url};
  const running = {queued:'新闻采集正在排队', requested:'新闻采集已请求', waiting:'新闻采集等待执行',
    pending:'新闻采集等待执行', in_progress:'新闻采集进行中'};
  if (r.status !== 'completed') return {title: running[r.status] || '采集状态尚未识别',
    detail: '这是本次查询范围内的实际运行状态，不是本页发起的证明；不要重复提交。', url:r.html_url};
  if (r.conclusion !== 'success') return {title: '最近采集没有成功完成',
    detail: '失败、取消或跳过不等于没有新消息。下方资料仍按原日期阅读，不自动重试。', url:r.html_url};
  const origin = saved?.archive?.origin_run, attempted = saved?.latest_attempt;
  const same = source => source && ['id','head_sha','path','run_attempt','event'].every(k => source[k] === r[k]) &&
    source.status === 'completed' && source.conclusion === 'success';
  const linked = same(origin) && same(attempted) && hash(saved?.capture_hash) &&
    saved?.details?.json?.read_path === 'details/radar/news-daily.json' && hash(saved.details.json.sha256);
  return {title:'新闻采集任务已成功结束', url:r.html_url,
    detail: linked ? '当前读取包已登记同次采集；正文是否可读及实际采集日期以下方为准，不代表 Quick 完成。' :
      '当前读取版本尚未确认包含这次采集。请用页面顶部“读取最新保存结果”核对；不据此断言发布失败或研究完成。'};
}
/** A common clipboard affordance. Double clicks and late completion do not claim
 * submission; failed clipboard writes expose the same exact request as text.
 */
export function requestControl(label, build, {ui, active}) {
  const {el,button} = ui, node=el('div',undefined,'product-actions'), text=el('pre'); text.hidden=true;
  let copying=false;
  const copy=button(label,async()=>{
    if (!active() || copying) return;
    copying=true;copy.disabled=true;
    try {
      const request=build();text.textContent=request;
      try {
        if (typeof globalThis.navigator?.clipboard?.writeText !== 'function') throw new Error('CLIPBOARD_UNAVAILABLE');
        await globalThis.navigator.clipboard.writeText(request);
        if (active()) copy.textContent='已复制；需在项目对话中提交，尚未启动';
      } catch { if(active()){text.hidden=false;copy.textContent='请复制下方请求；尚未启动';} }
    } catch { if(active()){text.hidden=false;text.textContent='上下文不完整，未生成请求。';} }
    finally { copying=false;copy.disabled=false; }
  });
  node.append(copy,text);return node;
}
const checking = new WeakMap();
function check(reading) {
  if (!checking.has(reading)) {
    const pending=readNewsExecution().finally(()=>checking.delete(reading));checking.set(reading,pending);
  }
  return checking.get(reading);
}
export function newsUpdateControls(target,ctx) {
  const {reading,ui,active}=ctx, {el,button,link,folded}=ui;
  target.append(newsRefreshControl(ctx));
  const panel=el('details',undefined,'human-material');
  panel.append(el('summary','其他更新方式与最近采集记录'));
  panel.append(el('h4','按需更新新闻'),el('p','在 GitHub 确认运行（选择 main），或复制请求交给本项目对话执行。打开链接、复制和查状态都不会启动采集。','small'),
    link('到 GitHub 更新新闻',NEWS_WORKFLOW_URL),requestControl('复制新闻更新请求（未触发）',()=>newsRefreshRequest(reading),ctx));
  const status=el('div');status.setAttribute('role','status');let busy=false;
  const inspect=button('检查新闻采集状态',async()=>{
    if(!active()||busy)return;busy=true;inspect.disabled=true;status.replaceChildren(el('p','正在读取采集状态…'));
    try {
      const observation=await check(reading);if(!active())return;
      const view=newsExecutionView(observation,reading.payload.research?.daily_news);
      status.replaceChildren(el('p',view.title),el('p',view.detail),
        el('p',`状态查询：${localTime(observation.observedAt)}；独立于本页保存资料时间。`,'small'));
      if(view.url)status.append(link('查看这次采集记录',view.url));
      status.append(folded('执行身份与查询范围',JSON.stringify(observation,null,2)));
    } catch(error) {if(active())status.replaceChildren(el('p','采集状态未取得；不要据此重新提交，已有新闻仍可阅读。'),folded('状态读取诊断',String(error.message)));}
    finally {busy=false;inspect.disabled=false;}
  });
  panel.append(inspect,status);target.append(panel);return panel;
}
