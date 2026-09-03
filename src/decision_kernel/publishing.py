from __future__ import annotations

import argparse
import json
from enum import StrEnum
from importlib.resources import files
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .deep_research import (
    DeepResearchPackage,
    ResearchMethodV1AcceptanceStatus,
    assess_research_method_v1_acceptance,
    deep_research_package_hash,
)
from .primitives import DomainValidationError, KernelModel
from .research_funnel import ResearchClaim, ResearchClaimKind


STYLE_POLICY_RESOURCE = "policy_data/xiaohongshu_harness_v1.json"


class PublicationEvidenceClearance(StrEnum):
    PUBLIC_SAFE = "PUBLIC_SAFE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    DO_NOT_PUBLISH = "DO_NOT_PUBLISH"


class PublicationClaim(KernelModel):
    statement: str = Field(min_length=1)
    kind: ResearchClaimKind
    evidence_artifact_ids: tuple[UUID, ...] = ()
    source_locators: tuple[str, ...] = ()


class PublicationAuthoringInput(KernelModel):
    source_research_snapshot_id: UUID
    reader_tension: str = Field(min_length=1)
    headline_question: str = Field(min_length=1)
    opening_contradiction: str = Field(min_length=1)
    selected_claims: tuple[str, ...] = Field(min_length=3, max_length=10)
    evidence_clearance: dict[UUID, PublicationEvidenceClearance]
    strongest_counterpoint: str = Field(min_length=1)
    editorial_verdict: str = Field(min_length=1)
    price_anchor: str | None = None
    style_sample_ids: tuple[str, ...] = Field(default=(), max_length=3)
    target_cards: int = Field(default=8, ge=6, le=13)
    human_state_policy: Literal["OMIT"] = "OMIT"
    schema_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_unique_claims(self) -> "PublicationAuthoringInput":
        if len(set(self.selected_claims)) != len(self.selected_claims):
            raise ValueError("selected publication claims must be unique")
        if len(set(self.style_sample_ids)) != len(self.style_sample_ids):
            raise ValueError("style sample ids must be unique")
        return self


class PublicationBrief(KernelModel):
    source_research_snapshot_id: UUID
    source_package_hash: str = Field(min_length=64, max_length=64)
    source_as_of: str
    ticker: str
    company_name: str
    reader_tension: str
    headline_question: str
    opening_contradiction: str
    claims: tuple[PublicationClaim, ...]
    strongest_counterpoint: str
    editorial_verdict: str
    price_anchor: str | None = None
    style_sample_ids: tuple[str, ...] = ()
    target_cards: int
    human_state_policy: Literal["OMIT"] = "OMIT"
    schema_version: Literal[1] = 1


class HarnessBundle(KernelModel):
    brief: PublicationBrief
    planner_prompt: str
    drafting_prompt: str
    judge_prompt: str
    schema_version: Literal[1] = 1


class DraftLintIssue(KernelModel):
    code: str
    message: str


class DraftLintResult(KernelModel):
    passed: bool
    issues: tuple[DraftLintIssue, ...]


_PORTFOLIO_STATE_MARKERS = (
    "我持有",
    "我的持仓",
    "我的仓位",
    "我的成本",
    "成本价",
    "我已经买",
    "我买入了",
    "我卖出了",
)

_INVESTMENT_COMMAND_MARKERS = (
    "建议买入",
    "建议卖出",
    "建议加仓",
    "建议减仓",
)

_GENERIC_REPORT_HEADINGS = (
    "公司简介",
    "行业概况",
    "竞争格局",
    "核心竞争力",
)


def load_style_policy() -> dict:
    try:
        raw = files("decision_kernel").joinpath(STYLE_POLICY_RESOURCE).read_text(
            encoding="utf-8"
        )
        payload = json.loads(raw)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise DomainValidationError("Xiaohongshu style policy is unavailable or invalid") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise DomainValidationError("Xiaohongshu style policy schema is unsupported")
    return payload


def _research_claims(package: DeepResearchPackage) -> tuple[ResearchClaim, ...]:
    claims: list[ResearchClaim] = []
    for observation in package.discovery.factual_observations:
        claims.append(
            ResearchClaim(
                statement=observation.statement,
                kind=ResearchClaimKind.FACT,
                evidence_artifact_ids=observation.evidence_artifact_ids,
            )
        )
    claims.extend(package.pre_research.material_claims)
    claims.extend(package.quick_research.supporting_claims)
    claims.extend(package.quick_research.contradictory_claims)
    claims.extend(package.deep_research.material_claims)

    deduped: dict[tuple[str, ResearchClaimKind, tuple[UUID, ...]], ResearchClaim] = {}
    for claim in claims:
        key = (claim.statement, claim.kind, claim.evidence_artifact_ids)
        deduped[key] = claim
    return tuple(deduped.values())


def build_publication_brief(
    package: DeepResearchPackage,
    authoring: PublicationAuthoringInput,
) -> PublicationBrief:
    assessment = assess_research_method_v1_acceptance(package)
    if assessment.status is not ResearchMethodV1AcceptanceStatus.ACCEPTED:
        codes = ", ".join(issue.code for issue in assessment.issues)
        raise DomainValidationError(
            f"publication requires an accepted Research Method v1 package: {codes}"
        )

    snapshot = package.research_snapshot
    if authoring.source_research_snapshot_id != snapshot.id:
        raise DomainValidationError("publication input changed ResearchSnapshot identity")

    artifacts = {artifact.id: artifact for artifact in package.evidence_artifacts}
    unknown_clearance = set(authoring.evidence_clearance) - set(artifacts)
    if unknown_clearance:
        raise DomainValidationError("publication clearance references unknown evidence")

    candidates: dict[str, list[ResearchClaim]] = {}
    for claim in _research_claims(package):
        candidates.setdefault(claim.statement, []).append(claim)

    selected: list[PublicationClaim] = []
    for statement in authoring.selected_claims:
        matches = candidates.get(statement, [])
        if not matches:
            raise DomainValidationError(
                "publication claim must be an exact Research claim: " + statement
            )
        signatures = {
            (claim.kind, claim.evidence_artifact_ids)
            for claim in matches
        }
        if len(signatures) != 1:
            raise DomainValidationError(
                "publication claim is ambiguous across Research states: " + statement
            )
        claim = matches[0]
        locators: list[str] = []
        for evidence_id in claim.evidence_artifact_ids:
            clearance = authoring.evidence_clearance.get(
                evidence_id, PublicationEvidenceClearance.REVIEW_REQUIRED
            )
            if clearance is not PublicationEvidenceClearance.PUBLIC_SAFE:
                raise DomainValidationError(
                    "selected claim uses evidence that is not PUBLIC_SAFE: " + statement
                )
            locators.append(artifacts[evidence_id].source_locator)
        selected.append(
            PublicationClaim(
                statement=claim.statement,
                kind=claim.kind,
                evidence_artifact_ids=claim.evidence_artifact_ids,
                source_locators=tuple(locators),
            )
        )

    policy = load_style_policy()
    known_sample_ids = {sample["id"] for sample in policy.get("samples", [])}
    unknown_samples = set(authoring.style_sample_ids) - known_sample_ids
    if unknown_samples:
        raise DomainValidationError(
            "unknown Xiaohongshu style sample ids: " + ", ".join(sorted(unknown_samples))
        )

    return PublicationBrief(
        source_research_snapshot_id=snapshot.id,
        source_package_hash=deep_research_package_hash(package),
        source_as_of=snapshot.as_of_datetime.isoformat(),
        ticker=snapshot.ticker,
        company_name=snapshot.company_name,
        reader_tension=authoring.reader_tension,
        headline_question=authoring.headline_question,
        opening_contradiction=authoring.opening_contradiction,
        claims=tuple(selected),
        strongest_counterpoint=authoring.strongest_counterpoint,
        editorial_verdict=authoring.editorial_verdict,
        price_anchor=authoring.price_anchor,
        style_sample_ids=authoring.style_sample_ids,
        target_cards=authoring.target_cards,
    )


def _selected_style_notes(brief: PublicationBrief, policy: dict) -> str:
    samples = {sample["id"]: sample for sample in policy.get("samples", [])}
    selected_ids = brief.style_sample_ids or tuple(samples)[:3]
    blocks: list[str] = []
    for sample_id in selected_ids:
        sample = samples[sample_id]
        moves = "\n".join(f"- {move}" for move in sample["signature_moves"])
        blocks.append(
            f"### {sample['label']}\n"
            f"核心张力：{sample['central_tension']}\n"
            f"开篇动作：{sample['opening_move']}\n"
            f"收尾动作：{sample['closing_move']}\n"
            f"可复用动作：\n{moves}"
        )
    return "\n\n".join(blocks)


def render_planner_prompt(brief: PublicationBrief) -> str:
    policy = load_style_policy()
    global_rules = "\n".join(f"- {rule}" for rule in policy["global_rules"])
    sample_notes = _selected_style_notes(brief, policy)
    claim_lines = "\n".join(
        f"- [{claim.kind}] {claim.statement}" for claim in brief.claims
    )
    return f"""你是小红书投资研究笔记的结构规划器。你不负责重新研究公司，只负责把已经冻结的 Research 压成一篇可读文章。\n\n唯一核心张力：{brief.reader_tension}\n标题问题：{brief.headline_question}\n开篇矛盾：{brief.opening_contradiction}\n价格锚：{brief.price_anchor or '无'}\n结论边界：{brief.editorial_verdict}\n最强反方：{brief.strongest_counterpoint}\n目标卡片数：{brief.target_cards}\n\n允许使用的 Research claim：\n{claim_lines}\n\n全局写作规则：\n{global_rules}\n\n真实高阅读样本的结构指纹：\n{sample_notes}\n\n请只输出 JSON，不写正文。Schema：\n{{\n  \"title_candidates\": [\"3-5个标题\"],\n  \"one_sentence_argument\": \"全文只证明这一句话\",\n  \"cards\": [\n    {{\"card\": 1, \"job\": \"这一页只完成什么\", \"claims\": [\"只能引用上面的claim\"], \"turn\": \"这一页如何把读者推向下一页\"}}\n  ],\n  \"final_answer\": \"对标题问题的明确回答\",\n  \"unresolved_uncertainty\": \"仍然不能假装知道什么\"\n}}\n\n硬约束：一个 reader tension；研究目录不能直接变成文章目录；不要平均分配事实；不要引入 Human Decision / Action / 持仓；不要把 INFERENCE 写成公司确认的 FACT。"""


def render_drafting_prompt(brief: PublicationBrief) -> str:
    policy = load_style_policy()
    global_rules = "\n".join(f"- {rule}" for rule in policy["global_rules"])
    sample_notes = _selected_style_notes(brief, policy)
    claims_json = json.dumps(
        [claim.model_dump(mode="json") for claim in brief.claims],
        ensure_ascii=False,
        indent=2,
    )
    return f"""根据 PublicationBrief 和规划 JSON 写小红书正文。\n\n<PLANNER_OUTPUT_JSON>\n{{{{PLANNER_OUTPUT_JSON}}}}\n</PLANNER_OUTPUT_JSON>\n\nResearch PIT：{brief.source_as_of}\n公司：{brief.company_name} / {brief.ticker}\n核心张力：{brief.reader_tension}\n标题问题：{brief.headline_question}\n价格锚：{brief.price_anchor or '无'}\n最强反方：{brief.strongest_counterpoint}\n作者最终倾向：{brief.editorial_verdict}\n目标卡片：{brief.target_cards}\n\n允许公开的 claim ledger：\n{claims_json}\n\n写作规则：\n{global_rules}\n\n风格校准：\n{sample_notes}\n\n要求：\n- 直接进入矛盾，不写公司百科。\n- 文章前 20% 内必须让读者知道“价格正在要求公司证明什么”。\n- 数字只服务于反推、因果或情景，不做数据堆砌。\n- 可以有明确个人判断，不要为了显得客观而把所有情景写成等权。\n- 最强反方必须被认真处理，不能稻草人化。\n- FACT / MARKET_CONTEXT / INFERENCE / ASSUMPTION 的语气必须不同。\n- 不能公开或猜测 Human Decision、Human Action、仓位、成本。\n- 禁止写“建议买入/卖出/加仓/减仓”。\n- 不要 emoji，不要营销腔，不要“公司简介/行业概况/核心竞争力”式研报目录。\n- 结尾回答标题问题，并明确还缺哪一条证据。\n\n只输出成稿。"""


def render_judge_prompt(brief: PublicationBrief) -> str:
    policy = load_style_policy()
    rubric = "\n".join(
        f"{index + 1}. {item}" for index, item in enumerate(policy["judge_rubric"])
    )
    return f"""你是这篇小红书投资研究笔记的严格编辑。目标不是夸文笔，而是判断它能不能像作者真实高阅读文章一样，把一个价格矛盾讲透。\n\n核心张力：{brief.reader_tension}\n标题问题：{brief.headline_question}\n作者最终倾向：{brief.editorial_verdict}\n\n<DRAFT>\n{{{{DRAFT}}}}\n</DRAFT>\n\n逐项打 0-2 分：\n{rubric}\n\n另外执行三个一票否决：\n- 出现 Research 中没有依据的公司事实或把推断升级为事实；\n- 泄露/猜测 Human Decision、Action、仓位、成本，或给出交易指令；\n- 全文没有真正回答“当前价格要求什么成立”。\n\n只输出 JSON：\n{{\n  \"scores\": {{\"rubric_item\": 0}},\n  \"hard_fail\": false,\n  \"hard_fail_reasons\": [],\n  \"most_ai_like_paragraph\": \"最像AI总结的段落\",\n  \"missing_causal_link\": \"最缺的一段因果\",\n  \"rewrite_instructions\": [\"最多5条，必须具体到怎么改\"],\n  \"verdict\": \"PASS 或 REWRITE\"\n}}"""


def build_harness_bundle(
    package: DeepResearchPackage,
    authoring: PublicationAuthoringInput,
) -> HarnessBundle:
    brief = build_publication_brief(package, authoring)
    return HarnessBundle(
        brief=brief,
        planner_prompt=render_planner_prompt(brief),
        drafting_prompt=render_drafting_prompt(brief),
        judge_prompt=render_judge_prompt(brief),
    )


def lint_publication_draft(draft: str) -> DraftLintResult:
    issues: list[DraftLintIssue] = []
    for marker in _PORTFOLIO_STATE_MARKERS:
        if marker in draft:
            issues.append(
                DraftLintIssue(
                    code="HUMAN_STATE_LEAK",
                    message=f"draft contains private Human-state marker: {marker}",
                )
            )
    for marker in _INVESTMENT_COMMAND_MARKERS:
        if marker in draft:
            issues.append(
                DraftLintIssue(
                    code="INVESTMENT_COMMAND",
                    message=f"draft contains investment command: {marker}",
                )
            )
    for heading in _GENERIC_REPORT_HEADINGS:
        if heading in draft:
            issues.append(
                DraftLintIssue(
                    code="REPORT_DUMP_SIGNAL",
                    message=f"draft uses generic research-report heading: {heading}",
                )
            )
    if len(draft) > 12000:
        issues.append(
            DraftLintIssue(
                code="DRAFT_TOO_LONG",
                message="draft exceeds 12,000 characters",
            )
        )
    return DraftLintResult(passed=not issues, issues=tuple(issues))


def render_harness_markdown(bundle: HarnessBundle) -> str:
    return "\n\n".join(
        (
            "# Xiaohongshu Writing Harness v1",
            "## PublicationBrief\n\n```json\n"
            + bundle.brief.model_dump_json(indent=2)
            + "\n```",
            "## 1. Planner\n\n```text\n" + bundle.planner_prompt + "\n```",
            "## 2. Drafter\n\n```text\n" + bundle.drafting_prompt + "\n```",
            "## 3. Judge / Rewrite\n\n```text\n" + bundle.judge_prompt + "\n```",
        )
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a bounded Xiaohongshu writing harness")
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    package = DeepResearchPackage.model_validate_json(
        args.research.read_text(encoding="utf-8")
    )
    authoring = PublicationAuthoringInput.model_validate_json(
        args.input.read_text(encoding="utf-8")
    )
    bundle = build_harness_bundle(package, authoring)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_harness_markdown(bundle), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
