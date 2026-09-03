from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from decision_kernel.deep_research import DeepResearchPackage
from decision_kernel.primitives import DomainValidationError
from decision_kernel.publishing import (
    PublicationAuthoringInput,
    PublicationEvidenceClearance,
    build_harness_bundle,
    lint_publication_draft,
)


SANHUA_RESEARCH = Path("research_cases/002050-sanhua-deep-research-v1.json")


E_H1 = UUID("c767343a-8a9c-5841-ac58-eb1fe26f56b7")
E_CONSENSUS = UUID("c016f87b-0042-532d-a29f-9749967a58eb")
E_ROBOT = UUID("f9b963f6-a536-5aa1-aea3-8f52abb9de99")
E_LIQUID = UUID("42091f91-7352-52d3-abf7-65c90f89fba4")


def _package() -> DeepResearchPackage:
    return DeepResearchPackage.model_validate_json(SANHUA_RESEARCH.read_text(encoding="utf-8"))


def _authoring(**updates) -> PublicationAuthoringInput:
    payload = {
        "source_research_snapshot_id": "1d890f85-1bf1-5ca8-b54b-dedf338783ff",
        "reader_tension": "三花的基本面没有明显坏掉，但36.3元到底还要求机器人和液冷兑现多少利润？",
        "headline_question": "跌跌不休的三花智控，36.3元贵不贵？",
        "opening_contradiction": "股价持续回落，但核心经营和现金流仍有韧性，新业务也已经进入商业化阶段。",
        "selected_claims": [
            "H1 revenue was about CNY16.9bn, deducted profit CNY2.15bn and OCF CNY2.50bn.",
            "Post-H1 2027 forecasts cluster around CNY5.26-5.77bn.",
            "Robot actuators were progressing through batch delivery/ramp; liquid-cooling products had some global customer supply.",
            "Core growth is not hypergrowth and new-business economics remain unquantified.",
            "CICC cut 2027 profit to CNY5.422bn for slower automotive growth; A/H 2027 PE context was about 28x/17x.",
        ],
        "evidence_clearance": {
            str(E_H1): "PUBLIC_SAFE",
            str(E_CONSENSUS): "PUBLIC_SAFE",
            str(E_ROBOT): "PUBLIC_SAFE",
            str(E_LIQUID): "PUBLIC_SAFE",
        },
        "strongest_counterpoint": "如果三花核心业务本身就值得长期高估值，那么当前价格未必需要机器人贡献大量利润才能成立。",
        "editorial_verdict": "不要用跌幅判断便宜；先反推36.3元已经把多少核心业务质量和新业务兑现写进价格。",
        "price_anchor": "CNY 36.3 — Human-provided publication anchor; verify against live market before publishing.",
        "style_sample_ids": ["hengtong_58", "gigadevice_48_5", "shengyi_3213"],
        "target_cards": 9,
    }
    payload.update(updates)
    return PublicationAuthoringInput.model_validate(payload)


def test_build_harness_bundle_is_bound_to_exact_research_and_public_claims() -> None:
    bundle = build_harness_bundle(_package(), _authoring())

    assert bundle.brief.ticker == "002050"
    assert bundle.brief.company_name == "三花智控"
    assert len(bundle.brief.claims) == 5
    assert len(bundle.brief.source_package_hash) == 64
    assert bundle.brief.human_state_policy == "OMIT"
    assert "36.3" in bundle.planner_prompt
    assert "PLANNER_OUTPUT_JSON" in bundle.drafting_prompt
    assert "当前价格要求什么成立" in bundle.judge_prompt


def test_publication_rejects_claim_not_present_in_research() -> None:
    authoring = _authoring(
        selected_claims=[
            "H1 revenue was about CNY16.9bn, deducted profit CNY2.15bn and OCF CNY2.50bn.",
            "Post-H1 2027 forecasts cluster around CNY5.26-5.77bn.",
            "机器人明年一定贡献十亿元利润。",
        ]
    )

    with pytest.raises(DomainValidationError, match="exact Research claim"):
        build_harness_bundle(_package(), authoring)


def test_publication_fails_closed_when_selected_fact_is_not_public_safe() -> None:
    authoring = _authoring(
        evidence_clearance={
            E_H1: PublicationEvidenceClearance.PUBLIC_SAFE,
            E_CONSENSUS: PublicationEvidenceClearance.PUBLIC_SAFE,
            E_ROBOT: PublicationEvidenceClearance.REVIEW_REQUIRED,
            E_LIQUID: PublicationEvidenceClearance.PUBLIC_SAFE,
        }
    )

    with pytest.raises(DomainValidationError, match="not PUBLIC_SAFE"):
        build_harness_bundle(_package(), authoring)


def test_unknown_style_sample_fails_closed() -> None:
    with pytest.raises(DomainValidationError, match="unknown Xiaohongshu style sample"):
        build_harness_bundle(
            _package(),
            _authoring(style_sample_ids=["not-a-real-sample"]),
        )


def test_draft_lint_blocks_private_state_and_trade_commands() -> None:
    result = lint_publication_draft("我的仓位不大，所以建议加仓。")
    assert result.passed is False
    assert {issue.code for issue in result.issues} == {
        "HUMAN_STATE_LEAK",
        "INVESTMENT_COMMAND",
    }


def test_draft_lint_flags_research_report_dump_signal() -> None:
    result = lint_publication_draft("公司简介\n三花是一家全球热管理零部件公司。")
    assert result.passed is False
    assert result.issues[0].code == "REPORT_DUMP_SIGNAL"


def test_draft_lint_allows_plain_research_prose() -> None:
    result = lint_publication_draft(
        "36.3元并不会因为跌了很多就自动变便宜。真正要问的是，这个价格还要求哪些盈利路径成立。"
    )
    assert result.passed is True
