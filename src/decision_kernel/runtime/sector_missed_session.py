"""Offline reconstruction of a sealed four-response Sector prefix, not production.

Reuses the original normalizers, pre-opening qualification and daily preparation.
No HTTP client, recovery installation, event emission or Stock/Research dispatch.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import re
from typing import Any

from decision_kernel.adapters.hithink import latest_completed_a_share_session, normalize_hithink_calendar
from decision_kernel.adapters.hithink_index import (
    normalize_hithink_completed_index_history,
    normalize_hithink_index_snapshot,
    normalize_hithink_industry_catalog,
)
from decision_kernel.identity import canonical_hash, canonical_json
from . import sector_radar_audit as audit
from .hithink_http import HITHINK_CALENDAR_PATH
from .hithink_index_http import HITHINK_INDEX_CATALOG_PATH, HITHINK_INDEX_HISTORY_PATH, HITHINK_INDEX_SNAPSHOT_PATH
from .sector_radar_daily import prepare_sector_radar_daily_run
from .sector_radar_state import serialize_sector_radar_market_state
from .stock_radar_reading import _qualify_stock_index_snapshot

SEMANTICS = "HISTORICAL_RECONSTRUCTION_NOT_NATURAL_PRODUCTION_OR_RESTORE_AUTHORITY"
STATUS = "PARTIAL_RECONSTRUCTED_SECTOR_PREFIX_ONLY"
_SHA = re.compile(r"^[0-9a-f]{40}$")


def reconstruct_sector_prefix(
    root: Path, *, expected_audit_hash: str, origin_run_id: int,
    origin_commit: str, market_session: date, reconstruction_commit: str,
    reconstructed_at: datetime,
) -> dict[str, bytes]:
    """Return create-only reading files; caller owns remote artifact binding.

    The expected audit hash must come from the independently bound source archive,
    never from a fresh local rehash of modified inputs. v0 accepts only a REJECTED
    audit with exactly the four successful pre-enrichment responses. Missing or
    later-acquired members cannot be filled using current data.
    """
    if (type(origin_run_id) is not int or origin_run_id <= 0
            or not isinstance(origin_commit, str) or not _SHA.fullmatch(origin_commit)
            or not isinstance(reconstruction_commit, str) or not _SHA.fullmatch(reconstruction_commit)
            or type(market_session) is not date):
        raise ValueError("reconstruction requires exact run/commit/session identities")
    reconstructed_at = audit._clock(reconstructed_at)
    manifest = audit.validate_sector_radar_input_audit_integrity(root)
    if not audit._hash_string(expected_audit_hash) or manifest["audit_hash"] != expected_audit_hash:
        raise ValueError("reconstruction source differs from the independently bound audit")
    if manifest["status"] != "REJECTED" or len(manifest["requests"]) != 4:
        raise ValueError("v0 requires a rejected, four-response Sector prefix")
    context, hints, resolution = audit._restore_audit_inputs(root)
    if context.run_id != origin_run_id or context.commit_sha != origin_commit:
        raise ValueError("reconstruction origin run/commit binding disagrees")
    records = manifest["requests"]
    receipts = [audit._clock(r["captured_at"]) for r in records]
    cutoff = receipts[-1]
    if receipts != sorted(receipts) or not context.observed_at <= receipts[0] <= cutoff <= reconstructed_at:
        raise ValueError("reconstruction capture/execution clocks disagree")
    if resolution.market_state.updated_at > cutoff or hints.captured_at > cutoff:
        raise ValueError("reconstruction parent inputs exceed the captured cutoff")
    codes = tuple(series.thscode for series in resolution.market_state.series)
    expected = (
        (HITHINK_CALENDAR_PATH, {}),
        (HITHINK_INDEX_CATALOG_PATH, {"tag": "industry"}),
        (HITHINK_INDEX_SNAPSHOT_PATH, {"thscodes": ",".join(codes)}),
    )
    for record, (path, params) in zip(records[:3], expected):
        if record["path"] != path or record["params"] != params:
            raise ValueError("reconstruction prefix request identity disagrees")
    history_request = records[3]
    if (history_request["path"] != HITHINK_INDEX_HISTORY_PATH
            or history_request["params"]["thscode"] != resolution.market_state.benchmark_thscode
            or history_request["params"]["interval"] != "1d"):
        raise ValueError("reconstruction benchmark request identity disagrees")
    envelopes = []
    for record, received_at in zip(records, receipts):
        if record["error_type"] is not None or record["response_file"] is None:
            raise ValueError("reconstruction cannot invent an unreceived response")
        envelope = json.loads((root / record["response_file"]).read_text(encoding="utf-8"))
        if not isinstance(envelope, dict) or not isinstance(envelope.get("data"), dict):
            raise ValueError("retained provider response must contain an object data envelope")
        ready_ms = envelope["data"].get("timestamp")
        if ready_ms is not None:
            if type(ready_ms) is not int or ready_ms <= 0:
                raise ValueError("provider data-ready clock is invalid")
            if datetime.fromtimestamp(ready_ms / 1000, tz=timezone.utc) > received_at:
                raise ValueError("provider data-ready clock follows original receipt")
        envelopes.append(envelope)
    sessions = normalize_hithink_calendar(envelopes[0])
    if latest_completed_a_share_session(sessions, observed_at=cutoff) != market_session:
        raise ValueError("requested session is not the captured completed session")
    after_parent = tuple(d for d in sessions if resolution.market_state.sessions[-1] < d <= market_session)
    if after_parent != (market_session,):
        raise ValueError("reconstruction cannot skip an unobserved intermediate session")
    catalog = normalize_hithink_industry_catalog(envelopes[1])
    snapshot = normalize_hithink_index_snapshot(envelopes[2], requested_thscodes=codes)
    history = normalize_hithink_completed_index_history(
        envelopes[3], thscode=resolution.market_state.benchmark_thscode,
        sessions=sessions, observed_at=cutoff,
    )
    if history.response_session != market_session or history.expected_latest_session != market_session:
        raise ValueError("benchmark history does not reach the requested session")
    start, end = (int(history_request["params"][k]) for k in ("start", "end"))
    if start > end or any(not start <= row["date_ms"] <= end for row in envelopes[3]["data"]["item"]):
        raise ValueError("benchmark rows fall outside the recorded request window")
    qualified, expiry = _qualify_stock_index_snapshot(
        snapshot, history, sessions, observed_at=cutoff, received_at=receipts[2],
    )
    preparation = prepare_sector_radar_daily_run(
        market_state=resolution.market_state, catalog=catalog, qualified_snapshot=qualified,
        parent_hints=hints, prepared_at=cutoff, next_completed_session_after_state=market_session,
    )
    entries = [asdict(entry) for selection in (preparation.broad_entries, preparation.granular_entries)
               for entry in selection.candidates]
    plan = asdict(preparation.acquisition_plan)
    implementation = {**audit._implementation(), "runtime/sector_missed_session.py": audit._sha(Path(__file__).read_bytes())}
    calculation = {
        "calculation_implementation_hash": canonical_hash(implementation),
        "market_session": market_session,
        "source_cutoff": cutoff,
        "availability_scope": "ORIGINAL_CAPTURE_WINDOW_NOT_CLAIMED_AVAILABLE_AT_MARKET_CLOSE",
        "input_audit_hash": expected_audit_hash,
        "input_market_state_hash": resolution.market_state.state_hash,
        "reconstructed_market_state_hash": preparation.output_market_state_hash,
        "qualified_snapshot_hash": preparation.qualified_snapshot_hash,
        "preparation_hash": preparation.preparation_hash,
        "formula_version": preparation.state_update.state.formula_version,
        "entries": entries,
        "enrichment_plan": plan,
        "original_preopen_qualification_expires_at": expiry,
        "stock": {"status": "NOT_RECONSTRUCTED", "candidate_codes": None,
                  "missing_inputs": ["HISTORICAL_MEMBERSHIPS_NOT_RETAINED", "HISTORICAL_STOCK_SNAPSHOT_NOT_RETAINED"]},
        "coverage": {"index_series": len(codes), "broad_entries": len(preparation.broad_entries.candidates),
                     "granular_entries": len(preparation.granular_entries.candidates),
                     "scope_complete": False},
    }
    report = {
        "schema_version": 1, "status": STATUS, "semantics": SEMANTICS,
        "original": {"repository": context.repository, "workflow": context.workflow_path,
                     "run_id": context.run_id, "attempt": context.run_attempt,
                     "commit": context.commit_sha, "status": manifest["status"],
                     "error_type": manifest["error_type"], "implementation": manifest["implementation"]},
        "reconstruction_commit": reconstruction_commit, "implementation": implementation,
        "reconstructed_at": reconstructed_at, "input_provenance": manifest["provenance"],
        "calculation": calculation, "calculation_hash": canonical_hash(calculation),
        "natural_acceptance": False, "production_restore_authority": False,
        "current_live_market_qualification": "NOT_ESTABLISHED",
        "event_ledger_modified": False, "market_provider_requests": 0,
        "research_executed": False, **audit.AUTHORITY,
    }
    files = {
        "reconstructed-market-state.json": serialize_sector_radar_market_state(preparation.state_update.state).encode(),
        "unchanged-event-ledger.json": (root / "inputs/candidate-events.json").read_bytes(),
    }
    report["files"] = {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in files.items()}
    report["reconstruction_hash"] = canonical_hash(report)
    files["reconstruction.json"] = canonical_json(report).encode()
    lines = [f"# {market_session} 板块历史重建（部分交付）", "",
             f"输入属性：{manifest['provenance']}。",
             "仅重建已保存的指数输入；不是当日自然运行成功，也不是今日股票推荐。",
             f"原运行：{origin_run_id}；重建时间：{reconstructed_at.isoformat()}。",
             f"来源检查截点：{cutoff.isoformat()}；不是声称这些数据在收盘瞬间已经可得。", "",
             "| 板块 | 代码 | 新状态 | 5日相对基准超额 | 20日相对基准超额 |", "|---|---|---|---:|---:|"]
    from decimal import Decimal
    for entry in entries:
        name = escape(str(entry['name'])).replace('|', '&#124;').replace('\n', ' ')
        lines.append(f"| {name} | {entry['thscode']} | {entry['event_type']} | "
                     f"{entry['horizon_5_excess_return'] * Decimal(100):+.2f}pct | "
                     f"{entry['horizon_20_excess_return'] * Decimal(100):+.2f}pct |")
    lines += ["", f"共 {len(entries)} 个状态进入项；不是 {len(entries)} 只股票。", "",
              f"股票尚未重建：原计划需要 {plan['distinct_membership_request_count']} 份当时成员表及当时全市场股票截面，原失败包没有这些输入。",
              "缺口不能用今日成员倒填，也不能解释成零只股票合格。此读取不写生产状态，不改旧事件账本，不发起研究、Odds或交易。"]
    files["summary.md"] = ('\n'.join(lines) + '\n').encode()
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-root', type=Path, required=True)
    parser.add_argument('--expected-audit-hash', required=True)
    parser.add_argument('--origin-run-id', type=int, required=True)
    parser.add_argument('--origin-commit', required=True)
    parser.add_argument('--market-session', type=date.fromisoformat, required=True)
    parser.add_argument('--reconstruction-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        source, output = args.audit_root.resolve(), args.output.resolve()
        if source == output or source in output.parents or output in source.parents:
            raise ValueError('reconstruction output must be separate from original input')
        files = reconstruct_sector_prefix(
            args.audit_root, expected_audit_hash=args.expected_audit_hash,
            origin_run_id=args.origin_run_id, origin_commit=args.origin_commit,
            market_session=args.market_session, reconstruction_commit=args.reconstruction_commit,
            reconstructed_at=datetime.now(timezone.utc),
        )
        args.output.mkdir(parents=True, exist_ok=False)
        for name, data in files.items():
            with (args.output / name).open('xb') as stream:
                stream.write(data)
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        print(f'RECONSTRUCTION_NOT_DELIVERED: {type(exc).__name__}: {exc}')
        return 2
    print(STATUS)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
