/** Same-R TDX observations and members. No source calls, research or saved state. */
import {fileUrl} from './reading.mjs';
import {makeStockComparisonLoader, mountStockComparison} from './concept-stock.mjs';
import {displayDecimal, localTime} from './product.mjs';
const TAXONOMY='TDX_CATEGORY_CONCEPT_SOURCE_NATIVE_NOT_EASTMONEY_BK_OR_HITHINK_TI';
const HASH=/^[a-f0-9]{64}$/, TICKER=/^[0-9]{6}\.(SH|SZ|BJ)$/;
const DAY=v=>typeof v==='string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10)===v;
const NONE=p=>['research_authority','odds_authority','action_authority','investment_authority'].every(k=>p?.[k]==='NONE');
function require(ok, reason){if(!ok)throw new Error(reason);}
export function conceptView(text,saved){
  const r=JSON.parse(text),p=r?.projection;
  require(NONE(p) && p.version==='tdx-concept-snapshot-v1' && p.taxonomy===TAXONOMY &&
    p.kind==='MARKET_EXPRESSION' && p.qualification==='CONTEXT_ONLY' && HASH.test(r.projection_hash) &&
    r.projection_hash===saved?.result?.projection_hash && DAY(p.market_session) &&
    p.market_session===saved.result.market_session && Array.isArray(p.observations) &&
    p.observations.length>0 && p.observations.length<=4096 && p.catalog_count===p.observations.length &&
    p.catalog_count===saved.result.catalog_count,'CONCEPT_OBSERVATION_SCOPE');
  require(new Set(p.observations.map(c=>c?.code)).size===p.catalog_count && p.observations.every(c=>
    /^[0-9]{6}$/.test(c?.code) && typeof c.name==='string' && c.market_session===p.market_session &&
    ['today','5d','10d'].every(k=>c.periods?.[k] && (c.periods[k].change_percent===null ||
      typeof c.periods[k].change_percent==='string' && /^-?\d+(?:\.\d+)?$/.test(c.periods[k].change_percent)))), 'CONCEPT_ROWS');
  return {rows:p.observations,day:p.market_session,hash:r.projection_hash};
}
const PHASE_LABELS={EMERGING:'20日相对强势新进入',STRENGTHENING:'持续强化',PERSISTENT:'持续但未进一步强化',MATURE_OR_DIVERGING:'强中分歧',WEAKENING_OR_EXIT:'弱化或退出',NOT_POSITIVE:'尚未形成20日相对强势',UNKNOWN:'阶段未知'};
const DEC=v=>typeof v==='string' && v.length<=160 && /^-?\d+(?:\.\d+)?$/.test(v);
/** Validate a derived, same-source reading after Reading.readFile authenticates its bytes. */
export function trendView(text,saved,observation){
  const r=JSON.parse(text),p=r?.projection;
  require(NONE(p) && p.version==='tdx-concept-trend-v1' && p.taxonomy===TAXONOMY &&
    p.kind==='MARKET_EXPRESSION' && p.qualification==='CONTEXT_ONLY' &&
    saved?.status==='VERIFIED_SAVED_LONG_HISTORY' && HASH.test(r.projection_hash) && r.projection_hash===saved.projection_hash &&
    p.observation_hash===observation.hash && HASH.test(p.base_capture_hash) && HASH.test(p.source_hash) &&
    p.market_session===observation.day && localTime(p.source_observed_at)!=='时间未知' &&
    p.benchmark?.full_code==='sh000300' && p.benchmark.source==='SAME_TDX_HOST' &&
    p.benchmark.history_end===observation.day && DAY(p.benchmark.history_start) &&
    Number.isInteger(p.benchmark.history_points) && p.benchmark.history_points>=2 && p.benchmark.history_points<=126 &&
    p.return_unit==='FRACTION_NOT_PERCENT' && p.source_calls_during_replay===0 &&
    p.policy?.phase_basis==='DESCRIPTIVE_20D_EXCESS_NOT_INVESTMENT_SIGNAL' &&
    p.policy.session_basis==='RETURNED_BENCHMARK_SESSIONS_NOT_EXCHANGE_CALENDAR' &&
    p.policy.custody==='EXTRACTED_SDK_TIME_AND_INTEGER_CLOSE_NOT_RAW_WIRE' &&
    p.historical_universe==='CURRENT_CATALOG_NOT_HISTORICAL_MEMBERSHIP' &&
    p.trend_age==='POSITIVE_20D_EXCESS_RUN_WITH_LEFT_CENSOR_NOT_THEME_LIFETIME' &&
    Array.isArray(p.observations) && p.catalog_count===p.observations.length &&
    p.catalog_count===observation.rows.length && p.catalog_count===saved.catalog_count,'CONCEPT_TREND_SCOPE');
  const originals=new Map(observation.rows.map(c=>[c.code,c])),names=new Map(observation.rows.map(c=>[c.code,c.name])),rows=new Map(),counts={'5':0,'20':0,'60':0};
  let phases=0,gaps=0;
  for(const c of p.observations){
    require(c && names.get(c.code)===c.name && !rows.has(c.code) && c.full_code===originals.get(c.code)?.full_code && /^(sh|sz)[0-9]{6}$/.test(c.full_code) &&
      Object.hasOwn(PHASE_LABELS,c.phase) && typeof c.phase_reason==='string' &&
      (c.gap===null || typeof c.gap==='string') && c.horizons &&
      Object.keys(c.horizons).sort().join(',')==='20,5,60','CONCEPT_TREND_ROW');
    for(const k of ['5','20','60']){
      const h=c.horizons[k];require(h===null || typeof h==='object' &&
        ['index_return','benchmark_return','excess_return'].every(n=>DEC(h[n])),'CONCEPT_TREND_HORIZON');
      if(h!==null)counts[k]++;
    }
    if(c.gap!==null){gaps++;require(c.phase==='UNKNOWN' && Object.values(c.horizons).every(h=>h===null),'CONCEPT_TREND_GAP');}
    else {
      require(Number.isInteger(c.history_points) && c.history_points>=2 && c.history_points<=126 &&
        DAY(c.history_start) && c.history_end===observation.day && DAY(c.previous_session) &&
        c.previous_session<observation.day && c.history_start<=c.previous_session,'CONCEPT_TREND_CLOCK');
      for(const n of [5,20,60])require((c.horizons[String(n)]!==null)===(c.history_points>n),'CONCEPT_TREND_COVERAGE');
      const count=c.positive_20d_excess_persistence_sessions;
      require(count===null && c.history_points<=20 || Number.isInteger(count) && count>=0 && count<=c.history_points-20,'CONCEPT_TREND_PERSISTENCE');
      require((c.previous_20d_excess===null || DEC(c.previous_20d_excess)) &&
        (c.excess_acceleration_5_sessions_20d===null || DEC(c.excess_acceleration_5_sessions_20d)), 'CONCEPT_TREND_CHANGE');
      if(count>0)require(DAY(c.positive_20d_excess_run_started) && c.positive_20d_excess_run_started<=observation.day &&
        typeof c.positive_20d_excess_persistence_left_censored==='boolean','CONCEPT_TREND_AGE');
    }
    if(c.phase!=='UNKNOWN'){
      phases++;require(c.horizons['60']!==null && c.previous_20d_excess!==null && c.excess_acceleration_5_sessions_20d!==null && c.gap===null,'CONCEPT_TREND_PHASE_HISTORY');
    }
    rows.set(c.code,c);
  }
  require(['5','20','60'].every(k=>p.coverage?.horizons?.[k]===counts[k] && saved.coverage?.horizons?.[k]===counts[k]) &&
    p.coverage.phase_rows===phases && saved.coverage.phase_rows===phases &&
    p.coverage.unavailable_rows===gaps && saved.coverage.unavailable_rows===gaps,'CONCEPT_TREND_INVENTORY');
  return {data:p,rows};
}
function phaseText(row){
  if(row.phase_reason==='TWENTY_DAY_EXCESS_EXITED_POSITIVE_STATE')return '20日相对强势条件已退出';
  if(row.phase_reason==='NONPOSITIVE_20D_EXCESS_STILL_WEAKENING_NOT_NEW_EXIT')return '相对走势仍弱，不是本次新退出';
  return PHASE_LABELS[row.phase];
}
function trendDetail(row,el,disclosure){
  const pct=v=>v===null?'未知':displayDecimal(v,{percent:true});
  const title=el('p',phaseText(row));
  if(row.gap)return [title,el('p','该概念长期数据未通过校验；不是条件不满足。'),disclosure('长期数据诊断',el('p',row.gap))];
  const count=row.positive_20d_excess_persistence_sessions;
  const age=count===null?'持续天数未知':count===0?'本次20日超额收益不为正':`${row.positive_20d_excess_persistence_left_censored?'至少 ':''}${count} 个已返回交易日的20日超额收益连续为正；不是题材年龄`;
  return [title,el('p',age),disclosure('多周期依据',
    ...[5,20,60].map(n=>{const h=row.horizons[String(n)];return el('p',h?`${n}日：指数 ${pct(h.index_return)} · 沪深300 ${pct(h.benchmark_return)} · 超额 ${pct(h.excess_return)}`:`${n}日：历史不足，未计算`);}),
    el('p',`相对20日超额收益较5个交易日前变化：${pct(row.excess_acceleration_5_sessions_20d).replace('%',' 个百分点')}。这是差值；不是收益预测。`),
    el('p',`本次取得历史 ${row.history_start}—${row.history_end}；上一已返回交易日 ${row.previous_session}。同次采集回看，不是假称当时已保存的信号。`))];
}

export function membershipView(text,saved,observation){
  const r=JSON.parse(text),p=r?.projection;
  require(NONE(p) && p.version==='tdx-concept-membership-v1' && p.taxonomy===TAXONOMY &&
    saved?.status==='VERIFIED_SAVED_MEMBERSHIP' && HASH.test(r.projection_hash) && r.projection_hash===saved.projection_hash &&
    HASH.test(p.capture_hash) && p.observation_hash===observation.hash && p.market_session===observation.day &&
    p.source_prepared_date===observation.day && localTime(p.source_observed_at)!=='时间未知' &&
    p.membership_time_basis==='SAVED_SOURCE_PREPARATION_NOT_HISTORICAL_EFFECTIVE_MEMBERSHIP' &&
    p.historical_membership==='NOT_ESTABLISHED' && p.member_ranking==='NOT_COMPUTED' &&
    p.business_benefit==='NOT_ESTABLISHED' && p.source_calls===0 && p.parser_version==='3.2.2' &&
    Array.isArray(p.concepts) && p.catalog_count===observation.rows.length && p.concepts.length===p.catalog_count &&
    p.catalog_count===saved.catalog_count && p.securities && typeof p.securities==='object' && !Array.isArray(p.securities),
    'CONCEPT_MEMBERSHIP_SCOPE');
  const names=new Map(observation.rows.map(c=>[c.code,c.name])),members=new Map(), used=new Set();let total=0;
  for(const c of p.concepts){
    require(names.get(c?.code)===c.name && !members.has(c.code) && Array.isArray(c.members) && c.members.length<=10000 &&
      new Set(c.members).size===c.members.length && c.members.every(t=>typeof t==='string' && TICKER.test(t)), 'CONCEPT_MEMBER_IDENTITY');
    total+=c.members.length;require(total<=200000,'CONCEPT_MEMBER_BOUND');
    members.set(c.code,new Set(c.members));for(const t of c.members)used.add(t);
  }
  require(total===p.relation_count && total===saved.relation_count && used.size<=10000 &&
    used.size===Object.keys(p.securities).length && [...used].every(t=>{
      const s=p.securities[t];return s && typeof s.in_source_catalog==='boolean' && (s.name===null || typeof s.name==='string');
    }), 'CONCEPT_MEMBER_INVENTORY');
  return {data:p,sets:members};
}
export function overlaps(view,code){
  const own=view.sets.get(code);require(own,'CONCEPT_NOT_REGISTERED');
  return view.data.concepts.filter(c=>c.code!==code).map(c=>{
    const other=view.sets.get(c.code), shared=[...own].filter(t=>other.has(t));
    return {code:c.code,name:c.name,shared,ownCount:own.size,otherCount:other.size,
      unionCount:own.size+other.size-shared.length};
  }).filter(r=>r.shared.length).sort((a,b)=>b.shared.length-a.shared.length || a.code.localeCompare(b.code));
}
const LABELS={CONTRACT_CHECKED_RAW_READING:'通过原价格观察',CONDITIONS_NOT_MET:'原条件未满足',DATA_QUALIFICATION_FAILED:'数据不可用，未作条件否决'};
export function stockStatus(ticker,lane){
  const result=lane?.last_qualified_result,rows=result?.dispositions;
  if(!Array.isArray(rows))return '本读取没有可用个股检查目录';
  const hits=rows.filter(r=>r?.thscode===ticker);
  if(!hits.length)return '不在本次已保存个股检查范围';
  if(hits.length!==1 || !LABELS[hits[0].status] || !DAY(result.market_session))return '原个股记录冲突或格式未知';
  return `${LABELS[hits[0].status]}（${result.market_session}）`;
}
function pages(target,rows,size,draw,ui){
  let page=0;const body=ui.el('div'),bar=ui.el('div',undefined,'product-actions');target.append(body,bar);
  function render(){
    const max=Math.max(1,Math.ceil(rows.length/size));page=Math.max(0,Math.min(page,max-1));
    body.replaceChildren(...draw(rows.slice(page*size,page*size+size)));
    const prev=ui.button('上一页',()=>{page--;render();}),next=ui.button('下一页',()=>{page++;render();});
    prev.disabled=page===0;next.disabled=page+1>=max;
    bar.replaceChildren(ui.el('span',`${rows.length} 项 · ${page+1}/${max}`),prev,next);
  }render();
}
export function conceptsPage(target,ctx){
  const {reading,ui,active,onRead,onCompany}=ctx,{el,card,button,notice,folded,disclosure,link}=ui;
  const saved=reading.payload.research?.tdx_concept_context;
  if(!saved)return; // Older readings retain their existing market panels.
  const panel=card('概念与成员','通达信自己的概念分类；来源成员不是持仓、业务受益或买卖建议。');target.append(panel);
  const od=saved.details?.observation,md=saved.membership?.file,td=saved.trend?.details?.['trend.json'];
  if(saved.status!=='VERIFIED_SAVED_TDX_CONCEPT_SOURCE' || !od){panel.append(notice('概念资料本次不可读；不是没有概念变化。'));return;}
  const body=el('div');body.append(el('p','正在读取保存的概念与成员…'));panel.append(body);
  const read=d=>Promise.resolve().then(()=>reading.readFile(d));
  Promise.allSettled([read(od),md?read(md):Promise.resolve(null),td?read(td):Promise.resolve(null)]).then(results=>{
    if(!active())return;
    if(results[0].status!=='fulfilled')throw results[0].reason;
    const observation=conceptView(results[0].value.text,saved);let membership=null,memberError=null;
    try{if(results[1].status==='rejected')throw results[1].reason;
      if(results[1].value)membership=membershipView(results[1].value.text,saved.membership,observation);
    }catch(e){memberError=e;}
    let trend=null,trendError=null;
    try{if(results[2].status==='rejected')throw results[2].reason;
      if(results[2].value)trend=trendView(results[2].value.text,saved.trend,observation);
    }catch(e){trendError=e;}
    const loadStock=makeStockComparisonLoader(reading);
    const search=el('input'),catalog=el('div'),detail=el('div');search.type='search';
    search.placeholder='搜索概念名称或代码';search.setAttribute('aria-label','搜索概念');
    body.replaceChildren(el('p',`保存市场日 ${observation.day} · 完整可用概念 ${observation.rows.length} 项`),
      notice(trend?'长期走势以同期沪深300为基准；阶段是20日相对路径描述，不是业务受益或投资信号。':'本版本没有可读的20／60日相对走势；保留原当日、5日、10日行情，不把短期涨幅改名为完整趋势。'));
    const browser=disclosure('浏览全部概念与成员',search,catalog,detail);body.append(browser);
    if(membership)body.insertBefore(el('p',`成员资料日 ${membership.data.source_prepared_date} · ${membership.data.relation_count} 条关系；不是这些日期之前的历史成员。`),browser);
    else body.insertBefore(notice('成员资料未能取得或通过校验；短期行情仍可读，不表示没有成员。'),browser);
    if(trend)body.append(el('p',`长期可比覆盖 5/20/60日：${['5','20','60'].map(k=>trend.data.coverage.horizons[k]).join('/')}；完整目录 ${observation.rows.length}。`),
      el('p',`长期资料取得于 ${localTime(trend.data.source_observed_at)}；非历史成员、非当时已知信号。`,'small'));
    if(trendError)body.append(folded('长期走势读取诊断',String(trendError.message)));
    if(td)panel.append(disclosure('长期走势原件',button('阅读完整长期走势',()=>onRead(td)),link('固定版本长期走势',fileUrl(reading.ref,td.read_path))));
    if(memberError)body.append(folded('成员读取诊断',String(memberError.message)));
    panel.append(disclosure('依据与固定版本',button('阅读原概念行情',()=>onRead(od)),link('固定版本概念行情',fileUrl(reading.ref,od.read_path))));
    if(md)panel.append(disclosure('完整成员原件',button('阅读全部成员原件',()=>onRead(md)),link('固定版本成员',fileUrl(reading.ref,md.read_path))));
    function select(code){
      if(!active() || !membership)return;
      const c=membership.data.concepts.find(v=>v.code===code);require(c,'CONCEPT_NOT_REGISTERED');
      const query=el('input'),members=el('div'),related=el('div');query.type='search';query.placeholder='搜索成员名称或代码';query.setAttribute('aria-label','搜索概念成员');
      detail.replaceChildren(el('h4',`${c.name} · 来源成员 ${c.members.length}`),
        el('p','以下按来源顺序列成员，不是领先成员排名。股价检查各有保存日期；进入公司页不等于已完成研究。'),query,members,
        disclosure('与其他概念共享的成员',el('p','按共享成员数展示关系，不是机会排序。两边分母分别列出，不合并概念身份。'),related));
      if(trend)detail.prepend(...trendDetail(trend.rows.get(code),el,disclosure));
      const comparison=el('section');detail.insertBefore(comparison,query);
      mountStockComparison(comparison,{...ctx,active:()=>active()&&detail.contains(comparison)},membership,code,loadStock);
      const securities=membership.data.securities;
      function drawMembers(){members.replaceChildren();const q=query.value.trim().toLowerCase();
        const rows=c.members.filter(t=>`${t} ${securities[t].name||''}`.toLowerCase().includes(q));
        pages(members,rows,25,part=>part.map(t=>{
          const s=securities[t],row=el('div',undefined,'human-material ref');
          row.append(button(`${s.name||'名称未知'} · ${t}`,()=>{if(active())onCompany(t);}),
            el('p',s.in_source_catalog?stockStatus(t,reading.payload.lanes?.stock):'该成员未见于同包证券目录；不推断已退市'),
            el('p','业务受益需独立研究；本页没有新增研究结论。','small'));return row;
        }),ui);
      }query.oninput=drawMembers;drawMembers();
      const relationships=overlaps(membership,code);
      if(!relationships.length)related.append(el('p','在本份完整成员表内未发现共享成员；不是业务独立性证明。'));
      else pages(related,relationships,10,part=>part.map(r=>{
        const row=el('div',undefined,'human-material ref');row.append(button(r.name,()=>select(r.code)),
          el('p',`共享 ${r.shared.length} 位 · 本概念 ${r.shared.length}/${r.ownCount} · 对方 ${r.shared.length}/${r.otherCount}`),
          el('p',r.shared.length===r.ownCount && r.shared.length===r.otherCount?'成员集合相同，概念身份仍不同':
            r.shared.length===r.ownCount?'本概念成员全部包含于对方':r.shared.length===r.otherCount?'对方成员全部包含于本概念':'部分成员重叠'),
          disclosure('共享成员明细',el('p',r.shared.map(t=>`${securities[t].name||'名称未知'} ${t}`).join('；'))));return row;
      }),ui);
    }
    function drawCatalog(){catalog.replaceChildren();const q=search.value.trim().toLowerCase();
      const rows=observation.rows.filter(c=>`${c.name} ${c.code}`.toLowerCase().includes(q));
      pages(catalog,rows,15,part=>part.map(c=>{
        const row=el('div',undefined,'human-material ref'),choose=button(`${c.name} · ${c.code}`,()=>select(c.code));choose.disabled=!membership;
        row.append(choose,el('p',`当日 / 5日 / 10日：${['today','5d','10d'].map(k=>c.periods[k].change_percent===null?'未知':displayDecimal(c.periods[k].change_percent)+'%').join(' / ')}`));
        if(trend)row.append(...trendDetail(trend.rows.get(c.code),el,disclosure));
        if(membership)row.append(el('p',`来源成员 ${membership.sets.get(c.code).size} 位；点击查看个股检查与重叠`,'small'));return row;
      }),ui);
    }search.oninput=drawCatalog;drawCatalog();
  }).catch(error=>{if(active())body.replaceChildren(notice('概念行情读取未完成；其他市场材料仍可读，不当作零变化。'),folded('概念读取诊断',String(error.message)));});
}
