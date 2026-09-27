/** Called by the ORIGINAL Sites Worker before its existing static/fallback path.
 * Keep the host's asset binding unchanged. No guessed binding or new deployment.
 */
import {handleQuickInbox} from './quick-inbox-handler.mjs';
import {handleNewsRefresh, NEWS_REFRESH_PATH} from './news-refresh-handler.mjs';
export async function handleWorkbenchAPI(request, env, options = {}) {
  const path = new URL(request.url).pathname;
  if (path === NEWS_REFRESH_PATH) return handleNewsRefresh(request, env, options);
  if (path === '/api/quick-inbox') return handleQuickInbox(request, env, options);
  if (path === '/api' || path.startsWith('/api/')) return new Response(JSON.stringify({code:'UNKNOWN_API'}), {
    status:404, headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
  });
  return null;
}
