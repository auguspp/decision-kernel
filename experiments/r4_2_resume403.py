"""One explicitly approved replacement for the retained 403; not general recovery."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess

_spec = importlib.util.spec_from_file_location('r4_2_original_driver', Path(__file__).with_name('r4_2_sub2api.py'))
e = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e)

PARENT = 'a3785f7264771836c8abff87e82b20834c4563b7'
DRIVER_BLOB = '7fd5e2a9924e9cd353d63c45f8cbde1b3eb4f853'
APPROVAL = '5797702255'
AUTHORITY = 'https://github.com/auguspp/decision-kernel/issues/526#issuecomment-' + APPROVAL
CHILD = 'continuations/permission-retry-1/'
PARENT_HASHES = {
    'launch.json': 'e21ebd4b9196c90ca6d294d702e16c1898e58879bec9d032eb148341354a442e',
    'receipt.json': '504dfa69970e6a4611cdcaf81fd4d3ece8baf752c12a1c7b1a394173d0d8822c',
    '600362/O/pre/usage.json': 'ffcc64cdca948e5c8373c64fb62de543bdb5ca8e0273fb391213f18a8af69be2',
}


def check_parent(api):
    """Accept only this exact settled denial, never a successful/unknown attempt."""
    e.once.require(api.get('git/ref/heads/' + e.WORK_REF)['object']['sha'] == PARENT,
                   'RETRY_PARENT_CHANGED_OR_ALREADY_CONSUMED')
    records = {}
    for name, digest in PARENT_HASHES.items():
        raw = api.file(e.PREFIX + name, PARENT)
        e.once.require(e.once.sha(raw) == digest, 'RETRY_PARENT_BYTES')
        records[name] = e.once.identity._json(raw)
    launch, receipt, usage = (records[n] for n in PARENT_HASHES)
    e.once.require(launch['id'] == e.EXPERIMENT and launch['run_id'] == '35877859341'
                   and receipt['experiment'] == e.EXPERIMENT
                   and receipt['model_requests_started'] == 1 and receipt['stopped_early'] is True
                   and receipt['records'] == [{**usage, 'ticker': '600362'}]
                   and usage['http_status'] == 403 and usage['error_type'] == 'PermissionDeniedError'
                   and usage['physical_sends'] == 1 and usage['response_received'] is False
                   and usage['request_id'] == '029a79da-308f-4c67-a316-7ec61e7a937f'
                   and usage['arm'] == 'O' and usage['stage'] == 'PRE'
                   and receipt['samples'] == list(e.SAMPLES), 'RETRY_NOT_EXACT_SETTLED_403')
    return usage


def run_remaining(samples, out, previous, *, send=None, before_send=lambda: None):
    """Reuse the original arm loop; only the rejected request is a repeated send."""
    e.once.require([spec for spec, _ in samples] == list(e.SAMPLES), 'RETRY_SAMPLE_SCOPE')
    sender = e.send_one if send is None else send
    seen = set()
    records = []
    stop = False

    def checked_send(prompt, output_type, arm, destination):
        key = (prompt['discovery_observation']['ticker'], arm, prompt['stage'])
        e.once.require(key not in seen and len(seen) < 8, 'RETRY_DUPLICATE_OR_CALL_LIMIT')
        before_send()
        if not seen:
            e.once.require(key == ('600362', 'O', 'PRE'), 'RETRY_FIRST_STAGE')
            params = e.parameters(prompt, output_type, arm)
            preview = e.preview(prompt, params)
            e.once.require(e.once.sha(e.once.raw(prompt)) == previous['prompt_sha256']
                           and preview['request_sha256'] == previous['pre_send']['request_sha256'],
                           'RETRY_ORIGINAL_REQUEST_CHANGED')
        seen.add(key)
        result, row = sender(prompt, output_type, arm, destination)
        return result, {**row, 'attempt_kind': 'HUMAN_AUTHORIZED_PERMISSION_RETRY'
                        if len(seen) == 1 else 'ORIGINAL_PREVIOUSLY_UNRUN_ARM',
                        'replaces_request_id': previous['request_id'] if len(seen) == 1 else None}

    for spec, (packet, discovery, context) in samples:
        rows, stop = e.run_arms(packet, discovery, context, out / spec['ticker'], send=checked_send)
        records.extend({**row, 'ticker': spec['ticker']} for row in rows)
        if stop:
            break
    count = sum(row.get('physical_sends', 0) for row in records)
    e.once.require(len(records) <= 8 and count <= 8, 'RETRY_TOTAL_CALL_LIMIT')
    return records, stop


def main():
    e.once.require(os.environ.get('R4_2_RETRY_APPROVAL') == APPROVAL
                   and os.environ.get('GITHUB_RUN_ATTEMPT') == '1', 'RETRY_EXPLICIT_AUTHORITY')
    code = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    e.once.require(code == os.environ.get('EVAL_CODE_SHA')
                   and e.once.blob(Path(e.__file__).read_bytes()) == DRIVER_BLOB,
                   'RETRY_CODE_IDENTITY')
    api = e.GitHubAPI(os.environ['GH_TOKEN'], max_calls=512)
    previous = check_parent(api)
    root = Path(e.PREFIX)
    root.mkdir(parents=True, exist_ok=False)
    out = root / CHILD
    out.mkdir(parents=True, exist_ok=False)
    scope = dict(experiment=e.EXPERIMENT, parent_commit=PARENT, parent_files=PARENT_HASHES,
                 authority=AUTHORITY, human_words='可以重试了，刚才联系了管理员，开了权限',
                 admin_permission='HUMAN_REPORTED_NOT_YET_INFERENCE_VERIFIED', code_commit=code,
                 original_driver_blob=DRIVER_BLOB, original_requests_sent=1,
                 authorized_replacement_retries=1, maximum_new_requests=8,
                 maximum_lifetime_requests=9, monetary_cap=None, provider='SUB2API', model=e.once.MODEL,
                 samples=e.SAMPLES, original_cutoffs_preserved=True, automatic_retry=False,
                 production_activation=False, investment_authority='NONE')
    e.put(out / 'scope.json', scope)
    samples = [(spec, e.load_sample(api, spec, out / spec['ticker'] / 'original')) for spec in e.SAMPLES]
    # No model is reached unless current head is still the inspected settled parent.
    check_parent(e.GitHubAPI(os.environ['GH_TOKEN']))
    ret = e.once.Retainer(api, {'id': e.EXPERIMENT, 'work_ref': e.WORK_REF,
        'prefix': e.PREFIX + CHILD, 'continuation': {'kind': 'EXPLICIT_RETRY_OF_SETTLED_403',
        'authority': AUTHORITY, 'parent_commit': PARENT, 'prior_requests_sent': 1}}, code, out)
    launch = ret.begin()  # Same experiment/ref, create-only child marker; never reset old launch.
    def current_launch():
        fresh = e.GitHubAPI(os.environ['GH_TOKEN'])
        e.once.require(fresh.get('git/ref/heads/' + e.WORK_REF)['object']['sha'] == launch['ref'],
                       'RETRY_CONCURRENT_WRITE')
    records, stop, accounting_complete = [], False, True
    try:
        records, stop = run_remaining(samples, out, previous, before_send=current_launch)
    except Exception as exc:
        stop = True
        accounting_complete = False
        e.put(out / 'failure.json', {'error_type': type(exc).__name__, 'automatic_retry': False})
        # Recover only actually retained per-send receipts, never infer a successful call.
        records = [{**json.loads(p.read_bytes()), 'ticker': p.relative_to(out).parts[0]}
                   for p in sorted(out.glob('*/**/usage.json'))]
    started = sum(row.get('physical_sends', 0) for row in records)
    e.once.require(started <= 8, 'RETRY_TOTAL_CALL_LIMIT')
    e.put(out / 'receipt.json', {**scope, 'records': records, 'model_requests_started': started if accounting_complete else None,
        'minimum_requests_from_saved_receipts': started, 'request_accounting_complete': accounting_complete,
        'lifetime_requests_started': 1 + started if accounting_complete else None, 'stopped_early': stop,
        'status': 'EXECUTION_RECORDS_NOT_QUALITY_ACCEPTANCE',
        'billing': 'ACCOUNT_BILL_NOT_RETRIEVED_NO_MONETARY_LIMIT', 'finished_at': e.once.now()})
    # Existing native writer appends only this child subtree; no original name is reused.
    e.once.require(all(p.is_relative_to(out) for p in root.rglob('*') if p.is_file()),
                   'RETRY_WRITE_OUTSIDE_CHILD')
    publication = e.retain_results(ret, api, root, launch)
    e.put(out / 'publication.json', publication)
    print('EVAL_RETRY_RESULT_COMMIT=' + publication['commit'])
    print('EVAL_LIFETIME_REQUESTS=' + (str(1 + started) if accounting_complete else 'UNKNOWN'))
    return 1 if stop else 0


if __name__ == '__main__':
    raise SystemExit(main())
