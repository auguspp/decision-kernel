"""Attach a small concept map to the existing saved-source publisher only."""
from __future__ import annotations

from copy import deepcopy
import json
from urllib.parse import quote

from . import current_state as model
from . import current_state_delivery as delivery
from . import concept_observation_map as observation
from . import institutional_radar_reading as radar_reading
from .radar_company_reading import retained_bytes

PREFIX = 'details/radar/concept-observation-map.'


def attach(collector, baseline):
    model.validate_read_package(baseline)
    discovery = baseline['research'].get('radar_discovery', {})
    status = discovery.get('source_status', {}).get('concept', {})
    if status.get('status') != 'VERIFIED_SAVED_CONCEPT_SOURCE':
        return baseline  # Existing source gap already explicit; no old fallback.
    before = dict(collector.files)
    research = deepcopy(baseline['research'])
    try:
        radar_reading._reserve(collector, files=2)
        reference = status['details']['observation.json']
        report = json.loads(retained_bytes(collector.files, reference))
        model.check(report['projection_hash'] == status['projection_hash']
                    and report['projection']['market_session'] == status['market_session']
                    and report['projection']['as_of'] == status['source_observed_at']
                    and model.clock(status['source_observed_at']) <= model.clock(baseline['generated_at']),
                    'Concept map source binding differs')
        supplement = supplement_reference = None
        detail_status = discovery.get('source_status', {}).get('concept_detail', {})
        if detail_status.get('status') == 'VERIFIED_SAVED_CONCEPT_DETAIL':
            supplement_reference = detail_status['details']['observation.json']
            supplement = json.loads(retained_bytes(collector.files, supplement_reference))
            sp = supplement['projection']
            model.check(supplement['projection_hash'] == detail_status['projection_hash']
                and sp['base_projection_hash'] == detail_status['base_projection_hash'] == report['projection_hash']
                and sp['market_session'] == detail_status['market_session'] == status['market_session']
                and sp['as_of'] == detail_status['source_observed_at']
                and model.clock(sp['as_of']) <= model.clock(baseline['generated_at']),
                'Concept map supplement binding differs')
        value = observation.build(report, supplement=supplement)
        observation.verify(value, report, supplement=supplement)
        data = {PREFIX+'json': model.json_bytes(value), PREFIX+'html': observation.render(value).encode()}
        model.check(sum(map(len, collector.files.values())) + sum(map(len, data.values()))
                    <= delivery.MAX_RETAINED_OUTPUT, 'Concept map byte reserve unavailable')
        refs = {suffix: collector.retain(PREFIX+suffix, data[PREFIX+suffix]) for suffix in ('json', 'html')}
        research['radar_discovery']['concept_observation_map'] = {
            'status': 'READ_OK', 'details': refs, 'source': reference,
            'source_projection_hash': status['projection_hash'],
            'projection_hash': value['projection_hash'], 'coverage': value['projection']['coverage'],
            'meaning': 'SOURCE_BOUND_NAVIGATION_AND_COVERAGE_NOT_NEW_ACQUISITION', **observation.AUTHORITY}
        if supplement is not None:
            research['radar_discovery']['concept_observation_map']['supplement_source'] = supplement_reference
        elif detail_status:
            # Do not let a usable primary map hide a failed/unread latest supplement.
            research['radar_discovery']['concept_observation_map']['supplement_status'] = detail_status['status']
        return _finish(collector, baseline, research)
    except radar_reading.ERRORS as exc:
        # No sources/cache/network touched here; only added/replacement files roll back.
        collector.files = before
        research = deepcopy(baseline['research'])
        research['radar_discovery']['concept_observation_map'] = {
            'status': 'UNAVAILABLE_OR_REJECTED', 'error_type': type(exc).__name__,
            'meaning': 'MAP_GAP_NOT_SOURCE_FAILURE; ORIGINAL_COMPANY_AND_SOURCE_DATA_PRESERVED',
            **observation.AUTHORITY}
        return _finish(collector, baseline, research)


def _finish(collector, baseline, research):
    payload = radar_reading._assemble(collector, baseline, research)
    value = research['radar_discovery']['concept_observation_map']
    if value['status'] == 'READ_OK':
        ref = value['details']['html']
        path = model.safe_path(ref['read_path'])
        model.check(ref['read_ref_rule'] == 'USE_THE_SAME_PINNED_READING_COMMIT', 'Foreign concept map')
        note = '\n## 概念趋势、重叠与未覆盖\n\n[打开概念观察地图](' + quote(path, safe='/') + ')\n'
        note += '保留各指数多日路径；按实际成员包含关系减少重复阅读。完整补查范围不是已执行批次，也不是研究优先级。\n'
        if value.get('supplement_status'):
            note += '补充批次本次未纳入地图，原因见来源状态；主来源可读不代表补充成功或无新增观察。\n'
    else:
        note = '\n概念观察地图读取有缺口；已核验的原始概念、公司和研究状态仍保留，不能把地图不可用当成无趋势。\n'
    data = {'README.md': collector.files['README.md'] + note.encode()}
    model.check(sum(len(raw) for path, raw in collector.files.items() if path not in data)
                + sum(map(len, data.values())) <= delivery.MAX_RETAINED_OUTPUT, 'Concept map final bytes unavailable')
    radar_reading._reserve(collector, replacements=data)
    collector.files.update(data)
    return payload
