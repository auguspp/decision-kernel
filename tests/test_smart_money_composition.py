"""Real existing optional-reader composition, including NOT_RUN and fallback."""
import json
import pytest
from decision_kernel.runtime import current_state as m
from decision_kernel.runtime import research_reentry_reading as reentry
from decision_kernel.runtime import smart_money_reading as sm
from decision_kernel.runtime import smart_money_view as view
from test_smart_money import offline
from test_smart_money_reading import setup


@pytest.mark.parametrize('mode',['ready','not_run','renderer_failure'])
def test_real_reentry_appended_markdown_precedes_smart_money(tmp_path,monkeypatch,mode):
    col,base,*_=setup(tmp_path)
    col.now=lambda:'2026-09-26T01:20:01+00:00'
    prior=reentry.attach(col,base)
    root=col.files['README.md']
    assert json.loads(col.files['current-state.json'])==prior
    assert not root.startswith(m.render_summary(prior).encode())
    if mode=='not_run':col.api.responses[sm.QUERY]={'total_count':0,'workflow_runs':[]}
    elif mode=='renderer_failure':
        def fail(*a,**k):raise ValueError('synthetic optional rendering failure')
        monkeypatch.setattr(view,'browser',fail)
    result=sm.attach(col,prior)
    assert result['lanes']==base['lanes']
    assert result['research']['asset_reentry']==prior['research']['asset_reentry']
    assert col.files['README.md'].startswith(root)
    assert json.loads(col.files['current-state.json'])==result
    assert result['research']['smart_money']['status']=={
        'ready':'READY','not_run':'NOT_RUN','renderer_failure':'OPTIONAL_PUBLICATION_GAP'}[mode]
    m.validate_read_package(result)


def test_canonical_json_binding_is_not_replaced_by_loose_markdown_match(tmp_path):
    col,base,*_=setup(tmp_path)
    col.files['current-state.json']=b'{}'
    with pytest.raises(ValueError,match='canonical composition binding'):
        sm.attach(col,base)
