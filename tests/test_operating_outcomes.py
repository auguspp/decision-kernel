"""Source-bound operating comparison contracts; fixtures do not certify markets."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path

import pytest

from decision_kernel.runtime import operating_outcomes as o

ROOT = Path(__file__).resolve().parents[1]
AT = '2026-10-06T05:45:00+00:00'


def retained():
    entry = json.loads((ROOT/'decision_inputs/d-operating-outcomes.json').read_bytes())['cases'][0]
    files = {k: (ROOT/v['path']).read_bytes() for k,v in entry['sources'].items()}
    return entry, files


def pair():
    e, files = retained()
    row = o.review(e, files, checked_at=AT)['rows'][0]
    return row['forecast'], row['actual']


def changed(entry, files, key, edit):
    entry, files = deepcopy(entry), dict(files)
    value = o.loads(files[key]); edit(value)
    raw = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode(); files[key] = raw
    spec = entry['sources'][key]
    spec.update(bytes=len(raw), sha256=o.model.sha256(raw), git_blob=o.model.blob_sha(raw))
    return entry, files


def test_actual_retained_review_matches_four_old_differences_without_scoring_ai():
    e, files = retained(); before = deepcopy(e)
    out = o.review(e, files, checked_at=AT)
    assert out['status'] == 'RETAINED_REVIEW_COMPARED'
    assert [Decimal(r['comparison']['difference']) for r in out['rows']] == [
        Decimal('4229'), Decimal('1'), Decimal('918'), Decimal('2.42')]
    assert out['rows'][0]['comparison']['actual_minus_upper'] == '3229'
    assert out['rows'][3]['comparison']['actual_minus_upper'] == '1.42'
    assert out['company_guidance_events'] == 1 and out['metric_count'] == 4
    assert out['independent_sample_count'] is None
    assert all(out[k] is None for k in ('ai_forecast_error','brier_score','win_rate','method_effectiveness','normalized_eps_floor'))
    assert all(r['comparison']['error_owner'] == o.ROLE for r in out['rows'])
    assert out['source_acquisition_limits']['raw_official_html_obtained'] is False
    assert out['automatic_method_change'] is False and e == before


@pytest.mark.parametrize('key,value', [
    ('subject','DIFFERENT'), ('event_id','DIFFERENT_EVENT'), ('period','FY2026'),
    ('basis','GAAP'), ('unit','USD_billion'), ('share_basis','BASIC_EPS'),
])
def test_incompatible_identity_is_not_a_numeric_result(key, value):
    f,a = pair(); a[key]=value
    out = o.compare_pair(f,a,checked_at=AT)
    assert out['status'] == 'INCOMPARABLE_BASIS' and out['difference'] is None
    assert key in out['mismatched_fields']


def test_unavailable_actual_and_missing_value_are_not_zero():
    f,a = pair()
    assert o.compare_pair(f,None,checked_at=AT)['status'] == 'ACTUAL_NOT_RETAINED'
    a['value'] = None
    out = o.compare_pair(f,a,checked_at=AT)
    assert out['status'] == 'VALUE_NOT_RETAINED' and out['difference'] is None


def test_unmature_and_later_review_keep_distinct_clocks():
    f,a = pair()
    out = o.compare_pair(f,a,checked_at='2026-09-20T00:00:00Z')
    assert out['status'] == 'RESULT_NOT_YET_MATURE_OR_PUBLISHED' and out['difference'] is None
    out = o.compare_pair(f,a,checked_at='2026-10-02T00:00:00Z')
    assert out['status'] == 'REVIEW_NOT_YET_RETAINED_AT_CUTOFF' and out['difference'] is None


def test_zero_or_negative_forecast_is_not_epsilon_or_sign_inversion():
    f,a = pair(); f['value']='0'; f['half_width']=None; a['value']='-3'
    out = o.compare_pair(f,a,checked_at=AT)
    assert out['difference']=='-3' and out['relative_to_absolute_forecast'] is None
    assert out['relative_denominator_status']=='ZERO_FORECAST_UNDEFINED'
    f['value']='-10'; a['value']='-8'
    assert o.compare_pair(f,a,checked_at=AT)['relative_to_absolute_forecast']=='0.2'


@pytest.mark.parametrize('actual,position', [('48999','BELOW'),('49000','WITHIN'),('51000','WITHIN'),('51001','ABOVE')])
def test_range_endpoints_are_inclusive_not_probability_coverage(actual, position):
    f,a = pair(); a['value']=actual
    out = o.compare_pair(f,a,checked_at=AT)
    assert out['range_position']==position and out['probability_score'] is None


@pytest.mark.parametrize('key,value', [('value','NaN'),('value','1e9'),('value',True),('half_width','-1')])
def test_invalid_numeric_input_is_rejected(key,value):
    f,a=pair(); f[key]=value
    with pytest.raises(ValueError): o.compare_pair(f,a,checked_at=AT)


def test_full_packet_rejects_future_review_without_exposing_values():
    e,files=retained()
    with pytest.raises(ValueError, match='after cutoff'):
        o.review(e,files,checked_at='2026-10-02T00:00:00Z')


def test_source_byte_change_is_not_a_new_accepted_revision():
    e,files=retained(); files['inputs']+=b' '
    with pytest.raises(ValueError,match='bytes differ'): o.review(e,files,checked_at=AT)


def test_three_inputs_cannot_come_from_different_archives():
    e,files=retained();e['sources']['notes']['ref']='a'*40
    with pytest.raises(ValueError,match='splice archives'):o.review(e,files,checked_at=AT)


def test_changed_period_stays_incomparable_without_hiding_other_metadata():
    e,files=retained()
    e,files=changed(e,files,'inputs',lambda p:p['actual'].update(period='FY2026'))
    out=o.review(e,files,checked_at=AT)
    assert out['comparable_metrics']==0 and out['status']=='RETAINED_REVIEW_WITH_COMPARISON_GAPS'
    assert all(r['comparison']['difference'] is None for r in out['rows'])


def test_notes_and_input_published_clock_must_agree():
    e,files=retained()
    e,files=changed(e,files,'inputs',lambda p:p['guide'].update(published_at='2026-09-30T20:01:00+00:00'))
    with pytest.raises(ValueError,match='clock binding'):o.review(e,files,checked_at=AT)


def test_source_declared_authority_cannot_promote_comparison():
    e,files=retained()
    e,files=changed(e,files,'inputs',lambda p:p['qualification'].update(investment_authority='TRADE'))
    with pytest.raises(ValueError,match='authority'):o.review(e,files,checked_at=AT)


def test_excerpt_must_exist_and_decimal_context_cannot_change_the_output():
    e,files=retained(); first=o.review(e,files,checked_at=AT)
    with localcontext() as ctx:
        ctx.prec=5
        assert o.review(e,files,checked_at=AT)==first
    e['excerpts'].append('unsupported new conclusion')
    with pytest.raises(ValueError):o.review(e,files,checked_at=AT)


def test_render_preserves_source_caveats_and_does_not_call_company_error_ai_error():
    e,files=retained();item=o.review(e,files,checked_at=AT)
    text=o.render({'items':[item]})
    assert '公司指引、研究者预测和人的决定分开' in text
    assert '公司整体跨周期盈利底部' in text
    assert '费用压力可以并存' in text
    assert '原审阅留存' in text and '不' in text


def test_different_metrics_never_compare_just_because_units_match():
    forecast, actual = pair()
    actual['metric'] = 'operating_expenses'
    result = o.compare_pair(forecast, actual, checked_at=AT)
    assert result['status'] == 'INCOMPARABLE_BASIS'
    assert result['mismatched_fields'] == ['metric'] and result['difference'] is None


def test_company_guidance_cannot_be_relabelled_as_research_forecast():
    forecast, actual = pair()
    forecast['role'] = 'RESEARCH_FORECAST'
    with pytest.raises(ValueError, match='roles'):
        o.compare_pair(forecast, actual, checked_at=AT)


def test_review_clock_before_report_publication_is_invalid():
    forecast, actual = pair()
    actual['retained_review_at'] = '2026-09-29T00:00:00Z'
    with pytest.raises(ValueError, match='temporal'):
        o.compare_pair(forecast, actual, checked_at=AT)
