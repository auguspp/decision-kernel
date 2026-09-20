"""Frozen real 300711 DeepSeek continuation activation material; no model send."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import socket

import pytest

from decision_kernel.runtime import reviewed_question_input as reviewed
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_continuation as cont
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import stock_research_sources as sources
from test_stock_question_activation import prepared_inputs, CODE

ROOT = Path(__file__).parents[1]
MATERIAL = ROOT / "docs/readings/300711-question-continuation-2026-09-20"
PREFLIGHT_PATH = "docs/readings/300711-question-continuation-2026-09-20/source-preflight.json"
PREFLIGHT_REF = "0a1c520527db7901a579e0f585bff6a5cf34d3a8"
PREFLIGHT_BLOB = "8e492303179ef9cb6f3c9fd6a9673805bcba5a26"
PREFLIGHT_SHA256 = "51c92c45a5b571374bbb3be349d3d6d1f1c28b62d1431609e23547c035926758"
CHECKED_AT = "2026-09-20T02:30:00+00:00"
BUNDLE = ROOT / "tests/fixtures/300711_question_continuation_predecessor.json"


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("continuation activation replay must not access networking")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def real_inputs():
    _, api, _ = prepared_inputs(CHECKED_AT)
    base_request = json.loads((ROOT / "research_runs/stock-question-request.json").read_bytes())
    bundle = json.loads(BUNDLE.read_bytes())
    preflight_raw = (ROOT / PREFLIGHT_PATH).read_bytes()
    assert once.blob(preflight_raw) == PREFLIGHT_BLOB
    assert once.sha(preflight_raw) == PREFLIGHT_SHA256

    original_file = api.file
    original_get = api.get
    original_call = api._call
    predecessor = bundle["predecessor"]

    def file(path, ref):
        if (ref, path) == (PREFLIGHT_REF, PREFLIGHT_PATH):
            return preflight_raw
        for key, spec in predecessor["sources"].items():
            if (ref, path) == (spec["ref"], spec["path"]):
                return bundle["bodies"][key].encode()
        return original_file(path, ref)

    def get(path):
        if path == "git/commits/" + PREFLIGHT_REF:
            return {"sha": PREFLIGHT_REF, "committer": {"date": "2026-09-20T02:25:00Z"}}
        if path == "git/trees/" + predecessor["work_commit"] + "?recursive=1":
            return {"truncated": False, "tree": [
                {"type": "blob", "path": spec["path"], "sha": spec["git_blob"]}
                for spec in predecessor["sources"].values()
            ]}
        if path == "actions/runs/35476493146":
            return {
                "id": 35476493146,
                "path": ".github/workflows/stock-business-research.yml",
                "event": "workflow_dispatch",
                "run_attempt": 1,
                "head_branch": "main",
                "head_sha": predecessor["artifact"]["head_sha"],
                "status": "completed",
                "conclusion": "failure",
            }
        if path == "actions/runs/35476493146/jobs?per_page=100":
            jobs = [
                {"name": "research-stock-business", "conclusion": "failure"},
                {"name": "prepare-stock-sources", "conclusion": "skipped"},
            ]
            return {"total_count": 2, "jobs": jobs}
        if path == "actions/runs/35476493146/artifacts?per_page=100":
            artifact = {**predecessor["artifact"], "expired": False,
                        "workflow_run": {"head_sha": predecessor["artifact"]["head_sha"]}}
            return {"total_count": 1, "artifacts": [artifact]}
        return original_get(path)

    def call(method, path):
        if (method, path) == ("GET", "git/ref/heads/" + intake.WORK_REF):
            class Reply:
                def json(self):
                    return {"object": {"type": "commit", "sha": predecessor["work_commit"]}}
            return Reply()
        return original_call(method, path)

    api.file = file
    api.get = get
    api._call = call
    assert request["enabled"] is True and request["mode"] == cont.MODE
    assert request["predecessor"] == predecessor
    assert request["preflight_source"] == {
        "repository": once.REPO,
        "ref": PREFLIGHT_REF,
        "path": PREFLIGHT_PATH,
        "purpose": "PRE_EXECUTION_SOURCE_PREFLIGHT",
        "git_blob": PREFLIGHT_BLOB,
        "sha256": PREFLIGHT_SHA256,
    }
    q, packet, discovery, context, checks, pred = cont._inputs(
        api=api, code=CODE, request=request, clock=lambda: CHECKED_AT)
    return request, api, q, packet, discovery, context, checks, pred


def test_real_continuation_material_prepares_and_computes_deepseek_egress():
    request, api, q, packet, discovery, context, checks, pred = real_inputs()
    receipt = reviewed.prepare(
        question_source=request["question_source"], checked_at=CHECKED_AT, **checks)
    sources.recheck(context, api=api, code_commit=CODE, clock=lambda: CHECKED_AT)
    digest = cont.egress_hash(packet, discovery, context)
    assert receipt["status"] == "QUESTION_INPUT_PREPARED_NOT_EXECUTED"
    assert q["question_id"] == "restricted-proceeds-internal-transfer-2026h1"
    assert packet.execution_id == pred["child_execution_id"]
    assert packet.candidate_output_prefix.endswith("/technical-continuation-v1/")
    assert digest and len(digest) == 64
    prompt = once.pre_prompt(packet, discovery, context)
    _, _, fmt, params = cont._deepseek_request(prompt, once.PreResearchResult)
    assert set(fmt) == {"type", "name", "schema"}
    assert params["model"] == "deepseek-flash"
    assert params["reasoning"] == {"effort": "none"}
    directory = os.environ.get("CI_REPORT_DIR")
    if directory:
        out = Path(directory) / "stock-question-continuation-activation"
        out.mkdir(exist_ok=False)
        (out / "preview.json").write_bytes(once.raw({
            "meaning": "FIXED_RECORDED_CONTINUATION_INPUT_REPLAY_NOT_LIVE_RESEARCH",
            "checked_at": CHECKED_AT,
            "question_id": q["question_id"],
            "parent_execution_id": pred["parent_execution_id"],
            "child_execution_id": pred["child_execution_id"],
            "preflight_ref": PREFLIGHT_REF,
            "approved_egress_hash_candidate": digest,
            "provider": cont.PROVIDER,
            "model": once.DEEPSEEK_MODEL,
            "network_calls": 0,
            "model_calls": 0,
            "launch_writes": 0,
        }))


def test_real_continuation_preflight_expiry_is_finite():
    request, api, q, packet, discovery, context, checks, pred = real_inputs()
    with pytest.raises(Exception) as caught:
        reviewed.prepare(
            question_source=request["question_source"],
            checked_at="2026-09-20T10:30:01+00:00", **checks)
    assert getattr(caught.value, "code", None) == "SOURCE_PREFLIGHT_STALE_OR_INVALID"
