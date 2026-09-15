"""Retry only the optional Disclosure-work projection with its own source registry.

This is a read-only capacity separation, not a larger baseline budget, retry of
Research execution, or acceptance/promotion of retained work. Retained bytes and
GitHub publication/API budgets remain owned by the original Collector.
"""
from __future__ import annotations

from copy import deepcopy
import json

from . import current_state_delivery as delivery

_SOURCE_BUDGET_CODE = "SOURCE_FILE_BUDGET"
_GAP = "RESEARCH_WORK_READ_UNAVAILABLE_NOT_QUIET"


def retry_if_source_budget(collector, baseline: dict) -> dict:
    """Re-run the same retained-work reader only after its exact source-cap rejection."""
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
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, json.JSONDecodeError):
        return baseline

    baseline_sources = collector.sources
    collector.sources = {}
    try:
        work = collector.research_work(config)
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError):
        return baseline
    finally:
        collector.sources = baseline_sources
    if not isinstance(work, dict) or work.get("status") != "READ_OK":
        return baseline

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
