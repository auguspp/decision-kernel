"""One current task's data assembly; Git only, no source acquisition/model call."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import NAMESPACE_URL, uuid5
import base64, json, os, subprocess, time
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import current_state as reading
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import reviewed_question_input as reviewed
from decision_kernel.runtime import stock_retained_source_import as imported
from decision_kernel.runtime import stock_daily_preparation as preparation
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime.current_state_delivery import GitHubAPI
from decision_kernel.adapters.pdf_text import extract_pdf_text

CODE = os.environ['TARGET_MAIN']
BRANCH = 'research-work/daily-603507-inputs-20260921'
PREFIX = 'research_runs/daily-inputs/603507-profit-cash-20260921/'
OUT = Path('material-output'); OUT.mkdir(exist_ok=False)
api=GitHubAPI(os.environ['GH_TOKEN'], max_calls=1024)
assert host.head(api,'main') == CODE
assert host.head(api,BRANCH) == CODE
notes=[]
for ref,path,expected in [
 ('a1f73741d4223c058364a6e1446dc8fda908b350','docs/readings/stock-financial-question-review-2026-09-21/workpaper.md','b444d3507ee74e1ed757a5a5c3a1056f0143a72a'),
 ('6eacd1fe5963514948cbcf0a516a13098286fe14','docs/readings/603507-profit-hedging-cash-2026-09-21/workpaper.md','0e2ba1468bf70404039d8b1ee71de344cb7b93d0')]:
    raw=api.file(path,ref); assert once.blob(raw)==expected
    notes.append(once.source_ref(path,ref,raw,'RETAINED_INTERACTIVE_QUESTION_REVIEW'))
R=host.head(api,reading.READ_REF)
state_raw=api.file('current-state.json',R); state=identity._json(state_raw)
reading.validate_read_package(state)
stock=state['lanes']['stock']['last_qualified_result']
assert stock['market_session']=='2026-09-21'
rows=stock['dispositions']; codes=[r['thscode'] for r in rows]
assert codes==['603507.SH','002285.SZ','688205.SH','301155.SZ','000560.SZ','002792.SZ']
rs=once.source_ref('current-state.json',R,state_raw,'SAVED_QUESTION_READING')
detail_path=stock['details']['reading/stock-reading.json']['read_path']
detail=api.file(detail_path,R)
origin=once.source_ref(detail_path,R,detail,'SAVED_STOCK_BATCH_ORIGIN')
work,tree=daily.work_tree(api)
formal=[]
for path,row in tree.items():
    if path.startswith('research_runs/candidates/') and path.endswith('/input.json'):
        raw=api.file(path,work); assert once.blob(raw)==row['sha']
        packet=json.loads(raw)
        formal.append({'path':path,'git_blob':row['sha'],'case_id':packet.get('case_id'),
                       'question':packet.get('research_question'),'execution_id':packet.get('execution_id')})
assert not [v for v in formal if v['case_id']=='603507.SH'], 'Retained formal Zhenjiang execution requires review, not new root'
profile=json.loads(api.file(imported.IMPORTS_PATH,CODE))['imports']['zhenjiang-2026h1']
run=api.get('actions/runs/'+str(profile['run']['id']))
artifacts=api.get(f"actions/runs/{run['id']}/artifacts?per_page=100")
artifact=next(a for a in artifacts['artifacts'] if a['id']==profile['artifact']['id'])
files=reading.unpack_archive(api.archive(artifact),artifact,run)
converted=imported.project(profile,files)
receipt=json.loads(files['receipt.json']); selected=receipt['selected']; extracted=json.loads(files['extraction.json'])
pdf=files[receipt['pdf']['path']]
parsed=extract_pdf_text(pdf,max_pdf_bytes=daily.POLICY['max_pdf_bytes'],max_pages=500,max_extracted_chars=daily.POLICY['max_context_bytes'])
assert extracted['pages']==[{'page_number':p.page_number,'text':p.text} for p in parsed.pages]
context={'issuer_documents':[{
 'announcement_id':selected['announcement_id'],'title':selected['title'],
 'source_locator':selected['source_locator'],'pdf_sha256':parsed.pdf_sha256,
 'published_at':selected['published_at'],'retrieved_at':receipt['pdf_finished_at'],
 'page_count':parsed.page_count,'reading_method':'ORIGINAL_PYPDF','page_reading':None,
 'pages':extracted['pages']}],
 'source_limitations':'完整2026半年报及同报比较列；未覆盖报告后公告。仅判断这些已披露资料能支持哪些有限经营与现金解释，不判断最新经营、长期可持续盈利或估值；表格与套期披露歧义保留未知。'}
assert len(once.raw(context)) <= daily.POLICY['max_context_bytes']
q={'format':reviewed.FORMAT,'case_id':'603507.SH','ticker':'603507','security_id':intake.security('603507.SH'),
 'question_id':'profit-growth-cash-conversion-2026h1','revision':1,'predecessor':None,
 'declared_at':once.now(),'reading_source':rs,
 'question':'在完整2026年半年报及其中2025年同期比较列范围内，振江归母利润增长和经营现金转正，是否足以支持经营盈利与股东现金创造同步改善？区分扣非与非经常性变化、营运资本及资本支出，交付有证据的有限判断和剩余限制，不要求逐工具穷尽套保归因或预测长期盈利。',
 'why_now':'2026-09-21正常已保存Stock批次中，振江通过原价格观察；必要完整中报已经取得并核验。价格只是问题来路，不证明业务受益。本次是原初步问题的首次正式有界执行，而不是重跑任何已消费研究。',
 'falsification_test':'若扣非、营运资本或资本支出证据不支持同步改善，应限制或否定该解释；保留支持真实经营改善的证据。缺失资料与套期披露矛盾不得补猜成收益或业务WAIT。',
 'required_classes':[{'id':'COMPLETE_H1_FINANCIAL_REPORT','mode':'STATIC','planned_queries':[]}],
 'known_counterevidence':['原交互审阅提示扣非利润也增长，不能将归母增长全部当作一次性。','经营现金的同比改善与资本占用变化有关，不能等同已产生同额股东自由现金。'],
 'known_unknowns':['报告后变化不在本次STATIC范围内。','逐工具套保与外币经营敞口对应、营运资本改善的持续性、维持性资本开支仍未建立。','此问题已有交互底稿；本次正式Pre不是全新经济发现或Full Research。'],
 'next_discriminating_search':'本次仅使用已保存完整半年报验证上述有限问题；需要其他关键材料时明确其名称与影响后停止，不自动抓取、重试或深化。',
 'origins':[{'kind':'SECTOR_LEADER','source':origin,'observed_at':stock['observed_at'],
 'qualification':'QUALIFIED_FOR_DECLARED_SCOPE','qualification_reason':'保存的Sector→Stock来路与原价格资格，仅支持纳入问题审阅，不认证经营领先或受益。'}],
 'existing_research_relation':{'kind':'NEW_DISTINCT_QUESTION',
 'note':'相对已消费正式研究的初次独立问题根；已有9月21日交互问题/有限底稿全部引用并复用，不伪称新的知识发现。完整既有work树及其正式input按证券核对未见603507执行；不重开沃顿或广哈，不宣称穷尽所有聊天的语义历史。',
 'source_refs':notes}}
reviewed._declaration(once.raw(q))
retainer=once.Retainer(api,{'prefix':PREFIX,'id':q['question_id'],'work_ref':BRANCH},CODE,OUT)
allowed={'question.json','context.json','source-journal.json','dedup.json','preflight.json','custody.json','batch-review.json'}
def save(name,value,purpose):
    assert name in allowed
    raw=value if isinstance(value,bytes) else once.raw(value)
    assert len(raw)<=identity.MAX_BYTES
    (OUT/name).write_bytes(raw)
    stamp=datetime.now(timezone.utc); boundary=stamp.replace(microsecond=0)+timedelta(seconds=1)
    time.sleep(max(0,(boundary-stamp).total_seconds()))
    result=retainer.native('PUT','contents/'+PREFIX+name,{'branch':BRANCH,'message':'Retain daily research input '+name,
                'content':base64.b64encode(raw).decode('ascii')})
    retainer.uncertain=True
    spec=once.source_ref(PREFIX+name,result['commit']['sha'],raw,purpose)
    assert result['content']['sha']==spec['git_blob'] and api.file(spec['path'],spec['ref'])==raw
    retainer.uncertain=False
    retainer.writes.append(spec)
    return spec
qs=save('question.json',q,reviewed.PURPOSE)
cs=save('context.json',context,'MODEL_CONTEXT')
js=save('source-journal.json',converted['603507.SH/sources/source-journal.json'],'RETAINED_CNINFO_SOURCE_JOURNAL')
dedup=save('dedup.json',{'work_commit':work,'checked_at':once.now(),'formal_inputs':formal,
 'scope':'All formal input files in current bounded work tree; not all-branch/chat semantic exhaustiveness',
 'prior_interactive_notes':notes,'new_model_calls':0},'RESEARCH_DEDUP_SCOPE')
began=once.now()
readraw=api.file(profile['files']['extraction.json']['path'],profile['files']['extraction.json']['ref'])
assert readraw==files['extraction.json']
ended=once.now()
body_read={'id':'603507-h1-primary','identity':'603507:1225506358','locator':selected['source_locator'],
 'tool_reference':f'Exact retained CNINFO bytes from Git {profile["files"]["receipt.json"]["ref"]}; original source run {run["id"]}',
 'authority':'PRIMARY','kind':'BODY','succeeded':True,'body_sha256':parsed.pdf_sha256,'checked_at':ended}
until=min(reading.clock(state['checks']['recheck_after']),reading.clock(daily.POLICY['execute_before']))
eid=host.question_execution(q['security_id'],q['question_id'])[0]
pf={'schema_version':1,'provenance':'RECORDED_TOOL_RETURNS','case_id':q['case_id'],'ticker':q['ticker'],'security_id':q['security_id'],
 'started_at':began,'finished_at':ended,'valid_until':until.isoformat(),'reads':[body_read],
 'required_classes':[{'id':'COMPLETE_H1_FINANCIAL_REPORT','mode':'STATIC','body_ids':['603507-h1-primary'],'inventory_id':None}],
 'inventories':[],'limits':{'max_queries':0,'max_reads':1},
 'seed_publications':[{'evidence_id':str(uuid5(NAMESPACE_URL,eid+':'+cs['sha256'])),'kind':'GIT_COMMIT','source':cs}]}
ps=save('preflight.json',pf,'PRE_EXECUTION_SOURCE_PREFLIGHT')
inv={k:v for k,v in profile['files']['inventory.json'].items() if k!='bytes'}
inv['purpose']='RETAINED_CNINFO_ISSUER_INVENTORY'
pdfsource={k:v for k,v in profile['files'][receipt['pdf']['path']].items() if k!='bytes'}
custody={'context':cs,'checked_at':once.now(),'ticker':'603507','source_run_id':run['id'],
 'source_artifact':profile['artifact'],'source_import':'zhenjiang-2026h1','inventory_source':inv,
 'journal_source':js,'documents':[{'announcement_id':'1225506358','pdf_source':pdfsource,
    'bytes':len(pdf),'pdf_sha256':parsed.pdf_sha256,'page_count':parsed.page_count}]}
ss=save('custody.json',custody,'DAILY_PUBLIC_PDF_CUSTODY')
reasons=[('SELECTED_NEW_DISTINCT_QUESTION','完整报告已具备，首次正式执行已声明的有限利润/现金问题；原交互底稿和未知保留。'),
 ('NOT_SELECTED','世联亏损与回款问题保留；完整必要正文尚未在这条资料链中核验，本日不执行。'),
 ('DATA_UNAVAILABLE','原公司行为窗口价格转换能力缺口保留，非经营否决。'),
 ('ORIGINAL_PRICE_DISPOSITION_ONLY','保留原20日价格条件未满足的处置，非经营否决。'),
 ('NOT_SELECTED','我爱我家收入/转租收益与现金问题保留；本期必要完整原件未取得，不因首页省略而漏审。'),
 ('NOT_SELECTED','通宇收入、毛利与利润问题保留；必要完整正文未取得，不凭二手摘要启动。')]
batch={'reading_source':rs,'question_source':qs,'batch_id':__import__('decision_kernel.runtime.reviewed_question_reading',fromlist=['stock_review_scope']).stock_review_scope(state)['batch_id'],
 'reviewed_at':once.now(),'items':[{'thscode':r['thscode'],'disposition':d,'reason':why} for r,(d,why) in zip(rows,reasons,strict=True)]}
bs=save('batch-review.json',batch,'DAILY_STOCK_BATCH_REVIEW')
selectors={k:{'ref':v['ref'],'path':v['path']} for k,v in [('batch_review',bs),('source_custody',ss),('preflight',ps)]}
(OUT/'selectors.json').write_bytes(once.raw(selectors))
report=preparation.prepare(api=api,code=CODE,selectors=selectors,output=OUT/'preparation')
(OUT/'retention.json').write_bytes(once.raw({'writes':retainer.writes,'code':CODE,'reading':R,'work':work,
 'main_unchanged':host.head(api,'main')==CODE,'model_calls':0,'source_requests':0,'daily_slots_consumed':0}))
print(once.raw(report).decode())
assert report['status']==preparation.SUCCESS, report
