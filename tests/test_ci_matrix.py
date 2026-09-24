"""Native matrix/needs contracts; these checks retire with this execution layout."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import runpy
import zipfile
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
R = runpy.run_path(str(ROOT / '.github/scripts/ci-merge-reuse.py'))
M = runpy.run_path(str(ROOT / '.github/scripts/ci-matrix.py'))


def xml(module, test):
    return (f'<testsuites><testsuite tests="1" errors="0" failures="0" skipped="0" time="1">'
            f'<testcase classname="tests.{module}" name="{test}" time="0.5"/>'
            '</testsuite></testsuites>').encode()


def bundle(files, name, identity):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for path, raw in files.items(): z.writestr(path, raw)
    raw = stream.getvalue()
    return raw, dict(id=1, expired=False, name=name, size_in_bytes=len(raw),
                    digest='sha256:' + hashlib.sha256(raw).hexdigest(),
                    workflow_run=dict(id=int(identity['run_id']), head_sha=identity['code_sha']))


def fixture():
    identity = dict(code_sha='a' * 40, event='pull_request', run_id='10', attempt='1')
    env = dict(tree='b' * 40, python='synthetic', packages={'pytest': 'synthetic'},
               machine='x86_64', platform='linux', runner_os='Linux', runner_arch='X64',
               image_os='ubuntu', image_version='synthetic')
    paths = ['tests/test_domain.py']
    collection = 'tests/test_domain.py::test_domain\n' + ''.join(f'tests/test_part.py::test_{g}\n' for g in range(1, 5))
    source = ''.join(k + '=' + v + '\n' for k, v in identity.items())
    files = []
    for group in range(1, 5):
        files.append({'identity.txt': source, 'environment.json': json.dumps(env),
            'selected-collection.txt': f'tests/test_part.py::test_{group}\n',
            'shard.xml': xml('test_part', f'test_{group}'),
            'shard.json': json.dumps(dict(group=group, splits=4, test_count=1,
                timing_sha256='c' * 64, scope='remaining-shard-v2', merge_eligible=False))})
    def pack(all_files):
        return [bundle(f, f'kernel-ci-shard-{g}-10-1', identity) for g, f in enumerate(all_files, 1)]
    return identity, env, paths, collection, files, pack


def test_native_needs_checks_all_outcomes_and_keeps_nonfull_scopes_distinct():
    good = dict(prepare=dict(result='success', outputs=dict(scope='full')),
                **{'contracts-v2': dict(result='success'), 'remaining-v2': dict(result='success')})
    assert M['check_needs'](good) == 'full'
    for job in good:
        for outcome in ('failure', 'cancelled', 'skipped', 'neutral', 'unknown'):
            bad = deepcopy(good); bad[job]['result'] = outcome
            with pytest.raises(ValueError): M['check_needs'](bad)
    for scope in ('content', 'draft_feedback', 'merge_reuse'):
        brief = deepcopy(good); brief['prepare']['outputs']['scope'] = scope
        with pytest.raises(ValueError): M['check_needs'](brief)
        brief['contracts-v2']['result'] = brief['remaining-v2']['result'] = 'skipped'
        assert M['check_needs'](brief) == scope
    with pytest.raises(ValueError): M['check_needs']({k: v for k, v in good.items() if k != 'remaining-v2'})


def test_real_shard_zips_require_complete_union_same_run_and_environment():
    identity, env, paths, collection, files, pack = fixture()
    def combine(f=files, e=env):
        return R['matrix_remaining'](collection, paths, pack(f), identity, e, 'c' * 64)
    result = combine()
    assert R['passed_test_set']('\n'.join(collection.splitlines()[1:]), result) == 4
    assert len(ET.fromstring(result).findall('testsuite')) == 4
    for field in ('code_sha', 'event', 'run_id', 'attempt'):
        bad = deepcopy(files); bad[0]['identity.txt'] = bad[0]['identity.txt'].replace(field + '=' + identity[field], field + '=wrong')
        with pytest.raises(ValueError): combine(bad)
    for field in ('tree', 'image_version', 'packages'):
        changed = deepcopy(env); changed[field] = {} if field == 'packages' else 'wrong'
        with pytest.raises(ValueError): combine(e=changed)
    for change in ({'group': True}, {'group': 2}, {'splits': 3}, {'timing_sha256': 'd' * 64},
                   {'merge_eligible': True}, {'test_count': True}):
        bad = deepcopy(files); bad[0]['shard.json'] = json.dumps({**json.loads(bad[0]['shard.json']), **change})
        with pytest.raises(ValueError): combine(bad)
    for field in ('selected-collection.txt', 'shard.xml'):
        bad = deepcopy(files); bad[0][field] = bad[1][field]
        with pytest.raises(ValueError): combine(bad)
    bad = deepcopy(files); bad[0]['selected-collection.txt'] = bad[1]['selected-collection.txt']; bad[0]['shard.xml'] = bad[1]['shard.xml']
    with pytest.raises(ValueError): combine(bad)  # Same count, duplicate one and omit another.
    with pytest.raises(ValueError): combine(files[:-1])
    for tag in ('failure', 'error', 'skipped'):
        bad = deepcopy(files); bad[0]['shard.xml'] = bad[0]['shard.xml'].replace(b'/>', f'><{tag}/></testcase>'.encode())
        with pytest.raises(ValueError): combine(bad)


def test_matrix_full_reader_rebuilds_inner_proof_not_only_aggregate_green():
    identity, env, paths, collection, files, pack = fixture()
    shards = pack(files)
    remaining = R['matrix_remaining'](collection, paths, shards, identity, env, 'c' * 64)
    source = ''.join(k + '=' + v + '\n' for k, v in identity.items())
    domain_files = dict({'identity.txt': source + 'scope=research-continuity-v2\n',
        'environment.json': json.dumps(env), 'domain-collection.txt': collection.splitlines()[0] + '\n',
        'domain.xml': xml('test_domain', 'test_domain'),
        'domain-result.json': json.dumps(dict(scope='research-continuity-v2', code_sha=identity['code_sha'],
            complete_domain='PASS', test_count=1, merge_eligible=False, full_suite='NOT_RUN_DOMAIN_ONLY'))})
    domain, metadata = bundle(domain_files, 'kernel-ci-v2-10-1', identity)
    merged = R['partition_junit'](collection, paths, remaining, domain, metadata, identity, env)
    all_files = {'identity.txt': source, 'environment.json': json.dumps(env),
        'scope.json': json.dumps(dict(scope='full', code_sha=identity['code_sha'], event='pull_request', full_suite='EXECUTED_MATRIX_V2')),
        'merge-reuse.json': json.dumps(dict(reuse=False, reason='PR_ALWAYS_FULL')),
        'partition.json': json.dumps(dict(paths=paths, artifact=metadata, shards=[a for _, a in shards], timing_sha256='c' * 64)),
        'collection.txt': collection, 'remaining.xml': remaining, 'domain-source.zip': domain, 'pytest.xml': merged,
        **{f'shard-{g}.zip': raw for g, (raw, _) in enumerate(shards, 1)}}
    def read(f):
        raw, a = bundle(f, 'kernel-ci-10-1', identity)
        return R['full_evidence'](raw, a, dict(id=10, head_sha=identity['code_sha']), env)
    assert read(all_files) == 5
    for key in ('partition.json', 'domain-source.zip', 'shard-2.zip'):
        with pytest.raises((KeyError, ValueError)): read({k: v for k, v in all_files.items() if k != key})
    for key in ('pytest.xml', 'remaining.xml', 'shard-1.zip'):
        with pytest.raises(ValueError): read({**all_files, key: all_files[key] + b'changed'})
    bad = dict(all_files); bad['scope.json'] = bad['scope.json'].replace('EXECUTED_MATRIX_V2', 'EXECUTED_PARTITIONED_V2')
    with pytest.raises(ValueError): read(bad)


def test_workflow_graph_uses_native_dependency_and_fixed_splitter_not_racing_reads():
    def workflow(name):
        return yaml.load((ROOT / '.github/workflows' / name).read_text(), Loader=yaml.BaseLoader)
    jobs = workflow('ci.yml')['jobs']
    assert set(jobs['test']['needs']) == {'prepare', 'contracts-v2', 'remaining-v2'}
    assert jobs['test']['if'] == 'always()'
    for name in ('contracts-v2', 'remaining-v2'):
        assert jobs[name]['needs'] == 'prepare'
        assert jobs[name]['if'] == "needs.prepare.outputs.scope == 'full'"
        assert (ROOT / jobs[name]['uses'][2:]).is_file()
    shard = workflow('ci-full-v2.yml')['jobs']['shard']
    assert shard['strategy']['matrix']['group'] == ['1', '2', '3', '4']
    assert shard['strategy']['fail-fast'] == 'false'
    assert 'continue-on-error' not in shard
    for name in ('ci-prepare.yml', 'ci-contracts-v2.yml', 'ci-full-v2.yml'):
        assert set(workflow(name)['on']) == {'workflow_call'}
    assert 'partition_operation' not in R  # Old temporal assembler retired, reader remains.
    assert {'matrix_remaining', 'partition_junit', 'passed_test_set'} <= R.keys()


def test_duration_input_is_only_a_hint_and_preserves_exact_node_addresses(monkeypatch):
    collection = 'tests/test_part.py::test_1\n'
    assert M['durations'](collection, xml('test_part', 'test_1')) == {'tests/test_part.py::test_1': 0.5}
    monkeypatch.setenv('CI_BASE_SHA', 'unknown')
    assert M['duration_hint']() == {}
