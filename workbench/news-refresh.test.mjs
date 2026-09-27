/** Controlled transport/DOM only; no live dispatch, credentials or Site acceptance. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {setTimeout as tick} from 'node:timers/promises';
import {handleNewsRefresh, SITE_ORIGIN, NEWS_REFRESH_PATH, WORKFLOW_SHA256} from './server/news-refresh-handler.mjs';
import {newsRefreshControl, refreshPresentation} from './news-refresh.mjs';
import {REPO, READ_REF} from './reading.mjs';
const M = '1'.repeat(40), R = '2'.repeat(40), T = Date.parse('2026-09-27T01:30:00Z');
const API = `https://api.github.com/repos/${REPO}`, WF = '.github/workflows/radar-newsnow-daily.yml';
const sha = text => createHash('sha256').update(text).digest('hex');
const json = (data,status=200) => new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});
const env = () => ({DECISION_KERNEL_ENABLE_NEWS_REFRESH:'1',DECISION_KERNEL_OWNER_USER_ID:'synthetic-owner',DECISION_KERNEL_GITHUB_TOKEN:'synthetic-test-token'});
const run = (extra={}) => ({id:100,run_number:7,run_attempt:1,path:WF,head_sha:M,head_branch:'main',event:'workflow_dispatch',
  repository:{full_name:REPO},head_repository:{full_name:REPO},actor:{id:83357964},display_title:'radar-newsnow-daily',
  html_url:`https://github.com/${REPO}/actions/runs/100`,created_at:new Date(T-10000).toISOString(),updated_at:new Date(T-5000).toISOString(),status:'completed',conclusion:'success',...extra});
const list = rows => ({total_count:rows.length,workflow_runs:rows});
const request = (body,headers={},url=SITE_ORIGIN+NEWS_REFRESH_PATH,method='POST') => new Request(url,{method,
  headers:{Origin:SITE_ORIGIN,'Content-Type':'application/json','X-Decision-Kernel-Intent':'news-refresh','oai-authenticated-user-id':'synthetic-owner',...headers},
  ...(method==='POST'?{body:JSON.stringify(body)}:{})});
async function fixture() {
  const workflow = await readFile(new URL('../.github/workflows/radar-newsnow-daily.yml',import.meta.url),'utf8');
  const state = {clock:T,main:M,workflow,news:[run()],ci:[run({id:200,run_number:1628,path:'.github/workflows/ci.yml',event:'push',html_url:`https://github.com/${REPO}/actions/runs/200`})],
    calls:[],posts:0,nativeNumber:7,created:[],active:null,dispatch:'200',publish:null,writeVisible:true,metadata:{id:364013307,path:WF,state:'active'}};
  const fetcher = async (url,options={}) => {
    state.calls.push({url:String(url),method:options.method,body:options.body,headers:options.headers});
    const u = new URL(url);
    assert.equal(options.redirect,'error'); assert.equal(options.credentials,'omit');
    if (u.hostname==='raw.githubusercontent.com') {
      assert.equal(options.headers?.Authorization,undefined);
      if (u.pathname.endsWith('/'+WF)) return new Response(state.workflow);
      if (u.pathname.endsWith('/current-state.json') && state.publish) return json(state.publish.root);
      if (u.pathname.endsWith('/details/radar/news-daily.json') && state.publish) return new Response(state.publish.body);
      assert.fail('unexpected raw URL '+url);
    }
    assert.ok(String(url).startsWith(API+'/'));
    if (u.pathname.endsWith('/git/ref/heads/main')) {
      assert.equal(options.headers.Authorization,undefined);
      return json({ref:'refs/heads/main',object:{type:'commit',sha:state.main}});
    }
    if (u.pathname.endsWith('/git/ref/heads/'+READ_REF)) {
      assert.equal(options.headers?.Authorization,undefined);
      if (!state.publish) return json({error:'no reading'},503);
      return json({ref:'refs/heads/'+READ_REF,object:{type:'commit',sha:R}});
    }
    assert.equal(options.headers.Authorization,'Bearer synthetic-test-token');
    if (u.pathname.endsWith('/actions/workflows/radar-newsnow-daily.yml')) return json(state.metadata);
    if (u.pathname.endsWith('/actions/workflows/ci.yml/runs')) return json(list(state.ci));
    if (u.pathname.endsWith('/actions/workflows/radar-newsnow-daily.yml/runs')) {
      if (u.searchParams.has('status')) return json(list(state.active?.status===u.searchParams.get('status')?[state.active]:[]));
      return json(list(state.news));
    }
    if (u.pathname.endsWith('/dispatches')) {
      assert.equal(options.method,'POST');state.posts++;
      const b=JSON.parse(options.body);assert.equal(b.ref,'main');assert.deepEqual(Object.keys(b.inputs).sort(),['site_expected_code_commit','site_expected_run_number','site_request_id']);
      const id=100+state.posts,n=Math.max(state.nativeNumber,...state.news.map(r=>r.run_number))+1;state.nativeNumber=n;
      const created=run({id,run_number:n,display_title:'site-news-refresh/'+b.inputs.site_request_id,status:'queued',conclusion:null,
        head_sha:state.main,html_url:`https://github.com/${REPO}/actions/runs/${id}`});
      state.created.push({run:created,inputs:b.inputs});
      if (state.writeVisible && !['403','500'].includes(state.dispatch))state.news.unshift(created);
      if(state.dispatch==='throw')throw new Error('DO NOT LEAK synthetic-test-token');
      if(state.dispatch==='204')return new Response(null,{status:204});
      if(state.dispatch==='403')return json({secret:'synthetic-test-token'},403);
      if(state.dispatch==='500')return json({secret:'synthetic-test-token'},500);
      if(state.dispatch==='html')return new Response('<html>not a receipt</html>',{headers:{'Content-Type':'text/html'}});
      return json({workflow_run_id:id,run_url:`${API}/actions/runs/${id}`,html_url:`https://github.com/${REPO}/actions/runs/${id}`});
    }
    const m=u.pathname.match(/\/actions\/runs\/(\d+)$/);
    if(m)return json(state.news.find(r=>r.id===Number(m[1]))||{},state.news.some(r=>r.id===Number(m[1]))?200:404);
    assert.fail('unexpected URL '+url);
  };
  const call = async (input,extra={},e=env()) => {
    const res=await handleNewsRefresh(request(input,extra),e,{fetcher,now:()=>state.clock});
    const data=await res.json();assert.ok(!JSON.stringify(data).includes('synthetic-test-token'));assert.ok(!JSON.stringify(data).includes('synthetic-owner'));
    return {status:res.status,...data};
  };
  return {state,fetcher,call,prepare:async()=>(await call({op:'prepare'})).ticket};
}
function publication(state,{wrongRun=false,corrupt=false,partial=false}={}) {
  const r=state.news[0];r.status='completed';r.conclusion='success';
  const capture={capture_hash:'a'.repeat(64),captured_through:new Date(T-1000).toISOString(),source_outcomes:[{source_id:'cls',status:partial?'SOURCE_FAILED':'OBSERVATIONS_NORMALIZED'}],news:{projection:{observations:[]}}};
  const body=JSON.stringify({projection:{capture:{projection:capture}}});
  const descriptor={read_path:'details/radar/news-daily.json',bytes:Buffer.byteLength(body),sha256:sha(body)};
  const s={...capture,details:{json:descriptor},archive:{origin_run:{...r,id:wrongRun?99:r.id}},latest_attempt:r};
  const auth={signal_transition_authority:'NONE',human_attention_authority:'NONE',research_authority:'NONE',investment_authority:'NONE'};
  state.publish={root:{schema_version:1,entry_ref:READ_REF,code_commit:M,reading_hash:'b'.repeat(64),...auth,lanes:{},
    semantics:'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',research:{daily_news:s}},body:corrupt?body.replace('cls','bad'):body};
}

test('workflow fingerprint binds exact optional admission and leaves the source commands in place',async()=>{
  const {state}=await fixture();assert.equal(sha(state.workflow),WORKFLOW_SHA256);assert.match(state.workflow,/SITE_SLOT_CHANGED_NO_CAPTURE/);
  assert.match(state.workflow,/workflows: \[sector-radar-shadow\]/);assert.match(state.workflow,/github.run_attempt == 1/);
  assert.match(state.workflow,/python -m decision_kernel.runtime.news_daily/);assert.ok(!state.workflow.includes('contents: write'));
});
test('routing/config/identity/CSRF reject before network and do not return static HTML',async()=>{
  const f=await fixture();
  for(const [headers,e] of [[{},{}],[{'oai-authenticated-user-id':''},env()],[{Origin:'https://evil.invalid'},env()],
    [{'Sec-Fetch-Site':'cross-site'},env()],[{'X-Decision-Kernel-Intent':'quick-inbox'},env()],[{'Content-Type':'text/plain'},env()]]){
    const res=await f.call({op:'prepare'},headers,e);assert.equal(res.kind,'blocked');
  }
  assert.equal(await handleNewsRefresh(request({}, {},SITE_ORIGIN+'/old-link'),env()),null);
  assert.equal((await handleNewsRefresh(request({}, {},SITE_ORIGIN+NEWS_REFRESH_PATH,'GET'),env())).status,405);
  assert.equal(f.state.calls.length,0);
});
test('caller cannot select workflow/repository/ref/inputs or pass oversized requests',async()=>{
  const f=await fixture();for(const b of [{op:'prepare',ref:'other'},{op:'dispatch'},{op:'prepare',repo:'other/x'},{op:'prepare',padding:'x'.repeat(9000)},null])
    assert.equal((await f.call(b)).status,400);
  assert.equal(f.state.calls.length,0);
});
test('prepare is read-only, checks all native active statuses and returns an owner-bound expiring permit',async()=>{
  const f=await fixture(),t=await f.prepare();assert.equal(t.permit.previous_number,7);assert.equal(t.permit.code,M);assert.match(t.signature,/^[a-f0-9]{64}$/);
  assert.equal(f.state.posts,0);assert.equal(f.state.calls.filter(c=>c.url.includes('status=')).length,5);
});
test('in-flight including older waiting work, failed CI, changed workflow and missing metadata each stop submission',async()=>{
  for(const mutate of [s=>{s.active=run({status:'waiting',conclusion:null});},s=>{s.ci[0].conclusion='failure';},
    s=>{s.workflow+='\n# changed';},s=>{s.metadata.state='disabled_manually';},s=>{s.news=[];}]){
    const f=await fixture();mutate(f.state);const r=await f.call({op:'prepare'});assert.equal(r.kind,'blocked');assert.equal(f.state.posts,0);
  }
});
test('tampered, foreign-owner, expired and future permits never dispatch',async()=>{
  const f=await fixture(),t=await f.prepare();
  const changed=structuredClone(t);changed.permit.previous_number=8;assert.equal((await f.call({op:'submit',ticket:changed,run_id:null})).kind,'blocked');
  const wrong=env();wrong.DECISION_KERNEL_OWNER_USER_ID='other';
  assert.equal((await f.call({op:'submit',ticket:t,run_id:null},{'oai-authenticated-user-id':'other'},wrong)).kind,'blocked');
  f.state.clock=T+120001;assert.equal((await f.call({op:'submit',ticket:t,run_id:null})).code,'PERMIT_EXPIRED');
  f.state.clock=T-1;assert.equal((await f.call({op:'submit',ticket:t,run_id:null})).code,'PERMIT_EXPIRED');assert.equal(f.state.posts,0);
});
test('same permit concurrent submits share exactly one isolate POST; GitHub direct ID is preserved without completion claim',async()=>{
  const f=await fixture(),ticket=await f.prepare(),input={op:'submit',ticket,run_id:null};
  const [a,b]=await Promise.all([f.call(input),f.call(input)]);assert.equal(f.state.posts,1);assert.deepEqual(a,b);
  assert.equal(a.kind,'submitted');assert.equal(a.run_id,101);assert.equal(a.publication,undefined);
  const posted=JSON.parse(f.state.calls.find(c=>c.method==='POST').body);assert.equal(posted.inputs.site_expected_run_number,'8');assert.equal(posted.inputs.site_expected_code_commit,M);
});
test('native counter or main movement after preparation blocks rather than silently rebasing',async()=>{
  for(const change of [s=>s.news.unshift(run({id:101,run_number:8,html_url:`https://github.com/${REPO}/actions/runs/101`})),
    s=>{s.main='3'.repeat(40);s.ci[0].head_sha=s.main;}]){
    const f=await fixture(),ticket=await f.prepare();change(f.state);assert.equal((await f.call({op:'submit',ticket,run_id:null})).kind,'blocked');assert.equal(f.state.posts,0);
  }
});
test('legacy 204, rejected write, server error and non-JSON receipt never claim publication or retry',async()=>{
  for(const [mode,kind] of [['204','submitted'],['403','rejected'],['500','uncertain'],['html','uncertain']]){
    const f=await fixture(),ticket=await f.prepare();f.state.dispatch=mode;
    const input={op:'submit',ticket,run_id:null},r=await f.call(input);assert.equal(r.kind,kind);assert.equal(r.publication,undefined);
    await f.call(input);assert.equal(f.state.posts,1);
  }
});
test('lost POST response is reconciled by exact correlation, not the newest arbitrary run',async()=>{
  const f=await fixture(),ticket=await f.prepare();f.state.dispatch='throw';
  assert.equal((await f.call({op:'submit',ticket,run_id:null})).kind,'uncertain');
  f.state.news.unshift(run({id:102,run_number:9,html_url:`https://github.com/${REPO}/actions/runs/102`}));
  const r=await f.call({op:'status',ticket,run_id:null});assert.equal(r.run.id,101);assert.equal(r.kind,'run');assert.equal(f.state.posts,1);
});
test('unidentified/multiple matching runs, wrong actor and wrong workflow cannot be silently chosen',async()=>{
  const f=await fixture(),ticket=await f.prepare();assert.equal((await f.call({op:'status',ticket,run_id:null})).kind,'uncertain');
  await f.call({op:'submit',ticket,run_id:null});
  f.state.news[0].actor={id:999};assert.equal((await f.call({op:'status',ticket,run_id:101})).kind,'blocked');
  f.state.news[0].actor={id:83357964};f.state.news[0].path='.github/workflows/other.yml';assert.equal((await f.call({op:'status',ticket,run_id:101})).kind,'blocked');
  f.state.news[0].path=WF;f.state.news.unshift({...f.state.news[0],id:102,run_number:9,html_url:`https://github.com/${REPO}/actions/runs/102`});
  assert.equal((await f.call({op:'status',ticket,run_id:null})).code,'MULTIPLE_REQUEST_RUNS');assert.equal(f.state.posts,1);
});
test('run-number race and rerun remain not-admitted, not fresh success',async()=>{
  for(const change of [r=>{r.run_number++;},r=>{r.run_attempt=2;},r=>{r.head_sha='4'.repeat(40);}]){
    const f=await fixture(),ticket=await f.prepare();await f.call({op:'submit',ticket,run_id:null});change(f.state.news[0]);
    const r=await f.call({op:'status',ticket,run_id:101});assert.equal(r.kind,'not_admitted');assert.equal(r.publication,'not_checked');
  }
});
test('run failure and successful-but-unreadable publication are different, never quiet-market assertions',async()=>{
  const f=await fixture(),ticket=await f.prepare();await f.call({op:'submit',ticket,run_id:null});const run=f.state.news[0];
  run.status='completed';run.conclusion='failure';let r=await f.call({op:'status',ticket,run_id:101});assert.equal(r.run.conclusion,'failure');assert.equal(r.publication,'not_checked');
  run.conclusion='success';r=await f.call({op:'status',ticket,run_id:101});assert.equal(r.publication,'read_unconfirmed');
});
test('same-R original reader verifies result bytes and exact archive/latest-attempt linkage before publication claim',async()=>{
  for(const options of [{},{partial:true},{wrongRun:true},{corrupt:true}]){
    const f=await fixture(),ticket=await f.prepare();await f.call({op:'submit',ticket,run_id:null});publication(f.state,options);
    const r=await f.call({op:'status',ticket,run_id:101});assert.equal(r.publication,options.wrongRun?'not_in_current_reading':options.corrupt?'read_unconfirmed':'same_run_bytes_read');
    if(!options.wrongRun&&!options.corrupt){assert.equal(r.reading_commit,R);assert.equal(r.window_titles,0);assert.equal(r.failed_sources,options.partial?1:0);}
    assert.equal(f.state.posts,1);
  }
});
test('oversized upstream list and response clock contradictions fail before dispatch',async()=>{
  const f=await fixture();f.state.news[0].updated_at=new Date(T+1).toISOString();assert.equal((await f.call({op:'prepare'})).kind,'blocked');assert.equal(f.state.posts,0);
  f.state.news[0].updated_at=new Date(T-5000).toISOString();f.state.news[0].padding='x'.repeat(1100000);assert.equal((await f.call({op:'prepare'})).kind,'blocked');assert.equal(f.state.posts,0);
});

// Minimal output sink: this tests event/data wiring, NOT a rendered browser.
class Element {
  constructor(tag,text=''){this.tag=tag;this.text=String(text);this.children=[];this.disabled=false;}
  append(...children){this.children.push(...children);}replaceChildren(...children){this.text='';this.children=children;}setAttribute(k,v){this[k]=v;}
  set textContent(s){this.text=String(s);this.children=[];}get textContent(){return this.text+this.children.map(c=>c.textContent).join('');}
}
const el=(tag,text='',className='')=>Object.assign(new Element(tag,text),{className});
const ui={el,button:(t,fn)=>Object.assign(el('button',t),{onclick:fn}),link:(t,u)=>Object.assign(el('a',t),{href:u}),folded:(t,s)=>{const n=el('details');n.append(el('summary',t),el('pre',s));return n;}};
function find(n,p){if(p(n))return n;for(const c of n.children){const r=find(c,p);if(r)return r;}}
const button=(n,text)=>find(n,e=>e.tag==='button'&&e.textContent===text);
const context=()=>({ui,reading:{},active:()=>true});
test('controls do no I/O on render, submit once on double click and only poll on an explicit status click',async()=>{
  const f=await fixture(),ctx=context(),calls=[];
  const transport=async(u,o)=>{calls.push(JSON.parse(o.body).op);return handleNewsRefresh(request(JSON.parse(o.body)),env(),{fetcher:f.fetcher,now:()=>f.state.clock});};
  const root=newsRefreshControl(ctx,transport);assert.equal(calls.length,0);const start=button(root,'刷新最新新闻');
  await Promise.all([start.onclick(),start.onclick()]);assert.deepEqual(calls,['prepare','submit']);assert.equal(f.state.posts,1);assert.equal(start.disabled,true);
  await button(root,'检查本次更新').onclick();assert.deepEqual(calls,['prepare','submit','status']);assert.match(root.textContent,/等待执行/);assert.equal(f.state.posts,1);
});
test('navigation during preparation prevents late submission; unknown HTML never becomes saved/success',async()=>{
  const ctx=context();let active=true,release,calls=0;ctx.active=()=>active;
  const root=newsRefreshControl(ctx,async()=>{calls++;return new Promise(r=>{release=r;});});const pending=button(root,'刷新最新新闻').onclick();
  active=false;release(json({kind:'ready',ticket:{permit:{},signature:'x'}}));await pending;assert.equal(calls,1);
  const other=newsRefreshControl(context(),async()=>new Response('<html>fallback</html>',{headers:{'Content-Type':'text/html'}}));await button(other,'刷新最新新闻').onclick();assert.match(other.textContent,/尚未配置/);
});
test('lost submit response and later status refusal retain the permit and never re-enable blind submission',async()=>{
  const f=await fixture(),ctx=context();let calls=0;
  const root=newsRefreshControl(ctx,async(u,o)=>{calls++;const input=JSON.parse(o.body);
    if(input.op==='prepare')return handleNewsRefresh(request(input),env(),{fetcher:f.fetcher,now:()=>T});
    if(input.op==='submit')throw new Error('response lost');return json({kind:'blocked',code:'INVALID_PERMIT'},409);
  });
  const start=button(root,'刷新最新新闻');await start.onclick();assert.equal(start.disabled,true);assert.match(root.textContent,/不要重复提交/);
  await button(root,'检查本次更新').onclick();assert.equal(start.disabled,true);await start.onclick();assert.equal(calls,3);
});
test('published result offers original reader refresh only after same-run byte proof, not an automatic second dispatch',async()=>{
  const f=await fixture(),ctx=context(),root=newsRefreshControl(ctx,async(u,o)=>handleNewsRefresh(request(JSON.parse(o.body)),env(),{fetcher:f.fetcher,now:()=>T}));
  await button(root,'刷新最新新闻').onclick();publication(f.state);await button(root,'检查本次更新').onclick();assert.match(root.textContent,/已发布并读回/);assert.ok(button(root,'读取最新保存结果'));assert.equal(f.state.posts,1);
});
test('human status wording preserves source failures, no-new-event inference and no research completion',()=>{
  const r=refreshPresentation({kind:'run',run:{status:'completed',conclusion:'success'},publication:'same_run_bytes_read',failed_sources:1,window_titles:0,captured_through:new Date(T).toISOString()});
  assert.match(r.title,/部分来源/);assert.match(r.detail,/不是新增事件数/);assert.match(r.detail,/未开展 Quick/);
});


test('separate Worker isolates may dispatch twice but bind the same unique native capture slot',async()=>{
  const f=await fixture(),ticket=await f.prepare();f.state.writeVisible=false;
  const isolated=await import('./server/news-refresh-handler.mjs?isolated-race-test');
  const a=await f.call({op:'submit',ticket,run_id:null});
  const b=await (await isolated.handleNewsRefresh(request({op:'submit',ticket,run_id:null}),env(),{fetcher:f.fetcher,now:()=>f.state.clock})).json();
  assert.equal(a.kind,'submitted');assert.equal(b.kind,'submitted');assert.equal(f.state.posts,2);
  assert.deepEqual(f.state.created.map(x=>x.run.run_number),[8,9]);
  assert.deepEqual(f.state.created.map(x=>x.inputs.site_expected_run_number),['8','8']);
  assert.equal(f.state.created.filter(x=>String(x.run.run_number)===x.inputs.site_expected_run_number).length,1);
  // Python tests execute the exact workflow guard for these two native numbers.
});

test('permit expiring during the second preflight stops before POST',async()=>{
  const f=await fixture(),ticket=await f.prepare();let mainReads=0;
  const fetcher=async(u,o)=>{const response=await f.fetcher(u,o);if(String(u).endsWith('/git/ref/heads/main')&&++mainReads===2)f.state.clock=T+120001;return response;};
  const r=await (await handleNewsRefresh(request({op:'submit',ticket,run_id:null}),env(),{fetcher,now:()=>f.state.clock})).json();
  assert.equal(r.code,'PERMIT_EXPIRED');assert.equal(f.state.posts,0);
});
