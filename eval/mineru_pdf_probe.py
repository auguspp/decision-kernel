from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, time, zipfile
from pathlib import Path

AID=10320565453; ABYTES=12563240; ASHA='25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c'
SEM='MINERU_CAPABILITY_PROBE_DERIVED_REPRESENTATION_NOT_EVIDENCE'
SAMPLES=(
 ('heshun-1225530965-p23','603353.SH','1225530965','cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa',23,'EMPTY_TEXT_NONBLANK_PAGE'),
 ('heshun-1225530957-p25','603353.SH','1225530957','0aa7c59b58b74ff50924716b18b37c9c95a6e4b76dbb06b4afe4dada5a84dd3f',25,'SIGNATURE_PAGE_SUPPLEMENTAL_READING'),
 ('guangha-1225486858-p4','300711.SZ','1225486858','cc65030bd9e676f5289d2bc2649eb7ff23b26a5b406b08b88cd20392d45df342',4,'EMPTY_TEXT_SUPPLEMENTAL_READING'),
 ('heshun-1225530957-p11-table','603353.SH','1225530957','0aa7c59b58b74ff50924716b18b37c9c95a6e4b76dbb06b4afe4dada5a84dd3f',11,'READABLE_TABLE_STRUCTURE_CONTROL'),
)
def h(b): return hashlib.sha256(b).hexdigest()
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def run(a,env):
 t=time.monotonic(); q=subprocess.run(a,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
 return {'argv':a,'exit_code':q.returncode,'elapsed_seconds':round(time.monotonic()-t,3),'stdout':q.stdout,'stderr':q.stderr}
def page(o,n):
 m=[p for p in o.get('pages',[]) if p.get('page_number')==n]
 if len(m)!=1: raise ValueError(f'page {n} missing/ambiguous')
 return m[0]
def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values(): yield from walk(v)
 elif isinstance(x,list):
  for v in x: yield from walk(v)
def markdown_text_only(value):
 return re.sub(r'!\\[\\]\\(data:image/[^)]*\\)', '', value, flags=re.S)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--archive',type=Path,required=True); ap.add_argument('--work',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
 raw=a.archive.read_bytes()
 if len(raw)!=ABYTES or h(raw)!=ASHA: raise SystemExit('frozen artifact identity differs')
 a.work.mkdir(parents=True,exist_ok=True); a.output.mkdir(parents=True,exist_ok=True)
 base=[]
 with zipfile.ZipFile(a.archive) as z:
  journals={}
  for sid,issuer,ann,sha,pn,purpose in SAMPLES:
   journals.setdefault(issuer,json.loads(z.read(f'{issuer}/sources/source-journal.json')))
   rows=[r for r in journals[issuer].get('body_events',[]) if r.get('announcement_id')==ann]
   if len(rows)!=1 or rows[0].get('pdf_sha256')!=sha: raise SystemExit(f'journal identity differs: {sid}')
   stem=f'{issuer}/sources/{sha}'; pdf=z.read(stem+'.pdf')
   if h(pdf)!=sha: raise SystemExit(f'PDF identity differs: {sid}')
   (a.work/f'{sid}.pdf').write_bytes(pdf)
   ext=json.loads(z.read(stem+'-extraction.json')); txt=page(ext,pn).get('text','') or ''
   bdir=a.output/'baseline'; bdir.mkdir(exist_ok=True); (bdir/f'{sid}.txt').write_text(txt,encoding='utf-8')
   supplement=False; rn=stem+'-page-readings.json'
   if rn in z.namelist():
    ro=json.loads(z.read(rn)); mm=[x for x in ro.get('pages',[]) if x.get('page_number')==pn]
    if mm: dump(bdir/f'{sid}-supplemental.json',mm[0]); supplement=True
   base.append({'sample_id':sid,'issuer':issuer,'announcement_id':ann,'pdf_sha256':sha,'page':pn,'purpose':purpose,'source_locator':rows[0].get('source_locator'),'baseline_text_chars':len(txt),'baseline_text_sha256':h(txt.encode()),'supplemental_reading_present':supplement})
 env=os.environ.copy(); env.setdefault('MINERU_MODEL_SOURCE','auto'); kit=shutil.which('mineru-kit')
 environment={'mineru_kit_path':kit,'tier_requested':'basic','ocr_mode_requested':'ocr','model_source_requested':env['MINERU_MODEL_SOURCE']}
 edir=a.output/'environment'; edir.mkdir(exist_ok=True)
 if kit:
  for name,cmd in [('parse-help',[kit,'parse','--help']),('version',[shutil.which('mineru') or kit,'version','--json'] if shutil.which('mineru') else [kit,'--version'])]:
   r=run(cmd,env); (edir/f'{name}.stdout.txt').write_text(r.pop('stdout'),encoding='utf-8'); (edir/f'{name}.stderr.txt').write_text(r.pop('stderr'),encoding='utf-8'); environment[name]=r
  if shutil.which('mineru'):
   r=run(['mineru','telemetry','disable'],env); (edir/'telemetry.stdout.txt').write_text(r.pop('stdout'),encoding='utf-8'); (edir/'telemetry.stderr.txt').write_text(r.pop('stderr'),encoding='utf-8'); environment['telemetry_disable']=r
  environment['status']='READY_TO_ATTEMPT_PARSE'
 else: environment['status']='MINERU_KIT_NOT_INSTALLED'
 dump(a.output/'environment.json',environment)
 results=[]; failures=0; table_signal=False; locator_signal=False
 for s in base:
  sd=a.output/'mineru'/s['sample_id']; sd.mkdir(parents=True,exist_ok=True); md=sd/'output.md'
  if kit:
   r=run([kit,'parse',str(a.work/f"{s['sample_id']}.pdf"),'-o',str(md),'--format','markdown','--tier','basic','--pages',str(s['page']),'--ocr-mode','ocr'],env)
   (sd/'markdown.stdout.txt').write_text(r.pop('stdout'),encoding='utf-8'); (sd/'markdown.stderr.txt').write_text(r.pop('stderr'),encoding='utf-8'); dump(sd/'markdown-command.json',r); failures+=r['exit_code']!=0
  txt=md.read_text(encoding='utf-8',errors='replace') if md.exists() else ''
  text_only=markdown_text_only(txt)
  tcount=bcount=0; pidx=set(); bidx=[]
  if kit and s['sample_id'] in {'guangha-1225486858-p4','heshun-1225530957-p11-table'}:
   mid=sd/'middle.json'; r=run([kit,'parse',str(a.work/f"{s['sample_id']}.pdf"),'-o',str(mid),'--format','middle_json','--tier','basic','--pages',str(s['page']),'--ocr-mode','ocr'],env)
   (sd/'middle.stdout.txt').write_text(r.pop('stdout'),encoding='utf-8'); (sd/'middle.stderr.txt').write_text(r.pop('stderr'),encoding='utf-8'); dump(sd/'middle-command.json',r); failures+=r['exit_code']!=0
   if mid.exists():
    try:
     obj=json.loads(mid.read_text(encoding='utf-8'))
     for n in walk(obj):
      if isinstance(n.get('page_idx'),int): pidx.add(n['page_idx'])
      if 'index' in n: bidx.append(n['index'])
      if 'type' in n: bcount+=1; tcount+=str(n['type']).lower()=='table'
    except json.JSONDecodeError: pass
  table_signal|=tcount>0; locator_signal|=bool(pidx or bidx)
  results.append({**s,'mineru_markdown_chars':len(txt),'mineru_text_chars_excluding_embedded_images':len(text_only),'mineru_nonempty':bool(text_only.strip()),'middle_table_blocks':tcount,'middle_typed_blocks':bcount,'middle_page_indices':sorted(pidx),'middle_block_index_count':len(bidx),'manual_semantic_acceptance':'NOT_ESTABLISHED'})
 empty=[x for x in results if x['baseline_text_chars']==0]; recovered=sum(x['mineru_nonempty'] for x in empty); parsed=sum(x['mineru_nonempty'] for x in results)
 if not kit: status='ENVIRONMENT_GAP'
 elif failures and not parsed: status='EXECUTION_GAP'
 elif recovered==len(empty) and table_signal: status='CAPABILITY_SIGNAL_POSITIVE'
 elif parsed: status='CAPABILITY_SIGNAL_PARTIAL'
 else: status='CAPABILITY_SIGNAL_NEGATIVE'
 out={'schema_version':1,'semantics':SEM,'status':status,'artifact_id':AID,'artifact_sha256':ASHA,'sample_count':len(results),'empty_baseline_sample_count':len(empty),'empty_baseline_recovered_nonempty_count':recovered,'structured_table_signal':table_signal,'structured_locator_signal':locator_signal,'command_failure_count':failures,'samples':results,'manual_quality_review':'REQUIRED','production_qualification':'NOT_ESTABLISHED','research_authority':'NONE','human_attention_authority':'NONE','investment_authority':'NONE'}
 out['probe_hash']=h(json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()); dump(a.output/'probe.json',out)
 lines=['# MinerU retained-PDF capability probe','',f'Status: **{status}**','','Derived representation diagnostic only; not Evidence truth certification, Research execution, or production acceptance.','',f'Frozen source artifact: `{AID}` / `{ASHA}`','','| sample | baseline chars | MinerU text chars (embedded images excluded) | table blocks | manual acceptance |','|---|---:|---:|---:|---|']
 for x in results: lines.append(f"| {x['sample_id']} | {x['baseline_text_chars']} | {x['mineru_text_chars_excluding_embedded_images']} | {x['middle_table_blocks']} | NOT_ESTABLISHED |")
 lines += ['',f'Recovered non-empty output on empty-baseline samples: **{recovered}/{len(empty)}**.',f'Structured table signal: **{table_signal}**. Structured locator signal: **{locator_signal}**.','','Manual visual/text review remains required before any capability or integration decision.','','Investment Authority: **NONE**.']
 (a.output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 # Self-verification: derived result cannot gain production, Research, attention, or investment authority.
 chk=json.loads((a.output/'probe.json').read_text()); ph=chk.pop('probe_hash')
 if h(json.dumps(chk,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())!=ph: raise SystemExit('probe hash differs')
 if chk['semantics']!=SEM or chk['artifact_sha256']!=ASHA or chk['manual_quality_review']!='REQUIRED' or chk['production_qualification']!='NOT_ESTABLISHED' or any(chk[k]!='NONE' for k in ('research_authority','human_attention_authority','investment_authority')): raise SystemExit('probe contract violated')
if __name__=='__main__': main()
