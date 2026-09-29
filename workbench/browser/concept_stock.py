"""Scoped TEST_ONLY scenes using the original browser harness, reader and DOM.

No source data or executable remote input. Registered by smoke.py; original scenes
and transport/digest/layout checks are unchanged.
"""
import json
from playwright.sync_api import expect
from fixtures import NOW, R1, R2, raw, descriptor

STOCK = 'details/stock/1/reading/stock-reading.json'


def install(data, ref, day='2026-09-25'):
    root = json.loads(data.files[ref]['current-state.json'])
    saved = root['lanes']['stock']['last_qualified_result']
    coverage = dict(planned_issuers=3, dispositioned_issuers=3, price_path_checked_issuers=2,
                    qualified_issuers=1, conditions_not_met_issuers=1, unavailable_issuers=1)
    rows = []
    for i, d in enumerate(saved['dispositions']):
        code = '881125.TI' if i != 1 else '884243.TI'
        values = {'5': '0.1' if i == 0 else '-0.1',
                  '20': ('0.2' if ref == R1 else '0.12') if i == 0 else '0.31', '60': '0.03' if i == 0 else None}
        windows = {n: dict(base_session=start, end_session=day, usable_for_raw_comparison=True)
                   for n, start in [('5', '2026-09-18'), ('20', '2026-08-28'), ('60', '2026-07-03')]}
        rows.append(dict(thscode=d['thscode'], company_name=f'TEST_ONLY 比较{i} <script>window.fixtureInjected=true</script>',
            status=d['status'], excluded_reasons=['TEST_ONLY_5D_NOT_POSITIVE'] if i == 1 else [],
            input_failure={'reason_code': 'TEST_ONLY_DATA_GAP'} if i == 2 else None,
            current_origins=[dict(current_member_sectors=[code], sector_codes=[code], direction_sources=[dict(
                family='BROAD_881' if i != 1 else 'GRANULAR_884', thscode=code, name='TEST_ONLY 原行业')])],
            stock_path=None if i == 2 else dict(price_convention='RAW_UNADJUSTED_PRICE_PATH_NOT_TOTAL_RETURN', returns=values,
                input_checks=dict(history_window_checks=windows, action_window_checks=windows)),
            market_comparison={} if i == 2 else {n: None if v is None else dict(stock_return=v, benchmark_return='0', excess_return=v)
                                                for n, v in values.items()}))
    p = dict(market_session=day, observed_at=NOW, status='PARTIAL_STOCKS_FOR_SHADOW_READING',
        scope='BOUNDED_SURFACED_SECTOR_MARKET_EXPRESSION_NOT_ALL_A_SHARES',
        semantics='BOUNDED_MARKET_EXPRESSION_NOT_BUSINESS_BENEFIT_OR_RECOMMENDATION',
        reference_input_provenance='HITHINK_REQUEST_BOUND_RAW_OBSERVATION',
        policy={'version': 'stock-market-expression-window-qualified-v8'}, price_path_is_not_total_return=True,
        automatic_research_routing=False, creates_canonical_wake=False, coverage=coverage, all_stock_observations=rows,
        **{k: 'NONE' for k in ('research_authority', 'human_attention_authority', 'signal_transition_authority', 'investment_authority')})
    report = dict(projection=p, projection_hash=('8' if ref == R1 else '9') * 64)
    data.files[ref][STOCK] = raw(report)
    saved.update({k: p[k] for k in ('market_session', 'observed_at', 'status', 'scope', 'coverage')})
    saved.update(projection_hash=report['projection_hash'], details={'reading/stock-reading.json': descriptor(STOCK, data.files[ref][STOCK])})
    data.files[ref]['current-state.json'] = raw(root)


def scenes(tab, release_and_wait_for_native_digest, source_url):
    def selected(page, name='TEST_ONLY 概念甲 · 111111', *, refresh=True):
        # Install changes the declared input, not an already-open Reading.
        if refresh:
            page.get_by_role('button', name='读取最新保存结果', exact=True).click()
            expect(page.locator('#refresh')).to_be_enabled()
        tab(page, '市场观察')
        page.get_by_text('浏览全部概念与成员', exact=True).click()
        page.get_by_role('button', name=name, exact=True).click()
        return page.locator('.concept-stock-comparison')

    def scene_concept_stock_read(page, data):
        install(data, R1)
        panel = selected(page)
        expect(panel).to_contain_text('已保存检查 3/4 位 · 通过 1 · 条件未满足 1 · 不可判断 1 · 未检查 1')
        expect(panel).to_contain_text('不是全体成员排名')
        order = panel.locator('.human-material > button').all_text_contents()
        assert '600001.SH' in order[0] and '600000.SH' in order[1] and '600002.SH' in order[2]
        first = panel.locator('.human-material').first
        expect(first).to_contain_text('原条件未满足')
        expect(first).to_contain_text('20日收盘收益 31%')
        first.get_by_text('价格窗口与原发现来路', exact=True).click()
        expect(first).to_contain_text('5日 2026-09-18—2026-09-25：个股 −10%')
        expect(first).to_contain_text('60日：未取得可比较价格，保持未知')
        expect(first).to_contain_text('细分行业 TEST_ONLY 原行业 884243.TI')
        expect(first).to_contain_text('TEST_ONLY_5D_NOT_POSITIVE')
        assert page.evaluate('window.fixtureInjected === undefined')
        first.get_by_role('button').click()
        expect(page.locator('.human-company')).to_contain_text('合成公司01')
        return {'ordering': 'checked subset only; highest 20d remains conditions-not-met',
                'coverage': '3/4 checked; unavailable and unexamined separate', 'company': 'original company reader'}

    def scene_concept_stock_bad(page, data):
        install(data, R1)
        original = data.files[R1][STOCK]
        changed = original.replace(b'TEST_ONLY', b'FAKE_ONLY', 1)
        assert len(changed) == len(original) and changed != original
        url = source_url(R1, STOCK)
        data.overrides[url] = (changed, 200)
        panel = selected(page)
        expect(panel).to_contain_text('个股比较正文未取得或核验失败')
        panel.get_by_text('个股比较诊断', exact=True).click()
        expect(panel).to_contain_text('FILE_INTEGRITY_MISMATCH')
        expect(page.get_by_role('searchbox', name='搜索概念成员', exact=True)).to_be_visible()
        page.get_by_role('button', name='TEST_ONLY 概念乙 · 222222', exact=True).click()
        expect(page.locator('.concept-stock-comparison')).to_contain_text('个股比较正文未取得或核验失败')
        assert sum(r['url'] == url for r in data.requests) == 1
        expect(page.get_by_role('button', name='TEST_ONLY 个股保留', exact=True)).to_be_visible()
        expect(page.locator('td[data-label="事件 / 报告期"]')).to_have_count(3)
        return {'tamper': 'real Web Crypto rejection; no read retry', 'independent': 'members, stock and calendar preserved'}

    def scene_concept_stock_late_reading(page, data):
        install(data, R1)
        install(data, R2)
        url = source_url(R1, STOCK)
        data.hold.add(url)
        expect(selected(page)).to_contain_text('正在读取已保存的个股价格正文')
        data.ref = R2
        page.get_by_role('button', name='读取最新保存结果', exact=True).click()
        expect(page.locator('#refresh')).to_be_enabled()
        expect(page.locator('#identity')).to_contain_text(R2)
        panel = selected(page, refresh=False)
        expect(panel).to_contain_text('已保存检查 1/1 位')
        expect(panel).to_contain_text('20日收盘收益 12%')
        assert url in data.pending
        release_and_wait_for_native_digest(page, data, url)
        expect(panel).not_to_contain_text('已保存检查 3/4 位')
        expect(panel).not_to_contain_text('20日收盘收益 31%')
        expect(panel).to_contain_text('20日收盘收益 12%')
        return {'late_R': 'old read cannot replace new member comparison after native digest completion'}

    def scene_concept_stock_late_selection(page, data):
        install(data, R1)
        url = source_url(R1, STOCK)
        data.hold.add(url)
        expect(selected(page)).to_contain_text('正在读取已保存的个股价格正文')
        page.get_by_role('button', name='TEST_ONLY 概念乙 · 222222', exact=True).click()
        expect(page.get_by_role('heading', name='TEST_ONLY 概念乙 · 来源成员 2', exact=True)).to_be_visible()
        assert url in data.pending
        release_and_wait_for_native_digest(page, data, url)
        panel = page.locator('.concept-stock-comparison')
        expect(panel).to_contain_text('已保存检查 2/2 位')
        expect(panel).not_to_contain_text('已保存检查 3/4 位')
        assert sum(r['url'] == url for r in data.requests) == 1
        return {'late_selection': 'one read shared; detached prior concept never replaces selected concept'}

    def scene_concept_stock_dates(page, data):
        install(data, R1, day='2026-09-24')
        panel = selected(page)
        expect(panel).to_contain_text('成员日 2026-09-25；个股价格保存日 2026-09-24')
        expect(panel).to_contain_text('日期不同，仅作历史参考，不作同日成员排名')
        order = panel.locator('.human-material > button').all_text_contents()
        assert '600000.SH' in order[0] and '600001.SH' in order[1]
        return {'different_dates': 'historical values retained; comparison order not promoted'}

    def scene_concept_stock_legacy(page, data):
        panel = selected(page)
        expect(panel).to_contain_text('本版本未登记个股价格正文')
        assert not any('/details/stock/1/' in r['url'] for r in data.requests)
        expect(page.get_by_role('searchbox', name='搜索概念成员', exact=True)).to_be_visible()
        return {'legacy': 'no guessed file fetch; original members retained'}

    return [scene_concept_stock_read, scene_concept_stock_bad, scene_concept_stock_late_reading,
            scene_concept_stock_late_selection, scene_concept_stock_dates, scene_concept_stock_legacy]
