"""Headline counts are derived context, never source, author or event acceptance."""
from copy import deepcopy
import json

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import news_daily_reading as r
from test_news_daily import no_network


def history(rows):
    # Minimal private-helper input only. Native custody is exercised below via ready().
    p = {'observations': rows, 'status': 'ROLLING_HISTORY_LIMITED',
         'window_start': '2026-10-05T12:00:00Z', 'generated_at': '2026-10-06T06:00:00Z',
         'retained_since': '2026-10-05T15:00:00Z',
         'coverage': {'observation_count': len(rows), 'maximum_capture_gap_seconds': 7200,
                      'complete_news_coverage': False, 'source_gap_capture_count': 1},
         'losses': [{'kind': 'PREDECESSOR_GAP', 'count': 1}]}
    return {'projection': p, 'projection_hash': canonical_hash(p)}


def entry(title='same title', source='cls', article='a', version='v1', count=1):
    return {'observation': {'title': title, 'source_id': source, 'article_id': article,
                           'version_id': version}, 'seen_capture_count': count,
            'first_seen_at': '2026-10-05T16:00:00Z', 'last_seen_at': '2026-10-06T01:00:00Z'}


def test_counts_separate_polling_versions_articles_channels_and_titles():
    h = history([entry(count=4), entry(source='jin10', article='b', version='v2', count=2),
                 entry(version='v3'), entry(title='other title', article='c', version='v4')])
    before = deepcopy(h); p = r._headline_repetition(h)
    assert h == before and p['source_history_hash'] == h['projection_hash']
    assert (p['observed_version_count'], p['observed_article_count'], p['distinct_title_count']) == (4, 3, 2)
    assert p['capture_appearance_count'] == 8
    assert p['repeat_title_group_count'] == p['cross_source_repeat_group_count'] == 1
    group = p['repeat_title_groups'][0]
    assert group['version_count'] == 3 and group['article_count'] == 2
    assert group['source_ids'] == ['cls', 'jin10']
    assert p['multiple_version_articles'] == [{'article_id': 'a', 'version_ids': ['v1', 'v3']}]
    assert p['origin_independence'] == 'NOT_ESTABLISHED'
    assert p['author_count'] is p['semantic_disagreement'] is p['crowding_score'] is None
    assert p['coverage'] == h['projection']['coverage'] and p['losses'] == h['projection']['losses']
    p['coverage']['maximum_capture_gap_seconds'] = 0
    assert h == before


def test_same_version_reobserved_is_not_a_repeated_title_group():
    p = r._headline_repetition(history([entry(count=12)]))
    assert p['capture_appearance_count'] == 12 and p['observed_article_count'] == 1
    assert p['repeat_title_groups'] == [] and p['repeat_title_group_count'] == 0
    assert p['status'] == 'NO_EXACT_REPETITION_IN_RETAINED_WINDOW'


def test_same_article_publication_claim_versions_are_not_independent_sources():
    p = r._headline_repetition(history([entry(), entry(version='v2')]))
    assert p['repeat_title_group_count'] == 1 and p['cross_source_repeat_group_count'] == 0
    assert p['repeat_title_groups'][0]['article_count'] == 1


@pytest.mark.parametrize('second', ['demand falls', 'demand rises 10%', 'DEMAND rises', 'demand rises!'])
def test_polarity_numbers_case_punctuation_are_not_fuzzy_merged(second):
    p = r._headline_repetition(history([entry('demand rises'), entry(second, version='v2')]))
    assert p['distinct_title_count'] == 2 and p['repeat_title_groups'] == []


def test_only_whitespace_is_collapsed_and_original_text_is_preserved():
    h = history([entry('demand\n  rises'), entry(' demand\trises ', version='v2')])
    before = deepcopy(h); p = r._headline_repetition(h)
    assert p['distinct_title_count'] == 1 and h == before


def test_empty_window_does_not_create_absence_of_news_or_consensus():
    p = r._headline_repetition(history([]))
    assert p['observed_version_count'] == 0 and p['repeat_title_groups'] == []
    assert p['crowding_score'] is None and p['coverage']['complete_news_coverage'] is False
    assert p['community_post_coverage'] == 'NOT_CAPTURED_BY_THE_SEVEN_NEWS_WINDOWS'


def test_ordering_and_render_limit_do_not_change_full_group_denominator():
    rows = [entry(title=f'title {i}', article=f'a{i}', version=f'v{i}-{j}') for i in range(12) for j in range(2)]
    first = r._headline_repetition(history(rows))
    second = r._headline_repetition(history(list(reversed(rows))))
    # Input hash records original index order; derived groups/order do not depend on it.
    assert first['repeat_title_groups'] == second['repeat_title_groups']
    text = '\n'.join(r._render_repetition(first, history(rows)))
    assert sum(line.startswith('- ') for line in text.splitlines()) == 10
    assert first['repeat_title_group_count'] == 12 and len(first['repeat_title_groups']) == 12


def test_normal_reader_exposes_context_without_an_extra_get(tmp_path, monkeypatch):
    from test_news_daily_reading import ready
    col, baseline, _, _, _ = ready(tmp_path, monkeypatch)
    before = deepcopy(baseline)
    out = r.attach(col, baseline)
    report = json.loads(col.files[r.REPORT]); p = report['projection']
    context = p['headline_repetition']
    assert context['observed_version_count'] == context['observed_article_count'] == 7
    assert context['distinct_title_count'] == context['cross_source_repeat_group_count'] == 1
    assert context['source_history_hash'] == p['history']['projection_hash']
    assert col.api.calls == 4 and baseline == before and out['lanes'] == baseline['lanes']
    assert '同标题复现' in col.files[r.DETAIL].decode()
    assert '<script>' not in col.files[r.DETAIL].decode()
    assert p['semantic_review'] == 'NOT_PERFORMED' and context['research_executions'] == 0
    p['headline_repetition']['author_count'] = 7
    report['projection_hash'] = canonical_hash(p)
    with pytest.raises(ValueError, match='headline context differs'):
        r.render(report)


def test_old_reading_without_new_context_keeps_its_render_contract(tmp_path, monkeypatch):
    from test_news_daily_reading import ready
    col, base, _, _, _ = ready(tmp_path, monkeypatch)
    r.attach(col, base); report = json.loads(col.files[r.REPORT])
    report['projection'].pop('headline_repetition')
    report['projection_hash'] = canonical_hash(report['projection'])
    text = r.render(report)
    assert '滚动18小时新闻索引' in text and '## 同标题复现' not in text
