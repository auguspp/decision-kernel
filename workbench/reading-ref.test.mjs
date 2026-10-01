import test from 'node:test';
import assert from 'node:assert/strict';
import {handleReadingRef,READING_REF_PATH,NEWS_LIVE_REF_PATH,SITE_ORIGIN} from './server/reading-ref-handler.mjs';
import {READ_REF,NEWS_LIVE_REF,REPO} from './reading.mjs';
const R='a'.repeat(40),token='synthetic-token',API=`https://api.github.com/repos/${REPO}/git/ref/heads/${READ_REF}`;
const env=()=>({DECISION_KERNEL_GITHUB_TOKEN:token});
const request=(headers={},url=SITE_ORIGIN+READING_REF_PATH,method='GET')=>new Request(url,{method,headers:{
  'X-Decision-Kernel-Intent':'read-model-ref','Sec-Fetch-Site':'same-origin',...headers}});
const github=(data={ref:`refs/heads/${READ_REF}`,object:{type:'commit',sha:R}},status=200,headers={})=>
  new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json',...headers}});

test('fixed pointer read uses token server-side and returns only public ref identity',async()=>{
  const calls=[];const fetcher=async(url,options)=>{calls.push({url,options});return github();};
  const res=await handleReadingRef(request(),env(),{fetcher});assert.equal(res.status,200);
  assert.deepEqual(await res.json(),{ref:READ_REF,commit:R});assert.equal(calls.length,1);assert.equal(calls[0].url,API);
  assert.equal(calls[0].options.headers.Authorization,'Bearer '+token);
});
test('route refuses wrong origin/method/intent/cross-site and missing token before GitHub',async()=>{
  let calls=0;const fetcher=async()=>{calls++;return github();};
  for(const [req,e,status] of [
    [request({},SITE_ORIGIN+READING_REF_PATH+'?x=1'),env(),403],
    [request({},SITE_ORIGIN+READING_REF_PATH,'POST'),env(),405],
    [request({'X-Decision-Kernel-Intent':'other'}),env(),403],
    [request({'Sec-Fetch-Site':'cross-site'}),env(),403],
    [request(),{},503]
  ]){const res=await handleReadingRef(req,e,{fetcher});assert.equal(res.status,status);}
  assert.equal(calls,0);
});
test('upstream identity and 403 classes fail closed without leaking body or token',async()=>{
  for(const [response,code] of [
    [github({secret:token},403,{'x-ratelimit-remaining':'0'}),'GITHUB_CONTENTS_RATE_LIMITED'],
    [github({secret:token},403,{'x-ratelimit-remaining':'4999'}),'GITHUB_CONTENTS_READ_FORBIDDEN'],
    [github({ref:'refs/heads/main',object:{type:'commit',sha:R}}), 'READ_REF_IDENTITY_UNCONFIRMED']
  ]){
    const res=await handleReadingRef(request(),env(),{fetcher:async()=>response});
    const body=await res.json();assert.equal(res.status,503);assert.equal(body.code,code);
    assert.ok(!JSON.stringify(body).includes(token));
  }
});
test('non-api path is not claimed by pointer handler',async()=>{
  assert.equal(await handleReadingRef(new Request(SITE_ORIGIN+'/old-link'),env()),null);
});

test('News live pointer is a second exact read-only route, not a generic ref proxy',async()=>{
  const calls=[],api=`https://api.github.com/repos/${REPO}/git/ref/heads/${NEWS_LIVE_REF}`;
  const req=new Request(SITE_ORIGIN+NEWS_LIVE_REF_PATH,{headers:{
    'X-Decision-Kernel-Intent':'news-live-ref','Sec-Fetch-Site':'same-origin'}});
  const fetcher=async(url,options)=>{calls.push({url,options});return github({
    ref:`refs/heads/${NEWS_LIVE_REF}`,object:{type:'commit',sha:R}});};
  const res=await handleReadingRef(req,env(),{fetcher});
  assert.equal(res.status,200);assert.deepEqual(await res.json(),{ref:NEWS_LIVE_REF,commit:R});
  assert.equal(calls[0].url,api);assert.equal(calls[0].options.headers.Authorization,'Bearer '+token);
  const wrong=new Request(SITE_ORIGIN+NEWS_LIVE_REF_PATH,{headers:{
    'X-Decision-Kernel-Intent':'read-model-ref','Sec-Fetch-Site':'same-origin'}});
  assert.equal((await handleReadingRef(wrong,env(),{fetcher})).status,403);
  assert.equal(await handleReadingRef(new Request(SITE_ORIGIN+'/api/read-model/arbitrary'),env(),{fetcher}),null);
});
