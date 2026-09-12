"""Synthetic exposure chronology regression, never an actual Human permission."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import disclosure_continuation as continuation
from decision_kernel.runtime import incremental_disclosure as work
from decision_kernel.runtime import saved_research_once as once
from test_incremental_disclosure import external_pair, packet

CODE, OLD, READING = "a" * 40, "b" * 40, "c" * 40
CHECKED = "2026-09-10T10:00:00Z"
RECORDED = "2026-09-10T09:00:00Z"


def binding(exposure_committed_at):
    """Reuse original packet, candidate and reading models with in-memory I/O."""
    old = packet(code="600036", version="a")
    child = packet(code="600036", version="b")
    key = work._packet(old).assessment_input_hash
    prefix = work.request_path(key).removesuffix("packet.json")
    old_input, old_result = external_pair(old, complete=True)
    files = {(prefix + "packet.json", OLD): old,
             (prefix + "input.json", OLD): old_input,
             (prefix + "candidate.json", OLD): old_result}
    prior = {name: once.source_ref(prefix + filename, OLD, value, "SYNTHETIC_PREDECESSOR")
             for name, filename, value in (("packet", "packet.json", old),
                 ("input", "input.json", old_input), ("result", "candidate.json", old_result))}
    prior["kind"] = "CANDIDATE"
    exposure = read.assemble(code_commit=CODE, checked_at="2026-09-10T08:00:00Z",
        check_started_at="2026-09-10T08:00:00Z", lanes={},
        research={"handoffs": {"active": []}, "candidate_work": {"status": "READ_OK",
                  "items": [{"sources": {"candidate": prior["result"]}}]}},
        capabilities=[], refresh_identity={})
    exposure_raw = read.json_bytes(exposure)
    files[("current-state.json", READING)] = exposure_raw
    body = "SYNTHETIC explicit continuation, not a real Human response"
    comment = {"id": 101, "issue_url": f"https://api.github.com/repos/{read.REPOSITORY}/issues/297",
               "body": body, "created_at": RECORDED, "updated_at": RECORDED}
    request = {"schema_version": 1, "mode": continuation.MODE, "enabled": True,
        "permission": {"issue_number": 297, "comment_id": 101, "record_body": body,
                       "body_sha256": read.sha256(body.encode()), "verbatim": body,
                       "response_kind": "EXPLICIT_RESEARCH_CONTINUE", "ticker": "600036"},
        "predecessor": prior,
        "exposed_reading": once.source_ref("current-state.json", READING, exposure_raw, "EXPOSURE"),
        "new_assessment_input_hash": work._packet(child).assessment_input_hash,
        "prior_question": read.json.loads(old_input)["research_question"],
        "follow_up_question": "Synthetic follow-up of that same problem",
        "new_evidence_reason": "Synthetic different primary body"}
    request_raw = once.raw(request)
    files[(continuation.REQUEST_PATH, CODE)] = request_raw
    commit_times = {CODE: "2026-09-10T09:30:00Z", OLD: "2026-09-09T16:00:00Z",
                    READING: exposure_committed_at}
    class API:
        def __init__(self):
            self.reads = []
        def file(self, path, ref):
            self.reads.append((path, ref))
            return files[(path, ref)]
        def get(self, path):
            assert path.startswith("git/commits/")
            ref = path.rsplit("/", 1)[-1]
            return {"sha": ref, "committer": {"date": commit_times[ref]}}
        def _call(self, method, path):
            assert method == "GET" and path == "issues/comments/101"
            return SimpleNamespace(json=lambda: deepcopy(comment))
    return dict(api=API(), code_commit=CODE,
        request_source=once.source_ref(continuation.REQUEST_PATH, CODE, request_raw, continuation.REQUEST_PURPOSE),
        new_packet_raw=child, checked_at=CHECKED)


@pytest.mark.parametrize("committed_at", ["2026-09-10T09:00:01Z", "2026-09-10T09:30:00Z"])
def test_old_check_clock_cannot_hide_exposure_created_after_response(committed_at):
    # checks.finished_at predates the response, but the exact Git version does not.
    with pytest.raises(ValueError, match="permission precedes its exposed reading"):
        continuation.check(**binding(committed_at))


@pytest.mark.parametrize("committed_at", ["2026-09-10T08:01:00Z", "2026-09-10T09:00:00Z",
                                          "2026-09-10T17:00:00+08:00"])
def test_existing_version_remains_eligible_at_equivalent_instants(committed_at):
    result = continuation.check(**binding(committed_at))
    assert result["permission_receipt"]["recorded_at"] == RECORDED
    assert result["question"] == "Synthetic follow-up of that same problem"
