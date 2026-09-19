"""Audit this one real external execution with existing installed models; no acquisition."""
from __future__ import annotations

import base64
import hashlib
import zlib
import json
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.research_funnel import PreResearchResult
from decision_kernel.runtime.external_research_execution import (
    ExternalResearchInputPacket, ExternalResearchCandidate,
    validate_external_research_candidate, main,
)
from decision_kernel.runtime.external_research_identity import ExecutionKey, read_bound_execution

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ROOT / "research_runs/candidates/MU/p0-4a-MU-20260909-sca-7c9e2b41"


def test_mu_sca_actual_input_and_execution(tmp_path, capsys):
    raw = (PREFIX / "input.json").read_bytes()
    packet = ExternalResearchInputPacket.model_validate_json(raw)
    assert packet.execution_id == "p0-4a-MU-20260909-sca-7c9e2b41"
    assert packet.code_commit == "29f98409dddd0032259e05a4bdad7ebad60b8a76"
    assert packet.security_id == "NASDAQ:MU"
    catalog = json.loads((ROOT / "research_runs/execution-inputs.json").read_text())
    assert packet.execution_id not in {r["execution_id"] for r in catalog["inputs"]}
    saved = (ROOT / "docs/live-decision-book.md").read_bytes()
    assert hashlib.sha256(saved).hexdigest() == packet.source_refs[0].sha256
    assert hashlib.sha1(b"blob " + str(len(saved)).encode() + b"\0" + saved).hexdigest() == packet.source_refs[0].git_blob
    with capsys.disabled():
        print("MU_INPUT_HASH=" + canonical_hash(packet), flush=True)
        print("MU_INPUT_FILE_SHA256=" + hashlib.sha256(raw).hexdigest(), flush=True)
    output = PREFIX / "execution-output.json"
    if not output.exists():
        with capsys.disabled():
            print("MU_STAGE=FROZEN_INPUT_ONLY_NOT_RESEARCH_COMPLETION", flush=True)
        return
    data = json.loads(output.read_text())
    # This file is explicitly unbound executor output. Only mechanical identity
    # fields are filled by the unchanged installed models; Research text is not edited.
    assert data["input_hash"] is None and data["receipt"]["input_hash"] is None
    data["input_hash"] = data["receipt"]["input_hash"] = canonical_hash(packet)
    if data.get("quick_research") is not None:
        assert data["quick_research"]["pre_research_hash"] is None
        pre = PreResearchResult.model_validate(data["pre_research"])
        data["quick_research"]["pre_research_hash"] = canonical_hash(pre)
    candidate = ExternalResearchCandidate.model_validate(data)
    validation = validate_external_research_candidate(packet=packet, candidate=candidate)
    key = ExecutionKey(packet.execution_id, canonical_hash(packet))
    assert read_bound_execution(raw, candidate.model_dump_json().encode(), key)[2] == validation
    if candidate.completion == "COMPLETE":
        inventory = json.loads((PREFIX / "source-assessment.json").read_text())
        required = json.loads((PREFIX / "preflight.json").read_text())["required_classes"]
        assert {r["id"] for r in inventory["classes"]} == {r["id"] for r in required}
        assert all(r["assessment_status"] == "ASSESSED" for r in inventory["classes"])
        assert inventory["missing_required_classes"] == []
        assert validation.status == "VALIDATED_FUNNEL_RESULT"
        assert validation.funnel_result is not None
    else:
        assert validation.status == "EXECUTION_GAP" and validation.funnel_result is None
    assert validation.investment_authority == validation.human_attention_authority == validation.signal_transition_authority == "NONE"
    normalized = canonical_json(candidate) + "\n"
    bound = tmp_path / "candidate.json"
    bound.write_text(normalized)
    report = tmp_path / "validation.json"
    assert main(["validate", "--input", str(PREFIX / "input.json"), "--candidate", str(bound), "--output", str(report)]) == 0
    if (PREFIX / "candidate.bound.json").exists():
        assert (PREFIX / "candidate.bound.json").read_bytes() == normalized.encode()
        assert json.loads((PREFIX / "validation.json").read_text()) == json.loads(report.read_text())
    with capsys.disabled():
        print("MU_PRE_HASH=" + (canonical_hash(candidate.pre_research) if candidate.pre_research else "NONE"), flush=True)
        print("MU_CANDIDATE_HASH=" + canonical_hash(candidate), flush=True)
        print("MU_BOUND_CANDIDATE_ZLIB_BASE64=" + base64.b64encode(zlib.compress(normalized.encode())).decode(), flush=True)
        print("MU_VALIDATION_ZLIB_BASE64=" + base64.b64encode(zlib.compress(report.read_bytes())).decode(), flush=True)
        print("MU_SOURCE_COMPLETENESS_LABEL_IS_NOT_DEMAND_SIDE_SEMANTIC_ACCEPTANCE", flush=True)
