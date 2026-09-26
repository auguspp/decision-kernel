"""Temporary offline acceptance; original captures are not fresh market scans."""
import json, os, socket, sys, tempfile, zipfile, shutil, subprocess
from pathlib import Path
from collections import Counter
from decision_kernel.runtime import smart_money_sources as s, smart_money_documents as d, smart_money_view as v

def denied(*a,**k):raise AssertionError('No source calls during offline acceptance')
socket.socket.connect=denied;socket.getaddrinfo=denied
root=Path(os.environ['RUNNER_TEMP'])/'smart-money-probe'
rows=[]
with zipfile.ZipFile(root/'10893279859.zip') as z:
    pairs={'ht-hot-23.body':('hot_money','2026-09-23'),'ht-hot-24.body':('hot_money','2026-09-24'),
           'ht-org-24.body':('institutional','2026-09-24'),'ft-northbound.body':('northbound','2026-09-24'),
           'em-activity.body':('activity','disclosures'),'em-reports.body':('forecasts','disclosures'),
           'em-repurchase.body':('repurchases','disclosures'),'em-placement.body':('placements','disclosures')}
    for name,(family,partition) in pairs.items():
        obj=s.decode(z.read(name));data=obj.get('result',obj.get('data',{}))
        if family=='forecasts':body=obj['data']
        elif family=='northbound':body=[data]
        elif family=='hot_money':body=data['hot_money_items']
        elif family=='institutional':body=data['stock_items']
        else:body=data['data']
        req=s.spec(family,partition,'2026-01-01','2026-09-26');good=[];bad=Counter()
        for i,row in enumerate(body):
            if family=='placements' and str(row.get('SEO_TYPE'))!='1':continue
            try:good.extend(s.normalize(row,req,i,0,obj))
            except Exception as e:bad[str(e) if type(e)is s.SourceError else type(e).__name__]+=1
        record={'file':name,'family':family,'returned_sample_rows':len(body),'normalized':len(good),
                'row_rejections':dict(bad),'examples':good[:2],'not_complete_source_scan':True}
        rows.append(record);print('RETAINED_SAMPLE',json.dumps(record,ensure_ascii=False))
with zipfile.ZipFile(root/'10893294994.zip') as z:
    for name,family,partition in [('ft-seats-fixed.body','seats','2026-09-24'),('em-holder-details.body','holdings','2026-06-30'),('ft-executives.body','executives','disclosures')]:
        obj=s.decode(z.read(name));data=obj.get('result',obj.get('data',{}));body=data.get('records',data.get('data',[]));good=[];bad=Counter()
        req=s.spec(family,partition,'2026-01-01','2026-09-26')
        for i,row in enumerate(body):
            try:good.extend(s.normalize(row,req,i,0,obj))
            except Exception as e:bad[str(e) if type(e)is s.SourceError else type(e).__name__]+=1
        record={'file':name,'family':family,'returned_sample_rows':len(body),'normalized':len(good),
                'row_rejections':dict(bad),'examples':good[:2],'not_complete_source_scan':True}
        rows.append(record);print('RETAINED_SAMPLE',json.dumps(record,ensure_ascii=False))
with zipfile.ZipFile(root/'10894571810.zip') as z:
    for channel in ['SH','SZ']:
        p=d.northbound_table(z.read('hkex-'+channel.lower()+'.body'),s.spec('north_holdings',channel,'2026-06-28','2026-09-26'))
        record={'family':'north_holdings','channel':channel,'period':p['period'],'count':p['count'],'first':p['rows'][:2]}
        rows.append(record);print('RETAINED_HKEX',json.dumps(record,ensure_ascii=False))
    reports=s.decode(z.read('gree-reports.body'))
    row=reports['data'][0];req=s.spec('forecasts','disclosures','2026-01-01','2026-09-26')
    norm=s.normalize(row,req,0,0,reports)[0]
    result=d.reported_revisions(z.read('forecast-0.body'),norm)
    rows.append(result);print('RETAINED_REPORT',json.dumps(result,ensure_ascii=False))
(root/'retained-samples.json').write_bytes(s.encoded(rows))
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
    assert result.returncode==0 and '<article>' in result.stdout and '读取失败：' not in result.stdout
    assert 'id="query"' in result.stdout and 'id="query" placeholder="公司 / 代码 / 游资标签 / 具名持有人" disabled' not in result.stdout
    (root/'browser-dom.html').write_text(result.stdout)
    proof={'browser':chrome,'synthetic_rows':len(hist['records']),'visible_articles':result.stdout.count('<article>'),
           'decompression_and_initial_render':True,'source_calls':0,'production_sample':False,
           'interactive_search_and_mobile_layout':'NOT_CHECKED_BY_THIS_SMOKE'}
    (root/'browser-proof.json').write_text(json.dumps(proof,ensure_ascii=False));print('BROWSER_SMOKE',json.dumps(proof))
