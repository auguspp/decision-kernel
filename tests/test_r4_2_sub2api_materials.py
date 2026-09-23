"""Complete saved-material loading regression; synthetic archive, no network."""
import pytest
from test_r4_2_sub2api_experiment import eval, once, pre, full_case, no_network


@pytest.mark.parametrize('size',[200000,900000])
def test_saved_archive_loader_uses_full_bound_and_serialized_prompt_identity(tmp_path,size):
    import io
    import zipfile
    from decision_kernel.runtime import reviewed_full_input as full
    p,d,ctx,bound=full_case(size)
    p=p.model_copy(update={'method_version':'research-funnel-v1','prompt_version':'test'})
    target=tmp_path/'old';target.mkdir()
    def call(stage,prompt,model,out,usage):return pre(prompt)
    candidate,checked,_=once.research(p,d,ctx,target,call=call,bound_context=bound)
    original=once.pre_prompt(p,d,ctx)
    material={'input.json':once.raw(p),'candidate.json':once.raw(candidate),
              'pre-model-input.json':once.raw(original),
              'quick-model-input.json':once.raw({'public_context':ctx}),'source.json':bound.stored_raw}
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in material.items():z.writestr(name,raw)
    archive=buf.getvalue()
    sample=dict(ticker=p.ticker,run_id=1,artifact_id=2,archive_sha256=once.sha(archive),
        input_sha256=once.sha(material['input.json']),candidate_hash=once.canonical_hash(candidate),
        context_sha256=once.sha(once.raw(ctx)),pages=[x['page_count'] for x in ctx['issuer_documents']])
    class FakeGit:
        def get(self,path):return {'workflow_run':{'id':1},'expired':False,'digest':'sha256:'+sample['archive_sha256']}
        def archive(self,artifact):return archive
        def file(self,path,ref):return bound.stored_raw
    p2,d2,ctx2=eval.load_sample(FakeGit(),sample,tmp_path/'restored')
    assert p2==p and d2==d and ctx2==ctx
    assert (tmp_path/'restored'/'original-source.json').read_bytes()==bound.stored_raw
