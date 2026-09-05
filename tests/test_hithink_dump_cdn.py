from datetime import datetime, timezone

import pytest

from decision_kernel.runtime.hithink_dump_trial import DumpTrialError, signing_identity


NOW = datetime(2026, 9, 5, 9, tzinfo=timezone.utc)
PATH = "/fuyao-market-dump/prod/release/daily_k/a_share_daily_k_1d_none_10d/2026-09-04T10-00-00Z.parquet"


def envelope(url):
    return {"code": 0, "data": {"presigned_url": url, "presigned_url_expires_at": "2026-09-05T09:05:00Z"}}


@pytest.mark.parametrize("path", [PATH, "/different_release_layout/recent.parquet", "/storage-v2/daily_k/2026-09-04.parquet"])
def test_authenticated_service_selects_object_path_on_exact_origin_without_url_rewriting(path):
    # Synthetic alternative layouts are not claims about the live object's path.
    original = "https://o.thsi.cn" + path + "?X-Amz-Signature=synthetic-test-only"
    url, expiry, host = signing_identity(envelope(original), now=NOW)
    assert url == original
    assert host == "o.thsi.cn"
    assert expiry == datetime(2026, 9, 5, 9, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("url", [
    "https://o.thsi.cn.evil.invalid" + PATH + "?x=1",
    "https://other.o.thsi.cn" + PATH + "?x=1",
    "https://o.thsi.cn/fuyao-market-dump/../other/object.parquet?x=1",
    "https://o.thsi.cn/fuyao-market-dump/%2e%2e/object.parquet?x=1",
    "https://o.thsi.cn/fuyao-market-dump/\\other/object.parquet?x=1",
    "http://o.thsi.cn" + PATH + "?x=1",
    "https://credential@o.thsi.cn" + PATH + "?x=1",
    "https://o.thsi.cn:443" + PATH + "?x=1",
    "https://o.thsi.cn" + PATH + "?x=1#fragment",
    "https://o.thsi.cn" + PATH,
])
def test_cdn_configuration_does_not_authorize_other_origins_or_ambiguous_paths(url):
    with pytest.raises(DumpTrialError):
        signing_identity(envelope(url), now=NOW)
