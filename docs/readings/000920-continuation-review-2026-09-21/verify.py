"""Offline review of retained bytes; never repairs, sends, or authorizes Research."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError
from decision_kernel.research_funnel import PreResearchResult


def verify(root: Path) -> dict:
    root = Path(root)
    diagnostic = json.loads((root / 'diagnosis.json').read_bytes())
    originals = {}
    for name, expected in diagnostic['retained_originals'].items():
        raw = (root / name).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256'] or blob != expected['git_blob']:
            raise ValueError('Retained original identity differs: ' + name)
        originals[name] = json.loads(raw)
    response = originals['pre-model-output.txt']
    try:
        PreResearchResult.model_validate(response)
    except ValidationError as exc:
        errors = [{'location': list(e['loc']), 'type': e['type']} for e in exc.errors()]
    else:
        raise ValueError('Original invalid response unexpectedly accepted')
    if errors != diagnostic['application_errors']:
        raise ValueError('Original rejection differs')
    host, candidate, validation = (originals[n] for n in ('host-receipt.json','candidate.json','validation.json'))
    if host['model_stage_attempts'] != ['pre'] or host['status'] != 'EXECUTION_GAP' or host['source_requests'] != 0 or host['market_requests'] != 0:
        raise ValueError('Execution scope differs')
    if candidate['pre_research'] is not None or candidate['quick_research'] is not None or validation['funnel_result'] is not None:
        raise ValueError('Invalid output was promoted')
    usage = host['provider_usage']
    if len(usage) != 1 or usage[0]['phase'] != 'APPLICATION_VALIDATION' or usage[0]['provider_status'] != 'completed' or usage[0]['output_sha256'] != diagnostic['retained_originals']['pre-model-output.txt']['sha256']:
        raise ValueError('Retained output/receipt binding differs')
    values = diagnostic['reported_engineering_amounts_cny']
    revenue, product_cost, segment_cost = (Decimal(values[k]) for k in ('revenue','product_cost','segment_cost'))
    computed = {'product_revenue_less_cost': str(revenue-product_cost),
                'segment_revenue_less_cost': str(revenue-segment_cost),
                'unexplained_cost_dimension_difference': str(segment_cost-product_cost)}
    if computed != diagnostic['arithmetic_cny']:
        raise ValueError('Diagnostic arithmetic differs')
    return {'status': 'ORIGINAL_REJECTION_REPRODUCED_NOT_REPAIRED', 'errors': errors,
            'originals_checked': len(originals), 'arithmetic_cny': computed,
            'economic_truth_certified': False, 'new_model_calls': 0,
            'research_execution_allowed': False, 'investment_authority': 'NONE'}


if __name__ == '__main__':
    print(json.dumps(verify(Path(__file__).parent), ensure_ascii=False, indent=2))
