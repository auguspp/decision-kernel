import io
import json
import zipfile
from hashlib import sha256

from decision_kernel.runtime import smart_money_reading as reading
from decision_kernel.runtime import smart_money_relay as relay_capture
from decision_kernel.runtime import tushare_relay as relay
from test_smart_money_capture import setup_reader

def relay_result(api,params,clock):
    raw=json.dumps({"code":0,"msg":"ok","data":{"fields":["api","value"],
                    "items":[[api,1]]},"count":1},separators=(",",":")).encode()
    return {"api":api,"params":{k:str(v) for k,v in params.items()},"status":"SUCCESS","attempts":[
        {"attempt":1,"http_status":200,"raw":raw,"requested_at":clock(),"received_at":clock(),
         "headers":{"X-Request-ID":"r"},"classification":"SUCCESS","business_code":0,
         "business_error":None,"business_msg":"ok"}]}

def test_normal_reading_retains_relay_supplement_without_replacing_primary(tmp_path,monkeypatch):
    col,base,run,job,artifact,primary=setup_reader(tmp_path)
    monkeypatch.setenv(relay.SECRET_ENV,"abcdefgh")
    out=tmp_path/"relay-source"
    times=iter([f"2026-09-26T02:10:{i:02d}+00:00" for i in range(40)])
    relay_capture.capture(out,primary["identity"],"2026-09-24",
                          request=lambda api,params,key,clock:relay_result(api,params,clock),
                          clock=lambda:next(times))
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            if p.is_file():
                z.writestr(p.name,p.read_bytes())
    relay_raw=stream.getvalue()
    relay_art={"id":901,"name":f"smart-money-relay-{run['id']}-1",
               "size_in_bytes":len(relay_raw),"digest":"sha256:"+sha256(relay_raw).hexdigest(),
               "expired":False,"workflow_run":{"id":run["id"],"head_sha":run["head_sha"]}}
    jobs_key=f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100"
    relay_job={"name":"capture-tushare-relay","id":43,"head_sha":run["head_sha"],
               "run_id":run["id"],"run_attempt":1,"status":"completed","conclusion":"success"}
    col.api.responses[jobs_key]["jobs"].append(relay_job)
    col.api.responses[jobs_key]["total_count"]+=1
    key=f"actions/runs/{run['id']}/artifacts?per_page=100"
    col.api.responses[key]["artifacts"].append(relay_art)
    col.api.responses[key]["total_count"]+=1
    original=col.api.raw_archive
    def archive(selected):
        col.api.calls+=1
        col.api.reads.append("ARCHIVE")
        return relay_raw if selected["id"]==901 else original
    col.api.archive=archive
    result=reading.attach(col,base)
    sm=result["research"]["smart_money"]
    assert sm["status"]=="READY" and sm["relay_status"]=="READY"
    assert sm["relay_retained_status"]=="READY"
    assert "relay" in sm["details"]
    saved=json.loads(col.files["details/radar/smart-money/relay.json"])
    assert saved["reading_relation"]=="CURRENT_SOURCE_RUN"
    assert saved["families"]["hm_list"]["row_count"]==1
    text=col.files["details/radar/smart-money.md"].decode()
    assert "Tushare Relay 补充来源" in text
    assert primary["capture_hash"]==sm["capture_hash"]

def test_legacy_capture_without_relay_remains_readable(tmp_path):
    col,base,*_=setup_reader(tmp_path)
    result=reading.attach(col,base)
    sm=result["research"]["smart_money"]
    assert sm["status"]=="READY"
    assert sm["relay_status"]=="NOT_PRESENT_LEGACY_OR_NOT_RUN"
