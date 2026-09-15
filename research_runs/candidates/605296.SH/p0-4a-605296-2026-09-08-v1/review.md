# Construction-side source and provenance review — 2026-09-08

Recorded after source re-checks; this is not the original execution receipt or new Evidence
inside its cutoff. Original observations, source records, failures and research text remain
unchanged. No new company or industry question was researched in this review.

## Exact saved input bytes

The existing Stock ZIP `df2de3a53eab178f82201bdf2317fe0f510f8a1bd7a713bda0d2c641003f4e66`
passed CRC. Independently calculated original-file SHA256 / Git blob:

- `reading/stock-reading.json`: `17cf0320ea54c33c137e69c4b7892badbce3d39ffe695d72a011875028e46942` / `55ebc73df9a4337db77989fa0b5d008eda3a790f`.
- `verification.json`: `4c2dfecffe2b4bd7d77c0d7fba8a186f265227a48d0211750bb1ce98dd781408` / `9d3d602f6ec2e91c37c61bfd25d1296718a460d0`.

These match the frozen input references. Locally reconstructed input and candidate bytes
were accepted for diagnostics only after matching the exact remote blobs `34273499…`
and `18a43542…`; they were not approximately rewritten inputs. Full model/Funnel qualification
remains subject to the unchanged CI validator.

## Same-source re-check, not a new historical retrieval claim

1. The original official SSE URL opened successfully in this review:
   https://big5.sse.com.cn/site/cht/www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-05-07/605296_20260507_S9WA.pdf
   Text and page-1 screenshot agree on April volume 31.80万头 (+48.53% YoY), revenue
   3.57亿元 (-8.46% YoY), ASP 8.65元/kg (-11.91% MoM). Sales include 5.22万头 sold
   internally to the group's slaughter businesses; the data is unaudited and excludes
   other segments. The page-2 screenshot failed with cache miss. Platform review references:
   `turn252329view0`, `turn815916view0`, `turn815916view1`.
2. The original Sina company-announcement mirror opened successfully:
   https://money.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12444426&stockid=605296
   It is a July 15 H1 earnings forecast, not audited realized final results. Its stated
   loss range and company-attributed ASP pressure match the candidate; it explicitly says
   the subsequent formal half-year report controls precise results. Review reference:
   `turn252329view1`.

The new successful page-1 screenshot does not erase the original receipt's failed screenshot.
No raw original PDF/HTTP snapshot from the initial execution was recovered by this review;
retained original evidence remains EXTRACTED_VALUES/PARTIAL, not full capture replay.

## Boundaries preventing a false acceptance

- Requests to resolve the two old Web references `turn941940view0` and `turn468765view0`
  returned `invalid ref_id argument` in this review. That does not prove the original calls
  never happened; it does mean this reviewer cannot authenticate them merely by following
  those identifiers. The new reads validate source content, not the old execution clock.
- The saved query targets summarize queries, and some failed targets are platform ids rather
  than durable URLs. Exact query/return provenance is not fully independently reconstructable.
- `model_exact_version` was a self-reported string, not a platform attestation; corrected to
  null in the separate binding repair. Task id and unavailable telemetry remain unknown.
- Four successful source reads were two GitHub input/test reads plus two external business
  reads. This is not four official company reports or an industry-wide investigation.
- The original code's existing validation rejects the wrong input hash. We repaired binding
  rather than weakening the check. The frozen input, Pre hash and Funnel body are unchanged.
- Historical April data and a July forecast cannot by themselves falsify improving September
  earnings or explain a September price move. The preserved Quick wording overstates that
  inference. WAIT can be a legitimate bounded route, but does not establish completeness.
- Reading the attack fixture while completing one task is one observed/saved episode, not
  an independently matched normal/adversarial real-executor comparison. That gate remains
  pending, as does demand-side semantic acceptance. Prompt/path lists are not hard permissions.

Do not register a new pending request or mark full P0-4A acceptance from this review. The
separate #286 engineering check addresses actual base-only installation without changing
Funnel, Research, market state, workflow or the candidate's own validation standards.
