/** Human reading of independently saved B1 families; no live quotes or causes. */
export const GLOBAL_REPORT = 'details/markets/global-market.json';
const V1='global-market-reading-v1', V2='global-market-reading-v2';
const SHA=/^[a-f0-9]{40}$/, HASH=/^[a-f0-9]{64}$/;
const INDEX={SPX:'标普500',IXIC:'纳斯达克综合',HSI:'恒生指数',HKTECH:'恒生科技',N225:'日经225',GDAXI:'德国 DAX'};
const TENORS=['on','1w','2w','1m','3m','6m','9m','1y'];
const names={on:'隔夜','1w':'1周','2w':'2周','1m':'1个月','3m':'3个月','6m':'6个月','9m':'9个月','1y':'1年'};
const UST={'1MONTH':'1个月','3MONTH':'3个月','6MONTH':'6个月','1YEAR':'1年','2YEAR':'2年','5YEAR':'5年','10YEAR':'10年','30YEAR':'30年'};
const FX=['USD','CNY','JPY','GBP'];
const PUBLIC={
  treasury:Object.fromEntries(Object.entries(UST).map(([t,n])=>['UST:'+t,{name:'美债 '+n,unit:'ANNUAL_PERCENT',label:'%（年化）',change:'bp'}])),
  fx:Object.fromEntries(FX.map(c=>['EUR/'+c,{name:'1欧元兑'+c,unit:c+'_PER_EUR',label:' '+c+'/EUR',change:'%'}])),
  commodities:{'GC=F':{name:'黄金 · GC=F',unit:'USD_PER_TROY_OUNCE',label:' 美元/金衡盎司',change:null},
    'CL=F':{name:'WTI原油 · CL=F',unit:'USD_PER_BARREL',label:' 美元/桶',change:null},
    'BZ=F':{name:'Brent原油 · BZ=F',unit:'USD_PER_BARREL',label:' 美元/桶',change:null}},
  crypto:Object.fromEntries(['BTC','ETH'].map(c=>[c+'-USD',{name:c+' / USD',unit:'USD_PER_'+c,label:' 美元/'+c,change:'%'}]))
};
const INFO={
  indices:['国际指数 · 保存日线','第三方 Tushare Relay','点位不是估值或投资信号'],
  shibor:['人民币同业利率 · Shibor','第三方 Tushare Relay','年化利率；1 bp = 0.01个百分点，不是收益率涨幅'],
  treasury:['美国国债 · 期限利率','美国财政部 Treasury','年化平价收益率（par yield），不是债券价格或持有回报'],
  fx:['外汇 · 每欧元参考价','欧洲央行 ECB','每1欧元对应的外币数量；不是美元基准或可成交买卖价'],
  commodities:['黄金与原油 · 期货日线','Yahoo 供应商期货序列','不是现货或结算价；换月连续性未知，不计算跨日收益'],
  crypto:['加密资产 · 日线','Coinbase Exchange','BTC/ETH 对美元；仅该场所的UTC日桶，不是全市场合成价']
};
const INTERVAL='TWO_RETURNED_DATES_NOT_ASSERTED_CONSECUTIVE_SESSIONS';
const ROLL='NOT_COMPUTED_CONTRACT_ROLL_IDENTITY_UNKNOWN';
const authority=p=>p&&['signal_transition_authority','human_attention_authority','research_authority','investment_authority'].every(k=>p[k]==='NONE')&&p.automatic_admission===false&&p.odds_recomputed===false;
function require(ok){if(!ok)throw new Error('GLOBAL_MARKET_CONTEXT_UNCONFIRMED');}
function clock(v){return typeof v==='string'&&/(Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v));}
function day(v){return typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v;}
function numeric(v){return v===null||typeof v==='string'&&/^-?\d+(?:\.\d+)?$/.test(v)&&v.length<=40&&Number.isFinite(Number(v));}
const number=v=>v===null?'未取得':v.replace(/(\.\d*?[1-9])0+$|\.0+$/,'$1');
const time=v=>new Date(v).toLocaleString('zh-CN',{hour12:false});
const gap=q=>q?.status==='QUERY_UNAVAILABLE'||!!q?.unattributed_run_ids?.length;
const age=(checked,date)=>date===null?null:Math.floor((Date.parse(checked.slice(0,10))-Date.parse(date))/86400000);

function publicRows(r,family,checked){
  const specs=PUBLIC[family],future=family==='commodities';
  require(day(r.as_of_date)&&r.vintage==='CURRENT_RETRIEVAL_OF_DATED_ROWS_NOT_HISTORICAL_AS_KNOWN_VINTAGE'&&
    Array.isArray(r.observations)&&r.observations.map(row=>row.symbol).join(',')===Object.keys(specs).join(','));
  return r.observations.map(row=>{
    const spec=specs[row.symbol];
    require(row.unit===spec.unit&&numeric(row.value)&&numeric(row.previous_value)&&numeric(row.change)&&row.change_unit===spec.change&&
      (row.source_date===null||day(row.source_date)&&row.source_date<=r.as_of_date&&Date.parse(row.source_date)<=Date.parse(checked))&&
      (row.previous_date===null||day(row.previous_date)&&row.source_date!==null&&row.previous_date<row.source_date)&&
      (row.value===null||row.source_date!==null)&&row.change_scope===(future?ROLL:INTERVAL)&&
      row.price_kind===(future?'VENDOR_FUTURE_DAILY_CLOSE_NOT_SPOT_OR_SETTLEMENT':'DATED_SOURCE_OBSERVATION'));
    require(row.change===null||row.value!==null&&row.previous_value!==null&&row.previous_date!==null);
    require(!future||row.change===null);
    require(row.value===null||family==='treasury'||['CL=F','BZ=F'].includes(row.symbol)||Number(row.value)>0);
    return {name:spec.name,missing:row.value===null,value:number(row.value)+(row.value===null?'':spec.label),date:row.source_date,
      prior:row.previous_date,change:future?'不计算（合约换月未确认）':row.change===null?'未取得':number(row.change)+(spec.change==='bp'?' bp':'%'),
      age:age(checked,row.source_date),original:row};
  });
}

function relayRows(r,family,checked){
  require(r.source==='TUSHARE_RELAY_THIRD_PARTY_NOT_OFFICIAL_TUSHARE'&&
    r.outcomes.map(o=>o.id).join(',')===(family==='indices'?Object.keys(INDEX).join(','):'shibor'));
  const rows=[];
  for(const outcome of r.outcomes){
    require(Array.isArray(outcome.observations)&&outcome.observations.length<=(family==='indices'?1:8));
    if(!outcome.observations.length){rows.push({name:INDEX[outcome.id]||'Shibor 本批',missing:true,reason:outcome.status});continue;}
    require(family!=='shibor'||outcome.observations.length===8);
    const seen=new Set();
    for(const row of outcome.observations){
      require(day(row.source_date)&&(row.previous_observed_date===null||day(row.previous_observed_date)&&row.previous_observed_date<row.source_date)&&
        Date.parse(row.source_date)<=Date.parse(checked)&&numeric(row.value)&&numeric(row.previous_value)&&row.change_scope===INTERVAL&&!seen.has(row.symbol));
      seen.add(row.symbol);const index=family==='indices';
      require(index?row.symbol===outcome.id&&row.unit==='INDEX_POINTS'&&Number(row.value)>0&&numeric(row.observed_interval_change_pct):
        TENORS.includes(row.tenor)&&row.symbol==='SHIBOR:'+row.tenor&&row.unit==='ANNUAL_PERCENT'&&row.currency==='CNY'&&numeric(row.observed_interval_change_bp));
      const change=index?row.observed_interval_change_pct:row.observed_interval_change_bp;
      require(change===null||row.value!==null&&row.previous_value!==null&&row.previous_observed_date!==null);
      rows.push({name:index?INDEX[row.symbol]:names[row.tenor],missing:row.value===null,
        value:number(row.value)+(row.value===null?'':index?' 点':'%（年化）'),date:row.source_date,prior:row.previous_observed_date,
        change:change===null?'未取得':number(change)+(index?'%':' bp'),age:age(checked,row.source_date),original:row});
    }
  }
  return rows;
}

export function globalMarketView(text,saved){
  const root=JSON.parse(text),p=root?.projection,order=p?.version===V1?['indices','shibor']:Object.keys(INFO);
  require([V1,V2].includes(p?.version)&&saved?.version===p.version&&HASH.test(root.projection_hash)&&
    root.projection_hash===saved.projection_hash&&p.checked_at===saved.checked_at&&clock(p.checked_at)&&authority(p.authority)&&
    p.source_calls===0&&p.complete_global_coverage===false&&Object.keys(p.families||{}).sort().join(',')===[...order].sort().join(','));
  const families=[];
  for(const family of order){
    const state=p.families[family],snap=state?.snapshot,isPublic=Object.hasOwn(PUBLIC,family);
    require(typeof state?.latest_read_status==='string');
    const group={family,title:INFO[family][0],status:state.latest_read_status,latest:state.latest_attempt,rows:[],snapshot:null,current:false};
    if(snap){
      const r=snap.report,run=snap.run,workflow=isPublic?'.github/workflows/radar-global-public.yml':'.github/workflows/radar-global-market.yml';
      require(r?.version===(isPublic?'global-public-context-v1':'global-market-context-v1')&&r.family===family&&authority(r.authority)&&
        r.source_calls_during_replay===0&&HASH.test(r.capture_hash)&&SHA.test(r.identity?.code_commit)&&
        r.identity?.repository==='auguspp/decision-kernel'&&r.identity.workflow===workflow&&
        r.identity.ref==='refs/heads/main'&&['workflow_dispatch','schedule'].includes(r.identity.event)&&r.identity.attempt===1&&
        r.identity.run_id===run?.id&&Number.isSafeInteger(run.id)&&run.id>0&&run.run_attempt===1&&
        run.path===workflow&&run.head_branch==='main'&&run.event===r.identity.event&&run.status==='completed'&&run.head_sha===r.identity.code_commit&&
        clock(r.captured_from)&&clock(r.captured_through)&&Date.parse(r.captured_from)<=Date.parse(r.captured_through)&&
        Date.parse(r.captured_through)<=Date.parse(p.checked_at)&&Array.isArray(r.outcomes));
      group.snapshot=snap;
      group.current=state.latest_attempt?.id===run.id&&state.latest_attempt?.run_attempt===1&&
        ['CAPTURE_READ','FAILED_RUN_CAPTURE_READ','REUSED_RETAINED_CAPTURE'].includes(state.latest_read_status);
      group.rows=isPublic?publicRows(r,family,p.checked_at):relayRows(r,family,p.checked_at);
      const available=group.rows.filter(row=>!row.missing).length;
      require(available===r.available_values&&available>0);
    }
    families.push(group);
  }
  return {families,checked:p.checked_at,queryGap:gap(p.query)||gap(p.public_query),priorGaps:Array.isArray(p.prior_read_gaps)?p.prior_read_gaps:[]};
}

/** One local panel; old R/A-share/News/Quick regions are not overwritten. */
export function globalMarketsPage(target,ctx){
  const {reading,ui,active,onRead}=ctx,{el,card,button,notice,folded,dataTable,link}=ui;
  const panel=card('全球市场 · 已保存背景','指数、利率、外汇、黄金原油与加密资产按各自来源读取；不是实时行情。');
  target.append(panel);panel.append(notice('Shibor不能代表全球债市；各来源保留自己的时点、单位与覆盖限制。'));
  const saved=reading.payload.research?.global_market,ref=saved?.details?.json;
  if(!ref){panel.append(notice('本包还没有可读全球市场资料；不是市场没有变化。'));return Promise.resolve();}
  const content=el('div');content.append(el('p','正在读取已保存市场资料…'));panel.append(content);
  return Promise.resolve().then(()=>{require(ref.read_path===GLOBAL_REPORT);return reading.readFile(ref);}).then(file=>{
    if(!active())return;
    const view=globalMarketView(file.text,saved);
    content.replaceChildren(el('p',`本包检查：${time(view.checked)}；各市场保留自己的数据日期。`,'small'));
    if(view.families.length===2)content.append(notice('这是旧版两族读取包；该版本未包含四个新增公开来源。'));
    if(view.queryGap)content.append(notice('最新运行查询有缺口；下面的历史结果不能证明当前更新成功。'));
    if(view.priorGaps.length)content.append(notice('部分旧资料未能完整恢复；原固定版本仍保留，未填成零。'));
    for(const group of view.families){
      const section=el('section');section.append(el('h4',group.title));content.append(section);
      if(!group.snapshot){section.append(notice('没有已核验的可读批次；不作无变化判断。'),folded('读取状态',group.status));continue;}
      const capture=group.snapshot.report;
      if(!group.current)section.append(notice('以下为上次可读结果，不是本次更新成功。'));
      if(group.latest?.status!=='completed'||group.latest?.conclusion!=='success')section.append(notice('最近一次采集尚未成功完成；保留历史日期和已有结果。'));
      section.append(el('p',`采集截止：${time(capture.captured_through)} · 来源：${INFO[group.family][1]} · ${capture.status==='AVAILABLE'?'本批所选系列均有值':'本批仅部分数据可读'}`,'small'));
      const heads=['对象','保存值','来源日期','两次返回间变化'],{wrapper,body}=dataTable(INFO[group.family][2],heads);
      for(const row of group.rows){
        const tr=el('tr'),values=[row.name,row.value||'本次未取得',row.date?`${row.date}（距检查日${row.age}天）`:'未知',
          group.family==='commodities'?row.change:row.prior?`${row.change}（${row.prior} → ${row.date}）`:'比较区间未知'];
        values.forEach((v,i)=>{const td=el('td',v);td.setAttribute('data-label',heads[i]);tr.append(td);});body.append(tr);
      }
      section.append(wrapper,el('p','变化仅比较两个实际返回日期，不保证相邻交易日。发布时间与市场开闭状态仍未知。','small'));
      const a=group.snapshot.archive;
      require(HASH.test(a?.sha256)&&a.read_path===`sources/artifacts/${a.sha256}.zip`&&SHA.test(reading.ref));
      section.append(link('查看本批原始存档',`https://github.com/auguspp/decision-kernel/blob/${reading.ref}/${a.read_path}`),
        folded('运行与来源状态',JSON.stringify({latest:group.latest,reading:group.status,outcomes:capture.outcomes.map(o=>({id:o.id,status:o.status}))},null,2)));
    }
    content.append(button('阅读全球市场保存原件',()=>{if(active())onRead(ref);}));
  }).catch(error=>{if(active())content.replaceChildren(notice('全球市场资料未能读完；A股与其他模块不受影响，不解释为没有变化。'),folded('读取诊断',error.message));});
}
