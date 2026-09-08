"""Behavior contract: qualified changes stay discoverable, not a new detector.

Generic scenarios use the REAL state-entry selector, current breadth calculator
and composer. Their market inputs are synthetic, not a claimed real market run.
The frozen pre-change renderer is executed only for a presentation comparison;
its external result validator is stubbed, not used to certify state or replay.
"""
import copy
import json
from dataclasses import asdict, replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_json
from decision_kernel.runtime import sector_radar_daily as daily
from decision_kernel.runtime.sector_radar_discovery import render_sector_radar_discovery
from decision_kernel.runtime.sector_radar_shadow import (
    BROAD_881, GRANULAR_884, build_current_parent_link,
    compose_sector_radar_shadow, select_sector_radar_state_entries,
)
from test_sector_radar_audit import prohibit_network
from test_sector_radar_shadow import (
    PREVIOUS, SESSION, breadth, candidate, entries, membership, observation, snapshot,
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)


def payload(broad, granular, widths, composition):
    return json.loads(canonical_json({
        'market_session': SESSION, 'benchmark_thscode': '000300.SH',
        'broad_entries': asdict(broad), 'granular_entries': asdict(granular),
        'breadth_observations': [asdict(b) for b in widths],
        'composition': asdict(composition),
        'output_market_state_hash': 'a'*64,
        'event_ledger_update': {'event_ledger_hash': 'b'*64},
        'result_hash': 'c'*64,
        'human_attention_authority': 'NONE', 'investment_authority': 'NONE',
    }))


def scenario(count=8, budget=3):
    codes = [f'881{700+i:03d}.TI' for i in range(count)]
    # One ordinarily rising sector NEVER enters the detector's qualified set.
    universe = [*codes, '881999.TI']
    previous = snapshot(PREVIOUS, tuple(
        observation(c, '合成行业 '+c, PREVIOUS, rating_20=89, positive_run=4)
        for c in universe))
    current = snapshot(SESSION, tuple(
        observation(c, '合成行业 '+c, SESSION,
                    rating_20=95 if c in codes else 50, rank_20=str(i+1),
                    positive_run=5 if c in codes else 4)
        for i,c in enumerate(universe)))
    broad = select_sector_radar_state_entries(current=current, previous=previous)
    granular = entries(GRANULAR_884)
    widths = tuple(breadth(c.thscode, c.name, (f'600{700+i:03d}.SH',))
                   for i,c in enumerate(broad.candidates))
    composed = compose_sector_radar_shadow(
        broad_entries=broad, granular_entries=granular,
        breadth_observations=widths, parent_links=(), max_surfaced_groups=budget)
    return payload(broad, granular, widths, composed), composed


def legacy_summary(composition):
    source = (Path(__file__).parent/'fixtures/sector_discovery/legacy_summary_renderer.py.txt').read_text()
    scope = {'Decimal': Decimal, '_validate_result': lambda _: None}
    exec(compile('from __future__ import annotations\n'+source, 'frozen-legacy-renderer', 'exec'), scope)
    return scope['render_sector_radar_daily_summary'](SimpleNamespace(
        market_session=SESSION, composition=composition,
        output_market_state_hash='a'*64, event_ledger_hash='b'*64, result_hash='c'*64))


@pytest.mark.parametrize('count', [0, 1, 3, 4, 8, 12])
def test_qualified_market_change_must_remain_human_discoverable(count):
    report, composition = scenario(count)
    before = copy.deepcopy(report)
    text = render_sector_radar_discovery(report)
    assert report == before
    assert len(composition.all_groups) == count
    assert len(composition.surfaced_groups) == min(3,count)
    assert text.split('### 其他变化',1)[1].count('<details>') == max(0,count-3)
    assert f'本次识别 {count} 个合格变化组' in text
    for group in composition.all_groups:
        assert group.primary_candidate.thscode in text
        for leader in group.primary_breadth.leaders:
            assert leader.thscode in text
    assert '881999.TI' not in text  # An upward price is not detector qualification.
    assert text == render_sector_radar_discovery(report)


def test_old_compression_loses_five_of_eight_but_new_path_preserves_them():
    report, composition = scenario(8)
    old, new = legacy_summary(composition), render_sector_radar_discovery(report)
    assert '5 additional complete group(s)' in old
    for group in composition.surfaced_groups:
        assert group.primary_candidate.thscode in old
    for group in composition.omitted_groups:
        assert group.primary_candidate.thscode not in old
        assert group.primary_candidate.thscode in new
    for group in composition.all_groups:
        assert group.primary_breadth.leaders[0].thscode not in old
        assert group.primary_breadth.leaders[0].thscode in new


def test_zero_summary_budget_does_not_say_nothing_was_detected():
    report, _ = scenario(8, budget=0)
    text = render_sector_radar_discovery(report)
    assert '首页摘要 0 个；其他变化 8 个' in text
    assert text.count('<details>') == 8
    assert 'Nothing new qualified' not in text


def test_plain_rise_and_unchanged_qualified_state_do_not_create_discovery():
    report, _ = scenario(8)
    observations = tuple(observation(
        f'881{700+i:03d}.TI', f'行业{i}', SESSION,
        rating_20=95, positive_run=8) for i in range(8))
    previous = snapshot(PREVIOUS, tuple(replace(o, as_of_session=PREVIOUS) for o in observations))
    selected = select_sector_radar_state_entries(current=snapshot(SESSION, observations), previous=previous)
    assert not selected.candidates
    assert '881999.TI' not in render_sector_radar_discovery(report)


@pytest.mark.parametrize('mutation', ['drop', 'append_unqualified', 'front_four', 'authority', 'wrong_breadth'])
def test_lossy_or_unauthorized_projection_is_rejected(mutation):
    report, _ = scenario(8)
    c = report['composition']
    if mutation == 'drop':
        c['all_groups'].pop(); c['omitted_groups'].pop(); c['truncated_group_count'] -= 1
    elif mutation == 'append_unqualified':
        g = copy.deepcopy(c['all_groups'][-1]); g['group_key'] = '881999.TI'
        c['all_groups'].append(g); c['omitted_groups'].append(copy.deepcopy(g)); c['truncated_group_count'] += 1
    elif mutation == 'front_four':
        c['surfaced_groups'] = c['all_groups'][:4]; c['omitted_groups'] = c['all_groups'][4:]; c['truncated_group_count'] = 4
    elif mutation == 'authority':
        report['human_attention_authority'] = 'WAKE'
    else:
        for groups in (c['all_groups'], c['omitted_groups']):
            groups[-1]['primary_breadth']['market_session'] = '2000-01-01'
    with pytest.raises(ValueError):
        render_sector_radar_discovery(report)


def test_missing_company_explanation_remains_explicit_and_no_wake_or_llm_fill():
    report, _ = scenario(8)
    report['why'] = 'UNTRUSTED_PRICE_MEANS_PROFIT_GROWTH'
    text = render_sector_radar_discovery(report)
    assert 'UNTRUSTED_PRICE_MEANS_PROFIT_GROWTH' not in text
    for required in ('WHY = UNKNOWN', 'BUSINESS LINK = NOT ESTABLISHED',
                     'UNREVIEWED', 'NEXT QUESTION', 'BELIEF = NONE',
                     'HUMAN ATTENTION AUTHORITY = NONE', 'RESEARCH AUTHORITY = NONE',
                     'INVESTMENT AUTHORITY = NONE', 'NOT A RECOMMENDATION'):
        assert required in text
    assert '不自动发起 Research' in text and '非多日强势认证或推荐' in text


def test_sibling_driver_leaders_survive_and_parent_context_is_not_a_candidate():
    cs = tuple(candidate(f'884{710+i:03d}.TI', f'合成子行业{i}', GRANULAR_884) for i in range(2))
    widths = tuple(breadth(c.thscode,c.name,(f'600{710+i:03d}.SH',)) for i,c in enumerate(cs))
    parent = membership('881710.TI','合成父上下文',('600710.SH','600711.SH'))
    links = tuple(build_current_parent_link(
        parent=parent, child=membership(c.thscode,c.name,(f'600{710+i:03d}.SH',)))
        for i,c in enumerate(cs))
    broad, granular = entries(BROAD_881), entries(GRANULAR_884,cs)
    composed = compose_sector_radar_shadow(broad_entries=broad,granular_entries=granular,
        breadth_observations=widths,parent_links=links,max_surfaced_groups=0)
    assert len(composed.all_groups) == 1
    assert '881710.TI' not in {c.thscode for c in composed.all_candidates}
    text = render_sector_radar_discovery(payload(broad,granular,widths,composed))
    assert all(code in text for code in ('881710.TI','884710.TI','884711.TI','600710.SH','600711.SH'))
    assert '父行业可仅作上下文' in text


def test_source_names_cannot_inject_html_or_markdown_requests():
    report, _ = scenario(4)
    unsafe = '</summary><script>evil()</script>![x](https://invalid.example/image)'
    # Names are display-only data; bind the same name consistently throughout.
    def walk(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if k == 'name': value[k] = unsafe
                else: walk(v)
        elif isinstance(value,list):
            for v in value: walk(v)
    walk(report)
    text = render_sector_radar_discovery(report)
    assert '<script>' not in text and '![x](' not in text
    assert '&lt;script&gt;' in text
    assert text.count('</summary>') == 4


def test_existing_daily_summary_routes_to_new_view_without_mutating_result(monkeypatch):
    from test_sector_radar_daily import (
        BROAD_881 as broad_family, PRODUCED, candidate as daily_candidate,
        prepared_run, parent_hints, memberships_for_plan, market_points, empty_ledger,
    )
    _, prep = prepared_run(monkeypatch, broad_candidates=(
        daily_candidate('881101.TI','种植业与林业',broad_family),
        daily_candidate('881102.TI','养殖业',broad_family)))
    result = daily.finalize_sector_radar_daily_run(preparation=prep,parent_hints=parent_hints(),
        memberships=memberships_for_plan(prep.acquisition_plan),
        constituent_points=market_points(prep.market_session),event_ledger=empty_ledger(),
        produced_at=PRODUCED,max_surfaced_groups=1)
    before = daily.serialize_sector_radar_daily_result(result)
    summary = daily.render_sector_radar_daily_summary(result)
    assert daily.serialize_sector_radar_daily_result(result) == before
    assert summary == render_sector_radar_discovery(json.loads(before))
    assert '881101.TI' in summary and '881102.TI' in summary
    assert len(result.composition.surfaced_groups) == 1 and summary.split('### 其他变化',1)[1].count('<details>') == 1


def test_workflow_reuses_summary_file_without_a_new_trigger_or_acquisition():
    root = Path(__file__).resolve().parents[1]
    workflow = (root/'.github/workflows/sector-radar-shadow.yml').read_text()
    assert 'cat sector-radar-run/summary.md >> "$GITHUB_STEP_SUMMARY"' in workflow
    # This renderer cannot invoke network, tools, a provider, LLM or company loader.
    import ast
    source = (root/'src/decision_kernel/runtime/sector_radar_discovery.py').read_text()
    modules = {n.module for n in ast.walk(ast.parse(source)) if isinstance(n,ast.ImportFrom)}
    assert modules <= {'__future__','decimal','html'}
    assert not any(isinstance(n,ast.Import) for n in ast.walk(ast.parse(source)))
