"""Bounded, pure NewsNow history; fetch clocks never become publication clocks.

The native artifact carries the exact preceding index and recovery receipt, so
one transition is replayable. Earlier rows are a native producer's retained
index, not a claim that every historical HTTP body was re-read this round.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import re

from ..identity import canonical_hash
from . import current_state as m
from . import external_radar_observations as news

HISTORY_VERSION = 'native-newsnow-rolling-v2'
HISTORY_FILE = 'history.json'
HISTORY_INPUT = 'history-input.json'
RECOVERY_FILE = 'history-recovery.json'
HISTORY_HOURS = 18
MAX_HISTORY_OBSERVATIONS = 2000
MAX_HISTORY_CAPTURES = 120
MAX_HISTORY_BYTES = 2 * 1024 * 1024
MEANING = 'CAPTURE_FIRST_SEEN_ROLLING_INDEX_NOT_PUBLISHER_TIME_OR_COMPLETE_NEWS'
LOSS_KINDS = {'OBSERVATION_LIMIT', 'CAPTURE_LIMIT', 'PREDECESSOR_GAP', 'LOSS_LOG_LIMIT'}


def _seal(p):
    return {'projection': p, 'projection_hash': canonical_hash(p)}


def _observation(row):
    from . import news_daily as source
    keys = {'source_id', 'item_id', 'url', 'title', 'publication_claims', 'article_id',
            'version_id', 'window_position', 'clock_origin', 'fetched_at',
            'business_linkage', 'question_status', 'qualification'}
    m.check(isinstance(row, dict) and set(row) == keys, 'News history observation shape')
    label = row['source_id']
    m.check(label in source.SOURCES and isinstance(row['item_id'], str)
            and 0 < len(row['item_id']) <= 256 and isinstance(row['title'], str)
            and 0 < len(row['title'].strip()) <= 8192, 'News history observation identity')
    news._url(row['url'], news.NEWS_DOMAINS[label])
    fetched = m.clock(row['fetched_at'])
    claims = row['publication_claims']
    m.check(isinstance(claims, dict) and set(claims) == {'pubDate', 'extra.date'},
            'News history publication claims')
    for claim in claims.values():
        m.check(isinstance(claim, dict) and 'raw' in claim
                and claim == news._claim(claim['raw'], fetched), 'News history claim differs')
    identity = {k: row[k] for k in ('source_id', 'item_id', 'url')}
    version = {**identity, 'title': row['title'],
               'publication_claims': {k: v['raw'] for k, v in claims.items()}}
    m.check(row['article_id'] == canonical_hash(identity)
            and row['version_id'] == canonical_hash(version), 'News history observation hash differs')
    expected_clock = ('RELATIVE_TIME_DERIVED_BY_SOURCE_ADAPTER' if label == 'gelonghui'
                      else 'SERVICE_PASSTHROUGH_NOT_VERIFIED_PUBLISHER_TIME')
    m.check(row['clock_origin'] == expected_clock and row['qualification'] == 'CONTEXT_ONLY'
            and row['business_linkage'] == 'NOT_ESTABLISHED' and row['question_status'] == 'NOT_FORMED'
            and type(row['window_position']) is int and 0 <= row['window_position'] < 30,
            'News history observation qualification differs')


def _summary(current):
    p = current['projection']; w = p['workflow']
    return {'run_id': w['run_id'], 'code_commit': w['code_commit'], 'event': w['event'],
            'captured_from': p['captured_from'], 'captured_through': p['captured_through'],
            'capture_hash': p['capture_hash'], 'status': p['status'],
            'source_outcomes': [{'source_id': x['source_id'], 'status': x['status'],
                                 'observations_in_window': x.get('observations_in_window')}
                                for x in p['source_outcomes']]}


def validate_history(value):
    from . import news_daily as source
    m.check(isinstance(value, dict) and set(value) == {'projection', 'projection_hash'},
            'News history wrapper differs')
    p = value['projection']
    m.check(isinstance(p, dict) and value['projection_hash'] == canonical_hash(p),
            'News history hash differs')
    m.check(set(p) == {'version', 'window_hours', 'generated_at', 'window_start', 'retained_since',
                      'captures', 'observations', 'losses', 'status', 'coverage', 'semantics'} | set(source.AUTHORITY)
            and p['version'] == HISTORY_VERSION and p['window_hours'] == HISTORY_HOURS
            and p['semantics'] == MEANING
            and all(p[k] == v for k, v in source.AUTHORITY.items()), 'News history contract differs')
    end = m.clock(p['generated_at']); start = m.clock(p['window_start'])
    m.check(start == end - timedelta(hours=HISTORY_HOURS)
            and m.clock(p['retained_since']) <= end, 'News history window differs')
    m.check(isinstance(p['captures'], list) and 0 < len(p['captures']) <= MAX_HISTORY_CAPTURES
            and isinstance(p['observations'], list) and len(p['observations']) <= MAX_HISTORY_OBSERVATIONS
            and isinstance(p['losses'], list) and len(p['losses']) <= MAX_HISTORY_CAPTURES,
            'News history budget differs')
    ids = set(); previous = None
    statuses = {'OBSERVATIONS_NORMALIZED', 'RESPONSE_UNAVAILABLE', 'SOURCE_UNAVAILABLE',
                'SOURCE_REPRESENTATION_REJECTED'}
    for row in p['captures']:
        m.check(set(row) == {'run_id', 'code_commit', 'event', 'captured_from', 'captured_through',
                            'capture_hash', 'status', 'source_outcomes'}, 'News capture summary shape')
        m.check(type(row['run_id']) is int and row['run_id'] > 0 and row['run_id'] not in ids
                and m.SHA.fullmatch(row['code_commit']) is not None
                and re.fullmatch(r'[a-f0-9]{64}', row['capture_hash']) is not None
                and row['event'] in {'schedule', 'workflow_dispatch', 'workflow_run'},
                'News capture summary identity')
        a, b = m.clock(row['captured_from']), m.clock(row['captured_through'])
        m.check(a <= b <= end and b >= start and (previous is None or previous <= a),
                'News capture summary chronology')
        outcomes = row['source_outcomes']
        m.check(isinstance(outcomes, list) and [x['source_id'] for x in outcomes] == list(source.SOURCES),
                'News history source inventory')
        for x in outcomes:
            n = x['observations_in_window']
            m.check(set(x) == {'source_id', 'status', 'observations_in_window'} and x['status'] in statuses
                    and ((type(n) is int and 0 <= n <= 30) if x['status'] == 'OBSERVATIONS_NORMALIZED'
                         else n is None), 'News history source outcome')
        good = sum(x['status'] == 'OBSERVATIONS_NORMALIZED' for x in outcomes)
        expected = 'WINDOWS_CAPTURED' if good == 7 else 'PARTIAL_NEWS_WINDOWS' if good else 'NEWS_SOURCE_UNAVAILABLE'
        m.check(row['status'] == expected, 'News history capture status')
        ids.add(row['run_id']); previous = b
    m.check(previous == end, 'News history tail differs')
    versions = set()
    for entry in p['observations']:
        m.check(set(entry) == {'observation', 'first_seen_at', 'last_seen_at', 'first_seen_run_id',
                             'last_seen_run_id', 'seen_capture_count'}, 'News history entry shape')
        row = entry['observation']; _observation(row)
        a, b = m.clock(entry['first_seen_at']), m.clock(entry['last_seen_at'])
        m.check(a == m.clock(row['fetched_at']) and a <= b <= end and b >= start
                and type(entry['seen_capture_count']) is int and entry['seen_capture_count'] > 0
                and all(type(entry[k]) is int and entry[k] > 0
                        for k in ('first_seen_run_id', 'last_seen_run_id'))
                and row['version_id'] not in versions, 'News history entry chronology')
        versions.add(row['version_id'])
    for loss in p['losses']:
        m.check(set(loss) == {'at', 'run_id', 'kind', 'count'} and loss['kind'] in LOSS_KINDS
                and type(loss['count']) is int and loss['count'] > 0
                and type(loss['run_id']) is int and loss['run_id'] > 0
                and start <= m.clock(loss['at']) <= end, 'News history loss record')
    m.check(p['coverage'] == _coverage(p), 'News history coverage differs')
    expected_status = ('ROLLING_HISTORY_LIMITED' if p['losses'] else
                       'ROLLING_HISTORY_STARTED' if m.clock(p['retained_since']) > start else
                       'ROLLING_HISTORY_READY')
    m.check(p['status'] == expected_status, 'News history status differs')
    return value


def _coverage(p):
    start = m.clock(p['window_start'])
    ends = [start] + [m.clock(x['captured_through']) for x in p['captures']]
    starts = [max(start, m.clock(x['captured_from'])) for x in p['captures']]
    return {'capture_count': len(p['captures']), 'observation_count': len(p['observations']),
            'dropped_observation_count': sum(x['count'] for x in p['losses'] if x['kind'] == 'OBSERVATION_LIMIT'),
            'dropped_capture_count': sum(x['count'] for x in p['losses'] if x['kind'] == 'CAPTURE_LIMIT'),
            'loss_count_meaning': 'RETAINED_DROP_OPERATIONS_NOT_DISTINCT_ARTICLES',
            'maximum_capture_gap_seconds': max([0] + [max(0, int((a-b).total_seconds()))
                                                    for a, b in zip(starts, ends)]),
            'source_gap_capture_count': sum(x['status'] != 'WINDOWS_CAPTURED' for x in p['captures']),
            'complete_news_coverage': False}


def rolling_history(current, previous_raw=None, recovery=None):
    from . import news_daily as source
    m.check(isinstance(current, dict) and current.get('projection_hash') == canonical_hash(current.get('projection')),
            'News current projection differs')
    p = current['projection']; summary = _summary(current)
    finish = m.clock(p['captured_through']); start = finish - timedelta(hours=HISTORY_HOURS)
    previous = None
    if previous_raw is not None:
        m.check(isinstance(previous_raw, bytes) and 0 < len(previous_raw) <= MAX_HISTORY_BYTES,
                'News previous history bytes')
        previous = validate_history(news._decode(previous_raw))['projection']
        m.check(m.clock(previous['generated_at']) <= m.clock(p['captured_from'])
                and summary['run_id'] not in {x['run_id'] for x in previous['captures']},
                'News history predecessor is not a distinct earlier run')
    if recovery is not None:
        m.check(isinstance(recovery, dict) and recovery.get('version') == 'news-history-recovery-v1'
                and recovery.get('status') in {'RESTORED', 'NO_PRIOR_CAPTURE', 'NO_SUCCESS_IN_WINDOW', 'RECOVERY_REJECTED'}
                and (recovery['status'] == 'RESTORED') == (previous is not None),
                'News recovery state differs')
        m.check(recovery['current_run_id'] == summary['run_id']
                and m.clock(recovery['checked_at']) <= m.clock(p['captured_from']),
                'News recovery/current binding differs')
        m.check(recovery['history_sha256'] == (m.sha256(previous_raw) if previous_raw is not None else None),
                'News recovered history bytes differ')
        if previous is not None:
            selected = recovery['selected_capture']; tail = previous['captures'][-1]
            m.check(recovery['status'] == 'RESTORED' and selected['id'] == tail['run_id']
                    and selected['head_sha'] == tail['code_commit'], 'News recovery predecessor differs')
    captures = [deepcopy(x) for x in (previous or {}).get('captures', [])
                if m.clock(x['captured_through']) >= start]
    rows = {x['observation']['version_id']: deepcopy(x)
            for x in (previous or {}).get('observations', []) if m.clock(x['last_seen_at']) >= start}
    losses = [deepcopy(x) for x in (previous or {}).get('losses', []) if m.clock(x['at']) >= start]
    retained_since = previous['retained_since'] if previous else p['captured_from']

    def loss(kind, count):
        if count:
            losses.append({'at': p['captured_through'], 'run_id': summary['run_id'], 'kind': kind, 'count': count})
    if recovery and (recovery['status'] in {'RECOVERY_REJECTED', 'NO_SUCCESS_IN_WINDOW'}
                     or recovery.get('newer_unusable_attempts')):
        loss('PREDECESSOR_GAP', max(1, len(recovery.get('newer_unusable_attempts', []))))
    captures.append(summary)
    loss('CAPTURE_LIMIT', max(0, len(captures) - MAX_HISTORY_CAPTURES))
    captures = captures[-MAX_HISTORY_CAPTURES:]
    for row in p['news']['projection']['observations'] if p.get('news') else []:
        _observation(row); key = row['version_id']; fetched = row['fetched_at']
        if key not in rows:
            rows[key] = {'observation': deepcopy(row), 'first_seen_at': fetched, 'last_seen_at': fetched,
                         'first_seen_run_id': summary['run_id'], 'last_seen_run_id': summary['run_id'],
                         'seen_capture_count': 1}
        else:
            entry = rows[key]
            m.check(m.clock(entry['last_seen_at']) <= m.clock(fetched), 'News last-seen reversed')
            entry['last_seen_at'] = fetched; entry['last_seen_run_id'] = summary['run_id']
            entry['seen_capture_count'] += 1
    ordered = sorted(rows.values(), key=lambda x: (m.clock(x['last_seen_at']), x['observation']['version_id']), reverse=True)
    initial_count = len(ordered); ordered = ordered[:MAX_HISTORY_OBSERVATIONS]
    initial_losses = deepcopy(losses)

    def seal():
        kept_losses = deepcopy(initial_losses)
        removed = initial_count - len(ordered)
        if removed:
            kept_losses.append({'at': p['captured_through'], 'run_id': summary['run_id'],
                                'kind': 'OBSERVATION_LIMIT', 'count': removed})
        if len(kept_losses) > MAX_HISTORY_CAPTURES:
            count = len(kept_losses) - MAX_HISTORY_CAPTURES + 1
            kept_losses = kept_losses[-(MAX_HISTORY_CAPTURES-1):] + [
                {'at': p['captured_through'], 'run_id': summary['run_id'], 'kind': 'LOSS_LOG_LIMIT', 'count': count}]
        payload = {'version': HISTORY_VERSION, 'window_hours': HISTORY_HOURS,
                   'generated_at': p['captured_through'], 'window_start': start.isoformat(),
                   'retained_since': retained_since, 'captures': captures,
                   'observations': sorted(ordered, key=lambda x: (m.clock(x['first_seen_at']), x['observation']['version_id'])),
                   'losses': kept_losses, 'semantics': MEANING, **source.AUTHORITY}
        payload['coverage'] = _coverage(payload)
        payload['status'] = ('ROLLING_HISTORY_LIMITED' if kept_losses else
                             'ROLLING_HISTORY_STARTED' if m.clock(retained_since) > start else 'ROLLING_HISTORY_READY')
        return _seal(payload)
    result = seal()
    while len(m.json_bytes(result)) > MAX_HISTORY_BYTES and ordered:
        ordered = ordered[:-max(1, len(ordered)//10)]
        result = seal()
    m.check(len(m.json_bytes(result)) <= MAX_HISTORY_BYTES, 'News history byte budget')
    return validate_history(result)


def build_history(current, previous_raw=None, recovery=None):
    """A rejected predecessor limits history, never the newly captured raw windows."""
    from . import news_daily as source
    try:
        m.check(previous_raw is None or recovery is not None, 'News predecessor provenance missing')
        return rolling_history(current, previous_raw, recovery)
    except (*source.ERRORS, AttributeError, IndexError):
        if previous_raw is None and recovery is None:
            raise
        p = current['projection']
        rejected = {'version': 'news-history-recovery-v1', 'status': 'RECOVERY_REJECTED',
                    'current_run_id': p['workflow']['run_id'], 'checked_at': p['captured_from'],
                    'history_sha256': None, 'newer_unusable_attempts': []}
        return rolling_history(current, recovery=rejected)


def replay_history(files, current):
    """Rebuild the last transition using manifest-bound exact predecessor bytes."""
    plan = news._decode(files['plan.json'])
    if plan.get('rolling_history_version') is not None:
        m.check(plan['rolling_history_version'] == HISTORY_VERSION and HISTORY_FILE in files,
                'News declared rolling output missing')
    else:
        m.check(not ({HISTORY_FILE, HISTORY_INPUT, RECOVERY_FILE} & set(files)),
                'News undeclared history contract')
    previous = files.get(HISTORY_INPUT)
    recovery = news._decode(files[RECOVERY_FILE]) if RECOVERY_FILE in files else None
    result = build_history(current, previous, recovery)
    if HISTORY_FILE in files:
        m.check(0 < len(files[HISTORY_FILE]) <= MAX_HISTORY_BYTES, 'News saved history byte budget')
        m.check(news._decode(files[HISTORY_FILE]) == result, 'News rolling transition replay differs')
    return result
