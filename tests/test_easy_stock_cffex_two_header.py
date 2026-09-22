"""Exact exchange two-row header from run 35726184042; data rows stay synthetic.

Original four GB18030 CSV bodies remain in artifact 10692678204, ZIP SHA256
 ee2942d186ec2bc7655a945cd4a7a8d412a58401a93d28aebd72c22397165431.
No source request, source/date fallback or authority change in these tests.
"""
import csv
from hashlib import sha256
import io

import pytest

from decision_kernel.runtime import easy_stock_context as c
from test_easy_stock_context import csv_body, project, receipt, NOW

GROUP_HEADER = ['交易日', '合约', '排名', '成交量排名', '', '',
                '持买单量排名', '', '', '持卖单量排名', '', '']
COLUMN_HEADER = ['', '', '', '会员简称', '成交量', '比上一交易日增减',
                 '会员简称', '持买单量', '比上一交易日增减',
                 '会员简称', '持卖单量', '比上一交易日增减']


def two_header_body(variety='IF', encoding='gb18030', edit=None):
    rows = list(csv.reader(io.StringIO(csv_body(variety, contracts=2).decode())))
    rows[:1] = [list(GROUP_HEADER), list(COLUMN_HEADER)]
    if edit:
        edit(rows)
    stream = io.StringIO()
    csv.writer(stream).writerows(rows)
    return stream.getvalue().encode(encoding)


@pytest.mark.parametrize('variety', c.VARIETIES)
@pytest.mark.parametrize('encoding', ['utf-8', 'utf-8-sig', 'gb18030'])
def test_exact_two_header_export_preserves_rows_totals_and_custody(variety, encoding):
    label = 'cffex-' + variety
    body = two_header_body(variety, encoding)
    p = project(label, body)
    legacy = project(label, csv_body(variety, contracts=2))
    assert p['status'] == 'POSITIONING_CONTEXT'
    assert p['totals'] == legacy['totals']
    assert p['contracts'] == legacy['contracts']
    assert p['coverage'] == legacy['coverage']
    assert len(p['rows']) == 40
    assert [r['source_row'] for r in p['rows']] == list(range(2, 42))
    assert [r['raw'] for r in p['rows']] == [r['raw'] for r in legacy['rows']]
    assert p['meta']['raw_sha256'] == sha256(body).hexdigest()
    assert p['meta']['trade_date'] == '2026-09-22'
    assert p['meta']['carry_forward'] is False
    assert p['coverage']['exchange_contract_catalog_complete'] == 'NOT_ESTABLISHED'
    assert p['historical_pit_availability'] == 'NOT_ESTABLISHED_BY_CURRENT_RETRIEVAL'
    assert all(p[k] == v for k, v in c.AUTHORITY.items())


def test_two_header_matching_allows_only_cell_whitespace_normalization():
    def edit(rows):
        rows[:2] = [[f' {cell} ' for cell in row] for row in rows[:2]]
    assert project('cffex-IF', two_header_body(edit=edit))['totals']['net_long_change'] == 120


@pytest.mark.parametrize('damage', [
    'missing_group', 'changed_group', 'extra_group_column', 'changed_subheader',
    'extra_subheader_column', 'standalone_subheader', 'duplicate_subheader',
    'subheader_after_data', 'blank_date_data', 'unknown_preamble',
])
def test_only_exact_adjacent_starting_header_is_skipped(damage):
    def edit(rows):
        if damage == 'missing_group':
            rows[0] = []
        elif damage == 'standalone_subheader':
            rows.pop(0)
        elif damage == 'changed_group':
            rows[0][6] = '未知排名'
        elif damage == 'extra_group_column':
            rows[0].append('')
        elif damage == 'changed_subheader':
            rows[1][7] = '持卖单量'
        elif damage == 'extra_subheader_column':
            rows[1].append('')
        elif damage == 'duplicate_subheader':
            rows.insert(2, list(COLUMN_HEADER))
        elif damage == 'subheader_after_data':
            rows.insert(3, rows.pop(1))
        elif damage == 'blank_date_data':
            rows[2][0] = ''
        else:
            rows.insert(0, ['说明'])
    with pytest.raises(ValueError):
        project('cffex-IF', two_header_body(edit=edit))


@pytest.mark.parametrize('damage', [
    'missing_rank', 'duplicate_rank', 'wrong_date', 'mixed_variety',
    'missing_change', 'negative_position', 'duplicate_member', 'bad_contract',
])
def test_two_header_support_does_not_relax_data_validation(damage):
    def edit(rows):
        if damage == 'missing_rank':
            rows.pop()
        elif damage == 'duplicate_rank':
            rows.append(list(rows[2]))
        elif damage == 'wrong_date':
            rows[2][0] = '20260921'
        elif damage == 'mixed_variety':
            rows[2][1] = 'IH2610'
        elif damage == 'missing_change':
            rows[2][8] = '--'
        elif damage == 'negative_position':
            rows[2][7] = '-1'
        elif damage == 'duplicate_member':
            rows[3][6] = rows[2][6]
        else:
            rows[2][1] = 'IF2613'
    with pytest.raises(ValueError):
        project('cffex-IF', two_header_body(edit=edit))


def test_header_is_not_removed_from_bytes_before_receipt_verification():
    body = two_header_body()
    original_receipt = receipt('cffex-IF', body)
    without_subheader = b'\r\n'.join(body.split(b'\r\n')[:1] + body.split(b'\r\n')[2:])
    with pytest.raises(ValueError, match='CONTEXT_BYTES_DIFFER'):
        c.normalize(without_subheader, original_receipt, cutoff=NOW)


def test_two_header_citic_missing_side_remains_unknown():
    def edit(rows):
        rows[3][9] = '其他空头会员'
    p = project('cffex-IF', two_header_body(edit=edit))
    assert p['totals']['citic_net_long_change'] is None
    assert p['totals']['citic_net_short_change'] is None
    assert not p['coverage']['citic_both_sides_all_returned_contracts']
