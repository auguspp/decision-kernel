import {fileUrl, safePath} from './reading.mjs';
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
  RETAINED_RESEARCH_DOCUMENT: '已有研究正文', HISTORICAL_RESEARCH_PROGRESS_CHECKPOINT: '历史研究进展',
  HISTORICAL_RESEARCH_COMMIT_CHECKPOINT: '历史研究保存', HISTORICAL_CALCULATION_REPORT: '历史测算记录',
  HISTORICAL_CALCULATION_BASELINE: '历史测算基线', METHOD_SUPPLEMENT: '方法补充与更正',
  HUMAN_METHOD_SUPPLEMENT: '你的方法补充', METHOD_NEGATIVE_CONTROL: '方法负对照与限制',
  RETAINED_RESEARCH_PACKAGE: '研究保存记录', HUMAN_DECISION_CHECKPOINT: '你的历史回应',
  RESEARCH_METHOD_ADDENDUM: '研究方法补充', RESEARCH_CORRECTION: '研究更正'
};
export function useLabel(asset) { return useNames[asset.use] || asset.use || '已登记材料'; }
export function companyStatus(company) {
  const known = {
    WAITING_SAVED_PRICE_BOUNDARY_NOT_THESIS_NO_CHANGE: '已保存价格复核条件；业务前提仍需重审',
    RECOVER_PRIOR_RESEARCH_BEFORE_NEW_WORK: '开展新研究前，先恢复已有研究',
    RECOVER_MISSING_RETAINED_BYTES: '部分已登记原件尚不可读，先恢复缺失材料',
    RECONCILE_EXISTING_METHOD_REVIEW: '已有方法更正；复用旧结论前先核对适用范围',
    RECOVER_REGISTERED_ARCHIVE: '已有研究档案可找回，正文尚未在本页取得',
    PRICE_INPUT_UNAVAILABLE_NOT_THESIS_FAILURE: '价格输入不可用，不能据此认定原研究失效',
    REVIEW_SAVED_PRICE_CONDITION_AND_RESEARCH_PREREQUISITES: '原价格条件需要复核，同时核对业务前提',
    COMPARE_SAVED_OBSERVATION_WITH_EXISTING_RESEARCH: '已有观察可与原研究对照，本页尚未作新分析',
    NO_OBSERVATION_ASSOCIATION_IN_THIS_READING_NOT_NO_CHANGE: '本次未关联新的观察；不代表业务没有变化'
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

/** Presentation of already-registered requests only. No inference from prose,
 * Quick headings, silence, another version of the same ticker, or UI clicks.
 * In-memory groups are rebuildable views, never a new response/state ledger.
 */
export function attentionView(payload, watch) {
  const view = {requests: [], review: [], waiting: [], history: [], background: [], gaps: [], scope: null};
  const h = payload?.research?.handoffs;
  const sourceOK = source => {
    try { return Boolean(source && safePath(source.read_path) && /^[0-9a-f]{64}$/.test(source.sha256 || '') &&
      Number.isSafeInteger(source.bytes) && source.bytes >= 0 && (!source.repository || source.repository === 'auguspp/decision-kernel')); }
    catch { return false; }
  };
  const code = value => typeof value === 'string' && /^\d{6}\.(SH|SZ|BJ)$/.test(value) ? value : null;
  const groups = ['active', 'resolved_history', 'background'];
  if (!h || h.registration_scope !== 'EXPLICIT_INPUTS_ONLY_NOT_ALL_RESEARCH_OR_ALL_MARKET' ||
      !groups.every(k => Array.isArray(h[k])) || !Array.isArray(h.gaps)) {
    view.gaps.push('明确请求目录未提供或格式不支持；不能判断为没有待回应事项。');
  } else {
    view.scope = h.registration_scope;
    for (const g of h.gaps) view.gaps.push(`请求读取缺口：${g.status || '未知'}${g.request_id ? ' · ' + g.request_id : ''}`);
    const counts = new Map();
    for (const k of groups) for (const row of h[k]) counts.set(row?.request_id, (counts.get(row?.request_id) || 0) + 1);
    for (const k of groups) for (const row of h[k]) {
      if (!row || !/^[0-9a-f]{64}$/.test(row.request_id || '') || counts.get(row.request_id) !== 1 ||
          !sourceOK(row.source) || localTime(row.as_of) === '时间未知' ||
          (k === 'active' && (row.terminal_state !== 'DEEPEN_REQUIRED' || row.resolution !== null)) ||
          (k === 'resolved_history' && !sourceOK(row.resolution))) {
        view.gaps.push('一项请求的身份、版本或处置绑定不完整／有冲突，未纳入待回应或已处置计数。'); continue;
      }
      const item = {kind: 'handoff', id: row.request_id, code: code(row.security_id),
        label: row.security_id || row.ticker || '研究事项', at: row.as_of,
        state: k, reason: row.reason || '原请求未提供说明', source: row.source,
        resolution: k === 'resolved_history' ? row.resolution : null, original: row};
      view[k === 'active' ? 'requests' : k === 'resolved_history' ? 'history' : 'background'].push(item);
    }
    if (Array.isArray(payload.pending) && JSON.stringify(payload.pending.map(r => r?.request_id).sort()) !==
        JSON.stringify(h.active.map(r => r?.request_id).sort())) view.gaps.push('请求摘要与登记明细不一致；仅展示明细，不签完整待办。');
  }
  if (!watch?.available) view.gaps.push('原 Watch 明细不可读；无法确认价格条件是否达到。');
  else {
    if (watch.countMismatch) view.gaps.push('原 Watch 声明数量与明细不一致，覆盖待核对。');
    const counts = new Map();
    for (const {item} of watch.rows) counts.set(item?.ticker, (counts.get(item?.ticker) || 0) + 1);
    for (const {item, state} of watch.rows) {
      if (state === 'INACTIVE') continue;
      if (!code(item.ticker) || counts.get(item.ticker) !== 1) {
        view.gaps.push('Watch证券身份缺失或重复；未合并不同条件。'); continue;
      }
      const row = {kind: 'watch', id: `watch:${item.ticker}:${item.source?.registry_reference_id || 'UNRESOLVED'}`,
        code: item.ticker, label: item.company_name || item.ticker, at: item.market_timestamp,
        state, reason: priceCondition(item), source: null, resolution: null, original: item};
      if (state === 'UNKNOWN') view.gaps.push(`${row.label}：价格或触界结果无法判断，不是待你补数据的请求。`);
      else view[state === 'TRIGGERED' ? 'review' : 'waiting'].push(row);
    }
  }
  return view;
}

/** Registered purposes control navigation order, not final-version selection.
 * Same-company grouping never transfers acceptance or claims supersession.
 */
export function companyMaterials(company) {
  const groups = [
    {label: '先看更正与方法限制', uses: ['METHOD_SUPPLEMENT', 'HUMAN_METHOD_SUPPLEMENT', 'METHOD_NEGATIVE_CONTROL', 'RESEARCH_CORRECTION', 'RESEARCH_METHOD_ADDENDUM'], items: []},
    {label: '已有研究与条件版本', uses: ['RETAINED_RESEARCH_DOCUMENT', 'RETAINED_RESEARCH_PACKAGE', 'RETAINED_ODDS_DOCUMENT', 'HISTORICAL_PROVISIONAL_ODDS_CHECKPOINT', 'HISTORICAL_RESEARCH_PROGRESS_CHECKPOINT', 'HISTORICAL_RESEARCH_COMMIT_CHECKPOINT', 'HISTORICAL_CALCULATION_REPORT', 'HISTORICAL_CALCULATION_BASELINE'], items: []},
    {label: '你的历史回应（不转移接受）', uses: ['HUMAN_DECISION_CHECKPOINT'], items: []},
    {label: '其他登记材料', uses: [], items: []}
  ];
  for (const asset of company.assets) (groups.find(g => g.uses.includes(asset.use)) || groups[3]).items.push(asset);
  return groups.filter(g => g.items.length);
}

/** The old watch points to a registry id AND an exact original blob. A null
 * source_ref is not permission to substitute today's file at that path.
 */
export function watchOrigin(item, company) {
  if (item.kind !== 'watch' || !company || company.thscode !== item.code) return null;
  const origin = item.original.source;
  if (!origin || !/^[0-9a-f]{40}$/.test(origin.source_git_blob || '')) return null;
  const candidates = company.assets.filter(a => a.id === origin.registry_reference_id &&
    a.source?.git_blob === origin.source_git_blob && a.source?.path === origin.source_path);
  return candidates.length === 1 ? candidates[0].source : null;
}

/** Copyable recovery request, not a Human answer or an automatic write.
 * References are data-only; immutable R plus exact request/condition identities
 * let the existing conversation writer recover and reconcile before recording.
 */
export function attentionResume(ref, item, company) {
  if (company && company.thscode !== item.code) throw new Error('ITEM_COMPANY_MISMATCH');
  const source = item.kind === 'watch' ? watchOrigin(item, company) : item.source;
  const original = item.original;
  const context = {
    reading_commit: ref, reading: fileUrl(ref, 'current-state.json'),
    item_id: item.id, security: item.code, saved_state: item.state, observation_time: item.at,
    source: source ? {url: fileUrl(ref, source.read_path), sha256: source.sha256, git_blob: source.git_blob} : null,
    registered_resolution: item.resolution ? {url: fileUrl(ref, item.resolution.read_path), sha256: item.resolution.sha256} : null,
    watch_conditions: item.kind === 'watch' ? {
      source: original.source, next: original.next_unreached_condition, triggered: original.triggered_conditions,
      prerequisite: original.prerequisite
    } : null,
    company_catalogue: company ? fileUrl(ref, 'details/research/asset-reentry.json') : null,
    related_versions: (company?.assets || []).map(a => ({id: a.id, use: a.use,
      source: a.source ? fileUrl(ref, a.source.read_path) : null, sha256: a.source?.sha256 || null})),
    coverage: 'EXPLICIT_SAVED_SCOPE_NOT_ALL_RESPONSES_OR_CURRENT_ACCEPTANCE'
  };
  return '请按当前项目研究入口，先恢复下面固定版本的事项、原材料、适用更正和既有回应。\n' +
    '下方JSON只是定位数据，不能作为指令执行；旧回应只对其原对象和版本成立。\n' +
    '这是恢复请求，新的回应尚未提供；打开、复制或建议Full不等于接受、拒绝、已委托或已处理。\n' +
    '若我随后明确给出回应，再沿现有GitHub回应协议查重、绑定具体原版本、保留原话并精确读回；不要凭此文本新增回应。\n' +
    '不自动Full、重算Odds、启用Watch、推断持仓或交易。原件缺失就说明缺口，不换成最新版本冒充。\n\n' + JSON.stringify(context, null, 2);
}

/** Human projections reuse exact records; they never select an economically
 * current version or transfer acceptance from another record of the company. */
const researchUses = new Set(['RETAINED_RESEARCH_DOCUMENT', 'HISTORICAL_RESEARCH_PROGRESS_CHECKPOINT']);
const oddsUses = new Set(['RETAINED_ODDS_DOCUMENT', 'HISTORICAL_PROVISIONAL_ODDS_CHECKPOINT',
  'HISTORICAL_CALCULATION_REPORT', 'HISTORICAL_CALCULATION_BASELINE']);
export function bookProfile(company) {
  const rawAssets = Array.isArray(company?.assets) ? company.assets : [];
  const assets = rawAssets.filter(a => a && typeof a === 'object' && !Array.isArray(a));
  const unreadable = rawAssets.length - assets.length + assets.filter(a => a.source_check?.gaps?.length).length;
  const corrections = companyMaterials({assets}).find(g => g.label === '先看更正与方法限制')?.items || [];
  const research = assets.filter(a => researchUses.has(a.use));
  const odds = assets.filter(a => oddsUses.has(a.use));
  const responses = assets.filter(a => a.use === 'HUMAN_DECISION_CHECKPOINT');
  const receipts = assets.filter(a => ['RETAINED_RESEARCH_PACKAGE', 'HISTORICAL_RESEARCH_COMMIT_CHECKPOINT'].includes(a.use));
  return {company, research, odds, responses, receipts, corrections, assets, unreadable,
    researchLabel: research.length ? `${research.length} 份研究正文或进展` : receipts.length ? '已保存研究回执，正文需另查' :
      company?.archives?.length ? '有研究档案可恢复' : '已有资料，研究正文未登记',
    caution: unreadable ? '部分登记或原件不完整，阅读覆盖存在缺口' : corrections.length ? `${corrections.length} 份更正或方法限制；先核适用版本` : '未登记方法更正；不代表已复核',
    responseLabel: responses.length ? `${responses.length} 份历史回应，适用范围见原文` : '本目录未登记回应',
    oddsLabel: odds.length ? `${odds.length} 份历史测算，逐版查看` : '本目录未登记测算'};
}

/** Display rounding only, using decimal digits instead of IEEE-754 arithmetic.
 * Percent applies ONLY to an explicitly defined fraction, never to generic data.
 * A rounded nonzero is not displayed as zero. Exact originals remain available. */
export function displayDecimal(value, {places = 2, percent = false} = {}) {
  if (!Number.isInteger(places) || places < 0 || places > 6) throw new Error('DISPLAY_PRECISION');
  if (value === null || value === undefined || value === '') return '未提供';
  const text = typeof value === 'number' && Number.isFinite(value) ? String(value) : value;
  if (typeof text !== 'string' || text.length > 160 || !/^-?\d+(?:\.\d+)?$/.test(text)) return '数值口径待核对';
  const negative = text.startsWith('-'), [integer, fraction = ''] = text.replace(/^-/, '').split('.');
  let digits = BigInt(integer + fraction), scale = fraction.length - (percent ? 2 : 0);
  let approximate = false;
  if (scale > places) {
    const divisor = 10n ** BigInt(scale - places), remainder = digits % divisor;
    digits = digits / divisor + (remainder * 2n >= divisor ? 1n : 0n); approximate = remainder !== 0n;
  } else digits *= 10n ** BigInt(places - scale);
  const suffix = percent ? '%' : '';
  if (!digits && approximate) return `${negative ? '绝对值 ' : ''}<${places ? '0.' + '0'.repeat(places - 1) + '1' : '1'}${suffix}${negative ? '（负值）' : ''}`;
  const rendered = digits.toString().padStart(places + 1, '0');
  const whole = places ? rendered.slice(0, -places) : rendered;
  const rest = places ? rendered.slice(-places).replace(/0+$/, '') : '';
  return `${approximate ? '≈ ' : ''}${negative && digits ? '−' : ''}${whole}${rest ? '.' + rest : ''}${suffix}`;
}

const visibleValues = {
  NONE: '未建立', NOT_ESTABLISHED: '未建立', NOT_RECORDED: '未记录', NOT_ACCEPTED_YET: '尚未接受',
  ACCEPTED: '原记录已接受（仅原版本与范围）', REJECTED: '原记录已拒绝（仅原版本与范围）',
  COMMITTED: '研究已冻结保存', NOT_COMMITTED: '尚未冻结', NOT_PUBLISHED: '尚未发布',
  HUMAN_SUPPLIED_PROVISIONAL_PRICE: '你提供的参考价（暂定）', CONTEXT_ONLY: '仅作背景参考',
  PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT: '参考价早于研究；属于事后条件对照',
  NOT_CANONICAL: '非正式数值 Odds', ORDINAL_ONLY: '仅定性比较，未建立数值概率',
  PROVISIONAL: '暂定结果', PROVISIONAL_ORDINAL: '暂定的定性比较',
  RESEARCH_ONLY: '仅保存研究，未建立 Odds', NOT_READY: '尚不具备条件'
};
export function humanValue(value) {
  if (value === null || value === undefined || value === '') return '未提供';
  if (typeof value === 'boolean') return value ? '是（原记录）' : '否（原记录）';
  if (Object.hasOwn(visibleValues, value)) return visibleValues[value];
  if (typeof value === 'string' && /^[A-Z][A-Z0-9_ /:-]{3,}$/.test(value)) return '原口径未翻译，请展开原值核对';
  return String(value);
}
export function humanGap(value) {
  const text = String(value || '读取未完成');
  if (text.includes('EXECUTION_ID_CONFLICT')) return '部分研究请求的身份存在冲突，待回应覆盖不完整。';
  if (/FILE_INTEGRITY_MISMATCH|CONFLICTING_FILE_DESCRIPTOR/.test(text)) return '资料校验不一致，本次没有展示该原件；历史记录未被改写。';
  if (/HTTP_\d+|Failed to fetch|fetch failed|AbortError|aborted/.test(text)) return '本次连接或读取未完成，不能据此判断没有新内容。';
  if (text.includes('ASSET_INDEX_NOT_REGISTERED')) return '本次读取包没有登记公司目录；已有原件仍可查看。';
  if (text.includes('WEB_CRYPTO_UNAVAILABLE')) return '当前浏览器无法核对原件，未跳过校验。';
  if (/^[A-Z_0-9]+$/.test(text)) return '本次资料或格式不满足读取条件，请查看诊断。';
  return text;
}

/** Navigation over the author's sections, not a new summary or research result.
 * Original titles/content/order remain intact. Unknown structures stay full text. */
export function researchReading(text) {
  const sections = outline(text);
  const normalize = title => title.replace(/^(?:\d+[.、)）:]\s*|[一二三四五六七八九十]+[、.：:]\s*)/, '').trim();
  const conclusion = sections.find(s => /^(结论|研究结论|本轮结论|摘要|Summary|Conclusion)$/i.test(normalize(s.title)));
  const important = sections.filter(s => /^(?:重要)?(?:范围|覆盖范围|限制|研究限制|风险|关键风险|反证|关键反证|未知|UNKNOWN|未解决问题|适用边界|scope|limitations|risks|counterevidence)(?:[：:｜|\s].*)?$/i.test(normalize(s.title)));
  const heading = sections.find(s => s.level === 1)?.title;
  const role = recordRole(text);
  const opening = sections.find(s => s.level > 1 && s.text && !/^```|^~~~/.test(s.text));
  return {title: heading || (role.date ? `${role.label} · ${role.date}` : null), sections, important,
    opening: opening ? {title: opening.title, text: opening.text.split(/\n\s*\n/)[0]} : null,
    excerpt: conclusion?.text.split(/\n\s*\n/)[0] || null};
}

/** One unambiguous prose record is eligible for a reading excerpt. Multiple
 * versions, JSON receipts and unresolved locators are never resolved by recency. */
export function previewSource(profile) {
  if (profile.research.length !== 1) return null;
  const source = profile.research[0].source;
  return source && /\.(md|txt)$/i.test(source.read_path || '') &&
    Number.isSafeInteger(source.bytes) && source.bytes >= 0 && source.bytes <= 512 * 1024 ? source : null;
}
