"""Temporary offline browser acceptance; no external source calls."""
import json,os,socket,sys,tempfile,shutil,subprocess,zipfile
from pathlib import Path
from bs4 import BeautifulSoup
from decision_kernel.runtime import smart_money_view as v

def denied(*a,**k):raise AssertionError('No source calls during offline acceptance')
socket.socket.connect=denied;socket.getaddrinfo=denied
root=Path(os.environ['RUNNER_TEMP'])/'smart-money-probe'
with zipfile.ZipFile(root/'previous-acceptance.zip') as archive:
    for name in ['retained-samples.json','archives-verified.json','legacy-replay.json']:
        (root/name).write_bytes(archive.read(name))
sys.path.insert(0,str(Path('tests').resolve()))
from test_smart_money import captured
with tempfile.TemporaryDirectory() as directory:
    obs,_=captured(Path(directory));hist=v.history(obs);chunks,meta=v.encode_chunks(hist)
    page=v.browser(v.summarize(obs,hist),chunks,meta,{})
    (root/'synthetic-browser.html').write_text(page)
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:raise RuntimeError('HEADLESS_BROWSER_UNAVAILABLE')
    result=subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--no-proxy-server',
        '--host-resolver-rules=MAP * ~NOTFOUND','--virtual-time-budget=10000','--dump-dom',
        (root/'synthetic-browser.html').as_uri()],capture_output=True,text=True,timeout=45)
    (root/'browser-dom.html').write_text(result.stdout)
    (root/'browser-stderr.txt').write_text(result.stderr[-20000:])
    dom=BeautifulSoup(result.stdout,'html.parser');health=dom.find(id='health');query=dom.find(id='query')
    proof={'browser':chrome,'returncode':result.returncode,'synthetic_rows':len(hist['records']),
           'visible_articles':len(dom.select('article')),'health':health.get_text() if health else None,
           'count':dom.find(id='count').get_text() if dom.find(id='count') else None,
           'query_enabled':query is not None and not query.has_attr('disabled'),
           'source_calls':0,'production_sample':False,'interactive_search_and_mobile_layout':'NOT_CHECKED_BY_THIS_SMOKE'}
    (root/'browser-proof.json').write_text(json.dumps(proof,ensure_ascii=False));print('BROWSER_SMOKE',json.dumps(proof,ensure_ascii=False))
    assert result.returncode==0 and proof['visible_articles']>0 and proof['query_enabled']
    assert health and not health.get_text().startswith('读取失败：')
