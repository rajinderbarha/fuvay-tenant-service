# Non-Canonical Entry Restrictions — Slice 2

## 1. Legacy review writes — FIXED
- **Before:** `POST /v1/reviews` (legacy `review` engine) was a live, working create endpoint writing to the orphaned `reviews` table, gated only by `get_current_user` (any authenticated user).
- **After:** returns `410 Gone` unconditionally, with a message pointing to the canonical `customer_reviews` engine. GET/list/aggregate/flag/resolve on the same engine are unaffected (legacy reads preserved, per the Phase 1A retirement plan).
- **Frontend impact:** none — Phase 1A's verification (repeated and reconfirmed this slice) found zero frontend callers of this endpoint across all 4 apps.
- **Regression test:** `tests/test_customer_idor.py::test_legacy_review_create_endpoint_is_blocked` — replaces the old spoofed-customer-id IDOR test, which is now moot (there's nothing left to spoof into).

## 2. Dead brands routes — VERIFIED, no code change needed
`frontend/super-admin/lib/api.ts`'s `brandApi`-family calls (brand CRUD, activate/deactivate/archive, category/service mapping, merge, bulk-map, seed) all target `/v1/admin/brands` — the canonical `admin_catalog` brand router. Grepped for any reference to the dead `brands/admin_router.py`/`brands/provider_router.py` paths (which are never mounted per Phase 1's router inventory) and found none. No frontend page links to a route that would 404 against the dead router.

## 3. Deprecated 410 workflows — VERIFIED, no code change needed
`mobile/customer-app/src/features/provider-matching/api/provider-matching-api.ts` already has an explicit code comment confirming it never calls the deprecated `match-providers`/`select-provider` endpoints, only the canonical `match-and-price`. Re-confirmed by direct grep this slice. Security-deposit: super-admin's Finance > Deposits page correctly targets `/v1/admin/finance/deposits*` (finance_hub canonical), not the 410'd `package_commerce` admin endpoints — confirmed via Phase 1A's prior verification, not re-derived from scratch this slice but spot-checked consistent.

## 4. Duplicate navigation entries — VERIFIED, one real referrer fixed
See `navigation-before-after.md`. No duplicate *menu* entries existed; one dashboard widget linked to an orphaned duplicate *page* and was repointed to the canonical one.

## 5. Placeholder roles — 2 real bugs found and fixed (this is the most significant finding of this slice)

### 5a. Super-admin platform-user invite default
`frontend/super-admin/app/admin/users/page.tsx`'s invite-form state defaulted `platform_role` to `"platform_admin"` — a string absent from the form's own `PLATFORM_ROLES` dropdown (which correctly lists only the 5 real admin roles, per an earlier fix noted in-code as `FINAL-L5-05N`). Fixed default to `"admin_readonly"`.

### 5b. Tenant user creation — newly discovered this slice, not previously flagged in Phase 1 or 1A
`app/engines/tenant_engine/admin_service.py::VALID_TENANT_ROLES` accepted `"tenant_manager"`, `"tenant_staff_admin"`, `"tenant_finance"`, `"tenant_support"` as valid values for the real `User.role` column — none of which exist in `app/core/permissions.py::ROLE_PERMISSIONS`. A tenant user created with any of these role strings would pass creation successfully but then get **zero permissions, permanently, on every subsequent request**, because `PermissionChecker.has()` has no entry for that role string. This is worse than the super-admin case above (5a), because 5a's mismatch was cosmetic (wrong default in a dropdown with correct options); this one was a live, silent authorization dead-end reachable by any super_admin using the "Add Tenant User" form's default settings without touching the Role field.

Fixed:
- Backend: `VALID_TENANT_ROLES` narrowed to `{"tenant_owner", "staff"}` (the only 2 real roles this endpoint should ever grant — technician onboarding uses a separate endpoint, `createStaff`, unaffected).
- Frontend: dropdown options reduced to Owner/Staff; default value fixed to `"staff"`.
- Tests: `tests/test_sprint4_tenant_onboarding.py` — fixed 1 existing test that used the now-invalid `"tenant_manager"` value, added 4 new parametrized regression tests (`test_create_user_rejects_former_placeholder_roles`) locking all 4 removed placeholder strings closed.

### 5c. Other placeholder-role-shaped arrays found, NOT fixed this slice (documented, not silently ignored)
Grepped for the 6 Phase-1A-flagged aspirational role names across `frontend/super-admin/app`. Found matches in `notifications/templates/page.tsx` (`AUDIENCES` array), `checklists/page.tsx` (`OWNER_ROLES`), `compliance/page.tsx`, `intelligence/page.tsx` (`ALL_ROLES`), and `workflow-templates/page.tsx` — all containing invented role-like strings (`support_admin`, `finance_admin`, `compliance_officer`, `tenant_manager`, `platform_admin`, etc.) used as **audience/ownership tags** for templates/checklists/workflows, not as live `User.role`-writing selectors like 5a/5b above. Fixing these correctly requires confirming, for each, whether the tag is (a) cosmetic categorization with no authorization consequence, or (b) actually compared against a real user's role somewhere downstream — that investigation was not completed this slice (6 separate contexts, each needing its own read), so no fix was applied to avoid guessing at the correct real-role mapping. See `known-limitations.md` and `deferred-items.md`.

## 6. Pages using confirmed disconnected endpoints
Not re-audited beyond what Phase 1A already covered (`/v1/bookings`, `/v1/jobs` (field_ops) — confirmed *not* disconnected, actively used; see Phase 1A's `booking-job-canonical-decision.md`). No new disconnected-endpoint page was found this slice.

## 7. Pages with non-canonical write actions
The tenant-user-creation bug (5b) is exactly this category — a write action (`create_user`) that could produce a non-canonical (unrecognized) role value. Fixed as above. No other non-canonical write action was found this slice.
