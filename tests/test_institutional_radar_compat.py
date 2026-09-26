"""Historical fingerprints stay immutable; only the reviewed pair may replay."""
import json
import pytest
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import institutional_radar_capture as capture
from decision_kernel.runtime import institutional_radar_compat as compat
from test_institutional_radar import run_capture


def test_exact_maps_differ_only_in_reviewed_unused_sector_code():
    assert capture._implementation()==compat.INSTALLED
    assert {k for k in compat.HISTORICAL if compat.HISTORICAL[k]!=compat.INSTALLED[k]}=={'runtime/sector_radar_audit.py'}
    with pytest.raises(TypeError):compat.HISTORICAL['new']='x'


def test_private_binding_does_not_modify_original_verifier_or_receipt(tmp_path):
    run_capture(tmp_path)
    root=tmp_path/'payload'
    if not root.exists():root=next(p.parent for p in tmp_path.rglob('capture.json'))
    receipt=json.loads((root/'capture.json').read_bytes())
    receipt['implementation']=dict(compat.HISTORICAL)
    receipt['capture_hash']=canonical_hash({k:v for k,v in receipt.items() if k!='capture_hash'})
    (root/'capture.json').write_bytes(capture._bytes(receipt));before=(root/'capture.json').read_bytes()
    implementation=capture._implementation
    with pytest.raises(ValueError):capture.verify(root)
    report,label=compat.verify(root)
    assert label=='REVIEWED_SECTOR_ONLY_CHANGE_579' and report['network_calls']==0
    assert (root/'capture.json').read_bytes()==before and capture._implementation is implementation


def test_unknown_historical_hash_never_whitelisted(tmp_path):
    run_capture(tmp_path);root=next(p.parent for p in tmp_path.rglob('capture.json'))
    receipt=json.loads((root/'capture.json').read_bytes());receipt['implementation']=dict(compat.HISTORICAL)
    receipt['implementation']['identity.py']='0'*64
    receipt['capture_hash']=canonical_hash({k:v for k,v in receipt.items() if k!='capture_hash'})
    (root/'capture.json').write_bytes(capture._bytes(receipt))
    with pytest.raises(ValueError,match='UNREVIEWED'):compat.verify(root)
