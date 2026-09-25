"""Explicit reviewed replay-equivalence maps; no artifact code or receipt rewriting.

#479 covered #478 root formatting. #530 additionally changes only the
project_handoffs display function in current_state; detail replay never calls it.
#579 changes only the stock-reference / Sector-audit surfaces whose hashes are
inherited by the broad implementation fingerprint; concept-detail replay never
calls those Sector paths. Historical maps remain immutable.
See docs/concept-detail-replay-compatibility-v1.md for the evidence and limits.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import FunctionType, MappingProxyType

from . import concept_detail_capture as capture

HISTORICAL_IMPLEMENTATION = MappingProxyType({
    'adapters/hithink.py': '37c0ef66e73eb6b0aab1da95929692e21e457f7bd664c59d1d51fddcccd83412',
    'adapters/hithink_index.py': '9bf1e637e9ce1542eb3e9e42a670a11f89a81f50833dc197f25b5ca4180a80cc',
    'identity.py': 'f1160658353809fa75f99986d041d9ece25bb8a1c0ddd68db8e88c8bd36dcf60',
    'runtime/concept_detail_capture.py': 'a1aa7c78c7b4d25219239293ebd675674c022127c36ec61012117e16d8f9af94',
    'runtime/concept_detail_supplement.py': 'c1cc07b4a6e68028e685f7c91d1b2e778fb23e7347efcec52df5acddfde8598e',
    'runtime/concept_radar.py': '3d572ce68cedd686bd442e7a8eb5e4b516f029908b90d253928cae8ee92d5be8',
    'runtime/concept_radar_capture.py': '8f9f4184b3a7d655f80be4b28760ffc3dfe4e9e435284f89dc31f04fa5e19e5e',
    'runtime/current_state.py': 'e3ac5837585bc48bd8355a33047511a377e5e246f6477cbc29fc89169fd27c05',
    'runtime/current_state_delivery.py': 'b78eeda1a3c59fdb3ac5b84c83065159a754239f5c899567024d0165f8b8990b',
    'runtime/hithink_dump_trial.py': '06ead7ca852c7192c983df2564a73425573ee6695a8ffbe7a82a8d8843bc0188',
    'runtime/hithink_sector_breadth_http.py': '3202b43a19c01acb93938e1913606d2dfd622b92c26cc892249a7a33539a86f9',
    'runtime/institutional_radar.py': 'dfb773636f5421268382b411ca2277636b0b53d61c9f274689b43062d4b5b45f',
    'runtime/institutional_radar_capture.py': '859cdbcf2ac1c7f19f382a8b1d3d8b4d32c7755a456895dd7eba94891e90aa73',
    'runtime/sector_breadth.py': 'a781d35ffcacaced39a8bd469669bb03d742da053b4ff92604e8e1d4289bad1d',
    'runtime/sector_radar.py': 'd69abee2d76da54c604d4f728501bf1f4be1028f81510bddcd7a893a7ac01f61',
    'runtime/sector_radar_audit.py': 'a92ef7350f824656cd40572d6d94a97b98fbf7b72461ab6c3064955e11693517',
    'runtime/theme_radar_probe.py': '2f48bff34c64e24090250ea00b7101c0cd4c07be1e718fdfeaa92fbdc61b4a56',
})
PRE_SINGLE_QUICK_IMPLEMENTATION = MappingProxyType({
    **HISTORICAL_IMPLEMENTATION,
    'runtime/current_state.py': 'e31f54cdef58e3566429e5cccbf87cc459c323d35ae217d68a330ccc3ae0b032',
    'runtime/current_state_delivery.py': '71445a002f5302534e372e8ca7273768b6519cddd54a4d5f532a148b94e09117',
})
REPLAY_IMPLEMENTATION = MappingProxyType({
    **PRE_SINGLE_QUICK_IMPLEMENTATION,
    'runtime/current_state.py': '1faa6925d05debe4b0f22e5574eb365de4d36380036fd50b110c8e541ad22845',
})
POST_SECTOR_BACKFILL_IMPLEMENTATION = MappingProxyType({
    **REPLAY_IMPLEMENTATION,
    'runtime/hithink_sector_breadth_http.py': '92f24b05d7baea252d67ae83d2caaab84eb12f57adfa03818bac046ab2aa294a',
    'runtime/sector_radar_audit.py': '1cdf284024b114b05d6fdfeeed99d4550d2b5d59b8b69676c1962660b5ac1e07',
})
CURRENT = 'CURRENT_IMPLEMENTATION'
HISTORICAL = 'REVIEWED_HISTORICAL_EQUIVALENCE_478'
PRE_SINGLE_QUICK = 'REVIEWED_HISTORICAL_EQUIVALENCE_530'


def verify(output: Path) -> tuple[dict, str]:
    """Rebuild with the unchanged verifier after exact two-sided identity checks.

    A private function binding reuses installed code without monkeypatching the
    capture module, mutating data, or executing source from an archive. All hash,
    inventory, base-ZIP, plan, clock, request and result checks still run.
    """
    receipt = json.loads(capture._read(output, 'capture.json'))
    installed = capture._implementation()
    if receipt.get('implementation') == installed:
        return capture.verify(output), CURRENT
    historical = receipt.get('implementation')
    capture.require(
        historical in (HISTORICAL_IMPLEMENTATION, PRE_SINGLE_QUICK_IMPLEMENTATION)
        and installed in (REPLAY_IMPLEMENTATION, POST_SECTOR_BACKFILL_IMPLEMENTATION),
        'DETAIL_HISTORICAL_IMPLEMENTATION_REJECTED',
    )
    # Bind only this invocation's identity expectation, after validating BOTH
    # complete maps. Never assign to capture._implementation or rewrite a receipt.
    bindings = dict(capture.verify.__globals__)
    bindings['_implementation'] = lambda: dict(historical)
    verifier = FunctionType(capture.verify.__code__, bindings,
                            capture.verify.__name__, capture.verify.__defaults__,
                            capture.verify.__closure__)
    return verifier(output), (HISTORICAL if historical == HISTORICAL_IMPLEMENTATION else PRE_SINGLE_QUICK)
