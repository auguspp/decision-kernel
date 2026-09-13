"""One explicit source-failure recovery in the existing Stock host, not retries.

Reuse exact source checks, shown-reading clocks and the original admission/loop.
The fixed child name cannot be reset by another permission, date, price or run.
"""
from __future__ import annotations

from . import current_state as read
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_research_intake as intake

REQUEST = 'research_runs/stock-source-recovery-request.json'
MODE = 'HUMAN_AUTHORIZED_STOCK_SOURCE_RECOVERY'
CHILD = 'source-recovery-v1/'
FAILURE_PURPOSE = 'STOCK_SOURCE_FAILURE_PREDECESSOR'
SELECTION_PURPOSE = 'STOCK_SOURCE_FAILURE_SELECTION'


def execution(thscode):
    eid, prefix = intake.execution(thscode)
    return eid + '-source-recovery-v1', prefix + CHILD


def request_items(request):
    once.require(set(request) == {'schema_version', 'enabled', 'mode', 'permission',
        'exposed_reading', 'source_stock_run_id', 'source_research_run_id', 'items'}
        and type(request['schema_version']) is int and request['schema_version'] == 1
        and request['enabled'] is True and request['mode'] == MODE
        and all(type(request[k]) is int and request[k] > 0 for k in ('source_stock_run_id', 'source_research_run_id')),
        'Stock recovery envelope differs')
    items = request['items']
    once.require(isinstance(items, list) and 0 < len(items) <= 16,
                 'Stock recovery scope unavailable')
    codes = []
    for item in items:
        once.require(set(item) == {'thscode', 'selection', 'failure', 'repair'},
                     'Stock recovery item differs')
        intake.security(item['thscode']); codes.append(item['thscode'])
        repair = item['repair']
        once.require(isinstance(repair, dict) and isinstance(repair.get('report_id'), str)
            and repair['report_id'].isdigit(), 'Stock recovery required report missing')
        if repair.get('kind') == 'REPORT_TITLE_PREFIX':
            once.require(set(repair) == {'kind', 'report_id'}, 'Stock report repair fields differ')
        else:
            once.require(set(repair) == {'kind', 'report_id', 'pdf_sha256', 'page_number', 'review_git_blob'}
                and repair['kind'] == 'BOUND_VISUAL_PAGE'
                and read.SHA.fullmatch(repair['review_git_blob']), 'Stock page repair fields differ')
            from .disclosure_source_reading import review_path
            review_path(repair['pdf_sha256'], repair['page_number'])
    once.require(len(codes) == len(set(codes)), 'duplicate Stock recovery scope')
    return items


def parent(thscode, selection, failure):
    """Shared producer/reader parent identity check, not Research acceptance."""
    eid, _ = intake.execution(thscode)
    once.require(selection['execution_id'] == eid and selection['thscode'] == thscode
        and selection['question_kind'] == intake.QUESTION_KIND
        and selection['observation']['thscode'] == thscode
        and selection['observation']['eligible_for_shadow_reading'] is True
        and failure.get('schema_version') == 1 and failure.get('execution_id') == eid
        and failure.get('thscode') == thscode and failure.get('question_kind') == intake.QUESTION_KIND
        and failure.get('record_kind') == 'PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT'
        and failure.get('formal_research_started') is False
        and failure.get('research_execution') == 'NOT_EXECUTED' and failure.get('funnel_status') == 'NOT_REACHED'
        and failure.get('phase') == 'SOURCE_PREPARATION'
        and failure.get('status') == 'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE'
        and failure.get('error_code') in {'full annual or half-year business report unavailable',
                                         'required page visual review unavailable'}
        and all(failure.get(k) == value for k, value in read.AUTHORITY.items()),
        'Stock predecessor is not the bound unexecuted source failure')


def bind(*, api, code, request, item, origin, clock=once.now):
    from .stock_research_host import authorize, head
    authorize(api, code, request, request_path=REQUEST, mode=MODE)
    entries = request_items(request)
    matches = [entry for entry in entries if entry['thscode'] == item['thscode']]
    once.require(len(matches) == 1 and origin['run']['id'] == request['source_stock_run_id']
        and (item['execution_id'], item['prefix']) == execution(item['thscode']),
        'Stock recovery target or original run differs')
    entry = matches[0]
    deadline, now = read.clock(request['permission']['created_at']), read.clock(clock())
    loaded = {}
    def load(spec):
        raw = identity._checked_source(spec, lambda s: api.file(s['path'], s['ref']))
        meta = api.get('git/commits/' + spec['ref'])
        once.require(meta['sha'] == spec['ref'] and read.clock(meta['committer']['date']) <= deadline <= now,
                     'Stock recovery predecessor/exposure committed after permission')
        loaded[(spec['ref'], spec['path'])] = raw
        return raw
    _, prefix = intake.execution(item['thscode'])
    once.require(entry['selection']['path'] == prefix + 'prepare.json'
        and entry['failure']['path'] == prefix + 'failure.json'
        and entry['selection']['ref'] == entry['failure']['ref'], 'Stock recovery parent path differs')
    sr, fr = load(entry['selection']), load(entry['failure'])
    selection, failure = identity._json(sr), identity._json(fr)
    parent(item['thscode'], selection, failure)
    once.require(selection['origin'] == origin and selection['observation'] == item['observation']
        and read.clock(failure['finished_at']) <= deadline, 'Stock recovery changed original question selection')
    expected = 'REPORT_TITLE_PREFIX' if failure['error_code'].startswith('full annual') else 'BOUND_VISUAL_PAGE'
    once.require(entry['repair']['kind'] == expected, 'Stock recovery does not address parent failure')
    current = intake.inventory(api, head(api, intake.WORK_REF))
    for spec in (entry['selection'], entry['failure']):
        once.require(current.get(spec['path'], {}).get('sha') == spec['git_blob'],
                     'Stock recovery parent changed in latest work history')
    once.require(not any(prefix + name in current for name in
        ('launch.json', 'input.json', 'candidate.json', 'funnel.json', 'admission.json', 'receipt.json')),
        'Stock recovery cannot revive a parent with execution/input history')
    exposure = identity._json(load(request['exposed_reading']))
    read.validate_read_package(exposure)
    once.require(request['exposed_reading']['path'] == 'current-state.json'
        and read.clock(exposure['checks']['finished_at']) <= deadline,
        'Stock permission precedes exposed reading')
    work = exposure['research']['stock_business_work']
    once.require(work['status'] == 'READ_OK'
        and work['latest_execution_attempt']['id'] == request['source_research_run_id'],
        'Stock recovery exposed run differs')
    shown = [r for r in work['items'] if r['thscode'] == item['thscode']]
    once.require(len(shown) == 1 and shown[0]['status'] == 'PRE_EXECUTION_FAILURE'
        and all(shown[0]['sources']['failure'].get(k) == entry['failure'].get(k)
                for k in ('repository', 'ref', 'path', 'git_blob', 'sha256')),
        'Stock recovery parent failure was not in exposed reading')
    def normalized(spec, purpose):
        return once.source_ref(spec['path'], spec['ref'], loaded[(spec['ref'], spec['path'])], purpose)
    return {'kind': MODE, 'parent_failure': normalized(entry['failure'], FAILURE_PURPOSE),
        'parent_selection': normalized(entry['selection'], SELECTION_PURPOSE),
        'exposure': normalized(request['exposed_reading'], 'HUMAN_CONTINUATION_EXPOSURE'),
        'request': once.source_ref(REQUEST, code, api.file(REQUEST, code), 'TRUSTED_STOCK_SOURCE_RECOVERY_REQUEST'),
        'repair': entry['repair'], 'permission': request['permission'], 'new_disclosure': False,
        'meaning': 'REPAIR_OF_REQUIRED_SOURCE_NOT_NEW_PRICE_QUESTION_OR_INDEPENDENT_EVIDENCE'}


def check_materials(binding, context):
    """A new clock alone is not repaired source input."""
    repair = binding['repair']
    report = repair['report_id']
    once.require(context['issuer_inventory']['report_id'] == report
        and any(d['announcement_id'] == report and d['pages'] for d in context['issuer_documents']),
        'Stock recovery missing exact required report body')
    if repair['kind'] == 'BOUND_VISUAL_PAGE':
        docs = [d for d in context['issuer_documents'] if d['pdf_sha256'] == repair['pdf_sha256']]
        once.require(len(docs) == 1 and docs[0].get('page_reading') is not None,
                     'Stock recovery missing required same-PDF reading')
        pages = [p for p in docs[0]['page_reading']['pages'] if p['page_number'] == repair['page_number']]
        once.require(len(pages) == 1 and pages[0]['method'] == 'AI_VISUAL_READING'
            and pages[0]['review_source']['git_blob'] == repair['review_git_blob'],
            'Stock recovery visual material differs')


def select(selected, request, source_run_id):
    entries = request_items(request)
    once.require(source_run_id == request['source_stock_run_id'], 'Stock recovery source run differs')
    codes = {e['thscode'] for e in entries}
    original = {i['thscode']: i for i in selected['items']}
    once.require(codes <= set(original), 'Stock recovery targets outside original qualified plan')
    items = []
    for code, row in original.items():
        if code in codes:
            eid, prefix = execution(code)
            items.append({**row, 'execution_id': eid, 'prefix': prefix})
    return items
