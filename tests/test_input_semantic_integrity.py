"""Source column identities and currency format; no network or investment claims."""
from copy import deepcopy
import json
import socket

from bs4 import BeautifulSoup
from pydantic import TypeAdapter, ValidationError
import pytest

from decision_kernel.primitives import CurrencyCode
from decision_kernel.runtime import industry_fundamentals as source

LABELS = (
    ('PMI', '生产', '新订单', '原材料库存', '从业人员', '供应商配送时间'),
    ('新出口订单', '进口', '采购量', '主要原材料购进价格', '出厂价格', '产成品库存', '在手订单', '生产经营活动预期'),
    ('商务活动', '新订单', '投入品价格', '销售价格', '从业人员', '业务活动预期'),
    ('新出口订单', '在手订单', '存货', '供应商配送时间'),
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError('semantic input test attempted networking')
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket, 'getaddrinfo', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)


def article(*, permute=None, merged=False):
    tables = []
    for i, labels in enumerate(LABELS):
        order = list(range(len(labels)))
        if permute == i:
            order[1], order[2] = order[2], order[1]
        columns = [labels[j] for j in order]
        width = len(labels) + 1
        unit = f'<tr><td colspan="{width}">单位： %</td></tr>'
        if merged and i == 0:
            header = ('<tr><td rowspan="2"></td><td rowspan="2">PMI</td>'
                      '<td colspan="5"></td></tr><tr>'
                      + ''.join(f'<th><p>{c}</p></th>' for c in columns[1:]) + '</tr>')
        else:
            header = '<tr><th></th>' + ''.join(f'<th>{c}</th>' for c in columns) + '</tr>'
        data = ''
        for month in (8, 9):
            data += f'<tr><td>2026年{month}月</td>'
            data += ''.join(f'<td>{40 + i + j + month}</td>' for j in order) + '</tr>'
        tables.append('<table>' + unit + header + data + '</table>')
    return BeautifulSoup('<div class="TRS_Editor">' + ''.join(tables) + '</div>', 'html.parser').div


@pytest.mark.parametrize('table_index', range(4))
@pytest.mark.parametrize('merged', [False, True])
def test_column_permutation_preserves_every_series(table_index, merged):
    baseline = source.pmi_tables(article(merged=merged))
    reordered = source.pmi_tables(article(permute=table_index, merged=merged))
    assert reordered == baseline
    assert len(reordered) == 24


def test_source_multiline_cells_keep_identity_and_index_units():
    page = article(merged=True)
    cell = page.find('th', string='原材料库存')
    cell.clear()
    cell.append(BeautifulSoup('<p>原材料</p><p> 库存</p>', 'html.parser'))
    assert source.pmi_tables(page) == source.pmi_tables(article())
    assert all(row['unit'] == '指数点' for row in source.pmi_tables(page))


@pytest.mark.parametrize('problem', ['duplicate', 'missing', 'foreign-label', 'unit', 'span-zero',
    'span-overflow', 'span-overlap', 'extra-cell', 'bad-number', 'footer', 'nested', 'wrong-table'])
def test_ambiguous_or_changed_pmi_shape_rejects(problem):
    page = article(merged=True)
    table = page.find('table')
    rows = table.find_all('tr')
    headers = rows[2].find_all('th')
    if problem == 'duplicate':
        headers[1].string = headers[0].get_text()
    elif problem == 'missing':
        headers[1].string = ''
        # A label in a data row or note must not qualify a missing header.
        table.append(BeautifulSoup('<tr><td colspan="7">新订单</td></tr>', 'html.parser'))
    elif problem == 'foreign-label':
        headers[1].string = '新订单同比增速'
    elif problem == 'unit':
        rows[0].td.string = '单位：亿元'
    elif problem == 'span-zero':
        rows[1].td['rowspan'] = '0'
    elif problem == 'span-overflow':
        rows[1].td['rowspan'] = '99'
    elif problem == 'span-overlap':
        rows[1].find_all('td')[1]['rowspan'] = '1'
        rows[2].find_all('th')[0]['colspan'] = '2'
        rows[1].find_all('td')[2]['rowspan'] = '2'
    elif problem == 'extra-cell':
        rows[-1].append(BeautifulSoup('<td>51</td>', 'html.parser').td)
    elif problem == 'bad-number':
        rows[-1].find_all('td')[2].string = '50亿元'
    elif problem == 'footer':
        rows[-1].td.string = '未知月份'
    elif problem == 'nested':
        rows[0].td.append(BeautifulSoup('<table><tr><td>x</td></tr></table>', 'html.parser'))
    else:
        page.find_all('table')[2].extract()
    with pytest.raises(ValueError):
        source.pmi_tables(page)


def test_invalid_pmi_isolated_from_other_source_family():
    page = article()
    page.find('th', string='新订单').string = '新订单同比'
    records = [
        {'id': 'nbs-pmi', 'status': 'CAPTURED', 'file': 'pmi', 'title': '2026年9月中国采购经理指数运行情况'},
        {'id': 'logistics', 'status': 'CAPTURED', 'file': 'logistics'},
    ]
    payload = {'success': True, 'code': 0, 'result': {'data': [
        {'REPORT_DATE': '2026-09-01', 'INDICATOR_VALUE': '50.9'},
        {'REPORT_DATE': '2026-08-01', 'INDICATOR_VALUE': '50.4'}]}}
    report = source.normalize(records, {'pmi': str(page).encode(), 'logistics': json.dumps(payload).encode()},
                              cutoff='2026-10-08T00:00:00+00:00')
    assert report['sections']['nbs-pmi']['status'] == 'SOURCE_SHAPE_OR_PERIOD_REJECTED'
    assert report['sections']['logistics']['status'] == 'OBSERVATIONS_AVAILABLE'
    assert report['coverage']['available_families'] == 1
    assert report['status'] == 'PARTIAL'
    assert not report['automatic_research_routing']


@pytest.mark.parametrize('value', ['人民币', 'ÄBC', 'ｕｓｄ', 'ßu', 'uſd', 'US1', 'US', 'USDD', '', 'U S', 'USD\x00'])
def test_currency_rejects_non_ascii_or_non_letter_identity(value):
    with pytest.raises(ValidationError):
        TypeAdapter(CurrencyCode).validate_python(value)


@pytest.mark.parametrize('value, expected', [('usd', 'USD'), (' Cny ', 'CNY'), ('JPY', 'JPY'),
                                           ('HKD', 'HKD'), ('zzz', 'ZZZ')])
def test_currency_preserves_ascii_normalization_not_registry_validation(value, expected):
    assert TypeAdapter(CurrencyCode).validate_python(value) == expected
