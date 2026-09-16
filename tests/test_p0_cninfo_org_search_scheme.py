from decision_kernel.runtime import cninfo_http as cninfo


def test_cninfo_identity_and_announcement_metadata_use_reviewed_http_routes_only() -> None:
    assert cninfo.CNINFO_STOCK_MAP_URL == (
        "http://www.cninfo.com.cn/new/information/topSearch/query"
    )
    assert cninfo.CNINFO_ORG_SEARCH_URL == cninfo.CNINFO_STOCK_MAP_URL
    assert cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL == (
        "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    )
    assert cninfo.CNINFO_ANNOUNCEMENT_HTTPS_URL == (
        "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    )
    assert cninfo.CNINFO_DISCLOSURE_STOCK_URL == (
        "http://www.cninfo.com.cn/new/disclosure/stock"
    )
