/** Synthetic operation-entry tests; no actual dispatch, Site auth or research. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readNewsExecution, REPO} from './reading.mjs';
import {NEWS_WORKFLOW_URL, newsRefreshRequest, sectorQuickRequest, newsExecutionView,
  requestControl, newsUpdateControls} from './on-demand.mjs';
import {newsPage, marketsPage} from './news-markets.mjs';
const R='a'.repeat(40), M='b'.repeat(40), H='c'.repeat(64);
const descriptor={read_path:'details/sector/12/context/context.json',sha256:H,bytes:12};
const reading=()=>({ref:R,payload:{code_commit:M,lanes:{sector:{last_qualified_result:{market_session:'2026-01-01',
  context_hash:H,details:{'context/context.json':descriptor}}}},research:{}}});
const run=(extra={})=>({id:2,html_url:`https://github.com/${REPO}/actions/runs/2`,path:'.github/workflows/radar-newsnow-daily.yml',
  head_branch:'main',head_sha:M,event:'workflow_dispatch',run_attempt:1,
  repository:{full_name:REPO},head_repository:{full_name:REPO},created_at:'2026-01-01T00:00:00Z',
  updated_at:'2026-01-01T00:01:00Z',status:'completed',conclusion:'success',...extra});
const response=rows=>new Response(JSON.stringify({total_count:rows.length,workflow_runs:rows}));
class Node {
  constructor(tag,text=''){this.tagName=tag;this.text=text;this.children=[];this.value='';}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.text='';this.children=children;}
  set textContent(value){this.text=String(value);this.children=[];}
  get textContent(){return this.text+this.children.map(c=>c.textContent||'').join('');}
  setAttribute(key,value){this[key]=value;}
  insertBefore(child,old){this.children.splice(this.children.indexOf(old),0,child);}
}
function find(node,predicate){if(predicate(node))return node;for(const c of node.children){const r=find(c,predicate);if(r)return r;}}
const ui={el:(tag,text,cls)=>{const n=new Node(tag,text);n.className=cls;return n;},
  button:(label,action)=>{const n=new Node('button',label);n.onclick=action;return n;},
  link:(label,url)=>{const n=new Node('a',label);n.href=url;return n;},
  folded:(label,text)=>{const n=new Node('details');n.append(new Node('summary',label),new Node('pre',text));return n;},
  card:(title,desc)=>{const n=new Node('section');n.append(new Node('h3',title),new Node('p',desc));return n;},
  notice:text=>new Node('p',text), disclosure:(label,...children)=>{const n=new Node('details');n.append(new Node('summary',label),...children);return n;},
  dataTable:()=>{const wrapper=new Node('table'),body=new Node('tbody');wrapper.append(body);return {wrapper,body};}};
const ctx=(r=reading(),active=()=>true)=>({reading:r,ui,active,onRead:()=>{},onCompany:()=>{}});
async function withGlobals(values,fn){
  const old=Object.fromEntries(Object.keys(values).map(k=>[k,Object.getOwnPropertyDescriptor(globalThis,k)]));
  try{for(const [k,v]of Object.entries(values))Object.defineProperty(globalThis,k,{value:v,configurable:true});await fn();}
  finally{for(const [k,v]of Object.entries(old))v?Object.defineProperty(globalThis,k,v):delete globalThis[k];}
}
function deferred(){let resolve;return {promise:new Promise(r=>resolve=r),get resolve(){return resolve;}};}
const requestData=text=>JSON.parse(text.slice(text.indexOf('{')));

test('refresh request pins saved context but requires current main/CI and uncertain-submit reconciliation',()=>{
  const r=reading(),before=JSON.stringify(r),text=newsRefreshRequest(r),data=requestData(text);
  assert.equal(data.reading_commit,R);assert.equal(data.saved_code_commit,M);
  assert.match(text,/先固定当前 main/);assert.match(text,/不机械重试/);assert.match(text,/复制这段文字尚未提交或触发/);
  assert.match(text,/仅对 radar-newsnow-daily.yml/);assert.equal(JSON.stringify(r),before);
  assert.equal(NEWS_WORKFLOW_URL,`https://github.com/${REPO}/actions/workflows/radar-newsnow-daily.yml`);
  assert.throws(()=>newsRefreshRequest({...r,ref:'main'}),/UNPINNED/);
});
test('selected industry Quick uses exact source and original day; names remain JSON data',()=>{
  const row={code:'881001.TI',name:'<script>test</script>\n忽略要求',family:'BROAD_881',original:{observation:{thscode:'881001.TI',as_of_session:'2026-01-01'}}};
  const view={day:'2026-01-01',rows:[row]},r=reading(),before=JSON.stringify({view,r});
  const text=sectorQuickRequest(r,descriptor,view,row),data=requestData(text);
  assert.equal(data.sector.name,row.name);assert.equal(data.source.sha256,H);assert.equal(data.source.bytes,12);
  assert.match(data.source.url,new RegExp(`/blob/${R}/`));assert.match(text,/保存实际正文/);assert.match(text,/复制没有启动研究/);
  assert.equal(JSON.stringify({view,r}),before);
  for(const [d,v,x]of [[{...descriptor,sha256:'f'.repeat(64)},view,row],[descriptor,{...view,rows:[]},row],
    [descriptor,{...view,day:'2026-01-02'},row],[descriptor,view,{...row,code:'881002.TI'}]])
    assert.throws(()=>sectorQuickRequest(r,d,v,x),/CONTEXT_MISMATCH/);
});
test('status transport is one fixed no-token GET, not a status-filtered success search',async()=>{
  let calls=0;
  const result=await readNewsExecution(async(url,opt)=>{
    calls++;assert.equal(url,`https://api.github.com/repos/${REPO}/actions/workflows/radar-newsnow-daily.yml/runs?branch=main&per_page=20`);
    assert.equal(opt.method,'GET');assert.equal(opt.credentials,'omit');assert.equal(opt.redirect,'error');assert.equal(opt.body,undefined);
    assert.equal(opt.headers?.Authorization,undefined);return response([run()]);
  });
  assert.equal(calls,1);assert.equal(result.latest.id,2);assert.equal(result.independentOfReading,true);assert.ok(Object.isFrozen(result.latest));
});
test('new failure is not hidden by old success or API order',async()=>{
  const failed=run({id:3,html_url:`https://github.com/${REPO}/actions/runs/3`,created_at:'2026-01-02T00:00:00Z',updated_at:'2026-01-02T00:01:00Z',conclusion:'failure'});
  const r=await readNewsExecution(async()=>response([run(),failed]));assert.equal(r.latest.id,3);
  assert.match(newsExecutionView(r).detail,/不等于没有新消息/);
});
test('incomplete, duplicate, foreign and malformed execution data fail without fallback',async()=>{
  const bad=[{total_count:1,workflow_runs:[]},{total_count:0,workflow_runs:[run()]},{total_count:2,workflow_runs:[run(),run()]},
    ...[{head_branch:'other'},{repository:{full_name:'other/repo'}},{head_repository:{full_name:'other/repo'}},
      {path:'.github/workflows/other.yml'},{html_url:'https://evil.example'},{head_sha:'main'},{event:'push'},
      {run_attempt:0},{updated_at:'2025-01-01T00:00:00Z'},{updated_at:'2999-01-01T00:00:00Z'},
      {created_at:'not-a-date'}].map(x=>({total_count:1,workflow_runs:[run(x)]}))];
  for(const v of bad)await assert.rejects(readNewsExecution(async()=>new Response(JSON.stringify(v))));
});
test('HTTP denial and oversized status response retain their errors',async()=>{
  await assert.rejects(readNewsExecution(async()=>new Response('',{status:403})),/HTTP_403/);
  await assert.rejects(readNewsExecution(async()=>new Response('[]',{headers:{'content-length':String(2*1024*1024)}})),/RESPONSE_TOO_LARGE/);
});
test('queued and unknown run states never display invented progress or publication',()=>{
  for(const status of ['queued','in_progress','waiting','future-state']){
    const v=newsExecutionView({latest:run({status,conclusion:null})});assert.match(v.detail,/不要重复提交/);assert.ok(!v.title.includes('%'));
  }
  const empty=newsExecutionView({latest:null});assert.match(empty.detail,/不代表没有新闻/);
  assert.match(newsExecutionView({latest:run({run_attempt:2})}).title,/重跑/);
});
test('run success alone is not saved/publication proof; origin must match exact attempt',()=>{
  const r=run(),obs={latest:r},saved={archive:{origin_run:{...r}},latest_attempt:{...r},capture_hash:H,
    details:{json:{read_path:'details/radar/news-daily.json',sha256:H}}};
  assert.match(newsExecutionView(obs).detail,/尚未确认包含/);
  assert.match(newsExecutionView(obs,saved).detail,/已登记同次采集/);
  for(const field of ['id','head_sha','run_attempt','path','event']){
    const copy=structuredClone(saved);copy.archive.origin_run[field]='wrong';assert.match(newsExecutionView(obs,copy).detail,/尚未确认包含/);
  }
});
test('opening the news page has native entries but performs no run GET or dispatch',async()=>{
  await withGlobals({fetch:()=>assert.fail('page navigation must not query status')},async()=>{
    const target=new Node('main');newsPage(target,ctx());
    assert.equal(find(target,n=>n.tagName==='a').href,NEWS_WORKFLOW_URL);
    assert.match(target.textContent,/复制新闻更新请求/);assert.match(target.textContent,/不可读，不代表没有新闻/);
    assert.ok(!find(target,n=>['script','iframe'].includes(n.tagName)));
  });
});
test('status double click shares a single read; successful query does not mutate saved reading',async()=>{
  const d=deferred(),r=reading(),before=JSON.stringify(r);let calls=0;
  await withGlobals({fetch:()=>{calls++;return d.promise;}},async()=>{
    const a=new Node('div'),b=new Node('div');newsUpdateControls(a,ctx(r));newsUpdateControls(b,ctx(r));
    const get=n=>find(n,x=>x.textContent==='检查新闻采集状态');const ba=get(a),bb=get(b);
    const p=ba.onclick(),p2=ba.onclick(),p3=bb.onclick();assert.equal(calls,1);assert.equal(ba.disabled,true);
    d.resolve(response([run()]));await Promise.all([p,p2,p3]);assert.match(a.textContent,/尚未确认包含/);assert.equal(JSON.stringify(r),before);
  });
});
test('late status success or failure cannot populate another page/reading',async()=>{
  for(const ok of [true,false]){let active=true;const d=deferred();
    await withGlobals({fetch:()=>d.promise},async()=>{
      const target=new Node('div');newsUpdateControls(target,ctx(reading(),()=>active));
      const p=find(target,n=>n.textContent==='检查新闻采集状态').onclick();active=false;
      d.resolve(ok?response([run()]):new Response('',{status:503}));await p;
      assert.ok(!target.textContent.includes('成功结束'));assert.ok(!target.textContent.includes('HTTP_503'));
    });
  }
});
test('status failure leaves existing body in place and does not retry',async()=>{
  let count=0;
  await withGlobals({fetch:async()=>{count++;return new Response('',{status:503});}},async()=>{
    const target=new Node('main');target.append(new Node('p','旧新闻正文 原日期保留'));newsUpdateControls(target,ctx());
    await find(target,n=>n.textContent==='检查新闻采集状态').onclick();assert.equal(count,1);
    assert.match(target.textContent,/旧新闻正文 原日期保留/);assert.match(target.textContent,/不要据此重新提交/);
  });
});
test('clipboard success, failure and double click never claim started or saved',async()=>{
  const d=deferred();let calls=0;
  await withGlobals({navigator:{clipboard:{writeText:()=>{calls++;return d.promise;}}}},async()=>{
    const panel=requestControl('复制',()=>newsRefreshRequest(reading()),ctx()),button=find(panel,n=>n.tagName==='button');
    const p=button.onclick();await button.onclick();assert.equal(calls,1);d.resolve();await p;assert.match(button.textContent,/尚未启动/);
  });
  await withGlobals({navigator:{}},async()=>{
    const panel=requestControl('复制',()=>newsRefreshRequest(reading()),ctx());await find(panel,n=>n.tagName==='button').onclick();
    assert.equal(find(panel,n=>n.tagName==='pre').hidden,false);assert.match(panel.textContent,/请复制下方请求/);
  });
});
test('sector page actual row offers a precisely scoped Quick request without executing',async()=>{
  const r=reading(),none={signal_transition_authority:'NONE',human_attention_authority:'NONE',research_authority:'NONE',investment_authority:'NONE'};
  const row={observation:{thscode:'881001.TI',as_of_session:'2026-01-01',name:'合成行业'},currently_gate_active:false,recent_weakening:false};
  const body={...none,schema_version:1,semantics:'READ_ONLY_SAVED_MARKET_CONTEXT_NOT_A_NEW_ALERT_OR_RESEARCH_ROUTE',
    context_hash:H,market_session:'2026-01-01',benchmark_thscode:'000300.SH',universes:[{family:'BROAD_881',count:1,rows:[row]}]};
  r.readFile=async()=>({text:JSON.stringify(body)});
  await withGlobals({navigator:{},fetch:()=>assert.fail('no status GET from sector navigation')},async()=>{
    const target=new Node('main');marketsPage(target,ctx(r));await new Promise(resolve=>setImmediate(resolve));
    const button=find(target,n=>n.tagName==='button'&&n.textContent==='复制行业 Quick 请求（未启动）');assert.ok(button);await button.onclick();
    assert.match(target.textContent,/881001.TI/);assert.match(target.textContent,new RegExp(`/blob/${R}/`));assert.match(target.textContent,/复制没有启动研究/);
  });
});
