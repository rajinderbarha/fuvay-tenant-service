# FINAL-L5-05O — Dashboard, Contextual Link, Export and In-Page Action Permission Certification

## Scope actually completed this sprint

FINAL-L5-05O's 49-part mission targets exhaustive permission coverage across every dashboard widget, contextual link, report, export, and in-page mutation action, across all 5 roles. Given the true size of that surface (dozens of dashboard widgets, ~150 pages' worth of contextual links, 33 registered export resources, and an effectively unbounded number of row/bulk/overflow actions across the admin app), this sprint made four real, bounded, high-leverage fixes — each investigated from first principles, live-verified, and honestly scoped — rather than attempting shallow coverage of every named surface, consistent with this engagement's established pattern.

### 1. Enterprise Export system had zero domain-permission gating (new P0 finding, not previously known)

**Investigation**: The Sprint 26 "Enterprise Grid" export system (`app/engines/enterprise_grid/`) is the platform's real, general-purpose CSV/XLSX export mechanism, covering 33 registered resources across every admin domain (`admin_finance_deposits`, `admin_finance_topups`, `admin_finance_wallets`, `admin_security_threats`, `admin_security_sessions`, `admin_audit_logs`, `admin_service_jobs`, and 26 others). `create_export_job` (`POST /v1/enterprise/exports`) had **only `get_current_user`** as a dependency — no domain permission check anywhere in the router or service layer. Any authenticated role, including Admin Read Only, could export any resource's real row data by simply supplying its `resource_key`, completely bypassing the domain's own read/export permissions.

**Fix**: `RESOURCE_EXPORT_PERMISSIONS` (`app/engines/enterprise_grid/filter_registry.py`) maps the Finance/Security/Operations-sensitive resources to a real, existing export-shaped backend permission (`FINANCE_EXPORT`, `SECURITY_AUDIT_EXPORT`, `FIELD_OPS_JOBS_EXPORT`) — never a read permission (rule 9). `create_export_job`'s router handler (`app/engines/enterprise_grid/router.py`) now checks this mapping via `permission_checker.has()` and raises the same `PERMISSION_DENIED` shape used by `require_permission()` elsewhere, so the frontend's existing 403 handling needed no changes. Resources not in the map (~25 lower-sensitivity catalog/operational resources) remain open to any authenticated admin — a documented, bounded-scope residual gap (see L5-05O-006 below), not an oversight.

**Live-verified**: Finance resource export — Super Admin/Finance Admin 201, Operations/Security/Read-Only 403. Security resource export — Super Admin/Security Admin 201, others 403. Jobs resource export — Super Admin/Operations Admin 201, others 403.

### 2. finance_hub's 4 export endpoints used a READ permission (rule 9 violation, P1)

**Investigation**: `/v1/admin/finance/{deposits,topups,warranty-claims,payouts}/export` were each gated by their domain's `*_READ` permission — the same permission that gates the corresponding list/summary/detail endpoints. This directly violates rule 9 ("report read permission must not automatically imply export").

**Fix**: All 4 now require `P.FINANCE_EXPORT` (the same key already introduced for the Enterprise Export fix above, kept consistent rather than inventing a second export permission for the same domain). `admin_finance` is granted `FINANCE_EXPORT`; no other non-super-admin role is.

**Live-verified**: `GET /v1/admin/finance/deposits/export` — Super Admin/Finance Admin 200, Operations/Security/Read-Only 403.

### 3. Dashboard widgets were unreachable by every non-super-admin role (new P0 finding, not previously known)

**Investigation**: `app/engines/dashboard_command_center/admin_router.py` already had a well-designed, purpose-built per-widget permission registry (`DASHBOARD_READ`, `DASHBOARD_FINANCE_READ`, `DASHBOARD_OPERATIONS_READ`, `DASHBOARD_SECURITY_READ`, `DASHBOARD_EXPORT`, `DASHBOARD_ACTION_QUEUE_MANAGE`, `DASHBOARD_ENGINE_HEALTH_READ`, `DASHBOARD_ACTIVITY_READ`) — built in an earlier sprint but never wired into any role bundle. Before this sprint, **0 of the 4 non-super-admin roles held `DASHBOARD_READ`**, the base gate every dashboard endpoint requires — meaning every dashboard widget 403'd for every non-super-admin role, and every dashboard page load for those roles was effectively a wall of inline "Permission required" error boxes (matches the interim-acceptable-but-not-good state noted in L5-05M-008/009).

**Fix**: Each of the 4 roles now holds `DASHBOARD_READ` (base) plus its own domain-specific widget permissions:
- `admin_operations`: `DASHBOARD_OPERATIONS_READ`, `DASHBOARD_ACTIVITY_READ`, `DASHBOARD_ENGINE_HEALTH_READ`, `DASHBOARD_ACTION_QUEUE_MANAGE`.
- `admin_finance`: `DASHBOARD_FINANCE_READ` (already held before this sprint).
- `admin_security`: `DASHBOARD_SECURITY_READ`.
- `admin_readonly`: base only — deliberately **no** domain-specific widget, action-queue, or export permission, consistent with its zero-mutation design even though it separately holds broad domain READ access elsewhere.

**Frontend companion fix — request suppression (Part 5)**: `useApi()` (`hooks/useApi.ts`) gained an `enabled` option (default `true`, fully backward-compatible with all ~100 existing call sites); when `false`, the hook never fires the fetch. The dashboard page (`app/admin/dashboard/page.tsx`) now resolves each sensitive widget's permission via `usePermissions()` before rendering, wires `enabled` to the corresponding `useApi` call, and — critically — **does not render the card at all** once permissions resolve and the widget is denied (not a hidden-but-fetched skeleton, not an inline error box: the section simply isn't in the DOM). The "Export Snapshot" quick action and the "Resolve"/"Snooze" action-queue mutations are similarly omitted (not disabled) when the caller lacks `DASHBOARD_EXPORT`/`DASHBOARD_ACTION_QUEUE_MANAGE`. The "Quick Links" panel now filters each link by its real destination-page permission (matching `NAV_GROUPS`, not a page-local guess) — a small, bounded Part 8/9 contextual-link fix.

**Live-verified (API)**: `executive-summary` (base) — all 5 roles 200. `finance-snapshot` — Super Admin/Finance Admin 200, others 403. `compliance-security` — Super Admin/Security Admin 200, others 403.

**Live-verified (Chromium, 8/8 passing)**: each role sees exactly its intended widget set (Operations sees Operations Snapshot + Engine Health, never Finance Snapshot/Compliance & Security/Export Snapshot; Finance sees Finance Snapshot, never Operations Snapshot/Live Operations Board/Compliance & Security; Security sees Compliance & Security, never Finance/Operations Snapshot; Admin Read Only sees none of the three domain widgets and no Export Snapshot, confirmed both in the closed page state and inside the opened header overflow menu). A dedicated network-level test confirms **zero** restricted dashboard requests fire for Admin Read Only (`finance-snapshot`, `compliance-security`, `operations-snapshot`, `action-queue` — none observed).

### 4. Security Deposits page: ungated mutation actions + a real cross-domain permission mismatch (P1, partially fixed)

**Investigation**: `/admin/finance/deposits`'s row overflow menu (Approve/Reject/Record-Offline/Refund/Forfeit-Adjust) had **zero frontend permission gating** — any role able to reach the page (gated only by `finance.security_deposits.read`, which `admin_readonly` and `admin_finance` both hold) would see all 5 mutation menu items regardless of whether the backend would actually allow them. Deeper investigation found a real, pre-existing architecture mismatch: the page's mutation buttons call backend endpoints (`/v1/admin/finance/deposits/{id}/approve|reject|record-offline|refund|adjust`) gated by a **different** permission domain (`finance:deposits:*`, `finance_hub/admin_router.py`) than the page's own route guard and the role bundle's evident intent (`finance.security_deposits.*`) — two independently-named "Security Deposits" permission domains exist side by side. Before this sprint, `admin_finance` held the latter but not the former, meaning Finance Admin could reach the page but every mutation on it would have 403'd despite the role's clear design intent.

**Fix (bounded)**: `admin_finance` is granted the real permissions its intended mutation actions require (`FINANCE_DEPOSITS_READ/APPROVE/UPDATE/REFUND`) — additive, no other role affected. The frontend's `ActionMenu` items are now individually gated via `perm.has()` against the real backend permission each one calls, so denied items are omitted (not disabled) from the menu for any role lacking them.

**Not fixed (documented)**: the two-domain naming mismatch itself is not reconciled — `finance.security_deposits.*` (used for Security Deposit adjustment elsewhere in the Finance Hub domain per FINAL-L5-05L/05J) and `finance:deposits:*` (used by this specific admin page) remain two separate, real permission domains. Reconciling them is a larger architecture decision beyond this sprint's bounded scope, tracked as L5-05O-004 below.

**Live-verified (API)**: `POST .../adjust` — Super Admin/Finance Admin reach the handler (404 on a fake UUID, proving the permission gate passed), Operations/Security/Read-Only 403.

**Live-verified (Chromium)**: Finance Admin reaches the page with no Permission Denied; Admin Read Only reaches the page but the opened overflow menu contains zero of the 4 mutation labels.

## Automated guards

`tests/test_final_l5_05o_inpage_permissions.py` — 33 new tests, all passing: export-permission mapping correctness, finance_hub export-permission separation, dashboard role-bundle correctness (per-role widget grants and cross-domain absence), export role separation (the 8 mandatory pairs from Part 41), the Security Deposits permission-domain-mismatch fix, dashboard request-suppression wiring, and permission-catalog key validity (every new frontend-referenced key exists in the real backend registry — no second permission registry).

## Verification summary

- Full backend regression: 9117+ passed (baseline), re-verified with all new code and the new test file — see commit for exact final count.
- TypeScript: 0 errors.
- Production build: passes, all routes compile.
- Live 5-role API matrix: all 8 mandatory cross-domain denial checks from Part 41 pass with real 403s (Operations→Finance mutation/export, Finance→Job-exceptional-mutation/Security-export, Security→Finance/Operations mutation, Admin Read Only→mutation/export).
- Live 5-role Chromium: 8/8 new tests + 22/22 re-run prior-sprint tests (05L/05M/05N), zero regression.

## Explicitly not attempted this sprint (honestly documented, not hidden)

See `FINAL_L5_05_BUG_REGISTER.md` (L5-05O-001 through 012) and `FINAL_L5_05_REMAINING_BLOCKERS.md` for the itemized list. In summary:

- **~25 of 33 Enterprise Export resources remain unmapped** (catalog/operational domain, lower sensitivity) — reachable by any authenticated admin, not individually classified this sprint.
- **Contextual links** were only bounded-fixed on the dashboard's own Quick Links panel; the ~150-page surface of tenant/job/finance/security detail-page contextual links (Parts 10-13) was not exhaustively inventoried or fixed.
- **Reports** (Part 14) were not separately inventoried as a distinct surface from exports this sprint.
- **In-page mutation actions** beyond the 4 domains fixed here (Jobs/Usage-Credits/Top-ups/Sessions were already covered in FINAL-L5-05M; Security Deposits closed this sprint) remain uncataloged — Tenant/Provider/Staff verify/suspend/reactivate actions (Part 26, confirmed via source read to have zero frontend permission gating on the large `tenants/[id]/page.tsx` file), Notification/System actions (Part 27), and bulk actions (Part 21) across the wider admin app were not touched.
- **Admin Read Only presentation** (Part 28) was extended to the dashboard and Security Deposits this sprint; the broader page-by-page `ReadOnlyNotice` rollout (started in FINAL-L5-05M for 1 page) remains at a small fraction of covered pages.
- **Mobile navigation, accessibility, responsive, and performance verification** (Parts 44-46) were not attempted — same pre-existing, unchanged gaps tracked since FINAL-L5-04/05M/05N.
- **Throttled-network verification** (Part 43) was not run as a dedicated network-throttled Chromium pass; the request-suppression test (Part 5/46) does prove no restricted request fires before permission resolution under normal network conditions.

## Result

Four real, high-leverage, live-verified fixes landed this sprint: (1) closed a genuine P0 gap where the platform's general-purpose export system had zero domain-permission gating across 33 resources; (2) fixed a rule-9 violation where 4 Finance Hub export endpoints relied on read permissions; (3) closed a P0 usability/architecture gap where dashboard widgets were 100% unreachable by every non-super-admin role, with real request-suppression wired in so denied widgets never fetch; (4) fixed Security Deposits' ungated mutation menu and granted Finance Admin the real permissions its role bundle already implied it should have. All four are proven correct via live API calls (real 403s/200s/201s across all 5 roles) and live Chromium (8 new + 22 re-verified prior-sprint tests, zero regression). The much larger remainder of the 49-part mission — exhaustive per-page contextual link/action cataloging, the ~25 remaining export resources, tenant/provider/staff/notification action matrices, mobile/accessibility/responsive/performance verification — is honestly carried forward as documented, evidenced remaining scope, not claimed complete.
