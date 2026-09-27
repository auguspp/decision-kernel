import {transferButton} from './quick-inbox-ui.mjs';
/** Saved news/market views, not a researcher, quote provider, or command bridge.
 * Same-R registered bytes only. Source titles and dates remain claims, not facts.
 */
import {fileUrl} from './reading.mjs';
import {newsUpdateControls, requestControl, sectorQuickRequest} from './on-demand.mjs';
import {localTime, displayDecimal} from './product.mjs';
const sources = {cls:'财联社', wallstreetcn:'华尔街见闻', fastbull:'FastBull', jin10:'金十数据', mktnews:'MKTNews', gelonghui:'格隆汇', thepaper:'澎湃新闻'};
const families = {BROAD_881:'一级行业', GRANULAR_884:'细分行业'};
const hash = v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const clock = v => localTime(v) !== '时间未知';
const day = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10) === v;
const list = (v, n) => Array.isArray(v) && v.length <= n;
const none = p => p && ['signal_transition_authority','human_attention_authority','research_authority','investment_authority'].every(k => p[k] === 'NONE');
function require(ok, reason) { if (!ok) throw new Error(reason); }
export function articleURL(value) {
  if (typeof value !== 'string' || /[\x00-\x20\x7f]/.test(value)) return null;
  try { const u = new URL(value); return ['http:','https:'].includes(u.protocol) && !u.username && !u.password ? value : null; } catch { return null; }
}
/** Display projection: shape/identity checks do not certify publisher claims. */
export function newsView(text, saved) {
  const p = JSON.parse(text)?.projection, c = p?.capture?.projection, n = c?.news?.projection;
  require(none(p) && p.automatic_admission === false && p.semantic_review === 'NOT_PERFORMED' &&
    c?.version === 'native-newsnow-window-v1' && none(c) && c.automatic_admission === false &&
    hash(c.capture_hash) && c.capture_hash === saved?.capture_hash && c.capture_hash === p.state?.capture_hash &&
    c.captured_through === saved.captured_through && clock(c.captured_from) && clock(c.captured_through) &&
    Date.parse(c.captured_from) <= Date.parse(c.captured_through) && list(c.source_outcomes,16) &&
    c.coverage?.complete_news_coverage === false, 'NEWS_SAVED_SCOPE_MISMATCH');
  const gaps = [], outcomes = c.source_outcomes.map(o => ({...o, name:sources[o.source_id] || o.source_id || '来源未提供'}));
  require(new Set(outcomes.map(o=>o.source_id)).size === outcomes.length, 'NEWS_SOURCE_ID_CONFLICT');
  for (const o of outcomes) if (o.status !== 'OBSERVATIONS_NORMALIZED') gaps.push(`${o.name}：窗口未正常取得，不能解释为没有新闻。`);
  if (!n) return {rows:[], outcomes, gaps:[...gaps,'本批没有可阅读窗口。'], captured:c.captured_through};
  require(none(n) && n.automatic_admission === false && n.kind === 'NEWS_EVENT_CANDIDATE' &&
    n.company_mapping === 'EXACT_SAVED_NAME_TEXT_ONLY_NOT_SECURITY_OR_EXPOSURE_ACCEPTANCE' &&
    list(n.observations,480) && list(n.companies,1000), 'NEWS_FORMAT_UNSUPPORTED');
  const counts = new Map();
  for (const r of n.observations) counts.set(r?.version_id,(counts.get(r?.version_id)||0)+1);
  const rows = [];
  for (const r of n.observations) {
    if (!r || !hash(r.article_id) || !hash(r.version_id) || counts.get(r.version_id)!==1 ||
        typeof r.title !== 'string' || !r.title.trim() || !clock(r.fetched_at) ||
        Date.parse(r.fetched_at)>Date.parse(c.captured_through) || r.business_linkage !== 'NOT_ESTABLISHED' ||
        r.qualification !== 'CONTEXT_ONLY' || !outcomes.some(o=>o.source_id===r.source_id && o.status==='OBSERVATIONS_NORMALIZED')) {
      gaps.push('一条新闻身份、来源或时钟不完整／重复，未放入可读列表。'); continue;
    }
    const claims = Object.values(r.publication_claims || {}).filter(v=>v?.status==='PARSED_CLAIM_NOT_PUBLISHER_VERIFIED' && clock(v.parsed_at));
    const times = [...new Map(claims.map(v=>[Date.parse(v.parsed_at),v.parsed_at])).values()];
    const named = n.companies.filter(co => /^\d{6}\.(SH|SZ|BJ)$/.test(co?.thscode || '') &&
      Array.isArray(co.matches) && co.matches.some(m=>m.observation_id===r.version_id)).map(co=>co.thscode);
    rows.push({id:r.version_id, original:r, title:r.title, source:r.source_id, sourceName:sources[r.source_id] || r.source_id,
      url:articleURL(r.url), fetched:r.fetched_at, published:times.length===1 ? localTime(times[0]) : times.length>1 ? '时间声明不一致' : '发布时间未知',
      companies:[...new Set(named)]});
  }
  return {rows, outcomes, gaps, captured:c.captured_through};
}
export function sectorView(text, saved) {
  const p = JSON.parse(text);
  require(none(p) && p.schema_version === 1 && p.semantics === 'READ_ONLY_SAVED_MARKET_CONTEXT_NOT_A_NEW_ALERT_OR_RESEARCH_ROUTE' &&
    hash(p.context_hash) && p.context_hash===saved?.context_hash && day(p.market_session) && p.market_session===saved.market_session &&
    typeof p.benchmark_thscode==='string' && list(p.universes,8), 'SECTOR_SAVED_SCOPE_MISMATCH');
  const rows=[], gaps=[];
  require(new Set(p.universes.map(u=>u?.family)).size===p.universes.length,'SECTOR_FAMILY_CONFLICT');
  for (const u of p.universes) {
    require(families[u?.family] && list(u.rows,1000), 'SECTOR_FORMAT_UNSUPPORTED');
    if (u.count!==u.rows.length) gaps.push(`${families[u.family]}：声明数量与明细不一致。`);
    const ids = new Map(); for (const r of u.rows) ids.set(r?.observation?.thscode,(ids.get(r?.observation?.thscode)||0)+1);
    for (const r of u.rows) {
      const o=r?.observation;
      if (!o || !/^(881|884)\d{3}\.TI$/.test(o.thscode || '') || ids.get(o.thscode)!==1 || o.as_of_session!==p.market_session ||
        !o.thscode.startsWith(u.family==='BROAD_881'?'881':'884') || typeof o.name!=='string' ||
        typeof r.currently_gate_active!=='boolean' || typeof r.recent_weakening!=='boolean') {
        gaps.push('一项板块身份或市场日不一致，未纳入列表。'); continue;
      }
      const returns = [5,20,60].map(h=>o[`horizon_${h}`]?.sessions===h ? displayDecimal(o[`horizon_${h}`].sector_return,{percent:true}) : '口径未知');
      rows.push({name:o.name, code:o.thscode, family:u.family, returns, active:r.currently_gate_active, weakening:r.recent_weakening,
        excess:o.horizon_20?.sessions===20 ? displayDecimal(o.horizon_20.excess_return,{percent:true}).replace(/%$/, '个百分点') : '口径未知',
        path:typeof r.path_description==='string'?r.path_description:'原路径描述未提供', original:r});
    }
  }
  return {rows,gaps,day:p.market_session,benchmark:p.benchmark_thscode};
}
export function newsResume(ref, descriptor, row) {
  require(hash(row?.id) && hash(descriptor?.sha256),'NEWS_CONTEXT_IDENTITY');
  return '请按当前项目研究入口，对这条明确定位的新闻开展 Quick。先从固定 R 恢复原件及适用旧研究，再自主查证公开资料；原因不明保留 UNKNOWN。\n' +
    '复制本身没有启动研究；不得自动 Full、重算 Odds、接受研究或交易。标题、发布时间、URL 等都以固定 R 原件为准，不信任这段复制文本自行补全。\n\n' +
    `reading R: ${ref}\nread_path: ${descriptor.read_path}\nsha256: ${descriptor.sha256}\nobservation_id: ${row.id}\n`;
}
const cache = new WeakMap();
function readSaved(reading, descriptor) {
  let entries=cache.get(reading); if (!entries) cache.set(reading,entries=new Map());
  const key=descriptor.read_path+':'+descriptor.sha256;
  if (!entries.has(key)) entries.set(key,reading.readFile(descriptor));
  return entries.get(key);
}
/** Uses the existing app's native table/text/disclosure helpers. No HTML injection. */
export function newsPage(target, ctx) {
  const {reading, ui, active, onRead, onCompany}=ctx, {el,card,button,link,notice,folded,disclosure}=ui;
  const saved=reading.payload.research?.daily_news, descriptor=saved?.details?.json;
  const panel=card('新闻 · 已保存窗口','按来源与关键词阅读。标题是原报道表述；尚未合并为已核实事件，也未关联新的 Quick 解读。'); target.append(panel);
  newsUpdateControls(panel,ctx);
  panel.append(notice('刷新只采集新闻；下方仍是当前保存版本。研究请加入待 Quick，页面不会自动开展研究。'));
  if (saved?.status === 'STALE_CAPTURE_NOT_TODAY_NEWS') panel.append(notice('这个保存窗口已陈旧，不代表今天的新消息。'));
  if (!descriptor) { panel.append(notice('新闻窗口本次不可读，不代表没有新闻。'),folded('实际来源状态',JSON.stringify(saved||{},null,2))); return; }
  const content=el('div'); panel.append(content,disclosure('窗口依据与完整原件',button('阅读保存窗口原件',()=>onRead(descriptor)),
    link('固定版本原件',fileUrl(reading.ref,descriptor.read_path))));
  content.append(el('p','正在读取保存窗口…'));
  readSaved(reading,descriptor).then(file=>{
    if (!active()) return;
    const view=newsView(file.text,saved);
    const toolbar=el('div',undefined,'product-actions'), input=el('input'), select=el('select');
    input.type='search'; input.placeholder='搜索新闻标题'; input.setAttribute('aria-label','搜索新闻标题');
    select.setAttribute('aria-label','新闻来源');
    for (const [id,label] of [['','全部来源'],...view.outcomes.map(o=>[o.source_id,o.name])]) { const option=el('option',label); option.value=id; select.append(option); }
    toolbar.append(input,select); const list=el('div'); let page=0;
    content.replaceChildren(el('p',`采集截止：${localTime(view.captured)} · 本窗口 ${view.rows.length} 条标题（不是事件数）`),toolbar,list);
    if (view.gaps.length) content.insertBefore(notice([...new Set(view.gaps)].join(' ')),toolbar);
    content.insertBefore(el('p','原文时间仅为上游声明，未向发布者核验；抓取时间不替代发布时间。','small'),toolbar);
    function draw() {
      const rows=view.rows.filter(r=>(!select.value || r.source===select.value) && r.title.toLowerCase().includes(input.value.trim().toLowerCase()));
      page=Math.min(page,Math.max(0,Math.ceil(rows.length/20)-1)); list.replaceChildren(el('p',`筛选 ${rows.length} 条 · 第 ${page+1} / ${Math.max(1,Math.ceil(rows.length/20))} 页`,'small'));
      if (!rows.length) list.append(el('p','当前筛选无匹配标题；不是市场没有新闻。'));
      for (const row of rows.slice(page*20,page*20+20)) {
        const article=el('article',undefined,'human-research-row'); article.append(el('h4',row.title),el('p',`${row.sourceName} · 原文时间声明：${row.published}`,'small'),
          el('p',`抓取：${localTime(row.fetched)} · 经济联系尚未研究`,'small'));
        const actions=el('div',undefined,'product-actions');
        if (row.url) actions.append(link('查看原报道',row.url)); else actions.append(el('p','原报道链接不可安全打开。','small'));
        const request=el('pre'); request.hidden=true;
        const copy=button('复制单条 Quick 请求（备用，不保存）',async()=>{
          if (!active()) return;
          request.textContent=newsResume(reading.ref,descriptor,row);
          try { await navigator.clipboard.writeText(request.textContent); copy.textContent='已复制；需到 ChatGPT 提交，尚未启动'; }
          catch { request.hidden=false; copy.textContent='请复制下方请求；尚未启动'; }
        }); actions.append(transferButton(ui,{kind:'news',reading:reading.ref,subject:row.id,asset:null},active),copy);
        if (row.companies.length) for (const code of row.companies) actions.append(button(`查看名称命中公司的研究 · ${code}`,()=>onCompany(code)));
        article.append(actions,request,folded('来源与时间声明原值',JSON.stringify(row.original,null,2))); list.append(article);
      }
      pager(list,page,rows.length,20,n=>{page=n;draw();},ui);
    }
    input.oninput=()=>{page=0;draw();}; select.onchange=()=>{page=0;draw();}; draw();
  }).catch(error=>{if(active()) content.replaceChildren(notice('新闻读取未完成；不把失败当作无新增。'),folded('读取诊断',String(error.message)));});
}
function pager(target,page,total,size,change,{el,button}) {
  const bar=el('div',undefined,'product-actions');
  const prev=button('上一页',()=>change(page-1)), next=button('下一页',()=>change(page+1));
  prev.disabled=page===0; next.disabled=(page+1)*size>=total; bar.append(prev,next); target.append(bar);
}
export function marketsPage(target,ctx) {
  const {reading,ui,active,onRead,onCompany}=ctx, {el,card,button,link,notice,folded,disclosure,dataTable}=ui;
  target.append(card('市场 · 已覆盖观察','先看 A 股行业结构与个股观察。全球指数、债券、商品、外汇和加密资产的统一快照尚未接入此页；不是实时行情终端。'));
  const lane=reading.payload.lanes?.sector, saved=lane?.last_qualified_result;
  const panel=card('A 股行业结构',`保存市场日：${day(saved?.market_session)?saved.market_session:'未知'}；基于原价格观察，不说明上涨原因。`); target.append(panel);
  if (lane?.health!=='LATEST_ATTEMPT_SUCCEEDED') panel.append(notice('最近板块更新未确认成功；以下若有数据，仍是上次保存结果。'));
  const descriptor=saved?.details?.['context/context.json'], area=el('div'); panel.append(area);
  if (!descriptor) area.append(notice('本次没有可读板块明细，不能判断为市场平静。'));
  else {
    area.append(el('p','正在读取原板块状态…'));
    panel.append(disclosure('板块依据与原件',button('阅读板块原件',()=>onRead(descriptor)),link('固定版本原件',fileUrl(reading.ref,descriptor.read_path))));
    readSaved(reading,descriptor).then(file=>{
      if (!active()) return; const view=sectorView(file.text,saved), input=el('input'), select=el('select'), box=el('div'); let page=0;
      input.type='search'; input.placeholder='搜索行业名称或代码'; input.setAttribute('aria-label','搜索行业'); select.setAttribute('aria-label','行业范围');
      for(const [id,label] of [['','全部行业'],...Object.entries(families)]) {const o=el('option',label);o.value=id;select.append(o);}
      area.replaceChildren(el('p',`市场日：${view.day} · 相对基准：${view.benchmark} · ${view.rows.length} 个行业观察（不是股票家数）`),input,select,box);
      if(view.gaps.length) area.append(notice([...new Set(view.gaps)].join(' ')));
      function draw(){
        const rows=view.rows.filter(r=>(!select.value||r.family===select.value) && `${r.name} ${r.code}`.includes(input.value.trim()));
        page=Math.min(page,Math.max(0,Math.ceil(rows.length/20)-1));
        const heads=['行业','5 / 20 / 60交易日涨跌幅','20日相对基准收益差','原观察状态','研究接续'];
        const {wrapper,body}=dataTable(`筛选 ${rows.length} 项 · 第 ${page+1} / ${Math.max(1,Math.ceil(rows.length/20))} 页；百分数仅格式化原值，不重算信号`,heads);
        for(const row of rows.slice(page*20,page*20+20)) {
          const tr=el('tr'),values=[`${row.name} · ${families[row.family]}`,row.returns.join(' / '),row.excess,
            `${row.active?'满足原价格观察条件':'未满足原价格观察条件'}${row.weakening?'；近期走弱':''}。${row.path}`];
          values.forEach((v,i)=>{const td=el('td',v);td.setAttribute('data-label',heads[i]);tr.append(td);});
          const action=el('td');action.setAttribute('data-label','研究接续');
          action.append(transferButton(ui,{kind:'sector',reading:reading.ref,subject:row.code,asset:null},active));
          action.append(requestControl('复制行业 Quick 请求（未启动）',()=>sectorQuickRequest(reading,descriptor,view,row),ctx));tr.append(action);body.append(tr);
        }
        box.replaceChildren(wrapper);if(!rows.length)box.append(el('p','当前筛选没有匹配行业。'));pager(box,page,rows.length,20,n=>{page=n;draw();},ui);
      }
      input.oninput=()=>{page=0;draw();};select.onchange=()=>{page=0;draw();};draw();
    }).catch(error=>{if(active())area.replaceChildren(notice('板块明细读取未完成，其他内容仍可读。'),folded('读取诊断',String(error.message)));});
  }
  const stockLane=reading.payload.lanes?.stock, stock=stockLane?.last_qualified_result;
  const stocks=card('个股观察',`保存市场日：${day(stock?.market_session)?stock.market_session:'未知'}；仅为已检查的候选范围，不是全市场。`);target.append(stocks);
  if(stockLane?.health!=='LATEST_ATTEMPT_SUCCEEDED')stocks.append(notice('最近个股更新未确认成功，不把旧结果包装为当前检查。'));
  const dispositions=stock?.dispositions;
  if(!list(dispositions,1000))stocks.append(notice('个股明细不可用。'));
  else {
    const states={CONTRACT_CHECKED_RAW_READING:'已有价格观察；业务联系待研究',CONDITIONS_NOT_MET:'原观察条件未满足',DATA_QUALIFICATION_FAILED:'数据无法判断，不是条件否决'};
    const ids=new Map();for(const r of dispositions)ids.set(r?.thscode,(ids.get(r?.thscode)||0)+1);
    for(const r of dispositions) {
      if(!/^\d{6}\.(SH|SZ|BJ)$/.test(r?.thscode||'')||ids.get(r.thscode)!==1){stocks.append(notice('一项个股身份不完整或重复。'));continue;}
      const row=el('div',undefined,'human-material');row.append(button(r.company_name||r.thscode,()=>onCompany(r.thscode)),el('p',states[r.status]||'原处置尚未适配，请查依据'));
      row.append(folded('原处置与缺口',JSON.stringify(r,null,2)));stocks.append(row);
    }
    if(!dispositions.length)stocks.append(el('p','保存候选列表为空；不代表全市场没有变化。'));
  }
}
