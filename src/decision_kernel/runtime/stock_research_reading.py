"""Optional Stock business outcomes in the ORIGINAL fixed reading/publisher.

No producer calls, semantic acceptance or second publication store. All original
market/disclosure bytes and their remaining publication budget take precedence.
"""
from __future__ import annotations

import re

from copy import deepcopy
from pathlib import Path

from . import current_state as model
from . import current_state_delivery as delivery
from . import disclosure_work_capacity as disclosure_capacity
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_research_intake as intake
from . import stock_source_recovery as recovery
from . import stock_source_successor as successor
from . import stock_source_successor_continuation as continuation


# Preserve the already accepted #360 Stock-reader capacity. Continuation must fit
# inside it; this repair neither raises nor narrows the publication boundary.
EXTRA_API_CALLS = 72
MAX_STOCK_SOURCE_FILES = 32


def call_limit(api):
    return min(getattr(api, 'max_calls', delivery.MAX_API_CALLS), delivery.MAX_API_CALLS + EXTRA_API_CALLS)


def attempts(collector):
    api = collector.api
    runs = api.get('actions/workflows/stock-business-research.yml/runs?branch=main&per_page=10')
    model.check(isinstance(runs.get('workflow_runs'), list) and len(runs['workflow_runs']) <= 10
        and (runs['workflow_runs'] or runs.get('total_count') == 0), 'Stock Research attempts unavailable')
    result = {'latest_workflow_invocation': None, 'latest_execution_attempt': None,
        'latest_source_preparation_attempt': None, 'latest_compatibility_attempt': None,
        'latest_report_source_attempt': None,
        'unclassified_invocations': [],
        'attempt_query_scope': 'NEWEST_TEN_EXACT_WORKFLOW_INVOCATIONS_NOT_ALL_HISTORY',
        'preparation_result_semantics': 'INVOCATION_METADATA_ONLY_NOT_SOURCE_OR_RESEARCH_ACCEPTANCE'}
    seen = set()
    for run in runs['workflow_runs']:
        model.check(run.get('event') in {'workflow_run', 'workflow_dispatch'}
            and run.get('path') == '.github/workflows/stock-business-research.yml'
            and run.get('head_branch') == 'main' and type(run.get('run_attempt')) is int
            and run['run_attempt'] == 1 and type(run.get('id')) is int and run['id'] > 0
            and run['id'] not in seen and model.SHA.fullmatch(run.get('head_sha', ''))
            and run.get('head_repository', {}).get('full_name') == model.REPOSITORY,
            'Stock Research attempt identity differs')
        seen.add(run['id'])
        summary = model.concise_run(run)
        if result['latest_workflow_invocation'] is None:
            result['latest_workflow_invocation'] = summary
        model.check(api.calls + 1 + len(collector.files) + 5 <= call_limit(api),
                    'Stock purpose reads would consume publication reserve')
        try:
            jobs = api.get(f"actions/runs/{run['id']}/jobs?per_page=100")
            rows = jobs['jobs']
            model.check(isinstance(rows, list) and type(jobs['total_count']) is int
                and len(rows) == jobs['total_count'] and len(rows) <= 100
                and all(isinstance(j, dict) and j.get('run_id') == run['id']
                        and j.get('name') in {'research-stock-business', 'prepare-stock-sources',
                                               'deepseek-compatibility', 'retain-public-report-source'} for j in rows)
                and len({j['name'] for j in rows}) == len(rows), 'Stock invocation jobs incomplete or ambiguous')
            active = [j['name'] for j in rows if j.get('conclusion') != 'skipped']
            if active == ['research-stock-business']:
                key = 'latest_execution_attempt'
            elif active == ['prepare-stock-sources'] and run['event'] == 'workflow_dispatch':
                key = 'latest_source_preparation_attempt'
            elif active == ['deepseek-compatibility'] and run['event'] == 'workflow_dispatch':
                key = 'latest_compatibility_attempt'
            elif active == ['retain-public-report-source'] and run['event'] == 'workflow_dispatch':
                key = 'latest_report_source_attempt'
            else:
                raise ValueError('Stock invocation mode not established')
            if result[key] is None:
                result[key] = summary
        except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError) as exc:
            result['unclassified_invocations'].append({'run': summary, 'error_type': type(exc).__name__,
                'meaning': 'UNCLASSIFIED_INVOCATION_NOT_RESEARCH_OR_QUIET'})
    result['attempt_classification_status'] = ('PARTIAL_OR_UNAVAILABLE' if result['unclassified_invocations']
                                              else 'CLASSIFIED_WITHIN_DECLARED_WINDOW')
    return result


def _collect(collector, payload):
    api = collector.api
    used = getattr(api, 'calls', None)
    model.check(type(used) is int and used >= 0, 'Stock reading API accounting unavailable')
    model.check(used + 3 + len(collector.files) + 5 <= call_limit(api),
                'Stock metadata reads would consume original publication reserve')
    stock = payload['lanes']['stock'].get('last_qualified_result')
    model.check(stock is not None, 'Stock business read lacks qualified Stock scope')
    codes = [row['thscode'] for row in stock['dispositions']
             if row['status'] == 'CONTRACT_CHECKED_RAW_READING' and row.get('input_failure') is None]
    model.check(len(codes) == len(set(codes)) == stock['coverage']['qualified_issuers']
                and len(codes) <= 16, 'Stock business reading scope differs')
    unsupported_codes = [code for code in codes if not intake.supported(code)]
    model.check(all(re.fullmatch(r'[0-9]{6}\.BJ', code) for code in unsupported_codes),
                'malformed Stock Research security identity')
    codes = [code for code in codes if intake.supported(code)]
    invocation = attempts(collector)
    if unsupported_codes:
        invocation['unsupported_research_scope'] = [
            {'thscode': code, 'status': 'RESEARCH_SCOPE_UNSUPPORTED', 'research_execution': 'NOT_EXECUTED'}
            for code in unsupported_codes]
    refs = api.get('git/matching-refs/heads/' + intake.WORK_REF)
    model.check(isinstance(refs, list) and len(refs) <= 16
        and all(isinstance(r, dict) and isinstance(r.get('ref'), str) for r in refs),
        'Stock work ref discovery malformed')
    exact = [r for r in refs if r['ref'] == 'refs/heads/' + intake.WORK_REF]
    model.check(len(exact) <= 1, 'Stock work ref discovery ambiguous')
    if not exact:
        return {'status': 'NOT_STARTED', **invocation,
                'items': [{'thscode': code, 'status': 'NOT_STARTED', **model.AUTHORITY} for code in codes],
                'meaning': 'NO_STOCK_BUSINESS_WORK_REF_NOT_RESEARCH_COMPLETE'}
    obj = exact[0]['object']
    model.check(obj.get('type') == 'commit' and model.SHA.fullmatch(obj.get('sha', '')),
                'Stock work ref not exact commit')
    commit = obj['sha']
    rows = intake.inventory(api, commit)
    needed, groups = set(), {}
    for code in codes:
        role_specs = [('ROOT', intake.execution(code)), ('RECOVERY', recovery.execution(code))]
        if code in successor.TARGETS:
            role_specs.extend([('SUCCESSOR', successor.execution(code)),
                               ('CONTINUATION', continuation.execution(code))])
        for role, (eid, prefix) in role_specs:
            names = {path[len(prefix):] for path in rows
                     if path.startswith(prefix) and '/' not in path[len(prefix):]}
            if role != 'ROOT' and not names:
                continue
            groups[(code, role)] = (eid, prefix, names)
            if names:
                model.check('prepare.json' in names, 'Stock work missing original reservation')
                needed.add(prefix + 'prepare.json')
                for name in ('candidate.json', 'input.json', 'failure.json'):
                    if name in names: needed.add(prefix + name)
    model.check(len(needed) <= MAX_STOCK_SOURCE_FILES,
                'Stock work exceeds separate source-file capacity; no silent truncation')
    extra_files = {}
    for path in needed:
        row = rows[path]
        model.check(type(row.get('size')) is int and 0 <= row['size'] <= 512*1024
                    and model.SHA.fullmatch(row.get('sha', '')), 'Stock work blob metadata invalid')
        read_path = 'sources/git/' + row['sha'] + '/' + Path(path).name
        if read_path in extra_files:
            model.check(extra_files[read_path] == row['size'], 'Stock work conflicting blob size')
        extra_files[read_path] = row['size']
    extra_bytes = sum(size for path, size in extra_files.items() if path not in collector.files)
    model.check(sum(map(len, collector.files.values())) + extra_bytes + 256*1024 <= delivery.MAX_RETAINED_OUTPUT,
                'Stock work would consume original retained-byte reserve')
    model.check(api.calls + len(needed) + len(set(collector.files) | set(extra_files)) + 13 <= call_limit(api),
                'Stock work would consume original publication API reserve')
    raw_cache, pinned_cache = {}, {}
    def fetched(path):
        data = api.file(path, commit)
        raw_cache[path] = data
        model.check(len(data) == rows[path]['size'] and model.blob_sha(data) == rows[path]['sha'],
                    'Stock work source bytes differ')
        stored = collector.retain('sources/git/' + rows[path]['sha'] + '/' + Path(path).name, data)
        return data, {'repository': model.REPOSITORY, 'ref': commit, 'path': path, **stored}
    def pinned(spec, purpose):
        model.check(isinstance(spec, dict) and spec.get('purpose') == purpose,
                    'Stock pinned source purpose differs')
        key = (spec['ref'], spec['path'], spec['git_blob'], spec['sha256'])
        if key not in pinned_cache:
            data = identity._checked_source(spec, lambda s: api.file(s['path'], s['ref']))
            stored = collector.retain('sources/git/' + model.blob_sha(data) + '/' + Path(spec['path']).name, data)
            model.check(stored['git_blob'] == spec['git_blob'] and stored['sha256'] == spec['sha256'],
                        'Stock pinned source differs')
            pinned_cache[key] = data
        return pinned_cache[key]
    def packet_ref(packet, expected):
        matches = [r.model_dump(mode='json') for r in packet.source_refs if r.purpose == expected['purpose']]
        model.check(len(matches) == 1 and all(matches[0].get(k) == expected.get(k)
            for k in ('repository','ref','path','git_blob','sha256','purpose')),
            'Stock candidate lost pinned predecessor/source')

    items, roots, recoveries, successors = [], {}, {}, {}
    for (code, role), (eid, prefix, names) in groups.items():
        item = {'thscode': code, 'execution_id': eid, 'candidate_output_prefix': prefix,
                'question_kind': intake.QUESTION_KIND, 'semantic_acceptance': 'NOT_ESTABLISHED_BY_READER',
                'registered_current_handoff': False, 'terminal_state': None, **model.AUTHORITY, 'sources': {}}
        packet = None; prep = None
        if not names:
            item['status'] = 'NOT_STARTED'
        else:
            raw, item['sources']['selection'] = fetched(prefix + 'prepare.json')
            prep = identity._json(raw)
            model.check(prep['execution_id'] == eid and prep['thscode'] == code
                        and prep['question_kind'] == intake.QUESTION_KIND,
                        'Stock reservation identity differs')
            item['company_name'] = prep['observation'].get('company_name')
            item['origin_market_session'] = prep['origin']['market_session']
            model.check(not ('candidate.json' in names and 'failure.json' in names),
                        'Stock work has candidate and pre-execution failure')
            if 'candidate.json' in names:
                model.check('input.json' in names, 'Stock candidate missing input')
                ir, item['sources']['input'] = fetched(prefix + 'input.json')
                cr, item['sources']['candidate'] = fetched(prefix + 'candidate.json')
                packet = intake.ExternalResearchInputPacket.model_validate(identity._json(ir))
                selection = [s.model_dump(mode='json') for s in packet.source_refs if s.purpose == 'STOCK_BASELINE_SELECTION']
                model.check(len(selection) == 1 and selection[0]['path'] == prefix + 'prepare.json',
                            'Stock input missing bound selection')
                identity._checked_source(selection[0], lambda _: raw)
                item.update(intake.describe(ir, cr))
            elif 'failure.json' in names:
                fr, item['sources']['failure'] = fetched(prefix + 'failure.json')
                failure = identity._json(fr)
                model.check(failure.get('record_kind') == 'PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT'
                    and failure.get('execution_id') == eid and failure.get('thscode') == code
                    and failure.get('research_execution') == 'NOT_EXECUTED'
                    and failure.get('funnel_status') == 'NOT_REACHED'
                    and failure.get('formal_research_started') is False
                    and all(failure.get(k) == v for k,v in model.AUTHORITY.items()),
                    'Stock source failure gained Research or mismatched identity')
                item.update(status='PRE_EXECUTION_FAILURE', failure_status=failure['status'],
                            error_type=failure.get('error_type'), error_code=failure.get('error_code'),
                            finished_at=failure.get('finished_at'))
            else:
                item['status'] = 'RETAINED_NO_RESEARCH_RESULT'
        if role == 'ROOT':
            items.append(item); roots[code] = item
            continue
        root = roots[code]
        _, root_prefix, root_names = groups[(code, 'ROOT')]
        model.check(root['status'] == 'PRE_EXECUTION_FAILURE' and not any(n in root_names for n in
            ('launch.json', 'input.json', 'candidate.json', 'funnel.json', 'admission.json', 'receipt.json')),
            'Stock child parent has execution history')
        parent_selection = identity._json(raw_cache[root_prefix + 'prepare.json'])
        parent_failure = identity._json(raw_cache[root_prefix + 'failure.json'])
        recovery.parent(code, parent_selection, parent_failure)
        if role == 'RECOVERY':
            binding = prep['source_recovery']
            model.check(binding['kind'] == recovery.MODE and binding['new_disclosure'] is False
                and binding['parent_selection']['path'] == root_prefix + 'prepare.json'
                and binding['parent_failure']['path'] == root_prefix + 'failure.json'
                and prep['observation'] == parent_selection['observation']
                and prep['origin'] == parent_selection['origin'], 'Stock recovery reading parent differs')
            for key in ('parent_selection', 'parent_failure'):
                identity._checked_source(binding[key], lambda spec: raw_cache[spec['path']])
            if packet is not None:
                for key in ('parent_selection', 'parent_failure', 'request', 'exposure'):
                    packet_ref(packet, binding[key])
            item.update(work_kind='SOURCE_PREPARATION_RECOVERY', new_disclosure=False)
            root['source_recovery'] = item; recoveries[code] = item
            continue
        model.check(code in recoveries and recoveries[code]['status'] == 'PRE_EXECUTION_FAILURE',
                    'Stock successor lacks preserved failed recovery')
        _, recovery_prefix, recovery_names = groups[(code, 'RECOVERY')]
        model.check('prepare.json' in recovery_names and 'failure.json' in recovery_names,
                    'Stock successor recovery history incomplete')
        binding = prep['source_successor']
        if role == 'SUCCESSOR':
            model.check(binding['thscode'] == code and binding['execution_id'] == eid
                and prep['observation'] == parent_selection['observation'] and prep['origin'] == parent_selection['origin']
                and binding['parent_selection']['path'] == root_prefix + 'prepare.json'
                and binding['parent_failure']['path'] == root_prefix + 'failure.json'
                and binding['recovery_selection']['path'] == recovery_prefix + 'prepare.json'
                and binding['recovery_failure']['path'] == recovery_prefix + 'failure.json',
                'Stock successor reading predecessor differs')
            for key in ('parent_selection', 'parent_failure', 'recovery_selection', 'recovery_failure'):
                identity._checked_source(binding[key], lambda spec: raw_cache[spec['path']])
            old_request_raw = pinned(binding['successor_request'], successor.REQUEST_PURPOSE)
            old_reading_raw = pinned(binding['current_reading'], successor.EXPOSURE_PURPOSE)
            old_request = identity._json(old_request_raw)
            old_reading = identity._json(old_reading_raw); model.validate_read_package(old_reading)
            model.check(old_request['mode'] == successor.MODE
                and old_request['permission'] == binding['permission']
                and old_reading['research']['stock_business_work']['work_commit'] == binding['parent_selection']['ref'],
                'Stock successor pinned reservation context differs')
            if packet is not None:
                for key in ('successor_request', 'current_reading'):
                    packet_ref(packet, binding[key])
            item.update(work_kind='SOURCE_PREPARATION_SUCCESSOR', new_disclosure=False)
            root['source_successor'] = item; successors[code] = item
            continue
        model.check(code in successors and successors[code]['status'] == 'PRE_EXECUTION_FAILURE'
                    and successors[code].get('error_type') == 'AttributeError',
                    'Stock successor continuation lacks preserved AttributeError predecessor')
        _, successor_prefix, successor_names = groups[(code, 'SUCCESSOR')]
        model.check('prepare.json' in successor_names and 'failure.json' in successor_names
                    and not any(n in successor_names for n in
                        ('launch.json','input.json','candidate.json','admission.json','receipt.json','funnel.json')),
                    'Stock successor continuation predecessor reached Research/admission')
        failed_work_ref = binding['predecessor_successor_selection']['ref']
        model.check(binding['thscode'] == code and binding['execution_id'] == eid
            and prep['observation'] == parent_selection['observation'] and prep['origin'] == parent_selection['origin']
            and binding['parent_selection']['path'] == root_prefix + 'prepare.json'
            and binding['parent_failure']['path'] == root_prefix + 'failure.json'
            and binding['recovery_selection']['path'] == recovery_prefix + 'prepare.json'
            and binding['recovery_failure']['path'] == recovery_prefix + 'failure.json'
            and binding['predecessor_successor_selection']['path'] == successor_prefix + 'prepare.json'
            and binding['predecessor_successor_failure']['path'] == successor_prefix + 'failure.json'
            and binding['predecessor_successor_failure']['ref'] == failed_work_ref
            and type(binding.get('technical_predecessor_run_id')) is int
            and binding['technical_predecessor_run_id'] > 0,
            'Stock successor continuation reading predecessor differs')
        for key in ('parent_selection', 'parent_failure', 'recovery_selection', 'recovery_failure',
                    'predecessor_successor_selection', 'predecessor_successor_failure'):
            identity._checked_source(binding[key], lambda spec: raw_cache[spec['path']])
        continuation_request_raw = pinned(binding['successor_request'], continuation.REQUEST_PURPOSE)
        continuation_reading_raw = pinned(binding['current_reading'], continuation.EXPOSURE_PURPOSE)
        predecessor_request_raw = pinned(binding['predecessor_successor_request'], continuation.PREDECESSOR_REQUEST_PURPOSE)
        predecessor_reading_raw = pinned(binding['predecessor_successor_reading'], continuation.PREDECESSOR_READING_PURPOSE)
        continuation_request = identity._json(continuation_request_raw)
        continuation_reading = identity._json(continuation_reading_raw)
        predecessor_request = identity._json(predecessor_request_raw)
        predecessor_reading = identity._json(predecessor_reading_raw)
        model.validate_read_package(continuation_reading); model.validate_read_package(predecessor_reading)
        model.check(continuation_request['mode'] == continuation.MODE
            and continuation_request['permission'] == binding['permission']
            and continuation_request['failed_successor_run_id'] == binding['technical_predecessor_run_id']
            and continuation_request['failed_successor_work_commit'] == failed_work_ref
            and continuation_request['failed_successor_reading_commit'] == binding['predecessor_successor_reading']['ref']
            and continuation_reading['research']['stock_business_work']['work_commit'] == failed_work_ref
            and predecessor_request['mode'] == successor.MODE
            and predecessor_request['permission'] == binding['permission']
            and predecessor_reading['research']['stock_business_work']['work_commit'] == failed_work_ref,
            'Stock successor continuation pinned reservation context differs')
        if packet is not None:
            for key in ('successor_request', 'current_reading', 'predecessor_successor_request',
                        'predecessor_successor_reading'):
                packet_ref(packet, binding[key])
        item.update(work_kind='SOURCE_PREPARATION_SUCCESSOR_TECHNICAL_CONTINUATION', new_disclosure=False)
        root['source_successor_continuation'] = item
    statuses = ('RETAINED_NO_RESEARCH_RESULT','PRE_EXECUTION_FAILURE','VALIDATED_EXECUTION_GAP','VALIDATED_FUNNEL_CANDIDATE')
    return {'status': 'READ_OK', 'work_ref': intake.WORK_REF, 'work_commit': commit,
            **invocation,
            'scope': 'CURRENT_QUALIFIED_STOCKS_FIRST_BUSINESS_BASELINES_NOT_ALL_RESEARCH',
            'items': items,
            'source_recovery_counts': {status: sum(i.get('source_recovery', {}).get('status') == status for i in items)
                for status in statuses},
            'source_successor_counts': {status: sum(i.get('source_successor', {}).get('status') == status for i in items)
                for status in statuses},
            'source_successor_continuation_counts': {status: sum(
                i.get('source_successor_continuation', {}).get('status') == status for i in items) for status in statuses},
            'counts': {status: sum(i['status'] == status for i in items) for status in
                ('NOT_STARTED','RETAINED_NO_RESEARCH_RESULT','PRE_EXECUTION_FAILURE',
                 'VALIDATED_EXECUTION_GAP','VALIDATED_FUNNEL_CANDIDATE')},
            'meaning': 'PRICE_OBSERVATION_AND_RESEARCH_REMAIN_SEPARATE_NO_AUTOMATIC_BELIEF_OR_ATTENTION'}


def attach(collector, baseline):
    baseline = disclosure_capacity.retry_if_source_budget(collector, baseline)
    before_files, before_sources = dict(collector.files), dict(collector.sources)
    research = deepcopy(baseline['research'])
    def assemble():
        payload = model.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
            check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
            capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
        data = {'current-state.json': model.read_package_bytes(payload), 'README.md': model.render_summary(payload).encode()}
        model.check(sum(len(v) for k,v in collector.files.items() if k not in data) + sum(map(len,data.values()))
                    <= delivery.MAX_RETAINED_OUTPUT, 'Stock reading entry exceeds original byte bound')
        model.check(collector.api.calls + len(set(collector.files) | set(data)) + 5 <= call_limit(collector.api),
                    'Stock reading entry would consume original publication budget')
        collector.files.update(data)
        return payload
    try:
        research['stock_business_work'] = _collect(collector, baseline)
        return assemble()
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError) as exc:
        collector.files, collector.sources = before_files, before_sources
        research['stock_business_work'] = {'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
            'meaning': 'STOCK_BUSINESS_READING_GAP_NOT_QUIET_OR_BUSINESS_DISPROOF'}
        return assemble()
