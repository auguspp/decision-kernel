from copy import deepcopy
import json

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import ima_private_probe as p

NOWS = iter([
    "2026-10-02T08:40:00+00:00", "2026-10-02T08:40:01+00:00",
    "2026-10-02T08:40:02+00:00", "2026-10-02T08:40:03+00:00",
])


def raw(data, code=0):
    return json.dumps({"code": code, "msg": "success" if code == 0 else "no", "data": data},
                      ensure_ascii=False, separators=(",", ":")).encode()

BASE_DATA = {"info_list": [{"kb_id": "kb_private_1", "kb_name": "智汇研 券商投行研报"}],
             "is_end": True, "next_cursor": ""}
DOC_DATA = {"info_list": [
    {"media_id": "private-1", "title": "2025-某券商-某报告.pdf", "highlight_content": "secret snippet"},
    {"media_id": "private-2", "title": "2025-另一报告.pdf", "highlight_content": "another"},
], "is_end": False, "next_cursor": "opaque-private-cursor"}


def run_probe(base=BASE_DATA, docs=DOC_DATA):
    calls = []
    times = iter(["2026-10-02T08:40:00+00:00", "2026-10-02T08:40:01+00:00",
                  "2026-10-02T08:40:02+00:00", "2026-10-02T08:40:03+00:00"])
    def send(spec):
        calls.append(deepcopy(spec))
        return (200, raw(base)) if spec["endpoint"] == "search_knowledge_base" else (200, raw(docs))
    result = p.probe("智汇研", "2025", send=send, clock=lambda: next(times))
    return result, calls


def test_two_bounded_calls_and_private_fields_not_retained(tmp_path):
    result, calls = run_probe()
    assert result["status"] == "CONNECTED_SEARCHABLE" and result["source_calls"] == 2
    assert calls[0] == p.base_spec("智汇研")
    assert calls[1] == p.document_spec("kb_private_1", "2025")
    assert result["base"]["match_count"] == 1 and result["documents"]["match_count"] == 2
    assert result["documents"]["next_cursor_present"] is True
    p.write_result(tmp_path / "out", result)
    saved = (tmp_path / "out" / "receipt.json").read_text()
    for private in ["kb_private_1", "智汇研", "2025-某券商", "secret snippet", "private-1", "opaque-private-cursor"]:
        assert private not in saved
    assert "media_id" not in saved and "knowledge_base_id" not in saved


def test_query_hashes_bind_intent_without_public_text():
    result, _ = run_probe()
    assert result["base_query_hash"] == canonical_hash("智汇研")
    assert result["document_query_hash"] == canonical_hash("2025")


def test_official_id_name_schema_also_supported():
    result, _ = run_probe(base={"info_list":[{"id":"official-id","name":"智汇研"}],"is_end":True,"next_cursor":""})
    assert result["status"] == "CONNECTED_SEARCHABLE"


def test_exact_name_wins_among_multiple_matches():
    base={"info_list":[{"id":"a","name":"智汇研增强"},{"id":"b","name":"智汇研"}],"is_end":True,"next_cursor":""}
    result, calls = run_probe(base=base)
    assert calls[1]["body"]["knowledge_base_id"] == "b"


def test_ambiguous_base_stops_before_document_call():
    base={"info_list":[{"id":"a","name":"智汇研A"},{"id":"b","name":"智汇研B"}],"is_end":True,"next_cursor":""}
    calls=[]; times=iter(["2026-10-02T08:40:00+00:00","2026-10-02T08:40:01+00:00"])
    def send(spec): calls.append(spec); return 200, raw(base)
    with pytest.raises(p.ProbeError, match="BASE_AMBIGUOUS"):
        p.probe("智汇研", "2025", send=send, clock=lambda: next(times))
    assert len(calls)==1


def test_no_base_stops_before_document_call():
    base={"info_list":[],"is_end":True,"next_cursor":""}
    calls=[]; times=iter(["2026-10-02T08:40:00+00:00","2026-10-02T08:40:01+00:00"])
    def send(spec): calls.append(spec); return 200, raw(base)
    with pytest.raises(p.ProbeError, match="BASE_NOT_FOUND"):
        p.probe("智汇研", "2025", send=send, clock=lambda: next(times))
    assert len(calls)==1


def test_document_query_optional_is_one_call():
    calls=[]; times=iter(["2026-10-02T08:40:00+00:00","2026-10-02T08:40:01+00:00"])
    def send(spec): calls.append(spec); return 200, raw(BASE_DATA)
    result=p.probe("智汇研", None, send=send, clock=lambda: next(times))
    assert result["status"]=="CONNECTED_BASE_VISIBLE" and result["documents"] is None and len(calls)==1

@pytest.mark.parametrize("bad", [None, "", " ", "x\n", "x"*121])
def test_query_validation(bad):
    with pytest.raises(p.ProbeError): p.query(bad)

@pytest.mark.parametrize("env,code", [
    ({"IMA_OPENAPI_CLIENTID":"", "IMA_OPENAPI_APIKEY":"abcdefgh"}, "CLIENT_ID_UNAVAILABLE"),
    ({"IMA_OPENAPI_CLIENTID":"abcdefgh", "IMA_OPENAPI_APIKEY":""}, "API_KEY_UNAVAILABLE"),
])
def test_credentials_missing(env, code):
    with pytest.raises(p.ProbeError, match=code): p.credentials(env)


def test_nonascii_secret_rejected():
    with pytest.raises(p.ProbeError): p.credentials({"IMA_OPENAPI_CLIENTID":"abcdefgh", "IMA_OPENAPI_APIKEY":"密钥abcdefgh"})

@pytest.mark.parametrize("status", [301,302,401,403,429,500])
def test_http_failure_stops(status):
    times=iter(["2026-10-02T08:40:00+00:00","2026-10-02T08:40:01+00:00"])
    with pytest.raises(p.ProbeError, match="HTTP_REJECTED"):
        p.probe("智汇研", "2025", send=lambda spec:(status,b"denied"), clock=lambda:next(times))


def test_business_failure_stops_without_exposing_message():
    times=iter(["2026-10-02T08:40:00+00:00","2026-10-02T08:40:01+00:00"])
    body=json.dumps({"code":200002,"msg":"private vendor error with secret details","data":{}}).encode()
    with pytest.raises(p.ProbeError, match="BUSINESS_REJECTED"):
        p.probe("智汇研", "2025", send=lambda spec:(200,body), clock=lambda:next(times))
    failure=p.safe_failure(p.ProbeError("BUSINESS_REJECTED"))
    assert "private vendor" not in json.dumps(failure)


def test_duplicate_json_key_rejected():
    with pytest.raises(p.ProbeError, match="DUPLICATE_JSON_KEY"):
        p.payload(b'{"code":0,"code":0,"data":{}}')

@pytest.mark.parametrize("data", [
    {"info_list":None,"is_end":True,"next_cursor":""},
    {"info_list":[],"is_end":"true","next_cursor":""},
    {"info_list":[],"is_end":True,"next_cursor":1},
])
def test_bad_base_schema(data):
    with pytest.raises(p.ProbeError): p.base_rows(data)

@pytest.mark.parametrize("row", [
    {"media_id":"m"}, {"title":"t"}, {"media_id":"m","title":""},
    {"media_id":"m","title":"t","highlight_content":7},
])
def test_bad_document_rows(row):
    with pytest.raises(p.ProbeError):
        p.document_rows({"info_list":[row],"is_end":True,"next_cursor":""})


def test_receipt_hash_detects_mutation():
    result,_=run_probe(); original=result["receipt_hash"]
    changed=deepcopy(result); changed["documents"]["match_count"]=3; changed.pop("receipt_hash")
    assert canonical_hash(changed) != original


def test_safe_failure_only_fixed_code():
    failure=p.safe_failure(RuntimeError("sensitive text"))
    assert failure["failure_code"]=="RuntimeError" and "sensitive" not in json.dumps(failure)


def test_output_create_only(tmp_path):
    result,_=run_probe(); root=tmp_path/"out"; p.write_result(root,result)
    with pytest.raises(p.ProbeError, match="OUTPUT_CREATE_ONLY"): p.write_result(root,result)


def test_symlink_parent_rejected(tmp_path):
    result,_=run_probe(); real=tmp_path/"real"; real.mkdir(); link=tmp_path/"link"; link.symlink_to(real,target_is_directory=True)
    with pytest.raises(p.ProbeError): p.write_result(link/"out",result)


def test_clock_requires_zone():
    with pytest.raises(p.ProbeError, match="CLOCK_ZONE"): p._clock("2026-10-02T08:00:00")


def test_request_spec_fixed_endpoints(monkeypatch):
    payload=raw(BASE_DATA); seen=[]
    class R:
        url=p.BASE+"search_knowledge_base"; status_code=200; headers={"Content-Length":str(len(payload))}
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def iter_content(self,n): yield payload
    class S:
        trust_env=True
        def __enter__(self): assert self.trust_env is False; return self
        def __exit__(self,*a): pass
        def post(self,url,**kwargs):
            seen.append((url,kwargs)); assert kwargs["allow_redirects"] is False and kwargs["timeout"]==(10,20); return R()
    monkeypatch.setattr(p.requests,"Session",S)
    spec=p.base_spec("智汇研")
    assert p.request_raw(spec,client_id="client123",api_key="apikey123")==(200,payload)
    bad=deepcopy(spec); bad["url"]="https://example.com/"
    with pytest.raises(p.ProbeError,match="REQUEST_SPEC"): p.request_raw(bad,client_id="client123",api_key="apikey123")
    assert len(seen)==1


def test_credential_reflection_rejected(monkeypatch):
    payload=b'{"code":0,"data":{"x":"apikey123"}}'
    class R:
        url=p.BASE+"search_knowledge_base"; status_code=200; headers={}
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def iter_content(self,n): yield payload
    class S:
        trust_env=True
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def post(self,*a,**k): return R()
    monkeypatch.setattr(p.requests,"Session",S)
    with pytest.raises(p.ProbeError,match="CREDENTIAL_REFLECTION"):
        p.request_raw(p.base_spec("智汇研"),client_id="client123",api_key="apikey123")


def test_render_never_contains_private_values():
    result,_=run_probe(); text=p.render(result)
    assert "智汇研" not in text and "2025-某券商" not in text and "private-1" not in text

from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def test_workflow_is_manual_only_and_uses_named_secrets():
    text=(ROOT/'.github/workflows/ima-private-probe.yml').read_text()
    assert 'workflow_dispatch:' in text and 'schedule:' not in text
    assert "github.actor == 'auguspp'" in text
    assert 'IMA_OPENAPI_CLIENTID: ${{ secrets.IMA_OPENAPI_CLIENTID || secrets.IMA_CLIENT_ID }}' in text
    assert 'IMA_OPENAPI_APIKEY: ${{ secrets.IMA_OPENAPI_APIKEY || secrets.IMA_API_KEY }}' in text
    assert "permissions:\n  contents: read\n  actions: read" in text
    assert 'retention-days: 7' in text


def test_workflow_never_prints_or_uploads_provider_raw_body():
    text=(ROOT/'.github/workflows/ima-private-probe.yml').read_text()
    assert 'IMA_BASE_QUERY: ${{ inputs.knowledge-base-query }}' in text
    assert 'IMA_DOCUMENT_QUERY: ${{ inputs.document-query }}' in text
    assert 'receipt.json' not in text  # uploads only the sanitized output directory, never a raw filename
    assert 'page-' not in text and '.body' not in text


def test_doc_calls_out_public_repo_private_source_boundary():
    text=(ROOT/'docs/ima-private-report-discovery-v1.md').read_text()
    assert '公开仓库' in text and 'PRIVATE_SECONDARY_LIBRARY / PROVENANCE_NOT_VERIFIED' in text
    assert '不留存' in text and 'source_replay=NOT_AVAILABLE_WITHOUT_PRIVATE_BYTES' in text
