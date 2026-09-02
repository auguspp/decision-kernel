from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo

from .deep_research import DeepResearchPackage
from .live import run_live_deep_research_package, run_live_research_commit_package
from .research_commit import ResearchCommitPackage
from .research_workflow_v1 import ResearchFunnelTerminalState
from .runtime import cninfo_http, hithink_http
from .runtime.disclosure_assessment import (
    parse_disclosure_assessment_packet,
    prepare_disclosure_assessment_packet,
    serialize_disclosure_assessment_packet,
)
from .runtime.disclosure_radar import (
    filter_research_uncovered_disclosure_batches,
    group_disclosures_by_publication_date,
)
from .runtime.disclosure_receipts import (
    DisclosureAssessmentReceipt,
    disclosure_assessment_receipt_identity,
    filter_unassessed_disclosure_batches,
    merge_disclosure_assessment_receipts,
    parse_disclosure_assessment_receipts,
    write_disclosure_assessment_receipts,
)
from .runtime.disclosure_research import (
    DisclosureResearchAssessment,
    run_disclosure_research_assessment,
)
from .runtime.inbox import render_decision_inbox_html, render_decision_inbox_markdown
from .workflow import DecisionSpineResult


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
DEFAULT_DISCLOSURE_PACKET_LIMIT = 20


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="decision-kernel",
        description="Run reviewed research through live Odds and Human gating.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser(
        "run",
        help="Run a Decision OS Research Method v1 DeepResearchPackage.",
    )
    run.add_argument(
        "package",
        type=Path,
        help="Path to one DeepResearchPackage JSON file.",
    )
    generic = subparsers.add_parser(
        "run-research",
        help="Run a method-agnostic ResearchCommitPackage.",
    )
    generic.add_argument(
        "package",
        type=Path,
        help="Path to one ResearchCommitPackage JSON file.",
    )
    inbox = subparsers.add_parser(
        "build-inbox",
        help="Run reviewed research packages and render one Human Decision Inbox.",
    )
    inbox.add_argument(
        "packages",
        nargs="+",
        type=Path,
        help="ResearchCommitPackage or DeepResearchPackage JSON files to include.",
    )
    inbox.add_argument(
        "--output",
        type=Path,
        default=Path("decision-inbox/index.html"),
        help="HTML output path.",
    )
    inbox.add_argument(
        "--summary",
        type=Path,
        default=Path("decision-inbox/summary.md"),
        help="Markdown summary output path.",
    )
    disclosure_scan = subparsers.add_parser(
        "scan-disclosures",
        help=(
            "One-shot scan for official CNINFO disclosure batches newer than frozen Research."
        ),
    )
    disclosure_scan.add_argument(
        "packages",
        nargs="+",
        type=Path,
        help="One current ResearchCommitPackage or DeepResearchPackage per A-share security.",
    )
    disclosure_scan.add_argument(
        "--through",
        type=date.fromisoformat,
        required=True,
        help="Inclusive CNINFO scan end date in YYYY-MM-DD form.",
    )
    disclosure_scan.add_argument(
        "--receipts",
        type=Path,
        help=(
            "Optional explicit JSON receipt file used to suppress exact batches already assessed "
            "against the same frozen Research."
        ),
    )
    disclosure_scan.add_argument(
        "--packet-dir",
        type=Path,
        help=(
            "Optional directory for auditable assessment packets for still-unassessed batches. "
            "Requires the documents extra for PDF text extraction."
        ),
    )
    disclosure_scan.add_argument(
        "--packet-limit",
        type=int,
        default=DEFAULT_DISCLOSURE_PACKET_LIMIT,
        help=(
            "Maximum unassessed batches to prepare when --packet-dir is used; fail closed rather "
            f"than silently truncate. Default: {DEFAULT_DISCLOSURE_PACKET_LIMIT}."
        ),
    )
    apply_disclosure = subparsers.add_parser(
        "apply-disclosure-assessment",
        help=(
            "Validate one external semantic disclosure assessment against its exact packet and "
            "record only quiet Research Funnel outcomes."
        ),
    )
    apply_disclosure.add_argument(
        "packet",
        type=Path,
        help="Self-validating DisclosureAssessmentPacket JSON produced by scan-disclosures.",
    )
    apply_disclosure.add_argument(
        "assessment",
        type=Path,
        help=(
            "External DisclosureResearchAssessment JSON containing existing Discovery / Pre / "
            "optional Quick Research objects."
        ),
    )
    apply_disclosure.add_argument(
        "--receipts",
        type=Path,
        required=True,
        help=(
            "Explicit receipt memory file. WAIT_FOR_TRIGGER / DROP_FOR_NOW are recorded; "
            "DEEPEN_REQUIRED remains actionable and unreceipted."
        ),
    )
    return parser


def _run_inbox_package(
    raw_package: str,
    *,
    fetch_market,
    observed_at: datetime,
) -> DecisionSpineResult:
    payload = json.loads(raw_package)
    if not isinstance(payload, dict):
        raise ValueError("inbox research package must be a JSON object")

    if "deep_research" in payload and "discovery" in payload:
        package = DeepResearchPackage.model_validate(payload)
        return run_live_deep_research_package(
            package=package,
            fetch_market=fetch_market,
            observed_at=observed_at,
        ).decision

    package = ResearchCommitPackage.model_validate(payload)
    return run_live_research_commit_package(
        package=package,
        fetch_market=fetch_market,
        observed_at=observed_at,
    ).decision


def _research_snapshot_from_raw_package(raw_package: str):
    payload = json.loads(raw_package)
    if not isinstance(payload, dict):
        raise ValueError("disclosure research package must be a JSON object")
    if "deep_research" in payload and "discovery" in payload:
        return DeepResearchPackage.model_validate(payload).research_snapshot
    return ResearchCommitPackage.model_validate(payload).research_snapshot


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)

    try:
        api_key = os.environ.get(hithink_http.HITHINK_API_KEY_ENV)

        def fetch_market(*, thscode: str, observed_at):
            return hithink_http.fetch_latest_hithink_observed_market(
                thscode=thscode,
                observed_at=observed_at,
                api_key=api_key,
            )

        if args.command == "build-inbox":
            generated_at = datetime.now(timezone.utc)
            decisions = [
                _run_inbox_package(
                    package_path.read_text(encoding="utf-8"),
                    fetch_market=fetch_market,
                    observed_at=generated_at,
                )
                for package_path in args.packages
            ]

            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.summary.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                render_decision_inbox_html(decisions, generated_at=generated_at),
                encoding="utf-8",
            )
            args.summary.write_text(
                render_decision_inbox_markdown(decisions, generated_at=generated_at),
                encoding="utf-8",
            )
            attention = sum(
                decision.human_surface.attention_eligible for decision in decisions
            )
            print(
                f"DECISION INBOX: {attention} attention / {len(decisions)} total",
                file=stdout,
            )
            print(f"HTML: {args.output}", file=stdout)
            print(f"SUMMARY: {args.summary}", file=stdout)
            return 0

        if args.command == "apply-disclosure-assessment":
            packet = parse_disclosure_assessment_packet(
                args.packet.read_text(encoding="utf-8")
            )
            assessment = DisclosureResearchAssessment.model_validate_json(
                args.assessment.read_text(encoding="utf-8")
            )
            result = run_disclosure_research_assessment(
                packet=packet,
                assessment=assessment,
            )

            existing_receipts = ()
            if args.receipts.exists():
                existing_receipts = parse_disclosure_assessment_receipts(
                    args.receipts.read_text(encoding="utf-8")
                )

            if result.terminal_state in {
                ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
                ResearchFunnelTerminalState.DROP_FOR_NOW,
            }:
                receipt = DisclosureAssessmentReceipt(
                    source_lane=packet.source_lane,
                    stock_code=packet.stock_code,
                    announcement_ids=packet.announcement_ids,
                    research_snapshot_id=packet.research_snapshot_id,
                    research_as_of=packet.research_as_of,
                    assessment_semantics_id=packet.assessment_semantics_id,
                    assessment_result=result.terminal_state,
                    assessed_at=datetime.now(timezone.utc),
                )
                merged = merge_disclosure_assessment_receipts(
                    existing_receipts,
                    (receipt,),
                )
                changed = len(merged) != len(existing_receipts)
                write_disclosure_assessment_receipts(args.receipts, merged)
                disposition = "QUIET"
                receipt_status = "RECORDED" if changed else "UNCHANGED"
                receipt_detail = f"{args.receipts} ({len(merged)} total)"
            elif result.terminal_state is ResearchFunnelTerminalState.DEEPEN_REQUIRED:
                exact_identity = (
                    packet.stock_code,
                    packet.announcement_ids,
                    packet.research_snapshot_id,
                    packet.research_as_of,
                    packet.assessment_semantics_id,
                )
                previous = next(
                    (
                        receipt
                        for receipt in existing_receipts
                        if disclosure_assessment_receipt_identity(receipt) == exact_identity
                    ),
                    None,
                )
                if previous is not None:
                    raise ValueError(
                        "DEEPEN_REQUIRED disclosure assessment conflicts with an existing quiet "
                        "receipt for the same exact batch, frozen Research, and assessment "
                        f"semantics: {previous.assessment_result.value}"
                    )
                disposition = "ACTIONABLE"
                receipt_status = "NOT WRITTEN"
                receipt_detail = (
                    f"{args.receipts} (DEEPEN_REQUIRED remains actionable and unreceipted)"
                )
            else:  # pragma: no cover - exhaustive ResearchFunnelTerminalState guard
                raise AssertionError(
                    f"unsupported disclosure Research result: {result.terminal_state.value}"
                )

            print(
                f"DISCLOSURE RESEARCH RESULT: {result.terminal_state.value}",
                file=stdout,
            )
            print(f"TERMINAL STAGE: {result.terminal_stage.value}", file=stdout)
            print(f"ASSESSMENT DISPOSITION: {disposition}", file=stdout)
            print(f"REASON: {result.terminal_reason}", file=stdout)
            print(
                f"RECEIPT: {receipt_status} | {receipt_detail}",
                file=stdout,
            )
            print(
                f"INVESTMENT AUTHORITY: {result.investment_authority}",
                file=stdout,
            )
            return 0

        if args.command == "scan-disclosures":
            if args.packet_dir is not None and args.packet_limit <= 0:
                raise ValueError("disclosure assessment packet limit must be positive")

            research_as_of_by_stock: dict[str, datetime] = {}
            research_identity_by_stock = {}
            research_snapshot_by_stock = {}
            company_by_stock: dict[str, str] = {}
            scan_inputs: list[tuple[str, date]] = []

            for package_path in args.packages:
                snapshot = _research_snapshot_from_raw_package(
                    package_path.read_text(encoding="utf-8")
                )
                ticker = snapshot.ticker.strip()
                if ticker in research_as_of_by_stock:
                    raise ValueError(
                        f"disclosure scan received more than one current Research package for {ticker}"
                    )
                start_date = snapshot.as_of_datetime.astimezone(SHANGHAI_TZ).date()
                if start_date > args.through:
                    raise ValueError(
                        f"disclosure scan end date precedes frozen Research for {ticker}"
                    )

                research_as_of_by_stock[ticker] = snapshot.as_of_datetime
                research_identity_by_stock[ticker] = (snapshot.id, snapshot.as_of_datetime)
                research_snapshot_by_stock[ticker] = snapshot
                company_by_stock[ticker] = snapshot.company_name
                scan_inputs.append((ticker, start_date))

            receipts = ()
            if args.receipts is not None:
                receipts = parse_disclosure_assessment_receipts(
                    args.receipts.read_text(encoding="utf-8")
                )

            announcements = []
            for ticker, start_date in scan_inputs:
                batch = cninfo_http.fetch_cninfo_disclosures(
                    stock_code=ticker,
                    start_date=start_date,
                    end_date=args.through,
                )
                announcements.extend(batch.announcements)

            batches = group_disclosures_by_publication_date(announcements)
            uncovered = filter_research_uncovered_disclosure_batches(
                batches,
                research_as_of_by_stock=research_as_of_by_stock,
            )
            unassessed = filter_unassessed_disclosure_batches(
                uncovered,
                research_identity_by_stock=research_identity_by_stock,
                receipts=receipts,
            )
            seen_suppressed = len(uncovered) - len(unassessed)

            packet_outputs: list[tuple[Path, str, str]] = []
            if args.packet_dir is not None:
                if len(unassessed) > args.packet_limit:
                    raise ValueError(
                        "disclosure assessment packet limit exceeded: "
                        f"{len(unassessed)} unassessed > {args.packet_limit}; no packets written"
                    )
                prepared_at = datetime.now(timezone.utc)
                for batch in unassessed:
                    packet = prepare_disclosure_assessment_packet(
                        research_snapshot=research_snapshot_by_stock[batch.stock_code],
                        batch=batch,
                        prepared_at=prepared_at,
                    )
                    packet_path = args.packet_dir / (
                        f"{batch.stock_code}-{batch.publication_date.isoformat()}-"
                        f"{packet.assessment_input_hash[:16]}.json"
                    )
                    packet_outputs.append(
                        (
                            packet_path,
                            serialize_disclosure_assessment_packet(packet),
                            packet.assessment_input_hash,
                        )
                    )

                if packet_outputs:
                    args.packet_dir.mkdir(parents=True, exist_ok=True)
                    for packet_path, serialized, _input_hash in packet_outputs:
                        packet_path.write_text(serialized, encoding="utf-8")

            print(
                "OFFICIAL DISCLOSURE SCAN: "
                f"{len(unassessed)} unassessed / "
                f"{seen_suppressed} seen-suppressed / "
                f"{len(uncovered)} research-uncovered / "
                f"{len(batches)} dated batches / "
                f"{len(announcements)} announcements / "
                f"{len(research_as_of_by_stock)} research cases",
                file=stdout,
            )
            if args.packet_dir is not None:
                print(
                    f"ASSESSMENT PACKETS: {len(packet_outputs)} prepared | dir={args.packet_dir}",
                    file=stdout,
                )
                for packet_path, _serialized, input_hash in packet_outputs:
                    print(
                        f"PACKET: {packet_path} | input_hash={input_hash}",
                        file=stdout,
                    )
            if not uncovered:
                print("NO RESEARCH-UNCOVERED OFFICIAL DISCLOSURES", file=stdout)
            elif not unassessed:
                print(
                    "NO UNASSESSED RESEARCH-UNCOVERED OFFICIAL DISCLOSURES",
                    file=stdout,
                )
            for batch in unassessed:
                print(
                    "UNASSESSED: "
                    f"{batch.stock_code} {company_by_stock[batch.stock_code]} | "
                    f"research_as_of={research_as_of_by_stock[batch.stock_code].isoformat()} | "
                    f"publication_date={batch.publication_date.isoformat()} | "
                    f"announcements={len(batch.announcements)}",
                    file=stdout,
                )
                for item in batch.announcements:
                    print(
                        f"- {item.announcement_id} | {item.title} | {item.source_locator}",
                        file=stdout,
                    )
            assessment_status = "UNASSESSED" if unassessed else "QUIET"
            print(
                f"DISCLOSURE ASSESSMENT STATUS: {assessment_status}",
                file=stdout,
            )
            print("INVESTMENT AUTHORITY: NONE", file=stdout)
            return 0

        raw_package = args.package.read_text(encoding="utf-8")
        if args.command == "run":
            package = DeepResearchPackage.model_validate_json(raw_package)
            decision = run_live_deep_research_package(
                package=package,
                fetch_market=fetch_market,
            ).decision
        elif args.command == "run-research":
            package = ResearchCommitPackage.model_validate_json(raw_package)
            decision = run_live_research_commit_package(
                package=package,
                fetch_market=fetch_market,
            ).decision
        else:
            raise AssertionError(f"unsupported command: {args.command}")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=stderr)
        return 2

    _print_decision(decision, stdout=stdout)
    return 0


def _print_decision(decision: DecisionSpineResult, *, stdout: TextIO) -> None:
    surface = decision.human_surface
    brief = surface.brief
    market = decision.odds.artifact.observed_market

    print("DECISION KERNEL", file=stdout)
    print(f"STATE: {decision.terminal_state.value}", file=stdout)
    print(f"SECURITY: {brief.ticker} {brief.company_name}", file=stdout)
    print(
        "PRICE: "
        f"{market.market_price} {market.currency} @ {market.market_timestamp.isoformat()}",
        file=stdout,
    )
    print(f"ODDS: {brief.odds.participation_zone.value}", file=stdout)
    print(
        "HUMAN ATTENTION: " + ("YES" if surface.attention_eligible else "NO"),
        file=stdout,
    )
    print(f"INVESTMENT AUTHORITY: {surface.investment_authority}", file=stdout)

    if not surface.attention_eligible:
        print(f"QUIET REASON: {surface.eligibility_reason}", file=stdout)
        return

    print(f"WHY NOW: {brief.why_now}", file=stdout)
    print(f"CURRENT BELIEF: {brief.current_belief}", file=stdout)
    print(f"MARKET EXPECTATION: {brief.market_expectation}", file=stdout)
    print("OPEN QUESTIONS:", file=stdout)
    for item in brief.open_questions:
        print(f"- {item}", file=stdout)
    print("INVALIDATION:", file=stdout)
    for item in brief.invalidation:
        print(f"- {item}", file=stdout)
    print("MONITORING TRIGGERS:", file=stdout)
    for item in brief.monitoring_triggers:
        print(f"- {item}", file=stdout)


if __name__ == "__main__":
    raise SystemExit(main())
