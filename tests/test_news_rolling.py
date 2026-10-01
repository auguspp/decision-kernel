"""Synthetic rolling-news regressions; no claims of live source or delivery acceptance."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import news_daily as s, news_rolling as h, current_state as m
from test_news_daily import captured, body, IDENTITY, TIME, IMAGE, no_network


def recovery(raw, run_id, when, *, newer=None):
    previous = json.loads(raw)['projection']['captures'][-1]
    return {'version': 'news-history-recovery-v1', 'status': 'RESTORED',
            'current_run_id': run_id, 'checked_at': when, 'history_sha256': m.sha256(raw),
            'selected_capture': {'id': previous['run_id'], 'head_sha': previous['code_commit']},
            'newer_unusable_attempts': newer or []}


def next_capture(tmp_path, files, *, number=902, when='2026-09-20T04:10:00+00:00', request=None):
    raw = files[s.HISTORY_FILE]
    return captured(tmp_path, request, clock=lambda: when, previous_history=raw,
                    identity={**IDENTITY, 'run_id': number},
                    history_recovery=recovery(raw, number, when))


def empty(label):
    return 200, body(label, items=[])


def test_item_rolled_out_of_last_window_survives_with_original_capture_clock(tmp_path):
    _, first, _ = captured(tmp_path/'first')
    _, second, current = next_capture(tmp_path/'second', first, request=empty)
    assert current['projection']['news']['projection']['observations'] == []
    history = s.replay_history(second, current)['projection']
    assert history['coverage']['observation_count'] == 7
    assert all(x['first_seen_at'] == TIME == x['last_seen_at'] for x in history['observations'])
    assert second[s.HISTORY_INPUT] == first[s.HISTORY_FILE]
    assert history['coverage']['complete_news_coverage'] is False


def test_same_article_revision_is_distinct_but_republication_is_not(tmp_path):
    _, first, _ = captured(tmp_path/'first')
    def revise(label):
        val = json.loads(body(label))
        if label == 'cls':
            val['items'][0]['title'] += ' 更正'
        return 200, m.json_bytes(val)
    _, second, _ = next_capture(tmp_path/'second', first, request=revise)
    p = json.loads(second[s.HISTORY_FILE])['projection']
    cls = [x for x in p['observations'] if x['observation']['source_id'] == 'cls']
    assert len(cls) == 2
    assert len({x['observation']['article_id'] for x in cls}) == 1
    assert len({x['observation']['version_id'] for x in cls}) == 2
    unchanged = next(x for x in p['observations'] if x['observation']['source_id'] == 'jin10')
    assert unchanged['seen_capture_count'] == 2 and unchanged['first_seen_at'] == TIME
    assert unchanged['observation']['fetched_at'] == TIME
    assert unchanged['observation']['publication_claims']['pubDate']['parsed_at'] is None


def test_truncation_remains_visible_after_a_successful_nontruncating_capture(tmp_path, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(h, 'MAX_HISTORY_OBSERVATIONS', 2)
        _, first, _ = captured(tmp_path/'first')
    p1 = json.loads(first[s.HISTORY_FILE])['projection']
    assert p1['coverage']['dropped_observation_count'] == 5
    _, second, _ = next_capture(tmp_path/'second', first, request=empty)
    p2 = json.loads(second[s.HISTORY_FILE])['projection']
    assert p2['status'] == 'ROLLING_HISTORY_LIMITED'
    assert p2['coverage']['dropped_observation_count'] == 5
    assert p2['losses'] == p1['losses']
    later = '2026-09-21T04:10:00+00:00'
    _, third, _ = next_capture(tmp_path/'third', second, number=903, when=later, request=empty)
    p3 = json.loads(third[s.HISTORY_FILE])['projection']
    assert p3['losses'] == []
    assert p3['coverage']['maximum_capture_gap_seconds'] == 18 * 3600
    assert p3['coverage']['complete_news_coverage'] is False


def test_capture_summary_limit_is_explicit_not_silent_history_completeness(tmp_path, monkeypatch):
    _, first, _ = captured(tmp_path/'first')
    with monkeypatch.context() as patch:
        patch.setattr(h, 'MAX_HISTORY_CAPTURES', 1)
        _, second, _ = next_capture(tmp_path/'second', first, request=empty)
    p = json.loads(second[s.HISTORY_FILE])['projection']
    assert p['coverage']['capture_count'] == 1
    assert p['coverage']['dropped_capture_count'] == 1
    assert p['status'] == 'ROLLING_HISTORY_LIMITED'


def test_byte_pressure_keeps_a_loss_record_and_stays_within_bound(tmp_path, monkeypatch):
    _, first, _ = captured(tmp_path/'first')
    previous_size = len(first[s.HISTORY_FILE])
    with monkeypatch.context() as patch:
        patch.setattr(h, 'MAX_HISTORY_BYTES', previous_size - 1000)
        _, bounded, _ = captured(tmp_path/'bounded')
        assert len(bounded[s.HISTORY_FILE]) <= h.MAX_HISTORY_BYTES
    p = json.loads(bounded[s.HISTORY_FILE])['projection']
    assert p['coverage']['dropped_observation_count'] > 0
    assert p['status'] == 'ROLLING_HISTORY_LIMITED'


@pytest.mark.parametrize('damage', ['json', 'self-hash', 'authority', 'claim', 'future', 'same-run', 'receipt'])
def test_bad_predecessor_does_not_destroy_new_raw_windows(tmp_path, damage):
    _, first, _ = captured(tmp_path/'first')
    raw = first[s.HISTORY_FILE]; val = json.loads(raw)
    when = '2026-09-20T04:10:00+00:00'; number = 902
    receipt = recovery(raw, number, when)
    if damage == 'json': raw = b'not json'
    elif damage == 'self-hash': val['projection_hash'] = '0'*64
    elif damage == 'authority': val['projection']['research_authority'] = 'GRANTED'
    elif damage == 'claim':
        val['projection']['observations'][0]['observation']['publication_claims']['pubDate']['status'] = 'VERIFIED'
    elif damage == 'future': when = '2026-09-20T03:00:00+00:00'
    elif damage == 'same-run': number = 901
    else: receipt['selected_capture']['id'] = 999
    if damage not in {'json', 'future', 'same-run', 'receipt'}:
        if damage != 'self-hash': val['projection_hash'] = canonical_hash(val['projection'])
        raw = m.json_bytes(val)
    receipt.update(current_run_id=number, checked_at=when, history_sha256=m.sha256(raw))
    root, second, current = captured(tmp_path/'second', clock=lambda: when,
        previous_history=raw, history_recovery=receipt, identity={**IDENTITY, 'run_id': number})
    assert current['projection']['status'] == 'WINDOWS_CAPTURED'
    assert all('raw/newsnow-'+label+'.json' in second for label in s.SOURCES)
    assert s.rebuild(second, cutoff=when) == current
    p = s.replay_history(second, current)['projection']
    assert p['status'] == 'ROLLING_HISTORY_LIMITED'
    assert p['coverage']['capture_count'] == 1 and p['coverage']['observation_count'] == 7
    assert {x['kind'] for x in p['losses']} == {'PREDECESSOR_GAP'}


def test_partial_current_source_retains_history_without_certifying_it_as_fresh(tmp_path):
    _, first, _ = captured(tmp_path/'first')
    def partial(label):
        if label == 'cls': raise TimeoutError('not for publication')
        return empty(label)
    _, second, current = next_capture(tmp_path/'second', first, request=partial)
    p = s.replay_history(second, current)['projection']
    assert current['projection']['status'] == 'PARTIAL_NEWS_WINDOWS'
    assert p['coverage']['observation_count'] == 7
    assert p['coverage']['source_gap_capture_count'] == 1
    assert all(x['last_seen_at'] == TIME for x in p['observations'])


def test_rehashed_derived_history_is_not_a_replay_proof(tmp_path):
    _, first, _ = captured(tmp_path/'first')
    _, second, current = next_capture(tmp_path/'second', first)
    value = json.loads(second[s.HISTORY_FILE])
    value['projection']['observations'][0]['seen_capture_count'] += 1
    value['projection_hash'] = canonical_hash(value['projection'])
    # Structurally plausible, but not the actual transition from retained input.
    s.validate_history(value)
    second[s.HISTORY_FILE] = m.json_bytes(value)
    with pytest.raises(ValueError, match='transition replay'):
        s.replay_history(second, current)


def test_bootstrap_and_same_run_have_distinct_meanings(tmp_path):
    _, files, current = captured(tmp_path)
    p = s.replay_history(files, current)['projection']
    assert p['status'] == 'ROLLING_HISTORY_STARTED'
    assert p['retained_since'] == TIME
    assert m.clock(p['window_start']) == m.clock(TIME) - timedelta(hours=18)
    with pytest.raises(ValueError, match='distinct earlier run'):
        s.rolling_history(current, files[s.HISTORY_FILE])


def _workflow(filename):
    root = Path(__file__).resolve().parents[1]
    return yaml.safe_load((root/'.github/workflows'/filename).read_text())


def _admit(condition, github):
    # Only the checked-in workflow expression is evaluated; no provider text/code.
    expr = ' '.join(condition.split()).replace('&&', ' and ').replace('||', ' or ')
    return bool(eval(expr, {'__builtins__': {}}, {'github': github}))


@pytest.mark.parametrize('cron,expected', [('50 23 * * *', True), ('10 11 * * *', True), ('3/10 * * * *', False)])
def test_only_two_explicit_publication_clocks_are_admitted(cron, expected):
    workflow = _workflow('current-state-read-entry.yml')
    github = SimpleNamespace(repository=m.REPOSITORY, ref='refs/heads/main', run_attempt=1,
                             event_name='schedule', event=SimpleNamespace(schedule=cron))
    assert _admit(workflow['jobs']['publish-reading']['if'], github) is expected


@pytest.mark.parametrize('event,action,expected', [('schedule', 'completed', False),
    ('schedule', 'requested', False), ('workflow_dispatch', 'completed', True),
    ('workflow_dispatch', 'requested', False), ('workflow_run', 'completed', True)])
def test_high_frequency_capture_does_not_fan_out_read_model_publication(event, action, expected):
    workflow = _workflow('current-state-read-entry.yml')
    run = SimpleNamespace(name='radar-newsnow-daily', path=s.WORKFLOW, head_branch='main',
                          head_repository=SimpleNamespace(full_name=m.REPOSITORY),
                          run_attempt=1, event=event)
    github = SimpleNamespace(repository=m.REPOSITORY, ref='refs/heads/main', run_attempt=1,
                             event_name='workflow_run', event=SimpleNamespace(action=action, workflow_run=run))
    assert _admit(workflow['jobs']['publish-reading']['if'], github) is expected


def test_source_credentials_and_scheduled_publisher_ci_guard_are_separate():
    steps = _workflow('radar-newsnow-daily.yml')['jobs']['capture']['steps']
    recovery_step = next(x for x in steps if 'news_history_recovery' in x.get('run', ''))
    source_step = next(x for x in steps if 'docker run' in x.get('run', ''))
    assert steps.index(recovery_step) < steps.index(source_step)
    assert recovery_step['env']['GH_TOKEN'] == '${{ github.token }}'
    assert 'GH_TOKEN' not in source_step.get('env', {}) and 'GH_TOKEN' not in source_step['run']
    assert 'gh run download' not in '\n'.join(x.get('run', '') for x in steps)
    reader_steps = _workflow('current-state-read-entry.yml')['jobs']['publish-reading']['steps']
    guard = next(x for x in reader_steps if 'reading-ci.json' in x.get('run', ''))
    assert guard['if'] == "github.event_name == 'schedule'"
    assert "r['run_attempt'] == 1" in guard['run'] and "r['conclusion'] == 'success'" in guard['run']
    assert reader_steps.index(guard) < next(i for i, x in enumerate(reader_steps) if '--publish' in x.get('run', ''))
