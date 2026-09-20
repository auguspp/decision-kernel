"""Offline contracts for the explicit DeepSeek V4.1 compatibility slice."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.research_funnel import PreResearchResult
from decision_kernel.runtime import saved_research_once as once

ROOT = Path(__file__).parents[1]
MODULE = ROOT / "eval" / "deepseek_responses_probe.py"
spec = importlib.util.spec_from_file_location("deepseek_responses_probe", MODULE)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def valid_pre(prompt):
    return PreResearchResult(
        discovery_id=prompt["binding"]["discovery_id"],
        as_of=prompt["binding"]["as_of"],
        what_is_this="Synthetic API compatibility probe",
        economic_direction="UNKNOWN",
        why_surfaced_now="Provider compatibility needs checking",
        basic_business_role="UNKNOWN",
        potential_fundamental_driver="UNKNOWN",
        current_market_expectation_hypothesis="UNKNOWN",
        material_claims=[{
            "statement": "Synthetic public compatibility string was supplied.",
            "kind": "FACT",
            "evidence_artifact_ids": prompt["evidence_ids"],
        }],
        largest_unknown="Company economics are out of scope.",
        next_discriminating_search="NONE",
        route="STOP",
        route_reason="Compatibility probe only.",
    )


def fake_response(prompt):
    parsed = valid_pre(prompt)
    return SimpleNamespace(
        output_text=parsed.model_dump_json(),
        status="completed",
        id="deepseek-synthetic-response",
        usage=None,
        output=[SimpleNamespace(type="message")],
    )


def test_explicit_deepseek_binding_uses_only_dedicated_secret(tmp_path, monkeypatch):
    import openai

    seen = {}
    response = fake_response(probe.PROMPT)

    class Stream:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def get_final_response(self):
            return response

    class Client:
        def __init__(self, **kwargs):
            seen["client"] = kwargs
            self.responses = self
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def stream(self, **kwargs):
            seen["request"] = kwargs
            return Stream()

    monkeypatch.setattr(openai, "OpenAI", Client)
    monkeypatch.setattr(openai, "DefaultHttpxClient", lambda **kwargs: kwargs)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-synthetic-secret")
    monkeypatch.setenv("SUB2API_API_KEY", "old-relay-secret-must-not-be-used")
    usage = []

    parsed = once.model_call(
        "pre", probe.PROMPT, PreResearchResult, tmp_path, usage,
        max_prompt_bytes=once.MAX_PROMPT_BYTES,
        base_url=once.DEEPSEEK_BASE_URL,
        model=once.DEEPSEEK_MODEL,
        api_key_env="DEEPSEEK_API_KEY",
        provider=probe.PROVIDER,
        extra_parameters={"reasoning": {"effort": "none"}},
    )

    assert parsed.route.value == "STOP"
    assert seen["client"]["api_key"] == "deepseek-synthetic-secret"
    assert seen["client"]["base_url"] == "https://api.deepseek.com"
    assert seen["client"]["max_retries"] == 0
    assert seen["client"]["http_client"]["follow_redirects"] is False
    assert seen["request"]["model"] == "deepseek-flash"
    assert seen["request"]["reasoning"] == {"effort": "none"}
    assert seen["request"]["text"]["format"]["type"] == "json_schema"
    assert set(seen["request"]["text"]["format"]) == {"type", "name", "schema"}
    assert "strict" not in seen["request"]["text"]["format"]
    assert seen["request"]["tools"] == []
    assert seen["request"]["store"] is False
    assert usage[0]["provider"] == "DEEPSEEK_OFFICIAL"
    assert usage[0]["provider_base_url"] == once.DEEPSEEK_BASE_URL
    saved = "\n".join(path.read_text() for path in tmp_path.iterdir())
    assert "deepseek-synthetic-secret" not in saved
    assert "old-relay-secret-must-not-be-used" not in saved


def test_provider_error_diagnostic_is_finite_and_drops_message(tmp_path, monkeypatch):
    import openai

    class Denied(Exception):
        status_code = 403
        request_id = "req_safe-123"
        body = {
            "error": {
                "code": "AUTH_DENIED",
                "type": "permission_error",
                "message": "SECRET UPSTREAM DETAIL MUST NOT BE RETAINED",
            }
        }

    class Client:
        def __init__(self, **kwargs):
            self.responses = self
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def stream(self, **kwargs):
            raise Denied("SECRET EXCEPTION TEXT")

    monkeypatch.setattr(openai, "OpenAI", Client)
    monkeypatch.setattr(openai, "DefaultHttpxClient", lambda **kwargs: kwargs)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-secret")
    usage = []

    with pytest.raises(Denied):
        once.model_call(
            "pre", probe.PROMPT, PreResearchResult, tmp_path, usage,
            max_prompt_bytes=once.MAX_PROMPT_BYTES,
            base_url=once.DEEPSEEK_BASE_URL,
            model=once.DEEPSEEK_MODEL,
            api_key_env="DEEPSEEK_API_KEY",
            provider=probe.PROVIDER,
            extra_parameters={"reasoning": {"effort": "none"}},
        )

    record = usage[0]
    assert record["status"] == "FAILED"
    assert record["http_status"] == 403
    assert record["request_id"] == "req_safe-123"
    assert record["provider_error_code"] == "AUTH_DENIED"
    assert record["provider_error_type"] == "permission_error"
    assert "message" not in record
    assert "SECRET" not in json.dumps(record)




def test_model_call_rejects_cross_provider_binding_before_secret_or_network(tmp_path):
    usage = []
    with pytest.raises(once.TrialError, match="provider binding"):
        once.model_call(
            "pre", probe.PROMPT, PreResearchResult, tmp_path, usage,
            max_prompt_bytes=once.MAX_PROMPT_BYTES,
            base_url=once.DEEPSEEK_BASE_URL,
            model=once.MODEL,
            api_key_env="DEEPSEEK_API_KEY",
            provider=probe.PROVIDER,
            extra_parameters={"reasoning": {"effort": "none"}},
        )
    assert usage == [] and list(tmp_path.iterdir()) == []


def test_provider_error_diagnostic_accepts_sdk_unwrapped_error_body():
    exc = SimpleNamespace(
        status_code=400,
        request_id=None,
        body={
            "code": "INVALID_REQUEST",
            "type": "invalid_request_error",
            "message": "must never be retained",
        },
    )
    assert once._provider_error_diagnostic(exc) == {
        "http_status": 400,
        "provider_error_code": "INVALID_REQUEST",
        "provider_error_type": "invalid_request_error",
    }


def test_provider_error_diagnostic_rejects_unsafe_identifiers():
    exc = SimpleNamespace(
        status_code=True,
        request_id="unsafe request id with spaces",
        body={"error": {"code": "bad code with spaces", "type": 123}},
    )
    assert once._provider_error_diagnostic(exc) == {}


@pytest.mark.parametrize("patch", [
    {"GITHUB_RUN_ATTEMPT": "2"},
    {"GITHUB_REF": "refs/heads/other"},
    {"GITHUB_EVENT_NAME": "push"},
    {"EXPECTED_CODE_SHA": "b" * 40},
    {"DEEPSEEK_API_KEY": ""},
])
def test_probe_native_identity_fails_closed(patch):
    env = {
        "GITHUB_REPOSITORY": once.REPO,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "123",
        "GITHUB_SHA": "a" * 40,
        "EXPECTED_CODE_SHA": "a" * 40,
        "DEEPSEEK_API_KEY": "synthetic",
    }
    env.update(patch)
    with pytest.raises(once.TrialError):
        probe._identity(env)


def test_probe_success_is_synthetic_and_verifiable(tmp_path, monkeypatch):
    out = tmp_path / "probe"
    parsed = valid_pre(probe.PROMPT)

    def call(stage, context, output_type, output, usage, **kwargs):
        usage.append({
            "stage": "pre",
            "provider": probe.PROVIDER,
            "provider_base_url": once.DEEPSEEK_BASE_URL,
            "requested_model": once.DEEPSEEK_MODEL,
            "status": "completed",
        })
        return parsed

    monkeypatch.setattr(once, "model_call", call)
    result = probe.run_probe(out, {"code_sha": "a" * 40})
    assert result["status"] == "COMPATIBILITY_PASSED"
    assert probe.verify(out) == "COMPATIBILITY_PASSED"
    assert json.loads((out / "parsed.json").read_text())["route"] == "STOP"
    text = json.dumps(probe.PROMPT, ensure_ascii=False)
    assert "300711" not in text and "SZSE" not in text and "广哈通信" not in text


def test_historical_defaults_remain_old_provider():
    params = once.response_parameters("{}", {"type": "json_object"})
    assert params["model"] == "gpt-6-astra"
    assert "reasoning" not in params
    assert once.BASE_URL == "https://ai.6600600.xyz/v1"


def test_only_reasoning_is_an_allowed_explicit_provider_parameter():
    with pytest.raises(once.TrialError):
        once.response_parameters("{}", {"type": "json_object"}, model=once.DEEPSEEK_MODEL,
                                 extra_parameters={"temperature": 0})
    with pytest.raises(once.TrialError):
        once.response_parameters("{}", {"type": "json_object"}, model=once.DEEPSEEK_MODEL,
                                 extra_parameters={"reasoning": {"effort": "medium"}})


def test_workflow_isolates_deepseek_probe_from_research_job():
    workflow = (ROOT / ".github/workflows/stock-business-research.yml").read_text()
    assert "deepseek-compat:" in workflow
    assert "!(github.event_name == 'workflow_dispatch' && inputs.deepseek-compat)" in workflow
    assert "deepseek-compatibility:" in workflow
    assert "secrets.DEEPSEEK_API_KEY" in workflow
    assert "eval/deepseek_responses_probe.py" in workflow
    assert "permissions:\n      contents: read" in workflow
    assert "research-work/stock-business-v0" not in (ROOT / "eval/deepseek_responses_probe.py").read_text()
