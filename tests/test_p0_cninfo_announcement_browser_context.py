from __future__ import annotations

from decision_kernel.runtime import cninfo_http as cninfo


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return b'{"totalAnnouncement":0,"announcements":null}'


def test_cninfo_https_announcement_query_uses_disclosure_browser_context(monkeypatch) -> None:
    seen = []

    def fake_urlopen(request, timeout):
        seen.append((request, timeout))
        return _Response()

    monkeypatch.setattr(cninfo, "urlopen", fake_urlopen)
    payload = cninfo._request_json(
        url=cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL,
        method="POST",
        form={"stock": "600519,gssh0600519", "pageNum": "1"},
        timeout_seconds=3.0,
    )

    assert payload == {"totalAnnouncement": 0, "announcements": None}
    assert len(seen) == 1
    request, timeout = seen[0]
    assert timeout == 3.0
    assert request.full_url == "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    headers = {key.lower(): value for key, value in request.header_items()}
    assert headers["origin"] == "https://www.cninfo.com.cn"
    assert headers["referer"] == "https://www.cninfo.com.cn/new/disclosure"
    assert "AppleWebKit/605.1.15" in headers["user-agent"]
    assert headers["content-type"] == "application/x-www-form-urlencoded; charset=UTF-8"
    assert headers["x-requested-with"] == "XMLHttpRequest"
