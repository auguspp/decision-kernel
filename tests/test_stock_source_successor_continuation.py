from decision_kernel.runtime import cninfo_http
from decision_kernel.runtime import stock_source_successor as successor
from decision_kernel.runtime import stock_source_successor_continuation as continuation


def test_cninfo_runtime_exports_shanghai_timezone_for_successor_capture():
    assert cninfo_http.SHANGHAI_TZ is not None


def test_continuation_identity_is_distinct_and_fixed():
    for code in ("603353.SH", "300711.SZ"):
        old_eid, old_prefix = successor.execution(code)
        new_eid, new_prefix = continuation.execution(code)
        assert new_eid == old_eid.removesuffix("-source-successor-v1") + "-source-successor-continuation-v1"
        assert new_prefix != old_prefix
        assert new_prefix.endswith("source-successor-continuation-v1/")


def test_continuation_is_not_a_retry_flag_or_new_authority():
    assert continuation.MODE == "HUMAN_AUTHORIZED_STOCK_SOURCE_SUCCESSOR_TECHNICAL_CONTINUATION"
    assert continuation.TARGETS == successor.TARGETS == frozenset({"603353.SH", "300711.SZ"})
    assert continuation.REQUEST != successor.REQUEST
