"""Opt-in immutable Git blob cache for the original reading publisher.

Only a complete tree of the explicitly pinned previous reading proves presence.
This saves duplicate blob POSTs, never qualifies a source or moves the read ref.
"""
from __future__ import annotations

import base64

from . import current_state as model
from . import current_state_delivery as base


class GitHubReadReuseAPI(base.GitHubAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proven_read_blobs = frozenset()
        self.blob_reuse_hits = 0
        self.blob_reuse_origin = None

    def prime_previous_reading(self, commit):
        model.check(model.SHA.fullmatch(commit) is not None, 'exact prior reading commit required')
        if self.blob_reuse_origin is not None:
            model.check(self.blob_reuse_origin['commit'] == commit, 'prior reading reuse identity changed')
            return
        origin = self.get('git/commits/' + commit)
        model.check(origin.get('sha') == commit, 'prior reading commit identity differs')
        tree_sha = origin['tree']['sha']
        model.check(model.SHA.fullmatch(tree_sha) is not None, 'prior reading tree required')
        result = self.get('git/trees/' + tree_sha + '?recursive=1')
        model.check(result.get('sha') == tree_sha and result.get('truncated') is False
                    and isinstance(result.get('tree'), list), 'prior reading tree incomplete')
        blobs, paths = set(), set()
        for row in result['tree']:
            path = model.safe_path(row['path'])
            model.check(path not in paths and model.SHA.fullmatch(row['sha']) is not None,
                        'prior reading tree entry identity differs')
            paths.add(path)
            model.check((row['type'], row['mode']) in {
                ('tree', '040000'), ('blob', '100644'), ('blob', '100755')},
                'prior reading tree entry type differs')
            if row['type'] == 'blob':
                model.check(type(row.get('size')) is int and row['size'] >= 0,
                            'prior reading blob size invalid')
                blobs.add(row['sha'])
        # Publish the proof only after the ENTIRE immutable tree has qualified.
        self.proven_read_blobs = frozenset(blobs)
        self.blob_reuse_origin = {'commit': commit, 'tree': tree_sha, 'known_blobs': len(blobs)}

    def write(self, endpoint, body, method='POST'):
        if endpoint == 'git/blobs' and method == 'POST' and self.proven_read_blobs:
            # Exactly the native publisher's existing UTF-8/binary encoding path.
            if set(body) == {'content', 'encoding'} and body['encoding'] == 'base64':
                raw = base64.b64decode(body['content'], validate=True)
                blob = model.blob_sha(raw)
                if blob in self.proven_read_blobs:
                    self.blob_reuse_hits += 1
                    return {'sha': blob}  # Proven existing object, NOT a network write.
        return super().write(endpoint, body, method)


def pending_blob_writes(api, files):
    known = api.proven_read_blobs if isinstance(api, GitHubReadReuseAPI) else frozenset()
    # Repeated NEW values remain conservatively counted as separate POSTs.
    return sum(model.blob_sha(raw) not in known for raw in files.values())
