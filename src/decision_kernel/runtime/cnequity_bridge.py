"""Read CNEquity's native lake without importing its scheduler or changing providers.

The optional dependency owns Parquet, revisions, PIT and adjustment algorithms.
Kernel retains provenance and never promotes a lake read into market authority.
"""
from __future__ import annotations

from datetime import date, datetime
from importlib.metadata import version
from pathlib import Path
import hashlib
import re

from .ftshare_financial import raw_json
from .ftshare_discovery import _require as require

VERSION = 'cnequity-bridge-v1'
UPSTREAM_VERSION = '0.11.0'
UPSTREAM_COMMIT = '1650e384a3fd1f67a70144a489acc91432f1df27'
DATASETS = {'daily_bars', 'adj_factors', 'corporate_actions', 'financial_statement_items',
            'shareholder_counts', 'index_constituents', 'industry_members', 'sector_members',
            'instruments', 'trading_status'}
MAX_FILES, MAX_LAKE_BYTES, MAX_ROWS = 512, 128 * 1024 * 1024, 4096


def _path(path):
    path = Path(path)
    require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents), 'LAKE_SYMLINK_REJECTED')
    return path


def _identity(root):
    """Bounded immutable-snapshot identity; no network or external link following."""
    root = _path(root)
    require(root.is_dir(), 'LAKE_NOT_FOUND')
    files = sorted(root.rglob('*'))
    require(not any(p.is_symlink() for p in files), 'LAKE_SYMLINK_REJECTED')
    files = [p for p in files if p.is_file()]
    require(len(files) <= MAX_FILES and sum(p.stat().st_size for p in files) <= MAX_LAKE_BYTES,
            'LAKE_IDENTITY_BUDGET')
    return [{'path': str(p.relative_to(root)), 'bytes': p.stat().st_size,
             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]


def read_lake(*, data_root, dataset, start, end, symbols, output, as_of=None,
              adjust=None, revision_map=None):
    """Native strict read; absent historical evidence is NOT inferred from dates."""
    require(dataset in DATASETS and isinstance(start, date) and not isinstance(start, datetime)
            and isinstance(end, date) and not isinstance(end, datetime) and start <= end,
            'LAKE_SCOPE_INVALID')
    require(isinstance(symbols, (list, tuple)) and 1 <= len(symbols) <= 6
            and len(set(symbols)) == len(symbols)
            and all(isinstance(s, str) and re.fullmatch(r'[0-9]{6}\.(?:SH|SZ|BJ)', s) for s in symbols),
            'LAKE_SECURITY_INVALID')
    require(adjust in {None, 'qfq', 'hfq'} and (adjust is None or dataset == 'daily_bars'), 'LAKE_ADJUST_INVALID')
    require(as_of is None or type(as_of) is date, 'LAKE_ASOF_INVALID')
    require(revision_map is None or isinstance(revision_map, dict)
            and set(revision_map) <= {dataset, 'adj_factors'}
            and all(type(v) is int and v > 0 or isinstance(v, str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,96}', v)
                    for v in revision_map.values()), 'LAKE_REVISION_INVALID')
    if adjust and revision_map is not None:
        require(set(revision_map) == {'daily_bars', 'adj_factors'}, 'INDEPENDENT_FACTOR_REVISION_REQUIRED')
    require(version('cnequity') == UPSTREAM_VERSION, 'CNEQUITY_VERSION_MISMATCH')
    from cnequity.query import load
    root, output = _path(data_root), _path(output)
    require(not output.exists() and root.resolve() not in output.resolve().parents,
            'CREATE_ONLY_EXTERNAL_OUTPUT_REQUIRED')
    before = _identity(root)
    # This reads native tables only. It never runs cne init/run/backfill or a provider.
    frame = load(dataset, data_root=root, start=start, end=end, symbols=list(symbols),
                 as_of=as_of, adjust=adjust, strict_adj=True, strict_universe=True,
                 pit_mode='strict', revision_map=revision_map)
    after = _identity(root)
    require(before == after, 'LAKE_CHANGED_DURING_READ')
    require(frame.height <= MAX_ROWS, 'LAKE_RESULT_BUDGET')
    require({'source', 'data_version', 'fetched_at'} <= set(frame.columns), 'LAKE_LINEAGE_MISSING')
    rows = frame.to_dicts()
    require(all(all(row.get(k) is not None for k in ('source','data_version','fetched_at'))
                for row in rows), 'LAKE_LINEAGE_MISSING')
    if dataset == 'daily_bars':
        require(all(row['data_version'] == 'v2' for row in rows), 'DAILY_VOLUME_V2_REQUIRED')
    result = {'kind': 'CNEQUITY_READ_CONTEXT', 'adapter_version': VERSION,
              'upstream_version': UPSTREAM_VERSION, 'audited_upstream_commit': UPSTREAM_COMMIT,
              'dataset': dataset, 'start': start, 'end': end, 'symbols': list(symbols),
              'as_of': as_of, 'pit_mode': 'strict', 'adjust': adjust,
              'strict_adjustment': True, 'revisions': revision_map,
              'status': 'CONTEXT_READY' if rows else 'NO_ROWS_FOR_STRICT_SCOPE',
              'source_files': before, 'rows': rows, 'network_calls': 0,
              'source_identity': 'ORIGINAL_ROW_SOURCE_NOT_CNEQUITY_AS_INDEPENDENT_PROVIDER',
              'market_qualification': 'NOT_GRANTED', 'investment_authority': 'NONE'}
    raw = raw_json(result)
    require(len(raw) <= 448 * 1024, 'LAKE_CONTEXT_TOO_LARGE')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'cnequity-context.json').write_bytes(raw)
    return result


def retain_bars(*, rows, output):
    """Put explicitly sourced share-volume bars in a NEW native CNEquity lake.

    This is a storage bridge, not acquisition or independent verification. The
    original exact JSON is retained beside Float64 Parquet values.
    """
    require(version('cnequity') == UPSTREAM_VERSION, 'CNEQUITY_VERSION_MISMATCH')
    require(isinstance(rows, list) and 0 < len(rows) <= MAX_ROWS, 'BAR_SCOPE_INVALID')
    for row in rows:
        require(isinstance(row, dict) and row.get('data_version') == 'v2'
                and row.get('volume_unit') == 'SHARES' and row.get('currency') == 'CNY'
                and row.get('adjustment') == 'NONE'
                and isinstance(row.get('source'), str) and row['source']
                and isinstance(row.get('original_sha256'), str)
                and re.fullmatch(r'[a-f0-9]{64}', row['original_sha256']), 'BAR_LINEAGE_OR_UNITS_INVALID')
    output = _path(output)
    require(not output.exists(), 'LAKE_EXISTS')
    import polars as pl
    from cnequity.domain.schemas import DAILY_BARS_SCHEMA
    from cnequity.storage.parquet import StagingWriter, compact_dataset
    native = [{k: row[k] for k in DAILY_BARS_SCHEMA} for row in rows]
    frame = pl.DataFrame(native, schema=DAILY_BARS_SCHEMA, strict=True)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'original-bars.json').write_bytes(raw_json(rows))
    staging, curated = output / 'staging', output / 'curated'
    StagingWriter(staging).write_batch('daily_bars', 'retained', '0', frame)
    compact_dataset(staging, curated, 'daily_bars', 'retained')
    return {'kind': 'RETAINED_NATIVE_CNEQUITY_LAKE', 'source_files': _identity(output),
            'network_calls': 0, 'independent_provider_verification': False}
