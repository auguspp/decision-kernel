/** Display-only projections of retained material. Never a researcher or new state store.
 * Original text/values remain available. A recognized heading is a display role,
 * not proof of research acceptance, current relevance, or a pending Human action.
 */
export function localTime(value) {
  if (typeof value !== 'string' || !/(Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) return '时间未知';
  return new Intl.DateTimeFormat('zh-CN', {timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}).format(new Date(value)) + ' 北京时间';
}
function day(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) &&
    new Date(value).toISOString().slice(0, 10) === value;
}
export function recordRole(text) {
  const first = String(text).trimStart().split('\n')[0].trim();
  const match = /^## (DAILY HOSTED QUICK|MANUAL E2E HOSTED QUICK|MANUAL E2E BRIEF) (\d{4}-\d{2}-\d{2})$/.exec(first);
  if (!match || !day(match[2])) return {kind: 'supplement', label: '补充或其他记录', date: null};
  return {kind: match[1].endsWith('BRIEF') ? 'brief' : 'research',
    label: match[1] === 'DAILY HOSTED QUICK' ? '日常 Quick' : match[1].endsWith('BRIEF') ? '手动简报' : '手动 Quick', date: match[2]};
}
/** Locate authored ATX sections for navigation, NOT a general Markdown renderer.
 * Fenced/indented code is not a heading. Formatting and raw HTML remain literal text.
 */
export function outline(text) {
  const lines = String(text).split('\n'), sections = [];
  let fence = null, current = {title: '正文', level: 0, lines: []};
  for (const line of lines) {
    const marker = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line);
    if (fence) {
      current.lines.push(line);
      if (marker && marker[1][0] === fence[0] && marker[1].length >= fence.length && !marker[2].trim()) fence = null;
      continue;
    }
    if (marker) { fence = marker[1]; current.lines.push(line); continue; }
    const heading = /^ {0,3}(#{1,6})[ \t]+(.+?)\s*$/.exec(line);
    if (heading) {
      if (current.lines.length || current.level) sections.push({...current, text: current.lines.join('\n').trim()});
      current = {title: heading[2], level: heading[1].length, lines: []};
    } else current.lines.push(line);
  }
  if (current.lines.length || current.level) sections.push({...current, text: current.lines.join('\n').trim()});
  return sections.map(({lines: _, ...section}) => section);
}
export function recordView(record) {
  const role = recordRole(record.text), sections = outline(record.text);
  const title = sections.find(s => s.level === 1)?.title || String(record.text).trim().split('\n')[0].replace(/^#+\s*/, '') || '已保存记录';
  const conclusion = sections.find(s => /^(结论|研究结论|本轮结论|摘要|Summary|Conclusion)$/i.test(s.title));
  return {record, ...role, title, sections,
    // Exact first paragraph, never a model-generated summary or authoritative selection.
    excerpt: conclusion?.text.split(/\n\s*\n/)[0] || null};
}
export function recordsView(info) {
  const unique = new Map();
  for (const record of [...(info?.items || []), ...(info?.supplements || [])]) unique.set(record.id, record);
  const rows = [...unique.values()].sort((a,b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt) || b.id - a.id).map(recordView);
  return {research: rows.filter(r => r.kind === 'research'), other: rows.filter(r => r.kind !== 'research')};
}
const useNames = {
  RETAINED_ODDS_DOCUMENT: '历史 Odds 文档', HISTORICAL_PROVISIONAL_ODDS_CHECKPOINT: '历史条件测算',
  RETAINED_RESEARCH_PACKAGE: '研究保存记录', HUMAN_DECISION_CHECKPOINT: '你的历史回应',
  RESEARCH_METHOD_ADDENDUM: '研究方法补充', RESEARCH_CORRECTION: '研究更正'
};
export function useLabel(asset) { return useNames[asset.use] || asset.use || '已登记材料'; }
export function companyStatus(company) {
  const known = {
    WAITING_SAVED_PRICE_BOUNDARY_NOT_THESIS_NO_CHANGE: '已保存价格复核条件；业务前提仍需重审',
    RECOVER_PRIOR_RESEARCH_BEFORE_NEW_WORK: '开展新研究前，先恢复已有研究'
  };
  return known[company.next_step] || '已有资料可继续阅读；当前处置请查原记录';
}
export function priceCondition(item) {
  const c = item?.next_unreached_condition;
  if (!c) return '下一价格条件未提供';
  const labels = {RE_UNDERWRITE: '业务前提复核', CONDITIONAL_FIRST_ENTRY_CONDITION: '首笔参与条件讨论'};
  const label = labels[c.kind] || '原登记价格复核';
  const numeric = value => typeof value === 'string' && /^\d+(?:\.\d+)?$/.test(value);
  if (numeric(c.upper_price) && (c.lower_price === null || c.lower_price === undefined || numeric(c.lower_price))) {
    const band = numeric(c.lower_price) ? `${c.lower_price}–${c.upper_price}` : c.upper_price;
    return `${label} · ${band} ${item.currency || '币种未知'}（原条件，不是买入指令）`;
  }
  return c.label || '原价格条件口径待核对';
}
/** Only existing registered summaries; no implicit URL discovery or new source. */
export function marketEntries(reading) {
  const specs = [
    ['板块变化', /^details\/sector\/\d+\/summary\.md$/],
    ['板块持续状态', /^details\/sector\/\d+\/context\/context\.json$/],
    ['个股观察', /^details\/stock\/\d+\/reading\/stock-reading\.json$/],
    ['概念观察', /^details\/radar\/tdx-concept\/summary\.md$/],
    ['新闻窗口', /^details\/radar\/news-daily\.md$/]
  ];
  return specs.map(([label, match]) => {
    const hits = reading.references.filter(r => match.test(r.read_path));
    return {label, source: hits.length === 1 ? hits[0] : null,
      gap: hits.length > 1 ? '同用途存在多个原件，请从完整索引选择' : '本次读取包未登记此摘要'};
  });
}
export function paragraphs(text) { return String(text).split(/\n\s*\n/).filter(t => t.trim()); }
function scalar(value) { return value === null || ['string','number','boolean'].includes(typeof value); }
/** A narrow typed display, not a generic JSON explorer/validator. Unknown formats
 * keep full original text instead of guessing labels, units, probability or status.
 */
export function documentView(text) {
  let data;
  try { data = JSON.parse(text); } catch { return null; }
  const a = data?.artifact;
  if (a?.adapter_version === 'probability-free-conditional-worlds-v1' &&
      a.schema_version === 1 && a.calculation_convention === 'UNDISCOUNTED_NOMINAL_CUMULATIVE_PAYOFF_V1' &&
      Array.isArray(a.world_results) && a.world_results.length <= 100 && Array.isArray(a.limitations) &&
      a.limitations.every(v => typeof v === 'string')) {
    const declared = a.conditional_worlds?.world_set?.worlds;
    if (!Array.isArray(declared) || declared.length > 100 ||
        !declared.every(w => w && typeof w.id === 'string' && typeof w.name === 'string') ||
        !a.world_results.every(w => w && typeof w.world_id === 'string') ||
        new Set(declared.map(w => w.id)).size !== declared.length) return null;
    const rows = a.world_results.map(w => {
      const original = declared.find(d => d.id === w.world_id && d.name === w.world_name);
      if (!original || !Array.isArray(original.operating_conditions) || !original.operating_conditions.every(v => typeof v === 'string')) return null;
      if (![w.world_name, w.terminal_equity_value_per_share, w.total_payoff_per_share, w.undiscounted_holding_period_return].every(scalar)) return null;
      return {name: w.world_name, terminal: w.terminal_equity_value_per_share, payoff: w.total_payoff_per_share,
        returnFraction: w.undiscounted_holding_period_return, conditions: original.operating_conditions};
    });
    if (rows.some(r => !r) || new Set(a.world_results.map(w => w.world_id)).size !== rows.length) return null;
    const p = a.price_context || {};
    if (![p.price, p.currency, p.price_timestamp, p.price_convention, a.price_clock_semantics,
      a.valuation_horizon_date, a.odds_status, a.canonical_odds, a.cardinal_probability, a.human_acceptance]
      .every(v => v === undefined || scalar(v))) return null;
    return {kind: 'conditional', title: '历史条件情景',
      notice: '下列为原文件已计算结果；不是当前估值、概率加权收益或参与建议。本页未重新计算。',
      facts: [['原参考价', p.price], ['币种', p.currency], ['参考价时点', p.price_timestamp],
        ['价格来源口径', p.price_convention], ['价格与研究时序', a.price_clock_semantics],
        ['原研究期限', a.valuation_horizon_date], ['原 Odds 状态', a.odds_status],
        ['原 canonical Odds', a.canonical_odds], ['原概率状态', a.cardinal_probability],
        ['原 Human 接受状态', a.human_acceptance]],
      limits: a.limitations, rows};
  }
  if (data?.format === 'research-commit-only-v0' &&
      [data.research_status, data.odds_status, data.publication_status, data.human_acceptance, data.semantics]
        .every(v => v === undefined || scalar(v))) return {kind: 'receipt', title: '研究保存回执',
    notice: '这是保存操作的回执，不是研究正文，也不代表研究已被接受。', rows: [], limits: [],
    facts: [['保存状态',data.research_status],['原 Odds 状态',data.odds_status],['原发布状态',data.publication_status],
      ['原 Human 接受状态',data.human_acceptance],['原操作含义',data.semantics]]};
  return null;
}
