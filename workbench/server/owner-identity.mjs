/** Trusted Sites owner bootstrap and comparison.
 * Raw oai-authenticated-user-id never leaves the Worker. Preferred production
 * configuration stores only an HMAC fingerprint derived with the existing
 * hosted GitHub token. Legacy raw owner-id config remains temporarily accepted
 * for rollback compatibility but is not required by the new adoption path.
 */
export const OWNER_BOOTSTRAP_PATH='/api/owner-fingerprint';
export const SITE_ORIGIN='https://decision-kernel-progress.a278038654.chatgpt.site';
const HASH=/^[a-f0-9]{64}$/;
const encoder=new TextEncoder();
const reply=(status,data)=>new Response(JSON.stringify(data),{status,headers:{
  'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',
  'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'
}});
const validIdentity=value=>typeof value==='string'&&value.length>0&&value.length<=240&&!/[\r\n\0]/.test(value);
const validToken=value=>typeof value==='string'&&value.length>0&&value.length<=4096&&!/[\r\n]/.test(value);

export async function ownerFingerprint(identity,token){
  if(!validIdentity(identity)||!validToken(token))throw new Error('OWNER_FINGERPRINT_INPUT');
  const key=await crypto.subtle.importKey('raw',encoder.encode(token),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const raw=await crypto.subtle.sign('HMAC',key,encoder.encode('decision-kernel/owner-fingerprint/v1\n'+identity));
  return [...new Uint8Array(raw)].map(b=>b.toString(16).padStart(2,'0')).join('');
}

/** Returns an env compatible with existing handlers without persisting raw id. */
export async function ownerEnvironment(request,env){
  const legacy=env?.DECISION_KERNEL_OWNER_USER_ID;
  const expected=env?.DECISION_KERNEL_OWNER_FINGERPRINT;
  if(typeof legacy==='string'&&legacy.trim()&&typeof expected==='string'&&expected.trim())
    return {ok:false,response:reply(503,{code:'OWNER_IDENTITY_CONFIG_AMBIGUOUS'})};
  if(typeof legacy==='string'&&legacy.trim())return {ok:true,env};
  if(typeof expected!=='string'||!HASH.test(expected)||!validToken(env?.DECISION_KERNEL_GITHUB_TOKEN))
    return {ok:false,response:reply(503,{code:'OWNER_IDENTITY_NOT_CONFIGURED'})};
  const identity=request.headers.get('oai-authenticated-user-id');
  if(!validIdentity(identity))return {ok:false,response:reply(403,{code:'OWNER_REQUIRED'})};
  let actual;
  try{actual=await ownerFingerprint(identity,env.DECISION_KERNEL_GITHUB_TOKEN);}
  catch{return {ok:false,response:reply(503,{code:'OWNER_IDENTITY_CHECK_UNAVAILABLE'})};}
  if(actual!==expected)return {ok:false,response:reply(403,{code:'OWNER_REQUIRED'})};
  return {ok:true,env:{...env,DECISION_KERNEL_OWNER_USER_ID:identity}};
}

/** One-time owner-only bootstrap. It returns only a keyed fingerprint, never raw id. */
export async function handleOwnerBootstrap(request,env){
  const url=new URL(request.url);
  if(url.pathname!==OWNER_BOOTSTRAP_PATH)return null;
  if(url.origin!==SITE_ORIGIN||url.search)return reply(403,{code:'WRONG_ORIGIN'});
  if(request.method!=='GET')return reply(405,{code:'METHOD_NOT_ALLOWED'});
  if(env?.DECISION_KERNEL_ENABLE_OWNER_BOOTSTRAP!=='1')return reply(503,{code:'OWNER_BOOTSTRAP_DISABLED'});
  if((typeof env?.DECISION_KERNEL_OWNER_USER_ID==='string'&&env.DECISION_KERNEL_OWNER_USER_ID.trim())||
     (typeof env?.DECISION_KERNEL_OWNER_FINGERPRINT==='string'&&env.DECISION_KERNEL_OWNER_FINGERPRINT.trim()))
    return reply(409,{code:'OWNER_ALREADY_CONFIGURED'});
  if(!validToken(env?.DECISION_KERNEL_GITHUB_TOKEN))return reply(503,{code:'OWNER_BOOTSTRAP_NOT_CONFIGURED'});
  const identity=request.headers.get('oai-authenticated-user-id');
  if(!validIdentity(identity))return reply(403,{code:'OWNER_REQUIRED'});
  const origin=request.headers.get('origin');
  if(origin&&origin!==SITE_ORIGIN)return reply(403,{code:'WRONG_ORIGIN'});
  const fetchSite=request.headers.get('sec-fetch-site');
  if(fetchSite&&!['same-origin','none'].includes(fetchSite))return reply(403,{code:'SAME_ORIGIN_REQUIRED'});
  try{
    return reply(200,{kind:'owner_fingerprint',fingerprint:await ownerFingerprint(identity,env.DECISION_KERNEL_GITHUB_TOKEN)});
  }catch{return reply(503,{code:'OWNER_BOOTSTRAP_UNAVAILABLE'});}
}
