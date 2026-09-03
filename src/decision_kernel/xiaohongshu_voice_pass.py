from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field

from .primitives import KernelModel
from .xiaohongshu_harness import (
    XiaohongshuDraft,
    XiaohongshuPlan,
    XiaohongshuWritingBrief,
    load_style_sample_bank,
)


class VoiceLintIssue(KernelModel):
    code: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1)


class VoiceLintReport(KernelModel):
    status: Literal["PASS", "REVISE"]
    issues: tuple[VoiceLintIssue, ...]


_TEMPLATE_TRANSITIONS = (
    "真正的问题是",
    "换句话说",
    "这意味着",
    "我的结论是",
    "所以现在",
    "这里就",
    "这时候",
)

_VISIBLE_HARNESS_LANGUAGE = (
    "核心张力",
    "reader tension",
    "proof ladder",
    "PUBLIC_SAFE",
    "PublicationBrief",
)


def voice_lint(draft: XiaohongshuDraft) -> VoiceLintReport:
    text = "\n".join(
        [
            draft.title,
            draft.final_takeaway,
            *[
                paragraph.text
                for card in draft.cards
                for paragraph in card.paragraphs
            ],
        ]
    )
    issues: list[VoiceLintIssue] = []

    counts = Counter(
        marker for marker in _TEMPLATE_TRANSITIONS for _ in range(text.count(marker))
    )
    repeated = [marker for marker, count in counts.items() if count >= 3]
    if repeated:
        issues.append(
            VoiceLintIssue(
                code="REPEATED_TEMPLATE_TRANSITIONS",
                message=(
                    "Repeated transition scaffolding makes the draft sound model-generated: "
                    + ", ".join(repeated)
                ),
            )
        )

    leaked = [marker for marker in _VISIBLE_HARNESS_LANGUAGE if marker in text]
    if leaked:
        issues.append(
            VoiceLintIssue(
                code="VISIBLE_HARNESS_LANGUAGE",
                message=(
                    "Draft exposes internal writing-harness vocabulary instead of natural prose: "
                    + ", ".join(leaked)
                ),
            )
        )

    return VoiceLintReport(
        status="REVISE" if issues else "PASS",
        issues=tuple(issues),
    )


def _sentence_anchors() -> str:
    bank = load_style_sample_bank()
    blocks: list[str] = []
    for sample in bank.samples:
        if sample.performance_label != "HIGH_READ":
            continue
        anchors = [
            item.removeprefix("句子级节奏：")
            for item in sample.reusable_lessons
            if item.startswith("句子级节奏：")
        ]
        if not anchors:
            continue
        blocks.append(
            f"### {sample.company}\n" + "\n".join(f"- {anchor}" for anchor in anchors)
        )
    return "\n\n".join(blocks)


def render_voice_rewrite_prompt(
    brief: XiaohongshuWritingBrief,
    plan: XiaohongshuPlan,
    draft: XiaohongshuDraft,
) -> str:
    """Render a style-only rewrite pass after factual/structural drafting.

    This pass may change prose rhythm, headings and title wording, but it may not add Research,
    arithmetic, authority or claim references. Claim ids and paragraph kinds remain fixed so the
    rewritten result can go back through the existing deterministic validator.
    """

    lint = voice_lint(draft)
    return f"""You are the VOICE REWRITER in a Xiaohongshu public-equity writing harness.

The first draft is logically acceptable but sounds too much like an AI completing a rubric.
Rewrite for natural Human author voice WITHOUT doing new Research.

Hard invariants:
- Investment Authority = NONE.
- Do not add, delete, swap, or infer claim_ids.
- Keep every paragraph's `kind` and `claim_ids` exactly unchanged.
- Keep the same card count and card numbers.
- Do not add a number, source, probability, market fact, company fact, recommendation, position,
  Human Decision, or arithmetic that is not already present in the draft.
- You may change title wording, headings, paragraph wording, paragraph order *within the same card*,
  and final_takeaway wording only when factual meaning and authority remain unchanged.

The main failure to fix is AI voice, not investment logic.

Anti-AI voice rules:
- Do not make every paragraph feel like it is closing a checklist item.
- Do not repeatedly use stock transitions such as “真正的问题是”, “换句话说”, “这意味着”,
  “所以现在”, “这里就”, or “我的结论是”. One natural use is fine; repeated scaffolding is not.
- Do not force every idea into balanced A/B symmetry, two-line slogans, or “如果A/如果B”的机械对照.
- Do not end every section with a mini-summary. Let some sections simply move the thought forward.
- Do not expose the harness's internal vocabulary: reader tension, proof ladder, claim authority,
  PUBLIC_SAFE, PublicationBrief, or similar meta-language.
- The proof ladder stays in the author's head. In prose, write the concrete missing step instead of
  announcing a framework.
- Prefer the rhythm visible in the Human references: state one concrete fact, say what it changes,
  then keep digging. The article should sound like a person thinking through a stock, not a model
  teaching an investing method.
- Uneven paragraph lengths are fine. A short sentence should earn its emphasis; do not manufacture
  a punchline every three lines.
- Use first-person judgment sparingly and specifically (“我更倾向于…”, “我现在更关心…”), not as
  a repeated author-brand device.
- Keep the article focused on the company and the price. Do not turn the ending into a generic lesson
  about investing.

Sentence-level rhythm anchors from the Human's actual high-read notes. Learn the cadence and move;
do NOT copy sentences or metaphors mechanically:
{_sentence_anchors()}

VOICE LINT ON CURRENT DRAFT:
{lint.model_dump_json(indent=2)}

BRIEF (truth boundary):
{brief.model_dump_json(indent=2)}

PLAN (argument boundary):
{plan.model_dump_json(indent=2)}

CURRENT DRAFT:
{draft.model_dump_json(indent=2)}

Return STRICT JSON matching the existing XiaohongshuDraft schema. Preserve every card number,
paragraph kind, and claim_ids exactly. Only rewrite the user-visible prose.
"""
