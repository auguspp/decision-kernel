"""Manual Actions delivery glue; reuse the existing read-only timeline and Git objects.

No source acquisition, Human-event recording, state restoration or judgment logic.
The outer receipt describes a local build, not successful remote publication.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.judgment_timeline import (
    DEFAULT_MANIFEST, REPOSITORY, _read, build_judgment_timeline,
    render_judgment_timeline, write_judgment_timeline,
)

BUILD_FILES = (
    ".github/scripts/build-judgment-timeline.py",
    ".github/workflows/judgment-timeline.yml",
    "pyproject.toml",
    "src/decision_kernel/identity.py",
    "src/decision_kernel/primitives.py",
    "src/decision_kernel/runtime/judgment_timeline.py",
    DEFAULT_MANIFEST,
)
README = """判断时间线 / 只读历史记录附件

打开 index.html；projection.json 保留精确投影与原记录时钟。
sources/ 只包含本视图明确选择的四份原文和展示清单，不是完整仓库。
build.json 记录生成代码版本、原文版本、运行身份和各文件 SHA-256。
它不是签名证明、Human 阅读日志、判断账本或远端上传成功凭证。

这是选定历史记录，不代表今天最新状态；页面生成不等于新判断。
原文、中文导读、行情时点、Human 表态与生成时间仍各自分开。
没有自动结算、收益率、代理行情、Research route 或新注意力提醒。

复核：先将 build.json 中的 run_id/build_commit 与 GitHub 成功运行核对，
再核对 GitHub artifact 摘要及 build.json 的文件清单。安装精确生成版本后，
可以用现有 build_judgment_timeline(sources, generated_at=原生成时间) 与
render_judgment_timeline 重建 projection.json/index.html；不需要访问行情。
普通 CLI 也可重建阅读页，但其新生成时间会改变文件字节，不改变投影身份。

附件保留30天；过期后从原 Git commit、固定原文 commit 和展示清单重建。
不要将旧附件当作今天最新状态，也不要以附件数作为预测样本数。
System investment authority = NONE.
"""


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"}, timeout=15,
    )
    if result.returncode:
        raise ValueError("local Git identity unavailable or mismatched; no remote fallback")
    return result.stdout


def _digest(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def build_ci_delivery(root: Path, output: Path, *, environ: Mapping[str, str], generated_at: datetime) -> dict:
    """Build from an explicit main-branch dispatch, then rebuild from copied source bytes."""
    required = {"GITHUB_REPOSITORY": REPOSITORY, "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REF": "refs/heads/main", "GITHUB_WORKFLOW": "judgment-timeline"}
    if any(environ.get(key) != value for key, value in required.items()):
        raise ValueError("timeline delivery requires explicit main workflow_dispatch context")
    commit = environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("invalid build commit")
    for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        if not re.fullmatch(r"[1-9][0-9]{0,19}", environ.get(key, "")):
            raise ValueError("invalid run identity")
    root = root.resolve(strict=True)
    if _git(root, "rev-parse", "HEAD").decode().strip() != commit:
        raise ValueError("build commit disagrees with checked-out HEAD")
    build_inputs = {}
    for relative in BUILD_FILES:
        raw = _read(root, relative)
        if _git(root, "cat-file", "blob", f"{commit}:{relative}") != raw:
            raise ValueError("build input differs from the committed version")
        build_inputs[relative] = _digest(raw)
    report = build_judgment_timeline(root, generated_at=generated_at)
    projection = report["projection"]
    source_commit = projection["source_commit"]
    _git(root, "cat-file", "-e", f"{source_commit}^{{commit}}")
    source_bytes = {DEFAULT_MANIFEST: _read(root, DEFAULT_MANIFEST)}
    for case in projection["cases"]:
        for record in case["records"]:
            relative = record["path"]
            raw = _read(root, relative)
            if _git(root, "cat-file", "blob", f"{source_commit}:{relative}") != raw:
                raise ValueError("source file does not belong to the declared source commit")
            source_bytes[relative] = raw

    # Existing writer rejects existing outputs and paths inside the source root.
    write_judgment_timeline(report, output, source_root=root)
    try:
        for relative, raw in source_bytes.items():
            target = output / "sources" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
        (output / "README.txt").write_text(README, encoding="utf-8")
        rebuilt = build_judgment_timeline(output / "sources", generated_at=generated_at)
        if (rebuilt != report
                or (output / "index.html").read_bytes() != render_judgment_timeline(rebuilt).encode("utf-8")
                or json.loads((output / "projection.json").read_text(encoding="utf-8")) != rebuilt):
            raise ValueError("delivered page and copied-source projection disagree")
        files = {str(p.relative_to(output)): _digest(p.read_bytes())
                 for p in sorted(output.rglob("*")) if p.is_file()}
        receipt = {
            "version": 1, "semantics": "READ_ONLY_MANUAL_DELIVERY_NOT_JUDGMENT_OR_EXPOSURE",
            "repository": REPOSITORY, "workflow": ".github/workflows/judgment-timeline.yml",
            "event": "workflow_dispatch", "ref": "refs/heads/main", "build_commit": commit,
            "run_id": int(environ["GITHUB_RUN_ID"]), "run_attempt": int(environ["GITHUB_RUN_ATTEMPT"]),
            "generated_at": report["generated_at"], "source_commit": source_commit,
            "projection_hash": report["projection_hash"], "build_inputs": build_inputs,
            "files": files, "retention_days": 30, "investment_authority": "NONE",
            "creates_canonical_wake": False, "records_human_exposure": False,
        }
        receipt["build_hash"] = canonical_hash(receipt)
        (output / "build.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError):
        shutil.rmtree(output)  # This directory was created by the new-output-only writer above.
        raise
    return receipt


def main() -> int:
    try:
        root = Path(os.environ["GITHUB_WORKSPACE"])
        out = Path(os.environ["RUNNER_TEMP"]) / "judgment-timeline"
        build_ci_delivery(root, out, environ=os.environ, generated_at=datetime.now(timezone.utc))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"TIMELINE DELIVERY FAILED: {exc}", file=sys.stderr)
        return 2
    print("READ-ONLY TIMELINE: local build verified; remote upload still pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
