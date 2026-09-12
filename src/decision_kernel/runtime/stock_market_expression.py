"""Bounded Stock market-expression routing from an already-qualified Sector result.

This module does not infer a beneficiary from membership. It reuses the Sector
homepage's already-bounded surfaced groups and retained current breadth leaders
only to freeze a small stock candidate set. The existing Stock price-path gate
must still pass before ``market_expression_status`` can become OBSERVED.
Company/business evidence is a separate annotation and never a candidate gate.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from decision_kernel.identity import canonical_hash
from decision_kernel.adapters.hithink import to_hithink_thscode
from . import economic_company_context as company
from . import sector_radar_discovery as discovery
from . import stock_radar_reading as stock
from .sector_radar_context import build_sector_radar_context


ROUTING_SEMANTICS = "SURFACED_SECTOR_BREADTH_LEADERS_BOUNDED_ROUTING_ONLY"
READING_SCOPE = "BOUNDED_SURFACED_SECTOR_MARKET_EXPRESSION_NOT_ALL_A_SHARES"
ORIGIN_KIND = "SECTOR_BREADTH_MARKET_EXPRESSION_CANDIDATE"
UNKNOWN_BUSINESS = "UNKNOWN"
REVIEWED_BUSINESS_LINK = "REVIEWED_BUSINESS_LINK_PRESENT"


def _validate_sector_result(result: dict, state, ledger, *, observed_at) -> None:
    if not isinstance(result, dict) or result.get("result_hash") != canonical_hash(
        {k: v for k, v in result.items() if k != "result_hash"}
    ):
        raise ValueError("Sector result hash differs")
    discovery._validate_projection(result)
    if (result["market_session"] != state.sessions[-1].isoformat()
            or result["output_market_state_hash"] != state.state_hash
            or result["event_ledger_update"]["event_ledger_hash"] != ledger.ledger_hash):
        raise ValueError("Sector result belongs to another saved market state")
    if stock.probe._clock(result["produced_at"]) > observed_at:
        raise ValueError("Sector result was produced after the Stock reading cutoff")


def _reviewed_links(linked: dict, association: dict) -> dict[tuple[str, str], dict]:
    """Exact issuer+sector reviewed links only; unrelated company evidence does not count."""
    panels = {row["node_id"]: row for row in association["projection"]["panels"]}
    found: dict[tuple[str, str], dict] = {}
    for node in linked["projection"]["nodes"]:
        panel = panels[node["node_id"]]
        sectors = [row["identity"]["thscode"] for row in panel["markets"]]
        for item in node["companies"]:
            code = to_hithink_thscode(ticker=item["ticker"], exchange=item["exchange"])
            for sector in sectors:
                key = (code, sector)
                if key in found and found[key] != item:
                    raise ValueError("one issuer-sector identity has conflicting reviewed business links")
                found[key] = item
    return found


def _leader(row: dict) -> tuple[str, str]:
    required = {"thscode", "ticker", "name", "daily_return", "turnover"}
    if not isinstance(row, dict) or not required <= set(row):
        raise ValueError("Sector breadth leader identity is incomplete")
    code, ticker, name = row["thscode"], row["ticker"], row["name"]
    if not isinstance(code, str) or not isinstance(ticker, str) or code[:6] != ticker or not name:
        raise ValueError("Sector breadth leader identity differs")
    for key in ("daily_return", "turnover"):
        value = Decimal(str(row[key]))
        if not value.is_finite() or (key == "turnover" and value < 0):
            raise ValueError("Sector breadth leader market value is invalid")
    return code, name


def candidate_label(group: dict) -> str:
    candidate = group["primary_candidate"]
    return f"{candidate['name']} {candidate['thscode']}"


def prepare_market_expression_reading(source_root: Path, state, ledger, association: dict,
                                      sector_result: dict, *, observed_at,
                                      company_manifest: str = stock.COMPANY_MANIFEST) -> dict:
    """Freeze a bounded market-expression candidate plan without beneficiary inference."""
    stock.check_observation_clock(state, observed_at)
    _validate_sector_result(sector_result, state, ledger, observed_at=observed_at)
    p = association["projection"]
    if (p["market_state_hash"] != state.state_hash or p["event_ledger_hash"] != ledger.ledger_hash
            or stock.probe._clock(p["as_of"]) > observed_at):
        raise ValueError("Stock association belongs to different or future inputs")

    linked = company.build_company_links(source_root, association, manifest_path=company_manifest)
    reviewed = _reviewed_links(linked, association)
    context = build_sector_radar_context(market_state=state, event_ledger=ledger, generated_at=observed_at)
    all_rows = {r["observation"]["thscode"]: r for u in context["universes"] for r in u["rows"]}
    families = {r["observation"]["thscode"]: u["family"] for u in context["universes"] for r in u["rows"]}

    groups = sector_result["composition"]["surfaced_groups"]
    if len(groups) > 3:
        raise ValueError("Sector surfaced-group attention budget differs")
    routed = []
    for group in groups:
        candidate, breadth = group["primary_candidate"], group["primary_breadth"]
        sector = candidate["thscode"]
        saved = all_rows.get(sector)
        if (saved is None or not saved["currently_gate_active"]
                or candidate["name"] != saved["observation"]["name"]
                or candidate["family"] != families[sector]
                or breadth["sector_thscode"] != sector
                or breadth["market_session"] != state.sessions[-1].isoformat()):
            raise ValueError("Sector surfaced primary direction differs from exact saved state")
        leaders = []
        for item in breadth["leaders"]:
            code, name = _leader(item)
            leaders.append({"thscode": code, "company_name": name, "breadth_leader": item})
        routed.append({"group": group, "sector": sector, "saved": saved, "leaders": leaders})

    direction_reserve = len(routed)
    capacity = min(stock.MAX_ISSUERS, max(0, (stock.MAX_REQUESTS - 4 - direction_reserve) // 3))
    issuers: dict[str, dict] = {}
    max_leaders = max((len(row["leaders"]) for row in routed), default=0)
    for rank in range(max_leaders):
        for route in routed:
            if rank >= len(route["leaders"]):
                continue
            item = route["leaders"][rank]
            code = item["thscode"]
            if code not in issuers and len(issuers) >= capacity:
                continue
            sector = route["sector"]
            reviewed_company = reviewed.get((code, sector))
            source = {
                "thscode": sector,
                "name": route["saved"]["observation"]["name"],
                "family": families[sector],
                "source_kind": "SURFACED_SECTOR_GROUP_PRIMARY",
                "recorded_event_ids": route["saved"]["recorded_event_ids_latest_session"],
            }
            origin = {
                "origin_kind": ORIGIN_KIND,
                "node_id": route["group"]["group_key"],
                "node_label": candidate_label(route["group"]),
                "sector_codes": [sector],
                "direction_sources": [source],
                "company": reviewed_company,
                "business_linkage_status": REVIEWED_BUSINESS_LINK if reviewed_company else UNKNOWN_BUSINESS,
                "node_relation_note": "CURRENT_MEMBERSHIP_AND_PRICE_ROUTING_ONLY_NOT_BENEFICIARY_PROOF",
                "review_question": "If decision-relevant, what public evidence establishes or rejects the business link?",
                "economic_coverage": None,
                "breadth_leader": item["breadth_leader"],
            }
            if code not in issuers:
                issuers[code] = {
                    "thscode": code,
                    "company_name": item["company_name"],
                    "origins": [],
                    "candidate_source": "SECTOR_SURFACED_GROUP_BREADTH_LEADER",
                    "business_linkage_status": UNKNOWN_BUSINESS,
                    "business_benefit_status": "NOT_ESTABLISHED",
                }
            if origin not in issuers[code]["origins"]:
                issuers[code]["origins"].append(origin)
            if reviewed_company is not None:
                issuers[code]["business_linkage_status"] = REVIEWED_BUSINESS_LINK

    selected = [issuers[k] for k in sorted(issuers)]
    used_sectors = sorted({s for item in selected for o in item["origins"] for s in o["sector_codes"]})
    directions = {code: all_rows[code] for code in used_sectors}
    order = [route["group"]["group_key"] for route in routed
             if any(route["sector"] in o["sector_codes"] for item in selected for o in item["origins"])]
    evidence_scope = [{"thscode": item["thscode"], "company_name": item["company_name"]}
                      for item in selected if item["business_linkage_status"] == REVIEWED_BUSINESS_LINK]
    request_count = 4 + len(directions) + 3 * len(selected) if selected else 0
    if (len(selected) > stock.MAX_ISSUERS or len(directions) > stock.MAX_MEMBERSHIPS
            or request_count > stock.MAX_REQUESTS):
        raise ValueError("market-expression Stock plan exceeds the existing request budget")
    linked_direction_codes = {s for item in selected for o in item["origins"]
                              if o["business_linkage_status"] == REVIEWED_BUSINESS_LINK
                              for s in o["sector_codes"]}
    body = {
        "version": stock.MARKET_EXPRESSION_VERSION,
        "semantics": stock.MARKET_EXPRESSION_SEMANTICS,
        "policy": stock.MARKET_EXPRESSION_POLICY,
        "observed_at": observed_at,
        "market_session": state.sessions[-1],
        "market_state_hash": state.state_hash,
        "event_ledger_hash": ledger.ledger_hash,
        "association_hash": association["projection_hash"],
        "company_links_hash": linked["projection_hash"],
        "company_manifest": company_manifest,
        "directions": {k: directions[k] for k in sorted(directions)},
        "issuers": selected,
        "node_order": order,
        "evidence_scope_issuers": evidence_scope,
        "all_active_direction_count": sum(r["currently_gate_active"] for r in all_rows.values()),
        "active_directions_without_stock_business_scope": sorted(set(directions) - linked_direction_codes),
        "recorded_sector_events_latest_session": context["recorded_events_latest_session"],
        "reviewed_company_coverage": READING_SCOPE,
        "reading_scope": READING_SCOPE,
        "sector_result_hash": sector_result["result_hash"],
        "candidate_source_group_count": len(groups),
        "candidate_routing": {
            "semantics": ROUTING_SEMANTICS,
            "surfaced_group_keys": [g["group_key"] for g in groups],
            "primary_sector_codes": [g["primary_candidate"]["thscode"] for g in groups],
            "candidate_capacity": capacity,
            "candidate_codes": [item["thscode"] for item in selected],
            "candidate_count": len(selected),
            "business_evidence_is_candidate_gate": False,
        },
        "maximum_request_count": request_count,
        "stock_gate_is_unvalidated_shadow_policy": True,
        **stock.LIMITS,
    }
    body["plan_hash"] = canonical_hash(body)
    return stock._plain(body)


def render_market_expression_reading(report: dict) -> str:
    """Render v7 without upgrading a market observation into a business claim."""
    p = report["projection"]
    coverage = stock._coverage(p["all_stock_observations"])
    partial = stock._partial_status(coverage, p["surfaced_stocks"])
    if (report["projection_hash"] != canonical_hash(p)
            or p["version"] != stock.MARKET_EXPRESSION_VERSION
            or p["semantics"] != stock.MARKET_EXPRESSION_SEMANTICS
            or p["policy"] != stock.MARKET_EXPRESSION_POLICY
            or any(p[k] != v for k, v in stock.LIMITS.items())
            or p["coverage"] != coverage or p["selection_scope_complete"] != coverage["scope_complete"]
            or len(p["surfaced_stocks"]) > 3
            or (partial is not None and p["status"] != partial)
            or p["status"] not in stock.STATUS_LABELS):
        raise ValueError("market-expression Stock reading identity or authority differs")
    if any(row["business_benefit_status"] != "NOT_ESTABLISHED" for row in p["all_stock_observations"]):
        raise ValueError("market expression cannot establish business benefit")
    from html import escape
    e = lambda value: escape(str(value), quote=True)
    pct = lambda value: "不可比" if value is None else f"{Decimal(str(value))*100:+.2f}%"
    parts = [
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
        '<title>股票市场表达 · Radar</title><style>body{font:16px/1.65 system-ui;margin:0;background:#f4f6f8;color:#20313d}main{max-width:980px;margin:auto;padding:24px}header,article,section{background:white;margin:16px 0;padding:24px;border:1px solid #dce3e7;border-radius:10px}.notice{padding:12px;background:#fff4d9}small{color:#52636f}pre{white-space:pre-wrap;overflow:auto}p,pre{overflow-wrap:anywhere}</style>',
        '<main><header><h1>股票市场表达 · 可以进一步看的对象</h1>',
        f'<p><strong>{len(p["surfaced_stocks"])} 只通过既有 Stock 价格观察条件</strong>；行情交易日 {e(p["market_session"])}。</p>',
        '<p class="notice">Market Expression ≠ Business Benefit。价格与成员关系可以提出问题，不能建立公司受益 Belief；不是推荐或自动 Research。</p>',
        f'<p>候选来自 Sector 已 surfaced 的 {p["candidate_source_group_count"]} 个有界组；计划检查 {coverage["planned_issuers"]} 只，不是全 A 股扫描。</p></header>',
        f'<section><h2>{e(stock.STATUS_LABELS[p["status"]])}</h2><p>已检查 {coverage["evaluated_issuers"]}；合格 {coverage["qualified_issuers"]}；条件不满足 {coverage["conditions_not_met_issuers"]}；数据不可用 {coverage["unavailable_issuers"]}。</p></section>',
    ]
    if not p["surfaced_stocks"]:
        parts.append('<section><h2>本次没有通过最终价格 gate 的市场表达</h2><p>这不是“没有股票机会”；只是这个有界候选集没有完成到可展示状态。</p></section>')
    for row in p["surfaced_stocks"]:
        if row.get("market_expression_status") != "OBSERVED":
            raise ValueError("surfaced market expression is not observed")
        path = row["stock_path"]
        parts += [
            f'<article><h2>{e(row["company_name"])} <small>{e(row["thscode"])}</small></h2>',
            '<p><strong>Market Expression = OBSERVED</strong>：它从已 surfaced Sector 的 breadth leader 有界进入，并通过既有 5/20 日相对价格条件；这仍不是买入结论。</p>',
            f'<p>5日相对沪深300：{pct(row["market_comparison"]["5"]["excess_return"])}；20日相对沪深300：{pct(row["market_comparison"]["20"]["excess_return"])}；最新原始收盘 {e(path["last_close"])} CNY。</p>',
        ]
        for origin in row["current_origins"]:
            parts.append(f'<h3>市场来源：{e(origin["node_label"])}</h3>')
            if origin.get("company") is None:
                parts.append('<p class="notice"><strong>Business Link = UNKNOWN</strong>；没有用成员身份或价格表现补写受益理由。</p>')
            else:
                c = origin["company"]
                parts += [f'<p><strong>Reviewed Business Link = PRESENT</strong>：{e(c["business_scope"])}</p>',
                          '<p class="notice"><strong>Business Benefit = NOT_ESTABLISHED</strong>；业务存在不等于净受益，仍需独立 Evidence/Judgment。</p>']
        parts.append('</article>')
    parts += ['<section><h2>完整有界结果</h2><pre>', e(stock.canonical_json({
        "routing": p["candidate_routing"], "coverage": p["coverage"],
        "all_stock_observations": p["all_stock_observations"],
        "omitted_eligible_stock_codes": p["omitted_eligible_stock_codes"],
    })), '</pre><p>Human Attention / Research / Investment authority = NONE。</p></section>',
              '<footer>SHADOW OBSERVATION ONLY · Evidence changes Belief · Price changes Odds</footer></main></html>']
    return "\n".join(parts) + "\n"
