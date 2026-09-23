"""Reuse the experiment's SDK fixture fix; no provider or experiment import."""
import importlib
import socket
import sys
from types import SimpleNamespace

import pytest
from test_saved_research_raw_retention import format_converter


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a, **kw): raise AssertionError('SDK fixture test cannot access network')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def test_converter_fixture_preserves_complete_installed_sdk_module(monkeypatch):
    module = importlib.import_module('openai.lib._parsing._responses')
    exports = dict(vars(module))
    converter = format_converter(monkeypatch)
    assert sys.modules[module.__name__] is module and vars(module) == exports
    assert converter is module.type_to_text_format_param
    from openai import OpenAI, DefaultHttpxClient
    import httpx2 as httpx
    def deny(request): raise AssertionError('No request allowed')
    with OpenAI(api_key='synthetic-not-real', base_url='https://invalid.example/v1',
                max_retries=0, http_client=DefaultHttpxClient(
                    transport=httpx.MockTransport(deny), trust_env=False)) as client:
        assert callable(client.responses.stream)


def test_old_converter_replacement_would_destroy_sdk_exports():
    module = importlib.import_module('openai.lib._parsing._responses')
    old = SimpleNamespace(type_to_text_format_param=module.type_to_text_format_param)
    assert set(vars(module)) - set(vars(old)) and not isinstance(module, SimpleNamespace)
