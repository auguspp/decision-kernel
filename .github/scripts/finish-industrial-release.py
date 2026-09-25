from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('prepare-industrial-release.py')))
p=Path('src/decision_kernel/runtime/industry_fundamentals.py')
s=p.read_text()
s=s.replace("('tb_NowDramSpotPrice', 'DRAM'), ('tb_NowFlashSpotPrice', 'NAND')", "('tb_NationalDramSpotPrice', 'DRAM'), ('tb_NationalFlashSpotPrice', 'NAND')")
# Normalize duplicate presentation of the exact same metric (NBS finance totals)
# while rejecting conflicting values, never averaging or arbitrary last wins.
s=s.replace("    return output, {'publication_at': publication, 'release_title': title,", "    unique = {}\n    for item in output:\n        m.check(item['id'] not in unique or unique[item['id']] == item, 'official same-period metric conflict')\n        unique[item['id']] = item\n    return list(unique.values()), {'publication_at': publication, 'release_title': title,")
s=s.replace("    if family in {'nbs-industry', 'nbs-energy'}:\n", "    if family == 'nbs-energy':\n        output = energy_fields(content, period)\n    elif family == 'nbs-industry':\n",1)
s=s.replace("        m.check(len(output) >= 3, 'PMI source field shape changed')", "        historical = pmi_tables(article)\n        if historical:\n            output = historical\n        m.check(len(output) >= 3, 'PMI source field shape changed')")
helper=r'''
def energy_fields(content, period):
    # Explicit quantities in the official energy release; first monthly and YTD
    # paragraphs remain different bases. No image reading or guessed values.
    output = []
    patterns = (
        ('原煤产量', r'原煤产量'), ('原油产量', r'原油产量'),
        ('原油加工量', r'原油加工量'), ('天然气产量', r'天然气产量'),
        ('发电量', r'发电量'),
    )
    for label, pattern in patterns:
        matches = list(re.finditer(pattern + r'([\d.]+)(亿吨|万吨|亿立方米|亿千瓦时)[，,]同比(增长|下降)([\d.]+)%', content))
        for match in matches[:2]:
            prefix = content[max(0,match.start()-45):match.start()]
            cumulative = bool(re.search(r'1[—－–-]\d{1,2}月份?', prefix))
            point = {'period': period, 'value': number(match[1]),
                     'reported_yoy_pct': str(Decimal(match[4]) * (-1 if match[3]=='下降' else 1))}
            if cumulative: point['period_start'] = period[:4] + '-01'
            output.append(series('nbs-energy', label, match[2],
                'YEAR_TO_DATE_OUTPUT' if cumulative else 'MONTHLY_OUTPUT', [point]))
    m.check(len(output) >= 5, 'official energy quantity fields missing')
    return output


def pmi_tables(article):
    specs = (
        ('制造业', ('PMI','生产','新订单','原材料库存','从业人员','供应商配送时间')),
        ('制造业', ('新出口订单','进口','采购量','主要原材料购进价格','出厂价格','产成品库存','在手订单','生产经营活动预期')),
        ('非制造业', ('商务活动','新订单','投入品价格','销售价格','从业人员','业务活动预期')),
        ('非制造业', ('新出口订单','在手订单','存货','供应商配送时间')),
    )
    tables = article.find_all('table')
    if not tables: return []
    m.check(len(tables) == 4, 'PMI table inventory changed')
    output = []
    for table_, (scope, labels) in zip(tables, specs):
        header = text(table_.get_text())
        m.check(all(label in header for label in labels), 'PMI table headings changed')
        buckets = {label: [] for label in labels}
        for row in rows(table_):
            match = re.fullmatch(r'(20\d{2})年(\d{1,2})月', row[0]) if row else None
            if not match: continue
            m.check(len(row) == len(labels)+1, 'PMI table row width changed')
            period = date(int(match[1]),int(match[2]),1).strftime('%Y-%m')
            for label, cell in zip(labels,row[1:]):
                m.check(number(cell) is not None, 'PMI numeric observation missing')
                buckets[label].append({'period': period,'value': number(cell)})
        m.check(all(2 <= len(v) <= 24 for v in buckets.values()), 'PMI monthly history bound')
        output += [series('nbs-pmi',scope+'/'+label,'指数点','MONTHLY_DIFFUSION_INDEX',points)
                   for label,points in buckets.items()]
    return output

'''
s=s.replace('\ndef official(family, raw, title):',helper+'\ndef official(family, raw, title):')
# Bind exact request contracts again during offline replay, independently of hash.
helper=r'''
def validate_source_record(record):
    key = record['id']
    if 'url' not in record:
        m.check(key in FAMILIES and record['status'] == 'NOT_FOUND_IN_BOUNDED_RELEASE_CATALOG', 'invalid missing source receipt')
        return
    url, params = record['url'], record.get('params')
    if key.startswith('catalog-'):
        index = int(key.removeprefix('catalog-'))
        m.check(0 <= index <= 2 and url == (NBS,NBS+'index_1.html',NBS+'index_2.html')[index] and params == {}, 'catalog receipt differs')
    elif key in PROFILES:
        m.check(re.search(PROFILES[key],record.get('title') or '') is not None and params == {}, 'official release contract differs')
        m.check(url.startswith(NBS) and '/t20' in url, 'official release source differs')
    elif key in EM_SPECS:
        expected = {**EM_SPECS[key], 'pageNumber':'1','pageSize':'30','sortColumns':'REPORT_DATE',
                    'sortTypes':'-1','source':'WEB','client':'WEB'}
        m.check(url == EM and params == expected, 'statistical series request identity differs')
    elif key == 'cpca':
        m.check(url == CPCA and params == {'charttype':'1'}, 'CPCA category request differs')
    elif key == 'memory':
        m.check(url == MEMORY and params == {}, 'memory source request differs')
    else:
        raise ValueError('unreviewed source record')

'''
s=s.replace('\ndef replay(files, identity, *, cutoff):',helper+'\ndef replay(files, identity, *, cutoff):')
s=s.replace("    for record in receipt['records']:\n", "    m.check(len({r['id'] for r in receipt['records']}) == len(receipt['records']), 'duplicate industrial request identity')\n    for record in receipt['records']:\n        validate_source_record(record)\n",1)
s=s.replace("                        status = response.status_code\n", "                        status = response.status_code\n                        record['http_status'] = status\n",1)
# Human-readable short facts first; original detailed numbers remain in JSON.
s=s.replace("    if comparison:\n        kinds = {}", "    featured = [x for x in report['series'] if x['basis'] != 'YEAR_TO_DATE_OUTPUT' and any(k in x['label'] for k in ('新订单','原材料库存','在手订单','规上工业/','狭义乘用车/','集成电路','工业机器人','BDTI','物流业景气'))]\n    lines += ['## 本次可读线索（不解释原因）', '']\n    for item in featured[:24]:\n        last = item['latest']; prior = item['points'][-2] if len(item['points']) > 1 else None\n        delta = {k:v for k,v in last.items() if k.startswith(('reported_', 'computed_'))}\n        lines.append('- ' + esc(item['label']) + '：' + esc(last['period']) + '，' + esc(last['value']) + ' ' + esc(item['unit']) + ('；前期 ' + esc(prior['period']) + ' ' + esc(prior['value']) if prior else '') + ('；' + esc(delta) if delta else ''))\n    lines += ['', '全部序列在下面逐源列出；首页不是采集或研究准入范围。', '']\n    if comparison:\n        kinds = {}",1)
p.write_text(s)
p=Path('tests/test_industry_fundamentals.py'); p.write_text(p.read_text().replace('tb_NowFlashSpotPrice','tb_NationalFlashSpotPrice'))
# Additional body shape observed in live NBS energy release, not a fabricated table.
p.write_text(p.read_text()+r'''

def test_official_energy_quantities_use_monthly_and_cumulative_periods():
    title='2026年8月份能源生产情况'
    prose='8月份，规上工业原煤产量3.6亿吨，同比下降7.7%。1—8月份，规上工业原煤产量30.6亿吨，同比下降3.3%。8月份，规上工业原油产量1843万吨，同比增长0.8%。1—8月份，规上工业原油产量14500万吨，同比增长0.9%。8月份，规上工业天然气产量200亿立方米，同比增长3.1%。8月份，规上工业发电量9000亿千瓦时，同比增长4.1%。'
    values,_=s.official('nbs-energy',page(title,prose),title)
    assert len(values)==6
    assert values[0]['basis']=='MONTHLY_OUTPUT'
    assert values[1]['basis']=='YEAR_TO_DATE_OUTPUT'
    assert values[0]['latest']['reported_yoy_pct']=='-7.7'


def test_same_provider_other_series_cannot_substitute_for_requested_logistics():
    record={'id':'logistics','url':s.EM,'params':{**s.EM_SPECS['logistics'],'pageNumber':'1','pageSize':'30','sortColumns':'REPORT_DATE','sortTypes':'-1','source':'WEB','client':'WEB'},'status':'CAPTURED'}
    s.validate_source_record(record)
    record['params']['filter']='(INDICATOR_ID="OTHER")'
    with pytest.raises(ValueError): s.validate_source_record(record)
''')
