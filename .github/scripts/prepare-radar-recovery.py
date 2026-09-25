"""Prepare existing workflow composition; diagnostic branch only."""
from pathlib import Path
import shutil
import textwrap
base = Path('../prep')
for path in ('.github/scripts/reconcile-radar-delivery.py', 'tests/test_radar_delivery_reconciliation.py'):
    shutil.copyfile(base / path, Path(path))
p = Path('.github/workflows/stock-reading-after-sector.yml')
s = p.read_text()
s = s.replace('    workflows: [sector-radar-shadow]', '    workflows: [sector-radar-shadow, hithink-stock-dump-trial, decision-inbox]')
s = s.replace('\npermissions:', '''
  schedule:
    - cron: '35 10 * * 1-5'
    - cron: '5 11,13 * * 1-5'
  workflow_dispatch:
    inputs:
      mode:
        description: Read-only audit or bounded recovery through existing source contracts
        type: choice
        options: [audit, execute]
        default: audit

permissions:''', 1)
a = s.index('  dispatch-stock-reading:\n')
b = s.index('\n  dispatch-tdx-concept:\n', a)
s = s[:a] + '''  reconcile-deliveries:
    if: >-
      github.repository == 'auguspp/decision-kernel' &&
      github.ref == 'refs/heads/main' && github.run_attempt == 1 &&
      (github.event_name != 'workflow_run' ||
       (github.event.workflow_run.head_branch == 'main' &&
        github.event.workflow_run.head_repository.full_name == github.repository &&
        github.event.workflow_run.run_attempt == 1))
    runs-on: ubuntu-latest
    timeout-minutes: 8
    permissions:
      contents: read
      actions: read
      issues: write
    concurrency:
      group: radar-delivery-reconciliation
      cancel-in-progress: false
    env:
      RECONCILE_MODE: ${{ inputs.mode || 'execute' }}
    steps:
      - uses: actions/checkout@v7
        with:
          ref: ${{ github.sha }}
          persist-credentials: false
      - uses: actions/setup-python@v7
        with:
          python-version: '3.12'
      - name: Install existing read-only consumer
        run: python -m pip install -e '.[feeds]'
      - name: Reconcile qualified deliveries and previous intents
        id: plan
        env:
          GH_TOKEN: ${{ github.token }}
        run: python .github/scripts/reconcile-radar-delivery.py plan
      - name: Retain exact dispatch intent before any POST
        id: intent
        if: steps.plan.outputs.dispatch == 'true' && env.RECONCILE_MODE == 'execute'
        uses: actions/upload-artifact@v7
        with:
          name: radar-reconcile-intent-${{ github.run_id }}
          path: radar-reconcile/plan.json
          if-no-files-found: error
          retention-days: 90
      - name: Dispatch only the missing stage once
        if: steps.intent.outcome == 'success' && env.RECONCILE_MODE == 'execute'
        env:
          GH_TOKEN: ${{ secrets.DAILY_CHAIN_DISPATCH_TOKEN }}
        shell: bash
        run: |
          if [ -z "${GH_TOKEN:-}" ]; then
            echo '::error::Missing repository secret DAILY_CHAIN_DISPATCH_TOKEN; do not fall back to GITHUB_TOKEN'
            exit 1
          fi
          python .github/scripts/reconcile-radar-delivery.py dispatch
      - name: Keep one visible system health issue
        if: always()
        env:
          GH_TOKEN: ${{ github.token }}
        run: python .github/scripts/reconcile-radar-delivery.py report
      - name: Retain reconciliation and gaps
        if: always()
        uses: actions/upload-artifact@v7
        with:
          name: radar-reconcile-report-${{ github.run_id }}
          path: radar-reconcile/report.json
          if-no-files-found: error
          retention-days: 90
''' + s[b:]
p.write_text(s)
for filename, title in (
    ('sector-radar-shadow.yml', "sector-radar-shadow | operation=${{ inputs.operation || 'produce' }} | recovery=${{ inputs.recovery-key || 'none' }}"),
    ('hithink-stock-dump-trial.yml', "${{ inputs.trial-purpose || 'stock-dump' }} | sector=${{ inputs.stock-market-run-id || 'none' }} | page=${{ inputs.stock-discovery-page || 'base' }} | recovery=${{ inputs.recovery-key || 'none' }}"),
):
    p = Path('.github/workflows', filename)
    s = p.read_text()
    first, rest = s.split('\n', 1)
    s = first + '\nrun-name: >-\n  ' + title + '\n' + rest
    s = s.replace('    inputs:\n', '''    inputs:
      recovery-key:
        description: Optional reconciliation intent identity; never changes data qualification
        type: string
        required: false
        default: ''
''', 1)
    p.write_text(s)
# Migrate only the superseded dispatcher orchestration test. All original
# classifier, source, artifact, TDX and authority tests remain intact.
p = Path('tests/test_stock_daily_successor.py')
s = p.read_text()
a = s.index('def test_successor_reuses_one_daily_sector_clock_for_stock_and_tdx_without_new_schedule():')
b = s.index('def test_tdx_daily_handoff_reuses_exact_sector_result_and_existing_capture_contract():', a)
s = s[:a] + '''def test_successor_reconciles_deliveries_without_a_second_source_clock():
    import yaml
    raw = WORKFLOW.read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)
    trigger = parsed.get("on", parsed.get(True))
    assert trigger["workflow_run"]["workflows"] == ["sector-radar-shadow", "hithink-stock-dump-trial", "decision-inbox"]
    assert trigger["workflow_run"]["types"] == ["completed"]
    assert {row["cron"] for row in trigger["schedule"]} == {"35 10 * * 1-5", "5 11,13 * * 1-5"}
    assert trigger["workflow_dispatch"]["inputs"]["mode"]["default"] == "audit"
    assert "push" not in trigger
    jobs = parsed["jobs"]
    assert set(jobs) == {"reconcile-deliveries", "dispatch-tdx-concept"}
    job = jobs["reconcile-deliveries"]
    assert job["concurrency"] == {"group": "radar-delivery-reconciliation", "cancel-in-progress": False}
    assert job["permissions"] == {"contents": "read", "actions": "read", "issues": "write"}
    steps = {step.get("name"): step for step in job["steps"] if "name" in step}
    intent = "Retain exact dispatch intent before any POST"
    dispatch = "Dispatch only the missing stage once"
    assert raw.index(intent) < raw.index(dispatch)
    assert "steps.intent.outcome == 'success'" in steps[dispatch]["if"]
    assert steps[dispatch]["env"]["GH_TOKEN"] == "${{ secrets.DAILY_CHAIN_DISPATCH_TOKEN }}"
    assert "do not fall back to GITHUB_TOKEN" in steps[dispatch]["run"]
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in job["if"]
    assert "github.run_attempt == 1" in job["if"]
    assert raw.count("tdx-concept-snapshot.yml/dispatches") == 1
    assert "Classify exact Sector origin for TDX" in raw
    assert "HITHINK_FINANCE_API_KEY" not in raw
    assert "/rerun" not in raw and "gh run watch" not in raw
    assert "stock-business-research.yml/dispatches" not in raw
    assert "schedule:" not in SECTOR_WORKFLOW.read_text().split("permissions:", 1)[0]
    assert "schedule:" not in STOCK_WORKFLOW.read_text().split("permissions:", 1)[0]


''' + s[b:]
p.write_text(s)
p = Path('docs/radar-delivery-recovery-v1.md')
p.write_text('''# Daily Radar delivery reconciliation — 2026-09-25

Human authority: #297/5831654154 and fixed operational health #581. This supersedes the old manual-only recovery policy only within the bounds below; old failures and policies remain historical. The R5 architecture is unchanged.

The existing stock-reading-after-sector workflow now compares saved qualified state with actual Stock completion. The former one-shot Stock dispatcher is retired, not left running in parallel. TDX keeps its existing independent exact-parent job. Completion events for Sector/Stock/Inbox recheck after shared-Key work ends. Maintenance-only checks at weekday18:35/19:05/21:05 supplement, not replace, the external18:13 primary clock; GitHub schedule can be delayed and is not an SLA.

A current verified same-session no-op retains its original result-bearing predecessor through #580. Matching completed Stock, including an explicit partial result, is not fetched again. If no Stock exists, one original stock-reading dispatch binds the precise Sector run. New child titles bind parent/page/intent. If an attempt already exists but has not produced a validated result, the system reports the gap instead of blindly duplicating it.

A missing after-close Sector invocation or a classified transient failure can receive a fresh produce attempt. At most3 source attempts per after-close day (original plus2 recovery) are observed. Only original transport TIMEOUT/URL_ERROR/HTTP502/503/504 and definite pre-acquisition metadata/shared-Key failure qualify.401/403/429, unknown failures, invalid data, corrupt archives and multi-day recovery requirements remain visible engineering work. Weekday checks request calendar-qualified production; they never fabricate a trading session. Generic historical membership/PIT backfill is not established.

All reconcilers serialize on one job concurrency group. They recheck active Key users before planning and before POST; it is bounded observation, not an atomic provider lock. An immutable intent artifact is uploaded before POST. No matching child means uncertainty: do not resend. A verified receipt proving no POST happened after a changed precheck permits a later plan. No rerun endpoint, retry loop or source credential is used in the reconciler. The source workflows still validate exact inputs, clocks, raw data, existing budgets, replay and publication.

#581 retains machine health and unresolved delivery identities. A later day succeeding cannot erase an older missing Stock parent. The Brief reads this status separately from Research and never assigns the Human data repair work. A transient incident can recover automatically; permanent data/permission failures require Main Construction. Live audit success proves idempotent use of current saved results, not that all future failures or historical gaps will be recoverable.

No new provider, package dependency, database, generic scheduler, Research execution, automatic Full/Odds/Watch or trading. Native GitHub history and original artifacts remain canonical. The actual dispatch, child completion, normal publication and useful daily research are distinct acceptance facts.
''')
