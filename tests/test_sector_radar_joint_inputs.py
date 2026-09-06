from __future__ import annotations

import json
import shutil
import zipfile
from datetime import timedelta

import pytest

from decision_kernel.runtime.economic_release_inputs import load_release_inputs
from test_economic_release_inputs import accepted_case
from test_sector_radar_joint_delivery import case, NOW
from test_sector_radar_publication_gate import identity, inventory


def populated(tmp_path, monkeypatch):
    glue, build, root, run, state, temp, outcome = case(tmp_path, monkeypatch)
    # Real review/scanner code with synthetic HTTP bodies and blocked transport.
    # No actual public source or Human acceptance is created by this fixture.
    seed, reviews, _, _, accepted = accepted_case(tmp_path / 'review-fixture', monkeypatch)
    shutil.copyfile(seed, root / glue['SEED'])
    shutil.copytree(reviews, root / glue['REVIEWS'], dirs_exist_ok=True)
    return glue, build, root, run, state, temp, accepted


def test_nonempty_reviews_survive_copy_and_zip_without_rewriting_acceptance(tmp_path, monkeypatch):
    glue, build, root, run, state, temp, accepted = populated(tmp_path, monkeypatch)
    reviews = root / glue['REVIEWS']
    original = load_release_inputs(root / glue['SEED'], reviews, as_of=NOW)
    shutil.copytree(original.review_paths[0], reviews / 'second-directory-same-receipt')
    before = inventory(reviews)
    delivery = build()
    output = run / 'economic-company'
    resolved = json.loads((output / 'input-set.json').read_text())
    assert resolved['accepted_bundle_count'] == 1
    assert resolved['review_receipts'][0]['acceptance_hash'] == accepted['acceptance_hash']
    assert inventory(reviews) == before
    copied = tmp_path / 'downloaded-with-reviews'
    with zipfile.ZipFile(output / 'inputs.zip') as archive:
        for relative, raw in before.items():
            assert archive.read(glue['REVIEWS'] + '/' + relative) == raw
        archive.extractall(copied)  # Trusted archive produced above in this isolated test.
    rebuilt = load_release_inputs(copied / glue['SEED'], copied / glue['REVIEWS'], as_of=NOW)
    assert rebuilt.receipt == resolved
    assert rebuilt.receipt['review_receipts'][0]['eligible_from'] == accepted['eligible_from']
    assert delivery['event_ledger_hash'] == json.loads((run / 'publication-verification.json').read_text())['event_ledger_hash']
    assert not list(temp.iterdir())


def test_acceptance_after_input_cutoff_is_not_backfilled_into_a_page(tmp_path, monkeypatch):
    glue, _, root, run, state, temp, accepted = populated(tmp_path, monkeypatch)
    from datetime import datetime
    cutoff = datetime.fromisoformat(accepted['eligible_from'].replace('Z', '+00:00')) - timedelta(microseconds=1)
    before = inventory(root), inventory(run), inventory(state)
    with pytest.raises(ValueError):
        glue['build_delivery'](root, run, state, temp, identity=identity(), as_of=cutoff)
    assert before == (inventory(root), inventory(run), inventory(state))
    assert not list(temp.iterdir())
