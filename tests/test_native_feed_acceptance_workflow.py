from pathlib import Path

WORKFLOW = Path('.github/workflows/hithink-stock-dump-trial.yml')
SCRIPT = Path('.github/scripts/native-feed-acceptance.py')


def native_job():
    return WORKFLOW.read_text().split('  native-feed:\n', 1)[1]


def test_native_acceptance_is_only_explicit_dispatch_not_a_push_or_schedule():
    text = WORKFLOW.read_text()
    job = native_job()
    assert "if: github.event_name == 'workflow_dispatch' && inputs.trial-purpose == 'native-feed-acceptance'" in job
    assert 'native-execute:' in text and 'type: boolean\n        default: false' in text
    paths = text.split('    paths:\n', 1)[1].split('\n\n', 1)[0]
    assert 'native' not in paths and 'schedule:' not in text
    assert 'actions: read' in job and 'contents: read' in job
    assert 'write' not in job.split('    steps:', 1)[0]
    for forbidden in ('actions/cache', 'continue-on-error', 'workflow_run:', 'gh workflow', 'radar_feed_intake capture', '--bootstrap'):
        assert forbidden not in job


def test_native_inputs_reach_shell_through_validated_outputs_not_code_interpolation():
    job = native_job()
    assert 'SOURCE_RUN: ${{ steps.intent.outputs.source_run_id }}' in job
    assert 'MARKET_RUN: ${{ steps.intent.outputs.market_run_id }}' in job
    assert 'test -n "$MARKET_RUN"' in job
    assert '${{ inputs.native-feed-run-id }}' not in job.split('run: python .github/scripts/native-feed-acceptance.py init', 1)[1]
    assert job.count('digest-mismatch: error') == 3
    assert job.count('uses: actions/download-artifact@v8') == 3
    assert 'artifact-ids: ${{ steps.source-meta.outputs.artifact_id }}' in job
    assert 'artifact-ids: ${{ steps.market-meta.outputs.artifact_id }}' in job
    assert 'artifact-ids: ${{ steps.history-meta.outputs.artifact_id }}' in job


def test_no_market_secret_or_catalog_access_precedes_source_qualification():
    job = native_job()
    assert job.index('Rebuild and qualify sources') < job.index('Bind exact saved market') < job.index('Scan one batch')
    segment = job.split('- name: Scan one batch', 1)[1].split('- name: Rebuild isolated', 1)[0]
    assert "if: steps.source-check.outputs.needs_market == 'true'" in segment
    assert segment.count('${{ secrets.HITHINK_FINANCE_API_KEY }}') == 1
    assert job.count('${{ secrets.HITHINK_FINANCE_API_KEY }}') == 1
    verify = job.split('- name: Rebuild isolated', 1)[1].split('- name: Preserve isolated', 1)[0]
    assert 'if: always()' in verify and "HITHINK_FINANCE_API_KEY: ''" in verify
    assert 'GH_TOKEN' not in verify
    assert "execution._decode(raw, credential=credential)" in SCRIPT.read_text()
    assert "collector['request_raw']" in SCRIPT.read_text()
    assert 'import requests' not in SCRIPT.read_text()


def test_attachment_is_after_replay_and_success_links_require_real_upload():
    job = native_job()
    assert job.index('Rebuild isolated') < job.index('Preserve isolated') < job.index('Publish native acceptance')
    assert 'retention-days: 90' in job and 'if-no-files-found: error' in job
    assert "os.environ['UPLOAD_RESULT'] == 'success' and os.environ['ARTIFACT_URL']" in job
    assert "os.environ['VERIFY_RESULT'] == 'success' and os.environ['CAPTURE_RESULT'] == 'success'" in job
    assert 'trial/scan/index.html' in job and 'trial/execution/index.html' in job
    assert '不是每日消费' in job and '不自动执行下一批' in job


def test_embedded_summary_python_compiles_without_github_expression_injection():
    job = native_job()
    code = job.split("          python - <<'PY'\n", 1)[1].split('\n          PY', 1)[0]
    source = '\n'.join(line.removeprefix('          ') for line in code.splitlines())
    assert '${{' not in source
    compile(source, '<native-acceptance-summary>', 'exec')
