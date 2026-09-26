import {REPO, openReading, readQuick, readHealth, loadModules, resumeText, fileUrl, references} from './reading.mjs';
import {locations, referenceMatches, watchSummary, companyName, companyMatches} from './presentation.mjs';
import {localTime, recordsView, outline, paragraphs, documentView, useLabel, companyStatus, priceCondition, marketEntries} from './product.mjs';

// Ordinary replaceable views; all retained source strings are text, never HTML.
const labels = {attention: '注意力', research: '研究', odds: 'Odds / Watch', markets: '市场观察', health: '系统健康'};
const hints = {attention: '先看已保存的研究增量与复核事项，再打开依据。不是新一轮全球扫描。',
  research: '按已登记公司找回研究、条件与更正。研究过不等于持有。',
  odds: '保存的价格条件和业务前提，不重算 Odds，不构成买卖指令。',
  markets: '观察日期与页面读取时间分别保留；没有覆盖不等于没有变化。',
  health: '只展示实际读取范围和失败；不从绿色任务或标题推断研究质量。'};
const enabled = new Set(Object.keys(labels));
let companyQuery = '';
let selected = 'attention', results = {}, reading = null, assets = null, detailGeneration = 0;
const $ = id => document.getElementById(id);
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}
function link(label, url) {
  const node = el('a', label); node.href = url; node.target = '_blank'; node.rel = 'noopener noreferrer';
  return node;
}
function button(label, action, className = 'control') {
  const node = el('button', label, className); node.type = 'button'; node.onclick = action; return node;
}
function card(title, description, isGap = false) {
  const node = el('section', undefined, isGap ? 'card gap' : 'card');
  node.append(el('h3', title)); if (description) node.append(el('p', description)); return node;
}
function gap(name, reason) { return card(`${name}：本次未取得`, reason || '未读取，不能当作零。', true); }
function folded(title, text, open = false) {
  const node = el('details'); node.open = open; node.append(el('summary', title), el('pre', text)); return node;
}
function value(object) { return JSON.stringify(object, null, 2); }
function prose(text) {
  const node = el('div', undefined, 'product-reading');
  for (const section of outline(text)) {
    if (section.level) node.append(el('h4', section.title));
    for (const paragraph of paragraphs(section.text)) node.append(el('p', paragraph));
  }
  return node;
}
function documentBody(file) {
  const view = documentView(file.text);
  if (!view) {
    // Proportional, wrapped original paragraphs; no invented Markdown engine or HTML.
    if (!/\.json$/i.test(file.path)) {
      const content = prose(file.text); content.append(folded('完整原始文本', file.text)); return content;
    }
    const raw = folded('完整 JSON 原件（此格式尚未提供摘要）', file.text, true);
    raw.className = 'product-original'; return raw;
  }
  const node = el('div', undefined, 'product-reading');
  node.append(el('h4', view.title), el('p', view.notice, 'product-notice'));
  const facts = el('dl', undefined, 'product-facts');
  for (const [label, field] of view.facts) {
    facts.append(el('dt', label), el('dd', field === null || field === undefined ? '未提供' : String(field)));
  }
  node.append(facts);
  if (view.limits.length) node.append(el('h4', '原计算限制'), ...view.limits.map(t => el('p', t)));
  for (const row of view.rows) {
    const section = el('details'); section.append(el('summary', row.name));
    section.append(el('p', `原终点每股价值：${row.terminal}；原累计每股回收：${row.payoff}`));
    section.append(el('p', `原未折现累计收益率（小数，非年化）：${row.returnFraction}`));
    section.append(el('h4', '原经营条件'), ...row.conditions.map(c => el('p', c))); node.append(section);
  }
  node.append(folded('完整原始 JSON 与其他字段', file.text)); return node;
}
function goCompany(code) {
  companyQuery = code; enabled.add('research'); selected = 'research'; nav(); render();
}
// Scoped additions only: do not replace the user's Sites root/layout/CSP.
if (document.head) {
  const style = el('style', '.product-reading{font:inherit;line-height:1.8;overflow-wrap:anywhere;min-width:0}.product-reading p{white-space:pre-wrap;margin:10px 0 16px}.product-reading h4{font:inherit;font-weight:650;margin:20px 0 8px}.product-reading .product-notice{border-left:3px solid currentColor;padding:8px 14px}.product-facts{display:grid;grid-template-columns:minmax(6em,10em) minmax(0,1fr);gap:8px 14px}.product-facts dt{font-weight:600}.product-facts dd{margin:0;overflow-wrap:anywhere}.product-original pre{max-height:65vh;overflow:auto}.product-record{border-top:1px solid #dce3e9;padding-top:14px;margin-top:16px}.product-excerpt{white-space:pre-wrap;font:inherit;line-height:1.8}.product-actions{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}.product-market{display:grid;gap:12px}.product-market>div{border-bottom:1px solid #dce3e9;padding:12px 0}@media(max-width:600px){.product-facts{grid-template-columns:1fr;gap:4px}.product-facts dd{margin-bottom:10px}}');
  style.id = 'kernel-product-view-style'; document.head.append(style);
}

function nav() {
  $('nav').replaceChildren();
  for (const [id, label] of Object.entries(labels)) if (enabled.has(id)) {
    const node = button(label, () => { selected = id; nav(); render(); }, '');
    if (id === selected) node.setAttribute('aria-current', 'page');
    $('nav').append(node);
  }
}
for (const [id, label] of Object.entries(labels)) if (id !== 'attention') {
  const wrapper = el('label'), input = el('input'); input.type = 'checkbox'; input.checked = true;
  input.onchange = () => {
    input.checked ? enabled.add(id) : enabled.delete(id);
    if (!enabled.has(selected)) selected = 'attention';
    nav(); render();
  };
  wrapper.append(input, document.createTextNode(` ${label}`)); $('modules').append(wrapper);
}
function watchCard() {
  if (!reading) return gap('价格复核', results.reading?.reason);
  const info = watchSummary(reading.payload);
  if (!info.available) return gap('价格复核', '没有可读的原 Watch 明细，不能判断是否触界。');
  const {counts} = info;
  const node = card('已登记的价格复核', '以下为原观察结果，不是当前实时行情；触界仍须核对业务前提。');
  node.append(el('p', `已启用 ${counts.enabled} · 已完成判断 ${counts.evaluated} · 原观察触界 ${counts.triggered} · 无法判断 ${counts.unknown}`, 'metric'));
  if (info.countMismatch) node.append(el('p', '原声明数量与可读明细不一致；覆盖待核对。', 'gap'));
  const order = {TRIGGERED: 0, UNKNOWN: 1, NOT_TRIGGERED: 2, INACTIVE: 3};
  const states = {TRIGGERED: '原观察已触界，待复核', UNKNOWN: '无法判断', NOT_TRIGGERED: '原观察未触界', INACTIVE: '未启用或不适用'};
  for (const {item, state} of [...info.rows].sort((a, b) => order[a.state] - order[b.state])) {
    const line = el('details'); line.open = state === 'TRIGGERED' || state === 'UNKNOWN';
    line.append(el('summary', `${item.company_name || item.ticker || '对象未知'} · ${states[state]}`));
    line.append(el('p', `原价格：${item.price ?? '未知'} ${item.currency || ''}；时点：${localTime(item.market_timestamp)}`));
    if (item.price_gap) line.append(el('p', `价格缺口：${item.price_gap}`, 'gap'));
    line.append(el('p', priceCondition(item)));
    if (item.ticker) line.append(button('查看这家公司的已有研究', () => goCompany(item.ticker)));
    line.append(folded('原条件名称与时点', value({condition: item.next_unreached_condition, market_timestamp: item.market_timestamp})));
    if (state === 'TRIGGERED') line.append(el('pre', value(item.triggered_conditions)));
    line.append(el('p', item.prerequisite || '业务前提未提供', 'small'));
    // Original Human checkpoint is an explicit source, not a page-created decision.
    if (item.source?.source_ref && item.source?.source_path) {
      try { line.append(link('查看原条件与回应', fileUrl(item.source.source_ref, item.source.source_path))); }
      catch { line.append(el('p', '原条件定位不合格', 'gap')); }
    }
    node.append(line);
  }
  return node;
}
function appendComment(target, item, open = false) {
  const detail = el('details'); detail.open = open;
  detail.append(el('summary', item.text.split('\n').find(line => line.trim())?.replace(/^#+\s*/, '') || `记录 ${item.id}`));
  detail.append(el('p', `保存：${localTime(item.createdAt)}；修改：${localTime(item.updatedAt)}`, 'small'));
  detail.append(prose(item.text), link('打开实际评论', item.url)); target.append(detail);
}
function quickCard() {
  const result = results.quick;
  if (result?.status !== 'READ') return gap('研究更新', result?.reason);
  const info = result.value, grouped = recordsView(info);
  const node = card('研究更新', '先看已保存的结论，再展开依据与限制。这里不是实时新闻，也不代表已经检查完今天的变化。');
  if (!grouped.research.length) node.append(el('p', '本次读取范围没有可识别的 Quick 正文；其他记录仍在下方保留。'));
  for (const entry of grouped.research) {
    const section = el('section', undefined, 'product-record');
    section.append(el('p', `${entry.label} · 原标题日期 ${entry.date}`, 'small muted'), el('h4', entry.title));
    if (entry.excerpt) section.append(el('p', '结论开头 · 原文摘录', 'small muted'), el('p', entry.excerpt, 'product-excerpt'));
    else section.append(el('p', '原记录没有单列结论段，请展开正文；本页不替作者生成结论。', 'small'));
    const body = el('details'); body.append(el('summary', '阅读完整分析、反证与限制'), prose(entry.record.text));
    section.append(body, el('p', `原记录保存：${localTime(entry.record.createdAt)}；修改：${localTime(entry.record.updatedAt)}`, 'small'),
      link('查看原评论及后续讨论', entry.record.url)); node.append(section);
  }
  const extra = el('details'); extra.open = !grouped.research.length;
  extra.append(el('summary', `简报、补充与其他记录（${grouped.other.length}）`));
  extra.append(el('p', '单独保留，不自动当作新 Quick、替代原结论或已处理事项。', 'small'));
  for (const entry of grouped.other) appendComment(extra, entry.record);
  node.append(extra, folded('读取范围与原始时钟', value({issue: 575, pages: info.pages,
    observedAt: info.observedAt, issueUpdatedAt: info.issueUpdatedAt, coverage: info.coverage})));
  return node;
}
function sourceRow(item, current, displayName = null) {
  const row = el('div', undefined, 'ref');
  const title = item.path || item.read_path;
  const readable = Number.isSafeInteger(item.bytes) && item.bytes >= 0 && item.bytes <= 512 * 1024 && !/\.zip$/i.test(item.read_path);
  if (readable) row.append(button(`读取 · ${displayName || title}`, () => readDetail(item, current), 'source-button'));
  else row.append(el('span', `${title}（本页不内嵌此附件）`));
  row.append(el('div', `${locations(item).join(' / ')} · ${item.bytes ?? '未知'} bytes`, 'small muted'));
  row.append(link('固定版本原件', fileUrl(current.ref, item.read_path))); return row;
}
function showRefs(target, predicate = () => true) {
  if (!reading) { target.append(gap('原件索引', results.reading?.reason)); return; }
  const current = reading, input = el('input'), list = el('div');
  input.type = 'search'; input.placeholder = '搜索原始文件名、保存路径或分类'; input.setAttribute('aria-label', '搜索原件');
  const all = [...current.references, ...(assets?.status === 'READ' ? assets.value.references : [])];
  const unique = new Map();
  for (const item of all.filter(predicate)) if (!unique.has(item.read_path)) unique.set(item.read_path, item);
  function filter() {
    const visible = [...unique.values()].filter(item => referenceMatches(item, input.value));
    list.replaceChildren(el('p', `${visible.length} 个定位；索引不等于正文已读。`, 'muted'));
    for (const item of visible) list.append(sourceRow(item, current));
  }
  input.oninput = filter; target.append(input, list); filter();
}
async function loadCompanies() {
  if (!reading || assets) return;
  const current = reading; assets = {status: 'LOADING'};
  try { const result = await current.readAssets(); if (current === reading) assets = {status: 'READ', value: result}; }
  catch (error) { if (current === reading) assets = {status: 'GAP', reason: error.message}; }
  if (current === reading && selected === 'research') render();
}
function companyView(target) {
  if (!reading) { target.append(gap('公司研究目录', results.reading?.reason)); return; }
  if (!assets) { target.append(card('公司研究目录', '正在读取已保存的关联目录…')); loadCompanies(); return; }
  if (assets.status === 'LOADING') { target.append(card('公司研究目录', '正在核对目录原件…')); return; }
  if (assets.status !== 'READ') { target.append(gap('公司研究目录', assets.reason)); return; }
  const current = reading, info = assets.value;
  const panel = card('按公司恢复研究', '沿用仓库已有公司关联，不推断持仓，不自动选择最终研究版本；用途说明和原接受边界一并保留。');
  panel.append(link('目录原件', info.file.url));
  const input = el('input'), list = el('div'); input.type = 'search'; input.placeholder = '公司名称、证券代码、研究用途';
  input.setAttribute('aria-label', '搜索公司研究'); input.value = companyQuery; panel.append(input, list);
  function filter() {
    const companies = info.companies.filter(c => companyMatches(c, input.value));
    list.replaceChildren(el('p', `本目录 ${companies.length} / ${info.companies.length} 个公司关联；不是全市场或完整持仓。`, 'muted'));
    for (const company of companies) {
      const detail = el('details');
      detail.append(el('summary', `${companyName(company)} · ${company.thscode} · ${company.assets.length} 项用途记录`));
      detail.append(el('p', companyStatus(company)));
      detail.append(el('p', '这些是历史材料。是否接受、是否仍有效，以原记录和适用更正为准。', 'small'));
      detail.append(folded('原状态与接受边界', value({next_step: company.next_step, human_acceptance: company.human_acceptance})));
      if (input.value.trim()) detail.open = true;
      for (const asset of company.assets) {
        const block = el('div', undefined, 'ref');
        block.append(el('strong', useLabel(asset)), el('p', asset.purpose_note || '用途说明未提供'));
        block.append(folded('登记标识与资格原值', value({id: asset.id, use: asset.use, qualification: asset.qualification})));
        for (const source of references(asset)) block.append(sourceRow(source, current, (source.path || source.read_path).split('/').at(-1)));
        detail.append(block);
      }
      if (company.archives.length) {
        const archive = el('details'); archive.append(el('summary', `研究档案（${company.archives.length}）`));
        for (const source of references(company.archives)) archive.append(sourceRow(source, current));
        archive.append(folded('档案关联元数据', value(company.archives))); detail.append(archive);
      }
      list.append(detail);
    }
  }
  input.oninput = () => { companyQuery = input.value; filter(); }; filter(); target.append(panel);
}
async function readDetail(descriptor, current = reading) {
  const generation = ++detailGeneration;
  $('detail').replaceChildren(el('h3', descriptor.path || descriptor.read_path), el('p', '正在读取原件并核对字节…'));
  try {
    const file = await current.readFile(descriptor);
    if (generation !== detailGeneration || current !== reading) return;
    const request = el('pre', resumeText(current.ref, descriptor)); request.hidden = true;
    const copy = button('复制接续请求', async () => {
      try { await navigator.clipboard.writeText(request.textContent); copy.textContent = '已复制；未执行或写回'; }
      catch { request.hidden = false; copy.textContent = '请复制下方接续文字'; }
    });
    $('detail').replaceChildren(el('h3', descriptor.path || file.path),
      el('p', '原件已核对字节与 SHA-256；下方仅整理原文，不更新研究判断。', 'muted'),
      link('固定版本原件', file.url), documentBody(file), copy, request);
    $('detail').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (error) {
    if (generation !== detailGeneration || current !== reading) return;
    $('detail').replaceChildren(el('h3', '原件未取得或核验失败'), el('p', error.message),
      link('检查固定原件定位', fileUrl(current.ref, descriptor.read_path)));
  }
}
function render() {
  ++detailGeneration; $('detail').replaceChildren(); $('content').replaceChildren();
  $('heading').textContent = labels[selected]; $('subtitle').textContent = hints[selected];
  const target = $('content');
  if (selected === 'attention') {
    target.append(quickCard(), watchCard(), folded('尚未覆盖的事项',
      '持续待回应队列、持仓上下文和日历尚未接通；不能将未接通当作0项。建议开展Full不等于已委托，页面不自动启动研究。'));
  }
  if (selected === 'research') {
    companyView(target);
    const other = el('details'); other.append(el('summary', '其他研究原件与定位'));
    showRefs(other, item => locations(item).some(place => place.startsWith('research.'))); target.append(other);
  }
  if (selected === 'odds') { target.append(watchCard()); showRefs(target, item => /odds/i.test(`${item.path} ${item.read_path}`)); }
  if (selected === 'markets') {
    if (!reading) target.append(gap('市场观察', results.reading?.reason));
    else {
      for (const name of ['sector', 'stock']) {
        const lane = reading.payload.lanes[name], panel = card(name === 'sector' ? '板块观察' : '个股观察',
          `原市场日：${lane?.last_qualified_result?.market_session || '未提供'}；运行状态：${lane?.health || '未知'}`);
        panel.append(el('p', `覆盖缺口：${lane?.gaps?.join('；') || '请按原件核对，未作全市场完备性认证。'}`, 'small'));
        panel.append(folded('运行与版本详情', value(lane ? {latest_attempt: lane.latest_attempt} : {gap: 'NOT_PROVIDED'}))); target.append(panel);
      }
      const summaries = card('按主题阅读市场材料', '以下沿用各原件的观察日与覆盖范围；强弱不等于公司受益，未解释的原因保持未知。');
      const entries = el('div', undefined, 'product-market');
      for (const entry of marketEntries(reading)) {
        const row = el('div'); row.append(el('strong', entry.label));
        if (entry.source) {
          const current = reading;
          row.append(button('阅读已保存摘要', () => readDetail(entry.source, current)), link('固定原件', fileUrl(current.ref, entry.source.read_path)));
        } else row.append(el('p', entry.gap, 'small'));
        entries.append(row);
      }
      summaries.append(entries); target.append(summaries);
      const more = el('details'); more.append(el('summary', '全部市场原件与定位'));
      showRefs(more, item => locations(item).some(place => /^lanes\.(sector|stock)\./.test(place)) || /radar\//.test(item.read_path)); target.append(more);
    }
  }
  if (selected === 'health') {
    if (reading) target.append(folded('读取包检查窗口与已登记缺口', value({checks: reading.payload.checks,
      capability_gaps: reading.payload.capability_gaps}), true));
    else target.append(gap('固定读取包', results.reading?.reason));
    if (results.health?.status === 'READ') {
      const h = results.health.value, panel = card('独立系统健康记录', `修改：${localTime(h.updatedAt)}；读取：${localTime(h.observedAt)}`);
      panel.append(link('实际健康 Issue', h.url), prose(h.text)); target.append(panel);
    } else target.append(gap('独立健康', results.health?.reason));
  }
}
async function refresh() {
  $('refresh').disabled = true; ++detailGeneration; reading = null; assets = null; results = {};
  $('detail').replaceChildren(); $('content').replaceChildren(card('正在读取', '只读取 GitHub 已保存结果，不启动采集、研究或任务。'));
  $('identity').textContent = '读取中…';
  try {
    results = await loadModules({reading: () => openReading(), quick: () => readQuick(), health: () => readHealth()});
    reading = results.reading.status === 'READ' ? results.reading.value : null;
    $('identity').replaceChildren();
    if (reading) {
      $('identity').append(el('span', `本页读取：${localTime(reading.checkedAt)} · 只读试用`),
        folded('来源版本与检查范围', `读取 R：${reading.ref}\n代码 M：${reading.payload.code_commit}\n原读取时间：${reading.checkedAt}\n${reading.validation}`));
      const recheck = Date.parse(reading.payload.checks?.recheck_after);
      if (!Number.isFinite(recheck) || Date.now() > recheck) $('identity').append(el('p', '读取包复查时点未知或已过期；不代表最新行情。本页不补跑生产。', 'gap'));
    } else $('identity').textContent = `固定读取包未取得：${results.reading.reason}；独立取得内容仍可查看。`;
    render();
  } finally { $('refresh').disabled = false; }
}
$('refresh').onclick = refresh; nav(); refresh();
