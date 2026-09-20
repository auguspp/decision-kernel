"""One local-image sample; reuses the existing eval parser, never Research."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: newsnow_selfhost_once.py NEW_OUTPUT_DIRECTORY")
    output = Path(sys.argv[1])
    spec = importlib.util.spec_from_file_location(
        "news_probe", Path(__file__).with_name("news_radar_reuse_probe.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The public RSSHub failures are already retained; do not request them again.
    module.RSS = {}
    sys.argv = ["news_probe", "--output", str(output),
                "--newsnow-base-url", "http://127.0.0.1:4444/api/s"]
    with contextlib.redirect_stdout(io.StringIO()):
        module.main()
    summary = json.loads((output / "summary.json").read_bytes())
    summary["source_implementation_inspected"] = summary.pop("newsnow_upstream")
    summary["deployed_source_commit"] = "UNKNOWN_SEE_SEPARATE_IMAGE_IDENTITY"
    summary["observations_with_parseable_publish_clock"] = summary.pop(
        "observations_with_qualified_publish_clock")
    summary["published_time_semantics"] = "PARSED_SOURCE_CLAIM_NOT_PIT_QUALIFICATION"
    summary["upstream_internal_requests_and_retries"] = "UNKNOWN"
    summary["normal_radar_reading_published"] = False
    summary["useful_question_count"] = None
    summary["question_count_status"] = "NOT_REVIEWED_NOT_ZERO"
    module.write(output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
