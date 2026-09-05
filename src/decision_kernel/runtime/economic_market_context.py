"""Read-only association of reviewed economic releases and saved industry paths.

This is a curated reading relationship, not economic confirmation, a new signal,
company exposure, a taxonomy, or an input to Research/Kernel/producer decisions.
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timezone
from decimal import Context, Decimal, localcontext
from html import escape
from pathlib import Path
from typing import Any

from decision_kernel.identity import canonical_hash, canonical_json
from .economic_node_study import (
    AUTHORITY as ECONOMIC_AUTHORITY, TZ, _aware, _validate,
    compare_release_observations,
)
from .sector_radar_context import build_sector_radar_context

SEMANTICS = "READ_ONLY_ECONOMIC_MARKET_ASSOCIATION_NOT_CAUSAL_CONFIRMATION"
LINK_SEMANTICS = "REVIEWED_READING_LINK_NOT_MEMBERSHIP_TAXONOMY_OR_COMPANY_EXPOSURE"
DEFAULT_LINKS = "radar_inputs/economic-market-links-v0.json"
AUTHORITY = {**ECONOMIC_AUTHORITY, "signal_transition_authority": "NONE"}
NODES = {"cn.livestock.price_feed", "cn.express.unit_economics"}
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_OBSERVATIONS = 64
COVERAGE_LABELS = {
    "NO_OBSERVATIONS": "没有提供该节点的合格经济记录，不能判断",
    "ONE_PERIOD_ONLY": "只有一个资料期，不判断变化方向",
    "VERSION_REVIEW_REQUIRED": "同一资料期有不同版本，须明确审阅，未自动选新值",
    "NONADJACENT_PERIODS": "最近两个资料期不连续，不冒充周环比／月环比",
    "CAPTURE_ORDER_REVIEW_REQUIRED": "资料期与采集顺序不一致，未自动重排比较",
    "TWO_PERIOD_DESCRIPTIVE_COMPARISON": "所供最近两期可作描述比较，不代表经营改善已确认",
}


def _clock(value: str) -> datetime:
    return _aware(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _keys(value: Any, expected: set[str]) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("association fields disagree")


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1600:
        raise ValueError("invalid association text")
    return value


def _validate_links(links: Mapping[str, Any], context: dict, as_of: datetime) -> None:
    _keys(links, {"schema_version", "semantics", "reviewed_at", "catalog_hash", "links"})
    if type(links["schema_version"]) is not int or links["schema_version"] != 1 or links["semantics"] != LINK_SEMANTICS:
        raise ValueError("unsupported reading-link contract")
    if _clock(_text(links["reviewed_at"])) > as_of:
        raise ValueError("reading links were not reviewed by the input cutoff")
    if links["catalog_hash"] != context["catalog_hash"]:
        raise ValueError("reading-link catalog drift requires explicit review")
    if not isinstance(links["links"], list) or len(links["links"]) != 2:
        raise ValueError("v0 requires the two explicitly reviewed economic nodes")
    rows = {(u["family"], r["observation"]["thscode"]): r["observation"]
            for u in context["universes"] for r in u["rows"]}
    seen = set()
    for link in links["links"]:
        _keys(link, {"node_id", "label", "relation_note", "review_question", "targets"})
        if link["node_id"] not in NODES or link["node_id"] in seen:
            raise ValueError("unknown or duplicate economic reading node")
        seen.add(link["node_id"])
        for field in ("label", "relation_note", "review_question"):
            _text(link[field])
        if not isinstance(link["targets"], list) or not 1 <= len(link["targets"]) <= 3:
            raise ValueError("reading link requires one to three explicit industry identities")
        seen_targets = set()
        for target in link["targets"]:
            _keys(target, {"family", "thscode", "name"})
            key = (target["family"], target["thscode"])
            if key in seen_targets or key not in rows or rows[key]["name"] != target["name"]:
                raise ValueError("reading-link industry identity/family/name disagrees")
            seen_targets.add(key)


def _consecutive(before: dict, after: dict) -> bool:
    left, right = before["period"], after["period"]
    if left["kind"] != right["kind"]:
        return False
    if left["kind"] == "COLLECTION_DATE":
        return (date.fromisoformat(right["end"]) - date.fromisoformat(left["end"])).days == 7
    a, b = date.fromisoformat(left["start"]), date.fromisoformat(right["start"])
    return left["kind"] == "CALENDAR_MONTH" and b.year * 12 + b.month == a.year * 12 + a.month + 1


def _economic_panel(records: list[dict], *, as_of: datetime, market_session: date) -> dict:
    """Choose distinct supplied periods, never count recaptures as new releases."""
    periods: dict[tuple, list[dict]] = {}
    for item in records:
        period = item["period"]
        periods.setdefault((period["end"], period["start"], period["kind"]), []).append(item)
    selected = [periods[key] for key in sorted(periods)[-2:]]
    status = "NO_OBSERVATIONS" if not selected else "ONE_PERIOD_ONLY"
    comparison = None
    representatives = []
    conflicting_periods = []
    for versions in selected:
        signatures = {canonical_hash({k: v for k, v in o["source_record"].items() if k != "captured_at"}) for o in versions}
        if len(signatures) != 1:
            conflicting_periods.append(versions[0]["period"])
        # Same release bytes re-captured later are not a new period or evidence of first-public vintage.
        representatives.append(min(versions, key=lambda o: (_clock(o["system_pit_eligible_from"]), o["observation_hash"])))
    if conflicting_periods:
        status = "VERSION_REVIEW_REQUIRED"
    elif len(representatives) == 2:
        before, after = representatives
        if not _consecutive(before, after):
            status = "NONADJACENT_PERIODS"
        elif (_clock(before["system_pit_eligible_from"]) > _clock(after["system_pit_eligible_from"])
              or before["source_record"]["published_date"] > after["source_record"]["published_date"]):
            status = "CAPTURE_ORDER_REVIEW_REQUIRED"
        else:
            comparison = compare_release_observations(before, after, as_of=as_of)
            status = "TWO_PERIOD_DESCRIPTIVE_COMPARISON"
    close_at = datetime.combine(market_session, time(15), tzinfo=TZ)
    timing = [{
        "observation_hash": o["observation_hash"],
        "period_end_to_market_calendar_days": (market_session - date.fromisoformat(o["period"]["end"])).days,
        "provided_capture_after_market_close": _clock(o["system_pit_eligible_from"]) > close_at,
        "period_extends_beyond_market_session": date.fromisoformat(o["period"]["end"]) > market_session,
    } for o in records]
    return {
        "coverage": status, "coverage_label": COVERAGE_LABELS[status],
        "supplied_distinct_periods": len(periods), "selected_periods": [p[0]["period"] for p in selected],
        "conflicting_selected_periods": conflicting_periods,
        "comparison": comparison,
        "directions": {} if comparison is None else {
            c["metric_id"]: "UP" if Decimal(c["difference"]) > 0 else "DOWN" if Decimal(c["difference"]) < 0 else "UNCHANGED"
            for c in comparison["changes"]},
        "observations": records, "timing": timing,
        "publisher_coverage": "SUPPLIED_RECORDS_ONLY_NOT_LATEST_RELEASE_COVERAGE",
        "release_freshness": "NEXT_RELEASE_SCHEDULE_NOT_QUALIFIED",
        "fundamental_confirmation": "NOT_ESTABLISHED",
    }


def build_economic_market_context(*, market_state, event_ledger, observations: Sequence[Mapping[str, Any]],
                                  links: Mapping[str, Any], as_of: datetime, generated_at: datetime,
                                  reviewed_releases: Sequence[Path] = ()) -> dict:
    """Use the existing saved-market projector and source-derived economic checks."""
    _aware(as_of)
    _aware(generated_at)
    if as_of > generated_at:
        raise ValueError("input cutoff follows generation")
    if not isinstance(observations, (list, tuple)) or len(observations) > MAX_OBSERVATIONS:
        raise ValueError("economic input count exceeds bounded reading budget")
    if (not isinstance(reviewed_releases, (list, tuple))
            or len(observations) + len(reviewed_releases) > MAX_OBSERVATIONS):
        raise ValueError("combined economic input count exceeds bounded reading budget")
    # A source capture is not yet an accepted excerpt. Keep that later eligibility
    # clock without altering the existing observation's actual capture identity.
    accepted = {}
    if reviewed_releases:
        from .economic_release_review import verify_release_review
        for root in reviewed_releases:
            receipt = verify_release_review(root, as_of=as_of)
            accepted[receipt["acceptance_hash"]] = receipt
    all_observations = [*observations, *(r["observation"] for r in accepted.values())]
    with localcontext(Context(prec=28)):
        # This is a reconstructed view at the explicit cutoff, not an original run receipt.
        context = build_sector_radar_context(market_state=market_state, event_ledger=event_ledger, generated_at=as_of)
        session = date.fromisoformat(context["market_session"])
        if datetime.combine(session, time(15), tzinfo=TZ) > as_of:
            raise ValueError("saved market close follows input cutoff")
        _validate_links(links, context, as_of)
        unique, methods = {}, set()
        for item in all_observations:
            _validate(item)
            if _clock(item["system_pit_eligible_from"]) > as_of:
                raise ValueError("economic record was captured after input cutoff")
            unique[item["observation_hash"]] = json.loads(canonical_json(dict(item)))
            methods.add(item["source_record"]["capture_method"])
        if len(methods) > 1:
            raise ValueError("do not mix synthetic and public economic provenance")
        rows = {(u["family"], r["observation"]["thscode"]): r for u in context["universes"] for r in u["rows"]}
        panels = []
        for link in links["links"]:
            records = sorted((o for o in unique.values() if o["node_id"] == link["node_id"]),
                             key=lambda o: (o["period"]["end"], _clock(o["system_pit_eligible_from"]), o["observation_hash"]))
            economics = _economic_panel(records, as_of=as_of, market_session=session)
            market_rows = []
            for target in link["targets"]:
                market = rows[(target["family"], target["thscode"])]
                active = market["currently_gate_active"]
                question = ("价格满足既有观察条件；产业确认未建立。" if active else
                            "价格未满足既有观察条件；不等于市场尚未反应。")
                market_rows.append({"identity": dict(target), "saved_market": market,
                                    "reading_note": question + economics["coverage_label"] + "。"})
            panels.append({"node_id": link["node_id"], "label": link["label"],
                           "relation_note": link["relation_note"], "review_question": link["review_question"],
                           "markets": market_rows, "economics": economics})
        payload = {
            "schema_version": 1, "semantics": SEMANTICS, "as_of": as_of,
            "link_manifest": dict(links), "link_manifest_hash": canonical_hash(dict(links)),
            "market_session": session, "market_state_hash": context["market_state_hash"],
            "event_ledger_hash": context["event_ledger_hash"], "catalog_hash": context["catalog_hash"],
            "formula_version": context["formula_version"], "policy_version": context["policy_version"],
            "benchmark_thscode": context["benchmark_thscode"], "market_source": market_state.source,
            "market_freshness": context["freshness"], "panels": panels,
            "new_events_created": 0, "creates_canonical_wake": False,
            "live_prospective_evidence_created": False, "company_exposure_established": False,
            **AUTHORITY,
        }
        if accepted:
            payload["source_review_receipts"] = [{
                **{key: r[key] for key in ("acceptance_hash", "archive_hash", "source_packet_id", "review_hash",
                    "reviewer", "reviewed_at", "recorded_at", "eligible_from", "reviewer_identity", "provenance")},
                "observation_hash": r["observation"]["observation_hash"],
            } for _, r in sorted(accepted.items())]
        return json.loads(canonical_json({"generated_at": generated_at, "projection": payload,
                                          "projection_hash": canonical_hash(payload)}))


def render_economic_market_context(report: dict) -> str:
    _keys(report, {"generated_at", "projection", "projection_hash"})
    p = report["projection"]
    if (p["semantics"] != SEMANTICS or report["projection_hash"] != canonical_hash(p)
            or any(p[k] != v for k, v in AUTHORITY.items()) or p["new_events_created"] != 0
            or any(p[k] is not False for k in ("creates_canonical_wake", "live_prospective_evidence_created", "company_exposure_established"))):
        raise ValueError("invalid association hash or authority")
    e = lambda value: escape(str(value), quote=True)
    pct = lambda value: f"{Decimal(value) * 100:+.2f}%"
    parts = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>产业证据 × 行业状态</title><style>',
             'body{font:16px/1.7 system-ui,sans-serif;color:#20333d;background:#f5f7f6;margin:0}main{max-width:1120px;margin:auto;padding:24px}',
             'header,section{background:white;padding:24px;margin:18px 0;border:1px solid #d9e3e1;border-radius:10px}.columns{display:grid;grid-template-columns:1fr 1fr;gap:22px}',
             'h1{font-size:30px}h2{font-size:24px}h3{font-size:18px}.muted{color:#53646b;font-size:14px}.notice{background:#eef4f2;padding:12px}',
             'p,code,a,pre{overflow-wrap:anywhere}pre{white-space:pre-wrap;font-size:12px;max-height:380px;overflow:auto}summary{cursor:pointer;padding:10px 0;color:#14685e}',
             'table{border-collapse:collapse;font-size:13px;width:100%}td,th{padding:7px;text-align:right;border-bottom:1px solid #d9e3e1}.scroll{overflow-x:auto}a{color:#14685e}',
             '@media(max-width:760px){main{padding:10px}header,section{padding:16px}.columns{grid-template-columns:1fr}h1{font-size:25px}}</style></head><body><main>',
             '<header><h1>产业证据 × 行业状态</h1><p>先看价格路径，再核对经营指标；两者并列，不合成机会分数。</p>',
             '<p><strong>SHADOW OBSERVATION ONLY · NOT RESEARCH · NOT A RECOMMENDATION</strong></p>',
             f'<p>保存行情交易日：<strong>{e(p["market_session"])}</strong><br>输入知识截止：{e(p["as_of"])}<br>页面生成：{e(report["generated_at"])}</p>',
             '<p class="notice">只读所提供的保存数据，未重新获取行情或检查官方最新发布。经济资料期、公开日期、系统采集时间和价格日期并不相同。采集晚于价格收盘的资料不回填到历史信号。</p></header>']
    for panel in p["panels"]:
        economics = panel["economics"]
        parts.extend([f'<section><h2>{e(panel["label"])}</h2><p>{e(panel["relation_note"])}</p>',
                      '<div class="columns"><div><h3>价格路径 · 分层读取</h3>'])
        for row in panel["markets"]:
            identity, saved = row["identity"], row["saved_market"]
            parts.append(f'<h3>{e(identity["name"])} · {e(identity["thscode"])} · {e(identity["family"])}</h3><p>{e(row["reading_note"])}</p>')
            parts.append('<div class="scroll"><table><thead><tr><th>窗口</th><th>行业</th><th>基准</th><th>超额</th><th>层内排名</th></tr></thead><tbody>')
            for n in (5, 20, 60):
                h = saved["observation"][f"horizon_{n}"]
                parts.append('<tr>' + ''.join(f'<td>{e(v)}</td>' for v in (f'{n}日', pct(h['sector_return']), pct(h['benchmark_return']), pct(h['excess_return']), h['cross_sectional_rank'])) + '</tr>')
            parts.append('</tbody></table></div>')
            parts.append(f'<p class="muted">既有 persistent：{e(saved["gates"]["persistent"]["current"])}；acceleration：{e(saved["gates"]["acceleration"]["current"])}。当日账本事件 {len(saved["recorded_event_ids_latest_session"])} 条；本页新建 0 条。</p>')
        parts.append(f'</div><div><h3>经济指标 · {e(economics["coverage_label"])}</h3>')
        comp = economics["comparison"]
        if comp is not None:
            selected = economics['selected_periods']
            parts.append(f'<p class="muted">所供比较期：{e(selected[0]["start"])}—{e(selected[0]["end"])} → {e(selected[1]["start"])}—{e(selected[1]["end"])}</p>')
            parts.append('<div class="scroll"><table><thead><tr><th>指标</th><th>前期</th><th>后期</th><th>变化</th></tr></thead><tbody>')
            labels = {m['metric_id']: m.get('label', '收入/件数结构代理') for o in economics['observations'] for m in o['metrics'] + o['derived']}
            for c in comp["changes"]:
                parts.append('<tr>' + ''.join(f'<td>{e(v)}</td>' for v in (labels[c['metric_id']] + ' [' + c['unit'] + ']', c['previous'], c['current'], pct(c['change_ratio']))) + '</tr>')
            parts.append('</tbody></table></div>')
        parts.append('<p class="muted">变化是未季调的已报数值比较，不是利润、同质服务价格或公司受益证明。两期记录不证明连续发布覆盖；未核验下次发布时间，不能判成逾期或确认没有新消息。</p>')
        parts.append(f'<p><strong>待核验问题（仅导读，不自动创建 Research）：</strong>{e(panel["review_question"])}</p></div></div>')
        for observation, timing in zip(economics["observations"], economics["timing"], strict=True):
            _validate(observation)  # Reuse official URL/source semantics before emitting a link.
            source = observation["source_record"]
            parts.append(f'<details><summary>{e(source["title"])} · 资料期 {e(observation["period"]["start"])}—{e(observation["period"]["end"])}</summary>')
            parts.append(f'<p>公开日期：{e(source["published_date"])}（仅日期）；实际采集：{e(source["captured_at"])}<br>出处标记：{e(source["capture_method"])}</p>')
            for review in p.get("source_review_receipts", []):
                if review["observation_hash"] == observation["observation_hash"]:
                    parts.append(f'<p class="notice">来源摘录审阅：{e(review["reviewer"])}（自报身份，非认证）；'
                                 f'审阅时间：{e(review["reviewed_at"])}；收录时间：{e(review["recorded_at"])}。'
                                 f'用于本读取通道不早于：{e(review["eligible_from"])}。'
                                 '这是来源审阅，不是 Human 投资判断或基本面确认。'
                                 f'<br>审阅凭证：<code>{e(review["acceptance_hash"])}</code></p>')
            if timing["provided_capture_after_market_close"]:
                parts.append('<p class="notice">本条采集凭证晚于保存行情收盘，不证明它曾进入当天信号；也不代表市场此前不知道这条公开资料。</p>')
            if timing["period_extends_beyond_market_session"]:
                parts.append('<p class="notice">经济资料期晚于价格状态，不可视作同时点确认。</p>')
            parts.append(f'<p>距行情日 {e(timing["period_end_to_market_calendar_days"])} 个自然日（不是发布逾期天数）。</p><a href="{e(source["source_url"])}" rel="noreferrer">打开指定官方原文</a><pre>{e(source["excerpt"])}</pre><code>{e(observation["observation_hash"])}</code></details>')
        parts.append('</section>')
    parts.append(f'<footer><p>所有认知／提醒／投资权限 = NONE。没有公司暴露映射、自动因果确认、阈值学习或候选写入。</p><p>Market: <code>{e(p["market_state_hash"])}</code><br>Association: <code>{e(report["projection_hash"])}</code></p><a href="association.json">本页完整数据与来源记录</a></footer></main></body></html>')
    return '\n'.join(parts) + '\n'


def _read_json(path: Path) -> Any:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink input is not an exact saved file")
    with path.open('rb') as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("association input exceeds byte budget")
    def unique(pairs):
        value = {}
        for k, v in pairs:
            if k in value:
                raise ValueError("duplicate JSON key")
            value[k] = v
        return value
    return json.loads(raw, object_pairs_hook=unique)


def main(argv=None) -> int:
    from .sector_parent_hints import load_sector_parent_hints
    from .sector_radar_persistence import load_sector_radar_persistent_bundle
    parser = argparse.ArgumentParser(description='Read saved industry state beside reviewed economic records; no network.')
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--parent-hints', type=Path, required=True)
    parser.add_argument('--links', type=Path, default=Path(DEFAULT_LINKS))
    parser.add_argument('--observation', type=Path, action='append', default=[])
    parser.add_argument('--reviewed-release', type=Path, action='append', default=[])
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    owned = False
    try:
        inputs = [args.parent_hints, args.links, *args.observation]
        if len(args.observation) + len(args.reviewed_release) > MAX_OBSERVATIONS:
            raise ValueError('economic input count exceeds bounded reading budget')
        if (args.output.exists() or args.output.is_symlink()
                or args.output.resolve().is_relative_to(args.bundle.resolve())
                or any(args.output.resolve().is_relative_to(p.resolve()) for p in args.reviewed_release)
                or any(args.output.resolve().is_relative_to(p.parent.resolve()) for p in inputs)):
            raise ValueError('output must be a new directory outside input directories')
        hints = load_sector_parent_hints(args.parent_hints)
        bundle = load_sector_radar_persistent_bundle(args.bundle,
            expected_repository="auguspp/decision-kernel",
            expected_workflow=".github/workflows/sector-radar-shadow.yml",
            expected_parent_hint_mapping_hash=hints.mapping_hash)
        report = build_economic_market_context(market_state=bundle.market_state, event_ledger=bundle.event_ledger,
            observations=[_read_json(p) for p in args.observation], links=_read_json(args.links),
            as_of=_clock(args.as_of), generated_at=datetime.now(timezone.utc),
            reviewed_releases=args.reviewed_release)
        page = render_economic_market_context(report)
        args.output.mkdir(parents=True, exist_ok=False)
        owned = True
        (args.output / 'index.html').write_text(page, encoding='utf-8')
        (args.output / 'association.json').write_text(canonical_json(report) + '\n', encoding='utf-8')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        if owned:
            shutil.rmtree(args.output)
        print(f'Economic/market reading unavailable: {exc}')
        return 2
    print('Read-only economic/market association; no new signal or fundamental confirmation')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
