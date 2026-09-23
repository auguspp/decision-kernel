"""Offline tests for the two-call #532 verification, not model quality claims."""
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket
from test_source_check_context import no_network

ROOT = Path(__file__).parents[1]
# Explicit experiment imports; do not replace any installed SDK module.
spec = importlib.util.spec_from_file_location('r4_2_sub2api', ROOT/'experiments/r4_2_sub2api.py')
pilot = importlib.util.module_from_spec(spec); spec.loader.exec_module(pilot)
sys.modules.setdefault('r4_2_sub2api', pilot)
spec = importlib.util.spec_from_file_location('r4_source_check_eval', ROOT/'experiments/r4_2_source_context_check.py')
check = importlib.util.module_from_spec(spec); spec.loader.exec_module(check)


def case():
    root = ROOT/'tests/fixtures/host_source_check_context'
    packet = ExternalResearchInputPacket.model_validate_json((root/'input.json').read_bytes())
    discovery = SimpleNamespace(discovery_id='synthetic-eval-test', ticker=packet.ticker,
        source_lane=packet.source_lane, why_now='synthetic test, not a new observation', factual_observations=())
    return packet, discovery, {'untouched_text':'synthetic test payload'}, (root/'preflight.json').read_bytes()


def test_only_bound_source_checks_added_and_old_clock_unchanged():
    p,d,ctx,pf = case(); before = p.model_dump_json()
    prompt = check.corrected_prompt(p,d,ctx,pf)
    assert prompt['public_context'] is ctx and p.model_dump_json()==before
    assert prompt['host_source_checks']['preflight_source']['sha256']==pilot.once.sha(pf)
    assert prompt['binding']['as_of']==p.research_cutoff.isoformat()
    assert prompt['stage']=='QUICK' and 'pre_research' not in prompt
    assert prompt['host_source_checks']['inventories'][0]['query_events'][0]['status']=='SUCCEEDED'


@pytest.mark.parametrize('damage',['bytes','binding','expired'])
def test_invalid_source_metadata_rejected_before_call(damage):
    p,d,ctx,pf = case()
    if damage=='bytes': pf += b' '
    elif damage=='binding': p=p.model_copy(update={'source_refs':()})
    else:
        from datetime import timedelta
        p=p.model_copy(update={'research_cutoff':p.research_cutoff+timedelta(days=2)})
    with pytest.raises(ValueError): check.corrected_prompt(p,d,ctx,pf)


def test_same_corrected_prompt_and_only_policy_description_differs():
    prompt=check.corrected_prompt(*case())
    a=pilot.parameters(prompt,pilot.single.QuickAssessment,'S0')
    b=pilot.parameters(prompt,pilot.single.QuickAssessment,'S1')
    assert a != b
    a['text']['format']['schema']['properties']['route']['description']=b['text']['format']['schema']['properties']['route']['description']
    assert a==b and json.loads(a['input'][0]['content'])==json.loads(b['input'][0]['content'])


@pytest.mark.parametrize('stop',[False,True])
def test_two_arms_only_no_o_no_repeat_and_transport_stop(tmp_path,stop):
    seen=[]; prompt={'test':'exact same input'}
    def send(p,model,arm,out):
        assert p is prompt and model is pilot.single.QuickAssessment
        seen.append((arm,out)); return None,{'physical_sends':1,'stop_batch':stop}
    records=check.run_pair(prompt,tmp_path,send=send)
    assert [a for a,p in seen]==(['S0'] if stop else ['S0','S1'])
    assert len(records)==len(seen) and all(p.parent==tmp_path for a,p in seen)


def test_unexpected_send_accounting_is_not_hidden(tmp_path):
    def send(*args): return None,{'physical_sends':2,'stop_batch':False}
    with pytest.raises(ValueError,match='CORRECTION_CALL_BOUND'):
        check.run_pair({},tmp_path,send=send)


def test_import_has_no_activation_and_same_root_is_preserved():
    assert check.ROOT==pilot.PREFIX
    assert check.PREFIX==pilot.PREFIX+'continuations/source-context-532-v1/'
    assert check.PARENT=='f0c9104c9dbc2b2fbdcf90b7b75bb024827509b2'
    assert check.ARMS==('S0','S1')
