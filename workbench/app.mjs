import {REPO, openReading, readQuick, readHealth, loadModules, resumeText, fileUrl} from './reading.mjs';

// Plain local modules, not a plugin runtime. Source strings are text, never HTML.
const labels = {attention: '注意力', research: '研究', odds: 'Odds / Watch', markets: '市场观察', health: '系统健康'};
const hints = {attention: '已保存的研究与明确价格复核事实；不是今天已完成全局扫描的证明。',
  research: '按原件定位恢复研究和更正；索引不等于正文已读。', odds: '原已保存价格条件，不重算 Odds，不构成买卖指令。',
  markets: '观察日与本页读取时间分开；未覆盖不等于没有变化。', health: '独立健康记录与固定读取包并列，不拼成同一时点。'};
const enabled = new Set(Object.keys(labels));
let selected = 'attention', results = {}, reading = null, detailGeneration = 0;
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
function card(title, description, gap = false) {
  const node = el('section', undefined, gap ? 'card gap' : 'card');
  node.append(el('h3', title)); if (description) node.append(el('p', description)); return node;
}
function gap(name, reason) { return card(`${name}：本次未取得`, reason || '未读取，不能当作零。', true); }
function value(object) { return JSON.stringify(object, null, 2); }
function nav() {
  $('nav').replaceChildren();
  for (const [id, label] of Object.entries(labels)) if (enabled.has(id)) {
    const button = el('button', label); button.type = 'button';
    if (id === selected) button.setAttribute('aria-current', 'page');
    button.onclick = () => { selected = id; nav(); render(); };
    $('nav').append(button);
  }
}
for (const [id, label] of Object.entries(labels)) if (id !== 'attention') {
  const wrapper = el('label'); const input = el('input'); input.type = 'checkbox'; input.checked = true;
  input.onchange = () => {
    input.checked ? enabled.add(id) : enabled.delete(id);
    if (!enabled.has(selected)) selected = 'attention';
    nav(); render();
  };
  wrapper.append(input, document.createTextNode(` ${label}`)); $('modules').append(wrapper);
}
function watchCard() {
  if (!reading) return gap('价格复核', results.reading?.reason);
  const watch = reading.payload.lanes?.inbox?.last_qualified_result?.odds_watch?.report?.watch;
  if (!watch || !Array.isArray(watch.active_cases)) return gap('价格复核', '当前读取包没有可展示的原 Watch 明细。');
  const node = card('原已登记的价格复核条件', '以下保留原观察时点及业务前提；不判断现在是否可以行动。');
  const table = el('table'), head = el('tr');
  for (const title of ['对象', '原价格 / 时间', '条件与前提']) head.append(el('th', title));
  table.append(head);
  for (const item of watch.active_cases) {
    const row = el('tr'); row.append(el('td', `${item.company_name || ''}\n${item.ticker || 'UNKNOWN'}`));
    row.append(el('td', item.price_gap || item.price === null || item.price === undefined ?
      `无法判断：${item.price_gap || '价格未知'}` : `${item.price} ${item.currency || ''}\n${item.market_timestamp || '时间未知'}`));
    const cell = el('td');
    const eligible = item.watch_enabled === true && item.status === 'ACTIVE_ODDS_WATCH' &&
      !item.price_gap && item.price !== null && item.price !== undefined;
    const triggered = eligible && Array.isArray(item.triggered_conditions) && item.triggered_conditions.length > 0;
    cell.append(el('strong', triggered ? '原观察已触界，需复核' : '以原条件为准，不推断当前触界'));
    cell.append(el('p', item.next_unreached_condition?.label || '没有下一未触及条件或未提供'));
    if (triggered) cell.append(el('pre', value(item.triggered_conditions)));
    cell.append(el('p', item.prerequisite || '业务前提未提供', 'small')); row.append(cell); table.append(row);
  }
  const scroll = el('div', undefined, 'tablewrap'); scroll.append(table); node.append(scroll); return node;
}
function quickCard() {
  const result = results.quick;
  if (result?.status !== 'READ') return gap('Hosted Quick', result?.reason);
  const info = result.value;
  const node = card('最近保存的 Quick 分析', `只读 #575 最近 ${info.pages.length} 页。读取时间：${info.observedAt}。独立于 R；不据此断言今天已完成研究。`);
  if (!info.items.length) node.append(el('p', '所读页面没有匹配的结果标题，不代表全历史没有研究。'));
  for (const [index, item] of info.items.entries()) {
    const detail = el('details'); detail.open = index === 0;
    detail.append(el('summary', item.text.split('\n')[0].replace(/^## /, '')));
    detail.append(el('p', `保存：${item.createdAt}；修改：${item.updatedAt}`, 'small'));
    detail.append(link('打开实际研究评论', item.url), el('pre', item.text)); node.append(detail);
  }
  return node;
}
function showRefs(target, predicate = () => true) {
  if (!reading) { target.append(gap('原件索引', results.reading?.reason)); return; }
  const input = el('input'); input.type = 'search'; input.placeholder = '搜索文件名或原目录'; input.setAttribute('aria-label', '搜索原件');
  const list = el('div'); target.append(input, list);
  const items = reading.references.filter(predicate);
  function filter() {
    list.replaceChildren();
    const visible = items.filter(item => `${item.read_path} ${item.location}`.toLowerCase().includes(input.value.toLowerCase()));
    list.append(el('p', `${visible.length} 个定位。点击“读取”才取得正文。`, 'muted'));
    for (const item of visible) {
      const row = el('div', undefined, 'ref'); const button = el('button', item.read_path); button.type = 'button';
      button.onclick = () => readDetail(item); row.append(button);
      row.append(el('div', `${item.location} · ${item.bytes ?? '未知'} bytes`, 'small muted'));
      row.append(link('GitHub 原件', fileUrl(reading.ref, item.read_path))); list.append(row);
    }
  }
  input.oninput = filter; filter();
}
async function readDetail(descriptor) {
  const generation = ++detailGeneration, current = reading;
  $('detail').replaceChildren(el('h3', descriptor.read_path), el('p', '正在取得原件并核对字节…'));
  try {
    const file = await current.readFile(descriptor);
    if (generation !== detailGeneration) return;
    const copy = el('button', '复制接续请求', 'control'); copy.type = 'button';
    const request = el('pre', resumeText(current.ref, descriptor)); request.hidden = true;
    copy.onclick = async () => {
      try { await navigator.clipboard.writeText(resumeText(current.ref, descriptor)); copy.textContent = '已复制；尚未执行或写回'; }
      catch { request.hidden = false; copy.textContent = '请复制下方接续文字'; }
    };
    $('detail').replaceChildren(el('h3', file.path), el('p', '选中文件字节数与 SHA-256 一致；不是完整读取包或经济判断验证。', 'muted'),
      link('固定版本原件', file.url), el('pre', file.text), copy, request);
  } catch (error) {
    if (generation !== detailGeneration) return;
    $('detail').replaceChildren(el('h3', '原件未取得或核验未通过'), el('p', error.message));
  }
}
function render() {
  ++detailGeneration; $('detail').replaceChildren(); $('content').replaceChildren();
  $('heading').textContent = labels[selected]; $('subtitle').textContent = hints[selected];
  const target = $('content');
  if (selected === 'attention') { target.append(watchCard(), quickCard()); }
  if (selected === 'research') showRefs(target, item => item.location.startsWith('research.'));
  if (selected === 'odds') {
    target.append(watchCard()); showRefs(target, item => /odds|ODDS-BOOK/.test(item.read_path));
  }
  if (selected === 'markets') {
    if (!reading) target.append(gap('市场观察', results.reading?.reason));
    else {
      for (const name of ['sector', 'stock']) {
        const lane = reading.payload.lanes[name];
        const panel = card(name === 'sector' ? '板块观察' : '个股观察', '原读取摘要；部分覆盖不能等同全市场。');
        panel.append(el('pre', value(lane ? {health: lane.health,
          market_session: lane.last_qualified_result?.market_session ?? null, gaps: lane.gaps,
          latest_attempt: lane.latest_attempt} : {gap: 'NOT_PROVIDED'}))); target.append(panel);
      }
      showRefs(target, item => item.location.startsWith('lanes.sector.') || item.location.startsWith('lanes.stock.') || /radar\//.test(item.read_path));
    }
  }
  if (selected === 'health') {
    if (reading) {
      const panel = card('固定读取包的检查窗口', '这是读取检查窗口，不是行情新鲜度或研究质量认证。');
      panel.append(el('pre', value({checks: reading.payload.checks, capability_gaps: reading.payload.capability_gaps}))); target.append(panel);
    } else target.append(gap('固定读取包', results.reading?.reason));
    const health = results.health;
    if (health?.status === 'READ') {
      const panel = card('独立系统健康记录', `修改：${health.value.updatedAt}；读取：${health.value.observedAt}。不由标题或Issue关闭推断健康。`);
      panel.append(link('实际健康 Issue', health.value.url), el('pre', health.value.text)); target.append(panel);
    } else target.append(gap('独立健康', health?.reason));
  }
}
async function refresh() {
  $('refresh').disabled = true; ++detailGeneration;
  reading = null; results = {}; $('detail').replaceChildren();
  $('content').replaceChildren(card('正在读取', '每轮固定一份 R；Quick 和健康记录分别保留自己的时点。'));
  $('identity').textContent = '读取中；不启动采集、研究或任务。';
  try {
    results = await loadModules({reading: () => openReading(), quick: () => readQuick(), health: () => readHealth()});
    reading = results.reading.status === 'READ' ? results.reading.value : null;
    $('identity').textContent = reading ? `R ${reading.ref} · 代码 ${reading.payload.code_commit} · 本页读取 ${reading.checkedAt}` :
      `固定读取包未取得：${results.reading.reason}；独立已取得内容仍可查看。`;
    const recheck = Date.parse(reading?.payload.checks?.recheck_after);
    if (reading && Number.isFinite(recheck) && Date.now() > recheck) $('identity').append(el('p', '读取包已超过自身复查窗口；本页不会自动重跑生产。', 'gap'));
    render();
  } finally { $('refresh').disabled = false; }
}
$('refresh').onclick = refresh; nav(); refresh();
