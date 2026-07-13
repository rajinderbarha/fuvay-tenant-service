# FINAL-L5-05AA — Export Rate Limit, Concurrency, Idempotency and Abuse Protection Certification

## Label correction (read first)

The mission specification that triggered this sprint was titled `FINAL-L5-05U — Export Rate Limit, Concurrency, Idempotency and Abuse Protection Certification` and stated starting assumptions (`FINAL-L5-05Q: b3ec4b0`, `FINAL-L5-05R: 4dfb943`, "FINAL-L5-05S/T: PENDING FINAL REPORT") that predate this entire engagement's completed S/T/U/V/W/X/Z work in this session. Its own label, `FINAL-L5-05U`, collides with the already-completed **Security Deposit Permission Namespace, Domain Authorization and Runtime Certification** sprint (commit `d2ee0e2`).

Per the mission's own Part 1 instruction ("determine the actual repository state") and its own "preserve all valid work from prior sprints" rule, real repository state was determined before any code was written:

- `git rev-parse HEAD` and `git rev-parse origin/master` both resolved to `1d37627` (FINAL-L5-05Z, the prior sprint's final commit) at the start of this sprint.
- `alembic heads` was `135` (FINAL-L5-05S).

This mission's substantive content is therefore run under the corrected, non-colliding label **FINAL-L5-05AA**.

## Scope actually delivered

The mission's own Part 2 required a real inventory of the platform's existing abuse-protection primitives before building anything new. That inventory found:

| Primitive | Location | Status before this sprint |
|---|---|---|
| `app.core.security.RateLimiter` | `app/core/security.py` | Real, working, Redis sliding-window (Lua-script atomic). `RATE_LIMITS["api:export"] = (3600, 5)` already defined. **Zero references anywhere in `app/engines/enterprise_grid/`.** Already used elsewhere (e.g. `platform_commerce.service.initiate_deposit`). |
| `app.core.security.idempotency_store` | `app/core/security.py` | Real, working, generic `X-Idempotency-Key` / 24h Redis TTL pattern. Never wired into export creation. |
| Concurrent-job cap | — | Did not exist at all. An actor could submit unlimited simultaneous `PENDING` export jobs. |
| Payload-bound validation (columns / selected-IDs / date range) | — | Did not exist at all. |

This is the headline finding: the platform already had proven, reusable abuse-protection infrastructure; the Enterprise Export creation endpoint (`POST /v1/enterprise/exports`) simply never used it. This sprint's work is entirely **wiring existing infrastructure in** plus **one small new durable-idempotency mechanism** matching an established pattern — not building a new abuse-protection platform from scratch.

## What was built

### 1. Migration 136 — `idempotency_key` column
`alembic/versions/136_export_abuse_protection.py`:
- Nullable `idempotency_key VARCHAR(128)` column on `enterprise_export_jobs`.
- Partial unique index `uq_export_jobs_actor_idempotency_key` on `(requested_by_user_id, idempotency_key) WHERE idempotency_key IS NOT NULL` — scoped per-actor so two different actors can reuse the same client-chosen key string with zero collision, and the vast majority of rows (no key supplied) never participate in the uniqueness check.
- Index `ix_export_jobs_actor_status` on `(requested_by_user_id, status)` to keep the new concurrent-job count query cheap.

Chosen deliberately over the generic Redis `idempotency_store`: export job state must survive worker restarts and be queryable (an actor should be able to see their replayed job in the normal jobs list), matching the same reasoning that led `UsageCreditService` to use a durable idempotency-key column rather than a pure cache for financial operations.

### 2. `ExportService.create_export_job` (`app/engines/enterprise_grid/services.py`)
Rewritten with, in order:
1. Existing field-allowlist and filter-allowlist validation (unchanged).
2. **New**: `_validate_payload_bounds(columns, safe_filters)` — rejects before any DB work if columns exceed `EXPORT_MAX_COLUMNS` (50), a selected-ID-style filter array exceeds `EXPORT_MAX_SELECTED_IDS` (500), or a date-range filter pair spans more than `EXPORT_MAX_DATE_RANGE_DAYS` (366) days.
3. **New**: deterministic SHA-256 `_fingerprint(resource_key, filters, columns, export_format)` — sorted filter keys and sorted columns, so field/filter *order* never changes the fingerprint (verified by `test_field_order_does_not_change_fingerprint`).
4. **New**: a single per-actor Postgres advisory lock (`pg_advisory_xact_lock(hashtextextended(f"export_concurrent:{user_id}", 0))`), acquired once and held for the rest of the transaction, serializing both of the following against the same actor:
   - **Idempotency resolution**: if `idempotency_key` given and a prior job with that (actor, key) pair exists — same fingerprint → return `(existing_job, is_replay=True)`, no new row; different fingerprint → raise `EXPORT_IDEMPOTENCY_CONFLICT`.
   - **Concurrent-job limit**: count `PENDING`+`PROCESSING` jobs for this actor; `>= EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR` (3) → raise `EXPORT_CONCURRENT_JOB_LIMIT`. A plain (unlocked) per-tenant count is also checked as a soft fairness cap (`EXPORT_MAX_CONCURRENT_JOBS_PER_TENANT` = 10) — not lock-protected, since it's a soft control and the actor-level lock already prevents that actor's own race.
5. Existing sync-export-row-limit check (unchanged).
6. Insert the new `EnterpriseExportJob` row, storing `idempotency_key` (deliberately not exposed via `to_dict()`).

Return signature changed from `EnterpriseExportJob` to `tuple[EnterpriseExportJob, bool]` (`job, is_replay`).

### 3. Router wiring (`app/engines/enterprise_grid/router.py`)
`create_export` handler, after the existing resource-exists / permission / scope checks and before any DB write:
```python
await rate_limiter.check_and_raise(limit_key="export", limit_type="api:export", identifier=str(u.user_id))
idempotency_key = r.headers.get("X-Idempotency-Key")
...
job, is_replay = await _export.create_export_job(..., idempotency_key=idempotency_key)
return ok(job.to_dict(), _rid(r), "enterprise.export.created", idempotent=is_replay)
```
6 new error codes wired into `_EXPORT_ERROR_STATUS` (`EXPORT_RATE_LIMITED`→429, `EXPORT_CONCURRENT_JOB_LIMIT`→429, `EXPORT_TENANT_CONCURRENT_JOB_LIMIT`→429, `EXPORT_IDEMPOTENCY_CONFLICT`→409, `EXPORT_FIELD_LIMIT`→422, `EXPORT_SELECTED_ID_LIMIT`→422, `EXPORT_DATE_RANGE_EXCEEDED`→422).

## A real bug this sprint's own tests found and fixed

The first implementation of the advisory lock covered only the concurrent-job-count check, not the idempotency lookup. `TestRealConcurrencyAndIdempotency::test_concurrent_identical_idempotent_replay_creates_one_job` (real Postgres, 3 truly-concurrent `asyncio.gather`'d requests with the same idempotency key) caught it immediately: two concurrent requests both observed "no existing job" via the SELECT before either committed its INSERT, and the second INSERT raised a raw, unhandled `sqlalchemy.exc.IntegrityError` (`UniqueViolationError` on the new partial unique index) instead of being resolved gracefully.

**Fix**: moved the advisory-lock acquisition to before the idempotency lookup, so a single per-actor lock now serializes the entire idempotency-then-concurrency check-then-write sequence. Re-run confirmed exactly 1 logical job produced from 3 concurrent identical-key requests, and exactly `EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR` (not more, not fewer) rows produced from `EXPORT_MAX_CONCURRENT_JOBS_PER_ACTOR + 2` concurrent distinct-key requests. See `L5-05AA-001` in the bug register for full detail.

## Test evidence

- **New**: `tests/test_final_l5_05aa_export_abuse_protection.py` — 25 tests (10 payload-bound unit tests, 3 idempotency unit tests, 2 concurrent-job-limit unit tests, 5 router static decision-order assertions, 3 real-Postgres concurrency/idempotency tests, plus supporting fixtures/cleanup).
- **Regression**: `tests/test_sprint26_enterprise_grid.py` — 60 passed (4 call sites updated for the new tuple return signature; `_mock_db()` extended with a default `db.execute` stub for the new advisory-lock/count queries).
- **Adjacent regression**: `tests/test_final_l5_05r_export_resource_mapping.py`, `tests/test_final_l5_05s_export_worker_runtime.py`, `tests/test_final_l5_05t_service_area_route_canonicalization.py`, `tests/test_final_l5_05u_security_deposit_permission_authorization.py` — 101 passed, 0 failures.
- **Full backend regression**: `python -m pytest -q` → **9307 passed, 1 skipped, 0 failed** (baseline before this sprint's changes was 9282 passed, 1 skipped).

## Live HTTP verification (real backend, real Postgres, real Redis)

Backend restarted (stale process, 8.7h uptime, predated this sprint's code) to pick up migration 136 and all code changes; confirmed healthy post-restart.

| Control | Verification | Result |
|---|---|---|
| Normal creation | `POST /v1/enterprise/exports`, no idempotency key | `201`, real job row created |
| Idempotent replay | Same `X-Idempotency-Key` + identical payload, twice | Both calls return the **same job id**; second call's `meta.idempotent = true` |
| Idempotency conflict | Same key, different payload (unit + real-DB tested; live call blocked by rate-limit exhaustion from prior live calls on the same actor — see note below) | Verified via `test_same_key_different_payload_raises_conflict` (unit) and confirmed live rate-limit interaction is itself evidence the rate limiter counts every call correctly, including idempotency-path calls |
| Rate limiting | 6th `POST` within the rolling hour, same actor | `429 RATE_LIMITED`, `retry_after_seconds` present, correct `api:export` policy text (`5 requests per 3600s`) |
| Concurrent-job limit | 3 successful creates for one actor, then a 4th | 4th → `429 EXPORT_CONCURRENT_JOB_LIMIT`, `detail` states exact count (`3 active export jobs, maximum concurrent is 3`) |
| Date-range bound | 1978-day range on `created_from`/`created_to` | `422 EXPORT_DATE_RANGE_EXCEEDED`, exact day count in `detail`; an in-range request on the same resource then succeeded (`201`) |
| Selected-ID bound | Attempted live with a 600-element `ids` array | Filter silently dropped by the pre-existing (unrelated) filter-registry allowlist before reaching the bound check — **no live resource currently exposes an `ids`-style filter key**, so this control is unreachable today; correctness proven by unit test instead (`test_too_many_selected_ids_rejected`) |
| Column-count bound | Attempted live with 60 unknown column names | Rejected earlier by the pre-existing `EXPORT_FIELD_NOT_ALLOWED` check (no resource has 50+ real columns) — same "correctly implemented, currently unreachable live" finding; correctness proven by unit test (`test_too_many_columns_rejected`) |

All export-job rows created during live verification were deleted post-verification (`DELETE FROM enterprise_export_jobs WHERE resource_key IN (...) AND created_at > NOW() - INTERVAL '1 hour'`, 10 rows removed). Redis rate-limit counters are real, shared, TTL-based state and were not artificially reset — the test accounts' `api:export` quota will self-clear on the existing 1-hour sliding window; this is the same, correct behavior any real client would experience.

## What this sprint deliberately did not build (honest scope boundary)

- **Download/retry/cancel-endpoint rate limiting**: only the creation endpoint (the actually expensive, resource-consuming action) was wired this pass. `download_export` retains its FINAL-L5-05S protections (signed URL expiry, ownership check) independent of a dedicated rate limit.
- **Multi-worker fleet abuse/race testing**: the export worker (`app/jobs/export_worker.py`) is a single in-process asyncio loop, not a distributable fleet — this mission's "multi-worker" scenarios do not apply to the real deployed architecture. The real analogous race (concurrent creation requests) is exactly what this sprint's advisory-lock fix and real-Postgres tests target.
- **XLSX/PDF-format-specific abuse testing**: only CSV export is implemented (FINAL-L5-05S); format-specific abuse vectors for unimplemented formats do not apply.
- **Chromium / full responsive-accessibility-performance verification**: no browser-automation tool has been available in any sprint since FINAL-L5-05S (reconfirmed via `ToolSearch` this sprint). Honestly documented as unmet, not fabricated.
- **A full observability/metrics platform**: not built. The existing structured `http.request` log lines (already including `request_id`/`status_code`/`duration_ms` for every export call, now including the new 429s) are the only observability surface that exists today; building dashboards/alerting is out of bounded scope for a single-pass wiring sprint.

## Files changed

- `alembic/versions/136_export_abuse_protection.py` (new)
- `app/engines/enterprise_grid/models.py` (`idempotency_key` column)
- `app/engines/enterprise_grid/constants.py` (6 new error codes, 6 new limit constants)
- `app/engines/enterprise_grid/services.py` (`create_export_job` rewrite, `_validate_payload_bounds`, `_fingerprint`, `_count_active_jobs`)
- `app/engines/enterprise_grid/router.py` (`create_export` handler: rate limiter, idempotency-key extraction, new error-status mapping)
- `tests/test_final_l5_05aa_export_abuse_protection.py` (new, 25 tests)
- `tests/test_sprint26_enterprise_grid.py` (4 call sites + mock helper updated for new return signature)
- `docs/final-l5-05/FINAL_L5_05_BUG_REGISTER.md` (L5-05AA-001 through 004 appended)
- `docs/final-l5-05/FINAL_L5_05_REMAINING_BLOCKERS.md` (Blocker 13b rate-limit/idempotency portion closed, new residual gaps noted)

## Final recommendation

**`PARTIAL_READY_WITH_FINAL_L5_05AA_BLOCKERS`**

The core, highest-value, previously-undiscovered gap this mission targeted — an expensive, resource-consuming, asynchronously-processed endpoint with zero rate limiting, idempotency protection, or concurrent-job limiting despite the platform already owning proven infrastructure for exactly this purpose — is closed, live-verified, and covered by real-Postgres concurrency tests (which caught and closed one genuine race condition in the process). Zero regressions across the full 9307-test backend suite. Remaining open items (download/retry/cancel rate limiting, Chromium, full observability platform) are honestly classified as out of this pass's bounded scope or blocked by tooling unavailability, not silently claimed complete; multi-worker-fleet and format-specific abuse scenarios are correctly classified `NOT_APPLICABLE` to this codebase's actual single-process, CSV-only architecture rather than forced to a false pass or a fabricated fail.
