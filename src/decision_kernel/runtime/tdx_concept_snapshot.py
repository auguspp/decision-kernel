"""TDX/eltdx completed-session concept cross-section; Eastmoney is secondary.

This is a source-native TDX observation, not a taxonomy translation.  Capture keeps
the exact eltdx version/wheel identity, bounded host observations, normalized
source models, and the board files materialized by eltdx.  Replay is network-free.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext, Context
from pathlib import Path
from typing import Any, Callable

from decision_kernel.identity import canonical_hash, canonical_json

VERSION = "tdx-concept-snapshot-v1"
WORKFLOW = "tdx-concept-snapshot"
ELTDX_VERSION = "3.2.2"
UPSTREAM_INSPECTED = "d19ac86f2bae7565660a89baf94a3fcc531fac93"
MAX_CONCEPTS = 4096
HISTORY_COUNT = 15
HISTORY_BATCH = 12
MAX_PROTOCOL_ATTEMPTS = 3
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
SOURCE_FILES = {
    ".eltdx_board_cache.json",
    "infoharbor_block.dat",
    "tdxhy.cfg",
    "security_list.json",
}
AUTHORITY = {
    "research_authority": "NONE",
    "odds_authority": "NONE",
    "action_authority": "NONE",
    "investment_authority": "NONE",
}
POLICY = {
    "version": VERSION,
    "taxonomy": "TDX_CATEGORY_CONCEPT_SOURCE_NATIVE_NOT_EASTMONEY_BK_OR_HITHINK_TI",
    "windows": [1, 5, 10],
    "window_basis": "COMPLETED_TRADING_SESSION_CLOSE_TO_CLOSE",
    "history_count": HISTORY_COUNT,
    "history_batch": HISTORY_BATCH,
    "maximum_concepts": MAX_CONCEPTS,
    "maximum_protocol_attempts": MAX_PROTOCOL_ATTEMPTS,
    "host_probe_timeout_seconds": "1.5",
    "protocol_timeout_seconds": "5",
    "eastmoney_role": "SECONDARY_BEST_EFFORT_NOT_REQUIRED",
    "historical_membership": "NOT_ESTABLISHED",
    "source_publication_time": "UNKNOWN",
    "raw_protocol_frames": "NOT_EXPOSED_BY_ELTDX_BOARD_HELPER",
}

class TdxConceptError(ValueError):
    pass

def require(condition: bool, reason: str) -> None:
    if not condition:
        raise TdxConceptError(reason)

def _encoded(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")

def _plain(value: Any) -> Any:
    return json.loads(canonical_json(value))

def _clock(value: Any) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise TdxConceptError("CLOCK_INVALID")
    require(result.tzinfo is not None, "CLOCK_NAIVE")
    return result

def _day(value: Any) -> date:
    try:
        return value if isinstance(value, date) and not isinstance(value, datetime) else date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise TdxConceptError("MARKET_SESSION_INVALID") from exc

def _dec(value: Any) -> Decimal:
    require(value is not None and not isinstance(value, bool), "NUMERIC_VALUE_MISSING")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TdxConceptError("NUMERIC_VALUE_INVALID") from exc
    require(result.is_finite(), "NUMERIC_VALUE_INVALID")
    return result

def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text

def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, float):
        require(value == value and value not in {float("inf"), float("-inf")}, "NONFINITE_FLOAT_REJECTED")
        return Decimal(str(value))
    if isinstance(value, (str, int, bool, Decimal)) or value is None:
        return value
    return str(value)

def workflow_identity(env: dict[str, str], expected_code: str) -> dict[str, str]:
    keys = (
        "GITHUB_REPOSITORY", "GITHUB_WORKFLOW", "GITHUB_REF", "GITHUB_EVENT_NAME",
        "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA",
    )
    require(
        isinstance(expected_code, str)
        and re.fullmatch(r"[0-9a-f]{40}", expected_code) is not None
        and env.get("GITHUB_REPOSITORY") == "auguspp/decision-kernel"
        and env.get("GITHUB_WORKFLOW") == WORKFLOW
        and env.get("GITHUB_REF") == "refs/heads/main"
        and env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and env.get("GITHUB_RUN_ATTEMPT") == "1"
        and re.fullmatch(r"[1-9][0-9]{0,19}", env.get("GITHUB_RUN_ID", "")) is not None
        and env.get("GITHUB_SHA") == expected_code,
        "WORKFLOW_IDENTITY_REJECTED",
    )
    return {key: env[key] for key in keys}

def _implementation() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    paths = ("identity.py", "runtime/tdx_concept_snapshot.py")
    return {
        path: hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in paths
    }

def _safe_root(root: Path) -> None:
    require(not root.is_symlink() and not any(p.is_symlink() for p in root.parents), "UNSAFE_PATH")

def _file_records(root: Path) -> list[dict[str, Any]]:
    source = root / "source-files"
    require(source.is_dir() and not source.is_symlink(), "SOURCE_FILES_MISSING")
    paths = sorted(p for p in source.iterdir() if p.is_file())
    require({p.name for p in paths} == SOURCE_FILES and not any(p.is_symlink() for p in paths),
            "SOURCE_FILE_SET_REJECTED")
    records = []
    for path in paths:
        raw = path.read_bytes()
        require(0 < len(raw) <= MAX_FILE_BYTES, "SOURCE_FILE_SIZE_REJECTED")
        records.append({
            "name": path.name,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    return records

def _inventory(root: Path) -> dict[str, dict[str, Any]]:
    _safe_root(root)
    allowed = {
        "plan.json", "source.json", "observation.json", "summary.md",
        *{f"source-files/{name}" for name in SOURCE_FILES},
    }
    files: dict[str, dict[str, Any]] = {}
    total = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        require(not path.is_symlink(), "UNSAFE_PATH")
        name = path.relative_to(root).as_posix()
        if name == "capture.json":
            continue
        require(name in allowed, "FILE_SCOPE_REJECTED")
        raw = path.read_bytes()
        total += len(raw)
        require(len(raw) <= MAX_FILE_BYTES and total <= MAX_TOTAL_BYTES, "CAPTURE_BUDGET_REJECTED")
        files[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return files

def _bar_rows(series: Any) -> list[dict[str, Any]]:
    bars = getattr(series, "bars", None)
    require(isinstance(bars, (list, tuple)), "HISTORY_SERIES_REJECTED")
    return [_jsonable(bar) for bar in bars]

def live_source(output: Path, market_session: date) -> dict[str, Any]:
    """One bounded eltdx acquisition. No Eastmoney request and no provider secret."""
    from importlib.metadata import version as package_version
    from eltdx import TdxClient
    from eltdx.hosts import DEFAULT_HOSTS, probe_hosts

    require(package_version("eltdx") == ELTDX_VERSION, "ELTDX_VERSION_REJECTED")
    source_dir = output / "source-files"
    os.environ["ELTDX_BOARD_DATA_DIR"] = str(source_dir)
    probe_rows = probe_hosts(DEFAULT_HOSTS, timeout=1.5, max_workers=32, persist=False)
    by_host = {row.host: row for row in probe_rows}
    order = {host: i for i, host in enumerate(DEFAULT_HOSTS)}
    reachable = sorted(
        (row for row in probe_rows if row.ok),
        key=lambda row: (row.latency_ms if row.latency_ms is not None else float("inf"), order.get(row.host, 10**9)),
    )
    require(reachable, "NO_TDX_HOST_REACHABLE")
    host_probes = [{
        "host": host,
        "ok": bool(by_host[host].ok) if host in by_host else False,
        "latency_ms": by_host[host].latency_ms if host in by_host else None,
        "error_type": by_host[host].error if host in by_host else "NOT_PROBED",
    } for host in DEFAULT_HOSTS]

    client = None
    attempts = []
    handshake = None
    chosen_host = None
    for row in reachable[:MAX_PROTOCOL_ATTEMPTS]:
        started = datetime.now(timezone.utc)
        candidate = None
        try:
            candidate = TdxClient(
                host=row.host, timeout=5, probe_hosts=False,
                pool_size=4, server_count=1, connections_per_server=4,
            )
            candidate.connect()
            hs = candidate.session.handshake()
            finished = datetime.now(timezone.utc)
            attempts.append({
                "host": row.host, "started_at": started, "finished_at": finished,
                "status": "CONNECTED", "error_type": None,
            })
            client, handshake, chosen_host = candidate, hs, row.host
            break
        except Exception as exc:  # Safe: retain type only, never remote text.
            finished = datetime.now(timezone.utc)
            attempts.append({
                "host": row.host, "started_at": started, "finished_at": finished,
                "status": "CONNECT_FAILED", "error_type": type(exc).__name__,
            })
            if candidate is not None:
                try:
                    candidate.close()
                except Exception:
                    pass
    require(client is not None and handshake is not None and chosen_host is not None,
            "TDX_PROTOCOL_CONNECT_FAILED")

    try:
        table = client.helpers.board_quotes(category="概念", refresh=True)
        require(0 < table.count <= MAX_CONCEPTS, "CATALOG_SCOPE_REJECTED")
        require(all(getattr(row, "quote", None) is not None for row in table.rows),
                "SNAPSHOT_CATALOG_INCOMPLETE")
        codes = [row.full_code for row in table.rows]
        histories = client.bars.get(
            codes, period="day", count=HISTORY_COUNT, kind="index", batch_size=HISTORY_BATCH
        )
        require(isinstance(histories, dict), "HISTORY_BATCH_REJECTED")
        boards = []
        for index, row in enumerate(table.rows):
            series = histories.get(row.full_code)
            boards.append({
                "source_order": index,
                "board_code": row.board_code,
                "board_name": row.board_name,
                "full_code": row.full_code,
                "snapshot": _jsonable(row.quote),
                "bars": _bar_rows(series) if series is not None else [],
            })
        return {
            "source_kind": "ELTDX_TDX_7709",
            "package_version": ELTDX_VERSION,
            "wheel_sha256": os.environ.get("ELTDX_WHEEL_SHA256", "UNKNOWN"),
            "upstream_inspected_commit": UPSTREAM_INSPECTED,
            "chosen_host": chosen_host,
            "host_probes": _jsonable(host_probes),
            "protocol_attempts": _jsonable(attempts),
            "handshake": _jsonable(handshake),
            "prepared_date": table.prepared_date.isoformat(),
            "requested_market_session": market_session.isoformat(),
            "boards": boards,
            "source_file_records": _file_records(output),
            "raw_protocol_frames": POLICY["raw_protocol_frames"],
        }
    finally:
        client.close()

def build_observation(source: dict[str, Any], market_session: date) -> dict[str, Any]:
    require(isinstance(source, dict)
            and source.get("source_kind") == "ELTDX_TDX_7709"
            and source.get("package_version") == ELTDX_VERSION
            and source.get("upstream_inspected_commit") == UPSTREAM_INSPECTED,
            "SOURCE_IDENTITY_REJECTED")
    target = _day(market_session)
    require(source.get("requested_market_session") == target.isoformat()
            and source.get("prepared_date") == target.isoformat(), "SOURCE_SESSION_REJECTED")
    require(isinstance(source.get("chosen_host"), str) and source["chosen_host"], "SOURCE_HOST_REJECTED")
    require(isinstance(source.get("host_probes"), list) and source["host_probes"], "HOST_PROBES_REJECTED")
    require(isinstance(source.get("protocol_attempts"), list)
            and 1 <= len(source["protocol_attempts"]) <= MAX_PROTOCOL_ATTEMPTS
            and source["protocol_attempts"][-1].get("status") == "CONNECTED",
            "PROTOCOL_ATTEMPTS_REJECTED")
    require(isinstance(source.get("source_file_records"), list)
            and {r.get("name") for r in source["source_file_records"]} == SOURCE_FILES,
            "SOURCE_FILE_RECORDS_REJECTED")
    boards = source.get("boards")
    require(isinstance(boards, list) and 0 < len(boards) <= MAX_CONCEPTS, "CATALOG_SCOPE_REJECTED")
    codes: set[str] = set()
    observations = []
    history5 = history10 = 0
    with localcontext(Context(prec=28)):
        for expected_order, row in enumerate(boards):
            require(isinstance(row, dict)
                    and row.get("source_order") == expected_order
                    and isinstance(row.get("board_code"), str)
                    and re.fullmatch(r"[0-9]{6}", row["board_code"]) is not None
                    and isinstance(row.get("board_name"), str) and row["board_name"].strip()
                    and isinstance(row.get("full_code"), str)
                    and re.fullmatch(r"(?:sh|sz)[0-9]{6}", row["full_code"]) is not None,
                    "CATALOG_ROW_REJECTED")
            require(row["board_code"] not in codes, "DUPLICATE_BOARD_CODE")
            codes.add(row["board_code"])
            snapshot = row.get("snapshot")
            bars = row.get("bars")
            require(isinstance(snapshot, dict) and isinstance(bars, list) and len(bars) >= 2,
                    "CURRENT_HISTORY_INCOMPLETE")
            times = []
            for bar in bars:
                require(isinstance(bar, dict) and "time" in bar and "close" in bar, "HISTORY_ROW_REJECTED")
                when = _clock(bar["time"])
                times.append(when)
            require(all(a < b for a, b in zip(times, times[1:]))
                    and times[-1].date() == target, "HISTORY_SESSION_REJECTED")
            last, prior = _dec(bars[-1]["close"]), _dec(bars[-2]["close"])
            require(last > 0 and prior > 0, "HISTORY_PRICE_REJECTED")
            snap_last, snap_prior = _dec(snapshot.get("last_price")), _dec(snapshot.get("pre_close_price"))
            require(snap_last == last and snap_prior == prior, "SNAPSHOT_HISTORY_MISMATCH")
            today = (last / prior - Decimal(1)) * Decimal(100)
            five = ten = None
            if len(bars) >= 6:
                base5 = _dec(bars[-6]["close"])
                require(base5 > 0, "HISTORY_PRICE_REJECTED")
                five = (last / base5 - Decimal(1)) * Decimal(100)
                history5 += 1
            if len(bars) >= 11:
                base10 = _dec(bars[-11]["close"])
                require(base10 > 0, "HISTORY_PRICE_REJECTED")
                ten = (last / base10 - Decimal(1)) * Decimal(100)
                history10 += 1
            observations.append({
                "source_order": expected_order,
                "code": row["board_code"],
                "name": row["board_name"],
                "full_code": row["full_code"],
                "market_session": target.isoformat(),
                "history_points": len(bars),
                "history_first_date": times[0].date().isoformat(),
                "history_last_date": times[-1].date().isoformat(),
                "periods": {
                    "today": {"change_percent": _decimal_text(today)},
                    "5d": {"change_percent": None if five is None else _decimal_text(five)},
                    "10d": {"change_percent": None if ten is None else _decimal_text(ten)},
                },
            })
    payload = {
        "version": VERSION,
        "kind": "MARKET_EXPRESSION",
        "qualification": "CONTEXT_ONLY",
        "status": ("MATCHED_TDX_CONCEPT_CATALOG"
                   if history10 == len(observations)
                   else "MATCHED_TDX_CURRENT_WITH_HISTORY_GAPS"),
        "taxonomy": POLICY["taxonomy"],
        "market_session": target.isoformat(),
        "source_trade_date": target.isoformat(),
        "prepared_date": source["prepared_date"],
        "package_version": source["package_version"],
        "wheel_sha256": source.get("wheel_sha256", "UNKNOWN"),
        "upstream_inspected_commit": source["upstream_inspected_commit"],
        "chosen_host": source["chosen_host"],
        "handshake": source.get("handshake"),
        "host_probes": source["host_probes"],
        "protocol_attempts": source["protocol_attempts"],
        "source_file_records": source["source_file_records"],
        "catalog_count": len(observations),
        "coverage": {
            "snapshot_catalog_complete": True,
            "history_5d_rows": history5,
            "history_10d_rows": history10,
            "history_5d_complete": history5 == len(observations),
            "history_10d_complete": history10 == len(observations),
            "historical_memberships": POLICY["historical_membership"],
            "source_publication_time": POLICY["source_publication_time"],
            "raw_protocol_frames": POLICY["raw_protocol_frames"],
            "eastmoney_required": False,
        },
        "period_basis": POLICY["window_basis"],
        "observations": observations,
        "source_calls_during_replay": 0,
        **AUTHORITY,
    }
    return _plain({"projection": payload, "projection_hash": canonical_hash(payload)})

def render(result: dict[str, Any]) -> str:
    projection = result["projection"]
    require(result.get("projection_hash") == canonical_hash(projection), "OBSERVATION_HASH_REJECTED")
    def text(value: Any) -> str:
        value = "UNKNOWN" if value is None else str(value)
        return (value.replace("\\r", " ").replace("\\n", " ")
                .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("|", "&#124;"))
    lines = [
        "# TDX 概念市场横截面",
        "",
        f"状态：{text(projection['status'])}",
        "",
        "通达信 source-native 概念口径；不映射或冒充东方财富 BK / 同花顺 TI。",
        "1/5/10 日均由已完成交易日收盘序列本地计算；价格变化只属于 Market Expression。",
        "Eastmoney/Vibe 已退为 best-effort secondary；本结果不依赖东财成功。",
        "原始 7709 frame 未由 eltdx board helper 暴露；保留其 source-native 模型、板块资料文件及精确 hash。",
        "",
        f"目标交易日：{text(projection['market_session'])}；板块资料日：{text(projection['prepared_date'])}",
        f"目录：{projection['catalog_count']}；5日覆盖：{projection['coverage']['history_5d_rows']}；10日覆盖：{projection['coverage']['history_10d_rows']}",
        f"实际主站：{text(projection['chosen_host'])}；eltdx：{text(projection['package_version'])}",
        "",
        "| 代码 | 名称 | 当日% | 5日% | 10日% |",
        "|---|---|---:|---:|---:|",
    ]
    for row in projection["observations"]:
        periods = row["periods"]
        lines.append("| " + " | ".join([
            text(row["code"]), text(row["name"]),
            text(periods["today"]["change_percent"]),
            text(periods["5d"]["change_percent"]),
            text(periods["10d"]["change_percent"]),
        ]) + " |")
    lines += [
        "",
        "[完整 source identity / host probes / 文件 hash / 历史覆盖见 observation.json]",
        "",
        "WHY UNKNOWN · BUSINESS LINK NOT ESTABLISHED · INVESTMENT AUTHORITY NONE",
        "",
    ]
    return "\n".join(lines)

def capture(
    output: Path,
    *,
    market_session: date | str,
    workflow: dict[str, str],
    expected_code: str,
    source_fn: Callable[[Path, date], dict[str, Any]] = live_source,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    target = _day(market_session)
    workflow = workflow_identity(workflow, expected_code)
    _safe_root(output)
    require(not output.exists(), "CREATE_ONLY_OUTPUT_REQUIRED")
    output.mkdir(parents=True)
    started = _clock(now())
    plan = {
        "version": VERSION,
        "market_session": target.isoformat(),
        "started_at": started,
        "workflow": workflow,
        "policy": POLICY,
        **AUTHORITY,
    }
    (output / "plan.json").write_bytes(_encoded(plan))
    status = "INCOMPLETE_TDX_SOURCE_CAPTURE"
    reason = None
    failure_type = None
    try:
        source = _jsonable(source_fn(output, target))
        # Bind the retained board-file bytes after live acquisition.
        source["source_file_records"] = _file_records(output)
        observation = build_observation(source, target)
        (output / "source.json").write_bytes(_encoded(source))
        (output / "observation.json").write_bytes(_encoded(observation))
        (output / "summary.md").write_text(render(observation), encoding="utf-8")
        status = "CAPTURED_TDX_CONCEPT_SNAPSHOT"
    except TdxConceptError as exc:
        reason, failure_type = str(exc), type(exc).__name__
    except Exception as exc:
        # Third-party eltdx has its own finite transport/protocol exception
        # classes. Retain only the exception type, never remote text/attributes.
        reason, failure_type = "SOURCE_UNAVAILABLE_OR_REJECTED", type(exc).__name__
    finished = _clock(now())
    require(finished >= started, "FINISH_CLOCK_REJECTED")
    if not (output / "summary.md").exists():
        (output / "summary.md").write_text(
            "# TDX 概念市场横截面\n\n"
            f"状态：{status}\n\n原因码：{reason or 'UNKNOWN'}\n\n"
            "未完成不等于市场无变化；Eastmoney不会被自动调用作为隐式回退。\n",
            encoding="utf-8",
        )
    receipt = {
        "version": VERSION,
        "workflow": workflow,
        "market_session": target.isoformat(),
        "started_at": started,
        "finished_at": finished,
        "status": status,
        "reason_code": reason,
        "failure_type": failure_type,
        "implementation": _implementation(),
        "files": _inventory(output),
        **AUTHORITY,
    }
    receipt["capture_hash"] = canonical_hash(receipt)
    (output / "capture.json").write_bytes(_encoded(receipt))
    return _plain(receipt)

def replay(output: Path, *, expected_execution: dict[str, str] | None = None) -> dict[str, Any]:
    _safe_root(output)
    receipt = json.loads((output / "capture.json").read_text(encoding="utf-8"))
    require(receipt.get("version") == VERSION
            and receipt.get("capture_hash") == canonical_hash({k: v for k, v in receipt.items() if k != "capture_hash"})
            and receipt.get("implementation") == _implementation()
            and all(receipt.get(k) == v for k, v in AUTHORITY.items()),
            "CAPTURE_IDENTITY_REJECTED")
    plan = json.loads((output / "plan.json").read_text(encoding="utf-8"))
    workflow = workflow_identity(receipt["workflow"], receipt["workflow"]["GITHUB_SHA"])
    require(plan == _plain({
        "version": VERSION,
        "market_session": receipt["market_session"],
        "started_at": receipt["started_at"],
        "workflow": workflow,
        "policy": POLICY,
        **AUTHORITY,
    }), "PLAN_IDENTITY_REJECTED")
    if expected_execution is not None:
        require(workflow == expected_execution, "EXECUTION_IDENTITY_REJECTED")
    current_files = _inventory(output)
    require(receipt.get("files") == current_files, "CAPTURE_FILES_REJECTED")
    if receipt["status"] != "CAPTURED_TDX_CONCEPT_SNAPSHOT":
        require(receipt["status"] == "INCOMPLETE_TDX_SOURCE_CAPTURE"
                and receipt.get("reason_code"), "FAILED_CAPTURE_REJECTED")
        return _plain({
            "status": "RETAINED_FAILED_TDX_CAPTURE_REMOTE_CAUSE_NOT_REPROVEN",
            "capture_hash": receipt["capture_hash"],
            "source_calls_during_replay": 0,
        })
    source = json.loads((output / "source.json").read_text(encoding="utf-8"))
    require(source.get("source_file_records") == _file_records(output), "SOURCE_FILE_IDENTITY_REJECTED")
    rebuilt = build_observation(source, _day(receipt["market_session"]))
    require((output / "observation.json").read_bytes() == _encoded(rebuilt)
            and (output / "summary.md").read_text(encoding="utf-8") == render(rebuilt),
            "DERIVED_OBSERVATION_DIFFERS")
    return rebuilt

def _execution_from_env() -> dict[str, str]:
    keys = (
        "GITHUB_REPOSITORY", "GITHUB_WORKFLOW", "GITHUB_REF", "GITHUB_EVENT_NAME",
        "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA",
    )
    return {key: os.environ.get(key, "") for key in keys}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("capture", "replay"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--market-session")
    args = parser.parse_args(argv)
    if args.operation == "capture":
        require(args.market_session is not None, "MARKET_SESSION_REQUIRED")
        result = capture(
            args.output,
            market_session=args.market_session,
            workflow=_execution_from_env(),
            expected_code=os.environ.get("EXPECTED_CODE", ""),
        )
        print("TDX_CONCEPT_CAPTURE_STATUS=" + result["status"])
        print("TDX_CONCEPT_CAPTURE_HASH=" + result["capture_hash"])
    else:
        require(args.market_session is None, "REPLAY_MARKET_SESSION_FORBIDDEN")
        result = replay(args.output)
        projection = result.get("projection")
        print("TDX_CONCEPT_REPLAY_STATUS=" + (projection["status"] if projection else result["status"]))
        print("TDX_CONCEPT_REPLAY_HASH=" + (result.get("projection_hash") or result["capture_hash"]))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
