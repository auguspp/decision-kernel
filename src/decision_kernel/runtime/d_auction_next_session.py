"""Next-session raw open/close observations over the original frozen auction pool.

Reuse saved-source replay and native Git history. No price/factor splice, return
backtest, acquisition, scheduling, ranking, new selection or trading occurs here.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from zipfile import BadZipFile

from decision_kernel.identity import canonical_hash
from . import current_state as model
from . import stock_market_inputs as prices
from . import d_auction_probe as probe
from .d_auction_follow_through import _read, _group, GROUPS
from .d_horizon_follow_up import _bound, read_price_parts

KEY = 'd_auction_next_session'
PATH = 'details/stock/auction-next-session.json'
VERSION = 'd-auction-next-session-observation-v1'
COLUMNS = ['symbol', 'group', 'next_open', 'next_close', 'open_status', 'close_status']
ERRORS = (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, ArithmeticError, BadZipFile)
TERMINAL = {'NEXT_SESSION_OBSERVED', 'NEXT_SESSION_OBSERVED_WITH_GAPS', 'NEXT_SESSION_QUOTES_UNAVAILABLE'}


def seed(auction, descriptor, checked_at):
    """Freeze every original row, including static exclusions and unknown identity."""
    model.check(auction['version'] in (probe.LEGACY_VERSION, probe.VERSION)
                and auction['profile'] == probe.PROFILE and auction['source'] == prices.SOURCE
                and auction['status'] in ('SHADOW_AUCTION_READING', 'NO_STATIC_MATCH_IN_RETURNED_POOL',
                                          'AUCTION_INPUT_UNAVAILABLE'),
                'next-session auction identity')
    model.check(auction['columns'] == list(probe.ROW_COLUMNS), 'next-session auction columns')
    rows = probe.row_dicts(auction)
    model.check(len(rows) == auction['cohort_denominator'], 'next-session original denominator')
    members = [{'symbol': r['symbol'], 'group': _group(r)} for r in rows]
    valid = [r['symbol'] for r in members if r['symbol'] is not None]
    model.check(len(set(valid)) == len(valid) and all(prices.CODE.fullmatch(s) for s in valid),
                'next-session cohort identity')
    model.check(model.clock(auction['observed_at']) <= model.clock(auction['received_through'])
                <= model.clock(checked_at), 'next-session auction clock')
    model.check(sum(r['group'] == 'MATCHED' for r in members) == auction['matched']
                and sum(r['group'] in ('MATCHED', 'NOT_MATCHED', 'AUCTION_UNRESOLVED') for r in members)
                == auction['static_eligible'], 'next-session original groups differ')
    source = descriptor['source_archive']
    identity = {'market_session': auction['market_session'], 'profile': auction['profile'],
                'archive_sha256': source['sha256']}
    return {'id': canonical_hash(identity), **identity, 'members': members,
            'members_hash': canonical_hash(members), 'auction_timeliness': auction['timeliness'],
            'auction_observed_at': auction['observed_at'], 'auction_received_through': auction['received_through'],
            'first_recorded_at': checked_at, 'auction_origin': deepcopy(source),
            'target_session': None, 'calendar_prefix': [], 'status': 'WAITING_FOR_NEXT_COMPLETED_SESSION'}


def target_session(cohort, calendar, completed_session):
    """The first explicit open date after T, not T+1 calendar day or a good quote."""
    previous = {r['session']: r['is_open'] for r in cohort.get('calendar_prefix', [])}
    model.check(all(type(v) is bool for v in calendar.values()), 'next-session calendar value')
    model.check(all(previous[d] == calendar[d] for d in previous.keys() & calendar.keys()),
                'next-session calendar revised; target cannot silently move')
    values = {**previous, **calendar}
    day = date.fromisoformat(cohort['market_session']) + timedelta(days=1)
    end = date.fromisoformat(completed_session)
    prefix, target, gap = [], None, None
    while day <= end:
        model.check(len(prefix) < 512, 'next-session calendar safety bound')
        text = day.isoformat()
        if text not in values:
            gap = text
            break
        prefix.append({'session': text, 'is_open': values[text]})
        if values[text]:
            target = text
            break
        day += timedelta(days=1)
    model.check(cohort.get('target_session') in (None, target), 'next-session target moved or disappeared')
    return target, prefix, gap


def project(cohort, calendar, completed_session, sources, *, checked_at):
    """sources contains independently replayed daily tables; never merge quote rows."""
    model.check(cohort['members_hash'] == canonical_hash(cohort['members']), 'next-session members changed')
    out = deepcopy(cohort)
    target, prefix, gap = target_session(cohort, calendar, completed_session)
    out.update(target_session=target, calendar_prefix=prefix, calendar_gap=gap)
    source = next((s for s in sources if target and ('daily', target.replace('-', '')) in s['tables']), None)
    # A later failed capture cannot erase already observed exact-date fields.
    # Keep the WHOLE previous result, not a splice of old/new quote rows.
    if source is None and cohort.get('quote_source') and target == cohort.get('target_session'):
        out.update(observation='PREVIOUS_DATED_OBSERVATIONS_RETAINED',
                   current_quote_gap='TARGET_QUOTE_NOT_IN_CURRENT_SAVED_SOURCES',
                   current_quote_attempt=None)
        return out
    quotes = source['tables']['daily', target.replace('-', '')] if source else {}
    if source:
        model.check(source['source'] == prices.SOURCE and source['provenance'] == 'LIVE_TUSHARE_RELAY',
                    'next-session source identity')
        model.check(model.clock(target+'T15:00:00+08:00') <= model.clock(source['received_through'])
                    <= model.clock(checked_at), 'next-session future close or acquisition')
    rows = []
    for member in cohort['members']:
        symbol = member['symbol']
        default = 'CALENDAR_GAP' if gap else 'WAITING_FOR_NEXT_COMPLETED_SESSION' if target is None else 'QUOTE_NOT_RETAINED'
        if symbol is None:
            default = 'COHORT_IDENTITY_UNRESOLVED'
        values, states = [], []
        for field in ('open', 'close'):
            value, state = None, default
            if symbol in quotes and target:
                raw = quotes[symbol].get(field)
                if raw is None:
                    state = 'FIELD_NOT_RETURNED'
                else:
                    try:
                        prices.number(raw)
                        value, state = str(raw), 'RAW_QUOTE_OBSERVED'
                    except (ValueError, ArithmeticError):
                        state = 'QUOTE_VALUE_INVALID'
            values.append(value); states.append(state)
        rows.append([symbol, member['group'], *values, *states])
    # A present table can still lose a previously observed row/field. Keep the
    # WHOLE prior observation, not old good cells merged into the new table.
    if source and cohort.get('quote_source') and target == cohort.get('target_session'):
        previous_rows = cohort['rows']
        model.check(cohort.get('columns') == list(COLUMNS) and len(previous_rows) == len(rows)
                    and all(len(old) == len(COLUMNS) and old[:2] == new[:2]
                            for old, new in zip(previous_rows, rows)),
                    'next-session previous observation identity')
        lost = [{'symbol': old[0], 'field': field, 'status': new[index+2]}
                for old, new in zip(previous_rows, rows)
                for index, field in ((2, 'open'), (3, 'close'))
                if old[index] is not None and new[index] is None]
        if lost:
            out.update(observation='PREVIOUS_DATED_OBSERVATIONS_RETAINED',
                current_quote_gap='CURRENT_DATED_FIELDS_UNAVAILABLE_PRIOR_RESULT_RETAINED',
                current_quote_attempt={'source': deepcopy(source['archive']),
                    'received_through': source['received_through'],
                    'row_coverage': deepcopy(source['coverage'].get('daily:' + target.replace('-', ''), {})),
                    'unavailable_previously_observed_fields': lost})
            return out
    out.pop('current_quote_attempt', None)
    groups = {g: {'denominator': 0, 'open_observed': 0, 'close_observed': 0} for g in GROUPS}
    for row in rows:
        group = groups[row[1]]; group['denominator'] += 1
        group['open_observed'] += row[2] is not None; group['close_observed'] += row[3] is not None
    status = ('CALENDAR_GAP' if gap else 'WAITING_FOR_NEXT_COMPLETED_SESSION' if target is None else
              'NEXT_SESSION_QUOTES_UNAVAILABLE' if source is None else
              'NEXT_SESSION_OBSERVED' if all(r[2] is not None and r[3] is not None for r in rows)
              else 'NEXT_SESSION_OBSERVED_WITH_GAPS')
    out.update(status=status, columns=list(COLUMNS), rows=rows, groups=groups,
               quote_source=deepcopy(source['archive']) if source else None,
               quote_received_through=source['received_through'] if source else None,
               quote_row_coverage=(deepcopy(source['coverage'].get('daily:' + target.replace('-', ''), {}))
                                   if source else None),
               current_quote_gap=None if source else 'TARGET_QUOTE_NOT_RETAINED' if target else None)
    result_hash = canonical_hash({'target': target, 'rows': rows})
    unchanged = result_hash == cohort.get('result_hash')
    out.update(result_hash=result_hash,
        result_first_recorded_at=cohort['result_first_recorded_at'] if unchanged else checked_at,
        observation='UNCHANGED_DATED_OBSERVATIONS' if unchanged else 'DATED_OBSERVATIONS_UPDATED',
        price_basis='RAW_OPEN_CLOSE_ONLY_NOT_CROSS_SESSION_ADJUSTED_RETURN',
        acquisition_timing=('SAME_SESSION_AFTER_CLOSE' if source and
            model.clock(source['received_through']).astimezone(prices.ZONE).date().isoformat() == target
            else 'LATER_ACQUISITION_NOT_HISTORICAL_KNOWLEDGE' if source else 'NOT_AVAILABLE'))
    return out


def render(report):
    lines = ['\n\n## D：原竞价名单的下一交易日开收盘观察\n',
             f"读取截止：{report['checked_at']}；最新日线状态：{report['latest_price_status']}。",
             'T+1按实际来源交易日历固定；停牌／缺价不顺延到另一日。原名单、未匹配与排除项均保留。']
    for cohort in report['cohorts']:
        lines += [f"\n### 原竞价 {cohort['market_session']} → {cohort['target_session'] or '下一完成交易日未建立'}",
                  f"原时点：{cohort['auction_timeliness']}；本次：{cohort['status']}。"]
        if cohort.get('observation') == 'PREVIOUS_DATED_OBSERVATIONS_RETAINED':
            lines.append(f"本次报价缺口：{cohort['current_quote_gap']}；以下保留整份旧观察，"
                         '不是本次重新取得，也未跨包拼接。具体缺项与本次来源见完整结果。')
        lines += ['| 原分组 | 全部分母 | T+1开盘可读 | T+1收盘可读 |', '|---|---:|---:|---:|']
        for key, title in GROUPS.items():
            row = cohort['groups'][key]
            lines.append(f"| {title} | {row['denominator']} | {row['open_observed']} | {row['close_observed']} |")
    lines += ['这里只展示准确日期的未复权开盘／收盘，不跨采集包拼价格与因子，不生成跨日收益或胜率。',
              '缺开盘不阻止已有收盘；旧包只请求收盘的事实保留。09:40、盘前及时性和交易效果仍未验。',
              f'[完整原名单、逐名字段缺口、来源与历史接续]({PATH})。\n']
    return '\n'.join(lines)


def _location(collector):
    descriptor = (collector.previous or {}).get('research', {}).get(KEY)
    if not descriptor:
        return None
    location = ({'reading_commit': collector.previous_commit, 'file': descriptor}
                if 'read_path' in descriptor else descriptor.get('previous_result'))
    return deepcopy(location)


def _previous(collector, location):
    if not location:
        return None
    reference = location['file']; commit = location['reading_commit']
    model.check(reference['read_path'] == PATH and model.SHA.fullmatch(commit or ''),
                'next-session previous locator')
    raw = collector.api.file(PATH, commit); _bound(raw, reference)
    report = prices.loads(raw)
    model.check(report['version'] == VERSION and report['report_hash'] ==
                canonical_hash({k: v for k, v in report.items() if k != 'report_hash'}), 'next-session previous report')
    return report


def retain_cohorts(prior, current, location):
    """Carry pending rows; completed old cohorts remain in their exact Git reading."""
    cohorts, archived = {}, []
    for cohort in (prior or {}).get('cohorts', []):
        if (cohort['status'] in TERMINAL and current is not None and cohort['id'] != current['id']
                and current['market_session'] > cohort['target_session']):
            archived.append({'id': cohort['id'], 'market_session': cohort['market_session'],
                'target_session': cohort['target_session'], 'status': cohort['status'],
                'reading_commit': location['reading_commit'], 'report_path': PATH})
            continue
        retained = deepcopy(cohort)
        # Any source not retained in this publication is reached via the exact
        # successful prior result, even across a sequence of failed publications.
        for key in ('auction_origin', 'quote_source'):
            origin = retained.get(key)
            if origin and 'read_path' in origin:
                retained[key] = {'reading_commit': location['reading_commit'], 'report_path': PATH,
                    'archive_sha256': origin['sha256'],
                    'meaning': 'EXPLICIT_PREVIOUS_READING_NOT_SAME_R_SOURCE'}
        cohorts[cohort['id']] = retained
    if current:
        old = cohorts.get(current['id'])
        model.check(old is None or old['members_hash'] == current['members_hash'], 'next-session frozen pool changed')
        cohorts.setdefault(current['id'], current)
    return list(cohorts.values()), archived


def _reserve(collector, **kwargs):
    from .institutional_radar_reading import _reserve as reserve
    return reserve(collector, **kwargs)


def attach(collector, baseline, *, retained_limit):
    """Original publisher/file budget and Git versions own retention, not a new service."""
    from .independent_stock_reading import KEY as STOCK_KEY, _cached
    before = dict(collector.files)
    phase, prior, location = 'PREVIOUS_READING', None, None
    try:
        model.validate_read_package(baseline)
        model.check(collector.code_commit == baseline['code_commit'], 'next-session code identity')
        location = _location(collector)
        _reserve(collector, calls=1, files=2)
        prior = _previous(collector, location)
        cutoff = collector.now()
        model.check(prior is None or model.clock(prior['checked_at']) <= model.clock(cutoff), 'next-session prior future')
        ref = baseline['research'][STOCK_KEY]; raw = collector.files[ref['read_path']]; _bound(raw, ref)
        daily_state = prices.loads(raw)['daily_market_inputs']
        phase = 'RETAINED_SOURCE_REPLAY'
        sources = []
        for description in (daily_state, daily_state.get('last_qualified_result') or {}):
            if not description.get('file') or not description.get('market_session'):
                continue
            if any(s['archive'] == description['source_archive'] for s in sources):
                continue
            report = _read(collector, description, cutoff)
            files = _cached(collector, description['source_archive'], cutoff)
            calendar, tables, coverage = read_price_parts(files, report)
            sources.append({'source': report['source'], 'provenance': report['provenance'],
                'archive': description['source_archive'], 'calendar': calendar, 'tables': tables,
                'coverage': coverage, 'market_session': report['market_session'],
                'received_through': report['received_through']})
        model.check(sources, 'next-session calendar not retained')
        calendar_source = max(sources, key=lambda s: (s['market_session'], model.clock(s['received_through'])))
        phase = 'ORIGINAL_COHORT'
        auction_description = daily_state.get('auction_probe', {})
        current = None
        if auction_description.get('file'):
            auction = _read(collector, auction_description, cutoff)
            if auction['status'] in ('SHADOW_AUCTION_READING', 'NO_STATIC_MATCH_IN_RETURNED_POOL',
                                      'AUCTION_INPUT_UNAVAILABLE'):
                current = seed(auction, auction_description, cutoff)
        cohorts, archived = retain_cohorts(prior, current, location)
        model.check(cohorts or archived, 'next-session no original auction pool retained')
        phase = 'DATED_OBSERVATIONS'
        checked = collector.now()
        built = [project(c, calendar_source['calendar'], calendar_source['market_session'], sources,
                         checked_at=checked) for c in cohorts]
        checked = collector.now()  # Close the stage after all projections, not before.
        report = {'version': VERSION, 'code_commit': collector.code_commit, 'checked_at': checked,
            'cohorts': built, 'archived_cohorts': archived, 'latest_price_status': daily_state['status'],
            'calendar_source': deepcopy(calendar_source['archive']),
            'calendar_market_session': calendar_source['market_session'],
            'previous_result': location,
            'latest_auction_status': auction_description.get('status', 'NO_RETAINED_AUCTION'),
            'new_source_requests': 0, 'automatic_research_routing': False,
            'cross_session_return': 'NOT_COMPUTED_RAW_DATED_OBSERVATIONS_ONLY', **model.AUTHORITY}
        report['report_hash'] = canonical_hash(report)
        phase = 'PUBLICATION_CAPACITY'
        raw, note = prices.dumps(report), render(report).encode()
        model.check(len(raw) <= prices.MAX_REPORT, 'next-session detail capacity')
        descriptor = {'read_path': PATH, 'bytes': len(raw), 'sha256': model.sha256(raw),
            'git_blob': model.blob_sha(raw), 'read_ref_rule': 'USE_THE_SAME_PINNED_READING_COMMIT'}
        research = deepcopy(baseline['research']); research[KEY] = descriptor
        model.check(model.clock(checked) >= model.clock(baseline['checks']['finished_at']), 'next-session clock reversed')
        payload = model.assemble(code_commit=baseline['code_commit'], checked_at=checked,
            check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
            capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
        entry = model.read_package_bytes(payload)
        model.check(sum(len(v) for k, v in before.items() if k != 'current-state.json') +
                    len(raw) + len(note) + len(entry) <= retained_limit, 'next-session total capacity')
        _reserve(collector, files=2)
        collector.retain(PATH, raw); collector.files['current-state.json'] = entry
        collector.files['README.md'] += note
        return payload
    except ERRORS as exc:
        collector.files = before
        # Keep other stages and their clocks untouched. A failed optional read is not zero outcomes.
        # The original prior file remains in Git; no partial cohort is silently published.
        research = deepcopy(baseline['research'])
        research[KEY] = {'status': 'NEXT_SESSION_READING_UNAVAILABLE_OTHER_INPUTS_PRESERVED',
            'phase': phase, 'error_type': type(exc).__name__,
            'previous_result': location,
            'new_source_requests': 0}
        try:
            checked = collector.now()
            model.check(model.clock(checked) >= model.clock(baseline['checks']['finished_at']), 'next-session failure clock')
            payload = model.assemble(code_commit=baseline['code_commit'], checked_at=checked,
                check_started_at=baseline['checks']['started_at'], lanes=baseline['lanes'], research=research,
                capabilities=baseline['capability_gaps'], refresh_identity=baseline['refresh'])
            entry = model.read_package_bytes(payload)
            note = b'\nD next-session reading unavailable; prior prices, auction and research preserved.\n'
            model.check(sum(len(v) for k, v in before.items() if k != 'current-state.json') +
                        len(entry) + len(note) <= retained_limit, 'next-session failure capacity')
            collector.files['current-state.json'] = entry; collector.files['README.md'] += note
            return payload
        except ERRORS:
            collector.files = before
            return baseline
