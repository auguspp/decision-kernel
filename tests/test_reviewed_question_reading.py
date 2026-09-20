"""Original host/validator round trips; synthetic Git/model only, no live Research."""
from copy import deepcopy
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import current_state_delivery_with_odds_watch as production
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_question_continuation as continuation
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_research_reading as legacy
from decision_kernel.runtime.read_blob_reuse import GitHubReadReuseAPI
from test_saved_research_once import pre, quick
from test_stock_question_host import setup_question
from test_stock_question_continuation import setup_continuation


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('saved question reader must not access networking')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)


def collector(args, tmp_path, *, stock=True):
    api = args['api']
    api.calls = 0
    api.max_calls = delivery.MAX_API_CALLS + legacy.EXTRA_API_CALLS
    lanes = {'stock': {'health': 'LATEST_ATTEMPT_SUCCEEDED', 'gaps': [],
        'last_qualified_result': {'market_session': '2026-09-18',
            'coverage': {'planned_issuers': 3, 'qualified_issuers': 1},
            'dispositions': [
                {'thscode': '000920.SZ', 'company_name': 'Synthetic current stock',
                 'status': 'CONTRACT_CHECKED_RAW_READING', 'input_failure': None},
                {'thscode': '600127.SH', 'company_name': 'Synthetic gap', 'status': 'UNAVAILABLE',
                 'input_failure': {'reason_code': 'CURRENT_QUOTE_HISTORY_MISMATCH'}},
                {'thscode': '000019.SZ', 'company_name': 'Synthetic other',
                 'status': 'CONDITIONS_NOT_MET', 'input_failure': None}],
            'projection_hash': 'e' * 64, 'archive': {'origin_run': {'id': 101}}}}} if stock else {}
    payload = model.assemble(code_commit=args['code'], checked_at=args['clock'](),
        check_started_at=args['clock'](), lanes=lanes,
        research={'handoffs': {'active': []}, 'records': [], 'gaps': [],
                  'candidate_work': {'status': 'READ_OK', 'items': []},
                  'stock_business_work': {'status': 'READ_OK', 'items': []}},
        capabilities=[], refresh_identity={})
    c = delivery.Collector(api, args['code'], tmp_path, now=args['clock'])
    c.files = {'current-state.json': model.json_bytes(payload),
               'README.md': model.render_summary(payload).encode(),
               'old-market.bin': b'original unrelated saved market'}
    return c, payload


def completed(tmp_path, monkeypatch, *, route='WAIT_FOR_TRIGGER', failure=False, stock=True):
    args, api, request, q, context, pf, calls, writes, prefix = setup_question(tmp_path, monkeypatch)
    def call(stage, prompt, schema, output, usage):
        calls.append(stage)
        if failure:
            raise RuntimeError('SYNTHETIC_SECRET_DO_NOT_DISPLAY')
        return pre(prompt, route) if stage == 'pre' else quick(prompt)
    args['call'] = call
    result = host.run_question(**args)
    assert result['status'] == ('EXECUTION_GAP' if failure else 'VALIDATED_FUNNEL_RESULT'), result
    c, payload = collector(args, tmp_path, stock=stock)
    return args, c, payload, prefix, calls, writes


def report(c, result):
    entry = result['research']['reviewed_question_work']
    assert 'items' not in entry  # All rows remain in the same-R detail, not the index.
    spec = entry['structured']
    assert spec['read_path'] == reader.REPORT
    raw = c.files[spec['read_path']]
    assert len(raw) == spec['bytes'] and once.sha(raw) == spec['sha256']
    assert once.blob(raw) == spec['git_blob']
    return json.loads(raw)


@pytest.mark.parametrize('route', ['WAIT_FOR_TRIGGER', 'STOP', 'CONTINUE_TO_QUICK'])
@pytest.mark.parametrize('stock', [True, False])
def test_original_result_survives_current_price_membership_and_absent_stock(
        tmp_path, monkeypatch, route, stock):
    args, c, baseline, prefix, calls, writes = completed(tmp_path, monkeypatch, route=route, stock=stock)
    saved = deepcopy(c.api.files[c.api.heads[intake.WORK_REF]])
    before_calls, before_writes = list(calls), len(writes)
    result = reader.attach(c, baseline)
    assert result['research']['reviewed_question_work']['status'] == 'READ_OK', result
    work = report(c, result)['question_work']
    assert len(work['items']) == 1
    item = work['items'][0]
    actual = json.loads(saved[prefix + 'validation.json'])['funnel_result']
    assert item['thscode'] == '600184.SH'
    assert item['terminal_state'] == actual['terminal_state']
    assert item['terminal_stage'] == actual['terminal_stage']
    assert item['quick_present'] == (route == 'CONTINUE_TO_QUICK')
    assert item['status'] == 'VALIDATED_FUNNEL_RESULT'
    assert result['pending'] == [] and not item['registered_current_handoff']
    assert item['semantic_acceptance'] == 'NOT_ESTABLISHED_BY_READER'
    assert result['lanes'] == baseline['lanes']
    assert c.files['old-market.bin'] == b'original unrelated saved market'
    assert calls == before_calls and len(writes) == before_writes
    assert c.api.files[c.api.heads[intake.WORK_REF]] == saved
    for spec in item['sources'].values():
        raw = c.files[spec['read_path']]
        assert model.blob_sha(raw) == spec['git_blob'] and once.sha(raw) == spec['sha256']
        assert len(raw) == spec['bytes']
    model.validate_read_package(result)


def test_original_execution_gap_remains_gap_not_business_wait(tmp_path, monkeypatch):
    _, c, baseline, _, _, _ = completed(tmp_path, monkeypatch, failure=True)
    result = reader.attach(c, baseline)
    work = report(c, result)['question_work']
    assert work['status'] == 'READ_OK', work
    row = work['items'][0]
    assert row['status'] == 'VALIDATED_EXECUTION_GAP'
    assert row['terminal_state'] is None and row['gap_reason']
    assert 'SYNTHETIC_SECRET_DO_NOT_DISPLAY' not in c.files[reader.DETAIL].decode()


def test_fixed_technical_child_and_original_failure_are_both_retained(tmp_path, monkeypatch):
    args, api, _, _, _, _, calls, writes, parent, pred = setup_continuation(tmp_path, monkeypatch)
    result = continuation.run_continuation(**args)
    assert result['status'] == 'VALIDATED_FUNNEL_RESULT', result
    c, baseline = collector(args, tmp_path, stock=False)
    before = deepcopy(api.files[api.heads[intake.WORK_REF]])
    call_count, write_count = len(calls), len(writes)
    result = reader.attach(c, baseline)
    work = report(c, result)['question_work']
    assert work['status'] == 'READ_OK', work
    byrole = {r['role']: r for r in work['items']}
    assert byrole['ROOT']['status'] == 'VALIDATED_EXECUTION_GAP'
    child = byrole['TECHNICAL_CONTINUATION']
    assert child['terminal_state'] == 'WAIT_FOR_TRIGGER'
    assert child['predecessor_execution_id'] == byrole['ROOT']['execution_id']
    assert len(calls) == call_count and len(writes) == write_count
    assert api.files[api.heads[intake.WORK_REF]] == before
    assert result['pending'] == []


@pytest.mark.parametrize('damage', ['candidate', 'input', 'validation', 'launch', 'host', 'funnel',
                                   'receipt', 'prepare', 'missing-input', 'missing-prepare', 'wrong-question'])
def test_corrupt_or_unbound_result_is_explicit_not_silently_absent(tmp_path, monkeypatch, damage):
    _, c, baseline, prefix, _, _ = completed(tmp_path, monkeypatch)
    files = c.api.files[c.api.heads[intake.WORK_REF]]
    if damage.startswith('missing-'):
        del files[prefix + damage.removeprefix('missing-') + '.json']
    elif damage == 'wrong-question':
        prep = json.loads(files[prefix + 'prepare.json'])
        spec = prep['question_source']
        c.api.files[spec['ref']][spec['path']] += b' '
    else:
        name = {'host': 'host-receipt'}.get(damage, damage) + '.json'
        files[prefix + name] = b'{}'
    result = reader.attach(c, baseline)
    work = report(c, result)['question_work']
    assert work['status'] == 'READ_OK_WITH_QUESTION_GAPS', work
    assert work['items'][0]['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert work['items'][0]['terminal_state'] is None
    assert result['lanes'] == baseline['lanes'] and result['pending'] == []


def test_partial_prepare_is_not_a_completed_research_result(tmp_path, monkeypatch):
    _, c, baseline, prefix, _, _ = completed(tmp_path, monkeypatch)
    files = c.api.files[c.api.heads[intake.WORK_REF]]
    for path in list(files):
        if path.startswith(prefix) and path != prefix + 'prepare.json':
            del files[path]
    result = reader.attach(c, baseline)
    row = report(c, result)['question_work']['items'][0]
    assert row['status'] == 'RETAINED_NO_RESEARCH_RESULT' and row['terminal_state'] is None


def test_absent_host_receipt_does_not_invent_write_completion(tmp_path, monkeypatch):
    _, c, baseline, prefix, _, _ = completed(tmp_path, monkeypatch)
    del c.api.files[c.api.heads[intake.WORK_REF]][prefix + 'host-receipt.json']
    result = reader.attach(c, baseline)
    row = report(c, result)['question_work']['items'][0]
    assert row['status'] == 'VALIDATED_FUNNEL_RESULT'
    assert row['host_receipt_present'] is False


@pytest.mark.parametrize('damage', ['truncated', 'oversize', 'symlink', 'renamed-child', 'duplicate-path', 'source-limit'])
def test_inventory_and_original_shared_capacity_fail_closed(tmp_path, monkeypatch, damage):
    _, c, baseline, prefix, _, _ = completed(tmp_path, monkeypatch)
    original = c.api.get
    def get(path):
        value = original(path)
        if path.startswith('git/trees/'):
            if damage == 'truncated': value['truncated'] = True
            else:
                row = next(r for r in value['tree'] if r['path'] == prefix + 'prepare.json')
                if damage == 'oversize': row['size'] = 512 * 1024 + 1
                elif damage == 'symlink': row['mode'] = '120000'
                elif damage == 'renamed-child': row['path'] = prefix + 'technical-continuation-v2/prepare.json'
                elif damage == 'duplicate-path': value['tree'].append(deepcopy(row))
        return value
    c.api.get = get
    if damage == 'source-limit':
        research = deepcopy(baseline['research'])
        research['stock_business_work'] = {'items': [
            {'sources': {str(i): {'read_path': f'sources/git/legacy-{i}/input.json'} for i in range(32)}}]}
        baseline = model.assemble(code_commit=baseline['code_commit'], checked_at=baseline['generated_at'],
            check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'],
            research=research, capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    result = reader.attach(c, baseline)
    entry = result['research']['reviewed_question_work']
    assert entry['status'] == 'UNAVAILABLE_OR_REJECTED' and entry['execution_count'] is None
    assert c.files['old-market.bin'] == b'original unrelated saved market'
    assert reader.DETAIL not in c.files
    assert 'UNAVAILABLE' in c.files['README.md'].decode()
    assert result['lanes'] == baseline['lanes']


def test_no_api_space_does_not_silently_publish_complete_read(tmp_path, monkeypatch):
    _, c, baseline, _, _, _ = completed(tmp_path, monkeypatch)
    c.api.calls = c.api.max_calls
    before = deepcopy(c.files)
    with pytest.raises(ValueError):
        reader.attach(c, baseline)
    assert c.files == before


def test_newest_stock_batch_not_reviewed_is_not_zero_questions(tmp_path, monkeypatch):
    _, c, baseline, _, _, _ = completed(tmp_path, monkeypatch)
    result = reader.attach(c, baseline)
    scope = report(c, result)['stock_review_scope']
    assert len(scope['items']) == 3
    assert [r['review_status'] for r in scope['items']] == [
        'QUESTION_REVIEW_REQUIRED', 'DATA_UNAVAILABLE_NOT_PRICE_REJECTED', 'ORIGINAL_PRICE_DISPOSITION_ONLY']
    assert scope['reviewed_question_count'] == 0
    assert scope['meaning'] == 'OBSERVATION_PROMPTS_AND_EXISTING_RELATIONS_NOT_FORMAL_QUESTION_OR_EXECUTION'
    assert scope['question_review_required_count'] == 1
    assert scope['existing_baseline_gap_count'] == 0
    assert not any(r['economic_question_assessed'] or r['research_execution_allowed'] for r in scope['items'])
    changed = deepcopy(baseline)
    changed['generated_at'] = '2030-01-01T00:00:00Z'
    assert reader.stock_review_scope(changed)['batch_id'] == scope['batch_id']


def test_existing_baseline_source_gap_is_visible_and_not_retried_as_new_question(tmp_path, monkeypatch):
    _, c, baseline, _, _, _ = completed(tmp_path, monkeypatch)
    research = deepcopy(baseline['research'])
    research['stock_business_work'] = {'status': 'READ_OK', 'items': [{
        'thscode': '000920.SZ', 'status': 'PRE_EXECUTION_FAILURE',
        'question_kind': 'FIRST_BUSINESS_BASELINE', 'execution_id': 'stock-business-' + 'a' * 64,
        'failure_status': 'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE',
        'error_type': 'CninfoPdfHttpError', 'error_code': None,
        'terminal_state': None, 'finished_at': '2026-09-18T10:31:13+00:00',
        'sources': {'failure': {'read_path': 'sources/git/failure.json'}}}]}
    changed = model.assemble(code_commit=baseline['code_commit'], checked_at=baseline['generated_at'],
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'],
        research=research, capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    observations = {'000920.SZ': {'current_origins': [{
        'direction_sources': [{'family': 'GRANULAR_884', 'name': '膜材料', 'thscode': '884213.TI'}],
        'review_question': 'If decision-relevant, what public evidence establishes or rejects the business link?'}]}}
    scope = reader.stock_review_scope(changed, observations, 'SAME_READING_STOCK_OBSERVATIONS')
    row = scope['items'][0]
    assert row['review_status'] == 'EXISTING_BASELINE_SOURCE_OR_INPUT_GAP'
    assert row['existing_research_relation']['error_type'] == 'CninfoPdfHttpError'
    assert row['distinct_question_assessment'] == 'NOT_PERFORMED'
    assert row['research_execution_allowed'] is False and row['economic_question_assessed'] is False
    assert '膜材料' in row['origin_question_prompts'][0]
    assert scope['existing_baseline_gap_count'] == 1 and scope['question_review_required_count'] == 0


def test_markup_remains_data_in_the_read_surface():
    report = {'stock_review_scope': {'status': 'UNKNOWN', 'items': []}, 'question_work': {
        'status': 'READ_OK', 'items': [{'status': 'PARTIAL', 'thscode': '<script>bad</script>',
            'question': '[execute](https://untrusted.invalid)\n# run', 'sources': {}}]}}
    text = reader.render(report)
    assert '<script>' not in text and '[execute]' not in text and '&lt;script&gt;' in text


def test_existing_production_collector_opts_in_without_a_second_publisher(tmp_path, monkeypatch):
    _, c, baseline, _, _, _ = completed(tmp_path, monkeypatch)
    monkeypatch.setattr(delivery.Collector, 'collect', lambda self, refresh: deepcopy(baseline))
    p = production.Collector(c.api, c.code_commit, tmp_path, now=c.now)
    p.files = deepcopy(c.files)
    assert 'reviewed_question_work' not in p.collect({})['research']
    p.include_reviewed_questions = True
    result = p.collect({})
    assert result['research']['reviewed_question_work']['status'] == 'READ_OK'
    assert len(report(p, result)['question_work']['items']) == 1
    assert 'old-market.bin' in p.files
    root = Path(__file__).parents[1]
    workflow = (root / '.github/workflows/current-state-read-entry.yml').read_text()
    assert '--include-reviewed-questions' in workflow
    assert 'schedule:' not in workflow and 'DEEPSEEK_API_KEY' not in workflow


def test_near_full_original_index_keeps_rows_in_hash_bound_details(tmp_path, monkeypatch):
    _, c, baseline, _, _, _ = completed(tmp_path, monkeypatch)
    research = deepcopy(baseline['research'])
    research['synthetic_existing_payload'] = 'x' * 187000
    baseline = model.assemble(code_commit=baseline['code_commit'], checked_at=baseline['generated_at'],
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'],
        research=research, capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    before_size = len(model.json_bytes(baseline))
    assert before_size > 185000
    c.files['current-state.json'] = model.json_bytes(baseline)
    result = reader.attach(c, baseline)
    after_size = len(model.json_bytes(result))
    assert after_size < 192 * 1024 and after_size - before_size < 3000
    assert len(report(c, result)['question_work']['items']) == 1
    assert result['research']['synthetic_existing_payload'] == research['synthetic_existing_payload']


def test_real_sized_prior_reading_uses_proven_blob_write_count_not_file_count():
    api = GitHubReadReuseAPI('SYNTHETIC', max_calls=252)
    api.calls = 230
    files = {f'prior/{i}.json': f'kept-{i}'.encode() for i in range(475)}
    api.proven_read_blobs = frozenset(model.blob_sha(raw) for raw in files.values())
    c = SimpleNamespace(api=api, files=files)
    reader._reserve(c, new_files=3)
    assert len(c.files) == 475
    changed = dict(files)
    changed['new.json'] = b'new-value'
    c.files = changed
    reader._reserve(c, new_files=2)
