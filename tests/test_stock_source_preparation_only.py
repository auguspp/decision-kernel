"""Synthetic controls for source-only checks; not issuer evidence or admission."""
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter

from decision_kernel.adapters.cninfo import CninfoAnnouncement
from decision_kernel.runtime import cninfo_http as cn
from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import disclosure_source_reading as page
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_research_sources as source

NOW = '2026-09-13T12:00:00+00:00'
CODE = 'a' * 40  # Synthetic test identity, never a production code reference.


@pytest.fixture(autouse=True)
def prohibit_network_and_models(monkeypatch):
    def denied(*a, **kw):
        raise AssertionError('Network/model/Retainer forbidden in source-only tests')
    import socket
    monkeypatch.setattr(socket, 'create_connection', denied)
    monkeypatch.setattr(socket.socket, 'connect', denied)
    monkeypatch.setattr(once, 'model_call', denied)
    monkeypatch.setattr(once.Retainer, 'save', denied)


def blank_pdf(count=3):
    writer = PdfWriter()
    for _ in range(count):
        writer.add_blank_page(width=100, height=100)
    out = BytesIO(); writer.write(out)
    return out.getvalue()


def evidence(pdf, n=3):
    return {'pdf_sha256': once.sha(pdf), 'text_sha256': 'b'*64,
            'source_locator': 'https://static.cninfo.com.cn/synthetic.PDF', 'page_count': n}


class NoReviews:
    def file(self, *args):
        raise delivery.GitHubReadError('GitHub HTTP 404')
    def get(self, *args):
        raise AssertionError('No commit read needed for an absent note')


def fixture_capture(tmp_path, monkeypatch, mode='missing', count=3):
    rows = tuple(CninfoAnnouncement(str(i), '603353', 'synthetic-org',
        '2026年半年度报告' if i == count else f'synthetic disclosure {i}', None,
        datetime.fromisoformat('2026-08-29T00:00:00+08:00'),
        f'https://static.cninfo.com.cn/synthetic-{i}.PDF') for i in range(1, count+1))
    batch = cn.CninfoDisclosureBatch('603353', 'synthetic-org', date(2025,8,9),
                                   date(2026,9,13), rows)
    pdf = blank_pdf(); calls = []
    def fetch_pdf(**kwargs):
        calls.append(kwargs['source_locator'])
        if mode == 'transport' and len(calls) == 2:
            raise cn.CninfoRuntimeError('synthetic transport failure')
        return pdf
    def extract(data, **kwargs):
        # Fake extraction is explicit: this tests dispatch/control, not typography.
        text = '' if mode == 'missing' and len(calls) == 1 else '603353 报告 full synthetic text'
        if mode == 'oversize':
            text += '风' * (source.CONTEXT_BYTES // 3 + 10)
        return SimpleNamespace(pdf_sha256=once.sha(data),text_sha256=once.sha(text.encode()),
            page_count=3,pages=[SimpleNamespace(page_number=i,text=text) for i in range(1,4)])
    return dict(ticker='603353',observation={'row':{'company_name':'和顺石油'}},
        api=NoReviews(),code_commit=CODE,output=tmp_path/'out',clock=lambda: NOW,
        fetch=lambda **kw: batch, fetch_pdf=fetch_pdf, extract=extract), calls


def test_original_default_still_stops_at_first_missing_page(tmp_path, monkeypatch):
    args, calls = fixture_capture(tmp_path, monkeypatch)
    with pytest.raises(once.TrialError, match='required page visual review unavailable'):
        source.capture(**args)
    assert len(calls) == 1
    journal=json.loads((args['output']/'source-journal.json').read_bytes())
    assert len(journal['representation_events'][0]['pages']) == 1
    assert not (args['output']/'source-preparation.json').exists()
    assert not (args['output']/'prepared-context.json').exists()


def test_preparation_enumerates_all_missing_pages_then_later_documents(tmp_path, monkeypatch):
    args, calls = fixture_capture(tmp_path, monkeypatch)
    result = source.capture(**args, preparation_only=True)
    assert len(calls) == 3
    assert result['status'] == 'PREPARATION_INCOMPLETE'
    assert result['checked_body_ids'] == ['2','3'] and result['unattempted_ids'] == []
    assert [p['page_number'] for p in result['missing_page_reviews'][0]['pages']] == [1,2,3]
    assert result['complete_context'] is None and result['research_execution_allowed'] is False
    assert not (args['output']/'prepared-context.json').exists()
    assert not list(args['output'].rglob('launch.json'))
    assert not list(args['output'].rglob('candidate.json'))
    assert json.loads((args['output']/'source-preparation.json').read_bytes()) == result


def test_preparation_saves_exact_complete_context_without_admitting(tmp_path, monkeypatch):
    args, calls = fixture_capture(tmp_path, monkeypatch, mode='ready')
    report = source.capture(**args, preparation_only=True)
    context_raw = (args['output']/'prepared-context.json').read_bytes()
    context = json.loads(context_raw)
    assert report['status'] == 'SOURCES_CHECKED_NOT_EXECUTION_ADMITTED'
    assert report['checked_body_ids'] == report['selected_ids'] == ['1','2','3']
    assert len(context['issuer_documents']) == 3
    assert report['complete_context']['bytes'] == len(context_raw)
    assert report['complete_context']['sha256'] == once.sha(context_raw)
    assert report['complete_context']['within_current_limit'] is True
    assert report['research_execution_allowed'] is False
    assert report['investment_authority'] == 'NONE'


def test_oversize_context_is_retained_not_clipped_or_marked_ready(tmp_path, monkeypatch):
    args, calls = fixture_capture(tmp_path, monkeypatch, mode='oversize')
    result = source.capture(**args, preparation_only=True)
    raw = (args['output']/'prepared-context.json').read_bytes()
    assert len(calls) == 3 and len(raw) > source.CONTEXT_BYTES
    assert result['status'] == 'PREPARATION_INCOMPLETE'
    assert result['error_code'] == 'full business context too large; no clipping'
    assert result['complete_context']['within_current_limit'] is False
    assert result['complete_context']['bytes'] == len(raw)
    assert result['complete_context']['sha256'] == once.sha(raw)
    assert sum(len(d['pages']) for d in json.loads(raw)['issuer_documents']) == 9
    assert result['research_execution_allowed'] is False


def test_default_oversize_still_raises_original_code(tmp_path, monkeypatch):
    args, _ = fixture_capture(tmp_path, monkeypatch, mode='oversize')
    with pytest.raises(once.TrialError, match='full business context too large; no clipping'):
        source.capture(**args)
    assert not (args['output']/'prepared-context.json').exists()


def test_transport_failure_not_swallowed_as_a_page_gap(tmp_path, monkeypatch):
    args, calls = fixture_capture(tmp_path, monkeypatch, mode='transport')
    with pytest.raises(cn.CninfoRuntimeError):
        source.capture(**args, preparation_only=True)
    r=json.loads((args['output']/'source-preparation.json').read_bytes())
    assert len(calls) == 2 and r['unattempted_ids'] == ['3']
    assert r['error_type'] == 'CninfoRuntimeError' and r['status'] == 'PREPARATION_INCOMPLETE'
    assert r['complete_context'] is None and r['research_execution_allowed'] is False


@pytest.mark.parametrize('mode',[None,0,1,'true',[],{}])
def test_strict_preparation_mode_before_any_io(tmp_path, monkeypatch, mode):
    args,calls=fixture_capture(tmp_path,monkeypatch)
    with pytest.raises(once.TrialError,match='invalid source preparation mode'):
        source.capture(**args,preparation_only=mode)
    assert not calls and not args['output'].exists()


def test_create_only_no_overwrite_of_a_previous_preparation(tmp_path, monkeypatch):
    args,calls=fixture_capture(tmp_path,monkeypatch,mode='ready')
    source.capture(**args,preparation_only=True)
    before={p.name:p.read_bytes() for p in args['output'].iterdir()}
    with pytest.raises(FileExistsError):
        source.capture(**args,preparation_only=True)
    assert len(calls)==3 and before=={p.name:p.read_bytes() for p in args['output'].iterdir()}


def test_symlink_output_rejected_before_capture(tmp_path, monkeypatch):
    args,calls=fixture_capture(tmp_path,monkeypatch)
    target=tmp_path/'target'; target.mkdir(); args['output'].symlink_to(target, target_is_directory=True)
    with pytest.raises(once.TrialError,match='unsafe source preparation output'):
        source.capture(**args,preparation_only=True)
    assert not calls and not list(target.iterdir())


def test_a_larger_capture_limit_cannot_hide_the_source_reference_limit(tmp_path, monkeypatch):
    args,calls=fixture_capture(tmp_path,monkeypatch,mode='ready')
    monkeypatch.setattr(source.identity,'MAX_BYTES',100)
    result=source.capture(**args,preparation_only=True)
    assert result['complete_context']['within_current_limit'] is True
    assert result['complete_context']['within_source_reference_limit'] is False
    assert result['error_code']=='complete source exceeds checked reference byte limit'
    assert result['status']=='PREPARATION_INCOMPLETE'
    assert result['research_execution_allowed'] is False
