import {REPO, openReading, readQuick, readHealth, loadModules, resumeText, fileUrl, references} from './reading.mjs';
import {locations, referenceMatches, watchSummary, watchState, companyName, companyMatches} from './presentation.mjs';
import {localTime, recordsView, outline, paragraphs, documentView, useLabel, companyStatus, priceCondition, marketEntries, attentionView, companyMaterials, watchOrigin, attentionResume, bookProfile, displayDecimal, humanValue, humanGap, researchReading, previewSource} from './product.mjs';

// Ordinary replaceable views; all retained source strings are text, never HTML.
const labels = {attention: '注意力', research: '研究', odds: 'Odds / Watch', markets: '市场观察', health: '系统健康'};
const hints = {attention: '先看已保存的研究增量与复核事项，再打开依据。不是新一轮全球扫描。',
  research: '按已登记公司找回研究、条件与更正。研究过不等于持有。',
  odds: '保存的价格条件和业务前提，不重算 Odds，不构成买卖指令。',
  markets: '观察日期与页面读取时间分别保留；没有覆盖不等于没有变化。',
  health: '只展示实际读取范围和失败；不从绿色任务或标题推断研究质量。'};
const enabled = new Set(Object.keys(labels));
let companyQuery = '', selectedAttention = null, selectedCompany = null, bookPage = 0;
let previews = new Map();
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
function gap(name, reason) { return impactGap(`${name}：本次未取得`, [reason || '未读取，不能当作零。']); }
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
    if (!/\.json$/i.test(file.path)) return readingBody(file.text);
    const node = el('div', undefined, 'product-reading');
    node.append(notice('这份原件尚无适配的阅读视图。没有生成摘要，也不把保存回执当作研究结论。'),
      folded('完整 JSON 原件（此格式尚未提供摘要）', file.text)); return node;
  }
  const node = el('div', undefined, 'product-reading');
  node.append(el('h4', view.title), notice(view.notice));
  const facts = el('dl', undefined, 'product-facts');
  for (const [label, field] of view.facts) facts.append(el('dt', label), el('dd', label === '原参考价' ? displayDecimal(field) : humanValue(field)));
  node.append(facts);
  if (view.limits.length) node.append(el('h4', '原计算限制'), ...view.limits.map(t => el('p', t)));
  for (const row of view.rows) {
    const section = el('details'); section.append(el('summary', row.name));
    section.append(el('p', `原终点每股价值：${displayDecimal(row.terminal)}；原累计每股回收：${displayDecimal(row.payoff)}`));
    section.append(el('p', `原未折现累计收益率（非年化）：${displayDecimal(row.returnFraction, {percent: true})}`));
    section.append(el('h4', '原经营条件'), ...row.conditions.map(c => el('p', c))); node.append(section);
  }
  node.append(el('p', '≈ 表示仅显示取舍小数位；原数值与条件没有修改。', 'small'),
    folded('完整原始 JSON 与其他字段', file.text)); return node;
}
function goCompany(code, item = null) {
  selectedAttention = item; selectedCompany = code;
  companyQuery = code; enabled.add('research'); selected = 'research'; nav(); render();
}
// Scoped additions only: do not replace the user's Sites root/layout/CSP.
if (document.head) {
  const style = el('style', '.product-reading{font:inherit;line-height:1.8;overflow-wrap:anywhere;min-width:0}.product-reading p{white-space:pre-wrap;margin:10px 0 16px}.product-reading h4{font:inherit;font-weight:650;margin:20px 0 8px}.product-reading .product-notice{border-left:3px solid currentColor;padding:8px 14px}.product-facts{display:grid;grid-template-columns:minmax(6em,10em) minmax(0,1fr);gap:8px 14px}.product-facts dt{font-weight:600}.product-facts dd{margin:0;overflow-wrap:anywhere}.product-original pre{max-height:65vh;overflow:auto}.product-record{border-top:1px solid #dce3e9;padding-top:14px;margin-top:16px}.product-excerpt{white-space:pre-wrap;font:inherit;line-height:1.8}.product-actions{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}.product-market{display:grid;gap:12px}.product-market>div{border-bottom:1px solid #dce3e9;padding:12px 0}@media(max-width:600px){.product-facts{grid-template-columns:1fr;gap:4px}.product-facts dd{margin-bottom:10px}}');
  style.textContent += '.human-table-wrap{max-width:100%;overflow-x:auto}.human-table{font-size:14px;line-height:1.6}.human-table caption{text-align:left;margin:6px 0 16px;font-size:12px;color:#526678}.human-table th{font-weight:600}.human-table p{margin:0 0 7px}.human-object{border:0;background:none;color:#245e91;padding:3px 0;text-align:left;font-weight:650;font-size:15px}.human-notice{border-left:3px solid #ae7a33;padding:10px 14px;background:#fffcf5;line-height:1.7}.human-lead{font-size:16px;line-height:1.85;white-space:pre-wrap}.human-research-row{padding:16px 0;border-top:1px solid #dce3e9}.human-research-row h4{font-size:18px;margin:5px 0 12px}.human-company{margin-top:22px}.human-company>h3{font-size:23px;margin-top:22px}.human-material{padding:14px 0 18px;border-top:1px solid #e4e9ee}.human-material>h4{font-size:16px;margin:4px 0 10px}.human-material-group>h4{font-size:18px;margin:26px 0 12px}.human-material>p{line-height:1.8}.human-document{max-width:850px}.human-limitations{border-left:3px solid #ae7a33;padding:12px 18px;margin:18px 0;background:#fffcf5}.human-table td{overflow-wrap:anywhere}.human-preview{margin-top:10px;font-size:13px}.human-preview-text{max-width:38em;line-height:1.75}.human-company .control{min-height:40px}@media(max-width:600px){.human-table thead{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}.human-table,.human-table tbody,.human-table tr,.human-table td{display:block;width:100%}.human-table tr{padding:12px 0;border-bottom:1px solid #c5d0d8}.human-table td{border:0;padding:6px 0}.human-table td:before{content:attr(data-label);display:block;font-size:12px;font-weight:600;color:#526678}.human-table caption{display:block}.human-lead{font-size:15px}}';
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
function continuationControls(item, company, current) {
  const controls = el('div', undefined, 'product-actions');
  const request = el('pre'); request.hidden = true;
  const copy = button('复制事项接续（未写回）', async () => {
    if (current !== reading) return;
    try {
      request.textContent = attentionResume(current.ref, item, company);
      try { await navigator.clipboard.writeText(request.textContent); copy.textContent = '已复制；尚未回应或写回'; }
      catch { request.hidden = false; copy.textContent = '请复制下方定位文字；尚未写回'; }
    } catch (error) { request.hidden = false; request.textContent = `定位不完整：${error.message}`; }
  });
  controls.append(copy, request); return controls;
}
function itemContext(item, current, company = null) {
  const node = card(`当前事项 · ${item.label}`, item.reason);
  node.append(el('p', `原观察时间：${localTime(item.at)}；旧处置不代表新版本已经接受。`, 'small'));
  const source = item.kind === 'watch' ? watchOrigin(item, company) : item.source;
  if (source) {
    const label = item.kind === 'watch' ? '精确原条件与回应' : '精确原请求';
    node.append(button('阅读原事项依据', () => readDetail(source, current, {title: label})),
      disclosure('事项依据与精确定位', sourceRow(source, current, label)));
  }
  else node.append(el('p', '原条件版本尚未唯一定位；不会替换成另一份材料。', 'small'));
  if (item.resolution) node.append(button('阅读这次事项的历史处置', () => readDetail(item.resolution, current, {title: '原事项处置'})),
    disclosure('处置依据与精确定位', sourceRow(item.resolution, current, '此版本已登记的处置')));
  node.append(continuationControls(item, company, current), folded('事项身份与原始状态', value({id: item.id,
    reading: current.ref, state: item.state, observation_time: item.at, original: item.original})));
  return node;
}
function attentionCard() {
  if (!reading) return gap('事项导航', results.reading?.reason);
  const current = reading, view = attentionView(current.payload, watchSummary(current.payload));
  const panel = card('需要留意的事项', '明确请求、价格条件和历史处置分开。只覆盖已登记材料；点击或已读不会改变处置状态。');
  const groups = [
    ['明确待你回应', view.requests, '本次可读登记中没有明确待回应项；不是全局无需判断。'],
    ['原价格已触界，待复核', view.review, '本次可判断的已登记价格观察没有触界项。'],
    ['等待原登记条件', view.waiting, '本次没有可确认的等待条件。'],
    ['已有处置记录', view.history, '本次没有可恢复的明确处置绑定。'],
    ['其他登记研究背景', view.background, '']
  ];
  for (const [label, items, empty] of groups) {
    if (!items.length && !empty) continue;
    const group = el('details'); group.open = (label === '明确待你回应' || label === '原价格已触界，待复核') && items.length > 0;
    group.append(el('summary', `${label}（${items.length}）`));
    if (!items.length) group.append(el('p', view.gaps.length ? '存在读取或覆盖缺口；0项不是已确认全部无事。' : empty, 'small'));
    for (const item of items) {
      const row = el('div', undefined, 'ref'); row.append(el('h4', item.label), el('p', item.reason));
      row.append(el('p', `原观察：${localTime(item.at)}`, 'small'));
      row.append(button('恢复这个事项', () => {
        if (current !== reading) return;
        if (item.code) goCompany(item.code, item);
        else { ++detailGeneration; $('detail').replaceChildren(itemContext(item, current)); }
      })); group.append(row);
    }
    panel.append(group);
  }
  if (view.gaps.length) panel.append(impactGap('读取与覆盖缺口（不是交给你的待办）', view.gaps));
  panel.append(el('p', '新Quick仍在下方作为研究资讯；未建立完整持续回应队列、持仓或日历，不能用这里的数量替代。', 'small'));
  return panel;
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
    line.append(el('p', `原价格：${displayDecimal(item.price)} ${item.currency || ''}；时点：${localTime(item.market_timestamp)}`));
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
function quickCard() { return researchRecords(); }
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
  if (current === reading && (selected === 'research' || selected === 'odds')) render(true);
}
function companyView(target) { bookView(target); }
async function readDetail(descriptor, current = reading, context = null) {
  const generation = ++detailGeneration;
  $('detail').replaceChildren(el('h3', context?.title || '正在打开资料'), el('p', '正在读取已保存原件…'));
  try {
    const file = await current.readFile(descriptor);
    if (generation !== detailGeneration || current !== reading) return;
    const request = el('pre', resumeText(current.ref, descriptor)); request.hidden = true;
    const copy = button('复制接续请求', async () => {
      try { await navigator.clipboard.writeText(request.textContent); copy.textContent = '已复制；未执行或写回'; }
      catch { request.hidden = false; copy.textContent = '请复制下方接续文字'; }
    });
    const title = researchReading(file.text).title || context?.title || '已保存原件';
    $('detail').replaceChildren(el('h3', title),
      el('p', '阅读已保存版本；不是新的研究或接受记录。', 'muted'),
      ...(context?.asset?.purpose_note ? [disclosure('本版本原登记说明', el('p', context.asset.purpose_note))] : []),
      documentBody(file), copy, request, disclosure('原件与技术校验', link('固定版本原件', file.url),
        el('p', '原件已核对字节与 SHA-256；没有改写研究判断。'),
        folded('精确定位', value({path: descriptor.path || file.path, reading: current.ref, sha256: file.sha256}))));
    $('detail').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (error) {
    if (generation !== detailGeneration || current !== reading) return;
    $('detail').replaceChildren(el('h3', '原件未取得或核验失败'), el('p', humanGap(error.message)), folded('技术诊断', error.message),
      link('检查固定原件定位', fileUrl(current.ref, descriptor.read_path)));
  }
}
function render(keepDetail = false) {
  // The catalogue completing is not a new selection. Do not cancel an original
  // the user opened while the optional catalogue was loading.
  if (!keepDetail) { ++detailGeneration; $('detail').replaceChildren(); }
  $('content').replaceChildren();
  $('heading').textContent = labels[selected]; $('subtitle').textContent = hints[selected];
  const target = $('content');
  if (selected === 'attention') {
    target.append(attentionCard(), quickCard(), button('打开 Odds / Watch 查看全部原价格条件', () => { selected = 'odds'; nav(); render(); }), folded('尚未覆盖的事项',
      '持续待回应队列、持仓上下文和日历尚未接通；不能将未接通当作0项。建议开展Full不等于已委托，页面不自动启动研究。'));
  }
  if (selected === 'research') {
    companyView(target);
    const other = el('details'); other.append(el('summary', '其他研究原件与定位'));
    showRefs(other, item => locations(item).some(place => place.startsWith('research.'))); target.append(other);
  }
  if (selected === 'odds') {
    bookView(target, true);
    target.append(disclosure('逐项原价格观察与完整条件', watchCard()));
    const originals = disclosure('全部 Odds 原件与定位');
    showRefs(originals, item => /odds/i.test(`${item.path} ${item.read_path}`)); target.append(originals);
  }
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
  $('refresh').disabled = true; ++detailGeneration; reading = null; assets = null; selectedAttention = null; selectedCompany = null; previews = new Map(); bookPage = 0; results = {};
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
    } else $('identity').append(el('p', `固定读取包未取得：${humanGap(results.reading.reason)}独立取得内容仍可查看。`), folded('读取诊断', results.reading.reason));
    render();
  } finally { $('refresh').disabled = false; }
}
$('refresh').onclick = refresh; nav(); refresh();

// Small native views over the already-verified reader. No new transport or store.
function disclosure(title, ...children) {
  const node = el('details'); node.append(el('summary', title), ...children); return node;
}
function notice(text) { return el('p', text, 'human-notice'); }
function dataTable(caption, headings) {
  const wrapper = el('div', undefined, 'human-table-wrap'), table = el('table', undefined, 'human-table');
  table.append(el('caption', caption));
  const head = el('thead'), tr = el('tr'), body = el('tbody');
  for (const heading of headings) { const th = el('th', heading); th.setAttribute('scope', 'col'); tr.append(th); }
  head.append(tr); table.append(head, body); wrapper.append(table); return {wrapper, body};
}
function tableCell(label, ...children) {
  const td = el('td'); td.setAttribute('data-label', label); td.append(...children); return td;
}
function impactGap(title, reasons) {
  const values = reasons.map(String), panel = card(title, null, true);
  for (const message of [...new Set(values.map(humanGap))]) panel.append(el('p', message));
  panel.append(folded('技术诊断与原值', values.join('\n'))); return panel;
}
function friendlySource(asset, current, ordinal = 1) {
  const row = el('div', undefined, 'human-material');
  const label = useLabel(asset), title = label === asset.use ? '其他已登记材料' : label;
  row.append(el('h4', `${title}${ordinal > 1 ? ` · ${ordinal}` : ''}`));
  const note = asset.purpose_note;
  if (typeof note === 'string' && note.trim()) {
    // Keep the complete authored explanation. English/technical notes are not
    // machine-translated or relabelled as a new research conclusion.
    if (/[\u3400-\u9fff]/.test(note)) row.append(el('p', note));
    else row.append(el('p', '该记录的原登记说明为英文，展开可查；本页未生成替代结论。', 'small'),
      disclosure('原登记说明', el('p', note)));
  } else row.append(el('p', '原记录没有单列阅读提要，请打开正文。', 'small'));
  const sources = references(asset);
  for (const [index, source] of sources.entries()) {
    const readable = Number.isSafeInteger(source.bytes) && source.bytes <= 512 * 1024 && !/\.zip$/i.test(source.read_path);
    if (readable) row.append(button(`阅读${title}${sources.length > 1 ? ` · ${index + 1}` : ''}`,
      () => readDetail(source, current, {title, asset}), 'control'));
    else row.append(link('打开原附件', fileUrl(current.ref, source.read_path)));
  }
  const evidence = disclosure('依据、原版本与技术信息');
  for (const source of sources) evidence.append(sourceRow(source, current, (source.path || source.read_path).split('/').at(-1)));
  evidence.append(folded('登记原值', value({id: asset.id, use: asset.use, qualification: asset.qualification})));
  row.append(evidence); return row;
}
function readingBody(text) {
  const view = researchReading(text), node = el('div', undefined, 'product-reading human-document');
  if (view.excerpt) { node.append(el('h4', '结论摘录 · 来自本篇原文'), el('p', view.excerpt, 'human-lead')); }
  if (view.important.length) {
    const warnings = el('section', undefined, 'human-limitations'); warnings.append(el('h4', '本篇原文中的重要限制与反证'));
    for (const part of view.important) warnings.append(el('strong', part.title), ...paragraphs(part.text).map(p => el('p', p)));
    node.append(warnings);
  } else node.append(notice('本篇未识别到单列的限制章节；不能据此认为没有限制。请结合全文与关联更正阅读。'));
  node.append(el('h4', '完整正文'));
  for (const part of view.sections) {
    const section = el('details'); section.open = true;
    section.append(el('summary', part.title), ...paragraphs(part.text).map(p => el('p', p))); node.append(section);
  }
  node.append(folded('完整原始文本', text)); return node;
}
function researchRecords() {
  const result = results.quick;
  if (result?.status !== 'READ') return gap('研究更新', result?.reason);
  const info = result.value, grouped = recordsView(info);
  const panel = card('研究更新', '这里是已保存的研究，不是今天全市场已经检查完毕。');
  if (!grouped.research.length) panel.append(el('p', '本次读取范围没有可识别的 Quick 正文。补充、更正与其他记录仍可查。'));
  for (const entry of grouped.research) {
    const view = researchReading(entry.record.text), row = el('section', undefined, 'human-research-row');
    row.append(el('p', `${entry.label} · ${entry.date}`, 'small muted'), el('h4', view.title || '已保存研究'));
    if (view.excerpt) row.append(el('p', '结论开头 · 原文摘录', 'small muted'), el('p', view.excerpt, 'human-lead'));
    else row.append(el('p', '原文没有单列结论段，打开全文阅读。', 'small'));
    if (view.important.length) {
      row.append(notice(`原文含 ${view.important.length} 个范围、限制或反证章节`));
      const limits = disclosure('范围、限制与反证 · 原文');
      for (const part of view.important) limits.append(el('strong', part.title), ...paragraphs(part.text).map(p => el('p', p)));
      row.append(limits);
    }
    row.append(button('阅读完整分析、反证与限制', () => {
      ++detailGeneration;
      $('detail').replaceChildren(el('h3', view.title || '已保存研究'),
        el('p', `原记录：${localTime(entry.record.createdAt)}；修改：${localTime(entry.record.updatedAt)}`, 'small'),
        readingBody(entry.record.text), link('查看原评论及后续讨论', entry.record.url));
      $('detail').scrollIntoView({behavior: 'smooth', block: 'start'});
    }));
    panel.append(row);
  }
  const extra = disclosure(`简报、补充与其他记录（${grouped.other.length}）`,
    el('p', '包含未按 Quick 标题登记的更正与其他记录；它们没有被删除，也不自动替代原结论。', 'small'));
  for (const entry of grouped.other) appendComment(extra, entry.record);
  panel.append(extra, folded('研究读取范围与时钟', value({pages: info.pages, observedAt: info.observedAt,
    issueUpdatedAt: info.issueUpdatedAt, coverage: info.coverage})));
  return panel;
}
function bookView(target, odds = false) {
  if (reading && selectedAttention) {
    const company = assets?.status === 'READ' ? assets.value.companies.find(c => c.thscode === selectedAttention.code) : null;
    target.append(itemContext(selectedAttention, reading, company));
  }
  if (!reading) { target.append(gap('公司研究目录', results.reading?.reason)); return; }
  if (!assets) { target.append(card('公司研究目录', '正在读取已保存的关联目录…')); loadCompanies(); return; }
  if (assets.status === 'LOADING') { target.append(card('公司研究目录', '正在核对目录原件…')); return; }
  if (assets.status !== 'READ') { target.append(gap('公司研究目录', assets.reason)); return; }
  const current = reading, info = assets.value;
  const panel = card(odds ? '赔率账本 · Odds Book' : '研究账本 · Research Book', odds ?
    '先看保存结果与原复核条件，再读对应研究。未重新计算，不是实时行情。' :
    '先选研究对象，再读正文、更正与历史回应。保存数量不代表研究质量或完成程度。');
  const input = el('input'); input.type = 'search'; input.value = companyQuery;
  input.placeholder = '搜索公司名称、证券代码或已登记研究'; input.setAttribute('aria-label', '搜索公司研究');
  const list = el('div');
  if (selectedCompany) panel.append(disclosure('切换研究对象', input, list)); else panel.append(input, list);
  function drawList() {
    const all = info.companies.map(bookProfile).filter(p => !odds || p.odds.length || p.company.saved_watch);
    const rows = all.filter(p => companyMatches(p.company, input.value));
    const headings = odds ? ['公司', '已存测算', '已保存价格 / 时点', '原复核条件', '重要提示'] :
      ['公司', '已存研究', '更正与限制', '历史回应'];
    const {wrapper, body} = dataTable(`${rows.length} / ${all.length} 个已登记对象；非完整持仓或全历史清单`, headings);
    bookPage = Math.min(bookPage, Math.max(0, Math.ceil(rows.length / 10) - 1));
    const pageRows = rows.slice(bookPage * 10, bookPage * 10 + 10);
    for (const profile of pageRows) {
      const c = profile.company, row = el('tr');
      const open = button(bookCompanyName(c), () => { selectedCompany = c.thscode; if (selectedAttention?.code !== c.thscode) selectedAttention = null; render(); }, 'human-object');
      open.setAttribute('aria-label', `打开 ${bookCompanyName(c)} 的研究与历史`);
      row.append(tableCell('公司', open, el('div', c.thscode, 'small muted')));
      if (odds) {
        const w = c.saved_watch?.ticker === c.thscode ? c.saved_watch : null, valid = w && watchState(w) !== 'UNKNOWN' && watchState(w) !== 'INACTIVE';
        row.append(tableCell('已存测算', el('span', profile.oddsLabel), el('p', profile.responseLabel, 'small')),
          tableCell('已保存价格 / 时点', el('strong', valid ? `${displayDecimal(w.price)} ${w.currency || '币种未提供'}` : '未取得可用价格'),
            el('div', w ? localTime(w.market_timestamp) : '本目录未登记价格观察', 'small')),
          tableCell('原复核条件', el('p', w ? priceCondition(w) : '本目录未登记复核条件'),
            ...(w && watchState(w) === 'TRIGGERED' ? [notice('原观察已触界，需复核业务前提')] : [])),
          tableCell('重要提示', el('p', profile.caution), el('p', '历史结果不自动成为当前有效 Odds。', 'small')));
      } else row.append(tableCell('已存研究', el('p', profile.researchLabel), previewExcerpt(profile, current)),
        tableCell('更正与限制', el('p', profile.caution)), tableCell('历史回应', el('p', profile.responseLabel)));
      body.append(row);
    }
    list.replaceChildren(wrapper);
    if (rows.length > 10) {
      const previous = button('上一页', () => { bookPage--; drawList(); }); previous.disabled = bookPage === 0;
      const next = button('下一页', () => { bookPage++; drawList(); }); next.disabled = (bookPage + 1) * 10 >= rows.length;
      list.append(el('p', `第 ${bookPage + 1} / ${Math.ceil(rows.length / 10)} 页`, 'small'), previous, next);
    }
    if (!rows.length) list.append(el('p', '本次目录中没有匹配对象；不代表没有做过研究或没有新变化。'));
  }
  input.oninput = () => { companyQuery = input.value; bookPage = 0; drawList(); }; drawList();
  const c = info.companies.find(c => c.thscode === selectedCompany);
  if (c) {
    const profile = bookProfile(c), detail = el('section', undefined, 'human-company');
    detail.append(button('收起公司详情，回到账本', () => { selectedCompany = null; selectedAttention = null; render(); }),
      el('h3', `${bookCompanyName(c)} · 已有研究与历史`), el('p', companyStatus(c)), notice(profile.caution),
      el('p', '先看适用更正，再打开需要的版本；旧回应不转移到新版本。', 'small'));
    if (c.saved_watch?.ticker === c.thscode) detail.append(el('p', priceCondition(c.saved_watch)),
      el('p', `原价格观察：${localTime(c.saved_watch.market_timestamp)}；不是当前行情。`, 'small'));
    for (const group of companyMaterials({assets: profile.assets})) {
      const section = el('section', undefined, 'human-material-group'); section.append(el('h4', group.label));
      group.items.forEach((asset, i) => section.append(friendlySource(asset, current, i + 1))); detail.append(section);
    }
    if (c.archives.length) {
      const archive = disclosure(`研究档案（${c.archives.length}）`);
      for (const source of references(c.archives)) archive.append(sourceRow(source, current));
      detail.append(archive);
    }
    detail.append(folded('公司目录原值与接受边界', value({next_step: c.next_step, human_acceptance: c.human_acceptance}))); panel.append(detail);
  }
  panel.append(disclosure('目录依据与覆盖', link('固定目录原件', info.file.url),
    el('p', '目录未给出的当前结论、完成阶段、日期和接受状态不由页面猜测。')));
  target.append(panel);
}

function paintPreview(node, profile, current, source, result) {
  node.replaceChildren();
  if (result.status === 'LOADING') node.append(el('p', '正在读取本页已存正文提要…', 'small'));
  else if (result.status === 'GAP') node.append(notice(humanGap(result.reason)), folded('提要读取诊断', result.reason));
  else {
    if (result.view.title) node.append(el('strong', result.view.title));
    node.append(el('p', result.view.excerpt ? '结论段 · 原文摘录' : result.view.opening ? `原文段落 · ${result.view.opening.title}` : '原文未提供段落提要', 'small'));
    node.append(el('p', result.view.excerpt || result.view.opening?.text || '原文没有单列结论段；打开全文阅读。', 'human-preview-text'));
    node.append(el('p', '已保存原文摘录，不代表现时结论；需一并查看更正和限制。', 'small'));
    node.append(button('打开这份正文', () => { if (current === reading) return readDetail(source, current, {asset: profile.research[0]}); }));
  }
}
function previewExcerpt(profile, current) {
  const node = el('div', undefined, 'human-preview'), source = previewSource(profile);
  if (!source) {
    node.append(el('p', profile.research.length > 1 ? '多份正文并存，打开公司选择版本。' : '打开公司查看已登记资料与原件。', 'small'));
    return node;
  }
  const key = `${current.ref}:${source.read_path}:${source.sha256}`;
  let result = previews.get(key);
  if (!result) {
    result = {status: 'LOADING', targets: new Set()}; previews.set(key, result);
    const finish = value => {
      if (current !== reading) { result.targets.clear(); return; }
      previews.set(key, value);
      // Update only cells belonging to this exact file. Do not replace the
      // search input, user's opened disclosures, selected company or original.
      for (const target of result.targets) paintPreview(target, profile, current, source, value);
      result.targets.clear();
    };
    current.readFile(source).then(file => finish({status: 'READ', view: researchReading(file.text)}))
      .catch(error => finish({status: 'GAP', reason: error.message}));
  }
  if (result.status === 'LOADING') result.targets.add(node);
  paintPreview(node, profile, current, source, result); return node;
}

function bookCompanyName(c) {
  return c.saved_watch?.ticker && c.saved_watch.ticker !== c.thscode ? c.thscode : companyName(c);
}
