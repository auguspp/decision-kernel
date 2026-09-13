"""Source-only composition in the original Stock host; no Research work writes.

Reuse the original permission, pinned-source, Stock identity and PDF preflight.
A saved preparation is neither execution admission nor another recovery attempt.
"""
from __future__ import annotations

from . import current_state as read
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_research_intake as intake
from . import stock_research_sources as sources
from . import stock_source_recovery as recovery

REQUEST = 'research_runs/stock-source-preparation-request.json'
MODE = 'HUMAN_AUTHORIZED_STOCK_SOURCE_PREPARATION_ONLY'
EXECUTION_FILES = ('launch.json', 'input.json', 'candidate.json', 'funnel.json',
                   'admission.json', 'receipt.json')


def bind(*, api, code, request, selected, origin, clock=once.now):
    """Check the actual shown failed recovery; do not assign a new execution key."""
    from .stock_research_host import authorize, head
    authorize(api, code, request, request_path=REQUEST, mode=MODE)
    once.require(set(request) == {'schema_version', 'enabled', 'mode', 'permission',
        'exposed_reading', 'source_stock_run_id', 'source_research_run_id', 'items'}
        and type(request['schema_version']) is int
        and all(type(request[k]) is int and request[k] > 0
                for k in ('source_stock_run_id', 'source_research_run_id'))
        and request['source_stock_run_id'] == origin['run']['id'], 'source preparation envelope differs')
    entries = request['items']
    once.require(isinstance(entries, list) and 0 < len(entries) <= 2
        and all(isinstance(e, dict) and set(e) == {'thscode', 'selection', 'failure'} for e in entries),
        'source preparation scope differs')
    codes = [e['thscode'] for e in entries]
    once.require(len(set(codes)) == len(codes)
        and set(codes) <= {'603353.SH', '300711.SZ'}, 'source preparation targets outside approved repair')
    original = {i['thscode']: i for i in selected['items']}
    once.require(len(original) == len(selected['items']) and set(codes) <= set(original),
        'source preparation targets outside qualified Stock input')
    deadline, current_time = read.clock(request['permission']['created_at']), read.clock(clock())
    def load(spec):
        raw = identity._checked_source(spec, lambda s: api.file(s['path'], s['ref']))
        meta = api.get('git/commits/' + spec['ref'])
        once.require(meta['sha'] == spec['ref']
            and read.clock(meta['committer']['date']) <= deadline <= current_time,
            'source preparation predecessor or exposure follows permission')
        return identity._json(raw)
    once.require(request['exposed_reading']['path'] == 'current-state.json', 'source preparation exposure path differs')
    exposure = load(request['exposed_reading'])
    read.validate_read_package(exposure)
    once.require(read.clock(exposure['checks']['finished_at']) <= deadline,
                 'source preparation permission predates shown reading')
    work = exposure['research']['stock_business_work']
    prior_run = work['latest_execution_attempt']
    once.require(work['status'] == 'READ_OK' and prior_run['id'] == request['source_research_run_id']
        and prior_run['path'] == '.github/workflows/stock-business-research.yml'
        and prior_run['event'] == 'workflow_dispatch' and prior_run['run_attempt'] == 1
        and prior_run['status'] == 'completed' and prior_run['conclusion'] == 'failure',
        'source preparation exposed execution differs')
    latest = intake.inventory(api, head(api, intake.WORK_REF))
    bound = []
    for entry in entries:
        code_id = entry['thscode']
        eid, prefix = recovery.execution(code_id)
        item = original[code_id]
        once.require(item['security_id'] == intake.security(code_id)
            and item['observation']['thscode'] == code_id
            and item['observation']['eligible_for_shadow_reading'] is True
            and (item['execution_id'], item['prefix']) == intake.execution(code_id),
            'source preparation Stock identity differs')
        once.require(entry['selection']['path'] == prefix + 'prepare.json'
            and entry['failure']['path'] == prefix + 'failure.json'
            and entry['selection']['ref'] == entry['failure']['ref'] == work['work_commit'],
            'source preparation predecessor path differs')
        selection, failure = load(entry['selection']), load(entry['failure'])
        once.require(selection['execution_id'] == eid and selection['thscode'] == code_id
            and selection['question_kind'] == intake.QUESTION_KIND
            and selection['origin'] == origin and selection['observation'] == item['observation']
            and type(failure.get('schema_version')) is int and failure['schema_version'] == 1
            and failure.get('execution_id') == eid
            and failure.get('thscode') == code_id and failure.get('question_kind') == intake.QUESTION_KIND
            and failure.get('record_kind') == 'PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT'
            and failure.get('formal_research_started') is False
            and failure.get('research_execution') == 'NOT_EXECUTED' and failure.get('funnel_status') == 'NOT_REACHED'
            and failure.get('phase') == 'SOURCE_PREPARATION'
            and failure.get('status') == 'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE'
            and failure.get('error_code') in {'required page visual review unavailable',
                                             'full business context too large; no clipping'}
            and read.clock(failure['finished_at']) <= deadline
            and all(failure.get(k) == v for k, v in read.AUTHORITY.items()),
            'source preparation predecessor is not an unexecuted source failure')
        shown = [row.get('source_recovery') for row in work['items'] if row['thscode'] == code_id]
        once.require(len(shown) == 1 and isinstance(shown[0], dict)
            and shown[0]['status'] == 'PRE_EXECUTION_FAILURE'
            and shown[0]['execution_id'] == eid, 'source preparation predecessor was not shown')
        for name in ('selection', 'failure'):
            spec = entry[name]
            once.require(all(shown[0]['sources'][name].get(k) == spec.get(k)
                for k in ('repository', 'ref', 'path', 'git_blob', 'sha256'))
                and latest.get(spec['path'], {}).get('sha') == spec['git_blob'],
                'source preparation predecessor changed or differs from shown source')
        once.require(not any(prefix + name in latest for name in EXECUTION_FILES),
                     'source preparation cannot reopen executed recovery')
        bound.append({'thscode': code_id, 'predecessor_execution_id': eid,
            'predecessor_selection': entry['selection'], 'predecessor_failure': entry['failure'],
            'observation': item['observation'], 'origin': origin})
    return {'kind': MODE, 'request': once.source_ref(REQUEST, code, api.file(REQUEST, code),
        'TRUSTED_SOURCE_PREPARATION_REQUEST_NOT_RESEARCH_INPUT'),
        'permission': request['permission'], 'exposed_reading': request['exposed_reading'],
        'items': bound, 'research_execution_allowed': False, **read.AUTHORITY}


def prepare(*, api, code, selected, origin, reading_commit, output,
            capture=sources.capture, clock=once.now):
    """Only invoked after original Stock validation. All output stays in artifact."""
    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
                 'unsafe preparation output')
    request = identity._json(api.file(REQUEST, code))
    binding = bind(api=api, code=code, request=request, selected=selected, origin=origin, clock=clock)
    path = output / 'source-preparation-batch.json'
    once.require(not path.exists() and not path.is_symlink(), 'preparation receipt already exists')
    result = {'schema_version': 1, 'kind': MODE, 'status': 'SOURCE_PREPARATION_INCOMPLETE',
        'source_run_id': origin['run']['id'], 'reading_commit': reading_commit,
        'code_commit': code, 'binding': binding, 'started_at': clock(),
        'items': [], 'planned_issuers': [i['thscode'] for i in binding['items']],
        'unattempted_issuers': [i['thscode'] for i in binding['items']],
        'research_execution_allowed': False, 'formal_research_started': False,
        'model_calls': 0, 'research_work_writes': 0, 'automatic_retry': False, **read.AUTHORITY}
    path.write_bytes(once.raw(result))
    try:
        for item in binding['items']:
            # Re-read trusted permission and current failed history before each issuer.
            fresh = bind(api=api, code=code, request=request, selected=selected, origin=origin, clock=clock)
            once.require(fresh == binding, 'source preparation binding changed')
            company = item['thscode']
            result['unattempted_issuers'].remove(company)
            outcome = {'thscode': company, 'predecessor_execution_id': item['predecessor_execution_id'],
                'status': 'PREPARATION_INCOMPLETE', 'research_execution_allowed': False, **read.AUTHORITY}
            try:
                report = capture(ticker=company[:6], observation={'origin': origin, 'row': item['observation']},
                    api=api, code_commit=code, output=output / company / 'sources',
                    clock=clock, preparation_only=True)
                once.require(report['kind'] == 'SOURCE_PREPARATION_ONLY'
                    and report['ticker'] == company[:6] and report['code_commit'] == code
                    and report['research_execution_allowed'] is False
                    and all(report.get(k) == v for k, v in read.AUTHORITY.items()),
                    'source preparation report identity differs')
                once.require(report['status'] in {'PREPARATION_INCOMPLETE',
                    'SOURCES_CHECKED_NOT_EXECUTION_ADMITTED'}, 'source preparation result status differs')
                if report['status'] == 'SOURCES_CHECKED_NOT_EXECUTION_ADMITTED':
                    full = report.get('complete_context')
                    once.require(report.get('inventory_checked') is True
                        and report.get('all_planned_bodies_inspected') is True
                        and bool(report.get('selected_ids'))
                        and report['selected_ids'] == report.get('checked_body_ids')
                        and report.get('unattempted_ids') == [] and report.get('missing_page_reviews') == []
                        and isinstance(full, dict) and full.get('within_current_limit') is True
                        and full.get('within_source_reference_limit') is True,
                        'source preparation success lacks full source coverage')
                outcome.update(status=report['status'], preparation=report)
            except Exception as exc:
                outcome['error_type'] = type(exc).__name__
                if isinstance(exc, once.TrialError): outcome['error_code'] = exc.code
            result['items'].append(outcome)
            path.write_bytes(once.raw(result))
        if all(i['status'] == 'SOURCES_CHECKED_NOT_EXECUTION_ADMITTED' for i in result['items']):
            result['status'] = 'SOURCES_CHECKED_NOT_EXECUTION_ADMITTED'
        return result
    finally:
        result['finished_at'] = clock()
        path.write_bytes(once.raw(result))
