import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {NEWS_LIVE_REF} from './reading.mjs';
import {NEWS_LIVE_PATH,openLiveNews,liveNewsView,liveNewsResume} from './news-live.mjs';

const R='d'.repeat(40),H=s=>createHash('sha256').update(s).digest('hex');
const T='2026-10-01T02:50:00Z';
const authority={signal_transition_authority:'NONE',human_attention_authority:'NONE',
  research_authority:'NONE',investment_authority:'NONE',automatic_admission:false,
  model_calls:0,market_requests:0,new_attention_events:0,research_executions:0};
function fixture(){
  const row={source_id:'cls',item_id:'1',url:'https://www.cls.cn/detail/1',title:'TEST_ONLY 美光财报后价格反应有限',
    publication_claims:{pubDate:{raw:'2026-10-01T02:40:00Z',status:'PARSED_CLAIM_NOT_PUBLISHER_VERIFIED',parsed_at:'2026-10-01T02:40:00Z'},
      'extra.date':{raw:null,status:'MISSING',parsed_at:null}},article_id:'a'.repeat(64),version_id:'b'.repeat(64),
    window_position:0,clock_origin:'SERVICE_PASSTHROUGH_NOT_VERIFIED_PUBLISHER_TIME',fetched_at:T,
    business_linkage:'NOT_ESTABLISHED',question_status:'NOT_FORMED',qualification:'CONTEXT_ONLY'};
  const capture={run_id:99,code_commit:'c'.repeat(40),event:'schedule',captured_from:T,captured_through:T,
    capture_hash:'e'.repeat(64),status:'WINDOWS_CAPTURED',
    source_outcomes:['cls','wallstreetcn','fastbull','jin10','mktnews','gelonghui','thepaper'].map(source_id=>({
      source_id,status:'OBSERVATIONS_NORMALIZED',observations_in_window:1}))};
  const coverage={capture_count:1,observation_count:1,dropped_observation_count:0,dropped_capture_count:0,
    loss_count_meaning:'RETAINED_DROP_OPERATIONS_NOT_DISTINCT_ARTICLES',maximum_capture_gap_seconds:0,
    source_gap_capture_count:0,complete_news_coverage:false};
  const history={projection:{version:'native-newsnow-rolling-v2',window_hours:18,generated_at:T,
    window_start:'2026-09-30T08:50:00Z',retained_since:T,captures:[capture],
    observations:[{observation:row,first_seen_at:T,last_seen_at:T,first_seen_run_id:99,last_seen_run_id:99,seen_capture_count:1}],
    losses:[],status:'ROLLING_HISTORY_STARTED',coverage,
    semantics:'CAPTURE_FIRST_SEEN_ROLLING_INDEX_NOT_PUBLISHER_TIME_OR_COMPLETE_NEWS',...authority},
    projection_hash:'f'.repeat(64)};
  const historyText=JSON.stringify(history);
  const manifest={projection:{version:'news-live-reading-v1',entry_ref:NEWS_LIVE_REF,published_at:'2026-10-01T02:51:00Z',
    code_commit:'c'.repeat(40),source_workflow:'.github/workflows/radar-newsnow-daily.yml',
    source_run:{run_id:99,attempt:1,event:'schedule',trigger_run_id:null},capture_hash:'e'.repeat(64),
    captured_from:T,captured_through:T,capture_status:'WINDOWS_CAPTURED',
    source_outcomes:capture.source_outcomes,history:{read_path:'history.json',bytes:Buffer.byteLength(historyText),
      sha256:H(historyText),git_blob:'1'.repeat(40)},rolling:{status:'ROLLING_HISTORY_STARTED',
      window_start:'2026-09-30T08:50:00Z',retained_since:T,coverage},complete_news_coverage:false,
    cache_meaning:'LATEST_ONLY_FORCE_UPDATED_DELIVERY_CACHE_NOT_SOURCE_ARCHIVE',
    semantics:'LATEST_VERIFIED_NEWS_CAPTURE_AND_ROLLING_INDEX_NOT_RESEARCH_OR_COMPLETE_NEWS',...authority},
    projection_hash:'2'.repeat(64)};
  return {history,historyText,manifest};
}
test('live News resolves exact pointer and verifies pinned history bytes',async()=>{
  const f=fixture(),calls=[];
  const fetcher=async(url,options)=>{calls.push({url,options});
    if(url===NEWS_LIVE_PATH)return new Response(JSON.stringify({ref:NEWS_LIVE_REF,commit:R}));
    if(url.endsWith('/news-live.json'))return new Response(JSON.stringify(f.manifest));
    if(url.endsWith('/history.json'))return new Response(f.historyText);
    assert.fail('unexpected '+url);
  };
  const live=await openLiveNews(fetcher);assert.equal(live.ref,R);assert.equal(live.history.projection.observations.length,1);
  assert.equal(calls[0].options.credentials,'same-origin');
  assert.equal(calls[0].options.headers['X-Decision-Kernel-Intent'],'news-live-ref');
});
test('live News exposes capture clocks and gaps without promoting them to publication facts',async()=>{
  const f=fixture(),live={ref:R,manifest:f.manifest.projection,history:f.history};
  const view=liveNewsView(live,Date.parse('2026-10-01T02:55:00Z'));
  assert.equal(view.rows.length,1);assert.equal(view.stale,false);assert.equal(view.rows[0].firstSeen,T);
  assert.deepEqual(view.rows[0].publishedClaims,['2026-10-01T02:40:00Z']);
  const copy=liveNewsResume(live,view.rows[0]);assert.match(copy,/news-live R/);assert.match(copy,/没有启动研究/);
  assert.ok(!copy.includes(view.rows[0].url));
});
test('wrong pointer or altered history fails closed',async()=>{
  const f=fixture();
  await assert.rejects(()=>openLiveNews(async url=>{
    if(url===NEWS_LIVE_PATH)return new Response(JSON.stringify({ref:'read-model/other',commit:R}));
    return new Response('{}');
  }),/WRONG_NEWS_LIVE_REF/);
  await assert.rejects(()=>openLiveNews(async url=>{
    if(url===NEWS_LIVE_PATH)return new Response(JSON.stringify({ref:NEWS_LIVE_REF,commit:R}));
    if(url.endsWith('/news-live.json'))return new Response(JSON.stringify(f.manifest));
    return new Response(f.historyText.replace('TEST_ONLY','FAKE_ONLY'));
  }),/INTEGRITY/);
});
