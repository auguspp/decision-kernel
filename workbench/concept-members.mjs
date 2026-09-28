/** Same-R TDX observations and members. No source calls, research or saved state. */
import {fileUrl} from './reading.mjs';
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
  const od=saved.details?.observation,md=saved.membership?.file;
  if(saved.status!=='VERIFIED_SAVED_TDX_CONCEPT_SOURCE' || !od){panel.append(notice('概念资料本次不可读；不是没有概念变化。'));return;}
  const body=el('div');body.append(el('p','正在读取保存的概念与成员…'));panel.append(body);
  const read=d=>Promise.resolve().then(()=>reading.readFile(d));
  Promise.allSettled([read(od),md?read(md):Promise.resolve(null)]).then(results=>{
    if(!active())return;
    if(results[0].status!=='fulfilled')throw results[0].reason;
    const observation=conceptView(results[0].value.text,saved);let membership=null,memberError=null;
    try{if(results[1].status==='rejected')throw results[1].reason;
      if(results[1].value)membership=membershipView(results[1].value.text,saved.membership,observation);
    }catch(e){memberError=e;}
    const search=el('input'),catalog=el('div'),detail=el('div');search.type='search';
    search.placeholder='搜索概念名称或代码';search.setAttribute('aria-label','搜索概念');
    body.replaceChildren(el('p',`保存市场日 ${observation.day} · 完整可用概念 ${observation.rows.length} 项`),
      notice('现有来源只提供当日、5日、10日路径。20／60日、相对基准和长期阶段尚未建立，不能把短期涨幅改名为完整趋势。'));
    const browser=disclosure('浏览全部概念与成员',search,catalog,detail);body.append(browser);
    if(membership)body.insertBefore(el('p',`成员资料日 ${membership.data.source_prepared_date} · ${membership.data.relation_count} 条关系；不是这些日期之前的历史成员。`),browser);
    else body.insertBefore(notice('成员资料未能取得或通过校验；短期行情仍可读，不表示没有成员。'),browser);
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
        if(membership)row.append(el('p',`来源成员 ${membership.sets.get(c.code).size} 位；点击查看个股检查与重叠`,'small'));return row;
      }),ui);
    }search.oninput=drawCatalog;drawCatalog();
  }).catch(error=>{if(active())body.replaceChildren(notice('概念行情读取未完成；其他市场材料仍可读，不当作零变化。'),folded('概念读取诊断',String(error.message)));});
}
