"""Existing daily host -> reader: saved review is not a new execution or acceptance."""
from copy import deepcopy
import json
import socket

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_research_intake as intake
from test_stock_daily_question import setup_daily
from test_reviewed_question_reading import collector, report


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('saved delivery tests must not access networking')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def setup(tmp_path, monkeypatch, route='WAIT_FOR_TRIGGER'):
    case = setup_daily(tmp_path, monkeypatch, route=route)
    assert host.run_question(**case.args)['status'] == 'VALIDATED_FUNNEL_RESULT'
    c, _ = collector(case.args, tmp_path, stock=False)
    baseline = deepcopy(case.state)
    path = case.stock['details']['reading/stock-reading.json']['read_path']
    c.files[path] = case.api.files[case.q['reading_source']['ref']][path]
    c.files['current-state.json'] = model.json_bytes(baseline)
    c.files['README.md'] = model.render_summary(baseline).encode()
    return case, c, baseline


@pytest.mark.parametrize('route', ['STOP', 'WAIT_FOR_TRIGGER', 'CONTINUE_TO_QUICK'])
def test_actual_daily_review_appears_before_independent_baseline_without_new_execution(tmp_path, monkeypatch, route):
    case, c, baseline = setup(tmp_path, monkeypatch, route)
    before = deepcopy(case.api.files)
    calls, writes = list(case.calls), list(case.writes)
    expected_scope = reader.stock_review_scope(baseline, {r['thscode']: r for r in case.projection['all_stock_observations']}, 'SAME_READING_STOCK_OBSERVATIONS')
    result = reader.attach(c, baseline)
    value = report(c, result)
    saved = value['recorded_batch_review']
    assert saved['status'] == 'MATCHED_SAVED_DAILY_REVIEW', saved
    assert saved['items'] == case.review['items']
    assert saved['reviewed_object_count'] == 3 and saved['selected_question_count'] == 1
    assert saved['execution']['quick_present'] is (route == 'CONTINUE_TO_QUICK')
    assert not saved['research_execution_allowed'] and saved['investment_authority'] == 'NONE'
    assert value['stock_review_scope'] == expected_scope  # No rewritten price/baseline state.
    original = json.loads(case.api.files[case.api.heads[intake.WORK_REF]][case.prefix + 'funnel.json'])
    assert value['question_work']['items'][0]['terminal_state'] == original['terminal_state']
    source = saved['source']; raw = c.files[source['read_path']]
    assert raw == case.api.files[case.request['batch_review_source']['ref']][case.request['batch_review_source']['path']]
    assert once.sha(raw) == source['sha256'] and once.blob(raw) == source['git_blob']
    text = c.files[reader.DETAIL].decode()
    assert text.index('本批已记录的审阅与执行') < text.index('原始价格观察与首次业务状态')
    assert 'NOT_STARTED不表示该证券没有已执行的问题' in text
    assert '本批已记录 3 个对象' in c.files['README.md'].decode()
    assert result['pending'] == [] and result['lanes'] == baseline['lanes']
    model.validate_read_package(result)
    assert case.api.files == before and case.calls == calls and case.writes == writes


@pytest.mark.parametrize('damage', ['missing-review', 'changed-review', 'missing-host', 'host-scope', 'unbound-review', 'future-commit', 'wrong-commit'])
def test_review_gap_is_visible_without_discarding_a_valid_original_result(tmp_path, monkeypatch, damage):
    case, c, baseline = setup(tmp_path, monkeypatch)
    files = case.api.files[case.api.heads[intake.WORK_REF]]
    source = case.request['batch_review_source']
    if damage == 'missing-review':
        del case.api.files[source['ref']][source['path']]
    elif damage == 'changed-review':
        case.api.files[source['ref']][source['path']] += b' '
    elif damage == 'missing-host':
        del files[case.prefix + 'host-receipt.json']
    elif damage == 'host-scope':
        value = json.loads(files[case.prefix + 'host-receipt.json'])
        value['daily_scope']['reviewed_items'][0]['reason'] = 'changed'
        files[case.prefix + 'host-receipt.json'] = once.raw(value)
    elif damage == 'unbound-review':
        for name in ['launch.json', 'host-receipt.json']:
            value = json.loads(files[case.prefix + name])
            value['daily_scope']['batch_review_source']['sha256'] = '0' * 64
            files[case.prefix + name] = once.raw(value)
    elif damage == 'future-commit':
        case.commits[source['ref']]['committer']['date'] = '2027-01-01T00:00:00Z'
    else:
        case.commits[source['ref']]['sha'] = 'a' * 40
    candidate_before = files[case.prefix + 'candidate.json']
    calls, writes = list(case.calls), list(case.writes)
    result = reader.attach(c, baseline)
    value = report(c, result)
    assert value['recorded_batch_review']['status'] == 'UNAVAILABLE_OR_REJECTED', value['recorded_batch_review']
    assert value['recorded_batch_review']['selected_question_count'] is None
    assert value['question_work']['items'][0]['status'] == 'VALIDATED_FUNNEL_RESULT'
    assert value['question_work']['items'][0]['terminal_state'] == 'WAIT_FOR_TRIGGER'
    assert '本批审阅关联暂不可核验' in c.files[reader.DETAIL].decode()
    assert files[case.prefix + 'candidate.json'] == candidate_before
    assert case.calls == calls and case.writes == writes


@pytest.mark.parametrize('change', ['day', 'origin-run', 'projection'])
def test_other_batch_same_ticker_does_not_inherit_old_review(tmp_path, monkeypatch, change):
    case, c, baseline = setup(tmp_path, monkeypatch)
    stock = baseline['lanes']['stock']['last_qualified_result']
    if change == 'day': stock['market_session'] = '2026-09-19'
    elif change == 'origin-run': stock['archive']['origin_run']['id'] += 1
    else: stock['projection_hash'] = 'f' * 64
    baseline['reading_hash'] = canonical_hash({k: v for k, v in baseline.items() if k != 'reading_hash'})
    result = reader.attach(c, baseline)
    value = report(c, result)
    assert value['recorded_batch_review']['status'] == 'NO_MATCHING_SAVED_DAILY_REVIEW'
    assert value['recorded_batch_review']['selected_question_count'] is None
    assert value['question_work']['items'][0]['status'] == 'VALIDATED_FUNNEL_RESULT'
    assert '本批已记录的审阅与执行' not in c.files[reader.DETAIL].decode()


@pytest.mark.parametrize('damage', ['row-omission', 'ambiguous-review', 'file-budget', 'api-budget'])
def test_projection_rejects_incomplete_conflicting_or_overbudget_association(tmp_path, monkeypatch, damage):
    case, c, baseline = setup(tmp_path, monkeypatch)
    scope = reader.stock_review_scope(baseline)
    work = reader.collect(c, baseline)
    if damage == 'row-omission': scope['items'].pop()
    elif damage == 'ambiguous-review': work['items'].append(deepcopy(work['items'][0]))
    elif damage == 'file-budget':
        baseline['research']['stock_business_work'] = {'items': [{'sources': {
            str(i): {'read_path': 'synthetic-' + str(i)} for i in range(32)}}]}
    else: c.api.calls = c.api.max_calls
    old_files = dict(c.files)
    saved = reader._recorded_batch_review(c, baseline, scope, work)
    assert saved['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert saved['selected_question_count'] is None and saved['items'] == []
    assert c.files == old_files


def test_render_escapes_saved_review_text(tmp_path, monkeypatch):
    case, c, baseline = setup(tmp_path, monkeypatch)
    result = reader.attach(c, baseline)
    value = report(c, result)
    value['recorded_batch_review']['items'][0]['reason'] = '<script>untrusted</script> [action](https://invalid)'
    rendered = reader.render(value)
    assert '<script>' not in rendered and '[action]' not in rendered
    assert '&lt;script&gt;' in rendered


def test_rejected_question_files_still_consume_the_shared_budget(tmp_path, monkeypatch):
    case, c, baseline = setup(tmp_path, monkeypatch)
    files = case.api.files[case.api.heads[intake.WORK_REF]]
    # Nine core files plus one declaration for the good root, and 22 retained
    # files from rejected roots: the original 32-file budget is already full.
    names = sorted(reader.CORE)
    for index, count in enumerate((9, 9, 4)):
        prefix = reader.PREFIX + str(index + 1) * 64 + '/'
        for name in names[:count]:
            files[prefix + name] = once.raw({'invalid_record': index, 'name': name})
    result = reader.attach(c, baseline)
    value = report(c, result)
    assert sum(i['status'] == 'UNAVAILABLE_OR_REJECTED' for i in value['question_work']['items']) == 3
    assert sum(i['status'] == 'VALIDATED_FUNNEL_RESULT' for i in value['question_work']['items']) == 1
    assert value['recorded_batch_review']['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert value['recorded_batch_review']['selected_question_count'] is None
    assert not case.calls[2:]  # No extra calls during reading.
