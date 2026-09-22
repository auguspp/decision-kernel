"""One bounded FTShare/CNEquity delivery using the existing source consumers.

No generic job engine, new research executor, retries, trade or automatic egress.
"""
from __future__ import annotations
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from . import ftshare_discovery as discovery
from . import ftshare_financial as financial
from . import ftshare_company_events as company
from . import ftshare_market_inputs as market
from .ftshare_financial import raw_json
from .reviewed_question_reading import _text

VERSION = "kernel-provider-batch-v1"
MAX_REQUESTS = 100
FIELDS = {"version", "market_start", "market_end", "event_start", "year", "report_type",
          "issuers", "reports", "sectors", "concepts", "futures", "build_lake"}
require = discovery._require


def validate(config):
    require(isinstance(config, dict) and set(config) == FIELDS and config["version"] == VERSION, "BATCH_SHAPE")
    start, end = market.day(config["market_start"]), market.day(config["market_end"])
    require(start <= end and (end-start).days <= 92 and 0 <= (end-market.day(config["event_start"])).days <= 366, "BATCH_WINDOW")
    require(type(config["year"]) is int and 1990 <= config["year"] <= 2100
            and config["report_type"] in financial.REPORT_TYPES and type(config["build_lake"]) is bool, "BATCH_PERIOD")
    for key, maximum in (("issuers", 6), ("reports", 6), ("sectors", 3), ("concepts", 3), ("futures", 3)):
        require(isinstance(config[key], list) and len(config[key]) <= maximum, "BATCH_SCOPE_LIMIT")
    require(0 < len(config["issuers"]) and len(set(config["issuers"])) == len(config["issuers"]), "BATCH_ISSUERS")
    for ticker in config["issuers"]: market.security(ticker)
    for key, kind in (("sectors", "sector_members"), ("concepts", "concept_members"), ("futures", "futures_bars")):
        require(len(set(config[key])) == len(config[key]), "BATCH_DUPLICATE_SCOPE")
        for ident in config[key]: market.parameters(kind, ident, config["market_start"], config["market_end"])
    seen = set()
    for report in config["reports"]:
        require(isinstance(report, dict) and set(report) == {"ticker", "issuer_name", "announcement_date", "period"}
                and report["ticker"] in config["issuers"] and report["ticker"] not in seen, "BATCH_REPORT_IDENTITY")
        require(isinstance(report["issuer_name"], str) and 0 < len(report["issuer_name"]) <= 80, "BATCH_REPORT_IDENTITY")
        market.day(report["announcement_date"])
        require(report["period"] == f'{config["year"]}H1' if config["report_type"] == "q2"
                else report["period"] == str(config["year"]), "BATCH_REPORT_PERIOD")
        seen.add(report["ticker"])


def prepare(*, config, output, clock=discovery.now, fetches=None, report_prepare=None):
    """One explicit batch; report discovery never downloads an issuer PDF."""
    from . import stock_research_sources as sources
    validate(config)
    output = Path(output)
    require(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents), "BATCH_OUTPUT_MUST_BE_NEW")
    started = clock()
    require(market.day(config["market_end"]) < discovery._clock(started).astimezone(market.TZ).date(), "BATCH_REQUIRES_COMPLETED_SESSION")
    output.mkdir(parents=True)
    (output / "request.json").write_bytes(raw_json(config))
    fetches = fetches or {}
    attempts, global_stop = [], None

    def bounded(namespace, fn):
        def run(kind, params):
            nonlocal global_stop
            require(global_stop is None, "NOT_ATTEMPTED_AFTER_PROVIDER_STOP")
            require(len(attempts) < MAX_REQUESTS, "BATCH_REQUEST_BUDGET")
            attempts.append({"namespace": namespace, "kind": kind, "parameters": params})
            result = fn(kind, params)
            if result[0] in {401, 429}: global_stop = result[0]
            return result
        return run

    result = {"version": VERSION, "started_at": started, "status": "INCOMPLETE", "families": {},
              "requests": attempts, "model_calls": 0, "pdf_calls": 0, "automatic_retry": False,
              "default_provider_changed": False, "research_execution_allowed": False,
              "investment_authority": "NONE", "daily_research_enabled": False}
    contexts, events, observations = [], [], []

    def save(name, fn):
        try:
            value = fn()
            result["families"][name] = {"status": value.get("status", value.get("projection", {}).get("status", "UNKNOWN")),
                                         "path": name}
            return value
        except Exception as exc:
            # Finite classification only; retain any earlier raw files. Never log credentials/response text.
            result["families"][name] = {"status": "PREPARATION_FAILED", "error_type": type(exc).__name__, "path": name}
            return None

    for item in config["reports"]:
        name = "discovery/" + item["ticker"]
        # This existing call has its own fixed 4-page FTShare + bounded official directory contract.
        save(name, lambda item=item, name=name: (report_prepare or sources.prepare_report_discovery)(
            ticker=item["ticker"][:6], issuer_name=item["issuer_name"], period=item["period"],
            announcement_date=date.fromisoformat(item["announcement_date"]), output=output/name, clock=clock))
    for ticker in config["issuers"]:
        name = "financial/" + ticker
        value = save(name, lambda ticker=ticker, name=name: sources.prepare_financial_context(
            ticker=ticker, year=config["year"], report_type=config["report_type"], output=output/name, clock=clock,
            fetch=bounded("financial", fetches.get("financial", financial.request_page))))
        if value: contexts.append(value)
        name = "company/" + ticker
        value = save(name, lambda ticker=ticker, name=name: sources.prepare_company_event_context(
            ticker=ticker, start_date=date.fromisoformat(config["event_start"]), end_date=date.fromisoformat(config["market_end"]),
            output=output/name, clock=clock, fetch=bounded("company", fetches.get("company", company.request_page))))
        if value: events.append(value)
    specs = [(k, t) for t in config["issuers"] for k in ("stock_bars", "stock_flow")]
    specs += [(k, t) for t in config["sectors"] for k in ("sector_members", "sector_bars")]
    specs += [(k, t) for t in config["concepts"] for k in ("concept_members", "concept_bars")]
    specs += [("futures_bars", t) for t in config["futures"]]
    specs += [("warehouse", t) for t in ("LC", "CU", "RB") if any(x.startswith(t) for x in config["futures"])]
    for kind, ident in specs:
        name = kind + "/" + ident
        captured = save(name, lambda kind=kind, ident=ident, name=name: market.capture(kind=kind, identity=ident,
            start=config["market_start"], end=config["market_end"], output=output/name, clock=clock,
            fetch=bounded("market", fetches.get("market", market.request))))
        if captured:
            view = market.normalize(captured)
            (output/name/"observation.json").write_bytes(raw_json(view))
            result["families"][name].update(status=view["projection"]["status"], capture_status=captured["status"],
                                           observations=len(view["projection"]["observations"]))
            observations.append(view)
    if config["build_lake"]:
        from . import cnequity_bridge as lake
        value = save("cnequity", lambda: lake.build_snapshot(root=output/"cnequity", financial=contexts,
                    companies=events, observations=observations))
        if value:
            result["lake"] = value
            result["lake_reads"] = {}
            cutoff = clock()
            for dataset in value["datasets"]:
                try:
                    read = lake.read(root=output/"cnequity", dataset=dataset, symbols=config["issuers"],
                        start=f'{config["year"]}-01-01', end=discovery._clock(cutoff).date().isoformat(), cutoff=cutoff,
                        expected_inventory=value["files"])
                    (output/("cnequity-"+dataset+".json")).write_bytes(raw_json(read))
                    result["lake_reads"][dataset] = {"status": read["status"], "rows": read["row_count"]}
                except Exception as exc:
                    result["lake_reads"][dataset] = {"status": "READ_FAILED", "error_type": type(exc).__name__}
    result.update(finished_at=clock(), network_attempts=len(attempts),
                  discovery_requests_counted_separately=True, status="BATCH_RETAINED_WITH_EXPLICIT_COVERAGE")
    (output/"batch.json").write_bytes(raw_json(result))
    lines = ["# FTShare + CNEquity 数据接入批次", "", "资料/观察与本地查询，不是研究、投资信号或默认来源切换。", "",
             "| 输入 | 实际状态 |", "|---|---|"]
    for name, block in result["families"].items(): lines.append(f'| {_text(name)} | {_text(block["status"])} |')
    lines += ["", "完整返回、失败与请求范围保留在对应目录。空结果不等于没有事件，当前成分不用于历史归属。",
              "CNEquity为原生Float64查询视图；金额的原始Decimal、原件和核验记录仍由原资料保留。", ""]
    (output/"README.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {p.relative_to(output).as_posix(): {"bytes": p.stat().st_size, "sha256": sha256(p.read_bytes()).hexdigest()}
                for p in sorted(output.rglob("*")) if p.is_file()}
    (output/"manifest.json").write_bytes(raw_json(manifest))
    return result


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Prepare one combined FTShare/CNEquity input batch, no research")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    raw = args.request.read_bytes()
    require(len(raw) <= 16384, "BATCH_REQUEST_TOO_LARGE")
    config = discovery._json(raw)
    result = prepare(config=config, output=args.output)
    print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
