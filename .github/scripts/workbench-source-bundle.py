"""One exact, CI-qualified source export; native Git/signature tools do the rest."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

REPO = "auguspp/decision-kernel"
WORKFLOW = ".github/workflows/workbench-source-bundle.yml"
PATHS = ("workbench", "docs/github-native-operations.md")
PREFIX = "decision-kernel-workbench/"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def qualify(env: dict, expected: str, main_ref: dict, runs: dict) -> dict:
    """Check the actual latest queried CI attempt, never search backwards for green."""
    require(re.fullmatch(r"[0-9a-f]{40}", expected) is not None, "invalid code SHA")
    require(env.get("GITHUB_REPOSITORY") == REPO, "wrong repository")
    require(env.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "manual entry only")
    require(env.get("GITHUB_REF") == "refs/heads/main", "main only")
    require(env.get("GITHUB_RUN_ATTEMPT") == "1", "fresh invocation only")
    require(env.get("GITHUB_SHA") == expected, "executing SHA differs")
    require(env.get("GITHUB_WORKFLOW_REF") == f"{REPO}/{WORKFLOW}@refs/heads/main", "wrong workflow")
    require(re.fullmatch(r"[1-9][0-9]*", env.get("GITHUB_RUN_ID", "")) is not None, "missing run identity")
    require(main_ref.get("ref") == "refs/heads/main", "wrong main ref")
    require(main_ref.get("object", {}).get("sha") == expected, "main advanced; do not export stale intent")
    items = runs.get("workflow_runs")
    require(isinstance(items, list) and 0 < len(items) <= 20, "CI query empty or invalid")
    require(all(type(item.get("id")) is int for item in items), "invalid CI identity")
    latest = max(items, key=lambda item: item["id"])
    require(latest.get("path") == ".github/workflows/ci.yml", "wrong CI workflow")
    require(latest.get("repository", {}).get("full_name") == REPO, "wrong CI repository")
    require(latest.get("head_sha") == expected and latest.get("head_branch") == "main", "wrong CI code")
    require(latest.get("event") == "push" and latest.get("run_attempt") == 1, "wrong CI origin")
    require(latest.get("status") == "completed" and latest.get("conclusion") == "success", "latest CI not successful")
    return {"run_id": latest["id"], "run_attempt": 1, "code_commit": expected}


def build(root: Path, output: Path, env: dict, expected: str, main_ref: dict, runs: dict) -> dict:
    ci = qualify(env, expected, main_ref, runs)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    require(head == expected, "checkout differs")
    for path in PATHS:
        subprocess.run(["git", "cat-file", "-e", f"{expected}:{path}"], cwd=root, check=True, capture_output=True)
    output.mkdir(parents=True, exist_ok=False)
    target = output / "workbench-source.tar"
    # Export the Git object, not the mutable checkout. Never import/run archived code.
    subprocess.run(["git", "archive", "--format=tar", f"--prefix={PREFIX}",
                    f"--output={target.resolve()}", expected, *PATHS], cwd=root, check=True)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    manifest = {"purpose": "WORKBENCH_SOURCE_NOT_SITE_DEPLOYMENT", "repository": REPO,
                "code_commit": expected, "workflow": WORKFLOW, "run_id": int(env["GITHUB_RUN_ID"]),
                "run_attempt": 1, "independent_main_ci": ci,
                "archive": {"name": target.name, "bytes": target.stat().st_size, "sha256": digest},
                "paths": list(PATHS), "site_adoption": "NOT_ESTABLISHED",
                "investment_authority": "NONE"}
    (output / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-ref", type=Path, required=True)
    parser.add_argument("--ci-runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        build(Path.cwd(), args.output, dict(os.environ), os.environ.get("EXPECTED_CODE", ""),
              json.loads(args.main_ref.read_text()), json.loads(args.ci_runs.read_text()))
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        # Don't print source text, credentials, or subprocess output.
        parser.exit(2, f"Source bundle rejected: {type(error).__name__}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
