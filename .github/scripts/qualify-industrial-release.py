import base64,hashlib,json,os,subprocess,zipfile
from pathlib import Path
from datetime import datetime,timezone
from bs4 import BeautifulSoup
from decision_kernel.runtime.current_state_delivery import GitHubAPI
from decision_kernel.runtime.current_state import unpack_archive
from decision_kernel.runtime import industry_fundamentals as s
api=GitHubAPI(os.environ['GH_TOKEN'])
sources={}
for aid,rid in ((10869756298,36146335949),(10869366697,36147004078)):
    a=api.get('actions/artifacts/'+str(aid)); r=api.get('actions/runs/'+str(rid))
    sources[aid]=unpack_archive(api.archive(a),a,r)
first,second=sources[10869756298],sources[10869366697]
records=[]; files={}; links=s.catalog(first['nbs-releases.body'],s.NBS)
for family,name in (('cpca','cpca-total.body'),('logistics','macro_china_lpi_index.body'),('tanker','macro_china_bdti_index.body'),('ppi','macro_china_ppi.body'),('memory','memory-market.body')):
    files[name]=first[name]
    records.append({'id':family,'status':'CAPTURED','file':name})
for record in json.loads(second['probe.json']):
    if not record['id'].startswith('release-'): continue
    name=record['id']+'.body'; raw=second[name]
    soup=BeautifulSoup(raw,'html.parser'); title=s.text(soup.title.get_text()).removesuffix('-国家统计局')
    family=next((key for key,pattern in s.PROFILES.items() if __import__('re').search(pattern,title)),None)
    if family:
        files[name]=raw
        records.append({'id':family,'status':'CAPTURED','file':name,'title':title,'url':record['url']})
result=s.normalize(records,files,cutoff=datetime.now(timezone.utc).isoformat())
print('ACTUAL_DISCOVERY='+json.dumps({k:len(v) for k,v in links.items()},ensure_ascii=False),flush=True)
print('ACTUAL_INDUSTRY_COVERAGE='+json.dumps(result['coverage']),flush=True)
for family,section in result['sections'].items():
    sample=[{'label':x['label'],'latest':x['latest'],'unit':x['unit'],'points':len(x['points'])} for x in result['series'] if x['family']==family][:4]
    print('FAMILY='+json.dumps({'family':family,'section':section,'sample':sample},ensure_ascii=False),flush=True)
Path('../qualification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
paths=['src/decision_kernel/runtime/industry_fundamentals.py','src/decision_kernel/runtime/industry_fundamentals_reading.py','src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py','.github/workflows/radar-industry-breadth.yml','tests/test_industry_fundamentals.py','docs/industry-fundamentals-v1.md']
with zipfile.ZipFile('../prepared-code.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for path in paths: z.write(path,path)
assert result['coverage']['available_families']==10, result['sections']
assert set(links)==set(s.PROFILES), links
entries=[]
for path in paths:
    raw=Path(path).read_bytes()
    result=subprocess.run(['gh','api','--method','POST','repos/auguspp/decision-kernel/git/blobs','--input','-'],input=json.dumps({'content':base64.b64encode(raw).decode(),'encoding':'base64'}),text=True,capture_output=True,check=True)
    sha=json.loads(result.stdout)['sha']
    assert sha==hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    entries.append({'path':path,'mode':'100644','type':'blob','sha':sha})
print('INDUSTRY_TREE_ENTRIES='+json.dumps(entries),flush=True)
subprocess.run(['git','add','--',*paths],check=True)
Path('../industry.patch').write_bytes(subprocess.check_output(['git','diff','--cached','--binary']))
