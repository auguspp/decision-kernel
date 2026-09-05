import json
from datetime import datetime, timezone

import pytest

from decision_kernel.runtime.hithink_dump_trial import destination_diagnostics, signing_identity, DumpTrialError


KEY = "sensitive-credential"


def test_diagnostics_distinguish_namespace_port_and_path_without_usable_url():
    url = "https://o.thsi.cn:443/reviewed-namespace/release%3Afile.parquet?signature=" + KEY
    value = destination_diagnostics(url, credential=KEY)
    assert value["cdn_host_match"] and value["cdn_prefix_match"]
    assert value["port"] == 443 and value["path_has_percent_escape"]
    assert value["top_level_namespace"] == "reviewed-namespace"
    assert value["query_present"] and not value["userinfo_present"]
    encoded = json.dumps(value)
    for secret in (KEY, "signature", "release", "parquet", "https://"):
        assert secret not in encoded
    with pytest.raises(DumpTrialError):
        signing_identity({"code": 0, "data": {"presigned_url": url,
            "presigned_url_expires_at": "2026-09-05T10:00:00Z"}}, now=datetime(2026, 9, 5, 9, tzinfo=timezone.utc))


@pytest.mark.parametrize("url", [
    "https://" + KEY + "@o.thsi.cn/fuyao-market-dump/a?x=" + KEY,
    "https://o.thsi.cn/" + KEY + "/a?x=1",
    "https://o.thsi.cn/a%2fb/a?x=1",
    "https://o.thsi.cn:invalid/fuyao-market-dump/a?x=1",
    "https://o.thsi.cn/fuyao-market-dump/a?x=1#" + KEY,
])
def test_credential_userinfo_fragment_and_noncanonical_namespace_are_not_retained(url):
    value = destination_diagnostics(url, credential=KEY)
    encoded = json.dumps(value)
    assert KEY not in encoded
    assert url not in encoded
    assert "?x=" not in encoded
    assert all(isinstance(item, (str, bool, int)) or item is None for item in value.values())


def test_diagnostic_reports_do_not_relax_any_destination_requirement():
    url = "https://o.thsi.cn/fuyao-market-dump/a.parquet"
    value = destination_diagnostics(url, credential=KEY)
    assert value["cdn_host_match"] and value["cdn_prefix_match"]
    assert value["query_present"] is False
    with pytest.raises(DumpTrialError):
        signing_identity({"code": 0, "data": {"presigned_url": url,
            "presigned_url_expires_at": "2026-09-05T10:00:00Z"}}, now=datetime(2026, 9, 5, 9, tzinfo=timezone.utc))
