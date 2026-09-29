"""B1 saved-source attachment: existing Relay/public archives -> one fixed R.

Each workflow/family keeps its own latest attempt and last byte-verified capture.
No source calls, saved-code execution, price rebasing, or research authority.
"""
from __future__ import annotations

from copy import deepcopy
import json

from ..identity import canonical_hash
from . import current_state as m, current_state_delivery as delivery
from . import global_market_context as source, global_public_context as public
from .institutional_radar_reading import _reserve, ERRORS

LEGACY_VERSION = 'global-market-reading-v1'
VERSION = 'global-market-reading-v2'
REPORT = 'details/markets/global-market.json'
DETAIL = 'details/markets/global-market.md'
QUERY = 'actions/workflows/radar-global-market.yml/runs?branch=main&per_page=20'
PUBLIC_QUERY = 'actions/workflows/radar-global-public.yml/runs?branch=main&per_page=20'
FAMILIES = {'indices': '国际指数', 'shibor': '人民币同业利率', **public.FAMILIES}
TITLES = {f'global-market / {f}': f for f in source.FAMILIES}
MAX_LEGACY_LOOKUPS = 4
RUN_KEYS = ('id', 'path', 'head_sha', 'head_branch', 'event', 'run_attempt',
            'status', 'conclusion', 'created_at', 'updated_at', 'run_started_at',
            'html_url', 'display_title', 'repository', 'head_repository')
IDENTITY_KEYS = ('id', 'path', 'head_sha', 'head_branch', 'event', 'run_attempt', 'created_at')


def codec(family):
    m.check(family in FAMILIES, 'Global market family unsupported')
    return public if family in public.FAMILIES else source


def artifact_prefix(family):
    return 'global-public' if family in public.FAMILIES else 'global-market'


def check_run(run, cutoff, workflow=source.WORKFLOW):
    m.check(run.get('repository', {}).get('full_name') == m.REPOSITORY
            and run.get('head_repository', {}).get('full_name') == m.REPOSITORY
            and run.get('path') == workflow and run.get('head_branch') == 'main'
            and run.get('event') in {'workflow_dispatch', 'schedule'}
            and type(run.get('id')) is int and run['id'] > 0
            and type(run.get('run_attempt')) is int and run['run_attempt'] >= 1
            and m.SHA.fullmatch(run.get('head_sha', '')) is not None,
            'Global market run identity differs')
    m.check(m.clock(run['created_at']) <= m.clock(run['updated_at']) <= m.clock(cutoff),
            'Global market run chronology differs')


def expected(run):
    return {'repository': m.REPOSITORY, 'workflow': run['path'],
            'ref': 'refs/heads/main', 'event': run['event'], 'code_commit': run['head_sha'],
            'run_id': run['id'], 'attempt': run['run_attempt']}


def rebuild(files, run, family, cutoff):
    module = codec(family)
    check_run(run, cutoff, module.WORKFLOW)
    report = module.replay(files, expected(run), cutoff)
    m.check(report['family'] == family, 'Global market family differs')
    m.check(m.clock(run['created_at']) <= m.clock(report['captured_from'])
            <= m.clock(report['captured_through']) <= m.clock(run['updated_at']),
            'Global market capture outside run')
    if 'summary.json' in files:
        m.check(module.encoded(report) == files['summary.json'], 'Global market saved summary differs')
    if 'summary.md' in files:
        m.check(module.render(report).encode() == files['summary.md'], 'Global market saved text differs')
    # Source replay can retain Decimal metadata (for example Yahoo meta prices).
    # Use its already-verified native canonical representation at this JSON seam:
    # exact decimal strings, no float conversion, dropped fields or raw rewriting.
    # Apply on fresh AND prior replay so later Git recovery compares like with like.
    return json.loads(module.encoded(report))


def bound(c, ref, commit):
    m.check(isinstance(commit, str) and m.SHA.fullmatch(commit), 'Global market prior R required')
    m.check(ref['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT', 'Global market prior ref rule')
    raw = c.api.file(m.safe_path(ref['read_path']), commit)
    m.check(len(raw) == ref['bytes'] and m.sha256(raw) == ref['sha256']
            and m.blob_sha(raw) == ref['git_blob'], 'Global market prior bytes differ')
    return raw


def prior(c):
    """V1 two-family and V2 six-family Git custody; no older-green-run search."""
    entry = (c.previous or {}).get('research', {}).get('global_market', {})
    ref = entry.get('details', {}).get('json')
    snapshots, gaps = {}, []
    if not ref:
        return snapshots, gaps
    try:
        _reserve(c, calls=1, files=0)
        raw = bound(c, ref, c.previous_commit)
        value = json.loads(raw)
        p = value['projection']
        allowed = {LEGACY_VERSION: set(source.FAMILIES), VERSION: set(FAMILIES)}
        m.check(value['projection_hash'] == canonical_hash(p) and p['version'] in allowed
                and p['authority'] == source.AUTHORITY
                and set(p['families']) == allowed[p['version']]
                and m.clock(p['checked_at']) <= m.clock(c.now()), 'Global market prior format')
    except ERRORS as exc:
        return {}, [{'stage': 'PRIOR_REPORT', 'error_type': type(exc).__name__,
                     'reading_commit': c.previous_commit, 'source': ref}]
    for family, state in p['families'].items():
        item = state.get('snapshot')
        if not item:
            continue
        before = dict(c.files)
        try:
            _reserve(c, calls=1, files=1)
            raw_zip = bound(c, item['archive'], c.previous_commit)
            # Use original admission metadata, not today's Actions expiry state.
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


def title_family(title, module):
    if module is source:
        return TITLES.get(title)
    if isinstance(title, str):
        for family in public.FAMILIES:
            prefix = 'B1 public · ' + family + ' · '
            if title.startswith(prefix):
                suffix = title[len(prefix):]
                if suffix:
                    try:
                        public.day(suffix)
                    except (ValueError, TypeError):
                        return None
                return family
    return None


def discover(c, module=source):
    _reserve(c, calls=5, files=0)
    page = c.api.get(PUBLIC_QUERY if module is public else QUERY)
    runs = page['workflow_runs']
    m.check(isinstance(runs, list) and len(runs) <= 20 and type(page['total_count']) is int
            and page['total_count'] >= len(runs) and (runs or page['total_count'] == 0)
            and len({r['id'] for r in runs}) == len(runs), 'Global market run query incomplete')
    for run in runs:
        check_run(run, c.now(), module.WORKFLOW)
    selected, artifacts, unknown = {}, {}, []
    legacy_reads = 0
    for run in sorted(runs, key=lambda r: (m.clock(r['created_at']), r['id']), reverse=True):
        family = title_family(run.get('display_title'), module)
        if family is None:
            # Titles are hints only; the exact artifact and codec prove identity.
            if legacy_reads >= MAX_LEGACY_LOOKUPS:
                unknown.append(run['id'])
                continue
            legacy_reads += 1
            _reserve(c, calls=1, files=0)
            rows = c.artifacts(run)
            hints = [f for f in module.FAMILIES if any(a.get('name') ==
                     f"{artifact_prefix(f)}-{f}-{run['id']}-{run['run_attempt']}" for a in rows)]
            if len(hints) != 1:
                unknown.append(run['id'])
                continue
            family = hints[0]
            artifacts[run['id']] = rows
        selected.setdefault(family, run)
        if len(selected) == len(module.FAMILIES):
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
        check_run(run, c.now(), codec(family).WORKFLOW)
        m.check(all(run[k] == selected[k] for k in IDENTITY_KEYS), 'Global market run changed')
        state['latest_attempt'] = m.concise_run(run)
        if run['run_attempt'] != 1:
            state['latest_read_status'] = 'RERUN_NOT_ADMITTED'
            return state
        if run['status'] != 'completed':
            state['latest_read_status'] = 'CAPTURE_IN_PROGRESS'
            return state
        if previous and all(previous['run'][k] == run[k] for k in
                            (*IDENTITY_KEYS, 'status', 'conclusion', 'updated_at')):
            report, archive = previous['report'], previous['archive']
            state['latest_read_status'] = 'REUSED_RETAINED_CAPTURE'
        else:
            rows = artifacts.get(run['id'])
            if rows is None:
                rows = c.artifacts(run)
            artifact = m.select_artifact(rows, f"{artifact_prefix(family)}-{family}-{run['id']}-1")
            files, archive = c.archive(artifact, run)
            report = rebuild(files, run, family, c.now())
            state['latest_read_status'] = ('CAPTURE_READ' if run['conclusion'] == 'success'
                                           else 'FAILED_RUN_CAPTURE_READ')
            if report['available_values']:
                state['snapshot'] = {'run': {k: deepcopy(run.get(k)) for k in RUN_KEYS},
                    'artifact_at_read': deepcopy(artifact), 'archive': archive,
                    'report': report, 'retained_at': c.now()}
        state.update(latest_capture_status=report['status'], latest_archive=archive,
                     latest_outcomes=[{k: row[k] for k in
                         ('id', 'status', 'attempt_count', 'http_status', 'request_state') if k in row}
                         for row in report['outcomes']])
    except ERRORS as exc:
        c.files, c.archive_cache = before_files, before_cache
        state.update(latest_read_status='CAPTURE_UNAVAILABLE_OR_REJECTED', error_type=type(exc).__name__)
    return state


def render(report):
    p = report['projection']
    m.check(report['projection_hash'] == canonical_hash(p), 'Global market reading hash')
    lines = ['# 全球市场 · 已保存的有限观察', '',
             '指数/Shibor来自第三方Relay；美债来自Treasury，外汇来自ECB，期货来自Yahoo，币价来自Coinbase。',
             'Shibor是人民币同业利率，不是美债。各原批次的范围声明不代表汇总的全部覆盖。',
             '最新尝试与最后可读批次分开；日期不统一成今日，空白或失败不等于没有变化。', '']
    for family, state in p['families'].items():
        lines += ['## ' + FAMILIES[family], '本次读取：' + state['latest_read_status'], '']
        snapshot = state['snapshot']
        if snapshot:
            lines += ['最后可读批次run：' + str(snapshot['run']['id']),
                      codec(family).render(snapshot['report']),
                      '[原始ZIP](../../' + m.safe_path(snapshot['archive']['read_path']) + ')', '']
        else:
            lines.append('本包无已核验可读批次；不表示没有市场变化。')
    lines += ['六族均为有限来源背景，不代表全市场覆盖、实时行情或公司获益；没有自动启动Quick或Odds。']
    return '\n'.join(lines) + '\n'


def attach(c, baseline):
    m.validate_read_package(baseline)
    original_files, original_cache = dict(c.files), dict(c.archive_cache)
    research = deepcopy(baseline['research'])
    try:
        old, gaps = prior(c)
        states, queries = {}, {}
        # Independent queries: a public workflow gap cannot erase Relay custody.
        for module, query_key in ((source, 'query'), (public, 'public_query')):
            try:
                selected, artifacts, query = discover(c, module)
            except ERRORS as exc:
                selected, artifacts = {}, {}
                query = {'status': 'QUERY_UNAVAILABLE', 'error_type': type(exc).__name__}
            queries[query_key] = query
            for family in module.FAMILIES:
                state = family_read(c, family, selected.get(family), artifacts, old.get(family))
                if query.get('status') == 'QUERY_UNAVAILABLE':
                    state['latest_read_status'] = 'QUERY_UNAVAILABLE'
                states[family] = state
        p = {'version': VERSION, 'checked_at': c.now(), 'families': states, **queries,
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
    note = ('\n[全球市场：指数、利率、外汇、黄金原油与加密资产，含各自日期与缺口](' + DETAIL + ')；不是实时行情。\n'
            if 'details' in research['global_market'] else '\n全球市场保存资料读取受阻；不代表没有市场变化。\n')
    replacements = {'current-state.json': m.read_package_bytes(payload),
                    'README.md': c.files['README.md'] + note.encode()}
    m.check(sum(len(v) for k, v in c.files.items() if k not in replacements)
            + sum(map(len, replacements.values())) <= delivery.MAX_RETAINED_OUTPUT, 'Global market retention budget')
    _reserve(c, replacements=replacements)
    c.files.update(replacements)
    return payload
