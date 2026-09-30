"""Read-only price-condition watch over explicitly registered retained decision assets.

Price changes Odds. This adapter only reports qualified completed-close distance to
already-retained Human/Odds boundaries. It never changes Belief, executes Research,
creates a Recommendation/Action, sizes a position, or grants Investment Authority.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any, Callable

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.odds import ODDS_DECIMAL_CONTEXT

from . import hithink_http


VERSION = "odds-watch-v0"
SEMANTICS = "READ_ONLY_PRICE_CONDITION_ATTENTION_NOT_ODDS_STATE_OR_ACTION"
CONFIG_SEMANTICS = "READ_ONLY_ODDS_WATCH_ATTENTION_NOT_ODDS_STATE_OR_ACTION"
NO_PROXIMITY_POLICY = "NO_GLOBAL_PROXIMITY_THRESHOLD_REPORT_FACTUAL_DISTANCE_ONLY"
MAX_ACTIVE_CASES = 24
ACTIVE_STATES = {
    "ACTIVE_ODDS_WATCH", "NEEDS_REVIEW_NOW", "PRICE_UNAVAILABLE_NOT_QUIET",
    "EVIDENCE_REOPEN_WATCH",
}
ODDS_LEVELS = {
    "L0_NO_ODDS",
    "L1_ANALYST_SENSITIVITY",
    "L2_PROVISIONAL_ORDINAL",
    "L3_HUMAN_ACCEPTED_ODDS",
    "L4_HUMAN_DECISION_BOUNDARY",
}
BOUNDARY_AUTHORITIES = {"NONE", "ANALYST_DERIVED", "HUMAN_ACCEPTED_ODDS", "HUMAN_DECISION"}
WATCH_MODES = {"PRICE_CONDITION", "EVIDENCE_REOPEN"}
INACTIVE_STATES = {
    "CHALLENGED_NO_ACTIVE_TRIGGER",
    "EVIDENCE_REVIEW_ONLY_NO_PRICE_BOUNDARY",
    "UNTYPED_HISTORY_NO_ACTIVE_TRIGGER",
    "DEQUALIFIED_HISTORY_ONLY",
}
ROUTES = {
    "PRICE_ONLY_RECOMPUTE_ELIGIBLE_ONLY_IF_FROZEN_BELIEF_AND_METHOD_STILL_VALID",
    "HUMAN_PRICE_CONDITION_REVIEW_NOT_NUMERICAL_ODDS_RECOMPUTE",
    "EVIDENCE_REOPEN_RESEARCH_REVIEW_NOT_PRICE_TRIGGER",
    "PROVISIONAL_PRICE_REVIEW_REUNDERWRITE_IF_EVIDENCE_CHANGES",
}
SHAPES = {"POINT_AT_OR_BELOW", "RANGE_AT_OR_BELOW_UPPER"}
AUTHORITY = {
    "signal_transition_authority": "NONE",
    "research_authority": "NONE",
    "human_attention_authority": "NONE",
    "investment_authority": "NONE",
    "action_authority": "NONE",
}
PriceFetcher = Callable[..., Any]


def _decimal(value: object, *, field: str) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field} is not a valid decimal") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{field} must be finite and positive")
    return number


def _text(value: Decimal) -> str:
    return format(value, "f")


def _require_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _validate_maturity(level: str, authority: str, mode: str, route: str) -> None:
    """Qualification and boundary origin are not inferred from membership."""
    if level not in ODDS_LEVELS or authority not in BOUNDARY_AUTHORITIES or mode not in WATCH_MODES:
        raise ValueError("Odds Watch maturity metadata unsupported")
    if mode == "EVIDENCE_REOPEN":
        if authority != "NONE" or route != "EVIDENCE_REOPEN_RESEARCH_REVIEW_NOT_PRICE_TRIGGER":
            raise ValueError("evidence-only Watch cannot claim a price-boundary authority or route")
        return
    expected = {
        "L1_ANALYST_SENSITIVITY": ("ANALYST_DERIVED", "PROVISIONAL_PRICE_REVIEW_REUNDERWRITE_IF_EVIDENCE_CHANGES"),
        "L2_PROVISIONAL_ORDINAL": ("ANALYST_DERIVED", "PROVISIONAL_PRICE_REVIEW_REUNDERWRITE_IF_EVIDENCE_CHANGES"),
        "L3_HUMAN_ACCEPTED_ODDS": ("HUMAN_ACCEPTED_ODDS", "PRICE_ONLY_RECOMPUTE_ELIGIBLE_ONLY_IF_FROZEN_BELIEF_AND_METHOD_STILL_VALID"),
        "L4_HUMAN_DECISION_BOUNDARY": ("HUMAN_DECISION", "HUMAN_PRICE_CONDITION_REVIEW_NOT_NUMERICAL_ODDS_RECOMPUTE"),
    }
    if expected.get(level) != (authority, route):
        raise ValueError("Odds Watch level/authority/route mismatch; membership cannot upgrade Odds")


def _validate_boundary_identity(path: object, ref: object) -> None:
    if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path:
        raise ValueError("Odds Watch boundary source path malformed")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise ValueError("Odds Watch boundary source path malformed")
    if not isinstance(ref, str) or re.fullmatch(r"[0-9a-f]{40}", ref) is None:
        raise ValueError("Odds Watch boundary source ref malformed")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Odds Watch input must be a JSON object")
    return payload


def validate_config(config: dict[str, Any], registry: dict[str, Any]) -> None:
    expected = {
        "schema_version", "semantics", "registration_authority", "price_contract",
        "approaching_policy", "max_active_cases", "active_cases", "inactive_cases", "authority",
    }
    if set(config) != expected:
        raise ValueError("Odds Watch config keys differ from v0 contract")
    if config["schema_version"] != 1 or config["semantics"] != CONFIG_SEMANTICS:
        raise ValueError("Odds Watch config schema/semantics unsupported")
    authority = config["registration_authority"]
    if not isinstance(authority, dict) or authority.get("issue") != 349:
        raise ValueError("Odds Watch registration authority must bind #349")
    if authority.get("comment_id") != 5913035975:
        raise ValueError("Odds Watch registration authority comment differs")
    if authority.get("meaning") != "HUMAN_AUTHORIZED_GRADED_WATCH_REGISTRATION_NOT_INVESTMENT_AUTHORITY":
        raise ValueError("Odds Watch registration authority meaning differs")
    if config["approaching_policy"] != NO_PROXIMITY_POLICY:
        raise ValueError("Odds Watch must not invent a global proximity threshold")
    if config["max_active_cases"] != MAX_ACTIVE_CASES:
        raise ValueError("Odds Watch active-case bound differs")
    if config["authority"] != AUTHORITY:
        raise ValueError("Odds Watch config cannot gain authority")
    if registry.get("schema_version") != 1 or not isinstance(registry.get("references"), list):
        raise ValueError("Odds Watch requires the existing purpose registry")

    references = {row.get("id"): row for row in registry["references"] if isinstance(row, dict)}
    active = config["active_cases"]
    inactive = config["inactive_cases"]
    if not isinstance(active, list) or not (1 <= len(active) <= MAX_ACTIVE_CASES):
        raise ValueError("Odds Watch active cases outside bounded scope")
    if not isinstance(inactive, list):
        raise ValueError("Odds Watch inactive cases must be a list")

    seen: set[str] = set()
    for case in active:
        if not isinstance(case, dict):
            raise ValueError("Odds Watch active case must be an object")
        required = {
            "ticker", "company_name", "registry_reference_id", "recompute_route",
            "prerequisite", "conditions", "odds_level", "boundary_authority",
            "watch_mode", "boundary_source_path", "boundary_source_ref",
        }
        if set(case) != required:
            raise ValueError("Odds Watch active-case keys differ")
        ticker = _require_string(case["ticker"], field="ticker").upper()
        if ticker in seen:
            raise ValueError("Odds Watch ticker duplicated")
        seen.add(ticker)
        _require_string(case["company_name"], field="company_name")
        route = _require_string(case["recompute_route"], field="recompute_route")
        if route not in ROUTES:
            raise ValueError("Odds Watch recompute route unsupported")
        odds_level = _require_string(case["odds_level"], field="odds_level")
        boundary_authority = _require_string(case["boundary_authority"], field="boundary_authority")
        watch_mode = _require_string(case["watch_mode"], field="watch_mode")
        _validate_maturity(odds_level, boundary_authority, watch_mode, route)
        _require_string(case["prerequisite"], field="prerequisite")
        ref_id = _require_string(case["registry_reference_id"], field="registry_reference_id")
        ref = references.get(ref_id)
        if not isinstance(ref, dict) or ref.get("case") != ticker:
            raise ValueError("Odds Watch case does not match registry reference")
        use = ref.get("use")
        if odds_level in {"L3_HUMAN_ACCEPTED_ODDS", "L4_HUMAN_DECISION_BOUNDARY"}:
            if use != "HUMAN_DECISION_CHECKPOINT":
                raise ValueError("Human-level Odds Watch requires an explicit Human checkpoint")
        elif use not in {"RETAINED_RESEARCH_DOCUMENT", "RETAINED_ODDS_DOCUMENT", "HUMAN_DECISION_CHECKPOINT"}:
            raise ValueError("non-Human Odds Watch requires retained research/Odds identity")
        source = ref.get("source") or ref.get("archive_source")
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            raise ValueError("active Odds Watch registry source missing")
        blob = source.get("git_blob")
        if blob is not None and (not isinstance(blob, str) or re.fullmatch(r"[0-9a-f]{40}", blob) is None):
            raise ValueError("active Odds Watch registry blob identity malformed")
        boundary_path, boundary_ref = case["boundary_source_path"], case["boundary_source_ref"]
        if boundary_path is None:
            if boundary_ref is not None or boundary_authority == "ANALYST_DERIVED":
                raise ValueError("Odds Watch analyst boundary requires an exact source path/ref")
        else:
            _validate_boundary_identity(boundary_path, boundary_ref)

        conditions = case["conditions"]
        if not isinstance(conditions, list):
            raise ValueError("Odds Watch conditions must be a list")
        if watch_mode == "EVIDENCE_REOPEN":
            if conditions or boundary_path is not None:
                raise ValueError("evidence-only Watch cannot carry Odds price conditions")
            continue
        if not conditions:
            raise ValueError("price Watch requires a non-L0 Odds level and price condition")
        upper_values: list[Decimal] = []
        condition_ids: set[str] = set()
        for condition in conditions:
            if not isinstance(condition, dict) or set(condition) != {
                "id", "kind", "shape", "upper_price", "lower_price", "label"
            }:
                raise ValueError("Odds Watch condition keys differ")
            condition_id = _require_string(condition["id"], field="condition.id")
            if condition_id in condition_ids:
                raise ValueError("Odds Watch condition id duplicated")
            condition_ids.add(condition_id)
            _require_string(condition["kind"], field="condition.kind")
            _require_string(condition["label"], field="condition.label")
            shape = _require_string(condition["shape"], field="condition.shape")
            if shape not in SHAPES:
                raise ValueError("Odds Watch condition shape unsupported")
            upper = _decimal(condition["upper_price"], field="condition.upper_price")
            lower_raw = condition["lower_price"]
            if shape == "POINT_AT_OR_BELOW":
                if lower_raw is not None:
                    raise ValueError("point condition cannot carry lower_price")
            else:
                lower = _decimal(lower_raw, field="condition.lower_price")
                if lower > upper:
                    raise ValueError("Odds Watch range lower_price exceeds upper_price")
            upper_values.append(upper)
        if upper_values != sorted(upper_values, reverse=True):
            raise ValueError("Odds Watch conditions must be ordered from shallow to deep")

    for case in inactive:
        if not isinstance(case, dict) or set(case) != {"ticker", "company_name", "state", "reason"}:
            raise ValueError("Odds Watch inactive-case keys differ")
        ticker = _require_string(case["ticker"], field="inactive.ticker").upper()
        if ticker in seen:
            raise ValueError("Odds Watch active/inactive ticker duplicated")
        seen.add(ticker)
        _require_string(case["company_name"], field="inactive.company_name")
        state = _require_string(case["state"], field="inactive.state")
        if state not in INACTIVE_STATES:
            raise ValueError("Odds Watch inactive state unsupported")
        _require_string(case["reason"], field="inactive.reason")


def _condition_projection(condition: dict[str, Any], current_price: Decimal) -> dict[str, Any]:
    upper = _decimal(condition["upper_price"], field="condition.upper_price")
    lower = None if condition["lower_price"] is None else _decimal(
        condition["lower_price"], field="condition.lower_price"
    )
    if current_price > upper:
        state = "ABOVE_CONDITION"
        triggered = False
    elif lower is None:
        state = "AT_OR_BELOW_POINT"
        triggered = True
    elif current_price >= lower:
        state = "WITHIN_RANGE"
        triggered = True
    else:
        state = "PASSED_BELOW_RANGE"
        triggered = True
    with localcontext(ODDS_DECIMAL_CONTEXT):
        distance = current_price - upper
        distance_fraction = distance / current_price
    return {
        **condition,
        "condition_state": state,
        "attention_triggered": triggered,
        "signed_distance_to_upper_cny": _text(distance),
        "signed_distance_to_upper_fraction_of_current": _text(distance_fraction),
        "meaning": "PRICE_CONDITION_FOR_HUMAN_REVIEW_NOT_ACTION",
    }


def _source_projection(reference: dict[str, Any]) -> dict[str, Any]:
    source = reference.get("source") or reference.get("archive_source")
    if not isinstance(source, dict):
        raise ValueError("Odds Watch registry source missing")
    return {
        "registry_reference_id": reference["id"],
        "use": reference["use"],
        "source_path": source["path"],
        "source_ref": source.get("ref"),
        "source_git_blob": source.get("git_blob"),
        "meaning": "RETAINED_REGISTERED_SOURCE_IDENTITY_NOT_AUTOMATIC_ACCEPTANCE_OR_SUPERSESSION",
    }


def _boundary_source_projection(case: dict[str, Any]) -> dict[str, Any] | None:
    path = case["boundary_source_path"]
    if path is None:
        return None
    return {
        "source_path": path,
        "source_ref": case["boundary_source_ref"],
        "meaning": "EXACT_BOUNDARY_SOURCE_NOT_HUMAN_ACCEPTANCE_UNLESS_BOUNDARY_AUTHORITY_SAYS_SO",
    }


def build_watch(
    *,
    config: dict[str, Any],
    registry: dict[str, Any],
    observed_at: datetime,
    fetch_market: PriceFetcher,
    price_error_types: tuple[type[BaseException], ...] = (hithink_http.HithinkRuntimeError,),
) -> dict[str, Any]:
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("Odds Watch observed_at must be timezone-aware")
    validate_config(config, registry)
    references = {row["id"]: row for row in registry["references"]}
    rows: list[dict[str, Any]] = []

    for case in config["active_cases"]:
        base = {
            "ticker": case["ticker"],
            "company_name": case["company_name"],
            "watch_enabled": True,
            "source": _source_projection(references[case["registry_reference_id"]]),
            "boundary_source": _boundary_source_projection(case),
            "odds_level": case["odds_level"],
            "boundary_authority": case["boundary_authority"],
            "watch_mode": case["watch_mode"],
            "recompute_route": case["recompute_route"],
            "prerequisite": case["prerequisite"],
            **AUTHORITY,
        }
        if case["watch_mode"] == "EVIDENCE_REOPEN":
            rows.append({
                **base,
                "status": "EVIDENCE_REOPEN_WATCH",
                "evidence_evaluation_state": "NOT_PERFORMED_REOPEN_CONDITIONS_RETAINED_ONLY",
                "price_fetch_performed": False,
                "price": None,
                "market_timestamp": None,
                "market_data_source": None,
                "price_convention": None,
                "currency": "CNY",
                "triggered_conditions": [],
                "next_unreached_condition": None,
                "price_gap": None,
            })
            continue
        try:
            market = fetch_market(thscode=case["ticker"], observed_at=observed_at)
        except price_error_types as exc:
            rows.append({
                **base,
                "status": "PRICE_UNAVAILABLE_NOT_QUIET",
                "price_fetch_performed": True,
                "price": None,
                "market_timestamp": None,
                "market_data_source": None,
                "price_convention": None,
                "triggered_conditions": [],
                "next_unreached_condition": None,
                "price_gap": {"error_type": type(exc).__name__, "meaning": "PRICE_UNKNOWN_NO_TRIGGER_INFERRED"},
            })
            continue

        price = Decimal(str(market.market_price))
        if not price.is_finite() or price <= 0:
            raise ValueError("Odds Watch market price must be finite and positive")
        projected = [_condition_projection(item, price) for item in case["conditions"]]
        triggered = [item for item in projected if item["attention_triggered"]]
        unreached = [item for item in projected if not item["attention_triggered"]]
        # Conditions are validated shallow-to-deep. The nearest still-unreached
        # boundary is therefore the first remaining item, never an arbitrary deep level.
        next_condition = unreached[0] if unreached else None
        rows.append({
            **base,
            "status": "NEEDS_REVIEW_NOW" if triggered else "ACTIVE_ODDS_WATCH",
            "price_fetch_performed": True,
            "price": _text(price),
            "market_timestamp": market.market_timestamp.isoformat(),
            "market_data_source": market.market_data_source,
            "price_convention": market.price_convention,
            "currency": market.currency,
            "triggered_conditions": triggered,
            "next_unreached_condition": next_condition,
            "price_gap": None,
        })

    inactive = [
        {
            **case,
            "watch_enabled": False,
            "price": None,
            "price_fetch_performed": False,
            "meaning": "STATIC_SAFETY_CLASSIFICATION_NO_PRICE_TRIGGER",
            **AUTHORITY,
        }
        for case in config["inactive_cases"]
    ]
    trigger_count = sum(row["status"] == "NEEDS_REVIEW_NOW" for row in rows)
    price_gap_count = sum(row["status"] == "PRICE_UNAVAILABLE_NOT_QUIET" for row in rows)
    evidence_only_count = sum(row["status"] == "EVIDENCE_REOPEN_WATCH" for row in rows)
    price_evaluated_count = sum(row["status"] in {"ACTIVE_ODDS_WATCH", "NEEDS_REVIEW_NOW"} for row in rows)
    payload = json.loads(canonical_json({
        "version": VERSION,
        "semantics": SEMANTICS,
        "observed_at": observed_at,
        "config_hash": canonical_hash(config),
        "registry_hash": canonical_hash(registry),
        "price_contract": config["price_contract"],
        "approaching_policy": config["approaching_policy"],
        "active_case_count": len(rows),
        "attention_case_count": trigger_count,
        "price_gap_count": price_gap_count,
        "price_evaluated_case_count": price_evaluated_count,
        "evidence_only_case_count": evidence_only_count,
        "active_cases": rows,
        "inactive_cases": inactive,
        "authority": AUTHORITY,
        "limitations": [
            "PRICE_CONDITION_CROSSING_MEANS_HUMAN_REVIEW_NOT_BUY_ADD_SELL",
            "PRICE_CHANGE_DOES_NOT_PROVE_BELIEF_UNCHANGED",
            "NO_GLOBAL_APPROACHING_THRESHOLD",
            "NO_POSITION_SIZE_OR_ORDER_AUTHORITY",
            "WATCH_MEMBERSHIP_DOES_NOT_EQUAL_HUMAN_ACCEPTANCE",
            "ODDS_LEVEL_AND_BOUNDARY_AUTHORITY_MUST_REMAIN_VISIBLE",
            "EVIDENCE_REOPEN_CONDITIONS_ARE_RETAINED_NOT_AUTOMATICALLY_EVALUATED",
            "NO_AUTOMATIC_ODDS_OR_RESEARCH_SUPERSESSION",
        ],
    }))
    return {"watch": payload, "watch_hash": canonical_hash(payload)}


def render_markdown(report: dict[str, Any]) -> str:
    payload = report["watch"]
    price_evaluated = sum(row["status"] in {"ACTIVE_ODDS_WATCH", "NEEDS_REVIEW_NOW"} for row in payload["active_cases"])
    evidence_count = sum(row["status"] == "EVIDENCE_REOPEN_WATCH" for row in payload["active_cases"])
    lines = [
        "# Odds Watch v0",
        "",
        f"观察时间：{payload['observed_at']}",
        "",
        (
            f"**需要复核：{payload['attention_case_count']}** · "
            f"价格已判断：{price_evaluated} · "
            f"仅证据重开：{evidence_count} · "
            f"价格缺口：{payload['price_gap_count']} · 活跃观察：{payload['active_case_count']}"
        ),
        "",
    ]
    attention = [row for row in payload["active_cases"] if row["status"] == "NEEDS_REVIEW_NOW"]
    gaps = [row for row in payload["active_cases"] if row["status"] == "PRICE_UNAVAILABLE_NOT_QUIET"]
    quiet = [row for row in payload["active_cases"] if row["status"] == "ACTIVE_ODDS_WATCH"]
    evidence_only = [row for row in payload["active_cases"] if row["status"] == "EVIDENCE_REOPEN_WATCH"]
    if attention:
        lines += ["## 需要 Human 复核", ""]
        for row in attention:
            lines += [
                f"### {row['company_name']} {row['ticker']} · CNY{row['price']}",
                f"- 状态：`{row['status']}`",
                f"- Odds层级：`{row.get('odds_level', 'LEGACY_UNSPECIFIED')}` · 边界权限：`{row.get('boundary_authority', 'LEGACY_UNSPECIFIED')}`",
                f"- 价格时点：`{row['market_timestamp']}`",
            ]
            for condition in row["triggered_conditions"]:
                lines.append(
                    f"- 已触及：**{condition['label']}** · `{condition['condition_state']}`"
                )
            lines += [
                f"- 前提：{row['prerequisite']}",
                f"- 路由：`{row['recompute_route']}`",
                "- **这不是 BUY / ADD / SELL，也不是自动执行。**",
                "",
            ]
    if quiet:
        lines += ["## 仍在等待原边界", ""]
        for row in quiet:
            next_condition = row["next_unreached_condition"]
            lines.append(
                f"- **{row['company_name']} {row['ticker']}** · "
                f"`{row.get('odds_level', 'LEGACY_UNSPECIFIED')}` / "
                f"`{row.get('boundary_authority', 'LEGACY_UNSPECIFIED')}` · "
                f"CNY{row['price']} · 下一边界 `{next_condition['label']}` · "
                f"距离上沿 CNY{next_condition['signed_distance_to_upper_cny']}"
            )
        lines.append("")
    if evidence_only:
        lines += ["## 仅证据／重开观察（无价格边界）", "",
                  "本轮仅保留重开条件，未自动判断新证据是否满足；不计为未触界或价格缺失。", ""]
        for row in evidence_only:
            lines.append(
                f"- **{row['company_name']} {row['ticker']}** · "
                f"`{row.get('odds_level', 'L0_NO_ODDS')}` · {row['prerequisite']}"
            )
        lines.append("")
    if gaps:
        lines += ["## 价格资格缺口", ""]
        for row in gaps:
            lines.append(
                f"- **{row['company_name']} {row['ticker']}** · "
                f"`{row.get('odds_level', 'LEGACY_UNSPECIFIED')}` / "
                f"`{row.get('boundary_authority', 'LEGACY_UNSPECIFIED')}` · "
                "`PRICE_UNAVAILABLE_NOT_QUIET` · 不推断 trigger"
            )
        lines.append("")
    lines += [
        "<details>",
        f"<summary>未启用价格触发（{len(payload['inactive_cases'])}）</summary>",
        "",
    ]
    for row in payload["inactive_cases"]:
        lines.append(f"- **{row['company_name']} {row['ticker']}** · `{row['state']}` · {row['reason']}")
    lines += [
        "",
        "</details>",
        "",
        f"Watch hash: `{report['watch_hash']}`",
        "",
        "_Price changes Odds; Evidence changes Belief. Watch allocates Human review attention only. Investment Authority = NONE._",
        "",
    ]
    return "\n".join(lines)


def write_watch(*, report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "watch.json").write_text(canonical_json(report) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(render_markdown(report), encoding="utf-8")


def validate_report(report: dict[str, Any]) -> None:
    if not isinstance(report, dict) or set(report) != {"watch", "watch_hash"}:
        raise ValueError("Odds Watch report shape differs")
    payload = report["watch"]
    if report["watch_hash"] != canonical_hash(payload):
        raise ValueError("Odds Watch hash mismatch")
    if payload.get("version") != VERSION or payload.get("semantics") != SEMANTICS:
        raise ValueError("Odds Watch report version/semantics differ")
    if payload.get("authority") != AUTHORITY:
        raise ValueError("Odds Watch report gained authority")
    active = payload.get("active_cases")
    if not isinstance(active, list) or len(active) > MAX_ACTIVE_CASES:
        raise ValueError("Odds Watch report active-case bound differs")
    # Old v0 reports remain readable without inventing grades. New metadata is
    # all-or-none, so removing one qualification cannot silently make it legacy.
    metadata = {"odds_level", "boundary_authority", "watch_mode", "boundary_source", "price_fetch_performed"}
    graded = ("price_evaluated_case_count" in payload or "evidence_only_case_count" in payload
              or any(isinstance(row, dict) and metadata.intersection(row) for row in active))
    tickers: set[str] = set()
    for row in active:
        if not isinstance(row, dict) or row.get("status") not in ACTIVE_STATES:
            raise ValueError("Odds Watch active status unsupported")
        if row.get("watch_enabled") is not True or row.get("ticker") in tickers:
            raise ValueError("Odds Watch active identity/enablement differs")
        tickers.add(row.get("ticker"))
        if graded:
            if not metadata.issubset(row):
                raise ValueError("Odds Watch graded metadata incomplete")
            _validate_maturity(row["odds_level"], row["boundary_authority"], row["watch_mode"], row.get("recompute_route"))
            if row["odds_level"] in {"L3_HUMAN_ACCEPTED_ODDS", "L4_HUMAN_DECISION_BOUNDARY"}:
                if row.get("source", {}).get("use") != "HUMAN_DECISION_CHECKPOINT":
                    raise ValueError("Human-level Odds Watch requires an explicit Human checkpoint")
            boundary = row["boundary_source"]
            if boundary is not None:
                if not isinstance(boundary, dict):
                    raise ValueError("Odds Watch report boundary source malformed")
                _validate_boundary_identity(boundary.get("source_path"), boundary.get("source_ref"))
            elif row["boundary_authority"] == "ANALYST_DERIVED":
                raise ValueError("Odds Watch analyst boundary source missing")
            if row["watch_mode"] == "PRICE_CONDITION" and row["price_fetch_performed"] is not True:
                raise ValueError("price Watch lacks actual price attempt")
            if (row["watch_mode"] == "EVIDENCE_REOPEN") != (row["status"] == "EVIDENCE_REOPEN_WATCH"):
                raise ValueError("Odds Watch mode/status mismatch")
        if any(row.get(name) != "NONE" for name in AUTHORITY):
            raise ValueError("Odds Watch case gained authority")
        if row["status"] == "NEEDS_REVIEW_NOW" and not row.get("triggered_conditions"):
            raise ValueError("Odds Watch review state lacks a crossed condition")
        if row["status"] == "ACTIVE_ODDS_WATCH" and row.get("triggered_conditions"):
            raise ValueError("quiet Odds Watch case contains crossed conditions")
        if row["status"] == "EVIDENCE_REOPEN_WATCH":
            if not graded or row.get("price") is not None or row.get("market_timestamp") is not None:
                raise ValueError("evidence-only Watch cannot carry a market observation")
            if row.get("price_fetch_performed") is not False or row.get("triggered_conditions") or row.get("next_unreached_condition") is not None:
                raise ValueError("evidence-only Watch cannot carry price trigger state")
            if row.get("boundary_source") is not None or row.get("price_gap") is not None:
                raise ValueError("evidence-only Watch cannot carry a price boundary or price gap")
    counts = {
        "active_case_count": len(active),
        "attention_case_count": sum(row["status"] == "NEEDS_REVIEW_NOW" for row in active),
        "price_gap_count": sum(row["status"] == "PRICE_UNAVAILABLE_NOT_QUIET" for row in active),
    }
    if graded:
        counts.update(
            price_evaluated_case_count=sum(row["status"] in {"ACTIVE_ODDS_WATCH", "NEEDS_REVIEW_NOW"} for row in active),
            evidence_only_case_count=sum(row["status"] == "EVIDENCE_REOPEN_WATCH" for row in active),
        )
    for key, expected in counts.items():
        if type(payload.get(key)) is not int or payload[key] != expected:
            raise ValueError("Odds Watch report coverage counts differ")
    for row in payload.get("inactive_cases", []):
        if row.get("state") not in INACTIVE_STATES or row.get("watch_enabled") is not False:
            raise ValueError("Odds Watch inactive safety state differs")
        if row.get("price_fetch_performed") is not False or row.get("price") is not None:
            raise ValueError("inactive Odds Watch case cannot fetch price")


def read_and_validate(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    validate_report(payload)
    return payload
