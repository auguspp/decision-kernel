"""Reuse CNEquity 0.11's native lake writer and strict reader, without its scheduler.

The optional dependency is isolated from core. Every snapshot is create-only;
Decimal input remains in the original Kernel files, not replaced by Float64 views.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from hashlib import sha256
import importlib
import json
from pathlib import Path

from .ftshare_financial import raw_json
from .ftshare_discovery import _clock, _require

UPSTREAM_VERSION = "0.11.0"
UPSTREAM_COMMIT = "1650e384a3fd1f67a70144a489acc91432f1df27"
ALLOWED = {"daily_bars", "financial_statement_items", "shareholder_counts", "industry_members", "sector_members", "adj_factors"}
MAX_FILES, MAX_LAKE_BYTES, MAX_ROWS = 1024, 128 * 1024 * 1024, 100_000


def native():
    try:
        cne = importlib.import_module("cnequity")
        _require(cne.__version__ == UPSTREAM_VERSION, "CNEQUITY_VERSION_DIFFERS")
        return importlib.import_module("polars"), importlib.import_module("cnequity.query"), importlib.import_module("cnequity.storage.parquet")
    except ImportError:
        raise ValueError("CNEQUITY_OPTIONAL_DEPENDENCY_NOT_INSTALLED") from None


def inventory(root):
    root = Path(root)
    _require(root.is_dir() and not root.is_symlink() and not any(x.is_symlink() for x in root.parents), "LAKE_ROOT_INVALID")
    found, total = {}, 0
    for p in sorted(root.rglob("*")):
        _require(not p.is_symlink(), "LAKE_SYMLINK_REJECTED")
        if not p.is_file(): continue
        size = p.stat().st_size; total += size
        _require(len(found) < MAX_FILES and total <= MAX_LAKE_BYTES, "LAKE_READ_BUDGET")
        found[p.relative_to(root).as_posix()] = {"bytes": size, "sha256": sha256(p.read_bytes()).hexdigest()}
    return found


def read(*, root, dataset, symbols, start, end, cutoff, adjust=None, expected_inventory=None):
    """Native read with strict adjustments/PIT and an extra exact timestamp cutoff.

    Explicit symbols only: this does not certify a survivorship-complete universe.
    all_vintages keeps late same-day rows from masking earlier eligible vintages.
    """
    _require(dataset in ALLOWED and isinstance(symbols, list) and 0 < len(symbols) <= 6
             and len(set(symbols)) == len(symbols), "LAKE_QUERY_SCOPE")
    from .ftshare_market_inputs import security, day
    for symbol in symbols: security(symbol)
    _require(day(start) <= day(end) and adjust in {None, "qfq", "hfq"}, "LAKE_QUERY_SCOPE")
    before = inventory(root)
    _require(expected_inventory is None or expected_inventory == before, "LAKE_CONTENT_CHANGED")
    pl, query, _ = native()
    at = _clock(cutoff).astimezone(timezone.utc)
    # Exact factors are required; never accept CNEquity's permissive factor=1 fallback.
    frame = query.load(dataset, data_root=Path(root), symbols=symbols, start=start, end=end,
                       as_of=at.date(), pit_mode="strict", all_vintages=True,
                       adjust=adjust, strict_adj=True)
    _require(frame.height <= MAX_ROWS, "LAKE_ROW_BUDGET")
    for key in ("fetched_at", "observed_at", "available_at", "source_published_at"):
        if key in frame.columns:
            frame = frame.filter(pl.col(key).is_null() | (pl.col(key) <= pl.lit(at)))
    if "source" in frame.columns:
        _require(not frame.filter(pl.col("source") == "mock").height, "MOCK_LAKE_REJECTED")
    _require(inventory(root) == before, "LAKE_CHANGED_DURING_READ")
    rows = frame.to_dicts()
    # Native Float64 is a query view, never the monetary source ledger.
    return {"upstream": "rootSunc/CNEquity", "version": UPSTREAM_VERSION, "reviewed_commit": UPSTREAM_COMMIT,
            "dataset": dataset, "status": "READ" if rows else "NO_ELIGIBLE_ROWS", "rows": rows,
            "row_count": len(rows), "source_files": before, "cutoff": cutoff, "symbols": symbols,
            "adjust": adjust, "strict_adj": True, "pit_mode": "strict", "all_vintages": True,
            "precision": "NATIVE_FLOAT64_QUERY_VIEW_ORIGINAL_DECIMAL_RETAINED_SEPARATELY",
            "historical_availability": "RETRIEVAL_BOUNDED_NOT_PRIMARY_PUBLICATION_CERTIFICATION",
            "investment_authority": "NONE", "research_execution_allowed": False, "network_calls": 0}


def build_snapshot(*, root, financial=(), companies=(), observations=()):
    """Write actual retained FTShare views through native StagingWriter/compact.

    No all-market init/backfill, acquisition, synthetic factors or hidden source
    fallback. Missing families remain absent. Root must not already exist.
    """
    root = Path(root)
    _require(not root.exists() and not root.is_symlink() and not any(x.is_symlink() for x in root.parents), "LAKE_MUST_BE_NEW")
    pl, _, storage = native()
    from cnequity.config import Config
    from cnequity.domain.schemas import DATASET_SCHEMAS, data_version_for
    from cnequity.domain.datasets import DATASETS
    root.mkdir(parents=True)
    cfg = Config(data_root=root)
    datasets = {}

    def add(dataset, values, received):
        values.update(source="ftshare", data_version=data_version_for(dataset), fetched_at=_clock(received))
        datasets.setdefault(dataset, []).append(values)

    for context in financial:
        for family, block in context["families"].items():
            if family not in {"balance", "income", "cashflow"} or block.get("status") != "SECONDARY_CONTEXT_READY": continue
            for r in block["records"]:
                for code, metric in r["metrics"].items():
                    if metric["value"] is None: continue
                    period = str(context["year"]) + {"q1": "Q1", "q2": "Q2", "q3": "Q3", "annual": "Q4"}[context["report_type"]]
                    add("financial_statement_items", {"symbol": context["ticker"], "report_period": period,
                        "statement_type": family, "item_code": code, "item_value": float(metric["value"]),
                        "announce_date": date.fromisoformat(r["publish_date"])}, r["retrieved_at"])
    for context in companies:
        block = context["families"].get("holder_counts", {})
        if block.get("status") != "SECONDARY_CONTEXT_READY": continue
        for r in block["records"]:
            add("shareholder_counts", {"symbol": context["ticker"], "count_date": date.fromisoformat(r["report_date"]),
                "holder_count": float(r["holder_count"]), "holder_count_change_pct": None,
                "avg_float_shares": None, "avg_holding_value": None,
                "announce_date": date.fromisoformat(r["publish_date"])}, r["retrieved_at"])
    for report in observations:
        p = report["projection"]
        if p["status"] != "OBSERVATIONS_NORMALIZED": continue
        for r in p["observations"]:
            if p["input_kind"] == "stock_bars":
                _require(r["adjustment"] == "none" and r["volume_unit"] == "SHARES", "LAKE_BAR_UNITS")
                add("daily_bars", {"symbol": r["ticker"], "trade_date": date.fromisoformat(r["date"]),
                    **{k: float(r[k]) for k in ("open", "high", "low", "close")},
                    "volume": int(r["volume"]), "amount": float(r["turnover"])}, r["received_at"])
            elif p["input_kind"] in {"sector_members", "concept_members"}:
                dataset = "industry_members" if p["input_kind"] == "sector_members" else "sector_members"
                field = "industry" if dataset == "industry_members" else "sector"
                values = {"symbol": r["ticker"], field + "_code": r["board_code"], field + "_name": r["board_name"],
                          "as_of_date": _clock(r["membership_as_of"]).date()}
                if field == "industry": values["classification_system"] = "THS"
                add(dataset, values, r["received_at"])
    counts = {}
    for dataset, rows in datasets.items():
        _require(len(rows) <= MAX_ROWS, "LAKE_ROW_BUDGET")
        frame = pl.DataFrame(rows, schema=DATASET_SCHEMAS[dataset], strict=True)
        storage.StagingWriter(cfg.staging_root).write_batch(dataset, "kernel", "0", frame)
        storage.compact_dataset(cfg.staging_root, cfg.curated_root, dataset, "kernel",
                                partition_col=DATASETS[dataset].partition_col)
        counts[dataset] = len(rows)
    return {"status": "NATIVE_LAKE_SNAPSHOT_WRITTEN" if counts else "NO_ELIGIBLE_DATASETS",
            "version": UPSTREAM_VERSION, "reviewed_commit": UPSTREAM_COMMIT, "datasets": counts,
            "files": inventory(root), "network_calls": 0, "default_source_changed": False,
            "limitation": "NATIVE_QUERY_VIEW_NOT_ORIGINAL_DECIMAL_LEDGER_OR_PRIMARY_EVIDENCE"}
