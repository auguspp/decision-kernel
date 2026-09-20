"""No source-content revision from fetch-clock or arithmetic-context changes."""
from copy import deepcopy
from decimal import localcontext, ROUND_FLOOR, Inexact

from decision_kernel.runtime import external_radar_observations as obs
from test_external_radar_observations import no_network, edit, news_pair, industry_inputs, CUTOFF, PERIOD


def test_version_identity_is_raw_content_not_later_clock_reinterpretation():
    pair = edit(news_pair(), lambda v: v['items'][0].update(pubDate='2026-09-20T03:05:00Z'))
    later = deepcopy(pair)
    later[1].update(requested_at='2026-09-20T03:10:00Z', received_at='2026-09-20T03:10:01Z')
    early_row = obs.news(*pair, cutoff=CUTOFF)['projection']['observations'][0]
    later_row = obs.news(*later, cutoff=CUTOFF)['projection']['observations'][0]
    assert early_row['publication_claims'] != later_row['publication_claims']
    assert early_row['version_id'] == later_row['version_id']
    forward = obs.news_context([pair, later], cutoff=CUTOFF)
    assert forward == obs.news_context([later, pair], cutoff=CUTOFF)
    assert len(forward['projection']['observations']) == 1
    assert forward['projection']['observations'][0]['publication_claims']['pubDate']['status'] == 'FUTURE_CLAIM'


def test_industry_arithmetic_does_not_inherit_callers_decimal_context():
    captures = industry_inputs()
    expected = obs.industry('LC', captures, **PERIOD)
    with localcontext() as ctx:
        ctx.prec = 6
        ctx.rounding = ROUND_FLOOR
        ctx.traps[Inexact] = True
        assert obs.industry('LC', captures, **PERIOD) == expected
