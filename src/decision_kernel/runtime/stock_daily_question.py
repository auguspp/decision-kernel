"""Bounded daily policy for the original question host; no scheduler or executor.

The saved batch review is an accountable researcher's declaration, not economic
truth certification. Existing Git readers, PDF extraction and create-only
Retainers supply the actual identity, source and consumption checks.
"""
from __future__ import annotations

from datetime import date
from pathlib import PurePosixPath
import re
from types import SimpleNamespace
from urllib.parse import urlsplit

from ..adapters.pdf_text import extract_pdf_text
from ..identity import canonical_hash
from . import current_state as reading
from . import external_research_admission as admission
from . import external_research_identity as identity
from . import reviewed_question_reading as reader
from . import saved_research_once as once
from . import stock_research_intake as intake
from . import stock_research_reading as stock_reader
from .external_research_execution import ExternalResearchInputPacket

REQUEST = "research_runs/stock-daily-question-request.json"
POLICY_PATH = "research_runs/stock-daily-question-policy.json"
MODE = "BOUNDED_DAILY_REVIEWED_STOCK_QUESTION"
PREFIX = "research_runs/daily-stock-questions-v0/"
PERMISSION = {"comment_id": 5748820065,
    "body_sha256": "6f45cf4378304c70fe734d2b080fd24115a6056966f60be5ec66dd5e27fb93f5",
    "created_at": "2026-09-20T09:00:30Z"}
POLICY = {"schema_version": 1, "mode": MODE, "permission": PERMISSION,
    "first_market_session": "2026-09-18", "execute_before": "2026-10-20T00:00:00Z",
    "max_market_days": 10, "max_attempts_per_market_day": 1,
    "required_source_modes": ["STATIC"], "max_documents": 4,
    "max_pdf_bytes": 32 * 1024 * 1024, "max_context_bytes": 448 * 1024,
    "max_prompt_bytes": 512 * 1024, "max_output_tokens": 6000,
    "retained_source_file_bytes": identity.MAX_BYTES,
    "provider": {"name": "DEEPSEEK_OFFICIAL", "base_url": once.DEEPSEEK_BASE_URL,
                 "model": once.DEEPSEEK_MODEL, "credential_binding": "DEEPSEEK_API_KEY",
                 "reasoning": {"effort": "none"}},
    "automatic_retry": False, "automatic_deep": False, "investment_authority": "NONE"}
EXTRA_SOURCES = {"batch_review_source": "DAILY_STOCK_BATCH_REVIEW",
                 "source_custody_source": "DAILY_PUBLIC_PDF_CUSTODY"}
REVIEW_DISPOSITIONS = {"SELECTED_NEW_DISTINCT_QUESTION", "NOT_SELECTED", "NO_DISTINCT_QUESTION",
    "EXISTING_RESEARCH", "SOURCE_UNAVAILABLE", "ORIGINAL_PRICE_DISPOSITION_ONLY", "DATA_UNAVAILABLE"}


READY_LABEL = "daily-stock-question-ready"


def label_transport(env):
    """A fixed owned-issue signal only; trusted main request still grants scope."""
    return (env.get("GITHUB_EVENT_NAME") == "issues"
            and env.get("GITHUB_WORKFLOW") == "stock-business-research"
            and env.get("DAILY_EVENT_ACTION") == "labeled"
            and env.get("DAILY_ISSUE_NUMBER") == "297"
            and env.get("DAILY_LABEL") == READY_LABEL
            and env.get("DAILY_SENDER") == "auguspp"
            and env.get("DAILY_IS_PULL_REQUEST") == "false")


def check_policy(api, code, request, clock):
    once.require(identity._json(api.file(POLICY_PATH, code)) == POLICY
                 and request["permission"] == PERMISSION, "DAILY_POLICY_CHANGED")
    once.require(admission.clock(PERMISSION["created_at"]) <= admission.clock(clock())
                 < admission.clock(POLICY["execute_before"]), "DAILY_POLICY_EXPIRED_OR_NOT_STARTED")


def base_request(request):
    from . import stock_question_host as host
    expected = {"schema_version", "enabled", "mode", "permission", "question_source",
                "context_source", "preflight_source", "approved_egress_hash", *EXTRA_SOURCES}
    once.require(set(request) == expected and request["approved_egress_hash"] is None,
                 "DAILY_REQUEST_SHAPE")
    return {**{k: v for k, v in request.items() if k not in EXTRA_SOURCES}, "mode": host.QUESTION_MODE}


def _source(api, spec, purpose, clock):
    once.require(spec["purpose"] == purpose, "DAILY_SOURCE_PURPOSE")
    raw = identity._checked_source(spec, lambda s: api.file(s["path"], s["ref"]))
    meta = api.get("git/commits/" + spec["ref"])
    once.require(meta["sha"] == spec["ref"]
                 and admission.clock(meta["committer"]["date"]) <= admission.clock(clock()),
                 "DAILY_SOURCE_COMMIT_CLOCK")
    return raw, meta["committer"]["date"]


def _retained_pdf(api, spec, archived_pdf, expected_bytes, clock):
    """Bind already-qualified artifact bytes to an immutable Git file.

    Only large PDFs take the tree path. Small sources keep the original reader.
    This does not qualify an artifact, fetch a PDF URL, or change metadata limits.
    """
    once.require(type(expected_bytes) is int and isinstance(archived_pdf, bytes)
                 and 0 < expected_bytes == len(archived_pdf) <= POLICY["max_pdf_bytes"],
                 "DAILY_RETAINED_PDF_IDENTITY_OR_SIZE")
    if expected_bytes <= identity.MAX_BYTES:
        raw, saved_at = _source(api, spec, "RETAINED_PUBLIC_ISSUER_PDF", clock)
        once.require(raw == archived_pdf, "DAILY_SOURCE_ARTIFACT_DOCUMENT_DIFFERS")
        return raw, saved_at
    once.require(isinstance(spec, dict) and spec.get("purpose") == "RETAINED_PUBLIC_ISSUER_PDF"
                 and spec.get("repository") == once.REPO
                 and isinstance(spec.get("ref"), str) and reading.SHA.fullmatch(spec["ref"])
                 and isinstance(spec.get("git_blob"), str) and reading.SHA.fullmatch(spec["git_blob"])
                 and isinstance(spec.get("sha256"), str)
                 and re.fullmatch(r"[0-9a-f]{64}", spec["sha256"]), "DAILY_PDF_SOURCE_REFERENCE")
    path = reading.safe_path(spec["path"])
    once.require(path.startswith("research_runs/") and path.lower().endswith(".pdf"),
                 "DAILY_PDF_SOURCE_REFERENCE")
    tree = api.get("git/trees/" + spec["ref"] + "?recursive=1")
    once.require(tree.get("truncated") is False and isinstance(tree.get("tree"), list)
                 and len(tree["tree"]) <= 5000
                 and all(isinstance(row, dict) for row in tree["tree"]), "DAILY_PDF_TREE_INCOMPLETE")
    matches = [row for row in tree["tree"] if row.get("path") == path]
    once.require(len(matches) == 1, "DAILY_PDF_GIT_BINDING_DIFFERS")
    row = matches[0]
    once.require(row.get("type") == "blob" and row.get("mode") == "100644"
                 and type(row.get("size")) is int and row["size"] == expected_bytes
                 and row.get("sha") == spec["git_blob"] == once.blob(archived_pdf)
                 and spec["sha256"] == once.sha(archived_pdf), "DAILY_PDF_GIT_BINDING_DIFFERS")
    meta = api.get("git/commits/" + spec["ref"])
    once.require(meta["sha"] == spec["ref"]
                 and admission.clock(meta["committer"]["date"]) <= admission.clock(clock()),
                 "DAILY_SOURCE_COMMIT_CLOCK")
    return archived_pdf, meta["committer"]["date"]


def _source_archive(api, custody, cache, *, code=None):
    """Reuse native saved artifact qualification; no issuer acquisition."""
    if "source_import" in custody:
        from . import stock_retained_source_import as imported
        return imported.load(api, code, custody, cache)
    expected = custody["source_artifact"]
    run_id = custody["source_run_id"]
    once.require(type(run_id) is int and run_id > 0, "DAILY_SOURCE_RUN_IDENTITY")
    run = api.get("actions/runs/" + str(run_id))
    once.require(run["id"] == run_id and run["path"] == ".github/workflows/stock-business-research.yml"
                 and run.get("repository", {}).get("full_name") == once.REPO
                 and run.get("head_repository", {}).get("full_name") == once.REPO
                 and run["head_branch"] == "main" and run["event"] == "workflow_dispatch"
                 and run["run_attempt"] == 1 and run["status"] == "completed"
                 and run["conclusion"] in {"success", "failure"}
                 and run["head_sha"] == expected["head_sha"] and reading.SHA.fullmatch(run["head_sha"]),
                 "DAILY_SOURCE_RUN_IDENTITY")
    listing = api.get(f"actions/runs/{run_id}/artifacts?per_page=100")
    once.require(len(listing["artifacts"]) == listing["total_count"] <= 100,
                 "DAILY_SOURCE_ARTIFACT_INVENTORY")
    found = [a for a in listing["artifacts"] if a["id"] == expected["id"]]
    once.require(len(found) == 1, "DAILY_SOURCE_ARTIFACT_UNAVAILABLE")
    artifact = found[0]
    once.require(all(artifact[k] == expected[k] for k in ("id", "name", "size_in_bytes", "digest"))
                 and artifact["name"] in {f"stock-source-preparation-{run_id}-1", f"stock-business-research-{run_id}-1"}
                 and not artifact.get("expired", True)
                 and artifact["workflow_run"]["id"] == run_id
                 and artifact["workflow_run"]["head_sha"] == run["head_sha"], "DAILY_SOURCE_ARTIFACT_IDENTITY")
    key = (artifact["id"], artifact["digest"])
    if key not in cache:
        cache[key] = reading.unpack_archive(api.archive(artifact), artifact, run)
    return cache[key]


def bind(api, request, q, packet, context, clock, *, archives=None):
    """Check complete saved batch review and original public PDF bytes, locally.

    Never fetch issuer websites or send batch/custody bodies to the model. The
    metadata reader stays at512KiB; PDF bytes use the existing32MiB total budget.
    """
    once.require(all(c["mode"] == "STATIC" and c["planned_queries"] == []
                     for c in q["required_classes"]), "DAILY_REQUIRES_DECLARED_STATIC_SOURCES")
    rs = q["reading_source"]
    selected_clock = lambda: packet.selected_at.isoformat()
    state = identity._json(identity._checked_source(rs, lambda s: api.file(s["path"], s["ref"])))
    reading.validate_read_package(state)
    stock = state["lanes"]["stock"]["last_qualified_result"]
    origin = stock["archive"]["origin_run"]
    run = api.get("actions/runs/" + str(origin["id"]))
    reading.run_identity(run, "stock", success=True)
    once.require(reading.concise_run(run) == origin
                 and stock["validation"] == "EXISTING_PURE_READING_VALIDATOR_AND_CAPTURE_INVENTORY_NOT_NEW_LIVE_RUN",
                 "DAILY_STOCK_SAVED_QUALIFICATION")
    spec = stock["details"]["reading/stock-reading.json"]
    raw = api.file(reading.safe_path(spec["read_path"]), rs["ref"])
    once.require(len(raw) <= identity.MAX_BYTES, "DAILY_STOCK_DETAIL_SIZE")
    observations, status = reader._saved_stock_observations(
        SimpleNamespace(files={spec["read_path"]: raw}), state)
    rows = stock["dispositions"]
    once.require([r["thscode"] for r in rows] == list(observations)
                 and len(rows) == stock["coverage"]["planned_issuers"]
                 and all(all(observations[r["thscode"]].get(k) == v for k, v in r.items()) for r in rows),
                 "DAILY_STOCK_FULL_SCOPE_DIFFERS")
    selected = observations[packet.case_id]
    once.require(selected["eligible_for_shadow_reading"] is True
                 and selected["status"] == "CONTRACT_CHECKED_RAW_READING"
                 and selected["input_failure"] is None and not selected["excluded_reasons"],
                 "DAILY_STOCK_SELECTED_ROW_UNQUALIFIED")
    detail_source = once.source_ref(spec["read_path"], rs["ref"], raw, "SAVED_STOCK_BATCH_ORIGIN")
    once.require(any(o["qualification"] == "QUALIFIED_FOR_DECLARED_SCOPE"
                     and all(o["source"].get(k) == detail_source[k] for k in
                             ("repository", "ref", "path", "git_blob", "sha256"))
                     and o["observed_at"] == stock["observed_at"] for o in q["origins"]),
                 "DAILY_QUESTION_ORIGIN_NOT_SAVED_BATCH")
    market_day = stock["market_session"]
    once.require(date.fromisoformat(market_day).isoformat() == market_day
                 and POLICY["first_market_session"] <= market_day <= admission.clock(clock()).date().isoformat(),
                 "DAILY_MARKET_SESSION_OUTSIDE_SCOPE")
    scope = reader.stock_review_scope(state, observations, status)
    review_raw, saved_at = _source(api, request["batch_review_source"], EXTRA_SOURCES["batch_review_source"], selected_clock)
    review = identity._json(review_raw)
    once.require(set(review) == {"reading_source", "question_source", "batch_id", "reviewed_at", "items"}
                 and review["reading_source"] == rs and review["question_source"] == request["question_source"]
                 and review["batch_id"] == scope["batch_id"]
                 and admission.clock(review["reviewed_at"]) <= admission.clock(saved_at)
                 and [r["thscode"] for r in review["items"]] == [r["thscode"] for r in rows]
                 and all(set(r) == {"thscode", "disposition", "reason"}
                         and r["disposition"] in REVIEW_DISPOSITIONS and admission.text(r["reason"])
                         for r in review["items"])
                 and [r["thscode"] for r in review["items"] if r["disposition"] == "SELECTED_NEW_DISTINCT_QUESTION"]
                 == [packet.case_id], "DAILY_FULL_BATCH_REVIEW_REQUIRED")
    custody_raw, saved_at = _source(api, request["source_custody_source"], EXTRA_SOURCES["source_custody_source"], selected_clock)
    custody = identity._json(custody_raw)
    docs = context["issuer_documents"]
    once.require(set(context) == {"issuer_documents", "source_limitations"}
                 and custody["context"] == request["context_source"]
                 and custody["ticker"] == packet.ticker
                 and admission.clock(custody["checked_at"]) <= admission.clock(saved_at)
                 and len(docs) == len(custody["documents"]) <= POLICY["max_documents"],
                 "DAILY_PUBLIC_CONTEXT_OR_CUSTODY_SCOPE")
    inventory_raw, _ = _source(api, custody["inventory_source"], "RETAINED_CNINFO_ISSUER_INVENTORY", selected_clock)
    journal_raw, _ = _source(api, custody["journal_source"], "RETAINED_CNINFO_SOURCE_JOURNAL", selected_clock)
    inventory, journal = identity._json(inventory_raw), identity._json(journal_raw)
    archive_files = _source_archive(api, custody, {} if archives is None else archives, code=packet.code_commit)
    source_prefix = packet.case_id + "/sources/"
    once.require(archive_files[source_prefix + "inventory.json"] == inventory_raw
                 and archive_files[source_prefix + "source-journal.json"] == journal_raw,
                 "DAILY_SOURCE_ARTIFACT_COPIES_DIFFER")
    once.require(inventory["stock_code"] == packet.ticker and admission.text(inventory["org_id"])
                 and isinstance(inventory["announcements"], list)
                 and isinstance(journal["body_events"], list), "DAILY_SOURCE_INVENTORY_IDENTITY")
    refs, total = list(packet.source_refs), 0
    for doc, record in zip(docs, custody["documents"], strict=True):
        doc_fields = {"announcement_id", "title", "source_locator", "pdf_sha256", "published_at",
                      "retrieved_at", "page_count", "reading_method", "page_reading", "pages"}
        once.require(doc_fields <= set(doc) <= doc_fields | {"original_text_sha256"}
                     and doc["reading_method"] == "ORIGINAL_PYPDF" and doc["page_reading"] is None,
                     "DAILY_ORIGINAL_PDF_REPRESENTATION_REQUIRED")
        locator = urlsplit(doc["source_locator"])
        once.require(locator.scheme == "https" and locator.netloc == "static.cninfo.com.cn"
                     and not locator.query and not locator.fragment
                     and re.fullmatch(r"/finalpage/\d{4}-\d{2}-\d{2}/[0-9]+\.[Pp][Dd][Ff]", locator.path)
                     and PurePosixPath(locator.path).stem == doc["announcement_id"]
                     and record["announcement_id"] == doc["announcement_id"], "DAILY_PUBLIC_CNINFO_PDF_REQUIRED")
        announcements = [r for r in inventory["announcements"] if r["announcement_id"] == doc["announcement_id"]]
        events = [r for r in journal["body_events"] if r["announcement_id"] == doc["announcement_id"]]
        once.require(len(announcements) == len(events) == 1, "DAILY_SOURCE_ACQUISITION_AMBIGUOUS")
        announced, captured = announcements[0], events[0]
        once.require(announced["stock_code"] == packet.ticker and announced["org_id"] == inventory["org_id"]
                     and all(announced[k] == doc[k] for k in ("title", "source_locator", "published_at"))
                     and captured["status"] == "FORMAT_AND_IDENTITY_CHECKED_NOT_TRUTH"
                     and all(captured[k] == doc[k] for k in ("source_locator", "pdf_sha256"))
                     and captured["bytes"] == record["bytes"]
                     and admission.clock(captured["captured_at"]) <= admission.clock(doc["retrieved_at"])
                     <= admission.clock(captured["finished_at"]) <= admission.clock(custody["checked_at"]),
                     "DAILY_SOURCE_ACQUISITION_BINDING_DIFFERS")
        from .stock_source_successor import _saved_document
        _, _, saved_pdf, extraction = _saved_document(
            SimpleNamespace(files=archive_files), packet.case_id, doc["announcement_id"])
        pdf, pdf_saved = _retained_pdf(api, record["pdf_source"], saved_pdf, record["bytes"], selected_clock)
        once.require(pdf == saved_pdf and extraction["pages"] == doc["pages"],
                     "DAILY_SOURCE_ARTIFACT_DOCUMENT_DIFFERS")
        completed = [r for r in journal["completed_reads"] if r["identity"] == packet.ticker + ":" + doc["announcement_id"]]
        once.require(len(completed) == 1 and completed[0]["authority"] == "PRIMARY"
                     and completed[0]["kind"] == "BODY" and completed[0]["succeeded"] is True
                     and completed[0]["locator"] == doc["source_locator"]
                     and completed[0]["body_sha256"] == doc["pdf_sha256"], "DAILY_PRIMARY_READ_RECEIPT_REQUIRED")
        total += len(pdf)
        once.require(type(record["bytes"]) is int and len(pdf) == record["bytes"]
                     and once.sha(pdf) == record["pdf_sha256"] == doc["pdf_sha256"]
                     and total <= POLICY["max_pdf_bytes"]
                     and admission.clock(pdf_saved) <= admission.clock(custody["checked_at"]),
                     "DAILY_RETAINED_PDF_IDENTITY_OR_SIZE")
        parsed = extract_pdf_text(pdf, max_pdf_bytes=POLICY["max_pdf_bytes"], max_pages=500,
                                  max_extracted_chars=POLICY["max_context_bytes"])
        once.require(parsed.page_count == record["page_count"] == doc["page_count"], "DAILY_PDF_PAGES_DIFFER")
        once.require(packet.ticker in "".join(p.text for p in parsed.pages[:10])
                     and doc.get("original_text_sha256", parsed.text_sha256) == parsed.text_sha256,
                     "DAILY_PRINTED_ISSUER_IDENTITY_OR_EXTRACTION_DIFFERS")
        once.require(doc["pages"] == [{"page_number": p.page_number, "text": p.text} for p in parsed.pages],
                     "DAILY_PDF_TEXT_DIFFERS")
        refs.append(record["pdf_source"])
    if "source_import" in custody:
        from .stock_retained_source_import import IMPORTS_PATH
        refs.append(once.source_ref(IMPORTS_PATH, packet.code_commit, api.file(IMPORTS_PATH, packet.code_commit),
                                   "REVIEWED_RETAINED_SOURCE_IMPORT"))
    refs.extend(request[k] for k in EXTRA_SOURCES)
    refs.extend(custody[k] for k in ("inventory_source", "journal_source"))
    packet = ExternalResearchInputPacket.model_validate({**packet.model_dump(mode="json"),
        "source_refs": [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in refs]})
    return packet, state, {"market_session": market_day, "batch_id": scope["batch_id"],
        "source_run_id": origin["id"], "reading_source": rs, "reading_hash": state["reading_hash"],
        "batch_review_source": request["batch_review_source"], "reviewed_items": review["items"],
        "source_custody_source": request["source_custody_source"], "pdf_bytes": total,
        "source_proof": "RETAINED_PDF_BYTES_AND_PAGES_NOT_ISSUER_OR_ECONOMIC_TRUTH_CERTIFICATION"}


def work_tree(api):
    from .current_state_delivery import GitHubReadError
    from .stock_research_host import head
    try:
        commit = head(api, intake.WORK_REF)
    except GitHubReadError as exc:
        if str(exc) != "GitHub HTTP 404":
            raise
        return None, {}
    tree = api.get("git/trees/" + commit + "?recursive=1")
    once.require(tree.get("truncated") is False and isinstance(tree.get("tree"), list)
                 and len(tree["tree"]) <= 5000, "DAILY_WORK_TREE_INCOMPLETE")
    rows = {r["path"]: r for r in tree["tree"] if r["type"] != "tree"}
    once.require(len(rows) == sum(r["type"] != "tree" for r in tree["tree"]), "DAILY_WORK_TREE_DUPLICATE")
    return commit, rows


def capacity(api, commit, rows, state, packet):
    """Reserve the original reader's32 files/8 executions against the real tree.

    This is a pre-spend representation check, not a future publisher success
    receipt; the publisher retains its own original API and byte checks.
    """
    groups, files, declarations, current_names = set(), set(), set(), set()
    for path, row in rows.items():
        if not path.startswith(reader.PREFIX):
            continue
        parts = path[len(reader.PREFIX):].split("/")
        once.require((len(parts) == 2 or len(parts) == 3 and parts[1] == reader.CHILD)
                     and re.fullmatch(r"[0-9a-f]{64}", parts[0])
                     and re.fullmatch(r"[A-Za-z0-9_-]+\.(?:json|md|txt)", parts[-1])
                     and row["mode"] == "100644" and row["type"] == "blob"
                     and type(row.get("size")) is int and 0 <= row["size"] <= identity.MAX_BYTES
                     and reading.SHA.fullmatch(row.get("sha", "")),
                     "DAILY_QUESTION_TREE_INVALID")
        groups.add(path.rsplit("/", 1)[0] + "/")
        if parts[-1] in reader.CORE:
            files.add((row["sha"], parts[-1]))
            if path == packet.candidate_output_prefix + parts[-1]:
                current_names.add(parts[-1])
        if parts[-1] == "prepare.json":
            raw = api.file(path, commit)
            once.require(len(raw) == row["size"] and once.blob(raw) == row["sha"], "DAILY_PREPARE_BYTES_DIFFER")
            source = identity._json(raw)["question_source"]
            declarations.add((source["ref"], source["path"], source["git_blob"], source["sha256"]))
    # The original legacy reader selects these exact four files for current
    # qualified securities, including their existing recovery/successor children.
    codes = [r["thscode"] for r in state["lanes"]["stock"]["last_qualified_result"]["dispositions"]
             if r["status"] == "CONTRACT_CHECKED_RAW_READING" and r.get("input_failure") is None and intake.supported(r["thscode"])]
    legacy_rows = intake.inventory(api, commit) if commit is not None else {}
    for code in codes:
        prefix = intake.execution(code)[1]
        for path, row in legacy_rows.items():
            if path.startswith(prefix) and PurePosixPath(path).name in {"prepare.json", "candidate.json", "input.json", "failure.json"}:
                once.require(row["type"] == "blob" and row["mode"] == "100644"
                             and type(row.get("size")) is int and 0 <= row["size"] <= identity.MAX_BYTES,
                             "DAILY_LEGACY_TREE_INVALID")
                files.add((row["sha"], PurePosixPath(path).name))
    is_new = packet.candidate_output_prefix not in groups
    source = next(r for r in packet.source_refs if r.purpose == "REVIEWED_RADAR_QUESTION")
    declaration = (source.ref, source.path, source.git_blob, source.sha256)
    once.require(len(groups) + int(is_new) <= reader.MAX_EXECUTIONS
                 and len(files) + len(declarations) + len(reader.CORE - current_names)
                 + int(declaration not in declarations)
                 <= stock_reader.MAX_STOCK_SOURCE_FILES, "DAILY_READING_CAPACITY_UNAVAILABLE")


def reservation_plan(api, commit, rows, scope, *, reserved=False):
    slots, days = {}, {}
    for path, row in rows.items():
        if not path.startswith(PREFIX):
            continue
        match = re.fullmatch(re.escape(PREFIX) + r"(slots/(0[1-9]|10)|days/(\d{4}-\d{2}-\d{2}))/prepare.json", path)
        once.require(match is not None and row["type"] == "blob" and row["mode"] == "100644"
                     and type(row.get("size")) is int and row["size"] <= identity.MAX_BYTES,
                     "DAILY_RESERVATION_TREE_INVALID")
        raw = api.file(path, commit)
        once.require(len(raw) == row["size"] and once.blob(raw) == row["sha"], "DAILY_RESERVATION_BYTES_DIFFER")
        marker = identity._json(raw)
        once.require(marker["policy"] == POLICY and date.fromisoformat(marker["market_session"]).isoformat()
                     == marker["market_session"]
                     and re.fullmatch(r"stock-question-[0-9a-f]{64}", marker["execution_id"]),
                     "DAILY_RESERVATION_INVALID")
        if match[2]:
            slots[int(match[2])] = marker
        else:
            once.require(match[3] == marker["market_session"], "DAILY_DAY_BINDING_DIFFERS")
            days[match[3]] = marker
    once.require(set(slots) == set(range(1, len(slots) + 1))
                 and len({m["market_session"] for m in slots.values()}) == len(slots)
                 and all(any(m == d for m in slots.values()) for d in days.values()), "DAILY_RESERVATION_HISTORY_INCOMPLETE")
    if reserved:
        own = [m for m in slots.values() if m["market_session"] == scope["market_session"]]
        once.require(len(own) == 1 and own[0]["execution_id"] == scope["execution_id"]
                     and days.get(scope["market_session"]) == own[0]
                     and len(slots) <= POLICY["max_market_days"], "DAILY_RESERVATION_NOT_OWNED")
        return None
    # A slot saved before an interrupted day/question save already consumes its
    # market day. Concurrent callers compete for the same next create-only slot.
    once.require(scope["market_session"] not in {m["market_session"] for m in slots.values()}, "DAILY_MARKET_DAY_ALREADY_CONSUMED")
    once.require(scope["execution_id"] not in {m["execution_id"] for m in slots.values()}, "DAILY_QUESTION_ALREADY_RESERVED")
    once.require(len(slots) < POLICY["max_market_days"], "DAILY_MARKET_DAY_LIMIT_REACHED")
    return PREFIX + f"slots/{len(slots) + 1:02}/", PREFIX + "days/" + scope["market_session"] + "/"
