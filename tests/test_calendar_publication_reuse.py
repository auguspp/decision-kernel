"""Saved calendar through native collection/publication; synthetic Git transport.

This is not live publisher acceptance, current BLS verification or a source call.
The existing native source, replay, proof, final budget and publisher all execute.
"""
import base64
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import current_state_delivery as d
from decision_kernel.runtime import research_calendar as cal
from decision_kernel.runtime import research_calendar_reading as r
from decision_kernel.runtime.read_blob_reuse import GitHubReadReuseAPI, pending_blob_writes
from test_research_calendar_reading import CONFIG, RAW, DIRECTORY

M, PRIOR, TREE, NEW = 'a'*40, 'b'*40, 'c'*40, 'd'*40


def setup(tmp_path, *, used=60, files=150, bad_tree=None):
    old = {f'kept/{n}.txt': str(n).encode() for n in range(files)}
    registry = {'schema_version': 1, 'capability_gaps': [], 'research_calendar': deepcopy(CONFIG)}
    reg = m.json_bytes(registry)
    regpath = 'sources/git/' + m.blob_sha(reg) + '/registry.json'
    old[regpath] = reg
    # These old entry blobs must NOT stand in for unknown/final replacements.
    old.update({'current-state.json': b'old root', 'README.md': b'old README'})
    api = GitHubReadReuseAPI('SYNTHETIC_LOCAL_ONLY', max_calls=d.MAX_API_CALLS)
    api.calls = used
    rows = [{'path': p, 'mode': '100644', 'type': 'blob', 'sha':m.blob_sha(b), 'size':len(b)}
            for p,b in old.items()]
    response = {'sha': TREE, 'truncated': False, 'tree': rows}
    if bad_tree == 'truncated': response['truncated'] = True
    elif bad_tree == 'wrong_tree': response['sha'] = 'e'*40
    elif bad_tree == 'duplicate': rows.append(deepcopy(rows[0]))
    elif bad_tree == 'symlink': rows[0]['mode'] = '120000'
    wire, posted = [], {}
    overrides = {}
    def call(method, endpoint, body=None):
        api.calls += 1
        assert api.calls <= api.max_calls
        wire.append((method, endpoint))
        if method == 'GET':
            if endpoint == 'git/commits/'+PRIOR: value = {'sha':PRIOR,'tree':{'sha':TREE}}
            elif endpoint == 'git/trees/'+TREE+'?recursive=1': value = response
            elif endpoint == 'contents/current-state.json?ref='+NEW:
                value = {'type':'file','encoding':'base64','sha':m.blob_sha(collector.files['current-state.json']),
                         'content':base64.b64encode(collector.files['current-state.json']).decode()}
            else:
                assert endpoint.startswith('contents/'+DIRECTORY+'/') and endpoint.endswith('?ref='+CONFIG['ref'])
                name = endpoint.split('?')[0].rsplit('/',1)[-1]
                raw = overrides.get(name, RAW[name])
                value = {'type':'file','encoding':'base64','sha':m.blob_sha(raw),
                         'content':base64.b64encode(raw).decode()}
        elif endpoint == 'git/blobs':
            raw = base64.b64decode(body['content']); value = {'sha':m.blob_sha(raw)}
            posted[value['sha']] = raw
        elif endpoint == 'git/trees':
            assert body['base_tree'] == TREE
            assert all(e['sha'] in posted or e['sha'] in api.proven_read_blobs for e in body['tree'])
            value = {'sha':'e'*40}
        elif endpoint == 'git/commits': value = {'sha':NEW}
        else:
            assert (method, endpoint, body) == ('PATCH','git/refs/heads/'+m.READ_REF,{'sha':NEW,'force':False})
            value = {'ref':'refs/heads/'+m.READ_REF}
        return SimpleNamespace(content=json.dumps(value).encode(), json=lambda:deepcopy(value))
    api._call = call  # Only HTTP transport. Native get/file/write run unchanged.
    class Collector(d.Collector):
        def lane(self, name):
            return {'health':'NO_SAVED_RUNS','latest_attempt':None,'last_qualified_result':None,'gaps':[]}
        def research(self, registry, *, include_work=True):
            # Synthetic surrounding Research; calendar adapter remains production code.
            return {'handoffs':{'active':[]},'records':[],'gaps':[],
                    'candidate_work':{'status':'NOT_CONFIGURED'},
                    'calendar':r.read_registered(self,registry['research_calendar'])}
    collector = Collector(api,M,tmp_path,previous_commit=PRIOR,now=lambda:'2026-10-06T02:00:00Z')
    collector.files = {p:b for p,b in old.items() if p not in {'current-state.json','README.md'}}
    collector.sources[(d.REGISTRY_PATH,M)] = (reg, {'read_path':regpath,'ref':M,'git_blob':m.blob_sha(reg),
        'sha256':m.sha256(reg),'bytes':len(reg),'repository':m.REPOSITORY,'path':d.REGISTRY_PATH,
        'read_ref_rule':'USE_THE_SAME_PINNED_READING_COMMIT'})
    return collector, wire, response, overrides, old


def test_calendar_and_final_collector_fit_same_180_call_envelope_and_publish(tmp_path):
    c,wire,_,_,old = setup(tmp_path)
    result = c.collect({})
    saved = result['research']['calendar']
    assert saved['status'] == r.STATUS and saved['event_count'] == 3
    assert saved['as_of'] == json.loads(RAW['calendar.json'])['as_of']
    assert c.api.calls == 66  # two proof reads plus four original calendar reads
    assert c.api.calls + len(c.files) + 5 > 180  # old repeated-upload budget rejects
    assert c.api.calls + pending_blob_writes(c.api,c.files) + 5 <= 180
    for n,ref in saved['files'].items(): assert c.files[ref['read_path']] == RAW[n]
    for p,b in old.items():
        if p not in {'current-state.json','README.md'}: assert c.files[p] == b
    m.validate_read_package(result)
    assert d.publish(c.api,c.files,PRIOR,M,result['reading_hash']) == NEW
    assert wire[-1] == ('PATCH','git/refs/heads/'+m.READ_REF)
    assert wire[-2] == ('GET','contents/current-state.json?ref='+NEW)
    assert c.api.calls <= 180 and c.api.blob_reuse_hits == len(old)-2
    assert d.MAX_API_CALLS == 180 and d.MAX_SOURCE_FILES == 60


@pytest.mark.parametrize('bad_tree',['truncated','wrong_tree','duplicate','symlink'])
def test_bad_complete_tree_proof_cannot_fetch_calendar_or_retry_later(tmp_path,bad_tree):
    c,wire,_,_,_ = setup(tmp_path,bad_tree=bad_tree)
    before = deepcopy(c.files)
    value = r.read_registered(c,CONFIG)
    assert value['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert value['diagnostic']['stage'] == 'PUBLICATION_REUSE'
    assert c.files == before and not c.api.proven_read_blobs and c.api.blob_reuse_origin is None
    count = c.api.calls
    with pytest.raises(ValueError,match='already failed'): c.api.prime_previous_reading(PRIOR)
    assert c.api.calls == count and len(wire) == 2


def test_successful_early_proof_is_not_queried_again_by_later_reader(tmp_path):
    c,wire,_,_,_ = setup(tmp_path)
    assert r.read_registered(c,CONFIG)['status'] == r.STATUS
    count = c.api.calls
    c.api.prime_previous_reading(PRIOR)
    assert c.api.calls == count and len([p for _,p in wire if p.startswith('git/')]) == 2
    with pytest.raises(ValueError,match='identity changed'): c.api.prime_previous_reading('e'*40)


def test_transport_proof_failure_is_not_retried_and_private_error_is_not_published(tmp_path):
    c,wire,_,_,_ = setup(tmp_path)
    original = c.api._call
    def unavailable(method,endpoint,body=None):
        if endpoint.startswith('git/trees/'):
            c.api.calls += 1
            raise RuntimeError('PRIVATE_TRANSPORT_BODY')
        return original(method,endpoint,body)
    c.api._call = unavailable
    value = r.read_registered(c,CONFIG)
    count = c.api.calls
    assert 'PRIVATE' not in json.dumps(value) and value['error_type']=='RuntimeError'
    with pytest.raises(ValueError,match='already failed'): c.api.prime_previous_reading(PRIOR)
    assert c.api.calls == count


def test_current_source_corruption_is_not_repaired_from_known_old_blobs(tmp_path):
    c,_,_,overrides,_ = setup(tmp_path)
    before = deepcopy(c.files)
    overrides['calendar.json'] = RAW['calendar.json'] + b'\n'
    value = r.read_registered(c,CONFIG)
    assert value['status'] == 'UNAVAILABLE_OR_REJECTED' and value['diagnostic']['code']=='SOURCE_BLOB_MISMATCH'
    assert c.files == before and c.api.blob_reuse_origin['commit']==PRIOR


def test_existing_proof_does_not_allow_unknown_root_replacements_for_free(tmp_path):
    c,_,_,_,_ = setup(tmp_path,used=0)
    c.api.prime_previous_reading(PRIOR)
    c.files.update({'current-state.json':b'old root','README.md':b'old README'})
    c.api.calls = 166
    before = deepcopy(c.files)
    value = r.read_registered(c,CONFIG)
    # Four source reads + six pending/possibly replaced files + five commit operations >180.
    assert value['status'] == 'UNAVAILABLE_OR_REJECTED' and value['diagnostic']['code']=='PUBLICATION_RESERVE'
    assert c.api.calls == 166 and c.files == before


def test_final_changed_root_bytes_cannot_reuse_old_root_budget(tmp_path,monkeypatch):
    c,_,_,_,_ = setup(tmp_path)
    def fill_budget(registry,research):
        c.api.calls = 171  # actual fresh entry/calendars cannot all fit
    monkeypatch.setattr(c,'include_research_work',fill_budget)
    with pytest.raises(ValueError,match='insufficient publication API budget'): c.collect({})
    assert c.api.calls == 171


def test_no_opt_in_keeps_original_calendar_failure_without_proof_requests(tmp_path):
    c,wire,_,_,_ = setup(tmp_path)
    c.api.__class__ = d.GitHubAPI  # exactly original transport contract; no reuse capability
    before = deepcopy(c.files)
    value = r.read_registered(c,CONFIG)
    assert value['diagnostic']['code']=='PUBLICATION_RESERVE'
    assert c.files == before and not wire and c.api.calls == 60
