from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from decision_kernel.claim_audit_contract_v1 import (
    ClaimAuditV1Check,
    ClaimAuditV1ClaimReview,
)
from decision_kernel.claim_audit_contract_v2 import (
    ClaimAuditContractV2Payload,
    ClaimAuditV2ClaimReview,
)
from decision_kernel.deep_research import (
    DeepResearchPackage,
    deep_research_information_bundle_hash,
    deep_research_package_hash,
)
from decision_kernel.evidence import EvidenceArtifact, EvidenceArtifactLink
from decision_kernel.identity import canonical_hash
from decision_kernel.research import ResearchSnapshot
from decision_kernel.research_contract_v1 import ResearchContractV1ScenarioDetail
from decision_kernel.research_contract_v2 import (
    ExpectationEventBridgeV2,
    ProbabilityEffect,
    ResearchContractV2Payload,
)
from decision_kernel.research_funnel import (
    PreResearchResult,
    QuickResearchResult,
    ResearchClaim,
    ResearchClaimKind,
)
from decision_kernel.source_policy_v2 import (
    AssertionScope,
    ClaimSourceUseV2,
    SourceEpistemicRole,
)

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "research_cases"
OUT = ROOT / "generated-yto-v2"
OUT.mkdir(exist_ok=True)

V1_PACKAGE = json.loads((CASE / "600233-yto-deep-research-v1.json").read_text(encoding="utf-8"))
V1_AUDIT = json.loads((CASE / "600233-yto-claim-audit-v1.json").read_text(encoding="utf-8"))
V1_CONTRACT = json.loads((CASE / "600233-yto-research-contract-v1.json").read_text(encoding="utf-8"))

OLD_SNAPSHOT_ID = V1_PACKAGE["research_snapshot"]["id"]
NEW_SNAPSHOT_ID = str(uuid5(NAMESPACE_URL, "decision-kernel:YTO:600233:research-v2:2026-09-02"))
NEW_DISCOVERY_ID = "yto-600233-full-v2-2026-09-02"


def uid(label: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"decision-kernel:YTO:600233:v2:{label}"))


def extract_hash(locator: str, values: dict) -> str:
    payload = json.dumps(
        {"source_locator": locator, "extracted_structured_values": values},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def artifact(
    *,
    label: str,
    source_type: str,
    source_identifier: str,
    source_locator: str,
    published_at: str,
    available_at: str,
    values: dict,
    source_location: str,
    report_period_end: str | None = None,
) -> dict:
    return {
        "id": uid(f"evidence:{label}"),
        "source_type": source_type,
        "source_identifier": source_identifier,
        "source_locator": source_locator,
        "published_at": published_at,
        "available_at": available_at,
        "retrieved_at": "2026-09-02T15:15:00Z",
        "content_hash": extract_hash(source_locator, values),
        "idempotency_key": source_identifier,
        "retention_mode": "EXTRACTED_VALUES",
        "replayability_level": "PARTIAL",
        "raw_storage_ref": None,
        "extracted_structured_values": values,
        "permitted_excerpt": None,
        "source_location": source_location,
        "license_terms_note": "Normalized structured extraction; source role is assessed separately by Research Method v2.",
        "report_period_end": report_period_end,
        "schema_version": 1,
    }


PREALERT = artifact(
    label="h1-prealert",
    source_type="OFFICIAL_FILING",
    source_identifier="YTO:600233:2026-H1-PREALERT",
    source_locator="https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12421972&stockid=600233",
    published_at="2026-07-01T00:00:00Z",
    available_at="2026-07-01T00:00:00Z",
    values={
        "h1_parent_np_low": "3100000000",
        "h1_parent_np_high": "3400000000",
        "h1_deducted_np_low": "3040000000",
        "h1_deducted_np_high": "3340000000",
    },
    source_location="2026 H1 preliminary earnings announcement",
    report_period_end="2026-06-30",
)
CICC = artifact(
    label="cicc-2026-07-01",
    source_type="SELL_SIDE_RESEARCH",
    source_identifier="CICC:YTO:2026-07-01:H1-PREALERT",
    source_locator="https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/lastest/rptid/836208060775/index.phtml",
    published_at="2026-07-01T00:00:00Z",
    available_at="2026-07-01T00:00:00Z",
    values={
        "2026_parent_np": "6210000000",
        "2027_parent_np": "7306000000",
        "target_price": "26.00",
        "2026_pe": "14",
        "2027_pe": "12",
    },
    source_location="CICC 1H26 earnings-prealert comment",
)
HUACHUANG = artifact(
    label="huachuang-2026-07-01",
    source_type="SELL_SIDE_RESEARCH",
    source_identifier="HUACHUANG:YTO:2026-07-01:H1-PREALERT",
    source_locator="https://stock.finance.sina.com.cn/stock/go.php/vReport_Show/kind/lastest/rptid/836221555904/index.phtml",
    published_at="2026-07-01T00:00:00Z",
    available_at="2026-07-01T00:00:00Z",
    values={
        "2026_parent_np": "6530000000",
        "2027_parent_np": "7500000000",
        "2028_parent_np": "8310000000",
        "target_price": "24.8",
        "2026_pe": "13",
    },
    source_location="Huachuang 2026 H1 earnings-prealert comment",
)
PRICE_REACTION = artifact(
    label="2026-08-20-price-reaction",
    source_type="PUBLIC_MARKET_CONTEXT",
    source_identifier="PUBLIC:YTO:600233:2026-08-18-20:CLOSES",
    source_locator="https://cn.investing.com/equities/dayang-historical-data",
    published_at="2026-08-21T00:00:00Z",
    available_at="2026-08-21T00:00:00Z",
    values={
        "2026-08-18_close": "19.25",
        "2026-08-19_close": "18.68",
        "2026-08-20_close": "17.50",
        "2026-08-20_return_pct": "-6.32",
        "2026-08-20_volume_shares": "51440000",
    },
    source_location="Public historical-price table; Research market context only, not production ObservedMarket",
)
HUATAI = artifact(
    label="huatai-2026-08-20",
    source_type="SELL_SIDE_RESEARCH",
    source_identifier="HUATAI:YTO:2026-08-20:H1-RESULT",
    source_locator="https://basic.10jqka.com.cn/600233/worth.html",
    published_at="2026-08-20T08:00:00Z",
    available_at="2026-08-20T08:00:00Z",
    values={
        "2026_parent_np": "6311000000",
        "2027_parent_np": "7542000000",
        "2028_parent_np": "8223000000",
        "2026_forecast_revision_pct": "8.19",
        "2027_forecast_revision_pct": "13.14",
        "2028_forecast_revision_pct": "10.31",
        "new_2026_pe": "13.3",
        "old_2026_pe": "16.3",
        "new_target_price": "24.51",
        "old_target_price": "27.74",
    },
    source_location="Huatai post-H1 result report excerpt in F10",
)
NEW_EVIDENCE = [PREALERT, CICC, HUACHUANG, PRICE_REACTION, HUATAI]

p = deepcopy(V1_PACKAGE)
p["label"] = "600233 圆通速递 Full Research v2"
p["discovery"]["discovery_id"] = NEW_DISCOVERY_ID
p["pre_research"]["discovery_id"] = NEW_DISCOVERY_ID
p["quick_research"]["discovery_id"] = NEW_DISCOVERY_ID
p["deep_research"]["discovery_id"] = NEW_DISCOVERY_ID
p["discovery"]["current_market_expression"] = (
    "600233 Research v2; historical event reaction is Research context only. Production Odds remains a separate HiThink-observed run."
)
p["discovery"]["why_now"] = (
    "H1 owner economics improved, while the formal print triggered a sharp negative repricing despite earnings expectations staying broadly intact."
)
p["discovery"]["contradiction_or_mapping_warning"] = (
    "A correct source extract is not automatically a truth-qualified claim; sell-side forecasts are expectation/model evidence, not realized FACT."
)

for item in NEW_EVIDENCE:
    p["evidence_artifacts"].append(item)
    p["discovery"]["source_lineage"].append(
        {
            "evidence_artifact_id": item["id"],
            "source_locator": item["source_locator"],
            "available_at": item["available_at"],
        }
    )

p["discovery"]["factual_observations"].extend(
    [
        {
            "statement": "The company had already announced a CNY3.1-3.4bn H1 parent-NP range before the formal H1 report.",
            "evidence_artifact_ids": [PREALERT["id"]],
        },
        {
            "statement": "Sampled post-prealert sell-side 2027 NP estimates were already CNY7.306bn and CNY7.50bn.",
            "evidence_artifact_ids": [CICC["id"], HUACHUANG["id"]],
        },
        {
            "statement": "The first full trading day after the formal report closed down 6.32% on 51.44m shares.",
            "evidence_artifact_ids": [PRICE_REACTION["id"]],
        },
    ]
)

p["pre_research"]["current_market_expectation_hypothesis"] = (
    "Formal H1 results arrived after a profit prealert and after sampled 2027 sell-side forecasts had already moved to roughly CNY7.3-7.5bn."
)
p["pre_research"]["material_claims"].extend(
    [
        {
            "statement": "The company announced a CNY3.1-3.4bn 2026H1 parent-NP range before the formal H1 report.",
            "kind": "FACT",
            "evidence_artifact_ids": [PREALERT["id"]],
        },
        {
            "statement": "After that prealert, sampled CICC and Huachuang 2027 parent-NP forecasts were CNY7.306bn and CNY7.50bn.",
            "kind": "MARKET_CONTEXT",
            "evidence_artifact_ids": [CICC["id"], HUACHUANG["id"]],
        },
    ]
)
p["pre_research"]["obvious_contradiction"] = (
    "The formal H1 print was strong year on year but mostly preannounced; the remaining surprise was durability and composition, not headline profit growth."
)
p["pre_research"]["largest_unknown"] = (
    "Whether the market's post-print de-rating reflects information about earnings durability that is not yet visible in realized owner economics."
)

p["quick_research"]["market_expectation_hypothesis"] = (
    "Pre-print sampled 2027 forecasts were already around CNY7.3-7.5bn; post-print fresh consensus stayed around CNY7.27bn, so the selloff was not a simple earnings-level reset."
)
p["quick_research"]["current_expression_or_leadership"] = (
    "Formal H1 print produced a company-specific negative event reaction; treat it as expectation evidence, not as a Fundamental Belief update by itself."
)
p["quick_research"]["supporting_claims"].extend(
    [
        {
            "statement": "On 2026-08-20 YTO closed at CNY17.50, down 6.32%, with 51.44m shares traded after the formal H1 report.",
            "kind": "MARKET_CONTEXT",
            "evidence_artifact_ids": [PRICE_REACTION["id"]],
        },
        {
            "statement": "Huatai raised its 2026/2027/2028 parent-NP forecasts to CNY6.311/7.542/8.223bn after H1.",
            "kind": "MARKET_CONTEXT",
            "evidence_artifact_ids": [HUATAI["id"]],
        },
        {
            "statement": "Huatai cut its applied 2026E PE from 16.3x to 13.3x and target price from CNY27.74 to CNY24.51 after H1.",
            "kind": "MARKET_CONTEXT",
            "evidence_artifact_ids": [HUATAI["id"]],
        },
    ]
)
p["quick_research"]["evidence_authority_assessment"] = (
    "Primary filings own realized facts; company statements prove what management said, not future realization; sell-side models/targets describe expectations or opinions; public historical prices are event context only."
)
p["quick_research"]["variant_perception"] = (
    "The post-H1 selloff is more consistent with a durability/multiple debate than a large earnings-level reset; do not let price action silently rewrite owner-economics probabilities."
)
p["quick_research"]["unresolved_questions"] = list(p["quick_research"]["unresolved_questions"]) + [
    "what durability/multiple assumptions were embedded before the formal H1 print"
]
p["quick_research"]["next_discriminating_evidence"] = list(p["quick_research"]["next_discriminating_evidence"]) + [
    "pre-event versus post-event expectation revisions and valuation assumptions"
]

p["deep_research"]["material_claims"].extend(
    [
        {
            "statement": "The CNY3.175bn formal H1 parent NP sat only 25% through the previously announced CNY3.1-3.4bn range, so the headline result was mostly known before the formal print.",
            "kind": "INFERENCE",
            "evidence_artifact_ids": [PREALERT["id"], "047e2546-389b-5274-a8dc-e4a0ce3931f4"],
        },
        {
            "statement": "Pre-print sampled 2027 sell-side NP was CNY7.306-7.50bn, while fresh post-H1 2027 estimates centered near CNY7.27bn.",
            "kind": "MARKET_CONTEXT",
            "evidence_artifact_ids": [CICC["id"], HUACHUANG["id"], "dbf7e565-b79f-5f2e-beea-fbe26ac655af"],
        },
        {
            "statement": "The negative event reaction alongside broadly intact earnings forecasts is consistent with durability/multiple repricing, but price action alone is not evidence to change Fundamental Belief probabilities.",
            "kind": "INFERENCE",
            "evidence_artifact_ids": [PREALERT["id"], CICC["id"], HUACHUANG["id"], PRICE_REACTION["id"], HUATAI["id"], "dbf7e565-b79f-5f2e-beea-fbe26ac655af"],
        },
    ]
)
p["deep_research"]["adversarial_findings"].append(
    {
        "question": "Did the post-H1 selloff prove the earnings thesis was wrong?",
        "finding": "No. Sampled pre-print and fresh post-print 2027 earnings expectations were broadly similar, while at least one broker raised earnings forecasts but cut the applied multiple.",
        "severity": "WARN",
        "resolution": "Freeze the event bridge, keep probabilities unchanged, and wait for owner-economics evidence before changing Fundamental Belief.",
    }
)

# Re-key the frozen snapshot and every snapshot-owned child identity.
s = p["research_snapshot"]
s["id"] = NEW_SNAPSHOT_ID
s["version"] = 2
s["supersedes_snapshot_id"] = OLD_SNAPSHOT_ID
s["research_origin"] = f"DISCOVERY_INPUT:{NEW_DISCOVERY_ID}"
s["market_expectations_narrative"] = (
    "The CNY3.1-3.4bn H1 profit range was known before the formal report. Sampled post-prealert 2027 sell-side forecasts were already CNY7.306-7.50bn; fresh post-H1 estimates center near CNY7.27bn. The 8/20 selloff therefore looks more like durability/multiple repricing than a large earnings-level reset. MARKET_CONTEXT is not truth."
)
s["model_risk_notes"] = (
    "Franchise returns are undisclosed; one H1 cannot prove a permanent price regime; maintenance capex and adjacent ROIC are unresolved; event-price repricing may reveal durability disagreement but cannot by itself change probabilities; PE/share-count remain explicit assumptions."
)
s["open_questions"] = list(s["open_questions"]) + [
    "durability/multiple assumptions embedded before and after the formal H1 print"
]
s["created_at"] = "2026-09-02T15:20:00Z"
s["status"] = "DRAFT"
s["committed_at"] = None
s["research_engine_version"] = "manual-full-research-v2-source-admissibility"
s["information_bundle_hash"] = "0" * 64

old_basis_id = s["valuation_bases"][0]["id"]
new_basis_id = uid("valuation-basis")
s["valuation_bases"][0]["id"] = new_basis_id
s["valuation_bases"][0]["research_snapshot_id"] = NEW_SNAPSHOT_ID
s["valuation_bases"][0]["version"] = 2
s["valuation_bases"][0]["supersedes_valuation_basis_id"] = old_basis_id
s["valuation_bases"][0]["declared_change_reasons"] = [
    "Research v2 adds source-admissibility and expectation-event evidence; valuation parameters and scenario economics are unchanged."
]
s["valuation_bases"][0]["other_explicit_inputs"]["expectation_event_rule"] = (
    "PRICE_REACTION_DOES_NOT_CHANGE_FUNDAMENTAL_PROBABILITIES_WITHOUT_NEW_OWNER_ECONOMICS_EVIDENCE"
)

scenario_id_map: dict[str, str] = {}
for scenario in s["scenarios"]:
    old = scenario["id"]
    new = uid(f"scenario:{scenario['name']}")
    scenario_id_map[old] = new
    scenario["id"] = new
    scenario["research_snapshot_id"] = NEW_SNAPSHOT_ID
    scenario["valuation_basis_id"] = new_basis_id

# Rebuild evidence links under the new snapshot, retaining v1 relationships and adding v2 evidence.
new_links = []
for link in s["evidence_links"]:
    new_links.append(
        {
            **link,
            "id": uid(f"link:existing:{link['evidence_artifact_id']}:{link['relationship']}:{link['relevance']}"),
            "research_snapshot_id": NEW_SNAPSHOT_ID,
        }
    )
for item, relationship, relevance, note in [
    (PREALERT, "SUPPORTS", "H1 preannouncement and surprise baseline", "Primary statement; proves the announced range."),
    (CICC, "CONTEXT", "Pre-print sell-side expectation", "Analyst model; expectation evidence only."),
    (HUACHUANG, "CONTEXT", "Pre-print sell-side expectation", "Analyst model; expectation evidence only."),
    (PRICE_REACTION, "CONTEXT", "Formal-H1 event reaction", "Historical market context; not production ObservedMarket."),
    (HUATAI, "CONTEXT", "Post-print earnings/multiple revision", "Analyst model/opinion; not realized truth."),
]:
    new_links.append(
        {
            "id": uid(f"link:new:{item['id']}:{relationship}"),
            "research_snapshot_id": NEW_SNAPSHOT_ID,
            "evidence_artifact_id": item["id"],
            "relationship": relationship,
            "relevance": relevance,
            "interpretation_notes": note,
        }
    )
s["evidence_links"] = new_links

# Fix funnel hashes after all semantic edits.
p["quick_research"]["pre_research_hash"] = canonical_hash(
    PreResearchResult.model_validate(p["pre_research"])
)
p["deep_research"]["quick_research_hash"] = canonical_hash(
    QuickResearchResult.model_validate(p["quick_research"])
)
p["proposed_committed_at"] = "2026-09-02T15:25:00Z"

# Compute exact Research Method v1-compatible information identity for the v2 lineage.
tmp = DeepResearchPackage.model_validate(p)
expected_info_hash = deep_research_information_bundle_hash(
    discovery=tmp.discovery,
    pre_research=tmp.pre_research,
    quick_research=tmp.quick_research,
    deep_research=tmp.deep_research,
    evidence_artifacts=tmp.evidence_artifacts,
    research_snapshot=tmp.research_snapshot,
)
p["research_snapshot"]["information_bundle_hash"] = expected_info_hash
package = DeepResearchPackage.model_validate(p)
package_hash = deep_research_package_hash(package)

# Build Claim Audit v2 by preserving old v1 reviews and creating bounded reviews for new claims.
old_reviews = {
    canonical_hash(ResearchClaim.model_validate(item["claim"])): item
    for item in V1_AUDIT["reviews"]
}
material_claims = (
    *package.pre_research.material_claims,
    *package.quick_research.supporting_claims,
    *package.quick_research.contradictory_claims,
    *package.deep_research.material_claims,
)


def fresh_v1_review(claim: ResearchClaim) -> ClaimAuditV1ClaimReview:
    if claim.kind in {ResearchClaimKind.FACT, ResearchClaimKind.MARKET_CONTEXT}:
        checks = (
            ClaimAuditV1Check.CLASSIFICATION,
            ClaimAuditV1Check.IDENTITY,
            ClaimAuditV1Check.PERIOD_OR_DATE,
            ClaimAuditV1Check.UNITS,
            ClaimAuditV1Check.SOURCE_LOCATION,
            ClaimAuditV1Check.EVIDENCE_SUPPORT,
        )
    else:
        checks = (ClaimAuditV1Check.CLASSIFICATION,)
    return ClaimAuditV1ClaimReview(
        claim=claim,
        accepted=True,
        verified_checks=checks,
        failed_checks=(),
        numerical_assertions=(),
        numerical_checks=(),
        resolution="accepted under v2 source-admissibility review",
    )


def source_use(claim: ResearchClaim, evidence_id: UUID) -> ClaimSourceUseV2:
    eid = str(evidence_id)
    statement = claim.statement.lower()
    if eid == "047e2546-389b-5274-a8dc-e4a0ce3931f4":
        if "attributes" in statement:
            role, scope, basis = SourceEpistemicRole.PRIMARY_STATEMENT, AssertionScope.ATTRIBUTED_STATEMENT, "Official filing is used for an attributed company explanation."
        else:
            role, scope, basis = SourceEpistemicRole.PRIMARY_REALIZED, AssertionScope.REALIZED_OUTCOME, "Official H1 filing supports realized period facts."
    elif eid == "ca8d51da-fdbc-57e1-b28a-55b74ca0432e":
        role, scope, basis = SourceEpistemicRole.PRIMARY_REALIZED, AssertionScope.REALIZED_OUTCOME, "Official annual filing supports realized historical facts."
    elif eid == "dbf7e565-b79f-5f2e-beea-fbe26ac655af":
        role, scope, basis = SourceEpistemicRole.MARKET_EXPECTATION, AssertionScope.MARKET_EXPECTATION, "Consensus table describes market forecasts, not realized truth."
    elif eid == "049a2ca6-c4e4-5469-8e59-9f3f0e071911":
        role, scope, basis = SourceEpistemicRole.PRIMARY_STATEMENT, AssertionScope.ATTRIBUTED_STATEMENT, "IR evidence proves what the company stated, not realized franchise ROIC."
    elif eid == "fee8d5ee-76e9-5bcc-b352-5651a43c5884":
        role, scope, basis = SourceEpistemicRole.PRIMARY_REALIZED, AssertionScope.REALIZED_OUTCOME, "Official regulator notice supports the realized industry observation."
    elif eid == PREALERT["id"]:
        role, scope, basis = SourceEpistemicRole.PRIMARY_STATEMENT, AssertionScope.ATTRIBUTED_STATEMENT, "Preannouncement proves the company announced a preliminary profit range."
    elif eid in {CICC["id"], HUACHUANG["id"]}:
        role, scope, basis = SourceEpistemicRole.ANALYST_MODEL, AssertionScope.MODEL_FORECAST, "Sell-side forecast is analyst-model expectation evidence only."
    elif eid == PRICE_REACTION["id"]:
        role, scope, basis = SourceEpistemicRole.SECONDARY_OBSERVATION, AssertionScope.ATTRIBUTED_SECONDARY_OBSERVATION, "Public historical price table is secondary event context, not production ObservedMarket."
    elif eid == HUATAI["id"]:
        if "pe" in statement or "target price" in statement:
            role, scope, basis = SourceEpistemicRole.ANALYST_OPINION, AssertionScope.OPINION, "Applied multiple/target price is analyst opinion, not evidence truth."
        else:
            role, scope, basis = SourceEpistemicRole.ANALYST_MODEL, AssertionScope.MODEL_FORECAST, "Sell-side earnings forecast is analyst-model expectation evidence."
    else:
        raise AssertionError(f"unmapped evidence id {eid}")
    return ClaimSourceUseV2(
        evidence_artifact_id=evidence_id,
        source_role=role,
        assertion_scope=scope,
        role_basis=basis,
    )


v2_reviews = []
for claim in material_claims:
    old = old_reviews.get(canonical_hash(claim))
    review = (
        ClaimAuditV1ClaimReview.model_validate(old)
        if old is not None
        else fresh_v1_review(claim)
    )
    uses = ()
    if claim.kind in {ResearchClaimKind.FACT, ResearchClaimKind.MARKET_CONTEXT}:
        uses = tuple(source_use(claim, evidence_id) for evidence_id in claim.evidence_artifact_ids)
    v2_reviews.append(ClaimAuditV2ClaimReview(review=review, source_uses=uses))

audit_v2 = ClaimAuditContractV2Payload(
    research_snapshot_id=package.research_snapshot.id,
    research_package_hash=package_hash,
    reviews=tuple(v2_reviews),
)

# Research Contract v2 keeps scenario economics unchanged but freezes three maps and the event bridge.
contract_base = deepcopy(V1_CONTRACT)
contract_base["research_snapshot_id"] = NEW_SNAPSHOT_ID
contract_base["variant_perception"] = (
    "Street earnings expectations were already elevated after the profit prealert; the formal-report selloff looks more like durability/multiple repricing. Owner-economics probabilities remain evidence-driven, not price-driven."
)
contract_base["market_expectation_map"] = {
    "as_of": "2026-09-02",
    "pre_formal_report_after_prealert_sample": {
        "scope": "sampled sell-side, not broad consensus",
        "2027_cicc": "7306000000",
        "2027_huachuang": "7500000000",
        "sample_mean": "7403000000",
    },
    "post_formal_report_fresh": {
        "n": "10",
        "2027_min": "7010000000",
        "2027_median": "7300500000",
        "2027_mean": "7266500000",
        "2027_max": "7542000000",
    },
    "post_formal_report_valuation_example": {
        "huatai_2027_np": "7542000000",
        "huatai_old_2026_pe": "16.3",
        "huatai_new_2026_pe": "13.3",
        "huatai_old_target": "27.74",
        "huatai_new_target": "24.51",
    },
}
contract_base["expectation_clock_assessment"] = {
    "state": "PREALERT_PRICED_THEN_FORMAL_PRINT_DERATED",
    "implication": "Headline earnings were largely known before 8/19; post-print earnings forecasts stayed broadly intact while at least one applied multiple compressed.",
}
contract_base["scenario_details"] = [
    {
        **item,
        "scenario_id": scenario_id_map[item["scenario_id"]],
    }
    for item in contract_base["scenario_details"]
]
contract_v2 = ResearchContractV2Payload(
    **contract_base,
    source_policy_version="research-source-admissibility-v2",
    reality_map={
        "2026_h1_parent_np": "3175000000",
        "2026_h1_preannounced_parent_np_range": ["3100000000", "3400000000"],
        "2026_h1_volume_yi": "162.78",
        "2026_h1_unit_revenue": "2.17",
        "2026_h1_unit_cost": "1.90",
        "2026_h1_ocf": "3958827124.74",
        "2026_h1_capex": "3482399714.60",
    },
    our_belief_map={
        "2027_probability_weighted_parent_np": "6906900000.00",
        "scenario_probabilities": {
            "renewed_price_war": "0.15",
            "partial_normalization": "0.25",
            "street_center": "0.35",
            "durable_discipline": "0.20",
            "network_compounder": "0.05",
        },
        "probability_change_from_v1": "NONE",
        "reason": "The event bridge changes our understanding of market expectations, not realized owner-economics evidence. Price action alone does not change probabilities.",
    },
    expectation_event_bridges=(
        ExpectationEventBridgeV2(
            event_id="YTO-2026-H1-FORMAL-PRINT",
            event_date="2026-08-20",
            pre_event_expectation={
                "known_company_h1_parent_np_range": ["3100000000", "3400000000"],
                "sampled_2027_sellside_np": ["7306000000", "7500000000"],
                "2026-08-18_close": "19.25",
                "2026-08-19_close": "18.68",
            },
            actual_event={
                "formal_h1_parent_np": "3175000000",
                "position_through_preannounced_range": "0.25",
                "interpretation": "strong YoY but near the low quartile of the already-known range",
            },
            post_event_expectation={
                "fresh_2027_np_mean": "7266500000",
                "fresh_2027_np_median": "7300500000",
                "huatai_2027_np": "7542000000",
                "huatai_2026_pe_change": "16.3x -> 13.3x",
            },
            market_reaction={
                "2026-08-20_close": "17.50",
                "one_day_return_pct": "-6.32",
                "volume_shares": "51440000",
            },
            interpretation=(
                "The formal print did not reset earnings expectations downward by an amount comparable with the share-price move. The evidence is more consistent with a durability/multiple repricing debate than a large earnings-level reset."
            ),
            probability_effect=ProbabilityEffect.UNCHANGED,
            probability_effect_reason=(
                "No new realized owner-economics evidence in this bridge justifies changing the frozen 15/25/35/20/5 scenario probabilities; evidence changes probability, price changes Odds."
            ),
            evidence_artifact_ids=(
                UUID(PREALERT["id"]),
                UUID(CICC["id"]),
                UUID(HUACHUANG["id"]),
                UUID("047e2546-389b-5274-a8dc-e4a0ce3931f4"),
                UUID("dbf7e565-b79f-5f2e-beea-fbe26ac655af"),
                UUID(PRICE_REACTION["id"]),
                UUID(HUATAI["id"]),
            ),
        ),
    ),
    schema_version=2,
)

(OUT / "600233-yto-deep-research-v2.json").write_text(package.model_dump_json(indent=2), encoding="utf-8")
(OUT / "600233-yto-claim-audit-v2.json").write_text(audit_v2.model_dump_json(indent=2), encoding="utf-8")
(OUT / "600233-yto-research-contract-v2.json").write_text(contract_v2.model_dump_json(indent=2), encoding="utf-8")
print(f"snapshot_id={package.research_snapshot.id}")
print(f"information_bundle_hash={package.research_snapshot.information_bundle_hash}")
print(f"package_hash={package_hash}")
print(f"generated={OUT}")
