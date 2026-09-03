from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal
from enum import StrEnum
from importlib.resources import files
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .deep_research import (
    DeepResearchPackage,
    freeze_deep_research_package,
)
from .identity import canonical_hash
from .primitives import (
    AwareDateTime,
    CurrencyCode,
    DomainValidationError,
    KernelModel,
)
from .research_funnel import ResearchClaim, ResearchClaimKind


STYLE_SAMPLE_BANK_RESOURCE = "policy_data/xiaohongshu_style_sample_bank_v1.json"
STYLE_PROFILE_ID = "xiaohongshu-investment-v1"


class XiaohongshuArchetype(StrEnum):
    EXPECTATION_REPRICING = "EXPECTATION_REPRICING"
    NORMALIZED_EARNINGS = "NORMALIZED_EARNINGS"
    INDUSTRY_ODDS = "INDUSTRY_ODDS"
    IMPLIED_EARNINGS = "IMPLIED_EARNINGS"


class PublicationClaimKind(StrEnum):
    FACT = "FACT"
    MARKET_CONTEXT = "MARKET_CONTEXT"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    DERIVATION = "DERIVATION"


class DraftParagraphKind(StrEnum):
    FACT = "FACT"
    MARKET_CONTEXT = "MARKET_CONTEXT"
    INFERENCE = "INFERENCE"
    ASSUMPTION = "ASSUMPTION"
    DERIVATION = "DERIVATION"
    EDITORIAL = "EDITORIAL"


class ValidationSeverity(StrEnum):
    BLOCK = "BLOCK"
    WARN = "WARN"


class ValidationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class XiaohongshuStyleSample(KernelModel):
    sample_id: str = Field(min_length=1, max_length=128)
    company: str = Field(min_length=1, max_length=128)
    performance_label: Literal["HIGH_READ", "HUMAN_REFERENCE", "LOW_READ"]
    archetype: str = Field(min_length=1, max_length=128)
    title_pattern: str | None = None
    reusable_lessons: tuple[str, ...] = Field(min_length=1)
    failure_modes: tuple[str, ...] = ()


class XiaohongshuStyleSampleBank(KernelModel):
    schema_version: Literal[1]
    profile_id: Literal["xiaohongshu-investment-v1"]
    samples: tuple[XiaohongshuStyleSample, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "XiaohongshuStyleSampleBank":
        ids = [sample.sample_id for sample in self.samples]
        if len(ids) != len(set(ids)):
            raise ValueError("style sample ids must be unique")
        return self


class PublicationEvidenceRef(KernelModel):
    evidence_artifact_id: UUID
    source_type: str = Field(min_length=1, max_length=128)
    source_locator: str = Field(min_length=1, max_length=2048)
    available_at: AwareDateTime


class PublicationClaim(KernelModel):
    claim_id: str = Field(min_length=1, max_length=128)
    kind: PublicationClaimKind
    text: str = Field(min_length=1)
    origin: str = Field(min_length=1, max_length=128)
    evidence_refs: tuple[PublicationEvidenceRef, ...] = ()
    source_claim_ids: tuple[str, ...] = ()
    calculation_ref: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_grounding(self) -> "PublicationClaim":
        if self.kind in {
            PublicationClaimKind.FACT,
            PublicationClaimKind.MARKET_CONTEXT,
        } and not self.evidence_refs:
            raise ValueError(f"{self.kind} publication claim requires Evidence lineage")
        if self.kind is PublicationClaimKind.DERIVATION and not self.source_claim_ids:
            raise ValueError("DERIVATION publication claim requires source_claim_ids")
        return self


class XiaohongshuDerivedClaimInput(KernelModel):
    claim_id: str = Field(pattern=r"^derived\.[a-z0-9][a-z0-9._-]*$", max_length=128)
    text: str = Field(min_length=1)
    source_claim_ids: tuple[str, ...] = Field(min_length=1)
    calculation_ref: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_unique_sources(self) -> "XiaohongshuDerivedClaimInput":
        if len(self.source_claim_ids) != len(set(self.source_claim_ids)):
            raise ValueError("derived claim source ids must be unique")
        return self


class XiaohongshuMarketAnchor(KernelModel):
    price: Decimal | None = Field(default=None, gt=Decimal("0"))
    market_cap: Decimal | None = Field(default=None, gt=Decimal("0"))
    currency: CurrencyCode
    observed_at: AwareDateTime
    source_ref: str = Field(min_length=1, max_length=2048)

    @model_validator(mode="after")
    def validate_has_value(self) -> "XiaohongshuMarketAnchor":
        if self.price is None and self.market_cap is None:
            raise ValueError("market anchor requires price or market_cap")
        return self


class XiaohongshuAuthoringSpec(KernelModel):
    schema_version: Literal[1]
    source_research_ref: str = Field(min_length=1, max_length=2048)
    archetype: XiaohongshuArchetype
    reader_tension: str = Field(min_length=1, max_length=768)
    headline_question: str = Field(min_length=1, max_length=768)
    public_claim_ids: tuple[str, ...] = Field(min_length=1)
    derived_claims: tuple[XiaohongshuDerivedClaimInput, ...] = ()
    market_anchor: XiaohongshuMarketAnchor | None = None
    strongest_counterpoint: str | None = Field(default=None, max_length=1024)
    closing_takeaway: str | None = Field(default=None, max_length=1024)
    human_state_policy: Literal["OMIT"] = "OMIT"
    notes: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_ids(self) -> "XiaohongshuAuthoringSpec":
        if len(self.public_claim_ids) != len(set(self.public_claim_ids)):
            raise ValueError("public_claim_ids must be unique")
        derived_ids = [claim.claim_id for claim in self.derived_claims]
        if len(derived_ids) != len(set(derived_ids)):
            raise ValueError("derived claim ids must be unique")
        if set(derived_ids) & set(self.public_claim_ids):
            raise ValueError("derived claim ids cannot collide with Research claim ids")
        return self


class XiaohongshuWritingBrief(KernelModel):
    schema_version: Literal[1]
    style_profile_id: Literal["xiaohongshu-investment-v1"]
    investment_authority: Literal["NONE"]
    source_research_ref: str
    source_package_hash: str = Field(min_length=64, max_length=64)
    research_snapshot_id: UUID
    source_pit_cutoff: AwareDateTime
    ticker: str
    company_name: str
    archetype: XiaohongshuArchetype
    reader_tension: str
    headline_question: str
    selected_claims: tuple[PublicationClaim, ...] = Field(min_length=1)
    market_anchor: XiaohongshuMarketAnchor | None
    strongest_counterpoint: str | None
    closing_takeaway: str | None
    human_state_policy: Literal["OMIT"]
    notes: str | None

    @property
    def brief_hash(self) -> str:
        return canonical_hash(self)


class XiaohongshuPlanCard(KernelModel):
    card_number: int = Field(ge=1, le=13)
    job: str = Field(min_length=1, max_length=512)
    turn: str = Field(min_length=1, max_length=512)
    claim_ids: tuple[str, ...] = ()


class XiaohongshuPlan(KernelModel):
    schema_version: Literal[1]
    reader_tension: str = Field(min_length=1)
    title_candidates: tuple[str, ...] = Field(min_length=3, max_length=5)
    cards: tuple[XiaohongshuPlanCard, ...] = Field(min_length=7, max_length=13)
    strongest_counterpoint: str | None = None
    final_takeaway: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_card_sequence(self) -> "XiaohongshuPlan":
        expected = list(range(1, len(self.cards) + 1))
        actual = [card.card_number for card in self.cards]
        if actual != expected:
            raise ValueError("plan card numbers must be consecutive starting at 1")
        return self


class XiaohongshuDraftParagraph(KernelModel):
    text: str = Field(min_length=1)
    kind: DraftParagraphKind
    claim_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_basic_grounding(self) -> "XiaohongshuDraftParagraph":
        if self.kind in {
            DraftParagraphKind.FACT,
            DraftParagraphKind.MARKET_CONTEXT,
            DraftParagraphKind.INFERENCE,
            DraftParagraphKind.DERIVATION,
        } and not self.claim_ids:
            raise ValueError(f"{self.kind} draft paragraph requires claim_ids")
        return self


class XiaohongshuDraftCard(KernelModel):
    card_number: int = Field(ge=1, le=13)
    heading: str | None = Field(default=None, max_length=256)
    paragraphs: tuple[XiaohongshuDraftParagraph, ...] = Field(min_length=1)


class XiaohongshuDraft(KernelModel):
    schema_version: Literal[1]
    title: str = Field(min_length=1, max_length=256)
    reader_tension: str = Field(min_length=1)
    cards: tuple[XiaohongshuDraftCard, ...] = Field(min_length=7, max_length=13)
    final_takeaway: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_card_sequence(self) -> "XiaohongshuDraft":
        expected = list(range(1, len(self.cards) + 1))
        actual = [card.card_number for card in self.cards]
        if actual != expected:
            raise ValueError("draft card numbers must be consecutive starting at 1")
        return self


class DraftValidationIssue(KernelModel):
    code: str = Field(min_length=1, max_length=128)
    severity: ValidationSeverity
    location: str = Field(min_length=1, max_length=256)
    message: str = Field(min_length=1)


class DraftValidationReport(KernelModel):
    status: ValidationStatus
    issues: tuple[DraftValidationIssue, ...]

    @model_validator(mode="after")
    def validate_status(self) -> "DraftValidationReport":
        should_fail = any(issue.severity is ValidationSeverity.BLOCK for issue in self.issues)
        expected = ValidationStatus.FAIL if should_fail else ValidationStatus.PASS
        if self.status is not expected:
            raise ValueError("validation status must match blocker set")
        return self


def load_style_sample_bank() -> XiaohongshuStyleSampleBank:
    try:
        text = files("decision_kernel").joinpath(STYLE_SAMPLE_BANK_RESOURCE).read_text(
            encoding="utf-8"
        )
        payload = json.loads(text)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise DomainValidationError(
            "Xiaohongshu style sample bank is unavailable or invalid"
        ) from exc
    return XiaohongshuStyleSampleBank.model_validate(payload)


def load_deep_research_package(path: Path) -> DeepResearchPackage:
    try:
        return DeepResearchPackage.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DomainValidationError(f"invalid DeepResearchPackage: {path}") from exc


def load_authoring_spec(path: Path) -> XiaohongshuAuthoringSpec:
    try:
        return XiaohongshuAuthoringSpec.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise DomainValidationError(f"invalid XiaohongshuAuthoringSpec: {path}") from exc


def _publication_kind(kind: ResearchClaimKind) -> PublicationClaimKind:
    return PublicationClaimKind(kind.value)


def _resolve_evidence_refs(
    package: DeepResearchPackage,
    evidence_ids: tuple[UUID, ...],
) -> tuple[PublicationEvidenceRef, ...]:
    artifacts = {artifact.id: artifact for artifact in package.evidence_artifacts}
    refs: list[PublicationEvidenceRef] = []
    for evidence_id in evidence_ids:
        artifact = artifacts.get(evidence_id)
        if artifact is None:
            raise DomainValidationError(
                f"publication claim references missing evidence: {evidence_id}"
            )
        refs.append(
            PublicationEvidenceRef(
                evidence_artifact_id=artifact.id,
                source_type=artifact.source_type,
                source_locator=artifact.source_locator,
                available_at=artifact.available_at,
            )
        )
    return tuple(refs)


def _claim_from_research(
    package: DeepResearchPackage,
    *,
    claim_id: str,
    origin: str,
    claim: ResearchClaim,
) -> PublicationClaim:
    return PublicationClaim(
        claim_id=claim_id,
        kind=_publication_kind(claim.kind),
        text=claim.statement,
        origin=origin,
        evidence_refs=_resolve_evidence_refs(package, claim.evidence_artifact_ids),
    )


def build_claim_catalog(
    package: DeepResearchPackage,
) -> dict[str, PublicationClaim]:
    """Expose deterministic claim ids without making any claim publication-safe by default."""

    freeze_deep_research_package(package)
    catalog: dict[str, PublicationClaim] = {}

    for index, observation in enumerate(package.discovery.factual_observations, start=1):
        claim_id = f"discovery.{index}"
        catalog[claim_id] = PublicationClaim(
            claim_id=claim_id,
            kind=PublicationClaimKind.FACT,
            text=observation.statement,
            origin="discovery",
            evidence_refs=_resolve_evidence_refs(
                package,
                observation.evidence_artifact_ids,
            ),
        )

    groups: tuple[tuple[str, str, tuple[ResearchClaim, ...]], ...] = (
        ("pre", "pre_research", package.pre_research.material_claims),
        ("quick.support", "quick_research.supporting", package.quick_research.supporting_claims),
        ("quick.contra", "quick_research.contradictory", package.quick_research.contradictory_claims),
        ("deep", "deep_research", package.deep_research.material_claims),
    )
    for prefix, origin, claims in groups:
        for index, claim in enumerate(claims, start=1):
            claim_id = f"{prefix}.{index}"
            catalog[claim_id] = _claim_from_research(
                package,
                claim_id=claim_id,
                origin=origin,
                claim=claim,
            )

    return catalog


def build_writing_brief(
    package: DeepResearchPackage,
    authoring: XiaohongshuAuthoringSpec,
) -> XiaohongshuWritingBrief:
    frozen = freeze_deep_research_package(package)
    catalog = build_claim_catalog(package)

    unknown = [claim_id for claim_id in authoring.public_claim_ids if claim_id not in catalog]
    if unknown:
        raise DomainValidationError(
            "publication selection references unknown Research claims: "
            + ", ".join(unknown)
        )

    selected = [catalog[claim_id] for claim_id in authoring.public_claim_ids]
    selected_ids = set(authoring.public_claim_ids)

    for derived in authoring.derived_claims:
        missing_sources = [
            claim_id
            for claim_id in derived.source_claim_ids
            if claim_id not in selected_ids
        ]
        if missing_sources:
            raise DomainValidationError(
                f"derived claim {derived.claim_id} references claims not explicitly "
                "selected PUBLIC_SAFE: "
                + ", ".join(missing_sources)
            )
        source_refs: list[PublicationEvidenceRef] = []
        seen_evidence: set[UUID] = set()
        for source_claim_id in derived.source_claim_ids:
            for ref in catalog[source_claim_id].evidence_refs:
                if ref.evidence_artifact_id not in seen_evidence:
                    seen_evidence.add(ref.evidence_artifact_id)
                    source_refs.append(ref)
        selected.append(
            PublicationClaim(
                claim_id=derived.claim_id,
                kind=PublicationClaimKind.DERIVATION,
                text=derived.text,
                origin="executor.derived",
                evidence_refs=tuple(source_refs),
                source_claim_ids=derived.source_claim_ids,
                calculation_ref=derived.calculation_ref,
            )
        )

    snapshot = package.research_snapshot
    return XiaohongshuWritingBrief(
        schema_version=1,
        style_profile_id=STYLE_PROFILE_ID,
        investment_authority="NONE",
        source_research_ref=authoring.source_research_ref,
        source_package_hash=frozen.package_hash,
        research_snapshot_id=snapshot.id,
        source_pit_cutoff=snapshot.as_of_datetime,
        ticker=snapshot.ticker,
        company_name=snapshot.company_name,
        archetype=authoring.archetype,
        reader_tension=authoring.reader_tension,
        headline_question=authoring.headline_question,
        selected_claims=tuple(selected),
        market_anchor=authoring.market_anchor,
        strongest_counterpoint=authoring.strongest_counterpoint,
        closing_takeaway=authoring.closing_takeaway,
        human_state_policy=authoring.human_state_policy,
        notes=authoring.notes,
    )


def _render_selected_claims(brief: XiaohongshuWritingBrief) -> str:
    lines: list[str] = []
    for claim in brief.selected_claims:
        refs = ", ".join(
            f"{ref.evidence_artifact_id} ({ref.source_type}) {ref.source_locator}"
            for ref in claim.evidence_refs
        ) or "NONE"
        source_claims = (
            f" | source_claim_ids: {', '.join(claim.source_claim_ids)}"
            if claim.source_claim_ids
            else ""
        )
        calculation = (
            f" | calculation_ref: {claim.calculation_ref}"
            if claim.calculation_ref
            else ""
        )
        lines.append(
            f"- {claim.claim_id} [{claim.kind.value}] {claim.text}"
            f" | evidence: {refs}{source_claims}{calculation}"
        )
    return "\n".join(lines)


def _render_market_anchor(brief: XiaohongshuWritingBrief) -> str:
    anchor = brief.market_anchor
    if anchor is None:
        return "NONE. Do not invent a current price or market cap."
    parts = [
        f"currency={anchor.currency}",
        f"observed_at={anchor.observed_at.isoformat()}",
        f"source_ref={anchor.source_ref}",
    ]
    if anchor.price is not None:
        parts.append(f"price={anchor.price}")
    if anchor.market_cap is not None:
        parts.append(f"market_cap={anchor.market_cap}")
    return "; ".join(parts)


def _render_sample_lessons(bank: XiaohongshuStyleSampleBank) -> str:
    blocks: list[str] = []
    for sample in bank.samples:
        lessons = " / ".join(sample.reusable_lessons)
        failures = (
            " / ".join(sample.failure_modes)
            if sample.failure_modes
            else "NONE"
        )
        title = sample.title_pattern or "NONE"
        blocks.append(
            f"- {sample.sample_id} | {sample.performance_label} | {sample.company} "
            f"| archetype={sample.archetype}\n"
            f"  title_pattern: {title}\n"
            f"  reusable: {lessons}\n"
            f"  avoid: {failures}"
        )
    return "\n".join(blocks)


def render_planner_prompt(
    brief: XiaohongshuWritingBrief,
    *,
    sample_bank: XiaohongshuStyleSampleBank | None = None,
) -> str:
    bank = sample_bank or load_style_sample_bank()
    archetype_instruction = {
        XiaohongshuArchetype.EXPECTATION_REPRICING: (
            "Reconstruct what the old price believed, what new evidence removed, "
            "what remains priced, and why the new price still may or may not be demanding."
        ),
        XiaohongshuArchetype.NORMALIZED_EARNINGS: (
            "Separate reported/peak earnings from durable earning power. Identify which "
            "profit pieces are cyclical, price/inventory-driven, or structurally repeatable."
        ),
        XiaohongshuArchetype.INDUSTRY_ODDS: (
            "Explain the bottleneck mechanism and duration first, then ask what duration "
            "and profit persistence the current valuation needs."
        ),
        XiaohongshuArchetype.IMPLIED_EARNINGS: (
            "Work backward from price/market cap to the earnings path the market is paying "
            "for. Separate capability, orders, revenue, margin, and durable profit."
        ),
    }[brief.archetype]

    return f"""You are the PLANNER in a Xiaohongshu public-equity writing harness.

Authority boundary:
- Investment Authority = NONE.
- Publishing is downstream from frozen Research. It may compress Research but may not rewrite it.
- Human Decision / Action / position / cost basis are OMIT and must never be inferred.
- Use only SELECTED CLAIMS below as factual or research inputs.
- Do not reconstruct unselected Research claims.
- A later market anchor is price context only; it is not new fundamental Evidence.
- Do not do new arithmetic. Any publishable arithmetic must already appear as a DERIVATION claim.
- Preserve FACT vs MARKET_CONTEXT vs INFERENCE vs ASSUMPTION vs DERIVATION.

Writing objective:
- One note = ONE reader_tension.
- New calibration supersedes the old "maximum three sub-questions" heuristic. Strong Human
  examples often use 4-6 numbered tests, but every test must advance the same tension.
- Target 7-13 cards. This range reflects the supplied long-form references; it is not a law.
- Opening: concrete earnings/price/valuation contradiction and why it matters now.
- Within the first 2-3 cards, make clear what the current price is asking the company to prove
  when the supplied claims/anchor support that question.
- Mechanism before dense numbers. Numbers prove the mechanism; they do not replace it.
- Prefer the proof ladder: capability -> demand -> order -> revenue -> margin -> durable profit.
  Never jump from "can do / certification / capacity" directly to durable profit.
- A strong move is "this proves A, but still does not prove B."
- Explicitly revise prior expectations when new evidence changes the credibility of an earnings
  path. A price can be similar while the underwriting changes.
- Use reverse valuation / implied earnings / SOTP only when supported by selected claims or
  DERIVATION claims.
- End with the hardest remaining proof, not a BUY/SELL call.
- No emoji bait, no "three bullish reasons", no hype, no fake certainty.

Archetype:
{brief.archetype.value}
{archetype_instruction}

Article:
- security: {brief.company_name} / {brief.ticker}
- source PIT: {brief.source_pit_cutoff.isoformat()}
- reader_tension: {brief.reader_tension}
- headline_question: {brief.headline_question}
- market_anchor: {_render_market_anchor(brief)}
- strongest_counterpoint: {brief.strongest_counterpoint or "NONE"}
- closing_takeaway: {brief.closing_takeaway or "NONE"}

SELECTED CLAIMS:
{_render_selected_claims(brief)}

Human-calibrated sample bank (distilled lessons, not copy text):
{_render_sample_lessons(bank)}

Return STRICT JSON matching this shape:
{{
  "schema_version": 1,
  "reader_tension": "{brief.reader_tension}",
  "title_candidates": ["3 to 5 Chinese title candidates"],
  "cards": [
    {{
      "card_number": 1,
      "job": "what this card must accomplish",
      "turn": "what new understanding/reversal the reader gets",
      "claim_ids": ["only ids from SELECTED CLAIMS; empty allowed for pure editorial framing"]
    }}
  ],
  "strongest_counterpoint": "publication-safe counterpoint or null",
  "final_takeaway": "restrained takeaway; what is known and what still needs proof"
}}

Do not write the prose article yet.
"""


def render_draft_prompt(
    brief: XiaohongshuWritingBrief,
    plan: XiaohongshuPlan,
) -> str:
    validate_plan(plan, brief)
    return f"""You are the DRAFTER in a Xiaohongshu public-equity writing harness.

Write from the exact plan and claims below. Do not add Research.

Hard boundary:
- Investment Authority = NONE.
- Human Decision / Action / holdings / cost basis are OMIT.
- Every FACT or MARKET_CONTEXT paragraph must cite claim_ids in the structured output.
- Every INFERENCE paragraph must cite the claims it reasons from.
- DERIVATION paragraphs may use only provided DERIVATION claim ids; do not invent arithmetic.
- ASSUMPTION must remain visibly conditional.
- Do not turn certification, capacity, product availability, or management aspiration into orders,
  market share, revenue, margin, or durable profit unless a selected claim says so.
- No recommendation language, target price, or false certainty.

Voice:
- Professional conversational Chinese, short paragraphs.
- Numbered sections are welcome when they form one causal chain.
- Use reasoning moves such as "真正值得讨论的是…", "这能证明A，但还不能证明B",
  "换句话说…", "市场现在真正押的是…" naturally, never as a template checklist.
- Start with tension, not company introduction.
- Show the economic mechanism before a wall of numbers.
- Price/implied expectations should arrive early when the brief supports them.
- End on the hardest remaining uncertainty.

BRIEF:
{brief.model_dump_json(indent=2)}

PLAN:
{plan.model_dump_json(indent=2)}

Return STRICT JSON:
{{
  "schema_version": 1,
  "title": "one selected title",
  "reader_tension": "{brief.reader_tension}",
  "cards": [
    {{
      "card_number": 1,
      "heading": "optional short heading",
      "paragraphs": [
        {{
          "text": "Chinese paragraph",
          "kind": "FACT | MARKET_CONTEXT | INFERENCE | ASSUMPTION | DERIVATION | EDITORIAL",
          "claim_ids": ["supporting ids; EDITORIAL may be empty"]
        }}
      ]
    }}
  ],
  "final_takeaway": "restrained closing"
}}
"""


def render_judge_prompt(
    brief: XiaohongshuWritingBrief,
    draft: XiaohongshuDraft,
    *,
    sample_bank: XiaohongshuStyleSampleBank | None = None,
) -> str:
    bank = sample_bank or load_style_sample_bank()
    report = validate_draft(draft, brief)
    return f"""You are the JUDGE in a Xiaohongshu public-equity writing harness.

Do not rewrite first. Evaluate whether this draft has the same *reason to keep reading* as the
Human reference notes while preserving Research truth.

Mechanical preflight:
{report.model_dump_json(indent=2)}

BRIEF:
{brief.model_dump_json(indent=2)}

DRAFT:
{draft.model_dump_json(indent=2)}

REFERENCE LESSONS:
{_render_sample_lessons(bank)}

Score each dimension 0-5:
1. truth_fidelity — facts/inferences/assumptions remain correctly typed and grounded;
2. single_tension — every card advances one pricing/expectation question;
3. title_gap — concrete, specific, creates an information gap without spending the answer;
4. opening_pull — contradiction is clear in card 1;
5. causal_mechanism — mechanism precedes dense numbers and has no logic jumps;
6. implied_expectations — reader understands what price/profit path is being underwritten;
7. proof_ladder — capability is not confused with orders/revenue/margin/durable profit;
8. scenario_discipline — scenarios separate base/optimistic/downside without peak-on-peak stacking;
9. counterpoint — strongest disconfirming evidence is treated seriously;
10. voice_and_pacing — short, conversational, investor-like; not a research report dump.

Hard blockers:
- any unsupported factual upgrade;
- invented number, price, probability, source, decision, action, position, or arithmetic;
- Human portfolio state leakage;
- recommendation language;
- multiple unrelated top-level tensions.

Return STRICT JSON:
{{
  "publish_readiness": "PASS | REVISE | BLOCK",
  "scores": {{
    "truth_fidelity": 0,
    "single_tension": 0,
    "title_gap": 0,
    "opening_pull": 0,
    "causal_mechanism": 0,
    "implied_expectations": 0,
    "proof_ladder": 0,
    "scenario_discipline": 0,
    "counterpoint": 0,
    "voice_and_pacing": 0
  }},
  "blockers": ["..."],
  "strongest_parts": ["..."],
  "rewrite_instructions": ["smallest changes that would materially improve the draft"]
}}
"""


def validate_plan(
    plan: XiaohongshuPlan,
    brief: XiaohongshuWritingBrief,
) -> DraftValidationReport:
    issues: list[DraftValidationIssue] = []
    known_ids = {claim.claim_id for claim in brief.selected_claims}

    if plan.reader_tension != brief.reader_tension:
        issues.append(
            DraftValidationIssue(
                code="TENSION_DRIFT",
                severity=ValidationSeverity.BLOCK,
                location="reader_tension",
                message="plan reader_tension must exactly preserve the brief tension",
            )
        )
    if not any("?" in title or "？" in title for title in plan.title_candidates):
        issues.append(
            DraftValidationIssue(
                code="TITLE_NO_QUESTION",
                severity=ValidationSeverity.WARN,
                location="title_candidates",
                message="at least one title should usually preserve an information gap",
            )
        )
    for card in plan.cards:
        unknown = [claim_id for claim_id in card.claim_ids if claim_id not in known_ids]
        if unknown:
            issues.append(
                DraftValidationIssue(
                    code="UNKNOWN_PLAN_CLAIM",
                    severity=ValidationSeverity.BLOCK,
                    location=f"cards[{card.card_number}].claim_ids",
                    message="plan references claims outside the publication brief: "
                    + ", ".join(unknown),
                )
            )

    return _validation_report(issues)


_FIRST_PERSON_POSITION_RE = re.compile(
    r"(?:我(?:已经|决定|准备|打算|会|要)?(?:买入|卖出|加仓|减仓|持有|建仓)"
    r"|我的(?:持仓|仓位|成本价)|我(?:的)?成本(?:价)?)"
)
_RECOMMENDATION_RE = re.compile(
    r"(?:建议买入|强烈推荐|必买|闭眼买|目标价\s*[：:]?|明确看多|明确看空)"
)


def validate_draft(
    draft: XiaohongshuDraft,
    brief: XiaohongshuWritingBrief,
) -> DraftValidationReport:
    issues: list[DraftValidationIssue] = []
    known = {claim.claim_id: claim for claim in brief.selected_claims}

    if draft.reader_tension != brief.reader_tension:
        issues.append(
            DraftValidationIssue(
                code="TENSION_DRIFT",
                severity=ValidationSeverity.BLOCK,
                location="reader_tension",
                message="draft reader_tension must exactly preserve the brief tension",
            )
        )

    all_text = "\n".join(
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
    if _FIRST_PERSON_POSITION_RE.search(all_text):
        issues.append(
            DraftValidationIssue(
                code="HUMAN_STATE_LEAK",
                severity=ValidationSeverity.BLOCK,
                location="draft",
                message="draft appears to disclose or invent Human Decision/Action/position state",
            )
        )
    if _RECOMMENDATION_RE.search(all_text):
        issues.append(
            DraftValidationIssue(
                code="RECOMMENDATION_LANGUAGE",
                severity=ValidationSeverity.BLOCK,
                location="draft",
                message="publishing harness does not emit investment recommendation language",
            )
        )

    for card in draft.cards:
        for paragraph_index, paragraph in enumerate(card.paragraphs, start=1):
            location = f"cards[{card.card_number}].paragraphs[{paragraph_index}]"
            unknown = [claim_id for claim_id in paragraph.claim_ids if claim_id not in known]
            if unknown:
                issues.append(
                    DraftValidationIssue(
                        code="UNKNOWN_DRAFT_CLAIM",
                        severity=ValidationSeverity.BLOCK,
                        location=f"{location}.claim_ids",
                        message="draft references claims outside the publication brief: "
                        + ", ".join(unknown),
                    )
                )
                continue

            referenced_kinds = {known[claim_id].kind for claim_id in paragraph.claim_ids}
            if paragraph.kind is DraftParagraphKind.FACT and referenced_kinds - {
                PublicationClaimKind.FACT
            }:
                issues.append(
                    DraftValidationIssue(
                        code="FACT_AUTHORITY_UPGRADE",
                        severity=ValidationSeverity.BLOCK,
                        location=location,
                        message="FACT paragraph may reference only FACT publication claims",
                    )
                )
            if paragraph.kind is DraftParagraphKind.MARKET_CONTEXT and referenced_kinds - {
                PublicationClaimKind.MARKET_CONTEXT
            }:
                issues.append(
                    DraftValidationIssue(
                        code="MARKET_CONTEXT_AUTHORITY_UPGRADE",
                        severity=ValidationSeverity.BLOCK,
                        location=location,
                        message=(
                            "MARKET_CONTEXT paragraph may reference only MARKET_CONTEXT claims"
                        ),
                    )
                )
            if paragraph.kind is DraftParagraphKind.DERIVATION and (
                not referenced_kinds
                or referenced_kinds - {PublicationClaimKind.DERIVATION}
            ):
                issues.append(
                    DraftValidationIssue(
                        code="UNDECLARED_DERIVATION",
                        severity=ValidationSeverity.BLOCK,
                        location=location,
                        message="DERIVATION paragraph may use only explicit DERIVATION claims",
                    )
                )

    if "?" not in draft.title and "？" not in draft.title:
        issues.append(
            DraftValidationIssue(
                code="TITLE_NO_INFORMATION_GAP",
                severity=ValidationSeverity.WARN,
                location="title",
                message="reference titles usually preserve a question or unresolved tension",
            )
        )

    return _validation_report(issues)


def _validation_report(
    issues: list[DraftValidationIssue],
) -> DraftValidationReport:
    status = (
        ValidationStatus.FAIL
        if any(issue.severity is ValidationSeverity.BLOCK for issue in issues)
        else ValidationStatus.PASS
    )
    return DraftValidationReport(status=status, issues=tuple(issues))


def render_draft_markdown(draft: XiaohongshuDraft) -> str:
    lines = [f"# {draft.title}", ""]
    for card in draft.cards:
        if card.heading:
            lines.extend([f"## {card.card_number}. {card.heading}", ""])
        else:
            lines.extend([f"## {card.card_number}", ""])
        for paragraph in card.paragraphs:
            lines.extend([paragraph.text, ""])
    lines.extend([draft.final_takeaway, ""])
    return "\n".join(lines)


def _load_brief(path: Path) -> XiaohongshuWritingBrief:
    try:
        return XiaohongshuWritingBrief.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise DomainValidationError(f"invalid XiaohongshuWritingBrief: {path}") from exc


def _load_plan(path: Path) -> XiaohongshuPlan:
    try:
        return XiaohongshuPlan.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DomainValidationError(f"invalid XiaohongshuPlan: {path}") from exc


def _load_draft(path: Path) -> XiaohongshuDraft:
    try:
        return XiaohongshuDraft.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DomainValidationError(f"invalid XiaohongshuDraft: {path}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m decision_kernel.xiaohongshu_harness",
        description=(
            "Build and validate a provider-agnostic Xiaohongshu writing harness "
            "from frozen Decision Kernel Research."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build brief + planner prompt.")
    build.add_argument("--research", type=Path, required=True)
    build.add_argument("--authoring", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)

    draft_prompt = subparsers.add_parser(
        "draft-prompt",
        help="Render a drafting prompt from a validated plan.",
    )
    draft_prompt.add_argument("--brief", type=Path, required=True)
    draft_prompt.add_argument("--plan", type=Path, required=True)
    draft_prompt.add_argument("--output", type=Path, required=True)

    judge_prompt = subparsers.add_parser(
        "judge-prompt",
        help="Render a judge prompt from a structured draft.",
    )
    judge_prompt.add_argument("--brief", type=Path, required=True)
    judge_prompt.add_argument("--draft", type=Path, required=True)
    judge_prompt.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser(
        "validate-draft",
        help="Run deterministic authority/shape checks and optionally render Markdown.",
    )
    validate.add_argument("--brief", type=Path, required=True)
    validate.add_argument("--draft", type=Path, required=True)
    validate.add_argument("--markdown", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "build":
            package = load_deep_research_package(args.research)
            authoring = load_authoring_spec(args.authoring)
            brief = build_writing_brief(package, authoring)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            (args.output_dir / "brief.json").write_text(
                brief.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
            (args.output_dir / "planner-prompt.txt").write_text(
                render_planner_prompt(brief),
                encoding="utf-8",
            )
            print(f"BRIEF: {args.output_dir / 'brief.json'}")
            print(f"PLANNER: {args.output_dir / 'planner-prompt.txt'}")
            print(f"BRIEF HASH: {brief.brief_hash}")
            return 0

        if args.command == "draft-prompt":
            brief = _load_brief(args.brief)
            plan = _load_plan(args.plan)
            report = validate_plan(plan, brief)
            if report.status is ValidationStatus.FAIL:
                print(report.model_dump_json(indent=2), file=sys.stderr)
                return 1
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_draft_prompt(brief, plan), encoding="utf-8")
            print(f"DRAFT PROMPT: {args.output}")
            return 0

        if args.command == "judge-prompt":
            brief = _load_brief(args.brief)
            draft = _load_draft(args.draft)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_judge_prompt(brief, draft), encoding="utf-8")
            print(f"JUDGE PROMPT: {args.output}")
            return 0

        if args.command == "validate-draft":
            brief = _load_brief(args.brief)
            draft = _load_draft(args.draft)
            report = validate_draft(draft, brief)
            print(report.model_dump_json(indent=2))
            if args.markdown is not None and report.status is ValidationStatus.PASS:
                args.markdown.parent.mkdir(parents=True, exist_ok=True)
                args.markdown.write_text(
                    render_draft_markdown(draft),
                    encoding="utf-8",
                )
            return 0 if report.status is ValidationStatus.PASS else 1

        raise AssertionError(f"unhandled command: {args.command}")
    except DomainValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
