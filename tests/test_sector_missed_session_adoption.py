from __future__ import annotations

import runpy
from pathlib import Path

import pytest


SCRIPT = Path('.github/scripts/adopt-sector-missed-session-20260914.py')
WORKFLOW = Path('.github/workflows/sector-radar-shadow.yml')


def module():
    return runpy.run_path(str(SCRIPT), run_name='sector_missed_session_adoption_test')


def step(raw: str, name: str) -> str:
    return raw.split(f'      - name: {name}\n', 1)[1].split('      - name: ', 1)[0]


def set_identity(monkeypatch, **changes):
    values = {
        'GITHUB_REPOSITORY': 'auguspp/decision-kernel',
        'GITHUB_REF': 'refs/heads/main',
        'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_RUN_ATTEMPT': '1',
        'GITHUB_RUN_ID': '12345',
        'GITHUB_SHA': 'a' * 40,
        'RECOVERY_OPERATION': 'adopt-missed-session-2026-09-14',
        'HITHINK_FINANCE_API_KEY': '',
    }
    values.update(changes)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_missed_session_adoption_is_exact_case_bound_and_reuses_offline_reconstruction():
    raw = SCRIPT.read_text(encoding='utf-8')
    m = module()
    assert m['OPERATION'] == 'adopt-missed-session-2026-09-14'
    assert m['TARGET_SESSION'].isoformat() == '2026-09-14'
    assert m['PARENT_RUN_ID'] == 34610140283
    assert m['PARENT_ARTIFACT_ID'] == 10268611038
    assert m['SOURCE_RUN_ID'] == 34868170673
    assert m['SOURCE_ARTIFACT_ID'] == 10358420687
    assert m['SOURCE_AUDIT_HASH'] == '788b8b89edd543026a6c0608ee61bfcc97c151257e44c115efe46ad30f971e69'
    assert m['CANDIDATE_STATE_HASH'] == 'fe869bf419d4b4a75095578caf422d873082605635c84f490832358c2c6a8109'
    assert m['CANDIDATE_CALCULATION_HASH'] == 'b661c6d16082f5b0d65505089a4682df6840b37e839acc58ba49f9630047fc9e'
    assert 'reconstruct_sector_prefix' in raw
    assert 'write_sector_radar_persistent_bundle' in raw
    assert 'import requests' not in raw
    assert 'urlopen' not in raw
    assert 'HITHINK_FINANCE_API_KEY' in raw
    assert 'natural_acceptance": False' in raw
    assert 'historical_stock_reconstructed": False' in raw


@pytest.mark.parametrize('change', [
    {'GITHUB_REPOSITORY': 'other/repo'},
    {'GITHUB_REF': 'refs/heads/feature'},
    {'GITHUB_EVENT_NAME': 'schedule'},
    {'GITHUB_RUN_ATTEMPT': '2'},
    {'RECOVERY_OPERATION': 'produce'},
    {'HITHINK_FINANCE_API_KEY': 'must-not-reach-adoption'},
    {'GITHUB_RUN_ID': '0'},
    {'GITHUB_SHA': 'not-a-sha'},
])
def test_missed_session_adoption_invocation_fails_closed(monkeypatch, change):
    set_identity(monkeypatch, **change)
    with pytest.raises(ValueError):
        module()['invocation']()


def test_missed_session_adoption_invocation_accepts_only_fresh_credential_free_main(monkeypatch):
    set_identity(monkeypatch)
    assert module()['invocation']() == {
        'run_id': 12345,
        'run_attempt': 1,
        'commit_sha': 'a' * 40,
    }


def test_original_sector_workflow_has_second_case_bounded_adoption_without_changing_produce():
    raw = WORKFLOW.read_text(encoding='utf-8')
    assert 'default: produce' in raw
    assert raw.count('adopt-missed-session-2026-09-14') >= 6
    download = step(raw, 'Download exact failed 2026-09-14 Sector run audit')
    adoption = step(raw, 'Adopt exact 2026-09-14 missed-session checkpoint')
    verify = step(raw, 'Verify 2026-09-14 missed-session adoption exact offline match')
    producer = step(raw, 'Run independent Sector Radar shadow producer')
    assert "artifact-ids: '10358420687'" in download
    assert "run-id: '34868170673'" in download
    assert 'digest-mismatch: error' in download
    assert "inputs.operation == 'adopt-missed-session-2026-09-14'" in adoption
    assert 'HITHINK_FINANCE_API_KEY: ""' in adoption
    assert 'adopt-sector-missed-session-20260914.py adopt' in adoption
    assert '--discovered-run-id' in adoption and '--discovered-artifact-id' in adoption and '--discovered-head-sha' in adoption
    assert 'if: success()' in verify
    assert 'adopt-sector-missed-session-20260914.py verify' in verify
    assert "inputs.operation == 'produce'" in producer
    assert '${{ secrets.HITHINK_FINANCE_API_KEY }}' in producer
    # The old 9/10 case remains separately explicit rather than generalized away.
    assert "adopt-recovery-2026-09-10" in raw


def test_missed_session_adoption_is_verified_before_authoritative_upload_and_cache():
    raw = WORKFLOW.read_text(encoding='utf-8')
    names = [
        'Download exact failed 2026-09-14 Sector run audit',
        'Adopt exact 2026-09-14 missed-session checkpoint',
        'Verify 2026-09-14 missed-session adoption exact offline match',
        'Upload complete run audit',
        'Upload authoritative state bundle',
        'Save cache acceleration copy',
    ]
    positions = [raw.index(name) for name in names]
    assert positions == sorted(positions)
    assert 'if: success()' in step(raw, 'Upload authoritative state bundle')
    assert 'if: success()' in step(raw, 'Save cache acceleration copy')
    assert 'group: sector-radar-prospective-state' in raw
    assert 'cancel-in-progress: false' in raw


def test_missed_session_summary_does_not_claim_natural_or_stock_recovery():
    summary = step(WORKFLOW.read_text(encoding='utf-8'), 'Publish separate shadow summary')
    assert 'Sector missed-session PIT reconstruction adoption' in summary
    assert 'no market/provider request' in summary
    assert 'Stock as NOT_RECONSTRUCTED' in summary
    assert 'does not rewrite the failed natural 9/14 run' in summary
    assert 'later ordinary Sector production run must separately prove' in summary
