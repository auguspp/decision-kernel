from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from zoneinfo import ZoneInfo

from decision_kernel.runtime.sector_breadth import (
    SectorConstituentIdentity,
    normalize_sector_membership,
)


SCRIPT = Path("experiments/sector_radar_full_current_hierarchy_2026_09_04.py")
CAPTURED = datetime(2026, 9, 4, 16, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "sector_radar_full_current_hierarchy_experiment",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def membership(code: str, name: str, member_codes: tuple[str, ...]):
    return normalize_sector_membership(
        sector_thscode=code,
        sector_name=name,
        captured_at=CAPTURED,
        members=tuple(
            SectorConstituentIdentity(
                thscode=member_code,
                ticker=member_code[:6],
                name=member_code,
            )
            for member_code in member_codes
        ),
    )


def test_granular_maps_to_one_exact_containing_parent() -> None:
    module = load_module()
    broad = (
        membership(
            "881101.TI",
            "种植业与林业",
            ("600001.SH", "600002.SH", "600003.SH"),
        ),
        membership(
            "881102.TI",
            "养殖业",
            ("600004.SH", "600005.SH"),
        ),
    )
    granular = (
        membership(
            "884001.TI",
            "种子生产",
            ("600001.SH", "600002.SH"),
        ),
    )

    row = module.map_granular_to_broad(broad=broad, granular=granular)[0]

    assert row["mapping_status"] == "UNIQUE_FULL_CONTAINMENT_PARENT"
    assert row["selected_unique_parent"]["parent_thscode"] == "881101.TI"
    assert row["selected_unique_parent"]["child_containment"] == 1
    assert row["historical_membership_authority"] == "NONE"


def test_granular_exposes_ambiguous_multiple_full_parents() -> None:
    module = load_module()
    broad = (
        membership(
            "881101.TI",
            "父甲",
            ("600001.SH", "600002.SH", "600003.SH"),
        ),
        membership(
            "881102.TI",
            "父乙",
            ("600001.SH", "600002.SH", "600004.SH"),
        ),
    )
    granular = (
        membership(
            "884001.TI",
            "子行业",
            ("600001.SH", "600002.SH"),
        ),
    )

    row = module.map_granular_to_broad(broad=broad, granular=granular)[0]

    assert row["mapping_status"] == "AMBIGUOUS_MULTIPLE_FULL_CONTAINMENT_PARENTS"
    assert row["selected_unique_parent"] is None
    assert {
        item["parent_thscode"] for item in row["full_containment_parents"]
    } == {"881101.TI", "881102.TI"}


def test_unmapped_granular_retains_ranked_partial_parents() -> None:
    module = load_module()
    broad = (
        membership(
            "881101.TI",
            "父甲",
            ("600001.SH", "600002.SH"),
        ),
        membership(
            "881102.TI",
            "父乙",
            ("600003.SH", "600004.SH"),
        ),
    )
    granular = (
        membership(
            "884001.TI",
            "跨父行业",
            ("600001.SH", "600003.SH", "600005.SH"),
        ),
    )

    row = module.map_granular_to_broad(broad=broad, granular=granular)[0]

    assert row["mapping_status"] == "NO_FULL_CONTAINMENT_PARENT"
    assert row["selected_unique_parent"] is None
    assert len(row["best_partial_parents"]) == 2
    assert {
        item["parent_thscode"] for item in row["best_partial_parents"]
    } == {"881101.TI", "881102.TI"}
    assert all(
        item["child_containment"] == Decimal(1) / Decimal(3)
        for item in row["best_partial_parents"]
    )


def test_exact_duplicate_groups_compare_member_sets_not_sector_identity_hashes() -> None:
    module = load_module()
    granular = (
        membership(
            "884001.TI",
            "细分甲",
            ("600001.SH", "600002.SH"),
        ),
        membership(
            "884002.TI",
            "细分乙",
            ("600002.SH", "600001.SH"),
        ),
        membership(
            "884003.TI",
            "不同集合",
            ("600003.SH",),
        ),
    )

    groups = module.exact_duplicate_groups(granular)

    assert len(groups) == 1
    assert groups[0]["member_count"] == 2
    assert [item["thscode"] for item in groups[0]["industries"]] == [
        "884001.TI",
        "884002.TI",
    ]
    assert len(groups[0]["member_set_hash"]) == 64


def test_broad_overlap_control_is_current_only_and_ranked() -> None:
    module = load_module()
    broad = (
        membership(
            "881101.TI",
            "行业甲",
            ("600001.SH", "600002.SH", "600003.SH"),
        ),
        membership(
            "881102.TI",
            "行业乙",
            ("600001.SH", "600002.SH", "600004.SH"),
        ),
        membership(
            "881103.TI",
            "行业丙",
            ("600001.SH", "600005.SH"),
        ),
    )

    rows = module.broad_overlap_controls(broad)

    assert rows[0]["intersection_count"] == 2
    assert rows[0]["jaccard"] == Decimal(1) / Decimal(2)
    assert {
        rows[0]["left_thscode"],
        rows[0]["right_thscode"],
    } == {"881101.TI", "881102.TI"}
