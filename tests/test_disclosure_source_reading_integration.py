"""Synthetic source preparation -> original admission/executor. No live calls."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from decision_kernel.runtime import disclosure_source_reading as r
from decision_kernel.runtime import saved_disclosure_preparation as prep
from decision_kernel.runtime import saved_disclosure_host as host
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import incremental_disclosure as work
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime.current_state_delivery import GitHubReadError
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket
from test_saved_disclosure_preparation import setup, packet_pdf, capture_files, archive, scan, CODE, WORK
from test_disclosure_source_reading import visual
from test_saved_research_once import pre


def context_args(packet, pdf):
    _, _, run = scan([packet])
    data, artifact = archive(capture_files(packet, pdf), run)
    return dict(packet_raw=packet, archive_raw=data, artifact=artifact, run=run,
                clock=lambda: '2026-09-13T08:00:00Z')


def add_review(api, packet, pdf):
    e = identity._json(packet)['evidence'][0]
    note, _ = visual(pdf, e)
    note['reviewed_at'] = '2026-09-12T12:00:00Z'
    path = r.review_path(e['pdf_sha256'], e['page_count'])
    api.snapshots[CODE][path] = once.raw(note)
    api.commits[CODE] = {'sha': CODE, 'committer': {'date': '2026-09-12T12:30:00Z'}}
    original = api.file
    def file(path, ref):
        try: return original(path, ref)
        except KeyError: raise GitHubReadError('GitHub HTTP 404') from None
    api.file = file
    return path, note


def test_legacy_source_context_still_rejects_empty_original():
    packet, pdf = packet_pdf('')
    with pytest.raises(once.TrialError, match='required body has no text'):
        prep.source_context(**context_args(packet, pdf))


def test_valid_original_keeps_exact_context_without_alternate_parser():
    packet, pdf = packet_pdf()
    args = context_args(packet, pdf)
    old = prep.source_context(**args)
    value = prep.source_context(**args, requalify=lambda *a: pytest.fail('unnecessary alternate parser'))
    assert value == old
    assert value[0]['disclosure_packet'] == identity._json(packet)
    assert 'page_readings' not in value[0]['source_capture']


def test_different_original_extraction_cannot_be_excused_by_new_parser():
    packet, pdf = packet_pdf()
    def wrong(raw, **limits):
        return replace(prep.extract_pdf_text(raw, **limits), text_sha256='0' * 64)
    with pytest.raises(once.TrialError, match='original PDF extraction identity differs'):
        prep.source_context(**context_args(packet, pdf), extract=wrong,
            requalify=lambda *a: pytest.fail('bypassed original identity'))


def test_new_reading_still_uses_original_encrypted_corrupt_guard():
    from decision_kernel.adapters.pdf_text import PdfTextExtractionError
    packet, pdf = packet_pdf()
    def reject(*args, **kwargs): raise PdfTextExtractionError('original guard rejects')
    with pytest.raises(PdfTextExtractionError, match='original guard rejects'):
        prep.source_context(**context_args(packet, pdf), extract=reject,
            requalify=lambda *a: pytest.fail('bypassed original structural guard'))


def test_reviewed_page_is_preserved_and_passes_original_preparation_and_executor(tmp_path, monkeypatch):
    args, api, clock, packet, pdf = setup(tmp_path, monkeypatch, text='')
    add_review(api, packet, pdf)
    original_work = deepcopy(api.snapshots[WORK])
    prepared = prep.prepare_reserved(**args)
    assert prepared['status'] == 'INPUT_PREPARED_NOT_EXECUTED', prepared
    p = ExternalResearchInputPacket.model_validate_json(api.file(
        prepared['input_source']['path'], prepared['input_source']['ref']))
    source = next(s for s in p.source_refs if s.purpose == 'MODEL_CONTEXT')
    context = identity._json(api.file(source.path, source.ref))
    assert context['disclosure_packet'] == identity._json(packet)
    assert context['source_capture']['page_readings'][0]['pages'][0]['method'] == 'AI_VISUAL_READING'
    assert len(p.seed_evidence_artifacts) == 1
    assert len(context['disclosure_packet']['evidence']) == 1  # Same source, not a second evidence vote.
    calls = []
    def mock_model(stage, prompt, model, out, usage):
        calls.append(stage)
        assert stage == 'pre'
        assert prompt['public_context'] == context
        assert prompt['evidence_ids'] == [str(p.seed_evidence_artifacts[0].id)]
        return pre(prompt)
    monkeypatch.setattr(once, 'model_call', mock_model)
    result = host.execute_prepared(api=api, prepared=prepared, code_commit=CODE,
                                   output=tmp_path/'execution', clock=clock)
    assert result['status'] == 'VALIDATED_FUNNEL_RESULT', result
    assert result['formal_research_started'] and calls == ['pre']
    assert all(api.file(path, api.work) == raw for path, raw in original_work.items())
    snapshots = deepcopy(api.snapshots)
    second = host.execute_prepared(api=api, prepared=prepared, code_commit=CODE,
                                    output=tmp_path/'again', clock=clock)
    assert second['status'] == 'ALREADY_LAUNCHED_NO_EXECUTION'
    assert calls == ['pre'] and snapshots == api.snapshots


@pytest.mark.parametrize('change', ['missing', 'edited', 'future'])
def test_main_visual_record_rechecked_before_egress_and_launch(tmp_path, monkeypatch, change):
    args, api, clock, packet, pdf = setup(tmp_path, monkeypatch, text='')
    path, note = add_review(api, packet, pdf)
    prepared = prep.prepare_reserved(**args)
    assert prepared['status'] == 'INPUT_PREPARED_NOT_EXECUTED', prepared
    if change == 'missing': del api.snapshots[CODE][path]
    elif change == 'edited':
        note['text'] += ' changed after source freeze'
        api.snapshots[CODE][path] = once.raw(note)
    else:
        api.commits[CODE]['committer']['date'] = '2027-01-01T00:00:00Z'
    prior = deepcopy(api.snapshots[api.work])
    monkeypatch.setattr(once, 'model_call', lambda *a: pytest.fail('model invoked'))
    with pytest.raises(once.TrialError):
        host.execute_prepared(api=api, prepared=prepared, code_commit=CODE,
                              output=tmp_path/'execution', clock=clock)
    assert api.snapshots[api.work] == prior
    assert not (tmp_path/'execution').exists()


def test_missing_visual_note_is_source_gap_with_partial_pixel_diagnosis(tmp_path, monkeypatch):
    args, api, _, packet, pdf = setup(tmp_path, monkeypatch, text='')
    path, _ = add_review(api, packet, pdf)
    del api.snapshots[CODE][path]
    result = prep.prepare_reserved(**args)
    assert result['status'] == 'NOT_EXECUTED' and result['error_code'] == 'required page visual review unavailable'
    assert [x.rsplit('/', 1)[-1] for x in api.writes] == ['failure.json']
    events = json.loads((args['output']/'source-reading-events.json').read_bytes())
    assert events[0]['pages'][0]['render']['pixels_sha256']
    prior = deepcopy(api.snapshots)
    again = prep.prepare_reserved(**dict(args, output=tmp_path/'again'))
    assert again['status'] == 'ALREADY_ATTEMPTED_NO_PREPARATION' and prior == api.snapshots


def test_mutated_capture_never_reaches_representation(tmp_path, monkeypatch):
    args, api, _, _, _ = setup(tmp_path, monkeypatch, text='')
    args['body_raw'] += b'changed'
    monkeypatch.setattr(r, 'represent', lambda *a, **k: pytest.fail('bad captured source accepted'))
    result = prep.prepare_reserved(**args)
    assert result['status'] == 'NOT_EXECUTED' and not result['formal_research_started']
    assert all(not x.endswith('/input.json') for x in api.writes)


def test_alternate_decoder_supplements_but_never_replaces_saved_extraction():
    # A synthetic recorded extractor makes the font-decoding defect explicit.
    # This is composition testing, not replay of a real issuer's pypdf output.
    from decision_kernel.adapters.pdf_text import PdfPageText
    def recorded(pdf, **limits):
        original = prep.extract_pdf_text(pdf, **limits)
        pages = (PdfPageText(page_number=1, text='damaged\x01text'),)
        return replace(original, pages=pages, extracted_char_count=len(pages[0].text),
            text_sha256=read.canonical_hash([{'page_number': 1, 'text': pages[0].text}]))
    packet, pdf = packet_pdf('Readable original PDF', extractor=recorded)
    args = context_args(packet, pdf)
    with pytest.raises(once.TrialError, match='encoding damage'):
        prep.source_context(**args, extract=recorded)
    context, reads = prep.source_context(**args, extract=recorded, requalify=r.represent)
    assert context['disclosure_packet'] == identity._json(packet)
    assert context['disclosure_packet']['evidence'][0]['pages'][0]['text'] == 'damaged\x01text'
    assert context['source_capture']['page_readings'][0]['pages'][0]['text'] == 'Readable original PDF'
    assert reads[0]['body_sha256'] == read.sha256(pdf) and len(reads) == 1
