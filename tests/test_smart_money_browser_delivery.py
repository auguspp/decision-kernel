"""Full data delivery must not depend on optional offline view size."""
import base64
from copy import deepcopy
import gzip
from hashlib import sha256
import json
import re

import pytest

from decision_kernel.runtime import smart_money_view as v, smart_money_reading as r
from decision_kernel.runtime import smart_money_sources as s
from test_smart_money import captured
from test_smart_money_reading import setup


def test_browser_projection_preserves_all_records_and_consumed_fields(tmp_path):
    observation,_=captured(tmp_path)
    history=v.history(observation)
    chunks,meta=v.encode_chunks(history)
    before=deepcopy((chunks,meta,history))
    page=v.browser(v.summarize(observation,history),chunks,meta,{})
    payload=json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>',page,re.S)[1])
    assert payload['projection'].startswith('DISPLAY_RECORDS_WITHOUT_UNUSED_ID')
    actual=[]
    for projected in payload['chunks']:
        ref=projected['ref'];raw=base64.b64decode(projected['base64'])
        assert len(raw)==ref['bytes'] and sha256(raw).hexdigest()==ref['sha256']
        decoded=gzip.decompress(raw)
        assert len(decoded)==ref['expanded_bytes']
        values=json.loads(decoded);assert len(values)==ref['rows']
        original=projected['original_ref']
        assert original in meta['chunks']
        source=json.loads(gzip.decompress(chunks[original['name']]))
        for a,b in zip(values,source,strict=True):
            assert 'id' not in a['data'] and 'id' in b['data']
            expected=deepcopy(b);del expected['data']['id']
            assert a==expected
        actual.extend(values)
    assert len(actual)==meta['record_count']==len(history['records'])
    assert (chunks,meta,history)==before
    assert 'withdrawn_from_source_snapshot_at' in page


def test_browser_size_only_error_keeps_qualified_data_and_progress(tmp_path,monkeypatch):
    col,baseline,*_=setup(tmp_path)
    def oversized(*args,**kwargs):raise s.SourceError('BROWSER_OUTPUT_BOUND')
    monkeypatch.setattr(v,'browser',oversized)
    result=r.attach(col,baseline)
    sm=result['research']['smart_money']
    assert sm['status']=='READY' and sm['pending_delivery_count']==0
    assert sm['browser_status']=='DISPLAY_SIZE_LIMIT_CANONICAL_DATA_RETAINED'
    assert sm['details']['history']['read_path'] in col.files
    assert '完整资料已保存'.encode() in col.files[sm['details']['browser']['read_path']]
    state=json.loads(col.files[sm['details']['state']['read_path']])
    assert state['unresolved']==[]
    assert result['lanes']==baseline['lanes']


def test_other_browser_identity_error_still_rejects_optional_composition(tmp_path,monkeypatch):
    col,baseline,*_=setup(tmp_path)
    def bad_identity(*args,**kwargs):raise s.SourceError('HISTORY_CHUNK_IDENTITY')
    monkeypatch.setattr(v,'browser',bad_identity)
    sm=r.attach(col,baseline)['research']['smart_money']
    assert sm['status']=='OPTIONAL_PUBLICATION_GAP'
    assert 'details' not in sm


def test_projection_checks_original_digest_before_reencoding(tmp_path):
    observation,_=captured(tmp_path);history=v.history(observation)
    chunks,meta=v.encode_chunks(history);key=next(iter(chunks));chunks[key]+=b'x'
    with pytest.raises(s.SourceError,match='HISTORY_CHUNK_IDENTITY'):
        v.browser_chunks(chunks,meta)
