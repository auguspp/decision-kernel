"""Use original daily/source/admission fixtures; no live source or model calls."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import stock_daily_preparation as prep
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_question_continuation as deepseek
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import saved_research_once as once
from test_stock_daily_question import setup_daily, refresh


def entries(case):
    return {name: {k: case.request[name + '_source'][k] for k in ('ref', 'path')}
            for name in prep.SELECTORS}


def run(case, output, selectors=None):
    return prep.prepare(api=case.api, code=case.args['code'], selectors=entries(case) if selectors is None else selectors,
                        output=output, clock=case.args['clock'])


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('only synthetic Git and existing native functions in preparation tests')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def test_three_saved_records_derive_exact_five_sources_without_changing_them(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    before = deepcopy(case.api.files)
    draft = prep.assemble(prep.ReadOnlyGit(case.api), entries(case))
    expected = {**case.request, 'enabled': False}
    assert draft == expected
    assert case.api.files == before and not case.calls and not case.writes
    draft['permission']['comment_id'] = 0
    assert daily.PERMISSION['comment_id'] == 5748820065


@pytest.mark.parametrize('route,expected_calls', [('STOP', ['pre']), ('WAIT_FOR_TRIGGER', ['pre']),
                                                  ('CONTINUE_TO_QUICK', ['pre', 'quick'])])
def test_draft_passes_original_host_only_after_separate_synthetic_activation(tmp_path, monkeypatch, route, expected_calls):
    case = setup_daily(tmp_path, monkeypatch, route=route)
    # The current request is disabled while preparing. Preparation must not need to turn it on.
    case.api.files[case.args['code']][daily.REQUEST] = once.raw({**case.request, 'enabled': False})
    before, heads = deepcopy(case.api.files), deepcopy(case.api.heads)
    directory = tmp_path / 'draft'
    report = run(case, directory)
    assert report['status'] == prep.SUCCESS, report
    assert report['request_draft_written'] and report['phase'] == 'COMPLETE'
    assert report['original_preparation']['status'] == 'QUESTION_INPUT_PREPARED_NOT_EXECUTED'
    assert report['market_session'] == '2026-09-18' and report['case_id'] == '600184.SH'
    assert report['context_bytes'] == len(once.raw(case.context))
    assert report['pdf_bytes'] == len(case.pdf)
    assert not report['research_execution_allowed']
    assert report['remote_writes'] == report['model_calls'] == report['source_site_requests'] == report['daily_slots_consumed'] == 0
    assert report['permission_status'] == 'NOT_GRANTED_BY_PREPARATION'
    assert case.api.files == before and case.api.heads == heads
    assert case.calls == case.writes == [] and case.archive_calls == [1020]
    draft_raw = (directory / 'request.json').read_bytes()
    draft = json.loads(draft_raw)
    assert not draft['enabled'] and draft['approved_egress_hash'] is None
    assert report['request_sha256'] == once.sha(draft_raw)
    assert json.loads((directory / 'preparation.json').read_bytes()) == report
    assert {p.name for p in directory.iterdir()} == {'request.json', 'preparation.json'}
    # Test only: original authorization/request and model seams, never a real activation.
    case.api.files[case.args['code']][daily.REQUEST] = once.raw({**draft, 'enabled': True})
    actual = host.run_question(**case.args)
    assert actual['status'] == 'VALIDATED_FUNNEL_RESULT', actual
    assert case.calls == expected_calls
    assert report['execution_id'] == actual['execution_id']
    assert not json.loads((directory / 'request.json').read_bytes())['enabled']


@pytest.mark.parametrize('damage', ['missing-row', 'continuation', 'missing-page', 'artifact',
                                     'context-reference', 'consumed-root', 'policy', 'main'])
def test_native_rejections_produce_gap_and_never_export_an_executable_request(tmp_path, monkeypatch, damage):
    case = setup_daily(tmp_path, monkeypatch)
    if damage == 'missing-row':
        case.review['items'].pop(); refresh(case)
    elif damage == 'continuation':
        case.q['existing_research_relation']['kind'] = 'CONTINUE_ANALYSIS'; refresh(case)
    elif damage == 'missing-page':
        case.context['issuer_documents'][0]['pages'] = []; refresh(case)
    elif damage == 'artifact':
        case.artifact['digest'] = 'sha256:' + 'f' * 64
    elif damage == 'context-reference':
        case.custody['context']['sha256'] = 'f' * 64
        s = case.request['source_custody_source']
        case.api.files[s['ref']][s['path']] = once.raw(case.custody)
    elif damage == 'consumed-root':
        # setup_daily starts without a work branch; construct saved partial history.
        work = '7' * 40
        assert work not in case.api.files
        case.api.heads[intake.WORK_REF] = work
        case.api.files[work] = {case.prefix + 'failure.json': b'partial'}
    elif damage == 'policy':
        case.api.files[case.args['code']][daily.POLICY_PATH] = b'{}'
    else:
        case.api.heads['main'] = 'f' * 40
    before = deepcopy(case.api.files)
    directory = tmp_path / 'draft'
    report = run(case, directory)
    assert report['status'] == 'DAILY_INPUT_PREPARATION_GAP', report
    assert not report['request_draft_written'] and not (directory / 'request.json').exists()
    assert case.api.files == before and not case.calls and not case.writes
    assert report['research_execution_allowed'] is False
    assert (directory / 'preparation.json').is_file()
    if damage == 'consumed-root':
        assert report['error_code'] == 'DAILY_PREPARATION_QUESTION_ALREADY_CONSUMED'


def test_already_consumed_day_does_not_reserve_another_slot(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    assert host.run_question(**case.args)['status'] == 'VALIDATED_FUNNEL_RESULT'
    before, calls, writes = deepcopy(case.api.files), list(case.calls), list(case.writes)
    report = run(case, tmp_path / 'after-consumption')
    assert report['status'] == 'DAILY_INPUT_PREPARATION_GAP'
    assert case.api.files == before and case.calls == calls and case.writes == writes
    assert not report['request_draft_written']


@pytest.mark.parametrize('changed', ['main', 'work'])
def test_state_move_after_native_checks_invalidates_preview(tmp_path, monkeypatch, changed):
    case = setup_daily(tmp_path, monkeypatch)
    original = deepseek._deepseek_request
    work = '7' * 40
    assert work not in case.api.files
    def moving(*args, **kwargs):
        value = original(*args, **kwargs)
        if changed == 'main':
            case.api.heads['main'] = 'f' * 40
        else:
            previous = case.api.heads.get(intake.WORK_REF)
            case.api.files[work] = deepcopy(case.api.files[previous]) if previous else {}
            case.api.heads[intake.WORK_REF] = work
        return value
    monkeypatch.setattr(deepseek, '_deepseek_request', moving)
    report = run(case, tmp_path / 'draft')
    assert report['status'] == 'DAILY_INPUT_PREPARATION_GAP', report
    assert report['error_code'] == 'DAILY_PREPARATION_STATE_CHANGED'
    assert not report['request_draft_written'] and not case.calls and not case.writes


def test_existing_output_directory_is_not_overwritten_or_resumed(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    directory = tmp_path / 'existing'; directory.mkdir()
    (directory / 'request.json').write_bytes(b'OLD')
    before = deepcopy(case.api.files)
    with pytest.raises(ValueError):
        run(case, directory)
    assert (directory / 'request.json').read_bytes() == b'OLD'
    assert case.api.files == before and case.calls == case.writes == []


def test_arbitrary_exception_message_is_not_copied_to_gap(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    def fail(*args):
        raise RuntimeError('PRIVATE_CREDENTIAL_OR_SOURCE_BODY')
    monkeypatch.setattr(case.api, 'file', fail)
    report = run(case, tmp_path / 'draft')
    assert report['status'] == 'DAILY_INPUT_PREPARATION_GAP'
    assert 'PRIVATE' not in json.dumps(report)
    assert report['error_code'] == 'DAILY_INPUT_PREPARATION_REJECTED'


@pytest.mark.parametrize('value', ['main:x.json', 'a'*39+':x.json', 'a'*40+':../x',
                                    'a'*40+':/x', 'a'*40+':x//y', 'a'*40+':x\\y',
                                    'a'*40+':x?ref=main', 'a'*40+':x\n', 'a'*40+':'])
def test_non_exact_or_unsafe_selector_rejected(value):
    with pytest.raises(ValueError):
        prep.selector(value)


def test_exact_selector_and_no_write_methods():
    assert prep.selector('a'*40+':research_runs/example/preflight.json') == {
        'ref': 'a'*40, 'path': 'research_runs/example/preflight.json'}
    reader = prep.ReadOnlyGit(object())
    for name in ('native', 'save', 'put', 'post', 'delete', 'patch'):
        assert not hasattr(reader, name)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "get"])
def test_read_only_facade_rejects_mutation_methods(method):
    with pytest.raises(ValueError, match="DAILY_PREPARATION_READ_ONLY"):
        prep.ReadOnlyGit(object())._call(method, "contents/anything")
