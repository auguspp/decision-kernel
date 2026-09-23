"""Explicit main-reviewed import of retained capture bytes into the daily host.

This is a read-only format adapter, not another capture, permission or executor.
The original acquisition run and clocks survive; unlisted captures are rejected.
"""
from __future__ import annotations

from . import current_state as reading
from . import external_research_identity as identity
from . import saved_research_once as once

IMPORTS_PATH = "research_runs/stock-retained-source-imports.json"
FORMAT = "CNINFO_EXACT_REPORT_CAPTURE_V1"
PROVENANCE = "IMPORTED_HISTORICAL_CAPTURE_NOT_NEW_ACQUISITION"


def project(profile, files):
    """Re-express an exact retained capture without changing any source bytes."""
    expected = profile["files"]
    once.require(set(files) == set(expected) and 1 <= len(expected) <= 16,
                 "DAILY_IMPORT_FILE_INVENTORY")
    for name, spec in expected.items():
        raw = files[name]
        once.require(isinstance(raw, bytes) and type(spec["bytes"]) is int
                     and len(raw) == spec["bytes"] and once.sha(raw) == spec["sha256"]
                     and once.blob(raw) == spec["git_blob"], "DAILY_IMPORT_FILE_BYTES")
    receipt = identity._json(files["receipt.json"])
    inventory = identity._json(files["inventory.json"])
    extraction = identity._json(files["extraction.json"])
    selected = receipt["selected"]
    ticker = profile["case_id"][:6]
    once.require(profile["format"] == FORMAT
                 and receipt["status"] == "EXACT_REPORT_RETAINED_NOT_RESEARCH_ADMITTED"
                 and receipt["run_id"] == str(profile["run"]["id"])
                 and receipt["workflow_commit"] == profile["run"]["head_sha"]
                 and receipt["target"]["code_commit"] == profile["capture_code"]
                 and receipt["research_execution"] == "NOT_EXECUTED"
                 and receipt["model_calls"] == 0 and receipt["automatic_retry"] is False
                 and receipt["investment_authority"] == "NONE",
                 "DAILY_IMPORT_ORIGINAL_RECEIPT")
    once.require(selected["stock_code"] == receipt["target"]["ticker"] == ticker
                 and selected["announcement_id"] == receipt["target"]["announcement_id"]
                 == profile["announcement_id"]
                 and selected["title"] == receipt["target"]["title"]
                 and inventory["stock_code"] == ticker
                 and inventory["org_id"] == selected["org_id"]
                 and [r for r in inventory["announcements"]
                      if r["announcement_id"] == profile["announcement_id"]] == [selected],
                 "DAILY_IMPORT_ISSUER_OR_DOCUMENT")
    pdf_name = receipt["pdf"]["path"]
    once.require(set(expected) == {pdf_name, "receipt.json", "inventory.json", "extraction.json",
                                  *[e["source"]["path"] for e in receipt["query_events"]]},
                 "DAILY_IMPORT_FILE_INVENTORY")
    for spec in [receipt["pdf"], receipt["inventory"], receipt["extraction"],
                 *[e["source"] for e in receipt["query_events"]]]:
        once.require(all(spec[k] == expected[spec["path"]][k] for k in ("bytes", "sha256")),
                     "DAILY_IMPORT_RECEIPT_FILES")
    times = [receipt[k] for k in ("started_at", "pdf_started_at", "pdf_finished_at", "finished_at")]
    parsed_times = [reading.clock(t) for t in times]
    once.require(parsed_times == sorted(parsed_times)
                 and reading.clock(selected["published_at"]) <= parsed_times[1],
                 "DAILY_IMPORT_ORIGINAL_CLOCK")
    digest = receipt["pdf"]["sha256"]
    once.require(extraction["pdf_sha256"] == digest
                 and extraction["page_count"] == receipt["page_count"], "DAILY_IMPORT_EXTRACTION")
    body_read = {"id": "retained-" + profile["announcement_id"],
        "identity": ticker + ":" + profile["announcement_id"],
        "locator": selected["source_locator"], "authority": "PRIMARY", "kind": "BODY",
        "succeeded": True, "body_sha256": digest, "checked_at": receipt["finished_at"],
        "tool_reference": f"GitHub source run {profile['run']['id']}; retained original receipt"}
    event = {"announcement_id": profile["announcement_id"],
        "source_locator": selected["source_locator"], "pdf_sha256": digest,
        "bytes": receipt["pdf"]["bytes"], "status": "FORMAT_AND_IDENTITY_CHECKED_NOT_TRUTH",
        "captured_at": receipt["pdf_started_at"], "finished_at": receipt["finished_at"]}
    journal = {"completed_reads": [body_read], "body_events": [event],
        "provenance": PROVENANCE, "original_source_run": profile["run"],
        "original_receipt_sha256": expected["receipt.json"]["sha256"],
        "new_source_requests": 0}
    prefix = profile["case_id"] + "/sources/"
    return {prefix + "inventory.json": files["inventory.json"],
            prefix + "source-journal.json": once.raw(journal),
            prefix + digest + ".pdf": files[pdf_name],
            prefix + digest + "-extraction.json": once.raw({**extraction,
                "source_locator": selected["source_locator"]})}


def load(api, code, custody, cache):
    """Only a reviewed exact-main profile admits this historical capture format."""
    from .stock_daily_question import _source
    raw_profile = api.file(IMPORTS_PATH, code)
    registry = identity._json(raw_profile)
    once.require(registry.get("schema_version") == 1 and isinstance(registry.get("imports"), dict)
                 and len(registry["imports"]) <= 16, "DAILY_IMPORT_REGISTRY")
    name = custody["source_import"]
    once.require(isinstance(name, str) and name in registry["imports"], "DAILY_IMPORT_NOT_REVIEWED")
    profile = registry["imports"][name]
    once.require(set(profile["run"]) == {"id", "path", "head_branch", "head_sha", "event"}
                 and type(profile["run"]["id"]) is int and profile["run"]["id"] > 0
                 and reading.SHA.fullmatch(profile["run"]["head_sha"])
                 and reading.SHA.fullmatch(profile["capture_code"]), "DAILY_IMPORT_RUN_PROFILE")
    once.require(profile["enabled"] is True and profile["format"] == FORMAT
                 and profile["case_id"][:6] == custody["ticker"]
                 and custody["source_run_id"] == profile["run"]["id"]
                 and custody["source_artifact"] == profile["artifact"], "DAILY_IMPORT_PROFILE_BINDING")
    run, files = _archive(api, profile, cache)
    converted = project(profile, files)
    receipt = identity._json(files["receipt.json"])
    once.require(reading.clock(run["run_started_at"]) <= reading.clock(receipt["started_at"])
                 <= reading.clock(receipt["finished_at"]) <= reading.clock(run["updated_at"])
                 <= reading.clock(custody["checked_at"]), "DAILY_IMPORT_RUN_CLOCK")
    # Small metadata uses the original checked reader. PDF bytes are independently
    # bound to exact Git by #492 in the caller; no second PDF body download.
    for name, spec in profile["files"].items():
        if name == receipt["pdf"]["path"]:
            once.require(len(custody["documents"]) == 1
                         and custody["documents"][0]["pdf_source"] == {
                             k: v for k, v in spec.items() if k != "bytes"},
                         "DAILY_IMPORT_PDF_REFERENCE")
        else:
            actual, _ = _source(api, spec, spec["purpose"], lambda: custody["checked_at"])
            once.require(actual == files[name], "DAILY_IMPORT_GIT_COPY_DIFFERS")
    return converted


def _archive(api, profile, cache):
    """Shared native artifact qualification; format adapters keep their own contracts."""
    run = api.get("actions/runs/" + str(profile["run"]["id"]))
    once.require(all(run.get(k) == v for k, v in profile["run"].items())
                 and run.get("repository", {}).get("full_name") == once.REPO
                 and run.get("head_repository", {}).get("full_name") == once.REPO
                 and run.get("status") == "completed" and run.get("conclusion") == "success"
                 and run.get("run_attempt") == 1, "DAILY_IMPORT_RUN_IDENTITY")
    listing = api.get(f"actions/runs/{run['id']}/artifacts?per_page=100")
    once.require(len(listing["artifacts"]) == listing["total_count"] <= 100,
                 "DAILY_IMPORT_ARTIFACT_INVENTORY")
    matches = [a for a in listing["artifacts"] if a["id"] == profile["artifact"]["id"]]
    once.require(len(matches) == 1, "DAILY_IMPORT_ARTIFACT_UNAVAILABLE")
    artifact = matches[0]
    once.require(all(artifact.get(k) == profile["artifact"][k]
                     for k in ("id", "name", "size_in_bytes", "digest"))
                 and not artifact.get("expired", True)
                 and artifact["workflow_run"]["id"] == run["id"]
                 and artifact["workflow_run"]["head_sha"] == profile["artifact"]["head_sha"]
                 == run["head_sha"], "DAILY_IMPORT_ARTIFACT_IDENTITY")
    key = (artifact["id"], artifact["digest"])
    if key not in cache:
        cache[key] = reading.unpack_archive(api.archive(artifact), artifact, run)
    files = cache[key]
    return run, files
