"""Exact integral source counts and immutable legacy replay; synthetic/offline."""
import json
import pytest

from decision_kernel.runtime import d_auction_probe as p
from test_d_auction_probe import capture, pool_row, sources, PRIOR, offline


@pytest.mark.parametrize('streak', [2, 2.0, '2', '2.000', '2e0'])
def test_integral_count_representations_from_json_are_not_missing(tmp_path, streak):
    report, root, _ = capture(tmp_path, prior_rows=[pool_row(streak=streak)])
    temperature = report['prior_temperature']
    assert report['version'] == p.VERSION and report['matched'] == 1
    assert temperature['maximum_consecutive'] == 2
    assert temperature['ladder_at_least_two'] == [{'symbol':'600001.SH','consecutive_limits':2}]
    assert not temperature['missing_streak_symbols']
    assert p.verify(root) == report
    assert '昨日来源池（2026-09-30）' in p.render(report)
    assert '不是今日情绪' in p.render(report)


@pytest.mark.parametrize('streak', [True, False, None, 0, -1, 2.5, '2.5', 'NaN', 'Infinity', [], {}])
def test_invalid_count_is_local_and_never_rounded_into_a_ladder(tmp_path, streak):
    report, _, _ = capture(tmp_path, prior_rows=[pool_row(streak=streak)])
    assert report['matched'] == report['comparable'] == 1
    assert report['prior_temperature']['maximum_consecutive'] is None
    assert report['prior_temperature']['missing_streak_symbols'] == ['600001.SH']


def test_equivalent_and_conflicting_duplicate_counts_are_separate_from_price(tmp_path):
    data = sources(prior_rows=[pool_row(streak=2),pool_row(streak='2.00')])
    _, temperature = p.prior_pool(data['limit_list_d'],p.saved.day(PRIOR))
    assert temperature['maximum_consecutive'] == 2 and not temperature['missing_streak_symbols']
    report, _, _ = capture(tmp_path,prior_rows=[pool_row(streak=2),pool_row(streak='3.00')])
    assert report['matched'] == 1 and report['cohort_denominator'] == 1
    assert report['prior_temperature']['maximum_consecutive'] is None


def legacy_files(files):
    """Synthetic v1 byte fixture, not a migration of production source records."""
    receipt = json.loads(files['receipt.json'])
    receipt['version'] = p.LEGACY_VERSION
    bodies = {name:files[name] for name in receipt['files']}
    old = p.build(receipt,bodies)
    files.update({'receipt.json':p.saved.dumps(receipt),'report.json':p.saved.dumps(old),
                  'summary.md':p.render(old).encode()})
    return old


def test_v1_exact_replay_and_labelled_new_count_reading_do_not_rewrite_history(tmp_path):
    _, root, _ = capture(tmp_path,prior_rows=[pool_row(streak=2.0)])
    files = {x.relative_to(root).as_posix():x.read_bytes() for x in root.rglob('*') if x.is_file()}
    old = legacy_files(files)
    for name,raw in files.items():(root/name).write_bytes(raw)
    assert old['prior_temperature']['missing_streak_symbols'] == ['600001.SH']
    assert p.verify(root) == old
    assert '昨日来源池（' not in p.render(old)
    qualified = p.verify(root,qualify_temperature=True)
    interpretation = qualified.pop('prior_temperature_qualification')
    assert qualified == old and interpretation['source_report_version'] == p.LEGACY_VERSION
    assert interpretation['source_report_sha256'] == p.sha256(files['report.json']).hexdigest()
    assert interpretation['source_response_sha256'] == p.sha256(files['raw/02-1.json']).hexdigest()
    assert interpretation['temperature']['maximum_consecutive'] == 2
    assert not interpretation['temperature']['missing_streak_symbols']
    assert {x.relative_to(root).as_posix():x.read_bytes() for x in root.rglob('*') if x.is_file()} == files
    (root/'raw/02-1.json').write_bytes(b'{}')
    with pytest.raises(ValueError):p.verify(root,qualify_temperature=True)
