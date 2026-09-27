/** Route module for the existing Sites Worker. Not a standalone new host.
 * Mount only behind the verified Sites identity edge; never expose a direct Worker URL.
 * Non-Inbox paths return null so the real host retains its original static fallback.
 */
import {REPO, openPinnedReading, readInboxComments, safePath, commit} from '../reading.mjs';
import {INBOX, MARKER, selection, resolveSelection, contextValue, digest, inboxView, recordBody} from '../quick-inbox.mjs';
export const SITE_ORIGIN='https://decision-kernel-progress.a278038654.chatgpt.site';
const API=`https://api.github.com/repos/${REPO}`;
const ROOT=`${API}/issues/${INBOX}`;
const OWNER=83357964;
const json=(status,value)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'}});
const keys=(value,names)=>value && typeof value==='object' && !Array.isArray(value) && Object.keys(value).length===names.length && names.every(k=>Object.hasOwn(value,k));
async function smallBody(request, limit=8192) {
  if(Number(request.headers.get('content-length'))>limit) throw new Error('BODY_TOO_LARGE');
  if(!request.body) throw new Error('EMPTY_BODY');
  const reader=request.body.getReader(),parts=[];let size=0,timer;
  const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error('BODY_TIMEOUT')),10000);});
  try { while(true) {const {value,done}=await Promise.race([reader.read(),deadline]);if(done)break;size+=value.length;if(size>limit)throw new Error('BODY_TOO_LARGE');parts.push(value);} }
  catch(e){await reader.cancel().catch(()=>{});throw e;} finally{clearTimeout(timer);reader.releaseLock();}
  const bytes=new Uint8Array(size);let p=0;for(const part of parts){bytes.set(part,p);p+=part.length;}
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}
/** Only this one repository/Issue receives this scoped PAT. It is never sent to raw source URLs. */
function authenticatedRead(fetcher,token) {
  return (url,options={})=>{
    const text=String(url);
    const permitted=text===ROOT || /^\/comments\?per_page=100&page=[1-5]$/.test(text.slice(ROOT.length)) && text.startsWith(ROOT);
    if(!permitted || options.method && options.method!=='GET') throw new Error('OUTSIDE_INBOX_READ');
    return fetcher(url,{...options,headers:{Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'decision-kernel-workbench',Authorization:`Bearer ${token}`}});
  };
}
/** Exact-R source validation for writes uses authenticated Contents reads.
 * The browser cannot choose repo/ref/path here: openPinnedReading generates the
 * raw URL, this adapter accepts only this repository and a 40-hex commit.
 */
function authenticatedOriginalRead(fetcher,token) {
  const rawOrigin='https://raw.githubusercontent.com', prefix=`/${REPO}/`;
  return async (url,options={})=>{
    const u=new URL(String(url));
    if(u.origin!==rawOrigin || !u.pathname.startsWith(prefix) || u.search || u.hash ||
      options.method && options.method!=='GET') throw new Error('OUTSIDE_PINNED_READING');
    const rest=u.pathname.slice(prefix.length), slash=rest.indexOf('/');
    if(slash<=0) throw new Error('OUTSIDE_PINNED_READING');
    const ref=commit(rest.slice(0,slash));
    let path;
    try { path=safePath(rest.slice(slash+1).split('/').map(decodeURIComponent).join('/')); }
    catch { throw new Error('OUTSIDE_PINNED_READING'); }
    const encoded=path.split('/').map(encodeURIComponent).join('/');
    const response=await fetcher(`${API}/contents/${encoded}?ref=${ref}`,{
      method:'GET',redirect:'error',credentials:'omit',cache:'no-store',signal:options.signal,
      headers:{Accept:'application/vnd.github.raw+json','X-GitHub-Api-Version':'2022-11-28',
        'User-Agent':'decision-kernel-workbench',Authorization:`Bearer ${token}`}
    });
    if(response.status===403){
      const code=response.headers.get('x-ratelimit-remaining')==='0'?'GITHUB_CONTENTS_RATE_LIMITED':'GITHUB_CONTENTS_READ_FORBIDDEN';
      throw new Error(code);
    }
    return response;
  };
}
async function append(body,token,fetcher) {
  let response;
  try {
    response=await fetcher(`${ROOT}/comments`,{method:'POST',redirect:'error',credentials:'omit',signal:AbortSignal.timeout(15000),
      headers:{'Content-Type':'application/json',Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'decision-kernel-workbench',Authorization:`Bearer ${token}`},body:JSON.stringify({body})});
  } catch {return json(202,{saved:false,uncertain:true,code:'SAVE_UNCONFIRMED_READ_INBOX_FIRST'});}
  if([401,403,404,422].includes(response.status))return json(502,{saved:false,code:'GITHUB_WRITE_REJECTED'});
  if(response.status!==201)return json(202,{saved:false,uncertain:true,code:'SAVE_UNCONFIRMED_READ_INBOX_FIRST'});
  try {
    const created=await smallJSON(response);
    if(!Number.isSafeInteger(created.id)||created.id<=0)throw new Error('IDENTITY');
    const exact=await fetcher(`${API}/issues/comments/${created.id}`,{method:'GET',redirect:'error',credentials:'omit',signal:AbortSignal.timeout(15000),
      headers:{Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'decision-kernel-workbench',Authorization:`Bearer ${token}`}});
    if(!exact.ok)throw new Error('READBACK');
    const c=await smallJSON(exact);
    if(c.id!==created.id || c.body!==body || c.user?.id!==OWNER || c.created_at!==c.updated_at ||
      c.issue_url!==ROOT || c.html_url!==`https://github.com/${REPO}/issues/${INBOX}#issuecomment-${c.id}`)throw new Error('READBACK');
    return json(201,{saved:true,comment_id:c.id,url:c.html_url});
  }catch{return json(202,{saved:false,uncertain:true,code:'SAVE_UNCONFIRMED_READ_INBOX_FIRST'});}
}
async function smallJSON(response){return smallBody(new Request('https://local.invalid',{method:'POST',body:response.body,duplex:'half',headers:response.headers}),65536);}

export async function handleQuickInbox(request,env,options={}) {
  const url=new URL(request.url);
  if(url.pathname!=='/api/quick-inbox')return url.pathname.startsWith('/api/') ? json(404,{saved:false,code:'UNKNOWN_API'}) : null;
  if(url.origin!==SITE_ORIGIN || url.search)return json(403,{saved:false,code:'WRONG_ORIGIN'});
  if(!['GET','POST'].includes(request.method))return json(405,{saved:false,code:'METHOD_NOT_ALLOWED'});
  const owner=env?.DECISION_KERNEL_OWNER_USER_ID;
  if(typeof owner!=='string'||!owner.trim()||owner.length>240||env.DECISION_KERNEL_ENABLE_INBOX!=='1')return json(503,{saved:false,code:'INBOX_NOT_CONFIGURED'});
  // Requires Sites to strip caller-supplied identity headers at its edge. Check this on the real host before enablement.
  const identity=request.headers.get('oai-authenticated-user-id');
  if(!identity||identity!==owner)return json(403,{saved:false,code:'OWNER_REQUIRED'});
  if(request.headers.has('origin') && request.headers.get('origin')!==SITE_ORIGIN)return json(403,{saved:false,code:'WRONG_ORIGIN'});
  const token=env.DECISION_KERNEL_GITHUB_TOKEN;
  if(typeof token!=='string'||!token)return json(503,{saved:false,code:'INBOX_NOT_CONFIGURED'});
  if(request.method==='POST' && (request.headers.get('origin')!==SITE_ORIGIN ||
    request.headers.get('x-decision-kernel-intent')!=='quick-inbox' ||
    !/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(request.headers.get('content-type')||'') ||
    (request.headers.has('sec-fetch-site') && request.headers.get('sec-fetch-site')!=='same-origin')))return json(403,{saved:false,code:'SAME_ORIGIN_JSON_REQUIRED'});
  const fetcher=options.fetcher||globalThis.fetch;
  let input;
  if(request.method==='POST') {
    try {
      input=await smallBody(request);
      if(input.action==='add') {
        if(!keys(input,['action','nonce','selection']))throw new Error('SHAPE');
        selection(input.selection);
        if(!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(input.nonce))throw new Error('NONCE');
      } else if(input.action==='remove') {
        if(!keys(input,['action','requests']))throw new Error('SHAPE');
        await recordBody({op:'remove',requests:input.requests});
      } else throw new Error('ACTION');
    }catch{return json(400,{saved:false,code:'INVALID_INBOX_REQUEST'});}
  }
  let view;
  try {
    // The mutation only needs request/withdrawal history. Do not download all Research bodies to append a locator.
    view=await inboxView(await readInboxComments(authenticatedRead(fetcher,token)),async()=>{throw new Error('NOT_CHECKED_HERE');});
  }catch{return json(503,{saved:false,code:'INBOX_READ_INCOMPLETE'});}
  if(request.method==='GET')return json(200,{available:true,comments:view.comments,observedAt:view.observedAt});
  if(input.action==='remove') {
    const adds=new Set(view.records.filter(r=>r.value.op==='add').map(r=>r.comment.id));
    if(!input.requests.every(id=>adds.has(id)))return json(409,{saved:false,code:'REQUEST_NO_LONGER_MATCHES'});
    if(input.requests.every(id=>view.removed.some(r=>r.requests.includes(id))))return json(200,{saved:true,reused:true});
    return append(await recordBody({op:'remove',requests:input.requests}),token,fetcher);
  }
  const replay=view.records.filter(r=>r.value.op==='add' && r.value.nonce===input.nonce);
  if(replay.length) {
    if(replay.some(r=>JSON.stringify(r.value.context.selection)!==JSON.stringify(selection(input.selection))))return json(409,{saved:false,code:'NONCE_CONTEXT_CONFLICT'});
    return json(200,{saved:true,reused:true,comment_id:replay[0].comment.id,url:replay[0].comment.html_url});
  }
  let context;
  try {
    const open=options.openReading || (ref=>openPinnedReading(ref,authenticatedOriginalRead(fetcher,token)));
    context=await resolveSelection(input.selection,open);
  } catch(error) {
    if(['GITHUB_CONTENTS_RATE_LIMITED','GITHUB_CONTENTS_READ_FORBIDDEN'].includes(error?.message))
      return json(503,{saved:false,code:error.message});
    return json(422,{saved:false,code:'ORIGINAL_CONTEXT_UNAVAILABLE'});
  }
  const key=await digest(JSON.stringify(contextValue(context))), prior=view.pending.find(r=>r.key===key);
  // A result receipt, even not yet byte-checked here, must not be mistaken for a fresh pending duplicate.
  if(prior && !prior.results.length)return json(200,{saved:true,reused:true,comment_id:prior.id,url:prior.url});
  return append(await recordBody({op:'add',nonce:input.nonce,context}),token,fetcher);
}
