"""B1 saved-source attachment: native GitHub archives -> fixed R, never prices.

The two source families remain independent. A failed/latest attempt does not
replace an older byte-verified capture or turn it into a current observation.
Historical archives are replayed with their original admission metadata, not
claimed to remain downloadable from Actions after expiry.
"""
from __future__ import annotations

from copy import deepcopy
import json

from ..identity import canonical_hash
from . import current_state as m, current_state_delivery as delivery
from . import global_market_context as source
from .institutional_radar_reading import _reserve, ERRORS

VERSION = 'global-market-reading-v1'
REPORT = 'details/markets/global-market.json'
DETAIL = 'details/markets/global-market.md'
QUERY = 'actions/workflows/radar-global-market.yml/runs?branch=main&per_page=20'
TITLES = {f'global-market / {f}': f for f in source.FAMILIES}
MAX_LEGACY_LOOKUPS = 4
RUN_KEYS = ('id', 'path', 'head_sha', 'head_branch', 'event', 'run_attempt',
            'status', 'conclusion', 'created_at', 'updated_at', 'run_started_at',
            'html_url', 'display_title', 'repository', 'head_repository')
IDENTITY_KEYS = ('id', 'path', 'head_sha', 'head_branch', 'event', 'run_attempt', 'created_at')


def check_run(run, cutoff):
    m.check(run.get('repository', {}).get('full_name') == m.REPOSITORY
            and run.get('head_repository', {}).get('full_name') == m.REPOSITORY
            and run.get('path') == source.WORKFLOW and run.get('head_branch') == 'main'
            and run.get('event') == 'workflow_dispatch'
            and type(run.get('id')) is int and run['id'] > 0
            and type(run.get('run_attempt')) is int and run['run_attempt'] >= 1
            and m.SHA.fullmatch(run.get('head_sha', '')) is not None,
            'Global market run identity differs')
    m.check(m.clock(run['created_at']) <= m.clock(run['updated_at']) <= m.clock(cutoff),
            'Global market run chronology differs')


def expected(run):
    return {'repository': m.REPOSITORY, 'workflow': source.WORKFLOW,
            'ref': 'refs/heads/main', 'event': run['event'], 'code_commit': run['head_sha'],
            'run_id': run['id'], 'attempt': run['run_attempt']}


def rebuild(files, run, family, cutoff):
    check_run(run, cutoff)
    report = source.replay(files, expected(run), cutoff)
    m.check(report['family'] == family, 'Global market family differs')
    m.check(m.clock(run['created_at']) <= m.clock(report['captured_from'])
            <= m.clock(report['captured_through']) <= m.clock(run['updated_at']),
            'Global market capture outside run')
    # Optional checkpoint files may not contain summaries. When present, they
    # must equal the original deterministic replay; they are not trusted input.
    if 'summary.json' in files:
        m.check(source.encoded(report) == files['summary.json'], 'Global market saved summary differs')
    if 'summary.md' in files:
        m.check(source.render(report).encode() == files['summary.md'], 'Global market saved text differs')
    return report


def bound(c, ref, commit):
    m.check(isinstance(commit, str) and m.SHA.fullmatch(commit), 'Global market prior R required')
    m.check(ref['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT', 'Global market prior ref rule')
    raw = c.api.file(m.safe_path(ref['read_path']), commit)
    m.check(len(raw) == ref['bytes'] and m.sha256(raw) == ref['sha256']
            and m.blob_sha(raw) == ref['git_blob'], 'Global market prior bytes differ')
    return raw


def prior(c):
    """Reuse only exact previously published bytes; never search older green runs."""
    entry = (c.previous or {}).get('research', {}).get('global_market', {})
    ref = entry.get('details', {}).get('json')
    snapshots, gaps = {}, []
    if not ref:
        return snapshots, gaps
    try:
        _reserve(c, calls=3, files=2)
        raw = bound(c, ref, c.previous_commit)
        value = json.loads(raw)
        p = value['projection']
        m.check(value['projection_hash'] == canonical_hash(p) and p['version'] == VERSION
                and p['authority'] == source.AUTHORITY
                and set(p['families']) == set(source.FAMILIES)
                and m.clock(p['checked_at']) <= m.clock(c.now()), 'Global market prior format')
    except ERRORS as exc:
        return {}, [{'stage': 'PRIOR_REPORT', 'error_type': type(exc).__name__,
                     'reading_commit': c.previous_commit, 'source': ref}]
    for family in source.FAMILIES:
        item = p['families'][family].get('snapshot')
        if not item:
            continue
        before = dict(c.files)
        try:
            _reserve(c, calls=1, files=1)
            raw_zip = bound(c, item['archive'], c.previous_commit)
            # artifact_at_read is the historical admission record, deliberately
            # not a statement about the artifact's current expiry/availability.
            files = m.unpack_archive(raw_zip, item['artifact_at_read'], item['run'])
            report = rebuild(files, item['run'], family, c.now())
            m.check(report == item['report'] and report['available_values'] > 0,
                    'Global market prior replay differs')
            meta = c.retain(item['archive']['read_path'], raw_zip)
            snapshots[family] = {**deepcopy(item), 'archive': {**item['archive'], **meta}}
        except ERRORS as exc:
            c.files = before
            gaps.append({'stage': 'PRIOR_CAPTURE', 'family': family, 'error_type': type(exc).__name__,
                         'reading_commit': c.previous_commit, 'source': item.get('archive')})
    return snapshots, gaps


def discover(c):
    _reserve(c, calls=5, files=0)
    page = c.api.get(QUERY)
    runs = page['workflow_runs']
    m.check(isinstance(runs, list) and len(runs) <= 20 and type(page['total_count']) is int
            and page['total_count'] >= len(runs) and (runs or page['total_count'] == 0)
            and len({r['id'] for r in runs}) == len(runs), 'Global market run query incomplete')
    for run in runs:
        check_run(run, c.now())
    selected, artifacts, unknown = {}, {}, []
    legacy_reads = 0
    for run in sorted(runs, key=lambda r: (m.clock(r['created_at']), r['id']), reverse=True):
        family = TITLES.get(run.get('display_title'))
        if family is None:
            # #610 predates family-bearing run-name. Its exact artifact name is
            # the only accepted legacy hint; no guessed inputs or shared clock.
            if legacy_reads >= MAX_LEGACY_LOOKUPS:
                unknown.append(run['id'])
                continue
            legacy_reads += 1
            _reserve(c, calls=1, files=0)
            rows = c.artifacts(run)
            hints = [f for f in source.FAMILIES if any(a.get('name') ==
                     f"global-market-{f}-{run['id']}-{run['run_attempt']}" for a in rows)]
            if len(hints) != 1:
                unknown.append(run['id'])
                continue
            family = hints[0]
            artifacts[run['id']] = rows
        selected.setdefault(family, run)
        if len(selected) == len(source.FAMILIES):
            break
    return selected, artifacts, {'limit': 20, 'total_count': page['total_count'],
        'examined': len(runs), 'unattributed_run_ids': unknown,
        'meaning': 'BOUNDED_LATEST_ATTEMPTS_NOT_ALL_HISTORY'}


def family_read(c, family, selected, artifacts, previous):
    state = {'latest_attempt': m.concise_run(selected), 'latest_read_status': 'NOT_SEEN_IN_QUERY',
             'snapshot': previous, 'latest_capture_status': None, 'latest_outcomes': [],
             'latest_archive': None, 'error_type': None}
    if selected is None:
        return state
    before_files, before_cache = dict(c.files), dict(c.archive_cache)
    try:
        _reserve(c, calls=3, files=1)
        run = c.api.get('actions/runs/' + str(selected['id']))
        check_run(run, c.now())
        m.check(all(run[k] == selected[k] for k in IDENTITY_KEYS), 'Global market run changed')
        state['latest_attempt'] = m.concise_run(run)
        if run['run_attempt'] != 1:
            state['latest_read_status'] = 'RERUN_NOT_ADMITTED'
            return state
        if run['status'] != 'completed':
            state['latest_read_status'] = 'CAPTURE_IN_PROGRESS'
            return state
        # Same original capture is already in Git. Do not require an unexpired
        # Actions artifact to keep reading it; no source fetch or new quote.
        if previous and all(previous['run'][k] == run[k] for k in
                            (*IDENTITY_KEYS, 'status', 'conclusion', 'updated_at')):
            report, archive = previous['report'], previous['archive']
            state['latest_read_status'] = 'REUSED_RETAINED_CAPTURE'
        else:
            rows = artifacts.get(run['id'])
            if rows is None:
                rows = c.artifacts(run)
            artifact = m.select_artifact(rows, f"global-market-{family}-{run['id']}-1")
            files, archive = c.archive(artifact, run)
            report = rebuild(files, run, family, c.now())
            state['latest_read_status'] = ('CAPTURE_READ' if run['conclusion'] == 'success'
                                           else 'FAILED_RUN_CAPTURE_READ')
            if report['available_values']:
                state['snapshot'] = {'run': {k: deepcopy(run.get(k)) for k in RUN_KEYS},
                    'artifact_at_read': deepcopy(artifact), 'archive': archive,
                    'report': report, 'retained_at': c.now()}
        state.update(latest_capture_status=report['status'], latest_archive=archive,
                     latest_outcomes=[{k: r[k] for k in ('id', 'status', 'attempt_count')}
                                      for r in report['outcomes']])
    except ERRORS as exc:
        c.files, c.archive_cache = before_files, before_cache
        state.update(latest_read_status='CAPTURE_UNAVAILABLE_OR_REJECTED', error_type=type(exc).__name__)
    return state


def render(report):
    p = report['projection']
    m.check(report['projection_hash'] == canonical_hash(p), 'Global market reading hash')
    lines = ['# 全球市场 · 已保存的有限观察', '',
             '第三方 Tushare Relay；不是实时行情或已研究的经济原因。Shibor是人民币同业利率，不是美债。',
             '最新尝试与最后可读批次分开；日期不统一成今日，空白或失败不等于没有变化。', '']
    for family, state in p['families'].items():
        lines += ['## ' + ('国际指数' if family == 'indices' else '人民币同业利率'),
                  '本次读取：' + state['latest_read_status'], '']
        snapshot = state['snapshot']
        if snapshot:
            lines += ['最后可读批次run：' + str(snapshot['run']['id']),
                      source.render(snapshot['report']),
                      '[原始ZIP](../../' + m.safe_path(snapshot['archive']['read_path']) + ')', '']
        else:
            lines.append('本包无已核验可读批次；不表示没有市场变化。')
    lines += ['美债/国际利率、黄金原油、外汇与加密资产尚未覆盖；没有自动启动Quick或Odds。']
    return '\n'.join(lines) + '\n'


def attach(c, baseline):
    m.validate_read_package(baseline)
    original_files, original_cache = dict(c.files), dict(c.archive_cache)
    research = deepcopy(baseline['research'])
    try:
        old, gaps = prior(c)
        try:
            selected, artifacts, query = discover(c)
        except ERRORS as exc:
            selected, artifacts = {}, {}
            query = {'status': 'QUERY_UNAVAILABLE', 'error_type': type(exc).__name__}
        states = {f: family_read(c, f, selected.get(f), artifacts, old.get(f)) for f in source.FAMILIES}
        if query.get('status') == 'QUERY_UNAVAILABLE':
            for state in states.values():
                state['latest_read_status'] = 'QUERY_UNAVAILABLE'
        p = {'version': VERSION, 'checked_at': c.now(), 'families': states, 'query': query,
             'prior_read_gaps': gaps, 'authority': deepcopy(source.AUTHORITY),
             'source_calls': 0, 'complete_global_coverage': False,
             'meaning': 'SAVED_SOURCE_REPLAY_NOT_CURRENT_QUOTES_OR_RESEARCH'}
        report = {'projection': p, 'projection_hash': canonical_hash(p)}
        raw = m.json_bytes(report)
        m.check(len(raw) <= 256 * 1024, 'Global market reading body bound')
        _reserve(c, files=2)
        research['global_market'] = {'version': VERSION, 'checked_at': p['checked_at'],
            'status': 'SAVED_CONTEXT' if any(s['snapshot'] for s in states.values()) else 'UNAVAILABLE',
            'projection_hash': report['projection_hash'], 'complete_global_coverage': False,
            'details': {'json': c.retain(REPORT, raw), 'markdown': c.retain(DETAIL, render(report).encode())},
            **source.AUTHORITY}
    except ERRORS as exc:
        c.files, c.archive_cache = original_files, original_cache
        research['global_market'] = {'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
            'meaning': 'READ_GAP_NOT_NO_MARKET_CHANGE', **source.AUTHORITY}
    payload = m.assemble(code_commit=c.code_commit, checked_at=c.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    note = ('\n[全球市场：国际指数与人民币同业利率，含各自日期与缺口](' + DETAIL + ')；不是实时行情。\n'
            if 'details' in research['global_market'] else '\n全球市场保存资料读取受阻；不代表没有市场变化。\n')
    replacements = {'current-state.json': m.read_package_bytes(payload),
                    'README.md': c.files['README.md'] + note.encode()}
    m.check(sum(len(v) for k, v in c.files.items() if k not in replacements)
            + sum(map(len, replacements.values())) <= delivery.MAX_RETAINED_OUTPUT, 'Global market retention budget')
    _reserve(c, replacements=replacements)
    c.files.update(replacements)
    return payload
