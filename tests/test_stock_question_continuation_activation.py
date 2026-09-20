"""Frozen Guangha continuation activation preview; no network or model send."""
from __future__ import annotations

import json
import os
from pathlib import Path

from decision_kernel.runtime import external_research_admission as admission
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_question_continuation as cont
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket
from test_stock_question_activation import prepared_inputs

ROOT = Path(__file__).parents[1]
MATERIAL = ROOT / "docs/readings/300711-question-continuation-2026-09-20"

PREFLIGHT_SOURCE = {
    "repository": once.REPO,
    "ref": "b4ccf7d326a512a8b4f9f07da9dc11996fe10f90",
    "path": "docs/readings/300711-question-continuation-2026-09-20/source-preflight.json",
    "git_blob": "c0b51d01e629cc16436405604fb13b25bc1469df",
    "sha256": "fa6e6054bcf1cb75a08400f41324a56bd6d5f42ca48592e59d757e096435126a",
    "purpose": admission.PREFLIGHT_PURPOSE,
}

PARENT_WORK = "135d705898f1f32aff4beab85742362d7c1cbad5"
PARENT_ROOT = (
    "research_runs/candidates/stock-questions/"
    "fd57f37c13cddeecfd66307f9dade8053c6b1f88b14bafe822583e651e6a87ec/"
)
PRED = {
    "host_receipt": ("host-receipt.json", "a49280db99f5a5ab4c47c085af5ac07fb71c4505",
                     "0c815b472db2d7b0780d17b6454fe3644e5b302bd9dc3c1f3656952c237f723d"),
    "candidate": ("candidate.json", "49f0b297006a97003f69b4f522d55e8e6cc8775c",
                  "c6186f10fd5f958d3bb8533108c88c837cc9b9cfd5fdf5e98d4a1d4f6247fc77"),
    "receipt": ("receipt.json", "902302515e469a0c4d5451100974c9e197850b9d",
                "f297bcf71035be8e8e6f01fa009dad000d9e1bcf41f5ac72d16c2e1f732d5e89"),
    "validation": ("validation.json", "f9c8e26f87bee13763598d86778b6edd10791c01",
                   "5ba0b4928ffccd08270a14502454096974e91976e5118f825d4bf275d1cf9877"),
    "launch": ("launch.json", "c97872eb173e028aed531e77241bfab5bc1ac959",
               "99f00a761c0923f1d4492062f5f303307bf2d3ac7ea1d6bb540bdd83bb049e50"),
    "input": ("input.json", "0ebfafc5b20fb65edf364d6e61d7a92f1a550c08",
              "42cec7ce48b2d7d88727c2da487e774edf02c73ac01f0c4570480eaaa5216851"),
    "admission": ("admission.json", "52b48b4869c74ab12e57859732b6d0370e66a486",
                  "01e7a250daa75fd9f1cd0b4eaecf27d5d16d6d7a4d1f91adfa7f3db90caf9f74"),
}


def predecessor_sources():
    result = {}
    for key, (name, blob, sha256) in PRED.items():
        filename, purpose = cont.PREDECESSOR_FILES[key]
        assert filename == name
        result[key] = {
            "repository": once.REPO,
            "ref": PARENT_WORK,
            "path": PARENT_ROOT + name,
            "git_blob": blob,
            "sha256": sha256,
            "purpose": purpose,
        }
    return result


def continuation_preview():
    request, _, (q, packet, discovery, context, _) = prepared_inputs()
    preflight_raw = (MATERIAL / "source-preflight.json").read_bytes()
    assert once.blob(preflight_raw) == PREFLIGHT_SOURCE["git_blob"]
    assert once.sha(preflight_raw) == PREFLIGHT_SOURCE["sha256"]
    preflight = json.loads(preflight_raw)
    assert preflight["notes"].startswith("RETAINED_ARTIFACT_RECHECK / STATIC")
    assert all(row["mode"] == "STATIC" for row in preflight["required_classes"])

    refs = []
    for spec in packet.source_refs:
        value = spec.model_dump(mode="json")
        if value["purpose"] == admission.PREFLIGHT_PURPOSE:
            value = PREFLIGHT_SOURCE
        if value not in refs:
            refs.append(value)
    pred = predecessor_sources()
    for key in cont.PREDECESSOR_FILES:
        if pred[key] not in refs:
            refs.append(pred[key])

    child_id, child_prefix = cont.execution(q["security_id"], q["question_id"])
    data = packet.model_dump(mode="json")
    data.update(
        execution_id=child_id,
        candidate_output_prefix=child_prefix,
        source_refs=refs,
        known_unknowns=list(dict.fromkeys([
            *packet.known_unknowns,
            "TECHNICAL_CONTINUATION_OF:" + packet.execution_id,
            "PREDECESSOR_RESULT:EXECUTION_GAP_PERMISSION_DENIED_NO_PRE_OUTPUT",
            "PROVIDER_CONTINUATION:DEEPSEEK_OFFICIAL_DEEPSEEK_FLASH",
        ])),
        prompt_version="reviewed-question-technical-continuation-v1",
    )
    continued = ExternalResearchInputPacket.model_validate(data)
    continued_discovery = discovery.model_copy(update={
        "discovery_id": child_id,
        "as_of": continued.research_cutoff,
    })
    digest = cont.egress_hash(continued, continued_discovery, context)
    return q, continued, continued_discovery, context, digest, pred


def test_real_guangha_material_builds_deepseek_continuation_egress_preview():
    q, packet, discovery, context, digest, pred = continuation_preview()
    assert q["case_id"] == "300711.SZ"
    assert q["question_id"] == "restricted-proceeds-internal-transfer-2026h1"
    assert packet.execution_id.endswith("-technical-continuation-v1")
    assert packet.candidate_output_prefix == PARENT_ROOT + cont.CHILD
    assert packet.seed_evidence_artifacts[0].id.hex == "631ae8e182e856bfa26bc4dce9c38148"
    assert PREFLIGHT_SOURCE in [s.model_dump(mode="json") for s in packet.source_refs]
    refs = [s.model_dump(mode="json") for s in packet.source_refs]
    assert all(pred[key] in refs for key in cont.PREDECESSOR_FILES)
    assert len(digest) == 64
    prompt = once.pre_prompt(packet, discovery, context)
    _, _, wire, params = cont._deepseek_request(prompt, once.PreResearchResult)
    assert set(wire) == {"type", "name", "schema"}
    assert params["model"] == "deepseek-flash"
    assert params["reasoning"] == {"effort": "none"}
    assert params["tools"] == [] and params["store"] is False

    directory = os.environ.get("CI_REPORT_DIR")
    if directory:
        out = Path(directory) / "stock-question-continuation-activation"
        out.mkdir(exist_ok=False)
        (out / "preview.json").write_bytes(once.raw({
            "meaning": "FIXED_RECORDED_MATERIAL_PREVIEW_NOT_EXECUTION_PERMISSION",
            "case_id": q["case_id"],
            "question_id": q["question_id"],
            "revision": q["revision"],
            "execution_id": packet.execution_id,
            "candidate_output_prefix": packet.candidate_output_prefix,
            "preflight_source": PREFLIGHT_SOURCE,
            "preflight_valid_until": json.loads(
                (MATERIAL / "source-preflight.json").read_bytes())["valid_until"],
            "predecessor_work_commit": PARENT_WORK,
            "predecessor_sources": pred,
            "provider": cont.PROVIDER,
            "base_url": once.DEEPSEEK_BASE_URL,
            "model": once.DEEPSEEK_MODEL,
            "reasoning": cont.REASONING,
            "approved_egress_hash": digest,
            "context_sha256": request["context_source"]["sha256"],
            "network_calls": 0,
            "model_calls": 0,
            "remote_writes": 0,
        }))
