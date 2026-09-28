"""Read saved TDX members with the already adopted eltdx parser, never a client.

The caller first replays the original capture. This optional projection owns no
capture, clock, portfolio or Research state; old v1 capture bytes stay unchanged.
"""
from __future__ import annotations

import csv
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import re

from decision_kernel.identity import canonical_hash, canonical_json
from . import tdx_concept_snapshot as tdx

VERSION = 'tdx-concept-membership-v1'
FILES = ('infoharbor_block.dat', 'security_list.json', '.eltdx_board_cache.json')
MAX_READING_BYTES = 1024 * 1024


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def encoded(value: dict) -> bytes:
    raw = (canonical_json(value) + '\n').encode('utf-8')
    require(len(raw) <= MAX_READING_BYTES, 'MEMBERSHIP_READING_SIZE')
    return raw


def build(root: Path, observation: dict, receipt: dict) -> dict:
    """Derive current source membership only, after the caller's original replay."""
    require(version('eltdx') == tdx.ELTDX_VERSION, 'MEMBERSHIP_PARSER_VERSION')
    # Private pure-file seams are pinned to 3.2.2. Never call _prepare,
    # board_member_quotes, TdxClient, network discovery or a current local cache.
    from eltdx.helpers.boards import BoardService, _infoharbor_headers

    p = observation['projection']
    require(observation['projection_hash'] == canonical_hash(p)
            and p['version'] == tdx.VERSION and p['taxonomy'] == tdx.POLICY['taxonomy']
            and receipt['status'] == 'CAPTURED_TDX_CONCEPT_SNAPSHOT'
            and receipt['market_session'] == p['market_session']
            and all(p.get(k) == v == receipt.get(k) for k, v in tdx.AUTHORITY.items()),
            'MEMBERSHIP_SOURCE_SCOPE')
    directory = root / 'source-files'
    inputs = {}
    for name in FILES:
        path = directory / name
        require(path.is_file() and not path.is_symlink(), 'MEMBERSHIP_FILE_SCOPE')
        raw = path.read_bytes()
        identity = {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        require(0 < len(raw) <= tdx.MAX_FILE_BYTES
                and identity == receipt['files']['source-files/' + name], 'MEMBERSHIP_FILE_IDENTITY')
        inputs['source-files/' + name] = identity
    cache = json.loads((directory / '.eltdx_board_cache.json').read_bytes())
    require(cache['last_success_date'] == p['market_session']
            and cache['sha256']['infoharbor_block.dat'] == inputs['source-files/infoharbor_block.dat']['sha256']
            and tdx._clock(receipt['started_at']) <= tdx._clock(cache['downloaded_at'])
            <= tdx._clock(receipt['finished_at']), 'MEMBERSHIP_SOURCE_CLOCK')

    rows = json.loads((directory / 'security_list.json').read_bytes())
    require(isinstance(rows, list) and 0 < len(rows) <= 100000, 'MEMBERSHIP_SECURITY_SCOPE')
    security = {}
    for row in rows:
        market, code = row.get('market'), row.get('code')
        require(type(market) is int and market in (0, 1, 2)
                and isinstance(code, str) and re.fullmatch(r'[0-9]{6}', code)
                and (row.get('name') is None or isinstance(row['name'], str)), 'MEMBERSHIP_SECURITY_IDENTITY')
        require((market, code) not in security, 'MEMBERSHIP_DUPLICATE_SECURITY')
        security[market, code] = row

    headers = [r for r in _infoharbor_headers(directory / 'infoharbor_block.dat') if r[2] == 4]
    require(len({r[0] for r in headers}) == len(headers) == p['catalog_count']
            and {(code, name) for code, name, _ in headers}
            == {(r['code'], r['name']) for r in p['observations']}, 'MEMBERSHIP_CATALOG_BINDING')
    # Check every declared count separately: the SDK's final header may not be
    # the selected board. The SDK still owns all member parsing and ordering.
    counts = {}
    codes = {r['code'] for r in p['observations']}
    text = (directory / 'infoharbor_block.dat').read_text(encoding='gb18030')
    for row in csv.reader(text.splitlines()):
        if row and row[0].startswith('#') and len(row) >= 3 and row[2].strip() in codes:
            require(row[0].startswith('#GN_') and row[1].isdigit() and row[2].strip() not in counts,
                    'MEMBERSHIP_HEADER_COUNT')
            counts[row[2].strip()] = int(row[1])
    service = BoardService(None, data_dir=directory)
    service._security = security
    securities, concepts = {}, []
    for original in p['observations']:
        code = original['code']
        parsed = service._members_for({'board_code': code, 'category': 4, 'membership_key': ''})
        members = []
        for member in parsed['raw_members']:
            key = (member['market'], member['code'])
            require(type(key[0]) is int and key[0] in (0, 1, 2)
                    and isinstance(key[1], str) and re.fullmatch(r'[0-9]{6}', key[1]), 'MEMBERSHIP_MEMBER_IDENTITY')
            ticker = key[1] + '.' + ('SZ', 'SH', 'BJ')[key[0]]
            members.append(ticker)
            securities[ticker] = {'name': security.get(key, {}).get('name'), 'in_source_catalog': key in security}
        require(len(members) == len(set(members)) == counts.get(code)
                and len(members) <= 10000, 'MEMBERSHIP_COUNT_MISMATCH')
        concepts.append({'code': code, 'name': original['name'], 'members': members})
    require(sum(len(c['members']) for c in concepts) <= 200000, 'MEMBERSHIP_RELATION_BOUND')
    payload = {
        'version': VERSION, 'taxonomy': p['taxonomy'], 'market_session': p['market_session'],
        'membership_time_basis': 'SAVED_SOURCE_PREPARATION_NOT_HISTORICAL_EFFECTIVE_MEMBERSHIP',
        'source_prepared_date': p['prepared_date'], 'source_observed_at': cache['downloaded_at'],
        'observation_hash': observation['projection_hash'], 'capture_hash': receipt['capture_hash'],
        'parser_version': tdx.ELTDX_VERSION, 'inputs': inputs, 'concepts': concepts, 'securities': securities,
        'catalog_count': len(concepts), 'relation_count': sum(len(c['members']) for c in concepts),
        'historical_membership': 'NOT_ESTABLISHED', 'member_ranking': 'NOT_COMPUTED',
        'business_benefit': 'NOT_ESTABLISHED', 'source_calls': 0, **tdx.AUTHORITY,
    }
    result = {'projection': payload, 'projection_hash': canonical_hash(payload)}
    encoded(result)  # The actual consumer byte bound, not an expanded source allowance.
    return result
