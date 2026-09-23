"""Real parent records with synthetic Git/model I/O through the original host.

Frozen evidence is not a new company conclusion. The trusted-page recheck edge
is substituted explicitly; its existing PDF/visual-note tests remain blocking.
"""
import base64
from copy import deepcopy
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_quick_continuation as resume
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import current_state as reading
from decision_kernel.runtime import current_state_delivery as delivery
from test_saved_research_once import quick

FIXTURE = Path(__file__).parent / 'fixtures/industry_quick_contract_20260923'
NOW = '2026-09-23T07:00:00+00:00'
CODE = 'a' * 40
WORK = '4b9988f20aa41810c6818d101e2bdb37cf139bde'
RUN = 35819538967


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('native continuation tests cannot access live networking')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def setup(tmp_path, monkeypatch):
    saved = lambda name: (FIXTURE / name).read_bytes()
    parent = once.ExternalResearchInputPacket.model_validate_json(saved('input.json'))
    original = json.loads(saved('original-request.json'))
    question = json.loads(saved('question.json'))
    root = parent.candidate_output_prefix
    files = {CODE: {},
             WORK: {root + name: saved(name) for name, _ in resume.previous.PREDECESSOR_FILES.values()},
             parent.code_commit: {daily.REQUEST: once.raw(original)}}
    files[WORK][root + 'prepare.json'] = saved('prepare.json')
    def put(spec, raw): files.setdefault(spec['ref'], {})[spec['path']] = raw
    for key, name in [('context_source', 'source.json'), ('question_source', 'question.json'),
                      ('preflight_source', 'preflight.json')]:
        put(original[key], saved(name))
    # Capacity only uses the original reading's Stock inventory. This synthetic
    # empty inventory is NOT used as financial evidence or a revalidated reading.
    put(question['reading_source'], once.raw({'lanes': {}}))
    admitted = json.loads(saved('admission.json'))
    put(admitted['input_source'], saved('input.json'))
    # The original identity gate intentionally requires a nonempty pinned scope.
    # Bind the existing parent input, not an invented approval for the new child.
    files[CODE][once.identity.CATALOG_PATH] = once.raw({'schema_version': 1, 'inputs': [
        {**once.identity.input_key(parent).as_dict(), 'input': admitted['input_source']}]})
    # Small synthetic Git inventory using one existing real note. The continuation
    # must actually read both versions; the original full-PDF checks stay separate.
    from decision_kernel.runtime import disclosure_source_reading as pages
    context = json.loads(resume.full.unpack(saved('source.json'), ticker=parent.ticker))
    doc = next(d for d in context['issuer_documents'] if resume.full.referenced_reading(d.get('page_reading')))
    note_path = pages.review_path(doc['pdf_sha256'], 100)
    note = (Path(__file__).parents[1] / note_path).read_bytes()
    files.setdefault(doc['page_reading']['review_commit'], {})[note_path] = note
    files[CODE][note_path] = note
    specs = {key: once.source_ref(root + name, WORK, saved(name), purpose)
             for key, (name, purpose) in resume.previous.PREDECESSOR_FILES.items()}
    comment = {'id': 123, 'body': 'SYNTHETIC explicit corrective Quick, not real permission.',
        'created_at': '2026-09-23T06:00:00Z',
        'issue_url': 'https://api.github.com/repos/' + once.REPO + '/issues/297'}
    request = {'schema_version': 1, 'enabled': True, 'mode': resume.MODE,
        'permission': {'comment_id': comment['id'], 'body_sha256': once.sha(comment['body'].encode()),
                       'created_at': comment['created_at']},
        'predecessor': {'run_id': RUN, 'work_commit': WORK, 'sources': specs},
        'source_scope': resume.SOURCE_SCOPE}
    files[CODE][daily.REQUEST] = once.raw(request)
    meta = {ref: {'sha': ref, 'committer': {'date': '2026-09-23T04:00:00Z'}} for ref in files}
    cs = original['context_source']
    meta[cs['ref']]['committer']['date'] = parent.seed_evidence_artifacts[0].published_at.isoformat()
    pf = json.loads(saved('preflight.json'))
    meta[original['preflight_source']['ref']]['committer']['date'] = pf['finished_at']
    heads = {'main': CODE, intake.WORK_REF: WORK}
    run = {'id': RUN, 'head_sha': parent.code_commit,
        'path': '.github/workflows/stock-business-research.yml', 'head_branch': 'main', 'run_attempt': 1,
        'event': 'issues', 'repository': {'full_name': once.REPO}, 'head_repository': {'full_name': once.REPO},
        'status': 'completed', 'conclusion': 'failure', 'updated_at': '2026-09-23T04:49:05Z'}
    calls, writes, page_checks = [], [], []
    class API:
        def __init__(self):
            self.calls = 0; self.max_calls = 1024
            self.files = files; self.heads = heads; self.comment = comment
        def file(self, path, ref):
            self.calls += 1
            try: return files[ref][path]
            except KeyError: raise delivery.GitHubReadError('GitHub HTTP 404') from None
        def get(self, path):
            self.calls += 1
            if path.startswith('git/ref/heads/'):
                return {'object': {'sha': heads[path.removeprefix('git/ref/heads/')], 'type': 'commit'}}
            if path.startswith('issues/comments/'): return deepcopy(self.comment)
            if path == 'actions/runs/' + str(RUN): return deepcopy(run)
            if path.startswith('git/commits/'): return deepcopy(meta[path.removeprefix('git/commits/')])
            if path.startswith('git/trees/'):
                ref = path.split('/')[2].split('?')[0]
                return {'truncated': False, 'tree': [{'path': p, 'sha': once.blob(b), 'size': len(b),
                    'mode': '100644', 'type': 'blob'} for p, b in files[ref].items()]}
            if path.startswith('git/matching-refs/heads/'):
                return [{'ref': 'refs/heads/' + k, 'object': {'sha': v, 'type': 'commit'}}
                    for k, v in heads.items() if k.startswith(path.removeprefix('git/matching-refs/heads/'))]
            raise AssertionError(path)
        def _call(self, method, path):
            assert method == 'GET'; value = self.get(path)
            return SimpleNamespace(json=lambda: value)
    api = API()
    def native(owner, method, endpoint, body):
        writes.append(endpoint)
        assert method == 'PUT' and endpoint.startswith('contents/') and 'sha' not in body
        assert body['branch'] == intake.WORK_REF
        path = endpoint.removeprefix('contents/'); before = heads[intake.WORK_REF]
        if path in files[before]:
            owner.uncertain = True
            raise ValueError('existing file')
        new = f'{len(writes):040x}'
        files[new] = {**files[before], path: base64.b64decode(body['content'])}
        heads[intake.WORK_REF] = new
        meta[new] = {'sha': new, 'committer': {'date': NOW}}
        return {'commit': {'sha': new}, 'content': {'sha': once.blob(files[new][path])}}
    monkeypatch.setattr(once.Retainer, 'native', native)
    monkeypatch.setattr(once, 'now', lambda: NOW)
    def page_check(context, *, api, code, clock):
        assert [d['page_count'] for d in context['issuer_documents']] == [262, 216]
        assert code == CODE and clock() == NOW
        page_checks.append(code)
    monkeypatch.setattr(resume.full, 'recheck_pages', page_check)
    def call(stage, prompt, model, out, usage):
        calls.append(stage)
        assert stage == 'quick' and model is once.QuickResearchResult
        assert prompt['continuation_scope']['source_freshness'] == 'ORIGINAL_CUTOFF_NOT_RECHECKED_AS_CURRENT'
        assert prompt['binding']['as_of'] == parent.research_cutoff.isoformat()
        return quick(prompt)
    args = dict(api=api, code=CODE, output=tmp_path / 'resume', call=call, clock=lambda: NOW, daily=True)
    return SimpleNamespace(api=api, args=args, files=files, heads=heads, meta=meta, request=request,
        original=original, root=root, parent=parent, run=run, calls=calls, writes=writes, page_checks=page_checks)


def test_native_host_reuses_expired_but_frozen_source_scope_without_pre_or_new_day(tmp_path, monkeypatch):
    c = setup(tmp_path, monkeypatch)
    before = deepcopy(c.files)
    result = host.run_question(**c.args)
    assert result['status'] == 'VALIDATED_FUNNEL_RESULT', json.dumps(result, ensure_ascii=False)
    assert c.calls == ['quick'] and result['pre_model_calls'] == 0
    assert result['quick_model_attempts'] == 1 and c.page_checks == [CODE, CODE]
    for ref, body in before.items(): assert c.files[ref] == body
    assert all('/daily-stock-questions-v0/' not in path for path in c.writes)
    prefix = c.root + resume.previous.CHILD
    saved = c.files[c.heads[intake.WORK_REF]]
    checked = json.loads(saved[prefix + 'admission.json'])
    assert checked['source_freshness'] == 'ORIGINAL_CUTOFF_NOT_CURRENT_PREFLIGHT'
    assert checked['source_checked_at'] == c.parent.research_cutoff.isoformat()
    assert checked['checked_at'] == NOW and checked['research_execution_allowed']
    candidate = json.loads(saved[prefix + 'candidate.json'])
    assert candidate['pre_research'] == json.loads(before[WORK][c.root + 'candidate.json'])['pre_research']
    assert candidate['receipt']['technical_retries_used'] == 1
    assert result['investment_authority'] == 'NONE' and not result['registered_current_handoff']
    baseline = reading.assemble(code_commit=CODE, checked_at=NOW, check_started_at=NOW, lanes={},
        research={'handoffs': {'active': []}, 'stock_business_work': {'status': 'READ_OK', 'items': []}},
        capabilities=[], refresh_identity={})
    collector = delivery.Collector(c.api, CODE, tmp_path / 'reading', now=lambda: NOW)
    c.api.calls = 0
    collector.files = {'README.md': reading.render_summary(baseline).encode(), 'current-state.json': reading.json_bytes(baseline)}
    final = reader.attach(collector, baseline)
    entry = final['research']['reviewed_question_work']
    assert entry['status'] == 'READ_OK', entry
    data = json.loads(collector.files[reader.REPORT])['question_work']['items']
    by_role = {row['role']: row for row in data}
    assert by_role['ROOT']['status'] == 'VALIDATED_EXECUTION_GAP'
    assert by_role['TECHNICAL_CONTINUATION']['status'] == 'VALIDATED_FUNNEL_RESULT'
    assert by_role['TECHNICAL_CONTINUATION']['quick_present']
    assert by_role['TECHNICAL_CONTINUATION']['predecessor_execution_id'] == by_role['ROOT']['execution_id']
    assert c.calls == ['quick']


@pytest.mark.parametrize('damage', ['revoked', 'main', 'parent-blob', 'missing-parent', 'run-code', 'run-unfinished',
                                    'run-success', 'run-rerun', 'run-repository', 'question-bytes', 'context-bytes',
                                    'preflight-bytes', 'future-now', 'scope', 'page-recheck'])
def test_ineligible_checkpoint_stops_before_any_writes_or_model(tmp_path, monkeypatch, damage):
    c = setup(tmp_path, monkeypatch)
    if damage == 'revoked': c.api.comment['body'] += ' revoked'
    elif damage == 'main': c.heads['main'] = 'b' * 40
    elif damage == 'parent-blob': c.files[WORK][c.root + 'candidate.json'] += b' '
    elif damage == 'missing-parent': del c.files[WORK][c.root + 'admission.json']
    elif damage.startswith('run-'):
        k, v = {'run-code': ('head_sha', 'b' * 40), 'run-unfinished': ('status', 'in_progress'),
            'run-success': ('conclusion', 'success'), 'run-rerun': ('run_attempt', 2),
            'run-repository': ('repository', {'full_name': 'other/repo'})}[damage]
        c.run[k] = v
    elif damage.endswith('-bytes'):
        key = {'question-bytes': 'question_source', 'context-bytes': 'context_source', 'preflight-bytes': 'preflight_source'}[damage]
        spec = c.original[key]; c.files[spec['ref']][spec['path']] += b' '
    elif damage == 'future-now': c.args['clock'] = lambda: '2026-09-23T04:00:00Z'
    elif damage == 'scope':
        c.request['source_scope'] = 'LATEST'
        c.files[CODE][daily.REQUEST] = once.raw(c.request)
    else:
        def reject(*a, **k): raise once.TrialError('SYNTHETIC_PAGE_RECHECK_FAILED')
        monkeypatch.setattr(resume.full, 'recheck_pages', reject)
    before = deepcopy(c.files)
    result = host.run_question(**c.args)
    assert result['status'] == 'NOT_EXECUTED', result
    assert c.calls == [] and c.writes == [] and c.files == before


@pytest.mark.parametrize('existing', ['prepare.json', 'input.json', 'launch.json', 'candidate.json'])
def test_partial_or_complete_child_is_never_reopened(tmp_path, monkeypatch, existing):
    c = setup(tmp_path, monkeypatch)
    c.files[WORK][c.root + resume.previous.CHILD + existing] = b'{}'
    before = deepcopy(c.files)
    result = host.run_question(**c.args)
    assert result['status'] == 'EXISTING_QUESTION_REUSED_NO_EXECUTION', result
    assert c.files == before and not c.calls and not c.writes


@pytest.mark.parametrize('damage', ['permission', 'child-marker', 'uncertain-launch'])
def test_launch_race_or_uncertain_mutation_does_not_call_provider(tmp_path, monkeypatch, damage):
    c = setup(tmp_path, monkeypatch)
    original = once.Retainer.native
    def write(owner, method, endpoint, body):
        result = original(owner, method, endpoint, body)
        if endpoint.endswith('/launch.json'):
            if damage == 'permission': c.api.comment['body'] += ' revoked'
            elif damage == 'child-marker':
                c.files[c.heads[intake.WORK_REF]][c.root + resume.previous.CHILD + 'prepare.json'] += b' '
            else:
                owner.uncertain = True
                raise ValueError('SYNTHETIC uncertain reply')
        return result
    monkeypatch.setattr(once.Retainer, 'native', write)
    result = host.run_question(**c.args)
    assert any(path.endswith('/launch.json') for path in c.writes), json.dumps(result, ensure_ascii=False)
    assert not c.calls and result['status'] in {'NOT_EXECUTED', 'EXECUTION_GAP'}, json.dumps(result, ensure_ascii=False)
    if damage == 'uncertain-launch':
        assert result['mutation_uncertain']
        assert c.writes[-1].endswith('/launch.json')


def test_second_quick_failure_retains_parent_and_cannot_trigger_another_call(tmp_path, monkeypatch):
    c = setup(tmp_path, monkeypatch)
    def failed(stage, prompt, model, out, usage):
        c.calls.append(stage)
        raw = (FIXTURE / 'quick-model-output.txt').read_bytes()
        (out / 'quick-model-output.txt').write_bytes(raw)
        return model.model_validate_json(raw)
    c.args['call'] = failed
    before = deepcopy(c.files[WORK])
    result = host.run_question(**c.args)
    assert result['status'] == 'EXECUTION_GAP', json.dumps(result, ensure_ascii=False)
    assert c.calls == ['quick'] and c.files[WORK] == before
    count = len(c.writes); c.args['output'] = tmp_path / 'again'
    again = host.run_question(**c.args)
    assert again['status'] == 'EXISTING_QUESTION_REUSED_NO_EXECUTION', again
    assert c.calls == ['quick'] and len(c.writes) == count


def test_empty_execution_catalogue_is_still_rejected_before_spending(tmp_path, monkeypatch):
    c = setup(tmp_path, monkeypatch)
    c.files[CODE][once.identity.CATALOG_PATH] = once.raw({'schema_version': 1, 'inputs': []})
    before = deepcopy(c.files)
    result = host.run_question(**c.args)
    assert result['status'] == 'NOT_EXECUTED', json.dumps(result, ensure_ascii=False)
    assert result['error_code'] == 'EXECUTION_SCOPE_INVALID_OR_INCOMPLETE'
    assert not c.calls and not c.writes and c.files == before
