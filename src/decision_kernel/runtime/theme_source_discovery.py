"""Source-text leads into the existing bounded theme probe; no network or signal.

Literal catalog mentions are retrieval leads, including denials and quotations.
They are NOT accepted facts, sentiment, business exposure, or first discoveries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from html import escape
from pathlib import Path

from decision_kernel.evidence import EvidenceArtifact
from decision_kernel.identity import canonical_hash, canonical_json
from . import theme_radar_probe as probe

VERSION = "retained-text-catalog-mentions-v0"
SEMANTICS = "SOURCE_TEXT_LEADS_NOT_MARKET_SIGNALS_OR_FACT_ACCEPTANCE"
MAX_SOURCES, MAX_FIELDS = 32, 16
MAX_TEXT_CHARS, MAX_TOTAL_CHARS = 16384, 131072
MAX_MATCHES, MAX_SCAN_CELLS = 2048, 64 * 1024 * 1024
ASCII_WORD = re.compile(r"[A-Za-z0-9_]")
INPUT_FIELDS = {"schema_version", "provenance", "source_scope", "concept_catalog",
                "industry_catalog", "industries", "sources"}


def _sources(rows, as_of):
    if not isinstance(rows, list) or len(rows) > MAX_SOURCES:
        raise ValueError("source record budget exceeded; no truncation")
    sources, identities, idempotency, total = {}, {}, {}, 0
    for row in rows:
        probe._keys(row, {"recorded_at", "evidence", "text_fields"})
        evidence = EvidenceArtifact.model_validate(row["evidence"])
        recorded = probe._clock(row["recorded_at"])
        if not evidence.retrieved_at <= recorded <= as_of:
            raise ValueError("source must be retrieved and recorded by the input cutoff")
        fields = row["text_fields"]
        if not isinstance(fields, list) or len(fields) > MAX_FIELDS:
            raise ValueError("explicit retained-text field list required within budget")
        texts, seen = [], set()
        for field in fields:
            if field == ["permitted_excerpt"]:
                text = evidence.permitted_excerpt
            elif (isinstance(field, list) and len(field) == 2
                  and field[0] == "extracted_structured_values" and isinstance(field[1], str)):
                values = evidence.extracted_structured_values or {}
                if field[1] not in values:
                    raise ValueError("selected retained text field is missing")
                text = values[field[1]]
            else:
                raise ValueError("only permitted excerpt or an explicit retained structured field may be scanned")
            key = tuple(field)
            if key in seen:
                raise ValueError("duplicate retained-text field")
            seen.add(key)
            if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS:
                raise ValueError("selected field must contain bounded retained text, not metadata or numbers")
            texts.append({"field": field, "text": text,
                          "text_sha256": hashlib.sha256(text.encode()).hexdigest()})
        value = {"evidence": evidence.model_dump(mode="python"), "recorded_at": recorded,
                 "texts": sorted(texts, key=lambda x: x["field"])}
        key = canonical_hash(value)
        for identity, mapping in ((str(evidence.id), identities), (evidence.idempotency_key, idempotency)):
            if identity in mapping and mapping[identity] != key:
                raise ValueError("conflicting source identity or idempotency key; retain separate explicit versions")
            mapping[identity] = key
        if key not in sources:
            total += sum(len(x["text"]) for x in texts)
            sources[key] = {"source_record_hash": key, **value}
    if total > MAX_TOTAL_CHARS:
        raise ValueError("aggregate retained-text budget exceeded")
    return [sources[k] for k in sorted(sources)], total


def _offsets(text, label):
    """Unicode character offsets; exact case, all nested labels, no alias guessing."""
    start = 0
    while (start := text.find(label, start)) >= 0:
        end = start + len(label)
        # Prevent an ASCII label such as AI matching inside RAIL. Chinese has no
        # inferred word segmentation; a substring is a mention, not a meaning.
        left = ASCII_WORD.fullmatch(label[0]) and start and ASCII_WORD.fullmatch(text[start - 1])
        right = ASCII_WORD.fullmatch(label[-1]) and end < len(text) and ASCII_WORD.fullmatch(text[end])
        if not left and not right:
            yield start, end
        start += 1


def discover_theme_sources(state, inputs, *, as_of, generated_at):
    """Validate the full supplied source scope, keep every lead, then budget a plan."""
    probe._keys(inputs, INPUT_FIELDS)
    if (type(inputs["schema_version"]) is not int or inputs["schema_version"] != 1
            or inputs["provenance"] not in {probe.SUPPLIED, probe.SYNTHETIC}):
        raise ValueError("unsupported source-discovery schema or provenance")
    scope = inputs["source_scope"]
    if not isinstance(scope, str) or not 1 <= len(scope.strip()) <= 1600:
        raise ValueError("explicit supplied-source scope required")
    as_of, generated = probe._clock(as_of), probe._clock(generated_at)
    if generated < as_of:
        raise ValueError("generation precedes source cutoff")
    state = probe.parse_sector_radar_market_state(probe.serialize_sector_radar_market_state(state))
    close = probe._window(state, as_of)
    if state.updated_at > as_of or state.benchmark_thscode != "000300.SH":
        raise ValueError("saved state must precede source cutoff and use CSI300")
    catalogs = []
    for field, tag in (("concept_catalog", "cn_concept"), ("industry_catalog", "industry")):
        body = probe._record(inputs[field], probe.CATALOG, {"tag": tag}, lower=close, upper=as_of)
        if len(body["data"].get("item", [])) > 4096:
            raise ValueError("catalog reading budget exceeded")
        catalogs.append(probe.normalize_hithink_industry_catalog(body))
    concepts, industry = catalogs
    if industry.catalog_hash != state.catalog_hash or industry.unexpected_industries:
        raise ValueError("industry catalog drift from saved market identity")
    if ({x.thscode for x in concepts.identities} & {x.thscode for x in industry.identities}
            or any(re.fullmatch(r"(881|884)[0-9]{3}\.TI", x.thscode) for x in concepts.identities)):
        raise ValueError("concept catalog must remain disjoint from industries")
    industries = probe._choices(inputs["industries"], industry, probe.MAX_INDUSTRIES, 0)
    if any(not re.fullmatch(r"881[0-9]{3}\.TI", x["thscode"]) for x in industries):
        raise ValueError("industry probes must use 881; no parent-child double count")
    sources, text_chars = _sources(inputs["sources"], as_of)
    names = {}
    for identity in concepts.identities:
        if len(identity.name) > 128:
            raise ValueError("catalog label exceeds text-matching budget")
        names.setdefault(identity.name, []).append(identity.thscode)
    if len(names) * text_chars > MAX_SCAN_CELLS:
        raise ValueError("literal matching work budget exceeded; no truncated source scan")
    catalog_hash = canonical_hash({"tag": "cn_concept", "identities": [asdict(x) for x in concepts.identities]})
    matches, matched_sources, count = {}, set(), 0
    for source in sources:
        for retained in source["texts"]:
            text = retained["text"]
            for label in sorted(names):
                for start, end in _offsets(text, label):
                    count += 1
                    if count > MAX_MATCHES:
                        raise ValueError("mention budget exceeded; no truncated discovery")
                    mention = {"source_record_hash": source["source_record_hash"],
                               "field": retained["field"], "text_sha256": retained["text_sha256"],
                               "start": start, "end": end, "matched_text": text[start:end],
                               "context_start": max(0, start - 100), "context_end": min(len(text), end + 100),
                               "context": text[max(0, start - 100):min(len(text), end + 100)]}
                    matches.setdefault(label, []).append(mention)
                    matched_sources.add(source["source_record_hash"])
    leads = []
    for label in sorted(matches):
        value = {"name": label, "catalog_thscodes": sorted(names[label]), "mentions": matches[label]}
        leads.append({"lead_id": canonical_hash({"version": VERSION, "catalog_hash": catalog_hash, **value}),
                      **value, "identity_status": "EXACT_UNIQUE_LABEL" if len(names[label]) == 1 else "AMBIGUOUS_CATALOG_LABEL"})
    blockers = []
    if not sources:
        blockers.append("NO_SOURCE_RECORDS")
    if any(not s["texts"] for s in sources):
        blockers.append("INCOMPLETE_RETAINED_TEXT_SCOPE")
    if any(len(lead["catalog_thscodes"]) != 1 for lead in leads):
        blockers.append("AMBIGUOUS_CATALOG_LABEL")
    if len({c for lead in leads for c in lead["catalog_thscodes"]}) > probe.MAX_THEMES:
        blockers.append("ACQUISITION_BUDGET_EXCEEDED")
    # Rebuilding an old scan cannot backdate a NEW request plan. The original
    # cutoff stays fixed, and only an actual current planning clock can qualify.
    try:
        probe._window(state, generated)
    except ValueError:
        blockers.append("PLAN_REQUIRES_CURRENT_SAVED_MARKET_STATE")
    coverage = [{"source_record_hash": s["source_record_hash"],
                 "status": "NO_RETAINED_TEXT_SELECTED" if not s["texts"] else
                 "LITERAL_MENTIONS_FOUND" if s["source_record_hash"] in matched_sources else "NO_LITERAL_CATALOG_MENTION"}
                for s in sources]
    projection = {"schema_version": 1, "formula_version": VERSION, "semantics": SEMANTICS,
                  "provenance": inputs["provenance"], "as_of": as_of, "source_scope": scope,
                  "market_state_hash": state.state_hash, "market_session": state.sessions[-1],
                  "concept_catalog_hash": catalog_hash, "input_hash": canonical_hash(inputs),
                  "sources": sources, "coverage": coverage, "leads": leads,
                  "supplied_source_records": len(inputs["sources"]), "unique_source_records": len(sources),
                  "duplicate_source_records": len(inputs["sources"]) - len(sources), "text_characters": text_chars,
                  "catalog_identity_count": len(concepts.identities), "literal_occurrences": count,
                  "global_source_coverage": "NOT_ESTABLISHED", "independent_source_count": None,
                  "first_system_discovery_at": None, "sentiment": "NOT_INFERRED",
                  "economic_truth": "NOT_ESTABLISHED", **probe.AUTHORITY}
    projection = json.loads(canonical_json(projection))
    projection_hash = canonical_hash(projection)
    plan = None
    if leads and not blockers:
        themes = [{"thscode": lead["catalog_thscodes"][0], "name": lead["name"],
                   "reason": f"Retained-text lead {lead['lead_id']} in scan {projection_hash}; mention only, not sentiment or fact acceptance"}
                  for lead in leads]
        plan = probe.make_theme_plan(state, inputs["concept_catalog"], inputs["industry_catalog"],
                                     themes=themes, industries=industries, planned_at=generated.isoformat())
    status = "BLOCKED" if blockers else "SOURCE_LEADS_PLANNED" if leads else "NO_LITERAL_CATALOG_MENTIONS"
    result = {"projection": projection, "projection_hash": projection_hash, "generated_at": generated,
              "status": status, "acquisition_blockers": blockers, "acquisition_plan": plan,
              "requests_executed": 0}
    return json.loads(canonical_json({**result, "result_hash": canonical_hash(result)}))


def render_source_discovery(report):
    """Render validated builder output; not an alternative arbitrary-JSON ingress."""
    body = {k: v for k, v in report.items() if k != "result_hash"}
    p = report["projection"]
    if (canonical_hash(body) != report["result_hash"] or canonical_hash(p) != report["projection_hash"]
            or p["semantics"] != SEMANTICS or any(p[k] != v for k, v in probe.AUTHORITY.items())):
        raise ValueError("invalid source discovery result identity or authority")
    e = lambda x: escape(str(x), quote=True)
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">',
             '<title>主题来源线索</title><style>body{font:16px/1.7 system-ui;max-width:960px;margin:24px auto;padding:16px}section{border:1px solid;padding:16px;margin:16px 0}pre,p,code,blockquote,summary{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}</style><main>',
             '<h1>主题来源线索 · 不是投资信号</h1><p>SHADOW OBSERVATION ONLY · Human / Research / Investment authority = NONE</p>',
             f'<p>状态：{e(report["status"])}<br>输入范围：{e(p["source_scope"])}<br>资料截止：{e(p["as_of"])}<br>生成／计划时间：{e(report["generated_at"])}</p>',
             '<p>在完整所供概念目录中匹配指定留存文本的字面提及。否认、风险提示与引述同样可能产生线索；不推断看多、受益、基本面改善或首次发现。没有匹配不等于没有主题或机会。当前没有新闻采集或市场请求。</p>',
             f'<p>目录身份 {p["catalog_identity_count"]}；所供记录 {p["supplied_source_records"]}；去除完全重复后 {p["unique_source_records"]}；线索标签 {len(p["leads"])}。记录数不是独立来源数，提及次数不构成排名。</p>',
             f'<p>采集阻塞原因：{e(report["acquisition_blockers"] or "无；仅生成待执行计划")}</p>']
    by_source = {s["source_record_hash"]: s for s in p["sources"]}
    for lead in p["leads"]:
        parts.append(f'<section><h2>{e(lead["name"])} · {e(", ".join(lead["catalog_thscodes"]))}</h2><p>{e(lead["identity_status"])}</p>')
        for mention in lead["mentions"]:
            source = by_source[mention["source_record_hash"]]
            ev = source["evidence"]
            parts.append(f'<p>{e(ev["source_identifier"])} · {e(ev["source_type"])} · {e(ev["retention_mode"])} / {e(ev["replayability_level"])}</p><blockquote>{e(mention["context"])}</blockquote><p>字段 {e(mention["field"])}；Unicode 字符区间 [{mention["start"]}, {mention["end"]})；来源 {e(ev["source_locator"])}；采集 {e(ev["retrieved_at"])}；本记录收录 {e(source["recorded_at"])}</p>')
        parts.append('</section>')
    parts.append(f'<details><summary>完整来源、未匹配记录与可复核计划</summary><pre>{e(canonical_json(report))}</pre></details><a href="source-discovery.json">完整 JSON</a><p>完整原句仍在输入副本中；摘录哈希不认证网站原文或历史可用性。超过预算时保留全部线索，不生成前三个主题的部分计划。</p></main></html>')
    return "\n".join(parts) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline source-text theme leads; zero requests and zero signal writes.")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        probe._safe_path(args.output)
        if args.output.exists() or any(args.output.resolve().is_relative_to(p.resolve().parent) for p in (args.state, args.input)):
            raise ValueError("output must be new and outside source directories")
        state_raw, input_raw = probe._read(args.state), probe._read(args.input)
        inputs = json.loads(input_raw, object_pairs_hook=probe._unique_object, parse_float=Decimal)
        report = discover_theme_sources(probe.parse_sector_radar_market_state(state_raw.decode()), inputs,
                                        as_of=args.as_of, generated_at=datetime.now(timezone.utc).isoformat())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".theme-source-", dir=args.output.parent) as temporary:
            stage = Path(temporary) / "result"; stage.mkdir()
            files = {"index.html": render_source_discovery(report).encode(),
                     "source-discovery.json": (canonical_json(report) + "\n").encode(),
                     "saved-market-state.json": state_raw, "supplied-input.json": input_raw}
            if report["acquisition_plan"] is not None:
                files["probe-plan.json"] = (canonical_json(report["acquisition_plan"]) + "\n").encode()
            for name, data in files.items():
                (stage / name).write_bytes(data)
            receipt = {"result_hash": report["result_hash"], "semantics": "READING_COPY_NOT_STATE_RECOVERY_OR_SOURCE_AUTHENTICATION",
                       "files": {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}, **probe.AUTHORITY}
            (stage / "files.json").write_text(canonical_json(receipt) + "\n", encoding="utf-8")
            if probe._read(args.state) != state_raw or probe._read(args.input) != input_raw:
                raise ValueError("source input changed during discovery")
            probe._safe_path(args.output)
            if args.output.exists():
                raise ValueError("output appeared during discovery")
            stage.rename(args.output)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print("Theme source discovery unavailable:", type(exc).__name__)
        return 2
    print(report["status"], "; no requests executed or market events created")
    return 2 if report["acquisition_blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
