from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from ..adapters.hithink import (
    HITHINK_MARKET_SOURCE,
    HITHINK_PRICE_CONVENTION,
    to_hithink_thscode,
)
from ..deep_research import DeepResearchPackage
from ..research_commit import ResearchCommitPackage
from . import hithink_http


SHADOW_STORAGE_CLASSIFICATION = "ACTIONS_SHORT_LIVED_HARNESS_OBSERVATION"
SHADOW_PURPOSE = (
    "Surprise Radar shadow price-path input only; no Research route, Human wake, "
    "fundamental-state migration, or investment authority."
)


def _research_snapshot_from_raw_package(raw_package: str):
    payload = json.loads(raw_package)
    if not isinstance(payload, dict):
        raise ValueError("market-history shadow package must be a JSON object")
    if "deep_research" in payload and "discovery" in payload:
        return DeepResearchPackage.model_validate(payload).research_snapshot
    return ResearchCommitPackage.model_validate(payload).research_snapshot


def _serialize_shadow_observation(
    *,
    package_path: Path,
    snapshot,
    history,
    captured_at: datetime,
) -> str:
    payload = {
        "schema_version": 1,
        "storage_classification": SHADOW_STORAGE_CLASSIFICATION,
        "purpose": SHADOW_PURPOSE,
        "captured_at": captured_at.isoformat(),
        "package_path": package_path.as_posix(),
        "research_identity": {
            "research_snapshot_id": str(snapshot.id),
            "research_as_of": snapshot.as_of_datetime.isoformat(),
            "research_information_bundle_hash": snapshot.information_bundle_hash,
        },
        "security": {
            "ticker": snapshot.ticker,
            "company_name": snapshot.company_name,
            "exchange": snapshot.exchange,
            "thscode": history.thscode,
        },
        "market_contract": {
            "source": HITHINK_MARKET_SOURCE,
            "price_convention": HITHINK_PRICE_CONVENTION,
            "response_session": history.response_session.isoformat(),
            "expected_latest_session": history.expected_latest_session.isoformat(),
        },
        "points": [
            {
                "as_of": point.as_of.isoformat(),
                "close": str(point.close),
            }
            for point in history.points
        ],
        "radar_semantics": "SHADOW_OBSERVATION_ONLY",
        "human_attention_authority": "NONE",
        "investment_authority": "NONE",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def capture_market_history_shadow(
    package_paths: Sequence[Path],
    *,
    output_dir: Path,
    captured_at: datetime,
    api_key: str | None,
) -> tuple[Path, ...]:
    """Capture qualified HiThink windows as short-lived Harness observations.

    Fetch and validation complete for the whole batch before any output is written.
    A shadow-capture failure therefore cannot leave a partial artifact set that looks
    complete. The caller decides whether a capture failure is fatal to its outer job.
    """

    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("market-history shadow captured_at must be timezone-aware")
    if not package_paths:
        raise ValueError("market-history shadow requires at least one Research package")

    seen_thscodes: set[str] = set()
    pending: list[tuple[Path, str]] = []

    for package_path in package_paths:
        raw_package = package_path.read_text(encoding="utf-8")
        snapshot = _research_snapshot_from_raw_package(raw_package)
        thscode = to_hithink_thscode(
            ticker=snapshot.ticker,
            exchange=snapshot.exchange,
        )
        if thscode in seen_thscodes:
            raise ValueError(
                f"market-history shadow received more than one current Research package for {thscode}"
            )
        seen_thscodes.add(thscode)

        history = hithink_http.fetch_hithink_completed_price_history(
            thscode=thscode,
            observed_at=captured_at,
            api_key=api_key,
        )
        artifact_path = output_dir / (
            f"{snapshot.ticker}-{history.response_session.isoformat()}.json"
        )
        pending.append(
            (
                artifact_path,
                _serialize_shadow_observation(
                    package_path=package_path,
                    snapshot=snapshot,
                    history=history,
                    captured_at=captured_at,
                ),
            )
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for artifact_path, serialized in pending:
        temporary = artifact_path.with_name(f".{artifact_path.name}.tmp")
        try:
            temporary.write_text(serialized, encoding="utf-8")
            temporary.replace(artifact_path)
        finally:
            if temporary.exists():
                temporary.unlink()
        written.append(artifact_path)

    return tuple(written)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m decision_kernel.runtime.market_history_shadow",
        description=(
            "Capture short-lived qualified HiThink price-history windows for Surprise Radar shadow evaluation."
        ),
    )
    parser.add_argument(
        "packages",
        nargs="+",
        type=Path,
        help="Current A-share ResearchCommitPackage or DeepResearchPackage JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("market-history-shadow"),
        help="Short-lived Harness artifact directory.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        captured_at = datetime.now(timezone.utc)
        outputs = capture_market_history_shadow(
            args.packages,
            output_dir=args.output_dir,
            captured_at=captured_at,
            api_key=os.environ.get(hithink_http.HITHINK_API_KEY_ENV),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=stderr)
        return 2

    print(
        f"MARKET HISTORY SHADOW: {len(outputs)} qualified windows | dir={args.output_dir}",
        file=stdout,
    )
    for output in outputs:
        print(f"SHADOW: {output}", file=stdout)
    print("RADAR SEMANTICS: SHADOW_OBSERVATION_ONLY", file=stdout)
    print("HUMAN ATTENTION AUTHORITY: NONE", file=stdout)
    print("INVESTMENT AUTHORITY: NONE", file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
