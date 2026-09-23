"""JSON representation is not a plan change; original bytes and types still bind."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import declared_report_sources as capture
from decision_kernel.runtime import declared_report_input as adopted
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_host as host
from test_declared_report_input import setup_declared


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("plan representation regressions are offline")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


@pytest.mark.parametrize("encoding", ["reverse", "compact", "unicode-escaped"])
def test_original_host_accepts_equivalent_trusted_plan_without_changing_originals(tmp_path, monkeypatch, encoding):
    c = setup_declared(tmp_path, monkeypatch, image=True)
    plan = deepcopy(c.manifest["plan"])
    ordered = dict(reversed(list(plan.items())))
    if encoding == "compact":
        encoded = json.dumps(ordered, separators=(",", ":")).encode()
    elif encoding == "unicode-escaped":
        # JSON escape syntax may encode an ASCII letter as well as non-ASCII.
        encoded = json.dumps(ordered, ensure_ascii=True).replace("Synthetic", "\\u0053ynthetic").encode()
    else:
        encoded = (json.dumps(ordered, indent=4) + "\n").encode()
    assert encoded != once.raw(plan) and identity._json(encoded) == plan
    c.api.files[c.source_run["head_sha"]][capture.REQUEST] = encoded
    retained = deepcopy(c.declared_files)
    result = host.run_question(**c.args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert c.calls == ["pre"] and c.declared_files == retained
    assert c.api.files[c.source_run["head_sha"]][capture.REQUEST] == encoded
    assert result["investment_authority"] == "NONE"


@pytest.mark.parametrize("damage", ["bool-for-int", "int-for-bool", "float-for-int", "extra-field",
                                     "period", "duplicate-report", "duplicate-key", "invalid-json"])
def test_semantic_or_ambiguous_plan_changes_still_stop_before_reservation(tmp_path, monkeypatch, damage):
    c = setup_declared(tmp_path, monkeypatch)
    plan = deepcopy(c.manifest["plan"])
    if damage == "bool-for-int": plan["schema_version"] = True
    elif damage == "int-for-bool": plan["enabled"] = 1
    elif damage == "float-for-int": plan["schema_version"] = 1.0
    elif damage == "extra-field": plan["unexpected"] = "not approved"
    elif damage == "period": plan["reports"][0]["period"] = "2025FY"
    elif damage == "duplicate-report": plan["reports"].append(deepcopy(plan["reports"][0]))
    encoded = once.raw(plan)
    if damage == "duplicate-key": encoded = b'{"schema_version":1,' + encoded[1:]
    elif damage == "invalid-json": encoded += b"null"
    c.api.files[c.source_run["head_sha"]][capture.REQUEST] = encoded
    result = host.run_question(**c.args)
    assert result["status"] == "NOT_EXECUTED", result
    assert c.calls == [] and c.writes == [] and not result["formal_research_started"]


def test_real_failed_capture_plan_representation_and_two_report_order():
    original = (Path(__file__).parent / "fixtures/declared-report-plan-original-20260922.json").read_bytes()
    assert len(original) == 835 and once.blob(original) == "d68c25df3aea64f935036edf2c4445aa80f3a1bb"
    assert once.sha(original) == "dd63282b70d791effc69e4509aab08b7049e0e9dfa44ea4e2e73ae0ff0e80316"
    plan = identity._json(original)
    canonical = once.raw(plan)
    assert original != canonical
    assert once.sha(canonical) == "b57a8c5de706a56c0d61aa4600122635446d84c5e8b0ea4a17fcb28af5ca40ff"
    reversed_plan = deepcopy(plan)
    reversed_plan["reports"].reverse()
    assert once.raw(reversed_plan) != canonical
    # This test is original-byte/representation evidence, not a live source run.
