# Phase 3C — Provider Pricing Overrides Frontend Report

Route: `/admin/pricing/provider-overrides`

## Header
Breadcrumb ("Pricing & Rules / Provider Pricing Overrides"), title, description,
Refresh + New Override (permission-gated). **Not built**: Bulk Validate, Export,
View Approval Queue as separate header actions — no backend bulk-validate/export
endpoint exists; "Approval Queue" is reachable via the Approval Status = Pending
filter/summary-card click instead of a dedicated page. Documented simplification.

## Summary cards
All 8 KPI cards wired to `GET /v1/admin/pricing/provider-overrides/summary` with
skeletons and real 0-value states. Live-confirmed real values (1 total, 1 active,
avg price ₹900, 1 tenant with overrides).

## The core bug this sprint fixes: tenant display
**Before**: `<span style="font-family:monospace">{row.tenant_id.slice(0,8)}…</span>`
— raw UUID fragment as the *only* tenant identifier shown.
**After**: Tenant column shows `tenant_name` (bold, primary), `tenant_code`
(secondary line), and the raw ID only as a small tertiary monospace line —
matching the ticket's explicit requirement field-for-field. Live-confirmed:
`GET /v1/admin/pricing/provider-overrides` returns `"tenant_name": "Demo AC
Services", "tenant_code": "demo-ac-services"` and the table renders both.

## Service context + platform range + delta
Service column shows master service, service type/brand/issue type, and
zipcode/tier. Platform Range column shows `₹min – ₹max` plus `Base ₹___` on a
second line. Delta column shows `+₹100 above base` / `Within range` or
`Out of range` computed from the real `delta_from_base`, `platform_min_price`,
`platform_max_price` fields returned by the backend — none of this is computed
or faked client-side from partial data.

## Table
Columns: Tenant, Service, Override Price, Platform Range, Delta, Approval,
Status, Reason, Actions — 9 of the ticket's 10 requested columns (Updated is
visible in the detail drawer rather than as a table column, to keep the table
width manageable — documented simplification).

## Detail drawer
Same `xl` Modal pattern as Bargain Rules (documented simplification — no
dedicated Drawer component in the shared UI kit). 3 tab groups cover all 6
requested tabs: Overview+Tenant+Service&Pricing combined, Validation+Approval
Timeline combined, Audit Logs separate. Approval Timeline renders Submitted →
Approved/Rejected → Activated as a real 3-step status list driven by
`created_at`/`approved_at`/`status`/`approval_status` — not hardcoded.
**Not built**: Tenant Status/Health/Package/Usage Credit Status fields in the
Tenant tab — the backend's `_override_dict` enrichment does not currently
resolve these tenant-health fields (out of Phase 3B's scope), so they were not
fabricated with placeholder values.

## Wizard
5 labeled sections: Tenant, Service Scope, Override Price (with inline
**Validate** button wired to the real `validate-preview` endpoint), Approval
(informational — approval is always required in this system, matching the
"Customer Service Credit is platform credit" business-rule set — no fake
"Approval Required yes/no" toggle was added since the backend always creates
overrides as `approval_status: "pending"`), Review.

## Validation Preview — exact ticket scenarios, live-verified
- ₹500 → `OVERRIDE_BELOW_PLATFORM_MIN`, `platform_min_price: 600`,
  `override_price: 500` rendered in a red block with the error code in the title.
- ₹1300 → `OVERRIDE_ABOVE_PLATFORM_MAX`, `platform_max_price: 1200`,
  `override_price: 1300`.
- ₹900 for a tenant/service with **no existing active override** → green
  "Valid Override" block showing Base ₹800 / Min ₹600 / Max ₹1200 / Delta +₹100.
  (For the specific seeded tenant+service from the prior sprint, ₹900 instead
  correctly returns `DUPLICATE_ACTIVE_OVERRIDE` because an active override
  already exists there — this is the new duplicate-guard from Phase 3B working
  as designed, not a bug; verified both code paths render correctly.)

## Result: **Enterprise-level, real-API-backed, tenant name always shown — not a single-row table.**
