import pytest

from decision_kernel.runtime import radar_feed_intake as intake
from decision_kernel.runtime.economic_source_capture import PublicResponse, _body_integrity, EconomicCaptureError
from test_radar_feed_intake import capture, offline, item, xml, advance, AT
from datetime import timedelta


def test_large_whole_feed_under_reviewed_capacity_is_retained_and_rebuilt(tmp_path):
    # Synthetic full 4,207,576-byte XML, matching only the observed byte-size.
    # Whitespace is not a claim that the actual publisher XML has this structure.
    raw = xml([item()])
    raw += b' ' * (4207576 - len(raw))
    def transport(key):
        return PublicResponse(intake.FEEDS[key], 200, {'content-type':'text/xml','content-length':str(len(raw))}, raw)
    root = tmp_path/'large'
    report,_ = capture(root,[],transport=transport)
    assert report['status']=='COMPLETE_FEED_INTAKE'
    assert len(report['requests'])==2
    assert (root/'nbs-interpretations.xml').read_bytes()==raw
    assert intake.verify_capture(root)['status']=='ORIGINAL_FEEDS_REGISTRY_AND_PAGE_REBUILT'
    assert intake.MAX_BODY==8*1024*1024
    # Existing HTML source contract is deliberately untouched.
    with pytest.raises(EconomicCaptureError): _body_integrity(raw,{})


@pytest.mark.parametrize('raw,length',[(b'', '0'),(b'<x/>', '6'),(b'x'*(8*1024*1024+1),None)])
def test_empty_mismatched_and_oversized_feed_bodies_still_fail(raw,length):
    with pytest.raises(intake.FeedResponseRejected):
        intake._feed_body_integrity(raw,{} if length is None else {'content-length':length})


def test_capacity_policy_changes_do_not_reinterpret_old_capture_identity():
    from decision_kernel.identity import canonical_hash
    old_policy=canonical_hash({'version':intake.VERSION,'feeds':intake.FEEDS,'feedparser':intake.FEEDPARSER_VERSION})
    assert old_policy!=intake.POLICY_HASH
    assert intake.MAX_ITEMS==512 and intake.MAX_SOURCES==32 and intake.MAX_TOTAL_CHARS==131072


def test_complete_500_item_baseline_never_becomes_500_new_source_rows():
    rows=[item(url=f'https://www.stats.gov.cn/sj/zxfb/202609/t20260904_{10000+i}.html',guid=str(i),
               published='2026-09-04 09:30:00') for i in range(500)]
    registry,delta=advance(rows)
    assert len(registry['versions'])==500 and delta['feed_occurrences']==1000
    assert intake.source_rows(registry,delta)['status']=='BASELINE_NOT_FORWARDED'
    assert all(v['payload']['published_raw']=='2026-09-04 09:30:00' for v in registry['versions'])
    successor,d2=advance(rows,registry,AT+timedelta(minutes=1))
    assert successor['versions']==registry['versions'] and d2['changes']==[]
    assert intake.publication_clock('2026-09-04 09:30:00') is None
    assert intake.source_rows(successor,d2)['sources']==[]


def test_above_512_items_refuses_instead_of_chopping_the_window():
    rows=[item(url=f'https://www.stats.gov.cn/sj/zxfb/202609/t20260904_{10000+i}.html',guid=str(i)) for i in range(513)]
    with pytest.raises(ValueError,match='item budget exceeded'):
        intake.parse_window(xml(rows),'nbs-releases')
