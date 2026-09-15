from decision_kernel.runtime import cninfo_http as cninfo


def test_cninfo_org_search_uses_observed_http_contract_only() -> None:
    assert cninfo.CNINFO_STOCK_MAP_URL == (
        "http://www.cninfo.com.cn/new/information/topSearch/query"
    )
    assert cninfo.CNINFO_ORG_SEARCH_URL == cninfo.CNINFO_STOCK_MAP_URL
    assert cninfo.CNINFO_ANNOUNCEMENT_QUERY_URL == (
        "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    )
