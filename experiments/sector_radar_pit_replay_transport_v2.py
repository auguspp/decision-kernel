from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

SCRIPT_PATH = Path("experiments/sector_radar_pit_replay_2026_09_04.py")
CHECKPOINT_DIR = Path("sector-radar-pit-replay-inputs")
MAX_TRANSPORT_ATTEMPTS = 3
RETRY_BASE_SECONDS = 1.0


def _load_experiment() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sector_radar_pit_replay_v1", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment script: {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _jsonable(module: ModuleType, value: Any) -> Any:
    return module.jsonable(value)


def _write_checkpoint(
    module: ModuleType,
    *,
    thscode: str,
    history: Any,
    request_meta: dict[str, Any],
) -> tuple[Path, str]:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    path = CHECKPOINT_DIR / f"{thscode.replace('.', '_')}.json"
    payload = {
        "schema_version": 1,
        "thscode": thscode,
        "request": request_meta,
        "response_session": history.response_session,
        "expected_latest_session": history.expected_latest_session,
        "points": history.points,
        "checkpoint_semantics": "QUALIFIED_HISTORY_INPUT_ONLY",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
    }
    serialized = (
        json.dumps(
            _jsonable(module, payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
    sha256 = module.hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return path, sha256


def _install_transport_boundary(module: ModuleType) -> dict[str, int]:
    original_request = module.request
    original_normalize = module.normalize_hithink_completed_index_history
    history_meta: dict[str, dict[str, Any]] = {}
    counters = {"retry_count": 0, "connection_failure_count": 0}

    def request(api_key: str, path: str, params: Mapping[str, str]):
        attempts: list[dict[str, Any]] = []
        for attempt_number in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
            started = datetime.now(timezone.utc)
            try:
                envelope, meta = original_request(api_key, path, params)
            except ConnectionError as exc:
                completed = datetime.now(timezone.utc)
                counters["connection_failure_count"] += 1
                attempt = {
                    "attempt_number": attempt_number,
                    "request_started_at": started,
                    "response_completed_at": completed,
                    "duration_seconds": (completed - started).total_seconds(),
                    "status": "TRANSIENT_CONNECTION_FAILURE",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                attempts.append(attempt)
                module.progress(
                    {
                        "stage": "transport_retry",
                        "path": path,
                        "params": dict(sorted(params.items())),
                        **attempt,
                    }
                )
                if attempt_number == MAX_TRANSPORT_ATTEMPTS:
                    raise
                counters["retry_count"] += 1
                time.sleep(RETRY_BASE_SECONDS * (2 ** (attempt_number - 1)))
                continue

            attempts.append(
                {
                    "attempt_number": attempt_number,
                    "request_started_at": started,
                    "response_completed_at": meta["response_completed_at"],
                    "duration_seconds": meta["duration_seconds"],
                    "status": "SUCCESS",
                }
            )
            meta["transport_attempt_count"] = attempt_number
            meta["transport_retry_count"] = attempt_number - 1
            meta["transport_attempts"] = attempts
            meta["retry_scope"] = "TRANSIENT_CONNECTION_FAILURE_ONLY"
            if path == module.HITHINK_INDEX_HISTORY_PATH:
                thscode = str(params["thscode"]).strip().upper()
                meta["checkpoint_path"] = str(
                    CHECKPOINT_DIR / f"{thscode.replace('.', '_')}.json"
                )
                history_meta[thscode] = meta
            return envelope, meta

        raise RuntimeError("unreachable transport loop")

    def normalize(envelope, *, thscode, sessions, observed_at):
        history = original_normalize(
            envelope,
            thscode=thscode,
            sessions=sessions,
            observed_at=observed_at,
        )
        normalized_code = str(thscode).strip().upper()
        meta = history_meta.get(normalized_code)
        if meta is None:
            raise RuntimeError(f"qualified history lacks request metadata: {normalized_code}")
        checkpoint_path, checkpoint_sha256 = _write_checkpoint(
            module,
            thscode=normalized_code,
            history=history,
            request_meta=meta,
        )
        meta["checkpoint_path"] = str(checkpoint_path)
        meta["checkpoint_sha256"] = checkpoint_sha256
        return history

    module.request = request
    module.normalize_hithink_completed_index_history = normalize
    return counters


def _rewrite_success_outputs(module: ModuleType, counters: Mapping[str, int]) -> None:
    payload = json.loads(module.RESULT.read_text(encoding="utf-8"))
    acquisition = payload["acquisition"]
    acquisition["transport_max_attempts"] = MAX_TRANSPORT_ATTEMPTS
    acquisition["transport_retry_base_seconds"] = str(Decimal(str(RETRY_BASE_SECONDS)))
    acquisition["transport_retry_count"] = counters["retry_count"]
    acquisition["connection_failure_count"] = counters["connection_failure_count"]
    acquisition["retry_scope"] = "TRANSIENT_CONNECTION_FAILURE_ONLY"
    acquisition["qualified_history_checkpoint_count"] = len(
        tuple(CHECKPOINT_DIR.glob("*.json"))
    )
    acquisition.pop("retry_count", None)
    module.RESULT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = module.summary_markdown(payload)
    marker = "- History calls:"
    replacement = (
        f"- Transport retries: `{counters['retry_count']}` across "
        f"`{counters['connection_failure_count']}` transient connection failures; "
        f"max `{MAX_TRANSPORT_ATTEMPTS}` attempts per request; no HTTP/business/semantic retry.\n"
        f"- Qualified history checkpoints: "
        f"`{acquisition['qualified_history_checkpoint_count']}`\n"
        f"{marker}"
    )
    summary = summary.replace(marker, replacement, 1)
    module.SUMMARY.write_text(summary, encoding="utf-8")


def _write_error(module: ModuleType, exc: Exception, counters: Mapping[str, int]) -> None:
    module.ERROR.write_text(
        json.dumps(
            {
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "progress_path": str(module.PROGRESS),
                "checkpoint_dir": str(CHECKPOINT_DIR),
                "qualified_history_checkpoint_count": (
                    len(tuple(CHECKPOINT_DIR.glob("*.json")))
                    if CHECKPOINT_DIR.is_dir()
                    else 0
                ),
                "transport_retry_count": counters["retry_count"],
                "connection_failure_count": counters["connection_failure_count"],
                "transport_retry_scope": "TRANSIENT_CONNECTION_FAILURE_ONLY",
                "transport_max_attempts": MAX_TRANSPORT_ATTEMPTS,
                "human_attention_authority": "NONE",
                "investment_authority": "NONE",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    module = _load_experiment()
    counters = _install_transport_boundary(module)
    try:
        module.main()
        _rewrite_success_outputs(module, counters)
    except Exception as exc:
        _write_error(module, exc, counters)
        raise


if __name__ == "__main__":
    main()
