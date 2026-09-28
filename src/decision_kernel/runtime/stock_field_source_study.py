"""Legacy CNINFO query form retained for the current announcement probe.

The frozen stock-field collectors and CLI are retired under #626. Only
notice_query is still consumed by cninfo_announcement_probe; its exact form
and organization checks remain unchanged. See docs/stock-field-source-study.md.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

NOTICES = "https://www.cninfo.com.cn/new/hisAnnouncement/query"


def notice_query(code: str, stock_list: dict, day: date) -> dict:
    records = stock_list.get("stockList")
    if not isinstance(records, list):
        raise ValueError("CNINFO_STOCK_LIST_REQUIRED")
    matches = [row for row in records if isinstance(row, dict) and row.get("code") == code[:6]]
    if len(matches) != 1 or not isinstance(matches[0].get("orgId"), str) or not re.fullmatch(r"[A-Za-z0-9]+", matches[0]["orgId"]):
        raise ValueError("CNINFO_EXACT_ORGANIZATION_UNAVAILABLE")
    return {"id": "notice-query-" + code, "url": NOTICES, "method": "POST", "params": {
        "pageNum": "1", "pageSize": "30", "column": "szse", "tabName": "fulltext", "plate": "",
        "stock": code[:6] + "," + matches[0]["orgId"], "searchkey": "权益分派实施公告", "secid": "",
        "category": "", "trade": "", "seDate": (day - timedelta(days=20)).isoformat() + "~" + day.isoformat(),
        "sortName": "", "sortType": "", "isHLtitle": "false"}}


if __name__ == "__main__":
    raise SystemExit("FROZEN_STOCK_SOURCE_STUDY_RETIRED: use retained history; no capture is available")
