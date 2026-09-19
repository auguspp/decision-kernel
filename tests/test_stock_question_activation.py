"""Frozen real activation material: original gates/SDK preview, never a model send."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import socket

import pytest
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import reviewed_question_input as reviewed
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_research_sources as sources
from decision_kernel.runtime.external_research_admission import AdmissionRejected
from test_reviewed_question_real_corpus import replay_checks

ROOT = Path(__file__).parents[1]
MATERIAL = ROOT / "docs/readings/300711-question-execution-2026-09-19"
CODE = "5e4cd7edef6bc2301feb976a69a8ccd1b29c2226"
CHECKED_AT = "2026-09-19T16:07:00+00:00"
EGRESS = "f8b414988f9049ca5be2923cd5d0a778dedf271e3f019343f4b6d015895a9c1e"


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("activation replay must not access the network")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def prepared_inputs(checked_at=CHECKED_AT):
    old_case, old = replay_checks()  # Exact original R/origin/catalog; do not duplicate them.
    request = json.loads((MATERIAL / "request.json").read_bytes())
    meta = copy.deepcopy(old_case["commit_metadata"])
    dates = {"question_source": "2026-09-19T15:53:13Z",
             "context_source": "2026-09-19T15:59:09Z",
             "preflight_source": "2026-09-19T16:02:05Z"}
    bodies = {}
    for field, date in dates.items():
        spec = request[field]
        raw = (ROOT / spec["path"]).read_bytes()
        assert once.blob(raw) == spec["git_blob"] and once.sha(raw) == spec["sha256"]
        bodies[(spec["ref"], spec["path"])] = raw
        meta[spec["ref"]] = {"sha": spec["ref"], "committer": {"date": date}}

    class RecordedAPI:
        def file(self, path, ref):
            key = (ref, path)
            if key in bodies:
                return bodies[key]
            if key == (CODE, identity.CATALOG_PATH):
                return old["load"](old["catalog_source"])
            return old["load"]({"ref": ref, "path": path})

        def get(self, path):
            assert path.startswith("git/commits/")
            return copy.deepcopy(meta[path.removeprefix("git/commits/")])

        def _call(self, method, path):
            assert (method, path) == ("GET", "git/ref/heads/main")
            class Reply:
                def json(self):
                    return {"object": {"type": "commit", "sha": CODE}}
            return Reply()

    api = RecordedAPI()
    result = host._question_inputs(api=api, code=CODE, request=request, clock=lambda: checked_at)
    return request, api, result


def test_real_activation_material_passes_original_prepare_and_sdk_preview():
    request, api, (question, packet, discovery, context, checks) = prepared_inputs()
    receipt = reviewed.prepare(question_source=request["question_source"],
                               checked_at=CHECKED_AT, **checks)
    sources.recheck(context, api=api, code_commit=CODE, clock=lambda: CHECKED_AT)
    assert receipt["status"] == "QUESTION_INPUT_PREPARED_NOT_EXECUTED"
    assert not receipt["research_execution_allowed"] and not receipt["funnel_invoked"]
    assert question["revision"] == 2 and question["predecessor"] is not None
    assert host.question_egress_hash(packet, discovery, context) == request["approved_egress_hash"] == EGRESS
    assert len(context["issuer_documents"]) == 3
    assert sum(d["page_count"] for d in context["issuer_documents"]) == 17
    permission = request["permission"]
    assert permission["comment_id"] == 5743341330
    assert permission["created_at"] == "2026-09-19T16:06:49Z"
    assert once.sha((MATERIAL / "permission.md").read_bytes()) == permission["body_sha256"]
    body, schema, output_format, parameters = once.model_request(
        once.pre_prompt(packet, discovery, context), once.PreResearchResult,
        max_prompt_bytes=host.STOCK_PROMPT_BYTES)
    assert parameters["model"] == once.MODEL and parameters["max_output_tokens"] == 6000
    assert len(once.SYSTEM.encode()) + len(body.encode()) + len(once.raw(output_format)) <= host.STOCK_PROMPT_BYTES
    assert json.loads(body)["evidence_ids"] == [str(packet.seed_evidence_artifacts[0].id)]
    directory = os.environ.get("CI_REPORT_DIR")
    if directory:
        out = Path(directory) / "stock-question-activation"
        out.mkdir(exist_ok=False)
        (out / "preview.json").write_bytes(once.raw({
            "meaning": "FIXED_RECORDED_INPUT_REPLAY_NOT_LIVE_ADMISSION_OR_RESEARCH",
            "original_checked_at": CHECKED_AT, "permission_comment": permission["comment_id"],
            "question_id": question["question_id"], "execution_id": packet.execution_id,
            "approved_egress_hash": EGRESS, "receipt": receipt,
            "context_bytes": len(once.raw(context)), "prompt_bytes": len(body.encode()),
            "output_format_sha256": once.sha(once.raw(output_format)),
            "network_calls": 0, "model_calls": 0, "launch_writes": 0,
        }))


def test_real_activation_preflight_expiry_still_blocks_preparation():
    with pytest.raises(AdmissionRejected) as caught:
        prepared_inputs("2026-09-20T10:30:01+00:00")
    assert caught.value.code == "SOURCE_PREFLIGHT_STALE_OR_INVALID"
