/** Synthetic consumer checks over retained example bytes; no live source or UI acceptance. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {setTimeout as tick} from 'node:timers/promises';
import {calendarView, calendarPage} from './research-calendar.mjs';
import {openPinnedReading, READ_REF} from './reading.mjs';
const R='a'.repeat(40), M='c'.repeat(40), NOW=new Date('2026-09-28T08:00:00Z');
const auth=Object.fromEntries(['signal_transition_authority','human_attention_authority','research_authority','investment_authority'].map(k=>[k,'NONE']));
const bytes=name=>readFileSync(new URL('../docs/readings/2026-09-28-b2-bls-calendar/'+name,import.meta.url));
const hash=raw=>createHash('sha256').update(raw).digest('hex');
function fixture(){
  const c=JSON.parse(bytes('calendar.json'));
  const files=Object.fromEntries(['source.txt','request.json','calendar.json','calendar.md'].map(name=>{
    const raw=bytes(name), blob=createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${raw.length}\0`),raw])).digest('hex');
    return [name,{read_path:`sources/git/${blob}/${name}`,sha256:hash(raw),bytes:raw.length}];
  }));
  return {c,saved:{...auth,version:'research-calendar-reading-v1',meaning:'SAVED_APPOINTMENTS_NOT_RELEASE_OR_RESEARCH',
    status:'SAVED_REVIEWED_CALENDAR',calendar_hash:c.calendar_hash,as_of:c.as_of,checked_at:NOW.toISOString(),
    event_count:c.events.length,window:{...c.window},coverage:c.coverage,files}};
}
test('retained appointments keep source/local clocks and provenance; passage only adds historical notice',()=>{
  const f=fixture(),before=JSON.stringify(f),v=calendarView(JSON.stringify(f.c),f.saved,NOW);
  assert.equal(v.calendar.events.length,3);assert.equal(v.expired,false);
  assert.equal(v.calendar.events[0].scheduled_at,'2026-10-02T08:30:00-04:00');
  assert.equal(v.calendar.events[0].local_scheduled_at,'2026-10-02T20:30:00+08:00');
  assert.equal(calendarView(JSON.stringify(f.c),f.saved,new Date('2026-11-01T00:00:00Z')).expired,true);
  assert.equal(JSON.stringify(f),before);
});
for(const [label,change] of [
  ['hash',f=>f.saved.calendar_hash='0'.repeat(64)],['authority',f=>f.c.authority.investment='BUY'],
  ['source',f=>f.c.source.url='https://www.bls.gov.evil.test/schedule/2026/10_sched_list.htm'],
  ['synthetic',f=>f.c.source.observation_kind='SYNTHETIC_TEST_ONLY'],['window',f=>f.saved.window.end='2026-10-24'],
  ['count',f=>f.saved.event_count=0],['actual',f=>f.c.events[0].release_observed='RELEASED'],
  ['material',f=>f.c.events[0].release_material_obtained='OBTAINED'],['response',f=>f.c.events[0].human_response='ACCEPTED'],
  ['time',f=>f.c.events[0].local_scheduled_at='2026-10-02T21:30:00+08:00'],
  ['duplicate',f=>f.c.events[1].event_id=f.c.events[0].event_id],['zone',f=>f.c.local_timezone='Not/AZone'],
])test('reject incompatible saved '+label,()=>{const f=fixture();change(f);assert.throws(()=>calendarView(JSON.stringify(f.c),f.saved,NOW));});
test('date-only remains unknown, never midnight; empty scope is not global quiet',()=>{
  const f=fixture();f.c.events[0].time_precision='DATE_ONLY';f.c.events[0].scheduled_at=f.c.events[0].local_scheduled_at='UNKNOWN';
  assert.equal(calendarView(JSON.stringify(f.c),f.saved,NOW).calendar.events[0].local_scheduled_at,'UNKNOWN');
  f.c.events=[];f.saved.event_count=0;f.c.excluded_outside_window=3;f.c.status='NO_SELECTED_EVENTS_IN_WINDOW';
  assert.equal(calendarView(JSON.stringify(f.c),f.saved,NOW).calendar.events.length,0);
});
test('actual Reading verifies selected same-R bytes and rejects equal-length tampering',async()=>{
  const f=fixture(),root={schema_version:1,entry_ref:READ_REF,code_commit:M,reading_hash:'b'.repeat(64),...auth,
    semantics:'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',lanes:{},research:{calendar:f.saved}};
  const calls=[];let corrupt=false;
  const reading=await openPinnedReading(R,async(url,options)=>{
    calls.push(url);assert.equal(options.method,'GET');assert.equal(options.credentials,'omit');assert.equal(options.body,undefined);
    if(url.endsWith('current-state.json'))return new Response(JSON.stringify(root));
    const raw=bytes('calendar.json');return new Response(corrupt?Buffer.from(raw.toString().replace('20:30','21:30')):raw);
  });
  assert.equal(calendarView((await reading.readFile(f.saved.files['calendar.json'])).text,f.saved,NOW).calendar.events.length,3);
  corrupt=true;await assert.rejects(reading.readFile(f.saved.files['calendar.json']),/INTEGRITY/);
  assert.ok(calls.every(url=>url.includes('/'+R+'/')));
});
// Output sink only, not a substitute for real Chromium/viewport evidence.
class Node{constructor(tag,text=''){this.tagName=tag;this.text=text;this.children=[];}append(...c){this.children.push(...c);}replaceChildren(...c){this.text='';this.children=c;}
  get textContent(){return this.text+this.children.map(c=>c.textContent).join('');}setAttribute(k,v){this[k]=v;}}
const el=(tag,text='')=>new Node(tag,text), button=(text,fn)=>Object.assign(el('button',text),{onclick:fn});
const ui={el,button,link:(text,url)=>Object.assign(el('a',text),{href:url}),notice:text=>el('p',text),
  folded:(t,s)=>{const n=el('details');n.append(el('summary',t),el('pre',s));return n;},
  disclosure:(t,...c)=>{const n=el('details');n.append(el('summary',t),...c);return n;},
  card:(t,s)=>{const n=el('section');n.append(el('h3',t),el('p',s));return n;},
  dataTable:(t,h)=>{const wrapper=el('table'),body=el('tbody');wrapper.append(el('caption',t),...h.map(v=>el('th',v)),body);return {wrapper,body};}};
function context(){const f=fixture();return {reading:{ref:R,payload:{research:{calendar:f.saved}},readFile:async()=>({text:JSON.stringify(f.c)})},ui,active:()=>true,onRead:()=>{}};}
test('panel reads saved rows via text sinks, exposes original and keeps legacy absence explicit',async()=>{
  const ctx=context(),root=el('div');calendarPage(root,ctx);await tick(0);
  assert.match(root.textContent,/美国就业报告/);assert.match(root.textContent,/America\/New_York/);assert.match(root.textContent,/Asia\/Singapore/);
  assert.match(root.textContent,/预约；实际发布未检查/);assert.match(root.textContent,/核读摘录/);
  delete ctx.reading.payload.research.calendar;ctx.reading.readFile=()=>assert.fail('absent calendar must not fetch');
  const old=el('div');calendarPage(old,ctx);assert.match(old.textContent,/尚未接入/);
});
test('late success or failure after a different reading cannot alter the active page',async()=>{
  for(const failed of [false,true]){
    const ctx=context(),root=el('div');let finish,active=true;
    ctx.active=()=>active;ctx.reading.readFile=()=>new Promise((res,rej)=>{finish=()=>failed?rej(new Error('HTTP_503')):res({text:JSON.stringify(fixture().c)});});
    calendarPage(root,ctx);active=false;root.replaceChildren(el('p','new reading'));finish();await tick(0);
    assert.equal(root.textContent,'new reading');
  }
});
test('local calendar error preserves independent material and never says zero events',async()=>{
  const ctx=context(),root=el('div');root.append(el('p','independent stock'));ctx.reading.readFile=async()=>{throw new Error('HTTP_503');};
  calendarPage(root,ctx);await tick(0);assert.match(root.textContent,/independent stock/);assert.match(root.textContent,/不把失败当作没有事件/);
});
