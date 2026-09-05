from __future__ import annotations
import copy
import json
import runpy
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
from decision_kernel.identity import canonical_hash, canonical_json

SCRIPT = Path('.github/scripts/capture-muyuan-filing.py')
M = runpy.run_path(str(SCRIPT))
NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)
SYMBOLS = {'stockList': [{'code': '002714', 'orgId': 'org002714'}]}


def payload(title='2026年半年度报告', **changes):
    row = dict(secCode='002714', orgId='org002714', announcementId='1225000000',
        announcementTitle=title, announcementTime=int(datetime(2026, 8, 21, tzinfo=timezone.utc).timestamp() * 1000),
        adjunctUrl='finalpage/2026-08-21/1225000000.PDF')
    row.update(changes)
    return {'hasMore': False, 'totalAnnouncement': 1, 'announcements': [row]}


def source_reply(spec):
    if spec == M['FIRST']:
        return 200, json.dumps(SYMBOLS).encode()
    if spec == M['query'](SYMBOLS):
        return 200, json.dumps(payload()).encode()
    assert spec == M['select'](payload(), M['query'](SYMBOLS))[0]
    return 200, b'%PDF-1.4\nSYNTHETIC NOT A REAL DOCUMENT'


def captured(tmp_path, response=source_reply):
    calls = []
    def request(spec):
        calls.append(copy.deepcopy(spec))
        return response(spec)
    root = tmp_path / 'capture'
    record = M['run'](root, request=request, now=lambda: NOW)
    return root, record, calls


def test_complete_uses_exact_three_requests_and_reconstructs(tmp_path):
    root, record, calls = captured(tmp_path)
    assert len(calls) == 3 and record['status'] == 'ORIGINAL_CAPTURED_REVIEW_REQUIRED'
    assert record['provenance'] == 'SYNTHETIC_TEST_ONLY'
    assert M['verify'](root) == record
    assert record['selected']['announcement_id'] == '1225000000'
    assert record['market_state_writes'] == record['events_created'] == 0
    assert set(p.name for p in root.iterdir()) == {'capture.json', '01.json', '02.json', '03.pdf'}
    assert calls[1]['params']['seDate'] == '2026-08-01~2026-09-06'
    assert 'X-api-key' not in canonical_json(record)


@pytest.mark.parametrize('change', ['summary', 'duplicate', 'different-company', 'different-org', 'future', 'truncated', 'foreign-pdf'])
def test_full_original_selection_fails_without_guessing(change):
    value = payload()
    row = value['announcements'][0]
    if change == 'summary': row['announcementTitle'] += '摘要'
    elif change == 'duplicate':
        value['announcements'].append(copy.deepcopy(row)); value['totalAnnouncement'] = 2
    elif change == 'different-company': row['secCode'] = '300498'
    elif change == 'different-org': row['orgId'] = 'anotherorg'
    elif change == 'future': row['announcementTime'] = int((NOW + timedelta(days=2)).timestamp() * 1000)
    elif change == 'truncated': value['hasMore'] = True
    elif change == 'foreign-pdf': row['adjunctUrl'] = 'https://other.test/document.pdf'
    with pytest.raises(ValueError):
        M['select'](value, M['query'](SYMBOLS))


def test_report_summary_does_not_conflict_with_unique_full_report():
    value = payload()
    value['announcements'].append(payload('2026年半年度报告摘要')['announcements'][0] | {'announcementId': '1225000001', 'adjunctUrl': 'finalpage/2026-08-21/1225000001.PDF'})
    value['totalAnnouncement'] = 2
    assert M['select'](value, M['query'](SYMBOLS))[1]['announcement_id'] == '1225000000'


@pytest.mark.parametrize('status', [403, 429, 500])
def test_http_failure_has_no_retry_no_error_body_and_preserves_attempt(tmp_path, status):
    root, record, calls = captured(tmp_path, lambda spec: (status, b'private error not retained'))
    assert len(calls) == 1 and record['status'] == 'INCOMPLETE'
    assert record['requests'][0]['http_status'] == status and record['files'] == []
    assert 'private error' not in (root / 'capture.json').read_text()
    assert M['verify'](root) == record


def test_no_pdf_on_ambiguous_query_and_error_message_not_saved(tmp_path):
    def reply(spec):
        if spec == M['FIRST']: return source_reply(spec)
        return 200, json.dumps(payload('2026年半年度报告摘要')).encode()
    root, record, calls = captured(tmp_path, reply)
    assert len(calls) == 2 and record['status'] == 'INCOMPLETE'
    assert len(record['files']) == 2
    assert M['verify'](root) == record


def test_archive_rejects_modified_raw_extra_file_and_rehashed_plan(tmp_path):
    root, record, _ = captured(tmp_path)
    pdf = root / '03.pdf'; saved = pdf.read_bytes(); pdf.write_bytes(saved + b'!')
    with pytest.raises(ValueError): M['verify'](root)
    pdf.write_bytes(saved)
    extra = root / 'unknown'; extra.write_text('x')
    with pytest.raises(ValueError): M['verify'](root)
    extra.unlink()
    record['requests'][1]['spec']['params']['stock'] = '300498,otherorg'
    record['capture_hash'] = canonical_hash({k:v for k,v in record.items() if k != 'capture_hash'})
    (root / 'capture.json').write_text(canonical_json(record))
    with pytest.raises(ValueError): M['verify'](root)


def test_existing_output_and_symbolic_link_refused(tmp_path):
    root, record, _ = captured(tmp_path)
    with pytest.raises(ValueError): M['run'](root, request=source_reply, now=lambda: NOW)
    alias = tmp_path / 'alias'; alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError): M['verify'](alias)


def test_workflow_reuses_existing_file_and_keeps_legacy_opt_in():
    raw = Path('.github/workflows/stock-field-source-study.yml').read_text()
    assert 'study-purpose:' in raw and 'default: livestock-filing' in raw
    assert "if: github.event_name == 'workflow_dispatch' && inputs.study-purpose == 'remaining-listings'" in raw
    assert "if: github.event_name == 'push' || inputs.study-purpose == 'livestock-filing'" in raw
    assert '.github/scripts/capture-muyuan-filing.py' in raw
    assert 'schedule:' not in raw and 'secrets.' not in raw
    new = raw.split('  livestock-original:', 1)[1]
    assert 'actions/download-artifact' not in new and 'HiThink' not in new
    assert 'capture muyuan-original/capture' in new and 'verify muyuan-original/capture' in new
    assert 'if: always()' in new and 'retention-days: 90' in new
