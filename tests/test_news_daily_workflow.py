"""Native trigger, unchanged authority and exact consumer wiring; no dispatch."""
from pathlib import Path

from decision_kernel.runtime import news_daily as s

ROOT = Path(__file__).resolve().parents[1]


def test_source_uses_existing_completion_clock_and_pinned_upstream():
    text=(ROOT/s.WORKFLOW).read_text()
    assert 'workflow_dispatch:' in text and 'workflow_run:' in text
    assert 'workflows: [sector-radar-shadow]' in text and 'types: [completed]' in text
    assert 'schedule:' not in text and '\n  push:' not in text
    assert s.IMAGE in text and ':latest' not in text
    assert '-p 127.0.0.1:4444:4444' in text and '--privileged' not in text and '-v ' not in text
    assert 'github.event.workflow_run.conclusion' not in text
    assert 'github.run_attempt == 1' in text and 'github.event.workflow_run.run_attempt == 1' in text
    assert "github.event.workflow_run.path == '.github/workflows/sector-radar-shadow.yml'" in text
    assert 'contents: write' not in text and 'secrets.' not in text
    assert 'persist-credentials: false' in text
    assert 'head_sha="$GITHUB_SHA"' in text and "r['conclusion']=='success'" in text
    assert 'python -m decision_kernel.runtime.news_daily' in text


def test_publisher_adds_only_owned_completed_native_news_event():
    text=(ROOT/'.github/workflows/current-state-read-entry.yml').read_text()
    assert 'radar-newsnow-daily' in text and '--include-daily-news' in text
    assert "github.event.workflow_run.path == '.github/workflows/radar-newsnow-daily.yml'" in text
    assert "github.event.action == 'completed'" in text
    assert 'docker ' not in text and 'localhost' not in text
    assert '--include-external-radar' in text and '--include-reviewed-questions' in text


def test_original_entry_keeps_new_reading_opt_in():
    text=(ROOT/'src/decision_kernel/runtime/current_state_delivery_with_odds_watch.py').read_text()
    assert 'parser.add_argument("--include-daily-news", action="store_true")' in text
    assert 'getattr(self, "include_daily_news", False)' in text
    assert 'from .news_daily_reading import attach as attach_daily_news' in text
    assert 'collector.include_daily_news = args.include_daily_news' in text
