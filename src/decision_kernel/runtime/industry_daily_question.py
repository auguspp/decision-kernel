"""Industry origin binding for the original daily question host.

No provider, selector, model loop or quota store. The legacy request-mode name
is transport compatibility only; the source proof explicitly says Industry.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from ..identity import canonical_hash
from . import current_state as reading
from . import external_research_admission as admission
from . import external_research_identity as identity
from . import industry_breadth as breadth
from . import industry_breadth_reading as breadth_reader
from . import saved_research_once as once
from . import stock_daily_question as daily
from .radar_company_reading import retained_bytes
from .reviewed_full_input import LIMITS as FULL_INPUT_LIMITS

PURPOSE = "DAILY_INDUSTRY_BATCH_REVIEW"
EXTENSION_PATH = "research_runs/industry-daily-question-extension.json"
PERMISSION = {"comment_id": 5778160521,
    "body_sha256": "45364363eccca62a115d35ea1212f02f9c2fa918b85cb4c7ad8ca3fd50677e1c",
    "created_at": "2026-09-22T14:17:34Z"}
EXTENSION = {"schema_version": 1, "permission": PERMISSION,
    "origin_kind": "INDUSTRY_VARIABLE_OBSERVATION", "batch_review_purpose": PURPOSE,
    "shared_policy_path": daily.POLICY_PATH, "shared_consumption_prefix": daily.PREFIX,
    "required_source_modes": ["STATIC", "LATEST_INVENTORY"],
    "complete_input": FULL_INPUT_LIMITS,
    "model_cost_policy": "HUMAN_MANAGED_ACCOUNT_NO_ADDITIONAL_PROJECT_MONETARY_CEILING",
    "automatic_retry": False, "automatic_deep": False, "investment_authority": "NONE"}
DISPOSITIONS = {"SELECTED_FOR_QUESTION", "CONTEXT_ONLY", "DATA_UNAVAILABLE",
                "NO_DISTINCT_QUESTION", "EXISTING_RESEARCH", "NOT_SELECTED"}


def check_policy(api, code, request, clock):
    once.require(request["permission"] == PERMISSION
                 and request["batch_review_source"]["purpose"] == PURPOSE
                 and identity._json(api.file(EXTENSION_PATH, code)) == EXTENSION,
                 "INDUSTRY_DAILY_EXTENSION_NOT_AUTHORIZED")
    once.require(admission.clock(PERMISSION["created_at"]) <= admission.clock(clock())
                 < admission.clock(daily.POLICY["execute_before"]),
                 "INDUSTRY_DAILY_PERMISSION_CLOCK")


def _native(api, state, rs, clock, archives):
    spec = state["research"]["industry_breadth"]["details"]["json"]
    once.require(spec["read_path"] == breadth_reader.REPORT, "INDUSTRY_REPORT_PATH")
    raw = api.file(spec["read_path"], rs["ref"])
    once.require(len(raw) <= identity.MAX_BYTES, "INDUSTRY_REPORT_SIZE")
    retained_bytes({spec["read_path"]: raw}, spec)
    report = identity._json(raw)
    once.require(report["projection_hash"] == canonical_hash(report["projection"]),
                 "INDUSTRY_REPORT_HASH")
    section = report["projection"]["sections"]["native"]
    once.require(section["status"] == "SAVED_NATIVE_SNAPSHOT", "INDUSTRY_NATIVE_NOT_QUALIFIED")
    origin = section["latest_attempt"]
    run = api.get("actions/runs/" + str(origin["id"]))
    breadth_reader._run(run, clock())
    once.require(run["status"] == "completed" and run["conclusion"] == "success"
                 and reading.concise_run(run) == origin, "INDUSTRY_NATIVE_RUN_DIFFERS")
    saved = section["archive"]
    once.require(saved["origin_run"] == origin, "INDUSTRY_ARCHIVE_ORIGIN_DIFFERS")
    listing = api.get(f"actions/runs/{run['id']}/artifacts?per_page=100")
    once.require(len(listing["artifacts"]) == listing["total_count"] <= 100,
                 "INDUSTRY_ARTIFACT_INVENTORY")
    found = [a for a in listing["artifacts"] if a["id"] == saved["artifact_id"]]
    once.require(len(found) == 1, "INDUSTRY_ARTIFACT_MISSING")
    artifact = found[0]
    once.require(artifact["name"] == saved["artifact_name"] == f"industry-breadth-{run['id']}-1"
                 and artifact["size_in_bytes"] == saved["bytes"]
                 and artifact["digest"] == "sha256:" + saved["sha256"]
                 and not artifact.get("expired", True)
                 and artifact["workflow_run"]["id"] == run["id"]
                 and artifact["workflow_run"]["head_sha"] == run["head_sha"],
                 "INDUSTRY_ARTIFACT_DIFFERS")
    key = (artifact["id"], artifact["digest"])
    if key not in archives:
        archives[key] = reading.unpack_archive(api.archive(artifact), artifact, run)
    rebuilt = breadth.replay(archives[key], run, cutoff=clock())
    once.require(all(rebuilt[k] == section[k] for k in ("status", "capture", "snapshot")),
                 "INDUSTRY_SAVED_REPLAY_DIFFERS")
    source = once.source_ref(spec["read_path"], rs["ref"], raw, "SAVED_INDUSTRY_BATCH_ORIGIN")
    return section, source


def row_binding(row):
    """All original rows, including unidentified ones, receive a review identity."""
    return {"source_row": row["source_row"], "raw_sha256": canonical_hash(row["raw"])}


def batch_id(rs, section):
    return canonical_hash({"kind": EXTENSION["origin_kind"], "reading_source": rs,
                           "run": section["latest_attempt"],
                           "capture_hash": section["capture"]["capture_hash"]})


def bind(api, request, q, packet, context, clock, *, archives=None):
    check_policy(api, packet.code_commit, request, clock)
    once.require(all(c["mode"] in EXTENSION["required_source_modes"] for c in q["required_classes"]),
                 "INDUSTRY_REQUIRED_SOURCE_MODE")
    rs = q["reading_source"]
    selected_clock = lambda: packet.selected_at.isoformat()
    state = identity._json(identity._checked_source(rs, lambda s: api.file(s["path"], s["ref"])))
    reading.validate_read_package(state)
    cache = {} if archives is None else archives
    section, source = _native(api, state, rs, selected_clock, cache)
    observed_at = section["capture"]["receipt"]["received_at"]
    once.require(any(o["kind"] == EXTENSION["origin_kind"]
                     and o["qualification"] == "QUALIFIED_FOR_DECLARED_SCOPE"
                     and o["source"] == source and o["observed_at"] == observed_at for o in q["origins"]),
                 "INDUSTRY_QUESTION_ORIGIN_DIFFERS")
    raw, saved_at = daily._source(api, request["batch_review_source"], PURPOSE, selected_clock)
    review = identity._json(raw)
    once.require(set(review) == {"reading_source", "question_source", "batch_id", "reviewed_at",
                                "market_session", "items", "economic_exposure"}
                 and review["reading_source"] == rs and review["question_source"] == request["question_source"]
                 and review["batch_id"] == batch_id(rs, section)
                 and admission.clock(observed_at) <= admission.clock(review["reviewed_at"])
                 <= admission.clock(saved_at), "INDUSTRY_BATCH_REVIEW_BINDING")
    # Reuse the saved completed A-share market day, NOT any Sector ranking/gate.
    # This anchor allocates the shared day slot; it does not date a futures close.
    sector = state["lanes"]["sector"]["last_qualified_result"]
    sector_origin = sector["archive"]["origin_run"]
    session_run = api.get("actions/runs/" + str(sector_origin["id"]))
    reading.run_identity(session_run, "sector", success=True)
    day = review["market_session"]
    once.require(reading.concise_run(session_run) == sector_origin
                 and day == sector["market_session"] and date.fromisoformat(day).isoformat() == day
                 and daily.POLICY["first_market_session"] <= day
                 and admission.clock(day + "T15:00:00+08:00") <= admission.clock(observed_at),
                 "INDUSTRY_SHARED_COMPLETED_DAY_DIFFERS")
    projection = section["snapshot"]["projection"]
    rows = sorted(projection["observations"] + projection["invalid_rows"], key=lambda r: r["source_row"])
    items = review["items"]
    once.require(isinstance(items, list) and 0 < len(items) == len(rows) <= breadth.MAX_ROWS
                 and [r["source_row"] for r in rows] == list(range(len(rows)))
                 and all(set(item) == {"source_row", "raw_sha256", "disposition", "reason"}
                         and type(item["source_row"]) is int
                         and item["disposition"] in DISPOSITIONS and admission.text(item["reason"])
                         and all(item[k] == v for k, v in row_binding(row).items())
                         for row, item in zip(rows, items, strict=True)),
                 "INDUSTRY_FULL_BATCH_REVIEW_REQUIRED")
    selected = [row for row, item in zip(rows, items, strict=True)
                if item["disposition"] == "SELECTED_FOR_QUESTION"]
    once.require(selected and all(r.get("lane") == "INDUSTRY_CANDIDATE_CONTEXT"
                 and r["source_date_status"] == "DATED_SOURCE_CLAIM"
                 and r["raw"]["spot_publish_date"] == day for r in selected),
                 "INDUSTRY_SELECTED_OBSERVATION_UNQUALIFIED")
    exposure = review["economic_exposure"]
    once.require(set(exposure) == {"case_id", "security_id", "context_source", "mechanism",
                                  "materiality_basis", "counterevidence", "falsification_test", "use"}
                 and exposure["case_id"] == packet.case_id and exposure["security_id"] == packet.security_id
                 and exposure["context_source"] == request["context_source"]
                 and all(admission.text(exposure[k]) for k in ("mechanism", "materiality_basis", "counterevidence"))
                 and exposure["falsification_test"] == q["falsification_test"]
                 and exposure["use"] == "QUESTION_FORMATION_NOT_QUANTIFIED_BENEFIT",
                 "INDUSTRY_COMPANY_EXPOSURE_DECLARATION_REQUIRED")
    from .declared_report_input import bind_or_legacy
    packet, total = bind_or_legacy(api, request, packet, context, clock, archives=cache)
    return packet, state, {"market_session": day, "batch_id": review["batch_id"],
        "source_run_id": section["latest_attempt"]["id"], "reading_source": rs,
        "reading_hash": state["reading_hash"], "batch_review_source": request["batch_review_source"],
        "reviewed_items": items, "source_custody_source": request["source_custody_source"], "pdf_bytes": total,
        "source_proof": "RETAINED_INDUSTRY_BYTES_AND_PUBLIC_PDFS_NOT_ECONOMIC_TRUTH",
        "origin_kind": EXTENSION["origin_kind"], "origin_source": source,
        "extension_permission": PERMISSION, "shared_day_anchor": sector_origin,
        "selected_observations": [row_binding(r) for r in selected], "economic_exposure": exposure}
