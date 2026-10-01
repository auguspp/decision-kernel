/** Saved Stock reading in a TDX member view. No qualification or source calls. */
import {fileUrl} from './reading.mjs';
import {displayDecimal, localTime} from './product.mjs';
const HASH=/^[a-f0-9]{64}$/, TICKER=/^[0-9]{6}\.(SH|SZ|BJ)$/;
const DEC=v=>typeof v==='string' && v.length<=160 && /^-?\d+(?:\.\d+)?$/.test(v);
const DAY=v=>typeof v==='string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10)===v;
const LABELS={CONTRACT_CHECKED_RAW_READING:'通过价格观察',CONDITIONS_NOT_MET:'原条件未满足',DATA_QUALIFICATION_FAILED:'数据不可用，未作条件否决',REQUEST_FAILED:'数据请求未完成，未作条件否决'};
const POLICY_VERSIONS=new Set(['stock-market-expression-window-qualified-v8','stock-market-expression-window-qualified-v9']);
const PRICE_CONVENTIONS=new Set(['RAW_UNADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN','REPORTED_ACTION_REFERENCE_ADJUSTED_NOT_TOTAL_RETURN','PROVIDER_FORWARD_ADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN']);
function require(ok,reason){if(!ok)throw new Error(reason);}
function compareDecimal(a,b){
  require(DEC(a)&&DEC(b),'STOCK_COMPARISON_DECIMAL');
  const [ai,af='']=a.split('.'),[bi,bf='']=b.split('.'),scale=Math.max(af.length,bf.length);
  const x=BigInt(ai+af.padEnd(scale,'0')),y=BigInt(bi+bf.padEnd(scale,'0'));
  return x<y?-1:x>y?1:0;
}
function directions(row){
  const found=new Map();
  require(Array.isArray(row.current_origins)&&row.current_origins.length<=16,'STOCK_COMPARISON_ORIGINS');
  for(const origin of row.current_origins){
    require(Array.isArray(origin.direction_sources)&&origin.direction_sources.length<=16 &&
      Array.isArray(origin.current_member_sectors)&&Array.isArray(origin.sector_codes),'STOCK_COMPARISON_ORIGIN_SCOPE');
    for(const d of origin.direction_sources){
      require(d && typeof d.name==='string' && d.name.length<=256 &&
        ((d.family==='BROAD_881'&&/^881\d{3}\.TI$/.test(d.thscode)) ||
         (d.family==='GRANULAR_884'&&/^884\d{3}\.TI$/.test(d.thscode))) &&
        origin.current_member_sectors.includes(d.thscode)&&origin.sector_codes.includes(d.thscode),
        'STOCK_COMPARISON_DIRECTION_IDENTITY');
      require(!found.has(d.thscode)||found.get(d.thscode).name===d.name,'STOCK_COMPARISON_DIRECTION_CONFLICT');
      found.set(d.thscode,{code:d.thscode,name:d.name,family:d.family});
    }
  }
  return [...found.values()];
}
/** Byte authentication belongs to Reading.readFile; this checks the retained consumer contract. */
export function stockComparisonView(text,saved){
  const report=JSON.parse(text),p=report?.projection;
  require(saved && p && HASH.test(report.projection_hash) && report.projection_hash===saved.projection_hash &&
    DAY(p.market_session)&&p.market_session===saved.market_session &&
    p.observed_at===saved.observed_at&&localTime(p.observed_at)!=='时间未知' && p.status===saved.status &&
    p.scope===saved.scope&&p.scope==='BOUNDED_SURFACED_SECTOR_MARKET_EXPRESSION_NOT_ALL_A_SHARES' &&
    p.semantics==='BOUNDED_MARKET_EXPRESSION_NOT_BUSINESS_BENEFIT_OR_RECOMMENDATION' &&
    p.reference_input_provenance==='HITHINK_REQUEST_BOUND_RAW_OBSERVATION' &&
    POLICY_VERSIONS.has(p.policy?.version) && p.price_path_is_not_total_return===true &&
    ['research_authority','human_attention_authority','signal_transition_authority','investment_authority'].every(k=>p[k]==='NONE') &&
    p.automatic_research_routing===false&&p.creates_canonical_wake===false &&
    Array.isArray(p.all_stock_observations)&&p.all_stock_observations.length<=16&&
    Array.isArray(saved.dispositions)&&saved.dispositions.length===p.all_stock_observations.length,
    'STOCK_COMPARISON_SCOPE');
  const declared=new Map(),rows=new Map(),counts={CONTRACT_CHECKED_RAW_READING:0,CONDITIONS_NOT_MET:0,DATA_QUALIFICATION_FAILED:0,REQUEST_FAILED:0};
  let priceChecked=0;
  for(const d of saved.dispositions){
    require(TICKER.test(d?.thscode)&&Object.hasOwn(LABELS,d.status)&&!declared.has(d.thscode),'STOCK_COMPARISON_DISPOSITIONS');
    declared.set(d.thscode,d.status);
  }
  for(const r of p.all_stock_observations){
    require(TICKER.test(r?.thscode)&&declared.get(r.thscode)===r.status&&!rows.has(r.thscode) &&
      typeof r.company_name==='string'&&r.company_name.length<=256 &&
      Array.isArray(r.excluded_reasons)&&r.excluded_reasons.length<=32&&r.excluded_reasons.every(x=>typeof x==='string'&&x.length<=256),
      'STOCK_COMPARISON_ROW');
    const path=r.stock_path,windows={};
    let basis=null;
    if(path===null){
      require(['DATA_QUALIFICATION_FAILED','REQUEST_FAILED','CONDITIONS_NOT_MET'].includes(r.status),
        'STOCK_COMPARISON_UNAVAILABLE_PRICE');
    }else{
      require(PRICE_CONVENTIONS.has(path.price_convention)&&path.returns,'STOCK_COMPARISON_PRICE_CONVENTION');
      basis=path.price_convention;priceChecked++;
      const forward=basis==='PROVIDER_FORWARD_ADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN';
      const reported=basis==='REPORTED_ACTION_REFERENCE_ADJUSTED_NOT_TOTAL_RETURN';
      if(forward)require(path.input_checks?.corporate_action_query_succeeded===false &&
        path.input_checks?.corporate_action_query?.provider_business_code===3002 &&
        path.input_checks?.adjusted_history_fallback?.status==='USED' &&
        path.input_checks.adjusted_history_fallback.event_details_inferred===false,
        'STOCK_COMPARISON_FORWARD_FALLBACK');
      for(const n of ['5','20','60']){
        const value=path.returns[n],h=r.market_comparison?.[n];
        require(value===null||DEC(value),'STOCK_COMPARISON_VALUE');
        if(value===null){windows[n]=null;continue;}
        const w=(forward?path.input_checks?.adjusted_history_fallback?.history_window_checks?.[n]:
          path.input_checks?.history_window_checks?.[n]);
        const a=path.input_checks?.action_window_checks?.[n];
        const actionOK=forward || (a&&a.base_session===w?.base_session&&a.end_session===w?.end_session &&
          (a.usable_for_raw_comparison===true || (reported&&a.usable_for_price_reference_adjusted_comparison===true)));
        require(w&&w.usable_for_raw_comparison===true&&actionOK &&
          DAY(w.base_session)&&w.base_session<p.market_session&&w.end_session===p.market_session &&
          h&&h.stock_return===value&&DEC(h.benchmark_return)&&DEC(h.excess_return),
          'STOCK_COMPARISON_WINDOW');
        windows[n]={base:w.base_session,end:w.end_session,value,benchmark:h.benchmark_return,excess:h.excess_return};
      }
    }
    counts[r.status]++;
    rows.set(r.thscode,{ticker:r.thscode,name:r.company_name,status:r.status,windows,basis,
      directions:directions(r),reasons:r.excluded_reasons,
      gap:r.input_failure?.reason_code??null});
  }
  for(const [key,n] of Object.entries({planned_issuers:rows.size,dispositioned_issuers:rows.size,
    price_path_checked_issuers:priceChecked,
    qualified_issuers:counts.CONTRACT_CHECKED_RAW_READING,conditions_not_met_issuers:counts.CONDITIONS_NOT_MET,
    unavailable_issuers:counts.DATA_QUALIFICATION_FAILED+counts.REQUEST_FAILED})){
    require(p.coverage?.[key]===n&&saved.coverage?.[key]===n,'STOCK_COMPARISON_COVERAGE');
  }
  return {rows,day:p.market_session,hash:report.projection_hash};
}
/** Intersect actual identities; never infer a Concept leader from its name or Sector rank. */
export function checkedMembers(membership,code,stock){
  const members=membership.sets.get(code);require(members,'STOCK_COMPARISON_CONCEPT');
  const rows=[...members].filter(t=>stock.rows.has(t)).map(t=>stock.rows.get(t));
  const priced=rows.filter(r=>r.windows['20']),bounds=new Set(priced.map(r=>r.windows['20'].base+'/'+r.windows['20'].end));
  const sameDay=membership.data.market_session===stock.day,ranked=sameDay&&priced.length>=2&&bounds.size===1;
  if(ranked)rows.sort((a,b)=>{
    const x=a.windows['20'],y=b.windows['20'];
    return x&&y?compareDecimal(y.value,x.value)||a.ticker.localeCompare(b.ticker):x?-1:y?1:0;
  });
  return {rows,total:members.size,checked:rows.length,notChecked:members.size-rows.length,
    qualified:rows.filter(r=>r.status==='CONTRACT_CHECKED_RAW_READING').length,
    notMet:rows.filter(r=>r.status==='CONDITIONS_NOT_MET').length,
    unavailable:rows.filter(r=>r.status==='DATA_QUALIFICATION_FAILED'||r.status==='REQUEST_FAILED').length,
    sameDay,ranked,day:stock.day,memberDay:membership.data.market_session};
}
/** One lazy read for this page/R. Rejected reads remain rejected, not retried by selection. */
export function makeStockComparisonLoader(reading){
  const saved=reading.payload.lanes?.stock?.last_qualified_result;
  const descriptor=saved?.details?.['reading/stock-reading.json'];let pending;
  return ()=>{
    if(!pending)pending=descriptor?Promise.resolve().then(()=>reading.readFile(descriptor)).then(result=>({
      view:stockComparisonView(result.text,saved),descriptor})):Promise.resolve(null);
    return pending;
  };
}
export function mountStockComparison(target,ctx,membership,code,load){
  const {ui,active,onCompany,onRead,reading}=ctx,{el,button,notice,disclosure,link,folded}=ui;
  target.className='concept-stock-comparison';target.append(el('h4','已检查成员比较'),el('p','正在读取已保存的个股价格正文…'));
  load().then(result=>{
    if(!active())return;
    target.replaceChildren(el('h4','已检查成员比较'));
    if(!result){target.append(notice('本版本未登记个股价格正文；原成员处置仍可读，不作排名。'));return;}
    const view=checkedMembers(membership,code,result.view);
    target.append(el('p',`已保存检查 ${view.checked}/${view.total} 位 · 通过 ${view.qualified} · 条件未满足 ${view.notMet} · 不可判断 ${view.unavailable} · 未检查 ${view.notChecked}`),
      el('p',`成员日 ${view.memberDay}；个股价格保存日 ${view.day}。`),
      notice(!view.sameDay?'日期不同，仅作历史参考，不作同日成员排名。':view.ranked?
        '以下仅在已检查且窗口一致的样本内按20日收盘收益排列；不是全体成员排名，也不是综合优胜。':
        '可比价格样本不足或窗口不同，保留来源成员顺序；不作排名。'));
    if(!view.checked)target.append(el('p','本概念成员不在这份个股检查范围；不是已查且无机会。'));
    const pct=v=>displayDecimal(v,{percent:true});
    for(const r of view.rows){
      const card=el('div',undefined,'human-material ref'),h=r.windows['20'];
      card.append(button(`查看 ${r.name} ${r.ticker} 的已有研究`,()=>{if(active())onCompany(r.ticker);}),
        el('p',`${LABELS[r.status]}（${view.day}）`),el('p',h?`20日收盘收益 ${pct(h.value)}`:'20日价格不可比较；不是零收益'));
      const basisText=r.basis==='PROVIDER_FORWARD_ADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN'?
        '公司行动端点未准备时使用供应商 forward-adjusted 价格路径作有限价格比较；原3002缺口仍保留，不证明事件完整，也不是总回报。':
        r.basis==='REPORTED_ACTION_REFERENCE_ADJUSTED_NOT_TOTAL_RETURN'?
        '已报告公司行动只用于价格参考调整；原始公司行动记录保留，不是总回报或经营受益证明。':
        '未复权收盘价格路径，不是总回报。';
      const evidence=[el('p',basisText+' 原基准不是本概念指数，不能解释成跑赢该概念。')];
      for(const n of ['5','20','60']){const w=r.windows[n];evidence.push(el('p',w?
        `${n}日 ${w.base}—${w.end}：个股 ${pct(w.value)} · 原市场基准 ${pct(w.benchmark)} · 超额 ${pct(w.excess)}`:
        `${n}日：未取得可比较价格，保持未知`));}
      evidence.push(el('p',r.directions.length?'原发现来路：'+r.directions.map(d=>`${d.family==='BROAD_881'?'宽行业':'细分行业'} ${d.name} ${d.code}`).join('；'):'原发现来路未提供；不按名称补关系。'),
        el('p','这是同一证券的TDX成员与原HiThink行业来路，不代表分类相等、指数走势互证或业务受益。'));
      if(r.reasons.length)evidence.push(el('p','原条件未满足原因：'+r.reasons.join('；')));
      if(r.gap)evidence.push(el('p','原数据缺口：'+String(r.gap)));
      card.append(disclosure('价格窗口与原发现来路',...evidence));target.append(card);
    }
    target.append(disclosure('个股比较原件',button('阅读这份完整个股检查',()=>{if(active())onRead(result.descriptor);}),
      link('固定版本个股检查',fileUrl(reading.ref,result.descriptor.read_path))));
  }).catch(error=>{if(active())target.replaceChildren(el('h4','已检查成员比较'),
    notice('个股比较正文未取得或核验失败；原概念、成员和处置仍可读，不作排名。'),folded('个股比较诊断',String(error.message)));});
}
