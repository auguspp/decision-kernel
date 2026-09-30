# 已选证券公告原文 · 单PDF标准通道

## 601155.SH｜PDF_RETAINED_TEXT_EXTRACTED

选择依据：b2-announcements-36675839340-1-601155-SH；明确公告ID：1225512314。
本次结束：2026-09-30T07:49:30.931963+00:00；原记录：receipt.json。
原件及提取结果（仅存在时）：source.pdf / extraction.json；精确定位与失败见下方。
```json
{
  "announcement": {
    "announcement_id": "1225512314",
    "announcement_type": null,
    "org_id": "GD012027",
    "source_announcement_time": "2026-08-27T00:00:00+08:00",
    "source_locator": "https://static.cninfo.com.cn/finalpage/2026-08-27/1225512314.PDF",
    "stock_code": "601155",
    "title": "新城控股2026年半年度报告摘要"
  },
  "extraction": {
    "bytes": 6616,
    "extracted_char_count": 2936,
    "page_count": 5,
    "path": "extraction.json",
    "pdf_sha256": "f2b6c09bbcb341039461bfa0be9b59a798a37b8740472585f7cdaed10f25d9ec",
    "representation": "ORIGINAL_PYPDF_NOT_TABLE_OR_EVENT_TRUTH",
    "retained": true,
    "sha256": "df51a58f25c4c92c2f46b901229ed2a53304708cdfcdffa796dd2e8b3df9fcf2",
    "source_locator": "https://static.cninfo.com.cn/finalpage/2026-08-27/1225512314.PDF",
    "status": "EXTRACTED",
    "text_sha256": "e21c7fbb4e19198fb2b2c78b1ed5f2f1425d3bef3d92bf9b1f02ea6461756566"
  },
  "failure": null,
  "getter_return": {
    "body_complete": true,
    "bytes": 152231,
    "http_status_basis": "EXISTING_GETTER_QUALIFICATION_NOT_RECORDED_HEADERS",
    "sha256": "f2b6c09bbcb341039461bfa0be9b59a798a37b8740472585f7cdaed10f25d9ec"
  },
  "http_status": 200,
  "pdf": {
    "body_complete": true,
    "bytes": 152231,
    "capture_manifest_sha256": "9c2e48f364cb2a7520b0518d183cf55cd2f5669c5fa105eef99b8f7144411b8e",
    "original_capture_path": "primary-bodies/objects/f2b6c09bbcb341039461bfa0be9b59a798a37b8740472585f7cdaed10f25d9ec.pdf",
    "path": "source.pdf",
    "sha256": "f2b6c09bbcb341039461bfa0be9b59a798a37b8740472585f7cdaed10f25d9ec",
    "source_locator": "https://static.cninfo.com.cn/finalpage/2026-08-27/1225512314.PDF"
  },
  "pdf_getter_invocations": 1,
  "source_status": "EXACT_SAVED_DIRECTORY_LOCATED"
}
```

原始字节先经原DisclosurePdfCapture保留，再逐字节复制到本平坦目录；capture-manifest.jsonl保持原清单，清单的objects路径属于原primary-bodies目录，不是本目录相对路径。
原件预算524288字节；不重查目录、不重试、重定向、换源或截断冒充完整PDF。
来源标题中的摘要仍是摘要，不是完整报告。source_announcement_time是公告目录时间，不是正文事件实施时间；取得/保留时间也不是公告时间。
EXTRACTED仅表示原pypdf文本提取完成；NO_TEXT不是空PDF，也不表示正文已读懂。人工/交互式正文阅读、表格语义与事件日期核对尚未执行，另行留存，不回写本捕获。
Git保管、用途登记、发布、固定R恢复及Human接受分别成立；没有研究、关注、持仓、Watch、提醒或投资执行。Investment Authority=NONE。
