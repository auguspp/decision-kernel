"""Current deployment versus immutable original daily policy; no live execution."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import re
import socket

import pytest

from decision_kernel.runtime import stock_quick_continuation as resume
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import current_state as reading

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / 'tests/fixtures/industry_quick_contract_20260923'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('activation contract tests cannot perform live I/O')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def saved_request():
    return json.loads((FIXTURE / 'quick-activation-request.json').read_bytes())


def check_resume_configuration(request):
    resume.check_request(request)
    permission = request['permission']
    assert set(permission) == {'comment_id', 'body_sha256', 'created_at'}
    assert type(permission['comment_id']) is int and permission['comment_id'] > 0
    assert re.fullmatch(r'[0-9a-f]{64}', permission['body_sha256'])
    reading.clock(permission['created_at'])
    pred = request['predecessor']; roots = set()
    for key, (name, purpose) in resume.previous.PREDECESSOR_FILES.items():
        spec = pred['sources'][key]
        assert set(spec) == {'repository', 'ref', 'path', 'git_blob', 'sha256', 'purpose'}
        assert spec['repository'] == once.REPO and spec['ref'] == pred['work_commit']
        assert reading.SHA.fullmatch(spec['git_blob']) and re.fullmatch(r'[0-9a-f]{64}', spec['sha256'])
        assert spec['purpose'] == purpose and spec['path'].endswith('/' + name)
        root = spec['path'][:-len(name)]
        assert re.fullmatch(r'research_runs/candidates/stock-questions/[0-9a-f]{64}/', root)
        roots.add(root)
    assert len(roots) == 1


def checked_daily_configuration(root):
    """Do not freeze a past deployment as permanent policy.

    Validate current corrective configuration in its own mode, then separately
    retain the original daily-policy assertions on the exact archived parent
    request. No monkeypatch, runtime fallback or substitute for native admission.
    The saved activation has dedicated original-host and exact-source tests.
    """
    request = json.loads((root / daily.REQUEST).read_bytes())
    if request['mode'] == resume.MODE:
        check_resume_configuration(request)
        return json.loads((root / 'tests/fixtures/industry_quick_contract_20260923/original-request.json').read_bytes())
    assert request['mode'] == daily.MODE
    return request


@pytest.mark.parametrize('key', sorted(resume.previous.PREDECESSOR_FILES))
def test_saved_activation_is_bound_to_each_exact_parent_file(key):
    request = saved_request(); check_resume_configuration(request)
    name, _ = resume.previous.PREDECESSOR_FILES[key]
    spec = request['predecessor']['sources'][key]
    raw = (FIXTURE / name).read_bytes()
    assert once.identity._checked_source(spec, lambda s: raw) == raw
    parent = once.ExternalResearchInputPacket.model_validate_json((FIXTURE / 'input.json').read_bytes())
    assert spec['path'] == parent.candidate_output_prefix + name
    assert request['predecessor']['run_id'] == 35819538967
    assert request['predecessor']['work_commit'] == '4b9988f20aa41810c6818d101e2bdb37cf139bde'


def test_saved_activation_permission_is_exact_recorded_scope_not_original_daily_permission():
    request = saved_request(); check_resume_configuration(request)
    body = (FIXTURE / 'quick-activation-permission.txt').read_bytes()
    assert once.sha(body) == request['permission']['body_sha256']
    assert request['permission']['comment_id'] == 5791078723
    assert request['permission']['created_at'] == '2026-09-23T07:46:56Z'
    assert request['permission'] != json.loads((FIXTURE / 'original-request.json').read_bytes())['permission']
    assert request['source_scope'] == resume.SOURCE_SCOPE


def test_saved_actual_activation_uses_original_host_with_only_synthetic_quick(tmp_path, monkeypatch):
    import test_stock_quick_continuation as fixture
    request = saved_request()
    stamp = (reading.clock(request['permission']['created_at']) + timedelta(minutes=1)).isoformat()
    monkeypatch.setattr(fixture, 'NOW', stamp)
    case = fixture.setup(tmp_path, monkeypatch)
    case.api.comment.update(id=request['permission']['comment_id'],
        created_at=request['permission']['created_at'],
        body=(FIXTURE / 'quick-activation-permission.txt').read_text())
    case.files[fixture.CODE][daily.REQUEST] = once.raw(request)
    before = deepcopy(case.files[fixture.WORK])
    result = host.run_question(**case.args)
    assert result['status'] == 'VALIDATED_FUNNEL_RESULT', json.dumps(result)
    assert case.calls == ['quick'] and result['pre_model_calls'] == 0
    assert case.files[fixture.WORK] == before
    assert all('/daily-stock-questions-v0/' not in path for path in case.writes)


def test_current_deployment_does_not_change_the_original_daily_policy():
    original = checked_daily_configuration(ROOT)
    assert original['mode'] == daily.MODE
    assert json.loads((ROOT / daily.POLICY_PATH).read_bytes()) == daily.POLICY
