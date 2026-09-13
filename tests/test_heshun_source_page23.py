"""Bind the actually reviewed page note; no live PDF/model/Research execution.

Real artifact/PDF/render checks are recorded in the audit reading. The fake
commit below is only a unit-test source ref, never a production approval.
"""
import json
from pathlib import Path

from decision_kernel.runtime import disclosure_source_reading as reading
from decision_kernel.runtime import saved_research_once as once


PDF_SHA = "cc3a234f7551ef02c401fae60452b891ca48ef0047aad7e26981e0f4ec7948fa"
NOTE_SHA = "6c50058e86954f71f0e97692a1b5b55fe692e32a8d34e6b29041e6b1912dbe49"
ENGINE = {"library": "pypdfium2", "method": "get_text_bounded/strict",
          "pdfium": "149.0.7825.0", "version": "5.8.0"}
RENDER = {"crop": [0, 0, 0, 0], "draw_annots": True, "format": "RGB",
          "height": 1678, "width": 1180, "rotation": 0, "scale": 2,
          "pixels_sha256": "196d9e941525f37577039e27b81fed72354caa0f1afb2844f856940ef6177059"}


def test_actual_heshun_page23_note_uses_original_checked_visual_contract():
    path = reading.review_path(PDF_SHA, 23)
    data = (Path(__file__).resolve().parents[1] / path).read_bytes()
    note = json.loads(data)
    assert data == once.raw(note)
    assert len(data) == 1778 and once.sha(data) == NOTE_SHA
    spec = once.source_ref(path, "a" * 40, data, "REVIEWED_SOURCE_PAGE_NOT_PERMISSION")
    result = reading.checked_visual(note, spec, PDF_SHA, 23, ENGINE, RENDER)
    assert result["method"] == "AI_VISUAL_READING"
    assert result["page_number"] == 23
    assert result["review"] == note and result["review_source"] == spec
    assert len(note["unknowns"]) == 3
    assert "不认证" in result["text"]
    assert "实际签署" in note["unknowns"][1]
