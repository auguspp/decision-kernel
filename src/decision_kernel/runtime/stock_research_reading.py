"""Optional Stock business outcomes in the ORIGINAL fixed reading/publisher.

No producer calls, semantic acceptance or second publication store. All original
market/disclosure bytes and their remaining publication budget take precedence.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from . import current_state as model
from . import current_state_delivery as delivery
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_research_intake as intake


# Additive bounds for the new lane, not a reduction of the original 180/60.
# At most 24 exact source reads + 24 new blob writes + metadata fit 64 calls.
EXTRA_API_CALLS = 64
MAX_STOCK_SOURCE_FILES = 24


def call_limit(api):
    return min(getattr(api, 'max_calls', delivery.MAX_API_CALLS), delivery.MAX_API_CALLS + EXTRA_API_CALLS)


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
    runs = api.get('actions/workflows/stock-business-research.yml/runs?branch=main&per_page=10')
    model.check(isinstance(runs.get('workflow_runs'), list) and len(runs['workflow_runs']) <= 10
                and (runs['workflow_runs'] or runs['total_count'] == 0), 'Stock Research attempts unavailable')
    latest = None
    for run in runs['workflow_runs']:
        if run.get('event') not in {'workflow_run', 'workflow_dispatch'}:
            continue
        model.check(run.get('path') == '.github/workflows/stock-business-research.yml'
            and run.get('head_branch') == 'main' and run.get('run_attempt') == 1
            and run.get('head_repository', {}).get('full_name') == model.REPOSITORY,
            'Stock Research attempt identity differs')
        latest = model.concise_run(run)
        break
    # Reuse the original publisher's exact matching-ref discovery. The CLI
    # transport may be loaded as __main__; absence must not depend on catching
    # a separately imported class with the same GitHubReadError name.
    refs = api.get('git/matching-refs/heads/' + intake.WORK_REF)
    model.check(isinstance(refs, list) and all(isinstance(r, dict)
                and isinstance(r.get('ref'), str) for r in refs), 'Stock ref response invalid')
    exact = [r for r in refs if r['ref'] == 'refs/heads/' + intake.WORK_REF]
    model.check(len(exact) <= 1, 'Stock work ref ambiguous')
    if not exact:
        return {'status': 'NOT_STARTED', 'latest_execution_attempt': latest,
                'items': [{'thscode': code, 'status': 'NOT_STARTED', **model.AUTHORITY} for code in codes],
                'meaning': 'NO_STOCK_BUSINESS_WORK_REF_NOT_RESEARCH_COMPLETE'}
    obj = exact[0]['object']
    model.check(obj.get('type') == 'commit' and model.SHA.fullmatch(obj.get('sha', '')),
                'Stock work ref not exact commit')
    commit = obj['sha']
    rows = intake.inventory(api, commit)
    needed, groups = set(), {}
    for code in codes:
        eid, prefix = intake.execution(code)
        names = {path[len(prefix):] for path in rows if path.startswith(prefix)}
        groups[code] = (eid, prefix, names)
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
    model.check(api.calls + len(needed) + len(set(collector.files) | set(extra_files)) + 5 <= call_limit(api),
                'Stock work would consume original publication API reserve')
    def fetched(path):
        data = api.file(path, commit)
        model.check(len(data) == rows[path]['size'] and model.blob_sha(data) == rows[path]['sha'],
                    'Stock work source bytes differ')
        stored = collector.retain('sources/git/' + rows[path]['sha'] + '/' + Path(path).name, data)
        return data, {'repository': model.REPOSITORY, 'ref': commit, 'path': path, **stored}
    items = []
    for code, (eid, prefix, names) in groups.items():
        item = {'thscode': code, 'execution_id': eid, 'candidate_output_prefix': prefix,
                'question_kind': intake.QUESTION_KIND, 'semantic_acceptance': 'NOT_ESTABLISHED_BY_READER',
                'registered_current_handoff': False, 'terminal_state': None, **model.AUTHORITY, 'sources': {}}
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
        items.append(item)
    return {'status': 'READ_OK', 'work_ref': intake.WORK_REF, 'work_commit': commit,
            'latest_execution_attempt': latest,
            'scope': 'CURRENT_QUALIFIED_STOCKS_FIRST_BUSINESS_BASELINES_NOT_ALL_RESEARCH',
            'items': items, 'counts': {status: sum(i['status'] == status for i in items) for status in
                ('NOT_STARTED','RETAINED_NO_RESEARCH_RESULT','PRE_EXECUTION_FAILURE',
                 'VALIDATED_EXECUTION_GAP','VALIDATED_FUNNEL_CANDIDATE')},
            'meaning': 'PRICE_OBSERVATION_AND_RESEARCH_REMAIN_SEPARATE_NO_AUTOMATIC_BELIEF_OR_ATTENTION'}


def attach(collector, baseline):
    """Original collection finishes first; this optional stage can roll back only itself."""
    before_files, before_sources = dict(collector.files), dict(collector.sources)
    research = deepcopy(baseline['research'])
    def assemble():
        payload = model.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
            check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
            capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
        data = {'current-state.json': model.json_bytes(payload), 'README.md': model.render_summary(payload).encode()}
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
