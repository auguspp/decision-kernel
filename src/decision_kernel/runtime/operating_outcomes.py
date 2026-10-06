"""Bounded operating-result comparisons, independent of prices and execution.

Reuse reviewed-comparison decimal/selection and canonical identity primitives.
A difference is arithmetic, not an economic verdict, probability or acceptance.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from html import escape
import json
import re

from decision_kernel.identity import canonical_hash
from . import current_state as model
from .research_comparison import number, selected, _unique_input

VERSION = 'reviewed-operating-outcomes-v1'
ROLE = 'COMPANY_GUIDANCE_NOT_CONSENSUS_OR_AI_FORECAST'
MAX_BYTES = 512 * 1024
COMMON = ('subject', 'event_id', 'metric', 'period', 'basis', 'currency', 'unit', 'share_basis')


def loads(raw):
    model.check(isinstance(raw, bytes) and 0 < len(raw) <= MAX_BYTES, 'outcome source byte bound')
    def nonfinite(value):
        raise ValueError('outcome nonfinite JSON')
    return json.loads(raw, object_pairs_hook=_unique_input, parse_constant=nonfinite)


def bound(raw, descriptor):
    model.check(isinstance(descriptor, dict) and isinstance(descriptor.get('ref'), str)
                and model.SHA.fullmatch(descriptor['ref']) and
                type(descriptor.get('bytes')) is int and 0 < descriptor['bytes'] <= MAX_BYTES,
                'outcome source descriptor')
    model.safe_path(descriptor['path'])
    model.check(isinstance(raw, bytes) and len(raw) == descriptor['bytes'] and
                model.sha256(raw) == descriptor['sha256'] and
                model.blob_sha(raw) == descriptor['git_blob'], 'outcome source bytes differ')


def compare_pair(forecast, actual, *, checked_at):
    """Source-normalized point/range pair; no pooled score or silent scale change."""
    now = model.clock(checked_at)
    result = {'status': 'ACTUAL_NOT_RETAINED', 'difference': None, 'absolute_difference': None,
              'relative_to_absolute_forecast': None, 'range_position': None,
              'actual_minus_upper': None, 'probability_score': None,
              'independent_forecast_sample': False}
    if actual is None:
        return result
    mismatch = [k for k in COMMON if forecast.get(k) != actual.get(k)
                or forecast.get(k) in (None, '', 'UNKNOWN')]
    if mismatch:
        return {**result, 'status': 'INCOMPARABLE_BASIS', 'mismatched_fields': mismatch}
    model.check(forecast['role'] == ROLE and actual['role'] == 'REPORTED_ACTUAL',
                'outcome roles differ')
    target = date.fromisoformat(actual['period_end'])
    model.check(target.isoformat() == actual['period_end'], 'outcome period end format')
    fp, ap = model.clock(forecast['published_at']), model.clock(actual['published_at'])
    recorded = model.clock(actual['retained_review_at'])
    model.check(fp < ap <= recorded and fp.date() <= target <= ap.date(), 'outcome temporal identity')
    if now.date() < target or now < ap:
        return {**result, 'status': 'RESULT_NOT_YET_MATURE_OR_PUBLISHED'}
    if now < recorded:
        return {**result, 'status': 'REVIEW_NOT_YET_RETAINED_AT_CUTOFF'}
    if forecast.get('value') is None or actual.get('value') is None:
        return {**result, 'status': 'VALUE_NOT_RETAINED'}
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        f, a = number(forecast['value']), number(actual['value'])
        diff = a - f
        out = {**result, 'status': 'COMPARABLE_RETAINED_VALUES',
               'difference': format(diff, 'f'), 'absolute_difference': format(abs(diff), 'f'),
               'relative_to_absolute_forecast': format(diff / abs(f), 'f') if f else None,
               'relative_denominator_status': 'ABSOLUTE_FORECAST' if f else 'ZERO_FORECAST_UNDEFINED',
               'error_owner': forecast['role'], 'unit': forecast['unit'],
               'approximate_forecast': forecast['approximate'],
               'knowledge': 'LATER_REVIEW_NOT_EX_ANTE_CAPTURE_PROOF',
               'source_precision': 'INHERITED_NOT_INCREASED_BY_DECIMAL_ARITHMETIC'}
        width = forecast.get('half_width')
        if width is not None:
            width = number(width)
            model.check(width >= 0, 'outcome negative half width')
            out.update(forecast_lower=format(f-width, 'f'), forecast_upper=format(f+width, 'f'),
                       actual_minus_upper=format(a-f-width, 'f'),
                       range_position='BELOW' if a < f-width else 'ABOVE' if a > f+width else 'WITHIN')
        return out


# The existing retained guide/actual layout has explicit global money/EPS units.
# Margin fields explicitly name fraction vs percent; conversion is only x100.
# This is not a parser for arbitrary issuer tables or a universal financial model.
METRICS = (
    ('revenue', '收入', 'revenue_mid', 'revenue', 'revenue_half_width', 'amount_unit', '1', False),
    ('gross_margin', '毛利率', 'gross_margin_fraction_approx', 'gross_margin_pct_reported', None,
     'PERCENTAGE_POINTS', '100', True),
    ('operating_expenses', '经营费用', 'operating_expenses_approx', 'operating_expenses', None,
     'amount_unit', '1', True),
    ('diluted_eps', '稀释EPS', 'eps_mid', 'eps', 'eps_half_width', 'eps_unit', '1', False),
)


def review(entry, source_files, *, checked_at):
    """Read an explicitly selected retained review; do not execute archived code."""
    model.check(entry['layout'] == 'RETAINED_GUIDANCE_ACTUAL_V1' and
                entry['comparator_role'] == ROLE, 'outcome selected layout or role')
    model.check(re.fullmatch(r'[A-Z0-9.:-]{1,40}', entry['subject']) is not None,
                'outcome subject identity')
    model.check(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', entry['id']) is not None and
                isinstance(entry['event_id'], str) and 0 < len(entry['event_id']) <= 100,
                'outcome selection identity')
    descriptors = entry['sources']
    model.check(set(descriptors) == {'inputs', 'notes', 'review'}, 'outcome three retained files')
    roots = set()
    for key, spec in descriptors.items():
        bound(source_files[key], spec)
        roots.add((spec['ref'], spec['path'].rsplit('/', 1)[0]))
    model.check(len(roots) == 1, 'outcome retained review cannot splice archives')
    source, notes = loads(source_files['inputs']), loads(source_files['notes'])
    model.check(source['case'] == entry['input_case'] and source['comparison'] == entry['comparison'],
                'outcome selected case differs')
    q = source['qualification']
    model.check(q['investment_authority'] == 'NONE' and q['cardinal_probability'] is None and
                q['new_human_decision'] is False and q['original_human_decision_modified'] is False and
                q['normalized_eps_floor'] is None and type(q['market_requests']) is int and q['market_requests'] == 0,
                'outcome retained authority differs')
    model.check(q['source_custody'] == entry['source_custody'], 'outcome source qualification differs')
    g, a = source['guide'], source['actual']
    model.check(g['period'] == entry['expected_period'] and g['basis'] == entry['expected_basis'] and
                source['currency'] == entry['expected_currency'], 'outcome selected period or basis differs')
    public = notes['public_sources']
    model.check(isinstance(public, list) and 0 < len(public) <= 16 and
                len({s['id'] for s in public}) == len(public), 'outcome source identities')
    by_id = {s['id']: s for s in public}
    model.check(g['source_id'] != a['source_id'], 'outcome forecast and actual source roles')
    for record in (g, a):
        declared = by_id[record['source_id']]
        model.check(record['published_at'] == declared['published_at'], 'outcome published clock binding')
    model.check(a['period_end'] == by_id[a['source_id']]['period_end'], 'outcome fiscal end binding')
    model.check(source['currency'] in ('USD', 'CNY') and
                source['amount_unit'] == source['currency'] + '_million' and
                source['eps_unit'] == source['currency'] + '_per_diluted_share' and
                source['shares_unit'] == 'million_shares', 'outcome reviewed unit convention')
    calibration = notes['calibration_limits']
    model.check(type(calibration['company_guidance_events']) is int and calibration['company_guidance_events'] == 1 and
                type(calibration['independent_ai_forecasts_scored']) is int and calibration['independent_ai_forecasts_scored'] == 0 and
                calibration['method_or_prompt_version_changed'] is False,
                'outcome prior review attribution differs')
    excerpts = entry['excerpts']
    model.check(isinstance(excerpts, list) and 1 <= len(excerpts) <= 6 and
                all(isinstance(t, str) and 0 < len(t) <= 3000 for t in excerpts), 'outcome selected excerpts')
    for quote in excerpts:
        selected(source_files['review'], {'quote': quote})
    model.check(model.clock(a['published_at']) <= model.clock(notes['recorded_at'])
                <= model.clock(checked_at), 'outcome review before result or after cutoff')
    rows = []
    for metric, label, fk, ak, wk, unit_key, multiplier, approximate in METRICS:
        unit = source[unit_key] if unit_key in ('amount_unit', 'eps_unit') else unit_key
        shared = {'subject': entry['subject'], 'event_id': entry['event_id'], 'metric': metric, 'period': g['period'],
                  'basis': g['basis'], 'currency': source['currency'], 'unit': unit,
                  'share_basis': 'REPORTED_DILUTED_EPS_NOT_CONSTANT_SHARE_COUNT' if metric == 'diluted_eps' else 'NOT_PER_SHARE'}
        value = g.get(fk)
        if value is not None:
            with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
                value = format(number(value) * Decimal(multiplier), 'f')
        forecast = {**shared, 'role': ROLE, 'published_at': g['published_at'], 'value': value,
                    'half_width': g.get(wk) if wk else None, 'approximate': approximate,
                    'source_id': g['source_id'], 'value_pointer': '/guide/' + fk,
                    'value_multiplier': multiplier, 'range_pointer': '/guide/' + wk if wk else None}
        actual = {**shared, 'role': 'REPORTED_ACTUAL', 'period': a['period'], 'basis': a['basis'],
                  'published_at': a['published_at'], 'period_end': a['period_end'],
                  'retained_review_at': notes['recorded_at'], 'value': a.get(ak),
                  'source_id': a['source_id'], 'value_pointer': '/actual/' + ak}
        compared = compare_pair(forecast, actual, checked_at=checked_at)
        rows.append({'metric': metric, 'label': label, 'forecast': forecast, 'actual': actual, 'comparison': compared})
    eligible = sum(r['comparison']['status'] == 'COMPARABLE_RETAINED_VALUES' for r in rows)
    report = {'version': VERSION, 'id': entry['id'], 'subject': entry['subject'], 'event_id': entry['event_id'],
              'selection_hash': canonical_hash(entry), 'checked_at': checked_at,
              'retained_review_at': notes['recorded_at'], 'comparator_role': ROLE,
              'status': 'RETAINED_REVIEW_COMPARED' if eligible == len(rows) else 'RETAINED_REVIEW_WITH_COMPARISON_GAPS',
              'period': a['period'], 'period_end': a['period_end'], 'rows': rows,
              'source_custody': q['source_custody'], 'sources': deepcopy(descriptors),
              'source_acquisition_limits': deepcopy(notes['acquisition_limits']),
              'public_source_declarations': deepcopy(public),
              'source_scope': 'THREE_SELECTED_RETAINED_FILES_NOT_RAW_ISSUER_OR_COMPLETE_ARCHIVE',
              'economic_adequacy': 'NOT_CERTIFIED_BY_ARITHMETIC_OR_PUBLICATION',
              'excerpts': deepcopy(excerpts), 'company_guidance_events': 1,
              'metric_count': len(rows), 'comparable_metrics': eligible, 'independent_sample_count': None,
              'ai_forecast_error': None, 'brier_score': None, 'win_rate': None,
              'method_effectiveness': None, 'normalized_eps_floor': q['normalized_eps_floor'],
              'new_source_requests': 0, 'model_calls': 0, 'new_research_execution': False,
              'original_human_decision_modified': False, 'automatic_method_change': False,
              **model.AUTHORITY}
    report['report_hash'] = canonical_hash(report)
    return report


def render(report):
    lines = ['\n\n## D2：已保存经营结果对账（不是收益或方法评分）\n',
             '公司指引、研究者预测和人的决定分开；同一事件的多个指标不是独立预测样本。']
    if not report['items']:
        lines.append('未配置经营结果比较；不是零误差、零事件或已完成全覆盖。')
    for item in report['items']:
        lines.append('\n### ' + escape(str(item.get('subject', item.get('id')))))
        if item['status'] not in ('RETAINED_REVIEW_COMPARED', 'RETAINED_REVIEW_WITH_COMPARISON_GAPS'):
            lines.append('本项读取或核验未完成；不代表经营失败、零误差或没有结果。')
            continue
        lines += [f"原审阅留存：{item['retained_review_at']}；本次读取：{item['checked_at']}。",
                  f"期间：{escape(item['period'])}；源资格：{escape(item['source_custody'])}。",
                  '| 指标 | 指引中点／近似值 | 报告实绩 | 实际减指引 | 原单位 | 比较状态 |',
                  '|---|---:|---:|---:|---|---|']
        for row in item['rows']:
            result = row['comparison']
            okay = result['status'] == 'COMPARABLE_RETAINED_VALUES'
            # Future/unavailable values never become an apparently mature table row.
            values = [row['label'], row['forecast']['value'] if okay else '未可比',
                      row['actual']['value'] if okay else '未可比', result['difference'],
                      row['forecast']['unit'], result['status']]
            lines.append('| ' + ' | '.join(escape(str(v)) if v is not None else '未建立' for v in values) + ' |')
        for quote in item['excerpts']:
            lines.append('\n'.join('> ' + escape(line) for line in quote.splitlines()))
        source = item.get('retained_files', {}).get('review')
        if source:
            lines.append(f"[本次读取的原审阅正文]({source['read_path']})；只恢复选定三文件，不认证发行人原件。")
        lines.append('AI预测误差、概率评分、方法有效性仍未建立；未改Human决定或原期限。')
    return '\n'.join(lines) + '\n'
