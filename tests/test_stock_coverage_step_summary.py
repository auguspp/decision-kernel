"""Execute the workflow's real read-only summary body; no workflow dispatch."""
import json
from pathlib import Path
from textwrap import dedent

import pytest

from decision_kernel.runtime import stock_radar_reading as stock
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


@pytest.mark.parametrize('status,planned,evaluated,unavailable', [
    ('NO_USABLE_STOCK_DATA',4,0,4),
    ('NO_MATCH_IN_EVALUATED_SUBSET_WITH_DATA_GAPS',4,2,2),
    ('NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE',4,4,0),
    ('BUSINESS_COVERAGE_INSUFFICIENT',0,0,0),
])
def test_step_success_and_empty_cards_do_not_override_business_status(tmp_path,monkeypatch,status,planned,evaluated,unavailable):
    source = Path('.github/workflows/hithink-stock-dump-trial.yml').read_text()
    step = source.split('      - name: Show stocks before technical details\n',1)[1].split('  theme-probe:\n',1)[0]
    body = dedent(step.split("          python - <<'PY'\n",1)[1].rsplit('          PY',1)[0])
    root = tmp_path/'stock-reading-run'/'reading'; root.mkdir(parents=True)
    p = {'status':status,'coverage':{'planned_issuers':planned,'evaluated_issuers':evaluated,
         'conditions_not_met_issuers':evaluated,'unavailable_issuers':unavailable,
         'scope_complete':not unavailable},'market_session':'2026-09-07',
         'surfaced_stocks':[],'reviewed_issuers':planned,'unreviewed_current_members':[]}
    (root/'stock-reading.json').write_text(json.dumps({'projection':p}))
    summary = tmp_path/'summary.md'
    for key,value in {'RUNNER_TEMP':str(tmp_path),'GITHUB_STEP_SUMMARY':str(summary),
                      'UPLOAD_RESULT':'success','CAPTURE_RESULT':'success',
                      'VERIFY_RESULT':'success','ARTIFACT_URL':''}.items():
        monkeypatch.setenv(key,value)
    exec(compile(body,'workflow-stock-summary','exec'),{'__name__':'stock_summary_test'})
    text = summary.read_text()
    assert stock.STATUS_LABELS[status] in text
    assert f'已完成条件检查 {evaluated}' in text
    assert f'数据不可用 {unavailable}' in text
    assert ('不能称作全计划零匹配' in text) is bool(unavailable)
    assert '本范围没有通过条件的股票；不是市场没有机会。' not in text
