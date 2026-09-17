"""Retry only the optional Disclosure-work projection with separate capacity views.

This is a read-only capacity separation, not a larger baseline budget, retry of
Research execution, or acceptance/promotion of retained work. The base Collector
still owns its unchanged 180-call / 60-source limits. When this helper is reached
inside the already-accepted Stock optional-reading stage, the underlying GitHubAPI
may already expose up to the existing +72-call envelope. A narrow accounting view
lets the reused Disclosure reader consume only that pre-existing optional reserve;
the underlying API keeps the real counter and hard max. Retained-byte and source
semantics remain unchanged.
"""
from __future__ import annotations

from copy import deepcopy
import json

from . import current_state_delivery as delivery

_SOURCE_BUDGET_CODE = "SOURCE_FILE_BUDGET"
_GAP = "RESEARCH_WORK_READ_UNAVAILABLE_NOT_QUIET"
# Reuse the already-accepted Stock optional-reading extension. This helper may use
# less when the underlying API exposes less, but must never invent a larger budget.
_EXISTING_OPTIONAL_API_EXTENSION = 72


class _OptionalApiAccountingView:
    """Forward all I/O to the exact API while rebasing only its visible call count.

    The wrapped GitHubAPI still increments and enforces its real `max_calls`. The
    legacy Disclosure reader has hard-coded base-180 reserve checks; subtracting at
    most the pre-authorized extension makes those checks algebraically equivalent to
    the underlying optional max without changing the shared Collector constant.
    """

    def __init__(self, api, extension: int):
        if (type(extension) is not int or extension < 0
                or extension > _EXISTING_OPTIONAL_API_EXTENSION):
            raise ValueError("invalid optional Disclosure API extension")
        exposed = getattr(api, "max_calls", delivery.MAX_API_CALLS)
        if type(exposed) is not int or exposed < delivery.MAX_API_CALLS + extension:
            raise ValueError("optional Disclosure API extension exceeds underlying bound")
        self._api = api
        self._extension = extension

    @property
    def calls(self):
        actual = getattr(self._api, "calls", None)
        if type(actual) is not int or actual < 0:
            return actual
        # For actual < extension, zero is the correct conservative base-lane view:
        # any <=180 forecast then remains <= actual+180 < extension+180.
        return max(0, actual - self._extension)

    @property
    def max_calls(self):
        return delivery.MAX_API_CALLS

    def __getattr__(self, name):
        return getattr(self._api, name)


def _available_optional_extension(api) -> int:
    """Use only extra capacity already present on the exact underlying API."""
    exposed = getattr(api, "max_calls", delivery.MAX_API_CALLS)
    if type(exposed) is not int or exposed <= delivery.MAX_API_CALLS:
        return 0
    return min(_EXISTING_OPTIONAL_API_EXTENSION, exposed - delivery.MAX_API_CALLS)


def _retry_failure(baseline: dict, research: dict, candidate: dict, collector,
                   exc: Exception, *, actual_api) -> dict:
    """Keep the original visible gap and add only a safe second-attempt diagnostic."""
    updated = deepcopy(baseline)
    updated_research = deepcopy(research)
    updated_candidate = deepcopy(candidate)
    updated_candidate["separate_capacity_retry"] = {
        "status": "UNAVAILABLE_OR_REJECTED",
        "error_type": type(exc).__name__,
        "diagnostic": delivery.research_work_diagnostic(
            exc,
            api_calls=getattr(actual_api, "calls", None),
            source_count=len(collector.sources),
            retained_file_count=len(collector.files),
        ),
        "meaning": "OPTIONAL_READ_RETRY_DIAGNOSTIC_ONLY_NOT_RESEARCH_EXECUTION_OR_ACCEPTANCE",
    }
    updated_research["candidate_work"] = updated_candidate
    updated["research"] = updated_research
    return updated


def retry_if_source_budget(collector, baseline: dict) -> dict:
    """Retry the same reader only after its exact source-cap rejection.

    Source capacity is isolated exactly as in #370. If the caller's underlying API
    already has the accepted optional extension, expose that bounded accounting
    view only for this retry. A failed retry remains a visible gap and now records
    the safe static rejection code rather than silently collapsing back to the first
    SOURCE_FILE_BUDGET diagnostic.
    """
    research = baseline.get("research")
    if not isinstance(research, dict):
        return baseline
    candidate = research.get("candidate_work")
    if not isinstance(candidate, dict):
        return baseline
    diagnostic = candidate.get("diagnostic")
    if not (candidate.get("status") == "UNAVAILABLE_OR_REJECTED"
            and isinstance(diagnostic, dict) and diagnostic.get("code") == _SOURCE_BUDGET_CODE):
        return baseline

    try:
        registry_raw, _ = collector.source({"path": delivery.REGISTRY_PATH})
        registry = json.loads(registry_raw)
        config = registry.get("research_work_read")
        if not isinstance(config, dict):
            return baseline
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError,
            json.JSONDecodeError):
        return baseline

    baseline_sources = collector.sources
    actual_api = collector.api
    extension = _available_optional_extension(actual_api)
    collector.sources = {}
    if extension:
        collector.api = _OptionalApiAccountingView(actual_api, extension)
    try:
        work = collector.research_work(config)
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError) as exc:
        # Collector.research_work has already rolled back this invocation's files
        # and sources. Preserve the original first rejection plus a finite retry
        # diagnostic; never stringify arbitrary exception/source text.
        return _retry_failure(baseline, research, candidate, collector, exc, actual_api=actual_api)
    finally:
        collector.api = actual_api
        collector.sources = baseline_sources
    if not isinstance(work, dict) or work.get("status") != "READ_OK":
        exc = ValueError("research work retry returned non-READ_OK result")
        return _retry_failure(baseline, research, candidate, collector, exc, actual_api=actual_api)

    updated = deepcopy(baseline)
    updated_research = deepcopy(research)
    updated_research["candidate_work"] = work
    removed = False
    gaps = []
    for gap in updated_research.get("gaps", []):
        if (not removed and isinstance(gap, dict) and gap.get("status") == _GAP
                and gap.get("error_type") == candidate.get("error_type")):
            removed = True
            continue
        gaps.append(gap)
    updated_research["gaps"] = gaps
    updated["research"] = updated_research
    return updated