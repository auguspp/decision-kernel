"""Long immutable prompts are compared as bytes, not parsed with small-file limits."""
import pytest
from test_r4_2_source_context_check import check, pilot
from test_source_check_context import no_network


def test_large_previous_prompt_is_compared_without_json_reparse(monkeypatch):
    prompt={'public_context':{'text':'A'*(1024*1024)},'host_source_checks':{'scope':'synthetic'}}
    previous=pilot.once.raw({'public_context':prompt['public_context']})
    def deny(*a,**kw): raise AssertionError('Do not reparse an exact original prompt')
    monkeypatch.setattr(pilot.once.identity,'_json',deny)
    check.check_previous_prompt(prompt,previous)


def test_byte_change_is_rejected_not_normalized_away():
    prompt={'public_context':{'text':'original'},'host_source_checks':{}}
    previous=pilot.once.raw({'public_context':prompt['public_context']})
    with pytest.raises(ValueError,match='PREVIOUS_PROMPT_DIFFERENT'):
        check.check_previous_prompt(prompt,previous+b' ')
