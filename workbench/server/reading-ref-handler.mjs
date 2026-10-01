/** Resolve only the fixed read-model pointer for the owner-only Site.
 * The hosted token never leaves the Worker; this is not a generic GitHub proxy.
 */
import {REPO, READ_REF, NEWS_LIVE_REF} from '../reading.mjs';

export const READING_REF_PATH='/api/read-model/current-state';
export const NEWS_LIVE_REF_PATH='/api/read-model/news-live';
export const SITE_ORIGIN='https://decision-kernel-progress.a278038654.chatgpt.site';
const API=`https://api.github.com/repos/${REPO}`;
const SHA=/^[a-f0-9]{40}$/;
const reply=(status,data)=>new Response(JSON.stringify(data),{status,headers:{
  'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',
  'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'
}});

async function smallJSON(response,limit=8192){
  const type=response.headers.get('content-type')||'';
  if(!/^application\/json(?:\s*;|$)/i.test(type))throw new Error('NON_JSON');
  const length=response.headers.get('content-length');
  if(length!==null&&(!/^\d+$/.test(length)||Number(length)>limit))throw new Error('TOO_LARGE');
  if(!response.body)throw new Error('EMPTY');
  const reader=response.body.getReader(),parts=[];let size=0,timer;
  const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('TIMEOUT')),10000);});
  try{
    while(true){const {value,done}=await Promise.race([reader.read(),deadline]);if(done)break;
      size+=value.byteLength;if(size>limit)throw new Error('TOO_LARGE');parts.push(value);}
  }catch(e){await reader.cancel().catch(()=>{});throw e;}finally{clearTimeout(timer);reader.releaseLock();}
  const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.byteLength;}
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}

export async function handleReadingRef(request,env,options={}){
  const url=new URL(request.url);
  const target=url.pathname===READING_REF_PATH ? {ref:READ_REF,intent:'read-model-ref'} :
    url.pathname===NEWS_LIVE_REF_PATH ? {ref:NEWS_LIVE_REF,intent:'news-live-ref'} : null;
  if(!target)return null;
  if(url.origin!==SITE_ORIGIN||url.search)return reply(403,{code:'WRONG_ORIGIN'});
  if(request.method!=='GET')return reply(405,{code:'METHOD_NOT_ALLOWED'});
  if(request.headers.get('x-decision-kernel-intent')!==target.intent ||
     request.headers.has('origin')&&request.headers.get('origin')!==SITE_ORIGIN ||
     request.headers.has('sec-fetch-site')&&request.headers.get('sec-fetch-site')!=='same-origin')
    return reply(403,{code:'SAME_ORIGIN_REQUIRED'});
  const token=env?.DECISION_KERNEL_GITHUB_TOKEN;
  if(typeof token!=='string'||!token||/[\r\n]/.test(token))return reply(503,{code:'READ_REF_NOT_CONFIGURED'});
  const fetcher=options.fetcher||globalThis.fetch;
  let response;
  try{
    response=await fetcher(`${API}/git/ref/heads/${target.ref}`,{method:'GET',redirect:'error',credentials:'omit',
      cache:'no-store',signal:AbortSignal.timeout(15000),headers:{Accept:'application/vnd.github+json',
        'X-GitHub-Api-Version':'2022-11-28','User-Agent':'decision-kernel-workbench',
        Authorization:`Bearer ${token}`}});
  }catch{return reply(503,{code:'READ_REF_UNAVAILABLE'});}
  if(response.status===403){
    const code=response.headers.get('x-ratelimit-remaining')==='0'?'GITHUB_CONTENTS_RATE_LIMITED':'GITHUB_CONTENTS_READ_FORBIDDEN';
    return reply(503,{code});
  }
  if(!response.ok)return reply(503,{code:'READ_REF_UNAVAILABLE'});
  try{
    const data=await smallJSON(response);
    if(data?.ref!==`refs/heads/${target.ref}`||data.object?.type!=='commit'||!SHA.test(data.object.sha||''))
      return reply(503,{code:'READ_REF_IDENTITY_UNCONFIRMED'});
    return reply(200,{ref:target.ref,commit:data.object.sha});
  }catch{return reply(503,{code:'READ_REF_IDENTITY_UNCONFIRMED'});}
}
