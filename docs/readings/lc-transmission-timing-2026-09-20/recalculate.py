"""Offline date alignment and an explicitly synthetic margin identity example.
Not a source downloader, issuer forecast, Kernel validator or Research executor.
"""
from __future__ import annotations
import hashlib
import json
import sys
import zipfile
from datetime import date, datetime
from decimal import Decimal, localcontext
from pathlib import Path
from zoneinfo import ZoneInfo

ARCHIVE_HASH = '8aa291e84d4b9577c903e702c43c9c8263871bd9371e8ed641a1118d0b312502'

def calculate(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) != 127752 or hashlib.sha256(raw).hexdigest() != ARCHIVE_HASH:
        raise ValueError('Unexpected retained input archive')
    with zipfile.ZipFile(path) as archive:
        receipts = json.loads(archive.read('requests.json'))
        matches = [r for r in receipts if r['label'] == 'LC-prices']
        if len(matches) != 1:
            raise ValueError('LC source identity ambiguous')
        receipt = matches[0]
        body = archive.read(receipt['response_file'])
        if len(body) != receipt['response_bytes'] or hashlib.sha256(body).hexdigest() != receipt['response_sha256']:
            raise ValueError('Capture body differs')
        envelope = json.loads(body, parse_float=Decimal)
        data = envelope['data']
        points = data['item']
    if envelope['code'] != 0 or data['thscode'] != 'LCZL.GFE' or len(points) != 118:
        raise ValueError('Price series identity differs')
    if not all(points[i]['timestamp'] < points[i+1]['timestamp'] for i in range(len(points)-1)):
        raise ValueError('Price ordering differs')
    def point(p: dict) -> dict:
        return {'date': datetime.fromtimestamp(p['timestamp']/1000, ZoneInfo('Asia/Shanghai')).date().isoformat(),
                'raw_close_price': str(p['close_price'])}
    with localcontext() as context:
        context.prec = 40
        windows = []
        for count in (5, 20):
            start, end = point(points[-count-1]), point(points[-1])
            windows.append({'observation_intervals': count, 'start': start, 'end': end,
                            'return': str(Decimal(end['raw_close_price'])/Decimal(start['raw_close_price'])-1),
                            'starts_after_H1_period_end': date.fromisoformat(start['date']) > date(2026,6,30)})
        examples = []
        for recognized_fraction in (Decimal('.25'), Decimal('1')):
            # Synthetic normalized one-unit product, NOT either company's figures.
            gross = Decimal('20') + recognized_fraction*Decimal('4') - Decimal('2')
            examples.append({'fraction_of_purchase_saving_recognized_in_COGS': str(recognized_fraction),
                             'gross_profit_after': str(gross), 'gross_profit_change': str(gross-20)})
    return {'meaning': 'RETAINED_DATE_ALIGNMENT_AND_SYNTHETIC_IDENTITY_NOT_COMPANY_EFFECT_ESTIMATE',
            'input_archive_sha256': ARCHIVE_HASH,
            'h1_period_end': '2026-06-30', 'LC_windows': windows,
            'h1_can_measure_realized_effect_of_these_later_windows': False,
            'h1_required_as_pre_event_baseline': True,
            'synthetic_example': {'baseline_sales': '100', 'baseline_COGS': '80',
                                  'post_event_input_purchase_saving': '4', 'customer_price_cut': '2',
                                  'all_other_unit_COGS_change': '0', 'break_even_recognized_fraction': '0.5',
                                  'examples': examples, 'company_parameters_established': False},
            'network_calls': 0, 'model_calls': 0, 'formal_admission': False,
            'investment_authority': 'NONE'}

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python recalculate.py <exact-retained-industry.zip>')
    print(json.dumps(calculate(Path(sys.argv[1])), ensure_ascii=False, indent=2))
