"""Actual SDK module must survive fixture setup; no provider connection."""
import importlib
import sys
from types import SimpleNamespace

import pytest
from test_r4_2_sub2api_experiment import no_network
from test_saved_research_raw_retention import format_converter


def test_converter_fixture_preserves_complete_installed_sdk_module(monkeypatch):
    module = importlib.import_module('openai.lib._parsing._responses')
    exports = dict(vars(module))
    converter = format_converter(monkeypatch)
    assert sys.modules[module.__name__] is module
    assert vars(module) == exports
    assert converter is module.type_to_text_format_param
    # Native client resources import parsing helpers lazily; setup must leave
    # those exports intact regardless of which xdist worker ran SDK code first.
    from openai import OpenAI, DefaultHttpxClient
    import httpx2 as httpx
    def deny(request): raise AssertionError('No model request in fixture test')
    with OpenAI(api_key='synthetic-not-real', base_url='https://invalid.example/v1',
                max_retries=0, http_client=DefaultHttpxClient(
                    transport=httpx.MockTransport(deny), trust_env=False)) as client:
        assert callable(client.responses.stream)


def test_old_converter_replacement_would_destroy_sdk_exports(monkeypatch):
    module = importlib.import_module('openai.lib._parsing._responses')
    old = SimpleNamespace(type_to_text_format_param=module.type_to_text_format_param)
    # Explicit negative evidence for the prior helper's unconditional replacement.
    assert set(vars(module)) - set(vars(old))
    assert not isinstance(module, SimpleNamespace)
