"""Current peer/budget boundaries, not re-execution of the retired gap capture.

Original capture/replay code and tests are retained at the pre-retirement Git
commit recorded in docs/CI-MAINLINE.md. No current reader imports that script.
"""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_existing_activity_checker_accepts_explicit_extra_peers():
    import runpy
    from urllib.parse import parse_qs,urlsplit
    c=runpy.run_path('.github/scripts/check-sector-scheduled-activity.py')
    path='.github/workflows/sector-member-reading.yml';calls=[]
    def read(url):
        calls.append(url); status=parse_qs(urlsplit(url).query)['status'][0]
        rows=[{'id':1,'path':path,'status':status}] if status=='in_progress' else []
        return {'total_count':len(rows),'workflow_runs':rows}
    assert c['check_activity'](read)==[] and len(calls)==5
    assert c['check_activity'](read,peers=c['PEERS']|{path})==[1] and len(calls)==10


def test_retired_execution_surfaces_stay_absent_without_reviving_old_writers(tmp_path):
    workflows = Path('.github/workflows')
    assert not Path('.github/workflows/sector-recovery-once.yml').exists()
    assert not Path('.github/scripts/capture-sector-recovery.py').exists()
    assert not Path('.github/workflows/incremental-disclosure-intake.yml').exists()
    assert not Path('.github/workflows/saved-research-once.yml').exists()

    combined = "\n".join(
        path.read_text() for path in (*workflows.glob('*.yml'), *workflows.glob('*.yaml'))
    )
    for retired in (
        'capture-sector-recovery.py',
        '-m decision_kernel.runtime.incremental_disclosure_intake',
        'research_runs/disclosure-intake-request.json',
        'decision_kernel.runtime.saved_research_once',
        'prepared_disclosure_research',
    ):
        assert retired not in combined

    # Frozen input remains readable; no production launcher owns it.
    assert json.loads(Path('research_runs/api-once-request.json').read_bytes())['id'] == 'p0-suken-api-20260910-v2'

    from decision_kernel.runtime import saved_research_once as once
    assert not any(hasattr(once, name) for name in ('run', 'main', 'acquire', 'checked_request'))
    assert not hasattr(once.Retainer, 'begin')
    out = tmp_path / 'retired'
    env = {k: v for k, v in os.environ.items()
           if k not in {'GH_TOKEN', 'GITHUB_TOKEN', 'SUB2API_API_KEY', 'DEEPSEEK_API_KEY'}}
    result = subprocess.run(
        [sys.executable, '-m', once.__name__, '--code-commit', 'a' * 40, '--output', str(out)],
        capture_output=True, text=True, timeout=10, check=False, env=env)
    assert result.returncode == 1 and 'SAVED_ONE_SHOT_RETIRED' in result.stderr
    assert not out.exists()

    from decision_kernel.runtime.sector_radar_audit import MAX_REQUESTS
    assert MAX_REQUESTS == 128
