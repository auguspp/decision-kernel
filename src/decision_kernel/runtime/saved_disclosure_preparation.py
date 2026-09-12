"""Prepare one reserved disclosure from existing saved artifacts, without Research.

THIN_ADAPTER: original archive/PDF/packet models, admission and create-only Retainer.
Format checks can reject damage; they cannot certify semantic readability or truth.
"""
from __future__ import annotations

import time
from datetime import timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from ..adapters.pdf_text import extract_pdf_text
from ..evidence import EvidenceArtifact
from ..research_funnel import DiscoveryInput
from . import current_state as read
from . import external_research_admission as admission
from . import external_research_identity as identity
from . import incremental_disclosure as work
from . import saved_research_once as once
from .external_research_execution import ExternalResearchInputPacket
from .incremental_disclosure_intake import mutable_ref, work_inventory

BODY_ROOT = "disclosure-primary-bodies/"
SOURCE_CLASS = "SAVED_DISCLOSURE_BODIES"
DISCOVERY_PURPOSE = "PREPARED_DISCLOSURE_DISCOVERY"
QUESTION = "这组已保存公告是否带来值得继续核验的公司经济问题？仅研究本组公告增量，不冒充当前全公司研究。"
LIMITATIONS = (
    "STATIC saved-announcement triage, not an exhaustive latest-issuer inventory. "
    "Original packet and prior research context are preserved, not newly accepted facts. "
    "PDF/text identity and format checks do not certify semantic readability or truth. "
    "Unreadable required content is an execution/source gap, never completed WAIT. "
    "Ambiguous tables, economic effects and present market expectations remain UNKNOWN."
)


def captured_bodies(*, archive_raw: bytes, artifact: dict, run: dict) -> dict:
    """Reuse archive validation and the existing capture manifest, with exact coverage."""
    read.run_identity(run, "inbox", success=True)
    once.require(artifact["name"] == "official-disclosure-primary-bodies", "wrong body artifact")
    files = read.unpack_archive(archive_raw, artifact, run)
    manifest = files[BODY_ROOT + "manifest.jsonl"]
    summary = identity._json(files[BODY_ROOT + "capture-summary.json"])
    rows = [identity._json(line) for line in manifest.splitlines()]
    once.require(summary.get("schema_version") == 1
                 and summary.get("status") == "PACKET_PREPARATION_COMPLETED"
                 and summary.get("investment_authority") == "NONE"
                 and summary.get("manifest_sha256") == read.sha256(manifest), "capture incomplete or changed")
    once.require(0 <= len(rows) <= admission.MAX_ITEMS
                 and summary.get("returned_pdf_reads") == len(rows)
                 and [r["sequence"] for r in rows] == list(range(1, len(rows) + 1)), "capture count differs")
    begin, end = read.clock(run["created_at"]), read.clock(run["updated_at"])
    completed = read.clock(summary["completed_at"])
    once.require(begin <= completed <= end, "capture completion outside run")
    objects, bodies = set(), {}
    for row in rows:
        digest = row["pdf_sha256"]
        once.require(isinstance(digest, str) and len(digest) == 64
                     and all(c in "0123456789abcdef" for c in digest), "invalid PDF identity")
        path = "objects/" + digest + ".pdf"
        once.require(row["path"] == path and type(row["bytes"]) is int, "capture object path differs")
        raw = files[BODY_ROOT + path]
        once.require(raw.startswith(b"%PDF-") and len(raw) == row["bytes"]
                     and len(raw) <= once.MAX_SOURCE_BYTES and read.sha256(raw) == digest,
                     "capture object bytes differ")
        once.require(begin <= read.clock(row["retained_at"]) <= completed, "capture clock outside run")
        locator = row["source_locator"]
        # Repeated original fetches are not a second source; inconsistent versions fail.
        once.require(locator not in bodies or bodies[locator][0] == raw, "conflicting captured source")
        bodies[locator] = (raw, row)
        objects.add(BODY_ROOT + path)
    actual = {p for p in files if p.startswith(BODY_ROOT + "objects/")}
    once.require(actual == objects and summary.get("unique_pdf_objects") == len(objects),
                 "capture object coverage differs")
    return bodies


def source_context(*, packet_raw: bytes, archive_raw: bytes, artifact: dict, run: dict,
                   clock=once.now, extract=extract_pdf_text, journal=None) -> tuple[dict, list[dict]]:
    """Read all required original bodies; no silent subset, OCR, fetch or new claim."""
    packet = work._packet(packet_raw)
    once.require(packet.prepared_at <= read.clock(run["updated_at"]) <= read.clock(clock()),
                 "packet or saved run is from the future")
    bodies = captured_bodies(archive_raw=archive_raw, artifact=artifact, run=run)
    original = identity._json(packet_raw)
    reads = []
    for index, evidence in enumerate(original["evidence"], 1):
        event = {"source_locator": evidence["source_locator"], "started_at": clock(),
                 "status": "FAILED", "scope": "LOCAL_SAVED_PDF_READ_NOT_GLOBAL_TOOL_JOURNAL"}
        if journal is not None:
            journal.append(event)
        try:
            pdf, capture = bodies[evidence["source_locator"]]
            once.require(evidence["pdf_sha256"] == read.sha256(pdf), "packet PDF differs from captured body")
            once.require(evidence["text_status"] == "EXTRACTED" and evidence["pages"], "required body has no text")
            parsed = extract(pdf, max_pdf_bytes=once.MAX_SOURCE_BYTES, max_pages=200,
                             max_extracted_chars=1_000_000)
            pages = [{"page_number": p.page_number, "text": p.text} for p in parsed.pages]
            once.require(parsed.pdf_sha256 == evidence["pdf_sha256"]
                         and parsed.text_sha256 == evidence["text_sha256"]
                         and parsed.page_count == evidence["page_count"] and pages == evidence["pages"],
                         "original PDF extraction identity differs")
            once.require(all(p["text"].strip() for p in pages), "required page text unavailable")
            once.require(all(not any((ord(c) < 32 and c not in "\n\r\t") or c == "\ufffd"
                                     for c in p["text"]) for p in pages), "required text contains encoding damage")
            reads.append({"id": "body" + str(index), "identity": evidence["evidence_artifact"]["source_identifier"],
                "locator": evidence["source_locator"], "authority": "PRIMARY", "kind": "BODY", "succeeded": True,
                "checked_at": clock(), "body_sha256": evidence["pdf_sha256"],
                "tool_reference": f"SAVED_ARTIFACT:{run['id']}/{artifact['id']}/{capture['path']}"})
            event["status"] = "FORMAT_AND_IDENTITY_CHECKED_NOT_SEMANTIC_ACCEPTANCE"
        finally:
            event["finished_at"] = clock()
    once.require(0 < len(reads) <= admission.MAX_ITEMS, "required body count unsupported")
    context = {"disclosure_packet": original, "source_limitations": LIMITATIONS,
               "source_capture": {"run_id": run["id"], "head_sha": run["head_sha"],
                                  "artifact_id": artifact["id"], "archive_sha256": read.sha256(archive_raw)}}
    once.require(len(once.raw(context)) < once.MAX_PROMPT_BYTES - 16000,
                 "context exceeds saved executor bound; no clipping")
    return context, reads


def _wait_until(cutoff, clock, wait):
    """One bounded time-barrier, not a retry; never backdate a committed Discovery."""
    remaining = (cutoff - read.clock(clock())).total_seconds()
    once.require(0 <= remaining <= 30, "prepared Discovery missed its declared cutoff")
    if remaining:
        wait(remaining)
    once.require(read.clock(clock()) >= cutoff, "declared cutoff not reached")


def prepare_reserved(*, api, code_commit: str, packet_source: dict, scan_raw: bytes,
                     scan_artifact: dict, body_raw: bytes, body_artifact: dict, run: dict,
                     reading_commit: str, output: Path, clock=once.now, wait=time.sleep,
                     continuation_request_source=None) -> dict:
    """Create original context/Discovery/preflight/input; never launch a model.

    prepare.json holds the original DiscoveryInput (not an admission PASS).
    Original Retainer names/old Suken host are unchanged. A partial preparation
    remains an attempted key; later calls do not overwrite or silently resume it.
    """
    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "unsafe output")
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"status": "NOT_EXECUTED", "phase": "IDENTITY", "started_at": clock(),
               "formal_research_started": False, "automatic_retry": False, **read.AUTHORITY}
    retain, reserved, packet_raw = None, None, None
    input_written = False
    journal = []
    try:
        once.require(mutable_ref(api, "main") == code_commit, "main moved")
        packet_raw = identity._checked_source(packet_source, lambda s: api.file(s["path"], s["ref"]))
        reserved = work._packet(packet_raw)
        key = reserved.assessment_input_hash
        once.require(packet_source["path"] == work.request_path(key)
                     and packet_source["purpose"] == work.PACKET_PURPOSE, "reserved packet path differs")
        prefix = work.request_path(key).removesuffix("packet.json")
        w = mutable_ref(api, work.WORK_REF)
        _, files = work_inventory(api, w)
        once.require(files[work.request_path(key)] == packet_raw, "reserved packet bytes changed")
        prior = [p for p in files if p.startswith(prefix)
                 and p.rsplit("/", 1)[-1] not in {"packet.json", "intake-plan.json"}]
        if prior:
            receipt.update(status="ALREADY_ATTEMPTED_NO_PREPARATION", existing_paths=sorted(prior))
            return receipt
        once.require(scan_artifact["name"] == "official-disclosure-scan", "wrong scan artifact")
        scan = read.unpack_archive(scan_raw, scan_artifact, run)
        scan_path = f"disclosure-assessment-packets/{reserved.stock_code}-{reserved.publication_date}-{key[:16]}.json"
        once.require(scan[scan_path] == packet_raw, "reserved packet not exact producing scan bytes")
        execution_id = "saved-disclosure-" + key
        retain = once.Retainer(api, {"id": execution_id, "prefix": prefix, "work_ref": work.WORK_REF},
                               code_commit, output)
        receipt.update(phase="SOURCE_PREFLIGHT", assessment_input_hash=key)
        continuation = None
        if continuation_request_source is not None:
            from . import disclosure_continuation
            continuation = disclosure_continuation.check(api=api, code_commit=code_commit,
                request_source=continuation_request_source, new_packet_raw=packet_raw, checked_at=clock())
        context, reads = source_context(packet_raw=packet_raw, archive_raw=body_raw,
                                       artifact=body_artifact, run=run, clock=clock, journal=journal)
        if continuation is not None:
            context["continuation_context"] = continuation["public_context"]
            receipt["continuation_permission"] = continuation["permission_receipt"]
            once.require(len(once.raw(context)) < once.MAX_PROMPT_BYTES - 16000,
                         "continuation context exceeds saved executor bound; no clipping")
        # The trusted caller may approve only this fixed public source/context shape.
        cs = retain.save("source.json", context); cs["purpose"] = "MODEL_CONTEXT"
        meta = api.get("git/commits/" + cs["ref"])
        once.require(meta["sha"] == cs["ref"], "context commit identity differs")
        seed = EvidenceArtifact(id=uuid5(NAMESPACE_URL, execution_id + cs["sha256"]),
            source_type="SAVED_RESEARCH_OBSERVATION", source_identifier=execution_id,
            source_locator=once.locator(cs), published_at=meta["committer"]["date"],
            available_at=clock(), retrieved_at=clock(), content_hash=cs["sha256"], idempotency_key=execution_id,
            retention_mode="FULL_ARTIFACT", replayability_level="PARTIAL", raw_storage_ref=once.locator(cs),
            license_terms_note="Exact internal public context, not primary truth certification. Original PDFs remain in the producing artifact with its expiry.")
        ticker = reserved.stock_code
        case_id = ticker + (".SH" if ticker.startswith("6") else ".SZ")
        security_id = ("SSE:" if ticker.startswith("6") else "SZSE:") + ticker
        pf = {"schema_version": 1, "provenance": "RECORDED_TOOL_RETURNS", "case_id": case_id,
            "ticker": ticker, "security_id": security_id, "started_at": receipt["started_at"],
            "finished_at": clock(), "valid_until": (read.clock(clock()) + timedelta(minutes=45)).isoformat(),
            "reads": reads, "required_classes": [{"id": SOURCE_CLASS, "mode": "STATIC",
                "body_ids": [r["id"] for r in reads], "inventory_id": None}], "inventories": [],
            "limits": {"max_queries": 0, "max_reads": len(reads)},
            "seed_publications": [{"evidence_id": str(seed.id), "kind": "GIT_COMMIT", "source": cs}],
            "notes": LIMITATIONS}
        ps = retain.save("preflight.json", pf); ps["purpose"] = admission.PREFLIGHT_PURPOSE
        reading = identity._json(api.file("current-state.json", reading_commit))
        read.validate_read_package(reading)
        once.require(read.clock(reading["checks"]["finished_at"]) <= read.clock(clock())
                     <= read.clock(reading["checks"]["recheck_after"]), "reading check window expired")
        selected = clock()
        # Declare before writing; only source versions already known are included.
        # #337 requires Discovery's commit <= its as_of. Never relabel a later
        # commit as earlier: cross a small explicit time barrier, or fail closed.
        cutoff = read.clock(clock()) + timedelta(seconds=30)
        discovery = DiscoveryInput(discovery_id=execution_id, source_lane="CNINFO_INCREMENTAL",
            ticker=ticker, security_id=security_id, as_of=cutoff,
            economic_direction="已保存公告对公司经济问题的增量尚未解释",
            factual_observations=({"statement": "已保存本组公告及其原研究上下文；保存不代表结论被接受。",
                                   "evidence_artifact_ids": (seed.id,)},),
            source_lineage=({"evidence_artifact_id": seed.id, "source_locator": seed.source_locator,
                             "available_at": seed.available_at},),
            why_now="原FIFO选中的新工作项，不是当前价格信号或完整公司更新。",
            next_discriminating_search="仅核验本组公告相对原上下文的经济增量；必要材料缺失则留缺口。",
            known_stop_or_downgrade_condition="无证据支持经济联系时允许停止；不发明原因，不为测试强行Quick。")
        ds = retain.save("prepare.json", discovery); ds["purpose"] = DISCOVERY_PURPOSE
        dm = api.get("git/commits/" + ds["ref"])
        once.require(dm["sha"] == ds["ref"] and read.clock(dm["committer"]["date"]) <= cutoff,
                     "Discovery commit missed declared cutoff")
        _wait_until(cutoff, clock, wait)
        packet = ExternalResearchInputPacket(execution_id=execution_id, case_id=case_id, ticker=ticker,
            security_id=security_id, source_lane="CNINFO_INCREMENTAL", selected_at=selected,
            research_cutoff=cutoff, code_commit=code_commit, current_state_commit=reading_commit,
            current_state_reading_hash=reading["reading_hash"], source_refs=(packet_source, cs, ps, ds, *(continuation["source_refs"] if continuation else ())),
            seed_evidence_artifacts=(seed,), research_question=continuation["question"] if continuation else QUESTION,
            known_unknowns=(f"REQUIRED_SOURCE_CLASS:{SOURCE_CLASS}:STATIC", LIMITATIONS),
            next_discriminating_search=discovery.next_discriminating_search,
            method_version="research-funnel-v1", prompt_version="saved-disclosure-continuation-v1" if continuation else "saved-disclosure-preparation-v1",
            allowed_tools=("OTHER_READ",), candidate_output_prefix=prefix,
            budget={"max_tool_calls": 6, "max_search_queries": 0, "max_source_reads": 4,
                "max_technical_retries": 0, "max_elapsed_minutes": 15,
                **{k + "_enforcement": "SOFT_EXECUTOR" for k in (
                    "tool_calls", "search_queries", "source_reads", "technical_retries", "elapsed_time")}})
        catalogue = api.file(identity.CATALOG_PATH, code_commit)
        _, execution_key, _ = admission.prepare_input(input_raw=once.raw(packet), preflight_raw=once.raw(pf),
            catalog_source=once.source_ref(identity.CATALOG_PATH, code_commit, catalogue, "CURRENT_CODE_EXECUTION_SCOPE"),
            load=lambda s: api.file(s["path"], s["ref"]), commit=lambda r: api.get("git/commits/" + r),
            checked_at=clock(), current_code=lambda: mutable_ref(api, "main"))
        receipt["phase"] = "INPUT_COMMIT"
        ins = retain.save("input.json", packet); input_written = True
        receipt.update(status="INPUT_PREPARED_NOT_EXECUTED", phase="COMPLETE", input_source=ins,
                       expected_key=execution_key.as_dict())
    except Exception as exc:
        receipt.update(error_type=type(exc).__name__, error_code=getattr(exc, "code", None))
        if retain and not retain.uncertain and not input_written:
            failure = {"schema_version": 1, "record_kind": "PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT",
                "assessment_input_hash": reserved.assessment_input_hash, "case_id": reserved.stock_code,
                "packet_blob": read.blob_sha(packet_raw), "packet_sha256": read.sha256(packet_raw),
                "status": "SOURCE_OR_INPUT_PREPARATION_INCOMPLETE", "research_execution": "NOT_EXECUTED",
                "funnel_status": "NOT_REACHED", "formal_research_budget_used": 0,
                "started_at": receipt["started_at"], "finished_at": clock(),
                "error_type": type(exc).__name__, "error_code": getattr(exc, "code", None),
                "automatic_retry": False, **read.AUTHORITY}
            try:
                retain.save("failure.json", failure)
            except Exception as retaining:
                receipt.update(retention_error_type=type(retaining).__name__)
    finally:
        receipt.update(finished_at=clock(), retained_files=list(retain.writes) if retain else [],
                       mutation_uncertain=bool(retain and retain.uncertain))
        (output / "preflight-read-events.json").write_bytes(once.raw(journal))
        (output / "preparation-receipt.json").write_bytes(once.raw(receipt))
    return receipt
