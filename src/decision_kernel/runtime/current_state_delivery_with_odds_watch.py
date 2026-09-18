"""Thin saved-product reading for typed Odds Watch and optional Radar discovery.

The base Collector remains canonical for Sector/Stock/Inbox/Research collection and
publication. This subclass validates retained Watch bytes and optionally composes
saved independent Radar sources. It never fetches market data or dispatches work.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import requests

from decision_kernel.identity import canonical_hash

from . import current_state as model
from . import current_state_delivery as base
from . import odds_watch


WATCH_CONFIG_PATH = "decision_inputs/odds-watch-v0.json"
WATCH_JSON_PATH = "odds-watch/watch.json"
WATCH_SUMMARY_PATH = "odds-watch/summary.md"


class Collector(base.Collector):
    def collect(self, refresh: dict) -> dict:
        payload = super().collect(refresh)
        if getattr(self, "include_radar_discovery", False):
            from .institutional_radar_reading import attach
            payload = attach(self, payload)
        return payload

    def saved_product(self, lane: str, run: dict) -> dict:
        product = super().saved_product(lane, run)
        if lane != "inbox":
            return product

        artifacts = self.artifacts(run)
        files, _ = self.archive(model.select_artifact(artifacts, "decision-inbox"), run)
        present = {name for name in (WATCH_JSON_PATH, WATCH_SUMMARY_PATH) if name in files}
        if not present:
            product["odds_watch"] = {
                "status": "NOT_AVAILABLE_IN_EXISTING_ARTIFACT",
                "meaning": "NO_TYPED_WATCH_BYTES_NO_TRIGGER_OR_QUIET_INFERRED",
            }
            return product
        model.check(present == {WATCH_JSON_PATH, WATCH_SUMMARY_PATH},
                    "Inbox Odds Watch artifact is partial")

        report = json.loads(files[WATCH_JSON_PATH])
        odds_watch.validate_report(report)
        origin_ref = run["head_sha"]
        model.check(model.SHA.fullmatch(origin_ref) is not None,
                    "Inbox Odds Watch origin commit required")
        config_raw, config_source = self.source({"path": WATCH_CONFIG_PATH, "ref": origin_ref})
        registry_raw, registry_source = self.source({"path": base.REGISTRY_PATH, "ref": origin_ref})
        config = json.loads(config_raw)
        registry = json.loads(registry_raw)
        odds_watch.validate_config(config, registry)
        watch = report["watch"]
        model.check(watch["config_hash"] == canonical_hash(config),
                    "Inbox Odds Watch config identity differs")
        model.check(watch["registry_hash"] == canonical_hash(registry),
                    "Inbox Odds Watch registry identity differs")

        prefix = f"details/inbox/{run['id']}/"
        product["details"][WATCH_JSON_PATH] = self.retain(
            prefix + WATCH_JSON_PATH, files[WATCH_JSON_PATH]
        )
        product["details"][WATCH_SUMMARY_PATH] = self.retain(
            prefix + WATCH_SUMMARY_PATH, files[WATCH_SUMMARY_PATH]
        )
        product["odds_watch"] = {
            "status": "TYPED_ODDS_WATCH_READ_OK",
            "report": report,
            "config_source": config_source,
            "registry_source": registry_source,
            "meaning": "READ_ONLY_PRICE_CONDITION_ATTENTION_NOT_REVALIDATED_DECISION_SPINE_ODDS_OR_ACTION",
        }
        return product


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Read saved GitHub results plus typed Odds Watch; never run market or Research producers"
    )
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--include-radar-discovery", action="store_true")
    parser.add_argument("--include-concept-discovery", action="store_true")
    args = parser.parse_args(argv)
    model.check(not args.include_concept_discovery or args.include_radar_discovery,
                "concept reading requires the existing Radar composition")
    model.check(model.SHA.fullmatch(args.code_commit) is not None, "code commit required")

    from .stock_research_reading import EXTRA_API_CALLS
    api = base.GitHubAPI(os.environ["GH_TOKEN"], max_calls=base.MAX_API_CALLS + EXTRA_API_CALLS)
    prior_commit = None
    previous = None
    try:
        refs = api.get("git/matching-refs/heads/" + model.READ_REF)
        exact = [row for row in refs if row["ref"] == "refs/heads/" + model.READ_REF]
        model.check(len(exact) <= 1, "ambiguous reading ref")
        if exact:
            prior_commit = exact[0]["object"]["sha"]
            previous = json.loads(api.file("current-state.json", prior_commit))
            model.validate_read_package(previous)
        collector = Collector(api, args.code_commit, Path.cwd(), previous, prior_commit)
        collector.include_radar_discovery = args.include_radar_discovery
        collector.include_concept_discovery = args.include_concept_discovery
        refresh = {
            "workflow": ".github/workflows/current-state-read-entry.yml",
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "event": os.environ.get("GITHUB_EVENT_NAME"),
            "trigger_run_id": os.environ.get("TRIGGER_RUN_ID"),
            "publication_status": "BLOB_READBACK_REQUIRED_NOT_UPSTREAM_PRODUCTION_ACCEPTANCE",
        }
        payload = collector.collect(refresh)
        args.output.mkdir(parents=True, exist_ok=False)
        for path, raw in collector.files.items():
            target = args.output / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        if args.publish:
            commit = base.publish(
                api, collector.files, prior_commit, args.code_commit, payload["reading_hash"]
            )
            print("READ_ENTRY_COMMIT=" + commit)
            summary = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary:
                with open(summary, "a") as out:
                    out.write("## Current-state read entry published\n\n")
                    out.write(
                        f"`{model.REPOSITORY}` / `{model.READ_REF}` / commit `{commit}` / `current-state.json`.\n\n"
                    )
                    out.write(
                        "This is a read-only delivery, including validated Odds Watch bytes when present; "
                        "it is not market/Research execution, Action, or natural Sector acceptance.\n"
                    )
        return 0
    except (
        ValueError, KeyError, TypeError, AttributeError, IndexError, OSError,
        RuntimeError, requests.RequestException,
    ) as exc:
        print("READ_ENTRY_PUBLICATION_FAILED: " + type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
