"""Read-only company-business evidence beside the existing economic Radar.

No beneficiary selection, membership inference, causal confirmation or new Kernel
object. Reuse exact EvidenceArtifact/source-policy semantics and Radar composition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from datetime import datetime
from decimal import Decimal
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

from decision_kernel.evidence import EvidenceArtifact, RetentionMode
from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.research_funnel import ResearchClaimKind
from decision_kernel.source_policy_v2 import (
    ClaimSourceUseV2, is_source_role_compatible_with_artifact, is_source_use_admissible,
)
from .economic_node_study import AUTHORITY
from .economic_release_review import _clock, _safe_path
from .judgment_timeline import REPOSITORY, _keys, _read, _text, _unique_object

SEMANTICS = "CURATED_COMPANY_BUSINESS_INPUTS_NOT_BENEFICIARY_OR_CAUSAL_CONFIRMATION"
DEFAULT_MANIFEST = "radar_inputs/economic-company-links-v0.json"
CHANNELS = {"REVENUE": "收入传导", "COST": "成本传导", "CAPACITY": "产能与利用率", "CASH_FLOW": "现金与再投入"}
LIMITS = {"membership_inferred": False, "company_benefit_established": False,
          "creates_canonical_wake": False, "market_event_writes": 0, **AUTHORITY}


def _json(root: Path, path: str):
    raw = _read(root, path)  # Existing bounded, traversal-safe exact-file reader.
    return raw, json.loads(raw, object_pairs_hook=_unique_object)


def _bounded(rows, maximum: int, *, minimum: int = 0):
    if not isinstance(rows, list) or not minimum <= len(rows) <= maximum:
        raise ValueError("company-link inventory exceeds the explicit reading budget")
    return rows


def _basis(spec: dict, artifacts: dict, *, prepared: datetime, as_of: datetime) -> dict:
    _keys(spec, {"key", "evidence_artifact_id", "source_identifier", "source_use", "fields"})
    key = _text(spec["key"])
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", key):
        raise ValueError("invalid evidence navigation key")
    record = artifacts.get(spec["evidence_artifact_id"])
    if record is None:
        raise ValueError("explicit company evidence is missing")
    evidence = EvidenceArtifact.model_validate(record)
    if evidence.source_identifier != spec["source_identifier"]:
        raise ValueError("company evidence identifier changed")
    use = ClaimSourceUseV2.model_validate({**spec["source_use"], "evidence_artifact_id": evidence.id})
    if (set(spec["source_use"]) != {"source_role", "assertion_scope", "role_basis"}
            or evidence.source_type not in {"OFFICIAL_FILING", "INVESTOR_RELATIONS"}
            or not is_source_role_compatible_with_artifact(source_type=evidence.source_type, source_role=use.source_role)
            or not is_source_use_admissible(claim_kind=ResearchClaimKind.FACT,
                                           source_role=use.source_role, assertion_scope=use.assertion_scope)):
        raise ValueError("source role cannot establish this company-business input")
    if (not evidence.is_available_at(as_of) or evidence.retrieved_at > prepared
            or prepared > as_of):
        raise ValueError("evidence acquisition/mapping preparation follows its eligible cutoff")
    if evidence.retention_mode is RetentionMode.METADATA_ONLY or evidence.extracted_structured_values is None:
        raise ValueError("metadata or report title alone cannot establish business exposure")
    url = urlsplit(evidence.source_locator)
    if url.scheme != "https" or not url.netloc or url.username or url.password:
        raise ValueError("company source link must be credential-free HTTPS")
    values, seen = [], set()
    for item in _bounded(spec["fields"], 16, minimum=1):
        _keys(item, {"field", "label", "unit", "kind", "scope_note"})
        field = _text(item["field"])
        if field in seen or field not in evidence.extracted_structured_values:
            raise ValueError("missing or duplicate exact extracted field")
        seen.add(field)
        value = evidence.extracted_structured_values[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError("unsupported retained field; no text inference or numeric coercion")
        if item["kind"] == "NUMBER":
            if not re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", value) or not Decimal(value).is_finite():
                raise ValueError("retained numeric field is not a finite decimal string")
        elif item["kind"] != "TEXT":
            raise ValueError("unsupported retained field kind")
        for name in ("label", "unit", "scope_note"):
            _text(item[name])
        values.append({**item, "value": value})
    return {"key": key, "evidence": record, "evidence_record_hash": canonical_hash(record),
            "source_use": json.loads(canonical_json(use)), "values": values,
            "retention_notice": "RETAINED_FIELDS_ONLY_NOT_ORIGINAL_DOCUMENT_REVERIFICATION",
            "original_page_verified_this_run": False,
            "units_and_business_scope": "CURATED_MAPPING_DECLARATIONS_NOT_NEW_SOURCE_EXTRACTIONS"}


def build_company_links(source_root: Path, association: dict, *, manifest_path: str = DEFAULT_MANIFEST) -> dict:
    """Bind curated mechanisms to exact retained company evidence, never to rank."""
    from .economic_market_context import render_economic_market_context
    render_economic_market_context(association)  # Existing projection/authority checks, not raw-market replay.
    parent = association["projection"]
    as_of = _clock(parent["as_of"])
    _safe_path(source_root)
    root = source_root.resolve(strict=True)
    manifest_raw, spec = _json(root, manifest_path)
    _keys(spec, {"schema_version", "semantics", "prepared_at", "prepared_by", "source_commit", "scope_note", "nodes"})
    if type(spec["schema_version"]) is not int or spec["schema_version"] != 1 or spec["semantics"] != SEMANTICS:
        raise ValueError("unsupported company reading contract")
    prepared = _clock(spec["prepared_at"])
    if prepared > as_of:
        raise ValueError("company reading links were prepared after input cutoff")
    if not isinstance(spec["source_commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", spec["source_commit"]):
        raise ValueError("company source reference must be an exact commit")
    _text(spec["prepared_by"]); _text(spec["scope_note"])
    parent_nodes = {p["node_id"]: p for p in parent["panels"]}
    nodes, seen_nodes, seen_companies, source_bytes = [], set(), set(), {}
    for node in _bounded(spec["nodes"], 8, minimum=1):
        _keys(node, {"node_id", "coverage_note", "companies"})
        node_id = node["node_id"]
        if node_id not in parent_nodes or node_id in seen_nodes:
            raise ValueError("unknown or duplicate economic node")
        seen_nodes.add(node_id); _text(node["coverage_note"])
        companies = []
        for company in _bounded(node["companies"], 8):
            _keys(company, {"ticker", "exchange", "company_name", "business_scope", "source_path", "source_blob_sha1",
                            "issuer_binding_note", "exposure_size_note", "basis", "mechanisms"})
            key = (node_id, company["ticker"], company["exchange"])
            if key in seen_companies:
                raise ValueError("duplicate company-node link is not another independent observation")
            seen_companies.add(key)
            if len(seen_companies) > 16:
                raise ValueError("company inventory exceeds reading budget; no truncation")
            path = _text(company["source_path"])
            if not path.startswith("research_cases/") or not path.endswith(".json"):
                raise ValueError("v0 selects existing research-case evidence containers only")
            if path not in source_bytes:
                source_bytes[path] = _json(root, path)
            raw, container = source_bytes[path]
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if blob != company["source_blob_sha1"]:
                raise ValueError("frozen company source bytes changed; explicit new mapping review required")
            snapshot = container["research_snapshot"]
            if any(company[k] != snapshot[k] for k in ("ticker", "exchange", "company_name")):
                raise ValueError("company identity differs from the explicitly selected source container")
            if not isinstance(company["ticker"], str) or not re.fullmatch(r"[0-9]{6}", company["ticker"]) or company["exchange"] not in {"SSE", "SZSE", "BSE"}:
                raise ValueError("v0 requires an exact A-share identity, no proxy normalization")
            for field in ("company_name", "exchange", "business_scope", "issuer_binding_note", "exposure_size_note"):
                _text(company[field])
            # This container is NOT committed/researched again. Only its selected EvidenceArtifacts are consumed.
            records = _bounded(container["evidence_artifacts"], 256, minimum=1)
            artifacts = {r["id"]: r for r in records}
            if len(artifacts) != len(records):
                raise ValueError("duplicate evidence IDs in frozen source")
            bases, ids = {}, set()
            for item in _bounded(company["basis"], 8, minimum=1):
                basis = _basis(item, artifacts, prepared=prepared, as_of=as_of)
                if basis["key"] in bases or basis["evidence"]["id"] in ids:
                    raise ValueError("duplicate company evidence basis")
                bases[basis["key"]] = basis; ids.add(basis["evidence"]["id"])
            mechanisms, channels = [], set()
            for mechanism in _bounded(company["mechanisms"], 4, minimum=1):
                _keys(mechanism, {"channel", "status", "hypothesis", "basis_keys", "next_checks"})
                channel = mechanism["channel"]
                if channel not in CHANNELS or channel in channels:
                    raise ValueError("unknown or repeated economic transmission channel")
                channels.add(channel)
                refs = _bounded(mechanism["basis_keys"], 8)
                if len(set(refs)) != len(refs) or not set(refs) <= set(bases):
                    raise ValueError("mechanism references missing company evidence")
                expected = "HYPOTHESIS_WITH_RETAINED_INPUTS" if refs else "EVIDENCE_GAP"
                if mechanism["status"] != expected:
                    raise ValueError("inputs are not confirmed transmission; absence cannot be labelled support")
                _text(mechanism["hypothesis"])
                for question in _bounded(mechanism["next_checks"], 6, minimum=1):
                    _text(question)
                mechanisms.append(mechanism)
            if set(bases) != {key for m in mechanisms for key in m["basis_keys"]}:
                raise ValueError("orphan evidence is not an attributed mechanism input")
            companies.append({**{k: company[k] for k in ("ticker", "exchange", "company_name", "business_scope", "issuer_binding_note", "exposure_size_note")},
                "source_path": path, "source_blob_sha1": blob, "source_sha256": hashlib.sha256(raw).hexdigest(),
                "source_reference": f"https://github.com/{REPOSITORY}/blob/{spec['source_commit']}/{quote(path, safe='/')}",
                "source_reference_semantics": "DECLARED_COMMIT_PLUS_VERIFIED_LOCAL_BLOB_NOT_A_GIT_ANCESTRY_PROOF",
                "basis": list(bases.values()), "mechanisms": mechanisms,
                "exposure_size": None, "elasticity": None, "benefit_direction": None,
                "current_business_freshness": "NOT_REVALIDATED", "temporal_alignment": "NOT_ESTABLISHED"})
        economic = parent_nodes[node_id]["economics"]
        nodes.append({"node_id": node_id, "coverage_note": node["coverage_note"], "companies": companies,
                      "company_coverage": "SELECTED_RETAINED_CASES_ONLY" if companies else "NO_COMPANY_EVIDENCE_SUPPLIED",
                      "economic_coverage": economic["coverage"], "economic_periods": economic["selected_periods"]})
    if seen_nodes != set(parent_nodes):
        raise ValueError("each displayed economic node needs explicit company coverage, even when empty")
    payload = {"schema_version": 1, "semantics": SEMANTICS, "as_of": parent["as_of"],
               "association_hash": association["projection_hash"], "market_session": parent["market_session"],
               "manifest": spec, "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
               "nodes": nodes, "source_authenticity": "NOT_ESTABLISHED_BY_HASH_OR_ROLE_LABEL",
               "automatic_research_routing": False, **LIMITS}
    return {"projection": payload, "projection_hash": canonical_hash(payload)}


def render_company_links(report: dict) -> str:
    p = report["projection"]
    if (report["projection_hash"] != canonical_hash(p) or p["semantics"] != SEMANTICS
            or any(p[k] != v for k, v in LIMITS.items()) or p["automatic_research_routing"] is not False):
        raise ValueError("company reading identity or authority differs")
    e = lambda value: escape(str(value), quote=True)
    parts = ['<section id="company-evidence"><h2>产业变化具体影响哪项公司业务？</h2>',
             '<p class="notice">这是选定冻结证据的业务阅读链接，不是受益股名单。传导机制均待验证；不依据行业排名或成员身份生成公司结论。</p>',
             f'<p>{e(p["manifest"]["scope_note"])}</p>',
             f'<p class="muted">映射整理：{e(p["manifest"]["prepared_at"])}；输入截止：{e(p["as_of"])}。不是 Human 阅读、认同或投资决定。</p>']
    for node in p["nodes"]:
        parts += [f'<h3>{e(node["node_id"])}</h3><p>{e(node["coverage_note"])}</p>']
        if not node["companies"]:
            parts.append('<p>尚未纳入公司披露依据；不以板块名单或关键词补齐。</p>')
        for company in node["companies"]:
            parts += [f'<h3>{e(company["company_name"])} · {e(company["ticker"])} · {e(company["exchange"])}</h3>',
                      f'<p>{e(company["business_scope"])}</p><p class="muted">{e(company["issuer_binding_note"])}</p>',
                      f'<p class="notice">暴露比例、敏感度与净受益方向未建立。{e(company["exposure_size_note"])}</p>']
            for mechanism in company["mechanisms"]:
                label = '缺少直接证据' if mechanism['status'] == 'EVIDENCE_GAP' else '有保留输入的待验证机制'
                parts += [f'<h3>{e(CHANNELS[mechanism["channel"]])} · {label}</h3><p>{e(mechanism["hypothesis"])}</p>',
                          f'<p class="muted">关联依据：{e(", ".join(mechanism["basis_keys"]) or "无")}</p>',
                          '<p>下一步核验：' + '；'.join(e(q) for q in mechanism['next_checks']) + '。</p>']
            for basis in company["basis"]:
                evidence = basis["evidence"]
                parts += [f'<details><summary>保留依据 {e(basis["key"])} · {e(evidence["source_identifier"])}</summary>',
                          f'<p>资料期末：{e(evidence.get("report_period_end") or "未记录")}；来源位置：{e(evidence.get("source_location") or "未记录页码")}</p>',
                          f'<p>公开：{e(evidence["published_at"])}<br>可用：{e(evidence["available_at"])}<br>取得：{e(evidence["retrieved_at"])}</p>',
                          f'<p>来源角色：{e(basis["source_use"]["source_role"])}；主张范围：{e(basis["source_use"]["assertion_scope"])}</p>',
                          f'<p class="notice">保留模式 {e(evidence["retention_mode"])}／重放等级 {e(evidence["replayability_level"])}。本次未重验公司原文或页码；来源角色标签不是真实性证明。报告期与全国月度指标不等同。</p>',
                          '<div class="scroll"><table><tr><th>字段／阅读标签</th><th>保留值</th><th>口径说明（映射声明）</th></tr>']
                for value in basis["values"]:
                    parts.append(f'<tr><td>{e(value["field"])} / {e(value["label"])}</td><td>{e(value["value"])} [{e(value["unit"])}]</td><td>{e(value["scope_note"])}</td></tr>')
                parts += ['</table></div>', f'<p><a href="{e(evidence["source_locator"])}" rel="noreferrer">原记录指向的来源（可能为镜像）</a> · <a href="{e(company["source_reference"])}" rel="noreferrer">精确仓库记录</a></p>',
                          f'<pre>{e(canonical_json(basis["evidence"]))}</pre></details>']
    return '\n'.join(parts + ['<p>没有评级、机会评分、持仓、执行或新的 Research 路由。<a href="company-links.json">完整公司链接与来源</a></p></section>'])


def main(argv=None) -> int:
    from .economic_release_inputs import DEFAULT_SEED, DEFAULT_REVIEWS, _new_output, load_release_inputs, render_input_context
    parser = argparse.ArgumentParser(description="Read existing Radar inputs beside exact company evidence; no network.")
    parser.add_argument('--seed', type=Path, default=DEFAULT_SEED)
    parser.add_argument('--reviews-dir', type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--parent-hints', type=Path, required=True)
    parser.add_argument('--links', type=Path, default=Path('radar_inputs/economic-market-links-v0.json'))
    parser.add_argument('--source-root', type=Path, default=Path('.'))
    parser.add_argument('--company-links', default=DEFAULT_MANIFEST)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        as_of = _clock(args.as_of)
        _new_output(args.output, args.seed, args.reviews_dir)
        if (args.output.resolve().is_relative_to(args.source_root.resolve())
                or args.source_root.resolve().is_relative_to(args.output.resolve())
                or args.output.resolve().is_relative_to(args.bundle.resolve())):
            raise ValueError('company report must be outside source and market input roots')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.company-reading-', dir=args.output.parent) as temporary:
            stage = Path(temporary) / 'reading'
            status = render_input_context(args.seed, args.reviews_dir, as_of=as_of, output=stage,
                                          bundle=args.bundle, parent_hints=args.parent_hints, links=args.links)
            if status != 0:
                return status
            from .economic_market_context import _read_json
            association = _read_json(stage / 'association.json')
            report = build_company_links(args.source_root, association, manifest_path=args.company_links)
            page = (stage / 'index.html').read_text(encoding='utf-8')
            if page.count('</main>') != 1:
                raise ValueError('existing page layout changed; no guessed insertion')
            (stage / 'index.html').write_text(page.replace('</main>', render_company_links(report) + '\n</main>'), encoding='utf-8')
            (stage / 'company-links.json').write_text(canonical_json(report) + '\n', encoding='utf-8')
            # Recheck supplied identities before publishing. This is not a concurrent data service.
            if (build_company_links(args.source_root, association, manifest_path=args.company_links) != report
                    or json.loads((stage / 'input-set.json').read_text()) != load_release_inputs(args.seed, args.reviews_dir, as_of=as_of).receipt):
                raise ValueError('company or economic input identity changed during rendering')
            _safe_path(args.output)
            if args.output.exists():
                raise ValueError('company output appeared during generation')
            stage.rename(args.output)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(f'Company reading unavailable: {type(exc).__name__}')
        return 2
    print('Read-only company evidence; benefit, magnitude and causal transmission remain unestablished')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
