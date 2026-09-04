from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from decision_kernel.adapters.hithink_index import normalize_hithink_industry_catalog
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.sector_breadth import (
    SectorConstituentIdentity,
    normalize_sector_membership,
)
from decision_kernel.runtime.sector_parent_hints import (
    load_sector_parent_hints,
    parse_sector_parent_hints,
    revalidate_current_sector_parent_hint,
    sector_parent_hint_for_child,
    validate_sector_parent_hint_catalog,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
CAPTURED = datetime(2026, 9, 5, 0, 10, tzinfo=SHANGHAI)


def catalog(items=None):
    return normalize_hithink_industry_catalog(
        {
            "code": 0,
            "data": {
                "timestamp": 1788540000000,
                "item": items
                or [
                    {"thscode": "881101.TI", "name": "种植业与林业"},
                    {"thscode": "881102.TI", "name": "养殖业"},
                    {"thscode": "884001.TI", "name": "种子生产"},
                    {"thscode": "884275.TI", "name": "生猪养殖"},
                ],
            },
        }
    )


def synthetic_payload() -> dict:
    current_catalog = catalog()
    payload = {
        "schema_version": 1,
        "captured_at": "2026-09-04T16:00:00+00:00",
        "membership_capture_window": {
            "start": "2026-09-05T00:00:01+08:00",
            "end": "2026-09-05T00:20:00+08:00",
        },
        "source": "HiThink Financial-API current industry constituents",
        "source_workflow_run_id": 1,
        "source_artifact_id": 2,
        "source_artifact_digest": "sha256:" + "a" * 64,
        "source_result_hash": "b" * 64,
        "catalog_hash": current_catalog.catalog_hash,
        "catalog_shape": {"broad_881": 2, "granular_884": 2},
        "mapping_result": {
            "unique_full_containment": 2,
            "ambiguous": 0,
            "unmapped": 0,
            "exact_duplicate_granular_member_sets": 0,
            "overlapping_broad_member_sets": 0,
            "parents_with_granular_children": 2,
            "broad_parents_without_granular_children": 0,
        },
        "parent_hints": [
            {
                "child_thscode": "884001.TI",
                "child_name": "种子生产",
                "child_member_count_at_capture": 1,
                "child_constituent_set_hash_at_capture": "c" * 64,
                "child_membership_captured_at": "2026-09-05T00:10:00+08:00",
                "parent_thscode": "881101.TI",
                "parent_name": "种植业与林业",
                "parent_member_count_at_capture": 2,
                "parent_constituent_set_hash_at_capture": "d" * 64,
                "parent_membership_captured_at": "2026-09-05T00:05:00+08:00",
                "intersection_count_at_capture": 1,
                "child_fully_contained_at_capture": True,
            },
            {
                "child_thscode": "884275.TI",
                "child_name": "生猪养殖",
                "child_member_count_at_capture": 1,
                "child_constituent_set_hash_at_capture": "e" * 64,
                "child_membership_captured_at": "2026-09-05T00:12:00+08:00",
                "parent_thscode": "881102.TI",
                "parent_name": "养殖业",
                "parent_member_count_at_capture": 2,
                "parent_constituent_set_hash_at_capture": "f" * 64,
                "parent_membership_captured_at": "2026-09-05T00:06:00+08:00",
                "intersection_count_at_capture": 1,
                "child_fully_contained_at_capture": True,
            },
        ],
        "use_semantics": {
            "purpose": "CURRENT_PARENT_HINT_FOR_CANDIDATE_TIME_REVALIDATION",
            "catalog_rule": (
                "CURRENT_CATALOG_IDENTITY_AND_HASH_MUST_BE_CHECKED_EXPLICITLY"
            ),
            "membership_rule": (
                "FETCH_CANDIDATE_CHILD_AND_HINTED_PARENT_CURRENT_MEMBERSHIPS_"
                "AND_REVALIDATE_FULL_CONTAINMENT_BEFORE_GROUPING"
            ),
            "failure_rule": (
                "CATALOG_OR_CONTAINMENT_DRIFT_REMAINS_VISIBLE_AND_PREVENTS_"
                "AUTOMATIC_GROUPING"
            ),
            "historical_taxonomy_authority": "NONE",
            "research_authority": "NONE",
            "human_attention_authority": "NONE",
            "investment_authority": "NONE",
        },
    }
    payload["mapping_hash"] = canonical_hash(payload)
    return payload


def membership(code: str, name: str, members: tuple[str, ...]):
    return normalize_sector_membership(
        sector_thscode=code,
        sector_name=name,
        captured_at=CAPTURED,
        members=tuple(
            SectorConstituentIdentity(
                thscode=member,
                ticker=member[:6],
                name=member,
            )
            for member in members
        ),
    )


def test_committed_parent_hint_file_parses_and_exposes_known_mapping() -> None:
    hints = load_sector_parent_hints(
        Path("radar_inputs/sector-parent-hints-2026-09-05.json")
    )

    assert hints.broad_count == 90
    assert hints.granular_count == 230
    assert len(hints.hints) == 230
    marine = sector_parent_hint_for_child(hints, child_thscode="884183.ti")
    assert marine.child_name == "航海装备"
    assert marine.parent_thscode == "881166.TI"
    assert marine.parent_name == "军工装备"
    assert hints.historical_taxonomy_authority == "NONE"
    assert hints.human_attention_authority == "NONE"
    assert hints.investment_authority == "NONE"


def test_mapping_hash_and_exact_schema_fail_closed() -> None:
    payload = synthetic_payload()
    payload["parent_hints"][0]["child_name"] = "被篡改"
    with pytest.raises(ValueError, match="mapping hash mismatch"):
        parse_sector_parent_hints(json.dumps(payload, ensure_ascii=False))

    payload = synthetic_payload()
    payload["unexpected"] = True
    payload["mapping_hash"] = canonical_hash(
        {key: value for key, value in payload.items() if key != "mapping_hash"}
    )
    with pytest.raises(ValueError, match="fields disagree"):
        parse_sector_parent_hints(json.dumps(payload, ensure_ascii=False))


def test_exact_current_catalog_must_match_frozen_hint_catalog() -> None:
    hints = parse_sector_parent_hints(
        json.dumps(synthetic_payload(), ensure_ascii=False)
    )
    validated = validate_sector_parent_hint_catalog(hints=hints, catalog=catalog())

    assert validated.validated_child_count == 2
    assert validated.current_catalog_hash == hints.catalog_hash
    assert validated.historical_taxonomy_authority == "NONE"

    changed_catalog = catalog(
        [
            {"thscode": "881101.TI", "name": "种植业与林业"},
            {"thscode": "881102.TI", "name": "养殖业（变更）"},
            {"thscode": "884001.TI", "name": "种子生产"},
            {"thscode": "884275.TI", "name": "生猪养殖"},
        ]
    )
    with pytest.raises(ValueError, match="catalog hash disagrees"):
        validate_sector_parent_hint_catalog(
            hints=hints,
            catalog=changed_catalog,
        )


def test_candidate_time_revalidation_accepts_membership_drift_if_containment_survives() -> None:
    hints = parse_sector_parent_hints(
        json.dumps(synthetic_payload(), ensure_ascii=False)
    )
    child = membership("884001.TI", "种子生产", ("600001.SH",))
    parent = membership(
        "881101.TI",
        "种植业与林业",
        ("600001.SH", "600002.SH"),
    )

    result = revalidate_current_sector_parent_hint(
        hints=hints,
        catalog=catalog(),
        child_thscode="884001.TI",
        child_membership=child,
        parent_membership=parent,
    )

    assert result.current_parent_link.child_fully_contained is True
    assert result.current_parent_link.parent_thscode == "881101.TI"
    assert result.child_membership_changed_since_hint_capture is True
    assert result.parent_membership_changed_since_hint_capture is True
    assert result.child_member_count_changed_since_hint_capture is False
    assert result.parent_member_count_changed_since_hint_capture is False
    assert result.historical_taxonomy_authority == "NONE"
    assert result.human_attention_authority == "NONE"
    assert result.investment_authority == "NONE"


def test_containment_or_hinted_parent_drift_prevents_automatic_grouping() -> None:
    hints = parse_sector_parent_hints(
        json.dumps(synthetic_payload(), ensure_ascii=False)
    )
    child = membership("884001.TI", "种子生产", ("600001.SH",))
    no_longer_containing_parent = membership(
        "881101.TI",
        "种植业与林业",
        ("600002.SH",),
    )
    with pytest.raises(ValueError, match="no longer fully contained"):
        revalidate_current_sector_parent_hint(
            hints=hints,
            catalog=catalog(),
            child_thscode="884001.TI",
            child_membership=child,
            parent_membership=no_longer_containing_parent,
        )

    different_parent = membership(
        "881102.TI",
        "养殖业",
        ("600001.SH", "600003.SH"),
    )
    with pytest.raises(ValueError, match="not the hinted parent"):
        revalidate_current_sector_parent_hint(
            hints=hints,
            catalog=catalog(),
            child_thscode="884001.TI",
            child_membership=child,
            parent_membership=different_parent,
        )


def test_unknown_child_does_not_trigger_parent_search() -> None:
    hints = parse_sector_parent_hints(
        json.dumps(synthetic_payload(), ensure_ascii=False)
    )
    with pytest.raises(ValueError, match="no frozen current parent hint"):
        sector_parent_hint_for_child(hints, child_thscode="884999.TI")
