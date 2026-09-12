"""Prior saved execution records must not be replayed as a new launch."""
import pytest

from test_prepared_disclosure_research import Case, no_network, prepared


@pytest.mark.parametrize("name", ["candidate.json", "candidate-before-validation.json", "receipt.json",
                                 "validation.json", "funnel.json", "host-receipt.json", "failure.json",
                                 "admission.json"])
def test_older_attempt_without_new_launch_marker_cannot_spend_again(tmp_path, monkeypatch, name):
    c=Case(monkeypatch)
    c.values[c.heads[prepared.work.WORK_REF],c.prefix+name]=b'{"historical":"keep unchanged"}'
    result=c.run(tmp_path/"run")
    assert result["status"]=="ALREADY_ATTEMPTED_NO_EXECUTION"
    assert not c.calls and not c.writes
