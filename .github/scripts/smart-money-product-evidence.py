"""Temporary production evidence reader; original source data is never executable."""
import base64,hashlib,io,json,os,subprocess,socket,zipfile,shutil,re
from pathlib import Path
from bs4 import BeautifulSoup
from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import smart_money_capture as capture, smart_money_view as view

repo='auguspp/decision-kernel';out=Path(os.environ['RUNNER_TEMP'])/'smart-money-product-evidence';out.mkdir(exist_ok=True)
rid=int(os.environ['SOURCE_RUN']);expected=os.environ['SOURCE_HEAD'];R=os.environ['READING_COMMIT']
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/'+path]))
def blob(ref):
    x=api('git/blobs/'+ref['git_blob']);raw=base64.b64decode(x['content'])
    assert x['sha']==ref['git_blob'] and m.blob_sha(raw)==ref['git_blob'] and len(raw)==ref['bytes'] and m.sha256(raw)==ref['sha256']
    return raw
run=api(f'actions/runs/{rid}');assert run['head_sha']==expected and run['run_attempt']==1 and run['status']=='completed'
arts=api(f'actions/runs/{rid}/artifacts?per_page=100');assert arts['total_count']==len(arts['artifacts'])
a=[a for a in arts['artifacts'] if a['name']==f'smart-money-{rid}-1'];assert len(a)==1;a=a[0]
assert not a['expired'] and a['workflow_run']['id']==rid and a['workflow_run']['head_sha']==expected
raw=subprocess.check_output(['gh','api',f"repos/{repo}/actions/artifacts/{a['id']}/zip"])
assert len(raw)==a['size_in_bytes'] and 'sha256:'+m.sha256(raw)==a['digest']
(out/'source-original.zip').write_bytes(raw)
z=zipfile.ZipFile(io.BytesIO(raw));assert z.testzip() is None and len(z.namelist())==len(set(z.namelist()))
assert all('/' not in n and (n=='capture.json' or n.startswith('raw-') and n.endswith('.body')) for n in z.namelist())
files={n:z.read(n) for n in z.namelist()};manifest=json.loads(files['capture.json'])
assert manifest['identity']['code_commit']==expected
root=api('contents/current-state.json?ref='+R)
if root.get('encoding')!='base64':root=api('git/blobs/'+root['sha'])
package=json.loads(base64.b64decode(root['content']));m.validate_read_package(package)
entry=package['research']['smart_money'];assert entry['capture_hash']==manifest['capture_hash']
refs=entry['details'];overview=json.loads(blob(refs['overview']));meta=json.loads(blob(refs['history']))
chunks={r['name']:blob(r['reference']) for r in meta['chunks']};page=blob(refs['browser']);markdown=blob(refs['markdown'])
(out/'reading.md').write_bytes(markdown);(out/'browse.html').write_bytes(page)
(out/'overview.json').write_text(json.dumps(overview,ensure_ascii=False,indent=2))
os.environ.pop('GH_TOKEN',None)
def deny(*a,**k):raise AssertionError('No source/network calls during replay')
socket.socket.connect=deny;socket.getaddrinfo=deny
obs=capture.replay(files,manifest['identity'],cutoff=run['updated_at']);hist=view.decode_chunks(meta,chunks)
assert obs['capture_hash']==entry['capture_hash'] and hist['capture_hash']==entry['capture_hash']
queries=['章盟主','葛卫东','章建平','徐开东','高毅','000651','002902']
examples={q:[r['data'] for r in hist['records'] if q in ' '.join(str(r['data'].get(k,'')) for k in ['ticker','company','actor_name'])][-8:] for q in queries}
(out/'actual-examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2))
proof={'source_run':rid,'head':expected,'R':R,'artifact':a['id'],'zip_bytes':len(raw),'zip_sha256':m.sha256(raw),
       'capture_hash':obs['capture_hash'],'status':obs['status'],'requests':obs['requests'],
       'available_partitions':obs['available_partitions'],'unresolved':obs['unresolved'],
       'family_coverage':entry['family_coverage'],'histories':len(hist['records']),
       'browser_bytes':len(page),'source_calls_during_replay':0,'source_code_executed_from_archive':False}
print('PRODUCT_EVIDENCE',json.dumps(proof,ensure_ascii=False))
for q,data in examples.items():print('ACTUAL_QUERY',q,json.dumps(data,ensure_ascii=False))
(out/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
tests=[('章盟主','hot_money'),('000651',''),('葛卫东','holdings'),('','north_holdings'),('__NO_SUCH_PARTICIPANT__','')]
def matches(record,q,family):
    if family and record['family']!=family:return False
    d=record['data'];values=d['values'];parts=[d.get('ticker'),d.get('company'),d.get('actor_name'),d.get('actor_id'),values.get('subscription_objects')]
    for person in values.get('roster',[]):parts.extend([person.get('name'),person.get('institution_code')])
    return q.lower() in ' '.join('' if x is None else str(x) for x in parts).lower()
expected_counts=[sum(matches(r,q,f) for r in hist['records']) for q,f in tests]
# Instrument a local COPY only. Saved product bytes above remain unchanged.
script='''
(async function(){
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 for(let i=0;i<600 && document.getElementById('query').disabled;i++)await sleep(50);
 const q=document.getElementById('query'),f=document.getElementById('family'),results=[];
 for(const [value,family] of TESTS){q.value=value;f.value=family;q.dispatchEvent(new Event('input'));results.push({query:value,family,count:document.getElementById('count').textContent,articles:document.querySelectorAll('article').length});}
 const p=document.createElement('pre');p.id='acceptance-proof';p.textContent=JSON.stringify({ready:!q.disabled,health:document.getElementById('health').textContent,results,innerWidth,scrollWidth:document.documentElement.scrollWidth});document.body.append(p);
})();
'''.replace('TESTS',json.dumps(tests,ensure_ascii=False))
hash64=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
text=page.decode().replace('; style-src'," 'sha256-"+hash64+"'; style-src",1).replace('</body>','<script>'+script+'</script></body>')
copy=out/'instrumented-browser.html';copy.write_text(text)
chrome=shutil.which('google-chrome') or shutil.which('chromium');assert chrome
browser_proofs=[]
for width in [1280,390]:
    p=subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--no-proxy-server','--host-resolver-rules=MAP * ~NOTFOUND',
        '--virtual-time-budget=45000',f'--window-size={width},900','--dump-dom',copy.as_uri()],capture_output=True,text=True,timeout=90)
    dom=BeautifulSoup(p.stdout,'html.parser');node=dom.find(id='acceptance-proof');assert p.returncode==0 and node is not None
    result=json.loads(node.get_text());assert result['ready'] and not result['health'].startswith('读取失败：')
    for actual,wanted in zip(result['results'],expected_counts,strict=True):
        assert int(re.search(r'匹配 (\d+) 条',actual['count']).group(1))==wanted and actual['articles']==min(40,wanted)
    result['requested_width']=width;result['page_overflow']=result['scrollWidth']>result['innerWidth'];browser_proofs.append(result)
    (out/f'browser-{width}.html').write_text(p.stdout);print('ACTUAL_BROWSER',json.dumps(result,ensure_ascii=False))
(out/'browser-proof.json').write_text(json.dumps(browser_proofs,ensure_ascii=False,indent=2))
