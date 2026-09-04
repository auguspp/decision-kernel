from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ARTIFACT = Path("hierarchy-artifact")
RESULT = ARTIFACT / "sector-radar-full-current-hierarchy.json"
CHECKPOINTS = ARTIFACT / "sector-radar-full-current-hierarchy-inputs"
OUTPUT = Path("radar_inputs/sector-parent-hints-2026-09-05.json")
DOC = Path("docs/sector-discovery-radar-full-current-hierarchy-result-2026-09-05.md")

SOURCE_WORKFLOW_RUN_ID = 33894305778
SOURCE_ARTIFACT_ID = 9945768475
SOURCE_ARTIFACT_DIGEST = (
    "sha256:f6471d240ce303b44cda6f1d9558e95c38e50aaf450eca86b2c1fe31dbe35cb4"
)


def canonical_hash(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def load_and_validate_result() -> dict:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    claimed_result_hash = payload.pop("result_hash")
    computed_result_hash = canonical_hash(payload)
    if claimed_result_hash != computed_result_hash:
        raise ValueError("hierarchy result hash mismatch")
    payload["result_hash"] = claimed_result_hash

    expected = {
        "broad_count": 90,
        "granular_count": 230,
        "checkpoint_count": 320,
    }
    for key, value in expected.items():
        if payload["integrity"][key] != value:
            raise ValueError(f"unexpected hierarchy integrity {key}")
    if payload["mapping"] != {
        "ambiguous_count": 0,
        "unique_count": 230,
        "unique_coverage_ratio": "1",
        "unmapped_count": 0,
    }:
        raise ValueError("full unique hierarchy was not established")
    if payload["exact_duplicate_granular_sets"]:
        raise ValueError("unexpected duplicate granular member sets")
    if payload["broad_overlap_controls"]:
        raise ValueError("unexpected current broad-industry overlap")
    return payload


def load_and_validate_checkpoints(payload: dict) -> dict[str, dict]:
    records = payload["acquisition"]["records"]
    if len(records) != 320:
        raise ValueError("expected 320 membership acquisition records")
    by_code = {record["sector_thscode"]: record for record in records}
    if len(by_code) != 320:
        raise ValueError("duplicate membership acquisition identity")

    memberships: dict[str, dict] = {}
    for code, record in by_code.items():
        path = CHECKPOINTS / Path(record["checkpoint_path"]).name
        if not path.exists():
            raise ValueError(f"missing hierarchy checkpoint {code}")
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha != record["checkpoint_sha256"]:
            raise ValueError(f"checkpoint hash mismatch for {code}")
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
        membership = checkpoint["membership"]
        if membership["sector_thscode"] != code:
            raise ValueError(f"checkpoint identity mismatch for {code}")
        memberships[code] = membership
    return memberships


def build_hints(payload: dict, memberships: dict[str, dict]) -> list[dict]:
    hints: list[dict] = []
    for row in payload["granular_to_broad"]:
        if row["mapping_status"] != "UNIQUE_FULL_CONTAINMENT_PARENT":
            raise ValueError("non-unique row found in frozen hierarchy")
        child_code = row["child_thscode"]
        parent = row["selected_unique_parent"]
        parent_code = parent["parent_thscode"]
        child_membership = memberships[child_code]
        parent_membership = memberships[parent_code]
        child_set = {member["thscode"] for member in child_membership["members"]}
        parent_set = {member["thscode"] for member in parent_membership["members"]}
        if not child_set or not child_set <= parent_set:
            raise ValueError(f"containment replay failed for {child_code}")
        if len(child_set) != row["child_member_count"]:
            raise ValueError(f"child count mismatch for {child_code}")
        hints.append(
            {
                "child_thscode": child_code,
                "child_name": row["child_name"],
                "child_member_count_at_capture": len(child_set),
                "child_constituent_set_hash_at_capture": child_membership[
                    "constituent_set_hash"
                ],
                "child_membership_captured_at": child_membership["captured_at"],
                "parent_thscode": parent_code,
                "parent_name": parent["parent_name"],
                "parent_member_count_at_capture": len(parent_set),
                "parent_constituent_set_hash_at_capture": parent_membership[
                    "constituent_set_hash"
                ],
                "parent_membership_captured_at": parent_membership["captured_at"],
                "intersection_count_at_capture": len(child_set),
                "child_fully_contained_at_capture": True,
            }
        )
    hints.sort(key=lambda item: item["child_thscode"])
    if len(hints) != 230 or len({item["child_thscode"] for item in hints}) != 230:
        raise ValueError("frozen parent hint set is incomplete")
    return hints


def write_hint_artifact(payload: dict, hints: list[dict]) -> dict:
    records = payload["acquisition"]["records"]
    capture_times = [
        datetime.fromisoformat(record["membership_captured_at"])
        for record in records
    ]
    parent_counts = Counter(item["parent_thscode"] for item in hints)
    frozen = {
        "schema_version": 1,
        "captured_at": payload["captured_at"],
        "membership_capture_window": {
            "start": min(capture_times).isoformat(),
            "end": max(capture_times).isoformat(),
        },
        "source": payload["source"],
        "source_workflow_run_id": SOURCE_WORKFLOW_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "source_result_hash": payload["result_hash"],
        "catalog_hash": payload["catalog"]["catalog_hash"],
        "catalog_shape": {"broad_881": 90, "granular_884": 230},
        "mapping_result": {
            "unique_full_containment": 230,
            "ambiguous": 0,
            "unmapped": 0,
            "exact_duplicate_granular_member_sets": 0,
            "overlapping_broad_member_sets": 0,
            "parents_with_granular_children": len(parent_counts),
            "broad_parents_without_granular_children": 90 - len(parent_counts),
        },
        "parent_hints": hints,
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
    frozen["mapping_hash"] = canonical_hash(frozen)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return frozen


def write_document(payload: dict, frozen: dict) -> None:
    hints = frozen["parent_hints"]
    parent_counts = Counter(item["parent_thscode"] for item in hints)
    parent_names = {item["parent_thscode"]: item["parent_name"] for item in hints}
    top_parents = sorted(
        parent_counts.items(),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )[:10]
    pressure_codes = {
        "884001.TI",
        "884005.TI",
        "884006.TI",
        "884182.TI",
        "884183.TI",
        "884275.TI",
        "884276.TI",
        "884277.TI",
    }
    pressure = [item for item in hints if item["child_thscode"] in pressure_codes]

    lines = [
        "# Sector Discovery Radar — full current hierarchy result — 2026-09-05",
        "",
        "Status: **CURRENT-PIT HIERARCHY ESTABLISHED / FROZEN PARENT HINTS / CANDIDATE-TIME REVALIDATION REQUIRED / NO HISTORICAL TAXONOMY / NO HUMAN WAKE / NO INVESTMENT AUTHORITY**  ",
        "Repository: `auguspp/decision-kernel`  ",
        "Experiment: PR `#178` — **CLOSED WITHOUT MERGE**",
        "",
        "## Executive result",
        "",
        "The full current formal-industry catalog produced a complete and unambiguous containment hierarchy:",
        "",
        "```text",
        "881 broad industries = 90",
        "884 granular industries = 230",
        "unique 884 -> 881 full-containment mappings = 230 / 230",
        "ambiguous mappings = 0",
        "unmapped granular industries = 0",
        "exact duplicate granular member sets = 0",
        "overlap between distinct broad 881 member sets = 0",
        "```",
        "",
        "This establishes a mechanically viable **current parent hint** for hierarchical Radar composition. It does not establish a permanent or historical taxonomy.",
        "",
        "## Operations lineage",
        "",
        "```text",
        f"workflow run = {SOURCE_WORKFLOW_RUN_ID}",
        f"artifact = {SOURCE_ARTIFACT_ID}",
        f"artifact digest = {SOURCE_ARTIFACT_DIGEST}",
        f"result hash = {payload['result_hash']}",
        f"parent-hint mapping hash = {frozen['mapping_hash']}",
        f"catalog hash = {frozen['catalog_hash']}",
        "qualified current membership checkpoints = 320 / 320",
        (
            "membership capture window = "
            f"{frozen['membership_capture_window']['start']} through "
            f"{frozen['membership_capture_window']['end']}"
        ),
        (
            "transient transport retries = "
            f"{payload['acquisition']['runner_transport_retry_count']}"
        ),
        "HTTP / business-code / adapter / semantic retries = 0",
        "```",
        "",
        "Every checkpoint hash and the final result hash were revalidated before the frozen hint file was generated.",
        "",
        "## Pressure-case mapping",
        "",
        "| Granular child | Broad parent | Members at capture |",
        "| --- | --- | ---: |",
    ]
    for item in pressure:
        lines.append(
            f"| {item['child_name']} `{item['child_thscode']}` | "
            f"{item['parent_name']} `{item['parent_thscode']}` | "
            f"{item['child_member_count_at_capture']} |"
        )
    lines.extend(
        [
            "",
            "## Parent distribution",
            "",
            (
                f"`{len(parent_counts)}` of the 90 broad industries currently have one "
                f"or more granular children; `{90 - len(parent_counts)}` have none in "
                "the formal 884 catalog."
            ),
            "",
            "| Broad parent | Granular children |",
            "| --- | ---: |",
        ]
    )
    for code, count in top_parents:
        lines.append(f"| {parent_names[code]} `{code}` | {count} |")
    lines.extend(
        [
            "",
            "## Production use rule",
            "",
            "The committed mapping is a lookup hint, not taxonomy authority:",
            "",
            "```text",
            "restore frozen child -> parent hint",
            "→ check the current formal-industry catalog explicitly",
            "→ only for a surfaced 884 candidate, fetch that child and hinted 881 parent",
            "→ normalize both exact current memberships",
            "→ require current child members to be fully contained in the hinted parent",
            "→ build the existing current parent link",
            "→ group only after revalidation",
            "```",
            "",
            "If catalog identity or current containment changes, automatic grouping fails visibly. The system must not silently search for a convenient replacement parent or perform a daily 320-membership fan-out.",
            "",
            "## Authority boundary",
            "",
            "```text",
            "current parent hint = Harness routing metadata",
            "historical taxonomy authority = NONE",
            "Fundamental Belief change = NO",
            "Research route = NO",
            "canonical Human wake = NO",
            "Recommendation = NO",
            "Action = NO",
            "Investment Authority = NONE",
            "```",
            "",
            "Central conclusion:",
            "",
            "> **At the current PIT, the formal 884 universe is a clean child partition of the 881 universe. That is strong enough to support deterministic parent-child deduplication, but only when the frozen hint is checked against current candidate memberships before use.**",
            "",
        ]
    )
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    payload = load_and_validate_result()
    memberships = load_and_validate_checkpoints(payload)
    hints = build_hints(payload, memberships)
    frozen = write_hint_artifact(payload, hints)
    write_document(payload, frozen)
    print(f"RESULT_HASH={payload['result_hash']}")
    print(f"MAPPING_HASH={frozen['mapping_hash']}")
    print(f"PARENT_HINTS={len(hints)}")
    print(f"DOC={DOC}")
    print(f"OUTPUT={OUTPUT}")


if __name__ == "__main__":
    main()
