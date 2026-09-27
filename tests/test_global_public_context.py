"""Synthetic public protocols through real capture/replay, never live market proof."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import global_public_context as g

TIME = '2026-09-27T11:00:00Z'
ASOF = '2026-09-26'
IDENT = {'repository': g.REPOSITORY, 'workflow': g.WORKFLOW, 'ref': 'refs/heads/main',
         'event': 'workflow_dispatch', 'code_commit': 'a'*40, 'run_id': 10, 'attempt': 1}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a, **k): raise AssertionError('Unexpected source network')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def stamp(dt):
    return int(datetime.fromisoformat(dt).replace(tzinfo=timezone.utc).timestamp())


def body(spec):
    family = spec['family']
    if family == 'treasury':
        fields = ''.join(f'<d:BC_{t}>4.25</d:BC_{t}>' for t in g.TENORS)
        entries = ''.join(f'<entry><content><m:properties><d:NEW_DATE>2026-09-{d}T00:00:00</d:NEW_DATE>{fields}</m:properties></content></entry>' for d in ('24','25'))
        return (f'<feed xmlns="{g.ATOM[1:-1]}" xmlns:d="{g.DATA[1:-1]}" xmlns:m="{g.META[1:-1]}">{entries}</feed>').encode()
    if family == 'fx':
        rates = ''.join(f'<Cube currency="{c}" rate="1.5"/>' for c in g.CURRENCIES)
        return (f'<gesmes:Envelope xmlns:gesmes="{g.GEST[1:-1]}" xmlns="{g.ECB[1:-1]}"><Cube><Cube time="2026-09-25">{rates}</Cube><Cube time="2026-09-24">{rates.replace("1.5", "1.4")}</Cube></Cube></gesmes:Envelope>').encode()
    if family == 'crypto':
        return g.encoded([[stamp('2026-09-26'),90,110,100,105,1],[stamp('2026-09-24'),90,110,100,100,1]])
    return g.encoded({'chart':{'error':None,'result':[{'meta':{'symbol':spec['id'],'currency':'USD',
         'instrumentType':'FUTURE','dataGranularity':'1d','exchangeTimezoneName':'America/New_York'},
         'timestamp':[stamp('2026-09-24T13:00:00'),stamp('2026-09-25T13:00:00')],
         'indicators':{'quote':[{'close':[100,101]}]}}]}})


def run(tmp_path, family='treasury', change=None):
    calls = []
    def request(spec):
        calls.append(spec); raw, status = body(spec), 200
        if change: raw, status = change(raw, spec, len(calls))
        return g.PublicResponse(spec['url'], status, {}, raw)
    root = tmp_path/'capture'
    report = g.capture(root, IDENT, family, ASOF, request=request, time=lambda:TIME)
    files = {p.name:p.read_bytes() for p in root.iterdir()}
    return report, files, calls


@pytest.mark.parametrize('family,expected,calls', [('treasury',8,1),('fx',4,1),('commodities',3,3),('crypto',2,2)])
def test_independent_families_capture_raw_rebuild_and_do_not_acquire_authority(tmp_path, family, expected, calls):
    report, files, requests = run(tmp_path, family)
    assert len(requests)==calls and report['available_values']==expected and report['status']=='AVAILABLE'
    assert g.replay(files, IDENT, TIME)==report
    assert report['source_calls_during_replay']==0 and report['authority']==g.AUTHORITY
    assert report['vintage'].startswith('CURRENT_RETRIEVAL')
    assert all(r['publication_time'] is None and r['market_status'].startswith('UNKNOWN') for r in report['observations'])


def test_rates_are_annual_percent_and_bp_and_null_latest_never_forward_fills(tmp_path):
    report,_,_=run(tmp_path,change=lambda raw,s,n:(raw.replace(b'<d:BC_10YEAR>4.25</d:BC_10YEAR>',b'<d:BC_10YEAR>4.30</d:BC_10YEAR>',1),200))
    row=next(r for r in report['observations'] if r['symbol']=='UST:10YEAR')
    assert row['value']=='4.25' and row['change']=='-5.00' and row['change_unit']=='bp'
    def null_latest(raw,s,n):
        raw=raw[::-1].replace(b'<d:BC_10YEAR>4.25</d:BC_10YEAR>'[::-1], b'<d:BC_10YEAR m:null="true"/>'[::-1],1)[::-1]
        return raw,200
    report,_,_=run(tmp_path/'null',change=null_latest)
    row=next(r for r in report['observations'] if r['symbol']=='UST:10YEAR')
    assert row['value'] is None and row['source_date']=='2026-09-25' and row['change'] is None
    assert report['status']=='PARTIAL'


def test_fx_quote_direction_and_crypto_actual_intervals_are_explicit(tmp_path):
    fx,_,_=run(tmp_path,'fx'); row=fx['observations'][0]
    assert row['symbol']=='EUR/USD' and row['unit']=='USD_PER_EUR' and row['value']=='1.5'
    crypto,_,_=run(tmp_path/'crypto','crypto'); row=crypto['observations'][0]
    assert row['source_date']=='2026-09-26' and row['previous_date']=='2026-09-24' and row['change']=='5.000000'


def test_vendor_futures_do_not_generate_roll_contaminated_returns(tmp_path):
    report,_,_=run(tmp_path,'commodities')
    assert all(r['value']=='101' and r['change'] is None and r['change_unit'] is None for r in report['observations'])
    assert all('ROLL_IDENTITY_UNKNOWN' in r['change_scope'] for r in report['observations'])
    assert report['observations'][0]['unit']=='USD_PER_TROY_OUNCE'


@pytest.mark.parametrize('status', [401,403,429])
def test_refusal_stops_same_service_without_retry_or_other_source(tmp_path,status):
    report,files,calls=run(tmp_path,'commodities',change=lambda raw,s,n:(b'{"error":"refused"}',status))
    assert len(calls)==1 and report['status']=='UNAVAILABLE' and 'raw-00.bin' in files
    assert all(o['request_state']=='NOT_ATTEMPTED_SERVICE_STOP' for o in report['outcomes'][1:])


@pytest.mark.parametrize('family,damage', [('treasury','duplicate'),('treasury','html'),('treasury','entities'),
    ('fx','duplicate'),('fx','number'),('crypto','ohlc'),('crypto','duplicate'),('crypto','bucket'),
    ('commodities','symbol'),('commodities','currency'),('commodities','timezone')])
def test_malformed_source_is_retained_but_not_normalized(tmp_path,family,damage):
    def mutate(raw,s,n):
        if damage=='html': raw=b'<html>source temporarily unavailable</html>'
        elif damage=='entities':raw=b'<!DOCTYPE x [<!ENTITY e "x">]>'+raw
        elif family=='treasury':raw=raw.replace(b'2026-09-24',b'2026-09-25')
        elif family=='fx':raw=raw.replace(b'currency="CNY"',b'currency="USD"') if damage=='duplicate' else raw.replace(b'1.5',b'NaN')
        else:
            b=g.decode(raw)
            if family=='crypto':
                if damage=='ohlc':b[0][4]=1000
                elif damage=='duplicate':b.append(deepcopy(b[0]))
                else:b[0][0]+=1
            else:
                meta=b['chart']['result'][0]['meta']
                meta[{'symbol':'symbol','currency':'currency','timezone':'exchangeTimezoneName'}[damage]]='OTHER'
            raw=g.encoded(b)
        return raw,200
    report,files,_=run(tmp_path,family,mutate)
    assert report['status']=='UNAVAILABLE' and report['outcomes'][0]['status']=='SOURCE_TABLE_UNCONFIRMED'
    assert 'raw-00.bin' in files


def test_empty_and_out_of_window_candles_never_become_no_change(tmp_path):
    report,_,_=run(tmp_path,'crypto',lambda raw,s,n:(b'[]',200))
    assert report['status']=='UNAVAILABLE' and report['outcomes'][0]['status']=='EMPTY_WINDOW_NOT_NO_CHANGE'
    def outside(raw,s,n):
        b=g.decode(raw);b.append([stamp('2026-09-27'),90,120,100,115,1]);return g.encoded(b),200
    report,_,_=run(tmp_path/'future','crypto',outside)
    assert report['observations'][0]['source_date']=='2026-09-26'
    assert report['outcomes'][0]['source_rows']==3 and report['outcomes'][0]['selected_rows']==2


@pytest.mark.parametrize('damage', ['raw','identity','authority','url','summary','clock','extra','false-complete'])
def test_replay_rejects_tampering_even_with_resealed_manifest(tmp_path,damage):
    _,files,_=run(tmp_path)
    cap=g.decode(files['capture.json'])
    if damage=='raw':files['raw-00.bin']+=b' '
    elif damage=='identity':cap['identity']['run_id']+=1
    elif damage=='authority':cap['authority']['investment_authority']='APPROVED'
    elif damage=='url':cap['records'][0]['spec']['url']='https://example.com'
    elif damage=='summary':files['summary.json']=b'{}'
    elif damage=='clock':cap['records'][0]['received_at']='2027-01-01T00:00:00Z'
    elif damage=='extra':files['execute.py']=b'not executed'
    else:cap['records'][0]['state']='REQUEST_IN_PROGRESS'
    cap['capture_hash']=g.seal(cap);files['capture.json']=g.encoded(cap)
    with pytest.raises((ValueError,KeyError)):g.replay(files,IDENT,TIME)


def test_uncertain_transport_stops_without_exception_text_or_fake_zero(tmp_path):
    calls=[]
    def request(spec):calls.append(spec);raise RuntimeError('sensitive reflected text')
    root=tmp_path/'capture';report=g.capture(root,IDENT,'crypto',ASOF,request=request,time=lambda:TIME)
    assert len(calls)==1 and report['outcomes'][0]['request_state']=='TRANSPORT_UNAVAILABLE'
    assert b'sensitive reflected text' not in b''.join(p.read_bytes() for p in root.iterdir())


def test_failed_body_preserves_refusal_code_and_stops(tmp_path):
    def request(spec):raise g.PublicReadError(403)
    root=tmp_path/'capture';r=g.capture(root,IDENT,'commodities',ASOF,request=request,time=lambda:TIME)
    assert r['outcomes'][0]['http_status']==403 and r['outcomes'][0]['status']=='RESPONSE_UNAVAILABLE_HTTP_403'
    assert all(o['request_state']=='NOT_ATTEMPTED_SERVICE_STOP' for o in r['outcomes'][1:])


def test_month_boundary_dates_identity_and_existing_output_are_checked_before_network(tmp_path):
    assert len(g.plan('treasury','2026-09-04'))==2
    for d in ('2026-09-27','2026-09-28','2026-01-01'):
        with pytest.raises(ValueError):g.capture(tmp_path/'x',IDENT,'fx',d,time=lambda:TIME)
    with pytest.raises(ValueError):g.capture(tmp_path,IDENT,'fx',ASOF,time=lambda:TIME)
    with pytest.raises(ValueError):g.capture(tmp_path/'x',{**IDENT,'attempt':2},'fx',ASOF,time=lambda:TIME)
    with pytest.raises(ValueError):g.plan('arbitrary',ASOF)


def test_workflow_is_finite_manual_main_ci_gated_and_credential_free():
    root=Path(__file__).resolve().parents[1]
    src=(root/'.github/workflows/radar-global-public.yml').read_text()
    assert 'workflow_dispatch:' in src and 'schedule:' not in src and 'secrets.' not in src
    assert 'contents: write' not in src and 'actions: write' not in src
    assert 'github.run_attempt == 1' in src and 'EXPECTED_CODE' in src and 'ci.yml' in src
    assert 'ref: ${{ github.sha }}' in src and 'persist-credentials: false' in src
    assert 'global-public-${{ inputs.family }}-${{ github.run_id }}-${{ github.run_attempt }}' in src


def test_actual_http_adapter_uses_no_credentials_proxy_retry_or_redirect(monkeypatch):
    spec=g.plan('crypto',ASOF)[0]; seen=[]
    class Response:
        status=429
        headers={'Content-Type':'application/json','Retry-After':'60'}
        def geturl(self):return spec['url']
        def read(self,n):assert n==g.MAX_BODY_BYTES+1;return b'{"message":"rate limited"}'
        def __enter__(self):return self
        def __exit__(self,*a):return None
    class Opener:
        def open(self,request,timeout):
            seen.append(request.full_url);assert timeout==25
            assert not {'Authorization','Cookie','X-api-key'} & set(request.headers)
            return Response()
    def opener(*handlers):
        assert len(handlers)==2 and handlers[0].proxies=={} and isinstance(handlers[1],g._NoRedirect)
        return Opener()
    monkeypatch.setattr(g,'build_opener',opener)
    response=g.fetch(spec)
    assert response.status==429 and response.headers['retry-after']=='60' and seen==[spec['url']]
    with pytest.raises(ValueError):g.fetch({**spec,'url':'https://example.com'})


def test_interrupted_checkpoint_replays_as_partial_not_completed(tmp_path):
    _,files,_=run(tmp_path,'crypto');cap=g.decode(files['capture.json'])
    cap['execution_complete']=False;r=cap['records'][1]
    r.update(state='REQUEST_IN_PROGRESS',received_at=None,http_status=None,headers={},body=None,bytes=None,sha256=None,error_type=None)
    files.pop('raw-01.bin');files.pop('summary.json');files.pop('summary.md')
    cap['capture_hash']=g.seal(cap);files['capture.json']=g.encoded(cap)
    report=g.replay(files,IDENT,TIME)
    assert report['status']=='PARTIAL' and report['available_values']==1
