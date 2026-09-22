"""Bounded untrusted numeric decoding and exact leader identity."""
import json
import pytest
from decimal import Decimal
from decision_kernel.runtime import easy_stock_context as c
from test_easy_stock_context import market_body, project

@pytest.mark.parametrize('value', ['1e99999999999', '1e-99999999999', '0e99999999999', '1e31', '1e-31'])
def test_numeric_strings_cannot_expand_canonical_output(value):
    assert c.number(value) == (None, 'INVALID')

@pytest.mark.parametrize('text', ['1e99999999999', '1e-99999999999', '0e99999999999', '1234567890123456789012345678901'])
def test_json_numeric_expansion_rejected_before_canonical_hash(text):
    with pytest.raises(ValueError): c.decode(('{"x":'+text+'}').encode())

@pytest.mark.parametrize('value', [None, {'url':'https://untrusted.invalid'}, 'sh600000;exec', '600000'])
def test_invalid_leader_code_is_not_an_available_identity(value):
    body=json.loads(market_body());body['data'][0]['nzg_code']=value
    p=project('tencent-industry',json.dumps(body).encode())
    row=p['observations'][0]
    assert row['values']['leader_source_code'] is None
    assert 'leader_source_code' not in row['meta']['available_fields']

def test_decimal_values_keep_small_real_changes_and_true_zero():
    assert c.number('0.000001') == (Decimal('0.000001'), 'AVAILABLE')
    assert c.number('0') == (Decimal('0'), 'AVAILABLE')
