import {REPO, openReading, readQuick, readHealth, loadModules, resumeText, fileUrl, references} from './reading.mjs';
import {locations, referenceMatches, watchSummary, companyName, companyMatches} from './presentation.mjs';

// Ordinary replaceable views; all retained source strings are text, never HTML.
const labels = {attention: '注意力', research: '研究', odds: 'Odds / Watch', markets: '市场观察', health: '系统健康'};
const hints = {attention: '先看已保存的研究增量与复核事项，再打开依据。不是新一轮全球扫描。',
  research: '按已登记公司找回研究、条件与更正。研究过不等于持有。',
  odds: '保存的价格条件和业务前提，不重算 Odds，不构成买卖指令。',
  markets: '观察日期与页面读取时间分别保留；没有覆盖不等于没有变化。',
  health: '只展示实际读取范围和失败；不从绿色任务或标题推断研究质量。'};
const enabled = new Set(Object.keys(labels));
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
    line.append(el('p', `原价格：${item.price ?? '未知'} ${item.currency || ''}；时点：${item.market_timestamp || '未知'}`));
    if (item.price_gap) line.append(el('p', `价格缺口：${item.price_gap}`, 'gap'));
    line.append(el('p', item.next_unreached_condition?.label || '下一未触及条件未提供'));
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
  const title = item.text.split('\n').find(line => line.trim()) || `记录 ${item.id}`;
  const detail = folded(title.replace(/^#+\s*/, ''), item.text, open);
  detail.insertBefore(el('p', `保存：${item.createdAt}；修改：${item.updatedAt}`, 'small'), detail.lastChild);
  detail.append(link('打开实际评论', item.url)); target.append(detail);
}
function quickCard() {
  const result = results.quick;
  if (result?.status !== 'READ') return gap('Hosted Quick', result?.reason);
  const info = result.value;
  const node = card('已保存的 Quick 分析', `读取 #575 最近 ${info.pages.length} 页；按最后修改时间排列。独立读取：${info.observedAt}。`);
  if (!info.items.length) node.append(el('p', '本次页面没有匹配的主结果，不代表没有其他研究。'));
  for (const [index, item] of info.items.entries()) appendComment(node, item, index === 0);
  const extra = el('details');
  extra.append(el('summary', `补充、更正及其他记录（${info.supplements.length}）`));
  extra.append(el('p', '保留未使用主结果标题的记录；不自动把工程回执当研究，也不自动认定它们取代原结论。', 'small'));
  for (const item of info.supplements) appendComment(extra, item);
  node.append(extra);
  node.append(el('p', '此范围不是完整研究历史或今天已扫描完毕的证明；主结果和后续补充需要一起阅读。', 'small muted'));
  return node;
}
function sourceRow(item, current) {
  const row = el('div', undefined, 'ref');
  const title = item.path || item.read_path;
  const readable = Number.isSafeInteger(item.bytes) && item.bytes >= 0 && item.bytes <= 512 * 1024 && !/\.zip$/i.test(item.read_path);
  if (readable) row.append(button(`读取 · ${title}`, () => readDetail(item, current), 'source-button'));
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
  input.setAttribute('aria-label', '搜索公司研究'); panel.append(input, list);
  function filter() {
    const companies = info.companies.filter(c => companyMatches(c, input.value));
    list.replaceChildren(el('p', `本目录 ${companies.length} / ${info.companies.length} 个公司关联；不是全市场或完整持仓。`, 'muted'));
    for (const company of companies) {
      const detail = el('details');
      detail.append(el('summary', `${companyName(company)} · ${company.thscode} · ${company.assets.length} 项用途记录`));
      detail.append(el('p', `原状态：${company.next_step || '未提供'}；接受边界：${company.human_acceptance || '未提供'}`, 'small'));
      for (const asset of company.assets) {
        const block = el('div', undefined, 'ref');
        block.append(el('strong', asset.id || asset.use || '已登记材料'), el('p', asset.purpose_note || asset.qualification || '用途说明未提供', 'small'));
        for (const source of references(asset)) block.append(sourceRow(source, current));
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
  input.oninput = filter; filter(); target.append(panel);
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
      el('p', '文件字节与 SHA-256 一致；不是整包或经济判断验证。', 'muted'),
      link('固定版本原件', file.url), el('pre', file.text), copy, request);
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
    target.append(quickCard(), watchCard(), card('持续事项与日历',
      '此版尚未接通完整待回应队列、持仓上下文和日历；不显示虚构的“0项待办”。研究仍由 ChatGPT 接续，页面不启动新研究。'));
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
      showRefs(target, item => locations(item).some(place => /^lanes\.(sector|stock)\./.test(place)) || /radar\//.test(item.read_path));
    }
  }
  if (selected === 'health') {
    if (reading) target.append(folded('读取包检查窗口与已登记缺口', value({checks: reading.payload.checks,
      capability_gaps: reading.payload.capability_gaps}), true));
    else target.append(gap('固定读取包', results.reading?.reason));
    if (results.health?.status === 'READ') {
      const h = results.health.value, panel = card('独立系统健康记录', `修改：${h.updatedAt}；读取：${h.observedAt}`);
      panel.append(link('实际健康 Issue', h.url), el('pre', h.text)); target.append(panel);
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
      $('identity').append(el('span', `本页读取：${reading.checkedAt} · 只读预览`),
        folded('来源版本与检查范围', `读取 R：${reading.ref}\n代码 M：${reading.payload.code_commit}\n${reading.validation}`));
      const recheck = Date.parse(reading.payload.checks?.recheck_after);
      if (!Number.isFinite(recheck) || Date.now() > recheck) $('identity').append(el('p', '读取包复查时点未知或已过期；不代表最新行情。本页不补跑生产。', 'gap'));
    } else $('identity').textContent = `固定读取包未取得：${results.reading.reason}；独立取得内容仍可查看。`;
    render();
  } finally { $('refresh').disabled = false; }
}
$('refresh').onclick = refresh; nav(); refresh();
