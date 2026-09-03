from __future__ import annotations

from pathlib import Path

import pytest

from decision_kernel.primitives import DomainValidationError
from decision_kernel.xiaohongshu_harness import (
    DraftParagraphKind,
    PublicationClaim,
    PublicationClaimKind,
    ValidationStatus,
    XiaohongshuDraft,
    XiaohongshuDraftCard,
    XiaohongshuDraftParagraph,
    XiaohongshuPlan,
    XiaohongshuPlanCard,
    build_claim_catalog,
    build_writing_brief,
    load_authoring_spec,
    load_deep_research_package,
    load_style_sample_bank,
    render_planner_prompt,
    validate_draft,
    validate_plan,
)


ROOT = Path(__file__).resolve().parents[1]
SANHUA_RESEARCH = ROOT / "research_cases" / "002050-sanhua-deep-research-v1.json"
SANHUA_AUTHORING = ROOT / "eval" / "xiaohongshu" / "002050-sanhua-authoring-v1.json"


def _brief():
    return build_writing_brief(
        load_deep_research_package(SANHUA_RESEARCH),
        load_authoring_spec(SANHUA_AUTHORING),
    )


def _seven_card_draft(*, text: str = "这一页只推进同一个定价问题。") -> XiaohongshuDraft:
    brief = _brief()
    cards = tuple(
        XiaohongshuDraftCard(
            card_number=index,
            heading=f"第{index}步",
            paragraphs=(
                XiaohongshuDraftParagraph(
                    text=text,
                    kind=DraftParagraphKind.EDITORIAL,
                    claim_ids=(),
                ),
            ),
        )
        for index in range(1, 8)
    )
    return XiaohongshuDraft(
        schema_version=1,
        title="跌跌不休的三花智控，36.3元贵不贵？",
        reader_tension=brief.reader_tension,
        cards=cards,
        final_takeaway="真正需要验证的是当前价格要求的新业务利润能否逐层兑现。",
    )


def test_style_bank_keeps_positive_and_negative_calibration() -> None:
    bank = load_style_sample_bank()
    labels = {sample.sample_id: sample.performance_label for sample in bank.samples}

    assert bank.profile_id == "xiaohongshu-investment-v1"
    assert labels["hengtong-expectation-repricing"] == "HIGH_READ"
    assert labels["demingli-overloaded-negative"] == "LOW_READ"
    assert "dongshan-earnings-path-reunderwrite" in labels
    assert "shengyi-sotp-implied-earnings" in labels


def test_real_sanhua_package_projects_only_explicit_public_claims() -> None:
    package = load_deep_research_package(SANHUA_RESEARCH)
    authoring = load_authoring_spec(SANHUA_AUTHORING)
    catalog = build_claim_catalog(package)
    brief = build_writing_brief(package, authoring)

    assert brief.investment_authority == "NONE"
    assert brief.human_state_policy == "OMIT"
    assert [claim.claim_id for claim in brief.selected_claims] == list(authoring.public_claim_ids)
    assert set(authoring.public_claim_ids).issubset(catalog)
    assert len(catalog) > len(brief.selected_claims)


def test_planner_prompt_uses_new_human_calibration_not_old_three_question_limit() -> None:
    prompt = render_planner_prompt(_brief())

    assert 'supersedes the old "maximum three sub-questions" heuristic' in prompt
    assert "Target 7-13 cards" in prompt
    assert "capability -> demand -> order -> revenue -> margin -> durable profit" in prompt
    assert "Human Decision / Action / position / cost basis are OMIT" in prompt


def test_unknown_research_claim_fails_closed() -> None:
    package = load_deep_research_package(SANHUA_RESEARCH)
    authoring = load_authoring_spec(SANHUA_AUTHORING)
    payload = authoring.model_dump(mode="python")
    payload["public_claim_ids"] = (*authoring.public_claim_ids, "deep.999")

    with pytest.raises(DomainValidationError, match="unknown Research claims"):
        build_writing_brief(package, authoring.__class__.model_validate(payload))


def test_plan_cannot_reference_claims_outside_publication_brief() -> None:
    brief = _brief()
    plan = XiaohongshuPlan(
        schema_version=1,
        reader_tension=brief.reader_tension,
        title_candidates=(
            "跌跌不休的三花智控，36.3元贵不贵？",
            "机器人开始批量交付，三花现在贵不贵？",
            "核心业务稳，新业务起量：三花的价格在押什么？",
        ),
        cards=tuple(
            XiaohongshuPlanCard(
                card_number=index,
                job=f"job {index}",
                turn=f"turn {index}",
                claim_ids=("deep.999",) if index == 4 else (),
            )
            for index in range(1, 8)
        ),
        strongest_counterpoint=None,
        final_takeaway="test",
    )

    report = validate_plan(plan, brief)

    assert report.status is ValidationStatus.FAIL
    assert any(issue.code == "UNKNOWN_PLAN_CLAIM" for issue in report.issues)


def test_structured_draft_passes_when_it_preserves_authority_boundary() -> None:
    report = validate_draft(_seven_card_draft(), _brief())

    assert report.status is ValidationStatus.PASS
    assert not [issue for issue in report.issues if issue.severity.value == "BLOCK"]


def test_fact_paragraph_cannot_upgrade_inference_to_fact() -> None:
    brief = _brief()
    synthetic_inference = PublicationClaim(
        claim_id="test.inference",
        kind=PublicationClaimKind.INFERENCE,
        text="测试用研究推断。",
        origin="test",
    )
    brief = brief.model_copy(
        update={"selected_claims": (*brief.selected_claims, synthetic_inference)}
    )
    draft = _seven_card_draft()
    cards = list(draft.cards)
    cards[0] = XiaohongshuDraftCard(
        card_number=1,
        heading="错误升级",
        paragraphs=(
            XiaohongshuDraftParagraph(
                text="把研究推断写成了公司事实。",
                kind=DraftParagraphKind.FACT,
                claim_ids=(synthetic_inference.claim_id,),
            ),
        ),
    )

    report = validate_draft(draft.model_copy(update={"cards": tuple(cards)}), brief)

    assert report.status is ValidationStatus.FAIL
    assert any(issue.code == "FACT_AUTHORITY_UPGRADE" for issue in report.issues)


def test_human_position_and_recommendation_language_are_blocked() -> None:
    brief = _brief()
    draft = _seven_card_draft(text="我决定买入并加仓，这里建议买入。")

    report = validate_draft(draft, brief)
    codes = {issue.code for issue in report.issues}

    assert report.status is ValidationStatus.FAIL
    assert "HUMAN_STATE_LEAK" in codes
    assert "RECOMMENDATION_LANGUAGE" in codes
