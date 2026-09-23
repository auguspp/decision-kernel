"""PR530 regression boundaries; no live source, model or remote mutation."""
from copy import deepcopy
import json
import socket

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import attention_inbox as brief
from decision_kernel.runtime import concept_detail_capture as capture
from decision_kernel.runtime import concept_detail_compat as compat
from decision_kernel.runtime import current_state as reading
from decision_kernel.runtime import reviewed_question_reading as reader
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import single_quick_contract as single
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_research_intake as intake


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError('Synthetic regression must not access network')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)


def test_legacy_core_is_not_redefined_by_new_raw_output_files():
    assert reader.CORE == {'prepare.json', 'input.json', 'candidate.json', 'validation.json',
                          'host-receipt.json', 'launch.json', 'funnel.json', 'receipt.json', 'admission.json'}
    assert reader.SINGLE_CORE == (reader.CORE - {'funnel.json'}) | {
        'research-attention.json', 'full-commission.json', *once.MODEL_OUTPUT_NAMES}
    assert reader.RETAINED_FILES == reader.CORE | reader.SINGLE_CORE


@pytest.mark.parametrize('method', ['research-funnel-v1', single.METHOD_VERSION])
def test_reservation_uses_selected_method_but_counts_existing_all_method_files(tmp_path, monkeypatch, method):
    from test_stock_daily_question import setup_daily
    from test_stock_daily_question_capacity import capacity_input, retain_case_files, view
    c = setup_daily(tmp_path, monkeypatch)
    p, state = capacity_input(c)
    p = p.model_copy(update={'method_version': method, 'prompt_version':
                           single.PROMPT_VERSION if method == single.METHOD_VERSION else p.prompt_version})
    # The same already-consumed new-method root is counted for both successors.
    old_prefix = reader.PREFIX + '1' * 64 + '/'
    retain_case_files(c, old_prefix, reader.SINGLE_CORE)
    commit, rows = view(c)
    planned = reader.SINGLE_CORE if method == single.METHOD_VERSION else reader.CORE
    required = len(reader.SINGLE_CORE) + 1 + len(planned)  # one shared declaration
    monkeypatch.setattr(daily.stock_reader, 'MAX_STOCK_SOURCE_FILES', required)
    daily.capacity(c.api, commit, rows, state, p)
    monkeypatch.setattr(daily.stock_reader, 'MAX_STOCK_SOURCE_FILES', required - 1)
    with pytest.raises(ValueError, match='DAILY_READING_CAPACITY_UNAVAILABLE'):
        daily.capacity(c.api, commit, rows, state, p)
    assert not c.calls and not c.writes


@pytest.mark.parametrize('damage', [None, 'unknown', 'missing', 'extra'])
def test_pre_single_quick_capture_replays_only_exact_reviewed_map(tmp_path, damage):
    from test_concept_detail_supplement import execute
    from test_concept_detail_compat import inventory, seal
    root, receipt, *_ = execute(tmp_path)
    expected = capture.verify(root)
    receipt = deepcopy(receipt)
    receipt['implementation'] = dict(compat.PRE_SINGLE_QUICK_IMPLEMENTATION)
    if damage == 'unknown': receipt['implementation']['identity.py'] = '0' * 64
    elif damage == 'missing': del receipt['implementation']['runtime/current_state.py']
    elif damage == 'extra': receipt['implementation']['new-code.py'] = '0' * 64
    seal(root, receipt)
    before = inventory(root)
    fn = capture._implementation
    with pytest.raises(ValueError, match='DETAIL_CAPTURE_IDENTITY_REJECTED'):
        capture.verify(root)
    if damage:
        with pytest.raises(ValueError, match='DETAIL_HISTORICAL_IMPLEMENTATION_REJECTED'):
            compat.verify(root)
    else:
        expected['capture_hash'] = receipt['capture_hash']
        assert compat.verify(root) == (expected, compat.PRE_SINGLE_QUICK)
    assert inventory(root) == before and capture._implementation is fn


def test_additional_compatibility_changes_only_the_handoff_projection_file():
    assert len(compat.PRE_SINGLE_QUICK_IMPLEMENTATION) == len(compat.REPLAY_IMPLEMENTATION) == 17
    assert {k for k in compat.REPLAY_IMPLEMENTATION
            if compat.REPLAY_IMPLEMENTATION[k] != compat.PRE_SINGLE_QUICK_IMPLEMENTATION[k]} == {'runtime/current_state.py'}
    assert capture._implementation() == compat.REPLAY_IMPLEMENTATION


def test_legacy_handoff_projection_identity_and_lane_remain_exact():
    from test_tinavi_drg_dip3_attention_dogfood import HANDOFF_PATH
    raw = HANDOFF_PATH.read_bytes()
    h = brief.parse_research_attention_handoff(raw.decode())
    source = {'path': 'saved/handoff.json', 'sha256': once.sha(raw)}
    expected = canonical_hash({'path': source['path'], 'sha256': once.sha(raw),
                               'funnel': h.research_funnel.model_dump(mode='json')})
    result = reading.project_handoffs([{'source': source}], lambda _: (raw, source))
    assert result['background'][0]['request_id'] == expected and not result['gaps']
    assert brief._markdown_lane('INDUSTRY_DISCOVERY') == 'INDUSTRY_DISCOVERY'


@pytest.mark.parametrize('value', ['<script>go()</script>', '![x](https://invalid.example/leak)', '__FORGED__', 'A\n# title'])
def test_only_plain_machine_lanes_bypass_markdown_escaping(value):
    assert brief._markdown_lane(value) == brief._markdown_text(value)
    assert '<script>' not in brief._markdown_lane(value)
    assert '![x]' not in brief._markdown_lane(value)


@pytest.mark.parametrize('field,value', [
    ('mutation_uncertain', True), ('mutation_uncertain', None),
    ('formal_research_started', False), ('automatic_retry', True), ('phase', 'RETENTION'),
])
def test_valid_candidate_is_not_confirmed_delivery_with_unsettled_host_receipt(tmp_path, monkeypatch, field, value):
    from test_single_quick_host_delivery import setup_single
    from test_reviewed_question_reading import collector, report
    c = setup_single(tmp_path, monkeypatch)
    assert host.run_question(**c.args)['status'] == 'VALIDATED_QUICK_RESULT'
    saved = c.api.files[c.api.heads[intake.WORK_REF]]
    name = c.prefix + 'host-receipt.json'
    receipt = json.loads(saved[name]); receipt[field] = value; saved[name] = once.raw(receipt)
    col, baseline = collector(c.args, tmp_path, stock=False)
    item = report(col, reader.attach(col, baseline))['question_work']['items'][0]
    assert item['status'] == 'UNAVAILABLE_OR_REJECTED'
    assert c.calls == ['quick']  # reading never retries the already-consumed research
