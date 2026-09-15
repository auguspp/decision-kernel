"""Versioned freeze eligibility; synthetic cases are not research acceptance."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import json
from pathlib import Path
import socket
from uuid import uuid4

import pytest
from pydantic import ValidationError

from decision_kernel.calculation import CalculationStatus, calculate_research_economics
from decision_kernel.deep_research import (
    ResearchMethodV1AcceptanceStatus, assess_research_method_v1_acceptance,
)
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.live import run_live_research_commit_package
from decision_kernel.odds import build_odds_research
from decision_kernel.policy import load_live_odds_v0_1
from decision_kernel.primitives import DomainValidationError
from decision_kernel.research import ResearchSnapshot, ResearchStatus
from decision_kernel.research_commit import (
    ResearchCommitPackage, commit_research_package,
    research_commit_information_bundle_hash, research_commit_package_hash,
)
from decision_kernel.runtime import research_commit_only as retained
from test_deep_research import _package as method_package, _rehash as method_rehash
from test_generic_research_commit import AS_OF, _fake_market, _generic_package


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("offline contract tests must not use network")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)


def rehash(package):
    snapshot = package.research_snapshot
    digest = research_commit_information_bundle_hash(
        research_snapshot=snapshot, evidence_artifacts=package.evidence_artifacts)
    return package.model_copy(update={"research_snapshot": snapshot.model_copy(
        update={"information_bundle_hash": digest})})


def v2_package(*, numerical=False):
    original = _generic_package()
    data = original.research_snapshot.model_dump(mode="python")
    data["schema_version"] = 2
    if not numerical:
        data.pop("valuation_horizon_date")
        data.update(scenarios=(), valuation_bases=(), market_expectations_narrative=None,
                    core_thesis="SYNTHETIC: conditional business thesis, not a price estimate.",
                    open_questions=("UNKNOWN: conversion of growth into owner cash",))
    snapshot = ResearchSnapshot.model_validate(data)
    return rehash(ResearchCommitPackage(
        research_snapshot=snapshot, evidence_artifacts=original.evidence_artifacts,
        proposed_committed_at=original.proposed_committed_at, schema_version=2))


def market():
    return _fake_market("8")(thscode="600000.SH", observed_at=AS_OF + timedelta(hours=3))


def test_research_only_commit_without_invented_final_fields():
    package = v2_package()
    before = canonical_json(package)
    result = commit_research_package(package)
    snapshot = result.research_snapshot
    assert snapshot.status is ResearchStatus.COMMITTED and snapshot.schema_version == 2
    assert snapshot.valuation_horizon_date is None and snapshot.scenarios == ()
    assert snapshot.valuation_bases == () and snapshot.market_expectations_narrative is None
    assert package.framing is None and snapshot.open_questions == package.research_snapshot.open_questions
    assert canonical_json(package) == before
    assert snapshot.information_bundle_hash == package.research_snapshot.information_bundle_hash


@pytest.mark.parametrize("field,value", [
    ("core_thesis", " "), ("model_risk_notes", None),
    ("thesis_invalidation", ()), ("information_bundle_hash", None),
    ("status", ResearchStatus.DRAFT),
])
def test_freeze_still_requires_research_accountability(field, value):
    package = v2_package()
    changed = package.model_copy(update={"research_snapshot": package.research_snapshot.model_copy(
        update={field: value})})
    if field != "information_bundle_hash":
        changed = rehash(changed)
    with pytest.raises(DomainValidationError):
        commit_research_package(changed)


@pytest.mark.parametrize("damage", ["missing", "duplicate", "extra", "future", "wrong-hash"])
def test_original_evidence_set_pit_and_information_checks_still_apply(damage):
    package = v2_package()
    evidence = package.evidence_artifacts
    if damage == "missing":
        evidence = evidence[1:]
    elif damage == "duplicate":
        evidence = (*evidence, evidence[0])
    elif damage == "extra":
        evidence = (*evidence, evidence[0].model_copy(update={"id": uuid4()}))
    elif damage == "future":
        evidence = (evidence[0].model_copy(update={
            "available_at": AS_OF + timedelta(seconds=1),
            "retrieved_at": AS_OF + timedelta(seconds=2)}), *evidence[1:])
    changed = rehash(package.model_copy(update={"evidence_artifacts": evidence}))
    if damage == "wrong-hash":
        changed = changed.model_copy(update={"research_snapshot": changed.research_snapshot.model_copy(
            update={"information_bundle_hash": "0" * 64})})
    with pytest.raises(DomainValidationError):
        commit_research_package(changed)


@pytest.mark.parametrize("damage", ["early-commit", "wrong-child", "wrong-version-lineage"])
def test_original_commit_chronology_and_child_lineage_remain(damage):
    package = v2_package()
    if damage == "early-commit":
        changed = package.model_copy(update={"proposed_committed_at": AS_OF - timedelta(seconds=1)})
    else:
        snapshot = package.research_snapshot
        updates = ({"evidence_links": (snapshot.evidence_links[0].model_copy(
            update={"research_snapshot_id": uuid4()}), *snapshot.evidence_links[1:])}
            if damage == "wrong-child" else {"version": 2, "supersedes_snapshot_id": None})
        changed = rehash(package.model_copy(update={"research_snapshot": snapshot.model_copy(update=updates)}))
    with pytest.raises((DomainValidationError, ValidationError)):
        commit_research_package(changed)


@pytest.mark.parametrize("target", ["snapshot", "package"])
def test_unknown_schema_rejected_even_after_unvalidated_model_copy(target):
    package = _generic_package()
    if target == "snapshot":
        package = rehash(package.model_copy(update={"research_snapshot": package.research_snapshot.model_copy(
            update={"schema_version": 99})}))
    else:
        package = package.model_copy(update={"schema_version": 99})
    with pytest.raises((DomainValidationError, ValidationError)):
        commit_research_package(package)


def test_v1_does_not_silently_adopt_v2_eligibility():
    legacy = _generic_package()
    with pytest.raises(ValidationError):
        ResearchCommitPackage.model_validate({**legacy.model_dump(mode="python"), "framing": None})
    with pytest.raises(ValidationError):
        ResearchSnapshot.model_validate({**legacy.research_snapshot.model_dump(mode="python"),
                                         "valuation_horizon_date": None})
    with pytest.raises((DomainValidationError, ValidationError)):
        commit_research_package(v2_package().model_copy(update={"schema_version": 1, "framing": legacy.framing}))


def test_v2_wrapper_can_remove_framing_without_rewriting_legacy_belief():
    legacy = _generic_package()
    wrapped = ResearchCommitPackage.model_validate({**legacy.model_dump(mode="python"),
                                                    "schema_version": 2, "framing": None})
    result = commit_research_package(wrapped)
    assert result.research_snapshot == commit_research_package(legacy).research_snapshot
    assert result.information_bundle_hash == legacy.research_snapshot.information_bundle_hash
    assert result.package_hash != research_commit_package_hash(legacy)


@pytest.mark.parametrize("damage", ["bad-sum", "no-horizon"])
def test_supplied_numerical_claims_are_not_ignored_to_obtain_research_commit(damage):
    package = v2_package(numerical=True)
    snapshot = package.research_snapshot
    updates = ({"scenarios": tuple(s.model_copy(update={"probability": Decimal("0")})
                                   for s in snapshot.scenarios)}
               if damage == "bad-sum" else {"valuation_horizon_date": None})
    changed = rehash(package.model_copy(update={"research_snapshot": snapshot.model_copy(update=updates)}))
    with pytest.raises((DomainValidationError, ValidationError)):
        commit_research_package(changed)


def test_research_commit_does_not_make_missing_numerical_inputs_zero_or_quiet():
    snapshot = commit_research_package(v2_package()).research_snapshot
    result = calculate_research_economics(snapshot, market(), created_at=AS_OF + timedelta(hours=3))
    assert result.status is CalculationStatus.NO_CALCULATION
    assert result.aggregate is None and result.scenario_results == ()
    assert {f.location for f in result.failures} >= {"valuation_horizon_date", "research_snapshot.scenarios"}
    with pytest.raises(DomainValidationError, match="calculation failed"):
        build_odds_research(artifact_id=uuid4(), created_at=AS_OF + timedelta(hours=3),
            research_snapshot=snapshot, observed_market=market(), policy=load_live_odds_v0_1())


@pytest.mark.parametrize("numerical,framing", [(False, False), (False, True), (True, False)])
def test_ineligible_live_consumer_stops_before_market_without_erasing_commit(numerical, framing):
    package = v2_package(numerical=numerical)
    if framing:
        package = package.model_copy(update={"framing": _generic_package().framing})
    result = commit_research_package(package)
    before = canonical_json(result)
    calls = []
    def fetch(**kwargs):
        calls.append(kwargs)
        raise AssertionError("not decision-ready; no market should be requested")
    with pytest.raises(DomainValidationError):
        run_live_research_commit_package(package=package, fetch_market=fetch,
                                        observed_at=AS_OF + timedelta(hours=3))
    assert calls == [] and canonical_json(result) == before


def test_explicit_numerical_successor_uses_original_engine_and_preserves_predecessor():
    prior = commit_research_package(v2_package()).research_snapshot
    before = canonical_json(prior)
    quantitative = v2_package(numerical=True)
    snapshot = quantitative.research_snapshot.model_copy(update={
        "version": prior.version + 1, "supersedes_snapshot_id": prior.id})
    quantitative = rehash(quantitative.model_copy(update={"research_snapshot": snapshot,
                                                     "framing": _generic_package().framing}))
    result = run_live_research_commit_package(package=quantitative, fetch_market=_fake_market("8"),
                                             observed_at=AS_OF + timedelta(hours=3))
    assert result.research_commit.research_snapshot.supersedes_snapshot_id == prior.id
    assert result.decision.odds.artifact.calculation.status is CalculationStatus.CALCULATED
    assert canonical_json(prior) == before and prior.scenarios == ()
    assert result.investment_authority == "NONE"
    # New declared numerical research state; not PRICE_ONLY, calibration or a model run.


def test_method_v1_cannot_silently_use_research_only_schema():
    original = method_package()
    changed = method_rehash(original, research_snapshot=original.research_snapshot.model_copy(
        update={"schema_version": 2}))
    assessment = assess_research_method_v1_acceptance(changed)
    assert assessment.status is ResearchMethodV1AcceptanceStatus.REJECTED
    assert "SNAPSHOT_SCHEMA_UNSUPPORTED" in {i.code for i in assessment.issues}


# Observed before this change with the same original core at c898cb2 (and dbf3abaa).
# These are wire/identity compatibility sentinels, not current company judgments.
@pytest.mark.parametrize("name,package_hash,result_hash", [
    ("600036-cmb", "51c8e85c09baea1963d752ffac111f63a03b7d3e942460df3c0384d652b714b3", "98e6e79d02e71134329e55c9f2413a4000040b540b14eadea9b2158b78ee91a2"),
    ("600519-moutai", "21b00e27d935f1c32abf8de1e0fa958fdf930ddfb961023128ebfc5f0e9d4af1", "6f3a97b8bcfe742c172d48b89ca968eb87655ee3a5c1d299b6ef50c99013175f"),
    ("300750-catl", "af9a784dc631afb2548984c510293789e0ddfc0aef7874f81ba89566496e5dff", "85c4e953837152197cc09c44ce5a89c5f7e4206667a5f000410dca3e336bc703"),
    ("601088-shenhua", "f445b0969493bca382a559ad0976ebc797f0d6171da9ee42729a09ab631e95cc", "9968e9087fdb8b04a4fad1dee98d3b9ae339435eaaebc319b6c149d85c332689"),
])
def test_original_v1_package_and_result_hashes_do_not_change(name, package_hash, result_hash):
    package = ResearchCommitPackage.model_validate_json(Path(f"dogfood/{name}.json").read_bytes())
    assert research_commit_package_hash(package) == package_hash
    assert canonical_hash(commit_research_package(package)) == result_hash


def test_original_offline_ingress_retains_v2_and_failure_of_later_consumer(tmp_path):
    package = v2_package()
    raw = (package.model_dump_json(indent=2) + "\n").encode()
    source = tmp_path / "package.json"
    source.write_bytes(raw)
    output = tmp_path / "saved"
    result = retained.commit_research_file(source, output=output)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert before["input.json"] == raw and "commit-rejection.json" not in before
    assert retained.RECEIPT_NAME not in before
    receipt = json.loads(before["commit.json"])
    assert receipt["human_acceptance"] == "NOT_ESTABLISHED_BY_THIS_OPERATION"
    assert receipt["odds_status"] == "NOT_COMPUTED"
    assert receipt["publication_status"] == "LOCAL_ONLY_NOT_GITHUB_PUBLICATION"
    with pytest.raises(DomainValidationError):
        result.research_snapshot.assert_decision_spine_ready()
    assert retained.read_retained_commit(output) == result
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    with pytest.raises(FileExistsError):
        retained.commit_research_file(source, output=output)


def test_ordinary_progress_remains_progress_not_automatic_commit(tmp_path):
    source = tmp_path / "partial.md"
    body = b"SYNTHETIC: cash bridge half done. PAUSED. No thesis or final fields yet.\n"
    source.write_bytes(body)
    output = tmp_path / "progress"
    digest = retained.save_research_progress(source, output=output, subject="SYNTHETIC", question_id="cash")
    metadata, actual = retained.read_research_progress(output, expected_sha256=digest)
    assert metadata["research_status"] == "RETAINED_PROGRESS_NOT_COMMITTED" and actual == body
    assert metadata["continuation_status"] == "NOT_EXECUTED"
    assert not (output / "research-commit.json").exists()


@pytest.mark.parametrize("field,value", [
    ("scenarios", ()), ("market_expectations_narrative", None),
    ("valuation_horizon_date", None),
])
def test_legacy_snapshot_commit_contract_is_not_relaxed(field, value):
    package = _generic_package()
    package = rehash(package.model_copy(update={"research_snapshot": package.research_snapshot.model_copy(
        update={field: value})}))
    with pytest.raises(DomainValidationError):
        commit_research_package(package)


@pytest.mark.parametrize("field,value", [
    ("schema_version", 3), ("investment_authority", "BUY"),
    ("human_acceptance", "ACCEPTED"),
])
def test_v2_does_not_ignore_unknown_versions_or_authority_fields(field, value):
    payload = v2_package().model_dump(mode="python")
    payload[field] = value
    with pytest.raises(ValidationError):
        ResearchCommitPackage.model_validate(payload)


def test_original_retainer_preserves_rejected_v2_inputs_without_committed_result(tmp_path):
    package = v2_package()
    package = package.model_copy(update={"research_snapshot": package.research_snapshot.model_copy(
        update={"core_thesis": ""})})
    raw = rehash(package).model_dump_json().encode()
    source = tmp_path / "invalid.json"
    source.write_bytes(raw)
    with pytest.raises(ValueError, match="input retained"):
        retained.commit_research_file(source, output=tmp_path / "failed")
    assert (tmp_path / "failed" / "input.json").read_bytes() == raw
    assert (tmp_path / "failed" / "commit-rejection.json").exists()
    assert not (tmp_path / "failed" / "research-commit.json").exists()


def test_v2_commit_and_verify_use_real_offline_entrypoint_without_live_imports(tmp_path):
    import os
    import subprocess
    import sys
    source = tmp_path / "v2.json"
    source.write_text(v2_package().model_dump_json(), encoding="utf-8")
    code = r'''
import importlib.abc, runpy, socket, sys
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.split('.')[0] in {'openai', 'requests', 'pypdf', 'pypdfium2'}
            or fullname in {'decision_kernel.live', 'decision_kernel.workflow',
                            'decision_kernel.runtime.hithink_http',
                            'decision_kernel.runtime.cninfo_http'}):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Deny())
def no(*a, **kw): raise AssertionError('network')
socket.create_connection = no
socket.socket.connect = no
sys.argv = ['research_commit_only', *sys.argv[1:]]
runpy.run_module('decision_kernel.runtime.research_commit_only', run_name='__main__')
'''
    env = dict(os.environ, PYTHONPATH=str(Path(retained.__file__).parents[2]))
    commands = [
        ['commit', str(source), '--output', str(tmp_path / 'saved')],
        ['verify', str(tmp_path / 'saved')],
    ]
    for args in commands:
        run = subprocess.run([sys.executable, '-c', code, *args], env=env,
                             capture_output=True, text=True, timeout=15)
        assert run.returncode == 0, run.stderr
        assert 'RESEARCH: COMMITTED' in run.stdout
        assert 'MARKET: NOT_REQUESTED; ODDS: NOT_COMPUTED' in run.stdout
    assert (tmp_path / 'saved' / 'input.json').read_bytes() == source.read_bytes()
