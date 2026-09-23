"""Thin native-Git reading extension for the reviewed Industry consumer.

The original capture/publisher client remains byte-identical. Only the two
research entry points opt into this subclass; no SDK, provider or retry loop.
"""
from __future__ import annotations

import base64
import urllib.parse

from .current_state_delivery import GitHubAPI as OriginalGitHubAPI
from . import current_state as model
from .external_research_identity import MAX_READING_BYTES, INDUSTRY_ORIGIN_PATH


class GitHubAPI(OriginalGitHubAPI):
    def file(self, path: str, ref: str) -> bytes:
        if path != INDUSTRY_ORIGIN_PATH:
            return super().file(path, ref)
        model.safe_path(path)
        model.check(model.SHA.fullmatch(ref) is not None, "file reads require exact commit")
        data = self.get("contents/" + urllib.parse.quote(path, safe="/") + "?ref=" + ref)
        if data.get("type") != "file" or data.get("encoding") != "none":
            return super().file(path, ref)  # Original inline path; get is memoized.
        size, digest = data.get("size"), data.get("sha", "")
        model.check(type(size) is int and 0 < size <= MAX_READING_BYTES
                    and model.SHA.fullmatch(digest) is not None
                    and data.get("path") == path and data.get("content") == ""
                    and not data.get("submodule_git_url") and not data.get("target"),
                    "GitHub large file metadata invalid")
        blob = self.get("git/blobs/" + digest)
        model.check(blob.get("sha") == digest and type(blob.get("size")) is int
                    and blob["size"] == size and blob.get("encoding") == "base64",
                    "GitHub large file blob metadata differs")
        raw = base64.b64decode("".join(blob["content"].splitlines()), validate=True)
        model.check(len(raw) == size and model.blob_sha(raw) == digest,
                    "GitHub large file bytes differ")
        return raw
