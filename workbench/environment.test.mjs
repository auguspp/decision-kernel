/** Sites v3 regression: an unavailable browser primitive is a GAP, never a hash PASS.
 * Synthetic transport in Node, not a browser secure-context or live-source test.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {REPO, READ_REF, openPinnedReading, loadModules} from './reading.mjs';
const R = 'a'.repeat(40), M = 'b'.repeat(40);
const original = 'retained text\n';
const descriptor = (read_path, body) => ({read_path, bytes: Buffer.byteLength(body),
  sha256: createHash('sha256').update(body).digest('hex')});
const leaf = descriptor('sources/example.txt', original);
const body = JSON.stringify({projection: {automatic_admission: false, companies: [
  {thscode: '600276.SH', assets: [{source: leaf}], archives: []}]}});
const catalogue = descriptor('details/research/asset-reentry.json', body);
function fixture(withCatalogue = false) {
  const payload = {schema_version: 1, entry_ref: READ_REF, code_commit: M,
    semantics: 'READ_ONLY_SAVED_RESULTS_AND_EXPLICIT_REQUESTS_NOT_RESTORE_AUTHORITY',
    reading_hash: 'c'.repeat(64), signal_transition_authority: 'NONE',
    human_attention_authority: 'NONE', research_authority: 'NONE', investment_authority: 'NONE',
    lanes: {}, research: {source: withCatalogue ? catalogue : leaf}};
  const calls = [];
  return {calls, fetcher: async (url, options) => {
    assert.equal(options.method, 'GET'); assert.equal(options.credentials, 'omit');
    assert.equal(options.body, undefined);
    assert.ok(url.startsWith(`https://raw.githubusercontent.com/${REPO}/${R}/`));
    calls.push(url);
    if (url.endsWith('/current-state.json')) return new Response(JSON.stringify(payload));
    if (url.endsWith('/asset-reentry.json')) return new Response(body);
    if (url.endsWith('/example.txt')) return new Response(original);
    throw new Error('UNEXPECTED_REQUEST');
  }};
}
async function withoutCrypto(value, action) {
  const old = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
  try {
    Object.defineProperty(globalThis, 'crypto', {configurable: true, value});
    await action();
  } finally {
    if (old) Object.defineProperty(globalThis, 'crypto', old);
    else delete globalThis.crypto;
  }
}
test('missing crypto, subtle or callable digest rejects selected-file verification explicitly', async () => {
  for (const value of [undefined, {}, {subtle: {}}, {subtle: {digest: null}}]) {
    await withoutCrypto(value, async () => {
      const reading = await openPinnedReading(R, fixture().fetcher);
      await assert.rejects(() => reading.readFile(leaf), /WEB_CRYPTO_UNAVAILABLE/);
      assert.equal(reading.ref, R);
    });
  }
  // Capability restoration does not bypass SHA-256; the normal path must still pass.
  const reading = await openPinnedReading(R, fixture().fetcher);
  assert.equal((await reading.readFile(leaf)).text, original);
});
test('missing Web Crypto cannot expand the catalogue allowlist or hide independent results', async () => {
  await withoutCrypto(undefined, async () => {
    const mock = fixture(true), reading = await openPinnedReading(R, mock.fetcher);
    const results = await loadModules({catalogue: () => reading.readAssets(),
      quick: async () => 'independent saved observation'});
    assert.equal(results.catalogue.status, 'GAP');
    assert.match(results.catalogue.reason, /WEB_CRYPTO_UNAVAILABLE/);
    assert.equal(results.quick.status, 'READ');
    await assert.rejects(() => reading.readFile(leaf), /UNREGISTERED_FILE/);
    assert.equal(mock.calls.some(url => url.endsWith('/example.txt')), false);
    assert.equal(reading.payload.code_commit, M);
  });
});
test('available but failing digest is not a match and does not expand the catalogue', async () => {
  await withoutCrypto({subtle: {digest: async () => { throw new Error('DIGEST_FAILED'); }}}, async () => {
    const reading = await openPinnedReading(R, fixture(true).fetcher);
    await assert.rejects(() => reading.readAssets(), /DIGEST_FAILED/);
    await assert.rejects(() => reading.readFile(leaf), /UNREGISTERED_FILE/);
  });
});
