/** Pure presentation helpers. No price calculation, scoring or state mutation. */
export function locations(item) { return item.locations || [item.location || '']; }
export function referenceMatches(item, query) {
  const text = [item.read_path, item.path, ...locations(item)].filter(Boolean).join(' ').toLowerCase();
  return text.includes(query.trim().toLowerCase());
}
export function watchState(item) {
  if (item?.watch_enabled !== true || item.status !== 'ACTIVE_ODDS_WATCH') return 'INACTIVE';
  if (item.price_gap || item.price === null || item.price === undefined || item.price === '' ||
      !Number.isFinite(Number(item.price)) || Number(item.price) <= 0 ||
      typeof item.market_timestamp !== 'string' || !Number.isFinite(Date.parse(item.market_timestamp)) ||
      !/(?:Z|[+-]\d{2}:\d{2})$/.test(item.market_timestamp)) return 'UNKNOWN';
  if (!Array.isArray(item.triggered_conditions)) return 'UNKNOWN';
  if (item.triggered_conditions.length) return item.triggered_conditions.every(c => c?.attention_triggered === true) ? 'TRIGGERED' : 'UNKNOWN';
  const next = item.next_unreached_condition;
  return next?.attention_triggered === false && next.condition_state === 'ABOVE_CONDITION' ? 'NOT_TRIGGERED' : 'UNKNOWN';
}
export function watchSummary(payload) {
  const watch = payload?.lanes?.inbox?.last_qualified_result?.odds_watch?.report?.watch;
  if (!Array.isArray(watch?.active_cases)) return {available: false, rows: [], counts: null};
  const rows = watch.active_cases.map(item => ({item, state: watchState(item)}));
  const counts = {enabled: 0, evaluated: 0, triggered: 0, unknown: 0, inactive: 0};
  for (const row of rows) {
    if (row.state === 'INACTIVE') { counts.inactive++; continue; }
    counts.enabled++;
    if (row.state === 'UNKNOWN') counts.unknown++;
    else { counts.evaluated++; if (row.state === 'TRIGGERED') counts.triggered++; }
  }
  return {available: true, rows, counts, declared: watch.active_case_count,
    countMismatch: Number.isSafeInteger(watch.active_case_count) && watch.active_case_count !== counts.enabled};
}
export function companyName(company) { return company.saved_watch?.company_name || company.thscode; }
export function companyMatches(company, query) {
  return [companyName(company), company.thscode, ...company.assets.flatMap(a =>
    [a.id, a.use, a.purpose_note, a.source?.path])].filter(Boolean).join(' ').toLowerCase().includes(query.trim().toLowerCase());
}
