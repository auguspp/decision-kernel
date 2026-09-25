"""Independent industry job reading, same GitHub publisher and original archive checks."""
from __future__ import annotations

from copy import deepcopy

from ..identity import canonical_hash
from . import current_state as m, current_state_delivery as delivery
from . import industry_fundamentals as source
from .institutional_radar_reading import _reserve, ERRORS

DETAIL = 'details/radar/industry-fundamentals.md'
REPORT = 'details/radar/industry-fundamentals.json'
QUERY = 'actions/workflows/radar-industry-breadth.yml/runs?branch=main&per_page=20'


def previous(c):
    ref = (c.previous or {}).get('research', {}).get('industry_fundamentals', {}).get('details', {}).get('json')
    if not ref:
        return None, 'NO_PREVIOUS_CAPTURE'
    try:
        m.check(c.previous_commit is not None, 'previous industrial reading commit missing')
        raw = c.api.file(m.safe_path(ref['read_path']), c.previous_commit)
        m.check(len(raw) == ref['bytes'] and m.sha256(raw) == ref['sha256'] and m.blob_sha(raw) == ref['git_blob'],
                'previous industrial reading bytes differ')
        report = source.decode(raw); m.check(report['projection_hash'] == canonical_hash(report['projection']), 'previous industry hash differs')
        value = report['projection']
        m.check(value['observation']['version'] == source.VERSION, 'previous industrial version differs')
        return value, 'EXACT_PREVIOUS_READING_' + c.previous_commit
    except ERRORS:
        return None, 'PREVIOUS_CAPTURE_UNAVAILABLE_NOT_NO_CHANGE'


def native(c):
    _reserve(c, calls=5, files=3)
    page = c.api.get(QUERY); runs = page['workflow_runs']
    m.check(isinstance(runs, list) and len(runs) <= 20 and page['total_count'] >= len(runs)
            and (runs or page['total_count'] == 0), 'industrial run query incomplete')
    if not runs:
        return {'status': 'NOT_RUN', 'observation': None}
    selected = max(runs, key=lambda r: (m.clock(r['created_at']), r['id']))
    run = c.api.get('actions/runs/' + str(selected['id']))
    m.check(run['id'] == selected['id'] and run['head_sha'] == selected['head_sha'], 'industrial selected run changed')
    identity = {'repository': run.get('repository', {}).get('full_name'), 'workflow': run['path'],
        'ref': 'refs/heads/' + str(run['head_branch']), 'event': run['event'], 'code_commit': run['head_sha'],
        'run_id': run['id'], 'attempt': run['run_attempt'], 'trigger_run_id': None}
    source.validate_identity(identity)
    m.check(run.get('head_repository', {}).get('full_name') == m.REPOSITORY, 'foreign industrial head')
    state = {'latest_attempt': m.concise_run(run), 'observation': None}
    if run['status'] != 'completed':
        return {**state, 'status': 'AWAITING_JOB_NOT_QUIET'}
    # Read the exact first attempt's job, not whole-workflow green: independent
    # public industrial capture survives a legacy commodity-basis sibling failure.
    page = c.api.get(f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100")
    m.check(page['total_count'] == len(page['jobs']), 'industrial job query incomplete')
    jobs = [j for j in page['jobs'] if j['name'] == 'industrial-fundamentals']
    if not jobs:
        return {**state, 'status': 'NEW_INDUSTRIAL_JOB_NOT_RUN'}
    m.check(len(jobs) == 1, 'industrial job duplicate')
    job = jobs[0]
    state['job'] = {'id': job['id'], 'status': job['status'], 'conclusion': job['conclusion'],
                    'workflow_conclusion': run['conclusion']}
    if job['status'] != 'completed' or job['conclusion'] != 'success':
        return {**state, 'status': 'INDUSTRIAL_JOB_FAILED_NOT_QUIET'}
    artifact = m.select_artifact(c.artifacts(run), f"industry-fundamentals-{run['id']}-1")
    files, archive = c.archive(artifact, run)
    manifest = source.decode(files['capture.json'])
    identity['trigger_run_id'] = manifest['identity']['trigger_run_id']
    observation, receipt = source.replay(files, identity, cutoff=c.now())
    return {**state, 'status': observation['status'], 'observation': observation,
            'archive': archive, 'capture_hash': receipt['capture_hash'],
            'validation': 'EXACT_ORIGINAL_BYTES_AND_PURE_REBUILD_NOT_SOURCE_TRUTH',
            'source_calls': 0}


def attach(c, baseline):
    m.validate_read_package(baseline)
    old, previous_status = previous(c)
    before = dict(c.files), dict(c.archive_cache)
    try:
        current = native(c)
    except ERRORS as exc:
        c.files, c.archive_cache = before
        current = {'status': 'INDUSTRIAL_READING_REJECTED_NOT_QUIET', 'error_type': type(exc).__name__, 'observation': None}
    observation = current['observation']
    prior_observation = (old or {}).get('observation')
    display = observation or prior_observation
    comparison = source.compare(observation, prior_observation) if observation else None
    value = {'version': source.VERSION, 'generated_at': c.now(), 'current': current,
             'observation': display, 'observation_is_prior': observation is None and display is not None,
             'previous_status': previous_status, 'comparison': comparison,
             'baseline_reading_hash': baseline['reading_hash'], **source.AUTHORITY}
    report = {'projection': value}; report['projection_hash'] = canonical_hash(value)
    text = source.render(display, comparison) if display else '# 产业雷达\n\n尚无可恢复产业观察，不是没有产业变化。\n'
    text = ('本次读取状态：' + current['status'] + '\n\n'
            + ('**以下为此前保存的观察，本次未取得新成果。**\n\n' if value['observation_is_prior'] else '') + text)
    _reserve(c, files=2)
    refs = {'json': c.retain(REPORT, m.json_bytes(report)), 'markdown': c.retain(DETAIL, text.encode())}
    research = deepcopy(baseline['research'])
    research['industry_fundamentals'] = {'status': current['status'], 'details': refs,
        'coverage': display['coverage'] if display else None,
        'source_cutoff': display['cutoff'] if display else None,
        'uses_prior_observation': value['observation_is_prior'], 'previous_status': previous_status,
        'latest_attempt': current.get('latest_attempt'), 'capture_hash': current.get('capture_hash'),
        'meaning': 'INDUSTRIAL_OBSERVATIONS_NOT_INFLECTION_OR_COMPANY_BENEFIT', **source.AUTHORITY}
    payload = m.assemble(code_commit=c.code_commit, checked_at=c.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    original = m.render_summary(baseline).encode(); root = c.files['README.md']
    m.check(root.startswith(original), 'industrial reading preserves root summary')
    replacements = {'current-state.json': m.read_package_bytes(payload),
        'README.md': m.render_summary(payload).encode() + root[len(original):]
            + ('\n[产业雷达：需求、生产、库存利润、价格与物流](' + DETAIL + ')；统计期与原始来源、增量及缺口分别保留。\n').encode()}
    m.check(sum(len(v) for k, v in c.files.items() if k not in replacements)
            + sum(map(len, replacements.values())) <= delivery.MAX_RETAINED_OUTPUT, 'industrial reading byte budget')
    _reserve(c, replacements=replacements); c.files.update(replacements)
    return payload
