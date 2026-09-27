/** Human controls for explicit transfer to GitHub. No localStorage, polling, or model calls. */
import {INBOX_URL, selection, loadInbox, batchRequest} from './quick-inbox.mjs';
import {fileUrl} from './reading.mjs';
import {localTime} from './product.mjs';
const labels={news:'新闻',sector:'行业',company:'公司',material:'研究／Odds材料'};
export async function saveInbox(request,fetcher=globalThis.fetch) {
  const response=await fetcher('/api/quick-inbox',{method:'POST',credentials:'same-origin',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(45000),
    headers:{'Content-Type':'application/json','X-Decision-Kernel-Intent':'quick-inbox'},body:JSON.stringify(request)});
  if(!response.headers.get('content-type')?.includes('application/json'))throw new Error('SITE_HANDLER_NOT_CONNECTED');
  const result=await response.json();
  if(!response.ok || result.saved!==true)throw new Error(result.uncertain?'SAVE_UNCONFIRMED_READ_INBOX_FIRST':result.code||'SAVE_NOT_CONFIRMED');
  return result;
}
export function transferButton(ui, value, active=()=>true) {
  const s=selection(value), {el,button}=ui, node=el('div',undefined,'product-actions'), status=el('span','', 'small');
  let nonce=null,busy=false;
  const add=button('加入待 Quick',async()=>{
    if(!active()||busy)return;
    busy=true;add.disabled=true;status.textContent='正在转存…';
    try {
      nonce ||= crypto.randomUUID();
      const result=await saveInbox({action:'add',nonce,selection:s});
      if(active()){add.textContent=result.reused?'已确认已有转存':'已加入待 Quick';
        status.textContent=result.reused?'未新增请求；请在待 Quick 核对原记录的当前状态。':'已保存到 GitHub；此次转存没有启动研究。';}
    } catch(error) {
      if(active()){
        status.textContent=error.message==='SAVE_UNCONFIRMED_READ_INBOX_FIRST' ? '保存未确认，请先打开待 Quick 核对；不要重复点新的请求。' : '未确认保存。请核对站点接入与权限；材料没有转存到浏览器替代。';
        add.disabled=false;
      }
    } finally {busy=false;}
  });
  add.title='仅保存当前公开材料的定位；不启动研究。';
  status.setAttribute('role','status');node.append(add,status);return node;
}
function copyControl(ui,title,build) {
  const {el,button}=ui,node=el('div'),text=el('pre');text.hidden=true;
  const copy=button(title,async()=>{
    try {
      text.textContent=build();
      try {await navigator.clipboard.writeText(text.textContent);copy.textContent='已复制；提交到网页版后才研究';}
      catch{text.hidden=false;copy.textContent='请复制下方内容；尚未研究';}
    }catch{text.hidden=false;text.textContent='当前没有可复制的有效请求，或超过单批100项；请先更新清单。';}
  });
  node.append(copy,text);return node;
}
export function quickInboxPage(target,ui,active=()=>true) {
  const {el,card,button,link,disclosure}=ui;
  const panel=card('待 Quick','把选中的材料集中交给网页版 ChatGPT。浏览、复制、移出不等于研究完成。');
  panel.append(el('p','这里保存在公开 GitHub 的 #601；不要转存私人原话或账户资料。','small'),link('打开 GitHub 收件箱',INBOX_URL));
  const content=el('div');let busy=false,generation=0;
  const refresh=button('读取待 Quick 清单',async()=>{
    if(!active()||busy)return;busy=true;refresh.disabled=true;const turn=++generation;
    content.replaceChildren(el('p','正在读取请求和核对已登记结果…'));
    try {
      const view=await loadInbox();if(!active()||turn!==generation)return;
      content.replaceChildren(el('p',`待 Quick ${view.pending.length} 项 · 已有保存结果 ${view.finished.length} 项 · 已移出 ${view.removed.length} 项`),
        el('p',`清单读取：${localTime(view.observedAt)}；与页面市场资料时间分开。`,'small'));
      for(const gap of view.gaps)content.append(el('p',gap,'human-notice'));
      if(view.pending.length)content.append(copyControl(ui,'复制全部待 Quick',()=>batchRequest(view.pending)));
      else content.append(el('p','当前已读取范围内没有待处理选择；不代表市场没有值得研究的事。'));
      for(const item of view.pending){
        const row=el('article',undefined,'human-research-row');
        row.append(el('h4',item.context.title),el('p',`${labels[item.context.selection.kind]} · 加入 ${localTime(item.createdAt)}`,'small'));
        if(item.results.length)row.append(el('p','已有关联结果，但原文尚未核验成功；仍保留待处理。','human-notice'));
        row.append(copyControl(ui,'复制这一项给 Quick',()=>batchRequest([item])),
          link('查看选中时的材料',fileUrl(item.context.selection.reading,item.context.source.read_path)));
        const state=el('span','', 'small'),remove=button('移出待 Quick',async()=>{
          if(!active())return;remove.disabled=true;
          try{await saveInbox({action:'remove',requests:item.requests});if(active())state.textContent='移出记录已保存；请重新读取清单。';}
          catch{if(active()){state.textContent='移出未确认，请重新读取清单核对。';remove.disabled=false;}}
        });
        row.append(remove,state,disclosure('原请求与版本',...item.requests.map(id=>link(`请求 ${id}`,`${INBOX_URL}#issuecomment-${id}`))));content.append(row);
      }
      const history=disclosure('已有结果和移出历史');
      for(const item of [...view.finished,...view.removed]){
        const row=el('div');row.append(el('strong',item.context.title),el('p',item.removed?'已移出；不是否定研究或投资判断。':'已有核对过字节的结果；不是接受或投资决定。'));
        for(const result of item.results)row.append(result.verified ? link('阅读保存结果',fileUrl(result.source.commit,result.source.path)) : el('p','一份结果定位尚未核验。'));
        row.append(link('原请求',item.url));history.append(row);
      }
      content.append(history);
    }catch{if(active()&&turn===generation)content.replaceChildren(el('p','收件箱未完整读回，不能当作0项。请稍后主动重读或查看 GitHub 原记录。','human-notice'));}
    finally{busy=false;refresh.disabled=false;}
  });
  panel.append(refresh,content);target.append(panel);
  // Loading this page does not claim/execute work. The user chooses when to query.
  content.append(el('p','点击“读取待 Quick 清单”，核对最新的选择和结果。'));
}
