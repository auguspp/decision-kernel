"""Two fixed corrected-input calls; reuse the existing experiment and Kernel.

Never a production selector, recovery service or authority to refresh sources.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import r4_2_sub2api as pilot

once = pilot.once
RUNTIME = '2971d00145e0980238429c4995d783fa3d280ef1'
PARENT = 'f0c9104c9dbc2b2fbdcf90b7b75bb024827509b2'
APPROVAL = '5804459106'
AUTHORITY = 'https://github.com/auguspp/decision-kernel/issues/526#issuecomment-' + APPROVAL
ROOT = pilot.PREFIX
PREFIX = ROOT + 'continuations/source-context-532-v1/'
ARMS = ('S0', 'S1')


def corrected_prompt(packet, discovery, context, preflight):
    sp = packet.model_copy(update={'method_version': pilot.single.METHOD_VERSION,
                                   'prompt_version': pilot.single.PROMPT_VERSION})
    old = once.initial_prompt(sp, discovery, context)
    prompt = once.initial_prompt(sp, discovery, context, source_preflight=preflight)
    once.require(set(prompt) == set(old) | {'host_source_checks'}
                 and once.raw({k:v for k,v in prompt.items() if k != 'host_source_checks'}) == once.raw(old),
                 'FIXED_FINANCIAL_INPUT_CHANGED')
    return prompt


def check_previous_prompt(prompt, previous_raw):
    expected = once.raw({k:v for k,v in prompt.items() if k != 'host_source_checks'})
    once.require(previous_raw == expected, 'PREVIOUS_PROMPT_DIFFERENT')


def run_pair(prompt, out, *, send=None):
    send = send or pilot.send_one
    records = []
    for arm in ARMS:
        _, record = send(prompt, pilot.single.QuickAssessment, arm, out / arm)
        records.append(record)
        if record.get('stop_batch'):
            break
    once.require(sum(r.get('physical_sends', 0) for r in records) <= 2, 'CORRECTION_CALL_BOUND')
    return records


def main():
    once.require(os.environ.get('R4_2_APPROVAL') == APPROVAL
                 and os.environ.get('GITHUB_RUN_ATTEMPT') == '1', 'CORRECTION_AUTHORITY')
    code = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    once.require(code == os.environ.get('EVAL_CODE_SHA'), 'CORRECTION_CODE')
    driver = Path(pilot.__file__).read_bytes()
    once.require(once.blob(driver) == '7fd5e2a9924e9cd353d63c45f8cbde1b3eb4f853', 'PILOT_DRIVER_CHANGED')
    api = pilot.GitHubAPI(os.environ['GH_TOKEN'], max_calls=512)
    once.require(api.get('git/ref/heads/main')['object']['sha'] == RUNTIME, 'RUNTIME_MOVED')
    once.require(api.get('git/ref/heads/' + pilot.WORK_REF)['object']['sha'] == PARENT, 'EVAL_PARENT_MOVED')
    prior_raw = api.file(ROOT + 'continuations/permission-retry-1/receipt.json', PARENT)
    prior = once.identity._json(prior_raw)
    once.require(prior['lifetime_requests_started'] == 8 and prior['model_requests_started'] == 7
                 and len(prior['records']) == 7
                 and all(r['response_received'] and r['provider_status'] == 'completed' for r in prior['records']),
                 'PRIOR_CALLS_NOT_RECONCILED')
    out = Path(PREFIX); out.mkdir(parents=True, exist_ok=False)
    packet, discovery, context = pilot.load_sample(api, pilot.SAMPLES[0], out / 'original')
    spec = next(s.model_dump(mode='json') for s in packet.source_refs
                if s.purpose == 'PRE_EXECUTION_SOURCE_PREFLIGHT')
    preflight = once.identity._checked_source(spec, lambda s: api.file(s['path'], s['ref']))
    prompt = corrected_prompt(packet, discovery, context, preflight)
    old_prompt = api.file(ROOT + 'continuations/permission-retry-1/600362/S1/prompt.json', PARENT)
    check_previous_prompt(prompt, old_prompt)
    # All checks and both real SDK previews precede any launch or credential use.
    previews = {arm: pilot.preview(prompt, pilot.parameters(prompt, pilot.single.QuickAssessment, arm))
                for arm in ARMS}
    pilot.put(out / 'preflight.json', preflight)
    pilot.put(out / 'host-source-checks.json', prompt['host_source_checks'])
    pilot.put(out / 'sdk-previews.json', previews)
    scope = dict(experiment=pilot.EXPERIMENT, authority=AUTHORITY, code_commit=code,
        runtime=RUNTIME, parent_commit=PARENT, prior_requests_started=8,
        prior_receipt_sha256=once.sha(prior_raw), max_new_calls=2, monetary_cap=None,
        arms=ARMS, provider='SUB2API', model=once.MODEL, automatic_retry=False, fallback=False,
        corrected_field='host_source_checks', preflight_source=spec,
        original_context_sha256=once.sha(once.raw(context)), original_cutoff=packet.research_cutoff.isoformat(),
        meaning='HISTORICAL_SOURCE_WINDOW_NOT_CURRENT_ADMISSION_OR_PRODUCTION_RESEARCH',
        production_activation=False, new_financial_fetches=0, hosted_calls=0)
    pilot.put(out / 'scope.json', scope)
    ret = once.Retainer(api, {'id':pilot.EXPERIMENT, 'work_ref':pilot.WORK_REF, 'prefix':PREFIX,
        'continuation':{'kind':'CORRECTED_SOURCE_STATUS_VALIDATION', 'authority':AUTHORITY,
                        'parent_commit':PARENT, 'prior_requests_started':8}}, code, out)
    launch = ret.begin()
    records = []; failure = None
    try:
        records = run_pair(prompt, out)
    except Exception as exc:
        failure = type(exc).__name__
    # Recover any saved per-arm receipt even if the orchestrator failed after a send.
    saved = [once.identity._json(p.read_bytes()) for p in sorted(out.glob('S*/usage.json'))]
    count = sum(r.get('physical_sends', 0) for r in saved)
    stopped = failure is not None or any(r.get('stop_batch') for r in saved)
    pilot.put(out / 'receipt.json', {**scope, 'records':saved, 'new_requests_started':count,
        'lifetime_requests_started':8+count, 'stopped_early':stopped, 'error_type':failure,
        'all_returns_complete':len(saved)==2 and all(r.get('provider_status')=='completed' for r in saved),
        'billing':'ACCOUNT_BILL_UNKNOWN', 'finished_at':once.now(), 'quality_acceptance':'NOT_ESTABLISHED'})
    # Reuse the exact native-Git retention implementation under this child only.
    old_prefix = pilot.PREFIX
    try:
        pilot.PREFIX = PREFIX
        publication = pilot.retain_results(ret, api, out, launch)
    finally:
        pilot.PREFIX = old_prefix
    pilot.put(out / 'publication.json', publication)
    print('CORRECTION_RESULT_COMMIT=' + publication['commit'])
    print('CORRECTION_NEW_REQUESTS=' + str(count))
    return 1 if stopped else 0


if __name__ == '__main__':
    raise SystemExit(main())
