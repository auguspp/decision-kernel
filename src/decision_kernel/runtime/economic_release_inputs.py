"""Assemble frozen seed sources and existing review bundles for Radar consumers.

This is orchestration over the existing scanner, verifier and reading page, not
another source registry, review authority, parser or production signal store.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Context, localcontext
from pathlib import Path

from decision_kernel.identity import canonical_hash, canonical_json
from .economic_node_study import AUTHORITY, MOA, SPB, _aware, qualify_release_excerpt
from .economic_release_review import _clock, _data, _read, _safe_path, verify_release_review
from . import economic_release_discovery as discovery

DEFAULT_SEED = Path("radar_inputs/economic-node-study-2026-09-05.json")
DEFAULT_REVIEWS = Path("radar_inputs/economic-reviewed-releases")
PUBLIC = "REVIEWED_OFFICIAL_WEB_EXCERPT"
SEMANTICS = "DERIVED_RELEASE_INPUT_SET_NOT_REVIEW_OR_PUBLISHER_COMPLETENESS"
MAX_RECORDS = 64
MAX_SEED_BYTES = 256 * 1024
READY = "COMPLETE_BOUNDED_INPUT_SCAN"


@dataclass(frozen=True)
class ReleaseInputs:
    seed_observations: tuple
    review_paths: tuple[Path, ...]
    baseline: list
    receipt: dict


def load_release_inputs(seed: Path, reviews: Path, *, as_of: datetime) -> ReleaseInputs:
    """Reverify every immediate review bundle; absence/unknown files are not empty.

    An empty .gitkeep is the sole allowed nondirectory entry. Duplicate receipts
    are deduplicated only after verification; revisions remain distinct inputs.
    No version is selected by directory name, mtime or most recent review time.
    """
    _aware(as_of)
    _safe_path(seed)
    _safe_path(reviews)
    with seed.open("rb") as stream:
        raw = stream.read(MAX_SEED_BYTES + 1)
    if len(raw) > MAX_SEED_BYTES:
        raise ValueError("seed input exceeds byte budget")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate seed JSON key")
            result[key] = value
        return result
    sources = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(sources, list) or not 2 <= len(sources) <= MAX_RECORDS:
        raise ValueError("bounded seed must explicitly cover both economic nodes")
    if {s.get("source_kind") for s in sources if isinstance(s, dict)} != {MOA, SPB}:
        raise ValueError("seed must cover both official economic families")
    # Bound inventory before validating/copying any potentially large review archive.
    children = []
    for child in reviews.iterdir():
        _safe_path(child)
        if child.name == ".gitkeep" and child.is_file() and child.stat().st_size == 0:
            continue
        if not child.is_dir():
            raise ValueError("review directory contains an unrecognized file")
        children.append(child)
        if len(children) + len(sources) > MAX_RECORDS:
            raise ValueError("combined source inputs exceed operations budget; no truncation")
    with localcontext(Context(prec=28)):
        observations = tuple(qualify_release_excerpt(s) for s in sources)
        if any(_clock(o["system_pit_eligible_from"]) > as_of for o in observations):
            raise ValueError("seed knowledge follows input cutoff")
        if len({s["source_url"] for s in sources}) != len(sources):
            raise ValueError("seed contains duplicate URL identities")
        accepted = {}
        for child in sorted(children):
            item = verify_release_review(child, as_of=as_of)
            accepted.setdefault(item["acceptance_hash"], (item, child))
        ordered = [accepted[key] for key in sorted(accepted)]
        methods = {s["capture_method"] for s in sources}
        methods.update(item["observation"]["source_record"]["capture_method"] for item, _ in ordered)
        if len(methods) != 1:
            raise ValueError("synthetic and public source inputs cannot be mixed")
        method = next(iter(methods))
        original_cutoffs = {}
        for source in sources:
            family = discovery._family(source["source_url"])
            original_cutoffs[family] = max(original_cutoffs.get(family, ""), source["published_date"])
        by_url = {}
        for source in [*sources, *(item["observation"]["source_record"] for item, _ in ordered)]:
            by_url.setdefault(source["source_url"], []).append(source)
        baseline, conflicts = [], []
        for url, versions in sorted(by_url.items()):
            identities = {(discovery._compact(s["title"]), s["published_date"]) for s in versions}
            if len(identities) != 1:
                conflicts.append({"source_url": url, "identities": [list(x) for x in sorted(identities)]})
            # Earliest actual source capture, not a fabricated new acquisition.
            baseline.append(min(versions, key=lambda s: (_clock(s["captured_at"]), canonical_hash(s))))
        if method == PUBLIC and not conflicts:
            discovery._baseline(baseline)  # Existing scanner contract; no new source semantics.
        payload = {
            "schema_version": 1, "semantics": SEMANTICS, "as_of": as_of,
            "seed_sha256": hashlib.sha256(raw).hexdigest(), "seed_hash": canonical_hash(sources),
            "source_provenance": method, "seed_count": len(sources),
            "accepted_bundle_count": len(ordered), "known_url_count": len(by_url),
            "original_seed_cutoffs": original_cutoffs,
            "baseline_status": "IDENTITY_REVIEW_REQUIRED" if conflicts else "READY",
            "baseline_conflicts": conflicts,
            "baseline_hash": None if conflicts else canonical_hash(baseline),
            "review_receipts": [{key: item[key] for key in (
                "acceptance_hash", "archive_hash", "source_packet_id", "review_hash", "eligible_from"
            )} for item, _ in ordered],
            "known_url_body_revisions_checked": False, "publisher_completeness": False,
            **AUTHORITY,
        }
        payload["input_set_hash"] = canonical_hash(payload)
        return ReleaseInputs(observations, tuple(path for _, path in ordered),
                             [] if conflicts else baseline, json.loads(canonical_json(payload)))


def _scan_report(inputs: ReleaseInputs, result: dict | None, archive_hash: str | None) -> dict:
    # Existing scanner advances the newest-date cutoff. Keep formerly covered but
    # still-unreviewed rows visible rather than laundering them into a quiet run.
    gaps = [] if result is None else [row for row in result["plan"]["entries"]
        if row["discovery_disposition"] == "OLDER_UNREVIEWED_BACKLOG_NOT_FETCHED"
        and row["listed_publication_date"] >= inputs.receipt["original_seed_cutoffs"][row["family"]]]
    status = ("BASELINE_IDENTITY_REVIEW_REQUIRED" if result is None else
              "INCOMPLETE_SCAN" if result["status"] != "COMPLETE_BOUNDED_SCAN" else
              "UNREVIEWED_BASELINE_GAP" if gaps else READY)
    payload = {"schema_version": 1, "semantics": SEMANTICS, "status": status,
               "input_set_hash": inputs.receipt["input_set_hash"], "archive_hash": archive_hash,
               "accepted_bundle_count": inputs.receipt["accepted_bundle_count"],
               "known_url_count": inputs.receipt["known_url_count"],
               "source_scan_status": None if result is None else result["status"],
               "scan_provenance": None if result is None else result["provenance"],
               "unreviewed_baseline_gaps": gaps,
               "known_url_body_revisions_checked": False, "publisher_completeness": False,
               "automatic_review_acceptance": False, **AUTHORITY}
    payload["report_hash"] = canonical_hash(payload)
    return json.loads(canonical_json(payload))


def _summary(report: dict) -> str:
    return ("## Economic release inputs — " + report["status"] + "\n\n"
            f"已核验接受包 {report['accepted_bundle_count']}；已知 URL {report['known_url_count']}。\n\n"
            f"尚未审阅、但被前移日期基线留在历史区的发布：{len(report['unreviewed_baseline_gaps'])}。\n\n"
            "这些记录保留在 report.json，未自动补抓或接受。它们不是没有更新。\n\n"
            "已知 URL 只核对目录元数据，本次未复核其正文，不能排除修订。\n"
            "仅扫描可见窗口；不证明完整发布覆盖，不创建 Research、市场事件或投资决定。\n")


def _new_output(output: Path, seed: Path, reviews: Path) -> None:
    _safe_path(output)
    if (output.exists() or "decision-state" in output.resolve().parts
            or output.resolve().is_relative_to(seed.parent.resolve())
            or output.resolve().is_relative_to(reviews.resolve())
            or reviews.resolve().is_relative_to(output.resolve())):
        raise ValueError("use a fresh output outside source and market-state directories")


def run_release_input_scan(seed: Path, reviews: Path, output: Path, *, now=None, transport=None) -> dict:
    clock = now or (lambda: datetime.now(timezone.utc))
    inputs = load_release_inputs(seed, reviews, as_of=_aware(clock()))
    if inputs.receipt["source_provenance"] != PUBLIC:
        raise ValueError("synthetic review inputs cannot seed the public scanner")
    _new_output(output, seed, reviews)
    output.mkdir(parents=True, exist_ok=False)
    (output / "input-set.json").write_bytes(_data(inputs.receipt))
    result, archive_hash = None, None
    if inputs.baseline:
        result = discovery.run_discovery(inputs.baseline, output / "scan", now=clock,
            transport=transport, provenance=discovery.LIVE if transport is None else discovery.SYNTHETIC)
        archive_hash = discovery.verify_discovery(output / "scan")["archive_hash"]
    report = _scan_report(inputs, result, archive_hash)
    (output / "report.json").write_bytes(_data(report))
    (output / "summary.md").write_text(_summary(report), encoding="utf-8")
    verify_release_input_scan(seed, reviews, output)
    return report


def verify_release_input_scan(seed: Path, reviews: Path, root: Path) -> dict:
    _safe_path(root)
    saved = _read(root / "input-set.json", MAX_SEED_BYTES)
    inputs = load_release_inputs(seed, reviews, as_of=_clock(saved["as_of"]))
    if (inputs.receipt != saved or (root / "input-set.json").read_bytes() != _data(saved)
            or saved["source_provenance"] != PUBLIC):
        raise ValueError("source input set no longer matches the exact original inputs")
    result, archive_hash = None, None
    allowed = {"input-set.json", "report.json", "summary.md"}
    if inputs.baseline:
        allowed.add("scan")
        archive_hash = discovery.verify_discovery(root / "scan")["archive_hash"]
        baseline = (root / "scan/baseline.json").read_bytes()
        if baseline != _data(inputs.baseline):
            raise ValueError("scan baseline differs from eligible verified reviews")
        first_request = _read(root / "scan/00.request.json", 65536)
        if _clock(first_request["started_at"]) < _clock(saved["as_of"]):
            raise ValueError("source scan predates its input knowledge boundary")
        result = _read(root / "scan/result.json", discovery.MAX_BODY)
    if {p.name for p in root.iterdir()} != allowed:
        raise ValueError("input scan inventory differs")
    report = _scan_report(inputs, result, archive_hash)
    if (_read(root / "report.json", discovery.MAX_BODY) != report
            or (root / "report.json").read_bytes() != _data(report)
            or (root / "summary.md").is_symlink()
            or (root / "summary.md").read_text(encoding="utf-8") != _summary(report)):
        raise ValueError("input scan report does not reconstruct")
    return report


def render_input_context(seed: Path, reviews: Path, *, as_of: datetime, output: Path,
                         bundle: Path, parent_hints: Path, links: Path) -> int:
    """Expand the one-directory input into the existing CLI, without editing it."""
    from . import economic_market_context as view
    inputs = load_release_inputs(seed, reviews, as_of=as_of)
    _new_output(output, seed, reviews)
    # Synthetic sets are permitted for explicit offline tests, never mixed with
    # public observations or promoted by this read-only projection.
    with tempfile.TemporaryDirectory(prefix="economic-seed-observations-") as temporary:
        args = ["--bundle", str(bundle), "--parent-hints", str(parent_hints), "--links", str(links),
                "--as-of", as_of.isoformat(), "--output", str(output)]
        for index, observation in enumerate(inputs.seed_observations):
            path = Path(temporary) / f"{index:02d}.json"
            path.write_bytes(_data(observation))
            args.extend(["--observation", str(path)])
        for path in inputs.review_paths:
            args.extend(["--reviewed-release", str(path)])
        status = view.main(args)
    if status != 0:
        return status
    try:
        current = load_release_inputs(seed, reviews, as_of=as_of)
        page = _read(output / "association.json", 4 * 1024 * 1024)
        actual_ids = sorted(r["acceptance_hash"] for r in page["projection"].get("source_review_receipts", []))
        expected_ids = sorted(r["acceptance_hash"] for r in inputs.receipt["review_receipts"])
        if current.receipt != inputs.receipt or actual_ids != expected_ids:
            raise ValueError("reading page and assembled source inputs disagree")
        (output / "input-set.json").write_bytes(_data(inputs.receipt))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        shutil.rmtree(output)
        raise
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Assemble reviewed Radar inputs; no automatic source acceptance.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("scan", "verify", "context"):
        sub = commands.add_parser(command)
        sub.add_argument("--seed", type=Path, default=DEFAULT_SEED)
        sub.add_argument("--reviews-dir", type=Path, default=DEFAULT_REVIEWS)
        if command == "verify":
            sub.add_argument("run", type=Path)
        else:
            sub.add_argument("--output", type=Path, required=True)
        if command == "context":
            sub.add_argument("--bundle", type=Path, required=True)
            sub.add_argument("--parent-hints", type=Path, required=True)
            sub.add_argument("--links", type=Path, default=Path("radar_inputs/economic-market-links-v0.json"))
            sub.add_argument("--as-of", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "context":
            return render_input_context(args.seed, args.reviews_dir, as_of=_clock(args.as_of), output=args.output,
                bundle=args.bundle, parent_hints=args.parent_hints, links=args.links)
        result = (run_release_input_scan(args.seed, args.reviews_dir, args.output) if args.command == "scan"
                  else verify_release_input_scan(args.seed, args.reviews_dir, args.run))
        print(canonical_json(result))
        return 0 if result["status"] == READY else 2
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print(f"Economic release inputs unavailable: {type(exc).__name__}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
