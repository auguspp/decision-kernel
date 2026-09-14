"""One create-only Stock source successor over the saved source-only artifact.

Reuse the original Stock selection, source-preparation binding, Retainer, admission,
Research/Funnel and full-input bridge. This module does not create permission,
a second Research loop, a retry of source-recovery-v1, or Investment Authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path

from ..adapters.cninfo import SHANGHAI_TZ
from ..adapters.pdf_text import extract_pdf_text
from . import cninfo_http as cninfo
from . import current_state as reading
from . import disclosure_source_reading as page_reading
from . import external_research_identity as identity
from . import saved_research_once as once
from . import stock_research_intake as intake
from . import stock_research_sources as sources
from . import stock_source_preparation as preparation
from . import stock_source_recovery as recovery

REQUEST = "research_runs/stock-source-successor-request.json"
MODE = "HUMAN_AUTHORIZED_STOCK_SOURCE_SUCCESSOR"
CHILD = "source-successor-v1/"
CONTINUATION_REQUEST = "research_runs/stock-source-successor-continuation-request.json"
CONTINUATION_MODE = "HUMAN_AUTHORIZED_STOCK_SOURCE_SUCCESSOR_TECHNICAL_CONTINUATION"
CONTINUATION_CHILD = "source-successor-continuation-v1/"
TARGETS = frozenset({"603353.SH", "300711.SZ"})
PARENT_SELECTION_PURPOSE = "STOCK_SUCCESSOR_PARENT_SELECTION"
PARENT_FAILURE_PURPOSE = "STOCK_SUCCESSOR_PARENT_FAILURE"
RECOVERY_SELECTION_PURPOSE = "STOCK_SUCCESSOR_RECOVERY_SELECTION"
RECOVERY_FAILURE_PURPOSE = "STOCK_SUCCESSOR_RECOVERY_FAILURE"
REQUEST_PURPOSE = "TRUSTED_STOCK_SOURCE_SUCCESSOR_REQUEST"
EXPOSURE_PURPOSE = "STOCK_SUCCESSOR_CURRENT_READING"
CONTINUATION_SELECTION_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_SELECTION"
CONTINUATION_FAILURE_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_FAILURE"
CONTINUATION_REQUEST_PURPOSE = "TRUSTED_STOCK_SUCCESSOR_TECHNICAL_CONTINUATION_REQUEST"
CONTINUATION_EXPOSURE_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_CURRENT_READING"
CONTINUATION_PREDECESSOR_REQUEST_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_REQUEST"
CONTINUATION_PREDECESSOR_READING_PURPOSE = "STOCK_SUCCESSOR_CONTINUATION_PREDECESSOR_READING"
MATERIAL_LIMITATION = ("Exact source-only artifact is the saved source body base. A fresh coherent CNINFO inventory "
    "is checked at successor time; already-saved PDFs are reused byte-for-byte and only newly selected PDFs, if any, "
    "are acquired. Same-PDF visual notes are explicitly rebound only after the current main note has the exact "
    "approved blob and render/engine binding. No clipping, summary substitution or source-truth certification.")


def execution(thscode: str) -> tuple[str, str]:
    eid, prefix = intake.execution(thscode)
    once.require(thscode in TARGETS, "Stock successor target outside approved scope")
    return eid + "-source-successor-v1", prefix + CHILD


def continuation_execution(thscode: str) -> tuple[str, str]:
    eid, prefix = intake.execution(thscode)
    once.require(thscode in TARGETS, "Stock successor continuation target outside approved scope")
    return eid + "-source-successor-continuation-v1", prefix + CONTINUATION_CHILD


def _spec_equal(actual, expected):
    return all(actual.get(k) == expected.get(k) for k in
               ("repository", "ref", "path", "git_blob", "sha256"))


def _checked_git(api, spec):
    raw = identity._checked_source(spec, lambda s: api.file(s["path"], s["ref"]))
    meta = api.get("git/commits/" + spec["ref"])
    once.require(meta["sha"] == spec["ref"], "Stock successor predecessor commit differs")
    return raw


def _current_work_ref(api, path, blob):
    from .stock_research_host import head
    rows = intake.inventory(api, head(api, intake.WORK_REF))
    once.require(rows.get(path, {}).get("sha") == blob, "Stock successor predecessor changed in latest work")


def _reading_item(saved, code):
    rows = [r for r in saved["research"]["stock_business_work"]["items"] if r["thscode"] == code]
    once.require(len(rows) == 1, "Stock successor target absent from current reading")
    return rows[0]


@dataclass
class Session:
    request: dict
    binding: dict
    files: dict[str, bytes]
    batch: dict
    code: str
    reading_commit: str
    reading_raw: bytes
    origin: dict
    request_path: str = REQUEST
    mode: str = MODE

    def for_code(self, thscode):
        rows = [r for r in self.binding["items"] if r["thscode"] == thscode]
        once.require(len(rows) == 1, "Stock successor binding target differs")
        return rows[0]


def _source_only_material(*, api, source_preparation, source_stock_run_id, material_by_code):
    run_id = source_preparation["run_id"]
    prep_run = api.get("actions/runs/" + str(run_id))
    once.require(prep_run["path"] == ".github/workflows/stock-business-research.yml"
        and prep_run["event"] == "workflow_dispatch" and prep_run["run_attempt"] == 1
        and prep_run["head_branch"] == "main" and prep_run["status"] == "completed"
        and prep_run["conclusion"] == "failure", "Stock successor source-only run identity differs")
    jobs = api.get(f"actions/runs/{prep_run['id']}/jobs?per_page=100")
    once.require(jobs["total_count"] == len(jobs["jobs"])
        and {j["name"]: j.get("conclusion") for j in jobs["jobs"]} ==
            {"research-stock-business": "skipped", "prepare-stock-sources": "failure"},
        "Stock successor source-only jobs differ")
    artifacts = api.get(f"actions/runs/{prep_run['id']}/artifacts?per_page=100")
    once.require(artifacts["total_count"] == len(artifacts["artifacts"]), "Stock successor artifact enumeration incomplete")
    matches = [a for a in artifacts["artifacts"] if a["id"] == source_preparation["artifact_id"]]
    once.require(len(matches) == 1, "Stock successor source-only artifact missing")
    artifact = matches[0]
    once.require(artifact["name"] == source_preparation["artifact_name"]
        and artifact["digest"] == source_preparation["artifact_digest"]
        and not artifact.get("expired", True) and artifact["workflow_run"]["id"] == prep_run["id"],
        "Stock successor source-only artifact identity differs")
    archive = api.archive(artifact)
    once.require(once.sha(archive) == source_preparation["archive_sha256"],
                 "Stock successor source-only archive changed")
    files = reading.unpack_archive(archive, artifact, prep_run)
    batch = identity._json(files["source-preparation-batch.json"])
    once.require(once.sha(files["source-preparation-batch.json"]) == source_preparation["batch_sha256"]
        and batch["status"] == "SOURCE_PREPARATION_INCOMPLETE"
        and batch["formal_research_started"] is False and batch["research_execution_allowed"] is False
        and batch["model_calls"] == 0 and batch["research_work_writes"] == 0
        and batch["source_run_id"] == source_stock_run_id
        and batch["planned_issuers"] == ["603353.SH", "300711.SZ"]
        and batch["unattempted_issuers"] == [], "Stock successor source-only batch differs")
    for thscode, material in material_by_code.items():
        source_item = next(i for i in batch["items"] if i["thscode"] == thscode)
        p = source_item["preparation"]
        once.require(p["selected_ids"] == material["selected_ids"]
            and p["inventory_sha256"] == material["inventory_sha256"]
            and p["all_planned_bodies_inspected"] is True and p["unattempted_ids"] == [],
            "Stock successor saved material inventory differs")
        if thscode == "603353.SH":
            once.require(len(p["checked_body_ids"]) == 19 and p["complete_context"] is None
                and p["missing_page_reviews"] == material["missing_page_reviews"],
                "Heshun saved preparation gap differs")
        else:
            full = p["complete_context"]
            prepared_raw = files["300711.SZ/sources/prepared-context.json"]
            once.require(p["checked_body_ids"] == p["selected_ids"] and p["missing_page_reviews"] == []
                and full["bytes"] == material["prepared_context_bytes"] == len(prepared_raw)
                and full["sha256"] == material["prepared_context_sha256"] == once.sha(prepared_raw),
                "Guangha saved complete context differs")
    return prep_run, artifact, archive, files, batch


def prepare(*, api, code, request, selected, origin, reading_commit, output, clock=once.now):
    """Validate predecessors + exact source-only artifact before reserving any successor child."""
    from .stock_research_host import authorize, head
    authorize(api, code, request, request_path=REQUEST, mode=MODE)
    once.require(set(request) == {"schema_version", "enabled", "mode", "permission",
        "source_stock_run_id", "source_research_run_id", "source_preparation_run_id",
        "source_preparation_artifact", "source_preparation_request_sha256", "items"}
        and type(request["schema_version"]) is int and request["schema_version"] == 1
        and request["enabled"] is True and request["mode"] == MODE
        and all(type(request[k]) is int and request[k] > 0 for k in
                ("source_stock_run_id", "source_research_run_id", "source_preparation_run_id")),
        "Stock successor request envelope differs")
    once.require(origin["run"]["id"] == request["source_stock_run_id"], "Stock successor original Stock run differs")
    entries = request["items"]
    once.require(isinstance(entries, list) and len(entries) == 2
        and {e.get("thscode") for e in entries} == TARGETS, "Stock successor request targets differ")
    original = {i["thscode"]: i for i in selected["items"]}
    once.require(TARGETS <= set(original), "Stock successor targets outside original qualified plan")

    prep_raw = api.file(preparation.REQUEST, code)
    once.require(once.sha(prep_raw) == request["source_preparation_request_sha256"],
                 "Stock source-preparation request changed")
    prep_request = identity._json(prep_raw)
    prep_binding = preparation.bind(api=api, code=code, request=prep_request,
        selected=selected, origin=origin, clock=clock)
    once.require(prep_binding["permission"] == request["permission"]
        and [i["thscode"] for i in prep_binding["items"]] == ["603353.SH", "300711.SZ"],
        "Stock successor source-preparation binding differs")

    binding_items = []
    for entry in entries:
        thscode = entry["thscode"]
        once.require(set(entry) == {"thscode", "parent_selection", "parent_failure",
            "required_reviews", "material"}, "Stock successor item fields differ")
        item = original[thscode]
        root_eid, root_prefix = intake.execution(thscode)
        rec_eid, rec_prefix = recovery.execution(thscode)
        root_selection = identity._json(_checked_git(api, entry["parent_selection"]))
        root_failure = identity._json(_checked_git(api, entry["parent_failure"]))
        recovery.parent(thscode, root_selection, root_failure)
        once.require(root_selection["execution_id"] == root_eid
            and root_selection["origin"] == origin and root_selection["observation"] == item["observation"],
            "Stock successor original selection differs")
        _current_work_ref(api, root_prefix + "prepare.json", entry["parent_selection"]["git_blob"])
        _current_work_ref(api, root_prefix + "failure.json", entry["parent_failure"]["git_blob"])
        prep_item = next(i for i in prep_binding["items"] if i["thscode"] == thscode)
        rec_selection = prep_item["predecessor_selection"]
        rec_failure = prep_item["predecessor_failure"]
        once.require(rec_selection["path"] == rec_prefix + "prepare.json"
            and rec_failure["path"] == rec_prefix + "failure.json", "Stock successor recovery child path differs")
        for spec in (rec_selection, rec_failure):
            _current_work_ref(api, spec["path"], spec["git_blob"])
        recovery_prepare = identity._json(_checked_git(api, rec_selection))
        once.require(recovery_prepare["execution_id"] == rec_eid
            and recovery_prepare["source_recovery"]["parent_selection"]["path"] == root_prefix + "prepare.json"
            and recovery_prepare["source_recovery"]["parent_failure"]["path"] == root_prefix + "failure.json",
            "Stock successor consumed recovery lost original parent")
        reviews = entry["required_reviews"]
        once.require(isinstance(reviews, list) and reviews
            and all(set(r) == {"pdf_sha256", "page_number", "git_blob"}
                    and reading.SHA.fullmatch(r["git_blob"]) for r in reviews),
            "Stock successor visual review request differs")
        eid, prefix = execution(thscode)
        binding_items.append({"thscode": thscode, "execution_id": eid, "prefix": prefix,
            "observation": item["observation"], "origin": origin,
            "parent_selection": once.source_ref(entry["parent_selection"]["path"], entry["parent_selection"]["ref"],
                once.raw(root_selection), PARENT_SELECTION_PURPOSE),
            "parent_failure": once.source_ref(entry["parent_failure"]["path"], entry["parent_failure"]["ref"],
                once.raw(root_failure), PARENT_FAILURE_PURPOSE),
            "recovery_selection": once.source_ref(rec_selection["path"], rec_selection["ref"],
                _checked_git(api, rec_selection), RECOVERY_SELECTION_PURPOSE),
            "recovery_failure": once.source_ref(rec_failure["path"], rec_failure["ref"],
                _checked_git(api, rec_failure), RECOVERY_FAILURE_PURPOSE),
            "required_reviews": reviews, "material": entry["material"]})

    once.require(head(api, reading.READ_REF) == reading_commit, "Stock successor fixed reading moved")
    reading_raw = api.file("current-state.json", reading_commit)
    saved = identity._json(reading_raw); reading.validate_read_package(saved)
    work = saved["research"]["stock_business_work"]
    once.require(saved["code_commit"] == code and work["status"] == "READ_OK"
        and work["work_commit"] == head(api, intake.WORK_REF)
        and work["latest_execution_attempt"]["id"] == request["source_research_run_id"]
        and work["latest_source_preparation_attempt"]["id"] == request["source_preparation_run_id"],
        "Stock successor current reading does not show required history")
    for entry, bound in zip(entries, binding_items):
        shown = _reading_item(saved, entry["thscode"])
        once.require(shown["status"] == "PRE_EXECUTION_FAILURE"
            and shown.get("source_recovery", {}).get("status") == "PRE_EXECUTION_FAILURE"
            and _spec_equal(shown["sources"]["selection"], entry["parent_selection"])
            and _spec_equal(shown["sources"]["failure"], entry["parent_failure"]),
            "Stock successor current reading parent differs")
        bound["current_reading_item_status"] = shown["status"]

    source_preparation = {"run_id": request["source_preparation_run_id"],
        "artifact_id": request["source_preparation_artifact"]["id"],
        "artifact_name": request["source_preparation_artifact"]["name"],
        "artifact_digest": request["source_preparation_artifact"]["digest"],
        "archive_sha256": request["source_preparation_artifact"]["digest"].removeprefix("sha256:")}
    prep_run, artifact, archive, files, batch = _source_only_material(api=api,
        source_preparation={**source_preparation,
            "batch_sha256": once.sha(reading.unpack_archive(archive, artifact, prep_run)["source-preparation-batch.json"])
            if False else ""}, source_stock_run_id=request["source_stock_run_id"],
        material_by_code={e["thscode"]: e["material"] for e in entries})
    # The helper above needs the canonical batch hash. Rebuild from the checked archive once,
    # then check it against the same bytes instead of inventing a request-side duplicate.
    source_preparation.update(archive_sha256=once.sha(archive), batch_sha256=once.sha(files["source-preparation-batch.json"]))

    exposure = once.source_ref("current-state.json", reading_commit, reading_raw, EXPOSURE_PURPOSE)
    request_ref = once.source_ref(REQUEST, code, api.file(REQUEST, code), REQUEST_PURPOSE)
    for bound in binding_items:
        bound.update(permission=request["permission"], successor_request=request_ref,
                     current_reading=exposure, source_preparation=source_preparation)
    binding = {"kind": MODE, "permission": request["permission"], "request": request_ref,
        "current_reading": exposure, "source_preparation": source_preparation,
        "items": binding_items, "meaning": "CREATE_ONLY_SAVED_SOURCE_SUCCESSOR_NOT_RETRY_OR_NEW_PRICE_QUESTION",
        **reading.AUTHORITY}
    (output / "source-successor-origin.zip").write_bytes(archive)
    (output / "source-successor-binding.json").write_bytes(once.raw(binding))
    return [{**original[i["thscode"]], "execution_id": i["execution_id"], "prefix": i["prefix"]}
            for i in binding_items], Session(request, binding, files, batch, code, reading_commit, reading_raw, origin)


def prepare_continuation(*, api, code, request, selected, origin, reading_commit, output, clock=once.now):
    """Bind the exact pre-Research successor failure into one create-only technical continuation."""
    from .stock_research_host import authorize, head
    authorize(api, code, request, request_path=CONTINUATION_REQUEST, mode=CONTINUATION_MODE)
    once.require(set(request) == {"schema_version", "enabled", "mode", "permission", "source_stock_run_id",
        "source_preparation_run_id", "failed_successor_run_id", "failed_successor_artifact",
        "failed_successor_reading_commit", "failed_successor_work_commit", "items"}
        and request["schema_version"] == 1 and request["enabled"] is True and request["mode"] == CONTINUATION_MODE
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
    once.require(artifacts["total_count"] == len(artifacts["artifacts"]),
                 "Stock successor continuation failed artifact enumeration incomplete")
    matches = [a for a in artifacts["artifacts"] if a["id"] == expected_artifact["id"]]
    once.require(len(matches) == 1 and all(matches[0].get(k) == expected_artifact[k]
        for k in ("id", "name", "size_in_bytes", "digest")) and not matches[0].get("expired", True)
        and matches[0]["workflow_run"]["head_sha"] == expected_artifact["head_sha"],
        "Stock successor continuation failed artifact identity differs")

    failed_reading_raw = api.file("current-state.json", request["failed_successor_reading_commit"])
    failed_reading = identity._json(failed_reading_raw); reading.validate_read_package(failed_reading)
    failed_work = failed_reading["research"]["stock_business_work"]
    once.require(failed_work["status"] == "READ_OK" and failed_work["work_commit"] == work_head
        and failed_work["latest_execution_attempt"]["id"] == request["failed_successor_run_id"],
        "Stock successor continuation failed reading differs")

    once.require(head(api, reading.READ_REF) == reading_commit, "Stock successor continuation fixed reading moved")
    reading_raw = api.file("current-state.json", reading_commit)
    saved = identity._json(reading_raw); reading.validate_read_package(saved)
    work = saved["research"]["stock_business_work"]
    once.require(saved["code_commit"] == code and work["status"] == "READ_OK"
        and work["work_commit"] == work_head
        and work["latest_execution_attempt"]["id"] == request["failed_successor_run_id"],
        "Stock successor continuation current reading does not show failed predecessor")

    request_ref = once.source_ref(CONTINUATION_REQUEST, code, api.file(CONTINUATION_REQUEST, code),
                                  CONTINUATION_REQUEST_PURPOSE)
    exposure = once.source_ref("current-state.json", reading_commit, reading_raw, CONTINUATION_EXPOSURE_PURPOSE)
    failed_exposure = once.source_ref("current-state.json", request["failed_successor_reading_commit"],
                                      failed_reading_raw, CONTINUATION_PREDECESSOR_READING_PURPOSE)
    binding_items = []
    shared_source_preparation = None
    material_by_code = {}
    for entry in entries:
        thscode = entry["thscode"]
        once.require(set(entry) == {"thscode", "predecessor_selection", "predecessor_failure"},
                     "Stock successor continuation item fields differ")
        old_eid, old_prefix = execution(thscode)
        new_eid, new_prefix = continuation_execution(thscode)
        selection_spec, failure_spec = entry["predecessor_selection"], entry["predecessor_failure"]
        once.require(selection_spec["path"] == old_prefix + "prepare.json"
            and failure_spec["path"] == old_prefix + "failure.json"
            and selection_spec["ref"] == failure_spec["ref"] == work_head
            and rows.get(selection_spec["path"], {}).get("sha") == selection_spec["git_blob"]
            and rows.get(failure_spec["path"], {}).get("sha") == failure_spec["git_blob"],
            "Stock successor continuation predecessor work identity differs")
        prep_raw, failure_raw = _checked_git(api, selection_spec), _checked_git(api, failure_spec)
        prep, failure = identity._json(prep_raw), identity._json(failure_raw)
        once.require(prep["execution_id"] == old_eid and prep["thscode"] == thscode
            and prep["question_kind"] == intake.QUESTION_KIND
            and prep["origin"] == origin and prep["observation"] == original[thscode]["observation"],
            "Stock successor continuation predecessor selection differs")
        once.require(failure.get("record_kind") == "PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT"
            and failure.get("execution_id") == old_eid and failure.get("thscode") == thscode
            and failure.get("phase") == "SOURCE_PREPARATION" and failure.get("error_type") == "AttributeError"
            and failure.get("formal_research_started") is False and failure.get("research_execution") == "NOT_EXECUTED"
            and failure.get("funnel_status") == "NOT_REACHED"
            and failure.get("status") == "SOURCE_OR_INPUT_PREPARATION_INCOMPLETE"
            and failure.get("automatic_retry") is False
            and all(failure.get(k) == v for k, v in reading.AUTHORITY.items()),
            "Stock successor continuation predecessor is not the exact pre-Research AttributeError")
        old_names = {path[len(old_prefix):] for path in rows if path.startswith(old_prefix)
                     and "/" not in path[len(old_prefix):]}
        once.require(not any(name in old_names for name in
            ("launch.json", "input.json", "candidate.json", "admission.json", "receipt.json", "funnel.json")),
            "Stock successor continuation predecessor reached Research/admission")
        shown_failed = _reading_item(failed_reading, thscode).get("source_successor")
        shown_current = _reading_item(saved, thscode).get("source_successor")
        once.require(isinstance(shown_failed, dict) and isinstance(shown_current, dict)
            and shown_failed["status"] == shown_current["status"] == "PRE_EXECUTION_FAILURE"
            and shown_failed["execution_id"] == shown_current["execution_id"] == old_eid,
            "Stock successor continuation predecessor not preserved in fixed reading")
        old_binding = prep["source_successor"]
        once.require(old_binding["execution_id"] == old_eid and old_binding["prefix"] == old_prefix
            and old_binding["permission"] == request["permission"],
            "Stock successor continuation old binding differs")
        for key in ("parent_selection", "parent_failure", "recovery_selection", "recovery_failure"):
            _current_work_ref(api, old_binding[key]["path"], old_binding[key]["git_blob"]); _checked_git(api, old_binding[key])
        old_request_raw = _checked_git(api, old_binding["successor_request"])
        old_request = identity._json(old_request_raw)
        once.require(old_request["mode"] == MODE and old_request["permission"] == request["permission"]
            and old_request["source_stock_run_id"] == request["source_stock_run_id"]
            and old_request["source_preparation_run_id"] == request["source_preparation_run_id"],
            "Stock successor continuation old request differs")
        old_source_preparation = old_binding["source_preparation"]
        once.require(old_source_preparation["run_id"] == request["source_preparation_run_id"],
                     "Stock successor continuation source-only run differs")
        if shared_source_preparation is None:
            shared_source_preparation = old_source_preparation
        once.require(old_source_preparation == shared_source_preparation,
                     "Stock successor continuation source material differs across issuers")
        material_by_code[thscode] = old_binding["material"]
        binding_items.append({**old_binding, "execution_id": new_eid, "prefix": new_prefix,
            "predecessor_successor_selection": once.source_ref(selection_spec["path"], selection_spec["ref"],
                prep_raw, CONTINUATION_SELECTION_PURPOSE),
            "predecessor_successor_failure": once.source_ref(failure_spec["path"], failure_spec["ref"],
                failure_raw, CONTINUATION_FAILURE_PURPOSE),
            "predecessor_successor_request": once.source_ref(old_binding["successor_request"]["path"],
                old_binding["successor_request"]["ref"], old_request_raw, CONTINUATION_PREDECESSOR_REQUEST_PURPOSE),
            "predecessor_successor_reading": failed_exposure,
            "technical_predecessor_run_id": request["failed_successor_run_id"],
            "permission": request["permission"], "successor_request": request_ref,
            "current_reading": exposure})

    once.require(shared_source_preparation is not None, "Stock successor continuation missing source material")
    prep_run, source_artifact, archive, files, batch = _source_only_material(api=api,
        source_preparation=shared_source_preparation, source_stock_run_id=request["source_stock_run_id"],
        material_by_code=material_by_code)
    source_preparation = {"run_id": prep_run["id"], "artifact_id": source_artifact["id"],
        "artifact_name": source_artifact["name"], "artifact_digest": source_artifact["digest"],
        "archive_sha256": once.sha(archive), "batch_sha256": once.sha(files["source-preparation-batch.json"])}
    once.require(source_preparation == shared_source_preparation,
                 "Stock successor continuation source material bytes changed")
    for bound in binding_items:
        bound["source_preparation"] = source_preparation
    binding = {"kind": CONTINUATION_MODE, "permission": request["permission"], "request": request_ref,
        "current_reading": exposure, "predecessor_reading": failed_exposure,
        "failed_successor_run": reading.concise_run(failed_run),
        "failed_successor_artifact": expected_artifact, "source_preparation": source_preparation,
        "items": binding_items,
        "meaning": "CREATE_ONLY_TECHNICAL_CONTINUATION_OF_EXACT_PRE_RESEARCH_SUCCESSOR_FAILURE",
        **reading.AUTHORITY}
    (output / "source-successor-origin.zip").write_bytes(archive)
    (output / "source-successor-continuation-binding.json").write_bytes(once.raw(binding))
    return [{**original[i["thscode"]], "execution_id": i["execution_id"], "prefix": i["prefix"]}
            for i in binding_items], Session(request, binding, files, batch, code, reading_commit, reading_raw, origin,
                                             request_path=CONTINUATION_REQUEST, mode=CONTINUATION_MODE)


def source_refs(binding):
    keys = ["parent_selection", "parent_failure", "recovery_selection", "recovery_failure"]
    keys += [k for k in ("predecessor_successor_selection", "predecessor_successor_failure",
                          "predecessor_successor_request", "predecessor_successor_reading") if k in binding]
    return [binding[k] for k in keys]


def _saved_document(session, thscode, identifier):
    prefix = thscode + "/sources/"
    inventory = identity._json(session.files[prefix + "inventory.json"])
    journal = identity._json(session.files[prefix + "source-journal.json"])
    row = next(r for r in inventory["announcements"] if r["announcement_id"] == identifier)
    event = next(e for e in journal["body_events"] if e["announcement_id"] == identifier)
    digest = event["pdf_sha256"]
    pdf = session.files[prefix + digest + ".pdf"]
    extraction = identity._json(session.files[prefix + digest + "-extraction.json"])
    once.require(once.sha(pdf) == digest and len(pdf) == event["bytes"]
        and extraction["pdf_sha256"] == digest and extraction["source_locator"] == row["source_locator"],
        "Stock successor saved PDF/extraction identity differs")
    return row, event, pdf, extraction


def _represent(pdf, extraction, *, api, code_commit, clock, diagnostics):
    pages = extraction["pages"]
    if all(page_reading.text_ok(p["text"]) for p in pages):
        return pages, None, "ORIGINAL_PYPDF"
    represented = page_reading.represent(pdf, extraction,
        load_review=page_reading.main_review_loader(api, code_commit, clock), diagnostics=diagnostics)
    page_reading.validate(represented, extraction)
    return represented["pages"], represented, "BOUND_SAME_PDF_READING"


def capture(*, session: Session, ticker: str, observation: dict, api, code_commit: str,
            output: Path, clock=once.now):
    """Fresh inventory + exact saved old bodies; no repeat source-only run or old-PDF recapture."""
    thscode = ticker + (".SH" if ticker.startswith("6") else ".SZ")
    once.require(code_commit == session.code and thscode in TARGETS
        and observation["row"]["thscode"] == thscode, "Stock successor capture identity differs")
    binding = session.for_code(thscode)
    output.mkdir(parents=True, exist_ok=False)
    start = clock(); events, body_events, representation_events = [], [], []
    end_date = reading.clock(start).astimezone(SHANGHAI_TZ).date()
    def query(method, url, form=None):
        once.require(url in {cninfo.CNINFO_STOCK_MAP_URL, cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL}
            and len(events) < 48, "Stock successor inventory query differs")
        record = {"method": method, "url": url, "form": form, "started_at": clock(), "status": "FAILED",
                  "representation": "DECODED_TOOL_RETURN_NOT_WIRE_BYTES"}
        events.append(record)
        try:
            result = cninfo._request_json(url=url, method=method, form=form, timeout_seconds=20)
            body = once.raw(result); once.require(len(body) <= 8*1024*1024, "Stock successor query response too large")
            name = "query-" + str(len(events)) + ".json"; (output / name).write_bytes(body)
            record.update(status="SUCCEEDED", path=name, sha256=once.sha(body)); return result
        finally: record["finished_at"] = clock()
    batch = cninfo.fetch_cninfo_disclosures(stock_code=ticker, start_date=end_date - timedelta(days=400),
        end_date=end_date, get_json=lambda u: query("GET", u), post_json=lambda u,f: query("POST", u,f))
    inventory_end = clock(); report, selected = sources.choose(batch, checked_at=inventory_end,
        issuer_name=observation["row"].get("company_name"))
    current_inventory = {"stock_code": batch.stock_code, "org_id": batch.org_id,
        "start_date": batch.start_date.isoformat(), "end_date": batch.end_date.isoformat(),
        "checked_at": inventory_end,
        "announcements": [{**asdict(row), "published_at": row.published_at.isoformat()} for row in batch.announcements],
        "report_id": report.announcement_id,
        "post_report_inventory_anchor": min(r.published_at for r in selected).isoformat(),
        "selected_ids": [r.announcement_id for r in selected]}
    saved_prefix = thscode + "/sources/"
    saved_inventory = identity._json(session.files[saved_prefix + "inventory.json"])
    saved_prep = identity._json(session.files[saved_prefix + "source-preparation.json"])
    old_ids = binding["material"]["selected_ids"]; current_ids = current_inventory["selected_ids"]
    once.require(saved_inventory["selected_ids"] == old_ids and saved_prep["selected_ids"] == old_ids
        and saved_inventory["report_id"] == current_inventory["report_id"]
        and set(old_ids) <= set(current_ids), "Stock successor current inventory invalidates saved baseline")
    old_context = None
    if thscode == "300711.SZ":
        raw = session.files[saved_prefix + "prepared-context.json"]
        once.require(len(raw) == binding["material"]["prepared_context_bytes"]
            and once.sha(raw) == binding["material"]["prepared_context_sha256"],
            "Guangha saved context bytes differ before successor capture")
        old_context = identity._json(raw)
        once.require(old_context["issuer_inventory"]["selected_ids"] == old_ids,
                     "Guangha saved context inventory differs")
    (output / "inventory.json").write_bytes(once.raw(current_inventory))
    documents, reads, total_pdf, upgrades = [], [], 0, []
    selected_by_id = {r.announcement_id: r for r in selected}
    old_documents = ({d["announcement_id"]: d for d in old_context["issuer_documents"]}
                     if old_context is not None else {})
    for index, identifier in enumerate(current_ids, 1):
        row = selected_by_id[identifier]
        event = {"announcement_id": identifier, "source_locator": row.source_locator,
                 "started_at": clock(), "status": "INCOMPLETE"}
        body_events.append(event)
        if identifier in old_ids:
            old_row, old_event, pdf, extraction = _saved_document(session, thscode, identifier)
            once.require(old_row["source_locator"] == row.source_locator
                and old_row["published_at"] == row.published_at.isoformat(),
                "Stock successor saved announcement identity changed")
            retrieved_at = old_event["captured_at"]
            body_origin = "SOURCE_ONLY_ARTIFACT:" + str(session.binding["source_preparation"]["artifact_id"])
            event["original_captured_at"] = retrieved_at
            if old_context is not None:
                old_doc = old_documents[identifier]
                once.require(old_doc["source_locator"] == row.source_locator
                    and old_doc["published_at"] == row.published_at.isoformat()
                    and old_doc["pdf_sha256"] == once.sha(pdf)
                    and old_doc["original_text_sha256"] == extraction["text_sha256"]
                    and old_doc["page_count"] == extraction["page_count"],
                    "Guangha reconstructed saved document differs from original context")
        else:
            pdf = cninfo.fetch_cninfo_pdf_bytes(source_locator=row.source_locator,
                max_bytes=once.MAX_SOURCE_BYTES, timeout_seconds=45)
            digest = once.sha(pdf)
            parsed = extract_pdf_text(pdf, max_pdf_bytes=once.MAX_SOURCE_BYTES, max_pages=500,
                                      max_extracted_chars=1_000_000)
            extraction = {"pdf_sha256": digest, "text_sha256": parsed.text_sha256,
                "source_locator": row.source_locator, "page_count": parsed.page_count,
                "pages": [{"page_number": p.page_number, "text": p.text} for p in parsed.pages]}
            retrieved_at = clock(); body_origin = "CURRENT_CNINFO_SUCCESSOR_FETCH"
        digest = once.sha(pdf); total_pdf += len(pdf)
        once.require(total_pdf <= 128*1024*1024 and extraction["pdf_sha256"] == digest,
                     "Stock successor PDF capacity/identity differs")
        event.update(pdf_sha256=digest, bytes=len(pdf), source_origin=body_origin)
        (output / (digest + ".pdf")).write_bytes(pdf)
        (output / (digest + "-extraction.json")).write_bytes(once.raw(extraction))
        pages, represented, method = _represent(pdf, extraction, api=api, code_commit=code_commit,
                                                 clock=clock, diagnostics=representation_events)
        if represented is not None:
            (output / (digest + "-page-readings.json")).write_bytes(once.raw(represented))
            for page in represented["pages"]:
                if page["method"] == "AI_VISUAL_READING":
                    upgrades.append({"pdf_sha256": digest, "page_number": page["page_number"],
                        "current_review_source": page["review_source"]})
        if identifier == report.announcement_id:
            first = "".join(p["text"] for p in pages[:10])
            once.require(ticker in first and "报告" in first, "Stock successor report printed identity unavailable")
        documents.append({"announcement_id": identifier, "title": row.title,
            "published_at": row.published_at.isoformat(), "retrieved_at": retrieved_at,
            "retrieval_clock_basis": "ORIGINAL_SOURCE_ONLY_CAPTURE" if identifier in old_ids else "CURRENT_SUCCESSOR_FETCH",
            "source_locator": row.source_locator, "pdf_sha256": digest,
            "original_text_sha256": extraction["text_sha256"], "page_count": extraction["page_count"],
            "reading_method": method, "pages": pages, "page_reading": represented})
        checked = clock(); event.update(status="FORMAT_AND_IDENTITY_CHECKED_NOT_TRUTH", finished_at=checked)
        reads.append({"id": "body" + str(index), "identity": ticker + ":" + identifier,
            "locator": row.source_locator, "authority": "PRIMARY", "kind": "BODY", "succeeded": True,
            "checked_at": checked, "body_sha256": digest, "tool_reference": body_origin})
    expected_reviews = {(r["pdf_sha256"], r["page_number"]): r["git_blob"] for r in binding["required_reviews"]}
    actual_reviews = {(u["pdf_sha256"], u["page_number"]): u["current_review_source"]["git_blob"] for u in upgrades}
    once.require(all(actual_reviews.get(k) == blob for k, blob in expected_reviews.items()),
                 "Stock successor required visual review did not rebind to exact current note")
    material = {"source_preparation_run_id": session.request["source_preparation_run_id"],
        "artifact_id": session.binding["source_preparation"]["artifact_id"],
        "artifact_digest": session.binding["source_preparation"]["artifact_digest"],
        "saved_selected_ids": old_ids, "current_selected_ids": current_ids,
        "new_selected_ids": [i for i in current_ids if i not in old_ids],
        "visual_ref_upgrades": upgrades, "latest_inventory_checked_at": inventory_end,
        "meaning": "EXPLICIT_SAVED_ARTIFACT_SUCCESSOR_MATERIAL_NOT_INDEPENDENT_EVIDENCE"}
    if old_context is not None:
        material["saved_prepared_context_sha256"] = binding["material"]["prepared_context_sha256"]
    context = {"stock_observation": observation, "issuer_inventory": current_inventory,
        "issuer_documents": documents, "source_limitations": sources.SCOPE + " " + MATERIAL_LIMITATION,
        "source_successor_material": material}
    sources.recheck(context, api=api, code_commit=code_commit, clock=clock)
    finished = clock()
    (output / "source-successor-material.json").write_bytes(once.raw(material))
    (output / "source-journal.json").write_bytes(once.raw({"started_at": start, "finished_at": finished,
        "events": events, "body_events": body_events, "representation_events": representation_events,
        "completed_reads": reads, "captured_pdf_bytes": total_pdf, "scope": context["source_limitations"],
        "source_successor_material": material}))
    return context, reads, {"started_at": start, "finished_at": finished,
        "inventory_finished_at": inventory_end, "decoded_query_events": events,
        "scope": context["source_limitations"], "captured_pdf_bytes": total_pdf}


def check_materials(session: Session, binding, context):
    once.require(binding == session.for_code(binding["thscode"])
        and context["stock_observation"]["row"]["thscode"] == binding["thscode"]
        and context["source_successor_material"]["artifact_digest"] ==
            session.binding["source_preparation"]["artifact_digest"],
        "Stock successor context binding differs")
    current_ids = context["issuer_inventory"]["selected_ids"]
    once.require(set(binding["material"]["selected_ids"]) <= set(current_ids),
                 "Stock successor lost saved selected bodies")


def recheck(*, api, code, session: Session, binding, context, clock=once.now):
    """Recheck permission/current reading/parents/notes before every model stage."""
    from .stock_research_host import authorize, head
    authorize(api, code, session.request, request_path=session.request_path, mode=session.mode)
    once.require(head(api, reading.READ_REF) == session.reading_commit
        and api.file("current-state.json", session.reading_commit) == session.reading_raw,
        "Stock successor fixed reading changed")
    for key in ("parent_selection", "parent_failure", "recovery_selection", "recovery_failure",
                "predecessor_successor_selection", "predecessor_successor_failure"):
        if key in binding:
            spec = binding[key]; _current_work_ref(api, spec["path"], spec["git_blob"]); _checked_git(api, spec)
    for key in ("predecessor_successor_request", "predecessor_successor_reading"):
        if key in binding:
            _checked_git(api, binding[key])
    once.require(binding["permission"] == session.request["permission"]
        and binding["successor_request"] == session.binding["request"]
        and binding["current_reading"] == session.binding["current_reading"]
        and binding["source_preparation"] == session.binding["source_preparation"],
        "Stock successor child binding changed")
    sources.recheck(context, api=api, code_commit=code, clock=clock)
    check_materials(session, binding, context)
