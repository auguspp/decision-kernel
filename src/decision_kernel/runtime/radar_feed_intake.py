"""Native NBS RSS windows and append-only seen versions; never fact acceptance.

feedparser owns RSS/Atom parsing. Only retained bytes enter it (no URL fetching).
First-seen feed representations are not new publications or independent evidence.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape
from importlib.metadata import version
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener
from uuid import NAMESPACE_URL, uuid5

import feedparser
from bs4 import BeautifulSoup

from decision_kernel.evidence import EvidenceArtifact
from decision_kernel.identity import canonical_hash, canonical_json
from .economic_source_capture import PublicResponse, _NoRedirect, _safe_headers, _body_integrity
from .theme_radar_probe import _clock, _keys, _safe_path, _read, _unique_object, AUTHORITY
from .theme_source_discovery import MAX_SOURCES, MAX_TEXT_CHARS, MAX_TOTAL_CHARS

VERSION = 'nbs-native-feed-seen-versions-v0'
FEEDPARSER_VERSION = '6.0.14'
FEEDS = {'nbs-releases': 'https://www.stats.gov.cn/sj/zxfb/rss.xml',
         'nbs-interpretations': 'https://www.stats.gov.cn/sj/sjjd/rss.xml'}
POLICY_HASH = canonical_hash({'version': VERSION, 'feeds': FEEDS, 'feedparser': FEEDPARSER_VERSION})
MAX_BODY = 2 * 1024 * 1024
MAX_ITEMS, MAX_VERSIONS, MAX_TEXT = 128, 4096, 65536
SEMANTICS = 'FEED_REPRESENTATIONS_NOT_ARTICLE_ACCEPTANCE_OR_MARKET_SIGNALS'
LINK = re.compile(r'https?://www\.stats\.gov\.cn/sj/(?:zxfb|sjjd)/[0-9]{6}/t[0-9]{8}_[0-9]+\.html')


def data(value):
    return (canonical_json(value) + '\n').encode('utf-8')


def digest(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def decode(raw):
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object)
    canonical_json(value)
    return value


def _sealed(value, field):
    return json.loads(canonical_json({**value, field: canonical_hash(value)}))


def _string(value, maximum=MAX_TEXT):
    if not isinstance(value, str) or len(value) > maximum or '\x00' in value:
        raise ValueError('invalid or over-budget feed string; no truncation')
    return value


def publication_clock(raw):
    """Do not inherit feedparser's lenient date-only/invalid-date corrections."""
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', raw):
            return datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if re.fullmatch(r'(?:[A-Z][a-z]{2}, )?\d{1,2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} (?:GMT|UT|UTC|[+-]\d{4})', raw):
            stamp = parsedate_to_datetime(raw)
            if stamp.tzinfo is not None and (',' not in raw or stamp.strftime('%a') == raw[:3]):
                return stamp
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def parse_window(raw, feed_id):
    if feed_id not in FEEDS or not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BODY:
        raise ValueError('unknown feed or body size outside budget')
    if version('feedparser') != FEEDPARSER_VERSION:
        raise ValueError('parser version differs; separately review parser migration')
    # Conservative preflight, including UTF-16/32 spellings. Never fetch entities.
    if re.search(br'<!\s*(?:DOCTYPE|ENTITY)\b', raw.replace(b'\x00', b''), re.I):
        raise ValueError('DTD/entity declarations are not accepted')
    parsed = feedparser.parse(io.BytesIO(raw), sanitize_html=False, resolve_relative_uris=False)
    if parsed.get('bozo', 1) or parsed.get('version') not in {'rss20', 'rss10', 'atom10'}:
        raise ValueError('not a well-formed supported RSS/Atom document; no loose recovery')
    entries = parsed.get('entries', [])
    if len(entries) > MAX_ITEMS:
        raise ValueError('feed item budget exceeded; no first-N truncation')
    rows, ids, total = [], {}, 0
    for entry in entries:
        # This source profile reads title/description/dates, not linked articles,
        # content:encoded bodies, enclosure files, author or inferred origin.
        entry = dict(entry)
        link = _string(entry.get('link', ''), 2048)
        if not LINK.fullmatch(link):
            raise ValueError('feed item link is outside the exact NBS source profile')
        identity = _string(entry.get('id', ''), 2048)
        if identity and identity in ids and ids[identity] != link:
            raise ValueError('same feed ID points to conflicting links')
        if identity:
            ids[identity] = link
        title = _string(entry.get('title', ''))
        if not title.strip():
            raise ValueError('feed entry lacks a title')
        payload = {'title': title, 'title_type': _string(entry.get('title_detail', {}).get('type', 'text/plain'), 64),
                   'summary': _string(entry.get('summary', '')),
                   'summary_type': _string(entry.get('summary_detail', {}).get('type', 'text/plain'), 64),
                   'published_raw': _string(entry.get('published', ''), 256),
                   'updated_raw': _string(entry.get('updated', ''), 256)}
        total += len(title) + len(payload['summary'])
        if total > 256 * 1024:
            raise ValueError('aggregate feed text budget exceeded')
        document = canonical_hash({'publisher': 'NBS', 'url': link})
        version_hash = canonical_hash({'document_key': document, 'payload': payload})
        rows.append({'feed_id': feed_id, 'entry_id': identity, 'url': link, 'document_key': document,
                     'payload': payload, 'version_hash': version_hash})
    return {'feed_id': feed_id, 'format': parsed['version'], 'raw': digest(raw), 'entries': rows}


def validate_registry(value):
    _keys(value, {'version', 'policy_hash', 'initialized_at', 'recorded_at', 'parent_registry_hash', 'versions', 'registry_hash'})
    if (value['version'] != VERSION or value['policy_hash'] != POLICY_HASH
            or canonical_hash({k:v for k,v in value.items() if k != 'registry_hash'}) != value['registry_hash']):
        raise ValueError('registry identity or parser/source policy differs')
    created, recorded = _clock(value['initialized_at']), _clock(value['recorded_at'])
    if created > recorded or not isinstance(value['versions'], list) or len(value['versions']) > MAX_VERSIONS:
        raise ValueError('registry clock/size invalid')
    parent = value['parent_registry_hash']
    if parent is not None and not re.fullmatch('[0-9a-f]{64}', parent):
        raise ValueError('invalid registry parent')
    seen, aliases = set(), {}
    for item in value['versions']:
        _keys(item, {'url', 'document_key', 'payload', 'version_hash', 'first_received_at', 'first_recorded_at', 'appearances'})
        doc = canonical_hash({'publisher': 'NBS', 'url': item['url']})
        if (not LINK.fullmatch(item['url']) or doc != item['document_key']
                or canonical_hash({'document_key': doc, 'payload': item['payload']}) != item['version_hash']
                or item['version_hash'] in seen):
            raise ValueError('invalid or duplicate registered version')
        seen.add(item['version_hash'])
        _keys(item['payload'], {'title','title_type','summary','summary_type','published_raw','updated_raw'})
        for key, text in item['payload'].items():
            _string(text, 64 if key.endswith('_type') else 256 if key.endswith('_raw') else MAX_TEXT)
        if not item['payload']['title'].strip(): raise ValueError('stored title is empty')
        if _clock(item['first_recorded_at']) < created: raise ValueError('version predates registry baseline')
        if not _clock(item['first_received_at']) <= _clock(item['first_recorded_at']) <= recorded:
            raise ValueError('registered first-seen clocks are invalid')
        if not isinstance(item['appearances'], list) or not item['appearances']:
            raise ValueError('registered source appearances missing')
        for appearance in item['appearances']:
            _keys(appearance, {'feed_id', 'entry_id'})
            if appearance['feed_id'] not in FEEDS:
                raise ValueError('registered feed identity unknown')
            _string(appearance['entry_id'], 2048)
            alias = (appearance['feed_id'], appearance['entry_id'])
            if alias[1] and alias in aliases and aliases[alias] != item['url']:
                raise ValueError('conflicting registered feed identifier')
            aliases[alias] = item['url']
        if len({canonical_hash(a) for a in item['appearances']}) != len(item['appearances']):
            raise ValueError('duplicate registered appearance')
    return value


def advance(windows, *, recorded_at, previous=None, bootstrap=False):
    recorded = _clock(recorded_at)
    if type(bootstrap) is not bool or (previous is None) != bootstrap:
        raise ValueError('supply exact previous registry OR explicitly initialize a separate baseline')
    if set(windows) != set(FEEDS):
        raise ValueError('both declared feeds required; no partial-state advancement')
    old = validate_registry(previous) if previous is not None else None
    if old and _clock(old['recorded_at']) >= min(_clock(w['requested_at']) for w in windows.values()):
        raise ValueError('previous registry must precede this acquisition')
    versions = {v['version_hash']: copy.deepcopy(v) for v in old['versions']} if old else {}
    before = set(versions)
    known_documents = {v['document_key'] for v in versions.values()}
    aliases = {(a['feed_id'], a['entry_id']): v['url'] for v in versions.values()
               for a in v['appearances'] if a['entry_id']}
    snapshots, occurrence_count, current = [], 0, set()
    for feed_id in sorted(FEEDS):
        window = windows[feed_id]
        requested, received = _clock(window['requested_at']), _clock(window['received_at'])
        if not requested <= received <= recorded:
            raise ValueError('feed clocks outside capture/recording boundary')
        parsed = parse_window(window['raw'], feed_id)
        snapshots.append({k:v for k,v in parsed.items() if k != 'entries'})
        for row in parsed['entries']:
            occurrence_count += 1
            alias = (feed_id, row['entry_id'])
            if row['entry_id'] and alias in aliases and aliases[alias] != row['url']:
                raise ValueError('feed identifier rebound to another link; no silent identity substitution')
            aliases[alias] = row['url']
            key = row['version_hash']; current.add(key)
            if key not in versions:
                versions[key] = {k:copy.deepcopy(row[k]) for k in ('url','document_key','payload','version_hash')}
                versions[key].update(first_received_at=received.isoformat(), first_recorded_at=recorded.isoformat(), appearances=[])
            appearance = {'feed_id': feed_id, 'entry_id': row['entry_id']}
            if appearance not in versions[key]['appearances']:
                versions[key]['appearances'].append(appearance)
                versions[key]['appearances'].sort(key=lambda a:(a['feed_id'], a['entry_id']))
    if len(versions) > MAX_VERSIONS:
        raise ValueError('registry full; explicit checkpoint/migration required, never prune history')
    registry = _sealed({'version': VERSION, 'policy_hash': POLICY_HASH,
        'initialized_at': old['initialized_at'] if old else recorded.isoformat(), 'recorded_at': recorded.isoformat(),
        'parent_registry_hash': old['registry_hash'] if old else None,
        'versions': [versions[k] for k in sorted(versions)]}, 'registry_hash')
    validate_registry(registry)
    if len(data(registry)) > 6*1024*1024: raise ValueError('registry byte budget exhausted; explicit checkpoint/migration required')
    new = sorted(current - before)
    by_document = {}
    for key in sorted(current): by_document.setdefault(versions[key]['url'], []).append(key)
    conflicts = {url:keys for url,keys in by_document.items() if len(keys)>1}
    changes = [{'version_hash': key, 'kind': 'BASELINE_ONLY' if bootstrap else
                'CHANGED_FEED_REPRESENTATION' if versions[key]['document_key'] in known_documents else 'FIRST_SEEN_LINK'} for key in new]
    delta = _sealed({'version': VERSION, 'semantics': SEMANTICS, 'registry_hash': registry['registry_hash'],
        'status': 'INITIAL_BASELINE_ONLY' if bootstrap else 'NEW_FEED_VERSIONS' if new else 'NO_NEW_FEED_VERSIONS',
        'feed_windows': snapshots, 'current_version_hashes': sorted(current), 'changes': changes, 'multiple_current_representations': conflicts,
        'feed_occurrences': occurrence_count, 'current_unique_versions': len(current),
        'duplicate_occurrences': occurrence_count - len(current), 'previously_seen_current_versions': len(current & before),
        'stored_versions': len(versions), 'coverage': 'TWO_ROLLING_FEED_WINDOWS_NOT_COMPLETE_PUBLISHER_HISTORY',
        'article_revision_verified': False, 'independent_source_count': None, **AUTHORITY}, 'delta_hash')
    return registry, delta


def source_rows(registry, delta):
    """New, usable descriptions only; every gap blocks the whole downstream batch."""
    validate_registry(registry)
    if (delta['registry_hash'] != registry['registry_hash']
            or canonical_hash({k:v for k,v in delta.items() if k != 'delta_hash'}) != delta['delta_hash']):
        raise ValueError('source export delta differs')
    if delta['status'] == 'INITIAL_BASELINE_ONLY':
        return {'status': 'BASELINE_NOT_FORWARDED', 'sources': [], 'gaps': []}
    wanted = {c['version_hash'] for c in delta['changes']}
    if not wanted <= {v['version_hash'] for v in registry['versions']}: raise ValueError('delta references missing version')
    rows, gaps = [], []
    if delta['multiple_current_representations']:
        gaps.append({'reason':'MULTIPLE_CURRENT_REPRESENTATIONS_REQUIRE_REVIEW','links':delta['multiple_current_representations']})
    for item in registry['versions']:
        if item['version_hash'] not in wanted:
            continue
        p = item['payload']; published = publication_clock(p['published_raw'])
        received = _clock(item['first_received_at'])
        text = p['summary']
        if p['summary_type'] in {'text/html', 'application/xhtml+xml'}:
            soup = BeautifulSoup(text, 'html.parser')
            for node in soup(['script','style','template','noscript']): node.decompose()
            text = soup.get_text(' ', strip=True)
        reason = ('PUBLISHED_TIME_NOT_QUALIFIED' if published is None else
                  'FUTURE_PUBLICATION_CLAIM' if published > received else
                  'NO_BOUNDED_SUMMARY_TEXT' if not text.strip() or len(text) > MAX_TEXT_CHARS else
                  'UNSUPPORTED_TEXT_TYPE' if p['summary_type'] not in {'text/plain','text/html','application/xhtml+xml'} else None)
        if reason:
            gaps.append({'version_hash': item['version_hash'], 'reason': reason}); continue
        ev = EvidenceArtifact(id=uuid5(NAMESPACE_URL, 'nbs-feed:' + item['version_hash']),
            source_type='OFFICIAL_FEED_DESCRIPTION', source_identifier='NBS-RSS:' + item['document_key'],
            source_locator=item['url'], published_at=published, available_at=received, retrieved_at=received,
            content_hash=item['version_hash'], idempotency_key='NBS-RSS:' + item['version_hash'],
            retention_mode='EXTRACTED_VALUES', replayability_level='PARTIAL', permitted_excerpt=text,
            source_location='Publisher RSS description, not linked article; original XML retained in capture bundle',
            license_terms_note='First received is conservative availability. Library-projected feed description; no article/full-text, fact acceptance, Human review or independent-source claim.')
        rows.append({'recorded_at': item['first_recorded_at'], 'evidence': ev.model_dump(mode='json'),
                     'text_fields': [['permitted_excerpt']]})
    if len(wanted) > MAX_SOURCES:
        gaps.append({'reason': 'DOWNSTREAM_SOURCE_BUDGET_EXCEEDED', 'count': len(wanted)})
    if sum(len(r['evidence']['permitted_excerpt']) for r in rows) > MAX_TOTAL_CHARS:
        gaps.append({'reason':'DOWNSTREAM_TEXT_BUDGET_EXCEEDED'})
    if gaps:
        return {'status': 'SOURCE_EXPORT_BLOCKED', 'sources': [], 'gaps': gaps}
    return {'status': 'READY_RETAINED_DESCRIPTIONS' if rows else 'NO_NEW_SOURCE_ROWS', 'sources': rows, 'gaps': []}


def render(registry, delta, exports):
    by_id = {v['version_hash']:v for v in registry['versions']}
    e = lambda x: escape(str(x), quote=True)
    parts = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">',
        '<title>雷达原生来源窗口</title><style>body{font:16px/1.7 system-ui;max-width:980px;margin:auto;padding:20px}section{border-top:1px solid;padding:14px 0}pre,p,summary,a{white-space:pre-wrap;overflow-wrap:anywhere}</style><main>',
        '<h1>国家统计局 · 来源接入窗口</h1><p>SHADOW OBSERVATION ONLY · Human / Research / Investment authority = NONE</p>',
        f'<p>状态：{e(delta["status"])}；接入记录时间：{e(registry["recorded_at"])}</p>',
        '<p>第一次看到不等于刚刚发布。同链接的描述变化不等于正文修订。首次采集只建立基线，不回填前瞻线索；不同链接也不自动视为独立来源。这里只覆盖两个 RSS 窗口，没有获取文章正文、行情或创建 Research。</p>',
        f'<p>本窗口条目 {delta["feed_occurrences"]}；去重版本 {delta["current_unique_versions"]}；重复出现 {delta["duplicate_occurrences"]}；历史累计版本 {delta["stored_versions"]}；下游输入状态 {e(exports["status"])}</p>']
    change = {x['version_hash']:x['kind'] for x in delta['changes']}
    for key in delta['current_version_hashes']:
        item = by_id[key]; p = item['payload']
        parts.append(f'<section><h2>{e(p["title"])}</h2><p>{e(change.get(key,"PREVIOUSLY_SEEN"))}</p><p>来源日期原文：{e(p["published_raw"] or "未提供")}；更新原文：{e(p["updated_raw"] or "未提供")}<br>首次实际收到：{e(item["first_received_at"])}</p><a href="{e(item["url"])}">发布者链接（本文未抓取）</a><details><summary>RSS 描述与完整版本记录</summary><pre>{e(canonical_json(item))}</pre></details></section>')
    parts.append(f'<details><summary>完整差异、覆盖限制与导出缺口</summary><pre>{e(canonical_json({"delta":delta,"export":exports}))}</pre></details></main></html>')
    return ''.join(parts)


def check_response(response, feed_id):
    headers = _safe_headers(response.headers)
    _body_integrity(response.body, headers)
    if (type(response.status) is not int or response.status != 200 or response.url != FEEDS[feed_id]
            or len(response.body)>MAX_BODY
            or headers.get('content-encoding', 'identity').lower() not in {'','identity'}
            or headers.get('content-type','').split(';')[0].lower() not in {'application/rss+xml','application/atom+xml','application/xml','text/xml'}):
        raise ValueError('unexpected official-feed HTTP response')
    return headers


def fetch_feed(feed_id):
    if feed_id not in FEEDS: raise ValueError('unknown official feed')
    request = Request(FEEDS[feed_id], headers={'User-Agent':'decision-kernel-public-source-study/1.0',
        'Accept':'application/rss+xml,application/atom+xml,text/xml,application/xml', 'Accept-Encoding':'identity'})
    with build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=20) as response:
        headers = _safe_headers(dict(response.headers.items()))
        length = headers.get('content-length')
        if length is not None and (not re.fullmatch('[0-9]+', length) or int(length) > MAX_BODY):
            raise ValueError('feed byte budget exceeded')
        raw = response.read(MAX_BODY + 1); _body_integrity(raw, headers)
        result=PublicResponse(response.geturl(), response.status, headers, raw)
        check_response(result, feed_id)
        return result


def capture(output, *, previous=None, bootstrap=False, context=None, transport=None, now=lambda:datetime.now(timezone.utc)):
    if (previous is None) != bootstrap: raise ValueError('explicit previous capture or baseline required')
    old = None
    if previous is not None:
        checked = verify_capture(previous)
        if checked['capture_status'] != 'COMPLETE_FEED_INTAKE': raise ValueError('previous capture was incomplete')
        old_receipt = decode(_read(previous / 'capture.json'))
        if transport is None and old_receipt['provenance'] != 'PUBLIC_HTTP_CAPTURE':
            raise ValueError('synthetic state cannot become a live intake predecessor')
        old = decode(_read(previous / 'registry.json'))
    _safe_path(output); output.mkdir(parents=True, exist_ok=False)
    started = now(); windows, files, attempts = {}, {}, []
    receipt = {'version':VERSION,'policy_hash':POLICY_HASH,'semantics':SEMANTICS,
        'provenance':'SYNTHETIC_TEST_ONLY' if transport is not None else 'PUBLIC_HTTP_CAPTURE',
        'workflow':context or {},'started_at':started.isoformat(), 'recorded_at':None,'finished_at':None,
        'bootstrap':bootstrap,'status':'INCOMPLETE_FEED_INTAKE','failure':None,'requests':attempts,'files':files,
        'previous_capture_hash':checked['capture_hash'] if old else None, **AUTHORITY}
    def save(name, raw):
        (output / name).write_bytes(raw); files[name]=digest(raw)
    try:
        if old: save('previous-registry.json',data(old))
        for feed_id in sorted(FEEDS):
            entry = {'feed_id':feed_id,'url':FEEDS[feed_id],'requested_at':now().isoformat(),
                     'received_at':None,'status':None,'headers':{},'body_file':None,'error_type':None}
            attempts.append(entry)
            try:
                response = (transport or fetch_feed)(feed_id)
                entry['received_at']=now().isoformat(); entry['status']=response.status
                headers = check_response(response,feed_id)
                entry['headers']=headers; name=feed_id+'.xml'; save(name,response.body); entry['body_file']=name
                windows[feed_id]={'raw':response.body,'requested_at':entry['requested_at'],'received_at':entry['received_at']}
            except (ValueError,OSError,RuntimeError) as exc:
                entry['received_at']=entry['received_at'] or now().isoformat(); entry['error_type']=type(exc).__name__
                status=getattr(exc,'code',getattr(exc,'http_status',None))
                if type(status) is int: entry['status']=status
                raise
        recorded=now().isoformat(); receipt['recorded_at']=recorded
        registry,delta=advance(windows,recorded_at=recorded,previous=old,bootstrap=bootstrap)
        exports=source_rows(registry,delta)
        save('registry.json',data(registry)); save('delta.json',data(delta)); save('source-rows.json',data(exports))
        save('index.html',render(registry,delta,exports).encode('utf-8'))
        receipt['status']='COMPLETE_FEED_INTAKE'
    except (OSError,ValueError,RuntimeError,KeyError,TypeError) as exc:
        receipt['failure']={'type':type(exc).__name__} # No response error text/cookie/location in diagnostics.
        for name in ('registry.json','delta.json','source-rows.json','index.html'):
            (output/name).unlink(missing_ok=True); files.pop(name,None)
    receipt['finished_at']=now().isoformat(); receipt=_sealed(receipt,'capture_hash')
    (output/'capture.json').write_bytes(data(receipt))
    return receipt


def verify_capture(root):
    _safe_path(root); receipt=decode(_read(root/'capture.json'))
    if (receipt['version']!=VERSION or receipt['policy_hash']!=POLICY_HASH or receipt['semantics']!=SEMANTICS
            or any(receipt[k]!=v for k,v in AUTHORITY.items())
            or canonical_hash({k:v for k,v in receipt.items() if k!='capture_hash'})!=receipt['capture_hash']):
        raise ValueError('invalid capture identity')
    allowed={'previous-registry.json','registry.json','delta.json','source-rows.json','index.html',*(x+'.xml' for x in FEEDS)}
    if (not set(receipt['files'])<=allowed or {str(p.relative_to(root)) for p in root.rglob('*') if not p.is_dir()} != {'capture.json',*receipt['files']}):
        raise ValueError('capture inventory differs')
    for name,expected in receipt['files'].items():
        if digest(_read(root/name))!=expected: raise ValueError('capture bytes differ')
    windows={}
    for i,request in enumerate(receipt['requests']):
        key=request['feed_id']
        if i>=len(FEEDS) or key!=sorted(FEEDS)[i] or request['url']!=FEEDS[key]: raise ValueError('request sequence differs')
        if not _clock(receipt['started_at'])<=_clock(request['requested_at'])<=_clock(request['received_at'])<=_clock(receipt['finished_at']):
            raise ValueError('captured request clocks differ')
        if request['body_file']:
            if request['body_file']!=key+'.xml' or request['status']!=200: raise ValueError('body identity differs')
            windows[key]={'raw':_read(root/request['body_file']),'requested_at':request['requested_at'],'received_at':request['received_at']}
            check_response(PublicResponse(request['url'],request['status'],request['headers'],windows[key]['raw']),key)
    verification='RETAINED_BYTES_ONLY_INCOMPLETE_INTAKE'
    if receipt['status']=='COMPLETE_FEED_INTAKE':
        if receipt['failure'] is not None or any(r['error_type'] is not None for r in receipt['requests']):
            raise ValueError('successful receipt contains a failure')
        if not _clock(receipt['recorded_at'])<=_clock(receipt['finished_at']): raise ValueError('finish precedes record')
        previous=None if receipt['bootstrap'] else decode(_read(root/'previous-registry.json'))
        registry,delta=advance(windows,recorded_at=receipt['recorded_at'],previous=previous,bootstrap=receipt['bootstrap'])
        exports=source_rows(registry,delta)
        for name,value in [('registry.json',data(registry)),('delta.json',data(delta)),('source-rows.json',data(exports)),('index.html',render(registry,delta,exports).encode())]:
            if _read(root/name)!=value: raise ValueError('original feed/previous-registry reconstruction differs')
        verification='ORIGINAL_FEEDS_REGISTRY_AND_PAGE_REBUILT'
    elif receipt['status']!='INCOMPLETE_FEED_INTAKE': raise ValueError('unknown intake status')
    return {'status':verification,'capture_status':receipt['status'],'capture_hash':receipt['capture_hash'],'network_calls':0,**AUTHORITY}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Two native NBS RSS windows; no article or market requests.')
    parser.add_argument('mode',choices=['capture','verify']); parser.add_argument('--output',type=Path,required=True)
    choice=parser.add_mutually_exclusive_group(); choice.add_argument('--bootstrap',action='store_true'); choice.add_argument('--previous',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.mode=='verify':
            result=verify_capture(args.output); print(canonical_json(result)); return 0 if result['capture_status']=='COMPLETE_FEED_INTAKE' else 2
        import os
        context={k:os.environ[k] for k in ('GITHUB_REPOSITORY','GITHUB_WORKFLOW','GITHUB_REF','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA') if k in os.environ}
        if context and (context.get('GITHUB_REPOSITORY')!='auguspp/decision-kernel' or context.get('GITHUB_REF')!='refs/heads/main'
                        or context.get('GITHUB_WORKFLOW')!='economic-release-discovery' or context.get('GITHUB_RUN_ATTEMPT')!='1'):
            raise ValueError('requires a fresh canonical main source workflow')
        if args.previous is not None and os.environ.get('EXPECTED_PREVIOUS_RUN_ID'):
            old_receipt=decode(_read(args.previous/'capture.json')); old_context=old_receipt['workflow']
            if (old_context.get('GITHUB_RUN_ID')!=os.environ['EXPECTED_PREVIOUS_RUN_ID']
                    or any(old_context.get(k)!=context.get(k) for k in ('GITHUB_REPOSITORY','GITHUB_WORKFLOW','GITHUB_REF'))
                    or old_context.get('GITHUB_RUN_ATTEMPT')!='1'):
                raise ValueError('restored source artifact has a different workflow/run identity')
        result=capture(args.output,previous=args.previous,bootstrap=args.bootstrap,context=context)
        print(canonical_json({'status':result['status'],'failure':result['failure'],'requests':len(result['requests'])}))
        return 0 if result['status']=='COMPLETE_FEED_INTAKE' else 2
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
        print(canonical_json({'status':'INTAKE_UNAVAILABLE','error_type':type(exc).__name__})); return 2


if __name__=='__main__':
    raise SystemExit(main())
