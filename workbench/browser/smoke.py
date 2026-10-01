"""Actual Workbench in isolated Chromium. No server, credentials or live requests.

Run explicitly, never imported by the ordinary pytest suite. Native Playwright
routing supplies fixed inputs; all product JS, CSP and Web Crypto stay real.
Each scene runs once in a fresh context. Assertions wait for UI state, not retry
failed scenes. A failed scene keeps its original trace/screenshot/diagnostics.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

from playwright.sync_api import expect, sync_playwright
from fixtures import MARKETS, NOW, R1, R2, M, NL, REPO, descriptor, fixture, news_live_fixture, raw
from concept_stock import scenes as concept_stock_scenes

ORIGIN = 'http://127.0.0.1:4173'
API = f'https://api.github.com/repos/{REPO}'
RAW = f'https://raw.githubusercontent.com/{REPO}'
WORKBENCH = Path(__file__).resolve().parents[1]


def source_url(ref, path):
    return f'{RAW}/{ref}/{path}'


class Inputs:
    def __init__(self):
        self.ref = R1
        self.files = {ref: fixture(ref) for ref in (R1, R2)}
        self.files[NL] = news_live_fixture()
        self.overrides = {}
        self.hold = set()
        self.pending = {}
        self.requests, self.unexpected, self.responses = [], [], []

    def fulfil(self, route, body, status=200, content_type='application/json'):
        response_id = str(len(self.responses) + 1)
        self.responses.append({'id': response_id, 'url': route.request.url, 'status': status,
                               'bytes': len(body), 'body_sha256': hashlib.sha256(body).hexdigest()})
        route.fulfill(status=status, body=body, content_type=content_type,
                      headers={'Access-Control-Allow-Origin': '*', 'Cache-Control': 'no-store',
                               'Access-Control-Expose-Headers': 'X-AN2-Response', 'X-AN2-Response': response_id})

    def handle(self, route):
        request = route.request
        url = request.url
        self.requests.append({'method': request.method, 'url': url})
        try:
            if request.method != 'GET' or any(k in request.all_headers() for k in ('authorization', 'cookie')):
                raise ValueError('write or credential attempted')
            if url in self.hold:
                self.pending.setdefault(url, []).append(route)
                return
            if url in self.overrides:
                body, status = self.overrides[url]
                self.fulfil(route, body, status)
            elif url == ORIGIN + '/api/read-model/current-state':
                if request.headers.get('x-decision-kernel-intent') != 'read-model-ref':
                    raise ValueError('missing ref-read intent')
                self.fulfil(route, raw({'ref': 'read-model/current-state', 'commit': self.ref}))
            elif url == ORIGIN + '/api/read-model/news-live':
                if request.headers.get('x-decision-kernel-intent') != 'news-live-ref':
                    raise ValueError('missing news-live ref intent')
                self.fulfil(route, raw({'ref': 'read-model/news-live', 'commit': NL}))
            elif url.startswith(ORIGIN + '/workbench/'):
                name = url.removeprefix(ORIGIN + '/workbench/')
                allowed = {p.name: p for p in WORKBENCH.glob('*.mjs') if not p.name.endswith('.test.mjs')}
                allowed['index.html'] = WORKBENCH / 'index.html'
                if name not in allowed:
                    raise ValueError('undeclared static file')
                self.fulfil(route, allowed[name].read_bytes(), content_type=(
                    'text/html; charset=utf-8' if name == 'index.html' else 'text/javascript; charset=utf-8'))
            elif url == API + '/issues/575':
                self.fulfil(route, raw({'number': 575, 'comments': 0,
                    'html_url': f'https://github.com/{REPO}/issues/575'}))
            elif url == API + '/issues/575/comments?per_page=100&page=1':
                self.fulfil(route, b'[]')
            elif url == API + '/issues/581':
                self.fulfil(route, raw({'number': 581, 'title': 'TEST_ONLY health',
                    'body': 'TEST_ONLY independent health', 'updated_at': NOW,
                    'html_url': f'https://github.com/{REPO}/issues/581'}))
            else:
                prefix = RAW + '/'
                if not url.startswith(prefix):
                    raise ValueError('undeclared endpoint')
                ref, path = url.removeprefix(prefix).split('/', 1)
                self.fulfil(route, self.files[ref][path])
        except Exception as error:
            self.unexpected.append({'url': url, 'reason': str(error)})
            route.abort('blockedbyclient')

    def release(self, url):
        routes = self.pending.pop(url)
        self.hold.remove(url)
        ref, path = url.removeprefix(RAW + '/').split('/', 1)
        for route in routes:
            self.fulfil(route, self.files[ref][path])


# Observe completion only, never return an invented digest or change a rejection.
# This makes late-response assertions wait for actual native SHA completion,
# rather than pass before the delayed product promise has been processed.
DIGEST_OBSERVER = """(() => {
  window.__AN2_NATIVE_DIGESTS = [];
  const native = SubtleCrypto.prototype.digest;
  SubtleCrypto.prototype.digest = async function(...args) {
    const answer = await native.apply(this, args);
    window.__AN2_NATIVE_DIGESTS.push([...new Uint8Array(answer)]
      .map(b => b.toString(16).padStart(2, '0')).join(''));
    return answer;
  };
  // Chromium can report ERR_ABORTED after a no-store stream reached EOF.
  // Record actual consumer completion per unique fulfilled response, not URL.
  // No clone/tee, cache change, invented result or swallowed stream rejection.
  window.__AN2_CONSUMED = [];
  window.__AN2_FETCHES = [];
  const owners = new WeakMap(), originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const observation = {url: String(args[0]), status: null, id: null};
    window.__AN2_FETCHES.push(observation);
    const response = await originalFetch.apply(this, args);
    const id = response.headers.get('x-an2-response');
    Object.assign(observation, {id, status: response.status, url: response.url});
    if (id && response.body) owners.set(response.body, {id, chunks: []});
    return response;
  };
  const getReader = ReadableStream.prototype.getReader;
  ReadableStream.prototype.getReader = function(...args) {
    const reader = getReader.apply(this, args), owner = owners.get(this);
    if (owner) owners.set(reader, owner);
    return reader;
  };
  const read = ReadableStreamDefaultReader.prototype.read;
  ReadableStreamDefaultReader.prototype.read = async function(...args) {
    const result = await read.apply(this, args), owner = owners.get(this);
    if (owner) {
      if (!result.done) owner.chunks.push(new Uint8Array(result.value));
      else {
        owners.delete(this);
        const bytes = new Uint8Array(owner.chunks.reduce((n,c) => n+c.length, 0));
        let at = 0;
        for (const chunk of owner.chunks) { bytes.set(chunk, at); at += chunk.length; }
        native.call(crypto.subtle, 'SHA-256', bytes).then(hash =>
          window.__AN2_CONSUMED.push({id: owner.id, bytes: bytes.length,
            sha256: [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('')}));
      }
    }
    return result;
  };
})();"""


def release_and_wait_for_native_digest(page, data, url):
    ref, path = url.removeprefix(RAW + '/').split('/', 1)
    digest = hashlib.sha256(data.files[ref][path]).hexdigest()
    before = page.evaluate('(h) => window.__AN2_NATIVE_DIGESTS.filter(x => x === h).length', digest)
    data.release(url)
    page.wait_for_function('([h,n]) => window.__AN2_NATIVE_DIGESTS.filter(x => x === h).length > n',
                           arg=[digest, before])

def qualify_consumption(data, consumed, fetches, failures):
    """Check exact consumer evidence, including failures that arrived during cleanup.

    Successful Fetch bodies require actual EOF. Declared HTTP errors intentionally
    stop at their status; this must not be called successful body consumption.
    """
    by_id = {r['id']: r for r in data.responses}
    seen = {r['id']: r for r in fetches}
    assert len(seen) == len(fetches) and fetches, 'missing or duplicate Fetch response identity'
    complete = {r['id']: r for r in consumed}
    for observed in fetches:
        response = by_id.get(observed['id'])
        assert response and response['url'] == observed['url'] and response['status'] == observed['status'], observed
        if response['status'] == 200:
            body = complete.get(response['id'])
            assert body and body['bytes'] == response['bytes'] and body['sha256'] == response['body_sha256'], observed
        else:
            assert data.overrides.get(response['url'], (None, None))[1] == response['status'], observed
    explained = []
    for failure in failures:
        assert failure['failure'] == 'net::ERR_ABORTED', failure
        response = by_id.get(failure['response_id'])
        assert response and response['id'] in seen and response['url'] == failure['url'], failure
        explained.append({**failure, 'classification': (
            'STREAM_EOF_BYTES_SHA_MATCH_TERMINAL_EVENT_CONFLICT' if response['status'] == 200 else
            'DECLARED_HTTP_FAILURE_BODY_NOT_CONSUMED'), 'consumed': complete.get(response['id'])})
    return explained


def tab(page, name):
    page.get_by_role('navigation').get_by_role('button', name=name, exact=True).click()
    expect(page.locator('#heading')).to_have_text(name)


def book(page):
    tab(page, '研究')
    expect(page.get_by_role('searchbox', name='搜索公司研究')).to_be_visible()


def open_company(page, index=0):
    page.get_by_role('button', name=f'打开 合成公司{index:02d} 的研究与历史', exact=True).click()
    expect(page.locator('.human-company')).to_contain_text(f'合成公司{index:02d}')


def read_paper(page):
    page.locator('.human-company').get_by_role('button', name='阅读已有研究正文', exact=True).click()


def scene_read_and_copy(page, data):
    page.get_by_role('button', name='恢复这个事项', exact=True).first.click()
    expect(page.locator('.human-company')).to_be_visible()
    headings = page.locator('.human-material-group > h4').all_text_contents()
    assert headings == ['先看更正与方法限制', '已有研究与条件版本', '你的历史回应（不转移接受）']
    page.get_by_role('button', name='阅读方法补充与更正', exact=True).click()
    expect(page.locator('#detail')).to_contain_text('只适用于原版本')
    page.get_by_role('button', name='阅读你的历史回应', exact=True).click()
    expect(page.locator('#detail')).to_contain_text('仅针对原版本，不是新接受')
    read_paper(page)
    expect(page.locator('#detail')).to_contain_text('合成正文 0')
    assert page.evaluate('window.fixtureInjected === undefined')
    page.get_by_text('原件与技术校验', exact=True).click()
    expect(page.locator('#detail')).to_contain_text('原件已核对字节与 SHA-256')
    href = page.locator('#detail').get_by_role('link', name='固定版本原件', exact=True).get_attribute('href')
    assert f'/blob/{R1}/sources/paper-0.md' in href
    page.get_by_role('button', name='复制事项接续（未写回）', exact=True).click()
    expect(page.get_by_role('button', name='已复制；尚未回应或写回', exact=True)).to_be_visible()
    copied = page.evaluate('navigator.clipboard.readText()')
    assert R1 in copied and '2' * 64 in copied and '新的回应尚未提供' in copied
    assert '/sources/response.md' in copied and '不自动Full' in copied
    tab(page, '注意力')
    expect(page.locator('#content')).to_contain_text('明确待你回应（1）')
    return {'groups': headings, 'clipboard': 'exact-R/request/history; no write'}


def scene_search_and_late_preview(page, data):
    url = source_url(R1, 'sources/paper-0.md')
    data.hold.add(url)
    book(page)
    expect(page.get_by_role('button', name='下一页', exact=True)).to_be_visible()
    page.get_by_role('button', name='下一页', exact=True).click()
    expect(page.get_by_role('button', name='打开 合成公司10 的研究与历史', exact=True)).to_be_visible()
    search = page.get_by_role('searchbox', name='搜索公司研究')
    search.fill('合成公司01')
    expect(page.get_by_role('button', name='打开 合成公司00 的研究与历史', exact=True)).to_have_count(0)
    search.fill('合成公司')
    open_company(page, 1)
    read_paper(page)
    expect(page.locator('#detail')).to_contain_text('合成正文 1')
    assert url in data.pending
    release_and_wait_for_native_digest(page, data, url)
    expect(page.locator('#detail')).to_contain_text('合成正文 1')
    expect(page.locator('#detail')).not_to_contain_text('合成正文 0')
    expect(page.locator('.human-company')).to_contain_text('合成公司01')
    page.get_by_text('切换研究对象', exact=True).click()
    expect(search).to_have_value('合成公司')
    return {'pagination': '12 companies / 2 pages', 'late_preview': 'does not replace chosen body'}


def scene_bad_body(page, data):
    book(page)
    open_company(page)
    url = source_url(R1, 'sources/paper-0.md')
    original = data.files[R1]['sources/paper-0.md']
    # Equal byte count: a digest failure must not be mistaken for just a size check.
    data.overrides[url] = (original.replace(b'TEST_ONLY', b'FAKE_ONLY'), 200)
    read_paper(page)
    expect(page.locator('#detail h3')).to_have_text('原件未取得或核验失败')
    page.locator('#detail').get_by_text('技术诊断', exact=True).click()
    expect(page.locator('#detail')).to_contain_text('FILE_INTEGRITY_MISMATCH')
    expect(page.locator('#detail')).not_to_contain_text('合成正文 0')
    tab(page, '注意力')
    expect(page.locator('#content')).to_contain_text('明确待你回应（1）')
    return {'equal_length_tamper': 'rejected by real Web Crypto', 'independent_request': 'preserved'}


def scene_new_reading_discards_old_detail(page, data):
    book(page)
    open_company(page)
    url = source_url(R1, 'sources/paper-0.md')
    data.hold.add(url)
    read_paper(page)
    expect(page.locator('#detail')).to_contain_text('正在读取已保存原件')
    data.ref = R2
    page.get_by_role('button', name='读取最新保存结果', exact=True).click()
    expect(page.locator('#refresh')).to_be_enabled()
    expect(page.locator('#identity')).to_contain_text(R2)
    book(page)
    open_company(page, 1)
    read_paper(page)
    expect(page.locator('#detail')).to_contain_text(R2)
    assert url in data.pending
    release_and_wait_for_native_digest(page, data, url)
    expect(page.locator('#detail')).to_contain_text('合成正文 1')
    expect(page.locator('#detail')).not_to_contain_text(R1)
    return {'cross_R': 'late R1 body cannot overwrite selected R2'}



def scene_news_live(page, data):
    tab(page, '新闻')
    expect(page.get_by_role('heading', name='新闻 · 滚动更新', exact=True)).to_be_visible()
    expect(page.locator('#content')).to_contain_text('TEST_ONLY 滚动新闻 <script>window.fixtureInjected=true</script>')
    expect(page.locator('#content')).to_contain_text('News live R：' + NL)
    expect(page.locator('#content')).to_contain_text('滚动历史仍在建立')
    assert page.evaluate('window.fixtureInjected === undefined')
    assert any(r['url'] == ORIGIN + '/api/read-model/news-live' for r in data.requests)
    assert all(r['method'] == 'GET' for r in data.requests)
    return {'news_live':'exact independent R', 'latest_capture':'visible', 'source_script':'inert text'}


def scene_news_live_gap(page, data):
    data.overrides[ORIGIN + '/api/read-model/news-live'] = (raw({'code':'TEST_ONLY_GAP'}), 503)
    tab(page, '新闻')
    expect(page.get_by_role('heading', name='新闻 · 低频保存快照', exact=True)).to_be_visible()
    expect(page.locator('#content')).to_contain_text('滚动新闻本次未取得或核验失败')
    expect(page.locator('#content')).to_contain_text('新闻窗口本次不可读，不代表没有新闻')
    return {'live_gap':'explicit', 'fallback':'current-state snapshot path preserved, no quiet inference'}

def scene_markets_local_gap(page, data):
    tab(page, '市场观察')
    expect(page.locator('#content')).to_contain_text('101 点')
    expect(page.locator('#content')).to_contain_text('没有已核验的可读批次；不作无变化判断')
    expect(page.get_by_role('button', name='TEST_ONLY 个股保留', exact=True)).to_be_visible()
    assert page.locator('td[data-label="对象"]').count() == 6
    return {'market_rows': 6, 'other_families': 'explicit gaps, not zero', 'stock': 'preserved'}


def scene_markets_read_failure(page, data):
    data.overrides[source_url(R1, MARKETS)] = (b'TEST_ONLY failure', 503)
    tab(page, '市场观察')
    expect(page.locator('#content')).to_contain_text('全球市场资料未能读完')
    expect(page.get_by_role('button', name='TEST_ONLY 个股保留', exact=True)).to_be_visible()
    expect(page.locator('#content')).not_to_contain_text('101 点')
    return {'HTTP_503': 'local panel failure; stock remains'}


def calendar_path(data, ref):
    return json.loads(data.files[ref]['current-state.json'])['research']['calendar']['files']['calendar.json']['read_path']


def scene_calendar_read(page, data):
    tab(page, '市场观察')
    expect(page.locator('td[data-label="事件 / 报告期"]')).to_have_count(3)
    expect(page.locator('#content')).to_contain_text('2026-10-02T08:30:00-04:00')
    expect(page.locator('#content')).to_contain_text('2026-10-02T20:30:00+08:00')
    expect(page.locator('#content')).to_contain_text('预约；实际发布未检查')
    page.get_by_text('日历依据与原件', exact=True).click()
    page.get_by_role('button', name='阅读日历核读摘录', exact=True).click()
    expect(page.locator('#detail')).to_contain_text('Employment Situation for September 2026')
    assert page.evaluate('window.fixtureInjected === undefined')
    return {'appointments':3, 'original_and_local_clocks':'visible', 'same_R_excerpt':'read', 'source_script':'inert text'}


def scene_calendar_bad_body(page, data):
    path = calendar_path(data, R1)
    original = data.files[R1][path]
    corrupted = original.replace(b'20:30', b'21:30', 1)
    assert len(corrupted) == len(original) and corrupted != original
    data.overrides[source_url(R1, path)] = (corrupted, 200)
    tab(page, '市场观察')
    expect(page.locator('#content')).to_contain_text('日历正文未能读完')
    expect(page.locator('td[data-label="事件 / 报告期"]')).to_have_count(0)
    page.get_by_text('日历读取诊断', exact=True).click()
    expect(page.locator('#content')).to_contain_text('FILE_INTEGRITY_MISMATCH')
    expect(page.get_by_role('button', name='TEST_ONLY 个股保留', exact=True)).to_be_visible()
    expect(page.locator('#content')).to_contain_text('101 点')
    return {'calendar_equal_length_tamper':'native digest rejected', 'other_markets':'preserved'}


def scene_calendar_late_read(page, data):
    url = source_url(R1, calendar_path(data, R1))
    data.hold.add(url)
    tab(page, '市场观察')
    expect(page.locator('#content')).to_contain_text('正在读取固定版本日历')
    data.ref = R2
    page.get_by_role('button', name='读取最新保存结果', exact=True).click()
    expect(page.locator('#refresh')).to_be_enabled()
    expect(page.locator('#identity')).to_contain_text(R2)
    expect(page.locator('td[data-label="事件 / 报告期"]')).to_have_count(1)
    assert url in data.pending
    release_and_wait_for_native_digest(page, data, url)
    expect(page.locator('td[data-label="事件 / 报告期"]')).to_have_count(1)
    expect(page.locator('#content')).not_to_contain_text('美国消费者价格指数')
    return {'late_R1_three_rows':'cannot replace R2 one-row scope'}


def scene_calendar_legacy_reading(page, data):
    legacy = json.loads(data.files[R2]['current-state.json'])
    del legacy['research']['calendar']
    data.files[R2]['current-state.json'] = raw(legacy)
    data.ref = R2
    page.get_by_role('button', name='读取最新保存结果', exact=True).click()
    expect(page.locator('#refresh')).to_be_enabled()
    expect(page.locator('#identity')).to_contain_text(R2)
    tab(page, '市场观察')
    expect(page.locator('#content')).to_contain_text('本读取尚未接入研究日历')
    expect(page.get_by_role('button', name='TEST_ONLY 个股保留', exact=True)).to_be_visible()
    assert not any(r['url'].endswith('/calendar.json') for r in data.requests)
    return {'legacy_R_without_calendar':'explicit absence, no calendar fetch, stock preserved'}



def scene_concepts_read(page, data):
    tab(page, '市场观察')
    panel = page.get_by_role('heading', name='概念与成员', exact=True).locator('..')
    expect(panel).to_contain_text('完整可用概念 3 项')
    page.get_by_text('浏览全部概念与成员', exact=True).click()
    search = page.get_by_role('searchbox', name='搜索概念', exact=True)
    expect(panel).to_contain_text('持续强化')
    expect(panel).to_contain_text('弱化或退出')
    expect(panel).to_contain_text('阶段未知')
    search.fill('概念甲')
    expect(page.get_by_role('button', name='TEST_ONLY 概念乙 · 222222', exact=True)).to_have_count(0)
    page.get_by_role('button', name='TEST_ONLY 概念甲 · 111111', exact=True).click()
    expect(panel).to_contain_text('来源成员 4')
    expect(panel).to_contain_text('至少 106 个已返回交易日')
    # Inspect the selected concept's original numbers, not only its phase label.
    panel.get_by_text('多周期依据', exact=True).last.click()
    expect(panel).to_contain_text('60日：指数 3% · 沪深300 1% · 超额 2%')
    expect(panel).to_contain_text('通过原价格观察（2026-09-25）')
    expect(panel).to_contain_text('原条件未满足（2026-09-25）')
    expect(panel).to_contain_text('数据不可用，未作条件否决（2026-09-25）')
    expect(panel).to_contain_text('不在本次已保存个股检查范围')
    page.get_by_text('与其他概念共享的成员', exact=True).click()
    expect(panel).to_contain_text('共享 2 位 · 本概念 2/4 · 对方 2/2')
    expect(panel).to_contain_text('对方成员全部包含于本概念')
    page.get_by_role('searchbox', name='搜索概念成员', exact=True).fill('600000')
    expect(page.get_by_role('button', name='TEST_ONLY 成员乙 · 600001.SH', exact=True)).to_have_count(0)
    assert page.evaluate('window.fixtureInjected === undefined')
    page.get_by_role('button', name='TEST_ONLY 成员甲 <script>window.fixtureInjected=true</script> · 600000.SH', exact=True).click()
    expect(page.locator('.human-company')).to_contain_text('合成公司00')
    read_paper(page)
    expect(page.locator('#detail')).to_contain_text('合成正文 0')
    assert page.evaluate('window.fixtureInjected === undefined')
    tab(page, '市场观察')
    page.get_by_text('浏览全部概念与成员', exact=True).click()
    page.get_by_role('searchbox', name='搜索概念', exact=True).fill('概念甲')
    page.get_by_role('button', name='TEST_ONLY 概念甲 · 111111', exact=True).click()
    page.get_by_text('与其他概念共享的成员', exact=True).click()
    expect(page.locator('#content')).to_contain_text('共享 2 位 · 本概念 2/4 · 对方 2/2')
    return {'concept_catalog': 'all three, searchable', 'members': 'four distinct Stock states',
            'overlap': '2/4 and 2/2; identities not merged', 'company': 'existing same-R research reader', 'source_script': 'inert'}


def scene_concepts_bad_members(page, data):
    path = 'details/radar/tdx-concept/membership.json'
    original = data.files[R1][path]
    changed = original.replace(b'TEST_ONLY', b'FAKE_ONLY', 1)
    assert len(changed) == len(original) and changed != original
    data.overrides[source_url(R1, path)] = (changed, 200)
    tab(page, '市场观察')
    expect(page.locator('#content')).to_contain_text('成员资料未能取得或通过校验')
    expect(page.locator('#content')).to_contain_text('完整可用概念 3 项')
    page.get_by_text('浏览全部概念与成员', exact=True).click()
    expect(page.get_by_role('button', name='TEST_ONLY 概念甲 · 111111', exact=True)).to_be_disabled()
    page.get_by_text('成员读取诊断', exact=True).click()
    expect(page.locator('#content')).to_contain_text('FILE_INTEGRITY_MISMATCH')
    expect(page.get_by_role('button', name='TEST_ONLY 个股保留', exact=True)).to_be_visible()
    expect(page.locator('td[data-label="事件 / 报告期"]')).to_have_count(3)
    return {'equal_length_member_tamper': 'native digest rejected', 'concept_quotes_calendar_stock': 'preserved'}


def scene_concepts_late_members(page, data):
    url = source_url(R1, 'details/radar/tdx-concept/membership.json')
    data.hold.add(url)
    tab(page, '市场观察')
    expect(page.locator('#content')).to_contain_text('正在读取保存的概念与成员')
    data.ref = R2
    page.get_by_role('button', name='读取最新保存结果', exact=True).click()
    expect(page.locator('#refresh')).to_be_enabled()
    expect(page.locator('#identity')).to_contain_text(R2)
    expect(page.locator('#content')).to_contain_text('4 条关系')
    page.get_by_text('浏览全部概念与成员', exact=True).click()
    page.get_by_role('button', name='TEST_ONLY 概念甲 · 111111', exact=True).click()
    expect(page.get_by_role('heading', name='TEST_ONLY 概念甲 · 来源成员 1', exact=True)).to_be_visible()
    assert url in data.pending
    release_and_wait_for_native_digest(page, data, url)
    expect(page.get_by_role('heading', name='TEST_ONLY 概念甲 · 来源成员 1', exact=True)).to_be_visible()
    expect(page.locator('#content')).not_to_contain_text('7 条关系')
    return {'late_R1_members': 'cannot replace R2 catalogue or chosen member detail'}



def scene_concepts_bad_trend(page, data):
    path = 'details/radar/tdx-concept/trend/trend.json'
    original = data.files[R1][path]
    changed = original.replace(b'TEST_ONLY', b'FAKE_ONLY', 1)
    assert len(changed) == len(original) and changed != original
    data.overrides[source_url(R1, path)] = (changed, 200)
    tab(page, '市场观察')
    panel = page.get_by_role('heading', name='概念与成员', exact=True).locator('..')
    expect(panel).to_contain_text('本版本没有可读的20／60日相对走势')
    page.get_by_text('浏览全部概念与成员', exact=True).click()
    page.get_by_role('button', name='TEST_ONLY 概念甲 · 111111', exact=True).click()
    expect(panel).to_contain_text('来源成员 4')
    expect(panel).to_contain_text('通过原价格观察（2026-09-25）')
    page.get_by_text('长期走势读取诊断', exact=True).click()
    expect(panel).to_contain_text('FILE_INTEGRITY_MISMATCH')
    return {'long_history_tamper':'native digest rejected; original quotes and members preserved'}


def scene_concepts_late_trend(page, data):
    url = source_url(R1, 'details/radar/tdx-concept/trend/trend.json')
    data.hold.add(url)
    tab(page, '市场观察')
    expect(page.locator('#content')).to_contain_text('正在读取保存的概念与成员')
    data.ref = R2
    page.get_by_role('button', name='读取最新保存结果', exact=True).click()
    expect(page.locator('#refresh')).to_be_enabled()
    expect(page.locator('#identity')).to_contain_text(R2)
    page.get_by_text('浏览全部概念与成员', exact=True).click()
    expect(page.locator('#content')).to_contain_text('强中分歧')
    assert url in data.pending
    release_and_wait_for_native_digest(page, data, url)
    expect(page.locator('#content')).not_to_contain_text('持续强化')
    expect(page.locator('#content')).to_contain_text('强中分歧')
    return {'old_R_trend':'cannot overwrite new R phase after native digest completes'}


def scene_concepts_legacy_trend(page, data):
    for ref in (R1,R2):
        payload = json.loads(data.files[ref]['current-state.json'])
        del payload['research']['tdx_concept_context']['trend']
        data.files[ref]['current-state.json'] = raw(payload)
    data.ref = R2
    page.get_by_role('button', name='读取最新保存结果', exact=True).click()
    expect(page.locator('#refresh')).to_be_enabled()
    expect(page.locator('#identity')).to_contain_text(R2)
    tab(page, '市场观察')
    expect(page.locator('#content')).to_contain_text('本版本没有可读的20／60日相对走势')
    page.get_by_text('浏览全部概念与成员', exact=True).click()
    page.get_by_role('button', name='TEST_ONLY 概念甲 · 111111', exact=True).click()
    expect(page.locator('#content')).to_contain_text('来源成员 1')
    assert not any('/trend/' in r['url'] for r in data.requests)
    return {'legacy_R':'explicit long-history absence, no invented trend fetch; members readable'}

def agenda_input(data, ref, label):
    """TEST_ONLY display input, never a live review or Human follow declaration."""
    body = (f'# TEST_ONLY {label}\n\n保存窗口：2026-09-28至2026-10-31。\n\n'
        '## 公司预约（原件待复核）\n\n10:00；检索正文不是完整公告。明确关注不是持仓。\n\n'
        '## 原研究复核条件\n\n时间未知，不补午夜；本记录不自动执行研究。\n\n'
        '## 依据与读取范围\n\n<script>window.fixtureInjected=true</script>\n').encode()
    source = descriptor('docs/readings/test-agenda.md', body)
    path = 'sources/git/' + source['git_blob'] + '/test-agenda.md'
    source.update(read_path=path, repository=REPO, ref=M)
    root = json.loads(data.files[ref]['current-state.json'])
    root['research']['records'] = [{'id':'research-agenda', 'case':'navigation', 'use':'NAVIGATION_ONLY',
        'qualification':'EXPLICIT_PURPOSE_REFERENCE_NOT_AUTOMATIC_SUPERSESSION', 'source':source}]
    data.files[ref][path] = body
    data.files[ref]['current-state.json'] = raw(root)
    return path


def agenda_refresh(page, data, ref):
    data.ref = ref
    page.get_by_role('button', name='读取最新保存结果', exact=True).click()
    expect(page.locator('#refresh')).to_be_enabled()
    expect(page.locator('#identity')).to_contain_text(ref)
    tab(page, '市场观察')


def scene_agenda_read(page, data):
    path = agenda_input(data, R2, '近期计划')
    agenda_refresh(page, data, R2)
    expect(page.get_by_role('heading', name='TEST_ONLY 近期计划', exact=True)).to_be_visible()
    expect(page.locator('#content')).to_contain_text('原件待复核')
    expect(page.locator('#content')).to_contain_text('时间未知，不补午夜')
    page.get_by_text('依据与读取范围', exact=True).first.click()
    assert page.evaluate('window.fixtureInjected === undefined')
    page.get_by_role('button', name='阅读近期列表原稿', exact=True).click()
    expect(page.locator('#detail')).to_contain_text('TEST_ONLY 近期计划')
    assert any(r['url'] == source_url(R2, path) for r in data.requests)
    expect(page.get_by_role('button', name='TEST_ONLY 个股保留', exact=True)).to_be_visible()
    return {'agenda':'same-R human text and original read', 'limits':'visible', 'source_script':'inert'}


def scene_agenda_bad_body(page, data):
    path = agenda_input(data, R2, '近期计划')
    body = data.files[R2][path]
    changed = body.replace(b'10:00', b'11:00')
    assert changed != body and len(changed) == len(body)
    data.overrides[source_url(R2, path)] = (changed, 200)
    agenda_refresh(page, data, R2)
    expect(page.locator('#content')).to_contain_text('近期列表未能读完')
    expect(page.locator('td[data-label="事件 / 报告期"]')).to_have_count(1)
    expect(page.get_by_role('button', name='TEST_ONLY 个股保留', exact=True)).to_be_visible()
    page.get_by_text('近期列表读取诊断', exact=True).click()
    expect(page.locator('#content')).to_contain_text('FILE_INTEGRITY_MISMATCH')
    return {'equal_length_tamper':'native SHA rejected', 'original_BLS_and_stock':'preserved'}


def scene_agenda_late_read(page, data):
    first = agenda_input(data, R1, '旧计划')
    agenda_input(data, R2, '新计划')
    url = source_url(R1, first)
    data.hold.add(url)
    agenda_refresh(page, data, R1)
    expect(page.locator('#content')).to_contain_text('正在读取已保存的近期列表')
    agenda_refresh(page, data, R2)
    expect(page.get_by_role('heading', name='TEST_ONLY 新计划', exact=True)).to_be_visible()
    assert url in data.pending
    release_and_wait_for_native_digest(page, data, url)
    expect(page.locator('#content')).not_to_contain_text('TEST_ONLY 旧计划')
    return {'late_old_agenda':'cannot overwrite new R after actual native digest'}


SCENES = [scene_read_and_copy, scene_search_and_late_preview, scene_bad_body,
          scene_new_reading_discards_old_detail, scene_markets_local_gap, scene_markets_read_failure,
          scene_calendar_read, scene_calendar_bad_body, scene_calendar_late_read, scene_calendar_legacy_reading,
          scene_concepts_read, scene_concepts_bad_members, scene_concepts_late_members,
          scene_concepts_bad_trend, scene_concepts_late_trend, scene_concepts_legacy_trend,
          scene_agenda_read, scene_agenda_bad_body, scene_agenda_late_read]


SCENES += concept_stock_scenes(tab, release_and_wait_for_native_digest, source_url)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New evidence directory (must not exist)')
    parser.add_argument('--chromium', type=Path, help='Explicit existing Chromium binary; default uses Playwright-installed browser')
    args = parser.parse_args()
    if not __debug__:
        raise RuntimeError('Assertions must be enabled; do not use python -O')
    if args.chromium and not args.chromium.is_file():
        parser.error('--chromium must name an existing executable')
    if args.output.resolve().is_relative_to(WORKBENCH):
        parser.error('--output must be outside workbench/')
    args.output.mkdir(parents=True, exist_ok=False)
    sources = {p.relative_to(WORKBENCH).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in WORKBENCH.rglob('*') if p.is_file() and p.suffix in {'.mjs', '.html', '.py', '.txt'}}
    git = subprocess.run(['git', '-C', str(WORKBENCH), 'rev-parse', 'HEAD'],
                         capture_output=True, text=True, timeout=10)
    report = {'git_head': git.stdout.strip() if git.returncode == 0 else None,
              'browser_executable_requested': str(args.chromium) if args.chromium else 'PLAYWRIGHT_MANAGED',
              'scope': 'TEST_ONLY_ISOLATED_WORKBENCH_NOT_SITES_OR_HUMAN_ACCEPTANCE',
              'playwright': version('playwright'), 'source_sha256': sources,
              'fixture_sha256': {ref: hashlib.sha256(raw({k: hashlib.sha256(v).hexdigest()
                  for k, v in fixture(ref).items()})).hexdigest() for ref in (R1, R2)},
              'attempts_per_scene': 1, 'scenes': []}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=str(args.chromium) if args.chromium else None)
            report['chromium'] = browser.version
            try:
                for label, viewport in [('desktop', {'width': 1360, 'height': 900}),
                                         ('narrow', {'width': 390, 'height': 844})]:
                    for scene in SCENES:
                        name = label + '-' + scene.__name__.removeprefix('scene_')
                        start = time.monotonic()
                        result = {'name': name, 'viewport': viewport, 'status': 'FAIL'}
                        data = Inputs()
                        context = browser.new_context(viewport=viewport, locale='zh-CN', timezone_id='Asia/Shanghai',
                            service_workers='block', offline=True)
                        context.grant_permissions(['clipboard-read', 'clipboard-write'], origin=ORIGIN)
                        context.route('**/*', data.handle)
                        context.add_init_script(DIGEST_OBSERVER)
                        context.tracing.start(screenshots=True, snapshots=True, sources=False)
                        page = context.new_page()
                        page.set_default_timeout(7000)
                        errors, console, failed = [], [], []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        page.on('console', lambda m: console.append({'type': m.type, 'text': m.text}))
                        response_ids = {}
                        page.on('response', lambda r: response_ids.update({r.request: r.headers.get('x-an2-response')}))
                        page.on('requestfailed', lambda r: failed.append({'url': r.url, 'failure': r.failure,
                            'response_id': response_ids.get(r)}))
                        try:
                            page.goto(ORIGIN + '/workbench/index.html')
                            expect(page.locator('#refresh')).to_be_enabled()
                            expect(page.locator('#identity')).to_contain_text(R1)
                            assert page.evaluate('isSecureContext && typeof crypto.subtle.digest === "function"')
                            result['assertions'] = scene(page, data)
                            assert not data.pending, 'unreleased response'
                            assert not data.unexpected, data.unexpected
                            assert not errors, errors
                            # Wait for actual Fetch consumption, not networkidle: the
                            # reader rightly does not consume an HTTP 503 error body.
                            page.wait_for_function("""() => window.__AN2_FETCHES.length > 0 &&
                              window.__AN2_FETCHES.every(f => f.status !== null &&
                                (f.status !== 200 || window.__AN2_CONSUMED.some(c => c.id === f.id)))""")
                            qualify_consumption(data, page.evaluate('window.__AN2_CONSUMED'),
                                                page.evaluate('window.__AN2_FETCHES'), failed)
                            unexpected_console = [m for m in console if m['type'] == 'error' and
                                not (scene is scene_markets_read_failure and '503' in m['text'])]
                            assert not unexpected_console, unexpected_console
                            # Responsive evidence is a viewport check, not physical-phone acceptance.
                            result['layout'] = page.evaluate('({scroll: document.documentElement.scrollWidth, viewport: innerWidth})')
                            assert result['layout']['scroll'] <= result['layout']['viewport'] + 1
                            if scene in (scene_search_and_late_preview, scene_markets_local_gap, scene_calendar_read, scene_concepts_read, scene_agenda_read) or scene.__name__ in ('scene_concept_stock_dates', 'scene_concept_stock_late_selection'):
                                page.screenshot(path=str(args.output / f'{name}.png'), full_page=True)
                            result['status'] = 'PASS'
                        except Exception:
                            result['error'] = traceback.format_exc()
                            try:
                                page.screenshot(path=str(args.output / f'{name}-failure.png'), full_page=True)
                            except Exception as error:
                                result['screenshot_error'] = str(error)
                        finally:
                            result.update(responses=data.responses, seconds=round(time.monotonic() - start, 3), requests=data.requests,
                                unexpected=data.unexpected, page_errors=errors, console=console, request_failures=failed,
                                pending_routes=list(data.pending),
                                consumed_streams=page.evaluate('window.__AN2_CONSUMED || []'),
                                fetches=page.evaluate('window.__AN2_FETCHES || []'))
                            trace = args.output / f'{name}-failure-trace.zip' if result['status'] == 'FAIL' else None
                            context.tracing.stop(path=str(trace) if trace else None)
                            context.close()
                            if result['status'] == 'PASS':
                                try:
                                    assert not data.unexpected and not errors
                                    result['terminal_event_diagnostics'] = qualify_consumption(
                                        data, result['consumed_streams'], result['fetches'], failed)
                                except Exception:
                                    result['status'] = 'FAIL'
                                    result['error'] = traceback.format_exc()
                            report['scenes'].append(result)
                            print(name, result['status'], flush=True)
                        if 'ERR_BLOCKED_BY_ADMINISTRATOR' in result.get('error', ''):
                            raise RuntimeError('Managed browser refused this environment; stop without changing policy or origin')
            finally:
                browser.close()
    except Exception:
        report['environment_error'] = traceback.format_exc()
    report['status'] = 'PASS' if len(report['scenes']) == 2 * len(SCENES) and all(r['status'] == 'PASS' for r in report['scenes']) else 'FAIL'
    (args.output / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
