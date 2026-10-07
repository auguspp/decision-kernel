"""Finite YTO workpaper arithmetic. Offline; new output is create-only.

No source truth, current consensus, investment authority or historical PIT
performance is inferred. --source-zip checks selected retained data, not the
repository's full native market verifier. Nothing is executed on archive read.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

KIND = 'D1_YTO_COST_PROOF_AND_PRICE_IMPLIED_REQUIREMENTS'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def load(raw: bytes) -> dict[str, Any]:
    require(0 < len(raw) <= 2_000_000, 'input size outside workpaper bound')
    value = json.loads(raw, object_pairs_hook=unique, parse_float=Decimal,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    require(isinstance(value, dict), 'JSON object required')
    return value


def number(value: str) -> Decimal:
    require(type(value) is str, 'decimal string required')
    result = Decimal(value)
    require(result.is_finite(), 'finite decimal required')
    return result


def encode(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def verify_archive(inp: dict[str, Any], path: Path) -> dict[str, Any]:
    """Read exact members without extraction; match original selected source rows."""
    require(path.is_file() and not path.is_symlink(), 'regular archive required')
    expected = inp['price_context']['archive']
    require(path.stat().st_size == expected['bytes'], 'archive byte count differs')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected['sha256'], 'archive digest differs')
    with zipfile.ZipFile(path) as z:
        require(len(z.namelist()) == len(set(z.namelist())), 'duplicate ZIP names')
        require(sum(i.file_size for i in z.infolist()) < 10_000_000, 'expanded archive bound')
        require(z.testzip() is None, 'archive CRC differs')
        receipt = load(z.read('receipt.json'))
        identity = receipt['workflow']
        require(identity['GITHUB_REPOSITORY'] == inp['delivery']['repository']
                and identity['GITHUB_RUN_ID'] == str(expected['run_id'])
                and identity['GITHUB_RUN_ATTEMPT'] == str(expected['attempt'])
                and identity['GITHUB_SHA'] == expected['original_code_commit'], 'archive identity differs')
        require(receipt['finished_at'] == expected['received_through'], 'source clock differs')
        for name, descriptor in receipt['files'].items():
            member = z.read(name)
            require(len(member) == descriptor['bytes']
                    and hashlib.sha256(member).hexdigest() == descriptor['sha256'], 'response digest differs')
        for row in inp['price_context']['selected_original_rows']:
            member = z.read(row['source_file'])
            require(hashlib.sha256(member).hexdigest() == row['source_sha256'], 'selected source differs')
            data = load(member)['data']
            matches = [dict(zip(data['fields'], values, strict=True)) for values in data['items']
                       if values[0] == inp['symbol']]
            require(len(matches) == 1, 'selected symbol not unique')
            require({k: str(v) for k, v in matches[0].items()} == row['row'], 'selected row differs')
        report = load(z.read('report.json'))
        matches = [r for r in report['rows'] if r[0] == inp['symbol']]
        require(matches == [inp['price_context']['saved_report_row']], 'saved report row differs')
    return {'archive_hash_crc_and_identity': 'PASS',
            'response_digest_count': len(receipt['files']),
            'selected_row_count': len(inp['price_context']['selected_original_rows']),
            'native_whole_price_verifier': 'NOT_RUN'}


def calculate(raw: bytes) -> dict[str, Any]:
    inp = load(raw)
    require(inp['kind'] == KIND and inp['symbol'] == '600233.SH' and inp['currency'] == 'CNY', 'case identity')
    require(inp['limitations']['investment_authority'] == 'NONE', 'investment authority must remain NONE')
    monthly, share, quoted = inp['monthly_reported'], inp['share_context'], inp['price_context']
    require(monthly['unit_cost'] is None and monthly['unit_attributable_profit'] is None,
            'new actual cost or profit needs a separate research reconciliation')
    with localcontext() as context:
        context.prec = 50
        def fmt(x: Decimal) -> str:
            return format(x.quantize(Decimal('.000000000001')), 'f')
        r = number(monthly['unit_revenue_cny']); g = number(monthly['unit_revenue_yoy'])
        v = number(monthly['volume_yoy']); volume = number(monthly['volume_parcels'])
        require(r > 0 and -1 < g < 0 and v > 0 and volume > 0, 'positive prices/volume and negative unit growth expected')
        q = monthly['rounding_sensitivity']
        half_r = number(q['unit_price_half_width']); half_g = number(q['fraction_yoy_half_width'])
        require(0 < half_r < r and 0 < half_g < min(-g, 1 + g), 'rounding envelope invalid')
        drag = r / (1 + g) - r
        lo = (r - half_r) / (1 + g + half_g) - (r - half_r)
        hi = (r + half_r) / (1 + g - half_g) - (r + half_r)
        # gross profit = unit revenue - comparable unit product cost.
        # This is a necessary offset, not measured cost or actual net profit.
        monthly_out = {'conditional_unit_cost_saving_for_flat_unit_gross_profit_cny': fmt(drag),
                       'assumed_rounding_envelope_cny': [fmt(lo), fmt(hi)],
                       'envelope_is_confidence_interval': False,
                       'revenue_difference_at_current_volume_cny_not_actual_profit_loss': fmt(drag * volume),
                       'same_scope_unit_profit_decline_at_flat_total_profit': fmt(v / (1 + v)),
                       'actual_august_unit_cost': None, 'actual_august_unit_profit': None}
        n = number(share['declared_total_shares']); treasury = number(share['repurchase_account_shares'])
        entitled = number(share['dividend_entitled_shares']); dividend = number(share['dividend_per_entitled_share'])
        require(n > treasury >= 0 and entitled > 0 and all(x == x.to_integral_value() for x in (n, treasury, entitled)),
                'invalid share counts')
        require(n - treasury == entitled, 'dividend share basis differs')
        require(entitled * dividend == number(share['announced_dividend_total_cny']), 'declared dividend amount differs')
        p = number(quoted['price_cny']); require(p > 0, 'positive reference price required')
        estimates = inp['inherited']['earnings_2027']
        require(estimates['period'] == inp['price_only_sensitivity']['future_forward_earnings_period'] == 'FY2027',
                'do not mix forward earnings periods')
        grid = []
        for label in ('low', 'sample_mean', 'high'):
            earnings = number(estimates[label]); require(earnings > 0, 'positive conditional profit required')
            for shock in inp['price_only_sensitivity']['hypothetical_price_changes']:
                a = number(shock); require(a > -1, 'invalid price change')
                multiple = p * (1 + a) * n / earnings
                grid.append({'retained_estimate_label': label, 'conditional_FY2027_profit_cny': str(earnings),
                             'hypothetical_price_change': shock, 'required_forward_multiple': fmt(multiple)})
        stress = inp['price_only_sensitivity']['synthetic_joint_stress']
        e, m, dilution = (number(stress[k]) for k in
                         ('earnings_fraction_change', 'multiple_fraction_change', 'shares_fraction_change'))
        require(min(e, m, dilution) > -1, 'joint sensitivity has invalid denominator')
        joint = (1 + e) * (1 + m) / (1 + dilution) - 1
        table = {}
        for item in quoted['selected_original_rows']:
            row = item['row']; require(row['ts_code'] == inp['symbol'], 'wrong security in selected rows')
            key = (item['api'], row['trade_date']); require(key not in table, 'duplicate endpoint')
            table[key] = row
        intervals = []
        end = quoted['date'].replace('-', '')
        for period, start, index in ((5, '20260922', 2), (20, '20260901', 3), (60, '20260707', 4)):
            needed = (('daily', start), ('adj_factor', start), ('daily', end), ('adj_factor', end))
            if any(key not in table for key in needed):
                require(quoted['saved_report_row'][index] is None, 'missing input but nonnull saved return')
                intervals.append({'period': period, 'start': start, 'end': end, 'change': None,
                                  'status': 'ENDPOINT_OR_FACTOR_MISSING_NOT_ZERO'})
                continue
            c0 = number(table['daily', start]['close']); c1 = number(table['daily', end]['close'])
            f0 = number(table['adj_factor', start]['adj_factor']); f1 = number(table['adj_factor', end]['adj_factor'])
            require(min(c0, c1, f0, f1) > 0, 'invalid price or factor')
            change = fmt(c1 * f1 / (c0 * f0) - 1)
            require(change == quoted['saved_report_row'][index], 'endpoint calculation differs from retained report')
            intervals.append({'period': period, 'start': start, 'end': end, 'change': change,
                              'status': 'RETAINED_PROVIDER_ENDPOINT_CONTEXT'})
        require(number(table['daily', end]['close']) == p, 'reference price differs from selected source')
        return {'kind': KIND, 'inputs_sha256': hashlib.sha256(raw).hexdigest(),
                'prepared_at': inp['prepared_at'], 'remote_publication': 'NOT_PERFORMED',
                'unit_economics': monthly_out,
                'static_equity_reference_cny_not_current_market_cap': fmt(p * n),
                'price_only_inverse_requirements': grid,
                'joint_stress_price_only_change': fmt(joint),
                'future_dividend_or_total_return': None,
                'historical_endpoint_context': intervals,
                'opportunity_probability': None, 'established_horizon_opportunity': None,
                'historical_pit_qualified_case_count': None, 'model_score': None,
                'new_human_acceptance': False, 'investment_authority': 'NONE'}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--source-zip', type=Path)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', type=Path)
    mode.add_argument('--output', type=Path)
    args = p.parse_args()
    require(args.inputs.is_file() and not args.inputs.is_symlink(), 'regular inputs required')
    raw = args.inputs.read_bytes(); result = encode(calculate(raw))
    if args.source_zip:
        print(json.dumps(verify_archive(load(raw), args.source_zip), sort_keys=True))
    if args.check:
        require(args.check.is_file() and not args.check.is_symlink(), 'regular result required')
        require(args.check.read_bytes() == result, 'retained calculation result differs')
        print('YTO_WORKPAPER_CALCULATIONS_MATCH_NOT_RESEARCH_ACCEPTANCE')
    else:
        with args.output.open('xb') as handle:
            handle.write(result)
        print('CREATED', args.output)


if __name__ == '__main__':
    main()
