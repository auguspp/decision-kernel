"""Real local Git diffs and content command; synthetic GitHub metadata, no network."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / '.github/scripts/ci-content-scope.py'
S = runpy.run_path(str(SCRIPT))


class ContentScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.put('README.md', '# Original prose\n')
        self.put('src/code.py', 'value = 1\n')
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'user.name=Synthetic CI', '-c',
            'user.email=ci@example.invalid', *args], cwd=self.root, stderr=subprocess.PIPE).decode().strip()

    def put(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode() if isinstance(text, str) else text)

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-qm', 'synthetic local test')
        return self.git('rev-parse', 'HEAD')

    def runs(self, base=None):
        return [dict(id=100, name='kernel-tests', path='.github/workflows/ci.yml',
            head_sha=base or self.base, head_branch='main', event='push', run_attempt=1,
            status='completed', conclusion='success', head_repository={'full_name': S['REPO']})]

    def select(self, *, base=None, head=None, event='push', read_runs=None):
        return S['select'](self.root, event, base or self.base,
            head or self.git('rev-parse', 'HEAD'),
            read_runs=read_runs or (lambda _root, sha: self.runs(sha)))

    def test_reviewed_prose_on_trusted_base_and_exact_bytes(self):
        self.put('README.md', '# 修改后的文字\n')
        head = self.commit()
        for event in ('push', 'pull_request'):
            with self.subTest(event=event):
                result = self.select(event=event)
                self.assertEqual(result['scope'], 'content')
                self.assertEqual(result['code_sha'], head)
                self.assertEqual(result['baseline_ci']['id'], 100)
                self.assertEqual(S['check_content'](self.root, result)[0]['path'], 'README.md')

    def test_only_new_research_markdown_not_old_evidence_edits(self):
        self.put('docs/readings/new-note.md', '# New retained note\n')
        first = self.commit()
        self.assertEqual(self.select()['scope'], 'content')
        self.put('docs/readings/new-note.md', '# Changed existing evidence\n')
        self.commit()
        self.assertEqual(self.select(base=first)['scope'], 'full')

    def test_multiple_push_commits_do_not_hide_earlier_code_change(self):
        self.put('src/code.py', 'value = 2\n')
        self.commit()
        self.put('README.md', '# Later prose\n')
        self.commit()
        result = self.select(read_runs=lambda *_: self.fail('not a prose candidate'))
        self.assertEqual(result['scope'], 'full')
        self.assertEqual({r['path'] for r in result['changes']}, {'README.md', 'src/code.py'})

    def test_json_computation_configuration_and_unknown_paths_stay_full(self):
        for path in ('docs/readings/case/calculations.py', 'docs/readings/case/input.json',
                     'current_state/registry.json', 'research_runs/request.json',
                     'tests/fixtures/source.md', 'docs/full-research-method-v3.md',
                     '.github/workflows/other.yml', 'pyproject.toml', 'unknown.md'):
            with self.subTest(path=path):
                row = dict(path=path, old_mode='000000', new_mode='100644', status='A')
                self.assertFalse(S['prose_change'](row))

    def test_delete_and_rename_are_full_even_when_new_name_is_markdown(self):
        self.git('mv', 'README.md', 'AGENTS.md')
        first = self.commit()
        self.assertEqual(self.select()['scope'], 'full')
        (self.root / 'AGENTS.md').unlink()
        self.commit()
        self.assertEqual(self.select(base=first)['scope'], 'full')

    def test_executable_and_symlink_modes_are_full(self):
        self.git('update-index', '--chmod=+x', 'README.md')
        self.git('commit', '-qm', 'mode only')
        self.assertEqual(self.select()['scope'], 'full')
        (self.root / 'README.md').unlink()
        (self.root / 'README.md').symlink_to('src/code.py')
        self.commit()
        self.assertEqual(self.select()['scope'], 'full')

    def test_more_than_300_files_does_not_hide_code_or_truncate(self):
        for i in range(305):
            self.put(f'docs/readings/{i:03d}.md', '# Synthetic\n')
        self.put('src/z-last.py', 'value = 2\n')
        self.commit()
        result = self.select()
        self.assertEqual(result['scope'], 'full')
        self.assertEqual(len(result['changes']), 306)

    def test_unknown_event_base_and_empty_change_are_not_content_success(self):
        for kwargs in ({'event': 'workflow_dispatch'}, {'base': '0' * 40}, {'base': '--unsafe'}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.select(**kwargs)['scope'], 'full')
        self.assertEqual(self.select()['scope'], 'full')
        with self.assertRaises(ValueError):
            self.select(head='a' * 40)

    def test_shallow_checkout_fetches_only_exact_base_from_local_origin(self):
        self.put('README.md', '# Prose on a shallow head\n')
        head = self.commit()
        with tempfile.TemporaryDirectory() as elsewhere:
            clone = Path(elsewhere) / 'shallow'
            subprocess.run(['git', 'clone', '-q', '--depth=1', self.root.as_uri(), str(clone)],
                           check=True, capture_output=True, timeout=30)
            absent = subprocess.run(['git', 'cat-file', '-e', self.base + '^{commit}'],
                                    cwd=clone, capture_output=True)
            self.assertNotEqual(absent.returncode, 0)
            report = S['select'](clone, 'pull_request', self.base, head,
                                read_runs=lambda *_: self.runs())
            self.assertEqual(report['scope'], 'content')
            self.assertEqual(S['check_content'](clone, report)[0]['path'], 'README.md')

    def test_unusual_names_cannot_become_prose_allowlist_matches(self):
        for path in ('../README.md', '/README.md', 'docs/readings/../run.md',
                     'docs/readings/a\nb.md', 'docs//readings/a.md'):
            with self.subTest(path=path):
                self.assertFalse(S['prose_change'](dict(path=path, status='A',
                    old_mode='000000', new_mode='100644')))

    def test_wrong_or_failed_baseline_cannot_launder_code(self):
        for key, value in (('event', 'pull_request'), ('head_sha', 'e' * 40),
                ('head_branch', 'other'), ('name', 'other'), ('path', 'other.yml'),
                ('head_repository', {'full_name': 'other/repo'}), ('run_attempt', 2),
                ('run_attempt', True), ('status', 'in_progress'), ('conclusion', 'failure')):
            with self.subTest(key=key):
                runs = self.runs()
                runs[0][key] = value
                self.assertIsNone(S['trusted_base'](runs, self.base))
        runs = self.runs()
        runs.append({**runs[0], 'id': 101, 'conclusion': 'failure'})
        self.assertIsNone(S['trusted_base'](runs, self.base))
        self.put('README.md', '# Prose\n')
        self.commit()
        self.assertEqual(self.select(read_runs=lambda *_: [])['scope'], 'full')

    def test_api_or_diff_read_failure_falls_back_to_full_without_raw_error(self):
        self.put('README.md', '# Prose\n')
        self.commit()
        def failed(*_):
            raise OSError('PRIVATE_REMOTE_ERROR')
        report = self.select(read_runs=failed)
        self.assertEqual(report['scope'], 'full')
        self.assertNotIn('PRIVATE_REMOTE_ERROR', json.dumps(report))
        with patch.dict(S['select'].__globals__, {'changes': failed}):
            self.assertEqual(self.select()['scope'], 'full')

    def test_bad_content_is_failure_not_full_fallback_or_quiet_success(self):
        for body in (b'\xff', b'\0', b' ', b'<<<<<<< unresolved\n', b'>>>>>>> unresolved\n'):
            with self.subTest(body=body):
                self.put('README.md', body)
                self.commit()
                report = self.select()
                self.assertEqual(report['scope'], 'content')
                with self.assertRaises(ValueError):
                    S['check_content'](self.root, report)

    def test_plan_and_checkout_tampering_are_rejected(self):
        self.put('README.md', '# Prose\n')
        self.commit()
        report = self.select()
        bad = deepcopy(report)
        bad['changes'][0]['path'] = 'AGENTS.md'
        with self.assertRaises(ValueError):
            S['check_content'](self.root, bad)
        self.put('README.md', '# Next prose\n')
        self.commit()
        with self.assertRaises(ValueError):
            S['check_content'](self.root, report)

    def test_actual_content_command_exit_and_honest_artifact(self):
        for valid in (True, False):
            with self.subTest(valid=valid):
                self.put('README.md', '# Prose\n' if valid else '<<<<<<< conflict\n')
                self.commit()
                report_dir = self.root / '.git' / ('good' if valid else 'bad')
                report_dir.mkdir()
                # The metadata lookup alone is synthetic; Git/read/check/CLI are real.
                (report_dir / 'scope.json').write_text(json.dumps(self.select()))
                run = subprocess.run([sys.executable, str(SCRIPT), 'check', '--report-dir',
                    str(report_dir)], cwd=self.root, capture_output=True, timeout=30)
                self.assertEqual(run.returncode, 0 if valid else 1, run.stderr)
                self.assertEqual((report_dir / 'content-check.json').exists(), valid)
                self.assertFalse((report_dir / 'pytest.xml').exists())
                if valid:
                    result = json.loads((report_dir / 'content-check.json').read_text())
                    self.assertEqual(result['full_suite'], 'NOT_RUN_CONTENT_ONLY')

    def test_workflow_keeps_stable_check_and_conditions_all_expensive_steps(self):
        text = (ROOT / '.github/workflows/ci.yml').read_text()
        self.assertTrue(text.startswith('name: kernel-tests\n'))
        self.assertIn('\n  test:\n', text)
        self.assertNotIn('paths-ignore:', text)
        self.assertIn("CI_BASE_SHA: ${{ github.event.pull_request.base.sha || github.event.before }}", text)
        for label in ('      - uses: actions/setup-python@', '      - name: Install\n',
                      '      - name: Record full test collection\n', '      - name: Test\n'):
            step = text.split(label, 1)[1].split('\n      - ', 1)[0]
            self.assertIn("if: steps.scope.outputs.scope != 'content'", step)
        self.assertIn("if: steps.scope.outputs.scope == 'content'", text)
        self.assertIn("python3 -m unittest discover -s tests -p test_ci_content_scope.py", text)
        self.assertIn('contents: read\n  actions: read', text)
        self.assertNotIn('secrets.', text)


if __name__ == '__main__':
    unittest.main()
