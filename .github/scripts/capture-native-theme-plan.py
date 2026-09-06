"""Reuse the existing capture script's transport; execute one verified source plan."""
from __future__ import annotations

import argparse
import os
import runpy
from pathlib import Path

from decision_kernel.identity import canonical_json
from decision_kernel.runtime.theme_plan_execution import capture_plan, verify_execution, COMPLETE


def main(argv=None):
    parser = argparse.ArgumentParser(description='Explicit source plan only; no feed scan or producer state changes.')
    parser.add_argument('mode', choices=['capture', 'verify'])
    parser.add_argument('--scan', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.mode == 'verify':
            if os.environ.get('HITHINK_FINANCE_API_KEY'):
                raise ValueError('offline verifier must not receive a market credential')
            result = verify_execution(args.output)
            print(canonical_json(result))
            return 0 if result['market_stage_succeeded'] else 2
        if args.scan is None:
            raise ValueError('exact completed source scan required')
        # Only this fixed, version-controlled sibling supplies HTTP. User inputs
        # cannot select code. No second Requests implementation is introduced.
        existing = runpy.run_path(str(Path(__file__).with_name('capture-theme-probe.py')), run_name='native_plan_transport')
        context = existing['workflow_identity'](os.environ)
        credential = os.environ.get('HITHINK_FINANCE_API_KEY', '')
        result = capture_plan(args.scan, args.output, context=context, credential=credential, public_http=True,
            transport=lambda path, params: existing['request_raw'](path, params, api_key=credential))
        print(canonical_json({'status': result['status'], 'requests': len(result['requests'])}))
        return 0 if result['status'] == COMPLETE else 2
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc:
        print(canonical_json({'status': 'EXACT_PLAN_UNAVAILABLE', 'error_type': type(exc).__name__}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
