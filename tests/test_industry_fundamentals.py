"""Synthetic inputs test contracts; separate live probes establish provider usability."""
from copy import deepcopy
import json
from datetime import datetime, timezone

import pytest

from decision_kernel.runtime import industry_fundamentals as s
from decision_kernel.runtime import industry_fundamentals_reading as r
from decision_kernel.runtime import current_state as m
from decision_kernel.identity import canonical_hash

AT = '2026-09-25T14:00:00+00:00'
ID = dict(repository=m.REPOSITORY, workflow=s.WORKFLOW, ref='refs/heads/main',
          event='workflow_dispatch', code_commit='a'*40, run_id=99, attempt=1, trigger_run_id=None)


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode()


def page(title, inner):
    return ('<html><body>2026/09/15 10:00<h1>'+title+'</h1><div class="TRS_Editor">'+inner+'</div></body></html>').encode()


def table(header, data):
    return '<table>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in [header, *data])+'</table>'


@pytest.mark.parametrize('raw,expected', [('−1.25%', '-1.25'), ('1,024.2', '1024.2'), ('…', None), ('-','None'), ('NaN', None), (True, None), (None,None)])
def test_number_is_finite_and_preserves_missing(raw, expected):
    if expected == 'None': expected = None
    assert s.number(raw) == expected


def test_json_duplicate_key_rejected():
    with pytest.raises(ValueError): s.decode(b'{"x":1,"x":2}')


def test_production_month_and_cumulative_are_distinct():
    title = '2026年8月份规模以上工业增加值增长5.2%'
    data = [[f'产品{i}(亿块)', 100+i, 25.5, 800+i, 26.1] for i in range(5)]
    raw = page(title, table(['同比增长','绝对量','同比增长(%)','绝对量','同比增长(%)'], data))
    result, context = s.official('nbs-industry', raw, title)
    assert len(result) == 10
    assert result[0]['latest']['period'] == '2026-08'
    assert result[0]['unit'] == '亿块'
    assert result[0]['basis'] == 'MONTHLY_OUTPUT'
    assert result[1]['basis'] == 'YEAR_TO_DATE_OUTPUT'
    assert result[1]['latest']['period_start'] == '2026-01'
    assert context['publication_at'] == '2026-09-15T10:00:00+08:00'


def test_reported_pmi_delta_is_points_not_pct_growth():
    title = '2026年8月中国采购经理指数运行情况'
    raw = page(title, '一、中国制造业采购经理指数运行情况 制造业采购经理指数（PMI）为49.8%，比上月上升0.6个百分点。生产指数为50.4%，比上月上升0.5个百分点。新订单指数为50.6%，比上月上升2.1个百分点。原材料库存指数为48.1%，比上月下降0.2个百分点。')
    result, _ = s.official('nbs-pmi', raw, title)
    order = next(x for x in result if x['label'].endswith('新订单指数'))
    assert order['latest']['reported_change_pp'] == '2.1'
    assert order['latest']['prior_value_derived_from_reported_change'] == '48.5'
    assert len(order['points']) == 1  # no fake independent historical point


def test_financial_flow_balance_and_turnover_days_are_not_conflated():
    title = '2026年1—7月份全国规模以上工业企业利润增长17.6%'
    data = [['总计',809230.7,6.5,687861.5,5.9,45820.6,17.6], ['制造业',703941.3,7,601300.5,6.5,34376,18.8]]
    raw = page(title, table(['分组','营业收入','亿元','营业成本','亿元','利润总额','亿元'], data)
        + '7月末，应收账款28.88万亿元，同比增长8.5%；产成品存货7.27万亿元，增长10.8%。产成品存货周转天数为21.3天，同比增加0.6天。')
    result, _ = s.official('nbs-profit',raw,title)
    assert len(result) == 9
    assert result[0]['basis'] == 'YEAR_TO_DATE_REPORTED'
    balance = next(x for x in result if x['label']=='规上工业/产成品存货')
    assert balance['basis'] == 'MONTH_END_BALANCE'
    assert balance['latest']['value']=='7.27'


def test_material_price_is_ten_day_and_currency_per_native_unit():
    title='2026年9月中旬流通领域重要生产资料市场价格变动情况'
    raw=page(title,table(['产品名称','单位','本期价格(元)','比上期价格涨跌','涨跌幅(%)'],[[f'品种{i}','吨',100+i,1,1] for i in range(10)]))
    values,_=s.official('nbs-goods',raw,title)
    assert values[0]['unit']=='元/吨'
    assert values[0]['latest']['period_start']=='2026-09-11'
    assert values[0]['latest']['period']=='2026-09-20'


def cpca():
    return encoded([{'dataList':[{'month':'7月','2025年':[10,10,10,10],'2026年':[11,12,13,14]},
                              {'month':'8月','2025年':[100,100,100,100],'2026年':[90,80,70,180]}]}]*2)


def test_car_year_keys_and_field_identity():
    values,_=s.cars(cpca())
    assert len(values)==8
    retail=next(x for x in values if x['label']=='狭义乘用车/零售')
    assert retail['unit']=='万辆' and retail['latest']['value']=='70'
    assert retail['latest']['computed_yoy_pct']=='-30.0'
    assert all('库存' not in x['label'] for x in values)


def em(value=50.9):
    return encoded({'success':True,'code':0,'result':{'data':[
        {'REPORT_DATE':'2026-08-01 00:00:00','INDICATOR_VALUE':value},
        {'REPORT_DATE':'2026-08-01 00:00:00','INDICATOR_VALUE':value},
        {'REPORT_DATE':'2026-07-01 00:00:00','INDICATOR_VALUE':50.4}]}})


def test_identical_monthly_mirror_rows_deduplicate_but_conflicts_reject():
    values,_=s.eastmoney('logistics',em())
    assert len(values[0]['points'])==2
    payload=json.loads(em()); payload['result']['data'][1]['INDICATOR_VALUE']=51
    with pytest.raises(ValueError,match='conflicting'):
        s.eastmoney('logistics',encoded(payload))


def test_memory_public_table_has_own_timestamp_and_unknown_currency():
    raw=b'<div class="tab_time">Last Update: Sep.14 2026 18:10 (GMT+8)</div><table><tr><th>Daily High</th><th>Session Average</th></tr><tbody id="tb_NowFlashSpotPrice"><tr><td>TLC 128Gb</td><td>12</td><td>10</td><td>12</td><td>10</td><td>11</td><td>-0.5%</td></tr><tr><td>TLC 256Gb</td><td>22</td><td>20</td><td>22</td><td>20</td><td>21</td><td>0%</td></tr></tbody></table>'
    result,_=s.memory(raw)
    assert result[0]['unit']=='UNKNOWN_SOURCE_CURRENCY'
    assert result[0]['latest']['period']=='2026-09-14T18:10:00+08:00'
    record={'id':'memory','status':'CAPTURED','file':'raw/memory.body'}
    normalized=s.normalize([record],{'raw/memory.body':raw},cutoff=AT)
    assert normalized['series'][0]['freshness']=='STALE_OR_DELAYED_SOURCE_PERIOD'


def test_source_failure_and_future_period_do_not_hide_other_families():
    future=json.loads(em()); future['result']['data'][0]['REPORT_DATE']='2099-08-01'
    records=[{'id':'cpca','status':'CAPTURED','file':'cpca'}, {'id':'logistics','status':'CAPTURED','file':'logistics'}]
    result=s.normalize(records,{'cpca':cpca(),'logistics':encoded(future)},cutoff=AT)
    assert result['status']=='PARTIAL' and result['sections']['cpca']['series_count']==8
    assert result['sections']['logistics']['status']=='SOURCE_SHAPE_OR_PERIOD_REJECTED'


def test_increment_revision_no_change_and_disappearance_are_distinct():
    first={'series':[s.series('logistics','LPI','点','MONTHLY',[{'period':'2026-08','value':'50.9'}])]}
    assert s.compare(first)['changes'][0]['kind']=='BASELINE_FIRST_SEEN'
    assert s.compare(first,deepcopy(first))['unchanged_count']==1
    revised=deepcopy(first); revised['series'][0]['latest']['value']='51.0'
    assert s.compare(revised,first)['changes'][0]['kind']=='SAME_PERIOD_REVISION'
    next_=deepcopy(first); next_['series'][0]['latest']['period']='2026-09'
    assert s.compare(next_,first)['changes'][0]['kind']=='NEW_STATISTICAL_PERIOD'
    missing=s.compare({'series':[]},first)
    assert len(missing['missing_previous_series'])==1


@pytest.mark.parametrize('url',['https://evil.example/a','https://www.stats.gov.cn.evil/a', 'http://127.0.0.1/', 'https://u:p@www.dramexchange.com/'])
def test_source_url_scope_is_not_document_authority(url):
    with pytest.raises(ValueError): s.allowed_url(url)


def test_catalog_uses_official_links_and_exact_release_title():
    raw='<a href="./202608/t20260831_1965154.html">2026年8月中国采购经理指数运行情况</a><a href="./202608/t20260831_1965155.html">解读2026年8月中国采购经理指数</a>'.encode()
    result=s.catalog(raw,s.NBS)
    assert list(result)==['nbs-pmi'] and len(result['nbs-pmi'])==1


def test_capture_replay_isolated_error_and_byte_tamper(tmp_path):
    calls=[]
    def get(url,params):
        calls.append((url,params))
        if url==s.CPCA: return 200,cpca()
        return 503,b'unavailable'
    value=s.capture(tmp_path/'new',ID,get=get,now=lambda:AT)
    files={str(p.relative_to(tmp_path/'new')):p.read_bytes() for p in (tmp_path/'new').rglob('*') if p.is_file()}
    report,receipt=s.replay(files,ID,cutoff=AT)
    assert report==value and value['coverage']['available_families']==1
    assert len(calls)<=s.MAX_REQUESTS and receipt['research_authority']=='NONE'
    files['raw/cpca.body']+=b' '
    with pytest.raises(ValueError,match='bytes changed'): s.replay(files,ID,cutoff=AT)


@pytest.mark.parametrize('field,value',[('ref','refs/heads/untrusted'),('event','pull_request'),('attempt',2),('repository','other/repo')])
def test_production_identity(field,value):
    bad={**ID,field:value}
    with pytest.raises(ValueError): s.validate_identity(bad)


def test_no_credentials_no_auto_research_or_investment():
    from pathlib import Path
    code=Path(s.__file__).read_text()
    assert 'secrets.' not in code and '/dispatches' not in code
    assert s.AUTHORITY['investment_authority']=='NONE'
    assert not s.AUTHORITY['automatic_research_routing']


def test_previous_report_reader_checks_exact_hash(tmp_path):
    observation={'version':s.VERSION,'series':[]}
    value={'observation':observation}; report={'projection':value,'projection_hash':canonical_hash(value)}
    raw=m.json_bytes(report)
    class API:
        def file(self,path,ref):
            assert path==r.REPORT and ref=='b'*40
            return raw
    class Collector:
        previous_commit='b'*40
        api=API()
        previous={'research':{'industry_fundamentals':{'details':{'json':{'read_path':r.REPORT,
            'bytes':len(raw),'sha256':m.sha256(raw),'git_blob':m.blob_sha(raw)}}}}}
    actual,status=r.previous(Collector())
    assert actual==value and status.startswith('EXACT_PREVIOUS_READING_')
