"""Reproduce run 34043329828's empty input through the existing CLI entry.

All source validation/binding functions are real; network is prohibited. These
are regression tests, not proof of a new live capture or remote artifact upload.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from test_stock_radar_capture import code, stock_environment
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def configure(monkeypatch, tmp_path, value):
    env=stock_environment()
    for key in list(os.environ):
        if key.startswith(('GITHUB_', 'STOCK_', 'TRIAL_')):
            monkeypatch.delenv(key)
    env['GITHUB_RUN_ID']='34043329828'
    env['GITHUB_SHA']='81ce648e140acdd35cc8249d796aecd842edde5b'
    env['GITHUB_OUTPUT']=str(tmp_path/'step-output')
    env['GITHUB_STEP_SUMMARY']=str(tmp_path/'step-summary')
    env['RUNNER_TEMP']=str(tmp_path)
    env['STOCK_MARKET_RUN_ID']=value
    for key,item in env.items():
        monkeypatch.setenv(key,item)
    return tmp_path/'stock-reading-run'


@pytest.mark.parametrize('value,reason',[
    ('','STOCK_MARKET_RUN_ID_REQUIRED'),
    (' \n','STOCK_MARKET_RUN_ID_REQUIRED'),
    ('latest','STOCK_MARKET_RUN_ID_INVALID'),
    (' 33939414197','STOCK_MARKET_RUN_ID_INVALID'),
    ('0','STOCK_MARKET_RUN_ID_INVALID'),
    ('9'*21,'STOCK_MARKET_RUN_ID_INVALID'),
    ('34043329828','STOCK_MARKET_RUN_ID_IS_CURRENT_RUN'),
    ('101\n::error::PRIVATE-CANARY','STOCK_MARKET_RUN_ID_INVALID'),
])
def test_invalid_intent_retains_diagnostics_but_no_request_or_scan(monkeypatch,tmp_path,capsys,value,reason):
    root=configure(monkeypatch,tmp_path,value);mod=code()
    def forbidden(*args,**kwargs):
        pytest.fail('invalid intent must not call market transport')
    monkeypatch.setattr(mod['hithink_stock_reading'],'request_json',forbidden)
    monkeypatch.setenv('HITHINK_FINANCE_API_KEY','PRIVATE-CANARY')
    monkeypatch.setenv('GH_TOKEN','PRIVATE-CANARY')
    assert mod['main'](['init','--root',str(root)])==2
    stdout=capsys.readouterr().out
    report=json.loads(stdout)
    assert report==json.loads((root/'preflight.json').read_text())
    assert report['status']=='STOCK_READING_NOT_STARTED' and report['reason_code']==reason
    assert report['phase']=='INTENT_VALIDATION' and report['market_run_id'] is None
    assert report['market_requests']==report['market_state_writes']==report['events_created']==0
    assert report['stock_scan_completed'] is report['remote_upload_verified'] is False
    assert report['research_authority']==report['investment_authority']=='NONE'
    assert {p.name for p in root.iterdir()}=={'preflight.json','README.txt','index.html'}
    assert (tmp_path/'step-output').read_text()=='artifact_ready=true\n'
    assert 'PRIVATE-CANARY' not in stdout+''.join(p.read_text() for p in root.iterdir())
    assert '未调用 HiThink' in (root/'README.txt').read_text()
    assert 'latest' not in report['workflow'].values()


def test_missing_environment_field_is_also_explicit(monkeypatch,tmp_path,capsys):
    root=configure(monkeypatch,tmp_path,'');monkeypatch.delenv('STOCK_MARKET_RUN_ID')
    assert code()['main'](['init','--root',str(root)])==2
    assert json.loads(capsys.readouterr().out)['reason_code']=='STOCK_MARKET_RUN_ID_REQUIRED'


def test_valid_intent_remains_exact_without_fetching_or_defaulting(monkeypatch,tmp_path,capsys):
    root=configure(monkeypatch,tmp_path,'33939414197');mod=code()
    assert mod['main'](['init','--root',str(root)])==0
    value=json.loads(capsys.readouterr().out)
    assert value['market_run_id']=='33939414197'
    assert value==json.loads((root/'request.json').read_text())
    assert {p.name for p in root.iterdir()}=={'request.json'}
    assert (tmp_path/'step-output').read_text()=='artifact_ready=true\nmarket_run_id=33939414197\n'
    # Numeric syntax acceptance is not remote success, provenance or freshness.
    assert 'stock-reading.json' not in value and not (root/'market-binding.json').exists()


@pytest.mark.parametrize('key,value',[
    ('GITHUB_REF','refs/heads/other'),('GITHUB_RUN_ATTEMPT','2'),
    ('GITHUB_REPOSITORY','other/repo'),('TRIAL_PURPOSE','stock-dump'),
    ('GITHUB_EVENT_NAME','push'),
])
def test_missing_field_does_not_bypass_execution_identity(monkeypatch,tmp_path,key,value):
    root=configure(monkeypatch,tmp_path,'');monkeypatch.setenv(key,value)
    assert code()['main'](['init','--root',str(root)])==2
    assert not root.exists() and not (tmp_path/'step-output').exists()


def test_existing_output_is_not_reused_as_a_new_failed_attempt(monkeypatch,tmp_path):
    root=configure(monkeypatch,tmp_path,'');root.mkdir();(root/'sentinel').write_text('keep')
    assert code()['main'](['init','--root',str(root)])==2
    assert {p.name for p in root.iterdir()}=={'sentinel'}
    assert (root/'sentinel').read_text()=='keep' and not (tmp_path/'step-output').exists()


def stock_job():
    text=Path('.github/workflows/hithink-stock-dump-trial.yml').read_text()
    return text.split('  stock-reading:\n',1)[1].split('  theme-probe:\n',1)[0]


def test_workflow_does_not_replay_skipped_capture_and_uploads_only_created_diagnostics():
    job=stock_job()
    replay=job.split('id: stock-verify\n',1)[1].split('      - name:',1)[0]
    upload=job.split('id: stock-evidence\n',1)[1].split('      - name:',1)[0]
    assert "if: always() && (steps.stock-capture.outcome == 'success' || steps.stock-capture.outcome == 'failure')" in replay
    assert "if: always() && steps.stock-intent.outputs.artifact_ready == 'true'" in upload
    assert "HITHINK_FINANCE_API_KEY: ''" in replay
    assert 'if-no-files-found: error' in upload and 'retention-days: 90' in upload
    assert job.count('${{ secrets.HITHINK_FINANCE_API_KEY }}')==1
    assert 'continue-on-error' not in job and 'contents: write' not in job
    assert "if: github.event_name == 'workflow_dispatch' && inputs.trial-purpose == 'stock-reading'" in job


def test_actual_summary_explains_not_started_and_does_not_invent_upload(monkeypatch,tmp_path):
    root=configure(monkeypatch,tmp_path,'')
    assert code()['main'](['init','--root',str(root)])==2
    for key,value in {'UPLOAD_RESULT':'failure','CAPTURE_RESULT':'skipped',
                      'VERIFY_RESULT':'skipped','ARTIFACT_URL':''}.items():
        monkeypatch.setenv(key,value)
    text=stock_job().split('      - name: Show stocks before technical details',1)[1]
    embedded=text.split("          python - <<'PY'\n",1)[1].split('\n          PY',1)[0]
    source='\n'.join(line.removeprefix('          ') for line in embedded.splitlines())
    exec(compile(source,'stock-workflow-summary','exec'),{})
    summary=(tmp_path/'step-summary').read_text()
    assert 'stock-market-run-id' in summary and '采集未开始' in summary
    assert '不是扫描后零匹配' in summary and '](' not in summary


def test_fresh_cli_process_reproduces_logged_empty_input(monkeypatch,tmp_path):
    root=configure(monkeypatch,tmp_path,'')
    env={k:v for k,v in os.environ.items() if k not in {'HITHINK_FINANCE_API_KEY','GH_TOKEN','GITHUB_TOKEN'}}
    env['PYTHONPATH']=str(Path('src').resolve())
    result=subprocess.run([sys.executable,'.github/scripts/capture-stock-reading.py','init','--root',str(root)],
                          env=env,text=True,capture_output=True,timeout=30,check=False)
    assert result.returncode==2,result.stderr
    assert json.loads(result.stdout)['reason_code']=='STOCK_MARKET_RUN_ID_REQUIRED'
    assert (root/'index.html').is_file() and not (root/'request.json').exists()
