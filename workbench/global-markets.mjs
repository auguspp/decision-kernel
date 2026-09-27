/** Human reading of the two B1 saved source families, never live quotes or causes. */
export const GLOBAL_REPORT = 'details/markets/global-market.json';
const VERSION = 'global-market-reading-v1';
const SHA = /^[a-f0-9]{40}$/, HASH = /^[a-f0-9]{64}$/;
const INDEX = {SPX:'标普500', IXIC:'纳斯达克综合', HSI:'恒生指数', HKTECH:'恒生科技', N225:'日经225', GDAXI:'德国 DAX'};
const TENORS = ['on','1w','2w','1m','3m','6m','9m','1y'];
const names = {on:'隔夜', '1w':'1周', '2w':'2周', '1m':'1个月', '3m':'3个月', '6m':'6个月', '9m':'9个月', '1y':'1年'};
const authority = p => p && ['signal_transition_authority','human_attention_authority','research_authority','investment_authority'].every(k=>p[k]==='NONE') && p.automatic_admission===false && p.odds_recomputed===false;
function require(ok) { if (!ok) throw new Error('GLOBAL_MARKET_CONTEXT_UNCONFIRMED'); }
function clock(v) { return typeof v==='string' && /(Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v)); }
function day(v) { return typeof v==='string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10)===v; }
function numeric(v) { return v===null || typeof v==='string' && /^-?\d+(?:\.\d+)?$/.test(v) && v.length<=40 && Number.isFinite(Number(v)); }
const number = v => v===null ? '未取得' : v.replace(/(\.\d*?[1-9])0+$|\.0+$/, '$1');
const time = v => new Date(v).toLocaleString('zh-CN',{hour12:false});

export function globalMarketView(text, saved) {
  const root=JSON.parse(text), p=root?.projection;
  require(p?.version===VERSION && saved?.version===VERSION && HASH.test(root.projection_hash) &&
    root.projection_hash===saved.projection_hash && p.checked_at===saved.checked_at && clock(p.checked_at) &&
    authority(p.authority) && p.source_calls===0 && p.complete_global_coverage===false &&
    Object.keys(p.families||{}).sort().join(',')==='indices,shibor');
  const families=[];
  for (const family of ['indices','shibor']) {
    const state=p.families[family], snap=state?.snapshot;
    require(typeof state?.latest_read_status==='string');
    const group={family,title:family==='indices'?'国际指数 · 保存日线':'人民币同业利率 · Shibor',
      status:state.latest_read_status, latest:state.latest_attempt, rows:[], snapshot:null, current:false};
    if (snap) {
      const r=snap.report, run=snap.run;
      require(r?.version==='global-market-context-v1' && r.family===family && authority(r.authority) &&
        r.source==='TUSHARE_RELAY_THIRD_PARTY_NOT_OFFICIAL_TUSHARE' && r.source_calls_during_replay===0 &&
        HASH.test(r.capture_hash) && SHA.test(r.identity?.code_commit) &&
        r.identity?.repository==='auguspp/decision-kernel' && r.identity.workflow==='.github/workflows/radar-global-market.yml' &&
        r.identity.ref==='refs/heads/main' && r.identity.event==='workflow_dispatch' && r.identity.attempt===1 &&
        r.identity.run_id===run?.id && Number.isSafeInteger(run.id) && run.id>0 && run.run_attempt===1 &&
        run.path===r.identity.workflow && run.head_branch==='main' && run.event==='workflow_dispatch' && run.status==='completed' &&
        run.head_sha===r.identity.code_commit &&
        clock(r.captured_from) && clock(r.captured_through) && Date.parse(r.captured_from)<=Date.parse(r.captured_through) &&
        Date.parse(r.captured_through)<=Date.parse(p.checked_at) && Array.isArray(r.outcomes) &&
        r.outcomes.map(o=>o.id).join(',')===(family==='indices'?Object.keys(INDEX).join(','):'shibor'));
      group.snapshot=snap;
      group.current=state.latest_attempt?.id===run.id && state.latest_attempt?.run_attempt===1 &&
        ['CAPTURE_READ','FAILED_RUN_CAPTURE_READ','REUSED_RETAINED_CAPTURE'].includes(state.latest_read_status);
      let available=0;
      for (const outcome of r.outcomes) {
        require(Array.isArray(outcome.observations) && outcome.observations.length<=(family==='indices'?1:8));
        if (!outcome.observations.length) {
          group.rows.push({name:INDEX[outcome.id]||'Shibor 本批',missing:true,reason:outcome.status}); continue;
        }
        require(family!=='shibor' || outcome.observations.length===8);
        const seen=new Set();
        for (const row of outcome.observations) {
          require(day(row.source_date) && (row.previous_observed_date===null || day(row.previous_observed_date) && row.previous_observed_date<row.source_date) &&
            Date.parse(row.source_date)<=Date.parse(p.checked_at) && numeric(row.value) && numeric(row.previous_value) &&
            row.change_scope==='TWO_RETURNED_DATES_NOT_ASSERTED_CONSECUTIVE_SESSIONS' && !seen.has(row.symbol));
          seen.add(row.symbol);
          const index=family==='indices';
          require(index ? row.symbol===outcome.id && row.unit==='INDEX_POINTS' && Number(row.value)>0 && numeric(row.observed_interval_change_pct) :
            TENORS.includes(row.tenor) && row.symbol==='SHIBOR:'+row.tenor && row.unit==='ANNUAL_PERCENT' && row.currency==='CNY' && numeric(row.observed_interval_change_bp));
          if (row.value!==null) available++;
          const change=index?row.observed_interval_change_pct:row.observed_interval_change_bp;
          require(change===null || row.value!==null && row.previous_value!==null && row.previous_observed_date!==null);
          group.rows.push({name:index?INDEX[row.symbol]:names[row.tenor],missing:row.value===null,
            value:number(row.value)+(row.value===null?'':index?' 点':'%（年化）'), date:row.source_date,
            prior:row.previous_observed_date, change:change===null?'未取得':number(change)+(index?'%':' bp'),
            age:Math.floor((Date.parse(p.checked_at.slice(0,10))-Date.parse(row.source_date))/86400000), original:row});
        }
      }
      require(available===r.available_values && available>0);
    }
    families.push(group);
  }
  return {families,checked:p.checked_at,queryGap:p.query?.status==='QUERY_UNAVAILABLE' || !!p.query?.unattributed_run_ids?.length,
    priorGaps:Array.isArray(p.prior_read_gaps)?p.prior_read_gaps:[]};
}

/** Updates only its own panel so A-share search/input and other modules survive. */
export function globalMarketsPage(target, ctx) {
  const {reading,ui,active,onRead}=ctx, {el,card,button,notice,folded,dataTable,link}=ui;
  const panel=card('全球市场 · 已保存背景','目前覆盖国际指数与人民币同业利率；不是实时行情。');
  target.append(panel);
  panel.append(notice('美债/国际利率、黄金原油、外汇、加密资产尚未接入。Shibor不能代表全球债市。'));
  const saved=reading.payload.research?.global_market, ref=saved?.details?.json;
  if (!ref) { panel.append(notice('本包还没有可读全球市场资料；不是市场没有变化。')); return Promise.resolve(); }
  const content=el('div'); content.append(el('p','正在读取已保存市场资料…')); panel.append(content);
  return Promise.resolve().then(()=>{require(ref.read_path===GLOBAL_REPORT);return reading.readFile(ref);}).then(file=>{
    if (!active()) return;
    const view=globalMarketView(file.text,saved);
    content.replaceChildren(el('p',`本包检查：${time(view.checked)}；各市场保留自己的数据日期。`,'small'));
    if(view.queryGap)content.append(notice('最新运行查询有缺口；下面的历史结果不能证明当前更新成功。'));
    if(view.priorGaps.length)content.append(notice('部分旧资料未能完整恢复；原固定版本仍保留，未填成零。'));
    for (const group of view.families) {
      const section=el('section'); section.append(el('h4',group.title)); content.append(section);
      if (!group.snapshot) { section.append(notice('没有已核验的可读批次；不作无变化判断。'),folded('读取状态',group.status)); continue; }
      const capture=group.snapshot.report;
      if(!group.current)section.append(notice('以下为上次可读结果，不是本次更新成功。'));
      if(group.latest?.status!=='completed'||group.latest?.conclusion!=='success')section.append(notice('最近一次采集尚未成功完成；保留历史日期和已有结果。'));
      section.append(el('p',`采集截止：${time(capture.captured_through)} · 来源：第三方 Tushare Relay · ${capture.status==='AVAILABLE'?'本批所选系列均有值':'本批仅部分数据可读'}`,'small'));
      const heads=['对象','保存值','来源日期','两次返回间变化'];
      const {wrapper,body}=dataTable(group.family==='indices'?'点位不是估值或投资信号':'年化利率；1 bp = 0.01个百分点，不是收益率涨幅',heads);
      for(const row of group.rows){
        const tr=el('tr');
        const values=[row.name,row.value||'本次未取得',row.date?`${row.date}（距检查日${row.age}天）`:'未知',
          row.prior?`${row.change}（${row.prior} → ${row.date}）`:'比较区间未知'];
        values.forEach((v,i)=>{const td=el('td',v);td.setAttribute('data-label',heads[i]);tr.append(td);});body.append(tr);
      }
      section.append(wrapper,el('p','变化仅比较两个实际返回日期，不保证相邻交易日。发布时间与市场开闭状态仍未知。','small'));
      const a=group.snapshot.archive;
      require(HASH.test(a?.sha256) && a.read_path===`sources/artifacts/${a.sha256}.zip` && SHA.test(reading.ref));
      section.append(link('查看本批原始存档',`https://github.com/auguspp/decision-kernel/blob/${reading.ref}/${a.read_path}`),
        folded('运行与来源状态',JSON.stringify({latest:group.latest,reading:group.status,outcomes:capture.outcomes.map(o=>({id:o.id,status:o.status}))},null,2)));
    }
    content.append(button('阅读全球市场保存原件',()=>{if(active())onRead(ref);}));
  }).catch(error=>{if(active())content.replaceChildren(notice('全球市场资料未能读完；A股与其他模块不受影响，不解释为没有变化。'),folded('读取诊断',error.message));});
}
