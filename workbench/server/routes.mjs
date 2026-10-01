/** Called by the ORIGINAL Sites Worker before its existing static/fallback path.
 * Keep the host's asset binding unchanged. No guessed binding or new deployment.
 */
import {handleQuickInbox} from './quick-inbox-handler.mjs';
import {handleNewsRefresh, NEWS_REFRESH_PATH} from './news-refresh-handler.mjs';
import {handleOwnerBootstrap, OWNER_BOOTSTRAP_PATH, ownerEnvironment} from './owner-identity.mjs';
import {handleReadingRef, READING_REF_PATH, NEWS_LIVE_REF_PATH} from './reading-ref-handler.mjs';

export async function handleWorkbenchAPI(request, env, options = {}) {
  const path = new URL(request.url).pathname;
  if (path === OWNER_BOOTSTRAP_PATH) return handleOwnerBootstrap(request, env);
  if (path === READING_REF_PATH || path === NEWS_LIVE_REF_PATH) return handleReadingRef(request, env, options);
  if (path === NEWS_REFRESH_PATH || path === '/api/quick-inbox') {
    const owner = await ownerEnvironment(request, env);
    if (!owner.ok) return owner.response;
    if (path === NEWS_REFRESH_PATH) return handleNewsRefresh(request, owner.env, options);
    return handleQuickInbox(request, owner.env, options);
  }
  if (path === '/api' || path.startsWith('/api/')) return new Response(JSON.stringify({code:'UNKNOWN_API'}), {
    status:404, headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
  });
  return null;
}
