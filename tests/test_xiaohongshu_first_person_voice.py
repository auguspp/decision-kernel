from pathlib import Path

from decision_kernel.xiaohongshu_harness import (
    DraftParagraphKind,
    XiaohongshuDraft,
    XiaohongshuDraftCard,
    XiaohongshuDraftParagraph,
    build_writing_brief,
    load_authoring_spec,
    load_deep_research_package,
)
from decision_kernel.xiaohongshu_voice_pass import voice_lint

ROOT = Path(__file__).resolve().parents[1]
SANHUA_RESEARCH = ROOT / "research_cases" / "002050-sanhua-deep-research-v1.json"
SANHUA_AUTHORING = ROOT / "eval" / "xiaohongshu" / "002050-sanhua-authoring-v1.json"


def _draft(text: str) -> XiaohongshuDraft:
    brief = build_writing_brief(
        load_deep_research_package(SANHUA_RESEARCH),
        load_authoring_spec(SANHUA_AUTHORING),
    )
    cards = tuple(
        XiaohongshuDraftCard(
            card_number=i,
            paragraphs=(
                XiaohongshuDraftParagraph(
                    text=text if i == 1 else "继续推进同一个问题。",
                    kind=DraftParagraphKind.EDITORIAL,
                ),
            ),
        )
        for i in range(1, 8)
    )
    return XiaohongshuDraft(
        schema_version=1,
        title="三花36.3元贵不贵？",
        reader_tension=brief.reader_tension,
        cards=cards,
        final_takeaway="看主业价值和未来预付款。",
    )


def test_unnecessary_first_person_emphasis_is_revise_signal() -> None:
    report = voice_lint(_draft("这才是我觉得36.3元最关键的地方。"))
    assert report.status == "REVISE"
    assert any(issue.code == "UNNECESSARY_FIRST_PERSON" for issue in report.issues)


def test_first_person_process_narration_is_revise_signal() -> None:
    report = voice_lint(_draft("所以这次我重新拆了一遍。"))
    assert report.status == "REVISE"
    assert any(issue.code == "UNNECESSARY_FIRST_PERSON" for issue in report.issues)
