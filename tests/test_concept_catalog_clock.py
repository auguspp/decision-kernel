"""Catalog publication clocks are not same-session price-ready clocks."""
from datetime import timedelta
import pytest
from tests.test_concept_radar import Fixture, AT, ms, no_network
from decision_kernel.runtime import concept_radar as radar


@pytest.mark.parametrize('tag', ['cn_concept', 'industry'])
def test_catalog_clock_is_not_price_ready_time(tag):
    f = Fixture()
    def change(path, params, value):
        if path == radar.probe.CATALOG and params['tag'] == tag:
            value['data']['timestamp'] = ms(AT - timedelta(days=1))
        return value
    f.change = change
    assert f.run()['projection']['catalog_count'] == 4


@pytest.mark.parametrize('tag', ['cn_concept', 'industry'])
def test_future_catalog_clock_still_rejected(tag):
    f = Fixture()
    def change(path, params, value):
        if path == radar.probe.CATALOG and params['tag'] == tag:
            value['data']['timestamp'] = ms(AT + timedelta(days=1))
        return value
    f.change = change
    with pytest.raises(ValueError): f.run()
    assert not any(path == radar.probe.SNAPSHOT for path, _ in f.called)
