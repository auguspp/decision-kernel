"""Actual optional CNEquity API integration. CI installs its pinned distribution."""
from datetime import date,datetime,timezone
from pathlib import Path
from copy import deepcopy
import json
import tomllib

import polars as pl
import pytest

from decision_kernel.runtime import cnequity_bridge as bridge

DAY=date(2026,9,21)


def bars():
    return [{'symbol':'603507.SH','trade_date':DAY,'open':24.22,'high':26.5,'low':24.22,'close':26.48,
             'volume':21725345,'amount':562388550.0,'source':'hithink_retained','data_version':'v2',
             'fetched_at':datetime(2026,9,21,9,tzinfo=timezone.utc),'volume_unit':'SHARES','currency':'CNY',
             'adjustment':'NONE','original_sha256':'a'*64}]


def test_native_writer_compactor_and_reader_roundtrip(tmp_path):
    root=tmp_path/'lake'
    receipt=bridge.retain_bars(rows=bars(),output=root)
    result=bridge.read_lake(data_root=root,dataset='daily_bars',start=DAY,end=DAY,
                            symbols=['603507.SH'],output=tmp_path/'reading')
    assert result['status']=='CONTEXT_READY'
    assert result['rows'][0]['close']==26.48 and result['rows'][0]['volume']==21725345
    assert result['rows'][0]['source']=='hithink_retained'
    assert not receipt['independent_provider_verification'] and result['network_calls']==0
    assert (root/'original-bars.json').is_file()
    with pytest.raises(ValueError,match='LAKE_EXISTS'):bridge.retain_bars(rows=bars(),output=root)


def test_native_missing_adjustment_fails_instead_of_factor_one(tmp_path):
    root=tmp_path/'lake';bridge.retain_bars(rows=bars(),output=root)
    with pytest.raises(ValueError):
        bridge.read_lake(data_root=root,dataset='daily_bars',start=DAY,end=DAY,adjust='hfq',
                        symbols=['603507.SH'],output=tmp_path/'adjusted')
    assert not (tmp_path/'adjusted').exists()


def test_native_adjustment_used_not_reimplemented(tmp_path):
    root=tmp_path/'lake';bridge.retain_bars(rows=bars(),output=root)
    factors=root/'derived'/'adj_factors';factors.mkdir(parents=True)
    pl.DataFrame({'symbol':['603507.SH'],'trade_date':[DAY],'adjust_type':['hfq'],'factor':[2.0],
        'source':['synthetic_factor'],'data_version':['v1'],
        'fetched_at':[datetime(2026,9,21,9,tzinfo=timezone.utc)]}).write_parquet(factors/'part-0.parquet')
    result=bridge.read_lake(data_root=root,dataset='daily_bars',start=DAY,end=DAY,adjust='hfq',
                           symbols=['603507.SH'],output=tmp_path/'adjusted')
    assert result['rows'][0]['adj_close']==52.96 and result['rows'][0]['adj_is_exact']


def test_native_strict_pit_excludes_later_reconstructed_fact(tmp_path):
    root=tmp_path/'lake';dataset=root/'curated'/'financial_statement_items';dataset.mkdir(parents=True)
    pl.DataFrame({'symbol':['603507.SH'],'report_period':['2026Q2'],'statement_type':['income'],
        'item_code':['revenue'],'item_value':[1.0],'announce_date':[date(2026,8,26)],
        'source':['retrospective_import'],'data_version':['v1'],
        'fetched_at':[datetime(2026,9,22,tzinfo=timezone.utc)]}).write_parquet(dataset/'part-0.parquet')
    result=bridge.read_lake(data_root=root,dataset='financial_statement_items',start=date(2026,1,1),end=DAY,
                           as_of=DAY,symbols=['603507.SH'],output=tmp_path/'reading')
    assert result['status']=='NO_ROWS_FOR_STRICT_SCOPE' and result['rows']==[]


@pytest.mark.parametrize('field,value',[('volume_unit','LOTS'),('currency','UNKNOWN'),('adjustment','QFQ'),
                                         ('data_version','v1'),('original_sha256','missing')])
def test_no_unverified_units_or_lineage_enter_lake(tmp_path,field,value):
    rows=bars();rows[0][field]=value
    with pytest.raises(ValueError,match='BAR_LINEAGE_OR_UNITS_INVALID'):bridge.retain_bars(rows=rows,output=tmp_path/'lake')
    assert not (tmp_path/'lake').exists()


def test_symlink_and_shared_revision_fail_closed(tmp_path):
    root=tmp_path/'lake';bridge.retain_bars(rows=bars(),output=root)
    link=tmp_path/'link';link.symlink_to(root,target_is_directory=True)
    with pytest.raises(ValueError,match='LAKE_SYMLINK_REJECTED'):
        bridge.read_lake(data_root=link,dataset='daily_bars',start=DAY,end=DAY,symbols=['603507.SH'],output=tmp_path/'x')
    with pytest.raises(ValueError,match='INDEPENDENT_FACTOR_REVISION_REQUIRED'):
        bridge.read_lake(data_root=root,dataset='daily_bars',start=DAY,end=DAY,symbols=['603507.SH'],output=tmp_path/'x',
                         adjust='hfq',revision_map={'daily_bars':1})


def test_core_does_not_depend_on_lake_stack():
    config=tomllib.loads((Path(__file__).parents[1]/'pyproject.toml').read_text())['project']
    assert config['dependencies']==['pydantic==2.13.4']
    assert config['optional-dependencies']['cnequity']==['cnequity==0.11.0']
