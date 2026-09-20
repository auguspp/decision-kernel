"""Offline arithmetic on researcher-transcribed issuer tables and retained LC bytes.
Does not verify issuer PDFs, infer economic truth, or run any Research/market API.
Usage: python recalculate.py /path/to/industry-final-35486156318.zip
"""
from __future__ import annotations
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

D = Decimal
EXPECTED = '8aa291e84d4b9577c903e702c43c9c8263871bd9371e8ed641a1118d0b312502'

def calculate(path: Path) -> dict:
    archive = path.read_bytes()
    assert len(archive) == 127752 and hashlib.sha256(archive).hexdigest() == EXPECTED
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        receipts = json.loads(z.read('requests.json'))
        wanted = {'LC-prices', 'LC-warehouse'}
        bodies = {}
        for r in receipts:
            if r['label'] not in wanted:
                continue
            b = z.read(r['response_file'])
            assert len(b) == r['response_bytes']
            assert hashlib.sha256(b).hexdigest() == r['response_sha256']
            bodies[r['label']] = json.loads(b, parse_float=D)['data']['item']
    prices = bodies['LC-prices']
    assert all(prices[i]['timestamp'] < prices[i+1]['timestamp'] for i in range(len(prices)-1))
    assert all(1774972800000 <= p['timestamp'] <= 1789747199999 for p in prices)
    wh = sorted((r for r in bodies['LC-warehouse'] if '2026-08-01' <= r['date'] <= '2026-09-18'), key=lambda r:r['date'])
    assert len(prices)==118 and len(wh)==35 and len({r['date'] for r in wh})==35
    with localcontext() as ctx:
        ctx.prec = 40
        g_total=D('22797728')
        g_ext=[D('13547723'), D('8535987'), D('714018')]
        assert sum(g_ext)==g_total
        assert D('26691317')-D('3893589')==g_total
        assert D('2779812')-D('378784')+D('252085')-D('1464660')==D('1188453')
        e_revenue=D('61469630776.09')
        e_power=D('25858369302.45'); e_storage=D('24441028386.51')
        raw_cost_pct=D('42243291164.90')/D('51528491525.28')*100
        return {
            'meaning':'OFFLINE_ARITHMETIC_NOT_PDF_AUTHENTICATION_OR_ADMISSION',
            'input_archive_sha256':EXPECTED,
            'LC':{'price_count':len(prices), 'warehouse_count':len(wh),
                  'return_5_observations':str(D(prices[-1]['close_price'])/D(prices[-6]['close_price'])-1),
                  'return_20_observations':str(D(prices[-1]['close_price'])/D(prices[-21]['close_price'])-1),
                  'warehouse_delta_raw_unit':str(D(wh[-1]['amount'])-D(wh[0]['amount'])), 'warehouse_unit':'UNKNOWN'},
            'Ganfeng_2025_IFRS_note4':{'unit':'RMB_thousand',
                'external_revenue_percent':[str(x/g_total*100) for x in g_ext],
                'external_revenue_total':str(g_total), 'intersegment_elimination':'3893589',
                'reconciled_profit_before_tax':'1188453',
                'lithium_price_elasticity':'NOT_ESTABLISHED'},
            'EVE_2025_PRC_GAAP':{'unit':'RMB',
                'power_storage_revenue_percent':str((e_power+e_storage)/e_revenue*100),
                'all_raw_materials_cost_percent_reported':'81.99',
                'all_raw_materials_cost_percent_recalculated':str(raw_cost_pct),
                'display_percentage_difference_pp':str(D('81.99')-raw_cost_pct),
                'lithium_only_cost_share':'NOT_ESTABLISHED',
                'raw_material_cost_savings_retention':'NOT_ESTABLISHED'},
            'network_calls':0,'model_calls':0,'formal_Pre_calls':0,'investment_authority':'NONE'
        }

if __name__=='__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: python recalculate.py <retained-industry-zip>')
    print(json.dumps(calculate(Path(sys.argv[1])), ensure_ascii=False, indent=2))
