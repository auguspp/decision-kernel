"""Offline D2 worked-case replay, not a scorer, Kernel schema or trading tool.

Requires eight original source files plus the exact pinned current-state.json in
--source-dir. Source files are data and never imported or executed. The source
index provides exact GitHub retrieval locators; no network is performed here.
--output creates a new file exclusively. --check and --self-test are read-only.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
D = Decimal


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'DUPLICATE_JSON_KEY')
        value[key] = item
    return value


def load(raw):
    return json.loads(raw, object_pairs_hook=unique_object)


def fingerprint(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}


def bound(raw, expected):
    require(all(fingerprint(raw)[k] == expected[k] for k in ('bytes', 'sha256', 'git_blob')),
            'SOURCE_BYTES_DIFFER')


def read_inputs(source_dir, index):
    def read(name):
        require(Path(name).name == name and name not in ('.', '..'), 'UNSAFE_LOCAL_NAME')
        p = source_dir / name
        require(p.is_file() and not p.is_symlink(), 'SOURCE_FILE_UNAVAILABLE')
        require(p.stat().st_size <= 512 * 1024, 'SOURCE_FILE_TOO_LARGE')
        return p.read_bytes()
    raw = read('current-state.json')
    bound(raw, index['root'])
    root = load(raw)
    canonical = json.dumps({k: v for k, v in root.items() if k != 'reading_hash'},
                           ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    require(hashlib.sha256(canonical).hexdigest() == root['reading_hash'] == index['root']['reading_hash'],
            'READING_HASH_DIFFERS')
    require(root['code_commit'] == index['root']['code_commit'], 'READING_CODE_DIFFERS')
    records = {r['id']: r for r in root['research']['records']}
    require(len(index['sources']) == 8 and len({s['key'] for s in index['sources']}) == 8,
            'THIS_CASE_STUDY_REQUIRES_ITS_EIGHT_SOURCES')
    values = {}
    for s in index['sources']:
        raw = read(s['local_name'])
        if 'root_record_id' in s:
            r = records[s['root_record_id']]
            require(r['use'] == s['record_use'], 'REGISTRY_USE_DIFFERS')
            descriptor = r['source']
            require(descriptor['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT', 'READING_RULE_DIFFERS')
        else:
            descriptor = s
        bound(raw, descriptor)
        values[s['key']] = load(raw) if s['local_name'].endswith('.json') else raw.decode('utf-8')
    direct = next(s for s in index['sources'] if s['key'] == 'GD_MARKDOWN')
    require('/blob/' + direct['fetch_commit'] + '/' + direct['fetch_path'] in values['GD_REVIEW']
            and direct['git_blob'] in values['GD_REVIEW'], 'HISTORICAL_SOURCE_LINK_DIFFERS')
    return values


def analyze(v):
    """Verify this explicit historical selection; text semantics are not inferred by NLP."""
    a, b, h = v['BA1'], v['BA2'], v['BA3']
    revision = b['revision']
    require(revision['previous_odds_ref'] == 'cc95a4fb42f332f8384dd2240647e61fa36fd49f'
            and revision['previous_odds_blob'] == '3611fa961ce09596849c3054e0edf3630e013e54',
            'BA_PREDECESSOR_DIFFERS')
    same_research = all(a['research_identity'][k] == b['research_identity'][k]
                        for k in ('source_commit', 'source_path', 'source_blob'))
    same_price = all(a['price_context'][k] == b['price_context'][k]
                     for k in ('price', 'price_date', 'source_authority'))
    frame_keys = ('holding_period_years', 'primary_working_annualized_return_requirement',
                  'gross_cumulative_dividend_middle_sensitivity_cny')
    same_frame = all(a['decision_use_context'][k] == b['decision_use_context'][k] for k in frame_keys)
    require(same_research and same_price and same_frame, 'BA_UNCHANGED_INPUT_DECLARATION_CONTRADICTED')
    require(revision['type'] == 'VALUATION_INTERPRETATION_NOT_PRICE_ONLY'
            and revision['new_operating_evidence'] is False
            and b['price_context']['price_refresh_this_revision'] is False, 'BA_REVISION_ROLE_DIFFERS')
    require(a['odds']['cardinal_probability'] == b['odds']['cardinal_probability'] == 'NOT_ESTABLISHED',
            'PROBABILITY_QUALIFICATION_CHANGED_REQUIRES_SEPARATE_REVIEW')
    def card(x):
        return next(c['price_region_cny'] for c in x['price_cards'] if c['label'] == 'CONDITIONAL_FIRST_ENTRY_REVIEW')
    before, after = card(a), card(b)
    changes = [str(D(y)-D(x)) for x, y in zip(before.split('-'), after.split('-'), strict=True)]
    anchors = {}
    for old, new in [('21x', '21x'), ('24x', '24x_upper_context_only')]:
        x = a['reverse_underwriting']['required_2029_net_income_for_10pct_cagr_cny'][old]
        y = b['reverse_underwriting_10pct']['required_2029_net_income_cny'][new]
        require(D(x) == D(y), 'BA_SHARED_ARITHMETIC_CHANGED')
        anchors[old] = x
    require(all(s in h for s in ('daf25acbda3a764c73ffad1a5de89bc365e6d924',
        'd35934f5f4ef27a225c7d7928e5ee7634dab3878', 'NO INVESTMENT DECISION / NO ACTION',
        '嗯，我现在同意了 odds', 'HUMAN INVESTMENT DECISION = NONE')), 'BA_ACCEPTANCE_TARGET_OR_SCOPE_DIFFERS')
    g = v['GD_JSON']
    require('HISTORICAL ENTRY LADDERS NOT ACTION-READY' in v['GD_REVIEW']
            and '895ba811d96750d02a4f0d7c08358b5e7fed3088' in v['GD_REVIEW'], 'GD_CHALLENGE_BINDING_DIFFERS')
    require(g['human_acceptance_of_distribution'] == 'NOT_RECORDED'
            and g['odds']['cardinal_probability'] == 'NOT_ESTABLISHED', 'GD_ORIGINAL_QUALIFICATION_DIFFERS')
    worlds = []
    for w in g['worlds']:
        line = next((x for x in v['GD_MARKDOWN'].splitlines() if x.startswith('| `' + w['name'] + '` |')), None)
        require(line is not None, 'GD_WORLD_ROW_UNAVAILABLE')
        match = re.search(r'\| ([0-9.]+)–([0-9.]+)bn CNY \|', line)
        require(match is not None, 'GD_ORIGINAL_UNIT_UNAVAILABLE')
        ratios = [str(D(text)*D('1e9')/D(raw)) for text, raw in
                  zip(match.groups(), w['normalized_parent_np_cny_range'], strict=True)]
        require(all(D(x) == 10 for x in ratios), 'GD_UNIT_CONTRADICTION_CHANGED')
        prices = [D(profit)*D(pe)/D(g['share_count']) for profit, pe in
                  zip(w['normalized_parent_np_cny_range'], w['terminal_pe_range'], strict=True)]
        residuals = [abs(x-D(y)) for x, y in zip(prices, w['terminal_value_per_share_cny_range'], strict=True)]
        require(all(x <= D('0.0051') for x in residuals), 'GD_STORED_PER_SHARE_NOT_ROUNDING_COMPATIBLE')
        worlds.append({'world': w['name'], 'markdown_to_json_profit_ratio': ratios,
                       'recomputed_per_share_cny': [str(x.quantize(D('.0001'))) for x in prices],
                       'stored_per_share_cny': w['terminal_value_per_share_cny_range'],
                       'source_line': line})
    old = re.search(r'贵州茅台 600519 @ CNY([0-9.]+) -> (\w+)', v['MT_BEFORE'])
    section = v['MT_AFTER'].split('## 贵州茅台 600519', 1)
    require(old is not None and len(section) == 2, 'MT_REQUIRED_SOURCE_SECTION_MISSING')
    new = re.search(r'\*\*当前状态：\*\* Research 已存在 · `(\w+)` · ¥([0-9.]+)', section[1])
    require(new is not None and old[2] == 'INSUFFICIENT_ODDS' and new[1] == 'ACCEPTABLE_ODDS',
            'MT_LABEL_OBSERVATION_DIFFERS')
    return {
        'purpose': 'D2_VERSION_ATTRIBUTION_WORKED_CONTROLS_NOT_MATURE_PERFORMANCE',
        'coverage': {'source_documents': 8, 'securities': 3, 'version_transitions': 4,
                     'independent_investment_outcomes': 0, 'comparable_realized_operating_pairs': 0,
                     'qualified_probability_outcome_pairs': 0, 'selection': 'PURPOSIVE_NOT_STATISTICAL'},
        'beidahuang_method_transition': {
            'same_research_identity': same_research, 'same_retained_price_context': same_price,
            'same_three_year_working_frame': same_frame,
            'same_serialization_schema': a['schema_version'] == b['schema_version'],
            'revision_declaration': revision, 'shared_reverse_underwriting_cny': anchors,
            'first_entry_review_before': before, 'first_entry_review_after': after,
            'review_range_endpoint_change_cny': changes,
            'attribution': 'Declared valuation interpretation and selected assumptions, not price-only refresh or new realized operating evidence.'},
        'beidahuang_acceptance_transition': {
            'accepted_odds_blob': 'd35934f5f4ef27a225c7d7928e5ee7634dab3878',
            'scope': 'BA2 decision preparation only; neither backfills BA1 acceptance nor creates an investment/Action outcome.',
            'historical_internal_model_version': None},
        'guangdian_representation_control': {
            'worlds': worlds, 'matched_per_share_endpoints': 2*len(worlds),
            'known_error': 'Tenfold monetary-unit label conflict in original Markdown; JSON yuan-based per-share math remains rounding-compatible.',
            'separate_unresolved_judgment': 'Valuation/operating bridge remains challenged; correcting units does not validate the worlds or restore an actionable ladder.'},
        'maotai_incomplete_comparison': {
            'earlier_label': old[2], 'earlier_retained_context_price_cny': old[1],
            'later_label': new[1], 'later_retained_context_price_cny': new[2],
            'evidence_kind': 'Earlier handoff account plus later saved Markdown; not two recovered typed numeric results.',
            'price_only_cause_established': None, 'matched_model_method_horizon_established': None,
            'attribution': 'Unresolved from this source set; neither label change nor changing prices establishes price-only causality.'},
        'statistics': {'forecast_error': None, 'brier_score': None, 'win_rate': None,
                       'method_improvement_estimate': None,
                       'reason': 'No matched mature realized outcome pairs in this selected evidence. Null is not zero error or zero skill.'},
        'authority': {'investment': 'NONE', 'human_decision_changes': 0,
                      'production_method_changes': 0, 'new_watch_or_notifications': 0},
        'limits': ['Project-source identity and artifact arithmetic only; issuer truth not revalidated.',
                   'Git/code/schema versions do not reveal unrecorded internal model or prompt versions.',
                   'These linked transitions are not independent observations of forecast performance.',
                   'No current trading/position inference; no whole-history or new-market search.']}


def self_test(values, index):
    """Labelled synthetic mutations of this selection, never additional real cases."""
    mutations = [
        ('BA_CHANGED_PRICE', lambda x: x['BA2']['price_context'].update(price='13')),
        ('BA_CHANGED_HORIZON', lambda x: x['BA2']['decision_use_context'].update(holding_period_years=1)),
        ('BA_WRONG_PREDECESSOR', lambda x: x['BA2']['revision'].update(previous_odds_blob='0'*40)),
        ('BA_FALSE_PRICE_ONLY', lambda x: x['BA2']['revision'].update(type='PRICE_ONLY')),
        ('BA_FAKE_ZERO_PROBABILITY', lambda x: x['BA2']['odds'].update(cardinal_probability=0)),
        ('BA_ACCEPTANCE_BORROWED', lambda x: x.update(BA3=x['BA3'].replace('d35934f5f4ef27a225c7d7928e5ee7634dab3878','3611fa961ce09596849c3054e0edf3630e013e54'))),
        ('GD_MISSING_UNIT_EVIDENCE', lambda x: x.update(GD_MARKDOWN=x['GD_MARKDOWN'].replace('bn CNY','CNY'))),
        ('GD_CHANGED_PER_SHARE', lambda x: x['GD_JSON']['worlds'][0].update(terminal_value_per_share_cny_range=['0','0'])),
        ('MT_MISSING_LATER_SECTION', lambda x: x.update(MT_AFTER='unavailable')),
    ]
    rejected = []
    for name, mutate in mutations:
        changed = deepcopy(values); mutate(changed)
        try:
            analyze(changed)
        except (ValueError, KeyError, TypeError, IndexError, StopIteration):
            rejected.append(name)
        else:
            raise ValueError('MUTATION_NOT_REJECTED:' + name)
    try:
        bound(b'tampered', index['root'])
    except ValueError:
        rejected.append('RAW_BYTE_TAMPERING')
    else:
        raise ValueError('RAW_BYTE_MUTATION_NOT_REJECTED')
    return {'synthetic_negative_controls_rejected': rejected, 'count': len(rejected),
            'meaning': 'Local evidence-contract tests, not independent review or economic validation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    try:
        index = load((ROOT/'source-index.json').read_bytes())
        values = read_inputs(args.source_dir, index)
        with localcontext() as context:
            context.prec = 40
            result = analyze(values)
            if args.self_test:
                print(encoded(self_test(values,index)).decode(), end=''); return
        raw = encoded(result)
        if args.check:
            require((ROOT/'results.json').read_bytes() == raw, 'RESULT_BYTES_DIFFER')
            print('EXACT_D2_CASE_REPLAY_MATCHED; not formal CI or economic validation')
        else:
            with args.output.open('xb') as stream:
                stream.write(raw)
            print('CREATED_D2_WORKED_CASE_RESULTS')
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration, ArithmeticError) as exc:
        raise SystemExit('D2_REPLAY_REJECTED: ' + type(exc).__name__ + ': ' + str(exc))


if __name__ == '__main__':
    main()
