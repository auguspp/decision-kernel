/** Synthetic contract tests. No live Site/user selection, model call, or production write. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {setTimeout as tick} from 'node:timers/promises';
import {selection,contextValue,resolveSelection,recordBody,inboxView,batchRequest,MARKER,INBOX_URL} from './quick-inbox.mjs';
import {readInboxComments,readQuickResult,openPinnedReading,REPO,READ_REF} from './reading.mjs';
import {handleQuickInbox,SITE_ORIGIN} from './server/quick-inbox-handler.mjs';
import {transferButton,quickInboxPage,saveInbox} from './quick-inbox-ui.mjs';
const sha=s=>createHash('sha256').update(s).digest('hex');
const R='a'.repeat(40),M='b'.repeat(40),T='2026-09-27T00:00:00Z';
const nonce='01234567-89ab-4cde-8fab-0123456789ab',nonce2='01234567-89ab-4cde-8fab-0123456789ac';
const API=`https://api.github.com/repos/${REPO}`,ROOT=`${API}/issues/601`;
const auth={signal_transition_authority:'NONE',human_attention_authority:'NONE',research_authority:'NONE',investment_authority:'NONE'};
const source={read_path:'details/radar/news-daily.json',bytes:12,sha256:'c'.repeat(64)};
const select={kind:'news',reading:R,subject:'d'.repeat(64),asset:null};
const context={selection:select,code:M,title:'测试来源标题',source};
const result={commit:M,path:'docs/readings/test.md',bytes:6,sha256:sha('result')};
const comment=(id,body,extra={})=>({id,body,created_at:T,updated_at:T,user:{id:83357964},issue_url:ROOT,html_url:`${INBOX_URL}#issuecomment-${id}`,...extra});
async function add(id=1,n=nonce,c=context){return comment(id,await recordBody({op:'add',nonce:n,context:c}));}
async function remove(id,requests){return comment(id,await recordBody({op:'remove',requests}));}
async function done(id,requests,r=result){return comment(id,await recordBody({op:'result',requests,result:r}));}
const view=(comments,verify=async()=>({text:'result'}))=>inboxView({comments,observedAt:T},verify);
const payload=()=>({schema_version:1,entry_ref:READ_REF,code_commit:M,reading_hash:'e'.repeat(64),semantics:'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',...auth,lanes:{}});
function transport(initial=[]) {
  let comments=[...initial];const calls=[];let writeMode='success';
  const meta=()=>({number:601,user:{id:83357964},html_url:INBOX_URL,comments:comments.length,updated_at:T});
  const fetcher=async(url,options={})=>{
    calls.push({url,options});
    if(url===ROOT)return Response.json(meta());
    if(url.startsWith(ROOT+'/comments?')){const page=Number(new URL(url).searchParams.get('page'));return Response.json(comments.slice((page-1)*100,page*100));}
    if(url===ROOT+'/comments' && options.method==='POST'){
      if(writeMode==='denied')return new Response('',{status:403});
      const id=comments.reduce((m,c)=>Math.max(m,c.id),0)+1;
      const c=comment(id,JSON.parse(options.body).body);comments.push(c);
      if(writeMode==='uncertain')throw new Error('never expose token: secret-fixture');
      return Response.json(c,{status:201});
    }
    if(url.startsWith(API+'/issues/comments/')){
      if(writeMode==='bad-readback')return Response.json({...comments.at(-1),body:'wrong'});
      return Response.json(comments.find(c=>c.id===Number(url.split('/').at(-1))));
    }
    throw new Error('UNEXPECTED_TRANSPORT '+url);
  };
  return {fetcher,calls,comments:()=>comments,setMode:m=>{writeMode=m;}};
}
const env={DECISION_KERNEL_ENABLE_INBOX:'1',DECISION_KERNEL_OWNER_USER_ID:'owner-fixture',DECISION_KERNEL_GITHUB_TOKEN:'secret-fixture'};
const post=(body,headers={},url=SITE_ORIGIN+'/api/quick-inbox')=>new Request(url,{method:'POST',headers:{Origin:SITE_ORIGIN,'Content-Type':'application/json','X-Decision-Kernel-Intent':'quick-inbox','oai-authenticated-user-id':'owner-fixture','Sec-Fetch-Site':'same-origin',...headers},body:typeof body==='string'?body:JSON.stringify(body)});
const addRequest={action:'add',nonce,selection:select};
function readingFixture(){return {ref:R,payload:{code_commit:M,research:{daily_news:{details:{json:source}}}},readFile:async()=>({text:JSON.stringify({projection:{capture:{projection:{news:{projection:{kind:'NEWS_EVENT_CANDIDATE',automatic_admission:false,observations:[{version_id:select.subject,qualification:'CONTEXT_ONLY',title:context.title}]}}}}}})})};}
const options=t=>({fetcher:t.fetcher,openReading:async()=>readingFixture()});

test('selection is a closed set of exact identities, not arbitrary URLs or workflow arguments',()=>{
  assert.deepEqual(selection(select),select);
  for(const bad of [{...select,repo:'foreign'}, {...select,reading:'main'},{...select,kind:'full'},{...select,subject:'javascript:x'},{...select,asset:'private note'}])assert.throws(()=>selection(bad));
  for(const kind of ['company','material'])assert.ok(selection({kind,reading:R,subject:'600276.SH',asset:kind==='material'?'retained':null}));
  assert.throws(()=>contextValue({...context,source:{...source,read_path:'../escape'}}));
});
test('server restores exact selected news and refuses nonexistent or duplicate observations',async()=>{
  const c=await resolveSelection(select,async()=>readingFixture());assert.deepEqual(c,context);
  await assert.rejects(()=>resolveSelection({...select,subject:'f'.repeat(64)},async()=>readingFixture()),/NOT_UNIQUE/);
  const r=readingFixture();const original=r.readFile;r.readFile=async()=>{const d=JSON.parse((await original()).text);d.projection.capture.projection.news.projection.observations.push(d.projection.capture.projection.news.projection.observations[0]);return{text:JSON.stringify(d)};};
  await assert.rejects(()=>resolveSelection(select,async()=>r),/NOT_UNIQUE/);
});
test('real unchanged reading transport verifies news bytes before an Inbox locator is built',async()=>{
  const text=(await readingFixture().readFile()).text,d={...source,bytes:Buffer.byteLength(text),sha256:sha(text)};
  const state={...payload(),research:{daily_news:{details:{json:d}}}};
  let calls=0;const fetcher=async url=>{calls++;return new Response(url.endsWith('current-state.json')?JSON.stringify(state):text);};
  const c=await resolveSelection(select,ref=>openPinnedReading(ref,fetcher));assert.equal(c.source.sha256,d.sha256);assert.equal(calls,2);
  await assert.rejects(()=>resolveSelection(select,ref=>openPinnedReading(ref,async url=>new Response(url.endsWith('current-state.json')?JSON.stringify(state):text+'x'))),/INTEGRITY/);
});
test('company and material resolve through the existing company catalogue; missing body cannot be called transferred',async()=>{
  const s={kind:'company',reading:R,subject:'600276.SH',asset:null},d={...source,read_path:'details/research/asset-reentry.json'};
  const r={ref:R,payload:{code_commit:M},references:[d],readAssets:async()=>({companies:[{thscode:s.subject,saved_watch:{ticker:s.subject,company_name:'测试公司'},assets:[{id:'a',use:'RETAINED_RESEARCH_DOCUMENT',source}]}]}),readFile:async()=>({text:'body'})};
  assert.equal((await resolveSelection(s,async()=>r)).source.read_path,d.read_path);
  assert.equal((await resolveSelection({...s,kind:'material',asset:'a'},async()=>r)).source.read_path,source.read_path);
  r.readFile=async()=>{throw new Error('BODY_UNAVAILABLE');};await assert.rejects(()=>resolveSelection({...s,kind:'material',asset:'a'},async()=>r),/UNAVAILABLE/);
});
test('sector selection preserves original day and rejects another market day',async()=>{
  const s={kind:'sector',reading:R,subject:'881101.TI',asset:null};
  const data={semantics:'READ_ONLY_SAVED_MARKET_CONTEXT_NOT_A_NEW_ALERT_OR_RESEARCH_ROUTE',context_hash:source.sha256,market_session:'2026-09-24',universes:[{rows:[{observation:{thscode:s.subject,name:'测试行业',as_of_session:'2026-09-24'}}]}]};
  const r={payload:{code_commit:M,lanes:{sector:{last_qualified_result:{context_hash:source.sha256,market_session:'2026-09-24',details:{'context/context.json':source}}}}},readFile:async()=>({text:JSON.stringify(data)})};
  assert.match((await resolveSelection(s,async()=>r)).title,/2026-09-24/);data.market_session='2026-09-25';await assert.rejects(()=>resolveSelection(s,async()=>r),/CONTEXT/);
});
test('identical pending contexts coalesce but all native request ids remain recoverable',async()=>{
  const v=await view([await add(1),await add(2,nonce2)]);assert.equal(v.pending.length,1);assert.deepEqual(v.pending[0].requests,[1,2]);
  assert.match(batchRequest(v.pending),/重新读取 #601/);assert.match(batchRequest(v.pending),/复制本身没有启动研究/);assert.match(batchRequest(v.pending),new RegExp(R));
});
test('a late duplicate of the same nonce cannot reopen a withdrawn request',async()=>{
  const v=await view([await add(1),await remove(2,[1]),await add(3)]);assert.equal(v.pending.length,0);assert.equal(v.removed.length,1);assert.deepEqual(v.removed[0].requests,[1,3]);
});
test('old result or withdrawal never closes a newly selected instance',async()=>{
  const v=await view([await add(1),await done(2,[1]),await add(3,nonce2),await remove(4,[1])]);
  assert.deepEqual(v.pending[0].requests,[3]);assert.equal(v.removed.length,1);assert.equal(v.finished.length,0);
});
test('a receipt is not completion until its pinned result bytes can be read and verified',async()=>{
  const cs=[await add(1),await done(2,[1])];const before=JSON.stringify(cs);
  const ok=await view(cs);assert.equal(ok.finished.length,1);assert.equal(ok.pending.length,0);
  const failed=await view(cs,async()=>{throw new Error('INTEGRITY');});assert.equal(failed.pending.length,1);assert.equal(failed.finished.length,0);assert.equal(JSON.stringify(cs),before);
});
test('foreign writers cannot grant completion; edited or malformed trusted records are explicit gaps',async()=>{
  const foreign={...await done(2,[1]),user:{id:7}};const v=await view([await add(1),foreign]);assert.equal(v.pending.length,1);assert.ok(v.gaps.length);
  const edited={...await add(1),updated_at:'2026-09-27T00:01:00Z'};await assert.rejects(()=>view([edited]),/EDITED/);
  await assert.rejects(()=>view([comment(1,MARKER+'\n{}')]),/UNKNOWN/);
  await assert.rejects(async()=>view([await done(1,[99])]),/UNKNOWN_INBOX_TARGET/);
  await assert.rejects(async()=>view([await add(1),await add(2,nonce,{...context,title:'changed'})]),/NONCE_CONTEXT_CONFLICT/);
});
test('native Inbox reader requires all declared pages and stable counts, including zero',async()=>{
  const t=transport([await add()]);assert.equal((await readInboxComments(t.fetcher)).comments.length,1);
  const zero=transport();assert.equal((await readInboxComments(zero.fetcher)).comments.length,0);
  await assert.rejects(()=>readInboxComments(async url=>url===ROOT?Response.json({number:601,user:{id:83357964},html_url:INBOX_URL,comments:1,updated_at:T}):Response.json([])),/PARTIAL/);
  await assert.rejects(()=>readInboxComments(async()=>Response.json({number:601,user:{id:83357964},html_url:INBOX_URL,comments:501,updated_at:T})),/500/);
});
test('result transport is pinned, bounded, no auth, and verifies bytes rather than a save claim',async()=>{
  let call;const ok=await readQuickResult(result,async(url,o)=>{call={url,o};return new Response('result');});assert.equal(ok.text,'result');assert.match(call.url,new RegExp(M));assert.equal(call.o.method,'GET');assert.equal(call.o.headers,undefined);
  await assert.rejects(()=>readQuickResult(result,async()=>new Response('wrong!')),/INTEGRITY/);
  for(const bad of [{...result,commit:'main'},{...result,path:'../../x.md'},{...result,path:'https://host/file.md'},{...result,bytes:0}])await assert.rejects(()=>readQuickResult(bad));
});
test('handler fails closed for missing config/owner and does not claim the root or unknown paths',async()=>{
  const t=transport();assert.equal((await handleQuickInbox(post(addRequest),{},options(t))).status,503);
  assert.equal((await handleQuickInbox(post(addRequest,{'oai-authenticated-user-id':'wrong'}),env,options(t))).status,403);
  assert.equal(await handleQuickInbox(new Request(SITE_ORIGIN+'/'),env,options(t)),null);assert.equal(t.calls.length,0);
});
test('cross-origin, simple forms, unknown intents and caller-selected targets cause zero GitHub requests',async()=>{
  for(const headers of [{Origin:'https://evil.test'},{'Content-Type':'text/plain'},{'X-Decision-Kernel-Intent':''},{'Sec-Fetch-Site':'cross-site'}]){
    const t=transport();assert.equal((await handleQuickInbox(post(addRequest,headers),env,options(t))).status,403);assert.equal(t.calls.length,0);
  }
  for(const body of [{...addRequest,workflow:'trade.yml'},{action:'full'},{...addRequest,nonce:'bad'},{...addRequest,selection:{...select,reason:'private note'}}]){
    const t=transport();assert.equal((await handleQuickInbox(post(body),env,options(t))).status,400);assert.equal(t.calls.length,0);
  }
});
test('one add POST is reported saved only after exact same-Issue body/user readback',async()=>{
  const t=transport();const r=await handleQuickInbox(post(addRequest),env,options(t));assert.equal(r.status,201);assert.equal((await r.json()).saved,true);
  assert.equal(t.calls.filter(c=>c.options.method==='POST').length,1);
  const writes=t.calls.filter(c=>c.options.method==='POST');assert.equal(writes[0].url,ROOT+'/comments');assert.ok(writes[0].options.headers.Authorization.includes('secret-fixture'));
  assert.ok(t.calls.every(c=>c.url.startsWith(API+'/issues/')));
  assert.equal(t.comments()[0].body,await recordBody({op:'add',nonce,context}));
});
test('same nonce and pending context reuse existing GitHub record without another POST',async()=>{
  const t=transport([await add()]);const r=await handleQuickInbox(post(addRequest),env,options(t));assert.equal((await r.json()).reused,true);
  const another=await handleQuickInbox(post({...addRequest,nonce:nonce2}),env,options(t));assert.equal((await another.json()).reused,true);
  assert.equal(t.calls.filter(c=>c.options.method==='POST').length,0);
  const conflict=await handleQuickInbox(post({...addRequest,selection:{...select,reading:M}}),env,options(t));assert.equal(conflict.status,409);
});
test('uncertain submission is not retried and replay reconciles the original saved nonce',async()=>{
  const t=transport();t.setMode('uncertain');const r=await handleQuickInbox(post(addRequest),env,options(t));assert.equal(r.status,202);
  const b=await r.text();assert.match(b,/false/);assert.ok(!b.includes('secret-fixture'));assert.equal(t.calls.filter(c=>c.options.method==='POST').length,1);
  const replay=await handleQuickInbox(post(addRequest),env,options(t));assert.equal((await replay.json()).saved,true);assert.equal(t.calls.filter(c=>c.options.method==='POST').length,1);
});
test('write denial and mismatched readback do not become a success or an authentication fallback',async()=>{
  for(const mode of ['denied','bad-readback']){const t=transport();t.setMode(mode);const r=await handleQuickInbox(post(addRequest),env,options(t));assert.equal((await r.json()).saved,false);assert.equal(t.calls.filter(c=>c.options.method==='POST').length,1);}
});
test('remove appends history, retains the add, and cannot target a foreign/missing request',async()=>{
  const t=transport([await add()]);const r=await handleQuickInbox(post({action:'remove',requests:[1]}),env,options(t));assert.equal(r.status,201);assert.equal(t.comments().length,2);assert.equal((await view(t.comments())).removed.length,1);
  const bad=await handleQuickInbox(post({action:'remove',requests:[99]}),env,options(t));assert.equal(bad.status,409);assert.equal(t.comments().length,2);
});
test('missing original and oversized input fail before any append',async()=>{
  const t=transport();const r=await handleQuickInbox(post({...addRequest,selection:{...select,subject:'f'.repeat(64)}}),env,options(t));assert.equal(r.status,422);
  assert.equal((await handleQuickInbox(post('x'.repeat(8193)),env,options(t))).status,400);assert.equal(t.calls.filter(c=>c.options.method==='POST').length,0);
});
// Minimal literal output sink, not a browser or a visual acceptance test.
class Node{constructor(tag,text=''){this.tagName=tag;this.text=text;this.children=[];}append(...c){this.children.push(...c);}replaceChildren(...c){this.text='';this.children=c;}set textContent(t){this.text=String(t);this.children=[];}get textContent(){return this.text+this.children.map(c=>c.textContent).join('');}setAttribute(k,v){this[k]=v;}}
const el=(tag,text='',className='')=>Object.assign(new Node(tag,text),{className});
const button=(text,fn)=>Object.assign(el('button',text),{onclick:fn});
const ui={el,button,link:(t,url)=>Object.assign(el('a',t),{href:url}),card:(t,s)=>{const n=el('section');n.append(el('h3',t),el('p',s));return n;},disclosure:(t,...c)=>{const n=el('details');n.append(el('summary',t),...c);return n;}};
function find(n,p){if(p(n))return n;for(const c of n.children){const r=find(c,p);if(r)return r;}}
async function globals(fetcher,run){const old=globalThis.fetch;globalThis.fetch=fetcher;try{await run();}finally{globalThis.fetch=old;}}
test('transfer button does not write on load; parallel clicks share one submission and successful save is not research',async()=>{
  let calls=0,resolve;await globals(()=>{calls++;return new Promise(r=>resolve=r);},async()=>{
    const root=transferButton(ui,select),b=find(root,n=>n.tagName==='button');assert.equal(calls,0);
    const first=b.onclick(),second=b.onclick();assert.equal(calls,1);resolve(Response.json({saved:true},{status:201}));await Promise.all([first,second]);
    assert.match(root.textContent,/没有启动研究/);assert.equal(b.disabled,true);
  });
});
test('uncertain/HTML response cannot paint saved, and late save cannot overwrite another view',async()=>{
  for(const response of [Response.json({saved:false,uncertain:true},{status:202}),new Response('<html>old Site</html>')])await globals(async()=>response,async()=>{
    const root=transferButton(ui,select);await find(root,n=>n.tagName==='button').onclick();assert.ok(!root.textContent.includes('已加入待 Quick'));
  });
  let resolve,active=true;await globals(()=>new Promise(r=>resolve=r),async()=>{const root=transferButton(ui,select,()=>active),b=find(root,n=>n.tagName==='button'),p=b.onclick();active=false;resolve(Response.json({saved:true}));await p;assert.ok(!root.textContent.includes('已加入待 Quick'));});
});
test('Inbox UI reads only by explicit choice, copies batches without writes, and an outage is not zero',async()=>{
  const t=transport([await add()]);await globals(t.fetcher,async()=>{
    const root=el('div');quickInboxPage(root,ui);assert.equal(t.calls.length,0);
    await find(root,n=>n.tagName==='button'&&n.textContent==='读取待 Quick 清单').onclick();assert.match(root.textContent,/待 Quick 1 项/);
    const before=t.calls.length;await find(root,n=>n.tagName==='button'&&n.textContent==='复制全部待 Quick').onclick();assert.equal(t.calls.length,before);assert.match(root.textContent,/复制本身没有启动研究/);
  });
  await globals(async()=>new Response('',{status:503}),async()=>{const root=el('div');quickInboxPage(root,ui);await find(root,n=>n.tagName==='button').onclick();assert.match(root.textContent,/不能当作0项/);});
});


test('preview permits only the explicit same-origin connection addition, not inline scripts or a new host',()=>{
  const html=readFileSync(new URL('./index.html',import.meta.url),'utf8');
  assert.match(html,/connect-src 'self' https:\/\/api.github.com https:\/\/raw.githubusercontent.com;/);
  assert.match(html,/default-src 'none'; script-src 'self';/);
  assert.match(html,/转存需明确点击并接通授权服务/);
  assert.ok(!html.includes('本页不执行研究、投资或写入'));
});


test('grouped pending results stay visible and replay confirmation does not claim a new pending item',async()=>{
  const v=await view([await add(1),await add(2,nonce2),await done(3,[2])],async()=>{throw new Error('UNREADABLE');});
  assert.equal(v.pending.length,1);assert.equal(v.pending[0].results.length,1);assert.deepEqual(v.pending[0].requests,[1,2]);
  await globals(async()=>Response.json({saved:true,reused:true}),async()=>{
    const root=transferButton(ui,select);await find(root,n=>n.tagName==='button').onclick();
    assert.match(root.textContent,/已确认已有转存/);assert.match(root.textContent,/核对原记录的当前状态/);
    assert.ok(!root.textContent.includes('已加入待 Quick'));assert.ok(!root.textContent.includes('尚未研究'));
  });
});
