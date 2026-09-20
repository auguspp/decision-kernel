"""Synthetic opt-in and declared-source controls, never a live disclosure run."""
from pathlib import Path
import os
import re
import subprocess
import sys
import textwrap

import pytest
import test_external_research_admission as fx
from decision_kernel.runtime import external_research_admission as gate

WORKFLOW = Path('.github/workflows/decision-inbox.yml')


def _scope_step():
    text = WORKFLOW.read_text(encoding='utf-8')
    step = text.split('      - name: Record disclosure request scope\n', 1)[1]
    step = step.split('      - name: Publish Human summary\n', 1)[0]
    return textwrap.dedent(step.split('        run: |\n', 1)[1])


def test_disclosure_job_requires_explicit_boolean_without_gating_inbox():
    text = WORKFLOW.read_text(encoding='utf-8')
    trigger = text.split('on:\n', 1)[1].split('\npermissions:', 1)[0]
    assert re.search(r'scan-disclosures:\n\s+description: [^\n]+\n\s+type: boolean\n'
                     r'\s+required: false\n\s+default: false', trigger)
    assert 'schedule:' not in trigger and 'push:' not in trigger
    inbox, disclosures = text.split('  inbox:\n', 1)[1].split('  disclosures:\n', 1)
    assert disclosures.startswith("    if: github.event_name == 'workflow_dispatch' && inputs.scan-disclosures == true\n")
    assert 'needs:' not in inbox and 'needs:' not in disclosures
    assert 'continue-on-error:' not in disclosures
    assert 'decision-kernel scan-disclosures' in disclosures
    assert '--attempt-history disclosure-attempt-history.json' in disclosures
    assert 'python -m decision_kernel.runtime.attention_inbox_with_odds_watch' in inbox
    assert 'DISCLOSURE_SCAN_REQUESTED: ${{ inputs.scan-disclosures }}' in inbox


@pytest.mark.parametrize('requested', ['', 'false', 'true'])
def test_actual_scope_step_retains_honest_markdown_html_and_summary(tmp_path, requested):
    output = tmp_path / 'decision-inbox'
    output.mkdir()
    (output / 'summary.md').write_text('Existing saved result\n', encoding='utf-8')
    (output / 'index.html').write_text('<html><body>Existing saved result</body></html>', encoding='utf-8')
    done = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', _scope_step()],
                          cwd=tmp_path, env={**os.environ, 'DISCLOSURE_SCAN_REQUESTED': requested},
                          text=True, capture_output=True, timeout=10)
    assert done.returncode == 0, done.stderr
    for content in [done.stdout, (output/'summary.md').read_text(), (output/'index.html').read_text()]:
        if requested == 'true':
            assert '执行结果见独立 disclosures job，不由 Inbox 成功推断' in content
            assert 'NOT_REQUESTED' not in content
        else:
            assert 'NOT_REQUESTED' in content
            assert '不代表没有公告，也不是来源获取失败' in content
    assert (output/'summary.md').read_text().startswith('Existing saved result\n')
    assert (output/'index.html').read_text().endswith('</body></html>')


def test_scope_step_does_not_create_a_fake_inbox_when_delivery_failed(tmp_path):
    done = subprocess.run(['bash', '-e', '-c', _scope_step()], cwd=tmp_path,
                          env={**os.environ, 'DISCLOSURE_SCAN_REQUESTED': 'false'},
                          text=True, capture_output=True, timeout=10)
    assert done.returncode == 0 and 'NOT_REQUESTED' in done.stdout
    assert not (tmp_path/'decision-inbox').exists()


def test_scope_step_rejects_unexpected_input_before_mutating_output(tmp_path):
    done = subprocess.run(['bash', '-e', '-c', _scope_step()], cwd=tmp_path,
                          env={**os.environ, 'DISCLOSURE_SCAN_REQUESTED': 'untrusted'},
                          text=True, capture_output=True, timeout=10)
    assert done.returncode != 0 and 'INVALID_DISCLOSURE_SCAN_REQUEST' in done.stderr
    assert not (tmp_path/'decision-inbox').exists()


def _with_unrelated_failed_background():
    packet, pf, cat, values, commits = fx.setup()
    background = dict(pf['reads'][1], id='background', identity='unrelated background',
                      locator='https://issuer.invalid/background', succeeded=False,
                      tool_reference='synthetic:failed-background')
    background.pop('body_sha256')
    pf['reads'].append(background)
    pf['inventories'][0]['leads'].append({
        'identity': background['identity'], 'locator': background['locator'],
        'authority': 'PRIMARY', 'decision_relevant': False,
        'relevance_note': 'Synthetic predeclared non-load-bearing background; not a relevance classifier.'})
    return packet, pf, cat, values, commits


def test_original_admission_allows_declared_scope_despite_unrelated_failed_background():
    parts = _with_unrelated_failed_background()
    before = fx.raw(parts[1])
    report, _, calls = fx.run(fx.checks(*parts))
    assert report['research_execution_allowed'] and len(calls) == 1
    assert fx.raw(parts[1]) == before  # failed read is not deleted or changed to success


@pytest.mark.parametrize('required_id', ['report', 'update'])
def test_required_report_or_relevant_counterevidence_failure_still_blocks(required_id):
    parts = _with_unrelated_failed_background()
    next(r for r in parts[1]['reads'] if r['id'] == required_id)['succeeded'] = False
    fx.denied(fx.checks(*parts), 'SOURCE_PREFLIGHT_INCOMPLETE')


def test_research_entry_links_source_scope_without_weakening_legacy_stock_contract():
    entry = Path('docs/RESEARCH-ENTRY.md').read_text(encoding='utf-8')
    policy = Path('docs/research-source-scope-v0.md').read_text(encoding='utf-8')
    assert '(research-source-scope-v0.md)' in entry
    assert 'FIRST_BUSINESS_BASELINE' in policy
    assert '不能在下载失败后把必要材料改成可选' in entry
