"""Published Industry bytes cross the real original host without global relaxation."""
from copy import deepcopy
import json
import socket

import pytest

from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import industry_daily_question as industry
from decision_kernel.runtime import stock_question_host as host, saved_research_once as once
from test_industry_daily_question import setup_industry, seal_case


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError("origin capacity tests are offline")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


@pytest.mark.parametrize("size", [573486, 2 * 1024 * 1024, 4 * 1024 * 1024])
def test_large_complete_origin_crosses_native_replay_prepare_admission_and_retention(tmp_path, monkeypatch, size):
    c = setup_industry(tmp_path, monkeypatch)
    # Deliberately synthetic padding outside native replay; no live historical facts.
    c.report["projection"]["synthetic_capacity_context"] = ""
    remaining = size - len(once.raw(c.report))
    c.report["projection"]["synthetic_capacity_context"] = "x" * remaining
    seal_case(c)
    spec = c.q["origins"][0]["source"]
    raw = c.api.file(spec["path"], spec["ref"])
    assert len(raw) == size and size > identity.MAX_BYTES
    original = deepcopy(c.context)
    result = host.run_question(**c.args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert c.calls == ["pre"] and c.context == original
    assert result["investment_authority"] == "NONE"
    again = host.run_question(**{**c.args, "output": tmp_path / "again"})
    assert again["status"] == "EXISTING_QUESTION_REUSED_NO_EXECUTION", again
    assert c.calls == ["pre"]


@pytest.mark.parametrize("damage", ["over-limit", "hash", "duplicate-json-key"])
def test_large_origin_errors_never_reserve_or_call_model(tmp_path, monkeypatch, damage):
    c = setup_industry(tmp_path, monkeypatch)
    c.report["projection"]["synthetic_capacity_context"] = "x" * (
        identity.MAX_READING_BYTES if damage == "over-limit" else 600000)
    seal_case(c)
    spec = c.q["origins"][0]["source"]
    if damage == "hash": c.api.files[spec["ref"]][spec["path"]] += b" "
    elif damage == "duplicate-json-key":
        # Corrupt the retained report; outer identity or strict JSON must reject it.
        raw = c.api.file(spec["path"], spec["ref"])
        altered = b'{"projection_hash":"invalid",' + raw[1:]
        c.api.files[spec["ref"]][spec["path"]] = altered
    result = host.run_question(**c.args)
    assert result["status"] == "NOT_EXECUTED", result
    assert c.calls == [] and c.writes == [] and not result["formal_research_started"]


@pytest.mark.parametrize("path,purpose,accepted", [
    (identity.INDUSTRY_ORIGIN_PATH, identity.INDUSTRY_ORIGIN_PURPOSE, True),
    (identity.INDUSTRY_ORIGIN_PATH, "MODEL_CONTEXT", False),
    ("research_runs/input.json", identity.INDUSTRY_ORIGIN_PURPOSE, False),
    ("details/radar/other.json", identity.INDUSTRY_ORIGIN_PURPOSE, False)])
def test_larger_read_budget_is_only_for_exact_published_origin(path, purpose, accepted):
    raw = once.raw({"synthetic": "x" * 600000})
    spec = once.source_ref(path, "a" * 40, raw, purpose)
    if accepted: assert identity._checked_source(spec, lambda _: raw) == raw
    else:
        with pytest.raises(ValueError, match="EXECUTION_INPUT_SIZE_INVALID"):
            identity._checked_source(spec, lambda _: raw)
    with pytest.raises(ValueError, match="EXECUTION_INPUT_SIZE_INVALID"): identity._json(raw)
    assert identity._json(raw, max_bytes=identity.MAX_READING_BYTES)["synthetic"] == "x" * 600000


def test_large_json_still_rejects_ambiguous_keys_and_invalid_budget():
    with pytest.raises(ValueError, match="EXECUTION_DUPLICATE_JSON_KEY"):
        identity._json(b'{"x":1,"x":2}', max_bytes=identity.MAX_READING_BYTES)
    for size in (True, 0, -1, identity.MAX_READING_BYTES + 1):
        with pytest.raises(ValueError, match="EXECUTION_JSON_BOUND_INVALID"):
            identity._json(b'{}', max_bytes=size)
