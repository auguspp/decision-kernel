"""Return saved question outcomes through the existing publisher; never execute.

Read stable question roots independently of current Stock price membership.
Reuse native Git, the original candidate validator and original reading bounds.
Reading a saved result is not fresh admission, economic truth or Human acceptance.
"""
from __future__ import annotations

from copy import deepcopy
import html
from pathlib import PurePosixPath
import re

from ..identity import canonical_hash
from . import current_state as model
from . import current_state_delivery as delivery
from . import external_research_identity as identity
from . import reviewed_question_input as reviewed
from . import saved_research_once as once
from . import stock_research_intake as intake
from . import stock_research_reading as stock_reader
from .read_blob_reuse import pending_blob_writes
from .external_research_execution import (
    ExternalResearchInputPacket, ExternalResearchCandidate,
    validate_external_research_candidate,
)

PREFIX = 'research_runs/candidates/stock-questions/'
CHILD = 'technical-continuation-v1'
DETAIL = 'details/research/reviewed-questions.md'
REPORT = 'details/research/reviewed-questions.json'
CORE = {'prepare.json', 'input.json', 'candidate.json', 'validation.json',
        'host-receipt.json', 'launch.json', 'funnel.json', 'receipt.json', 'admission.json'}
MAX_EXECUTIONS = 8
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError)


def _reserve(collector, reads=0, new_files=0, extra_bytes=0):
    calls = getattr(collector.api, 'calls', None)
    model.check(type(calls) is int and calls >= 0, 'Question API accounting unavailable')
    model.check(calls + reads + pending_blob_writes(collector.api, collector.files) + new_files + 7
                <= stock_reader.call_limit(collector.api), 'Question publication reserve')
    model.check(sum(map(len, collector.files.values())) + extra_bytes + 256 * 1024
                <= delivery.MAX_RETAINED_OUTPUT, 'Question retained-byte reserve')


def _legacy_sources(payload):
    """Share the accepted Stock file allowance, not a new independent budget."""
    paths = set()
    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get('read_path'), str):
                paths.add(value['read_path'])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(payload['research'].get('stock_business_work', {}).get('items', []))
    return paths


def _inventory(collector):
    _reserve(collector, reads=2)
    refs = collector.api.get('git/matching-refs/heads/' + intake.WORK_REF)
    model.check(isinstance(refs, list) and len(refs) <= 16
                and all(isinstance(r, dict) and isinstance(r.get('ref'), str) for r in refs),
                'Question work-ref inventory invalid')
    exact = [r for r in refs if r['ref'] == 'refs/heads/' + intake.WORK_REF]
    model.check(len(exact) <= 1, 'Question work-ref inventory ambiguous')
    if not exact:
        return None, {}, {}
    obj = exact[0]['object']
    commit = obj.get('sha', '')
    model.check(obj.get('type') == 'commit' and model.SHA.fullmatch(commit),
                'Question work-ref not a commit')
    tree = collector.api.get('git/trees/' + commit + '?recursive=1')
    model.check(tree.get('truncated') is False and isinstance(tree.get('tree'), list)
                and len(tree['tree']) <= 5000, 'Question work tree incomplete')
    groups, metadata = {}, {}
    for row in tree['tree']:
        path = row['path']
        if not path.startswith(PREFIX) or row['type'] == 'tree':
            continue
        parts = path[len(PREFIX):].split('/')
        model.check((len(parts) == 2 or (len(parts) == 3 and parts[1] == CHILD))
                    and re.fullmatch(r'[0-9a-f]{64}', parts[0])
                    and re.fullmatch(r'[A-Za-z0-9_-]+\.(?:json|md|txt)', parts[-1])
                    and row['type'] == 'blob' and row['mode'] == '100644'
                    and type(row.get('size')) is int and 0 <= row['size'] <= 512 * 1024
                    and model.SHA.fullmatch(row.get('sha', '')) and path not in metadata,
                    'Question work path invalid')
        prefix = path.rsplit('/', 1)[0] + '/'
        groups.setdefault(prefix, set()).add(parts[-1])
        metadata[path] = row
    model.check(len(groups) <= MAX_EXECUTIONS, 'Question execution scope exceeds bound')
    return commit, groups, metadata


def _describe(prefix, data, question_raw):
    prep = identity._json(data['prepare.json'])
    q = reviewed._declaration(question_raw)
    code = q['case_id']
    model.check(intake.security(code) == q['security_id'] and code[:6] == q['ticker'],
                'Question security differs')
    key = canonical_hash({'security_id': q['security_id'], 'question_id': q['question_id']})
    root = PREFIX + key + '/'
    model.check(prefix in {root, root + CHILD + '/'}, 'Question stable root differs')
    eid = 'stock-question-' + key + ('-' + CHILD if prefix != root else '')
    model.check(prep['status'] == 'QUESTION_INPUT_PREPARED_NOT_EXECUTED'
                and prep['question_id'] == q['question_id'] and prep['revision'] == q['revision']
                and prep['execution_key']['execution_id'] == eid
                and prep['research_execution_allowed'] is False and prep['funnel_invoked'] is False,
                'Question reservation differs')
    item = {'thscode': code, 'question_id': q['question_id'], 'revision': q['revision'],
            'question': q['question'], 'why_now': q['why_now'],
            'known_unknowns': q['known_unknowns'], 'known_counterevidence': q['known_counterevidence'],
            'next_discriminating_search': q['next_discriminating_search'],
            'execution_id': eid, 'candidate_output_prefix': prefix,
            'role': 'ROOT' if prefix == root else 'TECHNICAL_CONTINUATION',
            'predecessor_execution_id': None if prefix == root else 'stock-question-' + key,
            'status': 'RETAINED_NO_RESEARCH_RESULT', 'terminal_state': None,
            'terminal_stage': None, 'terminal_reason': None, 'finished_at': None,
            'semantic_acceptance': 'NOT_ESTABLISHED_BY_READER',
            'registered_current_handoff': False, 'new_research_execution': 'NOT_EXECUTED',
            'validation_scope': 'SAVED_CANDIDATE_CONSISTENCY_NOT_LIVE_ADMISSION_OR_SOURCE_TRUTH',
            **model.AUTHORITY}
    if 'candidate.json' not in data:
        model.check(not any(n in data for n in ('validation.json', 'funnel.json', 'receipt.json')),
                    'Question final files lack candidate')
        return item
    model.check({'input.json', 'validation.json', 'launch.json'} <= set(data),
                'Question candidate missing bound input or validation')
    packet = ExternalResearchInputPacket.model_validate(identity._json(data['input.json']))
    candidate = ExternalResearchCandidate.model_validate(identity._json(data['candidate.json']))
    model.check(packet.source_lane == reviewed.LANE and packet.case_id == code
                and packet.security_id == q['security_id'] and packet.ticker == q['ticker']
                and packet.execution_id == eid and packet.candidate_output_prefix == prefix
                and packet.research_question == q['question'], 'Question input identity differs')
    qrefs = [s.model_dump(mode='json') for s in packet.source_refs if s.purpose == reviewed.PURPOSE]
    model.check(qrefs == [prep['question_source']], 'Question declaration binding differs')
    model.check(once.sha(data['input.json']) == prep['input_file_sha256']
                and identity.input_key(packet).as_dict() == prep['execution_key'],
                'Question reservation input differs')
    launch = identity._json(data['launch.json'])
    model.check(launch['id'] == eid and launch['input_hash'] == canonical_hash(packet)
                and launch['code_commit'] == packet.code_commit
                and launch['question_source'] == prep['question_source']
                and launch['automatic_retry'] is False, 'Question launch differs')
    checked = validate_external_research_candidate(packet=packet, candidate=candidate)
    model.check(identity._json(data['validation.json']) == checked.model_dump(mode='json'),
                'Question saved validation differs')
    funnel = checked.funnel_result
    if 'funnel.json' in data:
        model.check(funnel is not None
                    and identity._json(data['funnel.json']) == funnel.model_dump(mode='json'),
                    'Question saved funnel differs')
    if 'receipt.json' in data:
        model.check(identity._json(data['receipt.json']) == candidate.receipt.model_dump(mode='json'),
                    'Question saved receipt differs')
    if 'host-receipt.json' in data:
        host = identity._json(data['host-receipt.json'])
        model.check(host['execution_id'] == eid and host['thscode'] == code
                    and host['question_id'] == q['question_id'] and host['revision'] == q['revision']
                    and host['code_commit'] == packet.code_commit
                    and host['candidate_hash'] == checked.candidate_hash
                    and host['validation_hash'] == canonical_hash(checked)
                    and host['status'] == checked.status.value
                    and all(host.get(k) == v for k, v in model.AUTHORITY.items())
                    and host['registered_current_handoff'] is False,
                    'Question host receipt differs')
        item['host_receipt_present'] = True
    else:
        item['host_receipt_present'] = False
    if prefix != root:
        pred = launch['predecessor']
        model.check(pred['execution_id'] == item['predecessor_execution_id']
                    and isinstance(pred.get('sources'), dict), 'Question predecessor missing')
        item['predecessor_sources'] = deepcopy(pred['sources'])
    item.update(status='VALIDATED_FUNNEL_RESULT' if funnel else 'VALIDATED_EXECUTION_GAP',
                completion=checked.completion.value, candidate_hash=checked.candidate_hash,
                validation_hash=canonical_hash(checked), source_reading_commit=packet.current_state_commit,
                research_cutoff=packet.research_cutoff.isoformat(),
                finished_at=candidate.receipt.finished_at.isoformat(),
                original_platform_task_id=candidate.receipt.platform_task_id,
                terminal_state=funnel.terminal_state.value if funnel else None,
                terminal_stage=funnel.terminal_stage.value if funnel else None,
                terminal_reason=funnel.terminal_reason if funnel else None,
                gap_reason=checked.gap_reason,
                pre_present=candidate.pre_research is not None,
                quick_present=candidate.quick_research is not None)
    return item


def collect(collector, payload):
    commit, groups, metadata = _inventory(collector)
    if not groups:
        return {'status': 'NO_RETAINED_QUESTION_ROOTS_WITHIN_SCOPE', 'work_commit': commit,
                'items': [], 'scope': PREFIX, 'new_research_execution': 'NOT_EXECUTED', **model.AUTHORITY}
    wanted = {p + n for p, names in groups.items() for n in names & CORE}
    legacy = _legacy_sources(payload)
    projected = {'sources/git/' + metadata[p]['sha'] + '/' + PurePosixPath(p).name for p in wanted}
    model.check(len(legacy | projected) <= stock_reader.MAX_STOCK_SOURCE_FILES,
                'Question shared source-file bound')
    _reserve(collector, reads=len(wanted), new_files=len(projected) + 2,
             extra_bytes=sum(metadata[p]['size'] for p in wanted))
    cache, references = {}, {}
    for path in sorted(wanted):
        body = collector.api.file(path, commit)
        row = metadata[path]
        model.check(len(body) == row['size'] and model.blob_sha(body) == row['sha'],
                    'Question retained blob differs')
        stored = collector.retain('sources/git/' + row['sha'] + '/' + PurePosixPath(path).name, body)
        cache[path] = body
        references[path] = {'repository': model.REPOSITORY, 'ref': commit, 'path': path, **stored}
    qcache, items = {}, []
    for prefix, names in sorted(groups.items()):
        try:
            model.check('prepare.json' in names and 'failure.json' not in names,
                        'Question reservation absent or legacy failure mixed')
            prep = identity._json(cache[prefix + 'prepare.json'])
            spec = prep['question_source']
            model.check(spec['purpose'] == reviewed.PURPOSE and spec['repository'] == model.REPOSITORY,
                        'Question declaration purpose differs')
            key = (spec['ref'], spec['path'], spec['git_blob'], spec['sha256'])
            if key not in qcache:
                model.check(len(legacy | projected) + len(qcache) + 1 <= stock_reader.MAX_STOCK_SOURCE_FILES,
                            'Question declarations exceed shared source-file bound')
                _reserve(collector, reads=1, new_files=3, extra_bytes=512 * 1024)
                raw = identity._checked_source(spec, lambda s: collector.api.file(s['path'], s['ref']))
                stored = collector.retain('sources/git/' + spec['git_blob'] + '/' + PurePosixPath(spec['path']).name, raw)
                qcache[key] = (raw, {'repository': model.REPOSITORY, 'ref': spec['ref'],
                                    'path': spec['path'], **stored})
            data = {n: cache[prefix + n] for n in names & CORE}
            item = _describe(prefix, data, qcache[key][0])
            if item['role'] != 'ROOT' and 'predecessor_sources' in item:
                for ps in item['predecessor_sources'].values():
                    model.check(ps['path'].startswith(PREFIX) and ps['path'] in cache,
                                'Question predecessor outside retained scope')
                    identity._checked_source(ps, lambda s: cache[s['path']])
            item['sources'] = {n: references[prefix + n] for n in sorted(names & CORE)}
            item['question_source'] = qcache[key][1]
            items.append(item)
        except ERRORS as exc:
            items.append({'candidate_output_prefix': prefix, 'status': 'UNAVAILABLE_OR_REJECTED',
                          'error_type': type(exc).__name__, 'terminal_state': None,
                          'meaning': 'QUESTION_READ_GAP_NOT_BUSINESS_WAIT_OR_ZERO', **model.AUTHORITY})
    return {'status': 'READ_OK_WITH_QUESTION_GAPS' if any(i['status'] == 'UNAVAILABLE_OR_REJECTED' for i in items) else 'READ_OK',
            'work_ref': intake.WORK_REF, 'work_commit': commit, 'scope': PREFIX,
            'scope_note': 'ALL_RETAINED_ROOTS_WITHIN_BOUND_NOT_CURRENT_PRICE_QUALIFIED_MEMBERS',
            'retained_source_file_count': len(legacy | projected) + len(qcache),
            'items': items, 'new_research_execution': 'NOT_EXECUTED', **model.AUTHORITY}


def _saved_stock_observations(collector, payload):
    lane = payload.get('lanes', {}).get('stock', {})
    stock = lane.get('last_qualified_result')
    if stock is None:
        return {}, 'STOCK_SCOPE_UNAVAILABLE'
    spec = stock.get('details', {}).get('reading/stock-reading.json')
    if not isinstance(spec, dict):
        return {}, 'STOCK_DETAIL_NOT_RETAINED'
    model.check(spec.get('read_ref_rule') == 'USE_THE_SAME_PINNED_READING_COMMIT',
                'Stock observation detail must remain in same reading')
    raw = collector.files[model.safe_path(spec['read_path'])]
    model.check(len(raw) == spec['bytes'] and once.sha(raw) == spec['sha256']
                and model.blob_sha(raw) == spec['git_blob'], 'Stock observation retained detail differs')
    report = identity._json(raw)
    projection = report['projection']
    model.check(report['projection_hash'] == canonical_hash(projection)
                and report['projection_hash'] == stock.get('projection_hash')
                and projection['market_session'] == stock.get('market_session'),
                'Stock observation detail identity differs')
    rows = projection['all_stock_observations']
    model.check(isinstance(rows, list) and len(rows) <= 16
                and len({r['thscode'] for r in rows}) == len(rows),
                'Stock observation detail scope invalid')
    return {r['thscode']: r for r in rows}, 'SAME_READING_STOCK_OBSERVATIONS'


def _question_prompts(row, observation):
    if not isinstance(observation, dict):
        return [], []
    prompts, directions = [], []
    company = row.get('company_name') or row['thscode']
    origins = observation.get('current_origins') or observation.get('origins') or []
    for origin in origins:
        for source in origin.get('direction_sources') or []:
            name, code = source.get('name'), source.get('thscode')
            if isinstance(name, str) and name and isinstance(code, str) and code:
                directions.append({'name': name, 'thscode': code, 'family': source.get('family')})
                prompts.append('来源方向“' + name + '”中，' + company
                               + '的真实业务联系、收入/利润/现金暴露是否成立？'
                               '哪些公开证据可以推翻这一联系？')
        prompt = origin.get('review_question')
        if not prompts and isinstance(prompt, str) and prompt:
            prompts.append(prompt)
    return list(dict.fromkeys(prompts)), list({(d['thscode'], d['name'], d.get('family')): d
                                               for d in directions}.values())


def stock_review_scope(payload, observations=None, observation_status='NOT_READ'):
    lane = payload.get('lanes', {}).get('stock', {})
    stock = lane.get('last_qualified_result')
    if stock is None:
        return {'status': 'STOCK_SCOPE_UNAVAILABLE', 'items': [], 'meaning': 'NOT_ZERO_QUESTIONS'}
    rows = stock.get('dispositions')
    model.check(isinstance(rows, list) and len(rows) <= 16
                and len({r['thscode'] for r in rows}) == len(rows), 'Stock review scope invalid')
    work = payload.get('research', {}).get('stock_business_work', {})
    work_items = work.get('items', []) if isinstance(work, dict) else []
    model.check(isinstance(work_items, list) and len(work_items) <= 16
                and len({r['thscode'] for r in work_items}) == len(work_items),
                'Stock business relation scope invalid')
    by_code = {r['thscode']: r for r in work_items}
    observations = observations or {}
    items = []
    for row in rows:
        failed = row.get('input_failure') is not None
        passed = row['status'] == 'CONTRACT_CHECKED_RAW_READING' and not failed
        relation = by_code.get(row['thscode'])
        if failed:
            disposition = 'DATA_UNAVAILABLE_NOT_PRICE_REJECTED'
        elif not passed:
            disposition = 'ORIGINAL_PRICE_DISPOSITION_ONLY'
        elif relation is not None and relation.get('status') == 'NOT_STARTED':
            # The Stock reader emits an empty-root placeholder, not saved Research.
            disposition = ('QUESTION_REVIEW_REQUIRED'
                           if work.get('status') == 'READ_OK' and relation.get('sources') == {}
                           else 'RESEARCH_CONTEXT_UNAVAILABLE_NOT_NEW_QUESTION')
        elif relation is not None:
            disposition = {
                'PRE_EXECUTION_FAILURE': 'EXISTING_BASELINE_SOURCE_OR_INPUT_GAP',
                'VALIDATED_EXECUTION_GAP': 'EXISTING_BASELINE_EXECUTION_GAP',
                'VALIDATED_FUNNEL_CANDIDATE': 'EXISTING_BASELINE_RESULT_PRESENT',
                'RETAINED_NO_RESEARCH_RESULT': 'EXISTING_BASELINE_PARTIAL_NO_RESULT',
            }.get(relation.get('status'), 'EXISTING_BASELINE_STATE_PRESENT')
        elif work.get('status') == 'READ_OK':
            disposition = 'QUESTION_REVIEW_REQUIRED'
        else:
            disposition = 'RESEARCH_CONTEXT_UNAVAILABLE_NOT_NEW_QUESTION'
        prompts, directions = _question_prompts(row, observations.get(row['thscode']))
        existing = None
        if relation is not None:
            existing = {k: deepcopy(relation.get(k)) for k in (
                'status', 'question_kind', 'execution_id', 'failure_status', 'error_type',
                'error_code', 'terminal_state', 'finished_at', 'sources') if k in relation}
        items.append({'thscode': row['thscode'], 'company_name': row.get('company_name'),
                      'original_stock_disposition': deepcopy(row), 'review_status': disposition,
                      'research_scope_supported': intake.supported(row['thscode']),
                      'origin_question_prompts': prompts, 'origin_directions': directions,
                      'observation_context_status': observation_status if row['thscode'] in observations
                      else 'NOT_MATCHED_IN_SAVED_STOCK_OBSERVATIONS',
                      'existing_research_relation': existing,
                      'distinct_question_assessment': 'NOT_PERFORMED',
                      'economic_question_assessed': False, 'research_execution_allowed': False})
    source_run = stock.get('archive', {}).get('origin_run', {}).get('id')
    return {'status': 'SAVED_STOCK_SCOPE_WITH_RESEARCH_RELATIONS_NOT_FORMAL_QUESTION_REVIEW',
            'batch_id': canonical_hash({'source_run': source_run, 'market_session': stock.get('market_session'),
                                       'projection_hash': stock.get('projection_hash'), 'dispositions': rows}),
            'source_run_id': source_run, 'market_session': stock.get('market_session'),
            'stock_lane_health': lane.get('health'), 'original_coverage': deepcopy(stock.get('coverage')),
            'items': items, 'reviewed_question_count': 0,
            'question_review_required_count': sum(r['review_status'] == 'QUESTION_REVIEW_REQUIRED' for r in items),
            'existing_baseline_gap_count': sum(r['review_status'] in {
                'EXISTING_BASELINE_SOURCE_OR_INPUT_GAP', 'EXISTING_BASELINE_EXECUTION_GAP',
                'EXISTING_BASELINE_PARTIAL_NO_RESULT'} for r in items),
            'data_unavailable_count': sum(r['review_status'] == 'DATA_UNAVAILABLE_NOT_PRICE_REJECTED' for r in items),
            'automatic_research_execution': False,
            'meaning': 'OBSERVATION_PROMPTS_AND_EXISTING_RELATIONS_NOT_FORMAL_QUESTION_OR_EXECUTION',
            **model.AUTHORITY}


def _recorded_batch_review(collector, payload, scope, work):
    """Project a saved same-batch review; never infer it from ticker or a label.

    The execution has already been revalidated by collect. Its original review
    is still fetched by exact identity. An optional review gap does not discard
    a valid saved result or overwrite the independent baseline observation.
    """
    absent = {'status': 'NO_MATCHING_SAVED_DAILY_REVIEW', 'items': [],
              'reviewed_object_count': None, 'selected_question_count': None,
              'research_execution_allowed': False, **model.AUTHORITY}
    if not scope.get('batch_id'):
        return absent
    try:
        matches = []
        for item in work['items']:
            if item['status'] not in {'VALIDATED_FUNNEL_RESULT', 'VALIDATED_EXECUTION_GAP'}:
                continue
            def saved(name):
                return identity._json(collector.files[item['sources'][name]['read_path']])
            launch = saved('launch.json')
            daily = launch.get('daily_scope')
            if not isinstance(daily, dict) or daily.get('batch_id') != scope['batch_id']:
                continue
            model.check(item.get('host_receipt_present') is True,
                        'Recorded batch review missing host receipt')
            host = saved('host-receipt.json')
            packet = saved('input.json')
            model.check(host.get('daily_scope') == daily
                        and daily['execution_id'] == item['execution_id'] == launch['id']
                        and daily['source_run_id'] == scope['source_run_id']
                        and daily['market_session'] == scope['market_session']
                        and daily['question_source'] == launch['question_source']
                        and daily['reading_source'] in packet['source_refs']
                        and daily['reading_source']['ref'] == packet['current_state_commit']
                        and daily['reading_hash'] == packet['current_state_reading_hash'],
                        'Recorded batch review execution binding differs')
            matches.append((item, daily, packet))
        if not matches:
            return absent
        model.check(len(matches) == 1, 'Recorded batch review ambiguous')
        item, daily, packet = matches[0]
        spec = daily['batch_review_source']
        model.check(spec['purpose'] == 'DAILY_STOCK_BATCH_REVIEW'
                    and spec in packet['source_refs'], 'Recorded batch review source differs')
        read_path = 'sources/git/' + spec['git_blob'] + '/' + PurePosixPath(spec['path']).name
        shared = _legacy_sources(payload)
        for row in work['items']:
            shared.update(s['read_path'] for s in row.get('sources', {}).values())
            if row.get('question_source'):
                shared.add(row['question_source']['read_path'])
        # Rejected roots still retain their raw files. Count the original
        # collector's whole scope, not only source mappings of valid results.
        retained_count = work['retained_source_file_count']
        model.check(type(retained_count) is int and len(shared) <= retained_count
                    and retained_count + int(read_path not in shared)
                    <= stock_reader.MAX_STOCK_SOURCE_FILES,
                    'Recorded batch review source-file bound')
        _reserve(collector, reads=2, new_files=1, extra_bytes=identity.MAX_BYTES)
        raw = identity._checked_source(spec, lambda source: collector.api.file(source['path'], source['ref']))
        review = identity._json(raw)
        meta = collector.api.get('git/commits/' + spec['ref'])
        model.check(meta['sha'] == spec['ref']
                    and model.clock(review['reviewed_at']) <= model.clock(meta['committer']['date'])
                    <= model.clock(packet['selected_at']), 'Recorded batch review clock differs')
        from .stock_daily_question import REVIEW_DISPOSITIONS
        rows = review['items']
        model.check(set(review) == {'reading_source', 'question_source', 'batch_id', 'reviewed_at', 'items'}
                    and review['reading_source'] == daily['reading_source']
                    and review['question_source'] == daily['question_source']
                    and review['batch_id'] == scope['batch_id']
                    and rows == daily['reviewed_items']
                    and isinstance(rows, list)
                    and [r['thscode'] for r in rows] == [r['thscode'] for r in scope['items']]
                    and all(set(r) == {'thscode', 'disposition', 'reason'}
                            and r['disposition'] in REVIEW_DISPOSITIONS
                            and isinstance(r['reason'], str) and r['reason'].strip() for r in rows)
                    and [r['thscode'] for r in rows if r['disposition'] == 'SELECTED_NEW_DISTINCT_QUESTION']
                    == [item['thscode']], 'Recorded batch review full scope differs')
        source = {'repository': model.REPOSITORY, 'ref': spec['ref'], 'path': spec['path'],
                  **collector.retain(read_path, raw)}
        return {**absent, 'status': 'MATCHED_SAVED_DAILY_REVIEW', 'batch_id': scope['batch_id'],
                'market_session': scope['market_session'], 'reviewed_at': review['reviewed_at'],
                'reviewed_object_count': len(rows), 'selected_question_count': 1,
                'items': deepcopy(rows), 'source': source,
                'execution': {k: deepcopy(item[k]) for k in ('execution_id', 'thscode', 'question_id',
                    'status', 'pre_present', 'quick_present', 'candidate_hash')},
                'meaning': 'SAVED_ROUTING_REVIEW_AND_EXECUTION_NOT_ECONOMIC_OR_HUMAN_ACCEPTANCE'}
    except ERRORS as exc:
        return {**absent, 'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
                'meaning': 'BATCH_REVIEW_READ_GAP_NOT_ABSENCE_OF_REVIEW_OR_RESEARCH'}


def _text(value):
    result = html.escape(str(value), quote=True).replace('\n', ' ').replace('\r', ' ')
    for char in '`[]()|*_!':
        result = result.replace(char, '&#' + str(ord(char)) + ';')
    return result


def render(report):
    lines = ['# 日常候选检查范围与已执行的问题研究', '',
             '这是保存结果的读取，不是本次执行研究。历史终态、资料失败、尚未检查和Human请求分开；不自动继承接受。', '']
    recorded = report.get('recorded_batch_review', {})
    if recorded.get('status') == 'MATCHED_SAVED_DAILY_REVIEW':
        lines += ['## 本批已记录的审阅与执行', '',
                  '已逐项记录 ' + _text(recorded['reviewed_object_count']) + ' 个对象的处置；选择 '
                  + _text(recorded['selected_question_count']) + ' 个具体问题执行。不是全公司研究完成或Human接受。']
        labels = {'SELECTED_NEW_DISTINCT_QUESTION': '已选择具体问题，执行记录见下方',
                  'NOT_SELECTED': '本批未选择执行', 'NO_DISTINCT_QUESTION': '未声明不同的新问题',
                  'EXISTING_RESEARCH': '接续已有研究', 'SOURCE_UNAVAILABLE': '必要资料不可用',
                  'ORIGINAL_PRICE_DISPOSITION_ONLY': '保留原价格条件处置', 'DATA_UNAVAILABLE': '数据资格缺口'}
        for row in recorded['items']:
            lines.append('- ' + _text(row['thscode']) + '：' + labels[row['disposition']] + '。' + _text(row['reason']))
        execution = recorded['execution']
        stages = 'Pre / Quick' if execution['quick_present'] else ('Pre' if execution['pre_present'] else '未保存阶段结果')
        lines += ['', '对应执行：' + _text(execution['status']) + '；已保存阶段：' + stages + '。原结果与局限见下方。',
                  '[本批原审阅记录](../../' + recorded['source']['read_path'] + ')', '',
                  '## 原始价格观察与首次业务状态', '',
                  '下列baseline字段与上方具体问题分开：NOT_STARTED不表示该证券没有已执行的问题；原观察草稿不是新的执行待办。', '']
    else:
        if recorded.get('status') == 'UNAVAILABLE_OR_REJECTED':
            lines += ['本批审阅关联暂不可核验；不能据此说没有审阅。已保存问题结果仍独立列在下方。', '']
        lines += ['## 当前保存Stock批次', '']
    scope = report['stock_review_scope']
    lines.append('市场日：' + _text(scope.get('market_session')) + '；' + _text(scope['status']))
    for row in scope['items']:
        lines.append('- ' + _text(row.get('company_name') or row['thscode']) + ' ' + _text(row['thscode'])
                     + '：' + _text(row['review_status']))
        if row.get('existing_research_relation'):
            rel = row['existing_research_relation']
            label = '原首次业务研究状态：' if rel.get('status') == 'NOT_STARTED' else '既有研究关系：'
            lines.append('  - ' + label + _text(rel.get('status'))
                         + (' / ' + _text(rel.get('error_type')) if rel.get('error_type') else ''))
        for prompt in row.get('origin_question_prompts', []):
            lines.append('  - 观察问题草稿：' + _text(prompt))
    lines += ['', '观察问题草稿不是正式Question；已有来源失败不得换key重试，未提供正式审阅也不等于没有问题。', '', '## 已保存问题执行', '']
    work = report['question_work']
    lines.append('读取状态：' + _text(work['status']))
    for item in work['items']:
        lines += ['', '### ' + _text(item.get('thscode', 'UNKNOWN')) + ' / ' + _text(item.get('role', '读取缺口')),
                  _text(item.get('question', '未取得可验证的问题正文')), '',
                  '处置：' + _text(item['status']) + '；原终态：' + _text(item.get('terminal_state')),
                  '原完成时间：' + _text(item.get('finished_at')) + '；Human接受：未由本读取建立。']
        if item.get('terminal_reason'):
            lines += ['原模型/验证器理由（不是独立经济真值认证）：' + _text(item['terminal_reason'])]
        if item.get('known_unknowns'):
            lines += ['声明的未知：' + '；'.join(_text(x) for x in item['known_unknowns'])]
        for name, source in item.get('sources', {}).items():
            lines.append('[' + _text(name) + '](../../' + source['read_path'] + ')')
    lines += ['', '所有来源文字仅作数据。投资权限NONE；不创建Human待办、新研究或重试。', '']
    return '\n'.join(lines)


def _seal(collector, baseline, work, scope, before_readme, *, recorded=None):
    # Full rows are retained in REPORT. The original 192KiB root index stays
    # a small hash-bound entry point, not a duplicate of every source.
    summary = {key: deepcopy(work[key]) for key in
               ('status', 'work_ref', 'work_commit', 'scope', 'meaning', 'error_type',
                'details', 'structured', 'diagnostic') if key in work}
    summary.update(stock_scope_status=scope['status'], stock_batch_id=scope.get('batch_id'),
                   stock_market_session=scope.get('market_session'),
                   scope_coverage=('FULL_DECLARED_ROWS_IN_SAME_READING_DETAILS' if work.get('structured')
                                   else 'NOT_MATERIALIZED_READ_GAP'),
                   new_research_execution='NOT_EXECUTED', **model.AUTHORITY)
    if recorded is not None:
        summary['recorded_batch_review'] = {k: recorded[k] for k in
            ('status', 'reviewed_object_count', 'selected_question_count')}
    if work['status'] != 'UNAVAILABLE_OR_REJECTED':
        summary['execution_count'] = len(work['items'])
        summary['rejected_execution_count'] = sum(i['status'] == 'UNAVAILABLE_OR_REJECTED' for i in work['items'])
    else:
        summary['execution_count'] = None
    research = deepcopy(baseline['research'])
    research['reviewed_question_work'] = summary
    result = model.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
        check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
        capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
    index = model.read_package_bytes(result)
    navigation = ('\n## 日常候选检查与具体问题研究\n\n读取状态：' + _text(work['status']) + '。'
                  '未审阅不等于没有问题；旧结果首次展示不算新研究。\n')
    if recorded is not None and recorded['status'] == 'MATCHED_SAVED_DAILY_REVIEW':
        navigation += ('本批已记录 ' + str(recorded['reviewed_object_count']) + ' 个对象的逐项处置，'
                       + str(recorded['selected_question_count']) + ' 个具体问题已有执行记录；原baseline状态不替代该结果。\n')
    if work.get('details'):
        navigation += '\n[查看本批完整处置、已执行问题的原结果及来源缺口](' + DETAIL + ')\n'
    readme = before_readme + navigation.encode()
    remaining = sum(len(v) for k, v in collector.files.items() if k not in {'README.md', 'current-state.json'})
    model.check(remaining + len(index) + len(readme) <= delivery.MAX_RETAINED_OUTPUT,
                'Question reading index exceeds byte budget')
    replacements = {**collector.files, 'current-state.json': index, 'README.md': readme}
    model.check(collector.api.calls + pending_blob_writes(collector.api, replacements) + 5
                <= stock_reader.call_limit(collector.api),
                'Question reading index exceeds publication reserve')
    collector.files.update({'current-state.json': index, 'README.md': readme})
    return result


def attach(collector, baseline):
    model.validate_read_package(baseline)
    before_files, before_sources = dict(collector.files), dict(collector.sources)
    try:
        observations, observation_status = _saved_stock_observations(collector, baseline)
    except ERRORS:
        observations, observation_status = {}, 'STOCK_OBSERVATION_DETAIL_UNAVAILABLE_OR_REJECTED'
    try:
        scope = stock_review_scope(baseline, observations, observation_status)
    except ERRORS:
        scope = {'status': 'STOCK_SCOPE_UNAVAILABLE', 'items': [], 'meaning': 'NOT_ZERO_QUESTIONS'}
    try:
        work = collect(collector, baseline)
        recorded = _recorded_batch_review(collector, baseline, scope, work)
        report = {'format': 'reviewed-question-reading-v1', 'question_work': work,
                  'stock_review_scope': scope, 'recorded_batch_review': recorded,
                  'research_execution': 'NOT_EXECUTED', **model.AUTHORITY}
        detail = render(report).encode()
        body = model.json_bytes(report)
        _reserve(collector, new_files=2, extra_bytes=len(body) + len(detail))
        work = {**work, 'details': collector.retain(DETAIL, detail),
                'structured': collector.retain(REPORT, body)}
        return _seal(collector, baseline, work, scope, before_files['README.md'], recorded=recorded)
    except ERRORS as exc:
        collector.files, collector.sources = before_files, before_sources
        labels = {'Question publication reserve': 'PUBLICATION_API_BUDGET',
                  'Question retained-byte reserve': 'RETENTION_BYTE_BUDGET',
                  'Question shared source-file bound': 'SHARED_SOURCE_FILE_BUDGET',
                  'Question execution scope exceeds bound': 'EXECUTION_SCOPE_BOUND',
                  'Question work tree incomplete': 'INCOMPLETE_WORK_TREE'}
        message = exc.args[0] if type(exc) is ValueError and len(exc.args) == 1 and type(exc.args[0]) is str else None
        work = {'status': 'UNAVAILABLE_OR_REJECTED', 'items': [], 'error_type': type(exc).__name__,
                'meaning': 'QUESTION_READING_GAP_NOT_ZERO_OR_QUIET',
                'diagnostic': {'code': labels.get(message, 'UNCLASSIFIED_READ_REJECTION'),
                               'api_calls_after_attempt': collector.api.calls,
                               'retained_files_after_rollback': len(collector.files)}, **model.AUTHORITY}
        # If even the compact gap cannot fit, fail the original publisher rather
        # than silently returning a complete-looking zero.
        return _seal(collector, baseline, work, scope, before_files['README.md'])
