from __future__ import annotations

from pathlib import Path

from decision_kernel.xiaohongshu_harness import (
    DraftParagraphKind,
    XiaohongshuDraft,
    XiaohongshuDraftCard,
    XiaohongshuDraftParagraph,
    XiaohongshuPlan,
    XiaohongshuPlanCard,
    build_writing_brief,
    load_authoring_spec,
    load_deep_research_package,
)
from decision_kernel.xiaohongshu_voice_pass import (
    render_voice_rewrite_prompt,
    voice_lint,
)


ROOT = Path(__file__).resolve().parents[1]
SANHUA_RESEARCH = ROOT / "research_cases" / "002050-sanhua-deep-research-v1.json"
SANHUA_AUTHORING = ROOT / "eval" / "xiaohongshu" / "002050-sanhua-authoring-v1.json"


def _brief():
    return build_writing_brief(
        load_deep_research_package(SANHUA_RESEARCH),
        load_authoring_spec(SANHUA_AUTHORING),
    )


def _plan(brief):
    return XiaohongshuPlan(
        schema_version=1,
        reader_tension=brief.reader_tension,
        title_candidates=(
            "跌跌不休的三花智控，36.3元贵不贵？",
            "三花36.3元，市场还在押什么？",
            "三花跌到36.3元以后，真的便宜了吗？",
        ),
        cards=tuple(
            XiaohongshuPlanCard(
                card_number=index,
                job=f"job {index}",
                turn=f"turn {index}",
                claim_ids=(),
            )
            for index in range(1, 8)
        ),
        strongest_counterpoint=None,
        final_takeaway="test",
    )


def _draft(brief, *, text: str):
    return XiaohongshuDraft(
        schema_version=1,
        title="跌跌不休的三花智控，36.3元贵不贵？",
        reader_tension=brief.reader_tension,
        cards=tuple(
            XiaohongshuDraftCard(
                card_number=index,
                heading=None,
                paragraphs=(
                    XiaohongshuDraftParagraph(
                        text=text,
                        kind=DraftParagraphKind.EDITORIAL,
                        claim_ids=(),
                    ),
                ),
            )
            for index in range(1, 8)
        ),
        final_takeaway="test",
    )


def test_voice_lint_catches_repeated_template_transitions() -> None:
    brief = _brief()
    report = voice_lint(_draft(brief, text="真正的问题是，这一段仍在机械总结。"))

    assert report.status == "REVISE"
    assert any(issue.code == "REPEATED_TEMPLATE_TRANSITIONS" for issue in report.issues)


def test_voice_lint_catches_repeated_not_but_scaffolding() -> None:
    brief = _brief()
    report = voice_lint(
        _draft(
            brief,
            text="不是机器人空间有多大，而是现在付了多少钱。不是故事真不真，而是利润何时出现。",
        )
    )

    assert report.status == "REVISE"
    assert any(issue.code == "REPEATED_NOT_BUT_CONTRAST" for issue in report.issues)


def test_voice_lint_catches_invented_author_backstory() -> None:
    brief = _brief()
    report = voice_lint(_draft(brief, text="我最近重新看三花，和以前不太一样。"))

    assert report.status == "REVISE"
    assert any(issue.code == "INVENTED_AUTHOR_BACKSTORY" for issue in report.issues)


def test_voice_rewrite_prompt_uses_real_sentence_anchors_and_preserves_authority() -> None:
    brief = _brief()
    draft = _draft(brief, text="这一页只推进同一个问题。")
    prompt = render_voice_rewrite_prompt(brief, _plan(brief), draft)
    normalized = " ".join(prompt.split())

    assert "真正的问题，不是能不能暴利。而是能暴利多久" in prompt
    assert "产品目录只能证明" in prompt
    assert "Keep every paragraph's `kind` and `claim_ids` exactly unchanged" in prompt
    assert "Do not force every idea into balanced A/B symmetry" in prompt
    assert "First-person memory is evidence too" in prompt
    assert "Treat “不是A，而是B” as a high-cost rhetorical device" in prompt
    assert "30倍可能不应该被当成常态估值" in prompt
    assert "Do not turn the ending into a generic lesson about investing" in normalized
