"""Offline consumer of explicitly reviewed, source-bound longitudinal comparisons.

Archive/progress/re-entry retain their ownership. This module checks declared
identity, basis and arithmetic; it cannot certify sources or economic meaning.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from html import escape
import json
from pathlib import Path
import re

from ..identity import canonical_hash, canonical_json
from . import current_state as state
from .research_commit_only import _read, _write, _publish_report_files

VERSION = 'reviewed-research-comparison-v0'
AUTHORITY = {'investment_authority': 'NONE', 'human_acceptance': 'NOT_ESTABLISHED',
             'network_requests': 0, 'model_calls': 0, 'research_committed': False,
             'economic_adequacy': 'NOT_CERTIFIED_BY_ARITHMETIC'}
KINDS = {'PERIOD_CHANGE', 'SOURCE_REVISION', 'RESEARCH_CORRECTION',
         'EVIDENCE_COVERAGE_CHANGE', 'CHECKED_UNCHANGED', 'NOT_CHECKED',
         'INCOMPARABLE', 'CASH_DIAGNOSTIC', 'DERIVED_QUARTER', 'FORECAST_COMPARISON'}
OPS = {'difference', 'signed_sum', 'ratio', 'quarter', 'coverage', 'claim', 'forecast_difference'}
SCALES = {'1', '10000', '1000000', '100000000', '1000000000'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def text(value):
    require(isinstance(value, str) and 0 < len(value) <= 8000, 'bounded text required')
    return value


def number(value):
    require(isinstance(value, str) and re.fullmatch(r'-?\d{1,24}(?:\.\d{1,18})?', value),
            'finite decimal string required, not float or missing-as-zero')
    return Decimal(value)


def parse(raw):
    require(isinstance(raw, bytes) and len(raw) <= 512 * 1024, 'bounded source bytes required')
    def unique(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, 'duplicate JSON key')
            result[k] = v
        return result
    def invalid(_):
        raise ValueError('nonfinite JSON number')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                      parse_float=Decimal, parse_int=Decimal, parse_constant=invalid)


def clock(value):
    if value is not None:
        require(isinstance(value, str), 'clock must be explicit or null')
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(d.tzinfo is not None, 'clock must include timezone')


def period(p):
    require(set(p) == {'kind', 'start', 'end'}, 'period keys differ')
    require(p['kind'] in {'FLOW', 'STOCK'}, 'stock/flow kind required')
    end = date.fromisoformat(p['end'])
    require(end.isoformat() == p['end'], 'canonical end date required')
    if p['kind'] == 'STOCK':
        require(p['start'] is None, 'stock has as-of date only')
    else:
        start = date.fromisoformat(p['start'])
        require(start.isoformat() == p['start'], 'canonical start date required')
        require(start <= end, 'period order differs')


def validate_input(v):
    require(isinstance(v, dict) and v.get('version') == VERSION, 'comparison version differs')
    require(v.get('authority') == AUTHORITY, 'authority differs')
    require(re.fullmatch(r'\d{6}\.(SH|SZ|BJ)', v.get('subject', '')), 'subject required')
    text(v['question']); text(v['predecessor']); text(v['remaining_evidence'])
    require(len(canonical_json(v).encode()) <= 512 * 1024, 'input byte bound')
    clock(v['analysis_cutoff']); clock(v['reviewed_at'])
    require(v['reviewed_at'] is not None, 'review clock required')
    review = datetime.fromisoformat(v['reviewed_at'].replace('Z', '+00:00'))
    cutoff = datetime.fromisoformat(v['analysis_cutoff'].replace('Z', '+00:00')) if v['analysis_cutoff'] else None
    require(cutoff is None or cutoff <= review, 'analysis cutoff is after review')
    for key, limit in [('sources', 16), ('observations', 64), ('comparisons', 32)]:
        rows = v[key]
        require(isinstance(rows, list) and 0 < len(rows) <= limit, 'bounded list required')
        ids = [text(x['id']) for x in rows]
        require(len(set(ids)) == len(ids), 'duplicate identity')
    for s in v['sources']:
        require(s['subject'] == v['subject'], 'source subject differs')
        require(re.fullmatch('[0-9a-f]{40}', s['ref']), 'immutable commit required')
        require(re.fullmatch('[0-9a-f]{40}', s['git_blob']), 'git blob required')
        require(re.fullmatch('[0-9a-f]{64}', s['sha256']), 'source hash required')
        require(type(s['bytes']) is int and 0 <= s['bytes'] <= 512 * 1024, 'source byte bound')
        state.safe_path(s['path']); text(s['identity_basis'])
        require(s['qualification'] in {'RETAINED_RESEARCH', 'ISSUER_DISCLOSURE_BYTES', 'SYNOPSIS', 'SYNTHETIC_FIXTURE'},
                'explicit source qualification required')
        clock(s['acquired_at']); clock(s['published_at'])
        published = datetime.fromisoformat(s['published_at'].replace('Z', '+00:00')) if s['published_at'] else None
        acquired = datetime.fromisoformat(s['acquired_at'].replace('Z', '+00:00')) if s['acquired_at'] else None
        require(published is None or published <= review, 'publication after review')
        require(acquired is None or acquired <= review, 'acquisition after review')
        require(cutoff is None or published is None or published <= cutoff, 'source published after cutoff')
    source_ids = {s['id'] for s in v['sources']}
    for o in v['observations']:
        require(o['subject'] == v['subject'], 'observation subject differs')
        require(o['status'] in {'KNOWN', 'UNKNOWN', 'NOT_CHECKED'}, 'observation status invalid')
        require(o['source_id'] in source_ids, 'source missing')
        for k in ('metric', 'scope', 'restatement', 'basis_note'):
            text(o[k])
        require(o['currency'] in {'CNY', 'USD', 'NONE'}, 'explicit currency required')
        require(o['scale'] in SCALES, 'explicit supported scale required')
        if o.get('forecast') is None or o['period'] is not None:
            period(o['period'])
        require(isinstance(o['locator'], dict), 'locator required')
        require(set(o['locator']) in ({'pointer'}, {'quote'}), 'one data locator required')
        for x in o['locator'].values(): text(x)
        if o['status'] == 'KNOWN':
            require(o['type'] in {'NUMBER', 'CLAIM'}, 'observation type invalid')
            number(o['value']) if o['type'] == 'NUMBER' else text(o['value'])
        else:
            require(o['value'] is None, 'unknown is not numeric zero')
            text(o['missing_reason'])
    obs = {o['id']: o for o in v['observations']}
    for c in v['comparisons']:
        require(c['kind'] in KINDS and c['operation'] in OPS, 'comparison kind/operation invalid')
        require(isinstance(c['terms'], list) and 1 <= len(c['terms']) <= 16, 'bounded terms required')
        require(all(t['observation'] in obs and type(t['sign']) is int and t['sign'] in {-1, 1}
                    for t in c['terms']), 'invalid comparison term')
        require(len({t['observation'] for t in c['terms']}) == len(c['terms']), 'duplicate term')
        for k in ('compatibility_note', 'interpretation', 'challenge_disposition', 'limitations'):
            text(c[k])
        has_forecast = any(obs[t['observation']].get('forecast') is not None for t in c['terms'])
        require(not has_forecast or c['operation'] == 'forecast_difference',
                'forecast observations require their qualification path')


def selected(raw, locator):
    require(isinstance(locator, dict) and set(locator) in ({'pointer'}, {'quote'}),
            'exactly one locator mode required')
    if 'quote' in locator:
        quote = locator['quote']
        require(quote in raw.decode('utf-8'), 'source quote not present')
        return quote
    value = parse(raw)
    pointer = locator['pointer']
    require(pointer.startswith('/'), 'absolute JSON pointer required')
    for token in pointer[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            require(token.isdigit(), 'array pointer invalid')
            value = value[int(token)]
        else:
            require(isinstance(value, dict) and token in value, 'JSON pointer missing')
            value = value[token]
    return value


def basis(rows, *, metric=True, same_period=True):
    keys = ['subject', 'currency', 'scope', 'restatement'] + (['metric'] if metric else [])
    require(all(all(r[k] == rows[0][k] for k in keys) for r in rows), 'incompatible basis')
    if same_period:
        require(all(r['period'] == rows[0]['period'] for r in rows), 'incompatible period')
    else:
        require(all(r['period']['kind'] == rows[0]['period']['kind'] for r in rows),
                'stock/flow mismatch')


def evaluate(c, rows):
    op, kind = c['operation'], c['kind']
    if kind in {'NOT_CHECKED', 'INCOMPARABLE'}:
        return {'status': kind, 'value': None}
    if op == 'coverage':
        require(kind == 'EVIDENCE_COVERAGE_CHANGE' and len(rows) == 2, 'coverage kind required')
        basis(rows)
        require(rows[0]['status'] != 'KNOWN' and rows[1]['status'] == 'KNOWN', 'coverage direction differs')
        return {'status': kind, 'value': None, 'meaning': 'NOT_ZERO_BASED_GROWTH_OR_NEW_COMPANY_EVENT'}
    if any(r['status'] != 'KNOWN' for r in rows):
        return {'status': 'EVIDENCE_GAP', 'value': None}
    if op == 'claim':
        require(len(rows) == 2 and all(r['type'] == 'CLAIM' for r in rows), 'two claims required')
        basis(rows)
        equal = rows[0]['value'] == rows[1]['value']
        require(kind in {'CHECKED_UNCHANGED', 'RESEARCH_CORRECTION', 'SOURCE_REVISION'}, 'claim kind differs')
        require(kind != 'CHECKED_UNCHANGED' or equal, 'unchanged claim differs')
        return {'status': 'UNCHANGED' if equal else kind, 'value': None}
    require(all(r['type'] == 'NUMBER' for r in rows), 'numeric terms required')
    require(all(r['currency'] != 'NONE' for r in rows), 'monetary arithmetic needs currency')
    vals = [number(r['value']) * Decimal(r['scale']) for r in rows]
    signs = [t['sign'] for t in c['terms']]
    if op == 'difference':
        require(len(rows) == 2 and signs == [-1, 1], 'difference is new minus old')
        basis(rows, same_period=kind != 'PERIOD_CHANGE')
        require(kind in {'PERIOD_CHANGE', 'SOURCE_REVISION', 'RESEARCH_CORRECTION', 'CHECKED_UNCHANGED'},
                'difference kind differs')
        if kind == 'PERIOD_CHANGE':
            a, b = [r['period'] for r in rows]
            require(a != b and a['end'] < b['end'], 'period change must advance period')
            # Fixed seasonal basis; annual/H1/Q1/TTM cannot be silently mixed.
            require(a['kind'] == 'STOCK' or (a['start'][5:], a['end'][5:]) ==
                    (b['start'][5:], b['end'][5:]), 'flow seasonal window differs')
            require(a['kind'] == 'STOCK' or int(a['end'][:4]) - int(a['start'][:4]) ==
                    int(b['end'][:4]) - int(b['start'][:4]), 'flow year span differs')
        value = vals[1] - vals[0]
        require(kind != 'CHECKED_UNCHANGED' or value == 0, 'unchanged value differs')
    elif op == 'quarter':
        require(kind == 'DERIVED_QUARTER' and len(rows) == 2 and signs == [-1, 1], 'quarter shape differs')
        basis(rows, same_period=False)
        q, h = [r['period'] for r in rows]
        require(q['kind'] == h['kind'] == 'FLOW' and q['start'] == h['start'] and
                q['start'][5:] == '01-01' and q['end'] == q['start'][:4] + '-03-31' and
                h['end'] == q['start'][:4] + '-06-30', 'quarter requires same-year H1 minus Q1')
        value = vals[1] - vals[0]
    elif op == 'signed_sum':
        require(kind == 'CASH_DIAGNOSTIC', 'signed bridge is cash diagnostic, not owner earnings')
        basis(rows, metric=False)
        value = sum((x * s for x, s in zip(vals, signs)), Decimal(0))
    elif op == 'ratio':
        require(kind == 'CASH_DIAGNOSTIC' and len(rows) == 2 and signs == [1, 1], 'ratio shape differs')
        basis(rows, metric=False)
        if vals[1] == 0: return {'status': 'ZERO_DENOMINATOR', 'value': None}
        value = vals[0] / vals[1]
    else:
        raise ValueError('unsupported operation')
    return {'status': 'ARITHMETIC_VERIFIED_NOT_ECONOMIC_ACCEPTANCE', 'value': format(value, 'f'),
            'unit': 'ratio' if op == 'ratio' else rows[0]['currency'],
            'precision': 'DECIMAL_50_DIGITS'}


FORECAST_CONTRACT = 'reviewed-institutional-forecast-v0'

def _known_forecast_text(value):
    return isinstance(value, str) and 0 < len(value.strip()) <= 8000 and value.strip().upper() not in {
        'UNKNOWN', 'NOT_ESTABLISHED', 'UNVERIFIED', 'UNRESOLVED', 'NONE', 'N/A'}


def _forecast_member(record, root_pointer, member_pointer):
    """One reviewed JSON row: direct facts, or one scalar-array value slot."""
    require(isinstance(record, dict) and isinstance(root_pointer, str)
            and isinstance(member_pointer, str) and member_pointer.startswith(root_pointer + '/'),
            'forecast binding is not a member of one JSON record')
    parts = member_pointer[len(root_pointer) + 1:].split('/')
    parts = [p.replace('~1', '/').replace('~0', '~') for p in parts]
    require(1 <= len(parts) <= 2 and parts[0] in record, 'forecast record nesting unsupported')
    found = record[parts[0]]
    if len(parts) == 2:
        require(isinstance(found, list) and all(not isinstance(x, (dict, list)) for x in found)
                and parts[1].isdigit(), 'forecast path traverses a record container')
        found = found[int(parts[1])]
    return found


def _forecast_info(o, files):
    """Qualify supplied reviewed facts, never infer missing provider semantics."""
    f = o.get('forecast')
    require(isinstance(f, dict) and f.get('contract') == FORECAST_CONTRACT,
            'explicit reviewed forecast contract required')
    institution, report = f['institution'], f['report']
    require(isinstance(institution, dict) and isinstance(report, dict)
            and isinstance(f['bindings'], dict), 'forecast metadata shape invalid')
    text(f['limitations']); text(f['value_kind_basis']); text(institution['mapping_note'])
    blockers = []
    source_id = report.get('source_id')
    locator = report.get('record_locator')
    record = None
    if source_id != o['source_id'] or source_id not in files or not isinstance(locator, dict):
        blockers.append('REPORT_SOURCE_UNRESOLVED')
    else:
        try:
            record = selected(files[source_id], locator)
            require(isinstance(record, dict) and set(locator) == {'pointer'},
                    'forecast record must be one JSON object')
            _forecast_member(record, locator['pointer'], o['locator'].get('pointer'))
        except (ValueError, KeyError, TypeError, IndexError):
            blockers.append('REPORT_RECORD_BINDING_INVALID'); record = None

    def fact(key, value):
        if value is None or value == '' or (isinstance(value, str) and not _known_forecast_text(value)):
            blockers.append(key + ':UNKNOWN'); return False
        b = f['bindings'].get(key)
        if not isinstance(b, dict) or b.get('source_id') != source_id or record is None:
            blockers.append(key + ':SOURCE_BINDING_MISSING'); return False
        try:
            loc = b['locator']
            require(isinstance(loc, dict) and set(loc) in ({'pointer'}, {'quote'}), 'exactly one fact locator mode required')
            rp = locator['pointer']; bp = loc.get('pointer')
            require(set(loc) == {'pointer'}, 'forecast facts require record-member pointers')
            found = _forecast_member(record, rp, bp)
            transform = b.get('transform', 'EXACT')
            if transform == 'DATE_PREFIX':
                require(key == 'report_date' and isinstance(found, str)
                        and re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[ T].*)?', found),
                        'unsupported date transformation')
                found = found[:10]
            elif transform == 'CURRENCY_ISO':
                require(key == 'currency', 'currency transform scope differs')
                aliases = {'CNY':'CNY', 'RMB':'CNY', '人民币':'CNY', '人民币元':'CNY', 'USD':'USD', '美元':'USD'}
                require(isinstance(found, str) and found in aliases, 'ambiguous currency label')
                found = aliases[found]
            elif transform == 'METRIC_BASIS_FIELDS':
                require(key == 'metric_basis' and isinstance(found, dict), 'basis transform scope differs')
                found = {k:found[k] for k in ('measure', 'attribution', 'adjustment')}
            elif transform == 'FORECAST_FIELD':
                require(key == 'value_kind' and bp is not None and bp == o['locator'].get('pointer'),
                        'forecast role must bind the observed value slot')
                field = bp[len(rp) + 1:].split('/')[0]
                require(field in {'forecast_values', 'predictThisYearEps', 'predictNextYearEps',
                                  'predictNextTwoYearEps'}, 'source field is not an identified forecast slot')
                found = 'FORECAST'
            elif transform == 'JSON_KEY':
                require(key == 'metric_label' and bp is not None, 'unsupported key transformation')
                found = bp.rsplit('/', 1)[-1].replace('~1', '/').replace('~0', '~')
            else:
                require(transform == 'EXACT', 'unknown qualification transformation')
            require(canonical_json(found) == canonical_json(value), 'forecast fact binding differs')
            return True
        except (ValueError, KeyError, TypeError, IndexError):
            blockers.append(key + ':SOURCE_BINDING_INVALID'); return False

    name_ok = fact('institution_name', institution.get('displayed_name'))
    identity = None
    identity_basis = institution.get('identity_basis')
    code_claimed = institution.get('provider_code') is not None or identity_basis == 'PROVIDER_ID'
    code_ok = fact('institution_code', institution.get('provider_code')) if code_claimed else False
    if identity_basis == 'PROVIDER_ID':
        if code_ok and name_ok and _known_forecast_text(report.get('namespace')):
            identity = ('provider', report['namespace'], institution['provider_code'])
    elif identity_basis == 'EXACT_DISPLAYED_NAME':
        if name_ok: identity = ('displayed_name', institution['displayed_name'])
    elif identity_basis == 'REVIEWED_ALIAS':
        if not _known_forecast_text(institution.get('mapping_note')):
            blockers.append('ALIAS_MAPPING_RATIONALE_UNKNOWN')
        elif name_ok and _known_forecast_text(institution.get('reviewed_key')):
            identity = ('reviewed_alias', institution['reviewed_key'])
    else:
        blockers.append('INSTITUTION_IDENTITY_BASIS_UNKNOWN')
    if identity is None: blockers.append('INSTITUTION_IDENTITY_UNRESOLVED')
    rid_ok = fact('record_id', report.get('record_id'))
    namespace = report.get('namespace')
    if not _known_forecast_text(namespace): blockers.append('REPORT_NAMESPACE_UNKNOWN')
    date_ok = fact('report_date', report.get('label_date'))
    if date_ok:
        try:
            require(date.fromisoformat(report['label_date']).isoformat() == report['label_date'],
                    'noncanonical report date')
        except (ValueError, TypeError): date_ok = False; blockers.append('REPORT_DATE_INVALID')
    if report.get('date_qualification') not in {'ORIGINAL_REPORT_DATE', 'PROVIDER_DATE_ONLY'}:
        blockers.append('REPORT_DATE_QUALIFICATION_UNKNOWN')
    original_id = report.get('original_report_id')
    original_ok = fact('original_report_id', original_id) if original_id is not None else False
    target_ok = fact('target_period', f.get('target_period'))
    if target_ok:
        try:
            target = f['target_period']
            require(set(target) == {'start', 'end', 'fiscal_basis'}, 'fiscal target shape differs')
            period({'kind': 'FLOW', 'start': target['start'], 'end': target['end']})
            require(_known_forecast_text(target['fiscal_basis']), 'fiscal basis unknown')
            require(o['period'] == {'kind': 'FLOW', 'start': target['start'], 'end': target['end']},
                    'observation and forecast target differ')
        except (ValueError, KeyError, TypeError): target_ok = False; blockers.append('TARGET_PERIOD_INVALID')
    metric_ok = fact('metric_label', f.get('metric_label'))
    mb = f.get('metric_basis')
    if not isinstance(mb, dict) or set(mb) != {'measure', 'attribution', 'adjustment', 'mapping_note'}:
        metric_ok = False; blockers.append('METRIC_BASIS_UNKNOWN')
    else:
        if mb['measure'] not in {'TOTAL_PARENT_PROFIT', 'EPS'} or not all(
                _known_forecast_text(mb[k]) for k in ('attribution', 'adjustment', 'mapping_note')):
            metric_ok = False; blockers.append('METRIC_BASIS_UNKNOWN')
    if metric_ok and not fact('metric_basis', {k:mb[k] for k in ('measure', 'attribution', 'adjustment')}):
        metric_ok = False
    if metric_ok:
        # The source-bound forecast basis is canonical for this opt-in path.
        # Outer fields must project it exactly, not supply a second basis.
        for outer, inner in (('metric', 'measure'), ('scope', 'attribution'), ('restatement', 'adjustment')):
            if not _known_forecast_text(o[outer]):
                blockers.append('OBSERVATION_BASIS_UNKNOWN:' + outer)
            elif o[outer] != mb[inner]:
                blockers.append('OBSERVATION_BASIS_DIFFERS:' + outer)
    currency_ok = fact('currency', f.get('currency'))
    if f.get('currency') not in {'CNY', 'USD'} or f.get('currency') != o['currency']:
        currency_ok = False; blockers.append('CURRENCY_UNQUALIFIED')
    scale_ok = fact('scale_label', f.get('scale_label'))
    scales = {'1': '1', '10000': '10000', '1000000': '1000000',
              '100000000': '100000000', '1000000000': '1000000000',
              '元': '1', '万元': '10000', '百万元': '1000000', '百万人民币': '1000000',
              '人民币百万元': '1000000', '亿元': '100000000', '元/股': '1'}
    if scales.get(f.get('scale_label')) != o['scale']:
        scale_ok = False; blockers.append('SCALE_UNQUALIFIED')
    # An explicit RMB unit cannot override the separately qualified currency.
    if f.get('scale_label') in {'百万人民币', '人民币百万元'} and currency_ok and f['currency'] != 'CNY':
        blockers.append('SCALE_CURRENCY_DIFFERS')
    share = f.get('share_basis')
    measure = mb.get('measure') if isinstance(mb, dict) else None
    if measure == 'TOTAL_PARENT_PROFIT':
        if f.get('scale_label') == '元/股': blockers.append('AMOUNT_UNIT_DIMENSION_DIFFERS')
        if share != {'application': 'NOT_APPLICABLE'}: blockers.append('TOTAL_AMOUNT_DENOMINATOR_MUST_BE_NOT_APPLICABLE')
    elif measure == 'EPS':
        if f.get('scale_label') not in {'1', '元/股'} or o['scale'] != '1':
            blockers.append('PER_SHARE_UNIT_DIMENSION_UNQUALIFIED')
        if not fact('share_basis', share): blockers.append('PER_SHARE_BASIS_UNQUALIFIED')
        elif not isinstance(share, dict) or set(share) != {'application', 'share_class', 'denominator', 'split_basis', 'model_basis'} or share.get('application') != 'PER_SHARE' or not all(_known_forecast_text(v) for v in share.values()):
            blockers.append('PER_SHARE_BASIS_UNQUALIFIED')
    fact('value_kind', f.get('value_kind'))
    if f.get('value_kind') != 'FORECAST': blockers.append('NOT_A_FORECAST')
    return {'metadata': f, 'identity': identity, 'record_id_valid': rid_ok,
            'date_valid': date_ok, 'target_valid': target_ok, 'metric_valid': metric_ok,
            'original_report_id_valid': original_ok,
            'content_hash': canonical_hash(record) if record is not None else None,
            'blockers': sorted(set(blockers))}


def _forecast_difference(c, rows, files, sources, context):
    require(c['kind'] == 'FORECAST_COMPARISON' and len(rows) == 2
            and [t['sign'] for t in c['terms']] == [-1, 1], 'forecast pair shape differs')
    a, b = [_forecast_info(o, files) for o in rows]
    x, y = a['metadata'], b['metadata']
    blockers = ['old:' + k for k in a['blockers']] + ['new:' + k for k in b['blockers']]
    for label, info in [('old', a), ('new', b)]:
        if info['date_valid']:
            report_day = date.fromisoformat(info['metadata']['report']['label_date'])
            for key in ('reviewed_at', 'analysis_cutoff'):
                if context[key] is not None:
                    bound = datetime.fromisoformat(context[key].replace('Z', '+00:00')).date()
                    if report_day > bound: blockers.append(label + ':REPORT_DATE_AFTER_' + key.upper())
    relation = 'IDENTITY_UNRESOLVED'
    same_record_ids = (a['record_id_valid'] and b['record_id_valid'] and
                       (x['report']['namespace'], x['report']['record_id']) ==
                       (y['report']['namespace'], y['report']['record_id']))
    if same_record_ids and a['identity'] is not None and b['identity'] is not None and a['identity'] != b['identity']:
        relation = 'SAME_RECORD_IDENTITY_CONFLICT_OR_CORRECTION'
        blockers.append('SAME_RECORD_INSTITUTION_CHANGED')
    elif a['identity'] is not None and b['identity'] is not None:
        if a['identity'] != b['identity']:
            ia, ib = a['identity'], b['identity']
            comparable_namespace = ia[0] == ib[0] and (ia[0] != 'provider' or ia[1] == ib[1])
            if comparable_namespace and ia[0] in {'provider', 'reviewed_alias'}:
                relation = 'CROSS_INSTITUTION_ATTRIBUTION_NOT_REVISION'
            else:
                blockers.append('INSTITUTION_RELATION_UNRESOLVED')
        elif a['record_id_valid'] and b['record_id_valid']:
            same_record = (x['report']['namespace'], x['report']['record_id']) == (y['report']['namespace'], y['report']['record_id'])
            if same_record:
                relation = 'DUPLICATE_BOUND_RECORD' if a['content_hash'] == b['content_hash'] else 'SAME_RECORD_CONTENT_VARIANT_NOT_NEW_REPORT'
            elif a['date_valid'] and b['date_valid'] and x['report']['label_date'] < y['report']['label_date']:
                relation = ('SAME_INSTITUTION_FORECAST_VINTAGE_CHANGE' if a['original_report_id_valid'] and b['original_report_id_valid']
                            and x['report']['original_report_id'] != y['report']['original_report_id']
                            and x['report']['date_qualification'] == y['report']['date_qualification'] == 'ORIGINAL_REPORT_DATE' else 'DISTINCT_PROVIDER_RECORDS_ORIGINAL_VINTAGE_UNESTABLISHED')
            else:
                relation = 'DISTINCT_RECORDS_NOT_TEMPORALLY_ORDERED'
    if a['target_valid'] and b['target_valid'] and x['target_period'] != y['target_period']:
        relation = 'DIFFERENT_FORECAST_HORIZON'; blockers.append('TARGET_PERIOD_DIFFERS')
    if a['metric_valid'] and b['metric_valid']:
        for key in ('measure', 'attribution', 'adjustment'):
            if x['metric_basis'][key] != y['metric_basis'][key]: blockers.append('METRIC_BASIS_DIFFERS:' + key)
        if x['share_basis'] != y['share_basis']: blockers.append('SHARE_DENOMINATOR_OR_SPLIT_BASIS_DIFFERS')
    if rows[0]['currency'] != rows[1]['currency']: blockers.append('CURRENCY_DIFFERS')
    if any(o['status'] != 'KNOWN' or o['type'] != 'NUMBER' for o in rows): blockers.append('FORECAST_VALUE_UNKNOWN')
    result = {'status': 'NOT_COMPARABLE' if blockers else 'REVIEWED_FORECAST_ARITHMETIC_ONLY',
              'relation': relation, 'value': None, 'blockers': sorted(set(blockers)),
              'source_qualifications': [sources[o['source_id']]['qualification'] for o in rows],
              'institution_identity_bases': [x['institution']['identity_basis'], y['institution']['identity_basis']],
              'report_date_qualifications': [x['report']['date_qualification'], y['report']['date_qualification']],
              'report_label_dates': [x['report'].get('label_date'), y['report'].get('label_date')],
              'original_broker_identity': 'ESTABLISHED_BY_SUPPLIED_BINDINGS' if a['original_report_id_valid'] and b['original_report_id_valid'] else 'NOT_ESTABLISHED',
              'historical_knowledge': 'NOT_ESTABLISHED_BY_RETRIEVAL', 'full_model_revision': 'NOT_CERTIFIED'}
    if blockers: return result
    vals = [number(o['value']) * Decimal(o['scale']) for o in rows]
    if relation == 'DUPLICATE_BOUND_RECORD':
        result['status'] = 'DUPLICATE_NOT_NEW_FORECAST' if vals[0] == vals[1] else 'INCONSISTENT_VALUES_WITHIN_BOUND_RECORD'
        return result
    result['value'] = format(vals[1] - vals[0], 'f')
    result['unit'] = rows[0]['currency'] + ('/share' if x['metric_basis']['measure'] == 'EPS' else '')
    result['precision'] = 'DECIMAL_50_DIGITS'
    return result


def build(value, source_files):
    validate_input(value)
    sources = {s['id']: s for s in value['sources']}
    verified, gaps = {}, []
    for sid, s in sources.items():
        raw = source_files.get(sid)
        if raw is None:
            gaps.append(sid)
            continue
        require(isinstance(raw, bytes) and len(raw) == s['bytes'] and
                state.sha256(raw) == s['sha256'] and state.blob_sha(raw) == s['git_blob'],
                'source byte identity differs')
        verified[sid] = raw
    observations = {}
    for original in value['observations']:
        o = deepcopy(original)
        if o['source_id'] not in verified:
            o.update(status='UNKNOWN', value=None, missing_reason='SOURCE_BYTES_UNAVAILABLE')
        else:
            found = selected(verified[o['source_id']], o['locator'])
            if o['status'] == 'KNOWN':
                if 'pointer' in o['locator']:
                    require((isinstance(found, Decimal) and o['type'] == 'NUMBER' and found == number(o['value']))
                            or (isinstance(found, str) and found == o['value']), 'selected value differs')
                else:
                    if o['type'] == 'NUMBER':
                        pattern = r'(?<![A-Za-z0-9_.,+\-−﹣－(])' + re.escape(o['value']) + r'(?![A-Za-z0-9_.,)])'
                        require(re.search(pattern, found) is not None, 'numeric token absent from exact quote')
                    else:
                        require(o['value'] in found, 'declared value absent from exact quote')
        observations[o['id']] = o
    results = []
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)):
        for c in value['comparisons']:
            rows = [observations[t['observation']] for t in c['terms']]
            missing = any(r['source_id'] not in verified for r in rows)
            result = ({'status': 'SOURCE_BYTES_UNAVAILABLE', 'value': None} if missing else
                      _forecast_difference(c, rows, verified, sources, value) if c['operation'] == 'forecast_difference'
                      else evaluate(c, rows))
            results.append({**deepcopy(c), 'result': result})
    report = {'version': VERSION, 'input_hash': canonical_hash(value),
              'subject': value['subject'], 'question': value['question'],
              'predecessor': value['predecessor'], 'analysis_cutoff': value['analysis_cutoff'],
              'reviewed_at': value['reviewed_at'], 'sources': deepcopy(value['sources']),
              'source_gaps': gaps, 'historical_knowledge': 'NOT_ESTABLISHED_BY_RETRIEVAL_CLOCK',
              'observations': list(observations.values()),
              'comparisons': results, 'remaining_evidence': value['remaining_evidence'],
              'authority': deepcopy(AUTHORITY),
              'qualification': 'REVIEWED_DECLARATIONS_AND_BYTE_ARITHMETIC_NOT_INDEPENDENT_ECONOMIC_TRUTH'}
    report['report_hash'] = canonical_hash(report)
    return report


def render(report):
    lines = [f"# {escape(report['subject'])}: reviewed comparison", escape(report['question']),
             report['qualification'], 'Investment authority: NONE',
             'Source qualification is declared; bytes and arithmetic do not upgrade it.']
    lines += ['## Source and knowledge limits', report['historical_knowledge']]
    for source in report['sources']:
        lines.append(escape(f"{source['id']}: {source['qualification']} | {source['ref']}:{source['path']} | published={source['published_at']}; acquired={source['acquired_at']}"))
    for observation in report['observations']:
        lines.append(escape(f"{observation['id']}: {observation['status']} | {observation['value']} × {observation['scale']} {observation['currency']} | {observation['scope']} | {observation['period']} | source={observation['source_id']}"))
    for c in report['comparisons']:
        lines += [f"## {escape(c['id'])}: {c['kind']}",
                  f"{c['result']['status']}: {c['result']['value']} {c['result'].get('unit', '')}",
                  escape(c['compatibility_note']), escape(c['interpretation']),
                  escape(c['challenge_disposition']), escape(c['limitations'])]
        if 'relation' in c['result']:
            lines.append(escape(canonical_json(c['result'])))
    lines += ['## Remaining evidence', escape(report['remaining_evidence'])]
    return '\n\n'.join(lines) + '\n'


def read_comparison(path, *, expected_sha256, source_files):
    raw = _read(Path(path))
    require(state.sha256(raw) == expected_sha256, 'externally pinned comparison hash differs')
    # Input contract contains decimal strings; source JSON alone uses Decimal lexemes.
    value = json.loads(raw, object_pairs_hook=_unique_input)
    return build(value, source_files)


def _unique_input(pairs):
    out = {}
    for k, v in pairs:
        require(k not in out, 'duplicate input key')
        out[k] = v
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input'); p.add_argument('--sha256', required=True)
    p.add_argument('--source', action='append', default=[], metavar='ID=LOCAL_FILE')
    p.add_argument('--output', required=True)
    a = p.parse_args(); files = {}
    for spec in a.source:
        sid, path = spec.split('=', 1)
        require(sid not in files, 'duplicate source argument')
        files[sid] = _read(Path(path))
    report = read_comparison(a.input, expected_sha256=a.sha256, source_files=files)
    _publish_report_files(Path(a.output), {
        'comparison.json': (canonical_json(report) + '\n').encode(),
        'comparison.md': render(report).encode(),
    }, write_file=_write)


if __name__ == '__main__':
    main()
