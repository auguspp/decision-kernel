"""One retained cross-section; calls existing validation and metric functions.

No network, optimization, producer or new ledger. Supply the exact predecessor
five files, trusted code and original seven ZIPs. Read the code before running.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
from statistics import median
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from zipfile import ZipFile


def require(ok, why):
    if not ok:
        raise ValueError(why)


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def calculate(args):
    here = Path(__file__).resolve().parent
    contract = json.loads((here / 'contract.json').read_bytes())
    for name, expected in contract['predecessor_files'].items():
        path = args.predecessor / name
        require(not path.is_symlink() and path.is_file(), 'predecessor file type')
        require(blob(path.read_bytes()) == expected, 'predecessor changed: ' + name)
    require(not args.output.exists() and not args.output.is_symlink(), 'output must be new')
    require(not any(args.output.resolve().is_relative_to(p.resolve()) for p in
                    (args.sources, args.predecessor, args.code_root, here)), 'output overlaps inputs')
    spec = importlib.util.spec_from_file_location('original_case_replay', args.predecessor / 'replay.py')
    predecessor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(predecessor)
    # Native replay checks the seven ZIPs, exact modules, all 334 original rows,
    # calendar, manifest/state/ledger, overlapping prices and source-time identity.
    with TemporaryDirectory() as temp:
        dest = Path(temp) / 'original'
        code = predecessor.run(SimpleNamespace(code_root=args.code_root, sources=args.sources, output=dest))
        require(code == 2, 'original incomplete denominator must remain visible')
        original = json.loads((dest / 'outcomes.json').read_bytes())['evaluation']
    from decision_kernel.identity import canonical_hash, canonical_json
    from decision_kernel.runtime.sector_radar_state import parse_sector_radar_market_state, calculate_sector_radar_state_snapshot_pair
    from decision_kernel.runtime.sector_radar_outcomes import _path_metrics, CONTEXT
    from decision_kernel.runtime.sector_radar_shadow import select_sector_radar_state_entries
    index = json.loads((args.predecessor / 'source-index.json').read_bytes())
    states = []
    for row in index['state_bundles']:
        with predecessor.read_zip(args.sources, row) as z:
            states.append(parse_sector_radar_market_state(z.read('market-state.json').decode()))
    require([s.sessions[-1].isoformat() for s in states] ==
            ['2026-09-22','2026-09-23','2026-09-24','2026-09-28','2026-09-29','2026-09-30'], 'case sessions')
    require(contract['horizon_sessions'] == 5 and contract['signal_session'] == '2026-09-22'
            and contract['as_of_session'] == '2026-09-30', 'fixed case contract')
    with localcontext(CONTEXT):
        pair = calculate_sector_radar_state_snapshot_pair(states[0])
        observations, entry_codes = {}, set()
        families = [('BROAD_881', pair.broad_previous, pair.broad_current),
                    ('GRANULAR_884', pair.granular_previous, pair.granular_current)]
        for family, previous, current in families:
            require(not previous.exclusions and not current.exclusions, 'family exclusions')
            entries = select_sector_radar_state_entries(current=current, previous=previous)
            entry_codes.update(c.thscode for c in entries.candidates)
            for obs in current.observations:
                require(obs.thscode not in observations, 'duplicate subject')
                observations[obs.thscode] = (family, obs)
        mature = {r['thscode']:r for r in original['rows'] if r['status'] == 'EVALUATED'}
        require(set(mature) == entry_codes and len(mature) == 12, 'original cohort mismatch')
        # Freeze all selection flags from T's native snapshots before reading
        # forward prices. This is a retrospective comparison, NOT new forecasts.
        selections = [(code, family, obs, code in entry_codes,
                       obs.horizon_20.excess_return > 0 and obs.horizon_20.cross_sectional_rating >= 90)
                      for code,(family,obs) in sorted(observations.items())]
        prices = [{s.thscode:s for s in state.series} for state in states]
        rows = []
        for code, family, obs, radar, baseline in selections:
            sec = [p[code].closes[-1] for p in prices]
            bench = [p[states[0].benchmark_thscode].closes[-1] for p in prices]
            metrics = _path_metrics(sec, bench)
            if radar:
                prior_metrics = mature[code]['outcome']['metrics']
                for key in ('sector_return','benchmark_return','excess_return','close_path_mfe','close_path_mae',
                            'close_path_excess_mfe','close_path_excess_mae'):
                    require(metrics[key] == Decimal(prior_metrics[key]), 'changed original result')
            rows.append(dict(thscode=code,name=obs.name,family=family,radar_entry=radar,baseline_level=baseline,
                rank_20d=obs.horizon_20.cross_sectional_rank,rating_20d=obs.horizon_20.cross_sectional_rating,
                prior_20d_excess=obs.horizon_20.excess_return,
                original_event_id=mature[code]['event_id'] if radar else None,
                original_group_hash=mature[code]['first_group_hash'] if radar else None,
                source_closes=sec,benchmark_closes=bench,metrics=metrics))
        summaries = []
        selectors = {'RADAR_ENTRY':lambda r:r['radar_entry'], 'BASELINE_LEVEL':lambda r:r['baseline_level'],
            'BOTH':lambda r:r['radar_entry'] and r['baseline_level'],
            'RADAR_ONLY':lambda r:r['radar_entry'] and not r['baseline_level'],
            'BASELINE_ONLY':lambda r:r['baseline_level'] and not r['radar_entry'],
            'NEITHER':lambda r:not r['radar_entry'] and not r['baseline_level']}
        for family, _, current in families:
            for label, selected in selectors.items():
                chosen = [r for r in rows if r['family']==family and selected(r)]
                excess = [r['metrics']['excess_return'] for r in chosen]
                summaries.append(dict(family=family,group=label,count=len(chosen), members=[r['thscode'] for r in chosen],
                    mean_excess=sum(excess,Decimal(0))/len(excess) if excess else None,
                    median_excess=median(excess) if excess else None,
                    mean_absolute=sum((r['metrics']['sector_return'] for r in chosen),Decimal(0))/len(chosen) if chosen else None))
        payload = dict(kind='DESCRIPTIVE_SAME_DATE_BASELINE_CONTEXT_NOT_OUTCOME_LEDGER',contract=contract,
            contract_hash=canonical_hash(contract), original_evaluation_hash=index['evaluation_hash'],
            original_coverage=original['status_counts'], original_ledger_event_count=original['event_count'],
            signal_state_hash=states[0].state_hash, state_hashes=[s.state_hash for s in states],
            family_denominators=dict(Counter(r['family'] for r in rows)),rows=rows,summaries=summaries,
            probability_score=None,method_improvement=None,investment_authority='NONE',
            limitation='ONE_DATE_NOT_HOLDOUT; BASELINE_LEVEL_VS_RADAR_ENTRY_NOT_MATCHED_RISK_OR_CAUSAL_EFFECT')
        result = dict(comparison=payload, comparison_hash=canonical_hash(payload))
        raw = (canonical_json(result)+'\n').encode()
    projection = dict(kind='BOUNDED_BASELINE_PROJECTION_NOT_NEW_EVALUATOR', comparison_hash=result['comparison_hash'],
        full_comparison_sha256=hashlib.sha256(raw).hexdigest(), contract_hash=canonical_hash(contract),
        family_denominators=payload['family_denominators'], original_coverage=payload['original_coverage'],
        summaries=summaries, probability_score=None, method_improvement=None, investment_authority='NONE')
    projection_raw = (canonical_json(projection)+'\n').encode()
    if args.check:
        require(args.check.read_bytes()==projection_raw, 'comparison differs from retained result')
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'comparison.json').write_bytes(raw)
    (args.output/'result.json').write_bytes(projection_raw)
    print('BASELINE_MATCH' if args.check else 'BASELINE_COMPUTED', result['comparison_hash'])
    print(json.dumps(json.loads(canonical_json(summaries)),ensure_ascii=False,indent=2))
    return 0


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('predecessor','code-root','sources','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--check',type=Path)
    try:
        raise SystemExit(calculate(p.parse_args()))
    except (ValueError,KeyError,OSError,RuntimeError) as exc:
        print('COMPARISON_NOT_COMPLETED: '+str(exc),file=sys.stderr)
        raise SystemExit(1)
