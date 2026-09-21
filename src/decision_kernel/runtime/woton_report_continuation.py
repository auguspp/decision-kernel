"""One Human-approved same-root Woton analysis; reuse custody/admission/Research.

This fixed logical child has its own directory outside the legacy baseline
inventory. The immutable parent ID, selection, failure and r3 remain bound;
no generic continuation policy or old validator is changed.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import timedelta
from functools import partial
import html
import os
from pathlib import Path
import re
import subprocess
import tempfile
from uuid import NAMESPACE_URL, uuid5

from ..evidence import EvidenceArtifact
from ..identity import canonical_hash
from ..research_funnel import DiscoveryInput
from . import current_state as reading
from . import external_research_admission as admission
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_research_intake as intake
from .current_state_delivery import GitHubAPI
from .external_research_execution import ExternalResearchInputPacket
from .research_commit_only import read_research_progress
from .stock_research_host import authorize, head, STOCK_PROMPT_BYTES

REQUEST = 'research_runs/woton-report-continuation-request.json'
REQUEST_SHA256 = '37047ef5386f5a32c5616a5fea992f4b9ec65f8503badfa4cbcd67a8f2908eb5'
MODE = 'WOTON_H1_REPORT_ANALYSIS_CONTINUATION_ONCE'
PARENT = 'stock-business-66446c4257a92cd4576ee87ff1bd4ead51ca61a4292befc55cbde3d514b5542c'
EXECUTION = PARENT + '-report-continuation-v1'
PREFIX = 'research_runs/candidates/stock-report-continuations/' + PARENT.removeprefix('stock-business-') + '/v1/'
LABEL = 'woton-h1-analysis-ready'
REUSED = 'EXISTING_REPORT_CONTINUATION_NO_EXECUTION'
MAX_CONTEXT = 448 * 1024
HISTORY_KEYS = ('parent_selection', 'parent_failure', 'predecessor_progress',
                'predecessor_workpaper', 'predecessor_parent')
UNKNOWN = (
    'REQUIRED_SOURCE_CLASS:SAVED_H1_REPORT:STATIC',
    '首次发行人公开时间UNKNOWN；Evidence publication仅指明确保存正文的Git提交时间，不是公告发布时间。',
    '本次是已获准的原问题接续，不是新日常问题；仅回答该半年报可支持的部分，不裁定最新经营状态。',
    '未检查报告后公告、全年持续性及当前行情；不把未分配的集团现金或合同成本归给膜工程。',
    '先前集团利润桥已做，本次不把重复计算称为新发现；不外发先前工作底稿正文。',
    'FALSIFICATION_TEST:核对收入确认、合同资产/负债、履约成本和回款的口径；名称相似不证明分部归属。',
)
BUDGET = {'max_tool_calls': 6, 'max_search_queries': 0, 'max_source_reads': 4,
    'max_technical_retries': 0, 'max_elapsed_minutes': 15,
    **{k + '_enforcement': 'SOFT_EXECUTOR' for k in
       ('tool_calls', 'search_queries', 'source_reads', 'technical_retries', 'elapsed_time')}}


def checked_request(api, code, clock):
    raw = api.file(REQUEST, code)
    once.require(once.sha(raw) == REQUEST_SHA256, 'WOTON_CONTINUATION_REQUEST_CHANGED')
    request = identity._json(raw)
    authorize(api, code, request, request_path=REQUEST, mode=MODE)
    once.require(request['parent_execution_id'] == PARENT and request['subject'] == '000920.SZ'
        and request['relation'] == 'CONTINUE_ANALYSIS'
        and admission.clock(request['permission']['created_at']) <= admission.clock(clock())
        < admission.clock(request['execute_before']), 'WOTON_CONTINUATION_SCOPE_EXPIRED')
    return request


def work_tree(api):
    commit = head(api, intake.WORK_REF)
    tree = api.get('git/trees/' + commit + '?recursive=1')
    once.require(tree.get('truncated') is False and isinstance(tree.get('tree'), list)
        and len(tree['tree']) <= 5000, 'WOTON_CONTINUATION_WORK_TREE')
    rows = {r['path']: r for r in tree['tree'] if r['type'] != 'tree'}
    once.require(len(rows) == sum(r['type'] != 'tree' for r in tree['tree']),
                 'WOTON_CONTINUATION_DUPLICATE_PATH')
    return commit, rows


def checked_source(api, spec):
    return identity._checked_source(spec, lambda s: api.file(s['path'], s['ref']))


def history(api, request, current, rows):
    """Verify original immutable files and the native three-file progress chain."""
    data = {k: checked_source(api, request[k]) for k in HISTORY_KEYS}
    for k in ('parent_selection', 'parent_failure'):
        spec = request[k]
        once.require(rows.get(spec['path'], {}).get('sha') == spec['git_blob']
            and api.file(spec['path'], current) == data[k], 'WOTON_PARENT_CHANGED')
    failure = identity._json(data['parent_failure'])
    selection = identity._json(data['parent_selection'])
    once.require(failure['execution_id'] == selection['execution_id'] == PARENT
        and failure['thscode'] == selection['thscode'] == '000920.SZ'
        and failure['formal_research_started'] is False
        and failure['research_execution'] == 'NOT_EXECUTED'
        and failure['error_type'] == 'CninfoPdfHttpError'
        and failure['status'] == 'SOURCE_OR_INPUT_PREPARATION_INCOMPLETE',
        'WOTON_ORIGINAL_FAILURE_DIFFERS')
    parent_prefix = request['parent_failure']['path'].rsplit('/', 1)[0] + '/'
    once.require(not any(parent_prefix + n in rows for n in
        ('launch.json', 'input.json', 'candidate.json')), 'WOTON_PARENT_ALREADY_LAUNCHED')
    with tempfile.TemporaryDirectory(prefix='woton-retained-progress-') as directory:
        p = Path(directory)
        for key, name in (('predecessor_progress', 'progress.json'),
                          ('predecessor_workpaper', 'workpaper.md'),
                          ('predecessor_parent', 'predecessor.json')):
            (p / name).write_bytes(data[key])
        progress, _ = read_research_progress(p, expected_sha256=request['predecessor_progress']['sha256'])
    once.require(progress['subject'] == '000920.SZ' and progress['question_id'] == PARENT
        and progress['revision'] == 3, 'WOTON_PROGRESS_PREDECESSOR_DIFFERS')
    return data


def public_context(parsed, manifest):
    """Construct from the exact verified whole report, never the prior AI paper."""
    from . import woton_report_custody as custody
    once.require(parsed['pdf_sha256'] == custody.PDF_SHA and parsed['page_count'] == 133
        and [p['page_number'] for p in parsed['pages']] == list(range(1, 134))
        and all(isinstance(p['text'], str) and p['text'].strip() for p in parsed['pages']),
        'WOTON_CONTINUATION_FULL_REPORT_REQUIRED')
    context = {'issuer_documents': [{
        'announcement_id': 'SINA-12512184', 'title': '沃顿科技股份有限公司2026年半年度报告',
        'source_locator': custody.SOURCE_URL, 'pdf_sha256': custody.PDF_SHA,
        'published_at': None, 'publication_time_status': 'UNKNOWN_NOT_INFERRED_FROM_URL_OR_RECEIPT',
        'retrieved_at': manifest['received_at'], 'page_count': 133,
        'reading_method': 'ORIGINAL_PYPDF', 'pages': deepcopy(parsed['pages'])}],
        'source_limitations': '发行人署名报告的新浪保存版本；不宣称CNINFO字节等价。'
            '仅原报告全文及当前限定问题，无报告后更新、其他来源或先前AI底稿。'
            '提取完整不代表每张表格语义可靠；行列和归属不清时保留UNKNOWN。'}
    once.require(len(once.raw(context)) <= MAX_CONTEXT, 'WOTON_CONTINUATION_CONTEXT_SIZE')
    return context


def make_input(api, code, request, retain, context, started, clock):
    cs = retain.save('source.json', context); cs['purpose'] = 'MODEL_CONTEXT'
    meta = api.get('git/commits/' + cs['ref'])
    once.require(meta['sha'] == cs['ref'], 'WOTON_CONTEXT_COMMIT_IDENTITY')
    # This is explicitly publication of a saved Git observation, not the issuer report.
    eid = uuid5(NAMESPACE_URL, EXECUTION + ':' + cs['sha256'])
    finish = clock()
    pf = {'schema_version': 1, 'provenance': 'RECORDED_TOOL_RETURNS',
        'case_id': '000920.SZ', 'ticker': '000920', 'security_id': intake.security('000920.SZ'),
        'started_at': started, 'finished_at': finish,
        'valid_until': min(admission.clock(finish) + timedelta(minutes=45),
                           admission.clock(request['execute_before'])).isoformat(),
        'reads': [{'id': 'report', 'identity': '000920:SINA-12512184',
            'locator': context['issuer_documents'][0]['source_locator'],
            'authority': 'PRIMARY', 'kind': 'BODY', 'succeeded': True,
            'checked_at': finish, 'body_sha256': context['issuer_documents'][0]['pdf_sha256'],
            'tool_reference': once.locator(request['source_manifest'])}],
        'required_classes': [{'id': 'SAVED_H1_REPORT', 'mode': 'STATIC',
            'body_ids': ['report'], 'inventory_id': None}], 'inventories': [],
        'limits': {'max_queries': 0, 'max_reads': 1},
        'seed_publications': [{'evidence_id': str(eid), 'kind': 'GIT_COMMIT', 'source': cs}],
        'notes': 'Recorded Git custody recovery and full-PDF replay; zero issuer GET. '
                 'PRIMARY describes the issuer-authored report, not mirror authenticity certification. '
                 'Git context publication is distinct from UNKNOWN issuer first-publication time.'}
    ps = retain.save('preflight.json', pf); ps['purpose'] = admission.PREFLIGHT_PURPOSE
    state_raw = api.file('current-state.json', request['reading_commit'])
    state = identity._json(state_raw); reading.validate_read_package(state)
    selected = clock()
    once.require(admission.clock(state['checks']['finished_at']) <= admission.clock(selected)
        <= admission.clock(state['checks']['recheck_after']), 'WOTON_READING_WINDOW_EXPIRED')
    seed = EvidenceArtifact(id=eid, source_type='SAVED_RESEARCH_OBSERVATION',
        source_identifier=EXECUTION, source_locator=once.locator(cs),
        published_at=meta['committer']['date'], available_at=selected, retrieved_at=selected,
        content_hash=cs['sha256'], idempotency_key=EXECUTION + ':' + cs['sha256'],
        retention_mode='FULL_ARTIFACT', replayability_level='PARTIAL', raw_storage_ref=once.locator(cs),
        license_terms_note='User-approved public report context. Publication is this Git record only; issuer publication UNKNOWN.')
    refs = [cs, ps, request['source_manifest'], *[request[k] for k in HISTORY_KEYS]]
    packet = ExternalResearchInputPacket(execution_id=EXECUTION, case_id='000920.SZ', ticker='000920',
        security_id=intake.security('000920.SZ'), source_lane='STOCK_REPORT_ANALYSIS_CONTINUATION',
        selected_at=selected, research_cutoff=selected, code_commit=code,
        current_state_commit=request['reading_commit'], current_state_reading_hash=state['reading_hash'],
        source_refs=refs, seed_evidence_artifacts=[seed], research_question=request['question'],
        known_unknowns=UNKNOWN, next_discriminating_search='仅检查已保存完整半年报的确认政策、分部和合同/现金附注；未披露的明细留空，不访问新来源。',
        method_version='research-funnel-v1', prompt_version='woton-report-continuation-v1',
        allowed_tools=['OTHER_READ'], candidate_output_prefix=PREFIX, budget=BUDGET)
    discovery = DiscoveryInput(discovery_id=EXECUTION, source_lane=packet.source_lane,
        ticker=packet.ticker, security_id=packet.security_id, as_of=selected,
        economic_direction='原问题的工程收入确认与营运资金归属接续，方向未定。',
        factual_observations=[{'statement': '已保存完整半年报供限定接续核验；留存及全文提取不认证经济解释。',
                              'evidence_artifact_ids': [eid]}],
        source_lineage=[{'evidence_artifact_id': eid, 'source_locator': seed.source_locator,
                         'available_at': seed.available_at}],
        why_now='Human已明确批准在同一原问题下继续尚未完成的合同与现金归属分析，不是新行情或新披露。',
        contradiction_or_mapping_warning='集团合同余额、法人口径与膜工程分部不能混用；不重复计入已完成集团利润桥。',
        next_discriminating_search=packet.next_discriminating_search,
        known_stop_or_downgrade_condition='仅原报告范围；未知细分归属不伪造。Pre可停止，仅合法CONTINUE才Quick；不自动Deep。')
    catalog = api.file(identity.CATALOG_PATH, code)
    checks = dict(input_raw=once.raw(packet), preflight_raw=once.raw(pf),
        catalog_source=once.source_ref(identity.CATALOG_PATH, code, catalog, 'CURRENT_CODE_EXECUTION_SCOPE'),
        load=lambda s: api.file(s['path'], s['ref']), commit=lambda r: api.get('git/commits/' + r),
        current_code=lambda: head(api, 'main'), now=clock, checked_at=clock())
    return packet, discovery, checks, cs


def summary(candidate, validation):
    lines = ['# 沃顿科技：原问题的工程收入确认与营运资金接续', '',
        '原问题：' + PARENT, '原验证状态：' + validation.status.value,
        '这是限定报告范围的执行候选，不是Full Research、Human接受或投资决定。', '']
    for stage, result in (('Pre', candidate.pre_research), ('Quick', candidate.quick_research)):
        if result is None:
            continue
        lines += ['## ' + stage, html.escape(result.route_reason), '']
        claims = getattr(result, 'material_claims', ()) or (
            *getattr(result, 'supporting_claims', ()), *getattr(result, 'contradictory_claims', ()))
        lines.extend('- ' + html.escape(c.kind.value + '：' + c.statement) for c in claims)
        unknowns = ([result.largest_unknown] if hasattr(result, 'largest_unknown')
                    else result.unresolved_questions)
        lines += ['', '未解决：' + '；'.join(html.escape(u) for u in unknowns), '']
    if validation.funnel_result is None:
        lines += ['执行缺口；不产生业务WAIT/DROP。', str(validation.gap_reason or 'UNKNOWN')]
    return ('\n'.join(lines) + '\n').encode()


def run(*, api, code, output, clock=once.now, call=None):
    from . import woton_report_custody as custody
    from . import stock_question_continuation as deepseek
    once.require(not output.exists() and not output.is_symlink()
        and not any(p.is_symlink() for p in output.parents), 'WOTON_CREATE_ONLY_OUTPUT')
    output.mkdir(parents=True)
    result = {'status': 'NOT_EXECUTED', 'phase': 'AUTHORIZATION', 'code_commit': code,
        'execution_id': EXECUTION, 'parent_execution_id': PARENT, 'relation': 'CONTINUE_ANALYSIS',
        'question_id': PARENT, 'candidate_output_prefix': PREFIX, 'started_at': clock(),
        'formal_research_started': False, 'automatic_retry': False, 'new_distinct_question': False,
        'source_requests': 0, 'market_requests': 0, 'model_stage_attempts': [],
        'semantic_acceptance': 'NOT_ESTABLISHED', 'registered_current_handoff': False, **reading.AUTHORITY}
    retain = None; reserved = False
    try:
        request = checked_request(api, code, clock)
        once.require(once.MAX_OUTPUT_TOKENS == 6000 and STOCK_PROMPT_BYTES == 512 * 1024,
                     'WOTON_MODEL_LIMITS_CHANGED')
        current, rows = work_tree(api)
        existing = sorted(p for p in rows if p.startswith(PREFIX))
        if existing:
            result.update(status=REUSED, existing_paths=existing,
                meaning='SAVED_OR_PARTIAL_ATTEMPT_NOT_PROOF_OF_COMPLETION')
            return result
        history(api, request, current, rows)
        source_started = clock()
        _, parsed, manifest = custody.recover(api, request['source_manifest'])
        context = public_context(parsed, manifest)
        once.require(request['provider'] == {'name': deepseek.PROVIDER,
            'base_url': once.DEEPSEEK_BASE_URL, 'model': once.DEEPSEEK_MODEL,
            'credential_binding': 'DEEPSEEK_API_KEY', 'reasoning': deepseek.REASONING},
            'WOTON_PROVIDER_SCOPE_CHANGED')
        retain = once.Retainer(api, {'prefix': PREFIX, 'id': EXECUTION, 'work_ref': intake.WORK_REF}, code, output)
        reservation = retain.save('prepare.json', {'execution_id': EXECUTION, 'parent_execution_id': PARENT,
            'question_id': PARENT, 'relation': 'CONTINUE_ANALYSIS', 'permission': request['permission'],
            'request': once.source_ref(REQUEST, code, api.file(REQUEST, code), 'TRUSTED_WOTON_CONTINUATION'),
            'predecessors': {k: request[k] for k in HISTORY_KEYS}, 'source_manifest': request['source_manifest'],
            'code_commit': code, 'started_at': clock(), **reading.AUTHORITY})
        reserved = True
        packet, discovery, checks, cs = make_input(api, code, request, retain, context, source_started, clock)
        ready = admission.assess_admission(**checks)
        once.require(ready['reason'] == 'INPUT_READY_TO_COMMIT_NOT_EXECUTION_ADMISSION', ready['reason'])
        deepseek._deepseek_request(once.pre_prompt(packet, discovery, context), once.PreResearchResult)
        egress = deepseek.egress_hash(packet, discovery, context)
        ins = retain.save('input.json', checks['input_raw'])
        checks.update(input_source=ins, expected_key=identity.input_key(packet).as_dict(), checked_at=clock())
        admitted = admission.assess_admission(**checks)
        once.require(admitted['research_execution_allowed'], admitted['reason'])
        launch = retain.save('launch.json', {'id': EXECUTION, 'parent_execution_id': PARENT,
            'input_hash': canonical_hash(packet), 'code_commit': code, 'permission': request['permission'],
            'approved_scope_egress_hash': egress, 'provider': request['provider'], 'automatic_retry': False,
            'source_manifest': request['source_manifest'], 'predecessor_progress': request['predecessor_progress']})

        def recheck():
            once.require(checked_request(api, code, clock) == request, 'WOTON_AUTHORIZATION_CHANGED')
            current, rows = work_tree(api); history(api, request, current, rows)
            for spec in (reservation, cs, ins, launch):
                data = checked_source(api, spec)
                once.require(rows.get(spec['path'], {}).get('sha') == spec['git_blob']
                    and api.file(spec['path'], current) == data, 'WOTON_RESERVED_FILE_CHANGED')
            checked_source(api, request['source_manifest'])
            once.require(once.sha(once.raw(context)) == cs['sha256']
                and deepseek.egress_hash(packet, discovery, context) == egress, 'WOTON_PUBLIC_CONTEXT_CHANGED')
            fresh = admission.assess_admission(**{**checks, 'checked_at': clock()})
            once.require(fresh['research_execution_allowed'], fresh['reason'])

        def execute(exact, key):
            once.require(exact == checks['input_raw'] and key == checks['expected_key'], 'WOTON_CALLBACK_IDENTITY')
            result.update(formal_research_started=True, phase='RESEARCH')
            def guarded(stage, prompt, model, out, usage):
                expected = once.pre_prompt(packet, discovery, context)
                spent = result['model_stage_attempts']
                if stage == 'quick':
                    once.require(spent == ['pre'], 'WOTON_QUICK_ORDER')
                    pre = once.PreResearchResult.model_validate(identity._json((output / 'pre.json').read_bytes()))
                    once.validate_pre_research_transition(discovery, pre, packet.seed_evidence_artifacts)
                    once.require(pre.route.value == 'CONTINUE_TO_QUICK', 'WOTON_QUICK_NOT_REQUIRED')
                    expected.update(stage='QUICK', pre_research=pre.model_dump(mode='json'), pre_research_hash=canonical_hash(pre))
                else:
                    once.require(stage == 'pre' and spent == [], 'WOTON_STAGE_ALREADY_USED')
                once.require((stage, model) in {('pre', once.PreResearchResult), ('quick', once.QuickResearchResult)}
                    and once.raw(prompt) == once.raw(expected), 'WOTON_EXACT_PROMPT_REQUIRED')
                recheck(); deepseek._deepseek_request(prompt, model)
                spent.append(stage)  # Intent is consumed before the provider boundary, including uncertain sends.
                fn = call or partial(once.model_call, max_prompt_bytes=STOCK_PROMPT_BYTES,
                    base_url=once.DEEPSEEK_BASE_URL, model=once.DEEPSEEK_MODEL, api_key_env='DEEPSEEK_API_KEY',
                    provider=deepseek.PROVIDER, extra_parameters={'reasoning': deepseek.REASONING})
                return fn(stage, prompt, model, out, usage)
            return once.research(packet, discovery, context, output, call=guarded, clock=clock,
                provider_event_prefix=deepseek.PROVIDER_EVENT_PREFIX, model_or_executor=deepseek.MODEL_OR_EXECUTOR)

        recheck()
        report, outcome = admission.execute_after_admission(executor=execute, **{**checks, 'checked_at': clock()})
        retain.save('admission.json', report)
        once.require(outcome is not None, report['reason'])
        candidate, validation, usage = outcome
        for name, value in (('candidate.json', candidate), ('receipt.json', candidate.receipt),
                            ('validation.json', validation)):
            retain.save(name, value)
        if validation.funnel_result is not None:
            retain.save('funnel.json', validation.funnel_result)
        retain.save('README.md', summary(candidate, validation))
        result.update(status=validation.status.value, phase='COMPLETE', provider_usage=usage,
            candidate_hash=canonical_hash(candidate), validation_hash=canonical_hash(validation),
            source_manifest=request['source_manifest'], predecessor_progress=request['predecessor_progress'])
    except Exception as exc:
        result.update(status='EXECUTION_INCOMPLETE' if result['formal_research_started'] else 'NOT_EXECUTED',
                      error_type=type(exc).__name__)
        reason = getattr(exc, 'code', None)
        if isinstance(reason, str) and re.fullmatch(r'[A-Z0-9_]{1,128}', reason): result['error_code'] = reason
    finally:
        result.update(finished_at=clock(), mutation_uncertain=bool(retain and retain.uncertain))
        if reserved and retain is not None and not retain.uncertain:
            try: retain.save('host-receipt.json', result)
            except Exception:
                result.update(status='RETENTION_INCOMPLETE', mutation_uncertain=retain.uncertain)
                (output / 'host-retention-failure.json').write_bytes(once.raw(result))
        else:
            (output / 'host-receipt-local.json').write_bytes(once.raw(result))
    return result


def check_environment(env, code):
    once.require(reading.SHA.fullmatch(code or '') is not None and env.get('GITHUB_SHA') == code
        and env.get('EXPECTED_CODE_SHA') == code and env.get('GITHUB_REPOSITORY') == once.REPO
        and env.get('GITHUB_REF') == 'refs/heads/main' and env.get('GITHUB_WORKFLOW') == 'stock-business-research'
        and env.get('GITHUB_EVENT_NAME') == 'issues' and env.get('GITHUB_RUN_ATTEMPT') == '1'
        and str(env.get('GITHUB_RUN_ID', '')).isdigit() and int(env['GITHUB_RUN_ID']) > 0
        and env.get('REPORT_EVENT_ACTION') == 'labeled' and env.get('REPORT_ISSUE_NUMBER') == '297'
        and env.get('REPORT_LABEL') == LABEL and env.get('REPORT_SENDER') == 'auguspp'
        and env.get('REPORT_IS_PULL_REQUEST') == 'false', 'WOTON_CONTINUATION_EVENT_REJECTED')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-commit', required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv); check_environment(os.environ, args.code_commit)
    once.require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == args.code_commit,
                 'WOTON_CONTINUATION_CHECKOUT_CHANGED')
    result = run(api=GitHubAPI(os.environ['GH_TOKEN'], max_calls=1024), code=args.code_commit, output=args.output)
    print(once.raw(result).decode())
    return 0 if result['status'] in {'VALIDATED_FUNNEL_RESULT', REUSED} else 2


if __name__ == '__main__':
    raise SystemExit(main())
