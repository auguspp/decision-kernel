"""One synthetic DeepSeek V4.1 Responses compatibility call; never company Research.

This probe reuses the existing bounded SDK/schema path with an explicit official
DeepSeek binding. It has no company/security source, Git write, Research authority,
automatic fallback, retry, Deep, Odds or Action.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from decision_kernel.research_funnel import PreResearchResult
from decision_kernel.runtime import saved_research_once as once

SEMANTICS = "DEEPSEEK_V41_SYNTHETIC_RESPONSES_COMPATIBILITY_NOT_RESEARCH"
PROVIDER = "DEEPSEEK_OFFICIAL"
EVIDENCE_ID = "8f9312e8-50df-5d90-a9e5-6d444bcf9248"
PROMPT = {
    "stage": "PRE",
    "binding": {
        "discovery_id": "deepseek-v41-compatibility",
        "as_of": "2026-09-20T00:00:00+00:00",
    },
    "question": (
        "这是合成 API 兼容性测试，不涉及任何公司或证券。"
        "请仅基于 public_context 返回符合所给 JSON schema 的 Pre 结果；"
        "不得添加外部事实。若声明 public_context 中的测试句为 FACT，"
        "只能引用顶层 evidence_ids。"
    ),
    "known_unknowns": ["No company, security, market, valuation or investment claim is in scope."],
    "discovery_observation": {
        "ticker": "SYNTHETIC",
        "source_lane": "API_COMPATIBILITY_PROBE",
        "why_now": "Validate one official provider binding before any company continuation.",
        "factual_observations": [
            {
                "statement": "A synthetic public compatibility string was supplied by the host.",
                "evidence_artifact_ids": [EVIDENCE_ID],
            }
        ],
    },
    "public_context": {
        "probe_statement": "Synthetic public compatibility payload. No company or user-private data.",
        "limitations": "API-format test only; not Evidence truth or Research.",
    },
    "evidence_ids": [EVIDENCE_ID],
}
AUTHORITY = {
    "research_authority": "NONE",
    "human_attention_authority": "NONE",
    "investment_authority": "NONE",
    "signal_transition_authority": "NONE",
}


def _identity(environ=None):
    env = os.environ if environ is None else environ
    sha = env.get("GITHUB_SHA", "")
    if (
        env.get("GITHUB_REPOSITORY") != once.REPO
        or env.get("GITHUB_REF") != "refs/heads/main"
        or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or env.get("GITHUB_RUN_ATTEMPT") != "1"
        or env.get("EXPECTED_CODE_SHA") != sha
        or not re.fullmatch(r"[0-9a-f]{40}", sha)
        or not re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", ""))
    ):
        raise once.TrialError("DEEPSEEK_COMPAT_NATIVE_IDENTITY_REQUIRED")
    if not env.get("DEEPSEEK_API_KEY"):
        raise once.TrialError("DEEPSEEK_API_KEY_REQUIRED")
    return {
        "repository": env["GITHUB_REPOSITORY"],
        "ref": env["GITHUB_REF"],
        "code_sha": sha,
        "event": env["GITHUB_EVENT_NAME"],
        "run_attempt": env["GITHUB_RUN_ATTEMPT"],
        "run_id": env["GITHUB_RUN_ID"],
    }


def _save(path, value):
    with path.open("xb") as stream:
        stream.write(once.raw(value))


def run_probe(output: Path, identity: dict):
    output.mkdir(parents=True, exist_ok=False)
    usage = []
    result = {
        "schema_version": 1,
        "semantics": SEMANTICS,
        "identity": identity,
        "provider": PROVIDER,
        "base_url": once.DEEPSEEK_BASE_URL,
        "model": once.DEEPSEEK_MODEL,
        "reasoning": {"effort": "none"},
        "model_calls": 1,
        "status": "COMPATIBILITY_STARTED",
        "parsed_output_retained": False,
        "automatic_retry": False,
        **AUTHORITY,
    }
    try:
        parsed = once.model_call(
            "pre",
            PROMPT,
            PreResearchResult,
            output,
            usage,
            max_prompt_bytes=once.MAX_PROMPT_BYTES,
            base_url=once.DEEPSEEK_BASE_URL,
            model=once.DEEPSEEK_MODEL,
            api_key_env="DEEPSEEK_API_KEY",
            provider=PROVIDER,
            extra_parameters={"reasoning": {"effort": "none"}},
        )
        _save(output / "parsed.json", parsed)
        result.update(
            status="COMPATIBILITY_PASSED",
            parsed_output_retained=True,
            route=parsed.route.value,
            parsed_sha256=once.sha(once.raw(parsed)),
        )
    except Exception as exc:
        result.update(status="COMPATIBILITY_FAILED", error_type=type(exc).__name__)
    result["provider_usage"] = usage
    result["probe_hash"] = once.sha(once.raw(result))
    _save(output / "probe.json", result)
    return result


def verify(output: Path):
    raw = (output / "probe.json").read_bytes()
    result = json.loads(raw)
    claimed = result.pop("probe_hash")
    if once.sha(once.raw(result)) != claimed:
        raise ValueError("DEEPSEEK_COMPAT_PROBE_HASH_MISMATCH")
    if (
        result["semantics"] != SEMANTICS
        or result["provider"] != PROVIDER
        or result["base_url"] != once.DEEPSEEK_BASE_URL
        or result["model"] != once.DEEPSEEK_MODEL
        or result["reasoning"] != {"effort": "none"}
        or result["model_calls"] != 1
        or result["automatic_retry"] is not False
        or any(result.get(k) != v for k, v in AUTHORITY.items())
        or len(result["provider_usage"]) != 1
    ):
        raise ValueError("DEEPSEEK_COMPAT_CONTRACT_CHANGED")
    usage = result["provider_usage"][0]
    if (
        usage.get("provider") != PROVIDER
        or usage.get("provider_base_url") != once.DEEPSEEK_BASE_URL
        or usage.get("requested_model") != once.DEEPSEEK_MODEL
        or usage.get("stage") != "pre"
    ):
        raise ValueError("DEEPSEEK_COMPAT_PROVIDER_IDENTITY_CHANGED")
    if result["status"] == "COMPATIBILITY_PASSED":
        if not result["parsed_output_retained"] or not (output / "parsed.json").exists():
            raise ValueError("DEEPSEEK_COMPAT_SUCCESS_WITHOUT_PARSED_OUTPUT")
    elif result["status"] != "COMPATIBILITY_FAILED":
        raise ValueError("DEEPSEEK_COMPAT_UNKNOWN_STATUS")
    text = raw.decode("utf-8")
    secret = os.environ.get("DEEPSEEK_API_KEY")
    if secret and secret in text:
        raise ValueError("DEEPSEEK_SECRET_LEAKED")
    return result["status"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        print(verify(args.output))
        return 0
    result = run_probe(args.output, _identity())
    print(result["status"])
    return 0 if result["status"] == "COMPATIBILITY_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
