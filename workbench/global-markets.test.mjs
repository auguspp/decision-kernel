import test from 'node:test';
import assert from 'node:assert/strict';
import {globalMarketView,globalMarketsPage,GLOBAL_REPORT} from './global-markets.mjs';
const M='a'.repeat(40), R='b'.repeat(40), H='c'.repeat(64), NOW='2026-09-27T08:30:00Z';
const auth={signal_transition_authority:'NONE',human_attention_authority:'NONE',research_authority:'NONE',investment_authority:'NONE',automatic_admission:false,odds_recomputed:false};
const ix=['SPX','IXIC','HSI','HKTECH','N225','GDAXI'],tenors=['on','1w','2w','1m','3m','6m','9m','1y'];
function fixture(){
  const families={};
  for(const [family,id] of [['indices',901],['shibor',902]]){
    const run={id,path:'.github/workflows/radar-global-market.yml',event:'workflow_dispatch',head_branch:'main',head_sha:M,run_attempt:1,status:'completed',conclusion:'success'};
    const row=symbol=>({symbol,source_date:'2026-09-25',previous_observed_date:'2026-09-21',value:'101',previous_value:'100',
      unit:'INDEX_POINTS',observed_interval_change_pct:'1.000000',change_scope:'TWO_RETURNED_DATES_NOT_ASSERTED_CONSECUTIVE_SESSIONS'});
    const outcomes=family==='indices'?ix.map(symbol=>({id:symbol,status:'ROWS_NORMALIZED',observations:[row(symbol)]})):
      [{id:'shibor',status:'ROWS_NORMALIZED',observations:tenors.map(tenor=>({...row('SHIBOR:'+tenor),tenor,unit:'ANNUAL_PERCENT',currency:'CNY',value:'1.25',previous_value:'1.20',observed_interval_change_bp:'5.00'}))}];
    const report={version:'global-market-context-v1',family,authority:auth,source:'TUSHARE_RELAY_THIRD_PARTY_NOT_OFFICIAL_TUSHARE',
      source_calls_during_replay:0,capture_hash:H,identity:{repository:'auguspp/decision-kernel',workflow:run.path,ref:'refs/heads/main',event:'workflow_dispatch',attempt:1,run_id:id,code_commit:M},
      captured_from:'2026-09-27T08:00:00Z',captured_through:'2026-09-27T08:01:00Z',outcomes,available_values:family==='indices'?6:8,status:'AVAILABLE'};
    families[family]={latest_attempt:run,latest_read_status:'CAPTURE_READ',snapshot:{run,report,archive:{sha256:H,read_path:`sources/artifacts/${H}.zip`}}};
  }
  const p={version:'global-market-reading-v1',checked_at:NOW,authority:auth,source_calls:0,complete_global_coverage:false,families,query:{unattributed_run_ids:[]},prior_read_gaps:[]};
  return {root:{projection:p,projection_hash:H},saved:{version:p.version,checked_at:NOW,projection_hash:H,details:{json:{read_path:GLOBAL_REPORT}}}};
}
const view=f=>globalMarketView(JSON.stringify(f.root),f.saved);
test('two source families keep dates and distinct percent/bp units',()=>{
 const f=fixture(),v=view(f);assert.equal(v.families[0].rows.length,6);assert.equal(v.families[1].rows.length,8);
 assert.equal(v.families[0].rows[0].change,'1%');assert.equal(v.families[1].rows[0].change,'5 bp');
 assert.equal(v.families[1].rows[0].value,'1.25%（年化）');assert.equal(v.families[0].rows[0].age,2);
 assert.equal(v.families[0].rows[0].prior,'2026-09-21');
});
test('partial symbols do not become zeros or quiet markets',()=>{
 const f=fixture(),r=f.root.projection.families.indices.snapshot.report;r.outcomes[0].observations=[];r.outcomes[0].status='TEMPORARY_QUEUE';r.available_values=5;
 const v=view(f);assert.equal(v.families[0].rows[0].missing,true);assert.equal(v.families[0].rows[0].value,undefined);
});
test('later failure and query gap do not repaint old capture as current success',()=>{
 const f=fixture(),s=f.root.projection.families.indices;s.latest_attempt={...s.latest_attempt,id:903,conclusion:'failure'};s.latest_read_status='CAPTURE_UNAVAILABLE_OR_REJECTED';
 f.root.projection.query.status='QUERY_UNAVAILABLE';const v=view(f);assert.equal(v.families[0].current,false);assert.equal(v.queryGap,true);
});
for(const kind of ['authority','hash','family','unit','future','symbol','nonfinite','foreign-run'])test(`reject malformed ${kind} before presenting values`,()=>{
 const f=fixture(),p=f.root.projection,r=p.families.indices.snapshot.report,row=r.outcomes[0].observations[0];
 if(kind==='authority')p.authority={...auth,investment_authority:'APPROVED'};
 if(kind==='hash')f.saved.projection_hash='d'.repeat(64);
 if(kind==='family')r.family='shibor';if(kind==='unit')row.unit='ANNUAL_PERCENT';
 if(kind==='future')row.source_date='2026-10-01';if(kind==='symbol')row.symbol='OTHER';
 if(kind==='nonfinite')row.value='Infinity';if(kind==='foreign-run')p.families.indices.snapshot.run.head_branch='foreign';
 assert.throws(()=>view(f),/UNCONFIRMED/);
});
class E{
 constructor(tag,text){this.tagName=tag;this.text=text??'';this.children=[];this.attributes={};}
 append(...children){this.children.push(...children);}replaceChildren(...children){this.children=children;this.text='';}
 setAttribute(k,v){this.attributes[k]=v;}get textContent(){return this.text+this.children.map(x=>typeof x==='string'?x:x.textContent).join('');}
}
const el=(t,x)=>new E(t,x), ui={el,card:(t,d)=>{const e=el('article');e.append(el('h3',t),el('p',d));return e;},
 button:(t,fn)=>Object.assign(el('button',t),{onclick:fn}),notice:t=>el('p',t),folded:(t,v)=>{const e=el('details',t);e.append(el('pre',v));return e;},
 link:(t,url)=>Object.assign(el('a',t),{href:url}),dataTable:(caption,heads)=>{const wrapper=el('table',caption),body=el('tbody');wrapper.append(body);return {wrapper,body};}};
function context(f,read){return {ui,reading:{ref:R,payload:{research:{global_market:f.saved}},readFile:read},active:()=>true,onRead:()=>{}};}
test('component reads only saved report; keeps other page regions and gives mobile table labels',async()=>{
 const f=fixture(),target=el('main');target.append(el('p','A股保留'));let reads=0;
 await globalMarketsPage(target,context(f,async ref=>{reads++;assert.equal(ref.read_path,GLOBAL_REPORT);return {text:JSON.stringify(f.root)};}));
 assert.equal(reads,1);assert.match(target.textContent,/A股保留/);assert.match(target.textContent,/不是实时行情/);assert.match(target.textContent,/Shibor不能代表全球债市/);
 const nodes=[];const walk=x=>{nodes.push(x);x.children?.forEach(walk);};walk(target);
 assert.ok(nodes.filter(x=>x.tagName==='td').every(x=>x.attributes['data-label']));
 assert.ok(!nodes.some(x=>x.tagName==='button'&&/刷新|交易/.test(x.textContent)));
});
test('bad descriptor and read failure remain local, not a failure of other Markets panels',async()=>{
 const f=fixture();f.saved.details.json.read_path='foreign/path';const target=el('main');target.append(el('p','A股仍可读'));
 await globalMarketsPage(target,context(f,async()=>assert.fail('invalid path must not fetch')));
 assert.match(target.textContent,/A股仍可读/);assert.match(target.textContent,/资料未能读完/);
});
test('navigation away prevents a late source read overwriting the new view',async()=>{
 const f=fixture(),target=el('main');let resolve,active=true;
 const ctx=context(f,()=>new Promise(r=>resolve=r));ctx.active=()=>active;
 const pending=globalMarketsPage(target,ctx);await Promise.resolve();active=false;target.replaceChildren(el('p','新页面'));resolve({text:JSON.stringify(f.root)});await pending;
 assert.equal(target.textContent,'新页面');
});

// V2 uses the unchanged #614 report shape, not a synthetic unified quote API.
function six(){
 const f=fixture(),p=f.root.projection;p.version=f.saved.version='global-market-reading-v2';p.public_query={unattributed_run_ids:[]};
 const specs={treasury:['1MONTH','3MONTH','6MONTH','1YEAR','2YEAR','5YEAR','10YEAR','30YEAR'].map(t=>['UST:'+t,'ANNUAL_PERCENT']),
  fx:['USD','CNY','JPY','GBP'].map(c=>['EUR/'+c,c+'_PER_EUR']),
  commodities:[['GC=F','USD_PER_TROY_OUNCE'],['CL=F','USD_PER_BARREL'],['BZ=F','USD_PER_BARREL']],
  crypto:[['BTC-USD','USD_PER_BTC'],['ETH-USD','USD_PER_ETH']]};
 let id=1000;
 for(const [family,rows] of Object.entries(specs)){
  const run={...p.families.indices.snapshot.run,id:++id,path:'.github/workflows/radar-global-public.yml'};
  const r={...structuredClone(p.families.indices.snapshot.report),version:'global-public-context-v1',family,as_of_date:'2026-09-26',
   identity:{...p.families.indices.snapshot.report.identity,run_id:run.id,workflow:run.path},
   vintage:'CURRENT_RETRIEVAL_OF_DATED_ROWS_NOT_HISTORICAL_AS_KNOWN_VINTAGE',outcomes:[{id:family,status:'ROWS_NORMALIZED'}],
   observations:rows.map(([symbol,unit])=>({symbol,unit,value:'101',previous_value:'100',source_date:'2026-09-25',previous_date:'2026-09-23',
    change:family==='commodities'?null:'1.00',change_unit:family==='commodities'?null:family==='treasury'?'bp':'%',
    price_kind:family==='commodities'?'VENDOR_FUTURE_DAILY_CLOSE_NOT_SPOT_OR_SETTLEMENT':'DATED_SOURCE_OBSERVATION',
    change_scope:family==='commodities'?'NOT_COMPUTED_CONTRACT_ROLL_IDENTITY_UNKNOWN':'TWO_RETURNED_DATES_NOT_ASSERTED_CONSECUTIVE_SESSIONS'})),available_values:rows.length};
  delete r.source;p.families[family]={latest_attempt:run,latest_read_status:'CAPTURE_READ',snapshot:{run,report:r,archive:{sha256:H,read_path:`sources/artifacts/${H}.zip`}}};
 }
 return f;
}
test('six-family report preserves source units, euro direction and futures no-return',()=>{
 const f=six(),v=view(f);assert.deepEqual(v.families.map(g=>g.rows.length),[6,8,8,4,3,2]);
 assert.match(v.families[2].rows[0].value,/%（年化）/);assert.equal(v.families[2].rows[0].change,'1 bp');
 assert.match(v.families[3].rows[1].value,/CNY\/EUR/);assert.match(v.families[4].rows[0].value,/金衡盎司/);
 assert.match(v.families[4].rows[0].change,/不计算/);assert.match(v.families[5].rows[0].value,/美元\/BTC/);
});
for(const damage of ['workflow','symbol','unit','return','vintage','date','count','omit-family'])test(`new public family rejects ${damage}`,()=>{
 const f=six(),p=f.root.projection,r=p.families.commodities.snapshot.report;
 if(damage==='workflow')r.identity.workflow='.github/workflows/radar-global-market.yml';
 if(damage==='symbol')r.observations[0].symbol='SPX';if(damage==='unit')r.observations[0].unit='INDEX_POINTS';
 if(damage==='return')r.observations[0].change='1';if(damage==='vintage')r.vintage='PIT_VERIFIED';
 if(damage==='date')r.observations[0].source_date='2026-09-27';if(damage==='count')r.available_values=2;
 if(damage==='omit-family')delete p.families.fx;assert.throws(()=>view(f),/UNCONFIRMED/);
});
test('new source null and failed query preserve original date and other families',()=>{
 const f=six(),p=f.root.projection,r=p.families.treasury.snapshot.report;r.observations[0].value=null;r.observations[0].change=null;r.available_values--;
 p.public_query.status='QUERY_UNAVAILABLE';p.families.crypto.latest_attempt={id:1111,run_attempt:1,conclusion:'failure'};
 const v=view(f);assert.equal(v.queryGap,true);assert.equal(v.families[2].rows[0].missing,true);
 assert.equal(v.families[2].rows[0].date,'2026-09-25');assert.equal(v.families[5].current,false);assert.equal(v.families[0].current,true);
});
test('six-family UI remains one saved read with explicit source conventions',async()=>{
 const f=six(),target=el('main');let n=0;await globalMarketsPage(target,context(f,async()=>{n++;return{text:JSON.stringify(f.root)};}));
 assert.equal(n,1);for(const word of ['美国财政部','欧洲央行','Yahoo','Coinbase','每1欧元','不是现货','不计算跨日收益'])assert.ok(target.textContent.includes(word),word);
 assert.ok(!target.textContent.includes('美债/国际利率、黄金原油、外汇、加密资产尚未接入'));
});
