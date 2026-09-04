from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from decision_kernel.research_funnel import (
    DiscoveryInput,
    DiscoveryObservation,
    DiscoverySource,
    PreResearchResult,
    PreResearchRoute,
    ResearchClaim,
    ResearchClaimKind,
)
from decision_kernel.research_workflow_v1 import ResearchFunnelTerminalState
from decision_kernel.runtime.disclosure_assessment import (
    DisclosureAssessmentPacket,
    parse_disclosure_assessment_packet,
)
from decision_kernel.runtime.disclosure_receipts import (
    DisclosureAssessmentReceipt,
    merge_disclosure_assessment_receipts,
    parse_disclosure_assessment_receipts,
    write_disclosure_assessment_receipts,
)
from decision_kernel.runtime.disclosure_research import (
    DisclosureResearchAssessment,
    run_disclosure_research_assessment,
)


SOURCE_RUN_ID = 33757562673

# These seven dispositions were already reviewed and frozen in the CATL disclosure
# cognition corpus or the exact assessment-artifact live exercise. Keep the exact
# announcement-set identity: file presence or publication date alone is not enough.
REVIEWED_QUIET_RESULTS: dict[
    tuple[str, tuple[str, ...]], ResearchFunnelTerminalState
] = {
    ("300750", ("1225448968",)): ResearchFunnelTerminalState.DROP_FOR_NOW,
    ("300750", ("1225456175",)): ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
    ("300750", ("1225462006",)): ResearchFunnelTerminalState.DROP_FOR_NOW,
    ("300750", ("1225464975",)): ResearchFunnelTerminalState.DROP_FOR_NOW,
    (
        "300750",
        ("1225470687", "1225470688", "1225470689"),
    ): ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
    ("300750", ("1225502236",)): ResearchFunnelTerminalState.DROP_FOR_NOW,
    ("300750", ("1225519101",)): ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
}

EXPECTED_INPUT_HASHES: dict[tuple[str, tuple[str, ...]], str] = {
    ("300750", ("1225448968",)): "ba2ebf17c1f338f044ff0c82ed63fc66843b46321cab0252e2490e9ab494cfca",
    ("300750", ("1225456175",)): "9076b90d4b7b5c36084a6e975e4c46508de0d0d8e618af3d3ed286d9746fa4a8",
    ("300750", ("1225462006",)): "68580c9ddba657bc02083a6e7208f9388a431815598afc265dc5ffafcbfd5998",
    ("300750", ("1225464975",)): "d22eaa83781cca36d00456eff766053577495050c9ef4ba5334636ca5d9c37f5",
    (
        "300750",
        ("1225470687", "1225470688", "1225470689"),
    ): "d5c110be0932b634b250fa4908095dcbbb7c208f100803155b415e7e6e200df6",
    ("300750", ("1225502236",)): "97ce9a01b90840b47edfb585d9b68e2128412f0abbebac2eae281a16a2794656",
    ("300750", ("1225519101",)): "deeeeecd4c76ead88b23a62e274d7c9dfa66c30c118f1c38cad14686601704d8",
    (
        "300750",
        ("1225545968", "1225547099"),
    ): "650fc5cc0c8c0accc3095dffd34cd8ee7346674e4b5a2e7fd525b83dec6c6ecc",
    ("002050", ("1225544315",)): "14436e8e40826d5aa11be2f18d2752efd671c0338d8980f3d0d8c9f57e328c66",
}


def _identity(packet: DisclosureAssessmentPacket) -> tuple[str, tuple[str, ...]]:
    return packet.stock_code, tuple(packet.announcement_ids)


def _lineage(packet: DisclosureAssessmentPacket) -> tuple[DiscoverySource, ...]:
    return tuple(
        DiscoverySource(
            evidence_artifact_id=item.evidence_artifact.id,
            source_locator=item.evidence_artifact.source_locator,
            available_at=item.evidence_artifact.available_at,
        )
        for item in packet.evidence
    )


def _catl_september_assessment(
    packet: DisclosureAssessmentPacket,
) -> DisclosureResearchAssessment:
    evidence_by_announcement = {
        item.announcement_id: item.evidence_artifact for item in packet.evidence
    }
    buyback = evidence_by_announcement["1225545968"]
    discovery_id = "cninfo-refresh-300750-2026-09-03-buyback-progress"
    discovery = DiscoveryInput(
        discovery_id=discovery_id,
        source_lane=packet.source_lane,
        ticker=packet.stock_code,
        economic_direction=(
            "approved capital return versus actual cash deployment, capex and owner cash"
        ),
        as_of=packet.prepared_at,
        factual_observations=(
            DiscoveryObservation(
                statement=(
                    "As of 2026-08-31 CATL had not executed the approved RMB20-40bn "
                    "A-share repurchase."
                ),
                evidence_artifact_ids=(buyback.id,),
            ),
        ),
        source_lineage=_lineage(packet),
        why_now=(
            "The official repurchase-progress batch is newer than the frozen CATL Research."
        ),
        contradiction_or_mapping_warning=(
            "An approved repurchase is a capital-allocation commitment; one month with no "
            "execution does not establish eventual cash deployment or per-share owner benefit."
        ),
        next_discriminating_search=(
            "Wait for later repurchase progress or completion plus operating cash flow and capex."
        ),
        known_stop_or_downgrade_condition=(
            "Keep quiet while the filing only reports non-execution and does not change the "
            "underlying capital-return or owner-cash assessment."
        ),
    )
    pre = PreResearchResult(
        discovery_id=discovery_id,
        as_of=packet.prepared_at,
        what_is_this=(
            "A monthly progress update on an approved repurchase, paired with a routine H-share "
            "securities report."
        ),
        economic_direction=(
            "approved capital return versus actual cash deployment, capex and owner cash"
        ),
        why_surfaced_now=(
            "The official batch post-dates the frozen CATL Research and reports execution status."
        ),
        current_expression_or_leadership=None,
        basic_business_role=(
            "The filing updates capital-allocation execution rather than battery demand, margins "
            "or utilization."
        ),
        potential_fundamental_driver=(
            "A material completed repurchase could improve per-share owner economics, subject to "
            "cash generation, capex and purchase price."
        ),
        current_market_expectation_hypothesis=(
            "The market may already recognize the approved repurchase while remaining uncertain "
            "about actual deployment and cash-conversion durability."
        ),
        material_claims=(
            ResearchClaim(
                statement=(
                    "The approved RMB20-40bn A-share repurchase had not been executed as of "
                    "2026-08-31."
                ),
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(buyback.id,),
            ),
        ),
        obvious_contradiction=(
            "The capital-return commitment exists, but no repurchase cash had yet been deployed."
        ),
        largest_unknown=(
            "How much of the approved repurchase will actually be executed, at what prices and "
            "funding cost, and how it interacts with capex and future operating cash flow."
        ),
        next_discriminating_search=(
            "Wait for subsequent repurchase progress or completion and the next operating cash "
            "flow and capex evidence."
        ),
        route=PreResearchRoute.WAIT_FOR_TRIGGER,
        route_reason=(
            "The non-execution update is real and relevant to an existing commitment, but it does "
            "not resolve or invalidate the frozen Research questions and does not justify a new "
            "Full Research loop."
        ),
    )
    return DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=pre,
    )


def _sanhua_september_assessment(
    packet: DisclosureAssessmentPacket,
) -> DisclosureResearchAssessment:
    official = packet.evidence[0].evidence_artifact
    discovery_id = "cninfo-refresh-002050-2026-09-03-h-share-return"
    discovery = DiscoveryInput(
        discovery_id=discovery_id,
        source_lane=packet.source_lane,
        ticker=packet.stock_code,
        economic_direction=(
            "no demonstrated change to core thermal-management or new-business owner economics"
        ),
        as_of=packet.prepared_at,
        factual_observations=(
            DiscoveryObservation(
                statement=(
                    "Sanhua published an H-share next-day securities disclosure return; the "
                    "packet is not an operating-results announcement."
                ),
                evidence_artifact_ids=(official.id,),
            ),
        ),
        source_lineage=_lineage(packet),
        why_now="The official H-share filing is newer than the frozen Sanhua Research.",
        contradiction_or_mapping_warning=(
            "A securities disclosure form must not be treated as evidence of robot allocation, "
            "segment margins, owner cash or optionality realization."
        ),
        next_discriminating_search=(
            "No follow-up unless a later filing contains an economically material securities "
            "change or operating evidence tied to a frozen reopen bucket."
        ),
        known_stop_or_downgrade_condition=(
            "Drop when the filing does not change share economics or any current Research reopen "
            "bucket."
        ),
    )
    pre = PreResearchResult(
        discovery_id=discovery_id,
        as_of=packet.prepared_at,
        what_is_this="A routine H-share next-day securities disclosure return.",
        economic_direction=(
            "no demonstrated change to core thermal-management or new-business owner economics"
        ),
        why_surfaced_now="It post-dates the frozen Sanhua Research.",
        current_expression_or_leadership=None,
        basic_business_role=(
            "The form concerns listed-security disclosure mechanics, not operating performance."
        ),
        potential_fundamental_driver=(
            "Only a material share-count or capital-structure change could affect per-share owner "
            "economics; none is established by this packet."
        ),
        current_market_expectation_hypothesis=(
            "The market thesis remains centered on the core franchise and unproven new-business "
            "optionality, not this routine filing."
        ),
        material_claims=(
            ResearchClaim(
                statement=(
                    "The new official filing is an H-share next-day securities disclosure return, "
                    "not an operating-results release."
                ),
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(official.id,),
            ),
        ),
        obvious_contradiction=None,
        largest_unknown="None material to the current frozen Research questions from this filing.",
        next_discriminating_search=(
            "No follow-up unless later primary evidence changes share economics, core margins, "
            "cash conversion, robot economics or capital allocation."
        ),
        route=PreResearchRoute.STOP,
        route_reason=(
            "The filing does not update the core franchise, owner cash, robot operating economics, "
            "liquid-cooling economics or any declared Sanhua reopen bucket."
        ),
    )
    return DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=pre,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    packet_paths = sorted(args.packet_dir.glob("*.json"))
    packets = tuple(
        parse_disclosure_assessment_packet(path.read_text(encoding="utf-8"))
        for path in packet_paths
    )
    packets_by_identity = {_identity(packet): packet for packet in packets}
    if len(packets_by_identity) != len(packets):
        raise SystemExit("duplicate exact disclosure packet identity")
    if set(packets_by_identity) != set(EXPECTED_INPUT_HASHES):
        raise SystemExit(
            "unexpected disclosure packet set: "
            f"actual={sorted(packets_by_identity)} expected={sorted(EXPECTED_INPUT_HASHES)}"
        )
    for identity, expected_hash in EXPECTED_INPUT_HASHES.items():
        if packets_by_identity[identity].assessment_input_hash != expected_hash:
            raise SystemExit(f"assessment input hash changed for {identity}")

    results = dict(REVIEWED_QUIET_RESULTS)
    generated_assessments: dict[
        tuple[str, tuple[str, ...]], DisclosureResearchAssessment
    ] = {}

    catl_identity = ("300750", ("1225545968", "1225547099"))
    catl_assessment = _catl_september_assessment(packets_by_identity[catl_identity])
    catl_result = run_disclosure_research_assessment(
        packet=packets_by_identity[catl_identity], assessment=catl_assessment
    )
    if catl_result.terminal_state is not ResearchFunnelTerminalState.WAIT_FOR_TRIGGER:
        raise SystemExit("CATL September assessment must remain WAIT_FOR_TRIGGER")
    results[catl_identity] = catl_result.terminal_state
    generated_assessments[catl_identity] = catl_assessment

    sanhua_identity = ("002050", ("1225544315",))
    sanhua_assessment = _sanhua_september_assessment(packets_by_identity[sanhua_identity])
    sanhua_result = run_disclosure_research_assessment(
        packet=packets_by_identity[sanhua_identity], assessment=sanhua_assessment
    )
    if sanhua_result.terminal_state is not ResearchFunnelTerminalState.DROP_FOR_NOW:
        raise SystemExit("Sanhua September assessment must remain DROP_FOR_NOW")
    results[sanhua_identity] = sanhua_result.terminal_state
    generated_assessments[sanhua_identity] = sanhua_assessment

    if any(
        result is ResearchFunnelTerminalState.DEEPEN_REQUIRED
        for result in results.values()
    ):
        raise SystemExit("quiet receipt seed cannot contain DEEPEN_REQUIRED")

    existing = ()
    if args.receipts.exists():
        existing = parse_disclosure_assessment_receipts(
            args.receipts.read_text(encoding="utf-8")
        )
    assessed_at = datetime.now(timezone.utc)
    incoming = tuple(
        DisclosureAssessmentReceipt(
            source_lane=packets_by_identity[identity].source_lane,
            stock_code=identity[0],
            announcement_ids=identity[1],
            research_snapshot_id=packets_by_identity[identity].research_snapshot_id,
            research_as_of=packets_by_identity[identity].research_as_of,
            assessment_semantics_id=packets_by_identity[
                identity
            ].assessment_semantics_id,
            assessment_result=result,
            assessed_at=assessed_at,
        )
        for identity, result in sorted(results.items())
    )
    merged = merge_disclosure_assessment_receipts(existing, incoming)
    write_disclosure_assessment_receipts(args.receipts, merged)

    args.audit_dir.mkdir(parents=True, exist_ok=True)
    for identity, assessment in generated_assessments.items():
        stock_code, announcement_ids = identity
        path = args.audit_dir / (
            f"{stock_code}-{'-'.join(announcement_ids)}-assessment.json"
        )
        path.write_text(
            assessment.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

    audit = {
        "schema_version": 1,
        "source_workflow_run_id": SOURCE_RUN_ID,
        "source_packet_count": len(packets),
        "existing_receipt_count": len(existing),
        "incoming_receipt_count": len(incoming),
        "merged_receipt_count": len(merged),
        "deepen_required_count": 0,
        "results": [
            {
                "stock_code": identity[0],
                "announcement_ids": list(identity[1]),
                "assessment_input_hash": packets_by_identity[
                    identity
                ].assessment_input_hash,
                "terminal_state": result.value,
                "provenance": (
                    "generated_exact_assessment"
                    if identity in generated_assessments
                    else "previously_reviewed_quiet_disposition"
                ),
            }
            for identity, result in sorted(results.items())
        ],
        "investment_authority": "NONE",
    }
    (args.audit_dir / "summary.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Disclosure receipt seed",
        "",
        f"Source workflow run: `{SOURCE_RUN_ID}`",
        "",
        f"Exact quiet batches recorded: **{len(incoming)}**",
        "",
        "| Security | Announcement IDs | Result | Provenance |",
        "| --- | --- | --- | --- |",
    ]
    for item in audit["results"]:
        lines.append(
            f"| {item['stock_code']} | {', '.join(item['announcement_ids'])} | "
            f"`{item['terminal_state']}` | {item['provenance']} |"
        )
    lines.extend(
        [
            "",
            "No batch earned `DEEPEN_REQUIRED`.",
            "",
            "Investment Authority = `NONE`.",
            "",
        ]
    )
    (args.audit_dir / "summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )

    print(f"DISCLOSURE RECEIPTS: {len(incoming)} exact quiet batches")
    print(f"MERGED RECEIPTS: {len(merged)}")
    print("DEEPEN_REQUIRED: 0")
    print("INVESTMENT AUTHORITY: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
