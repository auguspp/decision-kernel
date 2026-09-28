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
from fixtures import MARKETS, NOW, R1, R2, REPO, fixture, raw

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


SCENES = [scene_read_and_copy, scene_search_and_late_preview, scene_bad_body,
          scene_new_reading_discards_old_detail, scene_markets_local_gap, scene_markets_read_failure]


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
                            if scene in (scene_search_and_late_preview, scene_markets_local_gap):
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
