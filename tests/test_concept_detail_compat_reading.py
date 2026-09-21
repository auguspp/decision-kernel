"""Historical-equivalence integration through the existing Collector, synthetic only."""
import json

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import concept_detail_compat as compat
from decision_kernel.runtime import concept_detail_capture as capture
from decision_kernel.runtime import concept_detail_reading as reader
from decision_kernel.runtime import current_state as model
from decision_kernel.runtime import radar_company_reading as companies
from test_concept_detail_reading import fixture, packed, view, raw, no_network


@pytest.mark.parametrize('tamper', [False, True])
def test_historical_pair_through_existing_reader_preserves_bytes_or_reports_gap(tmp_path, tamper):
    col, parent, run, artifact, files, archives = fixture(tmp_path)
    before = view(col, parent)
    receipt = json.loads(files['payload/capture.json'])
    receipt['implementation'] = dict(compat.HISTORICAL_IMPLEMENTATION)
    if tamper:
        report = json.loads(files['payload/observation.json'])
        report['projection']['companies'][0]['source_names'] = ['FORGED']
        report['projection_hash'] = canonical_hash(report['projection'])
        files['payload/observation.json'] = raw(report)
        receipt['files']['observation.json'] = capture._digest(files['payload/observation.json'])
    receipt['capture_hash'] = canonical_hash({k: v for k, v in receipt.items() if k != 'capture_hash'})
    files['payload/capture.json'] = raw(receipt)
    verification = json.loads(files['verification.json'])
    verification['capture_hash'] = receipt['capture_hash']
    files['verification.json'] = raw(verification)
    archives[400] = packed(files)
    artifact.update(size_in_bytes=len(archives[400]), digest='sha256:' + model.sha256(archives[400]))
    result = reader.attach(col, parent)
    status = result['research']['radar_discovery']['source_status']['concept_detail']
    assert result['lanes'] == parent['lanes'] and result['pending'] == parent['pending']
    model.validate_read_package(result)
    assert len(col.files['current-state.json']) <= 192 * 1024
    if tamper:
        assert status['status'] == 'UNAVAILABLE_OR_REJECTED'
        assert status['failed_stage'] == 'PAYLOAD_REPLAY'
        assert view(col, result)['companies'] == before['companies']
        assert not any(p.startswith('details/concept-detail/') for p in col.files)
    else:
        assert status['status'] == 'VERIFIED_SAVED_CONCEPT_DETAIL'
        assert status['replay_mode'] == compat.HISTORICAL
        assert status['replay'] == verification
        assert status['replay']['network_calls'] == 0
        for name, data in files.items():
            if name.startswith('payload/'):
                assert companies.retained_bytes(col.files, status['details'][name[8:]]) == data
        assert col.files[status['archive']['read_path']] == archives[400]
