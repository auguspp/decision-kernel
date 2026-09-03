from __future__ import annotations

from collections import Counter
import re
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

_AUTHOR_BACKSTORY_SCAFFOLD = (
    "我最近重新看",
    "和以前不太一样",
    "我一开始也",
    "以前我觉得",
    "之前我觉得",
)

_NOT_BUT_RE = re.compile(r"不是[^。！？\n]{0,96}而是")


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

    not_but_count = len(_NOT_BUT_RE.findall(text))
    if not_but_count >= 2:
        issues.append(
            VoiceLintIssue(
                code="REPEATED_NOT_BUT_CONTRAST",
                message=(
                    "Repeated 不是…而是… contrast is functioning as AI scaffolding; "
                    "prefer direct statements or delete the setup."
                ),
            )
        )

    backstory = [marker for marker in _AUTHOR_BACKSTORY_SCAFFOLD if marker in text]
    if backstory:
        issues.append(
            VoiceLintIssue(
                code="INVENTED_AUTHOR_BACKSTORY",
                message=(
                    "Draft appears to manufacture a prior author stance or review history: "
                    + ", ".join(backstory)
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
- Delete sentences that merely announce what the author is about to investigate when the next
  paragraph can simply investigate it. Do not narrate the writing process.
- Do not invent author history. Never write things like “我最近重新看…”, “这和我以前的看法不太一样”,
  “我一开始也这么想”, or imply a previous stance unless that prior stance is explicitly supplied
  in BRIEF or PLAN. First-person memory is evidence too; do not fabricate it for warmth.
- Do not make every paragraph feel like it is closing a checklist item.
- Do not repeatedly use stock transitions such as “真正的问题是”, “换句话说”, “这意味着”,
  “所以现在”, “这里就”, or “我的结论是”. One natural use is fine; repeated scaffolding is not.
- Treat “不是A，而是B” as a high-cost rhetorical device, not a default transition. If B can stand
  alone, write B directly. More than one such contrast in a note is usually a rewrite signal.
- Do not force every idea into balanced A/B symmetry, two-line slogans, or “如果A/如果B”的机械对照.
- Do not end every section with a mini-summary. Let some sections simply move the thought forward.
- Prefer direct section questions over pseudo-personal headings. For example, “所以，如何看待未来？”
  is usually cleaner than “我现在更偏向哪边？”, unless the Human explicitly asked for a personal
  position update.
- When making a valuation judgment, state the judgment directly. “30倍可能不应该被当成常态估值”
  is better than manufacturing a personal preamble such as “我不太愿意把30倍直接当成…”.
- Do not expose the harness's internal vocabulary: reader tension, proof ladder, claim authority,
  PUBLIC_SAFE, PublicationBrief, or similar meta-language.
- The proof ladder stays in the author's head. In prose, write the concrete missing step instead of
  announcing a framework.
- Prefer the rhythm visible in the Human references: state one concrete fact, say what it changes,
  then keep digging. The article should sound like a person thinking through a stock, not a model
  teaching an investing method.
- Uneven paragraph lengths are fine. A short sentence should earn its emphasis; do not manufacture
  a punchline every three lines.
- Use first-person judgment only when it adds information that cannot be stated more cleanly as a
  direct judgment. Do not use first person as an authenticity costume.
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