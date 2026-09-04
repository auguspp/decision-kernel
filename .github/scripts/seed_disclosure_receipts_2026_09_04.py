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


SOURCE_RUN_ID = 33844850684

EXPECTED_INPUT_HASHES: dict[tuple[str, tuple[str, ...]], str] = {
    (
        "601088",
        ("1225546775", "1225546779"),
    ): "dd413682fb3b6502b1c79c2269b04864bc47f9ca2bd403534aa2b812f8a7768a",
    (
        "603986",
        ("1225546905",),
    ): "75c8b91f8e9223d801b416e3392def7af0f8568c640010212fdefc3121e1e6a7",
}

EXPECTED_CONTENT_HASHES: dict[str, str] = {
    "1225546775": "86514cc6996d65e8f410742b280d8532a164726f96d36390f73e253574896d86",
    "1225546779": "93c49e799e4e2767f78c74c10b36484fa746f6b8aa945e6f1fb7293150275311",
    "1225546905": "75d5b858c42b10c22a4046e0264b835c15b15b4156b2dfaf9b1e8791cc7191f8",
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


def _shenhua_assessment(
    packet: DisclosureAssessmentPacket,
) -> DisclosureResearchAssessment:
    artifacts = tuple(item.evidence_artifact for item in packet.evidence)
    discovery_id = "cninfo-refresh-601088-2026-09-04-interim-dividend-meeting"
    discovery = DiscoveryInput(
        discovery_id=discovery_id,
        source_lane=packet.source_lane,
        ticker=packet.stock_code,
        economic_direction=(
            "no new owner-cash evidence beyond the already-disclosed 2026 interim dividend proposal"
        ),
        as_of=packet.prepared_at,
        factual_observations=(
            DiscoveryObservation(
                statement=(
                    "China Shenhua scheduled a 2026-09-23 extraordinary general meeting to vote "
                    "on the 2026 interim dividend proposal and two independent-director candidates."
                ),
                evidence_artifact_ids=(artifacts[0].id, artifacts[1].id),
            ),
            DiscoveryObservation(
                statement=(
                    "The meeting notice states that the interim dividend proposal had already "
                    "been disclosed on 2026-08-29, before the frozen Research as-of date."
                ),
                evidence_artifact_ids=(artifacts[0].id, artifacts[1].id),
            ),
        ),
        source_lineage=_lineage(packet),
        why_now=(
            "The meeting notice and materials were published after the frozen Research cutoff."
        ),
        current_market_expression=None,
        contradiction_or_mapping_warning=(
            "A meeting notice and repeated proposal terms are governance procedure, not new proof "
            "of cash generation, payout durability, post-acquisition returns or balance-sheet change."
        ),
        next_discriminating_search=(
            "No follow-up on this repeated packet; observe the actual shareholder resolution, "
            "payment and later operating cash-flow evidence when available."
        ),
        known_stop_or_downgrade_condition=(
            "Drop when the packet only repeats a proposal already inside the frozen Research PIT "
            "and adds no new owner-economics fact."
        ),
    )
    pre = PreResearchResult(
        discovery_id=discovery_id,
        as_of=packet.prepared_at,
        what_is_this=(
            "An extraordinary-general-meeting notice and meeting pack repeating an already "
            "disclosed interim dividend proposal, plus independent-director elections."
        ),
        economic_direction=(
            "no new owner-cash evidence beyond the already-disclosed 2026 interim dividend proposal"
        ),
        why_surfaced_now=(
            "The governance documents post-date the frozen Research and therefore required an exact check."
        ),
        current_expression_or_leadership=None,
        basic_business_role=(
            "The documents govern shareholder voting; they do not update coal prices, volumes, "
            "segment earnings, cash conversion, acquisition integration or debt."
        ),
        potential_fundamental_driver=(
            "A completed dividend payment can distribute owner cash, but the proposal itself was "
            "already public before the current Research snapshot."
        ),
        current_market_expectation_hypothesis=(
            "The market can already incorporate the previously disclosed interim payout proposal; "
            "this packet principally confirms the voting timetable."
        ),
        material_claims=(
            ResearchClaim(
                statement=(
                    "The 2026-09-23 meeting will vote on an interim dividend proposal already "
                    "disclosed on 2026-08-29."
                ),
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(artifacts[0].id, artifacts[1].id),
            ),
        ),
        obvious_contradiction=None,
        largest_unknown=(
            "No new decision-critical unknown is introduced by these governance documents."
        ),
        next_discriminating_search=(
            "Wait for an actual vote/payment or new operating and capital-return evidence rather "
            "than re-researching the repeated proposal."
        ),
        route=PreResearchRoute.STOP,
        route_reason=(
            "The packet repeats information already available before the frozen Research cutoff "
            "and does not change any current China Shenhua Research question or invalidation condition."
        ),
    )
    return DisclosureResearchAssessment(
        assessment_input_hash=packet.assessment_input_hash,
        discovery=discovery,
        pre_research=pre,
    )


def _gigadevice_assessment(
    packet: DisclosureAssessmentPacket,
) -> DisclosureResearchAssessment:
    artifact = packet.evidence[0].evidence_artifact
    discovery_id = "cninfo-refresh-603986-2026-09-04-a-share-repurchase"
    discovery = DiscoveryInput(
        discovery_id=discovery_id,
        source_lane=packet.source_lane,
        ticker=packet.stock_code,
        economic_direction=(
            "actual post-H-share capital deployment through A-share repurchases and intended cancellation"
        ),
        as_of=packet.prepared_at,
        factual_observations=(
            DiscoveryObservation(
                statement=(
                    "On 2026-09-03 GigaDevice repurchased 135,000 A shares, 0.02% of issued shares, "
                    "at RMB380.27-385.00 per share for RMB51,852,403 in total."
                ),
                evidence_artifact_ids=(artifact.id,),
            ),
            DiscoveryObservation(
                statement=(
                    "The form reports 670,718,327 issued A shares both before and after the period; "
                    "the 135,000 repurchased shares are intended for cancellation rather than treasury retention."
                ),
                evidence_artifact_ids=(artifact.id,),
            ),
        ),
        source_lineage=_lineage(packet),
        why_now=(
            "The H-share next-day return was published after the frozen Research and contains a "
            "new A-share repurchase transaction tied to an existing capital-allocation monitoring trigger."
        ),
        current_market_expression=(
            "The company paid RMB380.27-385.00 for the disclosed 2026-09-03 repurchase; this is "
            "market and capital-allocation context, not Fundamental Belief or a Human entry instruction."
        ),
        contradiction_or_mapping_warning=(
            "One 0.02% repurchase does not establish material per-share accretion, sustainable owner "
            "cash, cycle duration or management's full post-H-share capital-allocation plan."
        ),
        next_discriminating_search=(
            "Observe cumulative repurchase execution and cancellation, funding, operating cash flow, "
            "working capital and capex before judging owner-return materiality."
        ),
        known_stop_or_downgrade_condition=(
            "Keep the event in background monitoring unless cumulative execution or cash consequences "
            "become large enough to change per-share owner economics."
        ),
    )
    pre = PreResearchResult(
        discovery_id=discovery_id,
        as_of=packet.prepared_at,
        what_is_this=(
            "A Hong Kong next-day disclosure return reporting one day of A-share repurchase execution."
        ),
        economic_direction=(
            "actual post-H-share capital deployment through A-share repurchases and intended cancellation"
        ),
        why_surfaced_now=(
            "The filing post-dates the frozen Research and directly touches the declared post-H-share "
            "capital-allocation monitoring question."
        ),
        current_expression_or_leadership=(
            "The disclosed 2026-09-03 repurchase was executed at RMB380.27-385.00 per A share."
        ),
        basic_business_role=(
            "This is a capital-allocation event; it does not update specialty-memory supply, product "
            "margins, MCU/custom-memory economics or operating demand."
        ),
        potential_fundamental_driver=(
            "Repurchases followed by cancellation can improve per-share owner economics if cumulative "
            "scale, funding and purchase price are attractive relative to sustainable owner cash."
        ),
        current_market_expectation_hypothesis=(
            "The market may read repurchase execution as management confidence, but the disclosed "
            "increment is too small to establish a durable valuation or earnings-floor conclusion."
        ),
        material_claims=(
            ResearchClaim(
                statement=(
                    "GigaDevice spent RMB51,852,403 to repurchase 135,000 A shares on 2026-09-03; "
                    "the shares are intended for cancellation and issued-share count had not yet changed."
                ),
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(artifact.id,),
            ),
            ResearchClaim(
                statement=(
                    "The transaction is relevant to post-H-share capital allocation but is not by "
                    "itself evidence about memory-cycle duration or normalized earnings."
                ),
                kind=ResearchClaimKind.INFERENCE,
            ),
        ),
        obvious_contradiction=(
            "Actual repurchase execution is supportive capital-allocation evidence, while its 0.02% "
            "single-day size remains insufficient to establish material owner-return impact."
        ),
        largest_unknown=(
            "The eventual cumulative repurchase and cancellation scale, funding source, interaction "
            "with working capital/capex, and resulting per-share owner economics."
        ),
        next_discriminating_search=(
            "Wait for later repurchase progress or completion, cancellation, and cash-flow/capex evidence."
        ),
        route=PreResearchRoute.WAIT_FOR_TRIGGER,
        route_reason=(
            "The filing supplies a real new fact for an existing monitoring trigger, but the disclosed "
            "increment does not justify a new Quick or Full Research loop and creates no Human wake."
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
        packet = packets_by_identity[identity]
        if packet.assessment_input_hash != expected_hash:
            raise SystemExit(f"assessment input hash changed for {identity}")
        for item in packet.evidence:
            expected_content_hash = EXPECTED_CONTENT_HASHES[item.announcement_id]
            if item.evidence_artifact.content_hash != expected_content_hash:
                raise SystemExit(
                    f"source content hash changed for {item.announcement_id}"
                )

    assessments = {
        ("601088", ("1225546775", "1225546779")): _shenhua_assessment(
            packets_by_identity[("601088", ("1225546775", "1225546779"))]
        ),
        ("603986", ("1225546905",)): _gigadevice_assessment(
            packets_by_identity[("603986", ("1225546905",))]
        ),
    }
    expected_results = {
        ("601088", ("1225546775", "1225546779")): ResearchFunnelTerminalState.DROP_FOR_NOW,
        ("603986", ("1225546905",)): ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
    }
    results = {}
    for identity, assessment in assessments.items():
        result = run_disclosure_research_assessment(
            packet=packets_by_identity[identity],
            assessment=assessment,
        )
        if result.terminal_state is not expected_results[identity]:
            raise SystemExit(
                f"unexpected terminal state for {identity}: {result.terminal_state}"
            )
        if result.investment_authority != "NONE":
            raise SystemExit("disclosure assessment gained investment authority")
        results[identity] = result

    if any(
        result.terminal_state is ResearchFunnelTerminalState.DEEPEN_REQUIRED
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
            assessment_semantics_id=packets_by_identity[identity].assessment_semantics_id,
            assessment_result=result.terminal_state,
            assessed_at=assessed_at,
        )
        for identity, result in sorted(results.items())
    )
    merged = merge_disclosure_assessment_receipts(existing, incoming)
    write_disclosure_assessment_receipts(args.receipts, merged)

    args.audit_dir.mkdir(parents=True, exist_ok=True)
    for identity, assessment in assessments.items():
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
                "terminal_state": result.terminal_state.value,
                "terminal_reason": result.terminal_reason,
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
        "# Current disclosure receipt seed",
        "",
        f"Source workflow run: `{SOURCE_RUN_ID}`",
        "",
        "| Security | Announcement IDs | Result | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for item in audit["results"]:
        lines.append(
            f"| {item['stock_code']} | {', '.join(item['announcement_ids'])} | "
            f"`{item['terminal_state']}` | {item['terminal_reason']} |"
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

    print("DISCLOSURE RECEIPTS: 2 exact quiet batches")
    print("DROP_FOR_NOW: 1")
    print("WAIT_FOR_TRIGGER: 1")
    print("DEEPEN_REQUIRED: 0")
    print(f"MERGED RECEIPTS: {len(merged)}")
    print("INVESTMENT AUTHORITY: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
