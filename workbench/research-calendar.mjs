/** Same-R saved appointments only. No provider fetch, reminders or research. */
import {fileUrl} from './reading.mjs';
const hash = v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const day = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) &&
  Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10) === v;
const instant = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v));
const none = v => v && ['signal_transition_authority','human_attention_authority','research_authority','investment_authority'].every(k => v[k] === 'NONE');
function require(ok, reason) { if (!ok) throw new Error(reason); }

/** Shape and saved identity checks; not a duplicate source parser or truth test. */
export function calendarView(text, saved, now = new Date()) {
  const c = JSON.parse(text);
  require(saved?.version === 'research-calendar-reading-v1' && saved.status === 'SAVED_REVIEWED_CALENDAR' &&
    saved.meaning === 'SAVED_APPOINTMENTS_NOT_RELEASE_OR_RESEARCH' && none(saved) &&
    c?.version === 'bls-research-calendar-v1' && hash(c.calendar_hash) && c.calendar_hash === saved.calendar_hash &&
    c.as_of === saved.as_of && instant(c.as_of) && instant(saved.checked_at) && Date.parse(c.as_of) <= Date.parse(saved.checked_at) &&
    ['research','human_attention','investment','execution'].every(k => c.authority?.[k] === 'NONE'), 'CALENDAR_SAVED_IDENTITY');
  require(c.coverage === 'THREE_BLS_SERIES_IN_REVIEWED_EXCERPT_NOT_COMPLETE_CALENDAR' && saved.coverage === c.coverage &&
    c.company_events === 'NOT_IMPLEMENTED_NO_FOLLOW_OR_HOLDING_INFERENCE' &&
    c.source?.observation_kind === 'REVIEWED_WEB_EXCERPT' && c.source.custody === 'EXCERPT_BYTES_ONLY_NOT_ORIGINAL_HTTP_BODY' &&
    /^https:\/\/www\.bls\.gov\/schedule\/\d{4}\/\d{2}_sched_list\.htm$/.test(c.source.url) &&
    c.source.published_at === 'UNKNOWN' && c.source.retrieved_at === 'UNKNOWN' && instant(c.source.reviewed_at) &&
    Date.parse(c.source.reviewed_at) <= Date.parse(c.as_of) && hash(c.source.sha256) &&
    c.source.sha256 === saved.files?.['source.txt']?.sha256 &&
    Number.isSafeInteger(c.source.bytes) && c.source.bytes > 0 && c.source.bytes <= 65536 &&
    c.source.bytes === saved.files['source.txt'].bytes, 'CALENDAR_SOURCE_SCOPE');
  require(c.window?.basis === 'SOURCE_DATE' && c.window.timezone === 'America/New_York' &&
    day(c.window.start) && day(c.window.end) && c.window.start <= c.window.end &&
    (Date.parse(c.window.end)-Date.parse(c.window.start))/86400000 < 42 &&
    ['basis','timezone','start','end'].every(k => c.window[k] === saved.window?.[k]) &&
    typeof c.local_timezone === 'string' && Array.isArray(c.events) && c.events.length <= 64 &&
    c.events.length === saved.event_count && Number.isSafeInteger(c.parsed_rows) && c.parsed_rows > 0 && c.parsed_rows <= 64 &&
    c.excluded_outside_window === c.parsed_rows-c.events.length &&
    c.status === (c.events.length ? 'SCHEDULED_EVENTS_IN_WINDOW' : 'NO_SELECTED_EVENTS_IN_WINDOW'), 'CALENDAR_WINDOW');
  new Intl.DateTimeFormat('en-CA', {timeZone:c.local_timezone}).format(now); // Reject unavailable zone/clock; no fixed offset fallback.
  const seen = new Set();
  for (const e of c.events) {
    require(/^BLS:(employment|cpi|ppi):\d{4}-\d{2}$/.test(e?.event_id) && !seen.has(e.event_id) &&
      typeof e.title === 'string' && e.title.length > 0 && e.title.length <= 120 &&
      ['Employment Situation','Consumer Price Index','Producer Price Index'].includes(e.source_series) &&
      /^\d{4}-(0[1-9]|1[0-2])$/.test(e.reporting_period) && e.event_id.endsWith(':'+e.reporting_period) &&
      e.date_status === 'SCHEDULED' && day(e.scheduled_date) && c.window.start <= e.scheduled_date && e.scheduled_date <= c.window.end &&
      e.source_timezone === c.window.timezone && e.source_sha256 === c.source.sha256 &&
      Number.isSafeInteger(e.source_line) && e.source_line > 0 &&
      e.actual_release_at === 'UNKNOWN' && e.release_observed === 'NOT_CHECKED' && e.release_material_obtained === 'NOT_CHECKED' &&
      e.analysis === 'NOT_RUN' && e.human_response === 'NOT_RECORDED', 'CALENDAR_EVENT_SCOPE');
    require((e.time_precision === 'DATE_ONLY' && e.scheduled_at === 'UNKNOWN' && e.local_scheduled_at === 'UNKNOWN') ||
      (e.time_precision === 'MINUTE' && instant(e.scheduled_at) && instant(e.local_scheduled_at) &&
       e.scheduled_at.slice(0,10) === e.scheduled_date && Date.parse(e.scheduled_at) === Date.parse(e.local_scheduled_at)), 'CALENDAR_EVENT_CLOCK');
    seen.add(e.event_id);
  }
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US-u-ca-iso8601-nu-latn', {timeZone:c.window.timezone, year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now).map(p => [p.type,p.value]));
  const today = `${parts.year}-${parts.month}-${parts.day}`;
  return {calendar:c, expired:today > c.window.end};
}

export function calendarPage(target, ctx) {
  const {reading, ui, active, onRead} = ctx, {el,card,button,link,notice,folded,disclosure,dataTable} = ui;
  const saved = reading.payload.research?.calendar, descriptor = saved?.files?.['calendar.json'];
  const panel = card('研究日历 · 有限预约', '仅阅读已保存的 BLS 日程摘录；页面刷新不会刷新来源，不触发研究、提醒或投资。');
  target.append(panel);
  if (saved?.status !== 'SAVED_REVIEWED_CALENDAR' || !descriptor) {
    panel.append(notice(saved?.status === 'UNAVAILABLE_OR_REJECTED' ? '日历资料读取受阻；不是没有事件，也不表示原预约已取消。' :
      '本读取尚未接入研究日历；不是近期没有事件。'));
    return;
  }
  const body = el('div'); body.append(el('p','正在读取固定版本日历…')); panel.append(body);
  reading.readFile(descriptor).then(file => {
    if (!active()) return;
    const {calendar:c, expired} = calendarView(file.text, saved);
    const heads = ['事件 / 报告期','原时区预约','本地预约','状态'];
    const {wrapper,body:rows} = dataTable('有限来源预约列表；报告期不等于发布日期',heads);
    for (const e of c.events) {
      const tr = el('tr');
      [`${e.title} / ${e.reporting_period}`,
       e.time_precision === 'DATE_ONLY' ? e.scheduled_date+'（时间未知）' : e.scheduled_at,
       e.local_scheduled_at === 'UNKNOWN' ? '时间未知，不补午夜' : e.local_scheduled_at,
       '预约；实际发布未检查'].forEach((value,i) => {const td=el('td',value);td.setAttribute('data-label',heads[i]);tr.append(td);});
      rows.append(tr);
    }
    body.replaceChildren(el('p',`保存窗口：${c.window.start} 至 ${c.window.end} · 原时区：${c.window.timezone} · 本地展示：${c.local_timezone}`),
      el('p',`来源核读：${c.source.reviewed_at}；本包核验：${saved.checked_at}。两者都不等于实际发布日期。`,'small'));
    if (expired) body.append(notice('保存窗口已过去；以下仅供历史阅读，未重新核实改期或实际发布。'));
    body.append(wrapper);
    if (!c.events.length) body.append(notice('所读摘录在这个窗口没有所选事件；不代表完整日历无事件。'));
    body.append(el('p','原件仅为核读摘录，不是原始 HTTP 正文；首发与 HTTP 取得时刻未知。取得发布材料、分析、Human 回应尚未核实；公司事件与完整改期链未接入。','small'),
      disclosure('日历依据与原件',button('阅读日历核读摘录',()=>onRead(saved.files['source.txt'])),
        button('阅读保存日历原件',()=>onRead(saved.files['calendar.md'])),
        link('固定 R 日历 JSON',fileUrl(reading.ref,descriptor.read_path)),link('BLS 原日历（外部当前页面）',c.source.url)));
  }).catch(error => {if (active()) body.replaceChildren(notice('日历正文未能读完；其他市场材料仍可读，不把失败当作没有事件。'),
    folded('日历读取诊断',String(error.message)));});
}
