from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from urllib.error import URLError

from decision_kernel.runtime.hithink_http import HithinkRuntimeError


SCRIPT = Path(
    "experiments/sector_radar_full_current_hierarchy_runner_2026_09_04.py"
)


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "sector_radar_full_current_hierarchy_runner",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_direct_network_and_timeout_errors_are_transient() -> None:
    module = load_module()

    assert module.is_transient_transport_error(ConnectionError("closed")) is True
    assert module.is_transient_transport_error(TimeoutError("timeout")) is True


def test_wrapped_url_timeout_is_transient() -> None:
    module = load_module()

    try:
        try:
            raise URLError(TimeoutError("TLS handshake timed out"))
        except URLError as cause:
            raise HithinkRuntimeError("wrapped request failure") from cause
    except HithinkRuntimeError as error:
        assert module.is_transient_transport_error(error) is True


def test_business_or_semantic_errors_are_not_retried() -> None:
    module = load_module()

    assert module.is_transient_transport_error(ValueError("bad data")) is False
    assert (
        module.is_transient_transport_error(
            HithinkRuntimeError("HiThink HTTP request failed with status 429")
        )
        is False
    )
