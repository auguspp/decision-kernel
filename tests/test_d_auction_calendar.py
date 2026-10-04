"""Only required calendar dates gate this purpose; no historical-row filler."""
import json

from decision_kernel.runtime import d_auction_probe as p
from test_d_auction_probe import AT, TARGET, PRIOR, sources, fake_request, offline


def test_older_calendar_rows_are_not_an_extra_admission_gate(tmp_path):
    data=sources(); calendar=json.loads(data['trade_cal'])
    calendar['data']['items']=[r for r in calendar['data']['items'] if r[1] >= PRIOR]
    calendar['data']['has_more']=True
    data['trade_cal']=p.saved.dumps(calendar)
    result=p.capture(tmp_path/'partial-calendar',market_session=TARGET,observed_at=AT,
                     request=fake_request(data),clock=AT.isoformat)
    assert result['matched']==1 and result['calendar_scope']['truncated']


def test_gap_between_previous_and_target_session_is_not_inferred_closed(tmp_path):
    data=sources(); calendar=json.loads(data['trade_cal'])
    calendar['data']['items']=[r for r in calendar['data']['items'] if r[1]!='20261005']
    data['trade_cal']=p.saved.dumps(calendar); request=fake_request(data)
    result=p.capture(tmp_path/'missing-required-day',market_session=TARGET,observed_at=AT,
                     request=request,clock=AT.isoformat)
    assert result['status']=='CALENDAR_UNAVAILABLE' and len(request.calls)==1
