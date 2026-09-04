from __future__ import annotations

import importlib.util
import sys
import time
from datetime import datetime, timezone
from http.client import RemoteDisconnected
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping
from urllib.error import URLError


SCRIPT = Path("experiments/sector_radar_full_current_hierarchy_2026_09_04.py")
MAX_TRANSPORT_ATTEMPTS = 3
RETRY_BASE_SECONDS = 1.0


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "sector_radar_full_current_hierarchy_experiment_v1",
        SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment script: {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def is_transient_transport_error(exc: BaseException) -> bool:
    """Recognize only network/timeout failures, including wrapped URL errors."""

    pending: list[BaseException] = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(
            current,
            (ConnectionError, TimeoutError, RemoteDisconnected),
        ):
            return True
        if isinstance(current, URLError) and isinstance(
            current.reason,
            BaseException,
        ):
            pending.append(current.reason)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)
    return False


def install_transport_boundary(module: ModuleType) -> dict[str, int]:
    counters = {
        "transport_retry_count": 0,
        "transient_transport_failure_count": 0,
    }

    def request(
        api_key: str,
        path: str,
        params: Mapping[str, str],
    ) -> tuple[Mapping[str, Any], dict[str, Any]]:
        attempts: list[dict[str, Any]] = []
        for attempt_number in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
            started = datetime.now(timezone.utc)
            try:
                envelope = module._request_hithink_json(
                    api_key=api_key,
                    path=path,
                    params=params,
                    timeout_seconds=30.0,
                )
            except Exception as exc:
                if not is_transient_transport_error(exc):
                    raise
                completed = datetime.now(timezone.utc)
                counters["transient_transport_failure_count"] += 1
                attempt = {
                    "attempt_number": attempt_number,
                    "status": "TRANSIENT_TRANSPORT_FAILURE",
                    "request_started_at": started,
                    "response_completed_at": completed,
                    "duration_seconds": (completed - started).total_seconds(),
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
                counters["transport_retry_count"] += 1
                time.sleep(RETRY_BASE_SECONDS * (2 ** (attempt_number - 1)))
                continue

            completed = datetime.now(timezone.utc)
            attempts.append(
                {
                    "attempt_number": attempt_number,
                    "status": "SUCCESS",
                    "request_started_at": started,
                    "response_completed_at": completed,
                    "duration_seconds": (completed - started).total_seconds(),
                }
            )
            return envelope, {
                "path": path,
                "params": dict(sorted(params.items())),
                "source_locator": module.locator(path, params),
                "request_started_at": started,
                "response_completed_at": completed,
                "duration_seconds": (completed - started).total_seconds(),
                "request_id": envelope.get("request_id"),
                "business_code": envelope.get("code"),
                "envelope_sha256": module.digest(envelope),
                "transport_attempt_count": attempt_number,
                "transport_retry_count": attempt_number - 1,
                "transport_attempts": attempts,
                "retry_scope": "TRANSIENT_NETWORK_OR_TIMEOUT_FAILURE_ONLY",
            }
        raise RuntimeError("unreachable transport loop")

    module.request = request
    return counters


def rewrite_success_outputs(
    module: ModuleType,
    counters: Mapping[str, int],
) -> None:
    payload = module.json.loads(module.RESULT.read_text(encoding="utf-8"))
    payload.pop("result_hash", None)
    acquisition = payload["acquisition"]
    acquisition["runner_transport_max_attempts"] = MAX_TRANSPORT_ATTEMPTS
    acquisition["runner_retry_base_seconds"] = str(RETRY_BASE_SECONDS)
    acquisition["runner_transport_retry_count"] = counters[
        "transport_retry_count"
    ]
    acquisition["runner_transient_transport_failure_count"] = counters[
        "transient_transport_failure_count"
    ]
    acquisition["runner_retry_scope"] = (
        "TRANSIENT_NETWORK_OR_TIMEOUT_FAILURE_ONLY"
    )
    payload["result_hash"] = module.digest(payload)
    module.RESULT.write_text(
        module.json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    summary = module.summary_markdown(payload)
    summary += (
        "\n## Transport boundary\n\n"
        f"- Retries: `{counters['transport_retry_count']}` across "
        f"`{counters['transient_transport_failure_count']}` transient failures.\n"
        f"- Maximum attempts per request: `{MAX_TRANSPORT_ATTEMPTS}`.\n"
        "- Retry scope: network / timeout failures only; no HTTP, business-code, "
        "adapter, data-shape or semantic retry.\n"
    )
    module.SUMMARY.write_text(summary, encoding="utf-8")


def main() -> None:
    module = load_module()
    counters = install_transport_boundary(module)
    module.main()
    rewrite_success_outputs(module, counters)


if __name__ == "__main__":
    main()
