"""Return saved question results through the existing publisher, without execution.

Stable question roots are independent of today's Stock price membership. Reuse
Git objects, the original candidate validator and existing publication bounds.
A source/partial-read gap never becomes a business WAIT or a Human request.
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
    model.check(calls + reads + len(collector.files) + new_files + 7
                <= stock_reader.call_limit(collector.api), 'Question publication reserve')
    model.check(sum(map(len, collector.files.values())) + extra_bytes + 256 * 1024
                <= delivery.MAX_RETAINED_OUTPUT, 'Question retained-byte reserve')


def _legacy_sources(payload):
    """Share the accepted Stock source-file allowance; do not create another one."""
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
            'items': items, 'new_research_execution': 'NOT_EXECUTED', **model.AUTHORITY}


def stock_review_scope(payload):
    lane = payload.get('lanes', {}).get('stock', {})
    stock = lane.get('last_qualified_result')
    if stock is None:
        return {'status': 'STOCK_SCOPE_UNAVAILABLE', 'items': [], 'meaning': 'NOT_ZERO_QUESTIONS'}
    rows = stock.get('dispositions')
    model.check(isinstance(rows, list) and len(rows) <= 16
                and len({r['thscode'] for r in rows}) == len(rows), 'Stock review scope invalid')
    items = []
    for row in rows:
        failed = row.get('input_failure') is not None
        passed = row['status'] == 'CONTRACT_CHECKED_RAW_READING' and not failed
        items.append({'thscode': row['thscode'], 'company_name': row.get('company_name'),
                      'original_stock_disposition': deepcopy(row),
                      'review_status': ('DATA_UNAVAILABLE_NOT_PRICE_REJECTED' if failed else
                          'QUESTION_NOT_YET_REVIEWED' if passed else 'PRICE_GATE_NOT_MET_IN_THIS_LANE'),
                      'economic_question_assessed': False, 'research_execution_allowed': False})
    source_run = stock.get('archive', {}).get('origin_run', {}).get('id')
    return {'status': 'SAVED_STOCK_SCOPE_NOT_A_COMPLETED_RESEARCH_REVIEW',
            'batch_id': canonical_hash({'source_run': source_run, 'market_session': stock.get('market_session'),
                                       'projection_hash': stock.get('projection_hash'), 'dispositions': rows}),
            'source_run_id': source_run, 'market_session': stock.get('market_session'),
            'stock_lane_health': lane.get('health'), 'original_coverage': deepcopy(stock.get('coverage')),
            'items': items, 'reviewed_question_count': 0,
            'meaning': 'NO_RESEARCH_REVIEW_RECEIPT_IS_NOT_NO_USEFUL_QUESTION', **model.AUTHORITY}


def _text(value):
    result = html.escape(str(value), quote=True).replace('\n', ' ').replace('\r', ' ')
    for char in '`[]()|*_!':
        result = result.replace(char, '&#' + str(ord(char)) + ';')
    return result


def render(report):
    lines = ['# 日常候选检查范围与已执行的问题研究', '',
             '这是保存结果的读取，不是本次执行研究。历史终态、资料失败、尚未检查和Human请求分开；不自动继承接受。', '',
             '## 当前保存Stock批次', '']
    scope = report['stock_review_scope']
    lines.append('市场日：' + _text(scope.get('market_session')) + '；' + _text(scope['status']))
    for row in scope['items']:
        lines.append('- ' + _text(row.get('company_name') or row['thscode']) + ' ' + _text(row['thscode'])
                     + '：' + _text(row['review_status']))
    lines += ['', '未提供问题审阅回执的对象仍是未检查，不得由未执行Pre反推没有问题。', '', '## 已保存问题执行', '']
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


def attach(collector, baseline):
    model.validate_read_package(baseline)
    before_files, before_sources = dict(collector.files), dict(collector.sources)
    try:
        scope = stock_review_scope(baseline)
        work = collect(collector, baseline)
    except ERRORS as exc:
        collector.files, collector.sources = before_files, before_sources
        work = {'status': 'UNAVAILABLE_OR_REJECTED', 'items': [], 'error_type': type(exc).__name__,
                'meaning': 'QUESTION_READING_GAP_NOT_ZERO_OR_QUIET', **model.AUTHORITY}
        try:
            scope = stock_review_scope(baseline)
        except ERRORS:
            scope = {'status': 'STOCK_SCOPE_UNAVAILABLE', 'items': [], 'meaning': 'NOT_ZERO_QUESTIONS'}
    report = {'format': 'reviewed-question-reading-v1', 'question_work': work,
              'stock_review_scope': scope, 'research_execution': 'NOT_EXECUTED', **model.AUTHORITY}
    try:
        detail = render(report).encode()
        body = model.json_bytes(report)
        _reserve(collector, new_files=2, extra_bytes=len(body) + len(detail))
        details = collector.retain(DETAIL, detail)
        structured = collector.retain(REPORT, body)
        research = deepcopy(baseline['research'])
        research['reviewed_question_work'] = {**work, 'details': details, 'structured': structured,
                                              'stock_review_scope': scope}
        result = model.assemble(code_commit=collector.code_commit, checked_at=collector.now(),
            check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
            capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
        current = model.json_bytes(result)
        _reserve(collector, extra_bytes=len(current))
        collector.files['current-state.json'] = current
        collector.files['README.md'] = before_files['README.md'] + (
            '\n## 日常候选检查与具体问题研究\n\n'
            '[查看本批完整处置、已执行问题的原结果及来源缺口](' + DETAIL + ')\n\n'
            '读取状态：' + _text(work['status']) + '。未审阅不等于没有问题；旧结果首次展示不算新研究。\n'
        ).encode()
        return result
    except ERRORS:
        collector.files, collector.sources = before_files, before_sources
        # Preserve the base delivery even when no optional publication space remains.
        return baseline
