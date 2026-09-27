/** Identity bootstrap only; no live Sites/GitHub access. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';
import {OWNER_BOOTSTRAP_PATH,SITE_ORIGIN,ownerFingerprint,ownerEnvironment,handleOwnerBootstrap} from './server/owner-identity.mjs';
import {handleWorkbenchAPI} from './server/routes.mjs';

const raw='opaque-runtime-owner-id';
const token='synthetic-test-token';
const expected=createHmac('sha256',token).update('decision-kernel/owner-fingerprint/v1\n'+raw).digest('hex');
const req=(headers={},url=SITE_ORIGIN+OWNER_BOOTSTRAP_PATH,method='GET')=>new Request(url,{method,headers:{'oai-authenticated-user-id':raw,...headers}});

test('fingerprint is deterministic HMAC and never the raw identity',async()=>{
  const value=await ownerFingerprint(raw,token);
  assert.equal(value,expected);assert.match(value,/^[a-f0-9]{64}$/);assert.ok(!value.includes(raw));
});
test('bootstrap returns only fingerprint when explicitly enabled',async()=>{
  const res=await handleOwnerBootstrap(req({'Sec-Fetch-Site':'none'}),{DECISION_KERNEL_ENABLE_OWNER_BOOTSTRAP:'1',DECISION_KERNEL_GITHUB_TOKEN:token});
  assert.equal(res.status,200);const body=await res.json();assert.equal(body.fingerprint,expected);
  assert.ok(!JSON.stringify(body).includes(raw));assert.ok(!JSON.stringify(body).includes(token));
});
test('bootstrap fails closed on disabled, missing identity, cross-site or existing config',async()=>{
  let r=await handleOwnerBootstrap(req(),{DECISION_KERNEL_GITHUB_TOKEN:token});assert.equal(r.status,503);
  r=await handleOwnerBootstrap(new Request(SITE_ORIGIN+OWNER_BOOTSTRAP_PATH),{DECISION_KERNEL_ENABLE_OWNER_BOOTSTRAP:'1',DECISION_KERNEL_GITHUB_TOKEN:token});assert.equal(r.status,403);
  r=await handleOwnerBootstrap(req({'Sec-Fetch-Site':'cross-site'}),{DECISION_KERNEL_ENABLE_OWNER_BOOTSTRAP:'1',DECISION_KERNEL_GITHUB_TOKEN:token});assert.equal(r.status,403);
  r=await handleOwnerBootstrap(req(),{DECISION_KERNEL_ENABLE_OWNER_BOOTSTRAP:'1',DECISION_KERNEL_GITHUB_TOKEN:token,DECISION_KERNEL_OWNER_FINGERPRINT:expected});assert.equal(r.status,409);
});
test('preferred owner config compares fingerprint and injects raw id only in-memory',async()=>{
  let result=await ownerEnvironment(req(),{DECISION_KERNEL_OWNER_FINGERPRINT:expected,DECISION_KERNEL_GITHUB_TOKEN:token,OTHER:'x'});
  assert.equal(result.ok,true);assert.equal(result.env.DECISION_KERNEL_OWNER_USER_ID,raw);assert.equal(result.env.OTHER,'x');
  result=await ownerEnvironment(req({'oai-authenticated-user-id':'someone-else'}),{DECISION_KERNEL_OWNER_FINGERPRINT:expected,DECISION_KERNEL_GITHUB_TOKEN:token});
  assert.equal(result.ok,false);assert.equal(result.response.status,403);
});
test('missing or ambiguous owner config fails closed; legacy raw config remains rollback-compatible',async()=>{
  let result=await ownerEnvironment(req(),{DECISION_KERNEL_GITHUB_TOKEN:token});assert.equal(result.ok,false);assert.equal(result.response.status,503);
  result=await ownerEnvironment(req(),{DECISION_KERNEL_OWNER_USER_ID:raw,DECISION_KERNEL_OWNER_FINGERPRINT:expected,DECISION_KERNEL_GITHUB_TOKEN:token});
  assert.equal(result.ok,false);assert.equal(result.response.status,503);
  const legacy={DECISION_KERNEL_OWNER_USER_ID:raw,DECISION_KERNEL_GITHUB_TOKEN:token};
  result=await ownerEnvironment(req(),legacy);assert.equal(result.ok,true);assert.equal(result.env,legacy);
});
test('unified router exposes bootstrap JSON, keeps unknown API JSON and static fallback null',async()=>{
  const env={DECISION_KERNEL_ENABLE_OWNER_BOOTSTRAP:'1',DECISION_KERNEL_GITHUB_TOKEN:token};
  let r=await handleWorkbenchAPI(req(),env);assert.equal(r.status,200);assert.equal((await r.json()).fingerprint,expected);
  r=await handleWorkbenchAPI(new Request(SITE_ORIGIN+'/api/nope'),env);assert.equal(r.status,404);assert.match(r.headers.get('content-type'),/application\/json/);
  assert.equal(await handleWorkbenchAPI(new Request(SITE_ORIGIN+'/old-link'),env),null);
});
