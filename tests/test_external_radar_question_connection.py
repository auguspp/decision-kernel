"""Synthetic integration with existing company reading and original Question gates."""
from copy import deepcopy

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import reviewed_question_input as qin
from decision_kernel.runtime import external_radar_observations as obs
from test_reviewed_question_input import fixture, arguments
from test_radar_company_reading import composed, compose
from test_external_radar_observations import no_network, news_pair, CUTOFF


@pytest.mark.parametrize('kind', [obs.NEWS_KIND, obs.INDUSTRY_KIND])
def test_authored_external_origin_uses_original_prepare_without_execution(kind):
    parts = fixture()
    parts[-1]['origins'][0]['kind'] = kind
    result = qin.prepare(**arguments(parts))
    assert result['status'] == 'QUESTION_INPUT_PREPARED_NOT_EXECUTED'
    assert result['research_execution_allowed'] is False
    assert result['funnel_invoked'] is False and result['formal_research_budget_used'] == 0
    assert result['investment_authority'] == 'NONE' and result['remote_writes'] == 0


@pytest.mark.parametrize('kind', [obs.NEWS_KIND, obs.INDUSTRY_KIND])
@pytest.mark.parametrize('damage', ['context-only', 'required-body-missing', 'changed-question'])
def test_new_origin_name_never_bypasses_question_or_source_gates(kind, damage):
    parts = fixture(); q = parts[-1]
    q['origins'][0]['kind'] = kind
    if damage == 'context-only':
        q['origins'][0]['qualification'] = 'CONTEXT_ONLY'
    elif damage == 'required-body-missing':
        parts[1]['reads'][0]['succeeded'] = False
    else:
        q['question'] = 'A different question from the bound packet'
    with pytest.raises(ValueError):
        qin.prepare(**arguments(parts))


def test_company_context_reuses_validated_reading_without_changing_old_projection():
    company = compose(composed())
    company['projection']['companies'][0]['source_names'] = ['SyntheticCompanyA']
    company['projection_hash'] = canonical_hash(company['projection'])
    original = deepcopy(company)
    captures = [news_pair(items=[{'id': 1, 'title': 'SyntheticCompanyA reports a product trial',
                                 'url': 'https://www.cls.cn/detail/1'}])]
    result = obs.news_context(captures, cutoff=CUTOFF, company_reading=company)
    rows = result['projection']['companies']
    assert company == original and len(rows) == 1
    assert rows[0]['thscode'] == company['projection']['companies'][0]['thscode']
    assert rows[0]['research'] == company['projection']['companies'][0]['research']
    assert rows[0]['qualification'] == 'CONTEXT_ONLY' and rows[0]['question_status'] == 'NOT_FORMED'
    assert result['projection']['company_reading_hash'] == company['projection_hash']
    obs.verify_news(result, captures, cutoff=CUTOFF, company_reading=company)
    company['projection']['companies'][0]['source_names'] = ['ChangedWithoutNewSource']
    with pytest.raises(ValueError):
        obs.news_context(captures, cutoff=CUTOFF, company_reading=company)


def test_same_name_in_two_saved_securities_is_not_silently_resolved():
    company = compose(composed())
    for row in company['projection']['companies'][:2]:
        row['source_names'] = ['AmbiguousSyntheticName']
    company['projection_hash'] = canonical_hash(company['projection'])
    captures = [news_pair(items=[{'id': 1, 'title': 'AmbiguousSyntheticName product update',
                                 'url': 'https://www.cls.cn/detail/1'}])]
    rows = obs.news_context(captures, cutoff=CUTOFF, company_reading=company)['projection']['companies']
    assert len(rows) == 2 and len({r['thscode'] for r in rows}) == 2
    assert all(not r['automatic_admission'] and r['business_linkage'] == 'NOT_ESTABLISHED' for r in rows)
