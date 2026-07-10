# Admin A3 — Remaining Blockers (all non-blocking for certification)

1. **List filters incomplete** — no vertical / bookability / health-band /
   deposit / usage-credit-range filters in `adminTenantsApi.list()`.
   Ticket examples suggest these; not present. Low risk (search/status/
   plan/date filters cover the primary use cases).
2. **Bulk "Suspend All" is a non-functional stub** on the list page
   (~line 917). Pre-existing, not touched this sprint.
3. **Add Admin Note has no frontend UI** — backend endpoint, service
   method, validation, and `adminTenantsApi.addNote()` client method are
   all complete and live-verified, but no button/modal was wired into the
   3044-line detail page's action menu this sprint (file size/time
   constraint).
4. **Fine-grained `admin.tenants.*` permissions not wired** — the real,
   frontend-facing router uses only coarse `require_super_admin`. A
   parallel, fully permission-gated router exists but is unused by the
   frontend. Confirmed low-risk today (`super_admin` role has the `P.ALL`
   wildcard) but architecturally incomplete; recommend a dedicated future
   sprint.
5. **"Wallet" tab naming/data-source inconsistency** — a section in the
   detail page is internally named "Wallet" and calls
   `commerceApi.walletBalance/Transactions` instead of the tenant-admin
   API's own equivalent. No forbidden label text is shown (finance gate
   still passes), but the two API surfaces should be unified.
6. **Overview readiness checklist is client-computed**, not sourced from
   the real `/v1/tenants/{id}/360` endpoint that exists on the unused
   parallel router. Same underlying data either way; not a correctness
   bug, but a missed opportunity for a single source of truth.
7. **External modification observed** (pre-existing, out of A3's scope):
   `frontend/tenant-portal/app/(tenant)/tenant/setup/services/page.tsx`
   continues to diverge from its previously-certified state (same pattern
   documented in the A11 sprint), causing 2 unrelated test failures in
   `test_home_services_menu_and_price_range.py`. Not reverted per standing
   session instruction to not fight externally/intentionally modified
   files. A3 does not touch the tenant-portal at all.

None of the above block the tenant-management/Provider-360 module itself
from being certified — all core list/detail/action/audit/finance-label/
data-accuracy requirements are met with real, DB-backed implementations,
and one genuine cross-sprint bug (audit-trail gap) was found and fixed
with live verification.
