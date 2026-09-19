"""Explicit archive locators, not eagerly read Research or execution authority.

This is a pure projection of the existing purpose registry. The original archive
reader remains responsible for fetching and validating every byte on demand.
"""
from __future__ import annotations

from copy import deepcopy
from html import escape
from pathlib import PurePosixPath
import re
from urllib.parse import quote

from . import current_state as model

POLICY = 'ON_DEMAND_ARCHIVE'
QUALIFICATION = 'REGISTERED_ARCHIVE_NOT_MATERIALIZED'
SOURCE_KEYS = {'path', 'ref', 'git_blob', 'sha256', 'bytes'}


def project(record: dict) -> dict:
    """Validate a declaration only. No I/O, body qualification or auto promotion."""
    from . import research_archive as archive

    model.check(record.get('read_policy') == POLICY
                and record.get('use') == 'RETAINED_RESEARCH_DOCUMENT',
                'on-demand policy is limited to retained research documents')
    for key in ('id', 'case', 'purpose_note'):
        model.check(isinstance(record.get(key), str) and bool(record[key]),
                    'archive index identity missing')
    model.check(archive.NAME.fullmatch(record['id']) is not None, 'archive index id invalid')
    model.check('source' not in record, 'on-demand registration must not declare an eager source')
    source = record['archive_source']
    model.check(isinstance(source, dict) and set(source) == SOURCE_KEYS,
                'archive index needs exact source metadata without executable selectors')
    path = model.safe_path(source['path'])
    parent = PurePosixPath(path).parent
    model.check(parent.as_posix().startswith(('research_runs/', 'docs/readings/'))
                and len(parent.parts) >= 3 and archive.NAME.fullmatch(PurePosixPath(path).name) is not None,
                'archive index root unsupported')
    archive._sha(source['ref']); archive._sha(source['git_blob'])
    model.check(isinstance(source['sha256'], str)
                and re.fullmatch(r'[0-9a-f]{64}', source['sha256']) is not None
                and type(source['bytes']) is int and 0 <= source['bytes'] <= archive.MAX_FILE_BYTES,
                'archive index byte identity invalid')
    config = record['archive']
    model.check(isinstance(config, dict) and config.get('format') in {'RETAINED_FILES', 'RESEARCH_PROGRESS'}
                and set(config) == archive.FORMATS[config['format']], 'archive index format unsupported')
    if config['format'] == 'RESEARCH_PROGRESS':
        model.check(isinstance(config['expected_sha256'], str)
                    and re.fullmatch(r'[0-9a-f]{64}', config['expected_sha256']) is not None,
                    'archive index progress digest missing')
        archive.retained._progress_identity(config['question_id'])
    return {**{k: record[k] for k in ('id', 'case', 'use', 'purpose_note')},
            'read_policy': POLICY, 'qualification': QUALIFICATION,
            'source': {'repository': model.REPOSITORY, **deepcopy(source)},
            'archive': deepcopy(config), 'body_materialized_in_reading': False,
            'meaning': 'REGISTERED_LOCATOR_ONLY_NOT_BODY_READ_RESEARCH_ACCEPTANCE_OR_CONTINUATION'}


def validate(entry: dict) -> None:
    """Do not let a rehashed/foreign/malformed locator become a trusted link."""
    source = entry['source']
    model.check(source.get('repository') == model.REPOSITORY
                and set(source) == SOURCE_KEYS | {'repository'}, 'archive index source differs')
    declared = {k: entry[k] for k in ('id', 'case', 'use', 'purpose_note', 'read_policy', 'archive')}
    declared['archive_source'] = {k: source[k] for k in SOURCE_KEYS}
    model.check(entry == project(declared), 'archive index projection differs')


def split(registry: dict) -> tuple[dict, list[dict], list[dict]]:
    """Keep every implicit eager record untouched; reject unknown opt-in policies."""
    eager, entries, gaps = [], [], []
    ids = [r['id'] for r in registry['references']]
    for record in registry['references']:
        if 'read_policy' not in record:
            eager.append(record)
            continue
        try:
            model.check(ids.count(record['id']) == 1, 'archive index id ambiguous')
            entries.append(project(record))
        except (ValueError, KeyError, TypeError, AttributeError):
            gaps.append({'id': record.get('id'), 'status': 'ARCHIVE_INDEX_DECLARATION_REJECTED',
                         'meaning': 'NOT_AN_EMPTY_RESEARCH_RESULT; NO_EAGER_FALLBACK'})
    return {**registry, 'references': eager}, entries, gaps


def entry_url(entry: dict) -> str:
    validate(entry)
    source = entry['source']
    return ('https://github.com/' + model.REPOSITORY + '/blob/' + source['ref'] + '/'
            + quote(source['path'], safe='/'))


def navigation(entries: list[dict]) -> str:
    """Explicit historical archive navigation, never an inferred same-R body link."""
    if not entries:
        return ''
    def text(value):
        value = escape(str(value), quote=True).replace('\n', ' ').replace('\r', ' ')
        for char in '`[]()|*_!': value = value.replace(char, '&#' + str(ord(char)) + ';')
        return value
    lines = ['', '## 按需恢复的已登记研究档案', '',
             '下列仅有精确档案定位，正文未纳入本读取；不是已读研究、待判断请求或新Pre/Quick。',
             '从本次固定R使用既有research_archive与record-id恢复，仍须核验完整目录、字节和进度。', '']
    for row in entries:
        url = entry_url(row)
        lines.append('- ' + text(row['case']) + ' / [' + text(row['id']) + '](' + url + ') — '
                     + text(row['purpose_note']) + '；状态：正文按需恢复，未在本包物化。')
    return '\n'.join(lines) + '\n'
