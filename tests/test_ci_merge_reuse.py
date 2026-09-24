"""Real local merge/ZIP/XML verification; synthetic GitHub reads, no external calls."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.github/scripts/ci-merge-reuse.py'
S = runpy.run_path(str(SCRIPT))


class MergeReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Synthetic CI')
        self.git('config', 'user.email', 'ci@example.invalid')
        for path in S['POLICY']:
            self.put(path, 'initial policy\n')
        self.put('pyproject.toml', '# Synthetic packaging fixture\n')
        self.put('src/engine.py', 'old\n')
        self.base = self.commit()
        self.git('checkout', '-q', '-b', 'feature')
        self.put('src/engine.py', 'new\n')
        self.pr_head = self.commit()
        self.git('checkout', '-q', 'main')
        self.git('merge', '--no-ff', '-m', 'normal merge', 'feature')
        self.head = self.git('rev-parse', 'HEAD')
        self.env = dict(GITHUB_EVENT_NAME='push', GITHUB_REF='refs/heads/main',
            GITHUB_REPOSITORY=S['REPO'], GITHUB_RUN_ATTEMPT='1', CI_CODE_SHA=self.head,
            CI_BASE_SHA=self.base, ImageOS='ubuntu24', ImageVersion='synthetic-image',
            RUNNER_OS='Linux', RUNNER_ARCH='X64')
        self.report = self.root / '.git/reports'
        self.report.mkdir()
        (self.report/'packages.json').write_text('[{"name":"pytest","version":"synthetic"}]')
        self.current = S['environment'](self.root, self.report, self.env)
        self.run = dict(id=10, head_sha=self.pr_head, event='pull_request', name='kernel-tests',
            path=S['WORKFLOW'], head_repository={'full_name':S['REPO']}, run_attempt=1,
            status='completed', conclusion='success', pull_requests=[dict(number=5,
            head={'sha':self.pr_head}, base={'sha':self.base,'ref':'main'})])
        self.pr = dict(number=5, merged=True, merge_commit_sha=self.head,
            head={'sha':self.pr_head,'repo':{'full_name':S['REPO']}},
            base={'ref':'main','sha':self.base,'repo':{'full_name':S['REPO']}})
        self.files = {
            'identity.txt':f'code_sha={self.pr_head}\nevent=pull_request\nrun_id=10\nattempt=1\n',
            'environment.json':json.dumps(self.current),
            'scope.json':json.dumps(dict(scope='full',code_sha=self.pr_head,event='pull_request')),
            'merge-reuse.json':json.dumps(dict(reuse=False,reason='PR_ALWAYS_FULL')),
            'collection.txt':'tests/test_synthetic.py::test_one\n1 test collected\n',
            'pytest.xml':'<testsuites><testsuite tests="1" errors="0" failures="0" skipped="0">'
                '<testcase classname="tests.test_synthetic" name="test_one"/>'
                '</testsuite></testsuites>',
        }
        self.runs = [self.run]
        self.calls = []
        self.build_archive()

    def git(self, *args):
        return subprocess.run(['git',*args],cwd=self.root,check=True,capture_output=True).stdout.decode().strip()

    def put(self, name, body):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)

    def commit(self):
        self.git('add','.'); self.git('commit','-qm','synthetic change')
        return self.git('rev-parse','HEAD')

    def build_archive(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            for name,body in self.files.items(): z.writestr(name,body)
        self.raw=buf.getvalue()
        self.artifact=dict(id=20,name='kernel-ci-10-1',expired=False,size_in_bytes=len(self.raw),
            digest='sha256:'+hashlib.sha256(self.raw).hexdigest(),
            workflow_run={'id':10,'head_sha':self.pr_head})
        self.artifacts=[self.artifact]

    def read(self, root, path):
        self.assertEqual(root,self.root);self.calls.append(path)
        if '/runs?' in path:return {'total_count':len(self.runs),'workflow_runs':self.runs}
        if path==f'commits/{self.head}/pulls?per_page=100':return [self.pr]
        if path=='pulls/5':return self.pr
        if path=='actions/runs/10/artifacts?per_page=100':
            return {'total_count':len(self.artifacts),'artifacts':self.artifacts}
        raise AssertionError(path)

    def select(self):
        return S['select'](self.root,self.report,self.env,self.current,read=self.read,
                          download=lambda root,aid:self.raw)

    def test_actual_merge_and_complete_artifact_reuse_exact_source(self):
        result=self.select()
        self.assertTrue(result['reuse'],result)
        self.assertEqual(result['source']['test_count'],1)
        self.assertEqual(result['source']['head_sha'],self.pr_head)
        self.assertEqual(result['full_suite'],'REUSED_NOT_RERUN')
        self.assertEqual(sum('/runs?' in p for p in self.calls),2)
        self.assertFalse((self.report/'pytest.xml').exists())

    def test_empty_run_association_uses_exact_merge_commit_not_branch_or_message(self):
        self.run['pull_requests']=[]
        result=self.select()
        self.assertTrue(result['reuse'],result)
        self.assertEqual(result['source']['pr'],5)
        self.assertIn(f'commits/{self.head}/pulls?per_page=100',self.calls)

    def test_empty_ambiguous_or_incomplete_commit_association_stays_full(self):
        read=self.read
        for linked in [[],[self.pr,self.pr],[self.pr]*100,{'items':[self.pr]},
                       [{**self.pr,'merge_commit_sha':'0'*40}]]:
            with self.subTest(linked_count=len(linked)):
                def changed(root,path):
                    return linked if path.startswith('commits/') else read(root,path)
                result=S['select'](self.root,self.report,self.env,self.current,read=changed,
                                   download=lambda root,aid:self.raw)
                self.assertFalse(result['reuse'])

    def test_class_and_parameter_separators_use_real_pytest_junit_identity(self):
        self.files['collection.txt']='tests/test_synthetic.py::Case::test_one[value::with::separators]\n'
        self.files['pytest.xml']=self.files['pytest.xml'].replace(
            'tests.test_synthetic" name="test_one"',
            'tests.test_synthetic.Case" name="test_one[value::with::separators]"')
        self.build_archive()
        self.assertTrue(self.select()['reuse'])

    def test_dirty_checkout_cannot_reuse_a_clean_commit_result(self):
        self.put('src/engine.py','uncommitted change\n')
        self.assertEqual(self.select()['reason'],'FULL_REQUIRED_DIRTY_CHECKOUT')
        self.assertFalse(self.calls)

    def test_pr_is_always_full_without_reading_a_previous_result(self):
        self.env['GITHUB_EVENT_NAME']='pull_request'
        self.assertEqual(self.select()['reason'],'PR_ALWAYS_FULL');self.assertFalse(self.calls)

    def test_wrong_event_repository_ref_or_attempt_never_reuses(self):
        for key,value in [('GITHUB_EVENT_NAME','workflow_dispatch'),('GITHUB_REPOSITORY','other/repo'),
                          ('GITHUB_REF','refs/heads/feature'),('GITHUB_RUN_ATTEMPT','2')]:
            with self.subTest(key=key),patch.dict(self.env,{key:value}):
                self.assertFalse(self.select()['reuse']);self.assertFalse(self.calls)

    def test_squash_multi_commit_push_and_changed_merge_tree_are_full(self):
        for damage in ['before','squash','tree']:
            with self.subTest(damage=damage):
                saved=deepcopy(self.env); self.git('checkout','-q','main')
                if damage=='before':self.env['CI_BASE_SHA']='0'*40
                elif damage=='squash':
                    self.git('checkout','-q','--detach',self.pr_head);self.env['CI_CODE_SHA']=self.pr_head
                else:self.current['tree']='0'*40
                self.assertFalse(self.select()['reuse'])
                self.env=saved
                self.current['tree']=self.git('rev-parse',self.head+'^{tree}')

    def test_gate_change_requires_full_including_its_first_deployment(self):
        self.git('reset','--hard',self.base)
        self.git('checkout','-q','-b','policy')
        self.put('.github/scripts/ci-merge-reuse.py','changed policy\n');pr=self.commit()
        self.git('checkout','-q','main');self.git('merge','--no-ff','-m','policy merge','policy')
        self.env['CI_CODE_SHA']=self.git('rev-parse','HEAD')
        self.current['tree']=self.git('rev-parse','HEAD^{tree}')
        result=self.select()
        self.assertEqual(result['reason'],'FULL_REQUIRED_CI_POLICY_CHANGED')
        self.assertFalse(self.calls)

    def test_latest_failed_pending_or_wrong_run_cannot_hide_behind_old_green(self):
        for key,value in [('conclusion','failure'),('status','in_progress'),('run_attempt',2),
            ('run_attempt',True),('event','push'),('head_repository',{'full_name':'other/repo'}),
            ('path','.github/workflows/other.yml'),('head_sha','0'*40)]:
            with self.subTest(key=key):
                newer={**deepcopy(self.run),'id':11,key:value};self.runs=[self.run,newer]
                self.assertFalse(self.select()['reuse'])
        self.runs=[self.run]

    def test_pr_must_be_this_merged_owned_head(self):
        for key,value in [('merged',False),('merge_commit_sha','0'*40),
                          ('head',{'sha':self.pr_head,'repo':{'full_name':'other/repo'}})]:
            with self.subTest(key=key),patch.dict(self.pr,{key:value}):
                self.assertFalse(self.select()['reuse'])

    def test_environment_changes_or_unknown_identity_require_full(self):
        for key,value in [('image_version','next-image'),('image_version',None),('python','changed'),
            ('runner_arch','ARM64'),('packages',{'pytest':'different'})]:
            with self.subTest(key=key),patch.dict(self.current,{key:value}):
                self.assertFalse(self.select()['reuse'])

    def test_artifact_expiry_identity_digest_and_missing_data_require_full(self):
        for key,value in [('expired',True),('digest','sha256:'+'0'*64),('size_in_bytes',1),
                          ('workflow_run',{'id':99,'head_sha':self.pr_head})]:
            with self.subTest(key=key),patch.dict(self.artifact,{key:value}):
                self.assertFalse(self.select()['reuse'])
        self.artifacts=[];self.assertFalse(self.select()['reuse'])
        self.artifacts=[self.artifact,self.artifact];self.assertFalse(self.select()['reuse'])

    def test_hashed_proof_still_rejects_content_inheritance_wrong_identity_or_partial_suite(self):
        original=deepcopy(self.files)
        mutations={
            'identity.txt':f'code_sha={self.pr_head}\nevent=push\nrun_id=10\nattempt=1\n',
            'scope.json':json.dumps(dict(scope='content',code_sha=self.pr_head,event='pull_request')),
            'merge-reuse.json':json.dumps(dict(reuse=True,reason='EXACT_PR_FULL_SUITE_REUSED')),
            'collection.txt':'tests/test_synthetic.py::test_one\ntests/test_synthetic.py::test_two\n',
            'pytest.xml':self.files['pytest.xml'].replace('failures="0"','failures="1"'),
            'environment.json':'{}'}
        for name,body in mutations.items():
            with self.subTest(name=name):
                self.files={**original,name:body};self.build_archive()
                self.assertFalse(self.select()['reuse'])
        self.files=original
        for name in original:
            with self.subTest(missing=name):
                self.files={k:v for k,v in original.items() if k!=name};self.build_archive()
                self.assertFalse(self.select()['reuse'])

    def test_corrupt_and_traversal_zip_are_not_extracted(self):
        self.raw=b'not a zip';self.artifact['size_in_bytes']=len(self.raw)
        self.artifact['digest']='sha256:'+hashlib.sha256(self.raw).hexdigest()
        self.assertFalse(self.select()['reuse'])
        self.files['../outside']='do not write';self.build_archive()
        self.assertFalse(self.select()['reuse']);self.assertFalse((self.root.parent/'outside').exists())

    def test_newer_failure_during_archive_read_invalidates_reuse(self):
        read=self.read
        def changed(root,path):
            value=read(root,path)
            if '/runs?' in path and sum('/runs?' in p for p in self.calls)==2:
                return {'total_count':1,'workflow_runs':[{**self.run,'id':11,'conclusion':'failure'}]}
            return value
        result=S['select'](self.root,self.report,self.env,self.current,read=changed,
                           download=lambda root,aid:self.raw)
        self.assertFalse(result['reuse'])

    def test_read_failure_is_full_without_exposing_error_body(self):
        def failed(*args):raise RuntimeError('PRIVATE_GITHUB_BODY')
        result=S['select'](self.root,self.report,self.env,self.current,read=failed)
        self.assertFalse(result['reuse']);self.assertNotIn('PRIVATE',json.dumps(result))

    def test_workflow_keeps_install_full_fallback_and_separate_smoke_result(self):
        text=(ROOT/'.github/workflows/ci.yml').read_text()
        install=text.split('      - name: Install\n',1)[1].split('\n      - ',1)[0]
        self.assertNotIn('reuse',install)
        for label in ('Record full test collection','Test'):
            step=text.split('      - name: '+label+'\n',1)[1].split('\n      - ',1)[0]
            self.assertIn("steps.reuse.outputs.reuse != 'true'",step)
        smoke=text.split('      - name: Main merge smoke checks\n',1)[1].split('\n      - ',1)[0]
        self.assertIn('set -euo pipefail',smoke);self.assertIn('main-smoke.xml',smoke)
        self.assertNotIn('continue-on-error',text)
        self.assertNotIn('secrets.',text)
        for name in ['checkout','setup-python','upload-artifact']:
            self.assertRegex(text,r'actions/'+name+r'@[0-9a-f]{40}')

    def test_actual_smoke_script_failure_propagates_without_full_rerun(self):
        text=(ROOT/'.github/workflows/ci.yml').read_text()
        step=text.split('      - name: Main merge smoke checks\n',1)[1].split('\n      - ',1)[0]
        script=textwrap.dedent(step.split('        run: |\n',1)[1])
        # Run the exact real shell/pytest command over only synthetic files, outside ROOT.
        for name in ['test_ci_merge_reuse','test_ci_contract','test_external_research_identity',
                     'test_external_research_admission']:
            self.put('tests/'+name+'.py','def test_synthetic():\n    assert '+str(name!='test_ci_contract')+'\n')
        self.put('pytest.ini','[pytest]\n')
        env={**os.environ,'CI_REPORT_DIR':str(self.report)};env.pop('PYTEST_ADDOPTS',None)
        result=subprocess.run(['bash','-c',script],cwd=self.root,env=env,capture_output=True,timeout=60)
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        self.assertTrue((self.report/'main-smoke.xml').exists())
        self.assertFalse((self.report/'pytest.xml').exists())


if __name__=='__main__':
    unittest.main()
