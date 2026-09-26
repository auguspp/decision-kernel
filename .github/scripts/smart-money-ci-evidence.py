"""Temporary exact-run CI evidence inspection; never execute artifact code."""
import hashlib,io,json,os,runpy,socket,subprocess,sys,zipfile
from pathlib import Path

root=Path('.').resolve();out=Path(os.environ['RUNNER_TEMP'])/'smart-money-evidence';out.mkdir(exist_ok=True)
rid=int(os.environ['EVIDENCE_RUN']);head=os.environ['EVIDENCE_HEAD'];repo='auguspp/decision-kernel'
def api(path,raw=False):
    value=subprocess.check_output(['gh','api',f'repos/{repo}/{path}'])
    return value if raw else json.loads(value)
run=api(f'actions/runs/{rid}')
assert run['id']==rid and run['head_sha']==head and run['run_attempt']==1
assert run['status']=='completed' and run['conclusion']=='success' and run['path']=='.github/workflows/ci.yml'
assert run['repository']['full_name']==repo and run['head_repository']['full_name']==repo
payload=api(f'actions/runs/{rid}/artifacts?per_page=100');assert payload['total_count']==len(payload['artifacts'])
items=[a for a in payload['artifacts'] if a['name']==f'kernel-ci-{rid}-1'];assert len(items)==1
artifact=items[0];assert not artifact['expired'] and artifact['workflow_run']['id']==rid and artifact['workflow_run']['head_sha']==head
raw=api(f"actions/artifacts/{artifact['id']}/zip",True)
assert len(raw)==artifact['size_in_bytes'] and hashlib.sha256(raw).hexdigest()==artifact['digest'].removeprefix('sha256:')
expected_tree=api('git/commits/'+head)['tree']['sha']
(out/'ci-original.zip').write_bytes(raw);(out/'artifact.json').write_text(json.dumps(artifact,indent=2))
(out/'run.json').write_text(json.dumps(run,indent=2))
os.environ.pop('GH_TOKEN',None)
def denied(*a,**k):raise AssertionError('No network during CI archive validation')
socket.socket.connect=denied;socket.getaddrinfo=denied
R=runpy.run_path('.github/scripts/ci-merge-reuse.py')
with R['verified_archive'](raw,artifact) as z:
    identity=dict(line.split('=',1) for line in z.read('identity.txt').decode().splitlines())
    environment=json.loads(z.read('environment.json'));scope=json.loads(z.read('scope.json'))
    assert identity['code_sha']==head and identity['run_id']==str(rid) and identity['attempt']=='1'
    assert identity['event']==run['event'] and environment['tree']==expected_tree
    if run['event']=='pull_request':
        count=R['full_evidence'](raw,artifact,run,environment);kind='EXACT_PR_FULL'
    elif scope['scope']=='merge_reuse':
        smoke=z.read('smoke.xml') if 'smoke.xml' in z.namelist() else None
        import xml.etree.ElementTree as ET
        assert smoke is not None
        xml=ET.fromstring(smoke);assert all(xml.find('.//'+tag) is None for tag in ['failure','error','skipped'])
        count=len(xml.findall('.//testcase'));kind='MAIN_REUSE_WITH_ACTUAL_SMOKE'
    else:
        collection=z.read('collection.txt').decode();xml=z.read('pytest.xml');plan=json.loads(z.read('partition.json'))
        remaining=R['matrix_remaining'](collection,plan['paths'],[(z.read(f'shard-{i}.zip'),a) for i,a in enumerate(plan['shards'],1)],identity,environment,plan['timing_sha256'])
        assert remaining==z.read('remaining.xml')
        rebuilt=R['partition_junit'](collection,plan['paths'],remaining,z.read('domain-source.zip'),plan['artifact'],identity,environment)
        assert rebuilt==xml
        count=R['passed_test_set'](collection,xml);kind='EXACT_MAIN_FULL'
    proof={'kind':kind,'run':rid,'head':head,'tree':expected_tree,'artifact':artifact['id'],
           'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'tests_verified':count,
           'scope':scope,'identity':identity,'archive_files':z.namelist(),'source_calls':0,
           'executed_artifact_code':False,'validation_environment':'ARCHIVED_CI_ENVIRONMENT_AND_PARTITIONS_NOT_THIS_RUNNER_REUSE'}
    (out/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
    print('EXACT_CI_EVIDENCE',json.dumps(proof,ensure_ascii=False))
