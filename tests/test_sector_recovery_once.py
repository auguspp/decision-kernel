"""Current peer/budget boundaries, not re-execution of the retired gap capture.

Original capture/replay code and tests are retained at the pre-retirement Git
commit recorded in docs/CI-MAINLINE.md. No current reader imports that script.
"""
from pathlib import Path


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


def test_consumed_recovery_has_no_launcher_and_normal_budget_is_unchanged():
    assert not Path('.github/workflows/sector-recovery-once.yml').exists()
    assert not Path('.github/scripts/capture-sector-recovery.py').exists()
    for path in Path('.github/workflows').glob('*.yml'):
        assert 'capture-sector-recovery.py' not in path.read_text()
    from decision_kernel.runtime.sector_radar_audit import MAX_REQUESTS
    assert MAX_REQUESTS==128
