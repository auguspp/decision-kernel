from pathlib import Path


WORKFLOW = Path(".github/workflows/economic-release-discovery.yml")


def test_discovery_workflow_is_manual_or_exact_main_code_change_only():
    raw = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in raw and "branches: [main]" in raw
    assert "schedule:" not in raw and "pull_request:" not in raw and "workflow_run:" not in raw
    paths = raw.split("    paths:\n", 1)[1].split("\n\n", 1)[0]
    assert [line.strip()[2:] for line in paths.splitlines()] == [
        ".github/workflows/economic-release-discovery.yml",
        "src/decision_kernel/runtime/economic_release_discovery.py",
        "src/decision_kernel/runtime/economic_release_inputs.py",
        "radar_inputs/economic-node-study-2026-09-05.json",
        "radar_inputs/economic-reviewed-releases/**",
    ]
    assert '"$GITHUB_REF" != "refs/heads/main"' in raw
    assert "timeout-minutes: 5" in raw and "cancel-in-progress: false" in raw


def test_discovery_workflow_has_no_secrets_market_cache_or_production_routes():
    raw = WORKFLOW.read_text(encoding="utf-8")
    assert "contents: read" in raw and "persist-credentials: false" in raw
    for forbidden in ("secrets.", "HITHINK", "actions/cache", "decision-state", "sector_radar_producer", "decision-inbox", "contents: write", "pip install pyarrow"):
        assert forbidden not in raw
    assert "continue-on-error" not in raw and "|| true" not in raw
    assert raw.count("economic_release_inputs scan") == 1
    assert "radar_inputs/economic-node-study-2026-09-05.json" in raw


def test_discovery_failure_is_retained_without_masking_or_repeating_acquisition():
    raw = WORKFLOW.read_text(encoding="utf-8")
    names = ["Record run identity", "Scan two visible directory windows once", "Reconstruct discovery offline", "Retain complete attempt evidence", "Publish bounded discovery summary"]
    positions = [raw.index(name) for name in names]
    assert positions == sorted(positions)
    verify = raw.split("      - name: Reconstruct discovery offline\n", 1)[1].split("      - name: ", 1)[0]
    assert "if: always()" in verify and "exit 1" in verify
    assert "economic_release_inputs verify" in verify
    assert "retention-days: 90" in raw and "if-no-files-found: error" in raw
    assert "github.run_id" in raw and "github.run_attempt" in raw
    assert "steps.evidence.outputs.artifact-url" in raw
    assert "未发现候选不等于发布者没有更新" in raw


def test_workflow_identity_remains_outside_sealed_scan_inventory():
    raw = WORKFLOW.read_text(encoding="utf-8")
    assert 'Path("release-discovery-proof")' in raw
    assert 'root / "workflow.json"' in raw
    assert 'record["provenance_hash"] = canonical_hash(record)' in raw
    for name in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_EVENT_NAME"):
        assert '"' + name + '"' in raw
    assert "--output release-discovery-proof/input-run" in raw
    assert "> release-discovery-proof/verification.json" in raw
    assert "BOUNDED_DIRECTORY_COMPATIBILITY_PROOF_NOT_CONTINUOUS_MONITORING" in raw


def test_scanner_and_replayer_use_identical_review_inputs_and_preserve_both_summaries():
    raw = WORKFLOW.read_text(encoding="utf-8")
    assert raw.count("--seed radar_inputs/economic-node-study-2026-09-05.json") == 2
    assert raw.count("--reviews-dir radar_inputs/economic-reviewed-releases") == 2
    assert "input-run/input-set.json" in raw
    assert "cat release-discovery-proof/input-run/summary.md" in raw
    assert "cat release-discovery-proof/input-run/scan/summary.md" in raw
    assert "economic_release_review apply" not in raw
    assert "ACCEPT_REVIEWED_EXCERPT" not in raw


def test_default_review_input_directory_exists_without_fabricated_acceptances():
    root = Path("radar_inputs/economic-reviewed-releases")
    assert root.is_dir()
    assert (root / ".gitkeep").read_bytes() == b""
    # Future explicit source-bundle registrations may add directories, never drafts/loose JSON.
    assert all(p.name == ".gitkeep" or p.is_dir() for p in root.iterdir())
