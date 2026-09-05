"""Explicit source-review receipts for existing discovery packets; no network.

Reuse the discovery archive verifier and reviewed-excerpt binder. These receipts
are source-review records, never Human investment decisions or authenticity proofs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Context, localcontext
from pathlib import Path
from typing import Callable

from decision_kernel.identity import canonical_hash, canonical_json
from .economic_node_study import AUTHORITY, MOA, SPB, _aware
from .economic_release_discovery import LIVE, SYNTHETIC, verify_discovery
from .economic_source_capture import PublicResponse, bind_reviewed_source, decode_page

SEMANTICS = "EXPLICIT_SOURCE_EXCERPT_REVIEW_NOT_INVESTMENT_OR_AUTOMATIC_FACT_ACCEPTANCE"
ACCEPT = "ACCEPT_REVIEWED_EXCERPT"
FIELDS = {"schema_version", "archive_hash", "source_packet_id", "raw_body_sha256",
          "decision", "reviewer", "reviewed_at", "reason", "excerpt"}
MAX_REVIEW_BYTES = 64 * 1024
MAX_ACCEPTANCE_BYTES = 256 * 1024
TOP_LEVEL = {"discovery", "review.json", "page.txt", "acceptance.json"}


def _data(value) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _safe_path(path: Path) -> None:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("source-review paths must not contain symlinks")


def _read(path: Path, limit: int) -> dict:
    _safe_path(path)
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("source-review input exceeds byte budget")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate source-review JSON key")
            result[key] = value
        return result
    result = json.loads(data, object_pairs_hook=unique)
    if not isinstance(result, dict):
        raise ValueError("source-review record must be an object")
    return result


def _clock(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("explicit source-review clock required")
    return _aware(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _select(archive: Path, packet_id: str):
    verified = verify_discovery(archive)
    result = _read(archive / "result.json", 2 * 1024 * 1024)
    packets = [p for p in result["review_packets"] if p.get("source_packet_id") == packet_id]
    if len(packets) != 1 or packets[0]["status"] != "PENDING_HUMAN_SOURCE_REVIEW":
        raise ValueError("select one exact identity-qualified pending packet; no guessed latest URL")
    packet = packets[0]
    index = result["plan"]["detail_requests"].index(packet["source_url"]) + 2
    meta = _read(archive / f"{index:02d}.response.json", 65536)
    response = PublicResponse(meta["url"], meta["status"], meta["headers"],
                              (archive / f"{index:02d}.body.bin").read_bytes())
    # All bytes, request ordering and packet fields were rebuilt by the existing verifier.
    latest_capture = max(_clock(_read(p, 65536)["completed_at"])
                         for p in archive.glob("*.request.json"))
    return verified, result["provenance"], packet, response, latest_capture


def prepare_release_review(archive: Path, packet_id: str) -> tuple[dict, str]:
    verified, _, packet, response, _ = _select(archive, packet_id)
    return {"schema_version": 1, "archive_hash": verified["archive_hash"],
            "source_packet_id": packet_id, "raw_body_sha256": packet["raw_body_sha256"],
            "decision": "PENDING_REVIEW", "reviewer": "", "reviewed_at": None,
            "reason": "", "excerpt": ""}, decode_page(response)


def _build(archive: Path, review: Mapping, recorded_at: datetime) -> tuple[dict, str]:
    if (not isinstance(review, Mapping) or set(review) != FIELDS
            or type(review["schema_version"]) is not int or review["schema_version"] != 1
            or review["decision"] != ACCEPT):
        raise ValueError("an explicit completed excerpt acceptance is required")
    if len(_data(review)) > MAX_REVIEW_BYTES:
        raise ValueError("source-review input exceeds byte budget")
    for field in ("archive_hash", "source_packet_id", "raw_body_sha256"):
        if not isinstance(review[field], str) or not re.fullmatch(r"[0-9a-f]{64}", review[field]):
            raise ValueError("review requires exact content identities")
    for field, limit in (("reviewer", 200), ("reason", 2000)):
        value = review[field]
        if (not isinstance(value, str) or not value.strip() or len(value) > limit
                or any(ord(c) < 32 for c in value)):
            raise ValueError("reviewer and source-review reason must be explicit")
    _aware(recorded_at)
    reviewed_at = _clock(review["reviewed_at"])
    verified, provenance, packet, response, latest_capture = _select(archive, review["source_packet_id"])
    if (review["archive_hash"] != verified["archive_hash"]
            or review["raw_body_sha256"] != packet["raw_body_sha256"]):
        raise ValueError("review belongs to another archive or body version")
    acquired_at = _clock(packet["content_acquired_at"])
    if not acquired_at <= reviewed_at <= recorded_at or latest_capture > recorded_at:
        raise ValueError("review/recording cannot precede actual source acquisition or follow recording")
    source = {"source_kind": {"MOA_FEED": MOA, "SPB_EXPRESS": SPB}[packet["family"]],
              "source_url": packet["source_url"], "title": packet["title"],
              "published_date": packet["listed_publication_date"], "published_time_precision": "DATE_ONLY",
              "captured_at": packet["content_acquired_at"],
              "capture_method": "REVIEWED_OFFICIAL_WEB_EXCERPT" if provenance == LIVE else SYNTHETIC,
              "excerpt": review["excerpt"]}
    with localcontext(Context(prec=28)):
        page, binding, observation = bind_reviewed_source(source, response, captured_at=acquired_at)
        payload = {"schema_version": 1, "semantics": SEMANTICS, "provenance": provenance,
                   "archive_hash": verified["archive_hash"], "source_scan_status": verified["status"],
                   "source_packet_id": packet["source_packet_id"], "review_hash": canonical_hash(dict(review)),
                   "reviewer": review["reviewer"], "reviewed_at": review["reviewed_at"],
                   "recorded_at": recorded_at, "eligible_from": recorded_at,
                   "reviewer_identity": "DECLARED_NOT_AUTHENTICATED", "automatic_acceptance": False,
                   "binding": binding, "observation": observation,
                   "page_sha256": hashlib.sha256(page.encode("utf-8")).hexdigest(), **AUTHORITY}
        payload["acceptance_hash"] = canonical_hash(payload)
        return json.loads(canonical_json(payload)), page


def verify_release_review(root: Path, *, as_of: datetime | None = None) -> dict:
    """Reconstruct acceptance from its copied original archive and explicit review."""
    _safe_path(root)
    if {p.name for p in root.iterdir()} != TOP_LEVEL:
        raise ValueError("source-review bundle inventory differs")
    for path in root.iterdir():
        _safe_path(path)
    accepted = _read(root / "acceptance.json", MAX_ACCEPTANCE_BYTES)
    review = _read(root / "review.json", MAX_REVIEW_BYTES)
    expected, page = _build(root / "discovery", review, _clock(accepted["recorded_at"]))
    if (accepted != expected or (root / "acceptance.json").read_bytes() != _data(expected)
            or (root / "review.json").read_bytes() != _data(review)
            or (root / "page.txt").stat().st_size != len(page.encode("utf-8"))
            or (root / "page.txt").read_bytes() != page.encode("utf-8")):
        raise ValueError("source-review content does not reconstruct from original bytes")
    if as_of is not None and _clock(expected["eligible_from"]) > _aware(as_of):
        raise ValueError("source review was not recorded by the requested input cutoff")
    return expected


def apply_release_review(archive: Path, review: Mapping, output: Path, *,
                         now: Callable[[], datetime] | None = None) -> dict:
    """Single-writer, new immutable local bundle; exact reruns keep the first receipt.

    Caller declarations are not authentication. No loose observation is exported:
    consumers must carry acceptance eligibility alongside the original capture time.
    """
    _safe_path(archive)
    _safe_path(output)
    if (output.resolve().is_relative_to(archive.resolve())
            or archive.resolve().is_relative_to(output.resolve())
            or "decision-state" in output.resolve().parts):
        raise ValueError("review output must be outside source and market-state directories")
    if output.exists():
        accepted = verify_release_review(output)
        if (not isinstance(review, Mapping) or accepted["review_hash"] != canonical_hash(dict(review))
                or accepted["archive_hash"] != verify_discovery(archive)["archive_hash"]):
            raise ValueError("existing review differs; never overwrite a prior acceptance")
        return accepted
    recorded_at = _aware((now or (lambda: datetime.now(timezone.utc)))())
    accepted, page = _build(archive, review, recorded_at)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".economic-review-", dir=output.parent) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir()
        shutil.copytree(archive, staging / "discovery")
        (staging / "review.json").write_bytes(_data(review))
        (staging / "page.txt").write_text(page, encoding="utf-8")
        (staging / "acceptance.json").write_bytes(_data(accepted))
        verify_release_review(staging)
        if output.exists() or output.is_symlink():
            raise ValueError("review output appeared during build; retry explicitly")
        staging.rename(output)
    return accepted


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Explicit economic-source review; no network or market-state writes.")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("archive", type=Path)
    prepare.add_argument("--packet-id", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("archive", type=Path)
    apply.add_argument("--review", type=Path, required=True)
    apply.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    verify.add_argument("--as-of")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            accepted = verify_release_review(args.bundle, as_of=_clock(args.as_of) if args.as_of else None)
        elif args.command == "apply":
            if args.output.resolve().is_relative_to(args.review.parent.resolve()):
                raise ValueError("acceptance output must be outside the review-input directory")
            accepted = apply_release_review(args.archive, _read(args.review, MAX_REVIEW_BYTES), args.output)
        else:
            _safe_path(args.output)
            if (args.output.exists() or args.output.resolve().is_relative_to(args.archive.resolve())
                    or args.archive.resolve().is_relative_to(args.output.resolve())
                    or "decision-state" in args.output.resolve().parts):
                raise ValueError("draft output must be new and outside the archive/market state")
            draft, page = prepare_release_review(args.archive, args.packet_id)
            args.output.mkdir(parents=True, exist_ok=False)
            try:
                (args.output / "review.json").write_bytes(_data(draft))
                (args.output / "page.txt").write_text(page, encoding="utf-8")
            except OSError:
                shutil.rmtree(args.output)
                raise
            print("PENDING_REVIEW: source text and blank review only; no accepted observation")
            return 0
        print(canonical_json({"acceptance_hash": accepted["acceptance_hash"],
                              "eligible_from": accepted["eligible_from"], "provenance": accepted["provenance"],
                              "investment_authority": "NONE"}))
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print(f"Economic source review unavailable: {type(exc).__name__}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
