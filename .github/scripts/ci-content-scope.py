"""Narrow prose CI gate. Native Git/gh only; no test-result cache or runtime state."""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

REPO = 'auguspp/decision-kernel'
# Reviewed prose entry points, NOT every Markdown file or every research asset.
PROSE = frozenset({
    'README.md', 'AGENTS.md', 'docs/CI-MAINLINE.md', 'docs/RESEARCH-ENTRY.md',
    'docs/research-outcome-contract-v1.md',
})
SHA = re.compile(r'[0-9a-f]{40}')


def command(root: Path, *args: str) -> bytes:
    return subprocess.run(args, cwd=root, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=30).stdout


def changes(root: Path, base: str, head: str) -> list[dict]:
    # No merge-base traversal, path-filter truncation, rename loss, or quoted paths.
    raw = command(root, 'git', 'diff', '--raw', '-z', '--no-renames',
                  '--no-ext-diff', base, head, '--')
    tokens = raw.split(b'\0')
    if tokens.pop() != b'' or len(tokens) % 2:
        raise ValueError('incomplete Git diff')
    result = []
    for metadata, path in zip(tokens[::2], tokens[1::2]):
        old, new, _old_blob, _new_blob, status = metadata.decode('ascii').split()
        result.append(dict(path=path.decode('utf-8'), status=status,
                           old_mode=old.removeprefix(':'), new_mode=new))
    return result


def prose_change(row: dict) -> bool:
    path = row['path']
    p = PurePosixPath(path)
    if (str(p) != path or p.is_absolute() or '..' in p.parts or
            any(ord(c) < 32 for c in path)):
        return False
    if row['new_mode'] != '100644' or row['old_mode'] not in ('000000', '100644'):
        return False
    if row['status'] not in ('A', 'M'):
        return False
    # Existing archived evidence edits, deletions and renames remain full-suite.
    return path in PROSE or (row['status'] == 'A' and
                            path.startswith('docs/readings/') and p.suffix == '.md')


def main_ci(root: Path, base: str) -> list[dict]:
    payload = json.loads(command(root, 'gh', 'api',
        f'repos/{REPO}/actions/workflows/ci.yml/runs?head_sha={base}'
        '&event=push&branch=main&per_page=100'))
    return payload['workflow_runs']


def trusted_base(runs: list[dict], base: str) -> dict | None:
    candidates = [r for r in runs if isinstance(r, dict) and
        isinstance(r.get('head_repository'), dict) and r.get('head_sha') == base and r.get('event') == 'push' and
        r.get('head_branch') == 'main' and r.get('name') == 'kernel-tests' and
        r.get('path') == '.github/workflows/ci.yml' and
        r.get('head_repository', {}).get('full_name') == REPO and
        type(r.get('id')) is int and r['id'] > 0]
    if not candidates:
        return None
    latest = max(candidates, key=lambda r: r['id'])
    if (latest.get('status') != 'completed' or latest.get('conclusion') != 'success'
            or type(latest.get('run_attempt')) is not int or latest['run_attempt'] != 1):
        return None
    return {k: latest[k] for k in ('id', 'head_sha', 'event', 'run_attempt', 'conclusion')}


def select(root: Path, event: str, base: str, head: str, *, read_runs=main_ci) -> dict:
    if not SHA.fullmatch(head) or command(root, 'git', 'rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('CI checkout identity mismatch')
    report = dict(scope='full', code_sha=head, base_sha=base, event=event,
                  reason='UNKNOWN_BASE_OR_EVENT', changes=[], baseline_ci=None)
    if event not in ('pull_request', 'push') or not SHA.fullmatch(base) or base == '0' * 40:
        return report
    try:
        try:
            command(root, 'git', 'cat-file', '-e', base + '^{commit}')
        except subprocess.CalledProcessError:
            command(root, 'git', 'fetch', '--no-tags', '--depth=1', 'origin', base)
        rows = changes(root, base, head)
        report['changes'] = rows
        if not rows or not all(prose_change(row) for row in rows):
            report['reason'] = 'NON_PROSE_OR_EMPTY_CHANGE'
            return report
        baseline = trusted_base(read_runs(root, base), base)
        if baseline is None:
            report['reason'] = 'NO_TRUSTED_SUCCESSFUL_BASE_CI'
            return report
        report.update(scope='content', reason='PROSE_ONLY_ON_SUCCESSFUL_MAIN_BASE', baseline_ci=baseline)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        # Read/diff uncertainty costs full CI, never produces a quiet content PASS.
        report['reason'] = 'SCOPE_READ_UNAVAILABLE_' + type(exc).__name__
    return report


def check_content(root: Path, report: dict) -> list[dict]:
    if report['scope'] != 'content' or not report['changes'] or not report['baseline_ci']:
        raise ValueError('not a qualified content plan')
    head, base = report['code_sha'], report['base_sha']
    if not SHA.fullmatch(head) or not SHA.fullmatch(base):
        raise ValueError('invalid content commit identity')
    if report['baseline_ci'].get('head_sha') != base:
        raise ValueError('content baseline identity changed')
    if command(root, 'git', 'rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('content checkout changed')
    if changes(root, base, head) != report['changes']:
        raise ValueError('content diff changed')
    checked = []
    for row in report['changes']:
        if not prose_change(row):
            raise ValueError('non-prose content plan')
        # Read committed bytes, not a mutable worktree or a followed symlink.
        raw = command(root, 'git', 'show', head + ':' + row['path'])
        text = raw.decode('utf-8')
        if not text.strip() or '\0' in text or re.search(r'(?m)^(?:<{7}|>{7})(?: |$)', text):
            raise ValueError('empty, binary or unresolved-conflict prose: ' + row['path'])
        checked.append(dict(path=row['path'], bytes=len(raw)))
    return checked


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('select', 'check'))
    parser.add_argument('--report-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    plan = args.report_dir / 'scope.json'
    if args.operation == 'select':
        report = select(root, os.environ['GITHUB_EVENT_NAME'], os.environ.get('CI_BASE_SHA', ''),
                        os.environ['CI_CODE_SHA'])
        plan.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
            output.write('scope=' + report['scope'] + '\n')
        print('CI_SCOPE=' + report['scope'] + ' REASON=' + report['reason'])
    else:
        report = json.loads(plan.read_text(encoding='utf-8'))
        checked = check_content(root, report)
        result = dict(code_sha=report['code_sha'], baseline_ci=report['baseline_ci'],
                      checked=checked, content_integrity='PASS',
                      full_suite='NOT_RUN_CONTENT_ONLY', research_acceptance='NOT_ESTABLISHED')
        (args.report_dir / 'content-check.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('CONTENT_INTEGRITY=PASS FULL_SUITE=NOT_RUN_CONTENT_ONLY')


if __name__ == '__main__':
    main()
