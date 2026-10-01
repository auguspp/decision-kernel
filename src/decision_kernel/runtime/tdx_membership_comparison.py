"""Compare two pinned, saved TDX member observations; never infer effective dates.

Reuse the read-package/byte identity and create-only report contracts. No source
client, backfill, as-of join, interpolation, ranking or production admission.
"""
from __future__ import annotations

import argparse
from datetime import date
from html import escape
from pathlib import Path
import re

from decision_kernel.identity import canonical_hash, canonical_json
from . import current_state as model
from .research_commit_only import _json, _publish_report_files, _safe_path

VERSION = 'tdx-observed-membership-comparison-v1'
MEMBER_PATH = 'details/radar/tdx-concept/membership.json'
MAX_MEMBER_BYTES = 1024 * 1024  # Existing membership output bound, not archive expansion.
TIME_BASIS = 'SAVED_SOURCE_PREPARATION_NOT_HISTORICAL_EFFECTIVE_MEMBERSHIP'
TAXONOMY = 'TDX_CATEGORY_CONCEPT_SOURCE_NATIVE_NOT_EASTMONEY_BK_OR_HITHINK_TI'
AUTHORITY = {k: 'NONE' for k in ('research_authority', 'odds_authority',
                               'action_authority', 'investment_authority')}


def _snapshot(root_raw, member_raw, ref, expected_hash):
    model.check(isinstance(root_raw, bytes) and len(root_raw) <= 192 * 1024,
                'bounded reading bytes required')
    model.check(isinstance(member_raw, bytes) and len(member_raw) <= MAX_MEMBER_BYTES,
                'bounded membership bytes required')
    model.check(isinstance(ref, str) and model.SHA.fullmatch(ref), 'exact reading ref required')
    model.check(isinstance(expected_hash, str) and re.fullmatch(r'[0-9a-f]{64}', expected_hash),
                'independently pinned reading hash required')
    root = _json(root_raw)
    model.validate_read_package(root)
    model.check(root['reading_hash'] == expected_hash, 'reading differs from supplied pin')
    section = root['research']['tdx_concept_context']
    declared = section['membership']
    model.check(section['status'] == 'VERIFIED_SAVED_TDX_CONCEPT_SOURCE'
                and declared['status'] == 'VERIFIED_SAVED_MEMBERSHIP', 'saved members unavailable')
    d = declared['file']
    model.check(d['read_path'] == MEMBER_PATH
                and d['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT'
                and type(d['bytes']) is int and d['bytes'] == len(member_raw)
                and d['sha256'] == model.sha256(member_raw)
                and d['git_blob'] == model.blob_sha(member_raw), 'same-reading member bytes differ')
    value = _json(member_raw)
    p = value['projection']
    model.check(value['projection_hash'] == canonical_hash(p) == declared['projection_hash'],
                'membership projection differs')
    model.check(p['version'] == 'tdx-concept-membership-v1'
                and p['taxonomy'] == section['result']['taxonomy'] == TAXONOMY
                and p['membership_time_basis'] == TIME_BASIS
                and p['historical_membership'] == 'NOT_ESTABLISHED'
                and p['member_ranking'] == 'NOT_COMPUTED'
                and p['business_benefit'] == 'NOT_ESTABLISHED'
                and type(p['source_calls']) is int and p['source_calls'] == 0
                and all(p[k] == section[k] == v for k, v in AUTHORITY.items()),
                'membership semantics differ')
    model.check(p['market_session'] == section['result']['market_session']
                and p['observation_hash'] == section['result']['projection_hash'],
                'membership source observation differs')
    for key in ('market_session', 'source_prepared_date'):
        model.check(date.fromisoformat(p[key]).isoformat() == p[key], 'invalid source date')
    model.check(model.clock(p['source_observed_at']) <= model.clock(root['generated_at']),
                'membership observation follows reading')
    model.check(isinstance(p['capture_hash'], str)
                and re.fullmatch(r'[0-9a-f]{64}', p['capture_hash']), 'capture identity missing')
    rows, catalog, securities = p['concepts'], {}, set()
    model.check(isinstance(rows, list) and rows, 'empty member catalog is not no change')
    for row in rows:
        code, name, members = row['code'], row['name'], row['members']
        model.check(isinstance(code, str) and re.fullmatch(r'[0-9]{6}', code)
                    and code not in catalog and isinstance(name, str) and bool(name),
                    'duplicate or invalid concept identity')
        model.check(isinstance(members, list) and all(isinstance(x, str)
                    and re.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)', x) for x in members),
                    'full security identity required')
        model.check(len(set(members)) == len(members), 'duplicate member identity')
        catalog[code] = row
        securities.update(members)
    count = sum(len(r['members']) for r in rows)
    model.check(type(p['catalog_count']) is int and type(p['relation_count']) is int
                and p['catalog_count'] == declared['catalog_count'] == len(rows)
                and p['relation_count'] == declared['relation_count'] == count
                and count <= 200000 and set(p['securities']) == securities,
                'complete membership denominator differs')
    origin = {'reading_ref': ref, 'reading_hash': expected_hash,
              'reading_sha256': model.sha256(root_raw), 'file': dict(d),
              'reading_generated_at': root['generated_at'],
              'membership_hash': value['projection_hash'],
              **{k: p[k] for k in ('capture_hash', 'observation_hash', 'parser_version',
                                  'source_observed_at', 'source_prepared_date', 'market_session')}}
    return p, catalog, origin


def build(before_reading, before_membership, after_reading, after_membership, *,
          before_ref, after_ref, before_hash, after_hash):
    """Caller obtains refs/pins from trusted GitHub reads, not the candidate files.

    Historical roots are deliberately distinct. Only each root's own member body
    may join it. A later publication can repeat a source without a new observation.
    """
    b, left, old = _snapshot(before_reading, before_membership, before_ref, before_hash)
    a, right, new = _snapshot(after_reading, after_membership, after_ref, after_hash)
    model.check(before_ref != after_ref or before_hash == after_hash, 'one ref has two readings')
    model.check(model.clock(old['reading_generated_at']) <= model.clock(new['reading_generated_at'])
                and model.clock(b['source_observed_at']) <= model.clock(a['source_observed_at'])
                and b['market_session'] <= a['market_session'], 'observations or readings reversed')
    model.check(b['parser_version'] == a['parser_version'], 'membership parser versions differ')
    same = old['membership_hash'] == new['membership_hash']
    if b['capture_hash'] == a['capture_hash'] or b['source_observed_at'] == a['source_observed_at']:
        model.check(same, 'same source observation has contradictory membership')
    changes, relation_changes, added, removed = [], 0, 0, 0
    for code in sorted(left.keys() | right.keys()):
        before, after = left.get(code), right.get(code)
        lset = set(before['members']) if before else set()
        rset = set(after['members']) if after else set()
        plus, minus = sorted(rset - lset), sorted(lset - rset)
        renamed = before is not None and after is not None and before['name'] != after['name']
        added += len(plus); removed += len(minus)
        relation_changes += bool(plus or minus)
        if plus or minus or renamed or before is None or after is None:
            changes.append({'code': code, 'before_name': before['name'] if before else None,
                            'after_name': after['name'] if after else None,
                            'catalog_status': 'BOTH' if before and after else
                                              'ONLY_AFTER' if after else 'ONLY_BEFORE',
                            'before_count': len(lset) if before else None,
                            'after_count': len(rset) if after else None,
                            'present_at_both_observations': len(lset & rset),
                            'observed_added': plus, 'observed_removed': minus,
                            'name_changed': renamed, 'effective_change_date': None})
    total_before, total_after = b['relation_count'], a['relation_count']
    model.check(total_after - total_before == added - removed, 'relationship reconciliation failed')
    payload = {'version': VERSION, 'before': old, 'after': new,
               'status': 'SAME_SAVED_OBSERVATION' if same else 'TWO_SAVED_OBSERVATIONS_COMPARED',
               'taxonomy': TAXONOMY, 'membership_time_basis': TIME_BASIS,
               'coverage': {'before_concepts': len(left), 'after_concepts': len(right),
                            'union_concepts': len(left.keys() | right.keys()),
                            'catalog_added': sorted(right.keys() - left.keys()),
                            'catalog_removed': sorted(left.keys() - right.keys()),
                            'before_relations': total_before, 'after_relations': total_after,
                            'observed_added_relations': added, 'observed_removed_relations': removed,
                            'present_at_both_observations': total_before - removed,
                            'concepts_with_relation_changes': relation_changes,
                            'unchanged_observed_concepts': len(left.keys() | right.keys()) - len(changes)},
               'changes': changes, 'historical_effective_membership': 'NOT_ESTABLISHED',
               'between_observations_continuity': 'NOT_ESTABLISHED',
               'historical_pit_knowledge': 'NOT_ESTABLISHED',
               'multi_horizon_stock_roles': 'NOT_COMPUTED', 'source_calls': 0,
               'signal_changes': False, **AUTHORITY}
    payload['report_hash'] = canonical_hash(payload)
    return payload


def render(report):
    c = report['coverage']
    lines = ['# TDX 成员：两次保存观察的变化', '',
             f"观察端点：{escape(report['before']['source_observed_at'])} → {escape(report['after']['source_observed_at'])}",
             f"状态：{report['status']}", '',
             f"完整概念：{c['before_concepts']} → {c['after_concepts']}；成员关系：{c['before_relations']} → {c['after_relations']}。",
             f"观察到新增 {c['observed_added_relations']} 条、移除 {c['observed_removed_relations']} 条；关系变化涉及 {c['concepts_with_relation_changes']} 个概念。", '',
             '**这是观察端点的差异，不是实际纳入/剔除日。两端相同也不证明中间从未变化。**',
             '目录缺失与零成员分开；名称只作展示，不用于跨来源归并。没有回填历史成员、5/20/60日角色或投资信号。', '',
             '| 概念代码 | 前名称 → 后名称 | 前/后人数 | 观察新增 | 观察移除 |',
             '|---|---|---:|---|---|']
    def text(value):
        result = escape(str(value) if value is not None else '本端目录无此概念').replace('\n', ' ').replace('\r', ' ')
        for char in '`[]()|*_!':
            result = result.replace(char, '&#' + str(ord(char)) + ';')
        return result
    for r in report['changes']:
        lines.append('| ' + ' | '.join((r['code'], text(r['before_name']) + ' → ' + text(r['after_name']),
                     str(r['before_count']) + '/' + str(r['after_count']),
                     ', '.join(r['observed_added']) or '无', ', '.join(r['observed_removed']) or '无')) + ' |')
    lines += ['', 'Investment authority: NONE', 'Report hash: ' + report['report_hash'], '']
    return '\n'.join(lines)


def _read(path, limit):
    path = Path(path)
    _safe_path(path)
    model.check(path.is_file(), 'regular input required')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    model.check(len(raw) <= limit, 'input byte bound exceeded')
    return raw


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for side in ('before', 'after'):
        for field in ('reading', 'membership', 'ref', 'hash'):
            parser.add_argument('--' + side + '-' + field, required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    result = build(_read(args.before_reading, 192 * 1024), _read(args.before_membership, MAX_MEMBER_BYTES),
                   _read(args.after_reading, 192 * 1024), _read(args.after_membership, MAX_MEMBER_BYTES),
                   before_ref=args.before_ref, after_ref=args.after_ref,
                   before_hash=args.before_hash, after_hash=args.after_hash)
    _publish_report_files(Path(args.output), {'comparison.json': (canonical_json(result) + '\n').encode(),
                                             'comparison.md': render(result).encode()})
    print(result['report_hash'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
