from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence


SCRIPT = Path("experiments/sector_radar_current_breadth_2026_09_04.py")
ALIAS_OUTPUT = Path("sector-radar-index-snapshot-provider-aliases.json")
_ALIAS = re.compile(r"^[0-9A-Z]{6}$")


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "sector_radar_current_breadth_experiment_v1",
        SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load experiment script: {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def install_standard_index_alias_compatibility(
    module: ModuleType,
) -> dict[str, str]:
    original = module.normalize_hithink_index_snapshot
    aliases: dict[str, str] = {}

    def normalize(
        envelope: Mapping[str, Any],
        *,
        requested_thscodes: Sequence[str],
    ):
        payload = copy.deepcopy(envelope)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("index snapshot alias seam received no data object")
        items = data.get("item")
        if not isinstance(items, list):
            raise ValueError("index snapshot alias seam received no item list")

        for raw in items:
            if not isinstance(raw, dict):
                raise ValueError("index snapshot alias seam received malformed row")
            thscode = str(raw.get("thscode", "")).strip().upper()
            ticker = str(raw.get("ticker", "")).strip().upper()
            if thscode.endswith((".SH", ".SZ")) and ticker != thscode[:6]:
                if not _ALIAS.fullmatch(ticker):
                    raise ValueError(
                        f"standard-index provider ticker alias is malformed for {thscode}"
                    )
                aliases[thscode] = ticker
                # The existing adapter's exact requested/returned thscode contract remains
                # authoritative. This experiment-only seam canonicalizes only the redundant
                # ticker metadata so the rest of the qualified snapshot contract can run.
                raw["ticker"] = thscode[:6]

        return original(payload, requested_thscodes=requested_thscodes)

    module.normalize_hithink_index_snapshot = normalize
    return aliases


def write_alias_evidence(aliases: Mapping[str, str]) -> None:
    ALIAS_OUTPUT.write_text(
        json.dumps(
            {
                "provider_ticker_aliases": dict(sorted(aliases.items())),
                "identity_authority": "EXACT_REQUESTED_AND_RETURNED_THSCODE",
                "ticker_semantics": "PROVIDER_METADATA_NOT_CANONICAL_INDEX_IDENTITY",
                "compatibility_scope": "EXPERIMENT_ONLY",
                "production_adapter_change": "NOT_INCLUDED_IN_THIS_EXPERIMENT",
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


def rewrite_success_outputs(
    module: ModuleType,
    aliases: Mapping[str, str],
) -> None:
    payload = json.loads(module.RESULT.read_text(encoding="utf-8"))
    payload.pop("result_hash", None)
    payload["index_snapshot_provider_ticker_aliases"] = dict(sorted(aliases.items()))
    payload["index_snapshot_identity_semantics"] = (
        "EXACT_THSCODE_AUTHORITATIVE_PROVIDER_TICKER_METADATA_ONLY"
    )
    payload["index_snapshot_alias_compatibility_scope"] = "EXPERIMENT_ONLY"
    payload["result_hash"] = module.digest(payload)
    module.RESULT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = module.summary_markdown(payload)
    summary += "\n## Provider ticker aliases\n\n"
    if aliases:
        for thscode, ticker in sorted(aliases.items()):
            summary += f"- `{thscode}` returned provider ticker metadata `{ticker}`.\n"
    else:
        summary += "- No non-canonical standard-index aliases were observed.\n"
    summary += (
        "\nExact `thscode` remained the request/response identity. The compatibility "
        "seam was experiment-only and does not modify the production adapter.\n"
    )
    module.SUMMARY.write_text(summary, encoding="utf-8")


def main() -> None:
    module = load_module()
    aliases = install_standard_index_alias_compatibility(module)
    try:
        module.main()
        rewrite_success_outputs(module, aliases)
    finally:
        write_alias_evidence(aliases)


if __name__ == "__main__":
    main()
