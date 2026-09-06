from pathlib import Path


WORKFLOW = Path(".github/workflows/economic-release-discovery.yml")
SCRIPT = Path('.github/scripts/prepare-native-rss-successor.py')


def test_discovery_workflow_is_manual_or_explicit_successor_request_only():
    raw = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in raw and "branches: [main]" in raw
    assert "schedule:" not in raw and "pull_request:" not in raw and "workflow_run:" not in raw
    paths = raw.split("    paths:\n", 1)[1].split("\n\n", 1)[0]
    assert [line.strip()[2:] for line in paths.splitlines()] == [
        "radar_inputs/native-rss-successor-request.json",
    ]
    assert "if: github.event_name == 'workflow_dispatch' && inputs.source-kind == 'economic-directories'" in raw
    assert '\"$GITHUB_REF\" != \"refs/heads/main\"' in raw
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
        assert '\"' + name + '\"' in raw
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
    assert all(p.name == ".gitkeep" or p.is_dir() for p in root.iterdir())


def test_native_feed_parser_and_previous_artifact_are_mature_components_not_silent_reset():
    raw = WORKFLOW.read_text(); script = SCRIPT.read_text()
    rss = raw.split('  native-rss:\n',1)[1]
    assert "pip install -e '.[feeds]'" in rss
    assert 'uses: actions/download-artifact@v8' in rss and 'digest-mismatch: error' in rss
    assert 'run-id: ${{ steps.lifecycle.outputs.previous_run_id }}' in rss
    assert 'artifact-ids: ${{ steps.predecessor.outputs.artifact_id }}' in rss
    assert "run['status'] != 'completed' or run['conclusion'] != 'success'" in script
    assert rss.count('gh api --method GET') == 2
    assert 'EXPECTED_PREVIOUS_RUN_ID' in rss and '--previous previous-native-rss/capture' in rss
    assert 'prepare-native-rss-successor.py restore' in rss
    assert 'default: false' in raw and 'default: economic-directories' in raw
    names=['Validate explicit source registry lifecycle','Verify exact successful source predecessor','Restore that source artifact only',
           'Bind restored original source','Read two native feeds once','Rebuild native intake','Retain native source attempt','Publish exact native source status']
    assert [rss.index(x) for x in names] == sorted(rss.index(x) for x in names)


def test_native_feed_source_step_has_no_github_or_business_token_and_failure_is_not_success():
    raw=WORKFLOW.read_text(); rss=raw.split('  native-rss:\n',1)[1]
    source=rss.split('- name: Read two native feeds once',1)[1].split('- name: Rebuild native intake',1)[0]
    assert 'github.token' not in source and 'GH_TOKEN' not in source
    assert 'test "$BOOTSTRAP" = true' in source and 'SOURCE_EVENT' not in source
    assert 'test -f native-rss-intake/predecessor-verification.json' in source
    assert "os.environ['CAPTURE_RESULT'] == os.environ['VERIFY_RESULT'] == 'success'" in rss
    assert 'registry' not in rss.split('uses: actions/upload-artifact@v7',1)[1].split('- name: Publish',1)[0]
    assert 'retention-days: 90' in rss and '没有自动寻找上一成功' in rss
