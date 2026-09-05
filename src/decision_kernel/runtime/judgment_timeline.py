"""Read-only projection of explicitly selected frozen checkpoints, not Judgment state.

No network, semantic Markdown parsing, Odds calculation, Human inference, outcome
settlement or record writing. The reviewed view manifest selects exact source lines.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path, PurePosixPath
from typing import Any, Sequence, TextIO
from urllib.parse import quote

from decision_kernel.identity import canonical_hash

REPOSITORY = "auguspp/decision-kernel"
SEMANTICS = "READ_ONLY_CHECKPOINT_PROJECTION_NOT_JUDGMENT_STATE"
DEFAULT_MANIFEST = "ui_inputs/judgment-timeline-v0.json"
MAX_BYTES = 256 * 1024
UNKNOWN_NOTICE = (
    "所选记录没有独立的展示／阅读日志，不能认定为独立 Human forecast。"
    "未标明的发生时间、记录时间和市场时点保持未知，不用页面生成时间补填。"
)
OUTCOME_NOTICE = (
    "本视图未纳入后续 Outcome／Attribution 记录；不代表外部没有新信息。"
    "不按今天日期自动结算，不计算胜率、样本独立性或实际交易盈亏。"
)


def _keys(value: Any, expected: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("unexpected or missing view-manifest fields")


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1200:
        raise ValueError("invalid view text")
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _read(root: Path, relative: str) -> bytes:
    path = PurePosixPath(_text(relative))
    if path.is_absolute() or path.as_posix() != relative or "\\" in relative:
        raise ValueError("source path must be canonical and relative")
    if any(part in {".", ".."} for part in path.parts):
        raise ValueError("source path traversal is forbidden")
    candidate = root
    for part in path.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError("source symbolic links are forbidden")
    if not candidate.resolve(strict=True).is_relative_to(root):
        raise ValueError("source path escaped root")
    with candidate.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("source exceeds bounded view size")
    return data


def _excerpt(lines: list[str], span: Any, source_url: str) -> dict:
    if (not isinstance(span, list) or len(span) != 2
            or any(type(n) is not int for n in span)
            or not 1 <= span[0] <= span[1] <= len(lines)):
        raise ValueError("invalid exact source-line span")
    start, end = span
    return {"text": "".join(lines[start - 1:end]), "lines": span,
            "url": f"{source_url}#L{start}-L{end}"}


def build_judgment_timeline(
    source_root: Path, *, generated_at: datetime,
    manifest_path: str = DEFAULT_MANIFEST,
) -> dict:
    """Resolve a reviewed display manifest against unchanged source-file identities."""
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generation clock must be timezone-aware")
    root = source_root.resolve(strict=True)
    raw = _read(root, manifest_path)
    spec = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    _keys(spec, {"view_version", "source_commit", "scope_note", "cases"})
    if type(spec["view_version"]) is not int or spec["view_version"] != 1:
        raise ValueError("unsupported view version")
    commit = _text(spec["source_commit"])
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("view source must be an exact commit, not a branch")
    if not isinstance(spec["cases"], list) or not 1 <= len(spec["cases"]) <= 10:
        raise ValueError("view requires one to ten explicitly selected cases")
    cases, seen_keys, seen_paths = [], set(), set()
    for case in spec["cases"]:
        _keys(case, {"key", "label", "records"})
        key = _text(case["key"])
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", key) or key in seen_keys:
            raise ValueError("invalid or duplicate navigation key")
        seen_keys.add(key)
        if not isinstance(case["records"], list) or not 1 <= len(case["records"]) <= 10:
            raise ValueError("invalid selected record count")
        records, prior_paths = [], set()
        for item in case["records"]:
            _keys(item, {"path", "blob_sha1", "title", "clock", "human_quote", "parent", "panels"})
            path = _text(item["path"])
            if not path.startswith("docs/") or not path.endswith(".md") or path in seen_paths:
                raise ValueError("source must be a unique selected Markdown record")
            seen_paths.add(path)
            data = _read(root, path)
            git_hash = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if git_hash != item["blob_sha1"]:
                raise ValueError(f"frozen source identity changed: {path}")
            text = data.decode("utf-8")
            parent = item["parent"]
            if parent is not None and (parent not in prior_paths or f"`{parent}`" not in text):
                raise ValueError("supplement requires an explicit earlier source reference")
            prior_paths.add(path)
            url = f"https://github.com/{REPOSITORY}/blob/{commit}/{quote(path, safe='/')}"
            lines = text.splitlines(keepends=True)
            panels = []
            if not isinstance(item["panels"], list) or not 1 <= len(item["panels"]) <= 6:
                raise ValueError("invalid display panel count")
            for panel in item["panels"]:
                _keys(panel, {"label", "navigation_note", "span"})
                panels.append({"label": _text(panel["label"]),
                               "navigation_note": _text(panel["navigation_note"]),
                               "source": _excerpt(lines, panel["span"], url)})
            records.append({"path": path, "blob_sha1": git_hash,
                            "sha256": hashlib.sha256(data).hexdigest(), "source_url": url,
                            "title": _text(item["title"]), "parent": parent,
                            "clock": _excerpt(lines, item["clock"], url),
                            "human_quote": _excerpt(lines, item["human_quote"], url),
                            "panels": panels})
        cases.append({"key": key, "label": _text(case["label"]), "records": records})
    projection = {
        "view_version": 1, "semantics": SEMANTICS,
        "source_commit": commit, "scope_note": _text(spec["scope_note"]),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "cases": cases, "unknown_notice": UNKNOWN_NOTICE, "outcome_notice": OUTCOME_NOTICE,
        "investment_authority": "NONE", "creates_canonical_wake": False,
    }
    return {"generated_at": generated_at.isoformat(), "projection": projection,
            "projection_hash": canonical_hash(projection)}


STYLE = """
:root{color-scheme:light;--ink:#182b35;--muted:#51636b;--line:#dbe4e4;--accent:#176d68}
*{box-sizing:border-box}body{margin:0;background:#f5f7f6;color:var(--ink);font:16px/1.65 system-ui,sans-serif}
main{max-width:1120px;margin:auto;padding:40px 24px 64px}header{padding:12px 0 24px}
h1{font-size:38px;line-height:1.2;letter-spacing:-1px;margin:12px 0}h2{font-size:25px;margin:0}
h3{font-size:21px;margin:8px 0}h4{font-size:15px;margin:0 0 8px;color:var(--muted)}p{margin:8px 0;overflow-wrap:anywhere}
a{color:var(--accent);text-underline-offset:3px;overflow-wrap:anywhere}a:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.eyebrow{color:var(--accent);font-size:12px;letter-spacing:2px;font-weight:700}
.muted,.clock{color:var(--muted);font-size:14px}.clock{white-space:pre-wrap;overflow-wrap:anywhere}
nav{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}nav a{border:1px solid var(--line);padding:8px 16px;background:white;border-radius:24px;text-decoration:none}
.scope{border-left:3px solid var(--accent);padding:12px 18px;background:#eaf2f0}
.case{margin:38px 0;scroll-margin-top:20px}.timeline{border-left:2px solid #b6ceca;margin:18px 0 0 8px;padding-left:24px}
.record{position:relative;background:white;border:1px solid var(--line);border-radius:12px;margin:0 0 22px;padding:24px}
.record:before{content:'';position:absolute;left:-31px;top:32px;width:12px;height:12px;border-radius:50%;background:var(--accent);border:2px solid #f5f7f6}
blockquote{margin:18px 0;padding:12px 16px;background:#f4f7f6;border-left:3px solid #b6ceca;font-size:18px;white-space:pre-wrap;overflow-wrap:anywhere}
.panels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.panel{padding:16px;border:1px solid var(--line);border-radius:8px}
summary{cursor:pointer;color:var(--accent);font-size:14px;padding:8px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.7 ui-monospace,monospace;background:#f4f6f6;padding:12px;border-radius:6px;max-height:520px;overflow:auto}
.audit{margin-top:20px;border-top:1px solid var(--line);padding-top:10px}.audit code{font-size:12px;overflow-wrap:anywhere}
.notice{padding:12px 16px;background:#edf1f1;font-size:14px;border-radius:8px;margin-top:16px}footer{margin-top:36px;padding-top:20px;border-top:1px solid var(--line)}
@media(max-width:650px){main{padding:22px 14px 40px}h1{font-size:30px}.record{padding:16px}.timeline{padding-left:18px}.record:before{left:-25px}.panels{grid-template-columns:1fr}nav{gap:8px}nav a{padding:7px 12px}}
@media print{body{background:white}.record{break-inside:avoid}pre{max-height:none}nav{display:none}}
"""


def render_judgment_timeline(report: dict) -> str:
    projection = report["projection"]
    if (report["projection_hash"] != canonical_hash(projection)
            or projection["semantics"] != SEMANTICS
            or projection["investment_authority"] != "NONE"
            or projection["creates_canonical_wake"] is not False):
        raise ValueError("invalid read-only projection identity or authority")
    e = escape
    parts = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>判断时间线 · Decision Kernel</title>', f'<style>{STYLE}</style></head><body><main>',
             '<header><div class="eyebrow">DECISION KERNEL / HUMAN SURFACE</div>',
             '<h1>判断时间线</h1><p>当时怎么看，回应了什么，在等什么。</p>',
             '<p class="muted">只读冻结记录 · 不是实时持仓、推荐榜或预测胜率表</p></header>',
             f'<div class="scope">{e(projection["scope_note"])}</div><nav aria-label="案例导航">']
    for case in projection["cases"]:
        parts.append(f'<a href="#{e(case["key"])}">{e(case["label"])}</a>')
    parts.append('</nav><p class="muted">按标的分组仅用于导航，不代表独立 Decision Episode。中文导读是人工审阅的非权威投影；原文在每项下方。</p>')
    for case in projection["cases"]:
        parts.append(f'<section class="case" id="{e(case["key"])}"><h2>{e(case["label"])}</h2><div class="timeline">')
        for item in case["records"]:
            parts.extend(['<article class="record">',
                          f'<div class="clock">原记录标注：{e(item["clock"]["text"].strip())}</div>',
                          f'<h3>{e(item["title"])}</h3>'])
            if item["parent"] is not None:
                parts.append(f'<p class="muted">原文明示的补充关系：{e(item["parent"])}</p>')
            parts.append(f'<blockquote>{e(item["human_quote"]["text"].removeprefix("> ").strip())}</blockquote>')
            parts.append(f'<a class="muted" href="{e(item["human_quote"]["url"])}" rel="noreferrer">核对 Human 原话</a><div class="panels">')
            for panel in item["panels"]:
                source = panel["source"]
                parts.append(f'<div class="panel"><h4>{e(panel["label"])}</h4><p>{e(panel["navigation_note"])}</p>'
                             f'<details><summary>展开对应冻结原文</summary><pre>{e(source["text"])}</pre>'
                             f'<a href="{e(source["url"])}" rel="noreferrer">固定版本 · L{source["lines"][0]}–L{source["lines"][1]}</a></details></div>')
            parts.append('</div><details class="audit"><summary>记录身份与时间边界</summary>')
            parts.append(f'<p>{e(UNKNOWN_NOTICE)}</p><p>原文件：<a href="{e(item["source_url"])}" rel="noreferrer">{e(item["path"])}</a></p>'
                         f'<p>Git blob：<code>{e(item["blob_sha1"])}</code><br>SHA-256：<code>{e(item["sha256"])}</code></p>'
                         '<p>来源引用用于核对选定字节，不证明原始对话曾精确呈现了这一 Git 文件版本。没有重算旧 Odds 或读取新的行情。</p></details></article>')
        parts.append(f'</div><div class="notice"><strong>后来如何？</strong> {e(OUTCOME_NOTICE)}</div></section>')
    parts.extend(['<footer><strong>System investment authority = NONE</strong>',
                  '<p class="muted">认可研究 ≠ 投资决定；投资决定 ≠ Action；触价 ≠ thesis 验证。此页面不创建 canonical Human wake。</p>',
                  f'<p class="muted">页面生成时间：{e(report["generated_at"])}（不是行情或判断时间）</p>',
                  f'<details><summary>视图版本与复核</summary><pre>source commit: {e(projection["source_commit"])}\nprojection hash: {e(report["projection_hash"])}</pre>',
                  '<a href="projection.json">下载本页投影 JSON</a><p>本页不是历史可得性回测，也不是新的判断账本。缺少合格市场序列，本版不画价格曲线，不估算收益。</p></details></footer></main></body></html>'])
    return "\n".join(parts) + "\n"


def write_judgment_timeline(report: dict, output: Path, *, source_root: Path) -> None:
    """Write only a new external display directory, never overwrite source/state."""
    if output.is_symlink() or output.exists() or output.resolve().is_relative_to(source_root.resolve()):
        raise ValueError("output must be a new directory outside the source root")
    rendered = render_judgment_timeline(report)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output.mkdir(parents=True, exist_ok=False)
    written = []
    try:
        for name, content in (("index.html", rendered), ("projection.json", serialized)):
            path = output / name
            with path.open("x", encoding="utf-8") as stream:
                written.append(path)
                stream.write(content)
    except OSError:
        for path in written:
            path.unlink(missing_ok=True)
        output.rmdir()
        raise


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render selected frozen checkpoints; no market or state access.")
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = build_judgment_timeline(args.source_root, generated_at=datetime.now(timezone.utc))
        write_judgment_timeline(report, args.output, source_root=args.source_root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=stderr or sys.stderr)
        return 2
    print(f"READ-ONLY TIMELINE: {args.output / 'index.html'}", file=stdout or sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
