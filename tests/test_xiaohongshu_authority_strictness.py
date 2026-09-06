from __future__ import annotations

from pathlib import Path

import pytest

from decision_kernel.xiaohongshu_harness import (
    DraftParagraphKind,
    PublicationClaimKind,
    ValidationStatus,
    XiaohongshuDraft,
    XiaohongshuDraftCard,
    XiaohongshuDraftParagraph,
    XiaohongshuPlan,
    XiaohongshuPlanCard,
    build_writing_brief,
    load_authoring_spec,
    load_deep_research_package,
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


def _draft(card_count: int, *, first: XiaohongshuDraftParagraph | None = None) -> XiaohongshuDraft:
    brief = _brief()
    cards = []
    for index in range(1, card_count + 1):
        paragraph = first if index == 1 and first is not None else XiaohongshuDraftParagraph(
            text="这一页只推进同一个定价问题。",
            kind=DraftParagraphKind.EDITORIAL,
            claim_ids=(),
        )
        cards.append(
            XiaohongshuDraftCard(
                card_number=index,
                heading=f"第{index}步",
                paragraphs=(paragraph,),
            )
        )
    return XiaohongshuDraft(
        schema_version=1,
        title="跌跌不休的三花智控，36.3元贵不贵？",
        reader_tension=brief.reader_tension,
        cards=tuple(cards),
        final_takeaway="真正需要验证的是当前价格要求的新业务利润能否逐层兑现。",
    )


def test_inference_cannot_be_created_from_non_inference_claims_in_publishing() -> None:
    brief = _brief()
    source = next(
        claim for claim in brief.selected_claims if claim.kind is not PublicationClaimKind.INFERENCE
    )
    draft = _draft(
        7,
        first=XiaohongshuDraftParagraph(
            text="把已有事实重新组合成一个写作层新推断。",
            kind=DraftParagraphKind.INFERENCE,
            claim_ids=(source.claim_id,),
        ),
    )

    report = validate_draft(draft, brief)

    assert report.status is ValidationStatus.FAIL
    assert any(issue.code == "UNDECLARED_INFERENCE" for issue in report.issues)


def test_assumption_requires_explicit_claim_ids_at_schema_boundary() -> None:
    with pytest.raises(ValueError, match="ASSUMPTION draft paragraph requires claim_ids"):
        XiaohongshuDraftParagraph(
            text="写作层不能凭空增加一个漂亮假设。",
            kind=DraftParagraphKind.ASSUMPTION,
            claim_ids=(),
        )


def test_assumption_cannot_be_created_from_non_assumption_claims_in_publishing() -> None:
    brief = _brief()
    source = next(
        claim for claim in brief.selected_claims if claim.kind is not PublicationClaimKind.ASSUMPTION
    )
    draft = _draft(
        7,
        first=XiaohongshuDraftParagraph(
            text="把其他类型的研究输入包装成一个新假设。",
            kind=DraftParagraphKind.ASSUMPTION,
            claim_ids=(source.claim_id,),
        ),
    )

    report = validate_draft(draft, brief)

    assert report.status is ValidationStatus.FAIL
    assert any(issue.code == "UNDECLARED_ASSUMPTION" for issue in report.issues)


def test_five_card_draft_is_allowed_but_warned_as_outside_style_heuristic() -> None:
    report = validate_draft(_draft(5), _brief())

    assert report.status is ValidationStatus.PASS
    assert any(issue.code == "CARD_COUNT_OUTSIDE_HEURISTIC" for issue in report.issues)
    assert not [issue for issue in report.issues if issue.severity.value == "BLOCK"]


def test_five_card_plan_is_allowed_but_warned_as_outside_style_heuristic() -> None:
    brief = _brief()
    plan = XiaohongshuPlan(
        schema_version=1,
        reader_tension=brief.reader_tension,
        title_candidates=(
            "三花36.3元贵不贵？",
            "核心业务稳了以后，市场还在买什么？",
            "机器人开始商业化，三花的价格押了多少未来？",
        ),
        cards=tuple(
            XiaohongshuPlanCard(
                card_number=index,
                job=f"job {index}",
                turn=f"turn {index}",
                claim_ids=(),
            )
            for index in range(1, 6)
        ),
        strongest_counterpoint=None,
        final_takeaway="保持同一个读者张力。",
    )

    report = validate_plan(plan, brief)

    assert report.status is ValidationStatus.PASS
    assert any(issue.code == "CARD_COUNT_OUTSIDE_HEURISTIC" for issue in report.issues)
    assert not [issue for issue in report.issues if issue.severity.value == "BLOCK"]
