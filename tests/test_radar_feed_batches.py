from __future__ import annotations

import copy
import json
from datetime import timedelta

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import radar_feed_consumer as consumer
from decision_kernel.runtime import radar_feed_intake as feed
from test_radar_feed_consumer import setup, register, contents, AS_OF, LATER
from test_radar_feed_intake import item, capture, AT, OTHER
from test_theme_radar_probe import THEMES
from test_sector_radar_audit import prohibit_network


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(feed.feedparser.http, 'get', lambda *a, **k: pytest.fail('parser HTTP forbidden'))


def rows(count, text='No literal catalog label.'):
    return [item(text, url=f'https://www.stats.gov.cn/sj/zxfb/202609/t20260904_{10000+i}.html', guid=str(i)) for i in range(count)]


def batch(tmp_path, values, name='scan', size=32, at=AS_OF, **kwargs):
    state, source, receipts, context = values
    return consumer.scan(source, state, context, receipts, tmp_path/name, batch_size=size,
                         as_of=at.isoformat(), generated_at=at.isoformat(), **kwargs)


def test_33_sources_are_32_then_one_not_a_lifetime_stop_or_silent_truncation(tmp_path):
    values=setup(tmp_path, rows(33)); before=contents(values[1])
    first=batch(tmp_path, values)
    assert first['strict_whole_export_status']=='SOURCE_EXPORT_BLOCKED'
    assert first['status']=='SOURCE_SCAN_COMPLETED' and first['selected_source_records']==32
    manifest=first['batch']
    assert len(manifest['all_post_baseline_source_keys'])==33
    assert len(manifest['deferred_source_keys'])==1
    assert set(manifest['selected_source_keys']).isdisjoint(manifest['deferred_source_keys'])
    assert manifest['selection_precedes_theme_matching'] is True
    consumer.verify_scan(tmp_path/'scan'); register(tmp_path)
    second=batch(tmp_path, values, 'second', at=LATER)
    assert second['selected_source_records']==1 and second['already_scanned_source_records']==32
    assert second['batch']['selected_source_keys']==manifest['deferred_source_keys']
    assert not second['batch']['deferred_source_keys']
    assert second['upstream_pending_versions']==33
    register(tmp_path, 'second')
    third=batch(tmp_path, values, 'third', at=LATER+timedelta(minutes=1))
    assert third['status']=='NO_PENDING_SOURCE_SCAN' and third['new_scan_receipt'] is None
    assert third['already_scanned_source_records']==33 and third['source_delivery_acknowledged'] is False
    assert contents(values[1])==before
    # The old public export and historical raw-input replay are unchanged.
    assert feed.verify_capture(values[1])['capture_status']=='COMPLETE_FEED_INTAKE'
    assert json.loads((values[1]/'source-rows.json').read_text())['status']=='SOURCE_EXPORT_BLOCKED'


def test_fifo_tiebreaker_uses_first_received_and_exact_version_not_theme_popularity(tmp_path):
    values=setup(tmp_path, rows(4)); result=batch(tmp_path, values, size=2)
    registry=json.loads((values[1]/'registry.json').read_text())
    _, candidates, gaps=feed._source_candidates(registry, json.loads((values[1]/'delta.json').read_text()))
    assert not gaps
    ordered=sorted(candidates, key=lambda r:(feed._clock(r['evidence']['retrieved_at']),
                    feed._clock(r['recorded_at']), r['evidence']['content_hash']))
    assert result['batch']['selected_source_keys']==sorted(canonical_hash(r) for r in ordered[:2])
    assert result['batch']['deferred_source_keys']==[canonical_hash(r) for r in ordered[2:]]


def test_aggregate_text_budget_causes_explicit_deferral_not_text_trimming(tmp_path):
    values=setup(tmp_path, rows(14, 'x'*10000)); result=batch(tmp_path, values)
    assert result['selected_source_records']==13
    assert result['batch']['selected_text_characters']==130000
    assert len(result['batch']['deferred_source_keys'])==1
    proof=consumer.verify_scan(tmp_path/'scan')
    assert len(proof['result']['projection']['sources'])==13
    assert all(len(s['evidence']['permitted_excerpt'])==10000 for s in proof['result']['projection']['sources'])


def test_bad_time_even_outside_first_batch_blocks_all_without_dropping_it(tmp_path):
    source_rows=rows(33)
    source_rows[-1]['pubDate']='2026-09-04 09:30:00'
    values=setup(tmp_path, source_rows); result=batch(tmp_path, values, size=1)
    assert result['status']=='SOURCE_EXPORT_BLOCKED' and result['new_scan_receipt'] is None
    assert any(g['reason']=='PUBLISHED_TIME_NOT_QUALIFIED' for g in result['gaps'])
    assert not (tmp_path/'scan/scan-receipt.json').exists()


def test_more_than_three_themes_in_one_batch_is_not_retried_as_smaller_success(tmp_path):
    labels=[f'Synthetic theme {i}' for i in range(1,5)]
    values=setup(tmp_path,[item('We deny '+', '.join(labels))])
    data=values[3]['concept_catalog']['response']['data']['item']
    data.extend([{'thscode':f'88600{i}.TI','name':labels[i-1]} for i in (3,4)])
    result=batch(tmp_path,values)
    assert result['status']=='SOURCE_SCAN_BLOCKED' and result['new_scan_receipt'] is None
    report=json.loads((tmp_path/'scan/source-discovery.json').read_text())
    assert 'ACQUISITION_BUDGET_EXCEEDED' in report['acquisition_blockers']
    assert len(report['projection']['leads'])==4 and report['acquisition_plan'] is None


@pytest.mark.parametrize('size',[0,33,-1,True,1.5])
def test_invalid_batch_budget_refused_before_output(tmp_path,size):
    values=setup(tmp_path)
    with pytest.raises(ValueError): batch(tmp_path,values,size=size)
    assert not (tmp_path/'scan').exists()


def test_baseline_is_not_converted_to_a_batch(tmp_path):
    state,source,receipts,context=setup(tmp_path)
    baseline=tmp_path/'populated'; capture(baseline,rows(40))
    result=batch(tmp_path,(state,baseline,receipts,context))
    assert result['status']=='BASELINE_NOT_FORWARDED' and result['new_scan_receipt'] is None
    assert result['batch']['all_post_baseline_source_keys']==[]


def test_legacy_receipt_is_reused_but_its_unexecuted_plan_remains_visible(tmp_path):
    values=setup(tmp_path); state,source,receipts,context=values
    consumer.scan(source,state,context,receipts,tmp_path/'scan',as_of=AS_OF.isoformat(),generated_at=AS_OF.isoformat())
    old=consumer.verify_scan(tmp_path/'scan')['receipt']; register(tmp_path)
    later=tmp_path/'later-feed'
    capture(later,[item('We deny '+THEMES[0]['name']+' exposure.'),*rows(33)],AT+timedelta(minutes=5),source)
    result=batch(tmp_path,(state,later,receipts,context),'later',at=LATER)
    assert result['already_scanned_source_records']==1 and result['selected_source_records']==32
    assert len(result['batch']['deferred_source_keys'])==1
    assert result['unexecuted_prior_plans'][0]['receipt_hash']==old['receipt_hash']
    assert result['source_delivery_acknowledged'] is False


def test_rehashed_false_batch_partition_cannot_replace_original_selection(tmp_path):
    values=setup(tmp_path,rows(33)); batch(tmp_path,values)
    root=tmp_path/'scan'; selection=json.loads((root/'selection.json').read_text())
    selection['batch']['deferred_source_keys']=[]
    (root/'selection.json').write_bytes(feed.data(selection))
    inventory=consumer._inventory(root); inventory.pop('files.json')
    (root/'files.json').write_bytes(feed.data(inventory))
    with pytest.raises(ValueError, match='batch partition'): consumer.verify_scan(root)


def test_unknown_or_duplicate_explicit_export_selection_is_rejected(tmp_path):
    values=setup(tmp_path)
    registry=json.loads((values[1]/'registry.json').read_text()); delta=json.loads((values[1]/'delta.json').read_text())
    candidates=feed._source_candidates(registry,delta)[1]; key=canonical_hash(candidates[0])
    for keys in ([key,key], ['f'*64], 'not-a-list'):
        with pytest.raises(ValueError): feed.source_rows(registry,delta,selected_source_keys=keys)
    assert feed.source_rows(registry,delta,selected_source_keys=[key])['sources']==candidates


def test_batch_cli_uses_existing_entry_and_retains_remaining_work(tmp_path,monkeypatch):
    state,source,receipts,context=setup(tmp_path,rows(33))
    (tmp_path/'state.json').write_text(consumer.probe.serialize_sector_radar_market_state(state))
    (tmp_path/'context.json').write_bytes(feed.data(context))
    class Clock:
        @classmethod
        def now(cls,tz=None): return AS_OF
    monkeypatch.setattr(consumer,'datetime',Clock)
    args=['scan','--feed-capture',str(source),'--market-state',str(tmp_path/'state.json'),
          '--context',str(tmp_path/'context.json'),'--receipts-dir',str(receipts),
          '--output',str(tmp_path/'scan'),'--as-of',AS_OF.isoformat(),'--batch-size','32']
    assert consumer.main(args)==0
    assert consumer.main(['verify','--output',str(tmp_path/'scan')])==0
    assert len(json.loads((tmp_path/'scan/handoff.json').read_text())['batch']['deferred_source_keys'])==1
