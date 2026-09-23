import datetime, hashlib, json, os, re, urllib.request, urllib.error
from pathlib import Path
URL='https://ai.6600600.xyz/v1/models'
r={'purpose':'ONE_READ_ONLY_CONNECTION_DIAGNOSTIC','model_generation_requests':0,
   'financial_materials_sent':False,'automatic_retry':False,'fallback':False,
   'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
   'url':URL,'requested_model':'gpt-6-astra','run_id':os.environ.get('GITHUB_RUN_ID')}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None
key=os.environ.get('SUB2API_API_KEY')
if not key:
    r['status']='CREDENTIAL_NOT_CONFIGURED'
else:
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    req=urllib.request.Request(URL,method='GET',headers={'Authorization':'Bearer '+key,'Accept':'application/json'})
    try:
        try: response=opener.open(req,timeout=45)
        except urllib.error.HTTPError as e: response=e
        with response:
            body=response.read(512*1024+1)
            r.update(http_status=response.code,body_sha256=hashlib.sha256(body).hexdigest(),
                     body_bytes_read=len(body),content_type=response.headers.get('Content-Type','')[:120],
                     request_id=response.headers.get('x-request-id','')[:100])
        if len(body)>512*1024: r['status']='RESPONSE_BOUND_EXCEEDED'
        else:
            try: data=json.loads(body)
            except (ValueError,UnicodeError): data=None
            r['json_object']=isinstance(data,dict)
            if response.code==200 and isinstance(data,dict) and isinstance(data.get('data'),list):
                ids=[i.get('id') for i in data['data'] if isinstance(i,dict)]
                r.update(status='MODEL_LIST_READ',model_count=len(ids),requested_model_present='gpt-6-astra' in ids)
            else:
                r['status']='CONNECTION_OR_PERMISSION_REJECTED'
                error=data.get('error',{}) if isinstance(data,dict) else {}
                if isinstance(error,dict):
                    for k in ('type','code'):
                        value=error.get(k)
                        if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',value): r['error_'+k]=value
                text=body.decode('utf-8',errors='replace').lower()
                r['body_keyword_indicators_only']=[word for word in ('api key','group','model','permission','expired','ip address','quota','balance','unauthorized','forbidden','denied','cloudflare','policy') if word in text]
    except Exception as e:
        r.update(status='TRANSPORT_UNAVAILABLE',error_type=type(e).__name__)
r['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
out=Path('sub2api-readcheck');out.mkdir(exist_ok=False)
(out/'receipt.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(r,ensure_ascii=False))
