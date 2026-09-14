"""Create-only technical continuation of the exact failed Stock source successor.

This module does not reopen source-successor-v1. It binds the canonical pre-Research
AttributeError from run 34797952444 and reuses the original saved-source capture,
full-input bridge, admission, Research and Funnel through the original host.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import current_state as reading
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_research_intake as intake
from . import stock_source_successor as base

REQUEST = "research_runs/stock-source-successor-continuation-request.json"
MODE = "HUMAN_AUTHORIZED_STOCK_SOURCE_SUCCESSOR_TECHNICAL_CONTINUATION"
CHILD = "source-successor-continuation-v1/"
TARGETS = base.TARGETS
SELECTION_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_SELECTION"
FAILURE_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_FAILURE"
REQUEST_PURPOSE = "TRUSTED_STOCK_SUCCESSOR_TECHNICAL_CONTINUATION_REQUEST"
EXPOSURE_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_CURRENT_READING"
PREDECESSOR_REQUEST_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_REQUEST"
PREDECESSOR_READING_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_READING"


def execution(thscode: str) -> tuple[str, str]:
    eid, prefix = intake.execution(thscode)
    once.require(thscode in TARGETS, "Stock successor continuation target outside approved scope")
    return eid + "-source-successor-continuation-v1", prefix + CHILD


@dataclass
class Session:
    request: dict
    binding: dict
    base_session: base.Session
    code: str
    reading_commit: str
    reading_raw: bytes
    origin: dict
    request_path: str = REQUEST
    mode: str = MODE

    @property
    def files(self):
        return self.base_session.files

    @property
    def batch(self):
        return self.base_session.batch

    def for_code(self, thscode):
        rows = [r for r in self.binding["items"] if r["thscode"] == thscode]
        once.require(len(rows) == 1, "Stock successor continuation binding target differs")
        return rows[0]


def _checked(api, spec):
    raw = identity._checked_source(spec, lambda s: api.file(s["path"], s["ref"]))
    meta = api.get("git/commits/" + spec["ref"])
    once.require(meta["sha"] == spec["ref"], "Stock successor continuation predecessor commit differs")
    return raw


def _reading_item(saved, code):
    rows = [r for r in saved["research"]["stock_business_work"]["items"] if r["thscode"] == code]
    once.require(len(rows) == 1, "Stock successor continuation target absent from reading")
    return rows[0]


def prepare(*, api, code, request, selected, origin, reading_commit, output, clock=once.now):
    """Bind the exact failed source-successor-v1 into a new create-only sibling."""
    from .stock_research_host import authorize, head
    authorize(api, code, request, request_path=REQUEST, mode=MODE)
    once.require(set(request) == {"schema_version", "enabled", "mode", "permission", "source_stock_run_id",
        "source_preparation_run_id", "failed_successor_run_id", "failed_successor_artifact",
        "failed_successor_reading_commit", "failed_successor_work_commit", "items"}
        and request["schema_version"] == 1 and request["enabled"] is True and request["mode"] == MODE
        and all(type(request[k]) is int and request[k] > 0 for k in
                ("source_stock_run_id", "source_preparation_run_id", "failed_successor_run_id")),
        "Stock successor continuation request envelope differs")
    once.require(origin["run"]["id"] == request["source_stock_run_id"],
                 "Stock successor continuation original Stock run differs")
    entries = request["items"]
    once.require(isinstance(entries, list) and len(entries) == 2
        and {e.get("thscode") for e in entries} == TARGETS, "Stock successor continuation targets differ")
    original = {i["thscode"]: i for i in selected["items"]}
    once.require(TARGETS <= set(original), "Stock successor continuation outside original qualified plan")
    work_head = head(api, intake.WORK_REF)
    once.require(work_head == request["failed_successor_work_commit"],
                 "Stock successor continuation predecessor work moved")
    rows = intake.inventory(api, work_head)

    failed_run = api.get("actions/runs/" + str(request["failed_successor_run_id"]))
    expected_artifact = request["failed_successor_artifact"]
    once.require(failed_run["path"] == ".github/workflows/stock-business-research.yml"
        and failed_run["event"] == "workflow_dispatch" and failed_run["run_attempt"] == 1
        and failed_run["head_branch"] == "main" and failed_run["head_sha"] == expected_artifact["head_sha"]
        and failed_run["status"] == "completed" and failed_run["conclusion"] == "failure",
        "Stock successor continuation failed run identity differs")
    jobs = api.get(f"actions/runs/{failed_run['id']}/jobs?per_page=100")
    once.require(jobs["total_count"] == len(jobs["jobs"])
        and {j["name"]: j.get("conclusion") for j in jobs["jobs"]} ==
            {"research-stock-business": "failure", "prepare-stock-sources": "skipped"},
        "Stock successor continuation failed jobs differ")
    artifacts = api.get(f"actions/runs/{failed_run['id']}/artifacts?per_page=100")
    matches = [a for a in artifacts["artifacts"] if a["id"] == expected_artifact["id"]]
    once.require(artifacts["total_count"] == len(artifacts["artifacts"]) and len(matches) == 1
        and all(matches[0].get(k) == expected_artifact[k] for k in ("id", "name", "size_in_bytes", "digest"))
        and not matches[0].get("expired", True) and matches[0]["workflow_run"]["head_sha"] == expected_artifact["head_sha"],
        "Stock successor continuation failed artifact identity differs")

    failed_reading_raw = api.file("current-state.json", request["failed_successor_reading_commit"])
    failed_reading = identity._json(failed_reading_raw); reading.validate_read_package(failed_reading)
    once.require(failed_reading["research"]["stock_business_work"]["work_commit"] == work_head
        and failed_reading["research"]["stock_business_work"]["latest_execution_attempt"]["id"] == request["failed_successor_run_id"],
        "Stock successor continuation failed reading differs")
    once.require(head(api, reading.READ_REF) == reading_commit, "Stock successor continuation fixed reading moved")
    reading_raw = api.file("current-state.json", reading_commit)
    current = identity._json(reading_raw); reading.validate_read_package(current)
    once.require(current["code_commit"] == code and current["research"]["stock_business_work"]["work_commit"] == work_head
        and current["research"]["stock_business_work"]["latest_execution_attempt"]["id"] == request["failed_successor_run_id"],
        "Stock successor continuation current reading does not show failed predecessor")

    request_ref = once.source_ref(REQUEST, code, api.file(REQUEST, code), REQUEST_PURPOSE)
    exposure = once.source_ref("current-state.json", reading_commit, reading_raw, EXPOSURE_PURPOSE)
    failed_exposure = once.source_ref("current-state.json", request["failed_successor_reading_commit"],
                                      failed_reading_raw, PREDECESSOR_READING_PURPOSE)
    binding_items, old_sessions = [], []
    for entry in entries:
        thscode = entry["thscode"]
        once.require(set(entry) == {"thscode", "predecessor_selection", "predecessor_failure"},
                     "Stock successor continuation item fields differ")
        old_eid, old_prefix = base.execution(thscode)
        new_eid, new_prefix = execution(thscode)
        selection_spec, failure_spec = entry["predecessor_selection"], entry["predecessor_failure"]
        once.require(selection_spec["path"] == old_prefix + "prepare.json"
            and failure_spec["path"] == old_prefix + "failure.json"
            and selection_spec["ref"] == failure_spec["ref"] == work_head
            and rows.get(selection_spec["path"], {}).get("sha") == selection_spec["git_blob"]
            and rows.get(failure_spec["path"], {}).get("sha") == failure_spec["git_blob"],
            "Stock successor continuation predecessor work identity differs")
        prep_raw, failure_raw = _checked(api, selection_spec), _checked(api, failure_spec)
        prep, failure = identity._json(prep_raw), identity._json(failure_raw)
        once.require(prep["execution_id"] == old_eid and prep["thscode"] == thscode
            and prep["question_kind"] == intake.QUESTION_KIND and prep["origin"] == origin
            and prep["observation"] == original[thscode]["observation"],
            "Stock successor continuation predecessor selection differs")
        once.require(failure.get("record_kind") == "PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT"
            and failure.get("execution_id") == old_eid and failure.get("thscode") == thscode
            and failure.get("phase") == "SOURCE_PREPARATION" and failure.get("error_type") == "AttributeError"
            and failure.get("formal_research_started") is False and failure.get("research_execution") == "NOT_EXECUTED"
            and failure.get("funnel_status") == "NOT_REACHED"
            and failure.get("status") == "SOURCE_OR_INPUT_PREPARATION_INCOMPLETE"
            and failure.get("automatic_retry") is False
            and all(failure.get(k) == v for k, v in reading.AUTHORITY.items()),
            "Stock successor continuation predecessor is not exact pre-Research AttributeError")
        old_names = {p[len(old_prefix):] for p in rows if p.startswith(old_prefix) and "/" not in p[len(old_prefix):]}
        once.require(not any(n in old_names for n in ("launch.json", "input.json", "candidate.json", "admission.json", "receipt.json", "funnel.json")),
                     "Stock successor continuation predecessor reached Research/admission")
        shown = _reading_item(current, thscode).get("source_successor")
        once.require(isinstance(shown, dict) and shown["status"] == "PRE_EXECUTION_FAILURE"
            and shown["execution_id"] == old_eid, "Stock successor continuation predecessor not preserved in reading")
        old_binding = prep["source_successor"]
        once.require(old_binding["execution_id"] == old_eid and old_binding["prefix"] == old_prefix
            and old_binding["permission"] == request["permission"], "Stock successor continuation old binding differs")
        old_request_raw = _checked(api, old_binding["successor_request"])
        old_request = identity._json(old_request_raw)
        once.require(old_request["mode"] == base.MODE and old_request["permission"] == request["permission"]
            and old_request["source_stock_run_id"] == request["source_stock_run_id"]
            and old_request["source_preparation_run_id"] == request["source_preparation_run_id"],
            "Stock successor continuation old request differs")
        old_sessions.append((old_binding, old_request, old_request_raw))
        binding_items.append({**old_binding, "execution_id": new_eid, "prefix": new_prefix,
            "predecessor_successor_selection": once.source_ref(selection_spec["path"], selection_spec["ref"], prep_raw, SELECTION_PURPOSE),
            "predecessor_successor_failure": once.source_ref(failure_spec["path"], failure_spec["ref"], failure_raw, FAILURE_PURPOSE),
            "predecessor_successor_request": once.source_ref(old_binding["successor_request"]["path"], old_binding["successor_request"]["ref"], old_request_raw, PREDECESSOR_REQUEST_PURPOSE),
            "predecessor_successor_reading": failed_exposure,
            "technical_predecessor_run_id": request["failed_successor_run_id"],
            "permission": request["permission"], "successor_request": request_ref, "current_reading": exposure})

    first_binding, first_request, _ = old_sessions[0]
    once.require(all(b["source_preparation"] == first_binding["source_preparation"] for b, _, _ in old_sessions)
        and all(r == first_request for _, r, _ in old_sessions), "Stock continuation predecessor material/request differs across issuers")
    source_preparation = first_binding["source_preparation"]
    prep_run = api.get("actions/runs/" + str(source_preparation["run_id"]))
    once.require(prep_run["path"] == ".github/workflows/stock-business-research.yml"
        and prep_run["event"] == "workflow_dispatch" and prep_run["run_attempt"] == 1
        and prep_run["head_branch"] == "main" and prep_run["status"] == "completed"
        and prep_run["conclusion"] == "failure", "Stock continuation source-only run differs")
    prep_jobs = api.get(f"actions/runs/{prep_run['id']}/jobs?per_page=100")
    once.require(prep_jobs["total_count"] == len(prep_jobs["jobs"])
        and {j["name"]: j.get("conclusion") for j in prep_jobs["jobs"]} ==
            {"research-stock-business": "skipped", "prepare-stock-sources": "failure"},
        "Stock continuation source-only jobs differ")
    artifacts = api.get(f"actions/runs/{prep_run['id']}/artifacts?per_page=100")
    source_matches = [a for a in artifacts["artifacts"] if a["id"] == source_preparation["artifact_id"]]
    once.require(artifacts["total_count"] == len(artifacts["artifacts"])
        and len(source_matches) == 1 and source_matches[0]["digest"] == source_preparation["artifact_digest"]
        and not source_matches[0].get("expired", True), "Stock continuation source-only artifact differs")
    archive = api.archive(source_matches[0])
    once.require(once.sha(archive) == source_preparation["archive_sha256"], "Stock continuation source archive changed")
    files = reading.unpack_archive(archive, source_matches[0], prep_run)
    once.require(once.sha(files["source-preparation-batch.json"]) == source_preparation["batch_sha256"],
                 "Stock continuation source batch changed")
    batch = identity._json(files["source-preparation-batch.json"])
    once.require(batch["status"] == "SOURCE_PREPARATION_INCOMPLETE"
        and batch["source_run_id"] == request["source_stock_run_id"]
        and batch["formal_research_started"] is False and batch["model_calls"] == 0
        and batch["research_work_writes"] == 0, "Stock continuation source batch semantics differ")
    for bound in binding_items: bound["source_preparation"] = source_preparation
    binding = {"kind": MODE, "permission": request["permission"], "request": request_ref,
        "current_reading": exposure, "predecessor_reading": failed_exposure,
        "failed_successor_run": reading.concise_run(failed_run), "failed_successor_artifact": expected_artifact,
        "source_preparation": source_preparation, "items": binding_items,
        "meaning": "CREATE_ONLY_TECHNICAL_CONTINUATION_OF_EXACT_PRE_RESEARCH_SUCCESSOR_FAILURE",
        **reading.AUTHORITY}
    (output / "source-successor-origin.zip").write_bytes(archive)
    (output / "source-successor-continuation-binding.json").write_bytes(once.raw(binding))
    base_session = base.Session(first_request, {"items": binding_items, "source_preparation": source_preparation,
        "request": first_binding["successor_request"], "current_reading": first_binding["current_reading"]},
        files, batch, code, reading_commit, reading_raw, origin)
    return [{**original[b["thscode"]], "execution_id": b["execution_id"], "prefix": b["prefix"]}
            for b in binding_items], Session(request, binding, base_session, code, reading_commit, reading_raw, origin)


def capture(*, session: Session, **kwargs):
    return base.capture(session=session.base_session, **kwargs)


def check_materials(session: Session, binding, context):
    surrogate = base.Session(session.base_session.request,
        {"items": [binding], "source_preparation": session.binding["source_preparation"]},
        session.files, session.batch, session.code, session.reading_commit, session.reading_raw, session.origin)
    base.check_materials(surrogate, binding, context)


def source_refs(binding):
    keys = ["parent_selection", "parent_failure", "recovery_selection", "recovery_failure",
            "predecessor_successor_selection", "predecessor_successor_failure",
            "predecessor_successor_request", "predecessor_successor_reading"]
    return [binding[k] for k in keys]


def recheck(*, api, code, session: Session, binding, context, clock=once.now):
    from .stock_research_host import authorize, head
    authorize(api, code, session.request, request_path=REQUEST, mode=MODE)
    once.require(head(api, reading.READ_REF) == session.reading_commit
        and api.file("current-state.json", session.reading_commit) == session.reading_raw,
        "Stock successor continuation fixed reading changed")
    work_head = head(api, intake.WORK_REF)
    rows = intake.inventory(api, work_head)
    for key in ("parent_selection", "parent_failure", "recovery_selection", "recovery_failure",
                "predecessor_successor_selection", "predecessor_successor_failure"):
        spec = binding[key]
        once.require(rows.get(spec["path"], {}).get("sha") == spec["git_blob"],
                     "Stock successor continuation predecessor changed in latest work")
        _checked(api, spec)
    predecessor_request_raw = _checked(api, binding["predecessor_successor_request"])
    predecessor_request = identity._json(predecessor_request_raw)
    once.require(predecessor_request["mode"] == base.MODE
        and predecessor_request["permission"] == session.request["permission"],
        "Stock successor continuation predecessor request changed")
    predecessor_reading_raw = identity._checked_source(binding["predecessor_successor_reading"],
        lambda s: api.file(s["path"], s["ref"]))
    predecessor_reading = identity._json(predecessor_reading_raw); reading.validate_read_package(predecessor_reading)
    once.require(predecessor_reading["research"]["stock_business_work"]["work_commit"] ==
        session.request["failed_successor_work_commit"], "Stock successor continuation predecessor reading changed")
    once.require(binding["permission"] == session.request["permission"]
        and binding["successor_request"] == session.binding["request"]
        and binding["current_reading"] == session.binding["current_reading"]
        and binding["source_preparation"] == session.binding["source_preparation"],
        "Stock successor continuation child binding changed")
    base.sources.recheck(context, api=api, code_commit=code, clock=clock)
    check_materials(session, binding, context)
