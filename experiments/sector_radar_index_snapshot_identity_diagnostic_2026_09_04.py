from __future__ import annotations

import json
import os
from pathlib import Path

from decision_kernel.runtime.hithink_http import (
    HITHINK_API_KEY_ENV,
    _request_hithink_json,
)
from decision_kernel.runtime.hithink_index_http import HITHINK_INDEX_SNAPSHOT_PATH


OUTPUT = Path("sector-radar-index-snapshot-identity-diagnostic.json")
REQUESTED = (
    "000001.SH",
    "000300.SH",
    "399001.SZ",
    "399006.SZ",
    "881101.TI",
)


def main() -> None:
    api_key = os.environ.get(HITHINK_API_KEY_ENV)
    if not api_key:
        raise ValueError(f"{HITHINK_API_KEY_ENV} is required")
    envelope = _request_hithink_json(
        api_key=api_key,
        path=HITHINK_INDEX_SNAPSHOT_PATH,
        params={"thscodes": ",".join(REQUESTED)},
        timeout_seconds=30.0,
    )
    data = envelope.get("data")
    if not isinstance(data, dict):
        raise ValueError("index snapshot diagnostic returned no data object")
    items = data.get("item")
    if not isinstance(items, list):
        raise ValueError("index snapshot diagnostic returned no item list")
    rows = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("index snapshot diagnostic returned malformed item")
        rows.append(
            {
                "thscode": item.get("thscode"),
                "ticker": item.get("ticker"),
                "ticker_python_type": type(item.get("ticker")).__name__,
            }
        )
    OUTPUT.write_text(
        json.dumps(
            {
                "requested": REQUESTED,
                "business_code": envelope.get("code"),
                "request_id": envelope.get("request_id"),
                "provider_timestamp_ms": data.get("timestamp"),
                "rows": rows,
                "diagnostic_semantics": "SAFE_IDENTITY_FIELDS_ONLY",
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
    print(OUTPUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
