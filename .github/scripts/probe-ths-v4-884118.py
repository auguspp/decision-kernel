#!/usr/bin/env python3
import hashlib,json,sys
from datetime import date,datetime
from decimal import Decimal
from pathlib import Path
import requests
from akshare.stock_feature import stock_board_industry_ths as ak
SRC=Path(sys.argv[1]); OUT=Path(sys.argv[2]); OUT.mkdir(parents=True,exist_ok=True)
CODE='884118.TI'; NEED=(date(2026,9,7),date(2026,9,8),date(2026,9,9),date(2026,9,10))
def req(c,m):
    if not c: raise RuntimeError(m)
st=json.loads((SRC/'input/market-state.json').read_text()); row=next(x for x in st['series'] if x['thscode']==CODE); days=[date.fromisoformat(x) for x in st['sessions']]; old={d:(Decimal(str(c)),Decimal(str(t))) for d,c,t in zip(days,row['closes'],row['turnovers'],strict=True)}
js=ak.py_mini_racer.MiniRacer(); js.eval(ak._get_file_content_ths('ths.js')); v=js.call('v')
url='https://d.10jqka.com.cn/v4/line/bk_884118/01/2026.js'; h={'User-Agent':'Mozilla/5.0','Referer':'http://q.10jqka.com.cn','Host':'d.10jqka.com.cn','Cookie':'v='+v}
r=requests.get(url,headers=h,timeout=12,allow_redirects=False); b=r.content; (OUT/'884118.js').write_bytes(b)
res={'status':'FAILED_CLOSED','http_status':r.status_code,'sha256':hashlib.sha256(b).hexdigest(),'checks':[],'error':None,'network_calls':1,'hithink_calls':0,'production_state_writes':0,'restore_authority':'NONE'}
try:
 req(r.status_code==200,f'HTTP {r.status_code}')
 text=b.decode(); s=text.find('{'); req(s>=0,'object missing'); p=ak.demjson.decode(text[s:-1]); series=p.get('data'); req(isinstance(series,str),'data missing')
 pts={}
 for rec in series.split(';'):
  c=rec.split(','); req(len(c) in (11,12),'row width'); raw=c[0]; d=date(int(raw[:4]),int(raw[4:6]),int(raw[6:8]))
  if d in NEED: pts[d]=(Decimal(c[4]),Decimal(c[5]),Decimal(c[6]))
 req(set(pts)==set(NEED),'needed dates missing')
 for d in NEED[:3]:
  cl,_,tu=pts[d]; ec,et=old[d]; ok=cl==ec and tu==et; res['checks'].append({'date':d.isoformat(),'close_exact':cl==ec,'turnover_exact':tu==et,'exact':ok}); req(ok,f'overlap mismatch {d}')
 cl,vo,tu=pts[NEED[-1]]; res['target']={'date':'2026-09-10','close':str(cl),'volume':str(vo),'turnover':str(tu)}; res['status']='EXACT_OVERLAP_V4_AVAILABLE'
except Exception as e: res['error']={'type':type(e).__name__,'message':str(e)}
(OUT/'result.json').write_text(json.dumps(res,ensure_ascii=False,indent=2,sort_keys=True)+'\n'); print(res['status'],res['error']); raise SystemExit(0 if res['status']=='EXACT_OVERLAP_V4_AVAILABLE' else 2)
