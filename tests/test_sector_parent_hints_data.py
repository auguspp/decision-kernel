from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


DATA = Path("radar_inputs/sector-parent-hints-2026-09-05.json")
BROAD = re.compile(r"^881\d{3}\.TI$")
GRANULAR = re.compile(r"^884\d{3}\.TI$")


def test_frozen_sector_parent_hints_are_complete_and_content_hashed() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    claimed = payload.pop("mapping_hash")
    computed = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    assert claimed == computed
    assert payload["catalog_shape"] == {"broad_881": 90, "granular_884": 230}
    assert payload["mapping_result"] == {
        "ambiguous": 0,
        "broad_parents_without_granular_children": 27,
        "exact_duplicate_granular_member_sets": 0,
        "overlapping_broad_member_sets": 0,
        "parents_with_granular_children": 63,
        "unique_full_containment": 230,
        "unmapped": 0,
    }

    hints = payload["parent_hints"]
    assert len(hints) == 230
    assert len({item["child_thscode"] for item in hints}) == 230
    assert all(GRANULAR.fullmatch(item["child_thscode"]) for item in hints)
    assert all(BROAD.fullmatch(item["parent_thscode"]) for item in hints)
    assert all(item["child_fully_contained_at_capture"] is True for item in hints)
    assert all(
        item["intersection_count_at_capture"]
        == item["child_member_count_at_capture"]
        for item in hints
    )

    semantics = payload["use_semantics"]
    assert semantics["historical_taxonomy_authority"] == "NONE"
    assert semantics["research_authority"] == "NONE"
    assert semantics["human_attention_authority"] == "NONE"
    assert semantics["investment_authority"] == "NONE"
