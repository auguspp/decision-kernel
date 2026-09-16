"""#407 conditional Odds through the existing #406 retention path; synthetic only."""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
import socket
import subprocess
import sys
from uuid import uuid4

import pytest

from decision_kernel.calculation import CalculationStatus
from decision_kernel.conditional_odds import build_conditional_provisional_odds
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import odds_retention as odds, research_archive as archive
from decision_kernel.runtime import research_commit_only as retained
from test_conditional_odds import AS_OF, COMMIT_AT, context, world_set
from test_odds_retention import CoupledAPI
from test_research_archive import R, RECORD
from test_research_only_commit_v2 import v2_package


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("conditional retention cannot request network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)


def make_conditional_result(tmp_path, *, no_calculation=False):
    package = v2_package()
    source_research = tmp_path / "research-input.json"
    source_research.write_bytes(retained._raw(package))
    directory = tmp_path / "research"
    research = retained.commit_research_file(source_research, output=directory)
    snapshot = research.research_snapshot
    worlds = world_set(snapshot, horizon_days=1 if no_calculation else 1095)
    human = context(snapshot)
    created_at = COMMIT_AT + timedelta(hours=3)
    if no_calculation:
        price_timestamp = AS_OF + timedelta(days=2)
        supplied_at = price_timestamp + timedelta(hours=1)
        human = context(
            snapshot,
            price_timestamp=price_timestamp,
            supplied_at=supplied_at,
        )
        created_at = supplied_at + timedelta(hours=1)
    result = build_conditional_provisional_odds(
        research_snapshot=snapshot,
        conditional_worlds=worlds,
        price_context=human,
        artifact_id=uuid4(),
        created_at=created_at,
    )
    raw = (result.model_dump_json(indent=2) + "\n\n").encode()
    source = tmp_path / "conditional-odds.json"
    source.write_bytes(raw)
    return directory, canonical_hash(snapshot), research, result, source


def save(source, directory, digest, output):
    return odds.retain_odds_file(
        source,
        result_kind="CONDITIONAL_PROVISIONAL",
        research_directory=directory,
        expected_research_hash=digest,
        output=output,
    )


def read(output, directory, digest):
    return odds.read_retained_odds(
        output,
        research_directory=directory,
        expected_research_hash=digest,
    )


@pytest.mark.parametrize("no_calculation", [False, True])
def test_conditional_result_keeps_exact_bytes_authority_and_no_probability(tmp_path, no_calculation):
    directory, digest, _, result, source = make_conditional_result(
        tmp_path, no_calculation=no_calculation
    )
    output = tmp_path / "saved"
    assert save(source, directory, digest, output) == result
    assert (output / "result.json").read_bytes() == source.read_bytes()
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert read(output, directory, digest) == result
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before

    metadata = retained._json((output / "retention.json").read_bytes())
    assert metadata["result_kind"] == "CONDITIONAL_PROVISIONAL"
    assert metadata["research_snapshot_hash"] == digest
    assert metadata["market_qualification"] == "NOT_ESTABLISHED_BY_RETENTION"
    assert metadata["human_acceptance"] == "NOT_ESTABLISHED_BY_RETENTION"
    assert metadata["investment_authority"] == "NONE"
    assert result.artifact.cardinal_probability == "NOT_ESTABLISHED"
    assert result.artifact.probability_input == "ABSENT_BY_DESIGN"
    assert result.artifact.weighted_aggregate == "NOT_COMPUTED"
    assert result.artifact.canonical_odds == "NOT_ESTABLISHED"
    if no_calculation:
        assert result.artifact.calculation_status is CalculationStatus.NO_CALCULATION
        assert result.artifact.ordinal_status == "ORDINAL_NOT_ESTABLISHED"
        assert result.artifact.world_results == ()
        assert result.artifact.failures


def test_same_pinned_reading_recovers_conditional_result_and_exact_research(tmp_path):
    directory, digest, research, result, source = make_conditional_result(tmp_path)
    saved = tmp_path / "saved"
    save(source, directory, digest, saved)
    api = CoupledAPI(
        {p.name: p.read_bytes() for p in saved.iterdir()},
        {p.name: p.read_bytes() for p in directory.iterdir()},
        digest,
        str(research.research_snapshot.id),
        "CONDITIONAL_PROVISIONAL",
    )

    output = tmp_path / "recovered"
    receipt = archive.recover_archive(
        api, reading_commit=R, record_id=RECORD, output=output
    )
    assert receipt["qualification"] == "ODDS_RESULT_REVALIDATED_NOT_CURRENT_QUALIFICATION"
    assert receipt["result_kind"] == "CONDITIONAL_PROVISIONAL"
    assert receipt["result_hash"] == canonical_hash(result)
    assert receipt["research_record_id"] == "synthetic-research"
    assert receipt["research_snapshot_hash"] == digest
    assert receipt["odds_status"] == "SAVED_RESULT_REBUILT_FOR_VERIFICATION_NOT_NEW_PRICE_ANALYSIS"
    assert receipt["market_qualification"] == "NOT_ESTABLISHED_BY_RECOVERY"
    assert receipt["human_acceptance"] == "NOT_ESTABLISHED_BY_RECOVERY"
    assert receipt["investment_authority"] == "NONE"
    assert receipt["remote_write"] is False
    assert read(output / "bundle", output / "research" / "bundle", digest) == result
    assert len(api.calls) <= archive.MAX_API_CALLS
    assert all(call[2] == R for call in api.calls if call[0] == "file")


@pytest.mark.parametrize("damage", ["payoff", "probability", "wrong-kind"])
def test_conditional_tamper_or_wrong_kind_is_retained_as_failure_not_relabelled(tmp_path, damage):
    directory, digest, _, _, source = make_conditional_result(tmp_path)
    kind = "CONDITIONAL_PROVISIONAL"
    if damage == "wrong-kind":
        kind = "PROVISIONAL"
    else:
        data = json.loads(source.read_bytes())
        if damage == "payoff":
            data["artifact"]["world_results"][0]["total_payoff_per_share"] = "999"
        else:
            data["artifact"]["conditional_worlds"]["world_set"]["worlds"][0][
                "probability"
            ] = "0.5"
        data["artifact_hash"] = canonical_hash(data["artifact"])
        source.write_bytes(retained._raw(data))

    raw = source.read_bytes()
    output = tmp_path / "rejected"
    with pytest.raises(ValueError, match="preserve files"):
        odds.retain_odds_file(
            source,
            result_kind=kind,
            research_directory=directory,
            expected_research_hash=digest,
            output=output,
        )
    assert (output / "result.json").read_bytes() == raw
    assert not (output / "retention.json").exists()
    assert (output / "rejection.json").exists()
    with pytest.raises(ValueError):
        read(output, directory, digest)
    with pytest.raises(FileExistsError):
        save(source, directory, digest, output)


def test_conditional_cli_uses_same_offline_entry_and_kind(tmp_path):
    directory, digest, _, result, source = make_conditional_result(tmp_path)
    output = tmp_path / "saved"
    script = r'''
import sys, socket, builtins
sys.path.insert(0, sys.argv[1])
def denied(*a, **k): raise AssertionError("no network")
socket.create_connection = denied
socket.socket.connect = denied
original = builtins.__import__
def guarded(name, *a, **k):
    if name.split('.')[0] in {'openai', 'requests'} or name.startswith((
        'decision_kernel.live', 'decision_kernel.runtime.hithink_http')):
        raise AssertionError('unexpected provider/model import')
    return original(name, *a, **k)
builtins.__import__ = guarded
from decision_kernel.runtime.odds_retention import main
raise SystemExit(main(sys.argv[2:]))
'''
    args = [
        sys.executable,
        "-I",
        "-c",
        script,
        str(Path(__file__).resolve().parents[1] / "src"),
        "retain",
        "--research-directory",
        str(directory),
        "--expected-research-hash",
        digest,
        "--output",
        str(output),
        "--input",
        str(source),
        "--kind",
        "CONDITIONAL_PROVISIONAL",
    ]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=15)
    assert proc.returncode == 0, proc.stderr
    assert "INVESTMENT AUTHORITY: NONE" in proc.stdout
    assert read(output, directory, digest) == result
