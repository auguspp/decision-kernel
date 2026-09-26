"""Fixed HKEX table and explicitly self-reported forecast revisions.

No OCR, no arbitrary navigation and no inference of an analyst's missing model.
A revision quoted by a later report is NOT independently recovered old-vintage
research. Its exact sentence, page and PDF identity travel with the numbers.
"""
from __future__ import annotations

import io
import re
from hashlib import sha256
from bs4 import BeautifulSoup

from . import smart_money_sources as s

HKEX='https://www3.hkexnews.hk/sdw/search/mutualmarket.aspx'
MAX_PDFS=12


def northbound_table(raw, request):
    parts=request['partition'].split('@');channel=parts[0]
    s.require(channel in {'SH','SZ'},'HKEX_CHANNEL')
    h=BeautifulSoup(raw,'html.parser')
    heading=h.select('h2.ccass-heading')
    dates=re.findall(r'Shareholding Date:\s*(\d{4}/\d{2}/\d{2})', ' '.join(x.get_text(' ',strip=True) for x in heading))
    s.require(len(dates)==1,'HKEX_OBSERVATION_DATE')
    period=dates[0].replace('/','-');s.require(s.day(period)<=s.day(request['end']),'HKEX_FUTURE_PERIOD')
    if len(parts)==2:s.require(period==parts[1],'HKEX_REQUESTED_QUARTER_NOT_RETURNED')
    control=h.select_one('input[name="txtShareholdingDate"]')
    s.require(control is not None and control.get('value')==dates[0],'HKEX_DATE_CONTROL_DIFFERS')
    # originalShareholdingDate is a request/default clock, NOT the displayed
    # holdings period. A real September26 page still displays June30 holdings.
    tables=h.select('table#mutualmarket-result');s.require(len(tables)==1,'HKEX_TABLE')
    headers=[x.get_text(' ',strip=True) for x in tables[0].select('thead th')]
    s.require(len(headers)==4 and headers[:3]==['Stock Code','Name','Shareholding in CCASS'],'HKEX_COLUMNS')
    exchange='SSE' if channel=='SH' else 'SZSE'
    s.require(exchange in headers[3],'HKEX_HEADER_EXCHANGE')
    rows=[]
    for tr in tables[0].select('tbody > tr'):
        cells=tr.select('td > div.mobile-list-body');s.require(len(cells)==4,'HKEX_ROW')
        vals=[x.get_text(' ',strip=True) for x in cells]
        match=re.search(r'#\s*(\d{6})(?!\d)',vals[1])
        s.require(match is not None,'HKEX_MAINLAND_CODE_NOT_SUPPLIED')
        shares=s.number(vals[2]);pct=s.number(vals[3].removesuffix('%'))
        rows.append({'code':match[1]+'.'+channel,'name':vals[1],'connect_code':vals[0],
                     'period':period,'shares':shares,'percent':pct})
    s.require(0<len(rows)<=8000 and len({x['code'] for x in rows})==len(rows),'HKEX_TABLE_COVERAGE')
    return {'rows':rows,'period':period,'count':len(rows),'source':'HKEX_PUBLIC_QUARTERLY_SEARCH'}


def pdf_spec(report_id, begin, end):
    s.require(isinstance(report_id,str) and re.fullmatch(r'AP\d{18}',report_id) is not None,'PDF_REPORT_ID')
    s.require(s.day(begin)<=s.day(end),'PDF_WINDOW')
    return {'family':'forecast_pdf','partition':report_id,'begin':begin,'end':end,'page':1,
            'provider':'EM','url':'https://pdf.dfcfw.com/pdf/H3_'+report_id+'_1.pdf','params':{}}


def select_reports(rows):
    """Finite two-per-broker coverage, not a company recommendation/ranking."""
    groups={}
    for r in rows:
        if not any(v is not None for v in r['values']['eps_slots']):continue
        group=groups.setdefault(r['actor_id'],[])
        if len(group)<2:group.append(r)
    chosen=[]
    for group in list(groups.values())[:MAX_PDFS//2]:chosen.extend(group)
    return chosen[:MAX_PDFS]


def reported_revisions(raw, report):
    from pypdf import PdfReader
    s.require(raw.startswith(b'%PDF-') and len(raw)<=s.MAX_BODY,'PDF_BYTES')
    reader=PdfReader(io.BytesIO(raw),strict=True)
    s.require(not reader.is_encrypted and 0<len(reader.pages)<=80,'PDF_SCOPE')
    found=[];pages=[];broker=text_broker=str(report.get('actor_name') or '').replace('证券','').replace('研究','')
    for i,page in enumerate(reader.pages[:3]):
        text=page.extract_text() or ''
        s.require(len(text)<=160000,'PDF_TEXT_SIZE')
        compact=re.sub(r'\s+','',text)
        pages.append(compact)
        if report['ticker'][:6] not in compact and not any(report['ticker'][:6] in p for p in pages):continue
        if not broker or not any(broker in p for p in pages):continue
        # Require an explicitly paired new/old forecast, shared metric/unit and
        # explicit target-year range; never assign EPS slots by retrieval year.
        pattern=(r'(?:预计|预测)(?:(?:公司|其))?(20\d{2})[-—–~至](20\d{2})年'
                 r'归母净利润(?:分别)?(?:为|达)?'
                 r'([\d.]+(?:[/／、][\d.]+){1,3})(亿|百万|万)(?:元)?'
                 r'[（(]前值(?:分别)?(?:为|[:：])?'
                 r'([\d.\-—]+(?:[/／、][\d.\-—]+){1,3})(亿|百万|万)(?:元)?[）)]')
        for m in re.finditer(pattern,compact):
            first,last=int(m[1]),int(m[2]);new=re.split('[/／、]',m[3]);old=re.split('[/／、]',m[5])
            s.require(m[4]==m[6] and 1<=last-first<=3 and len(new)==len(old)==last-first+1,'REVISION_TARGET_OR_UNIT')
            for j,year in enumerate(range(first,last+1)):
                value=s.number(new[j]);before=s.number(old[j])
                if before is None:continue
                found.append({'report_id':report['values']['report_id'],'ticker':report['ticker'],
                    'actor_id':report['actor_id'],'actor_name':report['actor_name'],'target_year':year,
                    'metric':'PARENT_NET_PROFIT','new':value,'old_as_quoted':before,'unit':m[4]+'（原文同句单位）',
                    'currency':'NOT_EXPLICITLY_STATED_NO_CURRENCY_CONVERSION','share_basis':'NOT_PER_SHARE',
                    'qualification':'SAME_DOCUMENT_BROKER_REPORTED_REVISION',
                    'old_original_report':'NOT_INDEPENDENTLY_RECOVERED','pdf_sha256':sha256(raw).hexdigest(),
                    'page':i+1,'quote':m[0],'source_list_publication_date':report['disclosed']})
    unique={s.canonical_hash(x):x for x in found}
    return {'report_id':report['values']['report_id'],'status':'REPORTED_COMPARABLE_REVISION' if unique else 'NO_QUALIFIED_REVISION_PATTERN',
            'revisions':list(unique.values()),'pages_inspected':min(3,len(reader.pages)),
            'pdf_pages':len(reader.pages),'pdf_sha256':sha256(raw).hexdigest(),
            'meaning':'QUOTED_SOURCE_CLAIM_NOT_VERIFIED_PREVIOUS_VINTAGE_OR_INVESTMENT_EVIDENCE'}


def post_form(raw,channel,period):
    """Public ASP.NET search-state fields, not login or account credentials."""
    h=BeautifulSoup(raw,'html.parser')
    form=h.select_one('form#form1')
    s.require(form is not None and form.get('method','').lower()=='post'
              and form.get('action')=='./mutualmarket.aspx?t='+channel.lower(),'HKEX_FORM_DESTINATION')
    values={x.get('name'):x.get('value','') for x in form.select('input[name]')}
    allowed={'__EVENTTARGET','__EVENTARGUMENT','__VIEWSTATE','__VIEWSTATEGENERATOR','today','sortBy',
             'sortDirection','originalShareholdingDate','alertMsg','txtShareholdingDate'}
    s.require(set(values)==allowed and all(isinstance(x,str) and len(x)<64000 for x in values.values()),'HKEX_FORM_FIELDS')
    values.update(__EVENTTARGET='btnSearch',__EVENTARGUMENT='',txtShareholdingDate=s.day(period).strftime('%Y/%m/%d'))
    return values
