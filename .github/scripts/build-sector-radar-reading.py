"""Workflow-only delivery of the existing economic/company reading, no acquisition.

The producer's sealed replay remains authoritative. This script packages a
separate read-only projection and its exact supplied inputs, never recovery state.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_company_context as company
from decision_kernel.runtime.economic_release_inputs import load_release_inputs
from decision_kernel.runtime.economic_release_review import _safe_path
from decision_kernel.runtime.judgment_timeline import _read, _unique_object
from decision_kernel.runtime.sector_radar_audit import LIVE_PROVENANCE, validate_sector_radar_input_audit

SEED = 'radar_inputs/economic-node-study-2026-09-05.json'
REVIEWS = 'radar_inputs/economic-reviewed-releases'
LINKS = 'radar_inputs/economic-market-links-v0.json'
HINTS = 'radar_inputs/sector-parent-hints-2026-09-05.json'
COMPANIES = 'radar_inputs/economic-company-links-livestock-v1.json'
STATE_FILES = {'market-state.json', 'candidate-events.json', 'manifest.json'}
PAGE_FILES = {'index.html', 'association.json', 'input-set.json', 'company-links.json'}
MAX_BYTES, MAX_FILES = 64 * 1024 * 1024, 2048
README = '''行业走势—产业数据—公司依据 / 只读联合页面

打开 index.html；完整行业表仍在上一级 context/index.html。
association.json、input-set.json、company-links.json 保留各自原有身份。
delivery.json 记录本次运行、输入截止、页面生成和包内文件身份。
inputs.zip 保存本次确实读取的状态副本、经济种子、完整接受包、映射及公司摘录。
它不是新的恢复来源、生产账本、完整历史数据库或原始公司 PDF 永久归档。

复现：核对实际 GitHub run、commit 和外层附件摘要，再核对 delivery.json。
将 inputs.zip 解压到独立 input-copy 目录，在精确 build_commit 的代码环境中运行：
python -m decision_kernel.runtime.economic_company_context --source-root ../input-copy \\
  --seed ../input-copy/radar_inputs/economic-node-study-2026-09-05.json \\
  --reviews-dir ../input-copy/radar_inputs/economic-reviewed-releases \\
  --bundle ../input-copy/state \\
  --parent-hints ../input-copy/radar_inputs/sector-parent-hints-2026-09-05.json \\
  --links ../input-copy/radar_inputs/economic-market-links-v0.json \\
  --company-links radar_inputs/economic-company-links-livestock-v1.json \\
  --as-of <delivery.json 中的 input_cutoff> --output ../rebuilt-reading
新生成时间会改变 HTML／外层报告字节，但不改变固定截止下的投影。

本页没有重新采集行情、经济数据或公司 PDF。旧资料不是本日最新发布确认。
公司摘录的 PARTIAL 等级不提升；归因、业务暴露比例与净受益方向仍未建立。
生成成功不等于已上传，更不等于整次工作流、权威状态或 cache 已保存成功。
附件保留90天。过期后须有原包或另行保存的全部精确输入；哈希不能恢复缺失原文。
SHADOW OBSERVATION ONLY. Human / Research / Investment authority = NONE.
'''


def _digest(raw: bytes) -> dict:
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _file(path: Path) -> bytes:
    _safe_path(path)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('reading requires bounded regular input files')
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('reading file grew beyond its budget')
    return raw


def _json(path: Path) -> dict:
    return json.loads(_file(path), object_pairs_hook=_unique_object)


def _check_run(run: Path, state: Path, identity: dict) -> dict:
    """Use the existing sealed audit/receipt, not a second replay implementation."""
    _safe_path(run); _safe_path(state)
    receipt = _json(run / 'publication-verification.json')
    manifest = validate_sector_radar_input_audit(run / 'input-audit')
    if (receipt['verification_hash'] != canonical_hash({k: v for k, v in receipt.items() if k != 'verification_hash'})
            or receipt['workflow_identity'] != identity
            or receipt['status'] != 'REPLAY_AND_UPLOAD_FILES_MATCHED'
            or manifest['status'] != 'SUCCEEDED' or manifest['provenance'] != LIVE_PROVENANCE
            or receipt['audit_hash'] != manifest['audit_hash']
            or receipt['offline_replay']['status'] != 'MATCHED_SUCCEEDED'):
        raise ValueError('reading must follow this successful live publication precheck')
    context = _json(run / 'input-audit/inputs/context.json')
    if any(context.get(k) != v for k, v in identity.items()):
        raise ValueError('reading workflow identity differs from sealed inputs')
    if {p.name for p in state.iterdir()} != STATE_FILES:
        raise ValueError('reading state inventory changed after replay')
    expected = {name.removeprefix('expected/') for name in manifest['files']
                if name.startswith(('expected/state/', 'expected/output/'))}
    if set(receipt['verified_files']) != expected:
        raise ValueError('publication receipt inventory disagrees with sealed outputs')
    for name in sorted(expected):
        category, relative = name.split('/', 1)
        path = PurePosixPath(relative)
        if path.is_absolute() or '..' in path.parts or len(path.parts) != 1:
            raise ValueError('invalid sealed output path')
        raw = _file((state if category == 'state' else run) / relative)
        if (_digest(raw) != receipt['verified_files'][name]
                or raw != _file(run / 'input-audit/expected' / name)):
            raise ValueError('producer bytes changed after publication precheck')
    saved = _json(run / 'context/context.json')
    if (saved['context_hash'] != canonical_hash({k: v for k, v in saved.items() if k != 'context_hash'})
            or any(saved[k] != receipt[k] for k in ('market_state_hash', 'event_ledger_hash', 'market_session'))):
        raise ValueError('industry context belongs to different saved state')
    return receipt


def _source_files(root: Path, state: Path, *, as_of: datetime) -> tuple[dict, list[str]]:
    _safe_path(root)
    root = root.resolve(strict=True)
    load_release_inputs(root / SEED, root / REVIEWS, as_of=as_of)
    spec = json.loads(_read(root, COMPANIES), object_pairs_hook=_unique_object)
    paths = {SEED, LINKS, HINTS, COMPANIES}
    paths.update(c['source_path'] for n in spec['nodes'] for c in n['companies'])
    files = {path: _read(root, path) for path in sorted(paths)}
    directories = [REVIEWS]
    for p in sorted((root / REVIEWS).rglob('*')):
        _safe_path(p)
        relative = p.relative_to(root).as_posix()
        if p.is_dir():
            directories.append(relative)
        else:
            files[relative] = _file(p)
        if len(files) + len(directories) > MAX_FILES or sum(map(len, files.values())) > MAX_BYTES:
            raise ValueError('complete reading inputs exceed delivery budget; no truncation')
    for name in sorted(STATE_FILES):
        files['state/' + name] = _file(state / name)
    if sum(map(len, files.values())) > MAX_BYTES or len(files) + len(directories) > MAX_FILES:
        raise ValueError('complete reading inputs exceed delivery budget; no truncation')
    return files, sorted(directories)


def build_delivery(root: Path, run: Path, state: Path, temporary: Path, *, identity: dict, as_of: datetime) -> dict:
    """Compose the existing CLI from copied inputs and atomically add one run folder."""
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError('reading cutoff must be an aware instant')
    for path in (root, run, state, temporary):
        _safe_path(path)
    if (temporary.resolve().is_relative_to(root.resolve())
            or temporary.resolve().is_relative_to(run.resolve())
            or temporary.resolve().is_relative_to(state.resolve())):
        raise ValueError('reading staging must be outside source and state roots')
    target = run / 'economic-company'
    _safe_path(target)
    if target.exists():
        raise ValueError('never replace a previously generated reading')
    receipt = _check_run(run, state, identity)
    source_files, directories = _source_files(root, state, as_of=as_of)
    if source_files[HINTS] != _file(run / 'input-audit/inputs/parent-hints.json'):
        raise ValueError('reading parent hints differ from the actual producer inputs')
    with tempfile.TemporaryDirectory(prefix='sector-reading-', dir=temporary) as scratch:
        scratch = Path(scratch); inputs, output = scratch / 'inputs', scratch / 'reading'
        for relative in directories:
            (inputs / relative).mkdir(parents=True, exist_ok=True)
        for relative, raw in source_files.items():
            p = inputs / relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
        status = company.main([
            '--source-root', str(inputs), '--seed', str(inputs / SEED), '--reviews-dir', str(inputs / REVIEWS),
            '--bundle', str(inputs / 'state'), '--parent-hints', str(inputs / HINTS), '--links', str(inputs / LINKS),
            '--company-links', COMPANIES, '--as-of', as_of.isoformat(), '--output', str(output),
        ])
        if status != 0 or {p.name for p in output.iterdir()} != PAGE_FILES:
            raise ValueError('combined reading did not complete; no old-page fallback')
        association, company_report = _json(output / 'association.json'), _json(output / 'company-links.json')
        if (any(association['projection'][k] != receipt[k] for k in ('market_state_hash', 'event_ledger_hash', 'market_session'))
                or company.build_company_links(inputs, association, manifest_path=COMPANIES) != company_report
                or load_release_inputs(inputs / SEED, inputs / REVIEWS, as_of=as_of).receipt != _json(output / 'input-set.json')):
            raise ValueError('delivered reading differs from producer or copied inputs')
        with zipfile.ZipFile(output / 'inputs.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in directories:
                archive.writestr(relative + '/', b'')  # Preserve empty reviews; outer upload may omit dotfiles.
            for relative, raw in sorted(source_files.items()):
                archive.writestr(relative, raw)
        (output / 'README.txt').write_text(README, encoding='utf-8')
        delivery = {
            'schema_version': 1, 'semantics': 'READ_ONLY_RUN_ATTACHMENT_NOT_PRODUCER_OR_RECOVERY_STATE',
            'workflow_identity': identity, 'build_commit': identity['commit_sha'], 'input_cutoff': as_of.isoformat(),
            'generated_at': association['generated_at'], 'publication_verification_hash': receipt['verification_hash'],
            'market_state_hash': receipt['market_state_hash'], 'event_ledger_hash': receipt['event_ledger_hash'],
            'market_session': receipt['market_session'], 'association_hash': association['projection_hash'],
            'company_links_hash': company_report['projection_hash'],
            'source_files': {name: _digest(raw) for name, raw in sorted(source_files.items())},
            'source_directories': directories,
            'files': {p.name: _digest(_file(p)) for p in sorted(output.iterdir())},
            'retention_days': 90, 'remote_upload_verified': False,
            'source_commit_membership_verified': False, 'original_pdfs_reverified': False,
            **company.LIMITS,
        }
        delivery['delivery_hash'] = canonical_hash(delivery)
        (output / 'delivery.json').write_text(canonical_json(delivery) + '\n', encoding='utf-8')
        if (_check_run(run, state, identity) != receipt
                or _source_files(root, state, as_of=as_of) != (source_files, directories)):
            raise ValueError('inputs changed during reading generation')
        # Stage on the destination filesystem too; RUNNER_TEMP may be another device.
        with tempfile.TemporaryDirectory(prefix='.reading-publish-', dir=run) as transfer:
            staged = Path(transfer) / 'reading'
            shutil.copytree(output, staged)
            if any(_file(staged / p.name) != _file(p) for p in output.iterdir()):
                raise ValueError('reading changed in delivery copy')
            _safe_path(target)
            if target.exists():
                raise ValueError('reading output appeared during generation')
            staged.rename(target)
    return delivery


def main() -> int:
    try:
        if (os.environ.get('GITHUB_REF') != 'refs/heads/main'
                or os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
                or os.environ.get('GITHUB_RUN_ATTEMPT') != '1'
                or os.environ.get('GITHUB_REPOSITORY') != 'auguspp/decision-kernel'
                or os.environ.get('HITHINK_FINANCE_API_KEY')):
            raise ValueError('reading requires the credential-free fresh main Sector run')
        root = Path(os.environ['GITHUB_WORKSPACE'])
        commit = os.environ['GITHUB_SHA']
        head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, check=True, timeout=15)
        if head.stdout.decode().strip() != commit:
            raise ValueError('reading build commit differs from actual checkout')
        identity = {'repository': os.environ['GITHUB_REPOSITORY'], 'workflow_path': '.github/workflows/sector-radar-shadow.yml',
                    'run_id': int(os.environ['GITHUB_RUN_ID']), 'run_attempt': 1, 'commit_sha': commit}
        build_delivery(root, root / 'sector-radar-run', root / 'decision-state/sector-radar',
                       Path(os.environ['RUNNER_TEMP']), identity=identity, as_of=datetime.now(timezone.utc))
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Joint Radar reading unavailable: {type(exc).__name__}; no published page or fallback')
        return 2
    print('Joint Radar reading packaged locally; remote artifact/state/cache publication still pending')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
