"""Recover ONE registered Git archive from a pinned reading; never execute it.

Storage and publication remain native Git + the existing purpose registry. This
reader neither writes remote state nor creates a Research/continuation request.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import re
import sys
from uuid import UUID

from . import current_state as model
from . import research_commit_only as retained

MAX_FILES = 16
MAX_FILE_BYTES = retained.MAX_BYTES
MAX_API_CALLS = 24
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
FORMATS = {
    "RETAINED_FILES": {"format"},
    "RESEARCH_PROGRESS": {"format", "expected_sha256", "question_id"},
    "RESEARCH_COMMIT": {"format", "snapshot_id"},
    "ODDS_RESULT": {"format", "result_kind", "research_record_id", "research_snapshot_hash"},
}


def _sha(value) -> str:
    model.check(isinstance(value, str) and model.SHA.fullmatch(value) is not None,
                "exact Git identity required")
    return value


def _bound(raw: bytes, source: dict) -> None:
    model.check(model.blob_sha(raw) == source["git_blob"]
                and model.sha256(raw) == source["sha256"]
                and type(source["bytes"]) is int and len(raw) == source["bytes"],
                "saved reading source binding differs")


def _record(api, reading_commit: str, record_id: str, output: Path) -> tuple[dict, dict]:
    reading_raw = api.file("current-state.json", reading_commit)
    reading = retained._json(reading_raw)
    model.validate_read_package(reading)
    model.check(model.clock(reading["generated_at"]) <= datetime.now(timezone.utc),
                "reading clock is in the future")
    reg = reading["research"]["registry"]
    model.check(reg["repository"] == model.REPOSITORY and reg["ref"] == reading["code_commit"]
                and reg["path"] == "current_state/registry.json", "registry origin differs")
    registry_raw = api.file(model.safe_path(reg["read_path"]), reading_commit)
    _bound(registry_raw, reg)
    registry = retained._json(registry_raw)
    model.check(registry["schema_version"] == 1, "unsupported purpose registry")
    records = [r for r in registry["references"] if r["id"] == record_id]
    model.check(len(records) == 1, "archive record absent or ambiguous")
    deferred = 'read_policy' in records[0]
    visible_key = 'on_demand_archives' if deferred else 'records'
    visible = [r for r in reading["research"].get(visible_key, []) if r["id"] == record_id]
    other_key = 'records' if deferred else 'on_demand_archives'
    other = [r for r in reading["research"].get(other_key, []) if r["id"] == record_id]
    model.check(len(visible) == 1 and not other, "archive record absent or ambiguous")
    record, shown = records[0], visible[0]
    model.check(all(record[k] == shown[k] for k in ("id", "case", "use", "purpose_note")),
                "archive purpose differs from shown reading")
    if deferred:
        from .research_archive_index import project
        model.check(shown == project(record), "on-demand archive declaration differs from reading")
    source = shown["source"]
    declared_source = record["archive_source"] if deferred else record["source"]
    model.check(source["repository"] == model.REPOSITORY
                and source["ref"] == declared_source.get("ref", reg["ref"])
                and source["path"] == declared_source["path"]
                and source["git_blob"] == declared_source.get("git_blob", source["git_blob"]),
                "archive source differs from shown reading")
    _sha(source["ref"]); _sha(source["git_blob"])
    config = record["archive"]  # Missing opt-in is not permission to scan a directory.
    model.check(isinstance(config, dict) and config.get("format") in FORMATS
                and set(config) == FORMATS[config["format"]], "unsupported archive registration")
    if config["format"] == "RESEARCH_PROGRESS":
        model.check(isinstance(config["expected_sha256"], str)
                    and re.fullmatch(r"[0-9a-f]{64}", config["expected_sha256"]) is not None,
                    "progress needs externally registered digest")
        retained._progress_identity(config["question_id"])
    if config["format"] == "RESEARCH_COMMIT":
        model.check(str(UUID(config["snapshot_id"])) == config["snapshot_id"],
                    "commit archive needs exact snapshot id")
    if config["format"] == "ODDS_RESULT":
        from . import odds_retention as odds
        model.check(config["result_kind"] in odds.KINDS, "unsupported Odds result kind")
        model.check(isinstance(config["research_record_id"], str)
                    and NAME.fullmatch(config["research_record_id"]) is not None
                    and config["research_record_id"] != record_id, "invalid Research dependency")
        odds.check_snapshot_hash(config["research_snapshot_hash"])
    retained._write(output / "reading.json", reading_raw)
    retained._write(output / "registry.json", registry_raw)
    return record, source


def _tree_files(api, source: dict, output: Path) -> tuple[list[dict], str]:
    path = model.safe_path(source["path"])
    root = PurePosixPath(path).parent.as_posix()
    model.check(root.startswith(("research_runs/", "docs/readings/"))
                and len(PurePosixPath(root).parts) >= 3, "archive root is too broad")
    commit = api.get("git/commits/" + source["ref"])
    model.check(commit["sha"] == source["ref"], "archive commit differs")
    tree_sha = _sha(commit["tree"]["sha"])
    tree = api.get("git/trees/" + tree_sha + "?recursive=1")
    model.check(tree["sha"] == tree_sha and tree["truncated"] is False
                and isinstance(tree["tree"], list) and len(tree["tree"]) <= 5000,
                "archive tree is incomplete")
    rows, seen = [], set()
    for item in tree["tree"]:
        name = model.safe_path(item["path"])
        model.check(name not in seen, "duplicate tree path")
        seen.add(name)
        if not name.startswith(root + "/"):
            continue
        relative = name[len(root) + 1:]
        model.check(NAME.fullmatch(relative) is not None and item["mode"] == "100644"
                    and item["type"] == "blob", "archive must be flat regular data files")
        _sha(item["sha"])
        model.check(type(item["size"]) is int and 0 <= item["size"] <= MAX_FILE_BYTES,
                    "archive file exceeds retention bound")
        rows.append(item)
    model.check(1 <= len(rows) <= MAX_FILES, "archive file count unsupported")
    entry = [r for r in rows if r["path"] == path]
    model.check(len(entry) == 1 and entry[0]["sha"] == source["git_blob"],
                "archive tree does not contain the exact shown entry")
    # These are API JSON representations, not raw HTTP telemetry or signatures.
    retained._write(output / "git-commit.json", model.json_bytes(commit))
    retained._write(output / "git-tree.json", model.json_bytes(tree))
    return sorted(rows, key=lambda r: r["path"]), tree_sha


def _qualify(directory: Path, record: dict) -> dict:
    config = record["archive"]
    if config["format"] == "RESEARCH_PROGRESS":
        value, _ = retained.read_research_progress(directory, expected_sha256=config["expected_sha256"])
        model.check(value["subject"] == record["case"] and value["question_id"] == config["question_id"],
                    "progress subject or question differs")
        return {"qualification": "RETAINED_PROGRESS_NOT_COMMITTED", "progress_revision": value["revision"]}
    if config["format"] == "RESEARCH_COMMIT":
        result = retained.read_retained_commit(directory)
        model.check(str(result.research_snapshot.id) == config["snapshot_id"], "snapshot identity differs")
        return {"qualification": "COMMITTED_PACKAGE_REVALIDATED_NOT_HUMAN_ACCEPTANCE",
                "snapshot_id": str(result.research_snapshot.id), "package_hash": result.package_hash,
                "information_bundle_hash": result.information_bundle_hash}
    return {"qualification": "RETAINED_FILES_NOT_REVALIDATED_RESEARCH"}


def recover_archive(api, *, reading_commit: str, record_id: str, output: Path,
                    _required_format: str | None = None) -> dict:
    """Fetch an exact existing archive. Source text is data, never resume authority.

    The supplied API needs only file/get. Unknown/failed remote reads are not
    retried, and a partial local directory cannot be overwritten. This checks
    archived bytes, not source truth, completeness of Research or Human consent.
    """
    _sha(reading_commit)
    model.check(isinstance(record_id, str) and NAME.fullmatch(record_id) is not None,
                "invalid purpose record id")
    retained._safe_path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        record, source = _record(api, reading_commit, record_id, output)
        config = record["archive"]
        if _required_format is not None:
            model.check(config["format"] == _required_format, "Research dependency must be RESEARCH_COMMIT")
        rows, tree_sha = _tree_files(api, source, output)
        if config["format"] == "ODDS_RESULT":
            from . import odds_retention as odds
            model.check({PurePosixPath(r["path"]).name for r in rows} == odds.FILES,
                        "Odds archive inventory differs")
        if _required_format == "RESEARCH_COMMIT":
            model.check(len(rows) <= 5, "Research dependency inventory exceeds bound")
        bundle = output / "bundle"; bundle.mkdir()
        inventory = {}
        for row in rows:
            value = api.get("git/blobs/" + row["sha"])
            model.check(value["sha"] == row["sha"] and value["encoding"] == "base64"
                        and type(value["size"]) is int and value["size"] == row["size"],
                        "archive blob metadata differs")
            model.check(isinstance(value["content"], str) and len(value["content"]) <= MAX_FILE_BYTES * 2,
                        "archive blob representation exceeds bound")
            raw = base64.b64decode(''.join(value["content"].split()), validate=True)
            model.check(len(raw) == row["size"] and model.blob_sha(raw) == row["sha"],
                        "archive blob bytes differ")
            if row["path"] == source["path"]:
                _bound(raw, source)
            name = PurePosixPath(row["path"]).name
            retained._write(bundle / name, raw)
            inventory[name] = {"path": row["path"], "git_blob": row["sha"], **retained._description(raw)}
        qualified = _qualify(bundle, record)
        if config["format"] == "ODDS_RESULT":
            # One dependency only; a non-COMMIT target fails before its blob reads.
            dependency = recover_archive(api, reading_commit=reading_commit,
                record_id=config["research_record_id"], output=output / "research",
                _required_format="RESEARCH_COMMIT")
            model.check(dependency["case"] == record["case"], "Odds/Research navigation case differs")
            for name in ("reading.json", "registry.json"):
                model.check(retained._read(output / name) == retained._read(output / "research" / name),
                            "dependency must use the exact same reading and registry bytes")
            result = odds.read_retained_odds(bundle, research_directory=output / "research" / "bundle",
                expected_research_hash=config["research_snapshot_hash"])
            metadata = retained._json(retained._read(bundle / "retention.json"))
            model.check(metadata["result_kind"] == config["result_kind"], "registered Odds kind differs")
            qualified = {"qualification": "ODDS_RESULT_REVALIDATED_NOT_CURRENT_QUALIFICATION",
                "result_kind": metadata["result_kind"], "result_hash": metadata["result_hash"],
                "research_record_id": dependency["record_id"],
                "research_source_commit": dependency["source_commit"],
                "research_snapshot_hash": config["research_snapshot_hash"],
                "research_package_hash": dependency["package_hash"],
                "verification": "EXISTING_DETERMINISTIC_REBUILD_ONLY"}
        receipt = {"format": "research-archive-read-v0", "reading_commit": reading_commit,
            "record_id": record_id, "case": record["case"], "original_use": record["use"],
            "original_purpose_note": record["purpose_note"], "source_commit": source["ref"],
            "source_tree": tree_sha, "source_entry": source["path"], "files": inventory, **qualified,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "meaning": "EXACT_GIT_ARCHIVE_READBACK_NOT_NEW_RESEARCH_OR_CURRENT_SOURCE_QUALIFICATION",
            "continuation_status": "NOT_EXECUTED", "human_acceptance": "NOT_ESTABLISHED_BY_RECOVERY",
            "investment_authority": "NONE", "market_status": "NOT_REQUESTED", "odds_status": "NOT_COMPUTED",
            "remote_write": False, "external_source_bodies": "ONLY_FILES_IN_INVENTORY_NOT_LINK_TARGETS"}
        if config["format"] == "ODDS_RESULT":
            receipt["odds_status"] = "SAVED_RESULT_REBUILT_FOR_VERIFICATION_NOT_NEW_PRICE_ANALYSIS"
            receipt["market_qualification"] = "NOT_ESTABLISHED_BY_RECOVERY"
        if record.get('read_policy') == 'ON_DEMAND_ARCHIVE':
            receipt['source_materialization'] = 'RECOVERED_ON_DEMAND_AFTER_REGISTERED_ONLY'
        retained._write(output / "readback.json", retained._raw(receipt))
        return receipt
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
        retained._write(output / "failure.json", retained._raw({"format": "research-archive-read-v0",
            "status": "ARCHIVE_NOT_VERIFIED", "error_type": type(exc).__name__,
            "continuation_status": "NOT_EXECUTED", "investment_authority": "NONE", "automatic_retry": False}))
        raise ValueError("archive not verified; preserve partial files; no overwrite/retry") from None


def main(argv=None, *, api=None) -> int:
    parser = argparse.ArgumentParser(description="Recover one pinned registered Git archive; no execution or remote writes.")
    parser.add_argument("--reading-commit", required=True)
    parser.add_argument("--record-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        _sha(args.reading_commit)
        if api is None:
            import os
            from .current_state_delivery import GitHubAPI
            api = GitHubAPI(os.environ["GH_TOKEN"], max_calls=MAX_API_CALLS)
        receipt = recover_archive(api, reading_commit=args.reading_commit, record_id=args.record_id, output=args.output)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, ImportError):
        print("ARCHIVE NOT VERIFIED; preserve files; no overwrite/retry.", file=sys.stderr)
        return 2
    print("ARCHIVE: " + receipt["qualification"])
    print("CONTINUATION: NOT_EXECUTED; INVESTMENT AUTHORITY: NONE; REMOTE WRITES: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
