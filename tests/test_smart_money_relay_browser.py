"""Saved Relay rows join the existing offline view, never a new source scan."""
from copy import deepcopy
from hashlib import sha256
import base64
import json
import re
import socket
import subprocess

import pytest

from decision_kernel.runtime import smart_money_view as view, smart_money_reading as reading
from decision_kernel.runtime import smart_money_sources as source
from test_smart_money_relay_reading import with_relay, primary_intact
from test_smart_money_relay_report_dates import capture as report_capture


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('source access is forbidden in browser tests')
    monkeypatch.setattr(socket, 'getaddrinfo', reject)
    monkeypatch.setattr(socket.socket, 'connect', reject)


@pytest.fixture
def saved(tmp_path, monkeypatch):
    col, base, *rest = with_relay(tmp_path, monkeypatch)
    result = reading.attach(col, base)
    sm = result['research']['smart_money']
    assert sm['relay_browser_status'] == 'QUALIFIED_SAVED_ROWS_SEARCHABLE'
    page = col.files[sm['details']['browser']['read_path']].decode()
    value = json.loads(col.files[sm['details']['relay']['read_path']])
    return col, base, result, page, value


def payload(page):
    return json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>', page, re.S)[1])


def test_existing_publisher_wires_every_qualified_family_and_preserves_primary(saved):
    col, base, result, page, value = saved
    pack = payload(page)
    assert len(pack['relay']['records']) == 5
    for row in pack['relay']['records']:
        api = row['family'].split(':')[1]
        assert row['data']['values'] == value['families'][api]['rows'][0]
        assert row['pointer'] == f'/families/{api}/rows/0'
        assert row['document'] == 'relay.json'
        assert row['data']['actor_id'] is None
    assert result['lanes'] == base['lanes']
    reading.m.validate_read_package(result)
    assert json.loads(col.files['current-state.json']) == result
    original = deepcopy(pack); original_value = deepcopy(value)
    enriched = view.enrich_browser(page, [('relay.json', value)], {'current_status': 'READY'})
    assert payload(enriched)['chunks'] == original['chunks']
    assert payload(enriched)['history'] == original['history']
    assert value == original_value


def test_reports_only_joins_previous_nonreports_without_refreshing_them(saved, tmp_path):
    *_, page, old = saved
    current = report_capture(tmp_path)
    current['reading_relation'] = 'CURRENT_SOURCE_RUN'
    projection = view.relay_projection([('relay.json', current), ('relay-previous.json', old)], {})
    assert len(projection['records']) == 11  # 7 daily forecast rows + 4 old families
    assert len([r for r in projection['records'] if r['family'] == 'relay:report_rc']) == 7
    for row in projection['records']:
        if row['document'] == 'relay-previous.json':
            assert row['cutoff'] == old['cutoff'] and row['family'] != 'relay:report_rc'
        else:
            assert row['cutoff'] == current['cutoff']
            assert row['data']['values']['quarter'] == '2027Q4'
            assert row['data']['source_rows']['original']['report_date'] == row['data']['date']
    directory = next(r for r in projection['records'] if r['family'] == 'relay:hm_list')
    assert directory['data']['date'] is None  # acquisition is not effective date


@pytest.mark.parametrize('indexes', [[True], [-1], [1], [0, 0], ['0']])
def test_invalid_qualification_indexes_never_enter_normal_results(saved, indexes):
    value = deepcopy(saved[4]); item = value['families']['top_inst']
    item['interpretation']['qualified_row_indexes'] = indexes
    item['interpretation']['qualified_row_count'] = len(indexes)
    with pytest.raises(source.SourceError, match='RELAY_DISPLAY_QUALIFIED_ROWS'):
        view.relay_projection([('relay.json', value)], {})


def test_failed_or_unqualified_rows_remain_gaps_not_search_hits(saved):
    value = deepcopy(saved[4]); item = value['families']['hm_detail']
    item['interpretation']['qualified_row_indexes'] = []
    item['interpretation']['qualified_row_count'] = 0
    item['interpretation']['row_gaps'] = [{'row_index': 0, 'codes': ['REQUEST_DATE_MISMATCH']}]
    result = view.relay_projection([('relay.json', value)], {})
    assert len(result['records']) == 4
    assert not any(r['family'] == 'relay:hm_detail' for r in result['records'])
    assert result['origins']['relay.json:hm_detail']['qualification']['row_gaps']
    item['interpretation'] = None; item['status'] = 'TEMPORARY_QUEUE'
    result = view.relay_projection([('relay.json', value)], {})
    assert result['origins']['relay.json:hm_detail']['status'] == 'TEMPORARY_QUEUE'
    assert not any(r['family'] == 'relay:hm_detail' for r in result['records'])


def test_source_side_and_numbers_remain_exact_and_no_name_alias_is_invented(saved):
    value = deepcopy(saved[4]); item = value['families']['top_inst']
    item['rows'][0].update(side='', net_buy='123456789.123456789')
    item['interpretation']['field_gaps'] = [{'row_index': 0, 'field': 'side', 'code': 'SIDE_NOT_ESTABLISHED'}]
    value['families']['hm_list']['rows'][0]['orgs'] = '["甲营业部", "甲营业部别称"]'
    result = view.relay_projection([('relay.json', value)], {})
    seat = next(r for r in result['records'] if r['family'] == 'relay:top_inst')
    assert seat['data']['values']['side'] == '' and seat['field_gaps']
    assert seat['data']['values']['net_buy'] == '123456789.123456789'
    directory = next(r for r in result['records'] if r['family'] == 'relay:hm_list')
    assert directory['associations'] == ['甲营业部', '甲营业部别称']
    assert directory['data']['ticker'] is None and directory['data']['actor_id'] is None


@pytest.mark.parametrize('failure', ['BROWSER_OUTPUT_BOUND', 'shape', 'retain'])
def test_optional_display_failure_keeps_original_page_and_supplement_json(tmp_path, monkeypatch, failure):
    col, base, run, job, artifact, primary, *_ = with_relay(tmp_path, monkeypatch)
    before = []
    enrich = view.enrich_browser
    def bad(page, *args):
        before.append(page.encode())
        if failure == 'shape':
            raise TypeError('synthetic projection failure')
        if failure == 'BROWSER_OUTPUT_BOUND':
            raise source.SourceError(failure)
        return enrich(page, *args)
    monkeypatch.setattr(view, 'enrich_browser', bad)
    retain = col.retain
    def fail_retain(path, data):
        if failure == 'retain' and path.endswith('browse.html') and b'"relay":{' in data:
            raise OSError('synthetic optional retention failure')
        return retain(path, data)
    monkeypatch.setattr(col, 'retain', fail_retain)
    result = reading.attach(col, base)
    sm = primary_intact(col, base, result, primary)
    assert sm['relay_browser_status'] == 'DISPLAY_GAP_PRIMARY_AND_RELAY_JSON_RETAINED'
    assert sm['relay_status'] == 'READY' and 'relay' in sm['details']
    assert col.files[sm['details']['browser']['read_path']] == before[0]
    assert 'relay' not in payload(before[0].decode())


def test_script_source_hash_and_hostile_source_text_are_not_executable(saved):
    value = deepcopy(saved[4]); evil = '</script><script>globalThis.pwned=1</script>'
    value['families']['hm_list']['rows'][0]['name'] = evil
    page = view.enrich_browser(saved[3], [('relay.json', value)], {})
    assert evil not in page and '\\u003c/script>' in page
    script = re.search(r'</script><script>(.*?)</script>', page, re.S)[1]
    digest = base64.b64encode(sha256(script.encode()).digest()).decode()
    assert "script-src 'sha256-" + digest + "'" in page
    assert 'innerHTML' not in script and 'fetch(' not in script
    assert next(r for r in payload(page)['relay']['records'] if r['family'] == 'relay:hm_list')['data']['values']['name'] == evil


# Execute the exact page controller with native Node crypto/gzip streams and a
# minimal DOM double. This is behavior coverage, not hosted-browser acceptance.
NODE = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
class Element{
  constructor(tag){this.tag=tag;this.children=[];this.value='';this.disabled=true;this.text='';this.events={};}
  set textContent(v){this.text=String(v);this.children=[];}
  get textContent(){return this.text+this.children.map(n=>typeof n==='string'?n:n.textContent).join(' ');}
  append(...nodes){this.children.push(...nodes);} replaceChildren(...nodes){this.children=nodes;this.text='';}
  addEventListener(name,fn){this.events[name]=fn;}
}
const elements=Object.fromEntries(['payload','query','family','health','relay-health','results','count','prev','next'].map(id=>[id,new Element(id)]));
elements.payload.textContent=JSON.stringify(input.payload);
const context=vm.createContext({document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},
  crypto:require('node:crypto').webcrypto,Blob,DecompressionStream,TextDecoder,atob,
  fetch:()=>{throw Error('network forbidden');}});
vm.runInContext(input.script.replace('init().catch(', 'globalThis.ready=init().catch('),context);
(async()=>{
  await vm.runInContext('ready',context);
  assert.equal(elements.query.disabled,false,elements.health.textContent);
  const evaluate=code=>vm.runInContext(code,context);
  assert.equal(evaluate('records.length'),input.payload.history.record_count+input.payload.relay.records.length);
  function search(q,family=''){elements.query.value=q;elements.family.value=family;elements.query.events.input();}
  search('合成甲公司');assert(evaluate("filtered.some(r=>r.family==='relay:top_inst')"));
  search('sample-broker');assert(evaluate("filtered.some(r=>r.family==='relay:report_rc')"));
  search('甲营业部');assert(evaluate("filtered.some(r=>r.family==='relay:hm_list')"));
  search('sample-label','relay:hm_list');assert.equal(evaluate('filtered.length'),1);
  const card=elements.results.children[0],nav=card.children.find(n=>n.tag==='p'&&n.children.some(c=>c.tag==='button'));
  nav.children[0].onclick();assert.equal(elements.family.value,'');
  assert(evaluate("filtered.some(r=>r.family==='relay:hm_detail')"));
  search('不存在的公司');assert.equal(evaluate('filtered.length'),0);assert(elements.next.disabled);
  search('sample-broker');assert(elements.results.textContent.includes('1.234567890123456789'));
  const details=elements.results.children[0].children.find(n=>n.tag==='details');
  assert.equal(details.children.find(n=>n.tag==='a').href,'relay.json');
  assert(elements['relay-health'].textContent.includes('complete_market'));
  console.log(JSON.stringify({controller:'PASS',records:evaluate('records.length'),source_requests:0}));
})().catch(e=>{console.error(e);process.exitCode=1;});
'''


def test_real_search_controller_company_actor_clicks_and_original_navigation(saved):
    value = deepcopy(saved[4])
    value['families']['report_rc']['rows'][0].update(name='合成甲公司', eps='1.234567890123456789')
    value['families']['hm_list']['rows'][0]['orgs'] = '["甲营业部"]'
    page = view.enrich_browser(saved[3], [('relay.json', value)], {})
    script = re.search(r'</script><script>(.*?)</script>', page, re.S)[1]
    result = subprocess.run(['node', '-e', NODE],
        input=json.dumps({'payload':payload(page),'script':script}),
        text=True,capture_output=True,timeout=15,check=True)
    assert json.loads(result.stdout)['controller'] == 'PASS'
