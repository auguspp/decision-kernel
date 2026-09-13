"""A diagnostic pass still fails closed; no partial reading is valid."""
from io import BytesIO
import json

import pytest
from pypdf import PdfWriter
from decision_kernel.runtime import disclosure_source_reading as page
from decision_kernel.runtime import saved_research_once as once


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def denied(*a, **kw): raise AssertionError('unexpected network/model')
    import socket
    monkeypatch.setattr(socket.socket,'connect',denied)
    monkeypatch.setattr(once,'model_call',denied)


def example(count=3):
    w=PdfWriter()
    for _ in range(count):w.add_blank_page(width=100,height=100)
    b=BytesIO();w.write(b);pdf=b.getvalue()
    return pdf,{'pdf_sha256':once.sha(pdf),'text_sha256':'a'*64,
                'source_locator':'https://static.cninfo.com.cn/synthetic.PDF','page_count':count}


def test_missing_reviews_are_collected_without_partial_representation():
    pdf,e=example();d=[]
    with pytest.raises(once.TrialError,match='required page visual review unavailable'):
        page.represent(pdf,e,diagnostics=d,collect_missing=True)
    assert len(d)==1 and [p['page_number'] for p in d[0]['pages']]==[1,2,3]
    assert d[0]['status']=='REQUIRED_PAGE_REVIEWS_MISSING'
    assert d[0]['missing_review_count']==3 and 'reading_hash' not in d[0]
    assert all(len(p['render']['pixels_sha256'])==64 for p in d[0]['pages'])


def test_default_remains_first_gap_fail_closed():
    pdf,e=example();d=[]
    with pytest.raises(once.TrialError,match='required page visual review unavailable'):
        page.represent(pdf,e,diagnostics=d)
    assert len(d[0]['pages'])==1 and 'reading_hash' not in d[0]


@pytest.mark.parametrize('bad',[None,0,1,'true',[],{}])
def test_diagnostic_mode_is_strict_boolean(bad):
    pdf,e=example();d=[]
    with pytest.raises(once.TrialError,match='invalid page diagnostic mode'):
        page.represent(pdf,e,diagnostics=d,collect_missing=bad)
    assert not d


def test_pdf_identity_error_not_downgraded_to_missing_reviews():
    pdf,e=example();e['pdf_sha256']='f'*64;d=[]
    with pytest.raises(once.TrialError,match='representation PDF identity differs'):
        page.represent(pdf,e,diagnostics=d,collect_missing=True)
    assert not d


def test_corrupt_visual_binding_is_not_skipped():
    pdf,e=example();d=[]
    def invalid(*a):return {'schema_version':1},{}
    with pytest.raises(once.TrialError,match='page visual review binding differs'):
        page.represent(pdf,e,diagnostics=d,load_review=invalid,collect_missing=True)
    assert len(d[0]['pages'])==1 and 'reading_hash' not in d[0]


def test_loader_permission_error_aborts_diagnostics():
    pdf,e=example();d=[]
    def forbidden(*a):raise PermissionError('synthetic forbidden')
    with pytest.raises(PermissionError):
        page.represent(pdf,e,diagnostics=d,load_review=forbidden,collect_missing=True)
    assert len(d[0]['pages'])==1


def test_successful_mode_does_not_change_reading_bytes(monkeypatch):
    # Reuse the repository's deterministic PDF fixture; no new dependency.
    from test_pdf_text import _pdf_with_text_pages
    pdf=_pdf_with_text_pages('synthetic text')
    e={'pdf_sha256':once.sha(pdf),'text_sha256':'a'*64,
        'source_locator':'https://static.cninfo.com.cn/synthetic.PDF','page_count':1}
    assert once.raw(page.represent(pdf,e))==once.raw(page.represent(pdf,e,collect_missing=True))
