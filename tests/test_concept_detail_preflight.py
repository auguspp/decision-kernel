"""Pre-source rejection diagnostics must be finite, safe and create-only."""
import json
import pytest

from decision_kernel.runtime import concept_detail_capture as capture
from decision_kernel.runtime import concept_radar_capture as original
from tests.test_concept_detail_supplement import WF2, SHA, no_network


@pytest.mark.parametrize('error,code,status',[
    (capture.GitHubReadError('GitHub HTTP 429'),'GITHUB_HTTP_REJECTED',429),
    (capture.GitHubReadError('DO-NOT-RETAIN-KEY https://bad.example'),'GITHUB_READ_UNAVAILABLE',None),
    (ValueError('token=DO-NOT-RETAIN-KEY'),'DETAIL_PHASE_REJECTED',None)])
def test_prepare_rejection_retains_only_finite_diagnostics(tmp_path,monkeypatch,capsys,error,code,status):
    class API:
        session=type('Session',(),{'close':lambda self:None})()
        def __init__(self,*a,**kw):pass
        def get(self,*a):raise error
    monkeypatch.setattr(capture,'GitHubAPI',API)
    for k,v in WF2.items():monkeypatch.setenv(k,v)
    monkeypatch.delenv(original.HITHINK_API_KEY_ENV,raising=False)
    dest=tmp_path/'artifact'/'preparation-failure.json'
    args=['prepare','--output',str(tmp_path/'input'),'--source-run-id','123456',
          '--expected-code',SHA,'--failure-output',str(dest)]
    assert capture.main(args)==2
    log=capsys.readouterr().out;data=json.loads(dest.read_bytes())
    assert data['phase']=='prepare' and data['reason_code']==code and data['http_status']==status
    assert 'DO-NOT-RETAIN-KEY' not in log and b'DO-NOT-RETAIN-KEY' not in dest.read_bytes()
    before=dest.read_bytes()
    assert capture.main(args)==2 and dest.read_bytes()==before
    assert json.loads(capsys.readouterr().out)['diagnostic_retention']=='NOT_SAVED'
