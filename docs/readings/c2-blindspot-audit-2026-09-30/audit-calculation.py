"""One-time analysis of exact retained #375 bytes; no detector/source execution.

Run explicitly with original ZIP and absent output directory. Not a scheduled
runtime or replacement archive reader. Output is intentionally lossy analysis.
"""
import hashlib,json,sys,zipfile
from collections import Counter,defaultdict
from pathlib import Path
from decision_kernel.identity import canonical_hash

ZIP_SHA='4a357ef5973439c3bf17e5842a17e879e3ebe5452070e7aea8d2cf2baaaf3fb1'
FILES={'study.json':(31759771,'c59fde0ad9268e3c49ebc62e98b64601266fac15333a64c0becb45371737417e'),
'execution.json':(738,'aa29c3c8e07ca2292011605264d2f6322ef034705deea00a7788615b133d9441'),
'summary.md':(1595,'05e1192fbba85bd8cb2b333c0db1912ba215bafd3e651ffcfd089d6b77b1f684')}
CASES=('881101.TI','881102.TI','881166.TI','884183.TI','881174.TI','881155.TI','881169.TI')
FAMILIES={'BROAD_881':90,'GRANULAR_884':230}
zip_path=Path(sys.argv[1]);out=Path(sys.argv[2]);raw=zip_path.read_bytes()
assert len(raw)==4042845 and hashlib.sha256(raw).hexdigest()==ZIP_SHA
with zipfile.ZipFile(zip_path) as z:
 assert sorted(z.namelist())==sorted(FILES) and z.testzip() is None
 blobs={name:z.read(name) for name in FILES}
for name,(size,digest) in FILES.items():
 assert len(blobs[name])==size and hashlib.sha256(blobs[name]).hexdigest()==digest
wrapper=json.loads(blobs['study.json']);s=wrapper['study'];e=json.loads(blobs['execution.json'])
assert canonical_hash(s)==wrapper['study_hash']=='bbe1500b75db1b73254fac2d074ba96a9de65e5ef9b69603eacc7bbf4afd62a6'
assert canonical_hash({k:v for k,v in e.items() if k!='receipt_hash'})==e['receipt_hash']
assert e['study_hash']==wrapper['study_hash'] and e['workflow_run_id']==35070558913 and e['workflow_run_attempt']==1
assert s['source_state_hash']==e['expected_state_hash'] and s['source_state_session']==e['expected_market_session']
assert e['provider_requests']==e['market_state_writes']==0
for key in ['research_authority','investment_authority','human_attention_authority']:
 assert e[key]==s[key]=='NONE'
assert s['signal_transition_authority']=='NONE' and s['horizons']==[5,20,60]
rows=s['rows'];assert len(rows)==s['row_count']==21120
keys={(r['family'],r['signal_session'],r['thscode']) for r in rows};assert len(keys)==len(rows)
sessions=sorted({r['signal_session'] for r in rows});assert len(sessions)==s['signal_session_count']==66
assert sessions[0]==s['first_signal_session'] and sessions[-1]==s['last_signal_session']
group=defaultdict(list)
for r in rows:
 assert r['family'] in FAMILIES and type(r['radar_selected']) is bool and type(r['baseline_selected']) is bool
 assert set(r['outcomes'])=={'5','20','60'}
 for o in r['outcomes'].values():
  assert o['status'] in {'EVALUATED','PENDING_HORIZON'}
  assert (o['metrics'] is None)==(o['status']=='PENDING_HORIZON')
  assert (o['target_session'] is None)==(o['status']=='PENDING_HORIZON')
 group[(r['family'],r['signal_session'])].append(r)
assert len(group)==132
census=[]
for family,size in FAMILIES.items():
 universes=[]
 for day in sessions:
  rr=group[(family,day)];assert len(rr)==size;universes.append({r['thscode'] for r in rr})
  partition=Counter('BOTH' if r['radar_selected'] and r['baseline_selected'] else
   'RADAR_ONLY' if r['radar_selected'] else 'BASELINE_ONLY' if r['baseline_selected'] else 'NEITHER' for r in rr)
  assert sum(partition.values())==size
  for h in ['5','20','60']:
   count={'family':family,'session':day,'horizon':int(h),'universe':size,
          'partition':{k:partition[k] for k in ['BOTH','RADAR_ONLY','BASELINE_ONLY','NEITHER']}}
   for name,choose in [('all',lambda r:True),('radar',lambda r:r['radar_selected']),('baseline',lambda r:r['baseline_selected'])]:
    cohort=[r for r in rr if choose(r)];n=sum(r['outcomes'][h]['status']=='EVALUATED' for r in cohort)
    count[name]={'selected':len(cohort),'evaluated':n,'pending':len(cohort)-n}
   census.append(count)
 assert all(x==universes[0] for x in universes) # Fixed observed universe, not proven historical effective catalog.
summary={}
for fam in FAMILIES:
 summary[fam]={}
 for h in ['5','20','60']:
  cells=[x for x in census if x['family']==fam and x['horizon']==int(h)]
  agg={n:{k:sum(x[n][k] for x in cells) for k in ['selected','evaluated','pending']} for n in ['all','radar','baseline']}
  agg['partition']={k:sum(x['partition'][k] for x in cells) for k in ['BOTH','RADAR_ONLY','BASELINE_ONLY','NEITHER']}
  for n in ['radar','baseline']:
   for k in ['selected','evaluated','pending']:assert agg[n][k]==s['summary'][fam][h][n][k+'_count']
  assert agg['partition']['BOTH']==s['summary'][fam][h]['radar_baseline_overlap_count']
  summary[fam][h]=agg
cases=[]
for code in CASES:
 rr=sorted([r for r in rows if r['thscode']==code],key=lambda r:r['signal_session'])
 assert len(rr)==66 and [r['signal_session'] for r in rr]==sessions
 for r in rr:
  cases.append({k:r[k] for k in ['family','thscode','name','signal_session','radar_selected','radar_event_type','baseline_selected','signal_features']} |
   {'outcomes':{h:{'status':o['status'],'target_session':o['target_session'],'excess_return':o['metrics']['excess_return'] if o['metrics'] else None} for h,o in r['outcomes'].items()}})
control=next(r for r in cases if r['thscode']=='884183.TI' and r['signal_session']=='2026-07-10')
assert control['baseline_selected'] and not control['radar_selected']
assert control['signal_features']['positive_20d_excess_persistence_sessions']==1
assert float(control['outcomes']['5']['excess_return'])<0 and float(control['outcomes']['20']['excess_return'])<0
metadata={k:v for k,v in s.items() if k not in ['rows','session_summaries','summary']}
audit={'qualification':'DERIVED_FROM_VERIFIED_RETAINED_STUDY_NOT_LOSSLESS_ORIGINAL_ARCHIVE',
 'original_custody':'GITHUB_ACTIONS_ARTIFACT','original_permanent_git_custody':'NOT_ESTABLISHED',
 'original_artifact':{'id':10435911881,'run':35070558913,'attempt':1,'zip_bytes':4042845,'zip_sha256':ZIP_SHA,
 'created_at':'2026-09-16T07:50:47Z','expires_at':'2026-12-15T07:50:09Z','files':FILES},
 'execution':e,'original_study_hash':wrapper['study_hash'],'original_generated_at':wrapper['generated_at'],
 'study_metadata':metadata,'complete_denominator_summary':summary,'complete_census':census,
 'pressure_identity_selection':'Purposive agricultural/livestock/broad-military/marine/kitchen/bank/metals diagnostic identities chosen from prior questions and known historical outcomes before this projection; every date retained, but not outcome-blind preregistration or a representative sample',
 'pressure_identities':CASES,'complete_pressure_histories':cases,
 'omissions':'Other identities remain in complete census but not per-row output; redundant original path metrics omitted. Original ZIP required for full recomputation; output is not a replacement.',
 'causal_limit':'radar_selected=false means no new state-entry event, not proof of no active signal; rows cannot establish actual display, research or delivery.',
 'selection_change':'NONE','production_change':'NONE','investment_authority':'NONE'}
audit['audit_hash']=canonical_hash(audit)
encoded=(json.dumps(audit,ensure_ascii=False,separators=(',',':'))+'\n').encode();assert len(encoded)<=512*1024
out.mkdir(parents=False,exist_ok=False)
(out/'derived-audit.json').write_bytes(encoded)
(out/'original-execution.json').write_bytes(blobs['execution.json'])
(out/'original-summary.md').write_bytes(blobs['summary.md'])
print(json.dumps({'bytes':len(encoded),'audit_hash':audit['audit_hash'],'census':len(census),'case_rows':len(cases),'summary':summary},ensure_ascii=False))
