"""Reviewed legacy institutional replay after Sector-only backfill changes.

The exact original seven-file receipt is not rewritten. Only the known
installed pair is admitted. _clock and _check_safe_json are AST-identical;
changed functions belong to the unused Sector producer/audit path.
"""
from pathlib import Path
from types import FunctionType, MappingProxyType

from . import institutional_radar_capture as capture
from . import institutional_radar as radar

HISTORICAL = MappingProxyType({'adapters/hithink.py': '37c0ef66e73eb6b0aab1da95929692e21e457f7bd664c59d1d51fddcccd83412',
 'identity.py': 'f1160658353809fa75f99986d041d9ece25bb8a1c0ddd68db8e88c8bd36dcf60',
 'runtime/hithink_dump_trial.py': '06ead7ca852c7192c983df2564a73425573ee6695a8ffbe7a82a8d8843bc0188',
 'runtime/institutional_radar.py': 'dfb773636f5421268382b411ca2277636b0b53d61c9f274689b43062d4b5b45f',
 'runtime/institutional_radar_capture.py': '859cdbcf2ac1c7f19f382a8b1d3d8b4d32c7755a456895dd7eba94891e90aa73',
 'runtime/sector_radar_audit.py': 'a92ef7350f824656cd40572d6d94a97b98fbf7b72461ab6c3064955e11693517',
 'runtime/theme_radar_probe.py': '2f48bff34c64e24090250ea00b7101c0cd4c07be1e718fdfeaa92fbdc61b4a56'})
INSTALLED = MappingProxyType({'adapters/hithink.py': '37c0ef66e73eb6b0aab1da95929692e21e457f7bd664c59d1d51fddcccd83412',
 'identity.py': 'f1160658353809fa75f99986d041d9ece25bb8a1c0ddd68db8e88c8bd36dcf60',
 'runtime/hithink_dump_trial.py': '06ead7ca852c7192c983df2564a73425573ee6695a8ffbe7a82a8d8843bc0188',
 'runtime/institutional_radar.py': 'dfb773636f5421268382b411ca2277636b0b53d61c9f274689b43062d4b5b45f',
 'runtime/institutional_radar_capture.py': '859cdbcf2ac1c7f19f382a8b1d3d8b4d32c7755a456895dd7eba94891e90aa73',
 'runtime/sector_radar_audit.py': '1cdf284024b114b05d6fdfeeed99d4550d2b5d59b8b69676c1962660b5ac1e07',
 'runtime/theme_radar_probe.py': '2f48bff34c64e24090250ea00b7101c0cd4c07be1e718fdfeaa92fbdc61b4a56'})


def verify(root: Path):
    capture._safe_path(root)
    receipt = radar.decode((root/'capture.json').read_bytes())
    current = capture._implementation()
    if receipt.get('implementation') == current:
        return capture.verify(root), 'ORIGINAL_CURRENT_IMPLEMENTATION'
    radar._require(receipt.get('implementation') == HISTORICAL and current == INSTALLED,
                   'UNREVIEWED_INSTITUTIONAL_COMPATIBILITY')
    bindings=dict(capture.verify.__globals__)
    bindings['_implementation']=lambda: dict(HISTORICAL)
    verifier=FunctionType(capture.verify.__code__,bindings,capture.verify.__name__,
                          capture.verify.__defaults__,capture.verify.__closure__)
    return verifier(root), 'REVIEWED_SECTOR_ONLY_CHANGE_579'
