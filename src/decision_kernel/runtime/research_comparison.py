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
from .research_commit_only import _read, _write, _safe_path

VERSION = 'reviewed-research-comparison-v0'
AUTHORITY = {'investment_authority': 'NONE', 'human_acceptance': 'NOT_ESTABLISHED',
             'network_requests': 0, 'model_calls': 0, 'research_committed': False,
             'economic_adequacy': 'NOT_CERTIFIED_BY_ARITHMETIC'}
KINDS = {'PERIOD_CHANGE', 'SOURCE_REVISION', 'RESEARCH_CORRECTION',
         'EVIDENCE_COVERAGE_CHANGE', 'CHECKED_UNCHANGED', 'NOT_CHECKED',
         'INCOMPARABLE', 'CASH_DIAGNOSTIC', 'DERIVED_QUARTER'}
OPS = {'difference', 'signed_sum', 'ratio', 'quarter', 'coverage', 'claim'}
SCALES = {'1', '10000', '100000000', '1000000000'}


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
        require(s['qualification'] in {'RETAINED_RESEARCH', 'ISSUER_DISCLOSURE_BYTES', 'SYNOPSIS'},
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


def selected(raw, locator):
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
            result = {'status': 'SOURCE_BYTES_UNAVAILABLE', 'value': None} if missing else evaluate(c, rows)
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
    out = Path(a.output); _safe_path(out); out.mkdir(parents=False, exist_ok=False)
    _write(out / 'comparison.json', (canonical_json(report) + '\n').encode())
    _write(out / 'comparison.md', render(report).encode())


if __name__ == '__main__':
    main()
