"""One bounded readonly engineering verification; never source or production writes."""
import hashlib,json,os,runpy,subprocess
from pathlib import Path
from decision_kernel.runtime.current_state_delivery import GitHubAPI
head='f2da085b99accb24e00cb5803a9a4467170aabb0'
rid=36151730407
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
api=GitHubAPI(os.environ['GH_TOKEN'],max_calls=20)
run=api.get('actions/runs/'+str(rid))
assert run['head_sha']==head and run['event']=='pull_request' and run['run_attempt']==1
assert run['status']=='completed' and run['conclusion']=='success'
page=api.get(f'actions/runs/{rid}/artifacts?per_page=100')
assert page['total_count']==len(page['artifacts'])
matches=[a for a in page['artifacts'] if a['name']==f'kernel-ci-{rid}-1']
assert len(matches)==1 and not matches[0]['expired']
a=matches[0];raw=api.archive(a)
check=runpy.run_path('.github/scripts/ci-merge-reuse.py')
with check['verified_archive'](raw,a) as z:
    environment=json.loads(z.read('environment.json'))
assert environment['tree']==subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip()
count=check['full_evidence'](raw,a,run,environment)
receipt={'status':'FULL_CI_ORIGINAL_VERIFIER_PASS','head':head,'tree':environment['tree'],
    'run_id':rid,'attempt':1,'artifact_id':a['id'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
    'test_count':count,'environment':'Verified recorded full-CI environment; not this verifier runner environment',
    'source_calls':0,'production_writes':0}
Path('../ci-verification.json').write_text(json.dumps(receipt,indent=2))
Path('../verified-ci.zip').write_bytes(raw)
print('VERIFIED_INDUSTRIAL_CI='+json.dumps(receipt),flush=True)
