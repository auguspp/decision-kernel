from pathlib import Path


def test_mineru_pdf_probe_is_manual_read_only_and_bounded() -> None:
    workflow = Path('.github/workflows/mineru-pdf-capability-probe.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in workflow
    assert 'schedule:' not in workflow
    assert 'pull_request:' not in workflow
    assert 'push:' not in workflow
    assert 'contents: read' in workflow and 'actions: read' in workflow
    assert 'persist-credentials: false' in workflow
    assert 'secrets.' not in workflow
    assert '10320565453' in workflow
    assert '25cda8a1d4afb4783432320239cd6271fe193cfdc5ed6dc2095a5deb833dce9c' in workflow
    assert 'mineru==4.0.2' in workflow
    assert '--tier", "basic"' not in workflow  # command is owned by the probe script, not shell text
    assert 'Research' not in workflow


def test_mineru_pdf_probe_script_keeps_authority_and_identity_explicit() -> None:
    source = Path('eval/mineru_pdf_probe.py').read_text(encoding='utf-8')
    assert 'MINERU_CAPABILITY_PROBE_DERIVED_REPRESENTATION_NOT_EVIDENCE' in source
    assert 'production_qualification' in source
    assert 'NOT_ESTABLISHED' in source
    assert source.count('investment_authority') >= 2
    assert 'research_authority' in source
    assert 'mineru_text_chars_excluding_embedded_images' in source
    assert 'data:image/' in source
    assert 'human_attention_authority' in source
    for value in (
        'cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa',
        '0aa7c59b58b74ff50924716b18b37c9c95a6e4b76dbb06b4afe4dada5a84dd3f',
        'cc65030bd9e676f5289d2bc2649eb7ff23b26a5b406b08b88cd20392d45df342',
    ):
        assert value in source
