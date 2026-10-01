/** Exact latest News read cache. No polling, source acquisition, Research or write. */
import {REPO,NEWS_LIVE_REF,commit,safePath,fileUrl} from './reading.mjs';

export const NEWS_LIVE_PATH='/api/read-model/news-live';
const RAW=`https://raw.githubusercontent.com/${REPO}`;
const LIMIT=2*1024*1024;
const SHA=/^[0-9a-f]{40}$/, HASH=/^[0-9a-f]{64}$/;
const SOURCES=['cls','wallstreetcn','fastbull','jin10','mktnews','gelonghui','thepaper'];
const AUTHORITY=['signal_transition_authority','human_attention_authority','research_authority','investment_authority'];
const decoder=new TextDecoder('utf-8',{fatal:true});
const validClock=v=>typeof v==='string'&&/(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v));
const require=(ok,reason)=>{if(!ok)throw new Error(reason);};
const escaped=path=>safePath(path).split('/').map(encodeURIComponent).join('/');
function freeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.freeze(value);Object.values(value).forEach(freeze);}return value;}
async function bounded(url,fetcher,limit=LIMIT,request={}){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try{
    const response=await fetcher(url,{method:'GET',credentials:request.credentials||'omit',redirect:'error',
      referrerPolicy:'no-referrer',cache:'no-store',signal:controller.signal,
      ...(request.headers?{headers:request.headers}:{})});
    require(response.ok,`HTTP_${response.status}`);
    const declared=response.headers.get('content-length');
    require(declared===null||/^\d+$/.test(declared)&&Number(declared)<=limit,'RESPONSE_TOO_LARGE');
    require(response.body,'EMPTY_RESPONSE');
    const reader=response.body.getReader(),parts=[];let size=0;
    try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;
      require(size<=limit,'RESPONSE_TOO_LARGE');parts.push(value);}}
    catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
    const raw=new Uint8Array(size);let at=0;for(const part of parts){raw.set(part,at);at+=part.length;}return raw;
  }finally{clearTimeout(timer);}
}
async function json(url,fetcher,limit,request){return JSON.parse(decoder.decode(await bounded(url,fetcher,limit,request)));}
async function digest(raw){require(typeof globalThis.crypto?.subtle?.digest==='function','WEB_CRYPTO_UNAVAILABLE');
  return Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',raw)),b=>b.toString(16).padStart(2,'0')).join('');}
function authority(value){return AUTHORITY.every(k=>value?.[k]==='NONE')&&value?.automatic_admission===false&&
  value?.model_calls===0&&value?.market_requests===0&&value?.new_attention_events===0&&value?.research_executions===0;}
export function validateLiveManifest(value,ref){
  const p=value?.projection;
  require(value&&typeof value==='object'&&HASH.test(value.projection_hash||'')&&p&&typeof p==='object','NEWS_LIVE_MANIFEST_INVALID');
  require(p.version==='news-live-reading-v1'&&p.entry_ref===NEWS_LIVE_REF&&p.code_commit&&SHA.test(p.code_commit)&&
    p.source_workflow==='.github/workflows/radar-newsnow-daily.yml'&&authority(p)&&
    p.complete_news_coverage===false&&
    p.semantics==='LATEST_VERIFIED_NEWS_CAPTURE_AND_ROLLING_INDEX_NOT_RESEARCH_OR_COMPLETE_NEWS'&&
    p.cache_meaning==='LATEST_ONLY_FORCE_UPDATED_DELIVERY_CACHE_NOT_SOURCE_ARCHIVE','NEWS_LIVE_SCOPE_MISMATCH');
  require(validClock(p.published_at)&&validClock(p.captured_from)&&validClock(p.captured_through)&&
    Date.parse(p.captured_from)<=Date.parse(p.captured_through)&&Date.parse(p.captured_through)<=Date.parse(p.published_at),
    'NEWS_LIVE_CLOCK_MISMATCH');
  const run=p.source_run;
  require(run&&Number.isSafeInteger(run.run_id)&&run.run_id>0&&run.attempt===1&&
    ['schedule','workflow_dispatch','workflow_run'].includes(run.event)&&
    (run.event==='workflow_run'?Number.isSafeInteger(run.trigger_run_id)&&run.trigger_run_id>0:run.trigger_run_id===null),
    'NEWS_LIVE_RUN_MISMATCH');
  require(Array.isArray(p.source_outcomes)&&p.source_outcomes.length===SOURCES.length&&
    p.source_outcomes.every((o,i)=>o?.source_id===SOURCES[i]&&typeof o.status==='string'),'NEWS_LIVE_SOURCE_MISMATCH');
  const h=p.history;
  require(h?.read_path==='history.json'&&Number.isSafeInteger(h.bytes)&&h.bytes>0&&h.bytes<=LIMIT&&
    HASH.test(h.sha256||'')&&/^[0-9a-f]{40}$/.test(h.git_blob||''),'NEWS_LIVE_HISTORY_DESCRIPTOR');
  require(p.rolling?.coverage?.complete_news_coverage===false&&validClock(p.rolling.window_start)&&
    validClock(p.rolling.retained_since)&&typeof p.rolling.status==='string','NEWS_LIVE_ROLLING_MISMATCH');
  commit(ref);return p;
}
export function validateLiveHistory(value,manifest){
  const p=value?.projection;
  require(value&&typeof value==='object'&&HASH.test(value.projection_hash||'')&&p?.version==='native-newsnow-rolling-v2'&&
    p.window_hours===18&&p.semantics==='CAPTURE_FIRST_SEEN_ROLLING_INDEX_NOT_PUBLISHER_TIME_OR_COMPLETE_NEWS'&&authority(p),
    'NEWS_LIVE_HISTORY_SCOPE');
  require(p.generated_at===manifest.captured_through&&p.window_start===manifest.rolling.window_start&&
    p.retained_since===manifest.rolling.retained_since&&p.status===manifest.rolling.status,'NEWS_LIVE_HISTORY_BINDING');
  require(Array.isArray(p.captures)&&p.captures.length>0&&p.captures.length<=120&&Array.isArray(p.observations)&&
    p.observations.length<=2000&&Array.isArray(p.losses)&&p.losses.length<=120,'NEWS_LIVE_HISTORY_BOUNDS');
  require(p.coverage?.complete_news_coverage===false&&p.coverage.capture_count===p.captures.length&&
    p.coverage.observation_count===p.observations.length,'NEWS_LIVE_HISTORY_COVERAGE');
  const tail=p.captures.at(-1);
  require(tail?.run_id===manifest.source_run.run_id&&tail.code_commit===manifest.code_commit&&
    tail.capture_hash===manifest.capture_hash&&tail.status===manifest.capture_status,'NEWS_LIVE_HISTORY_TAIL');
  const ids=new Set();
  for(const entry of p.observations){
    const row=entry?.observation;
    require(row&&HASH.test(row.article_id||'')&&HASH.test(row.version_id||'')&&!ids.has(row.version_id)&&
      SOURCES.includes(row.source_id)&&typeof row.title==='string'&&row.title.trim()&&
      validClock(row.fetched_at)&&validClock(entry.first_seen_at)&&validClock(entry.last_seen_at)&&
      Date.parse(entry.first_seen_at)<=Date.parse(entry.last_seen_at)&&Date.parse(entry.last_seen_at)<=Date.parse(p.generated_at)&&
      row.qualification==='CONTEXT_ONLY'&&row.business_linkage==='NOT_ESTABLISHED'&&row.question_status==='NOT_FORMED',
      'NEWS_LIVE_OBSERVATION_INVALID');
    ids.add(row.version_id);
  }
  return p;
}
export async function openLiveNews(fetcher=globalThis.fetch,endpoint=NEWS_LIVE_PATH){
  require(endpoint===NEWS_LIVE_PATH,'UNSUPPORTED_NEWS_LIVE_ENDPOINT');
  const pointer=await json(endpoint,fetcher,8192,{credentials:'same-origin',headers:{'X-Decision-Kernel-Intent':'news-live-ref'}});
  require(pointer?.ref===NEWS_LIVE_REF,'WRONG_NEWS_LIVE_REF');
  const ref=commit(pointer.commit);
  const report=await json(`${RAW}/${ref}/news-live.json`,fetcher,192*1024);
  const manifest=validateLiveManifest(report,ref),d=manifest.history;
  const raw=await bounded(`${RAW}/${ref}/${escaped(d.read_path)}`,fetcher,LIMIT);
  require(raw.byteLength===d.bytes&&await digest(raw)===d.sha256,'NEWS_LIVE_HISTORY_INTEGRITY');
  const history=JSON.parse(decoder.decode(raw));validateLiveHistory(history,manifest);
  return freeze({ref,manifest,history,checkedAt:new Date().toISOString(),
    historyUrl:fileUrl(ref,d.read_path),validation:'PINNED_NEWS_LIVE_MANIFEST_AND_HISTORY_BYTES_SHA256_MATCH'});
}
export function liveNewsView(live,now=Date.now()){
  const p=validateLiveHistory(live.history,live.manifest),rows=[];
  for(const entry of p.observations){
    const row=entry.observation;
    const claims=Object.values(row.publication_claims||{}).filter(v=>
      v?.status==='PARSED_CLAIM_NOT_PUBLISHER_VERIFIED'&&validClock(v.parsed_at));
    const times=[...new Set(claims.map(v=>v.parsed_at))];
    rows.push({id:row.version_id,title:row.title,source:row.source_id,url:row.url,
      firstSeen:entry.first_seen_at,lastSeen:entry.last_seen_at,publishedClaims:times,original:row});
  }
  rows.sort((a,b)=>Date.parse(b.firstSeen)-Date.parse(a.firstSeen)||a.id.localeCompare(b.id));
  const age=Math.max(0,Math.floor((now-Date.parse(live.manifest.captured_through))/1000));
  return {rows,captured:live.manifest.captured_through,publishedAt:live.manifest.published_at,
    ageSeconds:age,stale:age>1800,status:p.status,windowStart:p.window_start,retainedSince:p.retained_since,
    coverage:p.coverage,losses:p.losses};
}
export function liveNewsResume(live,row){
  require(commit(live?.ref)&&HASH.test(row?.id||''),'NEWS_LIVE_RESUME_IDENTITY');
  const d=live.manifest.history;safePath(d.read_path);
  return '请按当前项目研究入口，对这条滚动新闻开展 Quick。先从精确 News live R 恢复该版本，再按正常 Research/registry 查适用旧研究；标题不是事实认证，原因不明保留 UNKNOWN。\n'+
    '复制本身没有启动研究；不得自动 Full、重算 Odds、接受研究或交易。\n\n'+
    `news-live R: ${live.ref}\nread_path: ${d.read_path}\nsha256: ${d.sha256}\nobservation_id: ${row.id}\n`;
}
