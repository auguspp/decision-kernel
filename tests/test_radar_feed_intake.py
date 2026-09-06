from __future__ import annotations

import copy
import io
import json
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import radar_feed_intake as intake
from decision_kernel.runtime import theme_source_discovery as discovery
from decision_kernel.runtime.economic_source_capture import PublicResponse
from test_sector_radar_audit import prohibit_network
from test_theme_radar_probe import fixture, PLANNED, THEMES

UTC = timezone.utc
AT = datetime(2026, 9, 4, 8, 59, tzinfo=UTC)
URL = 'https://www.stats.gov.cn/sj/zxfb/202609/t20260904_1234567.html'
OTHER = 'https://www.stats.gov.cn/sj/zxfb/202609/t20260904_1234568.html'


def item(summary='A retained native feed description.', url=URL, guid='entry-1', published='Fri, 04 Sep 2026 08:00:00 GMT'):
    return {'title':'Synthetic source title', 'description':summary, 'link':url, 'guid':guid, 'pubDate':published}


def xml(rows):
    text = '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>NBS synthetic test</title><link>https://www.stats.gov.cn/</link><description>test</description>'
    for row in rows:
        text += '<item>' + ''.join(f'<{k}>{escape(v)}</{k}>' for k,v in row.items()) + '</item>'
    return (text+'</channel></rss>').encode()


def windows(rows, at=AT, other=None):
    return {key:{'raw':xml(rows if other is None or i==0 else other),
                 'requested_at':(at+timedelta(seconds=i*2)).isoformat(),
                 'received_at':(at+timedelta(seconds=i*2+1)).isoformat()}
            for i,key in enumerate(sorted(intake.FEEDS))}


def advance(rows, previous=None, at=AT, other=None):
    return intake.advance(windows(rows,at,other),recorded_at=(at+timedelta(seconds=5)).isoformat(),previous=previous,bootstrap=previous is None)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(intake.feedparser.http, 'get', lambda *a,**k:pytest.fail('feedparser must never fetch a URL'))


def test_baseline_and_unchanged_rerun_do_not_manufacture_new_publications():
    state,delta=advance([item(),item()])
    assert delta['status']=='INITIAL_BASELINE_ONLY'
    assert delta['feed_occurrences']==4 and delta['current_unique_versions']==1 and delta['duplicate_occurrences']==3
    assert intake.source_rows(state,delta)['status']=='BASELINE_NOT_FORWARDED'
    before=canonical_json(state)
    next_state,next_delta=advance([item()],state,AT+timedelta(minutes=1))
    assert next_delta['status']=='NO_NEW_FEED_VERSIONS' and next_delta['changes']==[]
    assert next_state['versions']==state['versions'] and canonical_json(state)==before
    assert next_state['parent_registry_hash']==state['registry_hash']
    assert len(state['versions'][0]['appearances'])==2
    assert intake.source_rows(next_state,next_delta)['sources']==[]


def test_older_published_late_arrival_is_kept_and_disappeared_entries_are_not_deleted():
    initial,_=advance([item()])
    newer,delta=advance([item(url=OTHER,guid='later',published='Thu, 03 Sep 2026 08:00:00 GMT')],initial,AT+timedelta(minutes=1))
    assert delta['changes'][0]['kind']=='FIRST_SEEN_LINK'
    assert len(newer['versions'])==2 and initial['versions'][0] in newer['versions']
    export=intake.source_rows(newer,delta)
    assert export['status']=='READY_RETAINED_DESCRIPTIONS' and len(export['sources'])==1
    ev=export['sources'][0]['evidence']
    assert datetime.fromisoformat(ev['published_at']).date().isoformat()=='2026-09-03'
    assert datetime.fromisoformat(ev['retrieved_at'])>AT
    assert ev['available_at']==ev['retrieved_at'] and ev['replayability_level']=='PARTIAL'
    assert delta['independent_source_count'] is None and not delta['article_revision_verified']


def test_same_link_changed_description_is_a_new_representation_not_overwritten_truth():
    initial,_=advance([item('Earlier description')])
    state,delta=advance([item('Corrected or alternate feed description')],initial,AT+timedelta(minutes=1))
    assert len(state['versions'])==2 and initial['versions'][0] in state['versions']
    assert delta['changes'][0]['kind']=='CHANGED_FEED_REPRESENTATION'
    assert len(intake.source_rows(state,delta)['sources'])==1


def test_different_guids_same_link_and_text_do_not_create_another_version():
    initial,_=advance([item()])
    state,delta=advance([item(guid='new-provider-guid')],initial,AT+timedelta(minutes=1))
    assert delta['changes']==[] and len(state['versions'])==1
    assert len(state['versions'][0]['appearances'])==4


def test_same_titles_different_links_are_not_automatically_independent_or_merged():
    state,delta=advance([item(),item(url=OTHER,guid='other')])
    assert len(state['versions'])==2 and delta['independent_source_count'] is None


def test_conflicting_current_descriptions_preserve_both_and_block_all_export():
    initial,_=advance([])
    state,delta=advance([item('first statement')],initial,AT+timedelta(minutes=1),other=[item('contradictory statement')])
    assert len(state['versions'])==2 and URL in delta['multiple_current_representations']
    export=intake.source_rows(state,delta)
    assert export['status']=='SOURCE_EXPORT_BLOCKED' and export['sources']==[]
    assert export['gaps'][0]['reason']=='MULTIPLE_CURRENT_REPRESENTATIONS_REQUIRE_REVIEW'


@pytest.mark.parametrize('published', ['2026-09-04','2026-09-04T08:00:00','Fri, 31 Jun 2026 08:00:00 GMT',
    'Fri, 04 Sep 2026 08:00:00 CST','2026-09-04T08:00:00.123456789Z','2026-09-07T08:00:00Z',''])
def test_unknown_ambiguous_and_future_dates_never_become_fabricated_publication_instants(published):
    initial,_=advance([])
    state,delta=advance([item(published=published)],initial,AT+timedelta(minutes=1))
    assert state['versions'][0]['payload']['published_raw']==published
    export=intake.source_rows(state,delta)
    assert export['status']=='SOURCE_EXPORT_BLOCKED' and not export['sources']


def test_offset_dates_preserve_the_instant():
    assert intake.publication_clock('2026-09-04T16:00:00+08:00')==intake.publication_clock('Fri, 04 Sep 2026 08:00:00 GMT')
    assert intake.publication_clock('Thu, 04 Sep 2026 08:00:00 GMT') is None


def test_empty_summary_is_metadata_not_a_source_text_success():
    initial,_=advance([])
    state,delta=advance([item('')],initial,AT+timedelta(minutes=1))
    assert intake.source_rows(state,delta)['status']=='SOURCE_EXPORT_BLOCKED'


def test_new_descriptions_feed_the_existing_source_discovery_without_new_market_math():
    state,captures=fixture()
    initial,_=advance([])
    registry,delta=advance([item('We deny '+THEMES[0]['name']+' exposure. Not a recommendation.')],initial,AT+timedelta(minutes=1))
    exported=intake.source_rows(registry,delta)
    assert exported['status']=='READY_RETAINED_DESCRIPTIONS'
    result=discovery.discover_theme_sources(state,{'schema_version':1,'provenance':'SYNTHETIC_TEST_ONLY',
        'source_scope':'Synthetic newly observed RSS descriptions, not full articles.',
        'concept_catalog':captures['concept_catalog'],'industry_catalog':captures['industry_catalog'],
        'industries':[],'sources':exported['sources']},as_of=PLANNED.isoformat(),generated_at=PLANNED.isoformat())
    assert result['status']=='SOURCE_LEADS_PLANNED' and result['requests_executed']==0
    assert result['acquisition_plan']['themes'][0]['thscode']==THEMES[0]['thscode']
    assert 'deny' in result['projection']['leads'][0]['mentions'][0]['context']
    assert result['projection']['investment_authority']=='NONE'


@pytest.mark.parametrize('body',[b'<html>Blocked</html>',b'<rss version="2.0"><channel>',
    b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss version="2.0"><channel/></rss>'])
def test_malformed_or_entity_documents_fail_without_loose_recovery(body):
    with pytest.raises(ValueError): intake.parse_window(body,'nbs-releases')


@pytest.mark.parametrize('url',['file:///tmp/article','https://evil.test/article',URL+'?tracked=1',URL+'#x','../article.html'])
def test_link_identity_is_not_inferred_or_normalized(url):
    with pytest.raises(ValueError): intake.parse_window(xml([item(url=url)]),'nbs-releases')


def test_missing_feed_or_implicit_reset_is_rejected():
    with pytest.raises(ValueError): intake.advance({},recorded_at=AT.isoformat(),bootstrap=True)
    with pytest.raises(ValueError): intake.advance(windows([]),recorded_at=(AT+timedelta(seconds=5)).isoformat())
    initial,_=advance([])
    with pytest.raises(ValueError): intake.advance(windows([]),recorded_at=AT.isoformat(),previous=initial,bootstrap=True)


def test_id_rebound_and_parser_version_migration_fail_closed(monkeypatch):
    initial,_=advance([item()])
    with pytest.raises(ValueError,match='identifier rebound'):
        advance([item(url=OTHER)],initial,AT+timedelta(minutes=1))
    monkeypatch.setattr(intake,'version',lambda _: 'unreviewed-version')
    with pytest.raises(ValueError,match='parser version'): advance([])


def test_no_silent_budget_truncation(monkeypatch):
    monkeypatch.setattr(intake,'MAX_ITEMS',1)
    with pytest.raises(ValueError,match='item budget'): advance([item(),item()])
    monkeypatch.setattr(intake,'MAX_ITEMS',128)
    initial,_=advance([])
    monkeypatch.setattr(intake,'MAX_VERSIONS',1)
    with pytest.raises(ValueError,match='registry full'): advance([item(),item(url=OTHER,guid='two')],initial,AT+timedelta(minutes=1))


def capture(root, rows, at=AT, previous=None, transport=None):
    clock=iter(at+timedelta(seconds=i) for i in range(30))
    calls=[]
    def get(key):
        calls.append(key); raw=xml(rows)
        return PublicResponse(intake.FEEDS[key],200,{'content-type':'text/xml; charset=utf-8','content-length':str(len(raw))},raw)
    report=intake.capture(root,previous=previous,bootstrap=previous is None,transport=transport or get,now=lambda:next(clock))
    return report,calls


def test_capture_and_exact_offline_rebuild_then_source_successor(tmp_path):
    first=tmp_path/'first'; second=tmp_path/'second'
    a,calls=capture(first,[item()])
    assert a['status']=='COMPLETE_FEED_INTAKE' and calls==sorted(intake.FEEDS)
    assert intake.verify_capture(first)['status']=='ORIGINAL_FEEDS_REGISTRY_AND_PAGE_REBUILT'
    b,_=capture(second,[item(),item(url=OTHER,guid='second')],AT+timedelta(minutes=1),first)
    assert b['status']=='COMPLETE_FEED_INTAKE'
    assert intake.verify_capture(second)['status']=='ORIGINAL_FEEDS_REGISTRY_AND_PAGE_REBUILT'
    assert b['previous_capture_hash']==a['capture_hash']
    assert len(json.loads((second/'source-rows.json').read_text())['sources'])==1
    soup=BeautifulSoup((second/'index.html').read_text(),'html.parser')
    assert not soup.find('script') and len(soup.select('section'))==2
    assert '第一次看到不等于刚刚发布' in soup.get_text()


def test_failed_second_request_preserves_first_raw_and_never_publishes_registry(tmp_path):
    calls=[]
    def get(key):
        calls.append(key)
        if len(calls)==2: raise HTTPError(intake.FEEDS[key],403,'blocked secret-like text',{},io.BytesIO(b'not read'))
        return PublicResponse(intake.FEEDS[key],200,{'content-type':'text/xml'},xml([item()]))
    root=tmp_path/'failed'; report,_=capture(root,[],transport=get)
    assert report['status']=='INCOMPLETE_FEED_INTAKE' and len(calls)==2
    assert report['requests'][1]['status']==403
    assert not (root/'registry.json').exists() and not (root/'index.html').exists()
    assert 'blocked secret-like text' not in (root/'capture.json').read_text()
    assert intake.verify_capture(root)['status']=='RETAINED_BYTES_ONLY_INCOMPLETE_INTAKE'
    with pytest.raises(ValueError): capture(tmp_path/'bad-successor',[],AT+timedelta(minutes=1),root)


@pytest.mark.parametrize('target',['nbs-releases.xml','registry.json','index.html','extra.txt'])
def test_tampering_or_extra_files_rejected(tmp_path,target):
    root=tmp_path/'capture'; capture(root,[item()])
    path=root/target; path.write_bytes((path.read_bytes() if path.exists() else b'')+b'\n')
    with pytest.raises(ValueError): intake.verify_capture(root)


def test_rehashed_page_does_not_replace_raw_rebuild(tmp_path):
    root=tmp_path/'capture'; capture(root,[item()])
    page=root/'index.html'; page.write_text('pretend success')
    receipt=json.loads((root/'capture.json').read_text()); receipt['files']['index.html']=intake.digest(page.read_bytes())
    receipt=intake._sealed({k:v for k,v in receipt.items() if k!='capture_hash'},'capture_hash')
    (root/'capture.json').write_bytes(intake.data(receipt))
    with pytest.raises(ValueError,match='reconstruction differs'): intake.verify_capture(root)


def test_registry_tamper_and_previous_clock_reversal_fail():
    initial,_=advance([item()])
    changed=copy.deepcopy(initial); changed['versions'][0]['payload']['summary']='modified'
    changed=intake._sealed({k:v for k,v in changed.items() if k!='registry_hash'},'registry_hash')
    with pytest.raises(ValueError): intake.validate_registry(changed)
    with pytest.raises(ValueError,match='previous registry must precede'): advance([],initial,AT)


def test_cli_existing_directory_and_no_implicit_bootstrap(tmp_path,monkeypatch,capsys):
    for key in ('GITHUB_REPOSITORY','GITHUB_WORKFLOW','GITHUB_REF','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA'):
        monkeypatch.delenv(key,raising=False)
    monkeypatch.setattr(intake,'fetch_feed',lambda key:PublicResponse(intake.FEEDS[key],200,{'content-type':'text/xml'},xml([item()])))
    root=tmp_path/'capture'
    assert intake.main(['capture','--output',str(root)])==2 and not root.exists()
    assert intake.main(['capture','--output',str(root),'--bootstrap'])==0
    assert intake.main(['verify','--output',str(root)])==0
    original=(root/'capture.json').read_bytes()
    assert intake.main(['capture','--output',str(root),'--bootstrap'])==2
    assert (root/'capture.json').read_bytes()==original


def test_unusable_new_item_blocks_other_source_exports():
    initial,_=advance([])
    registry,delta=advance([item(),item(url=OTHER,guid='unknown',published='2026-09-04')],initial,AT+timedelta(minutes=1))
    export=intake.source_rows(registry,delta)
    assert export['status']=='SOURCE_EXPORT_BLOCKED' and export['sources']==[]


def test_large_source_delta_preserved_without_silent_top_n():
    initial,_=advance([])
    rows=[item(url=f'https://www.stats.gov.cn/sj/zxfb/202609/t20260904_{1000+i}.html',guid=str(i)) for i in range(33)]
    registry,delta=advance(rows,initial,AT+timedelta(minutes=1))
    assert len(delta['changes'])==33
    export=intake.source_rows(registry,delta)
    assert export['sources']==[] and any(g['reason']=='DOWNSTREAM_SOURCE_BUDGET_EXCEEDED' for g in export['gaps'])
