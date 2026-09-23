"""GitHub's encoding-none path uses the same pinned blob, not a URL fallback."""
import base64
from copy import deepcopy
import json
import socket
from types import SimpleNamespace

import pytest

from decision_kernel.runtime import current_state_delivery as delivery
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime.external_research_identity import MAX_READING_BYTES


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError("GitHub transport tests must be offline")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


def fixture(size):
    api = delivery.GitHubAPI("synthetic-not-a-credential")
    data = b"x" * size
    path, ref = "details/radar/industry-breadth.json", "a" * 40
    digest = once.blob(data)
    meta = {"type": "file", "path": path, "sha": digest, "size": size, "encoding": "none", "content": ""}
    blob = {"sha": digest, "size": size, "encoding": "base64",
            "content": base64.encodebytes(data).decode()}
    calls = []
    def response(method, endpoint, body=None):
        calls.append((method, endpoint))
        assert method == "GET" and body is None
        value = meta if endpoint == "contents/" + path + "?ref=" + ref else blob
        assert endpoint in {"contents/" + path + "?ref=" + ref, "git/blobs/" + digest}
        return SimpleNamespace(content=json.dumps(value).encode(), json=lambda: deepcopy(value))
    api._call = response  # Only HTTP replies; real get/file and byte validation run.
    return api, data, path, ref, meta, blob, calls


@pytest.mark.parametrize("size", [1048577, 4 * 1024 * 1024])
def test_large_pinned_read_and_repeated_read_reuse_exact_native_blob(size):
    api, raw, path, ref, meta, blob, calls = fixture(size)
    assert api.file(path, ref) == raw
    assert api.file(path, ref) == raw
    assert len(calls) == 2
    assert calls[1] == ("GET", "git/blobs/" + once.blob(raw))
    assert len(json.dumps(blob).encode()) < 8 * 1024 * 1024


@pytest.mark.parametrize("damage", ["size", "bool-size", "path", "sha", "inline-content", "symlink", "submodule",
    "blob-sha", "blob-size", "blob-encoding", "base64", "blob-bytes"])
def test_malformed_large_contents_or_blob_is_rejected_without_other_destinations(damage):
    api, raw, path, ref, meta, blob, calls = fixture(1048577)
    if damage == "size": meta["size"] = MAX_READING_BYTES + 1
    elif damage == "bool-size": meta["size"] = True
    elif damage == "path": meta["path"] = "other.json"
    elif damage == "sha": meta["sha"] = "../outside"
    elif damage == "inline-content": meta["content"] = "not empty"
    elif damage == "symlink": meta["target"] = "somewhere"
    elif damage == "submodule": meta["submodule_git_url"] = "https://invalid.example"
    elif damage == "blob-sha": blob["sha"] = "b" * 40
    elif damage == "blob-size": blob["size"] += 1
    elif damage == "blob-encoding": blob["encoding"] = "none"
    elif damage == "base64": blob["content"] += "!"
    else: blob["content"] = base64.b64encode(b"z" * len(raw)).decode()
    with pytest.raises((ValueError, TypeError)): api.file(path, ref)
    assert len(calls) <= 2


def test_original_small_inline_read_stays_single_request():
    api, raw, path, ref, meta, blob, calls = fixture(100)
    meta.update(encoding="base64", content=blob["content"])
    assert api.file(path, ref) == raw and len(calls) == 1
