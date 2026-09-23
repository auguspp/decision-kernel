"""Shared Full proposals; no hosted execution or new company research."""
from copy import deepcopy
import json
import socket

import pytest
from decision_kernel.runtime import full_research_commission as full
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import attention_inbox as brief
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import current_state as reading
from test_direct_deep import req as direct_request
from test_single_quick_contract import synthetic


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError('No network in commission validation')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


def human_args():
    req = direct_request()
    request_raw = once.raw(req)
    permission_raw = b'SYNTHETIC bounded Human request, not real consent.'
    return dict(request_source=once.source_ref('human/request.json', 'a'*40, request_raw, 'HUMAN_DIRECT_FULL_REQUEST'),
                permission_source=once.source_ref('human/permission.txt', 'b'*40, permission_raw, 'HUMAN_FULL_PERMISSION'),
                request_raw=request_raw, permission_raw=permission_raw)


def test_human_full_uses_same_commission_without_fake_discovery_or_quick():
    args = human_args()
    c = full.from_human(**args)
    assert c.origin.research_origin == 'HUMAN_ORIGIN_DIRECT_DEEP'
    assert c.execution_authority == c.investment_authority == 'NONE'
    payload = c.model_dump(mode='json')
    assert not any(k in payload for k in ('pre_research', 'quick_research', 'discovery', 'handoff'))
    assert not hasattr(c.origin, 'handoff')
    parents = {args['request_source']['path']: args['request_raw'], args['permission_source']['path']: args['permission_raw']}
    assert full.verify(c, load=lambda s: parents[s['path']]) == c
    assert c.outcome_contract == 'research-outcome-contract-v1'


@pytest.mark.parametrize('damage', ['origin', 'scope', 'cutoff', 'budget', 'permission', 'source', 'fake-quick'])
def test_common_commission_never_certifies_mutated_origin_or_permissions(damage):
    args = human_args();c = full.from_human(**args);data = c.model_dump(mode='json')
    if damage == 'origin': data['origin']['research_origin'] = 'QUICK_RESEARCH_CANDIDATE'
    elif damage == 'scope': data['scope'] += ' expanded'
    elif damage == 'cutoff': data['research_cutoff'] = '2026-09-23T00:00:00Z'
    elif damage == 'budget': data['execution_budget']['max_source_reads'] += 1
    elif damage == 'permission': data['execution_authority'] = 'ALLOWED'
    elif damage == 'source': args['request_raw'] += b'changed'
    else: data['origin']['pre_research'] = {}
    parents = {args['request_source']['path']: args['request_raw'], args['permission_source']['path']: args['permission_raw']}
    with pytest.raises(ValueError):
        full.verify(full.FullResearchCommission.model_validate(data), load=lambda s: parents[s['path']])


def test_single_attention_requires_real_result_and_exact_registered_execution():
    p, c = synthetic()
    wrapper = brief.ResearchAttentionHandoff(single_quick_input=p, single_quick_candidate=c)
    raw = brief.serialize_research_attention_handoff(wrapper).encode()
    key = identity.input_key(p)
    ins = once.source_ref(p.candidate_output_prefix+'input.json', 'a'*40, once.raw(p), 'INPUT')
    cs = once.source_ref(p.candidate_output_prefix+'candidate.json', 'b'*40, once.raw(c), 'CANDIDATE')
    binding = {**key.as_dict(), 'input': ins, 'candidate': cs}
    catalogue = once.raw({'schema_version': 1, 'inputs': [{**key.as_dict(), 'input': ins}]})
    values = {ins['path']: once.raw(p), cs['path']: once.raw(c), 'handoff.json': raw,
              identity.CATALOG_PATH: catalogue}
    scope = identity.load_execution_scope(catalogue, lambda ref: values[ref['path']])
    assert identity.check_handoff_registration(raw, binding, scope, lambda ref: values[ref['path']]) == key
    changed = json.loads(raw);changed['candidate']['assessment']['explanation'] += ' changed'
    with pytest.raises(ValueError):
        identity.check_handoff_registration(once.raw(changed), binding, scope, lambda ref: values[ref['path']])
    load = lambda ref: (values[ref['path']], {'path': ref['path'], 'sha256': once.sha(values[ref['path']])})
    good = identity.project_registered_handoffs([{'source': {'path': 'handoff.json'}, 'registered_current': True,
                                                'external_execution': binding}], load)
    assert len(good['active']) == 1 and not good['gaps'], good
    unbound = identity.project_registered_handoffs([{'source': {'path': 'handoff.json'}, 'registered_current': True}], load)
    assert unbound['active'] == [] and unbound['gaps']


def test_shared_display_does_not_misinterpret_new_method_as_legacy_funnel():
    p, c = synthetic('WAIT_FOR_TRIGGER')
    wrapper = brief.ResearchAttentionHandoff(single_quick_input=p, single_quick_candidate=c)
    raw = brief.serialize_research_attention_handoff(wrapper)
    assert brief.parse_research_attention_handoff(raw).research_funnel is None
    assert 'WAIT_FOR_TRIGGER' in brief._background_html((wrapper,))
    with pytest.raises(ValueError):
        brief.parse_research_attention_handoff(raw[:-2] + ', "pre_research": {}}')


@pytest.mark.parametrize('route', ['FULL_CANDIDATE', 'WAIT_FOR_TRIGGER', 'STOP'])
def test_new_brief_content_is_escaped_in_both_formats(route):
    p, c = synthetic(route)
    text = '<script>run()</script> ![exfil](https://invalid.example/token) **fake**'
    a = c.assessment.model_copy(update={'explanation': text, 'route_reason': text})
    c = c.model_copy(update={'assessment': a})
    wrapped = brief.ResearchAttentionHandoff(single_quick_input=p, single_quick_candidate=c)
    if route == 'FULL_CANDIDATE':
        md = brief._render_research_markdown(p.ticker, (wrapped,), None)
        html = brief._render_research_html(p.ticker, (wrapped,), None)
    else:
        md = brief._background_markdown((wrapped,));html = brief._background_html((wrapped,))
    assert '<script>' not in html+md and '![exfil]' not in md
    assert '为什么值得看' in html+md
