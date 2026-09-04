from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from decision_kernel.identity import canonical_hash
from decision_kernel.odds import ParticipationZone
from decision_kernel.research_funnel import (
    DiscoveryInput,
    DiscoveryObservation,
    DiscoverySource,
    PreResearchResult,
    PreResearchRoute,
    QuickResearchResult,
    QuickResearchRoute,
    ResearchClaim,
    ResearchClaimKind,
)
from decision_kernel.research_workflow_v1 import (
    ResearchFunnelResult,
    ResearchFunnelStage,
    ResearchFunnelTerminalState,
)
from decision_kernel.runtime.attention_inbox import (
    ResearchAttentionHandoff,
    parse_research_attention_handoff,
    render_attention_inbox_html,
    render_attention_inbox_markdown,
    serialize_research_attention_handoff,
)


AS_OF = datetime(2026, 9, 4, 1, 0, tzinfo=timezone.utc)


def _discovery(*, ticker: str, discovery_id: str, lane: str) -> DiscoveryInput:
    evidence_a = uuid4()
    evidence_b = uuid4()
    return DiscoveryInput(
        discovery_id=discovery_id,
        source_lane=lane,
        ticker=ticker,
        security_id=f"{ticker}.SZ",
        economic_direction="possible improvement in owner economics",
        as_of=AS_OF,
        factual_observations=(
            DiscoveryObservation(
                statement="primary evidence changed",
                evidence_artifact_ids=(evidence_a,),
            ),
        ),
        source_lineage=(
            DiscoverySource(
                evidence_artifact_id=evidence_a,
                source_locator="https://example.com/a",
                available_at=AS_OF,
            ),
            DiscoverySource(
                evidence_artifact_id=evidence_b,
                source_locator="https://example.com/b",
                available_at=AS_OF,
            ),
        ),
        why_now="new operating evidence appeared",
        current_market_expression="price response remains context only",
        contradiction_or_mapping_warning="listed-company value capture still needs proof",
        next_discriminating_search="verify revenue and margin conversion",
        known_stop_or_downgrade_condition="drop if value capture is not attributable",
    )


def _deepen(*, ticker: str, discovery_id: str, lane: str) -> ResearchFunnelResult:
    discovery = _discovery(ticker=ticker, discovery_id=discovery_id, lane=lane)
    evidence_ids = tuple(item.evidence_artifact_id for item in discovery.source_lineage)
    pre = PreResearchResult(
        discovery_id=discovery.discovery_id,
        as_of=AS_OF,
        what_is_this="a listed operating company exposed to the changing economic node",
        economic_direction=discovery.economic_direction,
        why_surfaced_now=discovery.why_now,
        current_expression_or_leadership=discovery.current_market_expression,
        basic_business_role="operating company",
        potential_fundamental_driver="higher utilization and profit conversion",
        current_market_expectation_hypothesis="market may already see the theme but not the economics",
        material_claims=(
            ResearchClaim(
                statement="operating evidence changed",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(evidence_ids[0],),
            ),
        ),
        largest_unknown="whether the change reaches listed-company owner earnings",
        next_discriminating_search="verify revenue, margin and cash conversion",
        route=PreResearchRoute.CONTINUE_TO_QUICK,
        route_reason="the new evidence is material enough for bounded Quick Research",
    )
    quick = QuickResearchResult(
        discovery_id=discovery.discovery_id,
        pre_research_hash=canonical_hash(pre),
        as_of=AS_OF,
        business_model="industrial supplier",
        segment_mix="relevant segment plus other businesses",
        economic_role="direct operating exposure",
        major_profit_drivers=("volume", "margin"),
        industry_supply_demand_variables=("orders", "utilization"),
        value_chain_position="supplier",
        current_industry_state="change requires further confirmation",
        market_expectation_hypothesis="market recognizes the theme but economics remain debated",
        current_expression_or_leadership=discovery.current_market_expression,
        supporting_claims=(
            ResearchClaim(
                statement="new primary evidence supports a real operating change",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(evidence_ids[0],),
            ),
        ),
        contradictory_claims=(
            ResearchClaim(
                statement="value capture is not yet proven",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(evidence_ids[1],),
            ),
        ),
        evidence_authority_assessment="primary evidence plus explicit unresolved mapping",
        variant_perception="the decision-relevant gap may be economic conversion, not theme awareness",
        unresolved_questions=("does operating change reach owner earnings?",),
        next_discriminating_evidence=("segment revenue and margin conversion",),
        route=QuickResearchRoute.DEEPEN,
        route_reason="owner-economics conversion is unresolved but plausibly decision-relevant",
    )
    return ResearchFunnelResult(
        terminal_state=ResearchFunnelTerminalState.DEEPEN_REQUIRED,
        terminal_stage=ResearchFunnelStage.QUICK_RESEARCH,
        terminal_reason="owner-economics conversion now deserves Full Research",
        discovery=discovery,
        pre_research=pre,
        quick_research=quick,
    )


def _wait(*, ticker: str, discovery_id: str, lane: str) -> ResearchFunnelResult:
    discovery = _discovery(ticker=ticker, discovery_id=discovery_id, lane=lane)
    evidence_id = discovery.source_lineage[0].evidence_artifact_id
    pre = PreResearchResult(
        discovery_id=discovery.discovery_id,
        as_of=AS_OF,
        what_is_this="a weak early signal",
        economic_direction=discovery.economic_direction,
        why_surfaced_now=discovery.why_now,
        current_expression_or_leadership=discovery.current_market_expression,
        basic_business_role="operating company",
        potential_fundamental_driver="possible demand change",
        current_market_expectation_hypothesis="not enough evidence",
        material_claims=(
            ResearchClaim(
                statement="one fact changed",
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=(evidence_id,),
            ),
        ),
        largest_unknown="durability",
        next_discriminating_search="wait for a second operating confirmation",
        route=PreResearchRoute.WAIT_FOR_TRIGGER,
        route_reason="one observation is insufficient to spend Full Research budget",
    )
    return ResearchFunnelResult(
        terminal_state=ResearchFunnelTerminalState.WAIT_FOR_TRIGGER,
        terminal_stage=ResearchFunnelStage.PRE_RESEARCH,
        terminal_reason=pre.route_reason,
        discovery=discovery,
        pre_research=pre,
    )


def _decision(*, ticker: str, company: str, attention: bool):
    scenario_results = (
        SimpleNamespace(
            scenario_id="down",
            scenario_name="downside",
            probability=Decimal("0.30"),
            total_payoff_per_share=Decimal("20"),
        ),
        SimpleNamespace(
            scenario_id="base",
            scenario_name="base",
            probability=Decimal("0.50"),
            total_payoff_per_share=Decimal("40"),
        ),
        SimpleNamespace(
            scenario_id="up",
            scenario_name="upside",
            probability=Decimal("0.20"),
            total_payoff_per_share=Decimal("70"),
        ),
    )
    price = Decimal("36")
    weighted = sum(
        (item.probability * item.total_payoff_per_share for item in scenario_results),
        Decimal("0"),
    )
    brief = SimpleNamespace(
        ticker=ticker,
        company_name=company,
        current_price=str(price),
        currency="CNY",
        as_of=AS_OF,
        why_now="existing Odds gate changed",
        current_belief="frozen core thesis",
        market_expectation="market expectation stays separate",
        open_questions=("question",),
        invalidation=("invalidation",),
        monitoring_triggers=("trigger",),
        odds=SimpleNamespace(
            participation_zone=SimpleNamespace(
                value=("ACCEPTABLE_ODDS" if attention else "INSUFFICIENT_ODDS")
            ),
            expected_holding_period_return=(weighted / price) - Decimal("1"),
            positive_return_probability=Decimal("0.20"),
        ),
        participation_condition=SimpleNamespace(
            threshold_basis_zone=ParticipationZone.ACCEPTABLE_ODDS,
            required_expected_return=Decimal("0.32"),
            required_positive_return_probability=Decimal("0.55"),
        ),
    )
    return SimpleNamespace(
        odds=SimpleNamespace(
            artifact=SimpleNamespace(
                calculation=SimpleNamespace(
                    aggregate=SimpleNamespace(
                        probability_weighted_total_payoff_per_share=weighted,
                    ),
                    scenario_results=scenario_results,
                ),
            )
        ),
        human_surface=SimpleNamespace(
            attention_eligible=attention,
            investment_authority="NONE",
            brief=brief,
        ),
    )


def test_new_discovery_surfaces_ticker_without_inventing_research_or_odds() -> None:
    deepen = ResearchAttentionHandoff(
        company_name="英维克",
        research_funnel=_deepen(
            ticker="002837",
            discovery_id="industry-liquid-cooling",
            lane="INDUSTRY_DISCOVERY",
        ),
    )
    wait = ResearchAttentionHandoff(
        company_name="观察样例",
        research_funnel=_wait(
            ticker="000001",
            discovery_id="weak-signal",
            lane="OPEN_DISCOVERY",
        ),
    )

    html = render_attention_inbox_html((), (deepen, wait), generated_at=AS_OF)
    markdown = render_attention_inbox_markdown((), (deepen, wait), generated_at=AS_OF)

    assert "英维克" in html
    assert "002837" in html
    assert "DEEPEN_REQUIRED" in html
    assert "尚未建立 frozen Research · Odds 未生成" in html
    assert "INDUSTRY_DISCOVERY" in html
    assert "后台研究处置（1）" in html
    assert "WAIT_FOR_TRIGGER" in html
    assert "为什么值得看" in html
    assert "Investment Authority = NONE" in html

    assert "## 英维克 002837" in markdown
    assert "尚未建立 frozen Research · Odds 未生成" in markdown
    assert "owner-economics conversion now deserves Full Research" in markdown


def test_discovery_for_existing_case_joins_current_research_state() -> None:
    decision = _decision(ticker="002050", company="三花智控", attention=False)
    deepen = ResearchAttentionHandoff(
        research_funnel=_deepen(
            ticker="002050.SZ",
            discovery_id="robot-allocation-update",
            lane="DISCLOSURE_DISCOVERY",
        )
    )

    html = render_attention_inbox_html((decision,), (deepen,), generated_at=AS_OF)

    assert "三花智控" in html
    assert "Research 已存在" in html
    assert "INSUFFICIENT_ODDS" in html
    assert "¥36.00" in html
    assert "当前 Belief" in html
    assert "frozen core thesis" in html


def test_handoff_round_trip_keeps_funnel_authority_and_presentation_name_separate() -> None:
    handoff = ResearchAttentionHandoff(
        company_name="英维克",
        research_funnel=_deepen(
            ticker="002837",
            discovery_id="round-trip",
            lane="INDUSTRY_DISCOVERY",
        ),
    )

    parsed = parse_research_attention_handoff(serialize_research_attention_handoff(handoff))

    assert parsed.company_name == "英维克"
    assert parsed.research_funnel == handoff.research_funnel
    assert parsed.research_funnel.investment_authority == "NONE"
