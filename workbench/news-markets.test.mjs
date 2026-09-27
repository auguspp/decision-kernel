/** Synthetic view/DOM tests; not live Sites, visual layout or research acceptance. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {setTimeout as tick} from 'node:timers/promises';
import {articleURL,newsView,sectorView,newsResume,newsPage,marketsPage} from './news-markets.mjs';
import {FILE_LIMIT,openPinnedReading,REPO,READ_REF} from './reading.mjs';
const R='a'.repeat(40), H='b'.repeat(64), T='2026-09-26T02:00:00Z';
const auth={signal_transition_authority:'NONE',human_attention_authority:'NONE',research_authority:'NONE',investment_authority:'NONE'};
const sha=text=>createHash('sha256').update(text).digest('hex');
const descriptor=text=>({read_path:'details/radar/news-daily.json',bytes:Buffer.byteLength(text),sha256:sha(text)});
const observed=(i=1)=>({article_id:String(i).padStart(64,'0'),version_id:sha('version-'+i),title:'同一标题 '+(i===2?'':i),source_id:'cls',
  url:'https://www.cls.cn/detail/'+i,fetched_at:T,qualification:'CONTEXT_ONLY',business_linkage:'NOT_ESTABLISHED',
  publication_claims:{pubDate:{status:'PARSED_CLAIM_NOT_PUBLISHER_VERIFIED',parsed_at:'2026-09-26T01:00:00Z'}}});
function news(rows=[observed()]){
  const saved={capture_hash:H,captured_through:T,status:'WINDOWS_CAPTURED'};
  const report={projection:{...auth,automatic_admission:false,semantic_review:'NOT_PERFORMED',state:{...saved},capture:{projection:{...auth,
    version:'native-newsnow-window-v1',automatic_admission:false,capture_hash:H,captured_from:T,captured_through:T,
    coverage:{complete_news_coverage:false},source_outcomes:[{source_id:'cls',status:'OBSERVATIONS_NORMALIZED'}],
    news:{projection:{...auth,automatic_admission:false,kind:'NEWS_EVENT_CANDIDATE',company_mapping:'EXACT_SAVED_NAME_TEXT_ONLY_NOT_SECURITY_OR_EXPOSURE_ACCEPTANCE',observations:rows,companies:[]}}}}}};
  return {report,saved};
}
function sector(){
  const saved={context_hash:H,market_session:'2026-09-24'};
  const report={...auth,schema_version:1,context_hash:H,market_session:saved.market_session,benchmark_thscode:'000300.SH',
    semantics:'READ_ONLY_SAVED_MARKET_CONTEXT_NOT_A_NEW_ALERT_OR_RESEARCH_ROUTE',universes:[{family:'BROAD_881',count:1,rows:[{
      currently_gate_active:true,recent_weakening:false,path_description:'原路径描述',observation:{name:'测试行业',thscode:'881101.TI',as_of_session:saved.market_session,
      ...Object.fromEntries([5,20,60].map(h=>['horizon_'+h,{sessions:h,sector_return:'0.123456',excess_return:'0.01'}]))}}]}]};
  return {report,saved};
}
test('unsafe news URLs do not become clickable or execute source HTML',()=>{
  for(const u of ['javascript:alert(1)','data:text/html,x','//x','https://u:p@host/','https://host/\nx','file:///tmp/x',null])assert.equal(articleURL(u),null);
  assert.equal(articleURL('https://www.cls.cn/detail/1'),'https://www.cls.cn/detail/1');
});
test('news retains distinct versions/titles and time claims without inference or mutation',()=>{
  const a=observed(),b={...observed(2),title:a.title},f=news([a,b]),before=JSON.stringify(f);
  const v=newsView(JSON.stringify(f.report),f.saved);assert.equal(v.rows.length,2);assert.match(v.rows[0].published,/北京时间/);
  assert.equal(v.rows[0].fetched,T);assert.deepEqual(v.rows[0].companies,[]);assert.equal(JSON.stringify(f),before);
});
test('news inconsistent clocks, duplicate identities and failed sources never certify a clean empty event list',()=>{
  const f=news([observed(),observed()]);assert.equal(newsView(JSON.stringify(f.report),f.saved).rows.length,0);assert.ok(newsView(JSON.stringify(f.report),f.saved).gaps.length);
  f.report.projection.capture.projection.source_outcomes[0].status='RESPONSE_UNAVAILABLE';assert.match(newsView(JSON.stringify(f.report),f.saved).gaps.join(),/不能解释为没有新闻/);
  f.saved.capture_hash='c'.repeat(64);assert.throws(()=>newsView(JSON.stringify(f.report),f.saved),/MISMATCH/);
});
test('unverified publication time stays unknown or conflicted, not fetched time',()=>{
  const r=observed();r.publication_claims={};const f=news([r]);assert.equal(newsView(JSON.stringify(f.report),f.saved).rows[0].published,'发布时间未知');
  r.publication_claims={a:{status:'PARSED_CLAIM_NOT_PUBLISHER_VERIFIED',parsed_at:T},b:{status:'PARSED_CLAIM_NOT_PUBLISHER_VERIFIED',parsed_at:'2026-09-25T01:00:00Z'}};
  assert.equal(newsView(JSON.stringify(f.report),f.saved).rows[0].published,'时间声明不一致');
});
test('news unsupported semantic or authority cannot silently upgrade source context',()=>{
  const f=news();f.report.projection.research_authority='FULL';assert.throws(()=>newsView(JSON.stringify(f.report),f.saved),/MISMATCH/);
});
test('sector rows use exact saved context/session, units and independent family identifiers',()=>{
  const f=sector(),before=JSON.stringify(f);const v=sectorView(JSON.stringify(f.report),f.saved);assert.equal(v.rows.length,1);assert.match(v.rows[0].returns[0],/12.35%/);assert.equal(v.day,'2026-09-24');
  assert.equal(JSON.stringify(f),before);f.saved.market_session='2026-09-25';assert.throws(()=>sectorView(JSON.stringify(f.report),f.saved),/MISMATCH/);
});
test('sector malformed row cannot enter display and mismatched horizon is unknown',()=>{
  const f=sector();f.report.universes[0].rows[0].observation.horizon_20.sessions=5;assert.equal(sectorView(JSON.stringify(f.report),f.saved).rows[0].excess,'口径未知');
  f.report.universes[0].rows[0].observation.as_of_session='2026-09-25';const v=sectorView(JSON.stringify(f.report),f.saved);assert.equal(v.rows.length,0);assert.ok(v.gaps.length);
});
test('copied single-news fallback is a compact exact locator, not a duplicated source JSON blob',()=>{
  const f=news(),text=JSON.stringify(f.report),d=descriptor(text),r=newsView(text,f.saved).rows[0],copy=newsResume(R,d,r);
  assert.match(copy,/复制本身没有启动研究/);assert.match(copy,/不得自动 Full/);
  assert.match(copy,new RegExp(`reading R: ${R}`));assert.match(copy,new RegExp(`read_path: ${d.read_path}`));assert.match(copy,new RegExp(r.id));
  assert.ok(!copy.includes('publication_claims'));assert.ok(!copy.includes(r.url));assert.ok(!copy.trim().startsWith('{'));
  assert.throws(()=>newsResume('main',d,r),/UNPINNED/);
});
test('registered file over old 512KiB limit reads bounded bytes; >1MiB and corrupt content fail closed',async()=>{
  const text='x'.repeat(600*1024), d=descriptor(text);
  const state={schema_version:1,entry_ref:READ_REF,code_commit:'c'.repeat(40),semantics:'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',reading_hash:H,...auth,lanes:{},research:{d}};
  const reading=await openPinnedReading(R,async(url,o)=>{assert.equal(o.method,'GET');return new Response(url.endsWith('current-state.json')?JSON.stringify(state):text);});
  assert.equal((await reading.readFile(d)).text.length,text.length);assert.equal(FILE_LIMIT,1024*1024);
  const big={...d,bytes:FILE_LIMIT+1};state.research.d=big;
  const oversized=await openPinnedReading(R,async()=>new Response(JSON.stringify(state)));await assert.rejects(()=>oversized.readFile(big),/UNSUPPORTED/);
  state.research.d=d;const tooLong=await openPinnedReading(R,async url=>new Response(url.endsWith('current-state.json')?JSON.stringify(state):'x'.repeat(FILE_LIMIT+1)));
  await assert.rejects(()=>tooLong.readFile(d),/TOO_LARGE/);
  state.research.d=d;const wrong=await openPinnedReading(R,async url=>new Response(url.endsWith('current-state.json')?JSON.stringify(state):'y'.repeat(text.length)));
  await assert.rejects(()=>wrong.readFile(d),/INTEGRITY/);
});
// Output sink used only by the new views; no browser behaviour or policy emulation.
class Node{constructor(tag,text=''){this.tagName=tag;this.text=text;this.children=[];this.value='';}append(...c){this.children.push(...c);}replaceChildren(...c){this.text='';this.children=c;}
  set textContent(t){this.text=String(t);this.children=[];}get textContent(){return this.text+this.children.map(c=>c.textContent).join('');}setAttribute(k,v){this[k]=v;}insertBefore(c,b){this.children.splice(this.children.indexOf(b),0,c);}}
const el=(tag,text='',className='')=>Object.assign(new Node(tag,text),{className});
const button=(text,fn)=>Object.assign(el('button',text),{onclick:fn});
const ui={el,button,link:(t,url)=>Object.assign(el('a',t),{href:url}),notice:t=>el('p',t),folded:(t,s)=>{const n=el('details');n.append(el('summary',t),el('pre',s));return n;},
  disclosure:(t,...c)=>{const n=el('details');n.append(el('summary',t),...c);return n;},card:(t,s='')=>{const n=el('section');n.append(el('h3',t),el('p',s));return n;},dataTable:(t,h)=>{const wrapper=el('table'),body=el('tbody');wrapper.append(el('caption',t),...h.map(v=>el('th',v)),body);return {wrapper,body};}};
function find(n,p){if(p(n))return n;for(const c of n.children||[]){const r=find(c,p);if(r)return r;}}
function context(report,saved){const text=JSON.stringify(report);let calls=0;return{ctx:{reading:{ref:R,payload:{research:{daily_news:{...saved,details:{json:descriptor(text)}}},lanes:{}},readFile:async()=>{calls++;return {text};}},ui,active:()=>true,onRead:()=>{},onCompany:()=>{}},calls:()=>calls};}
test('news view paginates/searches source text, one cache per reading and no write/HTML execution',async()=>{
  const f=news(Array.from({length:25},(_,i)=>observed(i+1))),{ctx,calls}=context(f.report,f.saved),root=el('div');newsPage(root,ctx);await tick(0);
  assert.match(root.textContent,/25 条标题/);assert.equal(root.children[0].tagName,'section');assert.ok(!find(root,n=>n.tagName==='script'));
  const input=find(root,n=>n['aria-label']==='搜索新闻标题');input.value='同一标题 25';input.oninput();assert.match(root.textContent,/筛选 1 条/);assert.equal(calls(),1);
  newsPage(el('div'),ctx);await tick(0);assert.equal(calls(),1);
});
test('late news success after navigation cannot overwrite visible content',async()=>{
  const f=news(),{ctx}=context(f.report,f.saved),root=el('div');let resolve,active=true;ctx.active=()=>active;ctx.reading.readFile=()=>new Promise(r=>{resolve=r;});
  newsPage(root,ctx);active=false;root.replaceChildren(el('p','另一个页面'));resolve({text:JSON.stringify(f.report)});await tick(0);assert.equal(root.textContent,'另一个页面');
});
test('news failure remains a gap and not zero; missing source keeps other pages usable',async()=>{
  const f=news(),{ctx}=context(f.report,f.saved),root=el('div');ctx.reading.readFile=async()=>{throw new Error('HTTP_503');};newsPage(root,ctx);await tick(0);assert.match(root.textContent,/不把失败当作无新增/);assert.match(root.textContent,/HTTP_503/);
});
test('market view renders saved industry returns; unrelated news is not fetched and missing global data stays explicit',async()=>{
  const f=sector(),text=JSON.stringify(f.report),root=el('div');let calls=0;
  marketsPage(root,{reading:{ref:R,payload:{lanes:{sector:{health:'LATEST_ATTEMPT_SUCCEEDED',last_qualified_result:{...f.saved,details:{'context/context.json':{...descriptor(text),read_path:'details/sector/1/context/context.json'}}}},stock:{health:'LATEST_ATTEMPT_SUCCEEDED',last_qualified_result:{market_session:'2026-09-24',dispositions:[]}}}},readFile:async()=>{calls++;return {text};}},ui,active:()=>true,onRead:()=>{},onCompany:()=>{}});
  await tick(0);assert.match(root.textContent,/测试行业/);assert.match(root.textContent,/本包还没有可读全球市场资料/);assert.match(root.textContent,/美债\/国际利率、黄金原油、外汇、加密资产尚未接入/);assert.match(root.textContent,/不是全市场/);assert.equal(calls,1);
});

// Actual app wiring, existing reader, synthetic transport. No live browser claim.
test('actual app exposes News and preserves exact-R reading after refresh',async()=>{
  const ids=Object.fromEntries(['nav','modules','detail','content','heading','subtitle','refresh','identity'].map(id=>[id,el('div')]));
  let ref=R;const calls=[];const f=news();
  const bodies=new Map([R,'d'.repeat(40)].map(r=>{const n=structuredClone(f.report);n.projection.capture.projection.news.projection.observations[0].title='新闻-'+r;return[r,JSON.stringify(n)];}));
  const globals={document:{head:el('head'),createElement:el,createTextNode:t=>el('#text',t),getElementById:id=>ids[id]},navigator:{},fetch:async(url,options)=>{
    calls.push(url);assert.equal(options.method,'GET');assert.equal(options.body,undefined);
    let data;
    if(url==='/api/read-model/current-state'){
      assert.equal(options.credentials,'same-origin');assert.equal(options.headers?.['X-Decision-Kernel-Intent'],'read-model-ref');
      data={ref:READ_REF,commit:ref};
    }
    else if(url.includes('/git/ref/'))data={ref:'refs/heads/'+READ_REF,object:{type:'commit',sha:ref}};
    else if(url.endsWith('/current-state.json'))data={schema_version:1,entry_ref:READ_REF,code_commit:'c'.repeat(40),reading_hash:H,...auth,lanes:{},
      semantics:'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',checks:{},research:{daily_news:{...f.saved,details:{json:descriptor(bodies.get(ref))}}}};
    else if(url.endsWith('/issues/575'))data={number:575,html_url:`https://github.com/${REPO}/issues/575`,comments:0};
    else if(url.includes('/issues/575/comments?'))data=[];
    else if(url.endsWith('/issues/581'))data={number:581,html_url:`https://github.com/${REPO}/issues/581`,body:'健康原记录',updated_at:T};
    else if(url.endsWith('/details/radar/news-daily.json')){const r=url.split('/')[5];assert.ok(bodies.has(r));return new Response(bodies.get(r));}
    else assert.fail('Unexpected transport '+url);
    return new Response(JSON.stringify(data));
  }};
  const previous=Object.fromEntries(Object.keys(globals).map(k=>[k,Object.getOwnPropertyDescriptor(globalThis,k)]));
  for(const [k,v] of Object.entries(globals))Object.defineProperty(globalThis,k,{configurable:true,value:v});
  try{
    await import('./app.mjs?news-markets-test');
    for(let i=0;i<100 && ids.refresh.disabled;i++)await tick(1);
    const nav=find(ids.nav,n=>n.tagName==='button'&&n.textContent==='新闻');assert.ok(nav);nav.onclick();
    for(let i=0;i<100 && !ids.content.textContent.includes('新闻-'+R);i++)await tick(1);
    assert.match(ids.content.textContent,new RegExp('新闻-'+R));
    ref='d'.repeat(40);await ids.refresh.onclick();
    for(let i=0;i<100 && !ids.content.textContent.includes('新闻-'+ref);i++)await tick(1);
    assert.match(ids.content.textContent,new RegExp('新闻-'+ref));assert.ok(!ids.content.textContent.includes('新闻-'+R));
    assert.equal(calls.filter(u=>u.endsWith('/details/radar/news-daily.json')).length,2);
  }finally{for(const k of Object.keys(globals)){if(previous[k])Object.defineProperty(globalThis,k,previous[k]);else delete globalThis[k];}}
});
