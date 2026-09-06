from __future__ import annotations

import copy
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import radar_feed_consumer as consumer
from decision_kernel.runtime import radar_feed_intake as feed
from decision_kernel.runtime import theme_radar_probe as probe
from test_radar_feed_intake import capture, item, AT, OTHER
from test_theme_radar_probe import fixture, PLANNED, THEMES
from test_sector_radar_audit import prohibit_network

AS_OF = PLANNED + timedelta(minutes=1)
LATER = PLANNED + timedelta(minutes=3)


def setup(tmp_path, rows=None):
    state, inputs = fixture()
    baseline, source, receipts = (tmp_path / n for n in ('baseline', 'feed', 'receipts'))
    receipts.mkdir()
    (receipts / '.gitkeep').write_bytes(b'')
    capture(baseline, [])
    capture(source, rows if rows is not None else [item('We deny '+THEMES[0]['name']+' exposure.')],
            AT+timedelta(minutes=1), baseline)
    context = {key: copy.deepcopy(inputs[key]) for key in ('concept_catalog', 'industry_catalog')}
    context['industries'] = []
    return state, source, receipts, context


def run(tmp_path, values, *, name='scan', at=AS_OF):
    state, source, receipts, context = values
    return consumer.scan(source, state, context, receipts, tmp_path/name,
                         as_of=at.isoformat(), generated_at=at.isoformat())


def register(tmp_path, name='scan'):
    shutil.copytree(tmp_path/name, tmp_path/'receipts'/name)


def contents(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(feed.feedparser.http, 'get', lambda *a,**k:pytest.fail('no parser fetch'))


def test_actual_existing_scanner_receipt_is_not_a_market_execution_ack(tmp_path):
    values=setup(tmp_path)
    before=contents(values[1])
    result=run(tmp_path,values)
    assert result['status']=='SOURCE_SCAN_COMPLETED'
    verified=consumer.verify_scan(tmp_path/'scan')
    receipt=verified['receipt']; report=verified['result']
    assert receipt['scan_status']=='SOURCE_LEADS_PLANNED'
    assert report['acquisition_plan']['themes'][0]['thscode']==THEMES[0]['thscode']
    assert 'deny' in report['projection']['leads'][0]['mentions'][0]['context']
    assert receipt['acquisition_status']=='PLAN_NOT_EXECUTED'
    assert receipt['source_delivery_acknowledged'] is False
    assert not receipt['human_review_recorded'] and not receipt['article_accepted']
    assert all(receipt[k]==v for k,v in probe.AUTHORITY.items())
    assert contents(values[1])==before
    assert json.loads((values[1]/'source-rows.json').read_text())['pending_versions']==1


def test_unchanged_scope_reuses_exact_scan_without_hiding_unexecuted_plan(tmp_path):
    values=setup(tmp_path); first=run(tmp_path,values); register(tmp_path)
    receipt=(tmp_path/'receipts/scan/scan-receipt.json').read_bytes()
    again=run(tmp_path,values,name='again',at=LATER)
    assert again['status']=='NO_PENDING_SOURCE_SCAN'
    assert again['new_scan_receipt'] is None and again['selected_source_records']==0
    assert again['already_scanned_source_records']==1
    assert again['upstream_pending_versions']==1
    assert len(again['unexecuted_prior_plans'])==1
    assert again['unexecuted_prior_plans'][0]['receipt_hash']==first['new_scan_receipt']
    assert (tmp_path/'receipts/scan/scan-receipt.json').read_bytes()==receipt
    assert not (tmp_path/'again/scan-receipt.json').exists()


def test_new_version_alone_is_scanned_and_old_first_clocks_are_preserved(tmp_path):
    values=setup(tmp_path); run(tmp_path,values); register(tmp_path)
    state,source,receipts,context=values
    later=tmp_path/'later-feed'
    capture(later,[item('We deny '+THEMES[0]['name']+' exposure.'),item('No literal theme here.',url=OTHER,guid='new')],
            AT+timedelta(minutes=5),source)
    result=run(tmp_path,(state,later,receipts,context),name='later',at=LATER)
    receipt=consumer.verify_scan(tmp_path/'later')['receipt']
    assert result['upstream_pending_versions']==2 and result['selected_source_records']==1
    assert result['already_scanned_source_records']==1 and len(result['unexecuted_prior_plans'])==1
    assert receipt['scan_status']=='NO_LITERAL_CATALOG_MENTIONS'
    assert receipt['acquisition_status']=='NO_PLAN_FROM_THIS_SCAN'
    original=json.loads((source/'registry.json').read_text())['versions'][0]
    assert original in json.loads((later/'registry.json').read_text())['versions']


def test_same_url_changed_description_needs_new_scan(tmp_path):
    values=setup(tmp_path); run(tmp_path,values); register(tmp_path)
    state,source,receipts,context=values; later=tmp_path/'changed-feed'
    capture(later,[item('Changed '+THEMES[1]['name']+' statement')],AT+timedelta(minutes=5),source)
    result=run(tmp_path,(state,later,receipts,context),name='changed',at=LATER)
    assert result['selected_source_records']==1 and result['already_scanned_source_records']==1
    assert consumer.verify_scan(tmp_path/'changed')['result']['acquisition_plan']['themes'][0]['thscode']==THEMES[1]['thscode']


def test_duplicate_receipt_copies_do_not_increase_processed_sources(tmp_path):
    values=setup(tmp_path); run(tmp_path,values); register(tmp_path)
    shutil.copytree(tmp_path/'scan',tmp_path/'receipts/second-copy')
    result=run(tmp_path,values,name='again',at=LATER)
    assert len(result['prior_scan_receipts'])==1
    assert result['already_scanned_source_records']==1
    assert len(result['unexecuted_prior_plans'])==1


def test_changed_catalog_does_not_inherit_old_scan_ack(tmp_path):
    values=setup(tmp_path); run(tmp_path,values); register(tmp_path)
    state,source,receipts,context=values
    context=copy.deepcopy(context)
    context['concept_catalog']['response']['data']['item'][0]['name']='Different complete label'
    result=run(tmp_path,(state,source,receipts,context),name='new-catalog',at=LATER)
    assert result['selected_source_records']==1 and result['already_scanned_source_records']==0
    assert result['prior_scan_receipts'][0]['scope_matches'] is False
    assert result['unexecuted_prior_plans'][0]['scope_matches'] is False
    assert consumer.verify_scan(tmp_path/'new-catalog')['receipt']['scan_status']=='NO_LITERAL_CATALOG_MENTIONS'


def test_initial_baseline_is_never_scanned_or_acknowledged(tmp_path):
    state,source,receipts,context=setup(tmp_path)
    baseline=tmp_path/'real-baseline'; capture(baseline,[item(THEMES[0]['name'])])
    result=run(tmp_path,(state,baseline,receipts,context))
    assert result['status']=='BASELINE_NOT_FORWARDED'
    assert result['new_scan_receipt'] is None
    assert not (tmp_path/'scan/scan-receipt.json').exists()


@pytest.mark.parametrize('published',['2026-09-04 09:30:00','2026-09-04','2026-09-09T09:30:00Z',''])
def test_unqualified_source_time_stays_blocked_without_receipt(tmp_path,published):
    values=setup(tmp_path,[item(THEMES[0]['name'],published=published)])
    result=run(tmp_path,values)
    assert result['status']=='SOURCE_EXPORT_BLOCKED' and result['gaps']
    assert result['new_scan_receipt'] is None
    assert not (tmp_path/'scan/source-discovery.json').exists()
    with pytest.raises(ValueError): consumer.verify_scan(tmp_path/'scan')


def test_one_bad_new_record_blocks_the_whole_export_after_prior_ack(tmp_path):
    values=setup(tmp_path); run(tmp_path,values); register(tmp_path)
    state,source,receipts,context=values; later=tmp_path/'bad-feed'
    capture(later,[item('We deny '+THEMES[0]['name']+' exposure.'),item('new',url=OTHER,guid='new',published='2026-09-04')],
            AT+timedelta(minutes=5),source)
    result=run(tmp_path,(state,later,receipts,context),name='blocked',at=LATER)
    assert result['status']=='SOURCE_EXPORT_BLOCKED' and result['new_scan_receipt'] is None
    assert result['gaps'][0]['reason']=='PUBLISHED_TIME_NOT_QUALIFIED'
    assert len(result['unexecuted_prior_plans'])==1


def test_existing_full_export_capacity_is_not_silently_relaxed_by_acks(tmp_path):
    rows=[item('No theme',url=f'https://www.stats.gov.cn/sj/zxfb/202609/t20260904_{1000+i}.html',guid=str(i)) for i in range(33)]
    values=setup(tmp_path,rows)
    result=run(tmp_path,values)
    assert result['status']=='SOURCE_EXPORT_BLOCKED'
    assert any(g['reason']=='DOWNSTREAM_SOURCE_BUDGET_EXCEEDED' for g in result['gaps'])
    assert result['new_scan_receipt'] is None


def test_ambiguous_catalog_labels_do_not_receive_completion_receipt(tmp_path):
    values=setup(tmp_path); state,source,receipts,context=values
    rows=context['concept_catalog']['response']['data']['item']
    rows.append({'thscode':'886003.TI','name':THEMES[0]['name']})
    result=run(tmp_path,values)
    assert result['status']=='SOURCE_SCAN_BLOCKED'
    assert 'AMBIGUOUS_CATALOG_LABEL' in json.loads((tmp_path/'scan/source-discovery.json').read_text())['acquisition_blockers']
    assert not (tmp_path/'scan/scan-receipt.json').exists()


@pytest.mark.parametrize('target',['index.html','source-discovery.json','scan-receipt.json','selection.json','context.json','market-state.json','feed-capture/nbs-releases.xml'])
def test_modified_receipt_bundle_rejected(tmp_path,target):
    values=setup(tmp_path); run(tmp_path,values)
    path=tmp_path/'scan'/target; path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError): consumer.verify_scan(tmp_path/'scan')


def test_rehashing_a_fake_completion_does_not_bypass_original_scan(tmp_path):
    values=setup(tmp_path); run(tmp_path,values)
    root=tmp_path/'scan'; receipt=json.loads((root/'scan-receipt.json').read_text())
    receipt['acquisition_status']='EXECUTED'
    receipt=feed._sealed({k:v for k,v in receipt.items() if k!='receipt_hash'},'receipt_hash')
    (root/'scan-receipt.json').write_bytes(feed.data(receipt))
    inventory=consumer._inventory(root); inventory.pop('files.json')
    (root/'files.json').write_bytes(feed.data(inventory))
    with pytest.raises(ValueError,match='does not rebuild'): consumer.verify_scan(root)


def test_future_receipt_not_used_to_remove_earlier_pending_source(tmp_path):
    values=setup(tmp_path); run(tmp_path,values,at=LATER); register(tmp_path)
    with pytest.raises(ValueError,match='later than'): run(tmp_path,values,name='past',at=AS_OF)
    assert not (tmp_path/'past').exists()


def test_loose_hash_receipt_is_not_a_completed_execution_proof(tmp_path):
    values=setup(tmp_path)
    (values[2]/'fake.json').write_text('{}')
    with pytest.raises(ValueError,match='complete scan bundles'): run(tmp_path,values)


def test_missing_receipt_store_is_not_empty_store(tmp_path):
    values=setup(tmp_path); shutil.rmtree(values[2])
    with pytest.raises(ValueError,match='directory missing'): run(tmp_path,values)


def test_receipt_from_another_initialization_is_not_applied(tmp_path):
    values=setup(tmp_path); run(tmp_path,values); register(tmp_path)
    state,source,receipts,context=values
    alternative=tmp_path/'alternative-baseline'; capture(alternative,[],AT+timedelta(seconds=10))
    other=tmp_path/'alternative-child'; capture(other,[item('We deny '+THEMES[0]['name']+' exposure.')],AT+timedelta(minutes=1),alternative)
    with pytest.raises(ValueError,match='another source'): run(tmp_path,(state,other,receipts,context),name='other')


def test_exact_scanner_inputs_can_rebuild_after_original_inputs_are_removed(tmp_path):
    values=setup(tmp_path); run(tmp_path,values)
    shutil.rmtree(values[1]); shutil.rmtree(tmp_path/'baseline')
    assert consumer.verify_scan(tmp_path/'scan')['verification']=='ORIGINAL_FEED_AND_SOURCE_SCAN_REBUILT'


def test_existing_output_and_output_inside_store_are_not_overwritten(tmp_path):
    values=setup(tmp_path); run(tmp_path,values); before=contents(tmp_path/'scan')
    with pytest.raises(ValueError): run(tmp_path,values)
    state,source,receipts,context=values
    with pytest.raises(ValueError): consumer.scan(source,state,context,receipts,receipts/'nested',as_of=AS_OF.isoformat(),generated_at=AS_OF.isoformat())
    assert contents(tmp_path/'scan')==before


def test_atomic_write_failure_leaves_no_partial_completion(tmp_path,monkeypatch):
    values=setup(tmp_path); real=Path.write_bytes
    def fail(self,raw):
        if self.name=='scan-receipt.json': raise OSError('synthetic write failure')
        return real(self,raw)
    monkeypatch.setattr(Path,'write_bytes',fail)
    with pytest.raises(OSError): run(tmp_path,values)
    assert not (tmp_path/'scan').exists() and not list(tmp_path.glob('.feed-consumer-*'))


def test_symlink_registered_receipt_is_rejected(tmp_path):
    values=setup(tmp_path); run(tmp_path,values)
    (values[2]/'linked').symlink_to(tmp_path/'scan',target_is_directory=True)
    with pytest.raises(ValueError): run(tmp_path,values,name='again')


def test_full_cli_uses_saved_inputs_and_existing_verifier(tmp_path,monkeypatch):
    values=setup(tmp_path); state,source,receipts,context=values
    (tmp_path/'state.json').write_text(probe.serialize_sector_radar_market_state(state))
    (tmp_path/'context.json').write_bytes(feed.data(context))
    class Clock:
        @classmethod
        def now(cls,tz=None): return AS_OF
    monkeypatch.setattr(consumer,'datetime',Clock)
    args=['scan','--output',str(tmp_path/'scan'),'--feed-capture',str(source),
          '--market-state',str(tmp_path/'state.json'),'--context',str(tmp_path/'context.json'),
          '--receipts-dir',str(receipts),'--as-of',AS_OF.isoformat()]
    assert consumer.main(args)==0
    assert consumer.main(['verify','--output',str(tmp_path/'scan')])==0
    assert consumer.main(args)==2
    assert consumer.main(['scan','--output',str(tmp_path/'missing')])==2
