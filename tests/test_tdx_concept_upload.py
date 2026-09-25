"""The uploaded archive, not only the source workspace, must be replayable."""
from datetime import datetime, timezone
from pathlib import Path
import socket
import zipfile

import pytest

from decision_kernel.runtime import tdx_concept_snapshot as tdx
from test_tdx_concept_snapshot import DAY, SHA, WF, fake_source


@pytest.mark.parametrize("include_hidden", [True, False])
def test_capture_archive_fresh_directory_replay(tmp_path, monkeypatch, include_hidden):
    def forbidden(*args, **kwargs):
        raise AssertionError("no source calls during archive regression")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    captured = tmp_path / "captured"
    tdx.capture(captured, market_session=DAY, workflow=WF, expected_code=SHA,
                source_fn=fake_source,
                now=lambda: datetime(2026, 9, 25, 4, tzinfo=timezone.utc))
    original = tdx.replay(captured, expected_execution=WF)
    archive = tmp_path / "artifact.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for path in sorted(captured.rglob("*")):
            relative = path.relative_to(captured)
            if path.is_file() and (include_hidden or not any(p.startswith(".") for p in relative.parts)):
                z.writestr(relative.as_posix(), path.read_bytes())
    restored = tmp_path / "restored"
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        z.extractall(restored)  # This archive was constructed exclusively from our fixture above.
    if include_hidden:
        assert tdx.replay(restored, expected_execution=WF) == original
    else:
        assert not (restored / "source-files/.eltdx_board_cache.json").exists()
        with pytest.raises(ValueError, match="CAPTURE_FILES_REJECTED"):
            tdx.replay(restored, expected_execution=WF)


def test_upload_includes_required_hidden_metadata_only_from_source_output():
    text = (Path(__file__).resolve().parents[1] / ".github/workflows/tdx-concept-snapshot.yml").read_text()
    upload = text.split("uses: actions/upload-artifact@v7", 1)[1].split("      - name:", 1)[0]
    assert "include-hidden-files: true" in upload
    assert "path: ${{ runner.temp }}/tdx-concept/" in upload
    assert "secrets." not in text and "contents: write" not in text
