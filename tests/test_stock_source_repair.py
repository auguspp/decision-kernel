"""Regressions for recorded prefixed titles, not fabricated issuer research."""
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.runtime import stock_research_sources as source

NOW = '2026-09-13T08:00:00+00:00'


def batch(title, ticker='600184'):
    row = CninfoAnnouncement('synthetic', ticker, 'synthetic-org', title, '',
        datetime.fromisoformat('2026-08-28T00:00:00+08:00'),
        'https://static.cninfo.com.cn/synthetic.PDF')
    return SimpleNamespace(stock_code=ticker, announcements=(row,))


@pytest.mark.parametrize('title,name', [
    ('北方光电股份有限公司2026年半年度报告', '光电股份'),
    ('和顺石油2026年半年度报告', '和顺石油'),
])
def test_observed_issuer_prefix_is_a_report_not_unavailable(title, name):
    report, selected = source.choose(batch(title), checked_at=NOW, issuer_name=name)
    assert report.title == title and selected == [report]


@pytest.mark.parametrize('title', [
    '关于2026年半年度报告', '董事会2026年半年度报告',
    '审计机构2026年半年度报告', '光电股份2026年半年度报告摘要',
    '光电股份2026年半年度报告（审计意见）', '光电股份2026年半年度报告的核查意见',
    '证券公司关于光电股份2026年半年度报告', '陌生简称2026年半年度报告',
    '光电股份2026年第一季度报告',
    '另一公司股份有限公司2026年半年度报告',
])
def test_auxiliary_or_unbound_short_name_is_not_full_report(title):
    with pytest.raises(ValueError, match='full annual or half-year'):
        source.choose(batch(title), checked_at=NOW, issuer_name='光电股份')


@pytest.mark.parametrize('title', [
    '2026年半年度报告', '2026年半年度报告（修订版）',
    '北方光电股份有限公司 2026年半年度报告（更正后）',
    '光电股份：2026年半年度报告',
])
def test_supported_complete_titles_keep_period_selection(title):
    report, _ = source.choose(batch(title), checked_at=NOW, issuer_name='光电股份')
    assert report.title == title
